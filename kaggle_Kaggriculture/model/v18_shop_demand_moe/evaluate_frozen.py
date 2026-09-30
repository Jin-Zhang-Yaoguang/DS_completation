#!/usr/bin/env python3
"""Paired, frozen-seed, double-seat V18 evaluation against V17."""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
MODEL = PROJECT / "model"
CPPSIM = MODEL / "community_research" / "2026-08-26" / "live_cli" / "external_repos" / "kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
sys.path[:0] = [str(PROJECT.parent), str(HERE), str(FACTORY), str(sorted((CPPSIM / "build").glob("lib.*"))[-1])]

import kagsim  # type: ignore
from agent_factory import Registry, create_agent  # type: ignore
from shop_demand_policy import make_agent


OPPONENTS = {
    "adaptive_market": MODEL / "v1_adaptive_market" / "main.py",
    "bc_ppo": MODEL / "v3_bc_ppo_hybrid" / "main.py",
    "anti_mirror": MODEL / "v9_anti_mirror" / "main.py",
    "incumbent_r002": MODEL / "v12_incumbent_r002" / "main.py",
    "ppo_topdays": MODEL / "v5_ppo_v2_league" / "v5_ppo_v2_topdays" / "main.py",
    "rule_hybrid": MODEL / "v5_rule_hybrid" / "main.py",
    "kawa_lead2": MODEL / "v8_kawa_lead2_slot" / "main.py",
}


def score(margin: float) -> float:
    return 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0


def quantile(values: list[float], p: float) -> float:
    values = sorted(values)
    position = (len(values) - 1) * p
    low, high = math.floor(position), math.ceil(position)
    return values[low] if low == high else values[low] * (high - position) + values[high] * (position - low)


def summarize(rows: list[dict]) -> dict:
    margins = [float(row["margin"]) for row in rows]
    return {
        "games": len(rows),
        "wins_ties_losses": [sum(x > 0 for x in margins), sum(x == 0 for x in margins), sum(x < 0 for x in margins)],
        "score_rate": statistics.mean(score(x) for x in margins),
        "mean_bank": statistics.mean(float(row["own"]) for row in rows),
        "mean_margin": statistics.mean(margins),
    }


def play(policy, opponent, seed: int, seat: int):
    game = kagsim.Game(seed)
    agents = [None, None]
    agents[seat], agents[1 - seat] = policy, opponent
    first_shop = None
    calls = [0, 0]
    while not game.done:
        observations = [game.observe(0), game.observe(1)]
        if game.step_count == 72:
            shops = list(observations[seat]["town"]["unlocked_shops"])
            first_shop = shops[0] if shops else "NO_SHOP"
        actions = []
        for player in (0, 1):
            actions.append(agents[player](observations[player]))
            calls[player] += 1
        game.step(*actions)
    rewards = [float(game.reward(0)), float(game.reward(1))]
    return rewards[seat], rewards[1 - seat], first_shop, calls


def paired_summary(rows: list[dict], families: list[str]) -> dict:
    parent = {
        (row["opponent_family"], row["seed"], row["seat"]): row
        for row in rows if row["mode"] == "parent"
    }
    paired = []
    for row in rows:
        if row["mode"] != "candidate":
            continue
        base = parent[(row["opponent_family"], row["seed"], row["seat"])]
        paired.append({
            "opponent_family": row["opponent_family"], "seed": row["seed"],
            "seat": row["seat"], "first_shop": row["first_shop"],
            "score_delta": score(row["margin"]) - score(base["margin"]),
            "margin_delta": row["margin"] - base["margin"],
            "own_delta": row["own"] - base["own"],
        })

    by_seed = defaultdict(list)
    for row in paired:
        by_seed[int(row["seed"])].append(float(row["score_delta"]))
    seed_values = {seed: statistics.mean(values) for seed, values in by_seed.items()}
    seeds = sorted(seed_values)
    rng = random.Random(1801)
    bootstrap = []
    for _ in range(10000):
        selected = rng.choices(seeds, k=len(seeds))
        bootstrap.append(statistics.mean(seed_values[seed] for seed in selected))

    def group(key: str, value: str) -> dict:
        selected = [row for row in paired if str(row[key]) == value]
        return {
            "paired_cells": len(selected),
            "score_uplift_pp": 100 * statistics.mean(row["score_delta"] for row in selected),
            "margin_delta_mean": statistics.mean(row["margin_delta"] for row in selected),
            "own_delta_mean": statistics.mean(row["own_delta"] for row in selected),
        }

    family = {name: group("opponent_family", name) for name in families}
    shops = sorted({str(row["first_shop"]) for row in paired})
    result = {
        "paired_cells": len(paired),
        "score_uplift_pp": 100 * statistics.mean(row["score_delta"] for row in paired),
        "score_uplift_ci95_pp": [100 * quantile(bootstrap, 0.025), 100 * quantile(bootstrap, 0.975)],
        "margin_delta_mean": statistics.mean(row["margin_delta"] for row in paired),
        "own_delta_mean": statistics.mean(row["own_delta"] for row in paired),
        "positive_zero_negative": [
            sum(row["score_delta"] > 0 for row in paired),
            sum(row["score_delta"] == 0 for row in paired),
            sum(row["score_delta"] < 0 for row in paired),
        ],
        "bootstrap_unit": "seed; each seed averages both seats and all selected opponent families",
        "bootstrap_reps": 10000,
        "by_family": family,
        "by_first_shop": {name: group("first_shop", name) for name in shops},
    }
    result["primary_pass"] = result["score_uplift_ci95_pp"][0] > 0
    result["guardrail_pass"] = all(value["score_uplift_pp"] >= -2.0 for value in family.values())
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("discovery", "confirmation"), required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    frozen = json.loads((HERE / "frozen_seeds.json").read_text(encoding="utf-8"))
    candidate_manifest = json.loads((HERE / "submission_manifest.json").read_text(encoding="utf-8"))
    phase = frozen[args.phase]
    families = list(phase["opponent_families"])
    seeds = [seed for values in phase["seeds_by_first_shop"].values() for seed in values]
    output = Path(args.output) if args.output else HERE / f"{args.phase}_results.json"
    registry = Registry(path=Path(__file__).resolve(), models={}, raw={})

    rows = []
    for family in families:
        for seed in seeds:
            for seat in (0, 1):
                for mode in ("parent", "candidate"):
                    policy = make_agent("parent" if mode == "parent" else "router")
                    opponent = create_agent(registry, {
                        "id": f"v18_{args.phase}_{family}_{seed}_{seat}_{mode}",
                        "kind": "python", "path": str(OPPONENTS[family]), "entrypoint": "agent",
                    })
                    own, opp, first_shop, calls = play(policy, opponent, int(seed), seat)
                    rows.append({
                        "mode": mode, "opponent_family": family, "seed": int(seed), "seat": seat,
                        "first_shop": first_shop, "own": own, "opp": opp, "margin": own - opp,
                        "calls": calls,
                    })

    modes = {}
    for mode in ("parent", "candidate"):
        selected = [row for row in rows if row["mode"] == mode]
        modes[mode] = summarize(selected)
        modes[mode]["by_family"] = {
            family: summarize([row for row in selected if row["opponent_family"] == family])
            for family in families
        }
    paired = paired_summary(rows, families)
    passed = paired["primary_pass"] and paired["guardrail_pass"]
    decision = (
        "PROMOTE_TO_CHALLENGER" if args.phase == "confirmation" and passed
        else "ADVANCE_TO_CONFIRMATION" if args.phase == "discovery" and passed
        else "DO_NOT_PROMOTE"
    )
    result = {
        "schema": "kaggriculture-v18-frozen-paired-evaluation-v1",
        "phase": args.phase,
        "decision": decision,
        "engine": str(kagsim.ENGINE_VERSION),
        "candidate": candidate_manifest["candidate"],
        "candidate_main_sha256": candidate_manifest["main_sha256"],
        "candidate_archive_sha256": candidate_manifest["archive_sha256"],
        "frozen_seed_manifest": str(HERE / "frozen_seeds.json"),
        "seeds": seeds,
        "opponent_families": families,
        "double_seat": True,
        "modes": modes,
        "paired_candidate_vs_parent": paired,
        "rows": rows,
    }
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("phase", "decision", "engine", "seeds", "opponent_families", "modes", "paired_candidate_vs_parent")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
