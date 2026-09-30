"""Add a same-seed/seat baseline-V8 control arm to multi-lineage smoke."""

from __future__ import annotations

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
SOURCE = HERE / "multi_lineage_smoke_report.json"
OUTPUT = HERE / "paired_control_smoke_report.json"
V10_REGISTRY = HERE.parent / "v10_replay_lolo_router" / "final_registry.json"


def control_game(seed: int, opponent_id: str, subject_seat: int) -> dict[str, Any]:
    registry = load_registry(V10_REGISTRY)
    subject = create_agent(registry, "baseline_v8")
    opponent = create_agent(registry, opponent_id)
    agents = [subject, opponent]
    if subject_seat == 1:
        agents.reverse()
    env = make("kaggriculture", configuration={"seed": seed}, debug=True)
    steps = env.run(agents)
    final = steps[-1]
    statuses = [str(state.status) for state in final]
    rewards = [float(state.reward or 0) for state in final]
    margin = rewards[subject_seat] - rewards[1 - subject_seat]
    return {
        "seed": seed,
        "opponent": opponent_id,
        "subject_seat": subject_seat,
        "steps": len(steps),
        "statuses": statuses,
        "rewards": rewards,
        "margin": margin,
        "score": 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0,
    }


def effect_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    deltas = [row["margin_delta"] for row in rows]
    score_deltas = [row["score_delta"] for row in rows]
    triggered = [row for row in rows if row["trigger_count"] > 0]
    return {
        "tasks": len(rows),
        "mean_margin_delta": sum(deltas) / len(deltas),
        "mean_score_delta": sum(score_deltas) / len(score_deltas),
        "margin_improved_tied_worse": [
            sum(value > 0 for value in deltas),
            sum(value == 0 for value in deltas),
            sum(value < 0 for value in deltas),
        ],
        "triggered_tasks": len(triggered),
        "triggered_mean_margin_delta": (
            sum(row["margin_delta"] for row in triggered) / len(triggered) if triggered else 0.0
        ),
        "triggered_mean_score_delta": (
            sum(row["score_delta"] for row in triggered) / len(triggered) if triggered else 0.0
        ),
    }


def run() -> dict[str, Any]:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    candidates = source["games"]
    controls = [
        control_game(int(row["seed"]), str(row["opponent"]), int(row["candidate_seat"]))
        for row in candidates
    ]
    if any(row["steps"] != 720 or row["statuses"] != ["DONE", "DONE"] for row in controls):
        raise RuntimeError("incomplete control game")
    comparisons = []
    for candidate, control in zip(candidates, controls):
        key_candidate = (candidate["seed"], candidate["opponent"], candidate["candidate_seat"])
        key_control = (control["seed"], control["opponent"], control["subject_seat"])
        if key_candidate != key_control:
            raise RuntimeError((key_candidate, key_control))
        comparisons.append(
            {
                "seed": candidate["seed"],
                "opponent": candidate["opponent"],
                "seat": candidate["candidate_seat"],
                "candidate_margin": candidate["candidate_margin"],
                "control_margin": control["margin"],
                "margin_delta": candidate["candidate_margin"] - control["margin"],
                "candidate_score": candidate["candidate_score"],
                "control_score": control["score"],
                "score_delta": candidate["candidate_score"] - control["score"],
                "trigger_count": int(candidate["diagnostics"].get("trigger_count", 0)),
                "held_quantity": int(candidate["diagnostics"].get("held_quantity", 0)),
            }
        )
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in comparisons:
        grouped[row["opponent"]].append(row)
    payload = {
        "schema": "kaggriculture-v12b-paired-control-smoke-1",
        "formal_evaluation": False,
        "threshold_tuning_allowed": False,
        "candidate": "v12b_market_feedback_router",
        "control": "baseline_v8",
        "source_report": str(SOURCE),
        "comparisons": comparisons,
        "controls": controls,
        "summary": effect_summary(comparisons),
        "by_opponent": {key: effect_summary(rows) for key, rows in grouped.items()},
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"summary": payload["summary"], "by_opponent": payload["by_opponent"]}, ensure_ascii=False, indent=2))
    return payload


if __name__ == "__main__":
    run()
