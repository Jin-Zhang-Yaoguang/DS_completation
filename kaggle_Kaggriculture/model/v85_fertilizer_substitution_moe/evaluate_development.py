#!/usr/bin/env python3
"""Run V85's frozen 64-source originality-panel Development matrix."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
PROJECT = MODEL.parent
DATA = PROJECT / "model_data/loop_evaluations/v85_fertilizer_substitution_moe"
SOURCE_MANIFEST = DATA / "development_source_manifest.json"
CPPSIM = MODEL / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
V80 = MODEL / "v80_spatial_work_stealing_moe"
sys.path[:0] = [str(V80), str(FACTORY), str(sorted((CPPSIM / "build").glob("lib.*"))[-1])]
import kagsim  # type: ignore
from agent_factory import Registry, create_agent  # type: ignore
import evaluate_development as metrics  # type: ignore


POLICIES = {"candidate": HERE / "main.py", "parent": MODEL / "v76_adjacent_safe_buy_lead/main.py"}
OPPONENTS = {
    "v20": MODEL / "v20_demand_timing_moe/main.py",
    "v21": MODEL / "v21_top_meta_moe/main.py",
    "v32": MODEL / "v32_clone_horizon_preempt/main.py",
    "v54": MODEL / "v54_terminal_water_bypass/main.py",
    "v66": MODEL / "v66_margin_gated_sell_bubble/main.py",
    "v76": MODEL / "v76_adjacent_safe_buy_lead/main.py",
}
EXPECTED_ARCHIVE_SHA = "c2e822ec1d56f76f2edb857b2877041a38257f876cbe14de7d2c4cbd153fe51f"


def sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_action(action, obs):
    if not isinstance(action, dict):
        return 1
    seat = int(obs.get("player", 0) or 0)
    expected = len(obs["farms"][seat].get("hands", []) or [])
    return int(len(action.get("market", []) or []) > 10 or len(action.get("hands", []) or []) != expected)


def play(task):
    mode, family, source, seat = task
    base = {"mode": mode, "family": family, "source_id": source["episode_id"],
            "seed": source["seed"], "date": source["date"], "first_shop": source["first_shop"],
            "shops": source["shops"], "seat": seat}
    try:
        registry = Registry(path=HERE / "development_registry.json", models={}, raw={})
        own = create_agent(registry, {"id": f"{mode}_{family}_{source['episode_id']}_{seat}_{os.getpid()}",
                                      "kind": "python", "path": str(POLICIES[mode]), "entrypoint": "agent"})
        rival = create_agent(registry, {"id": f"opp_{mode}_{family}_{source['episode_id']}_{seat}_{os.getpid()}",
                                        "kind": "python", "path": str(OPPONENTS[family]), "entrypoint": "agent"})
        agents = [None, None]
        agents[seat], agents[1 - seat] = own, rival
        game = kagsim.Game(int(source["seed"]))
        violations, calls = 0, 0
        while not game.done:
            observations = [game.observe(0), game.observe(1)]
            actions = [agents[0](observations[0]), agents[1](observations[1])]
            violations += validate_action(actions[seat], observations[seat])
            game.step(actions[0], actions[1])
            calls += 1
        rewards = [float(game.reward(0)), float(game.reward(1))]
        return {**base, "status": "DONE", "error": None, "calls": calls,
                "own": rewards[seat], "opponent": rewards[1 - seat],
                "margin": rewards[seat] - rewards[1 - seat], "safety_violations": violations}
    except Exception as exc:
        return {**base, "status": "ERROR", "error": f"{type(exc).__name__}: {exc}"}


def main():
    if sha256(HERE / "submission.tar.gz") != EXPECTED_ARCHIVE_SHA:
        raise RuntimeError("candidate archive drifted after source freeze")
    payload = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    if payload["candidate_archive_sha256"] != EXPECTED_ARCHIVE_SHA or len(payload["sources"]) != 64:
        raise RuntimeError("source manifest violates frozen protocol")
    sources = payload["sources"]
    tasks = [(mode, family, source, seat) for mode in POLICIES for family in OPPONENTS
             for source in sources for seat in (0, 1)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=min(16, os.cpu_count() or 1)) as pool:
        rows = list(pool.map(play, tasks, chunksize=1))
    DATA.mkdir(parents=True, exist_ok=True)
    games_path = DATA / "development_games.jsonl"
    with games_path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    metrics.OPPONENTS = OPPONENTS
    summary = metrics.summarize(rows, sources)
    result = {"schema": "kaggriculture-loop-development-v1",
              "model_id": "v85_fertilizer_substitution_moe", "engine": str(kagsim.ENGINE_VERSION),
              "candidate_archive_sha256": EXPECTED_ARCHIVE_SHA,
              "source_manifest_sha256": sha256(SOURCE_MANIFEST), "games_sha256": sha256(games_path),
              "source_count": len(sources), "originality_panel": list(OPPONENTS),
              "ablation": {"model": "frozen_v76_parent", "mcu_equals_pou": True},
              "summary": summary}
    (DATA / "development_summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (HERE / "development_summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
