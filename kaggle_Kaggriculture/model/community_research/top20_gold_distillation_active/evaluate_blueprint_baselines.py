#!/usr/bin/env python3
"""Research-only duel of declarative blueprint baselines against V120."""

from __future__ import annotations

import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
MODEL = HERE.parents[1]
FACTORY = MODEL / "v10_replay_lolo_router"
EXTERNAL = MODEL / "community_research/2026-08-26/live_cli/external_repos"
CPPSIM = EXTERNAL / "kaggriculture-cppsim"
ISLAND = EXTERNAL / "kaggriculture-island-ga"
sys.path[:0] = [
    str(FACTORY),
    str(ISLAND),
    str(sorted((CPPSIM / "build").glob("lib.*"))[-1]),
]

import kagsim  # type: ignore  # noqa: E402
from agent_factory import Registry, create_agent  # type: ignore  # noqa: E402
from islandga.compiler import compile_spec  # type: ignore  # noqa: E402
from islandga.executor import make_agent  # type: ignore  # noqa: E402
from islandga.genome import (  # type: ignore  # noqa: E402
    species_boundmix,
    species_envelope,
    species_intensity,
)


OPPONENT = MODEL / "v120_hierarchical_top5_distillation/main.py"
SEEDS = (122003, 122021, 122041, 122063)
SPECIES = {
    "envelope": species_envelope,
    "boundmix": species_boundmix,
    "intensity": species_intensity,
}


def load_v120(tag: str):
    registry = Registry(path=HERE / "development_registry.json", models={}, raw={})
    return create_agent(
        registry,
        {"id": tag, "kind": "python", "path": str(OPPONENT), "entrypoint": "agent"},
    )


def play(name: str, seed: int, seat: int) -> dict:
    candidate = make_agent(compile_spec(SPECIES[name]()))
    opponent = load_v120(f"v120_{name}_{seed}_{seat}")
    agents = [opponent, opponent]
    agents[seat] = candidate
    game = kagsim.Game(seed)
    turns = 0
    while not game.done:
        obs = [game.observe(0), game.observe(1)]
        game.step(agents[0](obs[0]), agents[1](obs[1]))
        turns += 1
    rewards = [float(game.reward(0)), float(game.reward(1))]
    own, rival = rewards[seat], rewards[1 - seat]
    return {
        "species": name,
        "seed": seed,
        "seat": seat,
        "turns": turns,
        "own_reward": own,
        "opponent_reward": rival,
        "margin": own - rival,
        "outcome": "win" if own > rival else "tie" if own == rival else "loss",
    }


def main() -> int:
    rows = []
    for name in SPECIES:
        for seed in SEEDS:
            for seat in (0, 1):
                row = play(name, seed, seat)
                rows.append(row)
                print(json.dumps(row, ensure_ascii=False), flush=True)
    summaries = {}
    for name in SPECIES:
        part = [row for row in rows if row["species"] == name]
        wins = sum(row["outcome"] == "win" for row in part)
        ties = sum(row["outcome"] == "tie" for row in part)
        summaries[name] = {
            "games": len(part),
            "wins_ties_losses": [wins, ties, len(part) - wins - ties],
            "win_rate": wins / len(part),
            "mean_reward": sum(row["own_reward"] for row in part) / len(part),
            "mean_margin": sum(row["margin"] for row in part) / len(part),
        }
    report = {
        "schema": "blueprint-baseline-vs-v120-development-v1",
        "engine": str(kagsim.ENGINE_VERSION),
        "seed_role": "development",
        "dual_seat": True,
        "summaries": summaries,
        "rows": rows,
    }
    output = HERE / "blueprint_baselines_vs_v120.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summaries, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
