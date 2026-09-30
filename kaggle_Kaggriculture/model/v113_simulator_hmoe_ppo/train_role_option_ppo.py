"""Joint PPO update for V113's role manager, target manager, and full-action worker."""

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

from model_role_option import RoleOptionHMoEActorCritic
from train_factorized_ppo import categorical_stats, clipped_loss


MODEL_KEYS = ("global", "board", "units", "unit_mask")
BATCH_KEYS = MODEL_KEYS + (
    "unit_expert", "market_expert", "option_roles", "option_targets",
    "option_role_masks", "option_target_masks", "option_role_logprobs",
    "option_target_logprobs", "option_target_active",
    "option_decision_active",
    "unit_tokens", "unit_quantities", "unit_action_masks", "unit_logprobs",
    "unit_quantity_logprobs", "unit_quantity_mask", "unit_quantity_masks",
    "market_tokens", "market_quantities", "market_action_masks", "market_slot_mask",
    "market_logprobs", "market_quantity_logprobs", "market_quantity_mask",
    "market_quantity_masks", "value_prediction", "advantage", "return_target",
)


def make_loss(clip, value_coef, entropy_coef, worker_temperature, manager_temperature):
    def loss_fn(params, apply_fn, batch):
        output = apply_fn(
            {"params": params}, *(batch[key] for key in MODEL_KEYS),
            batch["option_roles"], batch["option_targets"],
        )
        index = jnp.arange(batch["unit_expert"].shape[0])
        unit_expert = batch["unit_expert"].astype(jnp.int32)
        market_expert = batch["market_expert"].astype(jnp.int32)
        role_logprob, role_entropy = categorical_stats(
            output["option_role_logits"] / manager_temperature,
            batch["option_roles"], batch["option_role_masks"],
        )
        target_logprob, target_entropy = categorical_stats(
            output["option_target_logits"] / manager_temperature,
            batch["option_targets"], batch["option_target_masks"],
        )
        unit_logprob, unit_entropy = categorical_stats(
            output["unit_logits"][index, unit_expert] / worker_temperature,
            batch["unit_tokens"], batch["unit_action_masks"],
        )
        unit_quantity_logprob, unit_quantity_entropy = categorical_stats(
            output["unit_quantity_logits"][index, unit_expert] / worker_temperature,
            batch["unit_quantities"], batch["unit_quantity_masks"],
        )
        market_logprob, market_entropy = categorical_stats(
            output["market_logits"][index, market_expert] / worker_temperature,
            batch["market_tokens"], batch["market_action_masks"],
        )
        market_quantity_logprob, market_quantity_entropy = categorical_stats(
            output["market_quantity_logits"][index, market_expert] / worker_temperature,
            batch["market_quantities"], batch["market_quantity_masks"],
        )
        advantage = batch["advantage"]
        role_loss, role_clip = clipped_loss(
            role_logprob, batch["option_role_logprobs"], advantage[:, None],
            batch["option_decision_active"], clip
        )
        target_loss, target_clip = clipped_loss(
            target_logprob, batch["option_target_logprobs"], advantage[:, None],
            batch["option_target_active"], clip,
        )
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
        def masked_mean(values, mask):
            return jnp.sum(values * mask) / jnp.maximum(1.0, jnp.sum(mask))
        entropy = (
            masked_mean(role_entropy, batch["option_decision_active"])
            + masked_mean(target_entropy, batch["option_target_active"])
            + masked_mean(unit_entropy, batch["unit_mask"])
            + masked_mean(unit_quantity_entropy, batch["unit_quantity_mask"])
            + masked_mean(market_entropy, batch["market_slot_mask"])
            + masked_mean(market_quantity_entropy, batch["market_quantity_mask"])
        )
        policy_loss = (
            role_loss + target_loss + unit_loss + 0.15 * unit_quantity_loss
            + market_loss + 0.15 * market_quantity_loss
        )
        total = policy_loss + value_coef * value_loss - entropy_coef * entropy
        approximate_kl = (
            masked_mean(
                batch["option_role_logprobs"] - role_logprob,
                batch["option_decision_active"],
            )
            + masked_mean(batch["option_target_logprobs"] - target_logprob, batch["option_target_active"])
            + masked_mean(batch["unit_logprobs"] - unit_logprob, batch["unit_mask"])
            + masked_mean(batch["market_logprobs"] - market_logprob, batch["market_slot_mask"])
        )
        return total, {
            "loss": total, "policy_loss": policy_loss, "value_loss": value_loss,
            "entropy": entropy, "approximate_kl": approximate_kl,
            "clip_fraction": (
                role_clip + target_clip + unit_clip + unit_quantity_clip
                + market_clip + market_quantity_clip
            ) / 6,
        }
    return loss_fn


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--rollouts", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--learning-rate", type=float, default=1e-5)
    parser.add_argument("--clip", type=float, default=0.1)
    parser.add_argument("--target-kl", type=float, default=0.02)
    parser.add_argument("--worker-temperature", type=float, default=0.2)
    parser.add_argument("--manager-temperature", type=float, default=0.5)
    parser.add_argument("--value-coef", type=float, default=0.2)
    parser.add_argument("--entropy-coef", type=float, default=0.001)
    parser.add_argument("--seed", type=int, default=1165001)
    args = parser.parse_args()
    started = time.time()
    payload = serialization.msgpack_restore(args.checkpoint.read_bytes())
    with np.load(args.rollouts) as archive:
        data = {key: archive[key] for key in archive.files}
    missing = set(BATCH_KEYS) - set(data)
    if missing:
        raise ValueError(f"rollouts missing role-option PPO fields: {sorted(missing)}")
    model = RoleOptionHMoEActorCritic()
    flat = traverse_util.flatten_dict(payload["params"])
    frozen = {"unit_router_head", "market_router_head", "opponent_prediction_head"}
    labels = traverse_util.unflatten_dict({
        path: ("freeze" if path[0] in frozen else "train") for path in flat
    })
    train_optimizer = optax.chain(
        optax.clip_by_global_norm(0.5), optax.adamw(args.learning_rate, weight_decay=1e-5)
    )
    optimizer = optax.multi_transform({"train": train_optimizer, "freeze": optax.set_to_zero()}, labels)
    state = TrainState.create(apply_fn=model.apply, params=payload["params"], tx=optimizer)
    loss_fn = make_loss(
        args.clip, args.value_coef, args.entropy_coef,
        args.worker_temperature, args.manager_temperature,
    )

    @jax.jit
    def train_step(train_state, batch):
        (_, metrics), gradients = jax.value_and_grad(loss_fn, has_aux=True)(
            train_state.params, train_state.apply_fn, batch
        )
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
        if not rows:
            raise ValueError("rollout is smaller than one PPO batch")
        row = {"epoch": epoch, **{
            key: float(np.mean([float(item[key]) for item in rows])) for key in rows[0]
        }}
        history.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
        if abs(row["approximate_kl"]) > args.target_kl:
            break
    args.output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = args.output_dir / "ppo_checkpoint.msgpack"
    result = {
        **{key: value for key, value in payload.items() if key != "params"},
        "params": jax.device_get(state.params),
        "architecture": "role-target-option-hmoe-v2-ppo",
        "strategy_parent": None,
        "source_checkpoint_sha256": hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
        "rollout_sha256": hashlib.sha256(args.rollouts.read_bytes()).hexdigest(),
    }
    with tempfile.NamedTemporaryFile("wb", dir=args.output_dir, delete=False) as sink:
        sink.write(serialization.msgpack_serialize(result))
        temporary = Path(sink.name)
    temporary.replace(checkpoint_path)
    report = {
        "schema": "kaggriculture-v113-role-option-ppo-v1",
        "transitions": len(indices), "history": history,
        "routers_frozen": True, "manager_and_workers_trained": True,
        "worker_temperature": args.worker_temperature,
        "manager_temperature": args.manager_temperature,
        "checkpoint": str(checkpoint_path), "elapsed_seconds": time.time() - started,
    }
    (args.output_dir / "ppo_update.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
