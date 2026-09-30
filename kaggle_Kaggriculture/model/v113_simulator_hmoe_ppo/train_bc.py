"""Behavior-clone V113's independent six-expert full-action policy."""

from __future__ import annotations

import argparse
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
from model import HMoEActorCritic, NUM_EXPERTS


MODEL_KEYS = ("global", "board", "units", "unit_mask")
BATCH_KEYS = MODEL_KEYS + ("unit_tokens", "unit_quantities", "market_tokens", "market_quantities", "market_mask", "expert", "value")
UNIT_QUANTITY_TOKEN = np.asarray([name.startswith("PICKUP:") or name.startswith("PLACE:") for name in space.UNIT_TOKENS])
MARKET_QUANTITY_TOKEN = np.asarray([name not in {"STOP", "HIRE", "BUY_LAND"} for name in space.MARKET_TOKENS])


def masked_ce(logits, targets, mask, weights):
    log_probability = jax.nn.log_softmax(logits, axis=-1)
    selected = jnp.take_along_axis(log_probability, targets[..., None], axis=-1)[..., 0]
    weighted_mask = mask * weights
    loss = -jnp.sum(selected * weighted_mask) / jnp.maximum(1.0, jnp.sum(weighted_mask))
    accuracy = jnp.sum((jnp.argmax(logits, axis=-1) == targets) * mask) / jnp.maximum(1.0, jnp.sum(mask))
    return loss, accuracy


def make_loss(class_weights, unit_action_weights, market_action_weights, value_coefficient):
    unit_quantity_lookup = jnp.asarray(UNIT_QUANTITY_TOKEN)
    market_quantity_lookup = jnp.asarray(MARKET_QUANTITY_TOKEN)
    class_weights = jnp.asarray(class_weights)
    unit_action_weights = jnp.asarray(unit_action_weights)
    market_action_weights = jnp.asarray(market_action_weights)

    def loss_fn(params, apply_fn, batch):
        output = apply_fn({"params": params}, *(batch[key] for key in MODEL_KEYS))
        batch_index = jnp.arange(batch["expert"].shape[0])
        expert = batch["expert"].astype(jnp.int32)
        sample_weight = class_weights[expert]
        unit_logits = output["unit_logits"][batch_index, expert]
        unit_quantity_logits = output["unit_quantity_logits"][batch_index, expert]
        market_logits = output["market_logits"][batch_index, expert]
        market_quantity_logits = output["market_quantity_logits"][batch_index, expert]
        unit_mask = batch["unit_mask"]
        market_mask = batch["market_mask"]
        unit_loss, unit_acc = masked_ce(
            unit_logits, batch["unit_tokens"], unit_mask,
            sample_weight[:, None] * unit_action_weights[batch["unit_tokens"]],
        )
        unit_quantity_mask = unit_mask * unit_quantity_lookup[batch["unit_tokens"]]
        unit_quantity_loss, unit_quantity_acc = masked_ce(unit_quantity_logits, batch["unit_quantities"], unit_quantity_mask, sample_weight[:, None])
        market_loss, market_acc = masked_ce(
            market_logits, batch["market_tokens"], market_mask,
            sample_weight[:, None] * market_action_weights[batch["market_tokens"]],
        )
        market_quantity_mask = market_mask * market_quantity_lookup[batch["market_tokens"]]
        market_quantity_loss, market_quantity_acc = masked_ce(market_quantity_logits, batch["market_quantities"], market_quantity_mask, sample_weight[:, None])
        router_loss, router_acc = masked_ce(output["router_logits"], expert, jnp.ones_like(expert, dtype=jnp.float32), sample_weight)
        value_loss = jnp.mean((output["value"] - batch["value"]) ** 2)
        router_probability = jax.nn.softmax(output["router_logits"], axis=-1)
        balance_loss = jnp.sum((jnp.mean(router_probability, axis=0) - 1.0 / NUM_EXPERTS) ** 2)
        normalized_expert = output["expert_h"] / jnp.maximum(1e-6, jnp.linalg.norm(output["expert_h"], axis=-1, keepdims=True))
        gram = jnp.einsum("beh,bfh->bef", normalized_expert, normalized_expert)
        diversity_loss = jnp.mean((gram - jnp.eye(NUM_EXPERTS)[None]) ** 2)
        total = (
            unit_loss + market_loss + 0.15 * unit_quantity_loss + 0.15 * market_quantity_loss
            + 0.5 * router_loss + value_coefficient * value_loss + 0.1 * balance_loss + 0.01 * diversity_loss
        )
        metrics = {
            "loss": total,
            "unit_loss": unit_loss,
            "unit_accuracy": unit_acc,
            "unit_quantity_accuracy": unit_quantity_acc,
            "market_loss": market_loss,
            "market_accuracy": market_acc,
            "market_quantity_accuracy": market_quantity_acc,
            "router_loss": router_loss,
            "router_accuracy": router_acc,
            "value_loss": value_loss,
            "balance_loss": balance_loss,
            "diversity_loss": diversity_loss,
        }
        return total, metrics
    return loss_fn


def batches(data, indices, batch_size, rng, shuffle):
    indices = np.asarray(indices).copy()
    if shuffle:
        rng.shuffle(indices)
    for start in range(0, len(indices), batch_size):
        selected = indices[start:start + batch_size]
        if len(selected) < batch_size:
            continue
        yield {
            key: jnp.asarray(data[key][selected], dtype=jnp.float32) if key in MODEL_KEYS or key in {"market_mask"}
            else jnp.asarray(data[key][selected])
            for key in BATCH_KEYS
        }


def mean_metrics(rows):
    return {key: float(np.mean([float(row[key]) for row in rows])) for key in rows[0]} if rows else {}


def frequency_weights(targets, mask, classes, exponent=0.75):
    counts = np.bincount(np.asarray(targets)[np.asarray(mask, dtype=bool)], minlength=classes).astype(np.float64)
    weights = np.zeros((classes,), dtype=np.float64)
    present = counts > 0
    weights[present] = counts[present] ** (-exponent)
    weights[present] *= counts.sum() / np.sum(weights[present] * counts[present])
    weights[present] = np.clip(weights[present], 0.05, 50.0)
    return weights.astype(np.float32), counts.astype(np.int64)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, nargs="+", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--seed", type=int, default=113005)
    parser.add_argument("--initial-checkpoint", type=Path)
    parser.add_argument("--opponent-blind", action="store_true")
    parser.add_argument("--value-coef", type=float, default=0.25)
    args = parser.parse_args()
    started = time.time()
    shards = []
    for dataset_path in args.dataset:
        with np.load(dataset_path) as archive:
            shards.append({key: archive[key] for key in archive.files})
    keys = set.intersection(*(set(shard) for shard in shards))
    data = {key: np.concatenate([shard[key] for shard in shards], axis=0) for key in keys}
    if args.opponent_blind:
        data["global"] = data["global"].copy()
        data["global"][:, 10:16] = 0
        data["board"] = data["board"].copy()
        data["board"][:, 1] = 0
    train_indices = np.flatnonzero(data["split"] == 0)
    validation_indices = np.flatnonzero(data["split"] == 1)
    counts = np.bincount(data["expert"][train_indices], minlength=NUM_EXPERTS).astype(np.float32)
    class_weights = np.sqrt(max(1.0, counts.mean()) / np.maximum(1.0, counts))
    class_weights /= np.average(class_weights, weights=np.maximum(1.0, counts))
    unit_action_weights, unit_action_counts = frequency_weights(
        data["unit_tokens"][train_indices], data["unit_mask"][train_indices], len(space.UNIT_TOKENS)
    )
    market_action_weights, market_action_counts = frequency_weights(
        data["market_tokens"][train_indices], data["market_mask"][train_indices], len(space.MARKET_TOKENS)
    )

    model = HMoEActorCritic()
    example = {key: jnp.asarray(data[key][:1]) for key in MODEL_KEYS}
    if args.initial_checkpoint:
        params = serialization.msgpack_restore(args.initial_checkpoint.read_bytes())["params"]
    else:
        params = model.init(jax.random.key(args.seed), *(example[key] for key in MODEL_KEYS))["params"]
    optimizer = optax.chain(optax.clip_by_global_norm(0.5), optax.adamw(args.learning_rate, weight_decay=1e-5))
    state = TrainState.create(apply_fn=model.apply, params=params, tx=optimizer)
    loss_fn = make_loss(class_weights, unit_action_weights, market_action_weights, args.value_coef)

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
        validation_loss = row["validation"].get("loss", row["train"]["loss"])
        if validation_loss < best_loss:
            best_loss = validation_loss
            best_params = jax.device_get(state.params)
        print(json.dumps(row, ensure_ascii=False), flush=True)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = {
        "params": best_params,
        "model_id": "v113_simulator_hmoe_ppo",
        "strategy_parent": None,
        "architecture": "local-board-unit-attention-hmoe-v2",
        "dataset_sha256": [__import__("hashlib").sha256(path.read_bytes()).hexdigest() for path in args.dataset],
        "initial_checkpoint": str(args.initial_checkpoint) if args.initial_checkpoint else None,
        "opponent_blind": args.opponent_blind,
        "value_coefficient": args.value_coef,
    }
    checkpoint_path = args.output_dir / "bc_best.msgpack"
    with tempfile.NamedTemporaryFile("wb", dir=args.output_dir, delete=False) as sink:
        sink.write(serialization.msgpack_serialize(checkpoint))
        temporary = Path(sink.name)
    temporary.replace(checkpoint_path)
    report = {
        "schema": "kaggriculture-v113-bc-report-v1",
        "status": "BC_COMPLETE",
        "dataset": [str(path) for path in args.dataset],
        "train_rows": len(train_indices),
        "validation_rows": len(validation_indices),
        "expert_counts_train": counts.astype(int).tolist(),
        "class_weights": class_weights.tolist(),
        "unit_action_counts": unit_action_counts.tolist(),
        "unit_action_weights": unit_action_weights.tolist(),
        "market_action_counts": market_action_counts.tolist(),
        "market_action_weights": market_action_weights.tolist(),
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "best_validation_loss": best_loss,
        "history": history,
        "checkpoint": str(checkpoint_path),
        "elapsed_seconds": time.time() - started,
    }
    (args.output_dir / "bc_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("status", "best_validation_loss", "elapsed_seconds", "checkpoint")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
