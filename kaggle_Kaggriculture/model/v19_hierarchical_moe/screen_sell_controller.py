#!/usr/bin/env python3
"""Development ablation for per-product sell controller variants."""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
MODEL = PROJECT / "model"
CPPSIM = MODEL / "community_research" / "2026-08-26" / "live_cli" / "external_repos" / "kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
sys.path[:0] = [str(PROJECT.parent), str(HERE), str(FACTORY), str(sorted((CPPSIM / "build").glob("lib.*"))[-1])]

import kagsim  # type: ignore
from agent_factory import Registry, create_agent  # type: ignore
from hierarchical_policy import make_agent


OPPONENTS = {
    "adaptive_market": MODEL / "v1_adaptive_market" / "main.py",
    "anti_mirror": MODEL / "v9_anti_mirror" / "main.py",
    "incumbent_r002": MODEL / "v12_incumbent_r002" / "main.py",
    "kawa_lead2": MODEL / "v8_kawa_lead2_slot" / "main.py",
}
MODES = (
    "none", "boost_strawberry", "boost_melon", "boost_milk",
    "boost_wool", "boost_fertilizer", "boost25", "band25",
)
SEEDS = tuple(range(71000, 71008))


def score(margin: float) -> float:
    return 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0


def play(policy, opponent, seed: int, seat: int):
    game = kagsim.Game(seed)
    agents = [None, None]
    agents[seat], agents[1 - seat] = policy, opponent
    while not game.done:
        observations = [game.observe(0), game.observe(1)]
        game.step(agents[0](observations[0]), agents[1](observations[1]))
    rewards = [float(game.reward(0)), float(game.reward(1))]
    return rewards[seat], rewards[1 - seat]


def summarize(rows: list[dict]) -> dict:
    return {
        "games": len(rows),
        "wins_ties_losses": [sum(row["margin"] > 0 for row in rows), sum(row["margin"] == 0 for row in rows), sum(row["margin"] < 0 for row in rows)],
        "score_rate": statistics.mean(score(row["margin"]) for row in rows),
        "mean_bank": statistics.mean(row["own"] for row in rows),
        "mean_margin": statistics.mean(row["margin"] for row in rows),
    }


def main() -> int:
    registry = Registry(path=Path(__file__).resolve(), models={}, raw={})
    rows = []
    for family, path in OPPONENTS.items():
        for seed in SEEDS:
            for seat in (0, 1):
                for mode in MODES:
                    policy = make_agent("router", seller_mode=mode)
                    opponent = create_agent(registry, {
                        "id": f"sell_screen_{family}_{seed}_{seat}_{mode}", "kind": "python",
                        "path": str(path), "entrypoint": "agent",
                    })
                    own, opp = play(policy, opponent, seed, seat)
                    rows.append({
                        "mode": mode, "opponent_family": family, "seed": seed, "seat": seat,
                        "own": own, "opp": opp, "margin": own - opp,
                    })
        print(f"completed {family}: {len(rows)} rows", flush=True)
    baseline = {(row["opponent_family"], row["seed"], row["seat"]): row for row in rows if row["mode"] == "none"}
    modes = {}
    for mode in MODES:
        selected = [row for row in rows if row["mode"] == mode]
        result = summarize(selected)
        if mode != "none":
            paired = []
            for row in selected:
                base = baseline[(row["opponent_family"], row["seed"], row["seat"])]
                paired.append({
                    "score_delta": score(row["margin"]) - score(base["margin"]),
                    "margin_delta": row["margin"] - base["margin"],
                    "own_delta": row["own"] - base["own"],
                })
            result["paired_vs_none"] = {
                "score_uplift_pp": 100 * statistics.mean(row["score_delta"] for row in paired),
                "margin_delta_mean": statistics.mean(row["margin_delta"] for row in paired),
                "own_delta_mean": statistics.mean(row["own_delta"] for row in paired),
                "positive_zero_negative": [sum(row["score_delta"] > 0 for row in paired), sum(row["score_delta"] == 0 for row in paired), sum(row["score_delta"] < 0 for row in paired)],
            }
        modes[mode] = result
    result = {
        "schema": "kaggriculture-v19-sell-controller-development-screen-v1",
        "status": "DEVELOPMENT_ABLATION_NOT_CONFIRMATION",
        "engine": str(kagsim.ENGINE_VERSION),
        "seeds": list(SEEDS), "opponent_families": list(OPPONENTS),
        "modes": modes, "rows": rows,
    }
    (HERE / "sell_controller_screen.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(modes, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
