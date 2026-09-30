#!/usr/bin/env python3
"""Qualify independent heuristic/replay-controller sources for V116."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import os
from pathlib import Path
import hashlib
import statistics
import sys


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
PROJECT = MODEL.parent
CPPSIM = MODEL / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
sys.path[:0] = [str(FACTORY), str(sorted((CPPSIM / "build").glob("lib.*"))[-1])]
import kagsim  # type: ignore
from agent_factory import Registry, create_agent  # type: ignore


POLICIES = {
    "v88_full": MODEL / "v88_reference_trajectory_state_tube_moe/main.py",
    "v96_full": MODEL / "v96_seat_priority_robust_route_moe/main.py",
    "v106_full": MODEL / "v106_conformal_support_option_moe/main.py",
    "v106_ablation": MODEL / "v106_conformal_support_option_moe/ablation_main.py",
}
ANCHORS = {
    "v20": MODEL / "v20_demand_timing_moe/main.py",
    "v21": MODEL / "v21_top_meta_moe/main.py",
    "v32": MODEL / "v32_clone_horizon_preempt/main.py",
    "v54": MODEL / "v54_terminal_water_bypass/main.py",
    "v66": MODEL / "v66_margin_gated_sell_bubble/main.py",
    "v76": MODEL / "v76_adjacent_safe_buy_lead/main.py",
}
FULL_GOLD = {
    "v19": MODEL / "v19_hierarchical_moe/main.py",
    **ANCHORS,
    "v33": MODEL / "v33_demand_gap_horizon4/main.py",
    "v34": MODEL / "v34_demand_boundary_preempt/main.py",
    "v37": MODEL / "v37_preterminal_boundary_preempt/main.py",
    "v46": MODEL / "v46_full_terminal_front_run/main.py",
    "v51": MODEL / "v51_post_action_terminal_sell/main.py",
    "v52": MODEL / "v52_terminal_route_acceleration/main.py",
    "v53": MODEL / "v53_terminal_access_flush/main.py",
    "v70": MODEL / "v70_duplicate_wheat_buy_lead/main.py",
    "v71": MODEL / "v71_duplicate_wheat_buy_lead_50/main.py",
    "v72": MODEL / "v72_duplicate_wheat_buy_lead_75/main.py",
    "v73": MODEL / "v73_duplicate_wheat_buy_full_merge/main.py",
}
MANIFEST = PROJECT / "model_data/loop_evaluations/v88_reference_trajectory_state_tube_moe/development_source_manifest.json"


def outcome(margin: float) -> tuple[int, int, int, float]:
    return (1, 0, 0, 1.0) if margin > 0 else (0, 1, 0, 0.5) if margin == 0 else (0, 0, 1, 0.0)


def validate(action, observation) -> int:
    if not isinstance(action, dict):
        return 1
    seat = int(observation.get("player", 0) or 0)
    hands = len(observation["farms"][seat].get("hands", []) or [])
    return int(len(action.get("hands", []) or []) != hands or len(action.get("market", []) or []) > 10)


def play(task):
    mode, family, source, seat, policy_path, opponent_path = task
    base = {
        "mode": mode, "family": family, "source_id": source["episode_id"],
        "seed": int(source["seed"]), "first_shop": source["first_shop"], "seat": seat,
    }
    try:
        registry = Registry(path=HERE / "qualification_registry.json", models={}, raw={})
        own = create_agent(registry, {
            "id": f"own_{mode}_{family}_{source['episode_id']}_{seat}_{os.getpid()}",
            "kind": "python", "path": str(policy_path), "entrypoint": "agent",
        })
        rival = create_agent(registry, {
            "id": f"opp_{mode}_{family}_{source['episode_id']}_{seat}_{os.getpid()}",
            "kind": "python", "path": str(opponent_path), "entrypoint": "agent",
        })
        agents = [None, None]
        agents[seat], agents[1 - seat] = own, rival
        game = kagsim.Game(int(source["seed"]))
        calls = violations = 0
        while not game.done:
            observations = [game.observe(0), game.observe(1)]
            actions = [agents[0](observations[0]), agents[1](observations[1])]
            violations += validate(actions[seat], observations[seat])
            game.step(actions[0], actions[1])
            calls += 1
        rewards = [float(game.reward(0)), float(game.reward(1))]
        margin = rewards[seat] - rewards[1 - seat]
        win, tie, loss, score = outcome(margin)
        return {
            **base, "status": "DONE", "error": None, "calls": calls,
            "own": rewards[seat], "opponent": rewards[1 - seat], "margin": margin,
            "win": win, "tie": tie, "loss": loss, "score": score,
            "safety_violations": violations,
        }
    except Exception as exc:
        return {**base, "status": "ERROR", "error": f"{type(exc).__name__}: {exc}"}


def wilson(wins: int, games: int, z: float = 1.959963984540054) -> list[float]:
    if not games:
        return [0.0, 0.0]
    p = wins / games
    den = 1 + z * z / games
    mid = (p + z * z / (2 * games)) / den
    half = z * math.sqrt(p * (1 - p) / games + z * z / (4 * games * games)) / den
    return [mid - half, mid + half]


def aggregate(rows):
    done = [row for row in rows if row.get("status") == "DONE"]
    planned_games = len(rows)
    games = len(done)
    wins, ties, losses = (sum(int(row[key]) for row in done) for key in ("win", "tie", "loss"))
    errors = planned_games - games
    return {
        "planned_games": planned_games, "completed_games": games,
        "wins": wins, "ties": ties, "losses": losses, "errors_as_losses": errors,
        "pure_win_rate": wins / planned_games if planned_games else 0.0,
        "pure_win_wilson95_naive_game_level": wilson(wins, planned_games),
        "score_rate": sum(row["score"] for row in done) / planned_games if planned_games else 0.0,
        "mean_margin": statistics.mean(row["margin"] for row in done) if done else 0.0,
        "errors": errors,
        "safety_violations": sum(int(row.get("safety_violations", 0)) for row in done),
        "all_719_calls": bool(done) and all(row["calls"] == 719 for row in done),
    }


def stratified_sources(limit):
    sources = json.loads(MANIFEST.read_text(encoding="utf-8"))["sources"]
    groups = {}
    for source in sources:
        groups.setdefault(source["first_shop"], []).append(source)
    shops = sorted(groups)
    per_shop = limit // len(shops)
    if per_shop * len(shops) != limit:
        raise ValueError(f"source count must be divisible by {len(shops)}")
    selected = [source for shop in shops for source in groups[shop][:per_shop]]
    if len(selected) != limit:
        raise RuntimeError(f"requested {limit} sources but selected {len(selected)}")
    if len({int(row["seed"]) for row in selected}) != limit:
        raise RuntimeError("source seeds are not unique")
    if len({str(row["episode_id"]) for row in selected}) != limit:
        raise RuntimeError("source episode ids are not unique")
    return selected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", choices=("anchors", "full"), default="anchors")
    parser.add_argument("--sources", type=int, default=16)
    parser.add_argument("--workers", type=int, default=max(1, int((os.cpu_count() or 1) * 0.60)))
    parser.add_argument("--modes", nargs="+", choices=sorted(POLICIES), default=sorted(POLICIES))
    parser.add_argument("--output", type=Path, default=HERE / "source_qualification_results.json")
    args = parser.parse_args()
    opponents = ANCHORS if args.pool == "anchors" else FULL_GOLD
    sources = stratified_sources(args.sources)
    if str(getattr(kagsim, "ENGINE_VERSION", "")) != "1.32.7":
        raise RuntimeError(f"unexpected kagsim engine: {getattr(kagsim, 'ENGINE_VERSION', None)}")
    # Restart the worker pool at every opponent boundary.  Some imported Kaggle
    # agents keep module-level episode state, so one giant long-lived pool both
    # grows memory and makes cross-opponent contamination harder to audit.
    rows = []
    for family, opponent in opponents.items():
        family_tasks = [
            (mode, family, source, seat, POLICIES[mode], opponent)
            for mode in args.modes for source in sources for seat in (0, 1)
        ]
        with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as executor:
            rows.extend(executor.map(play, family_tasks, chunksize=1))
    summary = {}
    for mode in args.modes:
        mode_rows = [row for row in rows if row["mode"] == mode]
        overall = aggregate(mode_rows)
        by_opponent = {family: aggregate([row for row in mode_rows if row["family"] == family]) for family in opponents}
        overall["macro_opponent_win_rate"] = statistics.mean(x["pure_win_rate"] for x in by_opponent.values())
        overall["by_opponent"] = by_opponent
        overall["gate_75"] = bool(
            overall["pure_win_rate"] >= 0.75 and not overall["errors"]
            and not overall["safety_violations"] and overall["all_719_calls"]
        )
        summary[mode] = overall
    file_hashes = {
        str(path.relative_to(PROJECT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted({*POLICIES.values(), *opponents.values()})
    }
    payload = {
        "schema": "kaggriculture-v116-source-qualification-v2",
        "engine": str(kagsim.ENGINE_VERSION), "pool": args.pool, "opponents": list(opponents),
        "sources": [{k: source[k] for k in ("episode_id", "seed", "first_shop")} for source in sources],
        "modes": args.modes, "tasks": len(rows), "workers": args.workers,
        "artifact_sha256": file_hashes, "primary_metric": "pure_win_rate",
        "confidence_note": "game-level Wilson is descriptive only; formal inference must cluster by seed",
        "gold_gate": 0.75, "summary": summary, "rows": rows,
    }
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "summary": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
