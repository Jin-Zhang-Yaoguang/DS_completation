#!/usr/bin/env python3
"""Exercise the 6/8/12-step beam on real legal service states."""

from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
MODEL = ROOT / "kaggle_Kaggriculture" / "model"
CPPSIM = MODEL / "community_research" / "2026-08-26" / "live_cli" / "external_repos" / "kaggriculture-cppsim"
sys.path[:0] = [str(HERE), str(ROOT), str(sorted((CPPSIM / "build").glob("lib.*"))[-1])]
import kagsim  # type: ignore  # noqa: E402
import policy  # noqa: E402
import task_dag  # noqa: E402


def percentile(values: list[float], p: float) -> float:
    values = sorted(values)
    return values[min(len(values) - 1, int((len(values) - 1) * p))]


def main() -> None:
    game = kagsim.Game(50017)
    parent = task_dag.load_frozen_parent().agent
    samples = []
    while not game.done and len(samples) < 40:
        obs = game.observe(0)
        action = parent(obs)
        orders = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
        for actor, order in enumerate(orders):
            if order and order[0] in {"DIG", "PLANT", "WATER", "HARVEST", "FEED", "CARE", "PLACE"} and policy._valid(obs, actor, order):
                pos = policy._positions(obs)[actor]
                samples.append((obs, actor, {
                    "id": f"qa:{len(samples)}", "route": "qa", "step": policy._step(obs),
                    "day": int(obs.get("day", 0) or 0), "hour": int(obs.get("hour", 0) or 0),
                    "actor": actor, "position": list(pos), "order": list(order),
                    "release": policy._step(obs), "deadline": policy._step(obs) + 1, "value": 1000,
                }))
                break
        game.step(action, {})
    result = {"schema": "kaggriculture-v18-beam-qa-v1", "real_states": len(samples), "horizons": {}}
    for horizon in (6, 8, 12):
        planner = policy.RepairPlanner("default", horizon=horizon)
        latencies = []
        legal = positive = 0
        for obs, actor, job in samples:
            t0 = time.perf_counter_ns()
            orders, certificate = planner.plan(obs, [actor], [job])
            latencies.append((time.perf_counter_ns() - t0) / 1000)
            if actor in orders and policy._valid(obs, actor, orders[actor]):
                legal += 1
            positive += int(certificate > 0)
        result["horizons"][str(horizon)] = {
            "calls": len(samples), "legal_first_actions": legal,
            "positive_certificates": positive,
            "mean_us": statistics.mean(latencies), "p99_us": percentile(latencies, .99),
        }
    result["pass"] = all(x["legal_first_actions"] == len(samples) and x["positive_certificates"] == len(samples)
                         for x in result["horizons"].values())
    (HERE / "planner_qa.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if not result["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
