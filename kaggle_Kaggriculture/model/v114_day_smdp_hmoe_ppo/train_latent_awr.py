"""Train V114 V8 latent-role decoders with outcome-weighted regression.

This is a conservative AWR update from the frozen V6 checkpoint.  It trains
only actions actually executed by the V6 candidate.  Gold/teacher action
labels are neither accepted as a fallback nor consumed by the loss.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
from typing import Any, Mapping

from flax import serialization, traverse_util
from flax.core import freeze, unfreeze
from flax.training.train_state import TrainState
import jax
import jax.numpy as jnp
import numpy as np
import optax


HERE = Path(__file__).resolve().parent
V113 = HERE.parent / "v113_simulator_hmoe_ppo"
if str(V113) not in sys.path:
    sys.path.insert(0, str(V113))

import action_space as space  # noqa: E402
from model_latent_role_hmoe import LatentRoleHMoE  # noqa: E402
from train_nested_bc import (  # noqa: E402
    MARKET_QUANTITY_TOKEN,
    MODEL_KEYS,
    UNIT_QUANTITY_TOKEN,
)


DEFAULT_V6_CHECKPOINT = (
    HERE.parent.parent
    / "model_data/v114_day_smdp_hmoe_ppo/experts/latent_role_bc_v6/train"
    / "latent_role_bc_best.msgpack"
)
V6_CHECKPOINT_SHA256 = (
    "ddc942b3d41177804a6163a3bde71d106daee9e6e8d0b7ca9d066df663e14dd2"
)
V6_DATASET_SHA256 = (
    "c7b996dc5b5801faa19a0c7e709ccf5ee28ffa3830fdd8a923ab89b45f9d18c8"
)
V6_MODEL_ID = "v114_day_smdp_hmoe_ppo_latent_role_bc_v1"
V6_ARCHITECTURE = "v114-causal-latent-role-absorbing-stop-hmoe-v1"

CANDIDATE_KEYS = (
    "candidate_unit_tokens",
    "candidate_unit_quantities",
    "candidate_market_tokens",
    "candidate_market_quantities",
    "candidate_market_mask",
)
ACTUAL_ACTION_KEY_MAP = {
    "candidate_unit_tokens": "unit_tokens",
    "candidate_unit_quantities": "unit_quantities",
    "candidate_market_tokens": "market_tokens",
    "candidate_market_quantities": "market_quantities",
    "candidate_market_mask": "market_mask",
}
REQUIRED_KEYS = MODEL_KEYS + CANDIDATE_KEYS + (
    "option_id",
    "episode",
    "seat",
    "episode_return",
    "candidate_reward",
    "source_kind",
)

# The encoder, manager, option router and catastrophe head stay bitwise frozen.
# Token/slot embeddings and recurrent modules are part of the autoregressive
# action/role decoder, so they are included in the conservative update.
TRAINABLE_ROOTS = frozenset(
    {
        "unit_decoder_seed",
        "unit_gru",
        "unit_token_embedding",
        "unit_quantity_embedding",
        "unit_slot_embedding",
        "unit_role_embedding",
        "unit_role_carry_projection",
        "unit_role_context_projection",
        "unit_role_head",
        "unit_action_head",
        "unit_quantity_head",
        "market_decoder_seed",
        "market_gru",
        "market_token_embedding",
        "market_quantity_embedding",
        "market_slot_embedding",
        "market_role_embedding",
        "market_role_carry_projection",
        "market_role_context_projection",
        "market_role_head",
        "market_action_head",
        "market_quantity_head",
        "option_value_head",
    }
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _average_ranks(values: np.ndarray) -> np.ndarray:
    """Return zero-based average ranks, with deterministic tie handling."""

    values = np.asarray(values, dtype=np.float64)
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=np.float64)
    start = 0
    while start < len(order):
        stop = start + 1
        while stop < len(order) and values[order[stop]] == values[order[start]]:
            stop += 1
        ranks[order[start:stop]] = 0.5 * (start + stop - 1)
        start = stop
    return ranks


def rank_standardized_advantages(
    option_id: np.ndarray,
    episode: np.ndarray,
    seat: np.ndarray,
    episode_utility: np.ndarray,
    opponent_layer: np.ndarray | None = None,
) -> np.ndarray:
    """Rank complete-game utility within option/opponent-layer strata.

    A game is identified by ``(option, episode, seat)``.  Every row belonging
    to a game must carry the same terminal return.  Ranking complete episodes,
    rather than timesteps, prevents long trajectories from receiving extra
    influence.
    """

    arrays = [np.asarray(x) for x in (option_id, episode, seat, episode_utility)]
    if not arrays or any(x.ndim != 1 for x in arrays):
        raise ValueError("advantage inputs must be one-dimensional")
    if len({len(x) for x in arrays}) != 1 or len(arrays[0]) == 0:
        raise ValueError("advantage inputs must be non-empty and row-aligned")
    if not np.all(np.isfinite(arrays[3])):
        raise ValueError("episode_utility contains non-finite values")

    if opponent_layer is None:
        layers = np.full(len(arrays[0]), "all", dtype="U3")
    else:
        layers = np.asarray(opponent_layer).astype(str)
        if layers.ndim != 1 or len(layers) != len(arrays[0]):
            raise ValueError("opponent_layer must be one-dimensional and row-aligned")

    options = arrays[0].astype(np.int64)
    episodes = arrays[1].astype(np.int64)
    seats = arrays[2].astype(np.int64)
    utilities = arrays[3].astype(np.float64)
    game_keys = np.stack((options, episodes, seats), axis=1)
    unique_keys, inverse = np.unique(game_keys, axis=0, return_inverse=True)
    game_utilities = np.empty(len(unique_keys), dtype=np.float64)
    game_layers = np.empty(len(unique_keys), dtype=object)
    for game_index in range(len(unique_keys)):
        values = utilities[inverse == game_index]
        if not np.all(values == values[0]):
            raise ValueError(
                "episode_utility must be constant within option/episode/seat"
            )
        layer_values = layers[inverse == game_index]
        if not np.all(layer_values == layer_values[0]):
            raise ValueError(
                "opponent_layer must be constant within option/episode/seat"
            )
        game_utilities[game_index] = values[0]
        game_layers[game_index] = layer_values[0]

    game_advantage = np.zeros(len(unique_keys), dtype=np.float64)
    for option in np.unique(unique_keys[:, 0]):
        for layer in np.unique(game_layers[unique_keys[:, 0] == option]):
            selected = np.flatnonzero(
                (unique_keys[:, 0] == option) & (game_layers == layer)
            )
            ranks = _average_ranks(game_utilities[selected])
            standard_deviation = float(np.std(ranks))
            if standard_deviation > 0:
                ranks = (ranks - float(np.mean(ranks))) / standard_deviation
            else:
                ranks = np.zeros_like(ranks)
            game_advantage[selected] = ranks
    return game_advantage[inverse].astype(np.float32)


def composite_episode_utility(
    episode_return: np.ndarray,
    candidate_reward: np.ndarray,
    *,
    own_reward_coefficient: float,
    catastrophe_penalty: float,
    catastrophe_threshold: float,
    own_reward_scale: float = 5000.0,
) -> np.ndarray:
    """Combine relative performance with an absolute-economy guardrail."""

    relative = np.asarray(episode_return, dtype=np.float64)
    reward = np.asarray(candidate_reward, dtype=np.float64)
    if relative.shape != reward.shape or relative.ndim != 1:
        raise ValueError("episode_return and candidate_reward must be row-aligned vectors")
    if not np.all(np.isfinite(relative)) or not np.all(np.isfinite(reward)):
        raise ValueError("utility inputs contain non-finite values")
    if own_reward_coefficient < 0 or catastrophe_penalty < 0:
        raise ValueError("utility coefficients must be non-negative")
    if catastrophe_threshold <= 0 or own_reward_scale <= 0:
        raise ValueError("utility reward thresholds must be positive")
    own_economy = np.clip(
        (reward - catastrophe_threshold) / own_reward_scale, -1.0, 1.0
    )
    catastrophe = (reward < catastrophe_threshold).astype(np.float64)
    utility = (
        relative
        + own_reward_coefficient * own_economy
        - catastrophe_penalty * catastrophe
    )
    return utility.astype(np.float32)


def normalize_candidate_action_keys(data: dict[str, np.ndarray]) -> None:
    """Map collector action fields only under explicit self-imitation provenance."""

    if "source_kind" not in data:
        raise ValueError("rollout dataset has no source_kind provenance")
    source_kind = np.asarray(data["source_kind"]).astype(str)
    if not np.all(source_kind == "candidate_self_imitation"):
        raise ValueError("only candidate_self_imitation actual actions are accepted")
    for candidate_key, collected_key in ACTUAL_ACTION_KEY_MAP.items():
        if candidate_key in data:
            continue
        if collected_key not in data:
            raise ValueError(f"rollout dataset missing actual action field {collected_key!r}")
        data[candidate_key] = np.asarray(data[collected_key])


def opponent_layers_from_report(
    data: Mapping[str, np.ndarray], report: Mapping[str, Any]
) -> np.ndarray:
    """Recover the immutable opponent layer for every timestep."""

    schedule = report.get("opponent_schedule")
    if not isinstance(schedule, list) or not schedule:
        raise ValueError("rollout report has no opponent_schedule")
    layer_by_seed = {}
    for row in schedule:
        seed = int(row["seed"])
        layer = str(row["layer"])
        if seed in layer_by_seed and layer_by_seed[seed] != layer:
            raise ValueError(f"seed {seed} has inconsistent opponent layers")
        layer_by_seed[seed] = layer
    episode = np.asarray(data["episode"], dtype=np.int64)
    option = np.asarray(data["option_id"], dtype=np.int64)
    if not np.all(episode % 3 == option):
        raise ValueError("episode ids violate seed * 3 + option_id contract")
    seeds = episode // 3
    missing = sorted(set(int(seed) for seed in np.unique(seeds)) - set(layer_by_seed))
    if missing:
        raise ValueError(f"rollout report misses seeds: {missing}")
    return np.asarray([layer_by_seed[int(seed)] for seed in seeds])


def clipped_awr_weights(
    advantage: np.ndarray, beta: float, clip: float
) -> np.ndarray:
    if beta < 0:
        raise ValueError("beta must be non-negative")
    if clip < 1:
        raise ValueError("clip must be at least one")
    values = np.asarray(advantage, dtype=np.float64)
    if not np.all(np.isfinite(values)):
        raise ValueError("advantage contains non-finite values")
    return np.minimum(np.exp(np.clip(beta * values, -60.0, 60.0)), clip).astype(
        np.float32
    )


def cap_catastrophe_weights(
    weights: np.ndarray,
    candidate_reward: np.ndarray,
    *,
    catastrophe_threshold: float,
    catastrophe_weight_cap: float,
) -> np.ndarray:
    """Prevent a best-in-bad-stratum catastrophe from becoming a target."""

    result = np.asarray(weights, dtype=np.float32).copy()
    reward = np.asarray(candidate_reward, dtype=np.float64)
    if result.shape != reward.shape:
        raise ValueError("weights and candidate_reward must be row-aligned")
    if not (0 < catastrophe_weight_cap <= 1):
        raise ValueError("catastrophe_weight_cap must be in (0, 1]")
    result[reward < catastrophe_threshold] = np.minimum(
        result[reward < catastrophe_threshold], catastrophe_weight_cap
    )
    return result


def validate_v6_payload(
    payload: Mapping[str, Any],
    checkpoint_path: Path,
    *,
    actual_sha256: str,
    expected_sha256: str = V6_CHECKPOINT_SHA256,
    expected_dataset_sha256: str = V6_DATASET_SHA256,
) -> None:
    """Fail closed unless the optimization anchor is the frozen V6 artifact."""

    if "v7" in str(checkpoint_path).lower():
        raise ValueError("V8 must initialize from V6, never from V7")
    if actual_sha256 != expected_sha256:
        raise ValueError("V6 checkpoint SHA256 mismatch")
    expected = {
        "model_id": V6_MODEL_ID,
        "architecture": V6_ARCHITECTURE,
        "dataset_sha256": expected_dataset_sha256,
        "strategy_parent": None,
        "inherits_v113_checkpoint": False,
        "online_historical_agent_fallback": False,
        "teacher_role_conditions_action_decoder": False,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise ValueError(f"invalid V6 checkpoint field {key!r}")
    if "params" not in payload:
        raise ValueError("V6 checkpoint has no params")


def validate_dataset(data: Mapping[str, np.ndarray]) -> int:
    missing = sorted(set(REQUIRED_KEYS) - set(data))
    if missing:
        raise ValueError(
            "candidate-executed rollout dataset missing keys: " + ", ".join(missing)
        )
    row_count = len(np.asarray(data["option_id"]))
    if row_count == 0:
        raise ValueError("rollout dataset is empty")
    for key in REQUIRED_KEYS:
        if len(np.asarray(data[key])) != row_count:
            raise ValueError(f"rollout field {key!r} is not row-aligned")
    if np.asarray(data["candidate_unit_tokens"]).shape[1:] != (16,):
        raise ValueError("candidate_unit_tokens must have shape [N, 16]")
    if np.asarray(data["candidate_unit_quantities"]).shape[1:] != (16,):
        raise ValueError("candidate_unit_quantities must have shape [N, 16]")
    for key in ("candidate_market_tokens", "candidate_market_quantities", "candidate_market_mask"):
        if np.asarray(data[key]).shape[1:] != (space.MAX_MARKET_SLOTS,):
            raise ValueError(f"{key} must have shape [N, {space.MAX_MARKET_SLOTS}]")
    options = np.asarray(data["option_id"])
    if np.any((options < 0) | (options >= 3)):
        raise ValueError("option_id must be in [0, 3)")
    if not np.all(np.isin(np.asarray(data["seat"]), (0, 1))):
        raise ValueError("seat must contain only 0 or 1")
    if not np.all(np.isfinite(np.asarray(data["episode_return"]))):
        raise ValueError("episode_return contains non-finite values")
    return row_count


def parameter_labels(params: Mapping[str, Any]):
    """Label exactly the decoder/value leaves that may change."""

    mutable = unfreeze(params)
    flat = traverse_util.flatten_dict(mutable)
    labels = {
        path: ("train" if path and path[0] in TRAINABLE_ROOTS else "freeze")
        for path in flat
    }
    return freeze(traverse_util.unflatten_dict(labels))


def trainable_parameter_paths(params: Mapping[str, Any]) -> list[str]:
    flat = traverse_util.flatten_dict(unfreeze(parameter_labels(params)))
    return ["/".join(path) for path, label in flat.items() if label == "train"]


def _categorical_kl(reference_logits, current_logits):
    reference_log_probability = jax.nn.log_softmax(reference_logits, axis=-1)
    current_log_probability = jax.nn.log_softmax(current_logits, axis=-1)
    return jnp.sum(
        jnp.exp(reference_log_probability)
        * (reference_log_probability - current_log_probability),
        axis=-1,
    )


def _masked_mean(values, mask):
    mask = mask.astype(jnp.float32)
    return jnp.sum(values * mask) / jnp.maximum(1.0, jnp.sum(mask))


def _weighted_action_loss(logits, labels, mask, row_weight):
    losses = optax.softmax_cross_entropy_with_integer_labels(
        logits, labels.astype(jnp.int32)
    )
    weights = mask.astype(jnp.float32) * row_weight[:, None]
    return jnp.sum(losses * weights) / jnp.maximum(1.0, jnp.sum(weights))


def _group_counts(logits, labels, mask, group):
    active = mask.astype(jnp.float32) * group[:, None].astype(jnp.float32)
    correct = (jnp.argmax(logits, axis=-1) == labels).astype(jnp.float32)
    return jnp.sum(correct * active), jnp.sum(active)


def make_loss(reference_params, kl_coefficient: float, value_coefficient: float):
    """Create AWR loss against the immutable V6 logit anchor."""

    reference_params = jax.tree_util.tree_map(jax.lax.stop_gradient, reference_params)
    unit_quantity_lookup = jnp.asarray(UNIT_QUANTITY_TOKEN)
    market_quantity_lookup = jnp.asarray(MARKET_QUANTITY_TOKEN)

    def loss_fn(params, apply_fn, batch):
        model_arguments = (
            *(batch[key] for key in MODEL_KEYS),
            batch["candidate_unit_tokens"],
            batch["candidate_unit_quantities"],
            batch["candidate_market_tokens"],
            batch["candidate_market_quantities"],
        )
        current = apply_fn({"params": params}, *model_arguments)
        reference = apply_fn({"params": reference_params}, *model_arguments)
        row = jnp.arange(batch["option_id"].shape[0])
        option = batch["option_id"].astype(jnp.int32)

        def select(output, key):
            return output[key][row, option]

        unit_logits = select(current, "unit_logits")
        unit_q_logits = select(current, "unit_quantity_logits")
        market_logits = select(current, "market_logits")
        market_q_logits = select(current, "market_quantity_logits")
        unit_mask = batch["unit_mask"]
        market_mask = batch["candidate_market_mask"]
        unit_qmask = unit_mask * unit_quantity_lookup[
            batch["candidate_unit_tokens"]
        ]
        market_qmask = market_mask * market_quantity_lookup[
            batch["candidate_market_tokens"]
        ]
        awr_weight = batch["awr_weight"]

        unit_loss = _weighted_action_loss(
            unit_logits, batch["candidate_unit_tokens"], unit_mask, awr_weight
        )
        unit_q_loss = _weighted_action_loss(
            unit_q_logits,
            batch["candidate_unit_quantities"],
            unit_qmask,
            awr_weight,
        )
        market_loss = _weighted_action_loss(
            market_logits, batch["candidate_market_tokens"], market_mask, awr_weight
        )
        market_q_loss = _weighted_action_loss(
            market_q_logits,
            batch["candidate_market_quantities"],
            market_qmask,
            awr_weight,
        )

        kl_terms = (
            _masked_mean(
                _categorical_kl(select(reference, "unit_logits"), unit_logits),
                unit_mask,
            )
            + 0.15
            * _masked_mean(
                _categorical_kl(
                    select(reference, "unit_quantity_logits"), unit_q_logits
                ),
                unit_qmask,
            )
            + _masked_mean(
                _categorical_kl(select(reference, "market_logits"), market_logits),
                market_mask,
            )
            + 0.15
            * _masked_mean(
                _categorical_kl(
                    select(reference, "market_quantity_logits"), market_q_logits
                ),
                market_qmask,
            )
            + 0.25
            * _masked_mean(
                _categorical_kl(
                    select(reference, "unit_role_logits"),
                    select(current, "unit_role_logits"),
                ),
                unit_mask,
            )
            + 0.25
            * _masked_mean(
                _categorical_kl(
                    select(reference, "market_role_logits"),
                    select(current, "market_role_logits"),
                ),
                market_mask,
            )
        )
        predicted_value = select(current, "option_value")
        value_loss = jnp.mean((predicted_value - batch["advantage"]) ** 2)
        behavior_loss = unit_loss + market_loss + 0.15 * (unit_q_loss + market_q_loss)
        total = behavior_loss + kl_coefficient * kl_terms + value_coefficient * value_loss

        metrics = {
            "loss": total,
            "behavior_loss": behavior_loss,
            "kl_to_v6": kl_terms,
            "value_loss": value_loss,
            "awr_weight_mean": jnp.mean(awr_weight),
        }
        high = batch["return_group"] > 0
        low = batch["return_group"] < 0
        for name, group in (("high", high), ("low", low)):
            unit_correct, unit_count = _group_counts(
                unit_logits, batch["candidate_unit_tokens"], unit_mask, group
            )
            market_correct, market_count = _group_counts(
                market_logits,
                batch["candidate_market_tokens"],
                market_mask,
                group,
            )
            metrics[f"{name}_unit_correct"] = unit_correct
            metrics[f"{name}_unit_count"] = unit_count
            metrics[f"{name}_market_correct"] = market_correct
            metrics[f"{name}_market_count"] = market_count
        return total, metrics

    return loss_fn


def _split_by_episode(data, seed: int, validation_fraction: float):
    episode = np.asarray(data["episode"])
    unique = np.unique(episode)
    if len(unique) < 2:
        raise ValueError("AWR requires at least two episode groups")
    shuffled = unique.copy()
    np.random.default_rng(seed).shuffle(shuffled)
    count = min(len(unique) - 1, max(1, int(round(len(unique) * validation_fraction))))
    validation_episode = shuffled[:count]
    validation = np.flatnonzero(np.isin(episode, validation_episode))
    train = np.flatnonzero(~np.isin(episode, validation_episode))
    return train, validation, validation_episode


def _batches(data, indices, batch_size: int, rng, shuffle: bool):
    selected_indices = np.asarray(indices).copy()
    if shuffle:
        rng.shuffle(selected_indices)
    for start in range(0, len(selected_indices), batch_size):
        selected = selected_indices[start : start + batch_size]
        if not len(selected):
            continue
        batch = {}
        for key in MODEL_KEYS:
            batch[key] = jnp.asarray(data[key][selected], dtype=jnp.float32)
        for key in CANDIDATE_KEYS:
            dtype = jnp.float32 if key == "candidate_market_mask" else jnp.int32
            batch[key] = jnp.asarray(data[key][selected], dtype=dtype)
        for key in ("option_id", "return_group"):
            batch[key] = jnp.asarray(data[key][selected], dtype=jnp.int32)
        for key in ("advantage", "awr_weight"):
            batch[key] = jnp.asarray(data[key][selected], dtype=jnp.float32)
        yield batch


def _summarize(rows) -> dict[str, float]:
    if not rows:
        raise ValueError("no metric rows to summarize")
    scalar = ("loss", "behavior_loss", "kl_to_v6", "value_loss", "awr_weight_mean")
    summary = {
        key: float(np.mean([float(row[key]) for row in rows])) for key in scalar
    }
    for group in ("high", "low"):
        for action in ("unit", "market"):
            correct = sum(float(row[f"{group}_{action}_correct"]) for row in rows)
            count = sum(float(row[f"{group}_{action}_count"]) for row in rows)
            summary[f"{group}_{action}_accuracy"] = correct / count if count else None
            summary[f"{group}_{action}_count"] = int(count)
    return summary


def _max_frozen_delta(initial_params, final_params, labels) -> float:
    initial = traverse_util.flatten_dict(unfreeze(initial_params))
    final = traverse_util.flatten_dict(unfreeze(final_params))
    flat_labels = traverse_util.flatten_dict(unfreeze(labels))
    deltas = [
        float(np.max(np.abs(np.asarray(final[path]) - np.asarray(initial[path]))))
        for path, label in flat_labels.items()
        if label == "freeze"
    ]
    return max(deltas, default=0.0)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--rollout-report", type=Path, required=True)
    parser.add_argument("--v6-checkpoint", type=Path, default=DEFAULT_V6_CHECKPOINT)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--learning-rate", "--lr", dest="learning_rate", type=float, default=3e-5)
    parser.add_argument("--beta", type=float, default=1.0)
    parser.add_argument("--weight-clip", "--clip", dest="weight_clip", type=float, default=20.0)
    parser.add_argument("--kl-coefficient", "--kl", dest="kl_coefficient", type=float, default=0.1)
    parser.add_argument("--value-coefficient", type=float, default=0.05)
    parser.add_argument("--validation-fraction", type=float, default=0.25)
    parser.add_argument("--own-reward-coefficient", type=float, default=0.25)
    parser.add_argument("--catastrophe-penalty", type=float, default=2.0)
    parser.add_argument("--catastrophe-threshold", type=float, default=3000.0)
    parser.add_argument("--catastrophe-weight-cap", type=float, default=0.5)
    parser.add_argument("--own-reward-scale", type=float, default=5000.0)
    parser.add_argument("--seed", type=int, default=114880)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.epochs <= 0 or args.batch_size <= 0:
        parser.error("--epochs and --batch-size must be positive")
    if not (0 < args.learning_rate <= 1e-3):
        parser.error("--learning-rate must be in (0, 1e-3] for a small V6 update")
    if args.beta < 0 or args.weight_clip < 1:
        parser.error("--beta must be non-negative and --clip must be at least one")
    if args.kl_coefficient <= 0:
        parser.error("--kl must be positive; the frozen V6 anchor is mandatory")
    if args.value_coefficient <= 0:
        parser.error("--value-coefficient must be positive")
    if not (0 < args.validation_fraction < 1):
        parser.error("--validation-fraction must be in (0, 1)")
    if args.own_reward_coefficient < 0 or args.catastrophe_penalty < 0:
        parser.error("utility coefficients must be non-negative")
    if args.catastrophe_threshold <= 0 or args.own_reward_scale <= 0:
        parser.error("utility reward thresholds must be positive")
    if not (0 < args.catastrophe_weight_cap <= 1):
        parser.error("--catastrophe-weight-cap must be in (0, 1]")

    started = time.time()
    checkpoint_sha = sha256_file(args.v6_checkpoint)
    payload = serialization.msgpack_restore(args.v6_checkpoint.read_bytes())
    validate_v6_payload(
        payload,
        args.v6_checkpoint,
        actual_sha256=checkpoint_sha,
    )
    initial_params = freeze(payload["params"])
    reference_params = jax.tree_util.tree_map(lambda value: jnp.asarray(value), initial_params)

    with np.load(args.dataset, allow_pickle=False) as archive:
        data = {key: archive[key] for key in archive.files}
    normalize_candidate_action_keys(data)
    row_count = validate_dataset(data)
    rollout_report_sha = sha256_file(args.rollout_report)
    rollout_report = json.loads(args.rollout_report.read_text(encoding="utf-8"))
    dataset_sha = sha256_file(args.dataset)
    if rollout_report.get("dataset_sha256") != dataset_sha:
        raise ValueError("rollout report dataset SHA256 mismatch")
    data["opponent_layer"] = opponent_layers_from_report(data, rollout_report)
    data["episode_utility"] = composite_episode_utility(
        data["episode_return"],
        data["candidate_reward"],
        own_reward_coefficient=args.own_reward_coefficient,
        catastrophe_penalty=args.catastrophe_penalty,
        catastrophe_threshold=args.catastrophe_threshold,
        own_reward_scale=args.own_reward_scale,
    )
    data["advantage"] = rank_standardized_advantages(
        data["option_id"],
        data["episode"],
        data["seat"],
        data["episode_utility"],
        data["opponent_layer"],
    )
    data["awr_weight"] = clipped_awr_weights(
        data["advantage"], args.beta, args.weight_clip
    )
    data["awr_weight"] = cap_catastrophe_weights(
        data["awr_weight"],
        data["candidate_reward"],
        catastrophe_threshold=args.catastrophe_threshold,
        catastrophe_weight_cap=args.catastrophe_weight_cap,
    )
    data["return_group"] = np.sign(data["advantage"]).astype(np.int8)
    train_indices, validation_indices, validation_episodes = _split_by_episode(
        data, args.seed, args.validation_fraction
    )

    model = LatentRoleHMoE(timed=True)
    labels = parameter_labels(initial_params)
    optimizer = optax.multi_transform(
        {
            "train": optax.chain(
                optax.clip_by_global_norm(0.25),
                optax.adam(args.learning_rate),
            ),
            "freeze": optax.set_to_zero(),
        },
        labels,
    )
    state = TrainState.create(apply_fn=model.apply, params=initial_params, tx=optimizer)
    loss_fn = make_loss(reference_params, args.kl_coefficient, args.value_coefficient)

    @jax.jit
    def train_step(current, batch):
        (_, metrics), gradients = jax.value_and_grad(loss_fn, has_aux=True)(
            current.params, current.apply_fn, batch
        )
        return current.apply_gradients(grads=gradients), metrics

    @jax.jit
    def eval_step(current, batch):
        return loss_fn(current.params, current.apply_fn, batch)[1]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = args.output_dir / "latent_role_awr_v8_best.msgpack"
    rng = np.random.default_rng(args.seed)
    best_loss = float("inf")
    best_params = state.params
    history = []
    for epoch in range(1, args.epochs + 1):
        train_rows = []
        for batch in _batches(data, train_indices, args.batch_size, rng, True):
            state, metrics = train_step(state, batch)
            train_rows.append(jax.device_get(metrics))
        validation_rows = [
            jax.device_get(eval_step(state, batch))
            for batch in _batches(data, validation_indices, args.batch_size, rng, False)
        ]
        row = {
            "epoch": epoch,
            "train": _summarize(train_rows),
            "validation": _summarize(validation_rows),
        }
        history.append(row)
        if row["validation"]["loss"] < best_loss:
            best_loss = row["validation"]["loss"]
            # msgpack strict mode cannot serialize Flax FrozenDict directly.
            best_params = unfreeze(jax.device_get(state.params))
            output_payload = {
                "params": best_params,
                "model_id": "v114_day_smdp_hmoe_latent_role_awr_v8",
                "architecture": V6_ARCHITECTURE,
                "strategy_parent": None,
                "optimization_init": {
                    "model_id": V6_MODEL_ID,
                    "checkpoint_sha256": checkpoint_sha,
                    "role": "frozen_initialization_and_kl_anchor_only",
                },
                "optimization_init_is_strategy_wrapper": False,
                "teacher_labels_used": False,
                "action_training_source": "candidate_actual_executed_actions_only",
                "trainable_scope": "latent_action_role_decoders_and_auxiliary_value_head",
                "value_head_status": "AUXILIARY_ONLY_NOT_A_QUALIFIED_CRITIC",
                "method": "AWR",
                "ppo_qualification": False,
                "gold_qualification": False,
                "qualification_status": "TRAINING_ARTIFACT_NOT_QUALIFIED",
                "dataset_sha256": dataset_sha,
                "rollout_report_sha256": rollout_report_sha,
                "utility_contract": {
                    "own_reward_coefficient": args.own_reward_coefficient,
                    "catastrophe_penalty": args.catastrophe_penalty,
                    "catastrophe_threshold": args.catastrophe_threshold,
                    "catastrophe_weight_cap": args.catastrophe_weight_cap,
                    "own_reward_scale": args.own_reward_scale,
                    "normalization_strata": "option_id x opponent_layer",
                },
                "training_seed": args.seed,
                "inherits_v113_checkpoint": False,
                "online_historical_agent_fallback": False,
                "teacher_role_conditions_action_decoder": False,
            }
            with tempfile.NamedTemporaryFile("wb", dir=args.output_dir, delete=False) as sink:
                sink.write(serialization.msgpack_serialize(output_payload))
                temporary = Path(sink.name)
            temporary.replace(checkpoint_path)
        print(json.dumps(row, ensure_ascii=False), flush=True)

    frozen_delta = _max_frozen_delta(initial_params, best_params, labels)
    if frozen_delta != 0.0:
        raise RuntimeError(f"frozen V6 parameters changed: max delta={frozen_delta}")
    report = {
        "schema": "kaggriculture-v114-latent-role-awr-v8-training-v1",
        "method": "AWR",
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": sha256_file(checkpoint_path),
        "dataset": str(args.dataset),
        "dataset_sha256": dataset_sha,
        "rollout_report": str(args.rollout_report),
        "rollout_report_sha256": rollout_report_sha,
        "rows": row_count,
        "train_rows": int(len(train_indices)),
        "validation_rows": int(len(validation_indices)),
        "validation_episodes": [int(value) for value in validation_episodes],
        "optimization_init": {
            "path": str(args.v6_checkpoint),
            "sha256": checkpoint_sha,
            "model_id": V6_MODEL_ID,
            "frozen_kl_anchor": True,
            "strategy_wrapper": False,
        },
        "teacher_labels_used": False,
        "action_training_source": "candidate_actual_executed_actions_only",
        "trainable_parameter_paths": trainable_parameter_paths(initial_params),
        "frozen_parameter_max_delta": frozen_delta,
        "utility_contract": (
            "episode_return + own_reward_coefficient * "
            "clip((candidate_reward - catastrophe_threshold) / own_reward_scale, -1, 1) "
            "- catastrophe_penalty * I(candidate_reward < catastrophe_threshold)"
        ),
        "advantage_contract": (
            "average composite-utility rank, z-normalized within option_id x opponent_layer"
        ),
        "awr_weight_contract": (
            "min(exp(beta * advantage), clip), then cap catastrophe rows"
        ),
        "hyperparameters": {
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "learning_rate": args.learning_rate,
            "beta": args.beta,
            "clip": args.weight_clip,
            "kl_coefficient": args.kl_coefficient,
            "value_coefficient": args.value_coefficient,
            "own_reward_coefficient": args.own_reward_coefficient,
            "catastrophe_penalty": args.catastrophe_penalty,
            "catastrophe_threshold": args.catastrophe_threshold,
            "catastrophe_weight_cap": args.catastrophe_weight_cap,
            "own_reward_scale": args.own_reward_scale,
            "seed": args.seed,
        },
        "best_validation_loss": best_loss,
        "history": history,
        "group_accuracy_contract": {
            "high_return": "rank-standardized advantage > 0",
            "low_return": "rank-standardized advantage < 0",
            "ties_at_option_center": "excluded from both groups",
        },
        "value_head_status": "AUXILIARY_ONLY_NOT_A_QUALIFIED_CRITIC",
        "ppo_qualification": False,
        "gold_qualification": False,
        "qualification_status": "TRAINING_ARTIFACT_NOT_QUALIFIED",
        "elapsed_seconds": time.time() - started,
    }
    (args.output_dir / "training_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "checkpoint": str(checkpoint_path),
                "checkpoint_sha256": report["checkpoint_sha256"],
                "best_validation_loss": best_loss,
                "frozen_parameter_max_delta": frozen_delta,
                "qualification_status": report["qualification_status"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
