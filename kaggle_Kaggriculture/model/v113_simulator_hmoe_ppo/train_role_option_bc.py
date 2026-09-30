"""Train V113's role/target manager and option-conditioned full-action worker."""

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
from model_role_option import NUM_EXPERTS, RoleOptionHMoEActorCritic
from model_staged_option import StagedOptionHMoEActorCritic
from train_bc_factorized import frequency_weights, masked_ce


MODEL_KEYS = ("global", "board", "units", "unit_mask")
BATCH_KEYS = MODEL_KEYS + (
    "unit_tokens", "unit_quantities", "market_tokens", "market_quantities", "market_mask",
    "unit_expert", "market_expert", "option_roles", "option_targets", "value",
)
UNIT_QUANTITY_TOKEN = np.asarray([name.startswith("PICKUP:") or name.startswith("PLACE:") for name in space.UNIT_TOKENS])
MARKET_QUANTITY_TOKEN = np.asarray([name not in {"STOP", "HIRE", "BUY_LAND"} for name in space.MARKET_TOKENS])


def make_loss(unit_action_weights, market_action_weights, value_coef, staged_option=False):
    unit_action_weights = jnp.asarray(unit_action_weights)
    market_action_weights = jnp.asarray(market_action_weights)
    unit_quantity_lookup = jnp.asarray(UNIT_QUANTITY_TOKEN)
    market_quantity_lookup = jnp.asarray(MARKET_QUANTITY_TOKEN)

    def loss_fn(params, apply_fn, batch):
        if staged_option:
            output = apply_fn(
                {"params": params}, *(batch[key] for key in MODEL_KEYS),
                batch["option_stages"], batch["option_targets"],
                batch["market_tokens"], batch["market_quantities"],
            )
            option_logits = output["option_stage_logits"]
            option_labels = batch["option_stages"]
        else:
            output = apply_fn(
                {"params": params}, *(batch[key] for key in MODEL_KEYS),
                batch["option_roles"], batch["option_targets"],
            )
            option_logits = output["option_role_logits"]
            option_labels = batch["option_roles"]
        index = jnp.arange(batch["unit_expert"].shape[0])
        unit_expert = batch["unit_expert"].astype(jnp.int32)
        market_expert = batch["market_expert"].astype(jnp.int32)
        unit_logits = output["unit_logits"][index, unit_expert]
        unit_quantity_logits = output["unit_quantity_logits"][index, unit_expert]
        market_logits = output["market_logits"][index, market_expert]
        market_quantity_logits = output["market_quantity_logits"][index, market_expert]
        unit_mask, market_mask = batch["unit_mask"], batch["market_mask"]
        unit_loss, unit_accuracy = masked_ce(
            unit_logits, batch["unit_tokens"], unit_mask, unit_action_weights[batch["unit_tokens"]]
        )
        unit_quantity_mask = unit_mask * unit_quantity_lookup[batch["unit_tokens"]]
        unit_quantity_loss, unit_quantity_accuracy = masked_ce(
            unit_quantity_logits, batch["unit_quantities"], unit_quantity_mask,
            jnp.ones_like(unit_quantity_mask),
        )
        market_loss, market_accuracy = masked_ce(
            market_logits, batch["market_tokens"], market_mask,
            market_action_weights[batch["market_tokens"]],
        )
        market_quantity_mask = market_mask * market_quantity_lookup[batch["market_tokens"]]
        market_quantity_loss, market_quantity_accuracy = masked_ce(
            market_quantity_logits, batch["market_quantities"], market_quantity_mask,
            jnp.ones_like(market_quantity_mask),
        )
        manager_role_loss, manager_role_accuracy = masked_ce(
            option_logits, option_labels, unit_mask,
            jnp.ones_like(unit_mask),
        )
        manager_target_loss, manager_target_accuracy = masked_ce(
            output["option_target_logits"], batch["option_targets"], unit_mask,
            jnp.ones_like(unit_mask),
        )
        unit_router_loss, unit_router_accuracy = masked_ce(
            output["unit_router_logits"], unit_expert, jnp.ones_like(unit_expert), jnp.ones_like(unit_expert)
        )
        market_router_loss, market_router_accuracy = masked_ce(
            output["market_router_logits"], market_expert, jnp.ones_like(market_expert), jnp.ones_like(market_expert)
        )
        value_loss = jnp.mean((output["value"] - batch["value"]) ** 2)
        total = (
            unit_loss + market_loss + 0.15 * (unit_quantity_loss + market_quantity_loss)
            + 0.5 * manager_role_loss + 0.75 * manager_target_loss
            + 0.2 * (unit_router_loss + market_router_loss) + value_coef * value_loss
        )
        return total, {
            "loss": total, "unit_accuracy": unit_accuracy, "market_accuracy": market_accuracy,
            "unit_quantity_accuracy": unit_quantity_accuracy,
            "market_quantity_accuracy": market_quantity_accuracy,
            "manager_role_accuracy": manager_role_accuracy,
            "manager_target_accuracy": manager_target_accuracy,
            "unit_router_accuracy": unit_router_accuracy,
            "market_router_accuracy": market_router_accuracy,
            "value_loss": value_loss,
        }
    return loss_fn


def make_batches(data, indices, batch_size, rng, shuffle, batch_keys=BATCH_KEYS):
    indices = np.asarray(indices).copy()
    if shuffle:
        rng.shuffle(indices)
    for start in range(0, len(indices) - batch_size + 1, batch_size):
        selected = indices[start:start + batch_size]
        yield {
            key: jnp.asarray(data[key][selected], dtype=jnp.float32)
            if key in MODEL_KEYS or key == "market_mask" else jnp.asarray(data[key][selected])
            for key in batch_keys
        }


def means(rows):
    if not rows:
        raise ValueError("metric rows are empty; check train/validation split and batch size")
    return {key: float(np.mean([float(row[key]) for row in rows])) for key in rows[0]}


def grouped_episode_split(data, seed, validation_fraction):
    """Create a deterministic split without leaking steps from one game across folds."""
    episodes = np.unique(data["episode"])
    if len(episodes) < 2:
        raise ValueError("role-option BC needs at least two episodes for grouped validation")
    validation_count = min(
        len(episodes) - 1,
        max(1, int(round(len(episodes) * validation_fraction))),
    )
    shuffled = episodes.copy()
    np.random.default_rng(seed).shuffle(shuffled)
    validation_episodes = shuffled[:validation_count]
    validation_mask = np.isin(data["episode"], validation_episodes)
    return np.flatnonzero(~validation_mask), np.flatnonzero(validation_mask), validation_episodes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, nargs="+", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--value-coef", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=1159000)
    parser.add_argument("--validation-fraction", type=float, default=0.25)
    parser.add_argument(
        "--day-start-repeat", type=int, default=1,
        help="Repeat hour-0 rows in the training sampler to preserve rare setup/restock decisions.",
    )
    parser.add_argument("--staged-option", action="store_true")
    args = parser.parse_args()
    started = time.time()
    shards = []
    for path in args.dataset:
        with np.load(path) as archive:
            shards.append({key: archive[key] for key in archive.files})
    keys = set.intersection(*(set(shard) for shard in shards))
    batch_keys = BATCH_KEYS
    if args.staged_option:
        batch_keys = tuple(key for key in BATCH_KEYS if key != "option_roles") + ("option_stages",)
    missing = set(batch_keys + ("episode", "step")) - keys
    if missing:
        raise ValueError(f"datasets missing role-option keys: {sorted(missing)}")
    data = {key: np.concatenate([shard[key] for shard in shards]) for key in keys}
    if not 0.0 < args.validation_fraction < 1.0:
        raise ValueError("--validation-fraction must be between 0 and 1")
    train_indices, validation_indices, validation_episodes = grouped_episode_split(
        data, args.seed, args.validation_fraction
    )
    if args.day_start_repeat < 1:
        raise ValueError("--day-start-repeat must be at least 1")
    day_start_indices = train_indices[np.asarray(data["step"][train_indices]) % 24 == 0]
    sampled_train_indices = np.concatenate(
        [train_indices] + [day_start_indices] * (args.day_start_repeat - 1)
    )
    unit_weights, _ = frequency_weights(
        data["unit_tokens"][train_indices], data["unit_mask"][train_indices], len(space.UNIT_TOKENS), 0.65
    )
    market_weights, _ = frequency_weights(
        data["market_tokens"][train_indices], data["market_mask"][train_indices], len(space.MARKET_TOKENS), 0.65
    )
    model = StagedOptionHMoEActorCritic() if args.staged_option else RoleOptionHMoEActorCritic()
    example = {key: jnp.asarray(data[key][:1]) for key in MODEL_KEYS}
    if args.staged_option:
        params = model.init(
            jax.random.key(args.seed), *(example[key] for key in MODEL_KEYS),
            jnp.asarray(data["option_stages"][:1]), jnp.asarray(data["option_targets"][:1]),
            jnp.asarray(data["market_tokens"][:1]), jnp.asarray(data["market_quantities"][:1]),
        )["params"]
    else:
        params = model.init(
            jax.random.key(args.seed), *(example[key] for key in MODEL_KEYS),
            jnp.asarray(data["option_roles"][:1]), jnp.asarray(data["option_targets"][:1]),
        )["params"]
    state = TrainState.create(
        apply_fn=model.apply, params=params,
        tx=optax.chain(optax.clip_by_global_norm(0.5), optax.adamw(args.learning_rate, weight_decay=1e-5)),
    )
    loss_fn = make_loss(unit_weights, market_weights, args.value_coef, args.staged_option)

    @jax.jit
    def train_step(s, batch):
        (_, metrics), gradients = jax.value_and_grad(loss_fn, has_aux=True)(s.params, s.apply_fn, batch)
        return s.apply_gradients(grads=gradients), metrics

    @jax.jit
    def eval_step(s, batch):
        return loss_fn(s.params, s.apply_fn, batch)[1]

    rng = np.random.default_rng(args.seed)
    history, best_loss, best_params = [], float("inf"), state.params
    for epoch in range(1, args.epochs + 1):
        train_rows = []
        for batch in make_batches(data, sampled_train_indices, args.batch_size, rng, True, batch_keys):
            state, metrics = train_step(state, batch)
            train_rows.append(jax.device_get(metrics))
        validation_rows = [jax.device_get(eval_step(state, batch)) for batch in make_batches(
            data, validation_indices, args.batch_size, rng, False, batch_keys
        )]
        row = {"epoch": epoch, "train": means(train_rows), "validation": means(validation_rows)}
        history.append(row)
        if row["validation"]["loss"] < best_loss:
            best_loss, best_params = row["validation"]["loss"], jax.device_get(state.params)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = args.output_dir / "bc_best.msgpack"
    checkpoint = {
        "params": best_params, "model_id": "v113_role_option_hmoe_ppo",
        "strategy_parent": None, "architecture": (
            "staged-option-autoregressive-market-hmoe-v1"
            if args.staged_option else "role-target-option-hmoe-v1"
        ),
        "dataset_sha256": [hashlib.sha256(path.read_bytes()).hexdigest() for path in args.dataset],
    }
    with tempfile.NamedTemporaryFile("wb", dir=args.output_dir, delete=False) as sink:
        sink.write(serialization.msgpack_serialize(checkpoint))
        temporary = Path(sink.name)
    temporary.replace(checkpoint_path)
    report = {
        "schema": (
            "kaggriculture-v113-staged-option-bc-v1"
            if args.staged_option else "kaggriculture-v113-role-option-bc-v1"
        ), "best_validation_loss": best_loss,
        "checkpoint": str(checkpoint_path), "history": history,
        "train_rows": int(len(train_indices)), "validation_rows": int(len(validation_indices)),
        "elapsed_seconds": time.time() - started,
        "split_contract": "deterministic grouped by episode",
        "validation_episodes": [int(value) for value in validation_episodes],
        "day_start_repeat": args.day_start_repeat,
        "sampled_train_rows": int(len(sampled_train_indices)),
    }
    (args.output_dir / "bc_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("best_validation_loss", "checkpoint", "elapsed_seconds")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
