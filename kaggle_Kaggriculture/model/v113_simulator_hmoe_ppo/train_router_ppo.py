"""PPO update for V113's crop Router while every action expert stays frozen."""

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


def router_loss(params, apply_fn, batch, clip: float, temperature: float, entropy_coef: float):
    output = apply_fn({"params": params}, *(batch[key] for key in MODEL_KEYS))
    logits = output["unit_router_logits"][:, :5] / temperature
    log_probability = jax.nn.log_softmax(logits, axis=-1)
    probability = jax.nn.softmax(logits, axis=-1)
    selected = jnp.take_along_axis(log_probability, batch["unit_expert"][:, None], axis=-1)[:, 0]
    ratio = jnp.exp(jnp.clip(selected - batch["unit_router_logprob"], -20.0, 20.0))
    advantage = batch["advantage"]
    objective = jnp.minimum(ratio * advantage, jnp.clip(ratio, 1 - clip, 1 + clip) * advantage)
    entropy = -jnp.mean(jnp.sum(probability * log_probability, axis=-1))
    policy_loss = -jnp.mean(objective)
    loss = policy_loss - entropy_coef * entropy
    return loss, {
        "loss": loss, "policy_loss": policy_loss, "entropy": entropy,
        "approximate_kl": jnp.mean(batch["unit_router_logprob"] - selected),
        "clip_fraction": jnp.mean(jnp.abs(ratio - 1.0) > clip),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--rollouts", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--clip", type=float, default=0.2)
    parser.add_argument("--target-kl", type=float, default=0.03)
    parser.add_argument("--router-temperature", type=float, default=1.0)
    parser.add_argument("--entropy-coef", type=float, default=0.01)
    parser.add_argument("--bias-only", action="store_true")
    parser.add_argument("--seed", type=int, default=1140001)
    args = parser.parse_args()
    started = time.time()
    payload = serialization.msgpack_restore(args.checkpoint.read_bytes())
    with np.load(args.rollouts) as archive:
        data = {key: archive[key] for key in archive.files}
    model = FactorizedHMoEActorCritic()
    flat = traverse_util.flatten_dict(payload["params"])
    labels = traverse_util.unflatten_dict({
        path: (
            "train" if path[0] == "unit_router_head" and (not args.bias_only or path[-1] == "bias")
            else "freeze"
        ) for path in flat
    })
    train_optimizer = (
        optax.sgd(args.learning_rate) if args.bias_only
        else optax.chain(optax.clip_by_global_norm(0.5), optax.adam(args.learning_rate))
    )
    optimizer = optax.multi_transform({
        "train": train_optimizer,
        "freeze": optax.set_to_zero(),
    }, labels)
    state = TrainState.create(apply_fn=model.apply, params=payload["params"], tx=optimizer)

    @jax.jit
    def train_step(train_state, batch):
        (_, metrics), gradients = jax.value_and_grad(router_loss, has_aux=True)(
            train_state.params, train_state.apply_fn, batch, args.clip,
            args.router_temperature, args.entropy_coef,
        )
        return train_state.apply_gradients(grads=gradients), metrics

    rng = np.random.default_rng(args.seed)
    indices = np.arange(len(data["advantage"]))
    history = []
    for epoch in range(1, args.epochs + 1):
        rng.shuffle(indices)
        rows = []
        for start in range(0, len(indices), args.batch_size):
            selected = indices[start:start + args.batch_size]
            batch = {key: jnp.asarray(data[key][selected]) for key in (
                *MODEL_KEYS, "unit_expert", "unit_router_logprob", "advantage"
            )}
            state, metrics = train_step(state, batch)
            rows.append(jax.device_get(metrics))
        row = {"epoch": epoch, **{
            key: float(np.mean([float(item[key]) for item in rows])) for key in rows[0]
        }}
        history.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
        if row["approximate_kl"] > args.target_kl:
            break
    args.output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = args.output_dir / "router_ppo_checkpoint.msgpack"
    result = {
        **{key: value for key, value in payload.items() if key != "params"},
        "params": jax.device_get(state.params),
        "architecture": "factorized-product-hmoe-v4-episode-router-ppo",
        "source_checkpoint_sha256": hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
        "rollout_sha256": hashlib.sha256(args.rollouts.read_bytes()).hexdigest(),
        "router_contract": {"experts": [0, 1, 2, 3, 4], "period": 720, "coupled_market": True},
    }
    with tempfile.NamedTemporaryFile("wb", dir=args.output_dir, delete=False) as sink:
        sink.write(serialization.msgpack_serialize(result))
        temporary = Path(sink.name)
    temporary.replace(checkpoint_path)
    report = {
        "schema": "kaggriculture-v113-router-ppo-update-v1", "samples": len(indices),
        "history": history, "workers_frozen": True, "router_temperature": args.router_temperature,
        "bias_only": args.bias_only,
        "checkpoint": str(checkpoint_path), "elapsed_seconds": time.time() - started,
    }
    (args.output_dir / "router_ppo_update.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
