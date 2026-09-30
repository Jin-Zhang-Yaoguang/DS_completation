"""Apply the preregistered Iteration 8 enterprise survival and scale gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from evaluate_event_program import atomic_json, file_sha256


ANIMAL_PROFILES = {"DAIRY_BERRY", "WOOL_MELON"}


def analyze(report: Mapping[str, Any]) -> dict[str, Any]:
    summaries = {str(item["decision_name"]): item for item in report["summaries"]}
    rows_by_profile: dict[str, list[Mapping[str, Any]]] = {}
    for row in report["rows"]:
        rows_by_profile.setdefault(str(row["decision_name"]), []).append(row)
    execution_errors: list[str] = []
    if report.get("status") != "VALID":
        execution_errors.append("campaign report is not VALID")
    results: dict[str, Any] = {}
    survivors: list[str] = []
    for profile, rows in sorted(rows_by_profile.items()):
        summary = summaries[profile]
        execution_passed = all(
            row.get("error") is None
            and row.get("statuses") == ["DONE", "DONE"]
            and int(row.get("contract_violations", 0)) == 0
            and int(row.get("terminal_procurement_count", 0)) == 0
            and not bool(row.get("catastrophe"))
            for row in rows
        )
        product_passed = all(int(row.get("distinct_products_sold", 0)) >= 2 for row in rows)
        animal_passed = profile not in ANIMAL_PROFILES or all(
            int(row.get("animal_product_sold", 0)) > 0 for row in rows
        )
        economic_passed = (
            int(summary["wdl"]["wins"]) >= 14
            and float(summary["p10_candidate_reward"]) >= 10000.0
            and float(summary["mean_candidate_reward"]) >= 18000.0
        )
        passed = execution_passed and product_passed and animal_passed and economic_passed
        results[profile] = {
            "passed": passed,
            "execution_passed": execution_passed,
            "product_diversity_passed": product_passed,
            "animal_product_passed": animal_passed,
            "economic_passed": economic_passed,
            "wins_draws_losses": [
                int(summary["wdl"]["wins"]),
                int(summary["wdl"]["draws"]),
                int(summary["wdl"]["losses"]),
            ],
            "mean_candidate_reward": float(summary["mean_candidate_reward"]),
            "p10_candidate_reward": float(summary["p10_candidate_reward"]),
            "minimum_distinct_products_sold": min(
                int(row.get("distinct_products_sold", 0)) for row in rows
            ),
            "minimum_animal_product_sold": min(
                int(row.get("animal_product_sold", 0)) for row in rows
            ),
        }
        if passed:
            survivors.append(profile)
    return {
        "schema": "kaggriculture-v114-enterprise-stage-a-gate-v1",
        "status": "PASS_STAGE_A" if len(survivors) >= 2 else "REJECT_STAGE_A",
        "execution_errors": execution_errors,
        "required_survivors": 2,
        "survivors": survivors,
        "profiles": results,
        "gold_qualification": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    result = analyze(report)
    result["source_report"] = {"path": str(args.report), "sha256": file_sha256(args.report)}
    atomic_json(args.output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
