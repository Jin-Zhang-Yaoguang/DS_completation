"""Train V114's two-level option x functional-role autoregressive HMoE."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time

from flax import serialization
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
from model_nested_hmoe import NestedOptionRoleHMoE  # noqa: E402


MODEL_KEYS = ("global", "board", "units", "unit_mask")
BATCH_KEYS = MODEL_KEYS + (
    "unit_tokens", "unit_quantities", "market_tokens", "market_quantities", "market_mask",
    "option_id", "unit_expert", "market_expert", "value",
)
UNIT_QUANTITY_TOKEN = np.asarray([
    name.startswith("PICKUP:") or name.startswith("PLACE:") for name in space.UNIT_TOKENS
])
MARKET_QUANTITY_TOKEN = np.asarray([
    name not in {"STOP", "HIRE", "BUY_LAND"} for name in space.MARKET_TOKENS
])


def frequency_weights(tokens, mask, classes: int, exponent: float) -> tuple[np.ndarray, np.ndarray]:
    valid = np.asarray(tokens)[np.asarray(mask, dtype=bool)]
    counts = np.bincount(valid.astype(np.int64), minlength=classes).astype(np.float64)
    weights = np.ones((classes,), dtype=np.float32)
    positive = counts > 0
    if exponent > 0 and np.any(positive):
        reference = np.mean(counts[positive])
        weights[positive] = np.power(reference / counts[positive], exponent)
        weights[positive] /= np.mean(weights[positive])
    return weights, counts.astype(np.int64)


def role_weights(labels, indices, classes: int = 6) -> tuple[np.ndarray, np.ndarray]:
    counts = np.bincount(np.asarray(labels)[indices].astype(np.int64), minlength=classes).astype(np.float64)
    weights = np.zeros((classes,), dtype=np.float32)
    positive = counts > 0
    if np.any(positive):
        reference = np.mean(counts[positive])
        weights[positive] = np.sqrt(reference / counts[positive])
        weights[positive] /= np.mean(weights[positive])
    return weights, counts.astype(np.int64)


def weighted_ce(logits, labels, mask, weights):
    loss = optax.softmax_cross_entropy_with_integer_labels(logits, labels.astype(jnp.int32))
    combined = mask.astype(jnp.float32) * weights.astype(jnp.float32)
    denominator = jnp.maximum(1.0, jnp.sum(combined))
    return jnp.sum(loss * combined) / denominator, jnp.sum(
        (jnp.argmax(logits, axis=-1) == labels) * combined
    ) / denominator


def make_loss(
    unit_role_weights, market_role_weights, unit_action_weights, market_action_weights,
    value_coef: float, role_router_coef: float, option_router_coef: float,
):
    unit_role_weights = jnp.asarray(unit_role_weights)
    market_role_weights = jnp.asarray(market_role_weights)
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
        index = jnp.arange(batch["option_id"].shape[0])
        option = batch["option_id"].astype(jnp.int32)
        unit_role = batch["unit_expert"].astype(jnp.int32)
        market_role = batch["market_expert"].astype(jnp.int32)
        unit_sample = unit_role_weights[unit_role]
        market_sample = market_role_weights[market_role]

        unit_logits = output["unit_logits"][index, option, unit_role]
        unit_quantity_logits = output["unit_quantity_logits"][index, option, unit_role]
        market_logits = output["market_logits"][index, option, market_role]
        market_quantity_logits = output["market_quantity_logits"][index, option, market_role]
        unit_mask = batch["unit_mask"]
        market_mask = batch["market_mask"]
        unit_loss, unit_accuracy = weighted_ce(
            unit_logits, batch["unit_tokens"], unit_mask,
            unit_sample[:, None] * unit_action_weights[batch["unit_tokens"]],
        )
        unit_qmask = unit_mask * unit_quantity_lookup[batch["unit_tokens"]]
        unit_q_loss, unit_q_accuracy = weighted_ce(
            unit_quantity_logits, batch["unit_quantities"], unit_qmask,
            unit_sample[:, None],
        )
        market_loss, market_accuracy = weighted_ce(
            market_logits, batch["market_tokens"], market_mask,
            market_sample[:, None] * market_action_weights[batch["market_tokens"]],
        )
        market_qmask = market_mask * market_quantity_lookup[batch["market_tokens"]]
        market_q_loss, market_q_accuracy = weighted_ce(
            market_quantity_logits, batch["market_quantities"], market_qmask,
            market_sample[:, None],
        )
        unit_role_logits = output["unit_role_router_logits"][index, option]
        market_role_logits = output["market_role_router_logits"][index, option]
        unit_router_loss, unit_router_accuracy = weighted_ce(
            unit_role_logits, unit_role, jnp.ones_like(unit_role), unit_sample,
        )
        market_router_loss, market_router_accuracy = weighted_ce(
            market_role_logits, market_role, jnp.ones_like(market_role), market_sample,
        )
        option_router_loss, option_router_accuracy = weighted_ce(
            output["option_router_logits"], option,
            jnp.ones_like(option), jnp.ones_like(option, dtype=jnp.float32),
        )
        predicted_value = output["option_value"][index, option]
        value_loss = jnp.mean((predicted_value - batch["value"]) ** 2)
        total = (
            unit_loss + market_loss + 0.15 * (unit_q_loss + market_q_loss)
            + role_router_coef * (unit_router_loss + market_router_loss)
            + option_router_coef * option_router_loss + value_coef * value_loss
        )
        return total, {
            "loss": total,
            "unit_accuracy": unit_accuracy,
            "unit_quantity_accuracy": unit_q_accuracy,
            "market_accuracy": market_accuracy,
            "market_quantity_accuracy": market_q_accuracy,
            "unit_role_router_accuracy": unit_router_accuracy,
            "market_role_router_accuracy": market_router_accuracy,
            "option_router_accuracy": option_router_accuracy,
            "value_loss": value_loss,
        }
    return loss_fn


def grouped_split(data, seed: int, fraction: float):
    episodes = np.unique(data["episode"])
    if len(episodes) < 2:
        raise ValueError("nested BC requires at least two episodes")
    shuffled = episodes.copy()
    np.random.default_rng(seed).shuffle(shuffled)
    count = min(len(episodes) - 1, max(1, int(round(len(episodes) * fraction))))
    validation_episodes = shuffled[:count]
    validation = np.flatnonzero(np.isin(data["episode"], validation_episodes))
    train = np.flatnonzero(~np.isin(data["episode"], validation_episodes))
    return train, validation, validation_episodes


def batches(data, indices, batch_size: int, rng, shuffle: bool):
    indices = np.asarray(indices).copy()
    if shuffle:
        rng.shuffle(indices)
    stop = len(indices) - batch_size + 1 if shuffle else len(indices)
    for start in range(0, max(0, stop), batch_size):
        selected = indices[start:start + batch_size]
        if len(selected):
            yield {
                key: jnp.asarray(data[key][selected], dtype=jnp.float32)
                if key in MODEL_KEYS or key == "market_mask" else jnp.asarray(data[key][selected])
                for key in BATCH_KEYS
            }


def means(rows):
    return {key: float(np.mean([float(row[key]) for row in rows])) for key in rows[0]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--value-coef", type=float, default=0.05)
    parser.add_argument("--role-router-coef", type=float, default=0.35)
    parser.add_argument("--option-router-coef", type=float, default=0.0)
    parser.add_argument("--action-weight-exponent", type=float, default=0.25)
    parser.add_argument("--day-start-repeat", type=int, default=2)
    parser.add_argument("--validation-fraction", type=float, default=0.25)
    parser.add_argument("--seed", type=int, default=114700)
    args = parser.parse_args()
    if args.value_coef <= 0:
        parser.error("--value-coef must be positive under PPO v4")
    if args.option_router_coef != 0:
        parser.error("teacher identity may not supervise the V114 option router")
    started = time.time()
    with np.load(args.dataset, allow_pickle=False) as archive:
        data = {key: archive[key] for key in archive.files}
    missing = set(BATCH_KEYS + ("episode", "step")) - set(data)
    if missing:
        raise ValueError(f"dataset missing keys: {sorted(missing)}")
    train_indices, validation_indices, validation_episodes = grouped_split(
        data, args.seed, args.validation_fraction
    )
    day_start = train_indices[np.asarray(data["step"])[train_indices] % 24 == 0]
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
    unit_role_weight, unit_role_counts = role_weights(data["unit_expert"], train_indices)
    market_role_weight, market_role_counts = role_weights(data["market_expert"], train_indices)

    model = NestedOptionRoleHMoE(timed=True)
    example = {key: jnp.asarray(data[key][:1]) for key in MODEL_KEYS}
    params = model.init(
        jax.random.key(args.seed), *(example[key] for key in MODEL_KEYS),
        jnp.asarray(data["unit_tokens"][:1]), jnp.asarray(data["unit_quantities"][:1]),
        jnp.asarray(data["market_tokens"][:1]), jnp.asarray(data["market_quantities"][:1]),
    )["params"]
    optimizer = optax.chain(
        optax.clip_by_global_norm(0.5),
        optax.adamw(args.learning_rate, weight_decay=1e-5),
    )
    state = TrainState.create(apply_fn=model.apply, params=params, tx=optimizer)
    loss_fn = make_loss(
        unit_role_weight, market_role_weight, unit_action_weights, market_action_weights,
        args.value_coef, args.role_router_coef, args.option_router_coef,
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
    checkpoint_path = args.output_dir / "nested_bc_best.msgpack"
    dataset_sha = hashlib.sha256(args.dataset.read_bytes()).hexdigest()
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
            payload = {
                "params": best_params,
                "model_id": "v114_day_smdp_hmoe_ppo_nested_bc_v1",
                "strategy_parent": None,
                "evidence_parent": "v113_stage35_closed_loop_teacher_data_only",
                "architecture": "v114-nested-option-role-autoregressive-hmoe-v1",
                "option_router_granularity": "day_or_event_untrained",
                "role_router_granularity": "step",
                "dataset_sha256": dataset_sha,
                "training_seed": args.seed,
                "inherits_v113_checkpoint": False,
                "online_historical_agent_fallback": False,
                "qualification_status": "BC_INIT_NOT_EXPERT_QUALIFIED_NOT_GOLD",
            }
            with tempfile.NamedTemporaryFile("wb", dir=args.output_dir, delete=False) as sink:
                sink.write(serialization.msgpack_serialize(payload))
                temporary = Path(sink.name)
            temporary.replace(checkpoint_path)
        print(json.dumps(row, ensure_ascii=False), flush=True)

    report = {
        "schema": "kaggriculture-v114-nested-bc-training-v1",
        "best_validation_loss": best_loss,
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": hashlib.sha256(checkpoint_path.read_bytes()).hexdigest(),
        "dataset": str(args.dataset),
        "dataset_sha256": dataset_sha,
        "training_seed": args.seed,
        "strategy_parent": None,
        "inherits_v113_checkpoint": False,
        "history": history,
        "train_rows": int(len(train_indices)),
        "sampled_train_rows": int(len(sampled_train)),
        "validation_rows": int(len(validation_indices)),
        "validation_episodes": [int(value) for value in validation_episodes],
        "unit_role_counts": unit_role_counts.tolist(),
        "market_role_counts": market_role_counts.tolist(),
        "unit_action_counts": unit_action_counts.tolist(),
        "market_action_counts": market_action_counts.tolist(),
        "value_coefficient": args.value_coef,
        "role_router_coefficient": args.role_router_coef,
        "option_router_coefficient": args.option_router_coef,
        "elapsed_seconds": time.time() - started,
    }
    (args.output_dir / "training_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "best_validation_loss": best_loss,
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": report["checkpoint_sha256"],
        "elapsed_seconds": report["elapsed_seconds"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
