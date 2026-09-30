"""Reproducibly evaluate the preregistered delayed-probe gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
import os
from typing import Any, Mapping

import numpy as np


def empirical_p10(values: list[float]) -> float:
    ordered = sorted(float(value) for value in values)
    return ordered[max(0, int(0.1 * (len(ordered) - 1)))] if ordered else 0.0


def analyze_reports(reports: list[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [row for report in reports for row in report["rows"]]
    groups: dict[tuple[str, int, int], list[np.ndarray]] = {}
    starter_rows: list[Mapping[str, Any]] = []
    for row in rows:
        features = np.asarray(row.get("probe_features"), dtype=np.float32)
        groups.setdefault(
            (str(row["opponent_id"]), int(row["seed"]), int(row["seat"])), []
        ).append(features)
        if row["opponent_id"] == "builtin:starter":
            starter_rows.append(row)

    representative = [vectors[0] for vectors in groups.values() if vectors]
    stack = np.stack(representative) if representative else np.empty((0, 0))
    route_equal = all(
        len(vectors) == 4
        and all(
            vector.shape == vectors[0].shape
            and np.array_equal(vector, vectors[0])
            for vector in vectors[1:]
        )
        for vectors in groups.values()
    )
    unique_vectors = len({vector.tobytes() for vector in representative})
    nonconstant_dimensions = (
        int(np.sum(np.ptp(stack, axis=0) > 0)) if len(representative) > 1 else 0
    )
    hard_execution = {
        "reports_valid": all(report.get("status") == "VALID" for report in reports),
        "errors_zero": all(row.get("error") is None for row in rows),
        "incomplete_games_zero": all(int(row.get("action_steps", 0)) == 719 for row in rows),
        "contract_violations_zero": all(int(row.get("contract_violations", 0)) == 0 for row in rows),
        "terminal_procurement_zero": all(int(row.get("terminal_procurement_count", 0)) == 0 for row in rows),
        "probe_steps_exact": all(int(row.get("probe_action_steps", 0)) == 24 for row in rows),
        "probe_features_present": all(
            isinstance(row.get("probe_features"), list)
            and len(row["probe_features"]) == 427
            for row in rows
        ),
    }
    survival = {
        "starter_catastrophe_rate": (
            sum(bool(row["catastrophe"]) for row in starter_rows) / len(starter_rows)
            if starter_rows
            else 1.0
        ),
        "starter_catastrophe_rate_max": 0.25,
        "combined_p10_candidate_reward": empirical_p10(
            [float(row["candidate_reward"]) for row in rows]
        ),
        "combined_p10_candidate_reward_min": 3000.0,
    }
    information = {
        "same_context_route_feature_equality": route_equal,
        "context_groups": len(groups),
        "unique_context_vectors": unique_vectors,
        "distinct_context_vectors_min": 2,
        "nonconstant_feature_dimensions": nonconstant_dimensions,
        "nonconstant_feature_dimensions_min": 1,
    }
    checks = {
        **hard_execution,
        "starter_catastrophe_rate_pass": survival["starter_catastrophe_rate"]
        <= survival["starter_catastrophe_rate_max"],
        "combined_p10_pass": survival["combined_p10_candidate_reward"]
        >= survival["combined_p10_candidate_reward_min"],
        "route_feature_equality_pass": route_equal,
        "distinct_context_vectors_pass": unique_vectors
        >= information["distinct_context_vectors_min"],
        "nonconstant_dimensions_pass": nonconstant_dimensions
        >= information["nonconstant_feature_dimensions_min"],
    }
    passed = all(checks.values())
    return {
        "schema": "kaggriculture-v114-delayed-probe-gate-report-v1",
        "status": "PASS_PROBE_GATE" if passed else "REJECT_PROBE_GATE",
        "strategy_proof": False,
        "gold_qualification": False,
        "rows": len(rows),
        "hard_execution": hard_execution,
        "survival": survival,
        "information": information,
        "checks": checks,
        "decision": (
            "Proceed to mixed-opponent delayed counterfactual collection."
            if passed
            else "Reject the probe and redesign before route training."
        ),
    }


def atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as sink:
        json.dump(payload, sink, ensure_ascii=False, indent=2, sort_keys=True)
        sink.write("\n")
        temporary = Path(sink.name)
    os.replace(temporary, path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    reports = [json.loads(path.read_text(encoding="utf-8")) for path in args.reports]
    result = analyze_reports(reports)
    atomic_json(args.output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
