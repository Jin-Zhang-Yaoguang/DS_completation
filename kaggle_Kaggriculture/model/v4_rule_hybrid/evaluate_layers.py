"""V4 各规则层的双席位配对评测。"""

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


HERE = Path(__file__).resolve().parent
MODEL_DIR = HERE.parent
_CACHE = {}


def _seed_bucket(seed):
    digest = hashlib.sha256(str(int(seed)).encode("ascii")).digest()
    return int.from_bytes(digest[:8], "big") % 100


def _partition_seeds(start, count, low=70, high=90):
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


def _modules():
    process = os.getpid()
    if "v4" not in _CACHE:
        _CACHE["v4"] = _load(HERE / "main.py", f"v4_eval_{process}")
        _CACHE["v0"] = _load(MODEL_DIR / "v0_api_smoke" / "main.py", f"v0_eval_{process}")
        _CACHE["v1"] = _load(MODEL_DIR / "v1_adaptive_market" / "main.py", f"v1_eval_{process}")
        _CACHE["v2"] = _load(MODEL_DIR / "v2_survival_guard" / "main.py", f"v2_eval_{process}")
    return _CACHE


def _agent(name):
    modules = _modules()
    if name in ("r1", "r2", "r3", "r4"):
        return modules["v4"].make_agent(name)
    if name in ("starter", "random"):
        from kaggle_environments.envs.kaggriculture import kaggriculture as kg
        return kg.starter_agent if name == "starter" else kg.random_agent
    return modules[name].agent


def _game(task):
    from kaggle_environments import make

    index, seed, seat, candidate_name, opponent_name = task
    candidate = _agent(candidate_name)
    opponent = _agent(opponent_name)
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
    rewards = np.asarray([float(state.reward or 0) for state in env.state])
    own, other = rewards[seat], rewards[1 - seat]
    return {
        "index": index,
        "seed": int(seed),
        "seat": int(seat),
        "candidate": candidate_name,
        "opponent": opponent_name,
        "own": float(own),
        "other": float(other),
        "margin": float(own - other),
        "score": 1.0 if own > other else 0.0 if own < other else 0.5,
    }


def _bootstrap(values, samples=5000, seed=404):
    values = np.asarray(values, dtype=np.float64)
    rng = np.random.default_rng(seed)
    estimates = np.empty(samples, dtype=np.float64)
    for start in range(0, samples, 500):
        count = min(500, samples - start)
        indices = rng.integers(0, len(values), size=(count, len(values)))
        estimates[start : start + count] = values[indices].mean(axis=1)
    return [float(np.quantile(estimates, 0.025)), float(np.quantile(estimates, 0.975))]


def _summarize(rows, seeds):
    scores = np.asarray([row["score"] for row in rows])
    margins = np.asarray([row["margin"] for row in rows])
    paired = np.asarray([
        np.mean([row["score"] for row in rows if row["seed"] == seed])
        for seed in seeds
    ])
    return {
        "games": len(rows),
        "wins": int(np.sum(scores == 1)),
        "ties": int(np.sum(scores == 0.5)),
        "losses": int(np.sum(scores == 0)),
        "score_rate": float(scores.mean()),
        "mean_margin": float(margins.mean()),
        "median_margin": float(np.median(margins)),
        "paired_bootstrap_95_ci": _bootstrap(paired),
        "by_seat": {
            str(seat): {
                "games": int(sum(row["seat"] == seat for row in rows)),
                "score_rate": float(np.mean([row["score"] for row in rows if row["seat"] == seat])),
                "mean_margin": float(np.mean([row["margin"] for row in rows if row["seat"] == seat])),
            }
            for seat in (0, 1)
        },
    }


def evaluate(pairs, seed_count, workers, seed_start=82000000, low=70, high=90):
    seeds = _partition_seeds(seed_start, seed_count, low=low, high=high)
    tasks = []
    index = 0
    for candidate, opponent in pairs:
        for seed in seeds:
            for seat in (0, 1):
                tasks.append((index, seed, seat, candidate, opponent))
                index += 1
    rows = []
    started = time.time()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_game, task) for task in tasks]
        for done, future in enumerate(as_completed(futures), 1):
            rows.append(future.result())
            if done % max(1, len(tasks) // 20) == 0 or done == len(tasks):
                print(json.dumps({
                    "phase": "evaluation",
                    "completed": done,
                    "games": len(tasks),
                    "games_per_second": done / max(time.time() - started, 1e-6),
                }), flush=True)
    rows.sort(key=lambda row: row["index"])
    results = {}
    for candidate, opponent in pairs:
        subset = [row for row in rows if row["candidate"] == candidate and row["opponent"] == opponent]
        results[f"{candidate}_vs_{opponent}"] = _summarize(subset, seeds)
    return {
        "schema": "kaggriculture-v4-layer-evaluation-1",
        "seed_count": seed_count,
        "seed_start": seed_start,
        "seed_bucket": [low, high],
        "both_seats": True,
        "games": len(tasks),
        "pairs": results,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=100)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--seed-start", type=int, default=82000000)
    parser.add_argument("--bucket-low", type=int, default=70)
    parser.add_argument("--bucket-high", type=int, default=90)
    parser.add_argument("--pairs", nargs="*", default=[
        "r1:v1", "r2:r1", "r2:v1", "r3:r2",
        "r3:v1", "r4:r3", "r4:v1", "r4:v2",
    ])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    pairs = [tuple(value.split(":", 1)) for value in args.pairs]
    allowed = {"v0", "v1", "v2", "starter", "random", "r1", "r2", "r3", "r4"}
    if any(a not in allowed or b not in allowed for a, b in pairs):
        raise SystemExit("invalid pair")
    result = evaluate(
        pairs,
        args.seeds,
        args.workers,
        seed_start=args.seed_start,
        low=args.bucket_low,
        high=args.bucket_high,
    )
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered)
    print(rendered, end="")


if __name__ == "__main__":
    main()
