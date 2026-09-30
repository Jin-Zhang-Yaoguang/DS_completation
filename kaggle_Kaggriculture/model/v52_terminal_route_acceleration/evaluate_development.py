#!/usr/bin/env python3
"""Run the frozen V52 Development matrix and source-cluster audit."""

from __future__ import annotations

import concurrent.futures
from collections import defaultdict
import hashlib
import json
import math
import os
from pathlib import Path
import random
import statistics
import sys
from typing import Any


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
PROJECT = MODEL.parent
DATA = PROJECT / "model_data/loop_evaluations/v52_terminal_route_acceleration"
SOURCE_MANIFEST = DATA / "development_source_manifest.json"
CPPSIM = MODEL / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
sys.path[:0] = [str(FACTORY), str(sorted((CPPSIM / "build").glob("lib.*"))[-1])]

import kagsim  # type: ignore
from agent_factory import Registry, create_agent  # type: ignore


POLICIES = {
    "candidate": HERE / "main.py",
    "parent": MODEL / "v51_post_action_terminal_sell/main.py",
}
OPPONENTS = {
    "v19": MODEL / "v19_hierarchical_moe/main.py",
    "v20": MODEL / "v20_demand_timing_moe/main.py",
    "v21": MODEL / "v21_top_meta_moe/main.py",
    "v32": MODEL / "v32_clone_horizon_preempt/main.py",
    "v33": MODEL / "v33_demand_gap_horizon4/main.py",
    "v34": MODEL / "v34_demand_boundary_preempt/main.py",
    "v37": MODEL / "v37_preterminal_boundary_preempt/main.py",
    "v46": MODEL / "v46_full_terminal_front_run/main.py",
    "v51": MODEL / "v51_post_action_terminal_sell/main.py",
}
EXPECTED_ARCHIVE_SHA = "95fc793da6ffd96aaf3a1b880b0a9672f77f9329f08a3b53dfd3711590b9b0b1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def score(margin: float) -> float:
    return 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0


def validate_action(action: Any, obs: Any) -> int:
    if not isinstance(action, dict):
        return 1
    market = action.get("market", []) or []
    hands = action.get("hands", []) or []
    player = int(obs.get("player", 0) or 0)
    farms = obs.get("farms", []) or []
    expected_hands = len((farms[player] if player < len(farms) else {}).get("hands", []) or [])
    return int(len(market) > 10 or len(hands) != expected_hands)


def play(task: tuple[str, str, dict[str, Any], int]) -> dict[str, Any]:
    mode, family, source, seat = task
    base = {
        "mode": mode, "family": family, "source_id": source["episode_id"],
        "seed": source["seed"], "date": source["date"],
        "first_shop": source["first_shop"], "shops": source["shops"], "seat": seat,
    }
    try:
        registry = Registry(path=HERE / "development_registry.json", models={}, raw={})
        own = create_agent(registry, {
            "id": f"{mode}_{family}_{source['episode_id']}_{seat}_{os.getpid()}",
            "kind": "python", "path": str(POLICIES[mode]), "entrypoint": "agent",
        })
        rival = create_agent(registry, {
            "id": f"opp_{mode}_{family}_{source['episode_id']}_{seat}_{os.getpid()}",
            "kind": "python", "path": str(OPPONENTS[family]), "entrypoint": "agent",
        })
        agents = [None, None]
        agents[seat], agents[1 - seat] = own, rival
        game = kagsim.Game(int(source["seed"]))
        safety_violations = 0
        calls = 0
        while not game.done:
            observations = [game.observe(0), game.observe(1)]
            actions = [agents[0](observations[0]), agents[1](observations[1])]
            safety_violations += validate_action(actions[seat], observations[seat])
            calls += 1
            game.step(actions[0], actions[1])
        rewards = [float(game.reward(0)), float(game.reward(1))]
        diagnostics = own.diagnostics().get("model_status", {})
        stats = diagnostics.get("route_acceleration_stats", {}).get(str(seat), {})
        if not stats:
            stats = diagnostics.get("route_acceleration_stats", {}).get(seat, {})
        return {
            **base, "status": "DONE", "error": None, "calls": calls,
            "own": rewards[seat], "opponent": rewards[1 - seat],
            "margin": rewards[seat] - rewards[1 - seat],
            "safety_violations": safety_violations,
            "route_acceleration_events": int(stats.get("events", 0) or 0),
            "route_acceleration_units": int(stats.get("units", 0) or 0),
        }
    except Exception as exc:
        return {**base, "status": "ERROR", "error": f"{type(exc).__name__}: {exc}"}


def percentile(values: list[float], p: float) -> float:
    values = sorted(values)
    index = (len(values) - 1) * p
    low, high = math.floor(index), math.ceil(index)
    if low == high:
        return values[low]
    return values[low] * (high - index) + values[high] * (index - low)


def bootstrap(source_rows: list[dict[str, Any]]) -> dict[str, list[float]]:
    strata: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in source_rows:
        strata[(row["date"], row["first_shop"])].append(row)
    rng = random.Random(520032)
    pgu_values: list[float] = []
    pool_values: list[float] = []
    for _ in range(20000):
        sample = []
        for values in strata.values():
            sample.extend(rng.choices(values, k=len(values)))
        pgu_values.append(100 * statistics.mean(float(row["candidate_score"]) - float(row["parent_score"]) for row in sample))
        pool_values.append(statistics.mean(float(row["candidate_score"]) for row in sample))
    return {
        "pgu_95ci_pp": [percentile(pgu_values, 0.025), percentile(pgu_values, 0.975)],
        "pool_score_95ci": [percentile(pool_values, 0.025), percentile(pool_values, 0.975)],
    }


def summarize(rows: list[dict[str, Any]], sources: list[dict[str, Any]]) -> dict[str, Any]:
    good = [row for row in rows if row.get("status") == "DONE"]
    by_key = {(row["mode"], row["family"], row["source_id"], row["seat"]): row for row in good}
    source_rows = []
    family_deltas: dict[str, list[float]] = defaultdict(list)
    flips = [0, 0, 0]
    for source in sources:
        candidate_scores = []
        parent_scores = []
        for family in OPPONENTS:
            for seat in (0, 1):
                candidate = by_key[("candidate", family, source["episode_id"], seat)]
                parent = by_key[("parent", family, source["episode_id"], seat)]
                candidate_score = score(float(candidate["margin"]))
                parent_score = score(float(parent["margin"]))
                candidate_scores.append(candidate_score)
                parent_scores.append(parent_score)
                delta = candidate_score - parent_score
                family_deltas[family].append(delta)
                flips[0 if delta > 0 else 1 if delta == 0 else 2] += 1
        source_rows.append({
            "source_id": source["episode_id"], "date": source["date"],
            "first_shop": source["first_shop"],
            "candidate_score": statistics.mean(candidate_scores),
            "parent_score": statistics.mean(parent_scores),
        })
    candidate_rows = [row for row in good if row["mode"] == "candidate"]
    parent_rows = [row for row in good if row["mode"] == "parent"]
    candidate_score = statistics.mean(score(float(row["margin"])) for row in candidate_rows)
    parent_score = statistics.mean(score(float(row["margin"])) for row in parent_rows)
    candidate_cat = statistics.mean(float(row["margin"]) < -10000 for row in candidate_rows)
    parent_cat = statistics.mean(float(row["margin"]) < -10000 for row in parent_rows)
    result = {
        "task_count": len(rows), "done_count": len(good),
        "error_count": len(rows) - len(good),
        "task_keys_unique": len(by_key) == len(good),
        "candidate_pool_score": candidate_score,
        "parent_pool_score": parent_score,
        "pgu_pp": 100 * (candidate_score - parent_score),
        "positive_zero_negative": flips,
        "by_family_pgu_pp": {family: 100 * statistics.mean(values) for family, values in family_deltas.items()},
        "candidate_catastrophic_rate": candidate_cat,
        "parent_catastrophic_rate": parent_cat,
        "catastrophic_rate_delta_pp": 100 * (candidate_cat - parent_cat),
        "candidate_mean_margin": statistics.mean(float(row["margin"]) for row in candidate_rows),
        "parent_mean_margin": statistics.mean(float(row["margin"]) for row in parent_rows),
        "candidate_route_acceleration_events": sum(int(row["route_acceleration_events"]) for row in candidate_rows),
        "candidate_route_acceleration_units": sum(int(row["route_acceleration_units"]) for row in candidate_rows),
        "candidate_action_changed_games": sum(int(row["route_acceleration_events"]) > 0 for row in candidate_rows),
        "safety_violations": sum(int(row.get("safety_violations", 0)) for row in good),
        **bootstrap(source_rows),
    }
    result["gate_checks"] = {
        "pgu_positive": result["pgu_pp"] > 0,
        "pool_score_at_least_50pct": result["candidate_pool_score"] >= 0.50,
        "each_family_delta_at_least_minus_3pp": min(result["by_family_pgu_pp"].values()) >= -3.0,
        "catastrophic_delta_at_most_1pp": result["catastrophic_rate_delta_pp"] <= 1.0,
        "zero_errors_integrity_safety": result["error_count"] == 0 and result["task_keys_unique"] and result["safety_violations"] == 0,
        "effective_action_change": result["candidate_action_changed_games"] > 0,
    }
    result["gate"] = "PASS" if all(result["gate_checks"].values()) else "FAIL"
    return result


def main() -> None:
    if sha256(HERE / "submission.tar.gz") != EXPECTED_ARCHIVE_SHA:
        raise RuntimeError("candidate archive drifted after source freeze")
    source_payload = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    sources = source_payload["sources"]
    tasks = [(mode, family, source, seat) for mode in POLICIES for family in OPPONENTS for source in sources for seat in (0, 1)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=min(16, os.cpu_count() or 1)) as pool:
        rows = list(pool.map(play, tasks, chunksize=1))
    DATA.mkdir(parents=True, exist_ok=True)
    games_path = DATA / "development_games.jsonl"
    with games_path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    result = {
        "schema": "kaggriculture-loop-development-v1",
        "model_id": "v52_terminal_route_acceleration",
        "engine": str(kagsim.ENGINE_VERSION),
        "candidate_archive_sha256": EXPECTED_ARCHIVE_SHA,
        "source_manifest_sha256": sha256(SOURCE_MANIFEST),
        "games_sha256": sha256(games_path),
        "source_count": len(sources),
        "gold_lineages": list(OPPONENTS),
        "summary": summarize(rows, sources),
    }
    (DATA / "development_summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (HERE / "development_summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
