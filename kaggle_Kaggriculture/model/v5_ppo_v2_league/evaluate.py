"""Paired offline evaluation for v3 against v2 and the holdout pool."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import time

import numpy as np

import base_agent
import main


HERE = Path(__file__).resolve().parent
MODEL_DIR = HERE.parent
_CACHE = {}


def _seed_bucket(seed):
    digest = hashlib.sha256(str(int(seed)).encode("ascii")).digest()
    return int.from_bytes(digest[:8], "big") % 100


def _partition_seeds(start, count, low=90, high=100):
    result = []
    candidate = int(start)
    while len(result) < count:
        if low <= _seed_bucket(candidate) < high:
            result.append(candidate)
        candidate += 7919
    return result


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _opponent(name):
    from kaggle_environments.envs.kaggriculture import kaggriculture as kg
    process = os.getpid()
    if "v0" not in _CACHE:
        _CACHE["v0"] = _load(MODEL_DIR / "v0_api_smoke" / "main.py", f"eval_v0_{process}")
        _CACHE["v1"] = _load(MODEL_DIR / "v1_adaptive_market" / "main.py", f"eval_v1_{process}")
        _CACHE["v2"] = _load(MODEL_DIR / "v3_bc_ppo_hybrid" / "base_agent.py", f"eval_v2_{process}")
    if name == "forced_low" or name == "forced_high":
        route = int(name == "forced_high")

        def forced(obs):
            base_agent._ACTIONS = base_agent._HIGH_ROUTE_ACTIONS if route else base_agent._LOW_ROUTE_ACTIONS
            return base_agent._CORE_AGENT(obs)
        return forced
    builtins = {
        "v0": _CACHE["v0"].agent,
        "v1": _CACHE["v1"].agent,
        "v2": _CACHE["v2"].agent,
        "starter": kg.starter_agent,
        "random": kg.random_agent,
    }
    if name in builtins:
        return builtins[name]
    # The formal G4 qualification uses the same 28 executable variants as
    # rollout.  Reuse the audited factory so qualification and training do
    # not silently evaluate different opponent pools.
    from train_ppo import _fixed_opponent
    return _fixed_opponent(name)


def _candidate(kind, weights):
    if kind == "v1":
        return base_agent.agent
    key = ("weights", str(weights))
    if key not in _CACHE:
        _CACHE[key] = main.NumpyPolicy(weights)
    main.MODEL_FILE = Path(weights)
    main._POLICY = _CACHE[key]
    main._POLICY_ERROR = None
    return main.agent


def _game(task, weights):
    from kaggle_environments import make
    index, seed, seat, candidate_kind, opponent_name = task
    candidate = _candidate(candidate_kind, weights)
    opponent = _opponent(opponent_name)
    agents = [candidate, opponent] if seat == 0 else [opponent, candidate]
    env = make("kaggriculture", configuration={"seed": int(seed)}, debug=False)
    env.reset(2)
    for step in range(719):
        env.state[0].observation.step = step
        env.state[1].observation.step = step
        env.step([agents[0](env.state[0].observation), agents[1](env.state[1].observation)])
    statuses = [str(state.status) for state in env.state]
    if statuses != ["DONE", "DONE"]:
        raise RuntimeError((index, seed, statuses))
    rewards = np.asarray([float(state.reward or 0.0) for state in env.state], dtype=np.float64)
    own, other = rewards[seat], rewards[1 - seat]
    score = 1.0 if own > other else 0.0 if own < other else 0.5
    return {
        "index": index, "seed": seed, "seat": seat,
        "candidate": candidate_kind, "opponent": opponent_name,
        "own": own, "other": other, "margin": own - other, "score": score,
    }


def _run_tasks(tasks, weights, workers):
    rows, started = [], time.time()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_game, task, str(weights)) for task in tasks]
        for done, future in enumerate(as_completed(futures), 1):
            rows.append(future.result())
            if done % max(1, len(tasks) // 10) == 0 or done == len(tasks):
                print(json.dumps({"phase": "evaluation", "completed": done, "games": len(tasks), "games_per_second": done / (time.time() - started)}), flush=True)
    return sorted(rows, key=lambda row: row["index"])


def _bootstrap(seed_scores, samples=10000, seed=991):
    values = np.asarray(seed_scores, dtype=np.float64)
    rng = np.random.default_rng(seed)
    estimates = np.empty(samples, dtype=np.float64)
    for start in range(0, samples, 500):
        count = min(500, samples - start)
        indices = rng.integers(0, len(values), size=(count, len(values)))
        estimates[start:start + count] = values[indices].mean(axis=1)
    return [float(np.quantile(estimates, 0.025)), float(np.quantile(estimates, 0.975))]


def evaluate(weights, paired_seeds=1000, pool_seeds=100, workers=12, output=None):
    weights = Path(weights)
    tasks = []
    index = 0
    paired_seed_values = _partition_seeds(61000000, paired_seeds)
    for seed in paired_seed_values:
        for seat in (0, 1):
            tasks.append((index, seed, seat, "v3", "v1")); index += 1
    paired = _run_tasks(tasks, weights, workers)
    per_seed = np.asarray([np.mean([row["score"] for row in paired if row["seed"] == seed]) for seed in sorted({row["seed"] for row in paired})])

    pool_names = ("v0", "v1", "starter", "random", "forced_low", "forced_high")
    tasks = []
    for opponent_index, opponent in enumerate(pool_names):
        pool_seed_values = _partition_seeds(71000000 + opponent_index * 1000003, pool_seeds)
        for seed_offset, seed in enumerate(pool_seed_values):
            seat = seed_offset % 2
            for kind in ("v1", "v3"):
                tasks.append((index, seed, seat, kind, opponent)); index += 1
    pool = _run_tasks(tasks, weights, workers)
    opponent_summary = {}
    for opponent in pool_names:
        opponent_summary[opponent] = {}
        for kind in ("v1", "v3"):
            subset = [row for row in pool if row["opponent"] == opponent and row["candidate"] == kind]
            opponent_summary[opponent][kind] = {
                "games": len(subset),
                "score_rate": float(np.mean([row["score"] for row in subset])),
                "mean_margin": float(np.mean([row["margin"] for row in subset])),
            }
        opponent_summary[opponent]["score_delta"] = (
            opponent_summary[opponent]["v3"]["score_rate"] - opponent_summary[opponent]["v1"]["score_rate"]
        )

    policy = main.NumpyPolicy(weights)
    feature = np.zeros(main.FEATURE_DIM, dtype=np.float32)
    hidden = np.zeros(main.HIDDEN_SIZE, dtype=np.float32)
    started = time.perf_counter()
    for _ in range(2000):
        policy.step(feature, hidden)
    inference_ms = (time.perf_counter() - started) * 1000.0 / 2000
    result = {
        "schema": "kaggriculture-ppo-v2-evaluation-1",
        "weights": str(weights),
        "paired": {
            "seeds": paired_seeds, "games": len(paired),
            "score_rate": float(np.mean(per_seed)),
            "bootstrap_95_ci": _bootstrap(per_seed),
            "mean_margin": float(np.mean([row["margin"] for row in paired])),
        },
        "pool": opponent_summary,
        "pool_score_delta": float(np.mean([value["score_delta"] for value in opponent_summary.values()])),
        "inference_ms": inference_ms,
    }
    result["gates"] = {
        "direct_score_rate_ge_53pct": result["paired"]["score_rate"] >= 0.53,
        "bootstrap_lower_gt_50pct": result["paired"]["bootstrap_95_ci"][0] > 0.50,
        "pool_composite_better_than_v1": result["pool_score_delta"] > 0.0,
        "no_opponent_decline_gt_2pp": all(
            value["score_delta"] >= -0.02 for value in opponent_summary.values()
        ),
        "inference_lt_5ms": inference_ms < 5.0,
    }
    if output:
        Path(output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", type=Path, default=HERE / "policy_weights.npz")
    parser.add_argument("--paired-seeds", type=int, default=1000)
    parser.add_argument("--pool-seeds", type=int, default=100)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    print(json.dumps(evaluate(args.weights, args.paired_seeds, args.pool_seeds, args.workers, args.output), ensure_ascii=False, indent=2))
