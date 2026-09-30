#!/usr/bin/env python3
"""Held-out multi-opponent action safety audit for the packaged V19 agent."""

from __future__ import annotations

import argparse
import concurrent.futures
import importlib.util
import json
import os
import sys
import uuid
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
MODEL = PROJECT / "model"
CPPSIM = MODEL / "community_research" / "2026-08-26" / "live_cli" / "external_repos" / "kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
PARENT_AUDIT = MODEL / "v16_gold_strategy_research" / "top_complete_portfolio" / "compatibility_audit.py"
sys.path[:0] = [str(PROJECT.parent), str(HERE), str(FACTORY), str(sorted((CPPSIM / "build").glob("lib.*"))[-1])]

import kagsim  # type: ignore
from agent_factory import Registry, create_agent  # type: ignore


OPPONENTS = {
    "adaptive_market": MODEL / "v1_adaptive_market" / "main.py",
    "bc_ppo": MODEL / "v3_bc_ppo_hybrid" / "main.py",
    "anti_mirror": MODEL / "v9_anti_mirror" / "main.py",
    "incumbent_r002": MODEL / "v12_incumbent_r002" / "main.py",
    "ppo_topdays": MODEL / "v5_ppo_v2_league" / "v5_ppo_v2_topdays" / "main.py",
    "rule_hybrid": MODEL / "v5_rule_hybrid" / "main.py",
    "kawa_lead2": MODEL / "v8_kawa_lead2_slot" / "main.py",
}
SEEDS = tuple(range(80000, 80016))


def load(path: Path, prefix: str):
    spec = importlib.util.spec_from_file_location(f"{prefix}_{uuid.uuid4().hex}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


AUDIT = load(PARENT_AUDIT, "v19_safety_audit")


def run_job(payload: tuple[str, int, int, str]) -> dict:
    family, seed, seat, candidate_dir = payload
    policy = load(Path(candidate_dir) / "main.py", "v19_safety_package").agent
    registry = Registry(path=Path(__file__).resolve(), models={}, raw={})
    opponent = create_agent(registry, {
        "id": f"v19_safety_{family}_{seed}_{seat}", "kind": "python",
        "path": str(OPPONENTS[family]), "entrypoint": "agent",
    })
    agents = [None, None]
    agents[seat], agents[1 - seat] = policy, opponent
    game = kagsim.Game(seed)
    counts = Counter()
    examples = {"unit_invalid": []}
    while not game.done:
        observations = [game.observe(0), game.observe(1)]
        pair = [agents[0](observations[0]), agents[1](observations[1])]
        action = pair[seat]
        counts["market_overflow"] += len(action.get("market") or []) > 10
        counts["hand_mismatch"] += len(action.get("hands") or []) != len(observations[seat]["farms"][seat]["hands"])
        AUDIT.audit_units(observations[seat], action, counts, examples)
        game.step(*pair)
    return {
        "family": family, "seed": seed, "seat": seat,
        "counts": dict(counts), "examples": examples["unit_invalid"],
        "reward": float(game.reward(seat)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-dir", type=Path, default=HERE)
    args = parser.parse_args()
    jobs = [(family, seed, seat, str(args.candidate_dir.resolve())) for family in OPPONENTS for seed in SEEDS for seat in (0, 1)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=max(1, os.cpu_count() or 1)) as pool:
        rows = list(pool.map(run_job, jobs, chunksize=1))
    total = Counter()
    examples = []
    by_family = {}
    for row in rows:
        total.update(row["counts"])
        examples.extend(row["examples"])
    for family in OPPONENTS:
        selected = [row for row in rows if row["family"] == family]
        family_counts = Counter()
        for row in selected:
            family_counts.update(row["counts"])
        by_family[family] = {
            "games": len(selected),
            "unit_orders": family_counts["unit_orders"],
            "unit_precondition_invalid": family_counts["unit_precondition_invalid"],
            "market_overflow": family_counts["market_overflow"],
            "hand_mismatch": family_counts["hand_mismatch"],
        }
    passed = (
        len(rows) == len(jobs)
        and total["unit_precondition_invalid"] == 0
        and total["market_overflow"] == 0
        and total["hand_mismatch"] == 0
    )
    result = {
        "status": "PASS" if passed else "FAIL",
        "engine": str(kagsim.ENGINE_VERSION),
        "seed_range": [SEEDS[0], SEEDS[-1]],
        "games": len(rows),
        "opponent_families": list(OPPONENTS),
        "counts": dict(total),
        "by_family": by_family,
        "invalid_examples": examples[:30],
    }
    (args.candidate_dir / "action_safety_audit_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
