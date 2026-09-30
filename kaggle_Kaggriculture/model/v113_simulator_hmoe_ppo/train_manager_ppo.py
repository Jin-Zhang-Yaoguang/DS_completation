"""PPO update restricted to V113's day-level Router and Value head."""

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
BATCH_KEYS = MODEL_KEYS + ("expert", "old_logprob", "old_value", "advantage", "return_target")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--rollouts", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=6)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--clip", type=float, default=0.2)
    parser.add_argument("--target-kl", type=float, default=0.02)
    parser.add_argument("--router-temperature", type=float, default=3.0)
    parser.add_argument("--seed", type=int, default=1138001)
    args = parser.parse_args()
    started = time.time()
    payload = serialization.msgpack_restore(args.checkpoint.read_bytes())
    with np.load(args.rollouts) as archive:
        data = {key: archive[key] for key in archive.files}
    model = HMoEActorCritic()
    flat = traverse_util.flatten_dict(payload["params"])
    labels = traverse_util.unflatten_dict({
        path: ("train" if path[0] in {"router_head", "value_head"} else "freeze")
        for path in flat
    })
    optimizer = optax.multi_transform({
        "train": optax.chain(optax.clip_by_global_norm(0.5), optax.adam(args.learning_rate)),
        "freeze": optax.set_to_zero(),
    }, labels)
    state = TrainState.create(apply_fn=model.apply, params=payload["params"], tx=optimizer)

    def loss_fn(params, batch):
        output = model.apply({"params": params}, *(batch[key] for key in MODEL_KEYS))
        scaled_router_logits = output["router_logits"] / args.router_temperature
        logp_all = jax.nn.log_softmax(scaled_router_logits, axis=-1)
        logp = jnp.take_along_axis(logp_all, batch["expert"][:, None], axis=-1)[:, 0]
        ratio = jnp.exp(jnp.clip(logp - batch["old_logprob"], -20, 20))
        surrogate = jnp.minimum(ratio * batch["advantage"], jnp.clip(ratio, 1 - args.clip, 1 + args.clip) * batch["advantage"])
        policy_loss = -jnp.mean(surrogate)
        clipped_value = batch["old_value"] + jnp.clip(output["value"] - batch["old_value"], -args.clip, args.clip)
        value_loss = 0.5 * jnp.mean(jnp.maximum((output["value"] - batch["return_target"]) ** 2, (clipped_value - batch["return_target"]) ** 2))
        probability = jax.nn.softmax(scaled_router_logits, axis=-1)
        entropy = -jnp.mean(jnp.sum(probability * logp_all, axis=-1))
        balance = jnp.sum((jnp.mean(probability, axis=0) - 1.0 / NUM_EXPERTS) ** 2)
        loss = policy_loss + 0.5 * value_loss + 0.05 * balance - 0.01 * entropy
        return loss, {
            "loss": loss, "policy_loss": policy_loss, "value_loss": value_loss,
            "entropy": entropy, "balance_loss": balance,
            "approximate_kl": jnp.mean(batch["old_logprob"] - logp),
            "clip_fraction": jnp.mean((jnp.abs(ratio - 1.0) > args.clip).astype(jnp.float32)),
        }

    @jax.jit
    def step(train_state, batch):
        (_, metrics), gradients = jax.value_and_grad(loss_fn, has_aux=True)(train_state.params, batch)
        return train_state.apply_gradients(grads=gradients), metrics

    rng = np.random.default_rng(args.seed)
    indices = np.arange(len(data["expert"]))
    history = []
    for epoch in range(1, args.epochs + 1):
        rng.shuffle(indices)
        rows = []
        for start in range(0, len(indices) - args.batch_size + 1, args.batch_size):
            selected = indices[start:start + args.batch_size]
            batch = {key: jnp.asarray(data[key][selected]) for key in BATCH_KEYS}
            state, metrics = step(state, batch)
            rows.append(jax.device_get(metrics))
        row = {"epoch": epoch, **{key: float(np.mean([float(item[key]) for item in rows])) for key in rows[0]}}
        history.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
        if row["approximate_kl"] > args.target_kl:
            break
    args.output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = args.output_dir / "manager_checkpoint.msgpack"
    result = {
        **{key: value for key, value in payload.items() if key != "params"},
        "params": jax.device_get(state.params),
        "manager_source_sha256": hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
    }
    with tempfile.NamedTemporaryFile("wb", dir=args.output_dir, delete=False) as sink:
        sink.write(serialization.msgpack_serialize(result))
        temporary = Path(sink.name)
    temporary.replace(checkpoint)
    report = {
        "schema": "kaggriculture-v113-manager-ppo-v1", "history": history,
        "checkpoint": str(checkpoint), "router_temperature": args.router_temperature,
        "elapsed_seconds": time.time() - started,
    }
    (args.output_dir / "manager_update.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
