"""Head-wise active-decision SMDP PPO for V114 V9.

Only decisions with more than one legal action contribute to a head's actor
loss, entropy, and exact KL.  Each active head has equal weight regardless of
how many rows are active; ratios are never multiplied across heads.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import time
from typing import Any, Mapping, Sequence

from flax import serialization
from flax.core import unfreeze
from flax.training.train_state import TrainState
import jax
import jax.numpy as jnp
import numpy as np
import optax

try:
    from .event_ppo_math import (
        HEAD_NAMES,
        HEAD_SIZES,
        duration_aware_smdp_gae,
        masked_categorical_entropy,
        masked_categorical_kl,
        masked_categorical_log_probability,
        validate_action_masks,
    )
    from .event_program_features import FEATURE_SCHEMA, MANAGER_FEATURE_DIM
    from .model_event_program_ppo import validate_checkpoint_metadata
    from .train_event_program_ppo import (
        PPOConfig,
        _validate_report_contract,
        atomic_checkpoint,
        atomic_json,
        create_train_state,
        file_sha256,
        load_npz,
        parameter_change_report,
        validate_npz_contract,
    )
except ImportError:  # Direct-file CLI execution.
    from event_ppo_math import (  # type: ignore
        HEAD_NAMES,
        HEAD_SIZES,
        duration_aware_smdp_gae,
        masked_categorical_entropy,
        masked_categorical_kl,
        masked_categorical_log_probability,
        validate_action_masks,
    )
    from event_program_features import FEATURE_SCHEMA, MANAGER_FEATURE_DIM  # type: ignore
    from model_event_program_ppo import validate_checkpoint_metadata  # type: ignore
    from train_event_program_ppo import (  # type: ignore
        PPOConfig,
        _validate_report_contract,
        atomic_checkpoint,
        atomic_json,
        create_train_state,
        file_sha256,
        load_npz,
        parameter_change_report,
        validate_npz_contract,
    )


TRAINING_SCHEMA = "kaggriculture-v114-event-program-headwise-ppo-training-v2"
REWARD_SCHEMA = "v114-v9-relative-share-terminal-plus-potential-v2"
TRAINING_METHOD = "headwise_active_decision_smdp_ppo_v2"
ADAPTIVE_TRAINING_METHOD = "responsibility_scoped_adaptive_active_head_smdp_ppo_v3"
NORMALIZATION_GROUPS = ("easy", "learnable", "hard_gold")


@dataclass(frozen=True)
class RewardConfig:
    outcome_win: float = 1.0
    outcome_draw: float = 0.0
    outcome_loss: float = -1.0
    relative_share_coefficient: float = 1.0
    own_economy_coefficient: float = 0.1
    catastrophe_penalty: float = 1.0
    potential_coefficient: float = 0.1
    potential_money_center: float = 3000.0
    potential_money_scale: float = 10000.0
    own_economy_center: float = 3000.0
    own_economy_scale: float = 10000.0


def normalization_group(binding_key: str) -> str:
    """Return the slash prefix used as the standardization group."""

    if binding_key.count("/") != 1:
        raise ValueError("binding key must have exactly one slash: layer/member")
    group, member = (part.strip() for part in binding_key.split("/", 1))
    if group not in NORMALIZATION_GROUPS:
        raise ValueError(
            f"binding prefix must be one of {NORMALIZATION_GROUPS}, got {group!r}"
        )
    if not member:
        raise ValueError("binding member must be non-empty")
    return group


def parse_unique_bindings(values: Sequence[str], *, flag: str) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for raw in values:
        if "=" not in raw:
            raise ValueError(f"{flag} requires layer/member=PATH, got {raw!r}")
        key, raw_path = raw.split("=", 1)
        key = key.strip()
        normalization_group(key)
        if key in result:
            raise ValueError(f"duplicate {flag} binding key: {key}")
        path = Path(raw_path).expanduser().resolve()
        if not raw_path.strip() or not path.is_file():
            raise ValueError(f"{flag} path does not exist: {path}")
        result[key] = path
    if not result:
        raise ValueError(f"at least one {flag} is required")
    return result


def pair_bindings(
    dataset_values: Sequence[str], report_values: Sequence[str]
) -> dict[str, tuple[Path, Path]]:
    datasets = parse_unique_bindings(dataset_values, flag="--dataset")
    reports = parse_unique_bindings(report_values, flag="--rollout-report")
    if set(datasets) != set(reports):
        raise ValueError(
            "dataset/report binding keys must match exactly: "
            f"datasets={sorted(datasets)}, reports={sorted(reports)}"
        )
    return {key: (datasets[key], reports[key]) for key in datasets}


def terminal_outcome_reward(
    *,
    score: float,
    own_reward: float,
    opponent_reward: float,
    catastrophe: bool,
    config: RewardConfig,
) -> float:
    """Public terminal reward without the deprecated tanh-margin term."""

    if score == 1.0:
        outcome = config.outcome_win
    elif score == 0.5:
        outcome = config.outcome_draw
    elif score == 0.0:
        outcome = config.outcome_loss
    else:
        raise ValueError(f"score must be 0, 0.5 or 1, got {score}")
    own = float(own_reward)
    opponent = float(opponent_reward)
    relative_share = 2.0 * own / max(own + opponent, 1.0) - 1.0
    own_economy = np.tanh(
        (own - config.own_economy_center) / config.own_economy_scale
    )
    return float(
        outcome
        + config.relative_share_coefficient * relative_share
        + config.own_economy_coefficient * own_economy
        - config.catastrophe_penalty * float(bool(catastrophe))
    )


def potential_shaping(
    own_money_start: np.ndarray,
    own_money_end: np.ndarray,
    durations_turns: np.ndarray,
    terminals: np.ndarray,
    *,
    gamma_day: float,
    config: RewardConfig,
) -> np.ndarray:
    start_phi = (
        np.asarray(own_money_start, dtype=np.float64)
        - config.potential_money_center
    ) / config.potential_money_scale
    next_phi = (
        np.asarray(own_money_end, dtype=np.float64)
        - config.potential_money_center
    ) / config.potential_money_scale
    next_phi = np.where(np.asarray(terminals, dtype=np.bool_), 0.0, next_phi)
    discount = np.power(
        float(gamma_day), np.asarray(durations_turns, dtype=np.float64) / 24.0
    )
    return config.potential_coefficient * (discount * next_phi - start_phi)


def compute_episode_rewards(
    data: Mapping[str, np.ndarray],
    begin: int,
    end: int,
    *,
    reward_config: RewardConfig,
    gamma_day: float,
) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
    terminals = np.asarray(data["terminal"])[begin:end].astype(np.bool_)
    shaping = potential_shaping(
        np.asarray(data["own_money_start"])[begin:end],
        np.asarray(data["own_money_end"])[begin:end],
        np.asarray(data["duration_turns"])[begin:end],
        terminals,
        gamma_day=gamma_day,
        config=reward_config,
    )
    terminal = terminal_outcome_reward(
        score=float(np.asarray(data["score"])[begin]),
        own_reward=float(np.asarray(data["candidate_reward"])[begin]),
        opponent_reward=float(np.asarray(data["opponent_reward"])[begin]),
        catastrophe=bool(np.asarray(data["catastrophe"])[begin]),
        config=reward_config,
    )
    rewards = shaping.astype(np.float32)
    rewards[-1] += np.float32(terminal)
    constraint_rewards = np.zeros(end - begin, dtype=np.float32)
    constraint_rewards[-1] = float(bool(np.asarray(data["catastrophe"])[begin]))
    return rewards, constraint_rewards, {
        "terminal_reward": terminal,
        "potential_shaping_sum": float(np.sum(shaping)),
        "training_reward_sum": float(np.sum(rewards)),
    }


def standardize_by_group(
    values: np.ndarray, groups: np.ndarray
) -> tuple[np.ndarray, dict[str, Any]]:
    values = np.asarray(values, dtype=np.float32)
    groups = np.asarray(groups).astype(str)
    if values.shape != groups.shape:
        raise ValueError("values and groups must share shape")
    result = np.empty_like(values)
    report: dict[str, Any] = {}
    for group in dict.fromkeys(groups.tolist()):
        if group not in NORMALIZATION_GROUPS:
            raise ValueError(f"unsupported normalization group {group!r}")
        selected = groups == group
        current = values[selected].astype(np.float64)
        mean, std = float(np.mean(current)), float(np.std(current))
        result[selected] = 0.0 if std < 1.0e-8 else (current - mean) / std
        report[group] = {
            "samples": int(np.sum(selected)),
            "raw_mean": mean,
            "raw_std": std,
            "normalized_mean": float(np.mean(result[selected])),
            "normalized_std": float(np.std(result[selected])),
        }
    return result, report


def prepare_binding_training_data(
    binding_key: str,
    data: Mapping[str, np.ndarray],
    *,
    reward_config: RewardConfig,
    ppo_config: PPOConfig,
) -> tuple[dict[str, np.ndarray], list[dict[str, float]]]:
    group = normalization_group(binding_key)
    offsets = np.asarray(data["episode_offsets"], dtype=np.int64)
    rows = int(np.asarray(data["features"]).shape[0])
    reward_advantages = np.empty(rows, dtype=np.float32)
    reward_returns = np.empty(rows, dtype=np.float32)
    constraint_advantages = np.empty(rows, dtype=np.float32)
    constraint_returns = np.empty(rows, dtype=np.float32)
    reward_rows: list[dict[str, float]] = []
    for episode_index in range(len(offsets) - 1):
        begin, end = int(offsets[episode_index]), int(offsets[episode_index + 1])
        rewards, constraint_rewards, reward_row = compute_episode_rewards(
            data,
            begin,
            end,
            reward_config=reward_config,
            gamma_day=ppo_config.gamma_day,
        )
        reward_gae = duration_aware_smdp_gae(
            jnp.asarray(rewards),
            jnp.asarray(data["value"][begin:end]),
            jnp.asarray(data["next_value"][begin:end]),
            jnp.asarray(data["terminal"][begin:end]),
            jnp.asarray(data["duration_turns"][begin:end]),
            gamma_day=ppo_config.gamma_day,
            lambda_day=ppo_config.lambda_day,
        )
        constraint_gae = duration_aware_smdp_gae(
            jnp.asarray(constraint_rewards),
            jnp.asarray(data["constraint_value"][begin:end]),
            jnp.asarray(data["next_constraint_value"][begin:end]),
            jnp.asarray(data["terminal"][begin:end]),
            jnp.asarray(data["duration_turns"][begin:end]),
            gamma_day=ppo_config.gamma_day,
            lambda_day=ppo_config.lambda_day,
        )
        reward_advantages[begin:end] = np.asarray(reward_gae["advantages"])
        reward_returns[begin:end] = np.asarray(reward_gae["returns"])
        constraint_advantages[begin:end] = np.asarray(constraint_gae["advantages"])
        constraint_returns[begin:end] = np.asarray(constraint_gae["returns"])
        reward_rows.append(reward_row)
    return {
        "binding": np.full(rows, binding_key),
        "normalization_group": np.full(rows, group),
        "reward_advantage_raw": reward_advantages,
        "reward_return": reward_returns,
        "constraint_advantage_raw": constraint_advantages,
        "constraint_return": constraint_returns,
    }, reward_rows


def recompute_old_head_logp(
    data: Mapping[str, np.ndarray]
) -> dict[str, np.ndarray]:
    rows = int(np.asarray(data["features"]).shape[0])
    masks = {name: np.asarray(data[f"mask_{name}"]) for name in HEAD_NAMES}
    validate_action_masks(masks, batch_size=rows)
    result: dict[str, np.ndarray] = {}
    for name in HEAD_NAMES:
        actions = np.asarray(data[f"action_{name}"])
        logits = np.asarray(data[f"old_logits_{name}"])
        if actions.shape != (rows,) or not np.issubdtype(actions.dtype, np.integer):
            raise ValueError(f"action_{name} must be an integer vector")
        if logits.shape != (rows, HEAD_SIZES[name]) or not np.all(np.isfinite(logits)):
            raise ValueError(f"old_logits_{name} is incomplete or non-finite")
        if np.any(actions < 0) or np.any(actions >= HEAD_SIZES[name]):
            raise ValueError(f"action_{name} is outside its head")
        if not np.all(masks[name][np.arange(rows), actions.astype(np.int64)]):
            raise ValueError(f"action_{name} contains a forbidden action")
        values = masked_categorical_log_probability(
            jnp.asarray(logits, dtype=jnp.float32),
            jnp.asarray(actions, dtype=jnp.int32),
            jnp.asarray(masks[name], dtype=jnp.bool_),
        )
        result[name] = np.asarray(jax.device_get(values), dtype=np.float32)
        if not np.all(np.isfinite(result[name])):
            raise ValueError(f"recomputed old logp is non-finite for {name}")
    if "old_joint_logp" in data:
        summed = sum((result[name] for name in HEAD_NAMES), np.zeros(rows, np.float32))
        stored = np.asarray(data["old_joint_logp"], dtype=np.float32)
        if stored.shape != (rows,) or not np.allclose(
            stored, summed, rtol=1.0e-5, atol=2.0e-5
        ):
            raise ValueError("stored old_joint_logp differs from recomputed head logps")
    return result


def concatenate_bindings(
    bindings: Mapping[str, Mapping[str, np.ndarray]],
    prepared: Mapping[str, Mapping[str, np.ndarray]],
    *,
    constraint_lambda: float,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    ordered = list(bindings)
    result: dict[str, np.ndarray] = {}
    data_keys = (
        "features",
        "value",
        "constraint_value",
        *(f"mask_{name}" for name in HEAD_NAMES),
        *(f"action_{name}" for name in HEAD_NAMES),
        *(f"old_logits_{name}" for name in HEAD_NAMES),
    )
    old_head_logps = {
        key: recompute_old_head_logp(bindings[key]) for key in ordered
    }
    for key in data_keys:
        result[key] = np.concatenate(
            [np.asarray(bindings[binding][key]) for binding in ordered]
        )
    for name in HEAD_NAMES:
        result[f"old_logp_{name}"] = np.concatenate(
            [old_head_logps[binding][name] for binding in ordered]
        )
    for key in (
        "binding",
        "normalization_group",
        "reward_advantage_raw",
        "reward_return",
        "constraint_advantage_raw",
        "constraint_return",
    ):
        result[key] = np.concatenate(
            [np.asarray(prepared[binding][key]) for binding in ordered]
        )
    result["constraint_event"] = np.concatenate(
        [np.asarray(bindings[binding]["catastrophe"], dtype=np.bool_) for binding in ordered]
    )
    groups = result["normalization_group"]
    reward_advantage, reward_stats = standardize_by_group(
        result["reward_advantage_raw"], groups
    )
    constraint_advantage, constraint_stats = standardize_by_group(
        result["constraint_advantage_raw"], groups
    )
    for group in dict.fromkeys(groups.astype(str).tolist()):
        selected = groups.astype(str) == group
        observed = int(np.sum(result["constraint_event"][selected]))
        enabled = observed > 0
        constraint_stats[group]["observed_constraint_events"] = observed
        constraint_stats[group]["actor_constraint_enabled"] = enabled
        if not enabled:
            constraint_advantage[selected] = 0.0
    result["reward_advantage"] = reward_advantage
    result["constraint_advantage"] = constraint_advantage
    result["actor_advantage"] = (
        reward_advantage - float(constraint_lambda) * constraint_advantage
    )
    return result, {"reward": reward_stats, "constraint": constraint_stats}


def make_batch(data: Mapping[str, np.ndarray], indices: Sequence[int]) -> dict[str, Any]:
    selected = np.asarray(indices, dtype=np.int64)
    return {
        "features": jnp.asarray(np.asarray(data["features"])[selected], dtype=jnp.float32),
        "shared_masks": {
            name: jnp.asarray(np.asarray(data[f"mask_{name}"])[selected], dtype=jnp.bool_)
            for name in HEAD_NAMES
        },
        "actions": {
            name: jnp.asarray(np.asarray(data[f"action_{name}"])[selected], dtype=jnp.int32)
            for name in HEAD_NAMES
        },
        "old_logits": {
            name: jnp.asarray(np.asarray(data[f"old_logits_{name}"])[selected], dtype=jnp.float32)
            for name in HEAD_NAMES
        },
        "old_logp": {
            name: jnp.asarray(np.asarray(data[f"old_logp_{name}"])[selected], dtype=jnp.float32)
            for name in HEAD_NAMES
        },
        "actor_advantage": jnp.asarray(
            np.asarray(data["actor_advantage"])[selected], dtype=jnp.float32
        ),
        "reward_return": jnp.asarray(
            np.asarray(data["reward_return"])[selected], dtype=jnp.float32
        ),
        "constraint_return": jnp.asarray(
            np.asarray(data["constraint_return"])[selected], dtype=jnp.float32
        ),
    }


def headwise_actor_objective(
    new_logits: Mapping[str, jnp.ndarray],
    batch: Mapping[str, Any],
    *,
    config: PPOConfig,
    actor_heads: Sequence[str] = HEAD_NAMES,
) -> tuple[jnp.ndarray, dict[str, Any]]:
    """Equal-head PPO objective using only active rows and per-head ratios."""

    advantage = jax.lax.stop_gradient(batch["actor_advantage"])
    head_metrics: dict[str, dict[str, jnp.ndarray]] = {}
    weighted_losses: list[jnp.ndarray] = []
    optimized_head_flags: list[jnp.ndarray] = []
    active_kls: list[jnp.ndarray] = []
    actor_head_set = frozenset(actor_heads)
    unknown = actor_head_set.difference(HEAD_NAMES)
    if unknown or not actor_head_set:
        raise ValueError(f"invalid actor_heads: {sorted(actor_head_set)}")
    for name in HEAD_NAMES:
        mask = batch["shared_masks"][name]
        active = (jnp.sum(mask, axis=-1) > 1).astype(jnp.float32)
        active_count = jnp.sum(active)
        denominator = jnp.maximum(active_count, 1.0)
        has_active = (active_count > 0).astype(jnp.float32)
        new_logp = masked_categorical_log_probability(
            new_logits[name], batch["actions"][name], mask
        )
        old_logp = jax.lax.stop_gradient(batch["old_logp"][name])
        log_ratio = new_logp - old_logp
        ratio = jnp.exp(log_ratio)
        unclipped = ratio * advantage
        clipped = jnp.clip(
            ratio, 1.0 - config.clip_epsilon, 1.0 + config.clip_epsilon
        ) * advantage
        policy_loss = -jnp.sum(active * jnp.minimum(unclipped, clipped)) / denominator
        entropy_rows = masked_categorical_entropy(new_logits[name], mask)
        entropy = jnp.sum(active * entropy_rows) / denominator
        exact_kl_rows = masked_categorical_kl(
            batch["old_logits"][name], new_logits[name], mask
        )
        exact_kl = jnp.sum(active * exact_kl_rows) / denominator
        approximate_kl = jnp.sum(
            active * ((ratio - 1.0) - log_ratio)
        ) / denominator
        clip_fraction = jnp.sum(
            active * (jnp.abs(ratio - 1.0) > config.clip_epsilon).astype(jnp.float32)
        ) / denominator
        actor_loss = policy_loss - config.entropy_coefficient * entropy
        optimized = float(name in actor_head_set)
        weighted_losses.append(optimized * has_active * actor_loss)
        optimized_head_flags.append(optimized * has_active)
        active_kls.append(jnp.where(has_active > 0, exact_kl, -jnp.inf))
        head_metrics[name] = {
            "optimized": bool(name in actor_head_set),
            "active_samples": active_count,
            "active_fraction": active_count / jnp.maximum(float(active.shape[0]), 1.0),
            "policy_loss": policy_loss,
            "entropy": entropy,
            "exact_kl": exact_kl,
            "approximate_kl": approximate_kl,
            "clip_fraction": clip_fraction,
            "mean_ratio": jnp.sum(active * ratio) / denominator,
        }
    active_head_count = sum(optimized_head_flags, jnp.asarray(0.0, jnp.float32))
    actor_loss = sum(weighted_losses, jnp.asarray(0.0, jnp.float32)) / jnp.maximum(
        active_head_count, 1.0
    )
    max_active_kl = jnp.where(
        active_head_count > 0,
        jnp.max(jnp.stack(active_kls)),
        jnp.asarray(0.0, jnp.float32),
    )
    return actor_loss, {
        "active_head_count": active_head_count,
        "max_active_head_exact_kl": max_active_kl,
        "heads": head_metrics,
    }


def ppo_loss(
    params: Any,
    apply_fn: Any,
    batch: Mapping[str, Any],
    *,
    config: PPOConfig,
    actor_heads: Sequence[str] = HEAD_NAMES,
) -> tuple[jnp.ndarray, dict[str, Any]]:
    outputs = apply_fn({"params": params}, batch["features"])
    actor_loss, actor_metrics = headwise_actor_objective(
        outputs["actor_logits"], batch, config=config, actor_heads=actor_heads
    )
    value_loss = jnp.mean((outputs["value"] - batch["reward_return"]) ** 2)
    constraint_value_loss = jnp.mean(
        (outputs["constraint_value"] - batch["constraint_return"]) ** 2
    )
    total = (
        actor_loss
        + config.value_coefficient * value_loss
        + config.constraint_value_coefficient * constraint_value_loss
    )
    return total, {
        "loss": total,
        "actor_loss": actor_loss,
        "value_loss": value_loss,
        "constraint_value_loss": constraint_value_loss,
        **actor_metrics,
    }


def train_minibatch(
    state: TrainState,
    batch: Mapping[str, Any],
    *,
    config: PPOConfig,
    actor_heads: Sequence[str] = HEAD_NAMES,
) -> tuple[TrainState, dict[str, Any]]:
    def loss_fn(params: Any) -> tuple[jnp.ndarray, dict[str, Any]]:
        return ppo_loss(
            params, state.apply_fn, batch, config=config, actor_heads=actor_heads
        )

    (_, metrics), gradients = jax.value_and_grad(loss_fn, has_aux=True)(state.params)
    return state.apply_gradients(grads=gradients), metrics


def create_scoped_train_state(
    params: Mapping[str, Any],
    config: PPOConfig,
    *,
    actor_heads: Sequence[str],
) -> TrainState:
    """Freeze the shared trunk and every non-selected actor projection."""

    actor_roots = frozenset(f"{name}_head" for name in actor_heads)
    critic_roots = frozenset(("value_head", "constraint_value_head"))

    def label(path: Any, _: Any) -> str:
        root = getattr(path[0], "key", None) if path else None
        if root in actor_roots:
            return "actor"
        if root in critic_roots:
            return "critic"
        return "frozen"

    labels = jax.tree_util.tree_map_with_path(label, params)
    optimizer = optax.chain(
        optax.clip_by_global_norm(float(config.gradient_clip_norm)),
        optax.multi_transform(
            {
                "actor": optax.adam(float(config.actor_learning_rate)),
                "critic": optax.adam(float(config.critic_learning_rate)),
                "frozen": optax.set_to_zero(),
            },
            labels,
        ),
    )
    from model_event_program_ppo import EventProgramPPOManager  # type: ignore

    model = EventProgramPPOManager()
    return TrainState.create(apply_fn=model.apply, params=params, tx=optimizer)


def parameter_root_changes(initial: Mapping[str, Any], final: Mapping[str, Any]) -> dict[str, float]:
    """Maximum absolute change for every top-level parameter root."""

    report: dict[str, float] = {}
    if set(initial) != set(final):
        raise ValueError("parameter roots changed during training")
    for root in initial:
        left = jax.tree_util.tree_leaves(initial[root])
        right = jax.tree_util.tree_leaves(final[root])
        if len(left) != len(right):
            raise ValueError(f"parameter leaf structure changed for {root}")
        report[root] = max(
            (
                float(np.max(np.abs(np.asarray(a) - np.asarray(b))))
                for a, b in zip(left, right)
            ),
            default=0.0,
        )
    return report


def production_behavior_diagnostics(
    state: TrainState,
    data: Mapping[str, np.ndarray],
    *,
    sampling_seed: int,
) -> dict[str, Any]:
    """Measure distribution and fixed-random action changes without simulator access."""

    name = "production_line"
    features = jnp.asarray(data["features"], dtype=jnp.float32)
    mask = np.asarray(data[f"mask_{name}"], dtype=np.bool_)
    active = np.sum(mask, axis=-1) > 1
    old_logits = np.asarray(data[f"old_logits_{name}"], dtype=np.float64)
    new_logits = np.asarray(
        state.apply_fn({"params": state.params}, features)["actor_logits"][name],
        dtype=np.float64,
    )

    def probabilities(logits: np.ndarray) -> np.ndarray:
        masked = np.where(mask, logits, -np.inf)
        maximum = np.max(masked, axis=-1, keepdims=True)
        exponent = np.where(mask, np.exp(masked - maximum), 0.0)
        return exponent / np.sum(exponent, axis=-1, keepdims=True)

    old_probability = probabilities(old_logits)
    new_probability = probabilities(new_logits)
    selected = np.flatnonzero(active)
    if not len(selected):
        raise ValueError("production_line has no active rows")
    total_variation = 0.5 * np.sum(
        np.abs(new_probability[selected] - old_probability[selected]), axis=-1
    )
    old_greedy = np.argmax(old_probability[selected], axis=-1)
    new_greedy = np.argmax(new_probability[selected], axis=-1)
    uniforms = np.random.default_rng(int(sampling_seed)).random(len(selected))

    def inverse_cdf(probability: np.ndarray) -> np.ndarray:
        cumulative = np.cumsum(probability, axis=-1)
        return np.sum(uniforms[:, None] > cumulative, axis=-1)

    old_sample = inverse_cdf(old_probability[selected])
    new_sample = inverse_cdf(new_probability[selected])
    return {
        "active_rows": int(len(selected)),
        "mean_total_variation": float(np.mean(total_variation)),
        "max_total_variation": float(np.max(total_variation)),
        "greedy_changed_rows": int(np.sum(old_greedy != new_greedy)),
        "fixed_uniform_changed_rows": int(np.sum(old_sample != new_sample)),
        "fixed_uniform_seed": int(sampling_seed),
    }


def _host_metrics(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _host_metrics(item) for key, item in value.items()}
    array = np.asarray(jax.device_get(value))
    return float(array) if array.shape == () else array.tolist()


def evaluate_state(
    state: TrainState,
    data: Mapping[str, np.ndarray],
    *,
    config: PPOConfig,
    actor_heads: Sequence[str] = HEAD_NAMES,
) -> dict[str, Any]:
    batch = make_batch(data, np.arange(len(data["features"])))
    _, metrics = ppo_loss(
        state.params, state.apply_fn, batch, config=config, actor_heads=actor_heads
    )
    return _host_metrics(metrics)


def _economy_summary(data: Mapping[str, np.ndarray]) -> dict[str, Any]:
    offsets = np.asarray(data["episode_offsets"], dtype=np.int64)
    terminal_indices = offsets[1:] - 1
    score = np.asarray(data["score"])[terminal_indices]
    own = np.asarray(data["candidate_reward"], dtype=np.float64)[terminal_indices]
    opponent = np.asarray(data["opponent_reward"], dtype=np.float64)[terminal_indices]
    catastrophe = np.asarray(data["catastrophe"])[terminal_indices].astype(bool)
    relative_share = 2.0 * own / np.maximum(own + opponent, 1.0) - 1.0
    return {
        "episodes": int(len(terminal_indices)),
        "wdl": {
            "wins": int(np.sum(score == 1.0)),
            "draws": int(np.sum(score == 0.5)),
            "losses": int(np.sum(score == 0.0)),
        },
        "score_rate": float(np.mean(score)),
        "mean_own_reward": float(np.mean(own)),
        "p10_own_reward": float(np.percentile(own, 10)),
        "mean_opponent_reward": float(np.mean(opponent)),
        "mean_money_margin": float(np.mean(own - opponent)),
        "mean_relative_share": float(np.mean(relative_share)),
        "catastrophes": int(np.sum(catastrophe)),
        "catastrophe_rate": float(np.mean(catastrophe)),
    }


def _merge_group_summary(
    binding_data: Mapping[str, Mapping[str, np.ndarray]]
) -> dict[str, Any]:
    grouped: dict[str, dict[str, list[np.ndarray]]] = {}
    for key, data in binding_data.items():
        group = normalization_group(key)
        offsets = np.asarray(data["episode_offsets"], dtype=np.int64)
        terminal = offsets[1:] - 1
        target = grouped.setdefault(
            group, {name: [] for name in ("score", "own", "opponent", "catastrophe")}
        )
        target["score"].append(np.asarray(data["score"])[terminal])
        target["own"].append(np.asarray(data["candidate_reward"])[terminal])
        target["opponent"].append(np.asarray(data["opponent_reward"])[terminal])
        target["catastrophe"].append(np.asarray(data["catastrophe"])[terminal])
    report: dict[str, Any] = {}
    for group, values in grouped.items():
        score = np.concatenate(values["score"])
        own = np.concatenate(values["own"]).astype(np.float64)
        opponent = np.concatenate(values["opponent"]).astype(np.float64)
        catastrophe = np.concatenate(values["catastrophe"]).astype(bool)
        report[group] = {
            "episodes": int(len(score)),
            "wdl": {
                "wins": int(np.sum(score == 1.0)),
                "draws": int(np.sum(score == 0.5)),
                "losses": int(np.sum(score == 0.0)),
            },
            "score_rate": float(np.mean(score)),
            "mean_own_reward": float(np.mean(own)),
            "mean_opponent_reward": float(np.mean(opponent)),
            "mean_money_margin": float(np.mean(own - opponent)),
            "catastrophe_rate": float(np.mean(catastrophe)),
        }
    return report


def build_checkpoint_payload(
    initial_payload: Mapping[str, Any],
    params: Any,
    *,
    initial_checkpoint_sha256: str,
    source_sha256: Mapping[str, str],
    dataset_sha256: Mapping[str, str],
    rollout_report_sha256: Mapping[str, str],
    reward_config: RewardConfig,
    ppo_config: PPOConfig,
    iteration: int,
    training_seed: int,
    training_method: str = TRAINING_METHOD,
) -> dict[str, Any]:
    payload = {key: value for key, value in initial_payload.items() if key != "params"}
    payload.update(
        {
            "params": unfreeze(params),
            "training_method": training_method,
            "training_initial_checkpoint_sha256": initial_checkpoint_sha256,
            "training_source_sha256": dict(source_sha256),
            "training_dataset_sha256": dict(dataset_sha256),
            "training_rollout_report_sha256": dict(rollout_report_sha256),
            "reward_contract": {"schema": REWARD_SCHEMA, **asdict(reward_config)},
            "hyperparameters": asdict(ppo_config),
            "training_seed": int(training_seed),
            "iteration": int(iteration),
            "strategy_parent": None,
            "parent_checkpoint_sha256": None,
            "PPO": True,
        }
    )
    validate_checkpoint_metadata(payload)
    return payload


def _source_paths() -> dict[str, Path]:
    root = Path(__file__).resolve().parent
    return {
        "headwise_trainer": Path(__file__).resolve(),
        "base_validation_trainer": root / "train_event_program_ppo.py",
        "event_ppo_math": root / "event_ppo_math.py",
        "manager_model": root / "model_event_program_ppo.py",
        "feature_contract": root / "event_program_features.py",
    }


def train_ppo(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    bindings = pair_bindings(args.dataset, args.rollout_report)
    initial_path = Path(args.initial_checkpoint).expanduser().resolve()
    if not initial_path.is_file():
        raise ValueError(f"initial checkpoint does not exist: {initial_path}")
    initial_sha = file_sha256(initial_path)
    initial_payload = serialization.msgpack_restore(initial_path.read_bytes())
    validate_checkpoint_metadata(initial_payload)
    if int(initial_payload.get("input_dim", -1)) != MANAGER_FEATURE_DIM:
        raise ValueError("initial checkpoint input_dim is not 427")
    if initial_payload.get("feature_schema") != FEATURE_SCHEMA:
        raise ValueError("initial checkpoint feature schema mismatch")
    if "params" not in initial_payload:
        raise ValueError("initial checkpoint has no params")

    output_path = Path(args.output).expanduser().resolve()
    report_path = Path(args.report).expanduser().resolve()
    immutable = {initial_path, *(path for pair in bindings.values() for path in pair)}
    if output_path in immutable or report_path in immutable or output_path == report_path:
        raise ValueError("output/report must be distinct from every immutable input")

    reward_config = RewardConfig(
        outcome_win=float(args.outcome_win),
        outcome_draw=float(args.outcome_draw),
        outcome_loss=float(args.outcome_loss),
        relative_share_coefficient=float(args.relative_share_coefficient),
        own_economy_coefficient=float(args.own_economy_coefficient),
        catastrophe_penalty=float(args.catastrophe_penalty),
        potential_coefficient=float(args.potential_coefficient),
    )
    ppo_config = PPOConfig(
        gamma_day=float(args.gamma_day),
        lambda_day=float(args.lambda_day),
        constraint_lambda=float(args.constraint_lambda),
        clip_epsilon=float(args.clip_epsilon),
        entropy_coefficient=float(args.entropy_coefficient),
        target_exact_kl=float(args.target_exact_kl),
        actor_learning_rate=float(args.actor_learning_rate),
        critic_learning_rate=float(args.critic_learning_rate),
        value_coefficient=float(args.value_coefficient),
        constraint_value_coefficient=float(args.constraint_value_coefficient),
        gradient_clip_norm=float(args.gradient_clip_norm),
        epochs=int(args.epochs),
        minibatch_size=int(args.minibatch_size),
    )
    if ppo_config.epochs <= 0 or ppo_config.minibatch_size <= 0:
        raise ValueError("epochs and minibatch_size must be positive")
    if not 0 < ppo_config.clip_epsilon < 1:
        raise ValueError("clip_epsilon must be between zero and one")
    if any(
        value <= 0
        for value in (
            ppo_config.gamma_day,
            ppo_config.lambda_day,
            ppo_config.target_exact_kl,
            ppo_config.actor_learning_rate,
            ppo_config.critic_learning_rate,
            ppo_config.gradient_clip_norm,
        )
    ):
        raise ValueError("discount, KL, learning rates and grad clip must be positive")

    actor_heads = tuple(args.actor_head or HEAD_NAMES)
    if len(set(actor_heads)) != len(actor_heads):
        raise ValueError("--actor-head values must be unique")
    unknown_actor_heads = set(actor_heads).difference(HEAD_NAMES)
    if unknown_actor_heads:
        raise ValueError(f"unknown --actor-head values: {sorted(unknown_actor_heads)}")
    min_epochs = int(args.min_epochs)
    min_production_kl = float(args.min_production_exact_kl)
    if not 1 <= min_epochs <= ppo_config.epochs:
        raise ValueError("min_epochs must be between one and epochs")
    if not 0.0 <= min_production_kl < ppo_config.target_exact_kl:
        raise ValueError("min production KL must be nonnegative and below target KL")
    adaptive_mode = min_production_kl > 0.0
    training_method = ADAPTIVE_TRAINING_METHOD if adaptive_mode else TRAINING_METHOD

    source_paths = _source_paths()
    source_before = {name: file_sha256(path) for name, path in source_paths.items()}
    binding_data: dict[str, dict[str, np.ndarray]] = {}
    prepared: dict[str, dict[str, np.ndarray]] = {}
    validation: dict[str, Any] = {}
    reward_audit: dict[str, Any] = {}
    dataset_shas: dict[str, str] = {}
    report_shas: dict[str, str] = {}
    binding_summaries: dict[str, Any] = {}
    for key, (dataset_path, rollout_report_path) in bindings.items():
        with rollout_report_path.open("r", encoding="utf-8") as source:
            rollout_report = json.load(source)
        report_contract = _validate_report_contract(
            rollout_report,
            report_path=rollout_report_path,
            dataset_path=dataset_path,
            initial_checkpoint_sha256=initial_sha,
        )
        data = load_npz(dataset_path)
        npz_contract = validate_npz_contract(data, report=rollout_report)
        if report_contract["episodes"] != npz_contract["episodes"]:
            raise ValueError("rollout report and NPZ episode counts differ")
        old_head_logp = recompute_old_head_logp(data)
        binding_data[key] = data
        prepared[key], reward_rows = prepare_binding_training_data(
            key, data, reward_config=reward_config, ppo_config=ppo_config
        )
        validation[key] = {
            "report": report_contract,
            "npz": npz_contract,
            "old_head_logp": {
                name: {
                    "samples": int(len(values)),
                    "finite": bool(np.all(np.isfinite(values))),
                }
                for name, values in old_head_logp.items()
            },
        }
        reward_audit[key] = {
            "episodes": len(reward_rows),
            "mean_terminal_reward": float(
                np.mean([row["terminal_reward"] for row in reward_rows])
            ),
            "mean_potential_shaping_sum": float(
                np.mean([row["potential_shaping_sum"] for row in reward_rows])
            ),
            "mean_training_reward_sum": float(
                np.mean([row["training_reward_sum"] for row in reward_rows])
            ),
        }
        dataset_shas[key] = file_sha256(dataset_path)
        report_shas[key] = file_sha256(rollout_report_path)
        binding_summaries[key] = _economy_summary(data)

    training_data, normalization = concatenate_bindings(
        binding_data, prepared, constraint_lambda=ppo_config.constraint_lambda
    )
    initial_params = unfreeze(initial_payload["params"])
    state = (
        create_scoped_train_state(initial_params, ppo_config, actor_heads=actor_heads)
        if adaptive_mode
        else create_train_state(initial_params, ppo_config)
    )
    pre_metrics = evaluate_state(
        state, training_data, config=ppo_config, actor_heads=actor_heads
    )
    for name in HEAD_NAMES:
        active_count = pre_metrics["heads"][name]["active_samples"]
        if active_count > 0 and pre_metrics["heads"][name]["exact_kl"] > 1.0e-6:
            raise ValueError(
                f"rollout is not on-policy for active head {name}: "
                f"KL={pre_metrics['heads'][name]['exact_kl']}"
            )

    rng = np.random.default_rng(int(args.seed))
    history: list[dict[str, Any]] = []
    stop_reason = "completed_configured_epochs"
    rollback: dict[str, Any] | None = None
    global_minibatch = 0
    stop_training = False
    for epoch in range(1, ppo_config.epochs + 1):
        order = np.arange(len(training_data["features"]), dtype=np.int64)
        rng.shuffle(order)
        minibatch_losses: list[float] = []
        for start in range(0, len(order), ppo_config.minibatch_size):
            batch = make_batch(training_data, order[start:start + ppo_config.minibatch_size])
            last_safe_state = state
            candidate_state, metrics = train_minibatch(
                state, batch, config=ppo_config, actor_heads=actor_heads
            )
            global_minibatch += 1
            minibatch_losses.append(float(jax.device_get(metrics["loss"])))
            check_now = bool(
                adaptive_mode
                and int(args.kl_check_interval_minibatches) > 0
                and global_minibatch % int(args.kl_check_interval_minibatches) == 0
            )
            if check_now:
                candidate_metrics = evaluate_state(
                    candidate_state,
                    training_data,
                    config=ppo_config,
                    actor_heads=actor_heads,
                )
                all_kls = [
                    candidate_metrics["heads"][name]["exact_kl"]
                    for name in HEAD_NAMES
                    if candidate_metrics["heads"][name]["active_samples"] > 0
                ]
                finite = bool(np.all(np.isfinite(all_kls)))
                exceeded = bool(
                    (not finite)
                    or candidate_metrics["max_active_head_exact_kl"]
                    > ppo_config.target_exact_kl
                )
                if exceeded:
                    state = last_safe_state
                    rollback = {
                        "epoch": epoch,
                        "global_minibatch": global_minibatch,
                        "reason": "nonfinite_kl" if not finite else "max_kl_exceeded",
                        "attempted_max_active_head_exact_kl": candidate_metrics[
                            "max_active_head_exact_kl"
                        ],
                        "attempted_production_head_exact_kl": candidate_metrics[
                            "heads"
                        ]["production_line"]["exact_kl"],
                        "full_train_state_restored": True,
                    }
                    stop_reason = "trust_region_overshoot_rolled_back"
                    stop_training = True
                    break
                state = candidate_state
                if (
                    epoch >= min_epochs
                    and candidate_metrics["heads"]["production_line"]["exact_kl"]
                    >= min_production_kl
                ):
                    stop_reason = "minimum_production_head_exact_kl_reached"
                    stop_training = True
                    break
            else:
                state = candidate_state
        epoch_metrics = evaluate_state(
            state, training_data, config=ppo_config, actor_heads=actor_heads
        )
        exceeded = bool(
            epoch_metrics["max_active_head_exact_kl"] > ppo_config.target_exact_kl
        )
        history.append(
            {
                "epoch": epoch,
                "minibatches": len(minibatch_losses),
                "mean_minibatch_loss": float(np.mean(minibatch_losses)),
                "full_dataset": epoch_metrics,
                "accepted": not exceeded,
                "global_minibatches_completed": global_minibatch,
            }
        )
        if stop_training:
            break
        if exceeded:
            if args.rollback_on_kl_exceed:
                state = last_safe_state
                stop_reason = "target_max_active_head_exact_kl_exceeded_rolled_back"
            else:
                stop_reason = "target_max_active_head_exact_kl_exceeded"
            break
        if (
            adaptive_mode
            and epoch >= min_epochs
            and epoch_metrics["heads"]["production_line"]["exact_kl"]
            >= min_production_kl
        ):
            stop_reason = "minimum_production_head_exact_kl_reached"
            break

    post_metrics = evaluate_state(
        state, training_data, config=ppo_config, actor_heads=actor_heads
    )
    adaptive_kl_qualified = bool(
        (not adaptive_mode)
        or (
            post_metrics["heads"]["production_line"]["exact_kl"]
            >= min_production_kl
            and post_metrics["max_active_head_exact_kl"]
            <= ppo_config.target_exact_kl
        )
    )
    changes = parameter_change_report(initial_params, state.params)
    if changes["actor_changed_leaves"] == 0 or changes["critic_changed_leaves"] == 0:
        raise RuntimeError("head-wise PPO did not change actor/trunk and critic parameters")
    root_changes = parameter_root_changes(initial_params, state.params)
    frozen_roots = sorted(
        set(initial_params).difference(
            {f"{name}_head" for name in actor_heads}
            | {"value_head", "constraint_value_head"}
        )
    )
    if adaptive_mode and any(root_changes[root] != 0.0 for root in frozen_roots):
        raise RuntimeError("scoped PPO changed a frozen parameter root")
    if adaptive_mode and root_changes.get("production_line_head", 0.0) <= 0.0:
        raise RuntimeError("scoped PPO did not change production_line_head")
    behavior_diagnostics = production_behavior_diagnostics(
        state, training_data, sampling_seed=int(args.seed) + 3001
    )

    source_after = {name: file_sha256(path) for name, path in source_paths.items()}
    if source_after != source_before:
        raise RuntimeError("trainer source changed during execution")
    checkpoint_payload = build_checkpoint_payload(
        initial_payload,
        state.params,
        initial_checkpoint_sha256=initial_sha,
        source_sha256=source_before,
        dataset_sha256=dataset_shas,
        rollout_report_sha256=report_shas,
        reward_config=reward_config,
        ppo_config=ppo_config,
        iteration=int(args.iteration),
        training_seed=int(args.seed),
        training_method=training_method,
    )
    checkpoint_sha = atomic_checkpoint(output_path, checkpoint_payload)
    restored = serialization.msgpack_restore(output_path.read_bytes())
    validate_checkpoint_metadata(restored)
    if file_sha256(initial_path) != initial_sha:
        raise RuntimeError("initial checkpoint changed during training")

    head_report = {
        name: {
            "active_samples": int(pre_metrics["heads"][name]["active_samples"]),
            "active_fraction": pre_metrics["heads"][name]["active_fraction"],
            "pre": {
                key: pre_metrics["heads"][name][key]
                for key in ("exact_kl", "entropy", "policy_loss")
            },
            "post": {
                key: post_metrics["heads"][name][key]
                for key in ("exact_kl", "entropy", "policy_loss")
            },
        }
        for name in HEAD_NAMES
    }
    report = {
        "schema": TRAINING_SCHEMA,
        "status": "COMPLETE" if adaptive_kl_qualified else "INCOMPLETE_KL_CONTRACT",
        "PPO": True,
        "training_method": training_method,
        "iteration": int(args.iteration),
        "lineage": {"strategy_parent": None},
        "binding_contract": {
            "syntax": "layer/member=PATH",
            "normalization_group": "slash prefix",
            "allowed_groups": list(NORMALIZATION_GROUPS),
        },
        "initial_checkpoint": {
            "path": str(initial_path),
            "sha256_before": initial_sha,
            "sha256_after": file_sha256(initial_path),
            "unchanged": True,
        },
        "inputs": {
            key: {
                "normalization_group": normalization_group(key),
                "dataset_path": str(bindings[key][0]),
                "dataset_sha256": dataset_shas[key],
                "rollout_report_path": str(bindings[key][1]),
                "rollout_report_sha256": report_shas[key],
            }
            for key in bindings
        },
        "source_sha256_before": source_before,
        "source_sha256_after": source_after,
        "source_unchanged": True,
        "validation": validation,
        "reward_contract": {
            "schema": REWARD_SCHEMA,
            "terminal": "outcome + relative_share + own_economy - catastrophe",
            "relative_share": "2*own/max(own+opponent,1)-1",
            "deprecated_tanh_margin_used": False,
            "potential": "0.1*(gamma^duration*Phi(next)-Phi(current)); terminal Phi=0",
            "phi": "(public own money-3000)/10000",
            **asdict(reward_config),
        },
        "hyperparameters": asdict(ppo_config),
        "advantage_contract": {
            "episode_smdp_gae": True,
            "normalization_groups": list(NORMALIZATION_GROUPS),
            "normalization": normalization,
            "constraint_actor_requires_real_catastrophe_in_group": True,
        },
        "actor_contract": {
            "ratio": "per-head; joint ratio forbidden",
            "active_decision": "legal action count > 1",
            "inactive_row_actor_weight": 0,
            "active_head_aggregation": "equal mean over heads with active samples",
            "shared_trunk_receives_aggregate_gradient": True,
            "optimized_heads": list(actor_heads),
        },
        "adaptive_kl_contract": {
            "enabled": adaptive_mode,
            "min_epochs": min_epochs,
            "max_epochs": ppo_config.epochs,
            "min_production_head_exact_kl": min_production_kl,
            "target_max_active_head_exact_kl": ppo_config.target_exact_kl,
            "rollback_on_kl_exceed": bool(args.rollback_on_kl_exceed),
            "check_interval_minibatches": int(args.kl_check_interval_minibatches),
            "qualified": adaptive_kl_qualified,
            "rollback": rollback,
        },
        "head_diagnostics": head_report,
        "economy_by_binding": binding_summaries,
        "economy_by_group": _merge_group_summary(binding_data),
        "reward_audit": reward_audit,
        "metrics": {"pre": pre_metrics, "post": post_metrics, "history": history},
        "training_stop_reason": stop_reason,
        "epochs_completed": len(history),
        "parameter_changes": changes,
        "parameter_root_max_abs_changes": root_changes,
        "production_behavior_diagnostics": behavior_diagnostics,
        "checkpoint": {"path": str(output_path), "sha256": checkpoint_sha},
        "training_seed": int(args.seed),
        "elapsed_seconds": time.time() - started,
    }
    atomic_json(report_path, report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--initial-checkpoint", type=Path, required=True)
    parser.add_argument(
        "--dataset", action="append", required=True, metavar="LAYER/MEMBER=NPZ"
    )
    parser.add_argument(
        "--rollout-report",
        action="append",
        required=True,
        metavar="LAYER/MEMBER=JSON",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--iteration", type=int, default=2)
    parser.add_argument("--seed", type=int, default=114940)
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--min-epochs", type=int, default=1)
    parser.add_argument("--minibatch-size", type=int, default=256)
    parser.add_argument("--gamma-day", type=float, default=0.99)
    parser.add_argument("--lambda-day", type=float, default=0.95)
    parser.add_argument("--constraint-lambda", type=float, default=0.5)
    parser.add_argument("--clip-epsilon", type=float, default=0.10)
    parser.add_argument("--entropy-coefficient", type=float, default=0.01)
    parser.add_argument("--target-exact-kl", type=float, default=0.01)
    parser.add_argument("--min-production-exact-kl", type=float, default=0.0)
    parser.add_argument(
        "--actor-head", action="append", choices=HEAD_NAMES,
        help="Optimize only the selected actor head; repeat for multiple heads.",
    )
    parser.add_argument("--rollback-on-kl-exceed", action="store_true")
    parser.add_argument("--kl-check-interval-minibatches", type=int, default=0)
    parser.add_argument("--actor-learning-rate", type=float, default=1.0e-5)
    parser.add_argument("--critic-learning-rate", type=float, default=3.0e-5)
    parser.add_argument("--value-coefficient", type=float, default=0.5)
    parser.add_argument("--constraint-value-coefficient", type=float, default=0.25)
    parser.add_argument("--gradient-clip-norm", type=float, default=0.5)
    parser.add_argument("--outcome-win", type=float, default=1.0)
    parser.add_argument("--outcome-draw", type=float, default=0.0)
    parser.add_argument("--outcome-loss", type=float, default=-1.0)
    parser.add_argument("--relative-share-coefficient", type=float, default=1.0)
    parser.add_argument("--own-economy-coefficient", type=float, default=0.1)
    parser.add_argument("--catastrophe-penalty", type=float, default=1.0)
    parser.add_argument("--potential-coefficient", type=float, default=0.1)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        report = train_ppo(args)
    except (TypeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(
        json.dumps(
            {
                "status": report["status"],
                "checkpoint": report["checkpoint"],
                "training_stop_reason": report["training_stop_reason"],
                "head_diagnostics": report["head_diagnostics"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()


__all__ = [
    "NORMALIZATION_GROUPS",
    "ADAPTIVE_TRAINING_METHOD",
    "PPOConfig",
    "REWARD_SCHEMA",
    "RewardConfig",
    "TRAINING_METHOD",
    "TRAINING_SCHEMA",
    "build_checkpoint_payload",
    "create_scoped_train_state",
    "compute_episode_rewards",
    "concatenate_bindings",
    "evaluate_state",
    "headwise_actor_objective",
    "make_batch",
    "normalization_group",
    "pair_bindings",
    "potential_shaping",
    "parameter_root_changes",
    "production_behavior_diagnostics",
    "ppo_loss",
    "prepare_binding_training_data",
    "recompute_old_head_logp",
    "standardize_by_group",
    "terminal_outcome_reward",
    "train_minibatch",
    "train_ppo",
]
