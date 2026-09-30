"""Train V114 option policies with independent unit/order role routing."""

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
from model_per_slot_hmoe import PerSlotOptionRoleHMoE  # noqa: E402
from model_latent_role_hmoe import LatentRoleHMoE  # noqa: E402
from train_nested_bc import (  # noqa: E402
    MARKET_QUANTITY_TOKEN, MODEL_KEYS, UNIT_QUANTITY_TOKEN,
    frequency_weights, grouped_split, means, weighted_ce,
)


BATCH_KEYS = MODEL_KEYS + (
    "unit_tokens", "unit_quantities", "market_tokens", "market_quantities", "market_mask",
    "unit_roles", "market_roles", "option_id", "value",
)


def slot_role_weights(labels, mask, indices, classes: int):
    selected = np.asarray(labels)[indices]
    active = np.asarray(mask)[indices].astype(bool)
    counts = np.bincount(selected[active].astype(np.int64), minlength=classes).astype(np.float64)
    weights = np.ones((classes,), dtype=np.float32)
    positive = counts > 0
    reference = np.mean(counts[positive])
    weights[positive] = np.sqrt(reference / counts[positive])
    weights[positive] /= np.mean(weights[positive])
    return weights, counts.astype(np.int64)


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


def make_loss(
    unit_role_weight, market_role_weight, unit_action_weight, market_action_weight,
    value_coef: float, role_router_coef: float,
):
    unit_role_weight = jnp.asarray(unit_role_weight)
    market_role_weight = jnp.asarray(market_role_weight)
    unit_action_weight = jnp.asarray(unit_action_weight)
    market_action_weight = jnp.asarray(market_action_weight)
    unit_quantity_lookup = jnp.asarray(UNIT_QUANTITY_TOKEN)
    market_quantity_lookup = jnp.asarray(MARKET_QUANTITY_TOKEN)

    def loss_fn(params, apply_fn, batch):
        output = apply_fn(
            {"params": params}, *(batch[key] for key in MODEL_KEYS),
            batch["unit_tokens"], batch["unit_quantities"],
            batch["market_tokens"], batch["market_quantities"],
            batch["unit_roles"], batch["market_roles"],
        )
        index = jnp.arange(batch["option_id"].shape[0])
        option = batch["option_id"].astype(jnp.int32)
        unit_mask, market_mask = batch["unit_mask"], batch["market_mask"]
        unit_logits = output["unit_logits"][index, option]
        unit_quantity_logits = output["unit_quantity_logits"][index, option]
        market_logits = output["market_logits"][index, option]
        market_quantity_logits = output["market_quantity_logits"][index, option]

        unit_loss, unit_accuracy = weighted_ce(
            unit_logits, batch["unit_tokens"], unit_mask,
            unit_action_weight[batch["unit_tokens"]],
        )
        unit_qmask = unit_mask * unit_quantity_lookup[batch["unit_tokens"]]
        unit_q_loss, unit_q_accuracy = weighted_ce(
            unit_quantity_logits, batch["unit_quantities"], unit_qmask,
            jnp.ones_like(unit_qmask),
        )
        market_loss, market_accuracy = weighted_ce(
            market_logits, batch["market_tokens"], market_mask,
            market_action_weight[batch["market_tokens"]],
        )
        market_qmask = market_mask * market_quantity_lookup[batch["market_tokens"]]
        market_q_loss, market_q_accuracy = weighted_ce(
            market_quantity_logits, batch["market_quantities"], market_qmask,
            jnp.ones_like(market_qmask),
        )
        unit_role_logits = output["unit_role_logits"][index, option]
        market_role_logits = output["market_role_logits"][index, option]
        unit_role_loss, unit_role_accuracy = weighted_ce(
            unit_role_logits, batch["unit_roles"], unit_mask,
            unit_role_weight[batch["unit_roles"]],
        )
        market_role_loss, market_role_accuracy = weighted_ce(
            market_role_logits, batch["market_roles"], market_mask,
            market_role_weight[batch["market_roles"]],
        )
        predicted_value = output["option_value"][index, option]
        value_loss = jnp.mean((predicted_value - batch["value"]) ** 2)
        total = (
            unit_loss + market_loss + 0.15 * (unit_q_loss + market_q_loss)
            + role_router_coef * (unit_role_loss + market_role_loss)
            + value_coef * value_loss
        )
        return total, {
            "loss": total,
            "unit_accuracy": unit_accuracy,
            "unit_quantity_accuracy": unit_q_accuracy,
            "market_accuracy": market_accuracy,
            "market_quantity_accuracy": market_q_accuracy,
            "unit_slot_role_accuracy": unit_role_accuracy,
            "market_slot_role_accuracy": market_role_accuracy,
            "value_loss": value_loss,
        }
    return loss_fn


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--value-coef", type=float, default=0.05)
    parser.add_argument("--role-router-coef", type=float, default=0.35)
    parser.add_argument("--action-weight-exponent", type=float, default=0.25)
    parser.add_argument("--day-start-repeat", type=int, default=2)
    parser.add_argument("--validation-fraction", type=float, default=0.25)
    parser.add_argument("--seed", type=int, default=114800)
    parser.add_argument(
        "--model-kind", choices=("teacher-role", "latent-role"),
        default="teacher-role",
        help="latent-role never conditions action decoding on teacher role labels",
    )
    args = parser.parse_args()
    if args.value_coef <= 0:
        parser.error("--value-coef must be positive under PPO v4")
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
    unit_action_weight, unit_action_counts = frequency_weights(
        data["unit_tokens"][train_indices], data["unit_mask"][train_indices],
        len(space.UNIT_TOKENS), args.action_weight_exponent,
    )
    market_action_weight, market_action_counts = frequency_weights(
        data["market_tokens"][train_indices], data["market_mask"][train_indices],
        len(space.MARKET_TOKENS), args.action_weight_exponent,
    )
    unit_role_weight, unit_role_counts = slot_role_weights(
        data["unit_roles"], data["unit_mask"], train_indices, 4
    )
    market_role_weight, market_role_counts = slot_role_weights(
        data["market_roles"], data["market_mask"], train_indices, 3
    )

    model = (
        LatentRoleHMoE(timed=True)
        if args.model_kind == "latent-role"
        else PerSlotOptionRoleHMoE(timed=True)
    )
    example = {key: jnp.asarray(data[key][:1]) for key in MODEL_KEYS}
    params = model.init(
        jax.random.key(args.seed), *(example[key] for key in MODEL_KEYS),
        jnp.asarray(data["unit_tokens"][:1]), jnp.asarray(data["unit_quantities"][:1]),
        jnp.asarray(data["market_tokens"][:1]), jnp.asarray(data["market_quantities"][:1]),
        jnp.asarray(data["unit_roles"][:1]), jnp.asarray(data["market_roles"][:1]),
    )["params"]
    state = TrainState.create(
        apply_fn=model.apply, params=params,
        tx=optax.chain(
            optax.clip_by_global_norm(0.5),
            optax.adamw(args.learning_rate, weight_decay=1e-5),
        ),
    )
    loss_fn = make_loss(
        unit_role_weight, market_role_weight, unit_action_weight, market_action_weight,
        args.value_coef, args.role_router_coef,
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
    checkpoint_name = (
        "latent_role_bc_best.msgpack"
        if args.model_kind == "latent-role" else "per_slot_bc_best.msgpack"
    )
    checkpoint_path = args.output_dir / checkpoint_name
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
            is_latent = args.model_kind == "latent-role"
            payload = {
                "params": best_params,
                "model_id": (
                    "v114_day_smdp_hmoe_ppo_latent_role_bc_v1"
                    if is_latent else "v114_day_smdp_hmoe_ppo_per_slot_bc_v1"
                ),
                "strategy_parent": None,
                "evidence_parent": "v113_stage35_closed_loop_teacher_data_only",
                "architecture": (
                    "v114-causal-latent-role-absorbing-stop-hmoe-v1"
                    if is_latent else "v114-per-slot-option-role-autoregressive-hmoe-v1"
                ),
                "option_router_granularity": "day_or_event_untrained",
                "role_router_granularity": "unit_and_order_slot",
                "teacher_role_conditions_action_decoder": not is_latent,
                "market_stop_contract": (
                    "absorbing_tail" if is_latent else "first_stop_only"
                ),
                "terminal_boundary": 671,
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
        "schema": (
            "kaggriculture-v114-latent-role-bc-training-v1"
            if args.model_kind == "latent-role"
            else "kaggriculture-v114-per-slot-bc-training-v1"
        ),
        "model_kind": args.model_kind,
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
