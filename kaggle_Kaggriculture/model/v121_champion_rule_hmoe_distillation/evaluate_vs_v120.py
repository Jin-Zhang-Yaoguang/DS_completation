#!/usr/bin/env python3
"""V121 对 V120 的双座位开发门；开发种子不用于最终确认。"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
FACTORY = MODEL / "v10_replay_lolo_router"
CPPSIM = MODEL / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
sys.path[:0] = [str(FACTORY), str(sorted((CPPSIM / "build").glob("lib.*"))[-1])]

import kagsim  # type: ignore  # noqa: E402
from agent_factory import Registry, create_agent  # type: ignore  # noqa: E402


CANDIDATE = HERE / "behavior_agent.py"
OPPONENT = MODEL / "v120_hierarchical_top5_distillation/main.py"
DEV_SEEDS = (
    121003, 121019, 121043, 121061, 121087, 121109, 121139, 121163,
    121189, 121229, 121259, 121283, 121309, 121343, 121369, 121403,
    121421, 121453, 121493, 121523, 121547, 121577, 121601, 121631,
    121661, 121687, 121721, 121747, 121789, 121819, 121843, 121883,
)


def load(path: Path, model_id: str):
    registry = Registry(path=HERE / "development_registry.json", models={}, raw={})
    return create_agent(registry, {"id": model_id, "kind": "python", "path": str(path), "entrypoint": "agent"})


def play(seed: int, seat: int) -> dict:
    candidate = load(CANDIDATE, f"v121_{seed}_{seat}")
    opponent = load(OPPONENT, f"v120_{seed}_{seat}")
    agents = [opponent, opponent]
    agents[seat] = candidate
    game = kagsim.Game(seed)
    turns = 0
    while not game.done:
        observations = [game.observe(0), game.observe(1)]
        game.step(agents[0](observations[0]), agents[1](observations[1]))
        turns += 1
    rewards = [float(game.reward(0)), float(game.reward(1))]
    own, rival = rewards[seat], rewards[1 - seat]
    return {
        "seed": seed, "seat": seat, "turns": turns, "own_reward": own,
        "opponent_reward": rival, "margin": own - rival,
        "outcome": "win" if own > rival else "tie" if own == rival else "loss",
    }


def main() -> int:
    global CANDIDATE
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=len(DEV_SEEDS))
    parser.add_argument("--output", default="development_vs_v120.json")
    parser.add_argument("--teacher", default="tetsuya")
    parser.add_argument("--candidate", default=str(CANDIDATE))
    args = parser.parse_args()
    CANDIDATE = Path(args.candidate).expanduser().resolve()
    os.environ["V121_TEACHER"] = args.teacher
    seeds = DEV_SEEDS[: max(1, min(len(DEV_SEEDS), args.seeds))]
    rows = []
    for seed in seeds:
        for seat in (0, 1):
            row = play(seed, seat)
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
    wins = sum(row["outcome"] == "win" for row in rows)
    ties = sum(row["outcome"] == "tie" for row in rows)
    report = {
        "schema": "kaggriculture-v121-vs-v120-development-v1",
        "engine": str(kagsim.ENGINE_VERSION), "seed_role": "development", "dual_seat": True,
        "teacher_expert": args.teacher,
        "games": len(rows), "wins_ties_losses": [wins, ties, len(rows) - wins - ties],
        "win_rate": wins / len(rows), "mean_margin": sum(row["margin"] for row in rows) / len(rows),
        "all_719_turns": all(row["turns"] == 719 for row in rows), "rows": rows,
    }
    (HERE / args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "rows"}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
