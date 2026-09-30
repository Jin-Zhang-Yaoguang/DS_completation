"""Train the independent V114 V9 Event-Program Manager with on-policy PPO.

The trainer accepts only collector-produced, train-split SMDP rollouts.  The
behavior policy is the immutable old-logit tree stored in each NPZ; current
policy logits are never substituted for that evidence.  Reward shaping uses
only public money at the two ends of an interval and audited terminal results.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import tempfile
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
    from .collect_event_program_ppo_rollouts import (
        EXPECTED_ACTION_STEPS,
        EXPECTED_DAY_TRANSITIONS,
        NPZ_SCHEMA,
    )
    from .event_ppo_math import (
        HEAD_NAMES,
        HEAD_SIZES,
        duration_aware_smdp_gae,
        factorized_exact_kl,
        factorized_log_probability_entropy,
        validate_action_masks,
    )
    from .event_program_features import FEATURE_SCHEMA, MANAGER_FEATURE_DIM
    from .model_event_program_ppo import (
        EventProgramPPOManager,
        validate_checkpoint_metadata,
    )
except ImportError:  # Direct-file CLI execution.
    from collect_event_program_ppo_rollouts import (  # type: ignore
        EXPECTED_ACTION_STEPS,
        EXPECTED_DAY_TRANSITIONS,
        NPZ_SCHEMA,
    )
    from event_ppo_math import (  # type: ignore
        HEAD_NAMES,
        HEAD_SIZES,
        duration_aware_smdp_gae,
        factorized_exact_kl,
        factorized_log_probability_entropy,
        validate_action_masks,
    )
    from event_program_features import FEATURE_SCHEMA, MANAGER_FEATURE_DIM  # type: ignore
    from model_event_program_ppo import (  # type: ignore
        EventProgramPPOManager,
        validate_checkpoint_metadata,
    )


TRAINING_SCHEMA = "kaggriculture-v114-event-program-on-policy-ppo-training-v1"
REWARD_SCHEMA = "v114-v9-public-terminal-plus-potential-v1"
CRITIC_PARAMETER_ROOTS = frozenset(("value_head", "constraint_value_head"))


@dataclass(frozen=True)
class RewardConfig:
    outcome_win: float = 1.0
    outcome_draw: float = 0.0
    outcome_loss: float = -1.0
    margin_coefficient: float = 0.25
    own_reward_coefficient: float = 0.25
    catastrophe_penalty: float = 1.0
    potential_coefficient: float = 0.1
    potential_money_center: float = 3000.0
    potential_money_scale: float = 10000.0
    margin_scale: float = 10000.0
    own_reward_center: float = 3000.0
    own_reward_scale: float = 10000.0


@dataclass(frozen=True)
class PPOConfig:
    gamma_day: float = 0.99
    lambda_day: float = 0.95
    constraint_lambda: float = 0.5
    clip_epsilon: float = 0.10
    entropy_coefficient: float = 0.01
    target_exact_kl: float = 0.01
    actor_learning_rate: float = 1.0e-5
    critic_learning_rate: float = 3.0e-5
    value_coefficient: float = 0.5
    constraint_value_coefficient: float = 0.25
    gradient_clip_norm: float = 0.5
    epochs: int = 4
    minibatch_size: int = 256


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.expanduser().resolve().open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as sink:
        json.dump(payload, sink, ensure_ascii=False, indent=2, sort_keys=True)
        sink.write("\n")
        sink.flush()
        os.fsync(sink.fileno())
        temporary = Path(sink.name)
    os.replace(temporary, path)


def atomic_checkpoint(path: Path, payload: Mapping[str, Any]) -> str:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = serialization.msgpack_serialize(dict(payload))
    with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False) as sink:
        sink.write(encoded)
        sink.flush()
        os.fsync(sink.fileno())
        temporary = Path(sink.name)
    os.replace(temporary, path)
    return hashlib.sha256(encoded).hexdigest()


def load_npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path.expanduser().resolve(), allow_pickle=False) as archive:
        return {name: archive[name] for name in archive.files}


def _scalar(value: np.ndarray) -> Any:
    array = np.asarray(value)
    if array.shape != ():
        raise ValueError("NPZ scalar metadata must be zero-dimensional")
    return array.item()


def parse_layer_bindings(values: Sequence[str], *, flag: str) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for raw in values:
        if "=" not in raw:
            raise ValueError(f"{flag} requires LAYER=PATH, got {raw!r}")
        layer, raw_path = raw.split("=", 1)
        layer = layer.strip()
        if not layer or not raw_path.strip():
            raise ValueError(f"{flag} requires non-empty LAYER and PATH")
        if layer in result:
            raise ValueError(f"duplicate {flag} layer: {layer}")
        path = Path(raw_path).expanduser().resolve()
        if not path.is_file():
            raise ValueError(f"{flag} path does not exist: {path}")
        result[layer] = path
    if not result:
        raise ValueError(f"at least one {flag} is required")
    return result


def pair_layer_bindings(
    dataset_values: Sequence[str], report_values: Sequence[str]
) -> dict[str, tuple[Path, Path]]:
    datasets = parse_layer_bindings(dataset_values, flag="--dataset")
    reports = parse_layer_bindings(report_values, flag="--rollout-report")
    if set(datasets) != set(reports):
        raise ValueError(
            "--dataset and --rollout-report layers must match exactly: "
            f"datasets={sorted(datasets)}, reports={sorted(reports)}"
        )
    return {layer: (datasets[layer], reports[layer]) for layer in datasets}


def normalization_layer(binding_key: str) -> str:
    """Map a unique ``layer/member`` binding to its advantage group."""

    group = str(binding_key).split("/", 1)[0].strip()
    if not group:
        raise ValueError("binding layer prefix must be non-empty")
    return group


def _required_npz_keys() -> set[str]:
    keys = {
        "schema", "feature_dim", "episode_offsets", "episode_ids",
        "episode_seed", "episode_seat", "episode_opponent_id",
        "episode_status", "episode_error", "transition_episode_index",
        "features", "old_joint_logp", "value", "constraint_value",
        "start_step", "start_day", "end_step", "duration_turns",
        "next_value", "next_constraint_value", "terminal",
        "own_money_start", "own_money_end", "reward_delta_money",
        "training_reward_raw", "training_reward_source", "candidate_reward",
        "opponent_reward", "margin", "score", "catastrophe",
    }
    for name in HEAD_NAMES:
        keys.update((f"mask_{name}", f"action_{name}", f"old_logits_{name}"))
    return keys


def recompute_old_joint_logp(data: Mapping[str, np.ndarray]) -> np.ndarray:
    masks = {
        name: jnp.asarray(data[f"mask_{name}"], dtype=jnp.bool_)
        for name in HEAD_NAMES
    }
    actions = {
        name: jnp.asarray(data[f"action_{name}"], dtype=jnp.int32)
        for name in HEAD_NAMES
    }
    logits = {
        name: jnp.asarray(data[f"old_logits_{name}"], dtype=jnp.float32)
        for name in HEAD_NAMES
    }
    joint_logp, _, _ = factorized_log_probability_entropy(logits, actions, masks)
    return np.asarray(jax.device_get(joint_logp), dtype=np.float32)


def validate_old_policy_evidence(
    data: Mapping[str, np.ndarray], *, tolerance: float = 2.0e-5
) -> dict[str, float]:
    rows = int(np.asarray(data["features"]).shape[0])
    masks = {name: np.asarray(data[f"mask_{name}"]) for name in HEAD_NAMES}
    validate_action_masks(masks, batch_size=rows)
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
            raise ValueError(f"action_{name} contains an action forbidden by shared mask")
    stored = np.asarray(data["old_joint_logp"], dtype=np.float32)
    if stored.shape != (rows,) or not np.all(np.isfinite(stored)):
        raise ValueError("old_joint_logp is incomplete or non-finite")
    recomputed = recompute_old_joint_logp(data)
    max_error = float(np.max(np.abs(stored - recomputed))) if rows else 0.0
    if not np.allclose(stored, recomputed, rtol=1.0e-5, atol=tolerance):
        raise ValueError(
            f"stored old_joint_logp does not match old logits/actions/masks; max={max_error}"
        )
    return {"max_old_joint_logp_recompute_error": max_error}


def _validate_report_contract(
    report: Mapping[str, Any],
    *,
    report_path: Path,
    dataset_path: Path,
    initial_checkpoint_sha256: str,
) -> dict[str, Any]:
    if report.get("status") != "VALID":
        raise ValueError(f"rollout report is not VALID: {report_path}")
    if report.get("split") != "train":
        raise ValueError("PPO trainer accepts only train-split rollout reports")
    checkpoint = report.get("checkpoint")
    if not isinstance(checkpoint, Mapping):
        raise ValueError("rollout report checkpoint contract is missing")
    before = checkpoint.get("sha256_before")
    after = checkpoint.get("sha256_after")
    if (
        before != initial_checkpoint_sha256
        or after != initial_checkpoint_sha256
        or checkpoint.get("unchanged") is not True
    ):
        raise ValueError("rollout checkpoint pre/post SHA is not the initial checkpoint")
    artifact = report.get("artifact")
    if not isinstance(artifact, Mapping):
        raise ValueError("rollout report artifact contract is missing")
    actual_npz_sha = file_sha256(dataset_path)
    if artifact.get("sha256") != actual_npz_sha:
        raise ValueError("NPZ SHA does not equal rollout report artifact SHA")
    episodes = report.get("episodes")
    if not isinstance(episodes, list) or not episodes:
        raise ValueError("rollout report must expose all episodes")
    for episode in episodes:
        valid = bool(
            isinstance(episode, Mapping)
            and episode.get("error") is None
            and episode.get("statuses") == ["DONE", "DONE"]
            and int(episode.get("action_steps", -1)) == EXPECTED_ACTION_STEPS
            and int(episode.get("transition_count", -1)) == EXPECTED_DAY_TRANSITIONS
            and int(episode.get("duration_turns_sum", -1)) == EXPECTED_ACTION_STEPS
            and int(episode.get("contract_violations", -1)) == 0
            and int(episode.get("terminal_procurement", -1)) == 0
        )
        if not valid:
            raise ValueError(
                f"rollout report contains invalid episode: {episode.get('episode_id') if isinstance(episode, Mapping) else '?'}"
            )
    return {
        "path": str(report_path),
        "sha256": file_sha256(report_path),
        "episodes": len(episodes),
        "npz_sha256": actual_npz_sha,
    }


def validate_npz_contract(
    data: Mapping[str, np.ndarray], *, report: Mapping[str, Any]
) -> dict[str, Any]:
    missing = _required_npz_keys() - set(data)
    if missing:
        raise ValueError(f"rollout NPZ missing keys: {sorted(missing)}")
    if str(_scalar(data["schema"])) != NPZ_SCHEMA:
        raise ValueError("unsupported rollout NPZ schema")
    if int(_scalar(data["feature_dim"])) != MANAGER_FEATURE_DIM:
        raise ValueError("rollout feature_dim is not 427")
    features = np.asarray(data["features"])
    if features.ndim != 2 or features.shape[1] != MANAGER_FEATURE_DIM:
        raise ValueError(f"features must have shape [N, {MANAGER_FEATURE_DIM}]")
    if not np.all(np.isfinite(features)):
        raise ValueError("features contain non-finite values")
    rows = int(features.shape[0])
    offsets = np.asarray(data["episode_offsets"], dtype=np.int64)
    episode_ids = np.asarray(data["episode_ids"]).astype(str)
    episodes = len(episode_ids)
    if offsets.shape != (episodes + 1,) or offsets[0] != 0 or offsets[-1] != rows:
        raise ValueError("episode_offsets do not cover the transition table")
    if np.any(np.diff(offsets) != EXPECTED_DAY_TRANSITIONS):
        raise ValueError("every episode must contain exactly 28 transitions")
    if len(set(episode_ids.tolist())) != episodes:
        raise ValueError("episode_ids must be unique")
    for key in ("episode_seed", "episode_seat", "episode_opponent_id", "episode_status", "episode_error"):
        if np.asarray(data[key]).shape != (episodes,):
            raise ValueError(f"{key} must align with episode rows")
    if np.any(np.asarray(data["episode_status"]).astype(str) != "DONE"):
        raise ValueError("all NPZ episodes must be DONE")
    if np.any(np.asarray(data["episode_error"]).astype(str) != ""):
        raise ValueError("all NPZ episodes must be error-free")
    report_episodes = report.get("episodes", [])
    report_ids = [str(row.get("episode_id")) for row in report_episodes]
    if report_ids != episode_ids.tolist():
        raise ValueError("rollout report episode order/identity differs from NPZ")

    transition_episode_index = np.asarray(data["transition_episode_index"], dtype=np.int64)
    if transition_episode_index.shape != (rows,):
        raise ValueError("transition_episode_index must align with transitions")
    expected_episode_index = np.repeat(np.arange(episodes), EXPECTED_DAY_TRANSITIONS)
    if not np.array_equal(transition_episode_index, expected_episode_index):
        raise ValueError("transition_episode_index disagrees with episode_offsets")

    vector_keys = (
        "old_joint_logp", "value", "constraint_value", "start_step", "start_day",
        "end_step", "duration_turns", "next_value", "next_constraint_value",
        "terminal", "own_money_start", "own_money_end", "reward_delta_money",
        "training_reward_raw", "training_reward_source", "candidate_reward",
        "opponent_reward", "margin", "score", "catastrophe",
    )
    for key in vector_keys:
        if np.asarray(data[key]).shape != (rows,):
            raise ValueError(f"{key} must align with transition rows")
    finite_keys = (
        "value", "constraint_value", "next_value", "next_constraint_value",
        "own_money_start", "own_money_end", "reward_delta_money",
        "training_reward_raw", "candidate_reward", "opponent_reward", "margin", "score",
    )
    for key in finite_keys:
        if not np.all(np.isfinite(np.asarray(data[key], dtype=np.float64))):
            raise ValueError(f"{key} contains non-finite values")
    if np.any(np.asarray(data["training_reward_source"]).astype(str) != "public_own_money_delta"):
        raise ValueError("training_reward_source must be public_own_money_delta")
    public_delta = np.asarray(data["own_money_end"], dtype=np.float64) - np.asarray(
        data["own_money_start"], dtype=np.float64
    )
    if not np.allclose(public_delta, np.asarray(data["reward_delta_money"]), atol=1.0e-4):
        raise ValueError("reward_delta_money is not the audited public money delta")
    if not np.allclose(public_delta, np.asarray(data["training_reward_raw"]), atol=1.0e-4):
        raise ValueError("training_reward_raw is not the audited public money delta")
    if not np.allclose(
        np.asarray(data["margin"], dtype=np.float64),
        np.asarray(data["candidate_reward"], dtype=np.float64)
        - np.asarray(data["opponent_reward"], dtype=np.float64),
        atol=1.0e-4,
    ):
        raise ValueError("margin disagrees with public terminal rewards")

    starts = np.asarray(data["start_step"], dtype=np.int64)
    ends = np.asarray(data["end_step"], dtype=np.int64)
    durations = np.asarray(data["duration_turns"], dtype=np.int64)
    terminals = np.asarray(data["terminal"], dtype=np.bool_)
    if np.any(durations <= 0) or not np.array_equal(ends - starts, durations):
        raise ValueError("transition durations are invalid")
    for episode_index in range(episodes):
        begin, end = int(offsets[episode_index]), int(offsets[episode_index + 1])
        if int(durations[begin:end].sum()) != EXPECTED_ACTION_STEPS:
            raise ValueError("episode duration sum must equal 719")
        if int(terminals[begin:end].sum()) != 1 or not bool(terminals[end - 1]):
            raise ValueError("each episode must terminate only on its final transition")
        if not np.allclose(
            np.asarray(data["own_money_end"])[begin:end - 1],
            np.asarray(data["own_money_start"])[begin + 1:end],
            atol=1.0e-4,
        ):
            raise ValueError("public money path is discontinuous inside an episode")
        for key in ("candidate_reward", "opponent_reward", "margin", "score", "catastrophe"):
            values = np.asarray(data[key])[begin:end]
            if not np.all(values == values[0]):
                raise ValueError(f"episode terminal field {key} changes inside episode")
    evidence = validate_old_policy_evidence(data)
    return {"episodes": episodes, "transitions": rows, **evidence}


def terminal_outcome_reward(
    *, score: float, margin: float, own_reward: float, catastrophe: bool,
    config: RewardConfig,
) -> float:
    if score == 1.0:
        outcome = config.outcome_win
    elif score == 0.5:
        outcome = config.outcome_draw
    elif score == 0.0:
        outcome = config.outcome_loss
    else:
        raise ValueError(f"score must be 0, 0.5 or 1, got {score}")
    return float(
        outcome
        + config.margin_coefficient * np.tanh(float(margin) / config.margin_scale)
        + config.own_reward_coefficient
        * np.tanh((float(own_reward) - config.own_reward_center) / config.own_reward_scale)
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
        np.asarray(own_money_start, dtype=np.float64) - config.potential_money_center
    ) / config.potential_money_scale
    next_phi = (
        np.asarray(own_money_end, dtype=np.float64) - config.potential_money_center
    ) / config.potential_money_scale
    next_phi = np.where(np.asarray(terminals, dtype=np.bool_), 0.0, next_phi)
    discounts = np.power(float(gamma_day), np.asarray(durations_turns, dtype=np.float64) / 24.0)
    return config.potential_coefficient * (discounts * next_phi - start_phi)


def compute_episode_rewards(
    data: Mapping[str, np.ndarray], begin: int, end: int, *,
    reward_config: RewardConfig, gamma_day: float,
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
        margin=float(np.asarray(data["margin"])[begin]),
        own_reward=float(np.asarray(data["candidate_reward"])[begin]),
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


def layer_standardize(values: np.ndarray, layers: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    values = np.asarray(values, dtype=np.float32)
    layers = np.asarray(layers).astype(str)
    if values.shape != layers.shape:
        raise ValueError("values and layers must share shape")
    result = np.empty_like(values)
    report: dict[str, Any] = {}
    for layer in dict.fromkeys(layers.tolist()):
        selected = layers == layer
        current = values[selected].astype(np.float64)
        mean = float(np.mean(current))
        std = float(np.std(current))
        result[selected] = 0.0 if std < 1.0e-8 else (current - mean) / std
        report[layer] = {
            "samples": int(selected.sum()),
            "raw_mean": mean,
            "raw_std": std,
            "normalized_mean": float(np.mean(result[selected])),
            "normalized_std": float(np.std(result[selected])),
        }
    return result, report


def prepare_layer_training_data(
    layer: str,
    data: Mapping[str, np.ndarray],
    *,
    reward_config: RewardConfig,
    ppo_config: PPOConfig,
) -> tuple[dict[str, np.ndarray], list[dict[str, float]]]:
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
            data, begin, end,
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
        "layer": np.full(rows, layer),
        "reward_advantage_raw": reward_advantages,
        "reward_return": reward_returns,
        "constraint_advantage_raw": constraint_advantages,
        "constraint_return": constraint_returns,
    }, reward_rows


def concatenate_layers(
    layers: Mapping[str, Mapping[str, np.ndarray]],
    prepared: Mapping[str, Mapping[str, np.ndarray]],
    *, constraint_lambda: float,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    ordered = list(layers)
    result: dict[str, np.ndarray] = {}
    data_keys = (
        "features", "old_joint_logp", "value", "constraint_value",
        *(f"mask_{name}" for name in HEAD_NAMES),
        *(f"action_{name}" for name in HEAD_NAMES),
        *(f"old_logits_{name}" for name in HEAD_NAMES),
    )
    for key in data_keys:
        result[key] = np.concatenate([np.asarray(layers[layer][key]) for layer in ordered])
    for key in ("layer", "reward_advantage_raw", "reward_return", "constraint_advantage_raw", "constraint_return"):
        result[key] = np.concatenate([np.asarray(prepared[layer][key]) for layer in ordered])
    result["constraint_event"] = np.concatenate(
        [np.asarray(layers[layer]["catastrophe"], dtype=np.bool_) for layer in ordered]
    )
    reward_normalized, reward_stats = layer_standardize(
        result["reward_advantage_raw"], result["layer"]
    )
    constraint_normalized, constraint_stats = layer_standardize(
        result["constraint_advantage_raw"], result["layer"]
    )
    # A constraint critic may have non-zero random residuals before it has seen
    # any violation.  Those residuals are valid critic targets, but they are
    # not evidence for changing the actor.  Disable the constrained-policy
    # term within a layer until at least one real catastrophe was observed.
    for layer in dict.fromkeys(result["layer"].astype(str).tolist()):
        selected = result["layer"].astype(str) == layer
        observed = int(np.sum(result["constraint_event"][selected]))
        constraint_stats[layer]["observed_constraint_events"] = observed
        constraint_stats[layer]["actor_constraint_enabled"] = observed > 0
        if observed == 0:
            constraint_normalized[selected] = 0.0
    result["reward_advantage"] = reward_normalized
    result["constraint_advantage"] = constraint_normalized
    result["actor_advantage"] = reward_normalized - float(constraint_lambda) * constraint_normalized
    return result, {"reward": reward_stats, "constraint": constraint_stats}


def parameter_labels(params: Mapping[str, Any]) -> Any:
    """Assign shared trunk and actor heads to actor LR; critic heads to critic LR."""

    return jax.tree_util.tree_map_with_path(
        lambda path, _: (
            "critic"
            if path and getattr(path[0], "key", None) in CRITIC_PARAMETER_ROOTS
            else "actor"
        ),
        params,
    )


def create_train_state(params: Any, config: PPOConfig) -> TrainState:
    model = EventProgramPPOManager()
    labels = parameter_labels(params)
    partitioned = optax.multi_transform(
        {
            "actor": optax.adam(float(config.actor_learning_rate)),
            "critic": optax.adam(float(config.critic_learning_rate)),
        },
        labels,
    )
    optimizer = optax.chain(
        optax.clip_by_global_norm(float(config.gradient_clip_norm)),
        partitioned,
    )
    return TrainState.create(apply_fn=model.apply, params=params, tx=optimizer)


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
        "old_joint_logp": jnp.asarray(np.asarray(data["old_joint_logp"])[selected], dtype=jnp.float32),
        "actor_advantage": jnp.asarray(np.asarray(data["actor_advantage"])[selected], dtype=jnp.float32),
        "reward_return": jnp.asarray(np.asarray(data["reward_return"])[selected], dtype=jnp.float32),
        "constraint_return": jnp.asarray(np.asarray(data["constraint_return"])[selected], dtype=jnp.float32),
    }


def ppo_loss(
    params: Any,
    apply_fn: Any,
    batch: Mapping[str, Any],
    *, config: PPOConfig,
) -> tuple[jnp.ndarray, dict[str, jnp.ndarray]]:
    """One-mask PPO objective; old logits remain immutable data evidence."""

    outputs = apply_fn({"params": params}, batch["features"])
    current_joint_logp, entropy, _ = factorized_log_probability_entropy(
        outputs["actor_logits"], batch["actions"], batch["shared_masks"]
    )
    exact_kl_rows = factorized_exact_kl(
        batch["old_logits"], outputs["actor_logits"], batch["shared_masks"]
    )
    log_ratio = current_joint_logp - jax.lax.stop_gradient(batch["old_joint_logp"])
    ratio = jnp.exp(log_ratio)
    advantage = jax.lax.stop_gradient(batch["actor_advantage"])
    unclipped = ratio * advantage
    clipped = jnp.clip(
        ratio, 1.0 - config.clip_epsilon, 1.0 + config.clip_epsilon
    ) * advantage
    policy_loss = -jnp.mean(jnp.minimum(unclipped, clipped))
    mean_entropy = jnp.mean(entropy)
    actor_loss = policy_loss - config.entropy_coefficient * mean_entropy
    value_loss = jnp.mean((outputs["value"] - batch["reward_return"]) ** 2)
    constraint_value_loss = jnp.mean(
        (outputs["constraint_value"] - batch["constraint_return"]) ** 2
    )
    total = (
        actor_loss
        + config.value_coefficient * value_loss
        + config.constraint_value_coefficient * constraint_value_loss
    )
    metrics = {
        "loss": total,
        "actor_loss": actor_loss,
        "policy_loss": policy_loss,
        "value_loss": value_loss,
        "constraint_value_loss": constraint_value_loss,
        "entropy": mean_entropy,
        "exact_kl": jnp.mean(exact_kl_rows),
        "approximate_kl": jnp.mean((ratio - 1.0) - log_ratio),
        "clip_fraction": jnp.mean(
            (jnp.abs(ratio - 1.0) > config.clip_epsilon).astype(jnp.float32)
        ),
        "mean_ratio": jnp.mean(ratio),
    }
    return total, metrics


def train_minibatch(
    state: TrainState, batch: Mapping[str, Any], *, config: PPOConfig
) -> tuple[TrainState, dict[str, jnp.ndarray]]:
    def loss_fn(params: Any) -> tuple[jnp.ndarray, dict[str, jnp.ndarray]]:
        return ppo_loss(params, state.apply_fn, batch, config=config)

    (_, metrics), gradients = jax.value_and_grad(loss_fn, has_aux=True)(state.params)
    return state.apply_gradients(grads=gradients), metrics


def evaluate_state(
    state: TrainState, data: Mapping[str, np.ndarray], *, config: PPOConfig
) -> dict[str, float]:
    batch = make_batch(data, np.arange(len(data["features"])))
    _, metrics = ppo_loss(state.params, state.apply_fn, batch, config=config)
    return {key: float(jax.device_get(value)) for key, value in metrics.items()}


def _flatten_params(params: Any) -> dict[tuple[str, ...], np.ndarray]:
    from flax.traverse_util import flatten_dict

    return {
        tuple(str(part) for part in path): np.asarray(jax.device_get(value))
        for path, value in flatten_dict(unfreeze(params)).items()
    }


def parameter_change_report(before: Any, after: Any) -> dict[str, Any]:
    left, right = _flatten_params(before), _flatten_params(after)
    if set(left) != set(right):
        raise ValueError("parameter tree changed structure during PPO")
    rows: list[dict[str, Any]] = []
    for path in sorted(left):
        delta = float(np.max(np.abs(right[path] - left[path])))
        role = "critic" if path[0] in CRITIC_PARAMETER_ROOTS else "actor"
        rows.append({"path": "/".join(path), "role": role, "max_abs_delta": delta, "changed": delta > 0.0})
    return {
        "total_leaves": len(rows),
        "changed_leaves": sum(row["changed"] for row in rows),
        "actor_changed_leaves": sum(row["changed"] and row["role"] == "actor" for row in rows),
        "critic_changed_leaves": sum(row["changed"] and row["role"] == "critic" for row in rows),
        "actor_max_abs_delta": max((row["max_abs_delta"] for row in rows if row["role"] == "actor"), default=0.0),
        "critic_max_abs_delta": max((row["max_abs_delta"] for row in rows if row["role"] == "critic"), default=0.0),
        "leaves": rows,
    }


def _layer_summary(data: Mapping[str, np.ndarray]) -> dict[str, Any]:
    offsets = np.asarray(data["episode_offsets"], dtype=np.int64)
    terminal_indices = offsets[1:] - 1
    scores = np.asarray(data["score"])[terminal_indices]
    rewards = np.asarray(data["candidate_reward"])[terminal_indices]
    catastrophes = np.asarray(data["catastrophe"])[terminal_indices].astype(bool)
    return {
        "samples": int(len(data["features"])),
        "episodes": int(len(terminal_indices)),
        "wdl": {
            "wins": int(np.sum(scores == 1.0)),
            "draws": int(np.sum(scores == 0.5)),
            "losses": int(np.sum(scores == 0.0)),
        },
        "score_rate": float(np.mean(scores)),
        "mean_own_reward": float(np.mean(rewards)),
        "p10_own_reward": float(np.percentile(rewards, 10)),
        "catastrophes": int(np.sum(catastrophes)),
        "catastrophe_rate": float(np.mean(catastrophes)),
    }


def build_checkpoint_payload(
    initial_payload: Mapping[str, Any],
    params: Any,
    *,
    initial_checkpoint_sha256: str,
    dataset_sha256: Mapping[str, str],
    rollout_report_sha256: Mapping[str, str],
    reward_config: RewardConfig,
    ppo_config: PPOConfig,
    iteration: int,
    training_seed: int,
) -> dict[str, Any]:
    payload = {key: value for key, value in initial_payload.items() if key != "params"}
    payload.update({
        "params": unfreeze(params),
        "training_method": "true_on_policy_event_program_smdp_ppo",
        "training_initial_checkpoint_sha256": initial_checkpoint_sha256,
        "training_dataset_sha256": dict(dataset_sha256),
        "training_rollout_report_sha256": dict(rollout_report_sha256),
        "reward_contract": {"schema": REWARD_SCHEMA, **asdict(reward_config)},
        "hyperparameters": asdict(ppo_config),
        "training_seed": int(training_seed),
        "iteration": int(iteration),
        "PPO": True,
    })
    validate_checkpoint_metadata(payload)
    return payload


def train_ppo(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    bindings = pair_layer_bindings(args.dataset, args.rollout_report)
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
    training_report_path = Path(args.report).expanduser().resolve()
    immutable_inputs = {
        initial_path,
        *(path for pair in bindings.values() for path in pair),
    }
    if output_path in immutable_inputs or training_report_path in immutable_inputs:
        raise ValueError("output/report paths must not overwrite immutable PPO inputs")
    if output_path == training_report_path:
        raise ValueError("checkpoint output and training report must use different paths")

    reward_config = RewardConfig(
        outcome_win=float(args.outcome_win), outcome_draw=float(args.outcome_draw),
        outcome_loss=float(args.outcome_loss), margin_coefficient=float(args.margin_coefficient),
        own_reward_coefficient=float(args.own_reward_coefficient),
        catastrophe_penalty=float(args.catastrophe_penalty),
        potential_coefficient=float(args.potential_coefficient),
    )
    ppo_config = PPOConfig(
        gamma_day=float(args.gamma_day), lambda_day=float(args.lambda_day),
        constraint_lambda=float(args.constraint_lambda), clip_epsilon=float(args.clip_epsilon),
        entropy_coefficient=float(args.entropy_coefficient), target_exact_kl=float(args.target_exact_kl),
        actor_learning_rate=float(args.actor_learning_rate), critic_learning_rate=float(args.critic_learning_rate),
        value_coefficient=float(args.value_coefficient),
        constraint_value_coefficient=float(args.constraint_value_coefficient),
        gradient_clip_norm=float(args.gradient_clip_norm), epochs=int(args.epochs),
        minibatch_size=int(args.minibatch_size),
    )
    if ppo_config.epochs <= 0 or ppo_config.minibatch_size <= 0:
        raise ValueError("epochs and minibatch_size must be positive")
    positive = (
        ppo_config.gamma_day, ppo_config.lambda_day, ppo_config.target_exact_kl,
        ppo_config.actor_learning_rate, ppo_config.critic_learning_rate,
        ppo_config.gradient_clip_norm,
    )
    if any(value <= 0 for value in positive):
        raise ValueError("PPO discount, KL, learning rates and grad clip must be positive")
    if not 0 < ppo_config.clip_epsilon < 1:
        raise ValueError("clip_epsilon must be between zero and one")

    layer_data: dict[str, dict[str, np.ndarray]] = {}
    prepared: dict[str, dict[str, np.ndarray]] = {}
    validation: dict[str, Any] = {}
    reward_audit: dict[str, Any] = {}
    dataset_shas: dict[str, str] = {}
    report_shas: dict[str, str] = {}
    layer_summaries: dict[str, Any] = {}
    for layer, (dataset_path, report_path) in bindings.items():
        with report_path.open("r", encoding="utf-8") as source:
            report = json.load(source)
        report_contract = _validate_report_contract(
            report, report_path=report_path, dataset_path=dataset_path,
            initial_checkpoint_sha256=initial_sha,
        )
        data = load_npz(dataset_path)
        npz_contract = validate_npz_contract(data, report=report)
        if report_contract["episodes"] != npz_contract["episodes"]:
            raise ValueError("rollout report and NPZ episode counts differ")
        layer_data[layer] = data
        prepared[layer], reward_rows = prepare_layer_training_data(
            normalization_layer(layer),
            data,
            reward_config=reward_config,
            ppo_config=ppo_config,
        )
        validation[layer] = {"report": report_contract, "npz": npz_contract}
        reward_audit[layer] = {
            "episodes": len(reward_rows),
            "mean_terminal_reward": float(np.mean([row["terminal_reward"] for row in reward_rows])),
            "mean_potential_shaping_sum": float(np.mean([row["potential_shaping_sum"] for row in reward_rows])),
            "mean_training_reward_sum": float(np.mean([row["training_reward_sum"] for row in reward_rows])),
        }
        dataset_shas[layer] = file_sha256(dataset_path)
        report_shas[layer] = file_sha256(report_path)
        layer_summaries[layer] = _layer_summary(data)

    training_data, normalization = concatenate_layers(
        layer_data, prepared, constraint_lambda=ppo_config.constraint_lambda
    )
    initial_params = unfreeze(initial_payload["params"])
    state = create_train_state(initial_params, ppo_config)
    pre_metrics = evaluate_state(state, training_data, config=ppo_config)
    if not np.isfinite(pre_metrics["exact_kl"]) or pre_metrics["exact_kl"] > 1.0e-6:
        raise ValueError(
            "rollouts are not on-policy for the initial checkpoint: "
            f"pre-update exact KL={pre_metrics['exact_kl']}"
        )
    rng = np.random.default_rng(int(args.seed))
    history: list[dict[str, Any]] = []
    stop_reason = "completed_configured_epochs"
    for epoch in range(1, ppo_config.epochs + 1):
        order = np.arange(len(training_data["features"]), dtype=np.int64)
        rng.shuffle(order)
        minibatch_metrics: list[dict[str, float]] = []
        for start in range(0, len(order), ppo_config.minibatch_size):
            batch = make_batch(training_data, order[start:start + ppo_config.minibatch_size])
            state, metrics = train_minibatch(state, batch, config=ppo_config)
            minibatch_metrics.append({
                key: float(jax.device_get(value)) for key, value in metrics.items()
            })
        epoch_metrics = evaluate_state(state, training_data, config=ppo_config)
        history.append({
            "epoch": epoch,
            "minibatches": len(minibatch_metrics),
            "mean_minibatch_loss": float(np.mean([row["loss"] for row in minibatch_metrics])),
            "full_dataset": epoch_metrics,
        })
        if epoch_metrics["exact_kl"] > ppo_config.target_exact_kl:
            stop_reason = "target_exact_kl_exceeded"
            break
    post_metrics = evaluate_state(state, training_data, config=ppo_config)
    changes = parameter_change_report(initial_params, state.params)
    if changes["actor_changed_leaves"] == 0 or changes["critic_changed_leaves"] == 0:
        raise RuntimeError("PPO update did not change both actor/trunk and critic parameters")

    checkpoint_payload = build_checkpoint_payload(
        initial_payload, state.params,
        initial_checkpoint_sha256=initial_sha,
        dataset_sha256=dataset_shas,
        rollout_report_sha256=report_shas,
        reward_config=reward_config,
        ppo_config=ppo_config,
        iteration=int(args.iteration),
        training_seed=int(args.seed),
    )
    checkpoint_sha = atomic_checkpoint(output_path, checkpoint_payload)
    restored = serialization.msgpack_restore(output_path.read_bytes())
    validate_checkpoint_metadata(restored)
    if file_sha256(initial_path) != initial_sha:
        raise RuntimeError("initial checkpoint changed during PPO training")
    report = {
        "schema": TRAINING_SCHEMA,
        "status": "COMPLETE",
        "PPO": True,
        "iteration": int(args.iteration),
        "lineage": {
            "strategy_parent": None,
            "loads_historical_policy_parameters": False,
            "uses_historical_agent_fallback": False,
        },
        "initial_checkpoint": {
            "path": str(initial_path), "sha256_before": initial_sha,
            "sha256_after": file_sha256(initial_path), "unchanged": True,
        },
        "inputs": {
            layer: {
                "dataset_path": str(bindings[layer][0]), "dataset_sha256": dataset_shas[layer],
                "rollout_report_path": str(bindings[layer][1]), "rollout_report_sha256": report_shas[layer],
            }
            for layer in bindings
        },
        "validation": validation,
        "reward_contract": {
            "schema": REWARD_SCHEMA,
            "terminal_only": "outcome + margin + own_reward - catastrophe",
            "interval_shaping": "coefficient * (gamma^duration * Phi(next) - Phi(current)); terminal Phi=0",
            "phi": "(public own money - 3000) / 10000",
            "future_derived_fields": False,
            **asdict(reward_config),
        },
        "hyperparameters": asdict(ppo_config),
        "advantage_contract": {
            "reward_and_constraint_gae_computed_per_episode": True,
            "normalization_unit": "LAYER",
            "actor_advantage": "normalized_reward_advantage - constraint_lambda * normalized_constraint_advantage",
            "normalization": normalization,
        },
        "layers": layer_summaries,
        "reward_audit": reward_audit,
        "metrics": {"pre": pre_metrics, "post": post_metrics, "history": history},
        "training_stop_reason": stop_reason,
        "epochs_completed": len(history),
        "parameter_changes": changes,
        "optimizer_parameter_roles": {
            "actor_lr": "shared trunk + five actor heads",
            "critic_lr": "value_head + constraint_value_head",
        },
        "checkpoint": {"path": str(output_path), "sha256": checkpoint_sha},
        "training_seed": int(args.seed),
        "elapsed_seconds": time.time() - started,
    }
    atomic_json(training_report_path, report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--initial-checkpoint", type=Path, required=True)
    parser.add_argument("--dataset", action="append", required=True, metavar="LAYER=NPZ")
    parser.add_argument("--rollout-report", action="append", required=True, metavar="LAYER=JSON")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--iteration", type=int, default=1)
    parser.add_argument("--seed", type=int, default=114930)
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--minibatch-size", type=int, default=256)
    parser.add_argument("--gamma-day", type=float, default=0.99)
    parser.add_argument("--lambda-day", type=float, default=0.95)
    parser.add_argument("--constraint-lambda", type=float, default=0.5)
    parser.add_argument("--clip-epsilon", type=float, default=0.10)
    parser.add_argument("--entropy-coefficient", type=float, default=0.01)
    parser.add_argument("--target-exact-kl", type=float, default=0.01)
    parser.add_argument("--actor-learning-rate", type=float, default=1.0e-5)
    parser.add_argument("--critic-learning-rate", type=float, default=3.0e-5)
    parser.add_argument("--value-coefficient", type=float, default=0.5)
    parser.add_argument("--constraint-value-coefficient", type=float, default=0.25)
    parser.add_argument("--gradient-clip-norm", type=float, default=0.5)
    parser.add_argument("--outcome-win", type=float, default=1.0)
    parser.add_argument("--outcome-draw", type=float, default=0.0)
    parser.add_argument("--outcome-loss", type=float, default=-1.0)
    parser.add_argument("--margin-coefficient", type=float, default=0.25)
    parser.add_argument("--own-reward-coefficient", type=float, default=0.25)
    parser.add_argument("--catastrophe-penalty", type=float, default=1.0)
    parser.add_argument("--potential-coefficient", type=float, default=0.1)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        report = train_ppo(args)
    except (TypeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps({
        "status": report["status"],
        "checkpoint": report["checkpoint"],
        "training_stop_reason": report["training_stop_reason"],
        "metrics": {"pre": report["metrics"]["pre"], "post": report["metrics"]["post"]},
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


__all__ = [
    "PPOConfig", "REWARD_SCHEMA", "RewardConfig", "TRAINING_SCHEMA",
    "build_checkpoint_payload", "compute_episode_rewards", "concatenate_layers",
    "create_train_state", "layer_standardize", "make_batch", "pair_layer_bindings",
    "parameter_change_report", "parameter_labels", "potential_shaping", "ppo_loss",
    "prepare_layer_training_data", "recompute_old_joint_logp", "terminal_outcome_reward",
    "train_minibatch", "train_ppo", "validate_npz_contract",
    "validate_old_policy_evidence",
]
