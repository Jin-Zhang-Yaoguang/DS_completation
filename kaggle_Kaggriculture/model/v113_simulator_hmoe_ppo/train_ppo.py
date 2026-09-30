"""PPO update for V113's Router, unit heads, market heads and critic."""

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

from model import HMoEActorCritic, NUM_EXPERTS


MODEL_KEYS = ("global", "board", "units", "unit_mask")
BATCH_KEYS = MODEL_KEYS + (
    "expert", "router_mask", "router_logprob", "unit_tokens", "unit_quantities",
    "unit_action_masks", "unit_logprobs", "unit_quantity_logprobs", "unit_quantity_mask",
    "unit_quantity_masks",
    "market_tokens", "market_quantities", "market_action_masks", "market_slot_mask",
    "market_logprobs", "market_quantity_logprobs", "market_quantity_mask",
    "market_quantity_masks",
    "value_prediction", "advantage", "return_target",
)


def categorical_stats(logits, targets, legal_mask=None):
    if legal_mask is not None:
        logits = jnp.where(legal_mask, logits, -1e30)
    log_probability = jax.nn.log_softmax(logits, axis=-1)
    probability = jax.nn.softmax(logits, axis=-1)
    selected = jnp.take_along_axis(log_probability, targets[..., None], axis=-1)[..., 0]
    entropy = -jnp.sum(probability * log_probability, axis=-1)
    return selected, entropy


def clipped_policy_loss(new_logprob, old_logprob, advantage, mask, clip):
    ratio = jnp.exp(jnp.clip(new_logprob - old_logprob, -20.0, 20.0))
    unclipped = ratio * advantage
    clipped = jnp.clip(ratio, 1.0 - clip, 1.0 + clip) * advantage
    denominator = jnp.maximum(1.0, jnp.sum(mask))
    return -jnp.sum(jnp.minimum(unclipped, clipped) * mask) / denominator, jnp.sum(((ratio < 1.0 - clip) | (ratio > 1.0 + clip)) * mask) / denominator


def make_loss(
    clip: float, value_coef: float, entropy_coef: float,
    router_entropy_coef: float, worker_temperature: float, freeze_router: bool,
):
    def loss_fn(params, apply_fn, batch):
        output = apply_fn({"params": params}, *(batch[key] for key in MODEL_KEYS))
        index = jnp.arange(batch["expert"].shape[0])
        expert = batch["expert"].astype(jnp.int32)
        advantage = batch["advantage"]
        unit_logits = output["unit_logits"][index, expert]
        unit_quantity_logits = output["unit_quantity_logits"][index, expert]
        market_logits = output["market_logits"][index, expert]
        market_quantity_logits = output["market_quantity_logits"][index, expert]

        router_logprob, router_entropy = categorical_stats(output["router_logits"], expert)
        unit_logprob, unit_entropy = categorical_stats(unit_logits / worker_temperature, batch["unit_tokens"], batch["unit_action_masks"])
        unit_quantity_logprob, unit_quantity_entropy = categorical_stats(unit_quantity_logits / worker_temperature, batch["unit_quantities"], batch["unit_quantity_masks"])
        market_logprob, market_entropy = categorical_stats(market_logits / worker_temperature, batch["market_tokens"], batch["market_action_masks"])
        market_quantity_logprob, market_quantity_entropy = categorical_stats(market_quantity_logits / worker_temperature, batch["market_quantities"], batch["market_quantity_masks"])

        router_loss, router_clip = clipped_policy_loss(router_logprob, batch["router_logprob"], advantage, batch["router_mask"], clip)
        unit_loss, unit_clip = clipped_policy_loss(unit_logprob, batch["unit_logprobs"], advantage[:, None], batch["unit_mask"], clip)
        unit_quantity_loss, unit_quantity_clip = clipped_policy_loss(unit_quantity_logprob, batch["unit_quantity_logprobs"], advantage[:, None], batch["unit_quantity_mask"], clip)
        market_loss, market_clip = clipped_policy_loss(market_logprob, batch["market_logprobs"], advantage[:, None], batch["market_slot_mask"], clip)
        market_quantity_loss, market_quantity_clip = clipped_policy_loss(market_quantity_logprob, batch["market_quantity_logprobs"], advantage[:, None], batch["market_quantity_mask"], clip)
        old_value = batch["value_prediction"]
        clipped_value = old_value + jnp.clip(output["value"] - old_value, -clip, clip)
        value_loss = 0.5 * jnp.mean(jnp.maximum((output["value"] - batch["return_target"]) ** 2, (clipped_value - batch["return_target"]) ** 2))
        router_probability = jax.nn.softmax(output["router_logits"], axis=-1)
        balance_loss = jnp.sum((jnp.mean(router_probability, axis=0) - 1.0 / NUM_EXPERTS) ** 2)
        entropy = (
            jnp.sum(unit_entropy * batch["unit_mask"]) / jnp.maximum(1.0, jnp.sum(batch["unit_mask"]))
            + jnp.sum(unit_quantity_entropy * batch["unit_quantity_mask"]) / jnp.maximum(1.0, jnp.sum(batch["unit_quantity_mask"]))
            + jnp.sum(market_entropy * batch["market_slot_mask"]) / jnp.maximum(1.0, jnp.sum(batch["market_slot_mask"]))
            + jnp.sum(market_quantity_entropy * batch["market_quantity_mask"]) / jnp.maximum(1.0, jnp.sum(batch["market_quantity_mask"]))
        )
        router_entropy_mean = jnp.sum(router_entropy * batch["router_mask"]) / jnp.maximum(1.0, jnp.sum(batch["router_mask"]))
        policy_loss = (
            (0.0 if freeze_router else router_loss) + unit_loss + 0.15 * unit_quantity_loss
            + market_loss + 0.15 * market_quantity_loss
        )
        router_regularization = 0.0 if freeze_router else 0.1 * balance_loss - router_entropy_coef * router_entropy_mean
        total = policy_loss + value_coef * value_loss + router_regularization - entropy_coef * entropy
        approximate_kl = (
            jnp.sum((batch["unit_logprobs"] - unit_logprob) * batch["unit_mask"]) / jnp.maximum(1.0, jnp.sum(batch["unit_mask"]))
            + jnp.sum((batch["market_logprobs"] - market_logprob) * batch["market_slot_mask"]) / jnp.maximum(1.0, jnp.sum(batch["market_slot_mask"]))
        )
        return total, {
            "loss": total,
            "policy_loss": policy_loss,
            "value_loss": value_loss,
            "entropy": entropy,
            "router_entropy": router_entropy_mean,
            "balance_loss": balance_loss,
            "approximate_kl": approximate_kl,
            "clip_fraction": (router_clip + unit_clip + unit_quantity_clip + market_clip + market_quantity_clip) / 5.0,
        }
    return loss_fn


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--rollouts", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--clip", type=float, default=0.2)
    parser.add_argument("--target-kl", type=float, default=0.015)
    parser.add_argument("--worker-temperature", type=float, default=1.0)
    parser.add_argument("--freeze-router", action="store_true")
    parser.add_argument("--value-coef", type=float, default=0.5)
    parser.add_argument("--seed", type=int, default=1132001)
    args = parser.parse_args()
    started = time.time()
    payload = serialization.msgpack_restore(args.checkpoint.read_bytes())
    with np.load(args.rollouts) as archive:
        data = {key: archive[key] for key in archive.files}
    model = HMoEActorCritic()
    train_optimizer = optax.chain(optax.clip_by_global_norm(0.5), optax.adamw(args.learning_rate, weight_decay=1e-5))
    if args.freeze_router:
        flat = traverse_util.flatten_dict(payload["params"])
        labels = traverse_util.unflatten_dict({
            path: ("freeze" if path[0] == "router_head" else "train") for path in flat
        })
        optimizer = optax.multi_transform({"train": train_optimizer, "freeze": optax.set_to_zero()}, labels)
    else:
        optimizer = train_optimizer
    state = TrainState.create(apply_fn=model.apply, params=payload["params"], tx=optimizer)
    loss_fn = make_loss(
        args.clip, value_coef=args.value_coef, entropy_coef=0.005, router_entropy_coef=0.01,
        worker_temperature=args.worker_temperature, freeze_router=args.freeze_router,
    )

    @jax.jit
    def train_step(train_state, batch):
        (_, metrics), gradients = jax.value_and_grad(loss_fn, has_aux=True)(train_state.params, train_state.apply_fn, batch)
        return train_state.apply_gradients(grads=gradients), metrics

    rng = np.random.default_rng(args.seed)
    history = []
    indices = np.arange(len(data["expert"]))
    stopped_early = False
    for epoch in range(1, args.epochs + 1):
        rng.shuffle(indices)
        metrics_rows = []
        for start in range(0, len(indices) - args.batch_size + 1, args.batch_size):
            selected = indices[start:start + args.batch_size]
            batch = {key: jnp.asarray(data[key][selected]) for key in BATCH_KEYS}
            state, metrics = train_step(state, batch)
            metrics_rows.append(jax.device_get(metrics))
        row = {"epoch": epoch, **{key: float(np.mean([float(item[key]) for item in metrics_rows])) for key in metrics_rows[0]}}
        history.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
        if row["approximate_kl"] > args.target_kl:
            stopped_early = True
            break

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_checkpoint = args.output_dir / "ppo_checkpoint.msgpack"
    result = {
        "params": jax.device_get(state.params),
        "model_id": "v113_simulator_hmoe_ppo",
        "strategy_parent": None,
        "architecture": payload.get("architecture", "local-board-unit-attention-hmoe-v2"),
        "source_checkpoint_sha256": hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
        "rollout_sha256": hashlib.sha256(args.rollouts.read_bytes()).hexdigest(),
    }
    with tempfile.NamedTemporaryFile("wb", dir=args.output_dir, delete=False) as sink:
        sink.write(serialization.msgpack_serialize(result))
        temporary = Path(sink.name)
    temporary.replace(output_checkpoint)
    report = {
        "schema": "kaggriculture-v113-ppo-update-v1",
        "transitions": len(indices),
        "epochs_completed": len(history),
        "stopped_early_kl": stopped_early,
        "worker_temperature": args.worker_temperature,
        "router_frozen": args.freeze_router,
        "value_coefficient": args.value_coef,
        "history": history,
        "output_checkpoint": str(output_checkpoint),
        "elapsed_seconds": time.time() - started,
    }
    (args.output_dir / "ppo_update_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("transitions", "epochs_completed", "stopped_early_kl", "output_checkpoint", "elapsed_seconds")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
