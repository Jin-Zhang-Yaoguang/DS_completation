"""Behavior-clone the fully autoregressive Hierarchical MoE joint action policy."""

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

import action_space as space
from model_sequence_action import NUM_EXPERTS, SequenceActionHMoEActorCritic
from train_bc_factorized import expert_weights, frequency_weights, masked_ce


MODEL_KEYS = ("global", "board", "units", "unit_mask")
BATCH_KEYS = MODEL_KEYS + (
    "unit_tokens", "unit_quantities", "market_tokens", "market_quantities", "market_mask",
    "unit_expert", "market_expert", "value",
)
UNIT_QUANTITY_TOKEN = np.asarray([
    name.startswith("PICKUP:") or name.startswith("PLACE:") for name in space.UNIT_TOKENS
])
MARKET_QUANTITY_TOKEN = np.asarray([
    name not in {"STOP", "HIRE", "BUY_LAND"} for name in space.MARKET_TOKENS
])


def make_loss(
    unit_class_weights, market_class_weights,
    unit_action_weights, market_action_weights, value_coef, router_coef,
):
    unit_class_weights = jnp.asarray(unit_class_weights)
    market_class_weights = jnp.asarray(market_class_weights)
    unit_action_weights = jnp.asarray(unit_action_weights)
    market_action_weights = jnp.asarray(market_action_weights)
    unit_quantity_lookup = jnp.asarray(UNIT_QUANTITY_TOKEN)
    market_quantity_lookup = jnp.asarray(MARKET_QUANTITY_TOKEN)

    def loss_fn(params, apply_fn, batch):
        output = apply_fn(
            {"params": params}, *(batch[key] for key in MODEL_KEYS),
            batch["unit_tokens"], batch["unit_quantities"],
            batch["market_tokens"], batch["market_quantities"],
        )
        index = jnp.arange(batch["unit_expert"].shape[0])
        unit_expert = batch["unit_expert"].astype(jnp.int32)
        market_expert = batch["market_expert"].astype(jnp.int32)
        unit_sample_weight = unit_class_weights[unit_expert]
        market_sample_weight = market_class_weights[market_expert]
        unit_logits = output["unit_logits"][index, unit_expert]
        unit_quantity_logits = output["unit_quantity_logits"][index, unit_expert]
        market_logits = output["market_logits"][index, market_expert]
        market_quantity_logits = output["market_quantity_logits"][index, market_expert]
        unit_mask, market_mask = batch["unit_mask"], batch["market_mask"]
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
            output["unit_router_logits"], unit_expert,
            jnp.ones_like(unit_expert), unit_sample_weight,
        )
        market_router_loss, market_router_accuracy = masked_ce(
            output["market_router_logits"], market_expert,
            jnp.ones_like(market_expert), market_sample_weight,
        )
        value_loss = jnp.mean((output["value"] - batch["value"]) ** 2)
        total = (
            unit_loss + market_loss
            + 0.15 * (unit_quantity_loss + market_quantity_loss)
            + router_coef * (unit_router_loss + market_router_loss)
            + value_coef * value_loss
            + 0.01 * jnp.mean(output["opponent_gate"])
        )
        return total, {
            "loss": total, "unit_accuracy": unit_accuracy,
            "unit_quantity_accuracy": unit_quantity_accuracy,
            "market_accuracy": market_accuracy,
            "market_quantity_accuracy": market_quantity_accuracy,
            "unit_router_accuracy": unit_router_accuracy,
            "market_router_accuracy": market_router_accuracy,
            "value_loss": value_loss,
        }
    return loss_fn


def grouped_split(data, seed, validation_fraction, eligible_indices=None):
    eligible = (
        np.arange(len(data["episode"]), dtype=np.int64)
        if eligible_indices is None else np.asarray(eligible_indices, dtype=np.int64)
    )
    episodes = np.unique(data["episode"][eligible])
    if len(episodes) < 2:
        raise ValueError("sequence BC requires at least two distinct seeds")
    shuffled = episodes.copy()
    np.random.default_rng(seed).shuffle(shuffled)
    count = min(len(episodes) - 1, max(1, int(round(len(episodes) * validation_fraction))))
    validation = shuffled[:count]
    mask = np.isin(data["episode"][eligible], validation)
    return eligible[~mask], eligible[mask], validation


def batches(data, indices, batch_size, rng, shuffle):
    indices = np.asarray(indices).copy()
    if shuffle:
        rng.shuffle(indices)
    stop = len(indices) - batch_size + 1 if shuffle else len(indices)
    for start in range(0, max(0, stop), batch_size):
        selected = indices[start:start + batch_size]
        if len(selected) == 0:
            continue
        yield {
            key: jnp.asarray(data[key][selected], dtype=jnp.float32)
            if key in MODEL_KEYS or key == "market_mask" else jnp.asarray(data[key][selected])
            for key in BATCH_KEYS
        }


def means(rows):
    if not rows:
        raise ValueError("empty metric rows; reduce batch size or add data")
    return {key: float(np.mean([float(row[key]) for row in rows])) for key in rows[0]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, nargs="+", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=16)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--value-coef", type=float, default=0.05)
    parser.add_argument("--router-coef", type=float, default=0.35)
    parser.add_argument("--seed", type=int, default=1179000)
    parser.add_argument("--validation-fraction", type=float, default=0.25)
    parser.add_argument("--day-start-repeat", type=int, default=4)
    parser.add_argument("--action-weight-exponent", type=float, default=0.0)
    parser.add_argument("--init-checkpoint", type=Path)
    parser.add_argument("--timed", action="store_true")
    parser.add_argument(
        "--leave-out-teacher-family",
        help=(
            "Exclude one teacher_family from optimization. Checkpoint selection uses a "
            "seed-grouped split of the remaining families; held-out metrics are reported only."
        ),
    )
    parser.add_argument(
        "--train-expert-projections-only", action="store_true",
        help="Freeze shared encoder/decoder parameters and specialize expert projections only.",
    )
    parser.add_argument(
        "--expert-projection-scope", choices=("both", "unit", "market"), default="both",
    )
    args = parser.parse_args()
    if args.router_coef < 0:
        parser.error("--router-coef must be non-negative")
    started = time.time()
    shards = []
    for path in args.dataset:
        with np.load(path) as archive:
            shards.append({key: archive[key] for key in archive.files})
    keys = set.intersection(*(set(shard) for shard in shards))
    missing = set(BATCH_KEYS + ("episode", "step")) - keys
    if missing:
        raise ValueError(f"datasets missing sequence keys: {sorted(missing)}")
    data = {key: np.concatenate([shard[key] for shard in shards]) for key in keys}
    heldout_indices = np.asarray([], dtype=np.int64)
    eligible_indices = None
    if args.leave_out_teacher_family:
        if "teacher_family" not in data:
            raise ValueError("leave-one-family-out requires teacher_family in every dataset")
        family = np.asarray(data["teacher_family"]).astype(str)
        heldout_indices = np.flatnonzero(family == args.leave_out_teacher_family)
        eligible_indices = np.flatnonzero(family != args.leave_out_teacher_family)
        if len(heldout_indices) == 0 or len(eligible_indices) == 0:
            raise ValueError("leave-one-family-out produced an empty held-out or training set")
    train_indices, validation_indices, validation_episodes = grouped_split(
        data, args.seed, args.validation_fraction, eligible_indices
    )
    day_start = train_indices[np.asarray(data["step"][train_indices]) % 24 == 0]
    sampled_train = np.concatenate(
        [train_indices] + [day_start] * (max(1, args.day_start_repeat) - 1)
    )
    unit_action_weights, unit_action_counts = frequency_weights(
        data["unit_tokens"][train_indices], data["unit_mask"][train_indices],
        len(space.UNIT_TOKENS), args.action_weight_exponent,
    )
    market_action_weights, market_action_counts = frequency_weights(
        data["market_tokens"][train_indices], data["market_mask"][train_indices],
        len(space.MARKET_TOKENS), args.action_weight_exponent,
    )
    unit_class_weights, unit_class_counts = expert_weights(data["unit_expert"], train_indices)
    market_class_weights, market_class_counts = expert_weights(data["market_expert"], train_indices)
    model = SequenceActionHMoEActorCritic(timed=args.timed)
    example = {key: jnp.asarray(data[key][:1]) for key in MODEL_KEYS}
    params = model.init(
        jax.random.key(args.seed), *(example[key] for key in MODEL_KEYS),
        jnp.asarray(data["unit_tokens"][:1]), jnp.asarray(data["unit_quantities"][:1]),
        jnp.asarray(data["market_tokens"][:1]), jnp.asarray(data["market_quantities"][:1]),
    )["params"]
    if args.init_checkpoint:
        payload = serialization.msgpack_restore(args.init_checkpoint.read_bytes())
        params = payload["params"]
    train_optimizer = optax.chain(
        optax.clip_by_global_norm(0.5),
        optax.adamw(args.learning_rate, weight_decay=1e-5),
    )
    if args.train_expert_projections_only:
        projection_modules = {
            "both": {"unit_expert_projection", "market_expert_projection"},
            "unit": {"unit_expert_projection"},
            "market": {"market_expert_projection"},
        }[args.expert_projection_scope]
        flat = traverse_util.flatten_dict(params)
        labels = traverse_util.unflatten_dict({
            path: "train" if path[0] in projection_modules else "freeze"
            for path in flat
        })
        optimizer = optax.multi_transform(
            {"train": train_optimizer, "freeze": optax.set_to_zero()}, labels
        )
    else:
        optimizer = train_optimizer
    state = TrainState.create(apply_fn=model.apply, params=params, tx=optimizer)
    loss_fn = make_loss(
        unit_class_weights, market_class_weights,
        unit_action_weights, market_action_weights, args.value_coef, args.router_coef,
    )

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
    checkpoint_path = args.output_dir / "bc_best.msgpack"
    dataset_hashes = [hashlib.sha256(path.read_bytes()).hexdigest() for path in args.dataset]

    def save_best(params, history, best_loss):
        checkpoint = {
            "params": params, "model_id": "v113_sequence_action_hmoe_ppo",
            "strategy_parent": None,
            "router_granularity": "step",
            "router_period": 1,
            "architecture": (
                "timed-joint-autoregressive-action-hmoe-v1"
                if args.timed else "joint-autoregressive-action-hmoe-v1"
            ),
            "dataset_sha256": dataset_hashes,
        }
        with tempfile.NamedTemporaryFile("wb", dir=args.output_dir, delete=False) as sink:
            sink.write(serialization.msgpack_serialize(checkpoint))
            temporary = Path(sink.name)
        temporary.replace(checkpoint_path)
        progress = {
            "schema": "kaggriculture-v113-sequence-action-bc-progress-v1",
            "completed_epochs": len(history),
            "best_validation_loss": best_loss,
            "checkpoint": str(checkpoint_path),
            "history": history,
        }
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=args.output_dir, delete=False
        ) as sink:
            json.dump(progress, sink, ensure_ascii=False, indent=2)
            sink.write("\n")
            temporary = Path(sink.name)
        temporary.replace(args.output_dir / "bc_progress.json")

    rng = np.random.default_rng(args.seed)
    history, best_loss, best_params = [], float("inf"), state.params
    for epoch in range(1, args.epochs + 1):
        train_rows = []
        for batch in batches(data, sampled_train, args.batch_size, rng, True):
            state, metrics = train_step(state, batch)
            train_rows.append(jax.device_get(metrics))
        validation_rows = [jax.device_get(eval_step(state, batch)) for batch in batches(
            data, validation_indices, args.batch_size, rng, False
        )]
        row = {"epoch": epoch, "train": means(train_rows), "validation": means(validation_rows)}
        history.append(row)
        if row["validation"]["loss"] < best_loss:
            best_loss, best_params = row["validation"]["loss"], jax.device_get(state.params)
            save_best(best_params, history, best_loss)
        print(json.dumps(row, ensure_ascii=False), flush=True)

    checkpoint = {
        "params": best_params, "model_id": "v113_sequence_action_hmoe_ppo",
        "strategy_parent": None,
        "router_granularity": "step",
        "router_period": 1,
        "architecture": (
            "timed-joint-autoregressive-action-hmoe-v1"
            if args.timed else "joint-autoregressive-action-hmoe-v1"
        ),
        "dataset_sha256": dataset_hashes,
    }
    with tempfile.NamedTemporaryFile("wb", dir=args.output_dir, delete=False) as sink:
        sink.write(serialization.msgpack_serialize(checkpoint))
        temporary = Path(sink.name)
    temporary.replace(checkpoint_path)
    best_state = state.replace(params=best_params)
    heldout_metrics = None
    heldout_by_teacher = {}
    if len(heldout_indices):
        heldout_metrics = means([
            jax.device_get(eval_step(best_state, batch))
            for batch in batches(data, heldout_indices, args.batch_size, rng, False)
        ])
        if "teacher_id" in data:
            teacher_ids = np.asarray(data["teacher_id"]).astype(str)
            for teacher_id in sorted(set(teacher_ids[heldout_indices])):
                selected = heldout_indices[teacher_ids[heldout_indices] == teacher_id]
                heldout_by_teacher[teacher_id] = means([
                    jax.device_get(eval_step(best_state, batch))
                    for batch in batches(data, selected, args.batch_size, rng, False)
                ])
    report = {
        "schema": "kaggriculture-v113-sequence-action-bc-v1",
        "best_validation_loss": best_loss, "checkpoint": str(checkpoint_path),
        "history": history, "train_rows": int(len(train_indices)),
        "sampled_train_rows": int(len(sampled_train)),
        "validation_rows": int(len(validation_indices)),
        "validation_episodes": [int(value) for value in validation_episodes],
        "leave_out_teacher_family": args.leave_out_teacher_family,
        "heldout_rows": int(len(heldout_indices)),
        "heldout_metrics": heldout_metrics,
        "heldout_by_teacher": heldout_by_teacher,
        "unit_expert_counts": unit_class_counts.tolist(),
        "market_expert_counts": market_class_counts.tolist(),
        "unit_action_counts": unit_action_counts.tolist(),
        "market_action_counts": market_action_counts.tolist(),
        "action_weight_exponent": args.action_weight_exponent,
        "router_coefficient": args.router_coef,
        "init_checkpoint": str(args.init_checkpoint) if args.init_checkpoint else None,
        "timed": args.timed,
        "trainable_scope": (
            f"expert_projections_only:{args.expert_projection_scope}"
            if args.train_expert_projections_only else "all_except_none"
        ),
        "elapsed_seconds": time.time() - started,
    }
    (args.output_dir / "bc_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: report[key] for key in (
        "best_validation_loss", "checkpoint", "elapsed_seconds",
    )}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
