"""Behavior-clone V113's factorized production and market expert branches."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import time

from flax import serialization
from flax.training.train_state import TrainState
import jax
import jax.numpy as jnp
import numpy as np
import optax

import action_space as space
from model_factorized import FactorizedHMoEActorCritic, NUM_EXPERTS


MODEL_KEYS = ("global", "board", "units", "unit_mask")
BATCH_KEYS = MODEL_KEYS + (
    "unit_tokens", "unit_quantities", "market_tokens", "market_quantities", "market_mask",
    "unit_expert", "market_expert", "value",
)
UNIT_QUANTITY_TOKEN = np.asarray([name.startswith("PICKUP:") or name.startswith("PLACE:") for name in space.UNIT_TOKENS])
MARKET_QUANTITY_TOKEN = np.asarray([name not in {"STOP", "HIRE", "BUY_LAND"} for name in space.MARKET_TOKENS])


def masked_ce(logits, targets, mask, weights):
    log_probability = jax.nn.log_softmax(logits, axis=-1)
    selected = jnp.take_along_axis(log_probability, targets[..., None], axis=-1)[..., 0]
    weighted_mask = mask * weights
    loss = -jnp.sum(selected * weighted_mask) / jnp.maximum(1.0, jnp.sum(weighted_mask))
    accuracy = jnp.sum((jnp.argmax(logits, axis=-1) == targets) * mask) / jnp.maximum(1.0, jnp.sum(mask))
    return loss, accuracy


def make_loss(unit_class_weights, market_class_weights, unit_action_weights, market_action_weights, value_coef):
    unit_quantity_lookup = jnp.asarray(UNIT_QUANTITY_TOKEN)
    market_quantity_lookup = jnp.asarray(MARKET_QUANTITY_TOKEN)
    unit_class_weights = jnp.asarray(unit_class_weights)
    market_class_weights = jnp.asarray(market_class_weights)
    unit_action_weights = jnp.asarray(unit_action_weights)
    market_action_weights = jnp.asarray(market_action_weights)

    def loss_fn(params, apply_fn, batch):
        output = apply_fn({"params": params}, *(batch[key] for key in MODEL_KEYS))
        index = jnp.arange(batch["unit_expert"].shape[0])
        unit_expert = batch["unit_expert"].astype(jnp.int32)
        market_expert = batch["market_expert"].astype(jnp.int32)
        unit_sample_weight = unit_class_weights[unit_expert]
        market_sample_weight = market_class_weights[market_expert]
        unit_logits = output["unit_logits"][index, unit_expert]
        unit_quantity_logits = output["unit_quantity_logits"][index, unit_expert]
        market_logits = output["market_logits"][index, market_expert]
        market_quantity_logits = output["market_quantity_logits"][index, market_expert]
        unit_mask = batch["unit_mask"]
        market_mask = batch["market_mask"]
        unit_loss, unit_accuracy = masked_ce(
            unit_logits, batch["unit_tokens"], unit_mask,
            unit_sample_weight[:, None] * unit_action_weights[batch["unit_tokens"]],
        )
        unit_quantity_mask = unit_mask * unit_quantity_lookup[batch["unit_tokens"]]
        unit_quantity_loss, unit_quantity_accuracy = masked_ce(
            unit_quantity_logits, batch["unit_quantities"], unit_quantity_mask,
            unit_sample_weight[:, None],
        )
        market_loss, market_accuracy = masked_ce(
            market_logits, batch["market_tokens"], market_mask,
            market_sample_weight[:, None] * market_action_weights[batch["market_tokens"]],
        )
        market_quantity_mask = market_mask * market_quantity_lookup[batch["market_tokens"]]
        market_quantity_loss, market_quantity_accuracy = masked_ce(
            market_quantity_logits, batch["market_quantities"], market_quantity_mask,
            market_sample_weight[:, None],
        )
        unit_router_loss, unit_router_accuracy = masked_ce(
            output["unit_router_logits"], unit_expert, jnp.ones_like(unit_expert), unit_sample_weight,
        )
        market_router_loss, market_router_accuracy = masked_ce(
            output["market_router_logits"], market_expert, jnp.ones_like(market_expert), market_sample_weight,
        )
        value_loss = jnp.mean((output["value"] - batch["value"]) ** 2)
        unit_probability = jax.nn.softmax(output["unit_router_logits"], axis=-1)
        market_probability = jax.nn.softmax(output["market_router_logits"], axis=-1)
        balance_loss = (
            jnp.sum((jnp.mean(unit_probability, axis=0) - 1.0 / NUM_EXPERTS) ** 2)
            + jnp.sum((jnp.mean(market_probability, axis=0) - 1.0 / NUM_EXPERTS) ** 2)
        )
        diversity_loss = 0.0
        for expert_h in (output["unit_expert_h"], output["market_expert_h"]):
            normalized = expert_h / jnp.maximum(1e-6, jnp.linalg.norm(expert_h, axis=-1, keepdims=True))
            gram = jnp.einsum("beh,bfh->bef", normalized, normalized)
            diversity_loss += jnp.mean((gram - jnp.eye(NUM_EXPERTS)[None]) ** 2)
        gate_penalty = jnp.mean(output["opponent_gate"])
        total = (
            unit_loss + market_loss + 0.15 * unit_quantity_loss + 0.15 * market_quantity_loss
            + 0.35 * unit_router_loss + 0.35 * market_router_loss + value_coef * value_loss
            + 0.05 * balance_loss + 0.005 * diversity_loss + 0.01 * gate_penalty
        )
        return total, {
            "loss": total, "unit_loss": unit_loss, "unit_accuracy": unit_accuracy,
            "unit_quantity_accuracy": unit_quantity_accuracy, "market_loss": market_loss,
            "market_accuracy": market_accuracy, "market_quantity_accuracy": market_quantity_accuracy,
            "unit_router_accuracy": unit_router_accuracy, "market_router_accuracy": market_router_accuracy,
            "value_loss": value_loss, "balance_loss": balance_loss,
            "diversity_loss": diversity_loss, "opponent_gate": gate_penalty,
        }
    return loss_fn


def frequency_weights(targets, mask, classes, exponent=0.75):
    counts = np.bincount(np.asarray(targets)[np.asarray(mask, dtype=bool)], minlength=classes).astype(np.float64)
    weights = np.zeros((classes,), dtype=np.float64)
    present = counts > 0
    weights[present] = counts[present] ** (-exponent)
    weights[present] *= counts.sum() / np.sum(weights[present] * counts[present])
    weights[present] = np.clip(weights[present], 0.05, 50.0)
    return weights.astype(np.float32), counts.astype(np.int64)


def expert_weights(labels, indices):
    counts = np.bincount(labels[indices], minlength=NUM_EXPERTS).astype(np.float32)
    weights = np.sqrt(max(1.0, counts.mean()) / np.maximum(1.0, counts))
    weights /= np.average(weights, weights=np.maximum(1.0, counts))
    return weights, counts.astype(np.int64)


def batches(data, indices, batch_size, rng, shuffle):
    indices = np.asarray(indices).copy()
    if shuffle:
        rng.shuffle(indices)
    for start in range(0, len(indices) - batch_size + 1, batch_size):
        selected = indices[start:start + batch_size]
        yield {
            key: jnp.asarray(data[key][selected], dtype=jnp.float32) if key in MODEL_KEYS or key == "market_mask"
            else jnp.asarray(data[key][selected])
            for key in BATCH_KEYS
        }


def mean_metrics(rows):
    return {key: float(np.mean([float(row[key]) for row in rows])) for key in rows[0]} if rows else {}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, nargs="+", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--value-coef", type=float, default=0.1)
    parser.add_argument("--initial-checkpoint", type=Path)
    parser.add_argument("--unit-action-weight-exponent", type=float, default=0.75)
    parser.add_argument("--market-action-weight-exponent", type=float, default=0.75)
    parser.add_argument("--experts", type=int, nargs="+", choices=range(NUM_EXPERTS))
    parser.add_argument("--seed", type=int, default=1136001)
    args = parser.parse_args()
    started = time.time()
    shards = []
    for path in args.dataset:
        with np.load(path) as archive:
            shards.append({key: archive[key] for key in archive.files})
    keys = set.intersection(*(set(shard) for shard in shards))
    data = {key: np.concatenate([shard[key] for shard in shards]) for key in keys}
    train_indices = np.flatnonzero(data["split"] == 0)
    validation_indices = np.flatnonzero(data["split"] == 1)
    if args.experts:
        selected_experts = np.asarray(args.experts)
        train_indices = train_indices[np.isin(data["unit_expert"][train_indices], selected_experts)]
        validation_indices = validation_indices[np.isin(data["unit_expert"][validation_indices], selected_experts)]
        if len(train_indices) == 0 or len(validation_indices) == 0:
            raise ValueError("expert filter produced an empty train or validation split")
    unit_class_weights, unit_expert_counts = expert_weights(data["unit_expert"], train_indices)
    market_class_weights, market_expert_counts = expert_weights(data["market_expert"], train_indices)
    unit_action_weights, unit_action_counts = frequency_weights(
        data["unit_tokens"][train_indices], data["unit_mask"][train_indices], len(space.UNIT_TOKENS),
        exponent=args.unit_action_weight_exponent,
    )
    market_action_weights, market_action_counts = frequency_weights(
        data["market_tokens"][train_indices], data["market_mask"][train_indices], len(space.MARKET_TOKENS),
        exponent=args.market_action_weight_exponent,
    )
    model = FactorizedHMoEActorCritic()
    example = {key: jnp.asarray(data[key][:1]) for key in MODEL_KEYS}
    if args.initial_checkpoint:
        params = serialization.msgpack_restore(args.initial_checkpoint.read_bytes())["params"]
    else:
        params = model.init(jax.random.key(args.seed), *(example[key] for key in MODEL_KEYS))["params"]
    state = TrainState.create(
        apply_fn=model.apply, params=params,
        tx=optax.chain(optax.clip_by_global_norm(0.5), optax.adamw(args.learning_rate, weight_decay=1e-5)),
    )
    loss_fn = make_loss(
        unit_class_weights, market_class_weights, unit_action_weights, market_action_weights, args.value_coef
    )

    @jax.jit
    def train_step(train_state, batch):
        (_, metrics), gradients = jax.value_and_grad(loss_fn, has_aux=True)(train_state.params, train_state.apply_fn, batch)
        return train_state.apply_gradients(grads=gradients), metrics

    @jax.jit
    def eval_step(train_state, batch):
        return loss_fn(train_state.params, train_state.apply_fn, batch)[1]

    rng = np.random.default_rng(args.seed)
    history = []
    best_loss = float("inf")
    best_params = state.params
    for epoch in range(1, args.epochs + 1):
        train_rows = []
        for batch in batches(data, train_indices, args.batch_size, rng, True):
            state, metrics = train_step(state, batch)
            train_rows.append(jax.device_get(metrics))
        validation_rows = [jax.device_get(eval_step(state, batch)) for batch in batches(data, validation_indices, args.batch_size, rng, False)]
        row = {"epoch": epoch, "train": mean_metrics(train_rows), "validation": mean_metrics(validation_rows)}
        history.append(row)
        if row["validation"].get("loss", float("inf")) < best_loss:
            best_loss = row["validation"]["loss"]
            best_params = jax.device_get(state.params)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = args.output_dir / "bc_best.msgpack"
    checkpoint = {
        "params": best_params, "model_id": "v113_factorized_hmoe_ppo",
        "strategy_parent": None, "architecture": "factorized-production-market-hmoe-v3",
        "dataset_sha256": [hashlib.sha256(path.read_bytes()).hexdigest() for path in args.dataset],
        "initial_checkpoint": str(args.initial_checkpoint) if args.initial_checkpoint else None,
    }
    with tempfile.NamedTemporaryFile("wb", dir=args.output_dir, delete=False) as sink:
        sink.write(serialization.msgpack_serialize(checkpoint))
        temporary = Path(sink.name)
    temporary.replace(checkpoint_path)
    report = {
        "schema": "kaggriculture-v113-factorized-bc-v1", "status": "BC_COMPLETE",
        "datasets": [str(path) for path in args.dataset], "train_rows": int(len(train_indices)),
        "validation_rows": int(len(validation_indices)), "unit_expert_counts": unit_expert_counts.tolist(),
        "market_expert_counts": market_expert_counts.tolist(), "unit_action_counts": unit_action_counts.tolist(),
        "market_action_counts": market_action_counts.tolist(), "history": history,
        "unit_action_weight_exponent": args.unit_action_weight_exponent,
        "market_action_weight_exponent": args.market_action_weight_exponent,
        "expert_filter": args.experts,
        "best_validation_loss": best_loss, "checkpoint": str(checkpoint_path),
        "elapsed_seconds": time.time() - started,
    }
    (args.output_dir / "bc_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("status", "best_validation_loss", "checkpoint", "elapsed_seconds")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
