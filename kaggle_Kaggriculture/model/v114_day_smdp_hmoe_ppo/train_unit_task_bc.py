"""Stream-shard BC warm start for the V12 persistent unit-task HMoE."""

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

from build_unit_task_dataset import ITEMS, ROLE_NAMES, TASK_OPERATIONS
from model_unit_task_hmoe import UnitTaskHMoE


MODEL_KEYS = ("global", "board", "unit")
LABEL_KEYS = (
    "role", "operation", "item", "quantity_tier", "target_x", "target_y", "duration",
)
ITEM_OPERATIONS = np.asarray([
    name in {"PLANT", "PICKUP", "PLACE"} for name in TASK_OPERATIONS
], dtype=np.float32)
QUANTITY_OPERATIONS = np.asarray([
    name in {"PICKUP", "PLACE"} for name in TASK_OPERATIONS
], dtype=np.float32)
TARGET_OPERATIONS = np.asarray([
    name != "REST" for name in TASK_OPERATIONS
], dtype=np.float32)


def weighted_ce(logits, labels, weights=None, mask=None):
    labels = labels.astype(jnp.int32)
    loss = -jnp.take_along_axis(
        jax.nn.log_softmax(logits), labels[:, None], axis=-1
    )[:, 0]
    if weights is not None:
        loss = loss * weights[labels]
    if mask is None:
        mask = jnp.ones_like(loss)
    denominator = jnp.maximum(1.0, jnp.sum(mask))
    accuracy = jnp.sum((jnp.argmax(logits, axis=-1) == labels) * mask) / denominator
    return jnp.sum(loss * mask) / denominator, accuracy


def make_loss(role_weights, operation_weights):
    role_weights = jnp.asarray(role_weights)
    operation_weights = jnp.asarray(operation_weights)
    item_mask_lookup = jnp.asarray(ITEM_OPERATIONS)
    quantity_mask_lookup = jnp.asarray(QUANTITY_OPERATIONS)
    target_mask_lookup = jnp.asarray(TARGET_OPERATIONS)

    def loss_fn(params, apply_fn, batch):
        output = apply_fn({"params": params}, *(batch[key] for key in MODEL_KEYS))
        role = batch["role"].astype(jnp.int32)
        index = jnp.arange(role.shape[0])

        def selected(name):
            return output[name][index, role]

        role_loss, role_accuracy = weighted_ce(
            output["role_logits"], role, role_weights
        )
        operation_loss, operation_accuracy = weighted_ce(
            selected("operation_logits"), batch["operation"], operation_weights
        )
        item_mask = item_mask_lookup[batch["operation"].astype(jnp.int32)]
        item_loss, item_accuracy = weighted_ce(
            selected("item_logits"), batch["item"], mask=item_mask
        )
        quantity_mask = quantity_mask_lookup[batch["operation"].astype(jnp.int32)]
        quantity_loss, quantity_accuracy = weighted_ce(
            selected("quantity_logits"), batch["quantity_tier"], mask=quantity_mask
        )
        target_mask = target_mask_lookup[batch["operation"].astype(jnp.int32)]
        x_loss, x_accuracy = weighted_ce(
            selected("target_x_logits"), batch["target_x"], mask=target_mask
        )
        y_loss, y_accuracy = weighted_ce(
            selected("target_y_logits"), batch["target_y"], mask=target_mask
        )
        duration_loss, duration_accuracy = weighted_ce(
            selected("duration_logits"), batch["duration"]
        )
        total = (
            operation_loss + 0.50 * role_loss
            + 0.35 * (x_loss + y_loss)
            + 0.20 * item_loss + 0.10 * quantity_loss + 0.10 * duration_loss
        )
        return total, {
            "loss": total,
            "role_accuracy": role_accuracy,
            "operation_accuracy": operation_accuracy,
            "target_x_accuracy": x_accuracy,
            "target_y_accuracy": y_accuracy,
            "item_accuracy": item_accuracy,
            "quantity_accuracy": quantity_accuracy,
            "duration_accuracy": duration_accuracy,
        }
    return loss_fn


def class_weights(counts):
    counts = np.asarray(counts, dtype=np.float64)
    weights = np.zeros_like(counts)
    present = counts > 0
    weights[present] = np.sqrt(np.sum(counts[present]) / counts[present])
    if np.any(present):
        weights[present] /= np.mean(weights[present])
    return weights.astype(np.float32)


def load_rows(path: Path, split: int, limit: int, rng: np.random.Generator):
    with np.load(path, allow_pickle=False) as archive:
        indices = np.flatnonzero(archive["split"] == split)
        if limit > 0 and len(indices) > limit:
            indices = rng.choice(indices, limit, replace=False)
        return {
            key: archive[key][indices]
            for key in (*MODEL_KEYS, *LABEL_KEYS)
        }


def batches(data, batch_size, rng, shuffle):
    indices = np.arange(len(data["role"]))
    if shuffle:
        rng.shuffle(indices)
    for start in range(0, len(indices) - batch_size + 1, batch_size):
        selected = indices[start:start + batch_size]
        yield {
            key: jnp.asarray(value[selected], dtype=jnp.float32)
            if key in MODEL_KEYS else jnp.asarray(value[selected])
            for key, value in data.items()
        }


def means(rows):
    if not rows:
        raise ValueError("empty metrics")
    return {key: float(np.mean([float(row[key]) for row in rows])) for key in rows[0]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, nargs="+", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=6)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--seed", type=int, default=11412001)
    parser.add_argument("--train-rows-per-shard", type=int, default=24000)
    parser.add_argument("--dev-rows-per-shard", type=int, default=5000)
    args = parser.parse_args()
    started = time.time()
    rng = np.random.default_rng(args.seed)

    role_counts = np.zeros((len(ROLE_NAMES),), dtype=np.int64)
    operation_counts = np.zeros((len(TASK_OPERATIONS),), dtype=np.int64)
    for path in args.dataset:
        with np.load(path, allow_pickle=False) as archive:
            train = archive["split"] == 0
            role_counts += np.bincount(archive["role"][train], minlength=len(ROLE_NAMES))
            operation_counts += np.bincount(
                archive["operation"][train], minlength=len(TASK_OPERATIONS)
            )
    role_weights = class_weights(role_counts)
    operation_weights = class_weights(operation_counts)

    first = load_rows(args.dataset[0], 0, 1, rng)
    model = UnitTaskHMoE()
    params = model.init(
        jax.random.key(args.seed), *(jnp.asarray(first[key]) for key in MODEL_KEYS)
    )["params"]
    optimizer = optax.chain(
        optax.clip_by_global_norm(0.5),
        optax.adamw(args.learning_rate, weight_decay=1e-5),
    )
    state = TrainState.create(apply_fn=model.apply, params=params, tx=optimizer)
    loss_fn = make_loss(role_weights, operation_weights)

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
    checkpoint_path = args.output_dir / "unit_task_bc_best.msgpack"
    history = []
    best_loss = float("inf")
    best_params = state.params
    for epoch in range(1, args.epochs + 1):
        train_metrics = []
        order = list(args.dataset)
        rng.shuffle(order)
        for path in order:
            data = load_rows(path, 0, args.train_rows_per_shard, rng)
            for batch in batches(data, args.batch_size, rng, True):
                state, metrics = train_step(state, batch)
                train_metrics.append(jax.device_get(metrics))
        dev_metrics = []
        for path in args.dataset:
            data = load_rows(path, 1, args.dev_rows_per_shard, rng)
            for batch in batches(data, args.batch_size, rng, False):
                dev_metrics.append(jax.device_get(eval_step(state, batch)))
        row = {"epoch": epoch, "train": means(train_metrics), "development": means(dev_metrics)}
        history.append(row)
        if row["development"]["loss"] < best_loss:
            best_loss = row["development"]["loss"]
            best_params = jax.device_get(state.params)
            payload = {
                "params": best_params,
                "model_id": "v114_v12_persistent_unit_task_hmoe_bc",
                "architecture": "v114-event-ledger-persistent-unit-task-hmoe-v1",
                "strategy_parent": None,
                "inherits_historical_checkpoint": False,
                "historical_agent_online_action_source": False,
                "training_seed": args.seed,
                "dataset_sha256": [hashlib.sha256(path.read_bytes()).hexdigest() for path in args.dataset],
                "qualification_status": "BC_WARMSTART_ONLY_NOT_G1_NOT_PPO_NOT_GOLD",
            }
            with tempfile.NamedTemporaryFile("wb", dir=args.output_dir, delete=False) as sink:
                sink.write(serialization.msgpack_serialize(payload))
                temporary = Path(sink.name)
            temporary.replace(checkpoint_path)
        print(json.dumps(row, ensure_ascii=False), flush=True)

    report = {
        "schema": "kaggriculture-v114-v12-unit-task-bc-v1",
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": hashlib.sha256(checkpoint_path.read_bytes()).hexdigest(),
        "best_development_loss": best_loss,
        "history": history,
        "role_counts": role_counts.tolist(),
        "operation_counts": operation_counts.tolist(),
        "role_weights": role_weights.tolist(),
        "operation_weights": operation_weights.tolist(),
        "blind_split_accessed_for_metrics_or_selection": False,
        "training_seed": args.seed,
        "elapsed_seconds": time.time() - started,
        "qualification_status": "BC_WARMSTART_ONLY_NOT_G1_NOT_PPO_NOT_GOLD",
    }
    (args.output_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "checkpoint_sha256": report["checkpoint_sha256"],
        "best_development_loss": best_loss,
        "elapsed_seconds": report["elapsed_seconds"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
