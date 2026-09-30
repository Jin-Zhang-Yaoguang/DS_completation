#!/usr/bin/env python3
"""Paired labour-layer benchmark under four frozen strong market streams."""

from __future__ import annotations

import json
import statistics
from pathlib import Path

import prototype


HERE = Path(__file__).resolve().parent


def main() -> None:
    genome = json.loads((prototype.OPT / "best_genome.json").read_text())
    routes = prototype.opt.load_routes()
    rows = []
    seeds = list(range(6100, 6104))
    for family, route in routes.items():
        for seed in seeds:
            for seat in (0, 1):
                for mode in ("stock", "joint_mpc"):
                    row = prototype.play(genome, seed, seat, mode, route)
                    row["family"] = family
                    rows.append(row)
    index = {(r["family"], r["seed"], r["seat"], r["mode"]): r for r in rows}
    deltas = []
    by_family = {}
    for family in routes:
        family_delta = []
        for seed in seeds:
            for seat in (0, 1):
                a = index[(family, seed, seat, "stock")]
                b = index[(family, seed, seat, "joint_mpc")]
                family_delta.append(b["bank"] - a["bank"])
        deltas.extend(family_delta)
        by_family[family] = {
            "episodes": len(family_delta),
            "mean_bank_delta": statistics.mean(family_delta),
            "positive": sum(x > 0 for x in family_delta),
            "minimum_bank_delta": min(family_delta),
        }
    payload = {
        "schema": "kaggriculture-labor-planner-route-benchmark-v1",
        "fixed_genome": str(prototype.OPT / "best_genome.json"),
        "seeds": seeds,
        "both_seats": True,
        "families": list(routes),
        "summary": {
            "episodes": len(deltas),
            "mean_bank_delta": statistics.mean(deltas),
            "median_bank_delta": statistics.median(deltas),
            "minimum_bank_delta": min(deltas),
            "maximum_bank_delta": max(deltas),
            "positive": sum(x > 0 for x in deltas),
            "stock_score_rate": statistics.mean(
                r["bank"] > r["opponent_bank"] for r in rows if r["mode"] == "stock"),
            "joint_mpc_score_rate": statistics.mean(
                r["bank"] > r["opponent_bank"] for r in rows if r["mode"] == "joint_mpc"),
            "by_family": by_family,
        },
        "episodes_detail": rows,
    }
    (HERE / "route_benchmark_results.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload["summary"], indent=2))


if __name__ == "__main__":
    main()
