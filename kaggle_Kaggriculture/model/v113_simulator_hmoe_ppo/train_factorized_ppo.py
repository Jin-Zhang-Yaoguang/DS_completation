"""PPO update for factorized V113 workers with both routers frozen."""

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

from model_factorized import FactorizedHMoEActorCritic


MODEL_KEYS = ("global", "board", "units", "unit_mask")
BATCH_KEYS = MODEL_KEYS + (
    "unit_expert", "market_expert", "unit_tokens", "unit_quantities",
    "unit_action_masks", "unit_logprobs", "unit_quantity_logprobs", "unit_quantity_mask",
    "unit_quantity_masks", "market_tokens", "market_quantities", "market_action_masks",
    "market_slot_mask", "market_logprobs", "market_quantity_logprobs",
    "market_quantity_mask", "market_quantity_masks", "value_prediction", "advantage", "return_target",
)


def categorical_stats(logits, targets, legal_mask=None):
    if legal_mask is not None:
        logits = jnp.where(legal_mask, logits, -1e30)
    log_probability = jax.nn.log_softmax(logits, axis=-1)
    probability = jax.nn.softmax(logits, axis=-1)
    selected = jnp.take_along_axis(log_probability, targets[..., None], axis=-1)[..., 0]
    entropy = -jnp.sum(probability * log_probability, axis=-1)
    return selected, entropy


def clipped_loss(new_logprob, old_logprob, advantage, mask, clip):
    ratio = jnp.exp(jnp.clip(new_logprob - old_logprob, -20, 20))
    objective = jnp.minimum(ratio * advantage, jnp.clip(ratio, 1 - clip, 1 + clip) * advantage)
    denominator = jnp.maximum(1.0, jnp.sum(mask))
    return -jnp.sum(objective * mask) / denominator, jnp.sum((jnp.abs(ratio - 1) > clip) * mask) / denominator


def make_loss(clip, value_coef, entropy_coef, worker_temperature):
    def loss_fn(params, apply_fn, batch):
        output = apply_fn({"params": params}, *(batch[key] for key in MODEL_KEYS))
        index = jnp.arange(batch["unit_expert"].shape[0])
        unit_expert = batch["unit_expert"].astype(jnp.int32)
        market_expert = batch["market_expert"].astype(jnp.int32)
        unit_logits = output["unit_logits"][index, unit_expert] / worker_temperature
        unit_quantity_logits = output["unit_quantity_logits"][index, unit_expert] / worker_temperature
        market_logits = output["market_logits"][index, market_expert] / worker_temperature
        market_quantity_logits = output["market_quantity_logits"][index, market_expert] / worker_temperature
        unit_logprob, unit_entropy = categorical_stats(unit_logits, batch["unit_tokens"], batch["unit_action_masks"])
        unit_quantity_logprob, unit_quantity_entropy = categorical_stats(
            unit_quantity_logits, batch["unit_quantities"], batch["unit_quantity_masks"]
        )
        market_logprob, market_entropy = categorical_stats(
            market_logits, batch["market_tokens"], batch["market_action_masks"]
        )
        market_quantity_logprob, market_quantity_entropy = categorical_stats(
            market_quantity_logits, batch["market_quantities"], batch["market_quantity_masks"]
        )
        advantage = batch["advantage"]
        unit_loss, unit_clip = clipped_loss(
            unit_logprob, batch["unit_logprobs"], advantage[:, None], batch["unit_mask"], clip
        )
        unit_quantity_loss, unit_quantity_clip = clipped_loss(
            unit_quantity_logprob, batch["unit_quantity_logprobs"], advantage[:, None],
            batch["unit_quantity_mask"], clip,
        )
        market_loss, market_clip = clipped_loss(
            market_logprob, batch["market_logprobs"], advantage[:, None], batch["market_slot_mask"], clip
        )
        market_quantity_loss, market_quantity_clip = clipped_loss(
            market_quantity_logprob, batch["market_quantity_logprobs"], advantage[:, None],
            batch["market_quantity_mask"], clip,
        )
        old_value = batch["value_prediction"]
        clipped_value = old_value + jnp.clip(output["value"] - old_value, -clip, clip)
        value_loss = 0.5 * jnp.mean(jnp.maximum(
            (output["value"] - batch["return_target"]) ** 2,
            (clipped_value - batch["return_target"]) ** 2,
        ))
        entropy = (
            jnp.sum(unit_entropy * batch["unit_mask"]) / jnp.maximum(1.0, jnp.sum(batch["unit_mask"]))
            + jnp.sum(unit_quantity_entropy * batch["unit_quantity_mask"]) / jnp.maximum(1.0, jnp.sum(batch["unit_quantity_mask"]))
            + jnp.sum(market_entropy * batch["market_slot_mask"]) / jnp.maximum(1.0, jnp.sum(batch["market_slot_mask"]))
            + jnp.sum(market_quantity_entropy * batch["market_quantity_mask"]) / jnp.maximum(1.0, jnp.sum(batch["market_quantity_mask"]))
        )
        policy_loss = unit_loss + 0.15 * unit_quantity_loss + market_loss + 0.15 * market_quantity_loss
        total = policy_loss + value_coef * value_loss - entropy_coef * entropy
        approximate_kl = (
            jnp.sum((batch["unit_logprobs"] - unit_logprob) * batch["unit_mask"]) / jnp.maximum(1.0, jnp.sum(batch["unit_mask"]))
            + jnp.sum((batch["market_logprobs"] - market_logprob) * batch["market_slot_mask"]) / jnp.maximum(1.0, jnp.sum(batch["market_slot_mask"]))
        )
        return total, {
            "loss": total, "policy_loss": policy_loss, "value_loss": value_loss,
            "entropy": entropy, "approximate_kl": approximate_kl,
            "clip_fraction": (unit_clip + unit_quantity_clip + market_clip + market_quantity_clip) / 4,
        }
    return loss_fn


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--rollouts", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--learning-rate", type=float, default=1e-5)
    parser.add_argument("--clip", type=float, default=0.1)
    parser.add_argument("--target-kl", type=float, default=0.01)
    parser.add_argument("--worker-temperature", type=float, default=0.2)
    parser.add_argument("--value-coef", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=1138201)
    args = parser.parse_args()
    started = time.time()
    payload = serialization.msgpack_restore(args.checkpoint.read_bytes())
    with np.load(args.rollouts) as archive:
        data = {key: archive[key] for key in archive.files}
    model = FactorizedHMoEActorCritic()
    train_optimizer = optax.chain(optax.clip_by_global_norm(0.5), optax.adamw(args.learning_rate, weight_decay=1e-5))
    flat = traverse_util.flatten_dict(payload["params"])
    frozen = {"unit_router_head", "market_router_head", "opponent_prediction_head"}
    labels = traverse_util.unflatten_dict({path: ("freeze" if path[0] in frozen else "train") for path in flat})
    optimizer = optax.multi_transform({"train": train_optimizer, "freeze": optax.set_to_zero()}, labels)
    state = TrainState.create(apply_fn=model.apply, params=payload["params"], tx=optimizer)
    loss_fn = make_loss(args.clip, args.value_coef, 0.001, args.worker_temperature)

    @jax.jit
    def train_step(train_state, batch):
        (_, metrics), gradients = jax.value_and_grad(loss_fn, has_aux=True)(train_state.params, train_state.apply_fn, batch)
        return train_state.apply_gradients(grads=gradients), metrics

    rng = np.random.default_rng(args.seed)
    indices = np.arange(len(data["advantage"]))
    history = []
    for epoch in range(1, args.epochs + 1):
        rng.shuffle(indices)
        rows = []
        for start in range(0, len(indices) - args.batch_size + 1, args.batch_size):
            selected = indices[start:start + args.batch_size]
            batch = {key: jnp.asarray(data[key][selected]) for key in BATCH_KEYS}
            state, metrics = train_step(state, batch)
            rows.append(jax.device_get(metrics))
        row = {"epoch": epoch, **{key: float(np.mean([float(item[key]) for item in rows])) for key in rows[0]}}
        history.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
        if row["approximate_kl"] > args.target_kl:
            break
    args.output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = args.output_dir / "ppo_checkpoint.msgpack"
    result = {
        **{key: value for key, value in payload.items() if key != "params"},
        "params": jax.device_get(state.params), "architecture": "factorized-production-market-hmoe-v3-ppo",
        "source_checkpoint_sha256": hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
        "rollout_sha256": hashlib.sha256(args.rollouts.read_bytes()).hexdigest(),
    }
    with tempfile.NamedTemporaryFile("wb", dir=args.output_dir, delete=False) as sink:
        sink.write(serialization.msgpack_serialize(result))
        temporary = Path(sink.name)
    temporary.replace(checkpoint_path)
    report = {
        "schema": "kaggriculture-v113-factorized-ppo-v1", "transitions": len(indices),
        "history": history, "routers_frozen": True, "worker_temperature": args.worker_temperature,
        "value_coefficient": args.value_coef, "checkpoint": str(checkpoint_path),
        "elapsed_seconds": time.time() - started,
    }
    (args.output_dir / "ppo_update.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
