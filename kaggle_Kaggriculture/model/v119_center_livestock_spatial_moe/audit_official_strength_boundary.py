#!/usr/bin/env python3
"""用官方 1.32.7 引擎复核 V119 对 V76 的 C++ 模拟结果。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

from kaggle_environments import __version__ as kaggle_environments_version
from kaggle_environments import make


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
FACTORY = MODEL / "v10_replay_lolo_router"
sys.path.insert(0, str(FACTORY))

from agent_factory import Registry, create_agent  # noqa: E402


SEEDS = (
    111406515,
    200111900,
    208899670,
    306678837,
    322754288,
    343166320,
    347218322,
    363531319,
)
CANDIDATE = HERE / "main.py"
OPPONENT = MODEL / "v76_adjacent_safe_buy_lead/main.py"
CPPSIM_RESULT = HERE / "strength_boundary_results.json"
OUTPUT = HERE / "official_strength_audit_results.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_agent(path: Path, model_id: str):
    registry = Registry(path=HERE / "official_audit_registry.json", models={}, raw={})
    return create_agent(
        registry,
        {"id": model_id, "kind": "python", "path": str(path), "entrypoint": "agent"},
    )


def play(seed: int, seat: int) -> dict:
    candidate = load_agent(CANDIDATE, f"v119_official_{seed}_{seat}")
    opponent = load_agent(OPPONENT, f"v76_official_{seed}_{seat}")
    agents = [opponent, opponent]
    agents[seat] = candidate
    env = make(
        "kaggriculture",
        configuration={
            "seed": seed,
            "episodeSteps": 720,
            "actTimeout": 10,
            "runTimeout": 1200,
        },
        debug=True,
    )
    env.run(agents)
    final = env.steps[-1]
    rewards = [float(final[index].reward) for index in (0, 1)]
    statuses = [str(final[index].status) for index in (0, 1)]
    own = rewards[seat]
    other = rewards[1 - seat]
    return {
        "seed": seed,
        "seat": seat,
        "turns": len(env.steps) - 1,
        "own_reward": own,
        "opponent_reward": other,
        "margin": own - other,
        "outcome": "win" if own > other else "tie" if own == other else "loss",
        "statuses": statuses,
    }


def main() -> int:
    cppsim = json.loads(CPPSIM_RESULT.read_text(encoding="utf-8"))
    expected = {
        (int(row["seed"]), int(row["seat"])): row
        for row in cppsim["panels"]["v119"]["rows"]
    }
    rows = []
    for seed in SEEDS:
        for seat in (0, 1):
            row = play(seed, seat)
            reference = expected[(seed, seat)]
            row["cppsim_exact_match"] = all(
                row[key] == reference[key]
                for key in ("turns", "own_reward", "opponent_reward", "margin", "outcome")
            )
            rows.append(row)
            print(
                json.dumps(
                    {
                        "seed": seed,
                        "seat": seat,
                        "outcome": row["outcome"],
                        "cppsim_exact_match": row["cppsim_exact_match"],
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
    wins = sum(row["outcome"] == "win" for row in rows)
    ties = sum(row["outcome"] == "tie" for row in rows)
    losses = len(rows) - wins - ties
    result = {
        "schema": "kaggriculture-v119-official-strength-audit-v1",
        "official_engine": f"kaggle_environments {kaggle_environments_version}",
        "configuration": {"episodeSteps": 720, "dualSeat": True, "sameSeeds": True},
        "candidate": {"path": str(CANDIDATE), "sha256": sha256(CANDIDATE)},
        "opponent": {"path": str(OPPONENT), "sha256": sha256(OPPONENT)},
        "games": len(rows),
        "wins_ties_losses": [wins, ties, losses],
        "mean_own_reward": sum(row["own_reward"] for row in rows) / len(rows),
        "mean_margin": sum(row["margin"] for row in rows) / len(rows),
        "all_done": all(row["statuses"] == ["DONE", "DONE"] for row in rows),
        "all_719_decisions": all(row["turns"] == 719 for row in rows),
        "cppsim_exact_match_all": all(row["cppsim_exact_match"] for row in rows),
        "rows": rows,
        "conclusion": "CPPSIM_RESULT_CONFIRMED_BY_OFFICIAL_ENGINE",
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "rows"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
