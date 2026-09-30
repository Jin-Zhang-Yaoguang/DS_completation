"""Duration-aware PPO update for V12 event transaction experts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import time

from flax import serialization
import jax
import jax.numpy as jnp
import numpy as np
import optax

from event_market_ppo_math import calibrated_presence_logits, factorized_logp_entropy
from model_event_market_hmoe import EventMarketHMoE


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as sink:
        json.dump(payload, sink, ensure_ascii=False, indent=2); sink.write("\n")
        temporary = Path(sink.name)
    temporary.replace(path)


def load(paths: list[Path]) -> dict[str, np.ndarray]:
    blocks = []
    for path in paths:
        with np.load(path, allow_pickle=False) as source:
            blocks.append({key: np.asarray(source[key]) for key in source.files})
    keys = set(blocks[0])
    if any(set(block) != keys for block in blocks):
        raise ValueError("rollout schemas differ")
    return {key: np.concatenate([block[key] for block in blocks]) for key in keys}


def gae(data, gamma_day=0.99, lambda_day=0.95):
    rows = len(data["reward"]); advantage = np.zeros(rows, np.float32); returns = np.zeros(rows, np.float32)
    identity = np.stack((data["seed"], data["seat"]), axis=1)
    _, inverse = np.unique(identity, axis=0, return_inverse=True)
    for group in range(int(inverse.max()) + 1):
        selected = np.flatnonzero(inverse == group)
        selected = selected[np.argsort(data["start_step"][selected], kind="stable")]
        next_adv = 0.0; next_value = 0.0
        for index in selected[::-1]:
            terminal = bool(data["terminal"][index])
            if terminal: next_adv = 0.0; next_value = 0.0
            gamma = gamma_day ** (float(data["duration_turns"][index]) / 24.0)
            lam = lambda_day ** (float(data["duration_turns"][index]) / 24.0)
            delta = float(data["reward"][index]) + (0.0 if terminal else gamma * next_value) - float(data["value"][index])
            current = delta + (0.0 if terminal else gamma * lam * next_adv)
            advantage[index] = current; returns[index] = current + float(data["value"][index])
            next_adv = current; next_value = float(data["value"][index])
    return advantage, returns


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--initial-checkpoint", type=Path, required=True)
    parser.add_argument("--rollout-dir", type=Path, required=True)
    parser.add_argument("--output-checkpoint", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--target-kl", type=float, default=0.01)
    parser.add_argument("--seed", type=int, default=11412004)
    args = parser.parse_args(); started = time.time()
    paths = sorted(args.rollout_dir.glob("*.npz")); data = load(paths)
    raw_advantage, returns = gae(data)
    advantage = np.zeros_like(raw_advantage)
    groups = {}
    for event_type in np.unique(data["event_type"]):
        selected = data["event_type"] == event_type
        values = raw_advantage[selected]; mean = float(values.mean()); std = float(values.std())
        advantage[selected] = (values - mean) / max(std, 1e-6)
        groups[str(int(event_type))] = {"rows": int(selected.sum()), "mean": mean, "std": std}
    data["advantage"] = advantage; data["returns"] = returns
    payload = serialization.msgpack_restore(args.initial_checkpoint.read_bytes())
    params = payload["params"]; thresholds = jnp.asarray(payload["presence_thresholds"], jnp.float32)
    model = EventMarketHMoE(); optimizer = optax.chain(optax.clip_by_global_norm(0.5), optax.adam(args.learning_rate)); state = optimizer.init(params)

    def batch(selected):
        return {key: jnp.asarray(data[key][selected]) for key in (
            "global", "board", "event_type", "presence_action", "quantity_action",
            "presence_mask", "quantity_mask", "old_logp", "advantage", "returns",
        )}

    def loss_fn(current_params, value):
        output = model.apply({"params": current_params}, value["global"], value["board"], value["event_type"])
        presence_logits = calibrated_presence_logits(
            output["presence_logits"], thresholds[None], value["presence_mask"]
        )
        logp, entropy = factorized_logp_entropy(
            presence_logits, output["quantity_logits"] / 0.5,
            value["presence_action"], value["quantity_action"],
            value["presence_mask"], value["quantity_mask"],
        )
        log_ratio = logp - jax.lax.stop_gradient(value["old_logp"]); ratio = jnp.exp(log_ratio)
        unclipped = ratio * jax.lax.stop_gradient(value["advantage"])
        clipped = jnp.clip(ratio, 0.85, 1.15) * jax.lax.stop_gradient(value["advantage"])
        actor = -jnp.mean(jnp.minimum(unclipped, clipped)) - 0.001 * jnp.mean(entropy)
        value_loss = jnp.mean(optax.huber_loss(output["value"], value["returns"], delta=1.0))
        total = actor + 0.25 * value_loss
        return total, {
            "actor_loss": actor, "value_loss": value_loss,
            "approximate_kl": jnp.mean((ratio - 1.0) - log_ratio),
            "entropy": jnp.mean(entropy), "total_loss": total,
        }

    @jax.jit
    def update(current_params, current_state, value):
        (_, metrics), gradients = jax.value_and_grad(loss_fn, has_aux=True)(current_params, value)
        updates, next_state = optimizer.update(gradients, current_state, current_params)
        return optax.apply_updates(current_params, updates), next_state, metrics

    @jax.jit
    def diagnostic(current_params, value):
        output = model.apply({"params": current_params}, value["global"], value["board"], value["event_type"])
        presence = calibrated_presence_logits(output["presence_logits"], thresholds[None], value["presence_mask"])
        logp, _ = factorized_logp_entropy(
            presence, output["quantity_logits"] / 0.5, value["presence_action"],
            value["quantity_action"], value["presence_mask"], value["quantity_mask"],
        )
        ratio = jnp.exp(logp - value["old_logp"])
        return jnp.mean((ratio - 1.0) - (logp - value["old_logp"]))

    rng = np.random.default_rng(args.seed); rows = len(data["reward"]); history = []
    safe_params = params; safe_state = state; stopped = False; steps = 0
    for epoch in range(1, args.epochs + 1):
        metrics_rows = []
        order = rng.permutation(rows)
        for offset in range(0, rows, args.batch_size):
            selected = order[offset:offset + args.batch_size]
            params, state, metrics = update(params, state, batch(selected)); steps += 1
            metrics_rows.append({key: float(item) for key, item in metrics.items()})
            full_kl = float(diagnostic(params, batch(np.arange(rows))))
            if full_kl > args.target_kl:
                params, state = safe_params, safe_state; stopped = True; break
            safe_params, safe_state = params, state
        row = {"epoch": epoch, **{key: float(np.mean([item[key] for item in metrics_rows])) for key in metrics_rows[0]}, "full_approximate_kl": float(diagnostic(params, batch(np.arange(rows))))}
        history.append(row); print(json.dumps(row), flush=True)
        if stopped: break
    output = {**payload, "params": params, "training_method": "event_transaction_duration_aware_smdp_ppo_v1", "initial_checkpoint_sha256": hashlib.sha256(args.initial_checkpoint.read_bytes()).hexdigest(), "qualification_status": "EVENT_MARKET_PPO_TRAINING_ARTIFACT_NOT_G2_NOT_GOLD"}
    args.output_checkpoint.parent.mkdir(parents=True, exist_ok=True); args.output_checkpoint.write_bytes(serialization.msgpack_serialize(output))
    report = {
        "schema": "kaggriculture-v114-v12-event-market-ppo-v1", "status": "TRAINING_ARTIFACT_NOT_G2_NOT_GOLD",
        "rows": rows, "games": len(np.unique(np.stack((data["seed"], data["seat"]), axis=1), axis=0)),
        "mean_episode_return": float(np.mean([np.asarray(np.load(path)["episode_return"])[0] for path in paths])),
        "advantage_groups": groups, "optimizer_steps": steps, "stopped_for_kl": stopped,
        "history": history, "output_checkpoint": str(args.output_checkpoint.resolve()),
        "output_checkpoint_sha256": hashlib.sha256(args.output_checkpoint.read_bytes()).hexdigest(),
        "fresh_evidence": False, "elapsed_seconds": time.time() - started,
    }
    atomic_json(args.report, report); print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
