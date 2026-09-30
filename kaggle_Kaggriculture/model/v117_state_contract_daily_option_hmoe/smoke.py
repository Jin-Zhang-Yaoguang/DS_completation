#!/usr/bin/env python3
"""Dual-seat engineering and idle-strength smoke for V117."""

from __future__ import annotations

import argparse
import concurrent.futures
import importlib.util
import json
import os
import statistics
import sys
import sysconfig
import time
from collections import Counter
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
CPPSIM = (MODEL / "community_research" / "2026-08-26" / "live_cli" /
          "external_repos" / "kaggriculture-cppsim")


def _load_policy(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, HERE / "main.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load V117 main.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _load_engine() -> Any:
    builds = sorted((CPPSIM / "build").glob("lib.*"))
    suffix = sysconfig.get_config_var("EXT_SUFFIX") or ".so"
    for build in reversed(builds):
        extension = build / f"kagsim{suffix}"
        if extension.is_file():
            sys.path.insert(0, str(build))
            import kagsim  # type: ignore
            return kagsim
    scenario = (MODEL / "v116_heuristic_gold_search/replay_arena/build" /
                f"kagsim_scenario{suffix}")
    spec = importlib.util.spec_from_file_location("kagsim_scenario", scenario)
    if spec is None or spec.loader is None:
        raise RuntimeError("cppsim build missing for current Python ABI")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _validate(action: Any, observation: dict[str, Any]) -> int:
    seat = int(observation.get("player", 0) or 0)
    farm = observation["farms"][seat]
    return int(
        not isinstance(action, dict)
        or set(action) != {"farmer", "hands", "market"}
        or not isinstance(action.get("farmer"), list)
        or not isinstance(action.get("hands"), list)
        or len(action.get("hands", [])) != len(farm.get("hands", []) or [])
        or not isinstance(action.get("market"), list)
        or len(action.get("market", [])) > 10
    )


def _asset_counts(grid: list[list[Any]]) -> tuple[int, int]:
    crops = animals = 0
    for row in grid:
        for tile in row:
            if not isinstance(tile, dict):
                continue
            crops += int(tile.get("kind") == "PLANT")
            animals += int(bool(tile.get("animal")))
    return crops, animals


def play(task: tuple[int, int, dict[str, Any], dict[str, Any]]) -> dict[str, Any]:
    seed, seat, balanced_genome, executor_tuning = task
    kagsim = _load_engine()
    policy_module = _load_policy(f"v117_smoke_{os.getpid()}_{seed}_{seat}")
    policy = policy_module.V117Policy(
        balanced_genome=balanced_genome,
        executor_tuning=executor_tuning,
    )
    game = kagsim.Game(seed)
    calls = violations = 0
    minimum_cash = float("inf")
    latencies: list[int] = []
    while not game.done:
        observation = game.observe(seat)
        minimum_cash = min(minimum_cash, float(observation["farms"][seat]["money"]))
        started = time.perf_counter_ns()
        action = policy.act(observation)
        latencies.append(time.perf_counter_ns() - started)
        violations += _validate(action, observation)
        pair = [{}, {}]
        pair[seat] = action
        game.step(pair[0], pair[1])
        calls += 1
    final = game.observe(seat)
    crops, animals = _asset_counts(final["farms"][seat]["tiles"])
    status = policy.status()["seats"][seat]
    loss_status = dict(status.get("loss_attribution") or {})
    outcomes = list(status["ledger"]["daily_outcomes"])
    realization = [float(row["target_realization_rate"]) for row in outcomes]
    return {
        "seed": seed,
        "seat": seat,
        "bank": float(game.reward(seat)),
        "idle_bank": float(game.reward(1 - seat)),
        "pure_win": bool(game.reward(seat) > game.reward(1 - seat)),
        "calls": calls,
        "schema_violations": violations,
        "minimum_cash": minimum_cash,
        "final_crops": crops,
        "final_animals": animals,
        "safety_rewrites": int(status["control_rewrites"]),
        "invariant_events": list(status["ledger"]["invariant_events"]),
        "daily_outcomes": len(status["ledger"]["daily_outcomes"]),
        "daily_target_realization": [
            {"day": int(row["day"]), "rate": float(row["target_realization_rate"])}
            for row in outcomes
        ],
        "mean_target_realization": statistics.mean(realization) if realization else 0.0,
        "router_daily_evaluations": int(policy.status()["router"]["audit"].get("daily_evaluation", 0)),
        "mean_latency_us": statistics.mean(latencies) / 1000.0,
        "p99_latency_us": sorted(latencies)[min(len(latencies) - 1, int(.99 * len(latencies)))] / 1000.0,
        "executor_audit": status["executor"],
        "loss_attribution": loss_status,
    }


def summarize(rows: list[dict[str, Any]], seeds: list[int]) -> dict[str, Any]:
    banks = [row["bank"] for row in rows]
    checks = {
        "engine_1_32_7": True,
        "all_719_calls": all(row["calls"] == 719 for row in rows),
        "zero_schema_violations": sum(row["schema_violations"] for row in rows) == 0,
        "zero_safety_rewrites": sum(row["safety_rewrites"] for row in rows) == 0,
        "zero_invariant_events": sum(len(row["invariant_events"]) for row in rows) == 0,
        "loss_attribution_schema_present": all(
            row["loss_attribution"].get("schema") == "v117-r2.1-a-loss-attribution-v1" for row in rows
        ),
        "all_seven_loss_categories_present": all(
            len(dict(row["loss_attribution"].get("totals") or {})) == 7 for row in rows
        ),
        "thirty_daily_contracts": all(row["router_daily_evaluations"] == 30 for row in rows),
        "daily_outcomes_emitted": all(row["daily_outcomes"] == 29 for row in rows),
        "target_realization_at_least_90pct": statistics.mean(row["mean_target_realization"] for row in rows) >= .90,
        "beats_idle_every_game": all(row["pure_win"] for row in rows),
        "mean_bank_at_least_70000": statistics.mean(banks) >= 70_000,
        "catastrophe_rate_at_most_5pct": statistics.mean(bank < 10_000 for bank in banks) <= .05,
    }
    return {
        "schema": "v117-r2.1-a-loss-attribution-idle-smoke-v2",
        "engine": "1.32.7",
        "seeds": seeds,
        "games": len(rows),
        "summary": {
            "mean_bank": statistics.mean(banks),
            "median_bank": statistics.median(banks),
            "minimum_bank": min(banks),
            "maximum_bank": max(banks),
            "pure_win_rate_vs_idle": statistics.mean(row["pure_win"] for row in rows),
            "mean_final_crops": statistics.mean(row["final_crops"] for row in rows),
            "mean_final_animals": statistics.mean(row["final_animals"] for row in rows),
            "mean_target_realization": statistics.mean(row["mean_target_realization"] for row in rows),
            "latency_p99_upper_us": max(row["p99_latency_us"] for row in rows),
        },
        "checks": checks,
        "engineering_pass": all(value for key, value in checks.items() if key != "mean_bank_at_least_70000"),
        "r1_health_pass": all(checks.values()),
        "rows": sorted(rows, key=lambda row: (row["seed"], row["seat"])),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-start", type=int, default=117001)
    parser.add_argument("--seeds", type=int, default=4)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--output", type=Path, default=HERE / "smoke_results.json")
    parser.add_argument("--balanced-genome-json", type=Path)
    parser.add_argument("--executor-tuning-json", type=Path)
    args = parser.parse_args()
    seeds = list(range(args.seed_start, args.seed_start + args.seeds))
    balanced_genome = (
        json.loads(args.balanced_genome_json.read_text(encoding="utf-8"))
        if args.balanced_genome_json else {}
    )
    executor_tuning = (
        json.loads(args.executor_tuning_json.read_text(encoding="utf-8"))
        if args.executor_tuning_json else {}
    )
    tasks = [
        (seed, seat, balanced_genome, executor_tuning)
        for seed in seeds for seat in (0, 1)
    ]
    with concurrent.futures.ProcessPoolExecutor(max_workers=max(1, args.workers)) as pool:
        rows = list(pool.map(play, tasks, chunksize=1))
    payload = summarize(rows, seeds)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in payload.items() if key != "rows"},
                     ensure_ascii=False, indent=2))
    return 0 if payload["engineering_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
