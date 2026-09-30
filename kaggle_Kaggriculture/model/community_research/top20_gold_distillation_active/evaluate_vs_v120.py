#!/usr/bin/env python3
"""V122 对 V120 双座位闭环开发评测。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
MODEL = HERE.parents[1]
FACTORY = MODEL / "v10_replay_lolo_router"
CPPSIM = MODEL / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
sys.path[:0] = [str(FACTORY), str(sorted((CPPSIM / "build").glob("lib.*"))[-1])]
import kagsim  # type: ignore  # noqa: E402
from agent_factory import Registry, create_agent  # type: ignore  # noqa: E402


CANDIDATE = HERE / "main.py"
OPPONENT = MODEL / "v120_hierarchical_top5_distillation/main.py"
DEV_SEEDS = (122003, 122021, 122041, 122063, 122087, 122111, 122137, 122167, 122189, 122219, 122251, 122279,
             122309, 122333, 122363, 122393, 122417, 122449, 122477, 122501, 122537, 122557, 122579, 122611,
             122633, 122663, 122689, 122719, 122743, 122773, 122801, 122827)


def load(path: Path, model_id: str):
    registry = Registry(path=HERE / "development_registry.json", models={}, raw={})
    return create_agent(registry, {"id": model_id, "kind": "python", "path": str(path), "entrypoint": "agent"})


def play(seed: int, seat: int, candidate_path: Path = CANDIDATE, opponent_path: Path = OPPONENT) -> dict:
    candidate, opponent = load(candidate_path, f"candidate_{seed}_{seat}"), load(opponent_path, f"opponent_{seed}_{seat}")
    agents = [opponent, opponent]; agents[seat] = candidate
    game, turns = kagsim.Game(seed), 0
    while not game.done:
        observations = [game.observe(0), game.observe(1)]
        game.step(agents[0](observations[0]), agents[1](observations[1])); turns += 1
    rewards = [float(game.reward(0)), float(game.reward(1))]
    own, rival = rewards[seat], rewards[1-seat]
    return {"seed": seed, "seat": seat, "turns": turns, "own_reward": own, "opponent_reward": rival,
            "margin": own-rival, "outcome": "win" if own > rival else "tie" if own == rival else "loss",
            "shop_sequence": list(((observations[seat].get("town") or {}).get("unlocked_shops") or []))}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--seeds", type=int, default=4); parser.add_argument("--seed-values", default=""); parser.add_argument("--output", default="development_vs_v120.json"); parser.add_argument("--candidate", default=str(CANDIDATE)); parser.add_argument("--opponent", default=str(OPPONENT))
    args = parser.parse_args()
    seeds = tuple(int(value) for value in args.seed_values.split(",") if value.strip()) if args.seed_values else DEV_SEEDS[:max(1, min(args.seeds, len(DEV_SEEDS)))]
    candidate_path = Path(args.candidate).expanduser().resolve()
    opponent_path = Path(args.opponent).expanduser().resolve()
    rows = []
    for seed in seeds:
        for seat in (0, 1):
            row = play(seed, seat, candidate_path, opponent_path); rows.append(row); print(json.dumps(row, ensure_ascii=False), flush=True)
    wins = sum(r["outcome"] == "win" for r in rows); ties = sum(r["outcome"] == "tie" for r in rows)
    report = {"schema": "kaggriculture-research-candidate-duel-development-v1", "candidate": str(candidate_path), "opponent": str(opponent_path), "engine": str(kagsim.ENGINE_VERSION),
              "seed_role": "development", "dual_seat": True, "games": len(rows),
              "wins_ties_losses": [wins, ties, len(rows)-wins-ties], "win_rate": wins/len(rows),
              "mean_margin": sum(r["margin"] for r in rows)/len(rows), "all_719_turns": all(r["turns"] == 719 for r in rows), "rows": rows}
    (HERE / args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k != "rows"}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
