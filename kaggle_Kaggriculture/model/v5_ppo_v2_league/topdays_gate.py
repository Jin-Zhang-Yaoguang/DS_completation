"""Acceptance report for the screened top-days residual candidate."""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np


DAYS = (12, 15, 18, 20, 23, 24, 28)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run(root=Path(".")):
    scan = read(root / "head_day_scan_v3_head3_2seed.json")
    action = read(root / "action_audit_topdays.json")
    evaluation = read(root / "evaluation_topdays_2000.json")
    pool = read(root / "evaluation_topdays_pool_64.json")
    v2 = read(root / "evaluation_topdays_v2_2000.json")
    v3 = read(root / "evaluation_topdays_v3_64.json")
    pool_large = read(root / "evaluation_topdays_pool_3996.json")
    selected = []
    for row in scan["rows_data"]:
        if int(row["day"]) in DAYS and int(row["head"]) == 3 and int(row["value"]) == 0:
            selected.append(float(row["margin_uplift"]))
    arr = np.asarray(selected, dtype=np.float64)
    rng = np.random.default_rng(20260819)
    draws = arr[rng.integers(0, len(arr), size=(5000, len(arr)))].mean(axis=1)
    scan_ci = [float(np.quantile(draws, .025)), float(np.quantile(draws, .975))]
    gates = {
        "selected_days_exact": tuple(DAYS) == tuple(sorted(DAYS)),
        "selected_interventions_n_ge_28": len(arr) >= 28,
        "selected_intervention_margin_ci_positive": len(arr) > 0 and scan_ci[0] > 0.0,
        "action_audit_zero_errors": int(action.get("errors", 1)) == 0,
        "action_change_rate_ge_5pct": float(action.get("actual_action_change_rate", 0.0)) >= 0.05,
        "main_2000_direct_score_gate": bool(evaluation.get("gates", {}).get("direct_score_rate_ge_53pct", False)),
        "main_2000_ci_gate": bool(evaluation.get("gates", {}).get("bootstrap_lower_gt_50pct", False)),
        "main_pool_better_than_v1": bool(evaluation.get("gates", {}).get("pool_composite_better_than_v1", False)),
        "main_pool_no_decline": bool(evaluation.get("gates", {}).get("no_opponent_decline_gt_2pp", False)),
        "large_pool_3996_no_decline": all(float(value.get("score_delta", -1.0)) >= -0.02 for value in pool_large.get("summary", {}).values()),
        "large_pool_3996_zero_errors": all(int(value.get("errors", 1)) == 0 for value in pool_large.get("summary", {}).values()),
        "v2_2000_zero_errors": int(v2["summary"]["v2"].get("errors", 1)) == 0,
        "v3_128_zero_errors": int(v3["summary"]["v3"].get("errors", 1)) == 0,
        "inference_lt_5ms": bool(evaluation.get("gates", {}).get("inference_lt_5ms", False)),
    }
    result = {
        "schema": "kaggriculture-ppo-v2-topdays-gate-1",
        "candidate": {"days": list(DAYS), "head": 3, "value": 0},
        "evidence": {
            "selected_intervention_n": int(len(arr)),
            "selected_intervention_mean_margin_uplift": float(arr.mean()) if len(arr) else None,
            "selected_intervention_bootstrap_ci95": scan_ci,
            "action_change_rate": action.get("actual_action_change_rate"),
            "paired_2000": evaluation.get("paired"),
            "pool_64": pool.get("summary"),
            "v2_2000": v2.get("summary", {}).get("v2"),
            "v3_128": v3.get("summary", {}).get("v3"),
            "pool_3996": pool_large.get("summary"),
        },
        "gates": gates,
        "passed": bool(all(gates.values())),
    }
    (root / "topdays_gate_report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
