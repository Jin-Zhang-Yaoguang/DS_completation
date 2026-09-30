"""Small official-seed smoke against three V5/V8 lineage controls."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
from typing import Any

from kaggle_environments import make

from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import (
    create_agent,
    load_registry,
)


HERE = Path(__file__).resolve().parent
V10_REGISTRY = HERE.parent / "v10_replay_lolo_router" / "final_registry.json"
CANDIDATE_REGISTRY = HERE / "registry_entry.json"
REPORT = HERE / "multi_lineage_smoke_report.json"
DEFAULT_OPPONENTS = ("baseline_v5", "baseline_v8", "v5_topdays")


def game(seed: int, opponent_id: str, candidate_seat: int) -> dict[str, Any]:
    candidate_registry = load_registry(CANDIDATE_REGISTRY)
    opponent_registry = load_registry(V10_REGISTRY)
    candidate = create_agent(candidate_registry, "v12b_market_feedback_router")
    opponent = create_agent(opponent_registry, opponent_id)
    agents = [candidate, opponent]
    if candidate_seat == 1:
        agents.reverse()
    env = make("kaggriculture", configuration={"seed": seed}, debug=True)
    steps = env.run(agents)
    final = steps[-1]
    statuses = [str(state.status) for state in final]
    rewards = [float(state.reward or 0) for state in final]
    margin = rewards[candidate_seat] - rewards[1 - candidate_seat]
    diagnostics = candidate.diagnostics().get("model_status", {})
    return {
        "seed": seed,
        "opponent": opponent_id,
        "candidate_seat": candidate_seat,
        "steps": len(steps),
        "statuses": statuses,
        "rewards": rewards,
        "candidate_margin": margin,
        "candidate_score": 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0,
        "diagnostics": diagnostics,
    }


def run(seeds: list[int], opponents: list[str]) -> dict[str, Any]:
    games = [
        game(seed, opponent, seat)
        for opponent in opponents
        for seed in seeds
        for seat in (0, 1)
    ]
    if any(row["steps"] != 720 or row["statuses"] != ["DONE", "DONE"] for row in games):
        raise RuntimeError("incomplete smoke game")
    if any(row["diagnostics"].get("errors") for row in games):
        raise RuntimeError("candidate residual error")

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in games:
        grouped[row["opponent"]].append(row)

    def summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "games": len(rows),
            "score_rate": sum(row["candidate_score"] for row in rows) / len(rows),
            "average_margin": sum(row["candidate_margin"] for row in rows) / len(rows),
            "triggered_games": sum(bool(row["diagnostics"].get("trigger_count")) for row in rows),
            "trigger_count": sum(int(row["diagnostics"].get("trigger_count", 0)) for row in rows),
            "held_quantity": sum(int(row["diagnostics"].get("held_quantity", 0)) for row in rows),
        }

    payload = {
        "schema": "kaggriculture-v12b-multi-lineage-smoke-1",
        "formal_evaluation": False,
        "threshold_tuning_allowed": False,
        "source": "official 2026-08-18 train-split screening seeds",
        "seeds": seeds,
        "opponents": opponents,
        "games": games,
        "summary": summary(games),
        "by_opponent": {key: summary(value) for key, value in grouped.items()},
    }
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"summary": payload["summary"], "by_opponent": payload["by_opponent"]}, ensure_ascii=False, indent=2))
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", required=True)
    parser.add_argument("--opponents", default=",".join(DEFAULT_OPPONENTS))
    args = parser.parse_args()
    run(
        [int(value) for value in args.seeds.split(",") if value.strip()],
        [value for value in args.opponents.split(",") if value.strip()],
    )
