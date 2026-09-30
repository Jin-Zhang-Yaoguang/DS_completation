#!/usr/bin/env python3
"""Unseen-seed benchmark against the current top fixed-route proxy."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

import optimizer
from islandga.bound import compute as relaxed_bound


PASS = {"farmer": ["PASS"], "hands": [], "market": []}


def stream_vs_idle(stream, seed: int, seat: int):
    game = optimizer.KAGSIM.Game(seed)
    while not game.done:
        pair = [PASS, PASS]
        pair[seat] = stream[game.step_count]
        game.step(pair[0], pair[1])
    return float(game.reward(seat)), float(game.reward(1 - seat))


def summary(rows):
    margins = [a - b for a, b in rows]
    return {"games": len(rows), "mean_bank": statistics.mean(a for a, _ in rows),
            "median_bank": statistics.median(a for a, _ in rows),
            "minimum_bank": min(a for a, _ in rows),
            "score_rate": statistics.mean(1.0 if a > b else 0.5 if a == b else 0.0 for a, b in rows),
            "mean_margin": statistics.mean(margins)}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, default=32)
    p.add_argument("--seed-start", type=int, default=9000)
    p.add_argument("--output", type=Path, default=Path(__file__).with_name("benchmark_results.json"))
    args = p.parse_args()
    genome = json.loads(Path(__file__).with_name("best_genome.json").read_text())
    top = optimizer.load_routes()["tyz123456"]
    seeds = range(args.seed_start, args.seed_start + args.seeds)
    candidate_idle = [(optimizer.play(genome, s, seat)["own"], 3000.0) for s in seeds for seat in (0, 1)]
    top_idle = [stream_vs_idle(top, s, seat) for s in seeds for seat in (0, 1)]
    head = [optimizer.play(genome, s, seat, top) for s in seeds for seat in (0, 1)]
    candidate_top = [(r["own"], r["opp"]) for r in head]
    _rows, allocation, upper = relaxed_bound()
    result = {
        "engine": getattr(optimizer.KAGSIM, "ENGINE_VERSION", "1.32.7"),
        "unseen_seeds": [args.seed_start, args.seed_start + args.seeds - 1],
        "both_seats": True,
        "candidate_vs_idle": summary(candidate_idle),
        "current_top_fixed_route_vs_idle": summary(top_idle),
        "candidate_vs_current_top_fixed_route": summary(candidate_top),
        "relaxed_finance_resource_upper_bound": upper,
        "relaxed_tile_day_allocation": allocation,
        "candidate_upper_capture": statistics.mean(a for a, _ in candidate_idle) / upper,
        "top_route_upper_capture": statistics.mean(a for a, _ in top_idle) / upper,
        "upper_over_top_route": upper / statistics.mean(a for a, _ in top_idle),
        "decision": "NOT_V17_STRONG_META_GATE_FAILED",
    }
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
