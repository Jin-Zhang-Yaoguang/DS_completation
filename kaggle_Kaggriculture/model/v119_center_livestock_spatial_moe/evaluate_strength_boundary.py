#!/usr/bin/env python3
"""Measure V119's local strength boundary; this is not a promotion gate."""

from __future__ import annotations

import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
CPPSIM = MODEL / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
sys.path[:0] = [str(FACTORY), str(sorted((CPPSIM / "build").glob("lib.*"))[-1])]

import kagsim  # type: ignore  # noqa: E402
from agent_factory import Registry, create_agent  # type: ignore  # noqa: E402


SEEDS = (111406515, 200111900, 208899670, 306678837,
         322754288, 343166320, 347218322, 363531319)
CANDIDATES = {
    "v118": MODEL / "v118_v76_yarn_reveal_liquidity_moe/main.py",
    "v119": HERE / "main.py",
}
OPPONENT = MODEL / "v76_adjacent_safe_buy_lead/main.py"


def load(path: Path, model_id: str):
    registry = Registry(path=HERE / "strength_boundary_registry.json", models={}, raw={})
    return create_agent(registry, {
        "id": model_id, "kind": "python", "path": str(path), "entrypoint": "agent",
    })


def play(path: Path, label: str, seed: int, seat: int) -> dict:
    candidate = load(path, f"{label}_{seed}_{seat}")
    opponent = load(OPPONENT, f"v76_{label}_{seed}_{seat}")
    agents = [opponent, opponent]
    agents[seat] = candidate
    game = kagsim.Game(seed)
    turns = 0
    while not game.done:
        observations = [game.observe(0), game.observe(1)]
        game.step(*[agents[index](observations[index]) for index in (0, 1)])
        turns += 1
    rewards = [float(game.reward(0)), float(game.reward(1))]
    own = rewards[seat]
    other = rewards[1 - seat]
    return {
        "seed": seed,
        "seat": seat,
        "turns": turns,
        "own_reward": own,
        "opponent_reward": other,
        "margin": own - other,
        "outcome": "win" if own > other else "tie" if own == other else "loss",
    }


def main() -> int:
    panels = {}
    for label, path in CANDIDATES.items():
        rows = [play(path, label, seed, seat) for seed in SEEDS for seat in (0, 1)]
        wins = sum(row["outcome"] == "win" for row in rows)
        ties = sum(row["outcome"] == "tie" for row in rows)
        losses = len(rows) - wins - ties
        panels[label] = {
            "opponent": "v76_adjacent_safe_buy_lead",
            "games": len(rows),
            "wins_ties_losses": [wins, ties, losses],
            "pure_win_rate": wins / len(rows),
            "mean_own_reward": sum(row["own_reward"] for row in rows) / len(rows),
            "mean_margin": sum(row["margin"] for row in rows) / len(rows),
            "rows": rows,
        }
    result = {
        "schema": "kaggriculture-v119-strength-boundary-v1",
        "engine": str(kagsim.ENGINE_VERSION),
        "purpose": "informational local boundary; not a spatial acceptance gate",
        "seeds": list(SEEDS),
        "panels": panels,
        "conclusion": (
            "GENERAL_STRENGTH_NOT_PROMOTABLE"
            if panels["v119"]["pure_win_rate"] < 0.75
            else "LOCAL_PANEL_PROMOTABLE"
        ),
    }
    (HERE / "strength_boundary_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "conclusion": result["conclusion"],
        "v118": {key: value for key, value in panels["v118"].items() if key != "rows"},
        "v119": {key: value for key, value in panels["v119"].items() if key != "rows"},
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
