#!/usr/bin/env python3
"""Preconstruction audit for cross-team whole-continuation experts."""

from __future__ import annotations

import concurrent.futures
from collections import Counter
import importlib.util
import json
import os
from pathlib import Path
import statistics
import sys


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
ROOT = MODEL.parents[1]
REPLAYS = ROOT / "kaggle_Kaggriculture/model_data/v17_rc1_online_2026-08-27/top5_leaderboard_replays"
MODEL_DATA = ROOT / "kaggle_Kaggriculture/model_data"
CPPSIM = MODEL / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
sys.path.insert(0, str(sorted((CPPSIM / "build").glob("lib.*"))[-1]))
import kagsim  # type: ignore


ROUTES = {
    "crop_high": {"team": "Crop Dusta", "submission_id": 55714252, "episode_id": 100075627},
    "milan_high": {"team": "Milan Leonard", "submission_id": 55801896, "episode_id": 100439982},
    "ryo_high": {"team": "Ryo Hasegawa", "submission_id": 55614463, "episode_id": 100075619},
    "subramanya_high": {"team": "Subramanya N", "submission_id": 55616096, "episode_id": 95118993},
    "lucaskna_high": {"team": "lucaskna", "submission_id": 55803928, "episode_id": 100485613},
}
OPPONENTS = {
    "v20": MODEL / "v20_demand_timing_moe/main.py",
    "v21": MODEL / "v21_top_meta_moe/main.py",
    "v32": MODEL / "v32_clone_horizon_preempt/main.py",
    "v54": MODEL / "v54_terminal_water_bypass/main.py",
    "v66": MODEL / "v66_margin_gated_sell_bubble/main.py",
    "v76": MODEL / "v76_adjacent_safe_buy_lead/main.py",
}
SEEDS = tuple(range(87201, 87217))
PHASES = {
    "setup_d0_2": (0, 72),
    "route_d3_9": (72, 240),
    "scale_d10_19": (240, 480),
    "monetize_d20_27": (480, 672),
    "liquidate_d28_29": (672, 719),
}


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def load_route(route_id: str) -> tuple[list[dict], dict]:
    meta = dict(ROUTES[route_id])
    path = REPLAYS / f"episode-{meta['episode_id']}-replay.json"
    if not path.exists():
        indexed = sorted(
            MODEL_DATA.glob(f"kaggriculture_episodes_index/date=*/data/{meta['episode_id']}.json")
        )
        if not indexed:
            raise FileNotFoundError(f"no local replay for episode {meta['episode_id']}")
        path = indexed[-1]
    replay = json.loads(path.read_text(encoding="utf-8"))
    seat = replay["info"]["TeamNames"].index(meta["team"])
    actions = [pair[seat].get("action") or {} for pair in replay["steps"][1:720]]
    meta.update(
        source_seat=seat,
        source_seed=int(replay["info"]["seed"]),
        source_reward=float(replay["rewards"][seat]),
        source_opponent_reward=float(replay["rewards"][1 - seat]),
        action_steps=len(actions),
        replay_path=str(path),
    )
    return actions, meta


def score(margin: float) -> float:
    return 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0


def play(task):
    route_id, family, seed, seat = task
    route, _ = load_route(route_id)
    rival = load_module(OPPONENTS[family], f"v87_{route_id}_{family}_{seed}_{seat}_{os.getpid()}")
    game = kagsim.Game(seed)
    calls = 0
    try:
        while not game.done:
            actions = [None, None]
            actions[seat] = route[game.step_count]
            actions[1 - seat] = rival.agent(game.observe(1 - seat))
            game.step(actions[0], actions[1])
            calls += 1
        own = float(game.reward(seat))
        opponent = float(game.reward(1 - seat))
        return {
            "route": route_id,
            "family": family,
            "seed": seed,
            "seat": seat,
            "own": own,
            "opponent": opponent,
            "margin": own - opponent,
            "score": score(own - opponent),
            "calls": calls,
            "error": None,
        }
    except Exception as exc:  # pragma: no cover - evidence capture
        return {
            "route": route_id,
            "family": family,
            "seed": seed,
            "seat": seat,
            "own": None,
            "opponent": None,
            "margin": None,
            "score": 0.0,
            "calls": calls,
            "error": f"{type(exc).__name__}: {exc}",
        }


def canonical(action: dict) -> str:
    return json.dumps(action, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def operation_profile(actions: list[dict]) -> dict[str, int]:
    result: Counter[str] = Counter()
    for action in actions:
        for order in [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]:
            result[f"unit:{order[0] if order else 'PASS'}"] += 1
        for order in action.get("market") or []:
            if not order:
                continue
            key = f"market:{order[0]}"
            if len(order) > 1 and order[0] in {"BUY_SEED", "BUY_ANIMAL", "BUY_PRODUCT", "SELL"}:
                key += f":{order[1]}"
            result[key] += 1
    return dict(sorted(result.items()))


def action_distance(left: list[dict], right: list[dict], start: int, end: int) -> float:
    pairs = zip(left[start:end], right[start:end], strict=True)
    return statistics.mean(canonical(a) != canonical(b) for a, b in pairs)


def summarize(rows: list[dict], route_id: str) -> dict:
    selected = [row for row in rows if row["route"] == route_id]
    good = [row for row in selected if row["error"] is None]
    by_family = {}
    for family in OPPONENTS:
        family_rows = [row for row in good if row["family"] == family]
        by_family[family] = {
            "games": len(family_rows),
            "score_rate": statistics.mean(row["score"] for row in family_rows) if family_rows else 0.0,
            "mean_bank": statistics.mean(row["own"] for row in family_rows) if family_rows else None,
            "mean_margin": statistics.mean(row["margin"] for row in family_rows) if family_rows else None,
        }
    return {
        "games": len(selected),
        "completed_games": len(good),
        "errors": len(selected) - len(good),
        "all_719_calls": bool(good) and all(row["calls"] == 719 for row in good),
        "panel_score_rate": statistics.mean(row["score"] for row in good) if good else 0.0,
        "mean_bank": statistics.mean(row["own"] for row in good) if good else None,
        "mean_margin": statistics.mean(row["margin"] for row in good) if good else None,
        "by_opponent": by_family,
    }


def main() -> None:
    streams = {}
    provenance = {}
    for route_id in ROUTES:
        streams[route_id], provenance[route_id] = load_route(route_id)

    tasks = [
        (route_id, family, seed, seat)
        for route_id in ROUTES
        for family in OPPONENTS
        for seed in SEEDS
        for seat in (0, 1)
    ]
    with concurrent.futures.ProcessPoolExecutor(max_workers=min(16, os.cpu_count() or 1)) as pool:
        rows = list(pool.map(play, tasks, chunksize=1))

    route_stats = {route_id: summarize(rows, route_id) for route_id in ROUTES}
    pairwise = {}
    route_ids = list(ROUTES)
    for i, left in enumerate(route_ids):
        for right in route_ids[i + 1 :]:
            pairwise[f"{left}__vs__{right}"] = {
                "global_action_mismatch_rate": action_distance(streams[left], streams[right], 0, 719),
                "phase_action_mismatch_rate": {
                    phase: action_distance(streams[left], streams[right], start, end)
                    for phase, (start, end) in PHASES.items()
                },
            }

    viable = []
    for route_id, row in route_stats.items():
        distinct_peers = 0
        for peer in route_ids:
            if peer == route_id:
                continue
            key = f"{route_id}__vs__{peer}" if f"{route_id}__vs__{peer}" in pairwise else f"{peer}__vs__{route_id}"
            distinct_peers += pairwise[key]["global_action_mismatch_rate"] >= 0.15
        row["distinct_peer_count"] = distinct_peers
        row["viable_expert"] = bool(
            row["errors"] == 0
            and row["all_719_calls"]
            and row["panel_score_rate"] >= 0.50
            and row["by_opponent"]["v76"]["score_rate"] >= 0.30
            and distinct_peers >= 2
        )
        if row["viable_expert"]:
            viable.append(route_id)

    payload = {
        "schema": "kaggriculture-v87-cross-team-expert-pool-audit-v1",
        "engine": str(kagsim.ENGINE_VERSION),
        "status": "SYNTHETIC_PRECONSTRUCTION_NOT_GOLD_EVIDENCE",
        "official_replay_sources_consumed": 0,
        "frozen_public_replay_training_cutoff": "2026-08-27",
        "synthetic_seed_range": [min(SEEDS), max(SEEDS)],
        "games": len(rows),
        "opponents": list(OPPONENTS),
        "provenance": provenance,
        "operation_profiles": {route_id: operation_profile(actions) for route_id, actions in streams.items()},
        "pairwise_behavior_distance": pairwise,
        "route_strength": route_stats,
        "viable_experts": viable,
        "viable_expert_count": len(viable),
        "gate": {
            "required_viable_experts": 3,
            "panel_score_rate_min": 0.50,
            "direct_v76_score_rate_min": 0.30,
            "global_action_mismatch_rate_min": 0.15,
            "distinct_peer_count_min": 2,
        },
        "decision": "PASS_EXPERT_POOL" if len(viable) >= 3 else "REJECT_PRECONSTRUCTION_WEAK_OR_COLLAPSED_EXPERT_POOL",
        "rows": rows,
    }
    (HERE / "expert_pool_audit.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: value for key, value in payload.items() if key != "rows"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
