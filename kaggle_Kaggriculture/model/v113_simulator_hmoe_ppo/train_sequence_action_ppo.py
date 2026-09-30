"""PPO update for the executed-prefix joint sequence action model."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import time

from flax import serialization, traverse_util
from flax.training.train_state import TrainState
import jax
import jax.numpy as jnp
import numpy as np
import optax

from model_sequence_action import HIDDEN, NUM_EXPERTS, SequenceActionHMoEActorCritic
from train_factorized_ppo import categorical_stats, clipped_loss


MODEL_KEYS = ("global", "board", "units", "unit_mask")
BATCH_KEYS = MODEL_KEYS + (
    "unit_expert", "market_expert", "unit_tokens", "unit_quantities",
    "unit_action_masks", "unit_logprobs", "unit_quantity_logprobs",
    "unit_quantity_mask", "unit_quantity_masks", "market_tokens",
    "market_quantities", "market_action_masks", "market_slot_mask",
    "market_logprobs", "market_quantity_logprobs", "market_quantity_mask",
    "market_quantity_masks", "value_prediction", "advantage", "return_target",
)
HISTORY_INPUT_PARAMETER = ("own_global_dense", "kernel")
PROJECTION_MODULES = {
    "both": {"unit_expert_projection", "market_expert_projection"},
    "unit": {"unit_expert_projection"},
    "market": {"market_expert_projection"},
}
MARKET_MEMORY_MODULE = "market_memory_dense"


def mask_history_input_gradients(gradients, history_features: int):
    """Keep gradients only for the appended history rows of own_global_dense."""
    flat = traverse_util.flatten_dict(gradients)
    if HISTORY_INPUT_PARAMETER not in flat:
        raise ValueError(f"missing history input parameter: {HISTORY_INPUT_PARAMETER}")
    kernel = flat[HISTORY_INPUT_PARAMETER]
    if kernel.ndim != 2 or not 0 < history_features < kernel.shape[0]:
        raise ValueError(
            f"invalid history feature count {history_features} for kernel {kernel.shape}"
        )
    masked = {path: jnp.zeros_like(value) for path, value in flat.items()}
    row_mask = (jnp.arange(kernel.shape[0]) >= kernel.shape[0] - history_features)[:, None]
    masked[HISTORY_INPUT_PARAMETER] = kernel * row_mask
    return traverse_util.unflatten_dict(masked)


def audit_history_input_scope(before, after, history_features: int) -> dict:
    """Prove that a residual update changed only appended history kernel rows."""
    before_flat = traverse_util.flatten_dict(before)
    after_flat = traverse_util.flatten_dict(after)
    if set(before_flat) != set(after_flat):
        raise ValueError("parameter tree changed during history-only update")
    changed_paths = []
    non_target_exact = True
    for path in sorted(before_flat):
        old = np.asarray(before_flat[path])
        new = np.asarray(after_flat[path])
        if old.shape != new.shape:
            raise ValueError(f"parameter shape changed at {path}: {old.shape} -> {new.shape}")
        if not np.array_equal(old, new):
            changed_paths.append("/".join(path))
            if path != HISTORY_INPUT_PARAMETER:
                non_target_exact = False
    old_kernel = np.asarray(before_flat[HISTORY_INPUT_PARAMETER])
    new_kernel = np.asarray(after_flat[HISTORY_INPUT_PARAMETER])
    split = old_kernel.shape[0] - history_features
    old_rows_exact = bool(np.array_equal(old_kernel[:split], new_kernel[:split]))
    history_delta = new_kernel[split:] - old_kernel[split:]
    report = {
        "target_parameter": "/".join(HISTORY_INPUT_PARAMETER),
        "base_input_rows": split,
        "history_input_rows": history_features,
        "changed_parameter_paths": changed_paths,
        "non_target_parameters_bitwise_equal": non_target_exact,
        "base_input_rows_bitwise_equal": old_rows_exact,
        "history_delta_l2": float(np.linalg.norm(history_delta)),
        "history_changed_elements": int(np.count_nonzero(history_delta)),
    }
    report["passed"] = bool(
        non_target_exact
        and old_rows_exact
        and changed_paths == ["/".join(HISTORY_INPUT_PARAMETER)]
        and report["history_delta_l2"] > 0.0
    )
    return report


def mask_expert_slot_gradients(gradients, scope: str, expert_slot: int):
    """Keep gradients only for one expert slice in selected projection modules."""
    if scope not in PROJECTION_MODULES:
        raise ValueError(f"unknown expert projection scope: {scope}")
    if expert_slot not in range(NUM_EXPERTS):
        raise ValueError(f"expert slot outside [0,{NUM_EXPERTS}): {expert_slot}")
    start, stop = expert_slot * HIDDEN, (expert_slot + 1) * HIDDEN
    flat = traverse_util.flatten_dict(gradients)
    masked = {path: jnp.zeros_like(value) for path, value in flat.items()}
    found = set()
    for module in PROJECTION_MODULES[scope]:
        for field in ("kernel", "bias"):
            path = (module, field)
            if path not in flat:
                raise ValueError(f"missing expert projection parameter: {path}")
            value = flat[path]
            axis_size = value.shape[-1]
            if axis_size != NUM_EXPERTS * HIDDEN:
                raise ValueError(f"unexpected projection shape at {path}: {value.shape}")
            slot_mask = (jnp.arange(axis_size) >= start) & (jnp.arange(axis_size) < stop)
            masked[path] = value * slot_mask
            found.add(path)
    if not found:
        raise ValueError("expert slot scope selected no parameters")
    return traverse_util.unflatten_dict(masked)


def audit_expert_slot_scope(before, after, scope: str, expert_slot: int) -> dict:
    """Prove that only one selected expert projection slice changed."""
    if scope not in PROJECTION_MODULES:
        raise ValueError(f"unknown expert projection scope: {scope}")
    if expert_slot not in range(NUM_EXPERTS):
        raise ValueError(f"expert slot outside [0,{NUM_EXPERTS}): {expert_slot}")
    before_flat = traverse_util.flatten_dict(before)
    after_flat = traverse_util.flatten_dict(after)
    if set(before_flat) != set(after_flat):
        raise ValueError("parameter tree changed during expert-slot update")
    start, stop = expert_slot * HIDDEN, (expert_slot + 1) * HIDDEN
    target_modules = PROJECTION_MODULES[scope]
    changed_paths = []
    outside_exact = True
    target_delta_l2 = 0.0
    target_changed_elements = 0
    for path in sorted(before_flat):
        old = np.asarray(before_flat[path])
        new = np.asarray(after_flat[path])
        if old.shape != new.shape:
            raise ValueError(f"parameter shape changed at {path}: {old.shape} -> {new.shape}")
        if np.array_equal(old, new):
            continue
        changed_paths.append("/".join(path))
        if len(path) != 2 or path[0] not in target_modules or path[1] not in {"kernel", "bias"}:
            outside_exact = False
            continue
        old_outside = np.concatenate((old[..., :start].ravel(), old[..., stop:].ravel()))
        new_outside = np.concatenate((new[..., :start].ravel(), new[..., stop:].ravel()))
        if not np.array_equal(old_outside, new_outside):
            outside_exact = False
        delta = new[..., start:stop] - old[..., start:stop]
        target_delta_l2 += float(np.sum(delta.astype(np.float64) ** 2))
        target_changed_elements += int(np.count_nonzero(delta))
    target_delta_l2 = float(np.sqrt(target_delta_l2))
    report = {
        "projection_scope": scope,
        "expert_slot": expert_slot,
        "slot_start": start,
        "slot_stop": stop,
        "changed_parameter_paths": changed_paths,
        "outside_target_slot_bitwise_equal": outside_exact,
        "target_delta_l2": target_delta_l2,
        "target_changed_elements": target_changed_elements,
    }
    report["passed"] = bool(outside_exact and target_delta_l2 > 0.0)
    return report


def audit_expert_projection_scope(before, after, scope: str) -> dict:
    """Prove that a full projection-only update touched no other parameters."""
    if scope not in PROJECTION_MODULES:
        raise ValueError(f"unknown expert projection scope: {scope}")
    before_flat = traverse_util.flatten_dict(before)
    after_flat = traverse_util.flatten_dict(after)
    if set(before_flat) != set(after_flat):
        raise ValueError("parameter tree changed during expert-projection update")
    target_modules = PROJECTION_MODULES[scope]
    expected_paths = {
        (module, field)
        for module in target_modules
        for field in ("kernel", "bias")
    }
    changed_paths = []
    outside_exact = True
    target_delta_l2 = 0.0
    target_changed_elements = 0
    changed_target_paths = set()
    for path in sorted(before_flat):
        old = np.asarray(before_flat[path])
        new = np.asarray(after_flat[path])
        if old.shape != new.shape:
            raise ValueError(f"parameter shape changed at {path}: {old.shape} -> {new.shape}")
        if np.array_equal(old, new):
            continue
        changed_paths.append("/".join(path))
        if path not in expected_paths:
            outside_exact = False
            continue
        changed_target_paths.add(path)
        delta = new - old
        target_delta_l2 += float(np.sum(delta.astype(np.float64) ** 2))
        target_changed_elements += int(np.count_nonzero(delta))
    target_delta_l2 = float(np.sqrt(target_delta_l2))
    report = {
        "projection_scope": scope,
        "changed_parameter_paths": changed_paths,
        "expected_target_paths": ["/".join(path) for path in sorted(expected_paths)],
        "changed_target_paths": ["/".join(path) for path in sorted(changed_target_paths)],
        "non_target_parameters_bitwise_equal": outside_exact,
        "target_delta_l2": target_delta_l2,
        "target_changed_elements": target_changed_elements,
    }
    report["passed"] = bool(
        outside_exact
        and changed_target_paths == expected_paths
        and target_delta_l2 > 0.0
    )
    return report


def mask_market_memory_expert_gradients(gradients, expert_slot: int):
    """Train the market-memory encoder and exactly one market expert slice."""
    flat = traverse_util.flatten_dict(gradients)
    masked = {path: jnp.zeros_like(value) for path, value in flat.items()}
    for field in ("kernel", "bias"):
        path = (MARKET_MEMORY_MODULE, field)
        if path not in flat:
            raise ValueError(f"missing market memory parameter: {path}")
        masked[path] = flat[path]
    projection = mask_expert_slot_gradients(gradients, "market", expert_slot)
    projection_flat = traverse_util.flatten_dict(projection)
    for path in (("market_expert_projection", "kernel"), ("market_expert_projection", "bias")):
        masked[path] = projection_flat[path]
    return traverse_util.unflatten_dict(masked)


def audit_market_memory_expert_scope(before, after, expert_slot: int) -> dict:
    """Prove that only market memory and one market projection slice changed."""
    before_flat = traverse_util.flatten_dict(before)
    after_flat = traverse_util.flatten_dict(after)
    if set(before_flat) != set(after_flat):
        raise ValueError("parameter tree changed during market-memory expert update")
    start, stop = expert_slot * HIDDEN, (expert_slot + 1) * HIDDEN
    memory_paths = {(MARKET_MEMORY_MODULE, "kernel"), (MARKET_MEMORY_MODULE, "bias")}
    projection_paths = {
        ("market_expert_projection", "kernel"),
        ("market_expert_projection", "bias"),
    }
    outside_exact = True
    changed_paths = []
    memory_delta_sq = projection_delta_sq = 0.0
    for path in sorted(before_flat):
        old, new = np.asarray(before_flat[path]), np.asarray(after_flat[path])
        if old.shape != new.shape:
            raise ValueError(f"parameter shape changed at {path}: {old.shape} -> {new.shape}")
        if np.array_equal(old, new):
            continue
        changed_paths.append("/".join(path))
        if path in memory_paths:
            memory_delta_sq += float(np.sum((new - old).astype(np.float64) ** 2))
        elif path in projection_paths:
            old_outside = np.concatenate((old[..., :start].ravel(), old[..., stop:].ravel()))
            new_outside = np.concatenate((new[..., :start].ravel(), new[..., stop:].ravel()))
            if not np.array_equal(old_outside, new_outside):
                outside_exact = False
            projection_delta_sq += float(np.sum(
                (new[..., start:stop] - old[..., start:stop]).astype(np.float64) ** 2
            ))
        else:
            outside_exact = False
    report = {
        "expert_slot": expert_slot,
        "changed_parameter_paths": changed_paths,
        "outside_market_memory_and_target_slot_bitwise_equal": outside_exact,
        "market_memory_delta_l2": float(np.sqrt(memory_delta_sq)),
        "market_projection_slot_delta_l2": float(np.sqrt(projection_delta_sq)),
    }
    report["passed"] = bool(
        outside_exact
        and report["market_memory_delta_l2"] > 0.0
        and report["market_projection_slot_delta_l2"] > 0.0
    )
    return report


def mask_market_memory_coordinated_gradients(gradients, expert_slot: int):
    """Train market memory plus matching unit and market expert slices."""
    flat = traverse_util.flatten_dict(gradients)
    masked = {path: jnp.zeros_like(value) for path, value in flat.items()}
    for field in ("kernel", "bias"):
        masked[(MARKET_MEMORY_MODULE, field)] = flat[(MARKET_MEMORY_MODULE, field)]
    projections = traverse_util.flatten_dict(
        mask_expert_slot_gradients(gradients, "both", expert_slot)
    )
    for module in ("unit_expert_projection", "market_expert_projection"):
        for field in ("kernel", "bias"):
            masked[(module, field)] = projections[(module, field)]
    return traverse_util.unflatten_dict(masked)


def audit_market_memory_coordinated_scope(before, after, expert_slot: int) -> dict:
    """Prove exact isolation to memory and paired unit/market expert slices."""
    before_flat = traverse_util.flatten_dict(before)
    after_flat = traverse_util.flatten_dict(after)
    start, stop = expert_slot * HIDDEN, (expert_slot + 1) * HIDDEN
    memory_paths = {(MARKET_MEMORY_MODULE, "kernel"), (MARKET_MEMORY_MODULE, "bias")}
    projection_paths = {
        (module, field)
        for module in ("unit_expert_projection", "market_expert_projection")
        for field in ("kernel", "bias")
    }
    outside_exact = True
    memory_sq = unit_sq = market_sq = 0.0
    changed_paths = []
    for path in sorted(before_flat):
        old, new = np.asarray(before_flat[path]), np.asarray(after_flat[path])
        if old.shape != new.shape:
            raise ValueError(f"parameter shape changed at {path}: {old.shape} -> {new.shape}")
        if np.array_equal(old, new):
            continue
        changed_paths.append("/".join(path))
        if path in memory_paths:
            memory_sq += float(np.sum((new - old).astype(np.float64) ** 2))
        elif path in projection_paths:
            if not np.array_equal(
                np.concatenate((old[..., :start].ravel(), old[..., stop:].ravel())),
                np.concatenate((new[..., :start].ravel(), new[..., stop:].ravel())),
            ):
                outside_exact = False
            delta = new[..., start:stop] - old[..., start:stop]
            if path[0] == "unit_expert_projection":
                unit_sq += float(np.sum(delta.astype(np.float64) ** 2))
            else:
                market_sq += float(np.sum(delta.astype(np.float64) ** 2))
        else:
            outside_exact = False
    report = {
        "expert_slot": expert_slot,
        "changed_parameter_paths": changed_paths,
        "outside_memory_and_paired_slots_bitwise_equal": outside_exact,
        "market_memory_delta_l2": float(np.sqrt(memory_sq)),
        "unit_projection_slot_delta_l2": float(np.sqrt(unit_sq)),
        "market_projection_slot_delta_l2": float(np.sqrt(market_sq)),
    }
    report["passed"] = bool(
        outside_exact and all(report[key] > 0.0 for key in (
            "market_memory_delta_l2", "unit_projection_slot_delta_l2",
            "market_projection_slot_delta_l2",
        ))
    )
    return report


def make_loss(clip, value_coef, entropy_coef, worker_temperature, ratio_mode):
    def loss_fn(params, apply_fn, batch):
        output = apply_fn(
            {"params": params}, *(batch[key] for key in MODEL_KEYS),
            batch["unit_tokens"], batch["unit_quantities"],
            batch["market_tokens"], batch["market_quantities"],
        )
        index = jnp.arange(batch["unit_expert"].shape[0])
        unit_expert = batch["unit_expert"].astype(jnp.int32)
        market_expert = batch["market_expert"].astype(jnp.int32)
        unit_logits = output["unit_logits"][index, unit_expert] / worker_temperature
        unit_quantity_logits = output["unit_quantity_logits"][index, unit_expert] / worker_temperature
        market_logits = output["market_logits"][index, market_expert] / worker_temperature
        market_quantity_logits = output["market_quantity_logits"][index, market_expert] / worker_temperature
        unit_logprob, unit_entropy = categorical_stats(
            unit_logits, batch["unit_tokens"], batch["unit_action_masks"]
        )
        unit_quantity_logprob, unit_quantity_entropy = categorical_stats(
            unit_quantity_logits, batch["unit_quantities"], batch["unit_quantity_masks"]
        )
        market_logprob, market_entropy = categorical_stats(
            market_logits, batch["market_tokens"], batch["market_action_masks"]
        )
        market_quantity_logprob, market_quantity_entropy = categorical_stats(
            market_quantity_logits, batch["market_quantities"], batch["market_quantity_masks"]
        )
        advantage = batch["advantage"]
        if ratio_mode == "joint":
            new_unit_total = jnp.sum(
                unit_logprob * batch["unit_mask"]
                + unit_quantity_logprob * batch["unit_quantity_mask"], axis=1
            )
            old_unit_total = jnp.sum(
                batch["unit_logprobs"] * batch["unit_mask"]
                + batch["unit_quantity_logprobs"] * batch["unit_quantity_mask"], axis=1
            )
            new_market_total = jnp.sum(
                market_logprob * batch["market_slot_mask"]
                + market_quantity_logprob * batch["market_quantity_mask"], axis=1
            )
            old_market_total = jnp.sum(
                batch["market_logprobs"] * batch["market_slot_mask"]
                + batch["market_quantity_logprobs"] * batch["market_quantity_mask"], axis=1
            )
            log_ratio = jnp.clip(
                new_unit_total + new_market_total - old_unit_total - old_market_total,
                -20.0, 20.0,
            )
            ratio = jnp.exp(log_ratio)
            clipped_ratio = jnp.clip(ratio, 1.0 - clip, 1.0 + clip)
            policy_loss = -jnp.mean(jnp.minimum(
                ratio * advantage, clipped_ratio * advantage
            ))
            joint_clip = jnp.mean(jnp.abs(ratio - 1.0) > clip)
            unit_clip = unit_quantity_clip = market_clip = market_quantity_clip = joint_clip
            unit_kl = jnp.mean(old_unit_total - new_unit_total)
            market_kl = jnp.mean(old_market_total - new_market_total)
            approximate_kl = jnp.mean((ratio - 1.0) - log_ratio)
            max_abs_log_ratio = jnp.max(jnp.abs(log_ratio))
        else:
            unit_loss, unit_clip = clipped_loss(
                unit_logprob, batch["unit_logprobs"], advantage[:, None],
                batch["unit_mask"], clip,
            )
            unit_quantity_loss, unit_quantity_clip = clipped_loss(
                unit_quantity_logprob, batch["unit_quantity_logprobs"], advantage[:, None],
                batch["unit_quantity_mask"], clip,
            )
            market_loss, market_clip = clipped_loss(
                market_logprob, batch["market_logprobs"], advantage[:, None],
                batch["market_slot_mask"], clip,
            )
            market_quantity_loss, market_quantity_clip = clipped_loss(
                market_quantity_logprob, batch["market_quantity_logprobs"], advantage[:, None],
                batch["market_quantity_mask"], clip,
            )
            policy_loss = (
                unit_loss + 0.15 * unit_quantity_loss
                + market_loss + 0.15 * market_quantity_loss
            )
            unit_kl = jnp.sum(
                (batch["unit_logprobs"] - unit_logprob) * batch["unit_mask"]
            ) / jnp.maximum(1.0, jnp.sum(batch["unit_mask"]))
            market_kl = jnp.sum(
                (batch["market_logprobs"] - market_logprob) * batch["market_slot_mask"]
            ) / jnp.maximum(1.0, jnp.sum(batch["market_slot_mask"]))
            approximate_kl = unit_kl + market_kl
            max_abs_log_ratio = jnp.asarray(0.0)
        old_value = batch["value_prediction"]
        clipped_value = old_value + jnp.clip(output["value"] - old_value, -clip, clip)
        value_loss = 0.5 * jnp.mean(jnp.maximum(
            (output["value"] - batch["return_target"]) ** 2,
            (clipped_value - batch["return_target"]) ** 2,
        ))
        entropy = (
            jnp.sum(unit_entropy * batch["unit_mask"]) / jnp.maximum(1.0, jnp.sum(batch["unit_mask"]))
            + jnp.sum(unit_quantity_entropy * batch["unit_quantity_mask"]) / jnp.maximum(1.0, jnp.sum(batch["unit_quantity_mask"]))
            + jnp.sum(market_entropy * batch["market_slot_mask"]) / jnp.maximum(1.0, jnp.sum(batch["market_slot_mask"]))
            + jnp.sum(market_quantity_entropy * batch["market_quantity_mask"]) / jnp.maximum(1.0, jnp.sum(batch["market_quantity_mask"]))
        )
        total = policy_loss + value_coef * value_loss - entropy_coef * entropy
        return total, {
            "loss": total, "policy_loss": policy_loss, "value_loss": value_loss,
            "entropy": entropy, "approximate_kl": approximate_kl,
            "unit_kl": unit_kl, "market_kl": market_kl,
            "max_abs_log_ratio": max_abs_log_ratio,
            "clip_fraction": (
                unit_clip + unit_quantity_clip + market_clip + market_quantity_clip
            ) / 4,
        }
    return loss_fn


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--rollouts", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--learning-rate", type=float, default=1e-5)
    parser.add_argument("--clip", type=float, default=0.1)
    parser.add_argument("--target-kl", type=float, default=0.01)
    parser.add_argument("--worker-temperature", type=float, default=0.2)
    parser.add_argument("--value-coef", type=float, default=0.01)
    parser.add_argument("--entropy-coef", type=float, default=0.0001)
    parser.add_argument("--seed", type=int, default=1194001)
    parser.add_argument("--timed", action="store_true")
    parser.add_argument("--ratio-mode", choices=("token", "joint"), default="joint")
    parser.add_argument(
        "--train-expert-projections-only", action="store_true",
        help="Freeze the shared trunk/decoder and specialize only selected expert projections.",
    )
    parser.add_argument(
        "--expert-projection-scope", choices=("both", "unit", "market"), default="both",
        help="Projection subset to train when --train-expert-projections-only is enabled.",
    )
    parser.add_argument(
        "--expert-slot-index", type=int,
        help="With --train-expert-projections-only, update only this expert projection slice.",
    )
    parser.add_argument(
        "--train-history-input-only", action="store_true",
        help="Train only the appended history rows of own_global_dense/kernel.",
    )
    parser.add_argument("--history-feature-count", type=int, default=32)
    parser.add_argument("--market-memory-features", type=int, default=0)
    parser.add_argument(
        "--train-market-memory-expert", action="store_true",
        help="Train market_memory_dense plus one selected market expert slice.",
    )
    parser.add_argument(
        "--train-market-memory-coordinated-expert", action="store_true",
        help="Train market memory plus matching unit and market expert slices.",
    )
    args = parser.parse_args()
    restricted_modes = sum((
        args.train_history_input_only, args.train_expert_projections_only,
        args.train_market_memory_expert,
        args.train_market_memory_coordinated_expert,
    ))
    if restricted_modes > 1:
        parser.error("restricted training modes are mutually exclusive")
    if args.expert_slot_index is not None and not (
        args.train_expert_projections_only or args.train_market_memory_expert
        or args.train_market_memory_coordinated_expert
    ):
        parser.error("--expert-slot-index requires an expert-restricted training mode")
    if args.train_market_memory_expert and (
        args.expert_slot_index is None or args.market_memory_features <= 0
        or args.expert_projection_scope != "market"
    ):
        parser.error("market-memory expert requires features, a slot, and market scope")
    if args.train_market_memory_coordinated_expert and (
        args.expert_slot_index is None or args.market_memory_features <= 0
        or args.expert_projection_scope != "both"
    ):
        parser.error("coordinated memory expert requires features, a slot, and both scope")
    if args.expert_slot_index is not None and args.expert_slot_index not in range(NUM_EXPERTS):
        parser.error(f"--expert-slot-index must be in [0,{NUM_EXPERTS})")
    started = time.time()
    payload = serialization.msgpack_restore(args.checkpoint.read_bytes())
    with np.load(args.rollouts) as archive:
        data = {key: archive[key] for key in archive.files}
    rollout_report_path = args.rollouts.with_suffix(".json")
    if not rollout_report_path.exists():
        raise ValueError(f"missing rollout contract sidecar: {rollout_report_path}")
    rollout_report = json.loads(rollout_report_path.read_text(encoding="utf-8"))
    rollout_temperature = rollout_report.get("worker_temperature")
    if rollout_temperature is None:
        raise ValueError("rollout sidecar is missing worker_temperature")
    if not np.isclose(float(rollout_temperature), args.worker_temperature, rtol=0.0, atol=1e-12):
        raise ValueError(
            "rollout/trainer worker temperature mismatch: "
            f"{rollout_temperature} != {args.worker_temperature}"
        )
    if int(rollout_report.get("rejected_games", 0)):
        raise ValueError("rollout sidecar reports rejected abnormal games")
    missing = set(BATCH_KEYS) - set(data)
    if missing:
        raise ValueError(f"rollouts missing sequence PPO keys: {sorted(missing)}")
    model = SequenceActionHMoEActorCritic(
        timed=args.timed, market_memory_features=args.market_memory_features,
    )
    # AdamW would decay frozen rows inside a partially trainable matrix.  The
    # history residual scope therefore uses Adam and an explicit row mask.
    train_optimizer = optax.chain(
        optax.clip_by_global_norm(0.5),
        optax.adam(args.learning_rate) if (
            args.train_history_input_only or args.expert_slot_index is not None
        )
        else optax.adamw(args.learning_rate, weight_decay=1e-5),
    )
    flat = traverse_util.flatten_dict(payload["params"])
    if args.train_history_input_only:
        if HISTORY_INPUT_PARAMETER not in flat:
            raise ValueError(f"checkpoint lacks {HISTORY_INPUT_PARAMETER}")
        history_kernel = np.asarray(flat[HISTORY_INPUT_PARAMETER])
        if history_kernel.ndim != 2 or not 0 < args.history_feature_count < history_kernel.shape[0]:
            raise ValueError(
                f"invalid history kernel/count: {history_kernel.shape}, {args.history_feature_count}"
            )
    frozen = {"unit_router_head", "market_router_head", "opponent_prediction_head"}
    projection_modules = PROJECTION_MODULES[args.expert_projection_scope]
    if args.expert_slot_index is not None:
        expected_key = (
            "unit_expert" if args.expert_projection_scope == "unit" else
            "market_expert" if args.expert_projection_scope == "market" else None
        )
        if expected_key is not None and not np.all(
            data[expected_key] == args.expert_slot_index
        ):
            raise ValueError(
                f"rollouts contain {expected_key} values outside expert slot "
                f"{args.expert_slot_index}"
            )
        if args.train_market_memory_coordinated_expert and not (
            np.all(data["unit_expert"] == args.expert_slot_index)
            and np.all(data["market_expert"] == args.expert_slot_index)
        ):
            raise ValueError("coordinated rollouts must use the selected slot for both experts")
    labels = traverse_util.unflatten_dict({
        path: (
            "train" if args.train_market_memory_coordinated_expert and path[0] in {
                MARKET_MEMORY_MODULE, "unit_expert_projection", "market_expert_projection"
            } else (
            "freeze" if args.train_market_memory_coordinated_expert else (
            "train" if args.train_market_memory_expert and path[0] in {
                MARKET_MEMORY_MODULE, "market_expert_projection"
            } else (
            "freeze" if args.train_market_memory_expert else (
            "train" if args.train_history_input_only and path == HISTORY_INPUT_PARAMETER else (
                "freeze" if args.train_history_input_only else (
                    "train" if args.train_expert_projections_only and path[0] in projection_modules else (
                        "freeze" if args.train_expert_projections_only or path[0] in frozen
                        else "train"
                    )
                )
            )))))
        )
        for path in flat
    })
    optimizer = optax.multi_transform(
        {"train": train_optimizer, "freeze": optax.set_to_zero()}, labels
    )
    state = TrainState.create(apply_fn=model.apply, params=payload["params"], tx=optimizer)
    loss_fn = make_loss(
        args.clip, args.value_coef, args.entropy_coef, args.worker_temperature,
        args.ratio_mode,
    )

    @jax.jit
    def train_step(current, batch):
        (_, metrics), gradients = jax.value_and_grad(loss_fn, has_aux=True)(
            current.params, current.apply_fn, batch
        )
        if args.train_history_input_only:
            gradients = mask_history_input_gradients(gradients, args.history_feature_count)
        elif args.train_market_memory_coordinated_expert:
            gradients = mask_market_memory_coordinated_gradients(
                gradients, args.expert_slot_index
            )
        elif args.train_market_memory_expert:
            gradients = mask_market_memory_expert_gradients(
                gradients, args.expert_slot_index
            )
        elif args.expert_slot_index is not None:
            gradients = mask_expert_slot_gradients(
                gradients, args.expert_projection_scope, args.expert_slot_index
            )
        return current.apply_gradients(grads=gradients), metrics

    rng = np.random.default_rng(args.seed)
    indices = np.arange(len(data["advantage"]))
    history = []
    for epoch in range(1, args.epochs + 1):
        rng.shuffle(indices)
        rows = []
        for start in range(0, len(indices) - args.batch_size + 1, args.batch_size):
            selected = indices[start:start + args.batch_size]
            batch = {key: jnp.asarray(data[key][selected]) for key in BATCH_KEYS}
            state, metrics = train_step(state, batch)
            rows.append(jax.device_get(metrics))
        row = {
            "epoch": epoch,
            **{key: float(np.mean([float(item[key]) for item in rows])) for key in rows[0]},
        }
        history.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
        if row["approximate_kl"] > args.target_kl:
            break

    final_rows = []
    final_weights = []
    for start in range(0, len(indices), args.batch_size):
        selected = indices[start:start + args.batch_size]
        batch = {key: jnp.asarray(data[key][selected]) for key in BATCH_KEYS}
        _, metrics = loss_fn(state.params, state.apply_fn, batch)
        final_rows.append(jax.device_get(metrics))
        final_weights.append(len(selected))
    final_metrics = {
        key: float(np.average(
            [float(item[key]) for item in final_rows], weights=final_weights
        ))
        for key in final_rows[0]
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = args.output_dir / "ppo_checkpoint.msgpack"
    scope_audit = (
        audit_market_memory_coordinated_scope(
            payload["params"], jax.device_get(state.params), args.expert_slot_index,
        ) if args.train_market_memory_coordinated_expert else (
        audit_market_memory_expert_scope(
            payload["params"], jax.device_get(state.params), args.expert_slot_index,
        ) if args.train_market_memory_expert else (
        audit_history_input_scope(payload["params"], jax.device_get(state.params), args.history_feature_count)
        if args.train_history_input_only else (
            audit_expert_slot_scope(
                payload["params"], jax.device_get(state.params),
                args.expert_projection_scope, args.expert_slot_index,
            )
            if args.expert_slot_index is not None else (
                audit_expert_projection_scope(
                    payload["params"], jax.device_get(state.params),
                    args.expert_projection_scope,
                )
                if args.train_expert_projections_only else None
            )
        )))
    )
    if scope_audit is not None and not scope_audit["passed"]:
        raise RuntimeError(f"restricted parameter scope audit failed: {scope_audit}")
    result = {
        **{key: value for key, value in payload.items() if key != "params"},
        "params": jax.device_get(state.params),
        "architecture": (
            "market-memory36-history32-timed-action-hmoe-v1-ppo-coordinated-expert"
            if args.train_market_memory_coordinated_expert else (
            "market-memory36-history32-timed-action-hmoe-v1-ppo-expert"
            if args.train_market_memory_expert else (
            "history32-timed-joint-autoregressive-action-hmoe-v1-ppo-residual"
            if args.train_history_input_only else (
                "timed-joint-autoregressive-action-hmoe-v1-ppo-expert-slot"
                if args.expert_slot_index is not None else (
                "timed-joint-autoregressive-action-hmoe-v1-ppo"
                if args.timed else "joint-autoregressive-action-hmoe-v1-ppo"
                )
            )))
        ),
        "source_checkpoint_sha256": hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
        "rollout_sha256": hashlib.sha256(args.rollouts.read_bytes()).hexdigest(),
    }
    with tempfile.NamedTemporaryFile("wb", dir=args.output_dir, delete=False) as sink:
        sink.write(serialization.msgpack_serialize(result))
        temporary = Path(sink.name)
    temporary.replace(checkpoint_path)
    report = {
        "schema": "kaggriculture-v113-sequence-action-ppo-v1",
        "transitions": len(indices), "history": history,
        "router_heads_frozen": True, "router_behavior_frozen": False,
        "trainable_scope": (
            f"market_memory_dense+unit_market_expert_slot:{args.expert_slot_index}"
            if args.train_market_memory_coordinated_expert else (
            f"market_memory_dense+market_expert_slot:{args.expert_slot_index}"
            if args.train_market_memory_expert else (
            f"history_input_only:last_{args.history_feature_count}_rows"
            if args.train_history_input_only else (
                (
                    f"expert_slot_only:{args.expert_projection_scope}:"
                    f"{args.expert_slot_index}"
                )
                if args.expert_slot_index is not None else (
                    f"expert_projections_only:{args.expert_projection_scope}"
                )
                if args.train_expert_projections_only else "shared_worker"
            )))
        ),
        "parameter_scope_audit": scope_audit,
        "worker_temperature": args.worker_temperature,
        "value_coefficient": args.value_coef, "checkpoint": str(checkpoint_path),
        "timed": args.timed,
        "market_memory_features": args.market_memory_features,
        "ratio_mode": args.ratio_mode,
        "final_full_rollout_metrics": final_metrics,
        "elapsed_seconds": time.time() - started,
    }
    (args.output_dir / "ppo_update.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
