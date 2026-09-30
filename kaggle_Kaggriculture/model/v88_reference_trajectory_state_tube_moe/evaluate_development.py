#!/usr/bin/env python3
"""Run V88's frozen 64-source Development and architecture ablation."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import statistics
import sys


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
PROJECT = MODEL.parent
DATA = PROJECT / "model_data/loop_evaluations/v88_reference_trajectory_state_tube_moe"
SOURCE_MANIFEST = DATA / "development_source_manifest.json"
CPPSIM = MODEL / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
METRICS_DIR = MODEL / "v80_spatial_work_stealing_moe"
sys.path[:0] = [str(METRICS_DIR), str(FACTORY), str(sorted((CPPSIM / "build").glob("lib.*"))[-1])]
import kagsim  # type: ignore
from agent_factory import Registry, create_agent  # type: ignore
import evaluate_development as metrics  # type: ignore


POLICIES = {
    "candidate": HERE / "main.py",
    "parent": MODEL / "v76_adjacent_safe_buy_lead/main.py",
    "ablation": HERE / "ablation_main.py",
}
OPPONENTS = {
    "v20": MODEL / "v20_demand_timing_moe/main.py",
    "v21": MODEL / "v21_top_meta_moe/main.py",
    "v32": MODEL / "v32_clone_horizon_preempt/main.py",
    "v54": MODEL / "v54_terminal_water_bypass/main.py",
    "v66": MODEL / "v66_margin_gated_sell_bubble/main.py",
    "v76": MODEL / "v76_adjacent_safe_buy_lead/main.py",
}
ABLATION_OPPONENTS = ("v54", "v76")
EXPECTED_ARCHIVE_SHA = "34eda74edac494fb351326147294778ce34f2f6bcdffa34f984608add6788fa8"


def sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def score(margin):
    return 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0


def validate_action(action, obs):
    if not isinstance(action, dict):
        return 1
    seat = int(obs.get("player", 0) or 0)
    expected = len(obs["farms"][seat].get("hands", []) or [])
    return int(len(action.get("market", []) or []) > 10 or len(action.get("hands", []) or []) != expected)


def play(task):
    mode, family, source, seat = task
    base = {
        "mode": mode,
        "family": family,
        "source_id": source["episode_id"],
        "seed": source["seed"],
        "date": source["date"],
        "first_shop": source["first_shop"],
        "shops": source["shops"],
        "seat": seat,
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
        shadow = None
        if mode == "candidate":
            shadow = create_agent(registry, {
                "id": f"shadow_{family}_{source['episode_id']}_{seat}_{os.getpid()}",
                "kind": "python", "path": str(POLICIES["ablation"]), "entrypoint": "agent",
            })
        agents = [None, None]
        agents[seat], agents[1 - seat] = own, rival
        game = kagsim.Game(int(source["seed"]))
        violations = calls = action_change_calls = 0
        while not game.done:
            observations = [game.observe(0), game.observe(1)]
            own_action = agents[seat](observations[seat])
            rival_action = agents[1 - seat](observations[1 - seat])
            if shadow is not None:
                action_change_calls += int(own_action != shadow(observations[seat]))
            actions = [None, None]
            actions[seat], actions[1 - seat] = own_action, rival_action
            violations += validate_action(own_action, observations[seat])
            game.step(actions[0], actions[1])
            calls += 1
        rewards = [float(game.reward(0)), float(game.reward(1))]
        return {
            **base,
            "status": "DONE",
            "error": None,
            "calls": calls,
            "own": rewards[seat],
            "opponent": rewards[1 - seat],
            "margin": rewards[seat] - rewards[1 - seat],
            "safety_violations": violations,
            "action_change_calls": action_change_calls,
        }
    except Exception as exc:
        return {**base, "status": "ERROR", "error": f"{type(exc).__name__}: {exc}"}


def ablation_summary(rows, sources):
    good = [row for row in rows if row.get("status") == "DONE"]
    by_key = {(row["mode"], row["family"], row["source_id"], row["seat"]): row for row in good}
    deltas = []
    margin_deltas = []
    source_changed = set()
    regimes = set()
    for source in sources:
        for family in ABLATION_OPPONENTS:
            for seat in (0, 1):
                full = by_key[("candidate", family, source["episode_id"], seat)]
                base = by_key[("ablation", family, source["episode_id"], seat)]
                deltas.append(score(full["margin"]) - score(base["margin"]))
                margin_deltas.append(full["margin"] - base["margin"])
                if int(full.get("action_change_calls", 0)) > 0:
                    source_changed.add(source["episode_id"])
                    regimes.add(source["first_shop"])
    return {
        "opponents": list(ABLATION_OPPONENTS),
        "games_per_policy": len(deltas),
        "mcu_pp": 100 * statistics.mean(deltas),
        "positive_zero_negative": [sum(x > 0 for x in deltas), sum(x == 0 for x in deltas), sum(x < 0 for x in deltas)],
        "mean_margin_delta": statistics.mean(margin_deltas),
        "mechanism_trigger_sources": len(source_changed),
        "mechanism_trigger_shop_regimes": sorted(regimes),
    }


def main():
    if sha256(HERE / "submission.tar.gz") != EXPECTED_ARCHIVE_SHA:
        raise RuntimeError("candidate archive drifted after source freeze")
    payload = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    if payload["candidate_archive_sha256"] != EXPECTED_ARCHIVE_SHA or len(payload["sources"]) != 64:
        raise RuntimeError("source manifest violates frozen protocol")
    sources = payload["sources"]
    tasks = [
        (mode, family, source, seat)
        for mode in ("candidate", "parent")
        for family in OPPONENTS
        for source in sources
        for seat in (0, 1)
    ]
    tasks.extend(
        ("ablation", family, source, seat)
        for family in ABLATION_OPPONENTS
        for source in sources
        for seat in (0, 1)
    )
    with concurrent.futures.ProcessPoolExecutor(max_workers=min(16, os.cpu_count() or 1)) as pool:
        rows = list(pool.map(play, tasks, chunksize=1))
    DATA.mkdir(parents=True, exist_ok=True)
    games_path = DATA / "development_games.jsonl"
    with games_path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    metrics.OPPONENTS = OPPONENTS
    primary_rows = [row for row in rows if row["mode"] in {"candidate", "parent"}]
    summary = metrics.summarize(primary_rows, sources)
    ablation = ablation_summary(rows, sources)
    summary["gate_checks"]["mcu_positive"] = ablation["mcu_pp"] > 0
    summary["gate_checks"]["mechanism_trigger_sources_at_least_8"] = ablation["mechanism_trigger_sources"] >= 8
    summary["gate_checks"]["mechanism_trigger_regimes_at_least_2"] = len(ablation["mechanism_trigger_shop_regimes"]) >= 2
    summary["gate"] = "PASS" if all(summary["gate_checks"].values()) else "FAIL"
    result = {
        "schema": "kaggriculture-loop-development-v2",
        "model_id": "v88_reference_trajectory_state_tube_moe",
        "engine": str(kagsim.ENGINE_VERSION),
        "candidate_archive_sha256": EXPECTED_ARCHIVE_SHA,
        "source_manifest_sha256": sha256(SOURCE_MANIFEST),
        "games_sha256": sha256(games_path),
        "source_count": len(sources),
        "originality_panel": list(OPPONENTS),
        "summary": summary,
        "ablation": ablation,
    }
    (DATA / "development_summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (HERE / "development_summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

