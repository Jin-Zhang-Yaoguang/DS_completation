"""Behavior-clone the frozen v2 macro decisions."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

import jax
import jax.numpy as jnp
import numpy as np
import optax

import main
from model_jax import MacroPolicy, apply_sequence, export_numpy, initial_params, parity_error, save_checkpoint


HERE = Path(__file__).resolve().parent


def _bucket(seed):
    digest = hashlib.sha256(str(int(seed)).encode("ascii")).digest()
    return int.from_bytes(digest[:8], "big") % 100


def load_dataset(directory):
    rows = {}
    for path in sorted(Path(directory).glob("bc-*.npz")):
        data = np.load(path, allow_pickle=False)
        for key in ("features", "actions", "route_mask", "seeds", "seats", "rewards"):
            rows.setdefault(key, []).append(np.asarray(data[key]))
    if not rows:
        raise ValueError(f"no BC shards in {directory}")
    data = {key: np.concatenate(values, axis=0) for key, values in rows.items()}
    buckets = np.asarray([_bucket(seed) for seed in data["seeds"]])
    data["split"] = np.where(buckets < 80, 0, np.where(buckets < 90, 1, 2)).astype(np.int8)
    seats = data["seats"].astype(np.int64)
    own = data["rewards"][np.arange(len(seats)), seats]
    opponent = data["rewards"][np.arange(len(seats)), 1 - seats]
    terminal = np.sign(own - opponent) + 0.1 * np.tanh((own - opponent) / 25000.0)
    data["value_target"] = np.repeat(terminal[:, None], data["features"].shape[1], axis=1).astype(np.float32)
    return data


def _slice(data, indices):
    return {
        "features": jnp.asarray(data["features"][indices], dtype=jnp.float32),
        "actions": jnp.asarray(data["actions"][indices], dtype=jnp.int32),
        "route_mask": jnp.asarray(data["route_mask"][indices], dtype=jnp.float32),
        "value_target": jnp.asarray(data["value_target"][indices], dtype=jnp.float32),
    }


def make_loss(model, label_smoothing):
    def loss_fn(params, batch):
        logits, values, _ = apply_sequence(model, params, batch["features"])
        losses = []
        accuracies = []
        for head_index, head_logits in enumerate(logits):
            labels = batch["actions"][..., head_index]
            log_probabilities = jax.nn.log_softmax(head_logits, axis=-1)
            selected = jnp.take_along_axis(log_probabilities, labels[..., None], axis=-1)[..., 0]
            cross_entropy = -(1.0 - label_smoothing) * selected - label_smoothing * jnp.mean(log_probabilities, axis=-1)
            mask = batch["route_mask"] if head_index == 0 else jnp.ones_like(batch["route_mask"])
            denominator = jnp.maximum(1.0, jnp.sum(mask))
            losses.append(jnp.sum(cross_entropy * mask) / denominator)
            predictions = jnp.argmax(head_logits, axis=-1)
            accuracies.append(jnp.sum((predictions == labels) * mask) / denominator)
        value_loss = jnp.mean(jnp.square(values - batch["value_target"]))
        total = jnp.sum(jnp.stack(losses)) + 0.1 * value_loss
        metrics = {
            "loss": total,
            "actor_loss": jnp.sum(jnp.stack(losses)),
            "value_loss": value_loss,
            "route_accuracy": accuracies[0],
            "macro_accuracy": jnp.mean(jnp.stack(accuracies[1:])),
        }
        return total, metrics

    return loss_fn


def train(data_dir, output_dir, epochs=5, batch_size=128, learning_rate=3e-4, label_smoothing=0.03, seed=11):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    data = load_dataset(data_dir)
    train_indices = np.flatnonzero(data["split"] == 0)
    validation_indices = np.flatnonzero(data["split"] == 1)
    test_indices = np.flatnonzero(data["split"] == 2)
    if not len(train_indices):
        raise ValueError("empty training split")
    if not len(validation_indices):
        validation_indices = train_indices[: min(len(train_indices), batch_size)]

    model = MacroPolicy()
    params = initial_params(seed)
    optimizer = optax.chain(optax.clip_by_global_norm(0.5), optax.adam(learning_rate))
    optimizer_state = optimizer.init(params)
    loss_fn = make_loss(model, label_smoothing)

    @jax.jit
    def update(params, optimizer_state, batch):
        (_, metrics), gradients = jax.value_and_grad(loss_fn, has_aux=True)(params, batch)
        updates, optimizer_state = optimizer.update(gradients, optimizer_state, params)
        return optax.apply_updates(params, updates), optimizer_state, metrics

    @jax.jit
    def evaluate(params, batch):
        return loss_fn(params, batch)[1]

    rng = np.random.default_rng(seed)
    history = []
    started = time.time()
    for epoch in range(1, epochs + 1):
        shuffled = rng.permutation(train_indices)
        train_metrics = []
        for start in range(0, len(shuffled), batch_size):
            indices = shuffled[start : start + batch_size]
            params, optimizer_state, metrics = update(params, optimizer_state, _slice(data, indices))
            train_metrics.append({key: float(value) for key, value in metrics.items()})
        validation = {key: float(value) for key, value in evaluate(params, _slice(data, validation_indices)).items()}
        row = {
            "epoch": epoch,
            "train": {key: float(np.mean([metrics[key] for metrics in train_metrics])) for key in train_metrics[0]},
            "validation": validation,
        }
        history.append(row)
        print(json.dumps(row), flush=True)

    checkpoint = output_dir / "bc_params.msgpack"
    weights = output_dir / "policy_weights.npz"
    save_checkpoint(checkpoint, params)
    export_numpy(params, weights)
    parity = parity_error(params, weights)
    test_metrics = (
        {key: float(value) for key, value in evaluate(params, _slice(data, test_indices)).items()}
        if len(test_indices)
        else {}
    )
    report = {
        "schema": "kaggriculture-v3-bc-report-1",
        "episodes": int(len(data["features"])),
        "splits": {"train": int(len(train_indices)), "validation": int(len(validation_indices)), "test": int(len(test_indices))},
        "epochs": epochs,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "label_smoothing": label_smoothing,
        "elapsed_seconds": time.time() - started,
        "parity_max_abs_error": parity,
        "test": test_metrics,
        "history": history,
        "checkpoint": checkpoint.name,
        "weights": weights.name,
    }
    (output_dir / "bc_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=HERE / "data" / "bc")
    parser.add_argument("--output", type=Path, default=HERE / "checkpoints" / "bc")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--label-smoothing", type=float, default=0.03)
    parser.add_argument("--seed", type=int, default=11)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print(json.dumps(train(args.data, args.output, args.epochs, args.batch_size, args.learning_rate, args.label_smoothing, args.seed), ensure_ascii=False, indent=2))
