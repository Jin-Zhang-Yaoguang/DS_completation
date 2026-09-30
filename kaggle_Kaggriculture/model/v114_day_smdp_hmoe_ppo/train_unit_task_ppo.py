"""Train V12 persistent unit tasks with candidate-level duration-aware PPO."""

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

from model_unit_task_hmoe import UnitTaskHMoE
from unit_task_ppo_math import categorical_stats, ppo_loss, score_candidates


CANDIDATE_KEYS = (
    "role", "operation", "item", "quantity", "target_x", "target_y",
    "duration", "use_item", "use_quantity", "mask",
)


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as sink:
        json.dump(payload, sink, ensure_ascii=False, indent=2)
        sink.write("\n")
        temporary = Path(sink.name)
    temporary.replace(path)


def load_rollouts(paths: list[Path]) -> dict[str, np.ndarray]:
    blocks = []
    for path in paths:
        with np.load(path, allow_pickle=False) as source:
            blocks.append({key: np.asarray(source[key]) for key in source.files})
    required = set(blocks[0])
    if any(set(block) != required for block in blocks):
        raise ValueError("rollout shards do not share an identical schema")
    return {key: np.concatenate([block[key] for block in blocks]) for key in required}


def duration_gae(data: dict[str, np.ndarray], *, gamma_day: float, lambda_day: float) -> tuple[np.ndarray, np.ndarray]:
    rows = len(data["reward"])
    advantage = np.zeros(rows, np.float32)
    returns = np.zeros(rows, np.float32)
    identities = np.stack((data["seed"], data["seat"], data["unit_index"]), axis=1)
    _, inverse = np.unique(identities, axis=0, return_inverse=True)
    for group in range(int(inverse.max()) + 1):
        selected = np.flatnonzero(inverse == group)
        selected = selected[np.argsort(data["start_step"][selected], kind="stable")]
        next_advantage = 0.0
        next_value = 0.0
        for index in selected[::-1]:
            terminal = bool(data["terminal"][index])
            if terminal:
                next_advantage = 0.0
                next_value = 0.0
            discount = gamma_day ** (float(data["duration_turns"][index]) / 24.0)
            trace = lambda_day ** (float(data["duration_turns"][index]) / 24.0)
            delta = float(data["reward"][index]) + (0.0 if terminal else discount * next_value) - float(data["value"][index])
            current = delta + (0.0 if terminal else discount * trace * next_advantage)
            advantage[index] = current
            returns[index] = current + float(data["value"][index])
            next_advantage = current
            next_value = float(data["value"][index])
    return advantage, returns


def normalize_by_operation(values: np.ndarray, operations: np.ndarray) -> tuple[np.ndarray, dict]:
    result = np.zeros_like(values, dtype=np.float32)
    report = {}
    for operation in sorted(set(operations.tolist())):
        selected = operations == operation
        group = np.asarray(values[selected], np.float64)
        mean = float(group.mean())
        std = float(group.std())
        result[selected] = ((group - mean) / max(std, 1e-6)).astype(np.float32)
        report[str(operation)] = {"rows": int(selected.sum()), "mean": mean, "std": std}
    return result, report


def batch_from(data: dict[str, np.ndarray], selected: np.ndarray) -> dict:
    candidates = {
        key: jnp.asarray(data[f"candidate_{key}"][selected]) for key in CANDIDATE_KEYS
    }
    return {
        "global": jnp.asarray(data["global"][selected], jnp.float32),
        "board": jnp.asarray(data["board"][selected], jnp.float32),
        "unit": jnp.asarray(data["unit"][selected], jnp.float32),
        "candidates": candidates,
        "action": jnp.asarray(data["action"][selected], jnp.int32),
        "old_logp": jnp.asarray(data["old_logp"][selected], jnp.float32),
        "advantage": jnp.asarray(data["advantage"][selected], jnp.float32),
        "returns": jnp.asarray(data["returns"][selected], jnp.float32),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--initial-checkpoint", type=Path, required=True)
    parser.add_argument("--rollout-dir", type=Path, required=True)
    parser.add_argument("--output-checkpoint", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=6)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--clip-epsilon", type=float, default=0.15)
    parser.add_argument("--entropy-coefficient", type=float, default=0.002)
    parser.add_argument("--value-coefficient", type=float, default=0.25)
    parser.add_argument("--target-kl", type=float, default=0.01)
    parser.add_argument("--seed", type=int, default=11412002)
    args = parser.parse_args()
    started = time.time()
    paths = sorted(args.rollout_dir.glob("*.npz"))
    if not paths:
        raise ValueError("no rollout shards found")
    data = load_rollouts(paths)
    raw_advantage, returns = duration_gae(data, gamma_day=0.99, lambda_day=0.95)
    normalized, group_report = normalize_by_operation(raw_advantage, data["operation"])
    data["advantage"] = normalized
    data["returns"] = returns

    payload = serialization.msgpack_restore(args.initial_checkpoint.read_bytes())
    if payload.get("strategy_parent") is not None:
        raise ValueError("V12 unit task checkpoint must have strategy_parent=null")
    params = payload["params"]
    model = UnitTaskHMoE()
    optimizer = optax.chain(optax.clip_by_global_norm(0.5), optax.adam(args.learning_rate))
    optimizer_state = optimizer.init(params)

    def loss_fn(current_params, batch):
        outputs = model.apply(
            {"params": current_params}, batch["global"], batch["board"], batch["unit"]
        )
        logits = score_candidates(outputs, batch["candidates"])
        new_logp, entropy = categorical_stats(
            logits, batch["action"], batch["candidates"]["mask"]
        )
        actor, metrics = ppo_loss(
            new_logp, batch["old_logp"], batch["advantage"], entropy,
            clip_epsilon=args.clip_epsilon,
            entropy_coefficient=args.entropy_coefficient,
        )
        value_loss = jnp.mean(optax.huber_loss(outputs["value"], batch["returns"], delta=1.0))
        total = actor + args.value_coefficient * value_loss
        return total, {**metrics, "value_loss": value_loss, "total_loss": total}

    @jax.jit
    def update(current_params, current_optimizer_state, batch):
        (loss, metrics), gradients = jax.value_and_grad(loss_fn, has_aux=True)(current_params, batch)
        updates, next_optimizer_state = optimizer.update(gradients, current_optimizer_state, current_params)
        next_params = optax.apply_updates(current_params, updates)
        return next_params, next_optimizer_state, metrics

    rng = np.random.default_rng(args.seed)
    history = []
    rows = len(data["reward"])
    stopped_for_kl = False
    rolled_back_for_kl = False

    @jax.jit
    def policy_diagnostics(current_params, batch):
        outputs = model.apply(
            {"params": current_params}, batch["global"], batch["board"], batch["unit"]
        )
        logits = score_candidates(outputs, batch["candidates"])
        new_logp, entropy = categorical_stats(
            logits, batch["action"], batch["candidates"]["mask"]
        )
        log_ratio = new_logp - batch["old_logp"]
        return jnp.sum((jnp.exp(log_ratio) - 1.0) - log_ratio), jnp.sum(entropy), new_logp.shape[0]

    def full_diagnostics(current_params) -> dict[str, float]:
        kl_sum = 0.0
        entropy_sum = 0.0
        count = 0
        for offset in range(0, rows, args.batch_size):
            selected = np.arange(offset, min(rows, offset + args.batch_size))
            kl, entropy, size = policy_diagnostics(current_params, batch_from(data, selected))
            kl_sum += float(kl)
            entropy_sum += float(entropy)
            count += int(size)
        return {"full_approximate_kl": kl_sum / count, "full_entropy": entropy_sum / count}

    last_safe_params = params
    last_safe_optimizer_state = optimizer_state
    optimizer_steps = 0
    for epoch in range(1, args.epochs + 1):
        order = rng.permutation(rows)
        epoch_metrics = []
        for offset in range(0, rows, args.batch_size):
            selected = order[offset:offset + args.batch_size]
            params, optimizer_state, metrics = update(
                params, optimizer_state, batch_from(data, selected)
            )
            optimizer_steps += 1
            epoch_metrics.append({key: float(value) for key, value in metrics.items()})
            if optimizer_steps % 2 == 0:
                diagnostic = full_diagnostics(params)
                if diagnostic["full_approximate_kl"] > args.target_kl:
                    params = last_safe_params
                    optimizer_state = last_safe_optimizer_state
                    stopped_for_kl = True
                    rolled_back_for_kl = True
                    break
                last_safe_params = params
                last_safe_optimizer_state = optimizer_state
        summary = {
            "epoch": epoch,
            **{key: float(np.mean([row[key] for row in epoch_metrics])) for key in epoch_metrics[0]},
        }
        summary.update(full_diagnostics(params))
        history.append(summary)
        print(json.dumps(summary, ensure_ascii=False), flush=True)
        if stopped_for_kl:
            break

    output_payload = {
        **payload,
        "params": params,
        "training_method": "candidate_level_duration_aware_smdp_ppo_v1",
        "initial_checkpoint_sha256": hashlib.sha256(args.initial_checkpoint.read_bytes()).hexdigest(),
        "rollout_shard_sha256": [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths],
        "ppo_training_seed": args.seed,
        "qualification_status": "UNIT_TASK_PPO_TRAINING_ARTIFACT_NOT_G1_NOT_FOUNDATION_NOT_GOLD",
    }
    args.output_checkpoint.parent.mkdir(parents=True, exist_ok=True)
    args.output_checkpoint.write_bytes(serialization.msgpack_serialize(output_payload))
    report = {
        "schema": "kaggriculture-v114-v12-unit-task-ppo-training-v1",
        "status": "TRAINING_ARTIFACT_NOT_G1_NOT_FOUNDATION_NOT_GOLD",
        "initial_checkpoint": str(args.initial_checkpoint.resolve()),
        "initial_checkpoint_sha256": hashlib.sha256(args.initial_checkpoint.read_bytes()).hexdigest(),
        "output_checkpoint": str(args.output_checkpoint.resolve()),
        "output_checkpoint_sha256": hashlib.sha256(args.output_checkpoint.read_bytes()).hexdigest(),
        "rollout_shards": [str(path.resolve()) for path in paths],
        "rows": rows,
        "success_rate": float(np.mean(data["status"] == "success")),
        "reward_mean": float(np.mean(data["reward"])),
        "advantage_groups": group_report,
        "epochs_requested": args.epochs,
        "epochs_completed": len(history),
        "stopped_for_kl": stopped_for_kl,
        "rolled_back_for_kl": rolled_back_for_kl,
        "optimizer_steps": optimizer_steps,
        "target_kl": args.target_kl,
        "value_coefficient": args.value_coefficient,
        "history": history,
        "fresh_evidence": False,
        "elapsed_seconds": time.time() - started,
    }
    _atomic_json(args.report, report)
    print(json.dumps({key: report[key] for key in (
        "status", "rows", "success_rate", "epochs_completed", "stopped_for_kl",
        "output_checkpoint_sha256", "elapsed_seconds"
    )}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
