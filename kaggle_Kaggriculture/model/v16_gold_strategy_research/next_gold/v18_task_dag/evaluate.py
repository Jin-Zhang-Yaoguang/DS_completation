#!/usr/bin/env python3
"""Paired V17 versus task-DAG repair evaluation on deduplicated strong families."""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
MODEL = ROOT / "kaggle_Kaggriculture" / "model"
CPPSIM = MODEL / "community_research" / "2026-08-26" / "live_cli" / "external_repos" / "kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
from policy import make_agent  # noqa: E402


OPPONENTS = {
    "adaptive_market": MODEL / "v1_adaptive_market" / "main.py",
    "bc_ppo": MODEL / "v3_bc_ppo_hybrid" / "main.py",
    "anti_mirror": MODEL / "v9_anti_mirror" / "main.py",
    "incumbent_r002": MODEL / "v12_incumbent_r002" / "main.py",
    "ppo_topdays": MODEL / "v5_ppo_v2_league" / "v5_ppo_v2_topdays" / "main.py",
    "rule_hybrid": MODEL / "v5_rule_hybrid" / "main.py",
    "kawa_lead2": MODEL / "v8_kawa_lead2_slot" / "main.py",
}


def runtime():
    builds = sorted((CPPSIM / "build").glob("lib.*"))
    sys.path.insert(0, str(builds[-1]))
    sys.path.insert(0, str(FACTORY))
    import kagsim  # type: ignore
    from agent_factory import Registry, create_agent  # type: ignore
    return kagsim, Registry(path=Path(__file__).resolve(), models={}, raw={}), create_agent


def score(margin: float) -> float:
    return 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0


def quantile(values: list[float], p: float) -> float:
    values = sorted(values)
    x = (len(values) - 1) * p
    lo, hi = math.floor(x), math.ceil(x)
    return values[lo] if lo == hi else values[lo] * (hi - x) + values[hi] * (x - lo)


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    margins = [float(r["margin"]) for r in rows]
    tail = sorted(margins)[:max(1, int(len(margins) * .1))]
    return {
        "games": len(rows),
        "wins_ties_losses": [sum(x > 0 for x in margins), sum(x == 0 for x in margins), sum(x < 0 for x in margins)],
        "score_rate": statistics.mean(score(x) for x in margins),
        "mean_bank": statistics.mean(float(r["own"]) for r in rows),
        "mean_margin": statistics.mean(margins),
        "margin_p10": quantile(margins, .1),
        "margin_cvar10": statistics.mean(tail),
        "runtime_us_per_call": statistics.mean(float(r["stats"]["total_ns"]) / max(1, int(r["stats"]["calls"])) / 1000 for r in rows),
        "modified_calls": sum(int(r["stats"]["modified_calls"]) for r in rows),
        "modified_units": sum(int(r["stats"]["modified_units"]) for r in rows),
        "parent_exact_fraction": sum(int(r["stats"]["parent_exact_calls"]) for r in rows) / max(1, sum(int(r["stats"]["calls"]) for r in rows)),
        "actual_execution_failures": sum(int(r["stats"]["actual_execution_failures"]) for r in rows),
        "actual_attempted_actions": sum(int(r["stats"]["actual_attempted_actions"]) for r in rows),
        "actual_completed_actions": sum(int(r["stats"]["actual_completed_actions"]) for r in rows),
        "deadline_attempted": sum(int(r["stats"]["actual_deadline_attempted"]) for r in rows),
        "deadline_completed": sum(int(r["stats"]["actual_deadline_completed"]) for r in rows),
        "deadline_completion_rate": sum(int(r["stats"]["actual_deadline_completed"]) for r in rows) / max(1, sum(int(r["stats"]["actual_deadline_attempted"]) for r in rows)),
        "harvest_units_certificate": sum(int(r["stats"]["harvest_units"]) for r in rows),
        "deadline_action_certificate": sum(int(r["stats"]["deadline_actions"]) for r in rows),
    }


def bootstrap_seed_ci(paired: list[dict[str, Any]], key: str, draws: int = 4000) -> list[float]:
    rng = random.Random(18032026)
    seeds = sorted({int(r["seed"]) for r in paired})
    groups = {seed: [float(r[key]) for r in paired if int(r["seed"]) == seed] for seed in seeds}
    values = []
    for _ in range(draws):
        sample = [rng.choice(seeds) for _ in seeds]
        values.append(statistics.mean(x for seed in sample for x in groups[seed]))
    return [quantile(values, .025), quantile(values, .975)]


def play(policy, opponent, seed: int, seat: int, kagsim):
    game = kagsim.Game(seed)
    agents = [None, None]
    agents[seat], agents[1 - seat] = policy, opponent
    while not game.done:
        game.step(agents[0](game.observe(0)), agents[1](game.observe(1)))
    rewards = [float(game.reward(0)), float(game.reward(1))]
    return rewards[seat], rewards[1 - seat]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=("dev", "test"), required=True)
    parser.add_argument("--seed-start", type=int)
    parser.add_argument("--seeds", type=int)
    parser.add_argument("--opponents", default=",".join(OPPONENTS))
    parser.add_argument("--output")
    args = parser.parse_args()
    default_start, default_n = ((50000, 8) if args.split == "dev" else (60000, 16))
    start, count = args.seed_start or default_start, args.seeds or default_n
    families = [x.strip() for x in args.opponents.split(",") if x.strip()]
    kagsim, registry, create_agent = runtime()
    rows = []
    for family in families:
        for seed in range(start, start + count):
            for seat in (0, 1):
                for mode in ("parent", "candidate"):
                    policy = make_agent(mode)
                    opponent = create_agent(registry, {
                        "id": f"dag_{family}_{seed}_{seat}_{mode}", "kind": "python",
                        "path": str(OPPONENTS[family]), "entrypoint": "agent",
                    })
                    own, opp = play(policy, opponent, seed, seat, kagsim)
                    rows.append({
                        "mode": mode, "family": family, "seed": seed, "seat": seat,
                        "own": own, "opp": opp, "margin": own - opp,
                        "stats": dict(policy.stats),
                    })
    result: dict[str, Any] = {
        "schema": "kaggriculture-v18-task-dag-eval-v1",
        "split": args.split, "seed_range": [start, start + count - 1],
        "seed_split_frozen": True, "both_seats": True,
        "opponent_families": families, "engine": str(kagsim.ENGINE_VERSION),
        "modes": {},
    }
    for mode in ("parent", "candidate"):
        subset = [r for r in rows if r["mode"] == mode]
        by_family = {f: summarize([r for r in subset if r["family"] == f]) for f in families}
        result["modes"][mode] = {
            **summarize(subset),
            "family_equal_score_rate": statistics.mean(x["score_rate"] for x in by_family.values()),
            "worst_family_score_rate": min(x["score_rate"] for x in by_family.values()),
            "by_family": by_family,
        }
    base = {(r["family"], r["seed"], r["seat"]): r for r in rows if r["mode"] == "parent"}
    paired = []
    for row in rows:
        if row["mode"] != "candidate":
            continue
        old = base[(row["family"], row["seed"], row["seat"])]
        paired.append({
            "family": row["family"], "seed": row["seed"], "seat": row["seat"],
            "score_delta": score(row["margin"]) - score(old["margin"]),
            "margin_delta": row["margin"] - old["margin"],
            "bank_delta": row["own"] - old["own"],
        })
    result["paired"] = {
        "games": len(paired),
        "score_uplift_pp": 100 * statistics.mean(r["score_delta"] for r in paired),
        "score_uplift_seed_cluster_ci95_pp": [100 * x for x in bootstrap_seed_ci(paired, "score_delta")],
        "score_positive_zero_negative": [sum(r["score_delta"] > 0 for r in paired), sum(r["score_delta"] == 0 for r in paired), sum(r["score_delta"] < 0 for r in paired)],
        "mean_margin_delta": statistics.mean(r["margin_delta"] for r in paired),
        "margin_seed_cluster_ci95": bootstrap_seed_ci(paired, "margin_delta"),
        "mean_bank_delta": statistics.mean(r["bank_delta"] for r in paired),
        "by_family": {
            f: {
                "score_uplift_pp": 100 * statistics.mean(r["score_delta"] for r in paired if r["family"] == f),
                "mean_margin_delta": statistics.mean(r["margin_delta"] for r in paired if r["family"] == f),
                "mean_bank_delta": statistics.mean(r["bank_delta"] for r in paired if r["family"] == f),
            } for f in families
        },
    }
    result["rows"] = rows
    output = Path(args.output) if args.output else HERE / f"{args.split}_results.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"split": args.split, "modes": result["modes"], "paired": result["paired"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
