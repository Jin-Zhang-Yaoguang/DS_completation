#!/usr/bin/env python3
"""Absolute L1 evaluation on deduplicated policy families and held-out seeds."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[4]
MODEL = ROOT / "kaggle_Kaggriculture" / "model"
CPPSIM = MODEL / "community_research" / "2026-08-26" / "live_cli" / "external_repos" / "kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
from portfolio_policy import make_agent


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
    pos = (len(values) - 1) * p
    low, high = math.floor(pos), math.ceil(pos)
    return values[low] if low == high else values[low] * (high - pos) + values[high] * (pos - low)


def summarize(rows: list[dict]) -> dict:
    margins = sorted(float(row["margin"]) for row in rows)
    n = max(1, int(len(margins) * 0.10))
    return {
        "games": len(rows),
        "wins_ties_losses": [sum(x > 0 for x in margins), sum(x == 0 for x in margins), sum(x < 0 for x in margins)],
        "score_rate": statistics.mean(score(x) for x in margins),
        "mean_bank": statistics.mean(float(row["own"]) for row in rows),
        "mean_margin": statistics.mean(margins),
        "margin_p10": quantile(margins, 0.10),
        "margin_cvar10": statistics.mean(margins[:n]),
    }


def play(policy, opponent, seed: int, seat: int, kagsim):
    game = kagsim.Game(seed)
    agents = [None, None]
    agents[seat] = policy
    agents[1 - seat] = opponent
    while not game.done:
        game.step(agents[0](game.observe(0)), agents[1](game.observe(1)))
    rewards = [float(game.reward(0)), float(game.reward(1))]
    return rewards[seat], rewards[1 - seat]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-start", type=int, default=20000)
    parser.add_argument("--seeds", type=int, default=24)
    parser.add_argument("--opponents", default=",".join(OPPONENTS))
    parser.add_argument("--output", default=str(HERE / "live_pool_results.json"))
    args = parser.parse_args()
    selected = [name.strip() for name in args.opponents.split(",") if name.strip()]
    kagsim, registry, create_agent = runtime()
    rows = []
    for family in selected:
        for seed in range(args.seed_start, args.seed_start + args.seeds):
            for seat in (0, 1):
                for mode in ("single_default", "router"):
                    policy = make_agent(mode)
                    opponent = create_agent(registry, {
                        "id": f"{family}_{seed}_{seat}_{mode}", "kind": "python",
                        "path": str(OPPONENTS[family]), "entrypoint": "agent",
                    })
                    own, opp = play(policy, opponent, seed, seat, kagsim)
                    rows.append({
                        "mode": mode, "opponent_family": family,
                        "seed": seed, "seat": seat, "own": own, "opp": opp,
                        "margin": own - opp,
                    })

    result = {
        "status": "HELD_OUT_LOCAL_L1_STRONG_PROXY_EVIDENCE_NOT_KAGGLE_GOLD_PROOF",
        "engine": str(kagsim.ENGINE_VERSION),
        "seed_range": [args.seed_start, args.seed_start + args.seeds - 1],
        "seeds_exposed_in_route_training": False,
        "opponent_families": selected,
        "modes": {},
    }
    for mode in ("single_default", "router"):
        mode_rows = [row for row in rows if row["mode"] == mode]
        by_family = {family: summarize([row for row in mode_rows if row["opponent_family"] == family]) for family in selected}
        result["modes"][mode] = {
            **summarize(mode_rows),
            "family_equal_score_rate": statistics.mean(value["score_rate"] for value in by_family.values()),
            "worst_family_score_rate": min(value["score_rate"] for value in by_family.values()),
            "by_family": by_family,
        }
    # Paired router delta isolates routing from the common route executor.
    index = {(row["opponent_family"], row["seed"], row["seat"]): row for row in rows if row["mode"] == "single_default"}
    paired = []
    for row in rows:
        if row["mode"] != "router":
            continue
        baseline = index[(row["opponent_family"], row["seed"], row["seat"])]
        paired.append({
            "opponent_family": row["opponent_family"], "seed": row["seed"], "seat": row["seat"],
            "score_delta": score(row["margin"]) - score(baseline["margin"]),
            "margin_delta": row["margin"] - baseline["margin"],
            "own_delta": row["own"] - baseline["own"],
        })
    result["paired_router_vs_single"] = {
        "games": len(paired),
        "score_uplift_pp": 100 * statistics.mean(row["score_delta"] for row in paired),
        "score_positive_zero_negative": [sum(row["score_delta"] > 0 for row in paired), sum(row["score_delta"] == 0 for row in paired), sum(row["score_delta"] < 0 for row in paired)],
        "margin_delta_mean": statistics.mean(row["margin_delta"] for row in paired),
        "own_delta_mean": statistics.mean(row["own_delta"] for row in paired),
        "by_family": {
            family: {
                "score_uplift_pp": 100 * statistics.mean(row["score_delta"] for row in paired if row["opponent_family"] == family),
                "margin_delta_mean": statistics.mean(row["margin_delta"] for row in paired if row["opponent_family"] == family),
            }
            for family in selected
        },
    }
    result["rows"] = rows
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("status", "engine", "seed_range", "opponent_families", "modes", "paired_router_vs_single")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
