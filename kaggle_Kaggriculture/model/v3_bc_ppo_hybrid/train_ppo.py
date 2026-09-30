"""On-policy PPO training for the daily v3 macro controller."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import time

import jax
import jax.numpy as jnp
import numpy as np
import optax
from flax import serialization

import main
import base_agent
from model_jax import MacroPolicy, export_numpy, initial_params, load_checkpoint, parity_error, save_checkpoint


HERE = Path(__file__).resolve().parent
MODEL_DIR = HERE.parent
_WORKER_CACHE = {}


def _seed_bucket(seed):
    digest = hashlib.sha256(str(int(seed)).encode("ascii")).digest()
    return int.from_bytes(digest[:8], "big") % 100


def _training_seeds(start, count):
    seeds = []
    candidate = int(start)
    while len(seeds) < count:
        if _seed_bucket(candidate) < 80:
            seeds.append(candidate)
        candidate += 7919
    return seeds


def _load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _worker_modules():
    if "v0" not in _WORKER_CACHE:
        process_id = os.getpid()
        _WORKER_CACHE["v0"] = _load_module(MODEL_DIR / "v0_api_smoke" / "main.py", f"ppo_v0_{process_id}")
        _WORKER_CACHE["v1"] = _load_module(MODEL_DIR / "v1_adaptive_market" / "main.py", f"ppo_v1_{process_id}")
    return _WORKER_CACHE


def _forced_route(module, route):
    def opponent(obs):
        module._ACTIONS = module._HIGH_ROUTE_ACTIONS if route == 1 else module._LOW_ROUTE_ACTIONS
        return module._CORE_AGENT(obs)
    return opponent


def _market_variant(module, scale):
    def opponent(obs):
        raw = module.agent(obs)
        action = {
            "farmer": list(raw.get("farmer") or ["PASS"]),
            "hands": [list(order or ["PASS"]) for order in list(raw.get("hands") or [])],
            "market": [list(order) for order in list(raw.get("market") or [])],
        }
        for order in action["market"]:
            if len(order) >= 3 and order[0] == "SELL":
                order[2] = max(0, int(round(int(order[2] or 0) * scale)))
        return action
    return opponent


class HybridRolloutAgent:
    def __init__(self, policy, seat, rng, stochastic, record):
        self.policy = policy
        self.seat = int(seat)
        self.rng = rng
        self.stochastic = stochastic
        self.record = record
        self.hidden = np.zeros(main.HIDDEN_SIZE, dtype=np.float32)
        self.history = {}
        self.macro = main.DEFAULT_MACRO.copy()
        self.route = None
        self.rows = []

    def __call__(self, obs):
        step = int(obs.get("step", 0) or 0)
        day = int(obs.get("day", step // 24) or 0)
        hour = int(obs.get("hour", step % 24) or 0)
        if step == 0:
            self.hidden = np.zeros(main.HIDDEN_SIZE, dtype=np.float32)
            self.history = {}
            self.macro = main.DEFAULT_MACRO.copy()
            self.route = None
            self.rows = []
        if hour == 0:
            features = main.encode_observation(obs, self.history, self.macro)
            hidden_before = self.hidden.copy()
            selected, log_probability, value, self.hidden, logits = self.policy.act(
                features,
                self.hidden,
                stochastic=self.stochastic,
                rng=self.rng,
                route_enabled=(day == 7),
            )
            if day < 7:
                selected[0] = 0
            elif day == 7:
                self.route = int(selected[0])
            else:
                selected[0] = int(self.route if self.route is not None else main.teacher_route(obs))
            action_mask = main.macro_action_mask(day, selected[0])
            for head in range(1, len(main.HEAD_SIZES)):
                if not action_mask[head]:
                    selected[head] = main.DEFAULT_MACRO[head]
            # Recompute the behavior-policy probability using only heads that
            # can affect this day's frozen v2 schedule.
            log_probability = 0.0
            for head, head_logits in enumerate(logits):
                if not action_mask[head]:
                    continue
                values = np.asarray(head_logits, dtype=np.float64)
                values -= values.max()
                probabilities = np.exp(values) / np.exp(values).sum()
                log_probability += math.log(max(1e-12, float(probabilities[int(selected[head])])))
            self.macro = selected
            if self.record:
                self.rows.append(
                    {
                        "features": features,
                        "hidden": hidden_before,
                        "actions": selected.copy(),
                        "log_probability": log_probability,
                        "value": value,
                        "action_mask": action_mask,
                        "potential": main.potential(obs),
                    }
                )
            self.history = main.update_history(obs, selected)
        if self.route is None:
            raw = base_agent.agent(obs)
        else:
            base_agent._ACTIONS = base_agent._HIGH_ROUTE_ACTIONS if self.route == 1 else base_agent._LOW_ROUTE_ACTIONS
            raw = base_agent._CORE_AGENT(obs)
        return main.apply_macro(obs, raw, self.macro, step)


def _fixed_opponent(name):
    from kaggle_environments.envs.kaggriculture import kaggriculture as kg
    modules = _worker_modules()
    return {
        "v0": modules["v0"].agent,
        "v1": modules["v1"].agent,
        "v2": base_agent.agent,
        "starter": kg.starter_agent,
        "random": kg.random_agent,
        "forced_low": _forced_route(base_agent, 0),
        "forced_high": _forced_route(base_agent, 1),
        "market_half": _market_variant(base_agent, 0.5),
        "market_double": _market_variant(base_agent, 2.0),
    }[name]


def _advantages(rewards, values, gamma, gae_lambda):
    result = np.zeros_like(rewards, dtype=np.float32)
    carry = 0.0
    next_value = 0.0
    for index in range(len(rewards) - 1, -1, -1):
        delta = rewards[index] + gamma * next_value - values[index]
        carry = delta + gamma * gae_lambda * carry
        result[index] = carry
        next_value = values[index]
    return result, result + values


def _rollout_episode(task, weight_path, gamma, gae_lambda, league_paths):
    from kaggle_environments import make
    index, seed, seat, opponent_name = task
    # A worker handles many episodes per pool. Reuse immutable weights instead
    # of reopening the same archive for every episode.
    policy_key = ("policy", str(weight_path))
    if policy_key not in _WORKER_CACHE:
        _WORKER_CACHE[policy_key] = main.NumpyPolicy(weight_path)
    policy = _WORKER_CACHE[policy_key]
    rng = np.random.default_rng(seed ^ 0x5A17)
    candidate = HybridRolloutAgent(policy, seat, rng, True, True)
    if opponent_name.startswith("league:"):
        snapshot_index = int(opponent_name.split(":", 1)[1])
        league_key = ("league", str(league_paths[snapshot_index]))
        if league_key not in _WORKER_CACHE:
            _WORKER_CACHE[league_key] = main.NumpyPolicy(league_paths[snapshot_index])
        opponent_policy = _WORKER_CACHE[league_key]
        opponent = HybridRolloutAgent(opponent_policy, 1 - seat, np.random.default_rng(seed ^ 0x7711), False, False)
    else:
        opponent = _fixed_opponent(opponent_name)
    agents = [candidate, opponent] if seat == 0 else [opponent, candidate]
    env = make("kaggriculture", configuration={"seed": int(seed)}, debug=False)
    env.reset(2)
    for step in range(719):
        env.state[0].observation.step = step
        env.state[1].observation.step = step
        env.step([agents[0](env.state[0].observation), agents[1](env.state[1].observation)])
    statuses = [str(state.status) for state in env.state]
    if statuses != ["DONE", "DONE"] or len(candidate.rows) != 30:
        raise RuntimeError((index, seed, statuses, len(candidate.rows)))
    final_rewards = np.asarray([float(state.reward or 0.0) for state in env.state], dtype=np.float32)
    own = final_rewards[seat]
    other = final_rewards[1 - seat]
    terminal = float(np.sign(own - other) + 0.1 * np.tanh((own - other) / 25000.0))
    potentials = np.asarray([row["potential"] for row in candidate.rows], dtype=np.float32)
    shaped = np.zeros(30, dtype=np.float32)
    shaped[:-1] = gamma * potentials[1:] - potentials[:-1]
    shaped[-1] = terminal - potentials[-1]
    values = np.asarray([row["value"] for row in candidate.rows], dtype=np.float32)
    advantages, returns = _advantages(shaped, values, gamma, gae_lambda)
    return {
        "index": index,
        "features": np.stack([row["features"] for row in candidate.rows]),
        "hidden": np.stack([row["hidden"] for row in candidate.rows]),
        "actions": np.stack([row["actions"] for row in candidate.rows]),
        "old_log_probability": np.asarray([row["log_probability"] for row in candidate.rows], dtype=np.float32),
        "old_value": values,
        "action_mask": np.stack([row["action_mask"] for row in candidate.rows]).astype(np.float32),
        "advantages": advantages,
        "returns": returns,
        "final_rewards": final_rewards,
        "seat": seat,
        "opponent": opponent_name,
        "terminal": terminal,
    }


def collect_rollouts(weight_path, episodes, workers, iteration, gamma, gae_lambda, league_paths):
    fixed = ("v2", "v2", "v1", "v0", "starter", "random", "forced_low", "forced_high", "market_half", "market_double")
    opponent_pool = list(fixed)
    if iteration * episodes >= 20000 and league_paths:
        opponent_pool.extend(f"league:{index}" for index in range(len(league_paths)))
    tasks = []
    seeds = _training_seeds(41000000 + iteration * 1000003, episodes)
    for index, seed in enumerate(seeds):
        tasks.append((index, seed, index % 2, opponent_pool[index % len(opponent_pool)]))
    rows = []
    started = time.time()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_rollout_episode, task, str(weight_path), gamma, gae_lambda, [str(path) for path in league_paths]) for task in tasks]
        for completed, future in enumerate(as_completed(futures), start=1):
            rows.append(future.result())
            if completed % max(1, episodes // 4) == 0 or completed == episodes:
                print(json.dumps({"phase": "rollout", "iteration": iteration, "completed": completed, "episodes": episodes, "episodes_per_second": completed / max(1e-6, time.time() - started)}), flush=True)
    rows.sort(key=lambda row: row["index"])
    keys = ("features", "hidden", "actions", "old_log_probability", "old_value", "action_mask", "advantages", "returns")
    batch = {key: np.stack([row[key] for row in rows]) for key in keys}
    batch["final_rewards"] = np.stack([row["final_rewards"] for row in rows])
    batch["seats"] = np.asarray([row["seat"] for row in rows], dtype=np.int8)
    batch["terminals"] = np.asarray([row["terminal"] for row in rows], dtype=np.float32)
    batch["opponents"] = np.asarray([row["opponent"] for row in rows])
    return batch, time.time() - started


def _log_probability_and_entropy(logits, actions, action_mask):
    total_log_probability = jnp.zeros(actions.shape[:-1], dtype=jnp.float32)
    total_entropy = jnp.zeros_like(total_log_probability)
    for index, head_logits in enumerate(logits):
        log_probs = jax.nn.log_softmax(head_logits, axis=-1)
        probabilities = jax.nn.softmax(head_logits, axis=-1)
        selected = jnp.take_along_axis(log_probs, actions[..., index, None], axis=-1)[..., 0]
        entropy = -jnp.sum(probabilities * log_probs, axis=-1)
        mask = action_mask[..., index]
        total_log_probability += selected * mask
        total_entropy += entropy * mask
    return total_log_probability, total_entropy


def make_ppo_loss(model, clip_ratio, value_coefficient):
    def loss_fn(params, batch, entropy_coefficient):
        logits, values, _ = model.apply(params, batch["features"], batch["hidden"])
        log_probability, entropy = _log_probability_and_entropy(logits, batch["actions"], batch["action_mask"])
        valid = jnp.max(batch["action_mask"], axis=-1)
        valid_count = jnp.maximum(1.0, jnp.sum(valid))
        ratio = jnp.exp(log_probability - batch["old_log_probability"])
        unclipped = ratio * batch["advantages"]
        clipped = jnp.clip(ratio, 1.0 - clip_ratio, 1.0 + clip_ratio) * batch["advantages"]
        policy_loss = -jnp.sum(jnp.minimum(unclipped, clipped) * valid) / valid_count
        clipped_value = batch["old_value"] + jnp.clip(values - batch["old_value"], -clip_ratio, clip_ratio)
        value_loss = 0.5 * jnp.mean(jnp.maximum(jnp.square(values - batch["returns"]), jnp.square(clipped_value - batch["returns"])))
        entropy_mean = jnp.sum(entropy * valid) / valid_count
        total = policy_loss + value_coefficient * value_loss - entropy_coefficient * entropy_mean
        approximate_kl = jnp.sum((batch["old_log_probability"] - log_probability) * valid) / valid_count
        clip_fraction = jnp.sum((jnp.abs(ratio - 1.0) > clip_ratio) * valid) / valid_count
        return total, {
            "loss": total,
            "policy_loss": policy_loss,
            "value_loss": value_loss,
            "entropy": entropy_mean,
            "approximate_kl": approximate_kl,
            "clip_fraction": clip_fraction,
        }
    return loss_fn


def _jax_batch(batch, indices):
    flattened = {
        "features": batch["features"].reshape(-1, main.FEATURE_DIM),
        "hidden": batch["hidden"].reshape(-1, main.HIDDEN_SIZE),
        "actions": batch["actions"].reshape(-1, len(main.HEAD_SIZES)),
        "old_log_probability": batch["old_log_probability"].reshape(-1),
        "old_value": batch["old_value"].reshape(-1),
        "action_mask": batch["action_mask"].reshape(-1, len(main.HEAD_SIZES)),
        "advantages": batch["advantages"].reshape(-1),
        "returns": batch["returns"].reshape(-1),
    }
    return {
        key: jnp.asarray(value[indices], dtype=jnp.int32 if key == "actions" else jnp.float32)
        for key, value in flattened.items()
    }


def _qualify_snapshot(weight_path, workers, seeds=32):
    """Use only validation-partition seeds before admitting a league policy."""
    from evaluate import _partition_seeds, _run_tasks

    tasks = []
    index = 0
    for seed in _partition_seeds(81000000, seeds, 80, 90):
        for seat in (0, 1):
            tasks.append((index, seed, seat, "v3", "v2"))
            index += 1
    rows = _run_tasks(tasks, weight_path, workers)
    score_rate = float(np.mean([row["score"] for row in rows]))
    mean_margin = float(np.mean([row["margin"] for row in rows]))
    return {
        "seeds": seeds,
        "games": len(rows),
        "score_rate": score_rate,
        "mean_margin": mean_margin,
        "passed": bool(score_rate >= 0.5 and mean_margin >= 0.0),
    }


def _read_jsonl(path):
    if not Path(path).is_file():
        return []
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def _save_resume_state(output_dir, params, optimizer_state, completed_iteration, rng):
    payload = serialization.to_bytes({"params": params, "optimizer_state": optimizer_state})
    temporary = output_dir / "ppo_state_latest.msgpack.tmp"
    temporary.write_bytes(payload)
    temporary.replace(output_dir / "ppo_state_latest.msgpack")
    metadata = output_dir / "ppo_state.json.tmp"
    metadata.write_text(json.dumps({
        "completed_iteration": completed_iteration,
        "numpy_rng_state": rng.bit_generator.state,
    }) + "\n", encoding="utf-8")
    metadata.replace(output_dir / "ppo_state.json")


def train(bc_checkpoint, output_dir, iterations=50, episodes_per_iteration=2048, workers=12, epochs=4, transition_batch=4096, seed=17, resume=False, qualification_seeds=32):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    model = MacroPolicy()
    params = load_checkpoint(bc_checkpoint, initial_params())
    transitions_per_iteration = episodes_per_iteration * 30
    updates_per_iteration = epochs * math.ceil(transitions_per_iteration / transition_batch)
    schedule = optax.linear_schedule(3e-4, 5e-5, max(1, iterations * updates_per_iteration))
    optimizer = optax.chain(optax.clip_by_global_norm(0.5), optax.adam(schedule))
    optimizer_state = optimizer.init(params)
    loss_fn = make_ppo_loss(model, 0.2, 0.5)

    @jax.jit
    def update(params, optimizer_state, batch, entropy_coefficient):
        (_, metrics), gradients = jax.value_and_grad(loss_fn, has_aux=True)(params, batch, entropy_coefficient)
        updates, optimizer_state = optimizer.update(gradients, optimizer_state, params)
        return optax.apply_updates(params, updates), optimizer_state, metrics

    start_iteration = 0
    metrics_path = output_dir / "ppo_metrics.jsonl"
    qualifications_path = output_dir / "snapshot_qualifications.jsonl"
    history = _read_jsonl(metrics_path) if resume else []
    qualifications = _read_jsonl(qualifications_path) if resume else []
    if resume:
        state_path = output_dir / "ppo_state_latest.msgpack"
        metadata_path = output_dir / "ppo_state.json"
        if not state_path.is_file() or not metadata_path.is_file():
            raise FileNotFoundError("resume requested but PPO state is incomplete")
        template = {"params": params, "optimizer_state": optimizer_state}
        restored = serialization.from_bytes(template, state_path.read_bytes())
        params, optimizer_state = restored["params"], restored["optimizer_state"]
        resume_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        start_iteration = int(resume_metadata["completed_iteration"])
    elif metrics_path.exists() or qualifications_path.exists():
        raise FileExistsError("output contains PPO logs; use --resume or a new output directory")

    rng = np.random.default_rng(seed)
    if resume:
        rng.bit_generator.state = resume_metadata["numpy_rng_state"]
    league_paths = [output_dir / f"policy_iter_{row['iteration']:03d}.npz" for row in qualifications if row.get("passed")]
    started = time.time()
    for iteration in range(start_iteration + 1, iterations + 1):
        rollout_weights = output_dir / "rollout_weights.npz"
        export_numpy(params, rollout_weights)
        rollout, rollout_seconds = collect_rollouts(
            rollout_weights,
            episodes_per_iteration,
            workers,
            iteration - 1,
            0.995,
            0.95,
            league_paths,
        )
        advantage_mean = float(rollout["advantages"].mean())
        advantage_std = float(rollout["advantages"].std())
        rollout["advantages"] = (rollout["advantages"] - advantage_mean) / max(advantage_std, 1e-6)
        entropy_coefficient = float(0.02 + (0.002 - 0.02) * ((iteration - 1) / max(1, iterations - 1)))
        metrics_rows = []
        early_stop = False
        for epoch in range(epochs):
            shuffled = rng.permutation(transitions_per_iteration)
            for start in range(0, transitions_per_iteration, transition_batch):
                indices = shuffled[start : start + transition_batch]
                params, optimizer_state, metrics = update(
                    params,
                    optimizer_state,
                    _jax_batch(rollout, indices),
                    entropy_coefficient,
                )
                row = {key: float(value) for key, value in metrics.items()}
                metrics_rows.append(row)
                if row["approximate_kl"] > 0.02:
                    early_stop = True
                    break
            if early_stop:
                break

        seats = rollout["seats"].astype(np.int64)
        own = rollout["final_rewards"][np.arange(episodes_per_iteration), seats]
        other = rollout["final_rewards"][np.arange(episodes_per_iteration), 1 - seats]
        summary = {
            "iteration": iteration,
            "episodes": episodes_per_iteration,
            "rollout_seconds": rollout_seconds,
            "episodes_per_second": episodes_per_iteration / max(rollout_seconds, 1e-6),
            "win_rate": float(np.mean(own > other)),
            "mean_margin": float(np.mean(own - other)),
            "mean_own_reward": float(np.mean(own)),
            "entropy_coefficient": entropy_coefficient,
            "advantage_mean": advantage_mean,
            "advantage_std": advantage_std,
            "early_stop_kl": early_stop,
            "update": {key: float(np.mean([row[key] for row in metrics_rows])) for key in metrics_rows[0]},
        }
        history.append(summary)
        print(json.dumps({"phase": "iteration", **summary}), flush=True)
        with metrics_path.open("a", encoding="utf-8") as destination:
            destination.write(json.dumps(summary, ensure_ascii=False) + "\n")

        if iteration % 5 == 0 or iteration == iterations:
            checkpoint = output_dir / f"ppo_iter_{iteration:03d}.msgpack"
            snapshot = output_dir / f"policy_iter_{iteration:03d}.npz"
            save_checkpoint(checkpoint, params)
            export_numpy(params, snapshot)
            qualification = {"iteration": iteration, **_qualify_snapshot(snapshot, workers, qualification_seeds)}
            qualifications.append(qualification)
            with qualifications_path.open("a", encoding="utf-8") as destination:
                destination.write(json.dumps(qualification, ensure_ascii=False) + "\n")
            print(json.dumps({"phase": "snapshot_qualification", **qualification}), flush=True)
            if qualification["passed"]:
                league_paths.append(snapshot)
        _save_resume_state(output_dir, params, optimizer_state, iteration, rng)

    final_checkpoint = output_dir / "ppo_final.msgpack"
    final_weights = output_dir / "policy_weights.npz"
    save_checkpoint(final_checkpoint, params)
    export_numpy(params, final_weights)
    report = {
        "schema": "kaggriculture-v3-ppo-report-1",
        "iterations": iterations,
        "episodes_per_iteration": episodes_per_iteration,
        "total_episodes": iterations * episodes_per_iteration,
        "workers": workers,
        "epochs": epochs,
        "transition_batch": transition_batch,
        "elapsed_seconds": time.time() - started,
        "resumed_from_iteration": start_iteration,
        "parity_max_abs_error": parity_error(params, final_weights),
        "league_snapshots": [path.name for path in league_paths],
        "snapshot_qualifications": qualifications,
        "history": history,
        "final_checkpoint": final_checkpoint.name,
        "final_weights": final_weights.name,
    }
    (output_dir / "ppo_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bc-checkpoint", type=Path, default=HERE / "checkpoints" / "bc" / "bc_params.msgpack")
    parser.add_argument("--output", type=Path, default=HERE / "checkpoints" / "ppo")
    parser.add_argument("--iterations", type=int, default=50)
    parser.add_argument("--episodes-per-iteration", type=int, default=2048)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--transition-batch", type=int, default=4096)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--qualification-seeds", type=int, default=32)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print(json.dumps(train(args.bc_checkpoint, args.output, args.iterations, args.episodes_per_iteration, args.workers, args.epochs, args.transition_batch, args.seed, args.resume, args.qualification_seeds), ensure_ascii=False, indent=2))
