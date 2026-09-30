"""Small paired closed-loop smoke; intentionally not a formal evaluation."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

from kaggle_environments import make


HERE = Path(__file__).resolve().parent
PARENT = HERE.parent / "v8_kawa_lead2_slot" / "main.py"
REPORT = HERE / "smoke_report.json"


def _fresh(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _game(seed: int, candidate_seat: int) -> dict[str, Any]:
    candidate = _fresh(HERE / "main.py", f"v12b_candidate_{seed}_{candidate_seat}")
    parent = _fresh(PARENT, f"v12b_parent_{seed}_{candidate_seat}")
    agents = [candidate.agent, parent.agent]
    if candidate_seat == 1:
        agents.reverse()
    env = make("kaggriculture", configuration={"seed": seed}, debug=True)
    steps = env.run(agents)
    final = steps[-1]
    statuses = [str(state.status) for state in final]
    rewards = [float(state.reward or 0) for state in final]
    candidate_reward = rewards[candidate_seat]
    parent_reward = rewards[1 - candidate_seat]
    return {
        "seed": seed,
        "candidate_seat": candidate_seat,
        "steps": len(steps),
        "statuses": statuses,
        "rewards": rewards,
        "candidate_margin": candidate_reward - parent_reward,
        "candidate_score": 1.0 if candidate_reward > parent_reward else 0.5 if candidate_reward == parent_reward else 0.0,
        "diagnostics": candidate.model_status(),
    }


def run(seeds: list[int]) -> dict[str, Any]:
    games = [_game(seed, seat) for seed in seeds for seat in (0, 1)]
    if any(game["steps"] != 720 or game["statuses"] != ["DONE", "DONE"] for game in games):
        raise RuntimeError("incomplete smoke game")
    if any(game["diagnostics"]["errors"] for game in games):
        raise RuntimeError("candidate residual error")
    payload = {
        "schema": "kaggriculture-v12b-paired-smoke-1",
        "formal_evaluation": False,
        "opponent": "baseline_v8",
        "seeds": seeds,
        "games": games,
        "summary": {
            "games": len(games),
            "score_rate": sum(game["candidate_score"] for game in games) / len(games),
            "average_margin": sum(game["candidate_margin"] for game in games) / len(games),
            "trigger_count": sum(game["diagnostics"]["trigger_count"] for game in games),
            "held_quantity": sum(game["diagnostics"]["held_quantity"] for game in games),
        },
    }
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", default="120021,120022")
    args = parser.parse_args()
    run([int(value) for value in args.seeds.split(",") if value.strip()])

