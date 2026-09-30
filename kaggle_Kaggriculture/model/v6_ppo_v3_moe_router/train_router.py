"""Train the conservative MoVE Router from same-state counterfactual data.

This is deliberately not behavior cloning: targets are paired uplift estimates
for each eligible expert.  V1 is an anchor column, not the sole teacher label.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import jax
import jax.numpy as jnp
import numpy as np
import optax
from flax import serialization

from router_model import RouterNetwork, export_numpy, initial_params, parity_error


HERE = Path(__file__).resolve().parent


def _text(values):
    return np.asarray([str(item) for item in np.asarray(values).tolist()])


def load_dataset(path: Path):
    data = np.load(path, allow_pickle=False)
    required = {"features", "production_mask", "market_mask", "production_uplift", "market_uplift"}
    missing = required.difference(data.files)
    if missing:
        raise ValueError(f"missing D2 fields: {sorted(missing)}")
    features = np.asarray(data["features"], dtype=np.float32)
    p_mask = np.asarray(data["production_mask"], dtype=bool)
    m_mask = np.asarray(data["market_mask"], dtype=bool)
    p_target = np.asarray(data["production_uplift"], dtype=np.float32)
    m_target = np.asarray(data["market_uplift"], dtype=np.float32)
    n = features.shape[0]
    if features.ndim != 2 or n < 10 or p_mask.shape != p_target.shape or m_mask.shape != m_target.shape:
        raise ValueError("invalid D2 matrix shapes")
    if p_mask.shape[0] != n or m_mask.shape[0] != n or p_target.shape[0] != n or m_target.shape[0] != n:
        raise ValueError("D2 row count mismatch")
    if not np.all(np.isfinite(features)):
        raise ValueError("non-finite D2 features")
    split = _text(data["split"]) if "split" in data.files else np.asarray(["train"] * n)
    production_names = _text(data["production_names"]) if "production_names" in data.files else np.asarray([f"production_{i}" for i in range(p_mask.shape[1])])
    market_names = _text(data["market_names"]) if "market_names" in data.files else np.asarray([f"market_{i}" for i in range(m_mask.shape[1])])
    if len(production_names) != p_mask.shape[1] or len(market_names) != m_mask.shape[1]:
        raise ValueError("expert name count mismatch")
    effective = np.asarray(data["effective_action_change"], dtype=bool) if "effective_action_change" in data.files else np.ones(n, dtype=bool)
    # A non-default expert needs at least one *actual* executable intervention
    # in the supplied tensor.  Otherwise the zero labels are silent no-ops and
    # reproduce the collapsed-BC failure mode that PPO v3 is designed to avoid.
    p_support = np.sum(p_mask & np.isfinite(p_target), axis=0)
    m_support = np.sum(m_mask & np.isfinite(m_target), axis=0)
    missing_p = [str(production_names[i]) for i in range(1, len(production_names)) if not int(p_support[i])]
    missing_m = [str(market_names[i]) for i in range(1, len(market_names)) if not int(m_support[i])]
    if missing_p or missing_m:
        raise ValueError(
            "D2 lacks effective support for non-default experts: "
            f"production={missing_p}, market={missing_m}; collect decision states where each expert changes the executable action"
        )
    return {
        "features": features, "p_mask": p_mask, "m_mask": m_mask, "p_target": p_target, "m_target": m_target,
        "split": split, "production_names": production_names, "market_names": market_names, "effective": effective,
        "metadata": {key: _text(data[key]) for key in ("source", "strategy_family", "episode_id", "pair_id") if key in data.files},
        "support": {"production": p_support.tolist(), "market": m_support.tolist()},
    }


def _masked_mse(prediction, target, mask):
    mask = jnp.asarray(mask, dtype=jnp.float32)
    finite = jnp.isfinite(target).astype(jnp.float32)
    mask = mask * finite
    diff = jnp.where(mask > 0.0, prediction - jnp.nan_to_num(target), 0.0)
    return jnp.sum(jnp.square(diff) * mask) / jnp.maximum(1.0, jnp.sum(mask))


def train(dataset, output: Path, epochs: int, batch_size: int, seed: int, learning_rate: float):
    split = dataset["split"]
    train_indices = np.flatnonzero(split == "train")
    validation_indices = np.flatnonzero(np.isin(split, ["validation", "val"]))
    if not len(train_indices):
        raise ValueError("D2 has no train rows")
    if not len(validation_indices):
        validation_indices = train_indices[-max(1, len(train_indices) // 10):]
        train_indices = train_indices[:-len(validation_indices)]
    if not len(train_indices):
        raise ValueError("too few D2 train rows after validation fallback")
    prod_dim = dataset["p_mask"].shape[1]
    market_dim = dataset["m_mask"].shape[1]
    model = RouterNetwork(prod_dim, market_dim)
    params = initial_params(prod_dim, market_dim, seed=seed)
    optimizer = optax.chain(optax.clip_by_global_norm(0.5), optax.adam(learning_rate))
    opt_state = optimizer.init(params)

    @jax.jit
    def update(params, opt_state, batch):
        def loss_fn(p):
            p_score, m_score, value = model.apply(p, batch["features"])
            p_loss = _masked_mse(p_score, batch["p_target"], batch["p_mask"])
            m_loss = _masked_mse(m_score, batch["m_target"], batch["m_mask"])
            best = jnp.maximum(
                jnp.max(jnp.where(batch["p_mask"], batch["p_target"], -1e6), axis=1),
                jnp.max(jnp.where(batch["m_mask"], batch["m_target"], -1e6), axis=1),
            )
            v_loss = jnp.mean(jnp.square(value - jax.lax.stop_gradient(best)))
            return p_loss + m_loss + 0.25 * v_loss, (p_loss, m_loss, v_loss)
        (loss, parts), grads = jax.value_and_grad(loss_fn, has_aux=True)(params)
        updates, opt_state = optimizer.update(grads, opt_state, params)
        return optax.apply_updates(params, updates), opt_state, loss, parts

    @jax.jit
    def evaluate(params, batch):
        p_score, m_score, value = model.apply(params, batch["features"])
        return (
            _masked_mse(p_score, batch["p_target"], batch["p_mask"]),
            _masked_mse(m_score, batch["m_target"], batch["m_mask"]),
            jnp.mean(value),
        )

    features = dataset["features"]
    arrays = {
        "features": features, "p_mask": dataset["p_mask"], "m_mask": dataset["m_mask"],
        "p_target": dataset["p_target"], "m_target": dataset["m_target"],
    }
    rng = np.random.default_rng(seed)
    history = []
    best = None
    output.mkdir(parents=True, exist_ok=True)
    for epoch in range(int(epochs)):
        order = rng.permutation(train_indices)
        losses = []
        for start in range(0, len(order), int(batch_size)):
            idx = order[start:start + int(batch_size)]
            batch = {key: jnp.asarray(value[idx]) for key, value in arrays.items()}
            params, opt_state, loss, _ = update(params, opt_state, batch)
            losses.append(float(loss))
        val_batch = {key: jnp.asarray(value[validation_indices]) for key, value in arrays.items()}
        p_loss, m_loss, mean_value = evaluate(params, val_batch)
        row = {"epoch": epoch + 1, "train_loss": float(np.mean(losses)), "validation_production_mse": float(p_loss), "validation_market_mse": float(m_loss), "validation_value_mean": float(mean_value)}
        history.append(row)
        criterion = row["validation_production_mse"] + row["validation_market_mse"]
        if best is None or criterion < best[0]:
            best = (criterion, jax.tree.map(lambda x: np.asarray(x), params), row)
        if (epoch + 1) % max(1, int(epochs) // 10) == 0:
            print(json.dumps(row), flush=True)
    assert best is not None
    params = jax.tree.map(jnp.asarray, best[1])
    weights = output / "router_weights.npz"
    export_numpy(params, weights, dataset["production_names"], dataset["market_names"])
    (output / "router_params.msgpack").write_bytes(serialization.to_bytes(params))
    parity = parity_error(params, weights, dataset["production_names"], dataset["market_names"])
    report = {
        "schema": "kaggriculture-ppo-v3-router-training-1",
        "data_rows": int(len(features)), "train_rows": int(len(train_indices)), "validation_rows": int(len(validation_indices)),
        "production_names": dataset["production_names"].tolist(), "market_names": dataset["market_names"].tolist(),
        "effective_action_change_rate": float(np.mean(dataset["effective"])),
        "effective_support": dataset["support"],
        "best": best[2], "epochs": int(epochs), "history": history,
        "numpy_jax_max_abs_error": float(parity), "weights": str(weights), "params": str(output / "router_params.msgpack"),
    }
    (output / "router_training_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=HERE / "checkpoints" / "router_pilot")
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    args = parser.parse_args()
    report = train(load_dataset(args.data), args.output, args.epochs, args.batch_size, args.seed, args.learning_rate)
    print(json.dumps(report, ensure_ascii=False, indent=2))
