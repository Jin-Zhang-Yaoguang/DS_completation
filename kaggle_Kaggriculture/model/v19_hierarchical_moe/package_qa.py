#!/usr/bin/env python3
"""Check research/package action parity and basic action contracts."""

from __future__ import annotations

import argparse
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
from hierarchical_policy import make_agent


def load(path: Path, prefix: str):
    spec = importlib.util.spec_from_file_location(f"{prefix}_{uuid.uuid4().hex}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


AUDIT = load(PARENT_AUDIT, "v19_parent_audit")
OPPONENT = MODEL / "v8_kawa_lead2_slot" / "main.py"
SEEDS = (78001, 78007, 78013, 78019)


def package_agent(candidate_dir: Path):
    return load(candidate_dir / "main.py", "v19_package").agent


def run(policy, seed: int, seat: int, audit: bool):
    registry = Registry(path=Path(__file__).resolve(), models={}, raw={})
    opponent = create_agent(registry, {
        "id": f"v19_qa_{seed}_{seat}_{uuid.uuid4().hex}", "kind": "python",
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
        action = pair[seat]
        actions.append(action)
        counts["market_overflow"] += len(action.get("market") or []) > 10
        counts["hand_mismatch"] += len(action.get("hands") or []) != len(observations[seat]["farms"][seat]["hands"])
        if audit:
            AUDIT.audit_units(observations[seat], action, counts, examples)
        game.step(*pair)
    return actions, [float(game.reward(0)), float(game.reward(1))], counts, examples


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-dir", type=Path, default=HERE)
    parser.add_argument("--seller-mode", default="none")
    parser.add_argument("--research-kind", choices=("v19", "v21", "v24", "v25"), default="v19")
    parser.add_argument("--v21-seller-mode", default="demand_delay_25")
    parser.add_argument("--v24-route", default="crop_yarn")
    parser.add_argument("--seeds", nargs="*", type=int, default=list(SEEDS))
    parser.add_argument("--target-shop", default="SMOOTHIE_SHOP")
    parser.add_argument("--target-team", default="Milan Leonard")
    parser.add_argument("--target-episode", type=int, default=99922362)
    parser.add_argument("--target-switch-step", type=int, default=216)
    args = parser.parse_args()
    v21 = None
    if args.research_kind in {"v21", "v24", "v25"}:
        v21 = load(MODEL / "v21_top_meta_moe" / "top_route_panel.py", "v21_research")
    rows = []
    total = Counter()
    examples = []
    for seed in args.seeds:
        for seat in (0, 1):
            if args.research_kind == "v24":
                research_policy = v21.make_shop_expert_router(args.v24_route, args.v21_seller_mode)
            elif args.research_kind == "v25":
                research_policy = v21.make_compatible_shop_router(
                    args.target_shop, args.target_team, args.target_episode,
                    args.v21_seller_mode, args.target_switch_step,
                )
            elif v21 is not None:
                research_policy = v21.make_lucaskna_hybrid(216, "non_yarn", args.v21_seller_mode)
            else:
                research_policy = make_agent("switch_360", seller_mode=args.seller_mode)
            research_actions, research_rewards, _, _ = run(research_policy, seed, seat, False)
            package_actions, package_rewards, counts, found = run(package_agent(args.candidate_dir), seed, seat, True)
            total.update(counts)
            examples.extend(found["unit_invalid"])
            rows.append({
                "seed": seed, "candidate_seat": seat,
                "actions_exact": research_actions == package_actions,
                "rewards_exact": research_rewards == package_rewards,
                "research_rewards": research_rewards,
                "package_rewards": package_rewards,
            })
    passed = (
        all(row["actions_exact"] and row["rewards_exact"] for row in rows)
        and total["unit_precondition_invalid"] == 0
        and total["market_overflow"] == 0
        and total["hand_mismatch"] == 0
    )
    result = {
        "status": "PASS" if passed else "FAIL",
        "engine": str(kagsim.ENGINE_VERSION),
        "games": len(rows),
        "exact_action_games": sum(row["actions_exact"] for row in rows),
        "exact_reward_games": sum(row["rewards_exact"] for row in rows),
        "counts": dict(total),
        "invalid_examples": examples[:20],
        "rows": rows,
    }
    (args.candidate_dir / "package_qa_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
