#!/usr/bin/env python3
"""Small synthetic anchor screen; diagnostic only, never formal gold evidence."""

from __future__ import annotations

import argparse
import concurrent.futures
import importlib.util
import json
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
CPPSIM = (MODEL / "community_research" / "2026-08-26" / "live_cli" /
          "external_repos" / "kaggriculture-cppsim")
OPPONENTS = {
    "v20": MODEL / "v20_demand_timing_moe" / "main.py",
    "v21": MODEL / "v21_top_meta_moe" / "main.py",
    "v32": MODEL / "v32_clone_horizon_preempt" / "main.py",
    "v54": MODEL / "v54_terminal_water_bypass" / "main.py",
    "v66": MODEL / "v66_margin_gated_sell_bubble" / "main.py",
    "v76": MODEL / "v76_adjacent_safe_buy_lead" / "main.py",
}


def _load(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _engine() -> Any:
    builds = sorted((CPPSIM / "build").glob("lib.*"))
    sys.path.insert(0, str(builds[-1]))
    import kagsim  # type: ignore
    return kagsim


def _invalid(action: Any, observation: dict[str, Any]) -> int:
    seat = int(observation.get("player", 0) or 0)
    hands = observation["farms"][seat].get("hands", []) or []
    return int(
        not isinstance(action, dict)
        or set(action) != {"farmer", "hands", "market"}
        or not isinstance(action.get("hands"), list)
        or len(action.get("hands", [])) != len(hands)
        or not isinstance(action.get("market"), list)
        or len(action.get("market", [])) > 10
    )


def play(task: tuple[str, int, int]) -> dict[str, Any]:
    opponent_name, seed, seat = task
    kagsim = _engine()
    own_module = _load(HERE / "main.py", f"v117_anchor_{os.getpid()}_{opponent_name}_{seed}_{seat}")
    opponent = _load(OPPONENTS[opponent_name],
                     f"anchor_{os.getpid()}_{opponent_name}_{seed}_{seat}")
    own = own_module.V117Policy()
    game = kagsim.Game(seed)
    calls = violations = 0
    latencies: list[int] = []
    while not game.done:
        observations = [game.observe(0), game.observe(1)]
        actions: list[Any] = [None, None]
        started = time.perf_counter_ns()
        actions[seat] = own.act(observations[seat])
        latencies.append(time.perf_counter_ns() - started)
        actions[1 - seat] = opponent.agent(observations[1 - seat])
        violations += _invalid(actions[seat], observations[seat])
        game.step(actions[0], actions[1])
        calls += 1
    own_reward = float(game.reward(seat))
    rival_reward = float(game.reward(1 - seat))
    return {
        "opponent": opponent_name,
        "seed": seed,
        "seat": seat,
        "own_reward": own_reward,
        "opponent_reward": rival_reward,
        "margin": own_reward - rival_reward,
        "win": int(own_reward > rival_reward),
        "tie": int(own_reward == rival_reward),
        "calls": calls,
        "schema_violations": violations,
        "p99_latency_us": sorted(latencies)[min(len(latencies) - 1, int(.99 * len(latencies)))] / 1000.0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-start", type=int, default=117201)
    parser.add_argument("--seeds", type=int, default=2)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--output", type=Path, default=HERE / "synthetic_anchor_r1_results.json")
    args = parser.parse_args()
    seeds = list(range(args.seed_start, args.seed_start + args.seeds))
    tasks = [(opponent, seed, seat) for opponent in OPPONENTS for seed in seeds for seat in (0, 1)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=max(1, args.workers)) as pool:
        rows = list(pool.map(play, tasks, chunksize=1))
    by_opponent: dict[str, Any] = {}
    for opponent in OPPONENTS:
        subset = [row for row in rows if row["opponent"] == opponent]
        by_opponent[opponent] = {
            "games": len(subset),
            "pure_win_rate": statistics.mean(row["win"] for row in subset),
            "mean_own_reward": statistics.mean(row["own_reward"] for row in subset),
            "mean_margin": statistics.mean(row["margin"] for row in subset),
        }
    payload = {
        "schema": "v117-r1-full-architecture-synthetic-anchor-screen-v1",
        "evidence_status": "SYNTHETIC_DIAGNOSTIC_ONLY_NOT_REPLAY_NOT_GOLD",
        "engine": "1.32.7",
        "seeds": seeds,
        "opponents": list(OPPONENTS),
        "games": len(rows),
        "pure_win_rate": statistics.mean(row["win"] for row in rows),
        "mean_own_reward": statistics.mean(row["own_reward"] for row in rows),
        "mean_opponent_reward": statistics.mean(row["opponent_reward"] for row in rows),
        "mean_margin": statistics.mean(row["margin"] for row in rows),
        "all_719_calls": all(row["calls"] == 719 for row in rows),
        "schema_violations": sum(row["schema_violations"] for row in rows),
        "latency_p99_upper_us": max(row["p99_latency_us"] for row in rows),
        "by_opponent": by_opponent,
        "rows": sorted(rows, key=lambda row: (row["opponent"], row["seed"], row["seat"])),
    }
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in payload.items() if key != "rows"},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
