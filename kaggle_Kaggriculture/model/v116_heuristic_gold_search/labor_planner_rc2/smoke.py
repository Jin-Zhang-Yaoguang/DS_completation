#!/usr/bin/env python3
"""Small dual-seat idle smoke for V116 RC2 (maximum four workers)."""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
MODEL = HERE.parents[1]
CPPSIM = (MODEL / "community_research" / "2026-08-26" / "live_cli" /
          "external_repos" / "kaggriculture-cppsim")
sys.path.insert(0, str(HERE))
import main as policy  # noqa: E402


def _load_cppsim() -> Any:
    builds = sorted((CPPSIM / "build").glob("lib.*"))
    if not builds:
        raise RuntimeError(f"missing cppsim build: {CPPSIM / 'build'}")
    sys.path.insert(0, str(builds[-1]))
    import kagsim  # type: ignore
    return kagsim


KAGSIM = _load_cppsim()


def realization(executor: policy.DailyGoalExecutor, obs: dict[str, Any], seat: int) -> float:
    farm = obs["farms"][seat]
    goal = executor.goals[min(29, int(obs.get("day", 0) or 0))]
    crops, animals, _structures = executor._counts(farm["tiles"])
    numerator = min(len(farm.get("unlocked_quadrants", []) or []), int(goal["lands"]))
    denominator = int(goal["lands"])
    for kind, target in goal["crops"].items():
        numerator += min(int(crops.get(kind, 0)), int(target))
        denominator += int(target)
    for kind, target in goal["animals"].items():
        numerator += min(int(animals.get(kind, 0)), int(target))
        denominator += int(target)
    return numerator / max(1, denominator)


def play(task: tuple[int, int]) -> dict[str, Any]:
    seed, seat = task
    game = KAGSIM.Game(int(seed))
    executor = policy.DailyGoalExecutor()
    daily: list[float] = []
    latency: list[int] = []
    schema_errors = 0
    minimum_cash = float("inf")
    while not game.done:
        obs = game.observe(seat)
        farm = obs["farms"][seat]
        minimum_cash = min(minimum_cash, float(farm.get("money", 0) or 0))
        if int(obs.get("hour", 0) or 0) == 23:
            daily.append(realization(executor, obs, seat))
        start = time.perf_counter_ns()
        action = executor.act(obs)
        latency.append(time.perf_counter_ns() - start)
        if (set(action) != {"farmer", "hands", "market"}
                or len(action["hands"]) != len(farm.get("hands", []) or [])
                or len(action["market"]) > 10):
            schema_errors += 1
        pair = [{}, {}]
        pair[seat] = action
        game.step(pair[0], pair[1])
    final = game.observe(seat)
    crops, animals, _structures = executor._counts(final["farms"][seat]["tiles"])
    return {
        "seed": seed,
        "seat": seat,
        "calls": int(executor.audit["calls"]),
        "bank": float(game.reward(seat)),
        "idle_bank": float(game.reward(1 - seat)),
        "pure_win": bool(game.reward(seat) > game.reward(1 - seat)),
        "minimum_cash": minimum_cash,
        "mean_daily_target_realization": statistics.mean(daily),
        "minimum_daily_target_realization": min(daily),
        "final_observed_day_target_realization": daily[-1],
        "mean_latency_us": statistics.mean(latency) / 1000,
        "max_latency_us": max(latency) / 1000,
        "schema_errors": schema_errors,
        "final_crops": dict(crops),
        "final_animals": dict(animals),
        "action_audit": dict(executor.audit),
    }


def static_originality_audit() -> dict[str, Any]:
    source_path = HERE / "main.py"
    source = source_path.read_text()
    tree = ast.parse(source)
    largest_literal = 0
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.List, ast.Tuple)):
            largest_literal = max(largest_literal, len(node.elts))
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    forbidden_imports = [name for name in imports if any(
        marker in name.lower() for marker in ("replay", "v19", "v20", "v21", "v76", "executor", "compiler"))]
    initial = KAGSIM.Game(99117).observe(0)
    poor = copy.deepcopy(initial)
    poor["farms"][0]["money"] = 250
    action_rich = policy.DailyGoalExecutor().act(initial)
    action_poor = policy.DailyGoalExecutor().act(poor)
    return {
        "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "largest_list_or_tuple_literal": largest_literal,
        "forbidden_imports": forbidden_imports,
        "daily_goal_records": len(policy.compile_daily_goals(policy.DEFAULT_GENOME)),
        "money_perturbation_changes_action": action_rich != action_poor,
        "contains_actions_constant": "_ACTIONS" in source,
        "pass": (largest_literal <= 30 and not forbidden_imports
                 and len(policy.compile_daily_goals(policy.DEFAULT_GENOME)) == 30
                 and action_rich != action_poor and "_ACTIONS" not in source),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-start", type=int, default=7100)
    parser.add_argument("--seeds", type=int, default=4)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--output", type=Path, default=HERE / "smoke_results.json")
    args = parser.parse_args()
    if not 1 <= args.workers <= 4:
        raise SystemExit("workers must be in [1,4]")
    tasks = [(seed, seat) for seed in range(args.seed_start, args.seed_start + args.seeds)
             for seat in (0, 1)]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(play, tasks))
    summary = {
        "games": len(rows),
        "pure_wins": sum(row["pure_win"] for row in rows),
        "pure_win_rate_vs_idle": statistics.mean(row["pure_win"] for row in rows),
        "mean_bank": statistics.mean(row["bank"] for row in rows),
        "median_bank": statistics.median(row["bank"] for row in rows),
        "minimum_bank": min(row["bank"] for row in rows),
        "maximum_bank": max(row["bank"] for row in rows),
        "mean_daily_target_realization": statistics.mean(
            row["mean_daily_target_realization"] for row in rows),
        "minimum_daily_target_realization": min(
            row["minimum_daily_target_realization"] for row in rows),
        "minimum_final_observed_day_target_realization": min(
            row["final_observed_day_target_realization"] for row in rows),
        "schema_errors": sum(row["schema_errors"] for row in rows),
        "all_719_calls": all(row["calls"] == 719 for row in rows),
        "mean_latency_us": statistics.mean(row["mean_latency_us"] for row in rows),
    }
    originality = static_originality_audit()
    gate = (summary["mean_bank"] >= 70_000
            and summary["mean_daily_target_realization"] >= 0.75
            and summary["schema_errors"] == 0 and summary["all_719_calls"]
            and originality["pass"])
    payload = {
        "schema": "v116-labor-planner-rc2-idle-smoke-v1",
        "engine": getattr(KAGSIM, "ENGINE_VERSION", "1.32.7"),
        "contract": {"seeds": [args.seed_start, args.seed_start + args.seeds - 1],
                     "both_seats": True, "workers": args.workers,
                     "idle_strength_gate_mean_bank": 70_000,
                     "target_realization_gate": 0.75},
        "genome": policy.DEFAULT_GENOME,
        "originality_audit": originality,
        "summary": summary,
        "episodes": rows,
        "decision": ("PASS_IDLE_SCREEN_REQUIRES_GOLD_ARENA" if gate else
                     "FAILED_IDLE_STRENGTH_GATE_DO_NOT_REGISTER_GOLDEN_MODEL"),
    }
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"summary": summary, "originality": originality,
                      "decision": payload["decision"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

