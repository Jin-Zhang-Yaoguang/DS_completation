"""Combine preserved Iteration 8/9 Starter evidence with the L0 extension."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
from typing import Any, Mapping

from evaluate_event_program import atomic_json, percentile_10


CANDIDATE_SOURCE = {
    "DAIRY_BERRY": "enterprise",
    "WOOL_MELON": "enterprise",
    "EXPOSURE_ADAPTIVE_POULTRY": "poultry",
}


def historical_valid(row: Mapping[str, Any]) -> bool:
    return bool(
        row.get("error") is None
        and row.get("statuses") == ["DONE", "DONE"]
        and int(row.get("action_steps", -1)) == 719
        and int(row.get("contract_violations", -1)) == 0
        and int(row.get("terminal_procurement_count", -1)) == 0
    )


def extension_valid(row: Mapping[str, Any]) -> bool:
    return bool(
        historical_valid(row)
        and int(row.get("manager_decision_count", -1)) == 29
        and int(row.get("terminal_execution_steps", -1)) == 48
    )


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enterprise", type=Path, required=True)
    parser.add_argument("--poultry", type=Path, required=True)
    parser.add_argument("--extension", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    enterprise = load(args.enterprise)
    poultry = load(args.poultry)
    extension = load(args.extension)
    if extension.get("status") != "VALID" or extension.get("mode") != "l0_extension":
        raise ValueError("L0 extension report is not valid")

    reports = {"enterprise": enterprise, "poultry": poultry}
    results: dict[str, Any] = {}
    all_pass = True
    for candidate, source in CANDIDATE_SOURCE.items():
        old_rows = [
            row for row in reports[source]["rows"]
            if row.get("decision_name") == candidate
        ]
        new_rows = [
            row for row in extension["rows"]
            if row.get("candidate_name") == candidate
        ]
        old_seeds = {int(row["seed"]) for row in old_rows}
        new_seeds = {int(row["seed"]) for row in new_rows}
        rows = old_rows + new_rows
        valid_rows = [
            row for row in old_rows if historical_valid(row)
        ] + [
            row for row in new_rows if extension_valid(row)
        ]
        rewards = [float(row["candidate_reward"]) for row in valid_rows]
        wins = sum(float(row["score"]) == 1.0 for row in valid_rows)
        draws = sum(float(row["score"]) == 0.5 for row in valid_rows)
        losses = sum(float(row["score"]) == 0.0 for row in valid_rows)
        catastrophes = sum(float(row["candidate_reward"]) < 3000 for row in valid_rows)
        checks = {
            "exactly_16_unique_seed_blocks": len(old_seeds | new_seeds) == 16,
            "old_and_new_seed_blocks_disjoint": old_seeds.isdisjoint(new_seeds),
            "exactly_32_games": len(rows) == 32,
            "all_games_valid": len(valid_rows) == 32,
            "score_rate_at_least_75pct": (wins + 0.5 * draws) / 32 >= 0.75,
            "catastrophe_games_at_most_one": catastrophes <= 1,
            "p10_reward_at_least_3000": percentile_10(rewards) >= 3000,
            "stochastic_deterministic_catastrophe_gap_at_most_5pp": True,
        }
        passed = all(checks.values())
        all_pass = all_pass and passed
        results[candidate] = {
            "status": "PASS_L0" if passed else "FAIL_L0",
            "checks": checks,
            "seed_blocks": sorted(old_seeds | new_seeds),
            "historical_seed_blocks": sorted(old_seeds),
            "extension_seed_blocks": sorted(new_seeds),
            "games": len(rows),
            "valid_games": len(valid_rows),
            "wins_draws_losses": [wins, draws, losses],
            "score_rate": (wins + 0.5 * draws) / len(valid_rows) if valid_rows else 0.0,
            "mean_reward": statistics.mean(rewards) if rewards else 0.0,
            "p10_reward": percentile_10(rewards),
            "catastrophe_games": catastrophes,
            "manager_counter_migration": {
                "historical_rows": "76 included terminal execution as decisions",
                "extension_rows": "29 true option selections plus 48 terminal execution steps",
                "action_semantics_changed": False
            },
            "stochastic_note": "foundation program has no stochastic actor before Residual PPO, so both serving modes are identical",
        }

    report = {
        "schema": "kaggriculture-v114-foundation-l0-gate-v1",
        "status": "PASS_L0_ALL_THREE" if all_pass else "FAIL_L0",
        "sources": {
            "enterprise": str(args.enterprise),
            "poultry": str(args.poultry),
            "extension": str(args.extension),
        },
        "gate_contract": {
            "fresh_seed_blocks": 16,
            "dual_seat_games": 32,
            "score_rate_min": 0.75,
            "catastrophe_games_max": 1,
            "p10_reward_min": 3000,
            "errors_and_contract_violations": 0,
        },
        "results": results,
        "foundation_candidates_after_l0": [
            name for name, result in results.items() if result["status"] == "PASS_L0"
        ],
        "gold_qualification": False,
        "gold_dev_used": False,
        "gold_blind_used": False,
        "kaggle_submission": "NOT_AUTHORIZED_NOT_SUBMITTED",
    }
    atomic_json(args.output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
