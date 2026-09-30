#!/usr/bin/env python3
"""Closed-loop L1 screen for the L0-shortlisted complete production routes."""

from __future__ import annotations

import argparse
import copy
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
MODEL = PROJECT / "model"
PARENT_DIR = MODEL / "v16_gold_strategy_research" / "top_complete_portfolio"
CPPSIM = MODEL / "community_research" / "2026-08-26" / "live_cli" / "external_repos" / "kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
sys.path[:0] = [str(PROJECT.parent), str(PARENT_DIR), str(FACTORY), str(sorted((CPPSIM / "build").glob("lib.*"))[-1])]

import kagsim  # type: ignore
from agent_factory import Registry, create_agent  # type: ignore
import portfolio_policy as parent


OPPONENTS = {
    "adaptive_market": MODEL / "v1_adaptive_market" / "main.py",
    "anti_mirror": MODEL / "v9_anti_mirror" / "main.py",
    "incumbent_r002": MODEL / "v12_incumbent_r002" / "main.py",
    "kawa_lead2": MODEL / "v8_kawa_lead2_slot" / "main.py",
}


def route_actions(metadata: dict) -> list[dict]:
    replay = json.loads(Path(metadata["path"]).read_text(encoding="utf-8"))
    seat = replay["info"]["TeamNames"].index(metadata["team"])
    actions = [copy.deepcopy(pair[seat].get("action") or {}) for pair in replay["steps"][1:720]]
    return parent._PREFIX_ACTIONS[:parent.ROUTER_STEP] + actions[parent.ROUTER_STEP:]


def shortlist(screen: dict) -> list[dict]:
    metadata = {row["full_action_hash"]: row for row in screen["candidates"]}
    chosen = {row["full_action_hash"]: row for row in screen["shop_choices"].values()}
    chosen[screen["best_single"]["route"]["full_action_hash"]] = screen["best_single"]["route"]
    for profile in sorted({row["profile"] for row in metadata.values()}):
        routes = [key for key, row in metadata.items() if row["profile"] == profile]
        best = max(routes, key=lambda key: (
            screen["route_dev"][key]["family_equal_score_rate"],
            screen["route_dev"][key]["worst_family_score_rate"],
            screen["route_dev"][key]["mean_margin"],
        ))
        chosen[best] = metadata[best]
    return sorted(chosen.values(), key=lambda row: (row["profile"], row["team"], row["episode"]))


def make_route_agent(actions: list[dict]):
    base = parent._fresh_base()
    base._V17_FEED_GUARD = False

    def policy(obs, configuration=None):
        del configuration
        base._ACTIONS = actions
        action = base._CORE_AGENT(obs)
        action = parent._cap_fixed_purchases(obs, action, base)
        return parent._fail_closed_units(obs, action)

    return policy


def play(policy, opponent, seed: int, seat: int):
    game = kagsim.Game(seed)
    agents = [None, None]
    agents[seat], agents[1 - seat] = policy, opponent
    first_three = []
    while not game.done:
        observations = [game.observe(0), game.observe(1)]
        if game.step_count in (72, 144, 216):
            first_three = list(observations[seat]["town"]["unlocked_shops"][:3])
        game.step(agents[0](observations[0]), agents[1](observations[1]))
    rewards = [float(game.reward(0)), float(game.reward(1))]
    return rewards[seat], rewards[1 - seat], first_three


def score(margin: float) -> float:
    return 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0


def summarize(rows: list[dict]) -> dict:
    return {
        "games": len(rows),
        "wins_ties_losses": [sum(row["margin"] > 0 for row in rows), sum(row["margin"] == 0 for row in rows), sum(row["margin"] < 0 for row in rows)],
        "score_rate": statistics.mean(score(row["margin"]) for row in rows),
        "mean_bank": statistics.mean(row["own"] for row in rows),
        "mean_margin": statistics.mean(row["margin"] for row in rows),
    }


def family_equal(rows: list[dict]) -> dict:
    families = sorted({row["opponent_family"] for row in rows})
    by_family = {family: summarize([row for row in rows if row["opponent_family"] == family]) for family in families}
    return {
        **summarize(rows),
        "family_equal_score_rate": statistics.mean(value["score_rate"] for value in by_family.values()),
        "worst_family_score_rate": min(value["score_rate"] for value in by_family.values()),
        "by_family": by_family,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-start", type=int, default=62000)
    parser.add_argument("--dev-seeds", type=int, default=8)
    parser.add_argument("--test-seeds", type=int, default=8)
    parser.add_argument("--output", type=Path, default=HERE / "production_route_l1_screen.json")
    args = parser.parse_args()

    l0 = json.loads((HERE / "production_route_l0_screen.json").read_text(encoding="utf-8"))
    candidates = shortlist(l0)
    actions = {row["full_action_hash"]: route_actions(row) for row in candidates}
    modes = {"parent": None, **{row["full_action_hash"]: row for row in candidates}}
    registry = Registry(path=Path(__file__).resolve(), models={}, raw={})
    rows = []
    progress_path = HERE / "production_route_l1_progress.json"
    total_seeds = args.dev_seeds + args.test_seeds
    for family, path in OPPONENTS.items():
        for offset, seed in enumerate(range(args.seed_start, args.seed_start + total_seeds)):
            split = "dev" if offset < args.dev_seeds else "test"
            for seat in (0, 1):
                for mode, metadata in modes.items():
                    policy = parent.make_agent("router") if mode == "parent" else make_route_agent(actions[mode])
                    opponent = create_agent(registry, {
                        "id": f"v19_l1_{family}_{seed}_{seat}_{mode}", "kind": "python",
                        "path": str(path), "entrypoint": "agent",
                    })
                    own, opp, shops = play(policy, opponent, seed, seat)
                    rows.append({
                        "split": split, "mode": mode,
                        "route_id": "V17_PARENT" if metadata is None else f'{metadata["team"]}::{metadata["episode"]}',
                        "profile": "PARENT" if metadata is None else metadata["profile"],
                        "opponent_family": family, "seed": seed, "seat": seat,
                        "shops": shops, "first_shop": shops[0] if shops else "NO_SHOP",
                        "own": own, "opp": opp, "margin": own - opp,
                    })
        progress_path.write_text(json.dumps({
            "status": "IN_PROGRESS", "completed_family": family,
            "rows": rows,
        }, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"completed {family}: {len(rows)} rows", flush=True)

    dev = [row for row in rows if row["split"] == "dev"]
    test = [row for row in rows if row["split"] == "test"]
    route_dev = {mode: family_equal([row for row in dev if row["mode"] == mode]) for mode in modes}
    choices = {}
    for shop in sorted({row["first_shop"] for row in dev}):
        metrics = {}
        for mode in modes:
            selected = [row for row in dev if row["first_shop"] == shop and row["mode"] == mode]
            if selected:
                metrics[mode] = family_equal(selected)
        choices[shop] = max(metrics, key=lambda mode: (
            metrics[mode]["family_equal_score_rate"], metrics[mode]["worst_family_score_rate"], metrics[mode]["mean_margin"],
        ))
    # A shallow tree must have an explicit safe branch for a category absent
    # from development.  Falling back to V17 is preferable to fitting on test.
    unseen_test_shops = sorted({row["first_shop"] for row in test} - set(choices))
    for shop in unseen_test_shops:
        choices[shop] = "parent"
    routed_test = [row for row in test if row["mode"] == choices[row["first_shop"]]]
    result = {
        "schema": "kaggriculture-v19-production-route-l1-screen-v1",
        "status": "CLOSED_LOOP_DISCOVERY_NOT_CONFIRMATION",
        "engine": str(kagsim.ENGINE_VERSION),
        "candidate_count": len(candidates),
        "candidates": candidates,
        "split": {
            "dev": [args.seed_start, args.seed_start + args.dev_seeds - 1],
            "test": [args.seed_start + args.dev_seeds, args.seed_start + total_seeds - 1],
        },
        "route_dev": route_dev,
        "shop_choices": choices,
        "unseen_test_shop_fallbacks": unseen_test_shops,
        "shop_router_test": family_equal(routed_test),
        "parent_test": family_equal([row for row in test if row["mode"] == "parent"]),
        "rows": rows,
    }
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    labels = {"parent": "V17_PARENT", **{row["full_action_hash"]: f'{row["team"]}::{row["episode"]} ({row["profile"]})' for row in candidates}}
    print(json.dumps({
        "candidate_count": len(candidates),
        "route_dev": {labels[key]: value for key, value in route_dev.items()},
        "shop_choices": {shop: labels[mode] for shop, mode in choices.items()},
        "shop_router_test": result["shop_router_test"],
        "parent_test": result["parent_test"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
