#!/usr/bin/env python3
"""Verify research/package action parity and basic action contracts."""

from __future__ import annotations

import importlib.util
import json
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
from shop_demand_policy import make_agent


def load(path: Path, prefix: str):
    spec = importlib.util.spec_from_file_location(f"{prefix}_{uuid.uuid4().hex}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


AUDIT = load(PARENT_AUDIT, "v18_parent_audit")
OPPONENT = MODEL / "v8_kawa_lead2_slot" / "main.py"
SEEDS = (52001, 52007, 52013, 52019)


def package_agent():
    return load(HERE / "main.py", "v18_package").agent


def run(policy, seed: int, seat: int, audit: bool):
    registry = Registry(path=Path(__file__).resolve(), models={}, raw={})
    opponent = create_agent(registry, {
        "id": f"v18_qa_{seed}_{seat}_{uuid.uuid4().hex}", "kind": "python",
        "path": str(OPPONENT), "entrypoint": "agent",
    })
    game = kagsim.Game(seed)
    agents = [None, None]
    agents[seat], agents[1 - seat] = policy, opponent
    actions = []
    counts = Counter()
    examples = {"unit_invalid": []}
    while not game.done:
        observations = [game.observe(0), game.observe(1)]
        pair = [agents[0](observations[0]), agents[1](observations[1])]
        candidate_action = pair[seat]
        actions.append(candidate_action)
        counts["market_overflow"] += len(candidate_action.get("market") or []) > 10
        counts["hand_mismatch"] += len(candidate_action.get("hands") or []) != len(observations[seat]["farms"][seat]["hands"])
        if audit:
            AUDIT.audit_units(observations[seat], candidate_action, counts, examples)
        game.step(*pair)
    return actions, [float(game.reward(0)), float(game.reward(1))], counts, examples


def main() -> int:
    rows = []
    total = Counter()
    examples = []
    for seed in SEEDS:
        for seat in (0, 1):
            research_actions, research_rewards, _, _ = run(make_agent("router"), seed, seat, False)
            package_actions, package_rewards, counts, found = run(package_agent(), seed, seat, True)
            total.update(counts)
            examples.extend(found["unit_invalid"])
            rows.append({
                "seed": seed, "candidate_seat": seat,
                "actions_exact": research_actions == package_actions,
                "rewards_exact": research_rewards == package_rewards,
                "research_rewards": research_rewards,
                "package_rewards": package_rewards,
            })
    result = {
        "status": "PASS" if (
            all(row["actions_exact"] and row["rewards_exact"] for row in rows)
            and total["unit_precondition_invalid"] == 0
            and total["market_overflow"] == 0
            and total["hand_mismatch"] == 0
        ) else "FAIL",
        "engine": str(kagsim.ENGINE_VERSION),
        "games": len(rows),
        "exact_action_games": sum(row["actions_exact"] for row in rows),
        "exact_reward_games": sum(row["rewards_exact"] for row in rows),
        "counts": dict(total),
        "invalid_examples": examples[:20],
        "rows": rows,
    }
    (HERE / "package_qa_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
