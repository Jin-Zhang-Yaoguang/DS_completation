#!/usr/bin/env python3
"""Blind paired-seat evaluation of the frozen standalone V120 candidate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
FACTORY = MODEL / "v10_replay_lolo_router"
CPPSIM = MODEL / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
sys.path[:0] = [str(FACTORY), str(sorted((CPPSIM / "build").glob("lib.*"))[-1])]

import kagsim  # type: ignore  # noqa: E402
from agent_factory import Registry, create_agent  # type: ignore  # noqa: E402


CANDIDATE = HERE / "main.py"
OPPONENTS = {"v76": MODEL / "v76_adjacent_safe_buy_lead/main.py", "v20": MODEL / "v20_demand_timing_moe/main.py"}
SEEDS = (
    1897393233, 1703055317, 508974116, 1688207266, 739482740, 208681512, 243990854, 515269722,
    1691793331, 817768090, 145270905, 903436061, 1660710189, 1390184932, 1001792142, 1955402915,
    1399306818, 523432823, 402554740, 223171881, 119880634, 1851192977, 846214653, 737203450,
    1670672181, 805521495, 227426904, 1288309731, 1941728086, 1130747197, 1146583089, 1817288966,
    612061758, 1983318057, 944811461, 1230601530, 323334823, 1755169918, 1718525828, 996453194,
    276918339, 1243211952, 347698581, 1661989834, 879586782, 87240299, 1010981688, 219237012,
    617160117, 906896190, 1135914765, 483076050, 1205985834, 982632125, 1963459545, 1932354099,
    408467463, 1025687344, 1991242411, 204435103, 458160755, 983519484, 1084298865, 1538496060,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path, model_id: str):
    registry = Registry(path=HERE / "gold_eval_registry.json", models={}, raw={})
    return create_agent(registry, {"id": model_id, "kind": "python", "path": str(path), "entrypoint": "agent"})


def play(opponent_name: str, seed: int, seat: int) -> dict:
    candidate = load(CANDIDATE, f"v120_{opponent_name}_{seed}_{seat}")
    opponent = load(OPPONENTS[opponent_name], f"{opponent_name}_{seed}_{seat}")
    agents = [opponent, opponent]; agents[seat] = candidate
    game = kagsim.Game(seed)
    turns = 0
    while not game.done:
        obs = [game.observe(0), game.observe(1)]
        game.step(agents[0](obs[0]), agents[1](obs[1])); turns += 1
    reward = [float(game.reward(0)), float(game.reward(1))]
    own, other = reward[seat], reward[1 - seat]
    return {"seed": seed, "seat": seat, "turns": turns, "own_reward": own, "opponent_reward": other, "margin": own - other, "outcome": "win" if own > other else "tie" if own == other else "loss"}


def main() -> int:
    panels = {}
    for opponent in OPPONENTS:
        rows = [play(opponent, seed, seat) for seed in SEEDS for seat in (0, 1)]
        wins = sum(row["outcome"] == "win" for row in rows); ties = sum(row["outcome"] == "tie" for row in rows)
        panels[opponent] = {"games": len(rows), "wins_ties_losses": [wins, ties, len(rows) - wins - ties], "win_rate": wins / len(rows), "mean_margin": sum(row["margin"] for row in rows) / len(rows), "mean_own_reward": sum(row["own_reward"] for row in rows) / len(rows), "all_719_turns": all(row["turns"] == 719 for row in rows), "rows": rows}
        print(json.dumps({"opponent": opponent, **{key: value for key, value in panels[opponent].items() if key != "rows"}}, ensure_ascii=False), flush=True)
    pass_gate = all(panel["win_rate"] >= 0.65 for panel in panels.values())
    report = {"schema": "kaggriculture-v120-gold-gate-v1", "engine": str(kagsim.ENGINE_VERSION), "candidate_sha256": sha256(CANDIDATE), "seed_role": "frozen_untouched_blind", "seeds": list(SEEDS), "dual_seat": True, "required_win_rate_each": 0.65, "panels": panels, "pass_gold_gate": pass_gate, "verdict": "GOLD_GATE_PASS" if pass_gate else "GOLD_GATE_FAIL"}
    (HERE / "gold_gate_results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if pass_gate else 2


if __name__ == "__main__":
    raise SystemExit(main())
