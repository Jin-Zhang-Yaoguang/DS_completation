"""Train and calibrate the V12 event transaction-intent BC warmstart."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import time

from flax import serialization
import jax
import jax.numpy as jnp
import numpy as np
import optax

from build_event_market_dataset import (
    EVENT_TYPES, PROCUREMENT_HEADS, QUANTITY_TIERS, TRANSACTION_HEADS,
)
from model_event_market_hmoe import EventMarketHMoE


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as sink:
        json.dump(payload, sink, ensure_ascii=False, indent=2)
        sink.write("\n")
        temporary = Path(sink.name)
    temporary.replace(path)


def batches(indices: np.ndarray, batch_size: int, rng: np.random.Generator | None = None):
    order = rng.permutation(indices) if rng is not None else indices
    for offset in range(0, len(order), batch_size):
        yield order[offset:offset + batch_size]


def load_dataset(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as archive:
        return {
            key: np.asarray(archive[key])
            for key in archive.files if key != "quantity_raw"
        }


def calibrate_thresholds(probability: np.ndarray, target: np.ndarray) -> tuple[list[float], dict]:
    thresholds = []
    report = {}
    procurement_count = len(PROCUREMENT_HEADS)
    for head in range(len(TRANSACTION_HEADS)):
        truth = target[:, head].astype(bool)
        if head >= procurement_count:
            threshold = 0.5
        elif int(truth.sum()) == 0:
            threshold = 1.1
        else:
            choices = []
            for threshold_value in np.linspace(0.05, 0.99, 95):
                predicted = probability[:, head] >= threshold_value
                true_positive = int(np.sum(predicted & truth))
                false_positive = int(np.sum(predicted & ~truth))
                precision = true_positive / max(1, true_positive + false_positive)
                recall = true_positive / int(truth.sum())
                if precision >= 0.95:
                    choices.append((recall, -threshold_value, precision, threshold_value))
            threshold = max(choices)[3] if choices else 1.1
        predicted = probability[:, head] >= threshold
        tp = int(np.sum(predicted & truth))
        fp = int(np.sum(predicted & ~truth))
        report[TRANSACTION_HEADS[head]] = {
            "threshold": float(threshold),
            "positives": int(truth.sum()),
            "predicted": int(predicted.sum()),
            "true_positive": tp,
            "false_positive": fp,
            "precision": tp / max(1, tp + fp),
            "recall": tp / max(1, int(truth.sum())),
        }
        thresholds.append(float(threshold))
    return thresholds, report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, nargs="+", required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--seed", type=int, default=11412003)
    args = parser.parse_args()
    started = time.time()
    train_rows = 0
    development_rows = 0
    positives = np.zeros((len(TRANSACTION_HEADS),), dtype=np.float64)
    first_batch = None
    for path in args.dataset:
        data = load_dataset(path)
        train = np.flatnonzero(data["split"] == 0)
        development = np.flatnonzero(data["split"] == 1)
        train_rows += len(train)
        development_rows += len(development)
        positives += data["presence"][train].sum(axis=0)
        if first_batch is None and len(train):
            first_batch = {key: value[train[:2]] for key, value in data.items()}
    if not train_rows or not development_rows or first_batch is None:
        raise ValueError("train and development splits must be non-empty")
    positives = positives.astype(np.float32)
    negatives = train_rows - positives
    positive_weight = np.clip(negatives / np.maximum(positives, 1.0), 1.0, 20.0)
    model = EventMarketHMoE()
    rng_key = jax.random.PRNGKey(args.seed)
    params = model.init(
        rng_key,
        jnp.asarray(first_batch["global"], jnp.float32),
        jnp.asarray(first_batch["board"], jnp.float32),
        jnp.asarray(first_batch["event_type"], jnp.int32),
    )["params"]
    optimizer = optax.chain(optax.clip_by_global_norm(1.0), optax.adam(args.learning_rate))
    optimizer_state = optimizer.init(params)
    positive_weight_jax = jnp.asarray(positive_weight)

    def make_batch(selected):
        return {
            "global": jnp.asarray(data["global"][selected], jnp.float32),
            "board": jnp.asarray(data["board"][selected], jnp.float32),
            "event_type": jnp.asarray(data["event_type"][selected], jnp.int32),
            "presence": jnp.asarray(data["presence"][selected], jnp.float32),
            "quantity": jnp.asarray(data["quantity_tier"][selected], jnp.int32),
        }

    def loss_fn(current_params, batch):
        output = model.apply(
            {"params": current_params}, batch["global"], batch["board"], batch["event_type"]
        )
        presence_loss = optax.sigmoid_binary_cross_entropy(
            output["presence_logits"], batch["presence"]
        ) * jnp.where(batch["presence"] > 0, positive_weight_jax, 1.0)
        presence_loss = jnp.mean(presence_loss)
        quantity_loss_all = optax.softmax_cross_entropy_with_integer_labels(
            output["quantity_logits"], batch["quantity"]
        )
        quantity_loss = jnp.sum(quantity_loss_all * batch["presence"]) / jnp.maximum(1.0, jnp.sum(batch["presence"]))
        router_loss = jnp.mean(optax.softmax_cross_entropy_with_integer_labels(
            output["router_logits"], batch["event_type"]
        ))
        value_target = jnp.log1p(jnp.sum(batch["quantity"].astype(jnp.float32), axis=-1)) / 5.0
        value_loss = jnp.mean(optax.huber_loss(output["value"], value_target, delta=1.0))
        total = presence_loss + 0.5 * quantity_loss + 0.1 * router_loss + 0.1 * value_loss
        return total, {
            "loss": total, "presence_loss": presence_loss,
            "quantity_loss": quantity_loss, "router_loss": router_loss,
            "value_loss": value_loss,
        }

    @jax.jit
    def update(current_params, current_optimizer_state, batch):
        (_, metrics), gradients = jax.value_and_grad(loss_fn, has_aux=True)(current_params, batch)
        updates, next_state = optimizer.update(gradients, current_optimizer_state, current_params)
        return optax.apply_updates(current_params, updates), next_state, metrics

    @jax.jit
    def evaluate(current_params, batch):
        return loss_fn(current_params, batch)

    rng = np.random.default_rng(args.seed)
    history = []
    best_loss = float("inf")
    best_params = params
    for epoch in range(1, args.epochs + 1):
        train_metrics = []
        shard_order = list(args.dataset)
        rng.shuffle(shard_order)
        for path in shard_order:
            data = load_dataset(path)
            train = np.flatnonzero(data["split"] == 0)
            for selected in batches(train, args.batch_size, rng):
                params, optimizer_state, metrics = update(params, optimizer_state, make_batch(selected))
                train_metrics.append({key: float(value) for key, value in metrics.items()})
        dev_metrics = []
        for path in args.dataset:
            data = load_dataset(path)
            development = np.flatnonzero(data["split"] == 1)
            for selected in batches(development, args.batch_size):
                _, metrics = evaluate(params, make_batch(selected))
                dev_metrics.append({key: float(value) for key, value in metrics.items()})
        row = {
            "epoch": epoch,
            "train_loss": float(np.mean([value["loss"] for value in train_metrics])),
            "development_loss": float(np.mean([value["loss"] for value in dev_metrics])),
        }
        history.append(row)
        print(json.dumps(row), flush=True)
        if row["development_loss"] < best_loss:
            best_loss = row["development_loss"]
            best_params = params

    probabilities = []
    quantity_predictions = []
    development_presence = []
    development_quantity = []
    for path in args.dataset:
        data = load_dataset(path)
        development = np.flatnonzero(data["split"] == 1)
        if not len(development):
            continue
        development_presence.append(data["presence"][development])
        development_quantity.append(data["quantity_tier"][development])
        for selected in batches(development, args.batch_size):
            output = model.apply(
                {"params": best_params},
                jnp.asarray(data["global"][selected], jnp.float32),
                jnp.asarray(data["board"][selected], jnp.float32),
                jnp.asarray(data["event_type"][selected], jnp.int32),
            )
            probabilities.append(np.asarray(jax.nn.sigmoid(output["presence_logits"])))
            quantity_predictions.append(np.asarray(jnp.argmax(output["quantity_logits"], axis=-1)))
    probability = np.concatenate(probabilities)
    quantity_prediction = np.concatenate(quantity_predictions)
    development_presence_array = np.concatenate(development_presence)
    development_quantity_array = np.concatenate(development_quantity)
    thresholds, calibration = calibrate_thresholds(probability, development_presence_array)
    procurement = len(PROCUREMENT_HEADS)
    predicted = probability[:, :procurement] >= np.asarray(thresholds[:procurement])
    truth = development_presence_array[:, :procurement]
    tp = int(np.sum(predicted & truth))
    fp = int(np.sum(predicted & ~truth))
    positive = development_presence_array
    quantity_accuracy = float(np.sum((quantity_prediction == development_quantity_array) & positive) / max(1, int(positive.sum())))
    payload = {
        "schema": "kaggriculture-v114-v12-event-market-hmoe-v1",
        "architecture": "hard-event-router-three-transaction-experts-v1",
        "strategy_parent": None,
        "inherits_historical_checkpoint": False,
        "historical_agent_online_action_source": False,
        "params": best_params,
        "presence_thresholds": thresholds,
        "transaction_heads": list(TRANSACTION_HEADS),
        "event_types": list(EVENT_TYPES),
        "quantity_tiers": list(QUANTITY_TIERS),
        "training_seed": args.seed,
        "qualification_status": "EVENT_MARKET_BC_WARMSTART_ONLY_NOT_G2_NOT_PPO_NOT_GOLD",
    }
    args.checkpoint.parent.mkdir(parents=True, exist_ok=True)
    args.checkpoint.write_bytes(serialization.msgpack_serialize(payload))
    report = {
        "schema": "kaggriculture-v114-v12-event-market-bc-report-v1",
        "status": "BC_WARMSTART_ONLY_NOT_G2_NOT_PPO_NOT_GOLD",
        "dataset": [str(path.resolve()) for path in args.dataset],
        "dataset_sha256": [hashlib.sha256(path.read_bytes()).hexdigest() for path in args.dataset],
        "checkpoint": str(args.checkpoint.resolve()),
        "checkpoint_sha256": hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
        "train_rows": train_rows,
        "development_rows": development_rows,
        "blind_split_accessed_for_metrics_or_selection": False,
        "best_development_loss": best_loss,
        "procurement_true_positive": tp,
        "procurement_false_positive": fp,
        "procurement_precision": tp / max(1, tp + fp),
        "procurement_recall": tp / max(1, int(truth.sum())),
        "positive_quantity_tier_accuracy": quantity_accuracy,
        "calibration": calibration,
        "history": history,
        "elapsed_seconds": time.time() - started,
    }
    atomic_json(args.report, report)
    print(json.dumps({key: report[key] for key in (
        "status", "checkpoint_sha256", "best_development_loss",
        "procurement_precision", "procurement_recall",
        "positive_quantity_tier_accuracy", "elapsed_seconds"
    )}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
