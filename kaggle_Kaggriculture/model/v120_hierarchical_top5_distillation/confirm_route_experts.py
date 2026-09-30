#!/usr/bin/env python3
"""Confirm the best Top5-derived route experts on untouched fresh seeds."""

from __future__ import annotations

import json

from search_top5_route_experts import OPPONENTS, play, routes


SELECTED = (
    "OceanMix__104547425__s0",
    "Driz Lo__104535318__s1",
    "QQ Farming__104548310__s0",
)
SEEDS = (
    1750237316, 386540959, 1675367089, 208927640, 105988272, 176840668,
    991358284, 1427255862, 1986190616, 920470308, 1989639141, 621034630,
    1408141287, 726921503, 1747338698, 1569903591, 1703048527, 536109841,
    398260213, 1746362336, 667364645, 856039202, 839896864, 814054296,
    1494429784, 1734110524, 54462235, 147187962, 1061747370, 350405114,
    986373255, 1283800802,
)


def main() -> int:
    catalog = {route["route_id"]: route for route in routes()}
    reports = {}
    for route_id in SELECTED:
        route = catalog[route_id]
        rows = [play(route, opponent, seed, seat) for opponent in OPPONENTS for seed in SEEDS for seat in (0, 1)]
        by_opponent = {}
        for opponent in OPPONENTS:
            sample = [row for row in rows if row["opponent"] == opponent]
            wins = sum(row["outcome"] == "win" for row in sample)
            ties = sum(row["outcome"] == "tie" for row in sample)
            by_opponent[opponent] = {"games": len(sample), "wins_ties_losses": [wins, ties, len(sample) - wins - ties], "win_rate": wins / len(sample), "mean_margin": sum(row["margin"] for row in sample) / len(sample), "mean_own_reward": sum(row["own_reward"] for row in sample) / len(sample)}
        reports[route_id] = {"teacher": route["teacher"], "episode_id": route["episode_id"], "by_opponent": by_opponent, "passes_65_both": all(value["win_rate"] >= 0.65 for value in by_opponent.values()), "rows": rows}
        print(json.dumps({"route": route_id, "by_opponent": by_opponent}, ensure_ascii=False), flush=True)
    report = {"schema": "kaggriculture-v120-route-confirmation-v1", "seeds": list(SEEDS), "seed_role": "untouched_confirmation", "dual_seat": True, "routes": reports}
    from pathlib import Path
    path = Path(__file__).resolve().parent / "route_confirmation_results.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
