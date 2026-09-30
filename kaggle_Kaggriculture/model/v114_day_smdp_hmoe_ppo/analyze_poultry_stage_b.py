"""Apply Iteration 9 poultry-vs-four-control paired Stage B gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Any, Mapping

from evaluate_event_program import atomic_json, file_sha256


CANDIDATE = "POULTRY__EXPOSURE_ADAPTIVE"
CONTROLS = (
    "ENTERPRISE__DAIRY_BERRY",
    "ENTERPRISE__WOOL_MELON",
    "FIXED__MELON",
    "FIXED__STRAWBERRY",
)


def compare(report: Mapping[str, Any]) -> dict[str, Any]:
    rows = list(report["rows"])
    indexed = {
        (str(row["decision_name"]), int(row["seed"]), int(row["seat"])): row
        for row in rows
    }
    candidates = [row for row in rows if row["decision_name"] == CANDIDATE]
    margin_deltas: list[float] = []
    own_deltas: list[float] = []
    opponent_deltas: list[float] = []
    selected_controls: dict[str, int] = {control: 0 for control in CONTROLS}
    candidate_wins = envelope_wins = 0
    candidate_catastrophes = envelope_catastrophes = 0
    for candidate in candidates:
        seed, seat = int(candidate["seed"]), int(candidate["seat"])
        controls = [indexed[(name, seed, seat)] for name in CONTROLS]
        baseline = max(controls, key=lambda row: (float(row["margin"]), float(row["candidate_reward"])))
        selected_controls[str(baseline["decision_name"])] += 1
        margin_deltas.append(float(candidate["margin"]) - float(baseline["margin"]))
        own_deltas.append(float(candidate["candidate_reward"]) - float(baseline["candidate_reward"]))
        opponent_deltas.append(float(candidate["opponent_reward"]) - float(baseline["opponent_reward"]))
        candidate_wins += int(float(candidate["score"]) == 1.0)
        envelope_wins += int(any(float(row["score"]) == 1.0 for row in controls))
        candidate_catastrophes += int(bool(candidate["catastrophe"]))
        envelope_catastrophes += int(all(bool(row["catastrophe"]) for row in controls))
    return {
        "pairs": len(candidates),
        "mean_margin_delta": mean(margin_deltas),
        "mean_candidate_reward_delta": mean(own_deltas),
        "mean_opponent_reward_delta": mean(opponent_deltas),
        "delta_signs": [
            sum(value > 0 for value in margin_deltas),
            sum(value == 0 for value in margin_deltas),
            sum(value < 0 for value in margin_deltas),
        ],
        "candidate_vs_envelope_wins": [candidate_wins, envelope_wins],
        "candidate_vs_envelope_catastrophes": [candidate_catastrophes, envelope_catastrophes],
        "selected_control_counts": selected_controls,
    }


def analyze(reports: list[tuple[Path, Mapping[str, Any]]]) -> dict[str, Any]:
    execution_errors: list[str] = []
    for path, report in reports:
        if report.get("status") != "VALID":
            execution_errors.append(f"{path}: report is not VALID")
        summary = next(item for item in report["summaries"] if item["decision_name"] == CANDIDATE)
        if (
            int(summary["errors"])
            or int(summary["incomplete_games"])
            or int(summary["contract_violations"])
            or int(summary["terminal_procurement_count"])
            or int(summary["catastrophe_games"])
            or float(summary["p10_candidate_reward"]) < 10000.0
        ):
            execution_errors.append(f"{path}: candidate execution gate failed")
    opponents = {
        str(report["opponent"]["id"]): compare(report) for _, report in reports
    }
    passed = (
        not execution_errors
        and all(result["mean_margin_delta"] > 0 for result in opponents.values())
        and all(result["mean_candidate_reward_delta"] >= 0 for result in opponents.values())
        and all(result["delta_signs"][0] >= 10 for result in opponents.values())
        and all(
            result["candidate_vs_envelope_wins"][0]
            >= result["candidate_vs_envelope_wins"][1]
            for result in opponents.values()
        )
        and all(result["candidate_vs_envelope_catastrophes"][0] == 0 for result in opponents.values())
    )
    return {
        "schema": "kaggriculture-v114-poultry-stage-b-gate-v1",
        "status": "PASS_QUALIFIED_LOW_LEVEL_ENTERPRISE_EXPERT" if passed else "REJECT_STAGE_B",
        "passed": passed,
        "execution_errors": execution_errors,
        "opponents": opponents,
        "router_ppo_allowed": False,
        "router_ppo_reason": "one qualified new expert cannot form an MoE" if passed else "candidate failed Stage B",
        "gold_qualification": False,
        "source_reports": [
            {"path": str(path), "sha256": file_sha256(path)} for path, _ in reports
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="append", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    reports = [(path, json.loads(path.read_text())) for path in args.report]
    result = analyze(reports)
    atomic_json(args.output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
