"""PPO fine-tuning for MoVE Router on post-Router on-policy trajectories.

This command is intentionally separate from counterfactual Router training.
It refuses to operate on D2 data: PPO needs D3 trajectories collected from the
currently deployed Router decision rule and action closure.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from flax import serialization
import jax
import jax.numpy as jnp
import numpy as np
import optax

from router_model import RouterNetwork, export_numpy, initial_params, parity_error


def _masked_logprob(logits, action, mask):
    legal = jnp.asarray(mask, dtype=bool)
    safe_logits = jnp.where(legal, logits, -1e9)
    log_probs = jax.nn.log_softmax(safe_logits, axis=-1)
    return jnp.take_along_axis(log_probs, action[..., None], axis=-1)[..., 0]


def _entropy(logits, mask):
    legal = jnp.asarray(mask, dtype=bool)
    safe_logits = jnp.where(legal, logits, -1e9)
    p = jax.nn.softmax(safe_logits, axis=-1)
    return -jnp.sum(jnp.where(legal, p * jax.nn.log_softmax(safe_logits, axis=-1), 0.0), axis=-1)


def load_rollouts(path: Path):
    data = np.load(path, allow_pickle=False)
    required = {"features", "production_actions", "market_actions", "production_mask", "market_mask", "old_logprob", "advantages", "returns"}
    missing = required.difference(data.files)
    if missing:
        raise ValueError(f"D3/on-policy rollout missing fields: {sorted(missing)}")
    rows = {key: np.asarray(data[key]) for key in required}
    n = rows["features"].shape[0]
    if n < 32 or any(value.shape[0] != n for value in rows.values()):
        raise ValueError("invalid on-policy rollout row counts")
    p_names = [str(x) for x in np.asarray(data["production_names"]).tolist()]
    m_names = [str(x) for x in np.asarray(data["market_names"]).tolist()]
    if rows["production_mask"].shape[1] != len(p_names) or rows["market_mask"].shape[1] != len(m_names):
        raise ValueError("rollout expert schema mismatch")
    return rows, p_names, m_names


def train(rollout_path: Path, params_path: Path, output: Path, epochs=4, batch_size=4096, learning_rate=1e-4, clip=0.2, entropy_coef=0.01, value_coef=0.5, target_kl=0.015, seed=17):
    rows, production_names, market_names = load_rollouts(rollout_path)
    template = initial_params(len(production_names), len(market_names), seed=0)
    params = serialization.from_bytes(template, params_path.read_bytes())
    model = RouterNetwork(len(production_names), len(market_names))
    optimizer = optax.chain(optax.clip_by_global_norm(0.5), optax.adam(float(learning_rate)))
    opt_state = optimizer.init(params)
    advantages = rows["advantages"].astype(np.float32)
    rows["advantages"] = (advantages - advantages.mean()) / max(1e-6, advantages.std())

    @jax.jit
    def update(params, opt_state, batch):
        def loss_fn(p):
            p_logits, m_logits, value = model.apply(p, batch["features"])
            new_lp = _masked_logprob(p_logits, batch["production_actions"], batch["production_mask"]) + _masked_logprob(m_logits, batch["market_actions"], batch["market_mask"])
            ratio = jnp.exp(new_lp - batch["old_logprob"])
            clipped = jnp.clip(ratio, 1.0 - clip, 1.0 + clip)
            policy_loss = -jnp.mean(jnp.minimum(ratio * batch["advantages"], clipped * batch["advantages"]))
            value_loss = jnp.mean(jnp.square(value - batch["returns"]))
            entropy = jnp.mean(_entropy(p_logits, batch["production_mask"]) + _entropy(m_logits, batch["market_mask"]))
            approx_kl = jnp.mean(batch["old_logprob"] - new_lp)
            loss = policy_loss + value_coef * value_loss - entropy_coef * entropy
            return loss, (policy_loss, value_loss, entropy, approx_kl)
        (loss, parts), grads = jax.value_and_grad(loss_fn, has_aux=True)(params)
        updates, state = optimizer.update(grads, opt_state, params)
        return optax.apply_updates(params, updates), state, loss, parts

    rng = np.random.default_rng(int(seed))
    history = []
    n = rows["features"].shape[0]
    stopped_early = False
    for epoch in range(int(epochs)):
        order = rng.permutation(n)
        epoch_parts = []
        for start in range(0, n, int(batch_size)):
            index = order[start:start + int(batch_size)]
            batch = {key: jnp.asarray(value[index]) for key, value in rows.items()}
            params, opt_state, _, parts = update(params, opt_state, batch)
            epoch_parts.append([float(x) for x in parts])
        means = np.mean(np.asarray(epoch_parts), axis=0).tolist()
        row = {"epoch": epoch + 1, "policy_loss": means[0], "value_loss": means[1], "entropy": means[2], "approx_kl": means[3]}
        history.append(row)
        if row["approx_kl"] > float(target_kl):
            stopped_early = True
            break
    output.mkdir(parents=True, exist_ok=True)
    weights = output / "router_weights.npz"
    export_numpy(params, weights, production_names, market_names)
    (output / "router_params.msgpack").write_bytes(serialization.to_bytes(params))
    report = {
        "schema": "kaggriculture-ppo-v3-router-ppo-1", "rollout": str(rollout_path),
        "epochs_requested": int(epochs), "epochs_run": len(history), "stopped_target_kl": stopped_early,
        "history": history, "production_names": production_names, "market_names": market_names,
        "numpy_jax_max_abs_error": parity_error(params, weights, production_names, market_names),
    }
    (output / "ppo_router_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rollouts", type=Path, required=True)
    parser.add_argument("--params", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=4096)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--seed", type=int, default=17)
    args = parser.parse_args()
    print(json.dumps(train(args.rollouts, args.params, args.output, args.epochs, args.batch_size, args.learning_rate, seed=args.seed), ensure_ascii=False, indent=2))
