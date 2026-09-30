"""Full-information clipped PPO for the V114 production-route Router."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import time
from typing import Any, Mapping

from flax import serialization
from flax.training.train_state import TrainState
import jax
import jax.numpy as jnp
import numpy as np
import optax

from event_ppo_math import masked_categorical_entropy, masked_categorical_kl
from model_event_program_ppo import EventProgramPPOManager, validate_checkpoint_metadata
from train_event_program_headwise_ppo import parameter_root_changes
from train_event_program_ppo import atomic_checkpoint, atomic_json, file_sha256


SCHEMA = "kaggriculture-v114-counterfactual-route-ppo-training-v1"
METHOD = "full_information_counterfactual_route_ppo_v1"


def route_utility(
    score: np.ndarray,
    own: np.ndarray,
    opponent: np.ndarray,
    catastrophe: np.ndarray,
) -> np.ndarray:
    outcome = np.where(score == 1.0, 1.0, np.where(score == 0.5, 0.0, -1.0))
    relative = 2.0 * own / np.maximum(own + opponent, 1.0) - 1.0
    economy = 0.1 * np.tanh((own - 3000.0) / 10000.0)
    return outcome + relative + economy - catastrophe.astype(np.float32)


def normalize_utility_by_layer(
    utility: np.ndarray,
    mask: np.ndarray,
    layers: np.ndarray,
) -> tuple[np.ndarray, dict[str, dict[str, float | int]]]:
    """Equalize counterfactual advantage scale across opponent layers."""

    utility = np.asarray(utility, dtype=np.float32)
    mask = np.asarray(mask, dtype=np.bool_)
    layers = np.asarray(layers).astype(str)
    if utility.shape != mask.shape or utility.shape[0] != layers.shape[0]:
        raise ValueError("utility, mask and layer arrays have incompatible shapes")
    normalized = np.zeros_like(utility, dtype=np.float32)
    report: dict[str, dict[str, float | int]] = {}
    valid_count = np.maximum(mask.sum(axis=1, keepdims=True), 1)
    row_mean = np.sum(np.where(mask, utility, 0.0), axis=1, keepdims=True) / valid_count
    centered = np.where(mask, utility - row_mean, 0.0)
    for layer in sorted(set(layers.tolist())):
        rows = layers == layer
        active = centered[rows][mask[rows]]
        if active.size == 0:
            raise ValueError(f"opponent layer has no active counterfactual actions: {layer}")
        scale = max(float(np.std(active)), 1.0e-6)
        normalized[rows] = np.where(mask[rows], centered[rows] / scale, 0.0)
        report[layer] = {
            "contexts": int(np.sum(rows)),
            "active_route_values": int(active.size),
            "centered_advantage_std": float(np.std(active)),
            "normalization_scale": scale,
        }
    return normalized, report


def masked_probabilities(logits: jnp.ndarray, mask: jnp.ndarray) -> jnp.ndarray:
    masked = jnp.where(mask, logits, -jnp.inf)
    return jax.nn.softmax(masked, axis=-1)


def counterfactual_actor_loss(
    new_logits: jnp.ndarray,
    old_logits: jnp.ndarray,
    mask: jnp.ndarray,
    utility: jnp.ndarray,
    *,
    clip_epsilon: float,
    entropy_coefficient: float,
) -> tuple[jnp.ndarray, dict[str, jnp.ndarray]]:
    old_probability = jax.lax.stop_gradient(masked_probabilities(old_logits, mask))
    new_probability = masked_probabilities(new_logits, mask)
    baseline = jnp.sum(old_probability * utility, axis=-1, keepdims=True)
    advantage = jax.lax.stop_gradient(utility - baseline)
    ratio = new_probability / jnp.maximum(old_probability, 1.0e-12)
    clipped_ratio = jnp.clip(ratio, 1.0 - clip_epsilon, 1.0 + clip_epsilon)
    surrogate = jnp.minimum(ratio * advantage, clipped_ratio * advantage)
    objective = jnp.mean(jnp.sum(old_probability * surrogate, axis=-1))
    entropy = jnp.mean(masked_categorical_entropy(new_logits, mask))
    exact_kl = jnp.mean(masked_categorical_kl(old_logits, new_logits, mask))
    expected_old = jnp.mean(jnp.sum(old_probability * utility, axis=-1))
    expected_new = jnp.mean(jnp.sum(new_probability * utility, axis=-1))
    loss = -objective - entropy_coefficient * entropy
    return loss, {
        "loss": loss,
        "clipped_objective": objective,
        "entropy": entropy,
        "exact_kl": exact_kl,
        "expected_utility_old": expected_old,
        "expected_utility_new": expected_new,
        "mean_oracle_utility": jnp.mean(jnp.max(jnp.where(mask, utility, -jnp.inf), axis=-1)),
    }


def create_state(params: Mapping[str, Any], learning_rate: float) -> TrainState:
    def label(path: Any, _: Any) -> str:
        root = getattr(path[0], "key", None) if path else None
        return "train" if root == "production_line_head" else "frozen"

    labels = jax.tree_util.tree_map_with_path(label, params)
    tx = optax.multi_transform(
        {"train": optax.adam(float(learning_rate)), "frozen": optax.set_to_zero()},
        labels,
    )
    model = EventProgramPPOManager()
    return TrainState.create(apply_fn=model.apply, params=params, tx=tx)


def _batch(data: Mapping[str, np.ndarray], indices: np.ndarray) -> dict[str, jnp.ndarray]:
    return {
        key: jnp.asarray(np.asarray(data[key])[indices])
        for key in ("features", "old_logits", "mask", "utility")
    }


def _metrics(
    state: TrainState,
    data: Mapping[str, np.ndarray],
    *,
    clip_epsilon: float,
    entropy_coefficient: float,
) -> dict[str, float]:
    outputs = state.apply_fn({"params": state.params}, jnp.asarray(data["features"]))
    _, metrics = counterfactual_actor_loss(
        outputs["actor_logits"]["production_line"],
        jnp.asarray(data["old_logits"]),
        jnp.asarray(data["mask"]),
        jnp.asarray(data["utility"]),
        clip_epsilon=clip_epsilon,
        entropy_coefficient=entropy_coefficient,
    )
    return {key: float(np.asarray(jax.device_get(value))) for key, value in metrics.items()}


def train(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    checkpoint = Path(args.initial_checkpoint).expanduser().resolve()
    dataset = Path(args.dataset).expanduser().resolve()
    payload = serialization.msgpack_restore(checkpoint.read_bytes())
    validate_checkpoint_metadata(payload)
    source = dict(np.load(dataset, allow_pickle=False))
    required = {
        "features", "mask_production_line", "old_logits_production_line",
        "candidate_reward", "opponent_reward", "score", "catastrophe",
    }
    if not required.issubset(source):
        raise ValueError(f"dataset missing fields: {sorted(required.difference(source))}")
    raw_utility = route_utility(
        source["score"], source["candidate_reward"], source["opponent_reward"], source["catastrophe"]
    )
    mask = source["mask_production_line"].astype(np.bool_)
    raw_utility = np.where(mask, raw_utility, 0.0).astype(np.float32)
    normalization_report: dict[str, dict[str, float | int]] = {}
    if bool(args.normalize_by_layer):
        if "layer" not in source:
            raise ValueError("layer-normalized training requires dataset layer labels")
        utility, normalization_report = normalize_utility_by_layer(
            raw_utility, mask, source["layer"]
        )
    else:
        utility = raw_utility
    data = {
        "features": source["features"].astype(np.float32),
        "old_logits": source["old_logits_production_line"].astype(np.float32),
        "mask": mask,
        "utility": utility,
    }
    initial_params = deepcopy(payload["params"])
    state = create_state(initial_params, float(args.learning_rate))
    pre = _metrics(
        state, data, clip_epsilon=args.clip_epsilon,
        entropy_coefficient=args.entropy_coefficient,
    )
    if abs(pre["exact_kl"]) > 1.0e-6:
        raise ValueError("counterfactual dataset is not on-policy for initial checkpoint")

    rng = np.random.default_rng(int(args.seed))
    history: list[dict[str, Any]] = []
    global_minibatch = 0
    stop_reason = "max_epochs_under_minimum_kl"
    rollback: dict[str, Any] | None = None
    done = False
    for epoch in range(1, int(args.max_epochs) + 1):
        order = np.arange(len(data["features"])); rng.shuffle(order)
        for start in range(0, len(order), int(args.minibatch_size)):
            indices = order[start:start + int(args.minibatch_size)]
            batch = _batch(data, indices)

            def loss_fn(params: Any) -> tuple[jnp.ndarray, dict[str, jnp.ndarray]]:
                logits = state.apply_fn({"params": params}, batch["features"])["actor_logits"]["production_line"]
                return counterfactual_actor_loss(
                    logits, batch["old_logits"], batch["mask"], batch["utility"],
                    clip_epsilon=args.clip_epsilon,
                    entropy_coefficient=args.entropy_coefficient,
                )

            last_safe = state
            (_, _), gradients = jax.value_and_grad(loss_fn, has_aux=True)(state.params)
            candidate = state.apply_gradients(grads=gradients)
            global_minibatch += 1
            metrics = _metrics(
                candidate, data, clip_epsilon=args.clip_epsilon,
                entropy_coefficient=args.entropy_coefficient,
            )
            if not np.isfinite(metrics["exact_kl"]) or metrics["exact_kl"] > args.max_exact_kl:
                state = last_safe
                rollback = {"epoch": epoch, "global_minibatch": global_minibatch, "attempted_exact_kl": metrics["exact_kl"], "full_train_state_restored": True}
                stop_reason = "trust_region_overshoot_rolled_back"
                done = True
                break
            state = candidate
            if epoch >= int(args.min_epochs) and metrics["exact_kl"] >= args.min_exact_kl:
                stop_reason = "minimum_exact_kl_reached"
                done = True
                break
        epoch_metrics = _metrics(
            state, data, clip_epsilon=args.clip_epsilon,
            entropy_coefficient=args.entropy_coefficient,
        )
        history.append({"epoch": epoch, "global_minibatches": global_minibatch, **epoch_metrics})
        if done:
            break

    post = _metrics(
        state, data, clip_epsilon=args.clip_epsilon,
        entropy_coefficient=args.entropy_coefficient,
    )
    qualified = bool(args.min_exact_kl <= post["exact_kl"] <= args.max_exact_kl)
    root_changes = parameter_root_changes(initial_params, state.params)
    if root_changes.get("production_line_head", 0.0) <= 0:
        raise RuntimeError("production line head did not change")
    if any(value != 0.0 for root, value in root_changes.items() if root != "production_line_head"):
        raise RuntimeError("counterfactual route PPO changed a frozen parameter root")

    old_p = np.asarray(masked_probabilities(jnp.asarray(data["old_logits"]), jnp.asarray(mask)))
    new_logits = np.asarray(state.apply_fn({"params": state.params}, jnp.asarray(data["features"]))["actor_logits"]["production_line"])
    new_p = np.asarray(masked_probabilities(jnp.asarray(new_logits), jnp.asarray(mask)))
    uniforms = np.random.default_rng(int(args.seed) + 3001).random(len(mask))
    sample = lambda p: np.sum(uniforms[:, None] > np.cumsum(p, axis=1), axis=1)
    behavior = {
        "mean_total_variation": float(np.mean(0.5 * np.sum(np.abs(new_p - old_p), axis=1))),
        "greedy_changed_contexts": int(np.sum(np.argmax(new_p, axis=1) != np.argmax(old_p, axis=1))),
        "fixed_uniform_changed_contexts": int(np.sum(sample(new_p) != sample(old_p))),
        "fixed_uniform_seed": int(args.seed) + 3001,
        "mean_old_probability": old_p.mean(axis=0).tolist(),
        "mean_new_probability": new_p.mean(axis=0).tolist(),
    }

    output_payload = {key: value for key, value in payload.items() if key != "params"}
    method = str(args.method)
    output_payload.update({
        "params": deepcopy(state.params), "PPO": True, "training_method": method,
        "training_initial_checkpoint_sha256": file_sha256(checkpoint),
        "training_dataset_sha256": file_sha256(dataset), "training_seed": int(args.seed),
        "iteration": int(args.iteration), "strategy_parent": None, "parent_checkpoint_sha256": None,
    })
    validate_checkpoint_metadata(output_payload)
    output = Path(args.output).expanduser().resolve()
    checkpoint_sha = atomic_checkpoint(output, output_payload)
    report = {
        "schema": SCHEMA, "status": "COMPLETE" if qualified else "INCOMPLETE_KL_CONTRACT",
        "PPO": True, "training_method": method, "stop_reason": stop_reason,
        "qualified_training_contract": qualified, "pre": pre, "post": post,
        "history": history, "rollback": rollback, "parameter_root_max_abs_changes": root_changes,
        "behavior": behavior,
        "advantage_normalization": {
            "enabled": bool(args.normalize_by_layer),
            "method": "per_context_center_then_opponent_layer_std" if args.normalize_by_layer else "none",
            "layers": normalization_report,
        },
        "hyperparameters": {
            "seed": int(args.seed), "max_epochs": int(args.max_epochs), "min_epochs": int(args.min_epochs),
            "minibatch_size": int(args.minibatch_size), "learning_rate": float(args.learning_rate),
            "clip_epsilon": float(args.clip_epsilon), "entropy_coefficient": float(args.entropy_coefficient),
            "min_exact_kl": float(args.min_exact_kl), "max_exact_kl": float(args.max_exact_kl),
        },
        "dataset": {"path": str(dataset), "sha256": file_sha256(dataset), "contexts": len(mask)},
        "initial_checkpoint": {"path": str(checkpoint), "sha256": file_sha256(checkpoint)},
        "checkpoint": {"path": str(output), "sha256": checkpoint_sha},
        "elapsed_seconds": time.time() - started,
    }
    atomic_json(Path(args.report).expanduser().resolve(), report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--initial-checkpoint", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--seed", type=int, default=115410)
    parser.add_argument("--max-epochs", type=int, default=64)
    parser.add_argument("--min-epochs", type=int, default=2)
    parser.add_argument("--minibatch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=1.0e-5)
    parser.add_argument("--clip-epsilon", type=float, default=0.1)
    parser.add_argument("--entropy-coefficient", type=float, default=0.01)
    parser.add_argument("--min-exact-kl", type=float, default=0.002)
    parser.add_argument("--max-exact-kl", type=float, default=0.01)
    parser.add_argument("--normalize-by-layer", action="store_true")
    parser.add_argument("--iteration", type=int, default=4)
    parser.add_argument("--method", default=METHOD)
    return parser


if __name__ == "__main__":
    result = train(build_parser().parse_args())
    print(json.dumps({key: result[key] for key in ("status", "stop_reason", "post", "behavior", "checkpoint")}, indent=2))
