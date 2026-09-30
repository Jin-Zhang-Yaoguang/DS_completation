"""Deterministic acceptance check for the paired residual candidate.

The PPO pilot may discover a policy that is mostly the frozen V1 policy.  This
small checker keeps the residual intervention separately auditable: a residual
is accepted only when the same candidate is present in the counterfactual
report, changes enough executable actions, and wins the paired V1 evaluation.
It intentionally does not edit ``main.py`` or mutate any checkpoint.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import main


def _read(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} is not a JSON object")
    return value


def run(counterfactual: Path, action_audit: Path, evaluation: Path, output: Path) -> dict:
    cf = _read(counterfactual)
    audit = _read(action_audit)
    evaluation_report = _read(evaluation)
    key = f"head{int(main.SAFE_RESIDUAL_HEAD)}_value{int(main.SAFE_RESIDUAL_VALUE)}"
    summary = cf.get("summary", {}).get(key, {})
    ci = list(summary.get("bootstrap_ci95", []))
    paired = evaluation_report.get("paired", {})
    paired_ci = list(paired.get("bootstrap_95_ci", []))
    gates = {
        "counterfactual_schema": cf.get("schema") == "kaggriculture-ppo-v2-counterfactual-audit-1",
        "counterfactual_zero_errors": int(cf.get("errors", 1)) == 0,
        "selected_intervention_present": len(ci) == 2 and int(summary.get("n", 0)) >= 32,
        "selected_intervention_ci_lower_positive": len(ci) == 2 and float(ci[0]) > 0.0,
        "action_audit_zero_errors": int(audit.get("errors", 1)) == 0,
        "action_change_rate_ge_5pct": float(audit.get("actual_action_change_rate", 0.0)) >= 0.05,
        "evaluation_paired_score_ge_53pct": float(paired.get("score_rate", 0.0)) >= 0.53,
        "evaluation_bootstrap_lower_gt_50pct": len(paired_ci) == 2 and float(paired_ci[0]) > 0.50,
        "evaluation_pool_better_than_v1": bool(evaluation_report.get("gates", {}).get("pool_composite_better_than_v1", False)),
        "evaluation_no_opponent_decline": bool(evaluation_report.get("gates", {}).get("no_opponent_decline_gt_2pp", False)),
        "inference_lt_5ms": bool(evaluation_report.get("gates", {}).get("inference_lt_5ms", False)),
    }
    result = {
        "schema": "kaggriculture-ppo-v2-residual-gate-1",
        "candidate": {
            "days": [int(day) for day in main.SAFE_RESIDUAL_DAYS],
            "head": int(main.SAFE_RESIDUAL_HEAD),
            "value": int(main.SAFE_RESIDUAL_VALUE),
            "key": key,
        },
        "evidence": {
            "counterfactual_n": int(summary.get("n", 0)),
            "counterfactual_mean_uplift": summary.get("mean_uplift"),
            "counterfactual_ci95": ci,
            "action_change_rate": audit.get("actual_action_change_rate"),
            "paired_score_rate": paired.get("score_rate"),
            "paired_ci95": paired_ci,
        },
        "gates": gates,
        "passed": bool(all(gates.values())),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--counterfactual", type=Path, default=root / "counterfactual_audit_report.json")
    parser.add_argument("--action-audit", type=Path, default=root / "action_audit_residual.json")
    parser.add_argument("--evaluation", type=Path, default=root / "evaluation_residual.json")
    parser.add_argument("--output", type=Path, default=root / "residual_gate_report.json")
    args = parser.parse_args()
    print(json.dumps(run(args.counterfactual, args.action_audit, args.evaluation, args.output), ensure_ascii=False, indent=2))
