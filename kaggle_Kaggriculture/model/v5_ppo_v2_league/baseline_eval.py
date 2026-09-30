"""Small paired baseline matrix for the PPO v2 primary/safety baselines."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import importlib.util
import json
import os
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
MODEL_DIR = HERE.parent
CACHE = {}


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def modules():
    pid = os.getpid()
    if "v1" not in CACHE:
        CACHE["v1"] = load(MODEL_DIR / "v1_adaptive_market" / "main.py", f"baseline_v1_{pid}")
        CACHE["v2"] = load(MODEL_DIR / "v3_bc_ppo_hybrid" / "base_agent.py", f"baseline_v2_{pid}")
        CACHE["v0"] = load(MODEL_DIR / "v0_api_smoke" / "main.py", f"baseline_v0_{pid}")
    return CACHE


def opponent(name):
    from kaggle_environments.envs.kaggriculture import kaggriculture as kg
    m = modules()
    if name == "v1": return m["v1"].agent
    if name == "v2": return m["v2"].agent
    if name == "v0": return m["v0"].agent
    if name == "starter": return kg.starter_agent
    if name == "random": return kg.random_agent
    if name in {"forced_low", "forced_high"}:
        route = int(name == "forced_high")
        def forced(obs):
            m["v2"]._ACTIONS = m["v2"]._HIGH_ROUTE_ACTIONS if route else m["v2"]._LOW_ROUTE_ACTIONS
            return m["v2"]._CORE_AGENT(obs)
        return forced
    raise KeyError(name)


def candidate(name):
    return opponent(name)


def game(task):
    from kaggle_environments import make
    index, seed, seat, candidate_name, opponent_name = task
    agents = [candidate(candidate_name), opponent(opponent_name)]
    if seat == 1:
        agents.reverse()
    env = make("kaggriculture", configuration={"seed": int(seed)}, debug=False)
    env.reset(2)
    for step in range(719):
        env.state[0].observation.step = step
        env.state[1].observation.step = step
        env.step([agents[0](env.state[0].observation), agents[1](env.state[1].observation)])
    rewards = np.asarray([float(s.reward or 0.0) for s in env.state])
    own, other = rewards[seat], rewards[1 - seat]
    return {"index": index, "seed": int(seed), "seat": int(seat), "candidate": candidate_name, "opponent": opponent_name, "own": float(own), "other": float(other), "margin": float(own - other), "score": float(1.0 if own > other else 0.5 if own == other else 0.0)}


def run(seeds, workers, output):
    pool = ("v0", "starter", "random", "forced_low", "forced_high")
    tasks = []
    index = 0
    for seed in seeds:
        for opponent_name in pool:
            for candidate_name in ("v1", "v2"):
                for seat in (0, 1):
                    tasks.append((index, seed, seat, candidate_name, opponent_name)); index += 1
    rows = []
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(game, task) for task in tasks]
        for done, future in enumerate(as_completed(futures), 1):
            rows.append(future.result())
            if done % max(1, len(tasks) // 10) == 0 or done == len(tasks):
                print(json.dumps({"phase": "baseline", "completed": done, "games": len(tasks)}), flush=True)
    rows.sort(key=lambda row: row["index"])
    summary = {}
    for opp in pool:
        summary[opp] = {}
        for cand in ("v1", "v2"):
            subset = [r for r in rows if r["opponent"] == opp and r["candidate"] == cand]
            summary[opp][cand] = {"games": len(subset), "score_rate": float(np.mean([r["score"] for r in subset])), "mean_margin": float(np.mean([r["margin"] for r in subset])), "wins": int(sum(r["score"] == 1.0 for r in subset)), "ties": int(sum(r["score"] == 0.5 for r in subset)), "losses": int(sum(r["score"] == 0.0 for r in subset))}
            if cand == "v2":
                summary[opp]["v2_minus_v1_score"] = summary[opp]["v2"]["score_rate"] - summary[opp]["v1"]["score_rate"]
    result = {"schema": "kaggriculture-ppo-v2-baseline-matrix-1", "seeds": len(seeds), "games": len(rows), "both_seats": True, "opponents": list(pool), "summary": summary, "primary_baseline": "v1", "safety_comparator": "v2"}
    Path(output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-start", type=int, default=92000000)
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--output", type=Path, default=HERE / "baseline_matrix_report.json")
    args = parser.parse_args()
    seeds = [args.seed_start + 1009 * i for i in range(args.seeds)]
    print(json.dumps(run(seeds, args.workers, args.output), ensure_ascii=False, indent=2))
