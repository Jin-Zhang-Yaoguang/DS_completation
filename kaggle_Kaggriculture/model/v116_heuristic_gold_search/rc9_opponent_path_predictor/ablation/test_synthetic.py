#!/usr/bin/env python3
"""No-game checks for the RC9 preregistration and paired estimators."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile


HERE = Path(__file__).resolve().parent


def load_ablation():
    path = HERE / "ablation.py"
    spec = importlib.util.spec_from_file_location("rc9_ablation_under_test", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import ablation.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def result_row(variant, bank, rival, score, *, status="DONE", diagnostics=None):
    margin = bank - rival
    return {
        "task_id": f"{variant}__v21__1641819451__s0",
        "variant_id": variant,
        "opponent": "v21",
        "seed": 1641819451,
        "candidate_seat": 0,
        "status": status,
        "calls": 719 if status == "DONE" else 0,
        "candidate_schema_violations": 0,
        "opponent_schema_violations": 0,
        "candidate_bank": bank if status == "DONE" else None,
        "opponent_bank": rival if status == "DONE" else None,
        "margin": margin if status == "DONE" else None,
        "score": score if status == "DONE" else 0,
        "win": int(status == "DONE" and margin > 0),
        "tie": int(status == "DONE" and margin == 0),
        "loss": int(status == "DONE" and margin < 0),
        "first_shop": "PET_SHOP",
        "diagnostics": diagnostics or {
            "base_expert": "root", "path_leaf": variant,
            "path_candidate": variant, "stage_commits": {},
            "market_policy_counts": {},
        },
    }


def main():
    ablation = load_ablation()
    candidate = HERE / "synthetic_contract_fixture.py"

    core_manifest, core_tasks = ablation.plan(candidate, False, 8)
    fixed_manifest, fixed_tasks = ablation.plan(candidate, True, 8)
    assert core_manifest["planned_games"] == len(core_tasks) == 288
    assert fixed_manifest["planned_games"] == len(fixed_tasks) == 504
    assert core_manifest["r3_exposed_seeds"] == list(ablation.EXPECTED_R3_SEEDS)
    assert core_manifest["gold_opponents"] == list(ablation.EXPECTED_GOLD)
    assert len({task["task_id"] for task in fixed_tasks}) == 504
    assert len({task["cache_key"] for task in fixed_tasks}) == 504
    assert len(set(fixed_manifest["source_hashes"]["variants"].values())) == 7
    fixed_specs = [spec for spec in fixed_manifest["variants"]
                   if spec["variant_id"].startswith("fixed_")]
    assert all(spec["target_predictor"] and spec["market_predictor"]
               for spec in fixed_specs)

    with tempfile.TemporaryDirectory(prefix="rc9_ablation_plan_") as temporary:
        output = Path(temporary) / "plan"
        ablation.write_plan(output, core_manifest, core_tasks)
        reread, frozen = ablation.verify_preregistered(
            output / "preregistered_manifest.json", output / "tasks.json",
        )
        assert reread["task_plan_sha256"] == core_manifest["task_plan_sha256"]
        assert len(frozen) == 288

    rows = [
        result_row("base", 100, 90, 1.0),
        result_row("target_only", 110, 88, 1.0),
        result_row("market_only", 105, 93, 1.0),
        result_row("full", 121, 85, 1.0),
    ]
    pairs = ablation.paired_rows(rows, ablation.CORE_VARIANTS)
    assert len(pairs) == 3
    assert next(row for row in pairs if row["variant_id"] == "full")["candidate_bank_delta"] == 21
    synergy = ablation.synergy_rows(rows)
    assert len(synergy) == 1
    assert synergy[0]["candidate_bank_synergy"] == 6
    assert synergy[0]["opponent_bank_synergy"] == -6
    assert synergy[0]["margin_synergy"] == 12
    assert synergy[0]["score_synergy"] == 0
    coverage = ablation.path_coverage(rows, ablation.CORE_VARIANTS)
    assert all(value["coverage_complete"] for value in coverage.values())
    assert all(value["base_expert"] == {"root": 1}
               for value in coverage.values())

    error = result_row("base", 0, 0, 0.0, status="ERROR")
    aggregate = ablation.aggregate([rows[0], error])
    assert aggregate["planned_games"] == 2
    assert aggregate["completed_games"] == 1
    assert aggregate["errors_as_nonwins"] == 1
    assert aggregate["pure_win_rate_planned"] == 0.5
    assert aggregate["all_719_calls"] is False

    report = {
        "status": "PASS",
        "games_executed": 0,
        "core_planned_games": len(core_tasks),
        "fixed_planned_games": len(fixed_tasks),
        "exact_seeds": core_manifest["r3_exposed_seeds"],
        "gold_opponents": len(core_manifest["gold_opponents"]),
        "core_variant_hashes": core_manifest["source_hashes"]["variants"],
        "fixed_variant_hashes_unique": len(set(fixed_manifest["source_hashes"]["variants"].values())),
        "paired_rows_checked": len(pairs),
        "synergy_rows_checked": len(synergy),
        "error_retained_in_denominator": True,
        "preregister_round_trip": True,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
