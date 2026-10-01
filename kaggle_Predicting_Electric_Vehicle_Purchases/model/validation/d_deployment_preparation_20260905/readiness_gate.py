#!/usr/bin/env python3
"""PREPARATION_ONLY_NOT_AUTHORIZED: read-only admission check, never starts work."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LEGACY = ROOT.parent / "e2e_legacy_comparison_20260905"
EXPECTED = {
    "PREREGISTRATION_R01.md": "5d8ecfad981e7de6be27181c2d14f7ca962f68a954235917a5601bbc5f572388",
    "compare_legacy.py": "2ed1b0ec0bc889b7ec4a987ef59c450ab7ad4bf0479d715400e40a91487e40c6",
    "comparison_config.json": "67d375616576585dfe728fa2969ff96c6328513c0fd0f6618789bb637c9b76c1",
    "frozen_config.json": "cb164585d3bb50e5f8bc32d2c774cca9889ad124619b7275dcb86aba61c106d7",
}
TERMINAL_FILES = (
    "comparison_snapshot.json", "RUN_RESULT.json",
    "comparison/results.json", "comparison/independent_reconstruction.json",
    *(f"comparison/{stage}_{suffix}.json" for stage in ("assemble", "verify", "score")
      for suffix in ("STARTED", "RUN_RESULT", "PARENT_GUARD_READY")),
    *(f"comparison/{stage}.log" for stage in ("assemble", "verify", "score")),
)


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def digest(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), "not a regular file: " + str(path))
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for part in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def source_snapshot(directory, expected):
    """The production caller always supplies the constant EXPECTED mapping."""
    result = {}
    for name, wanted in expected.items():
        require(not Path(name).is_absolute() and ".." not in Path(name).parts, "unsafe source path")
        actual = digest(directory / name)
        require(actual == wanted, "frozen source drift: " + name)
        result[name] = actual
    return result


def positive_report(report):
    folds = report["folds"]
    require(len(folds) == 5 and [f["fold"] for f in folds] == [1, 2, 3, 4, 5],
            "five ordered validation folds required")
    for row in (report, *folds):
        for key in ("baseline_auc", "candidate_auc", "delta"):
            value = row[key]
            require(type(value) in (int, float) and math.isfinite(value), "invalid numeric AUC")
        require(0 <= row["baseline_auc"] <= 1 and 0 <= row["candidate_auc"] <= 1, "AUC out of range")
        require(abs(row["candidate_auc"] - row["baseline_auc"] - row["delta"]) <= 1e-12,
                "AUC delta mismatch")
    count = sum(f["delta"] > 0 for f in folds)
    require(type(report["positive_folds"]) is int and report["positive_folds"] == count,
            "positive fold count mismatch")
    return report["delta"] > 0 and count == 5


def qualification(result):
    """Validate the complete verifier's decision, not a user-supplied PASS flag."""
    required = {
        "status": "COMPLETE_LEGACY_COMPARISON_CONFIRMATION_ONLY",
        "candidate": "D", "baseline": "C", "primary_comparison": "D_MINUS_C",
        "selection_revision": "R01", "selected_candidate": "D",
    }
    for key, value in required.items():
        require(result.get(key) == value, "invalid completed comparison role: " + key)
    for key in ("requires_successful_score_stage_result", "candidate_rebuild_eligible",
                "B_minus_A_prerequisite_gate_passed", "D_minus_C_gate_passed"):
        require(result.get(key) is True, "comparison did not qualify: " + key)
    for key in ("allowed_for_submission", "actual_test_predictions_generated", "is_new_blind_test",
                "A_can_replace_D", "B_can_replace_D"):
        require(result.get(key) is False, "scope mismatch: " + key)
    require(positive_report(result["B_minus_A_recomputed"]), "B-A prerequisite failed")
    require(positive_report(result["D_minus_C"]), "D-C primary comparison failed")
    # +0.0001 remains a research classification. It is not an additional submission gate.
    research = result["D_minus_C"]["delta"] >= 0.0001
    require(result.get("D_minus_C_research_gate_passed") is research
            and result.get("research_promotion_gate_passed") is research, "research flag mismatch")
    return {"candidate": "D", "selected_candidate": "D", "baseline": "C",
            "candidate_rebuild_eligible": True, "eligible_to_define_actual_contract": True,
            "research_promotion_gate_passed": research, "execution_authorized": False,
            "allowed_for_submission": False}


def readiness():
    """No path arguments, fake backend, environment bypass, fitting, or file writes."""
    sources = source_snapshot(LEGACY, EXPECTED)
    missing = [name for name in TERMINAL_FILES if not (LEGACY / name).is_file()]
    if missing:
        return {"status": "NOT_READY", "missing": missing, "bound_sources": sources,
                "execution_authorized": False, "allowed_for_submission": False}
    before = {name: digest(LEGACY / name) for name in TERMINAL_FILES}
    spec = importlib.util.spec_from_file_location("s6e9_frozen_d_comparison", LEGACY / "compare_legacy.py")
    require(spec is not None and spec.loader is not None, "cannot load frozen comparison verifier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # This is the existing immutable, read-only final verifier. Never call verify_all/audit_inputs.
    result = module.require_successful_comparison()
    decision = qualification(result)
    after = {name: digest(LEGACY / name) for name in TERMINAL_FILES}
    require(before == after and sources == source_snapshot(LEGACY, EXPECTED), "evidence changed during read")
    return {"status": "VERIFIED_D_REBUILD_ELIGIBLE", **decision,
            "checked_at_utc": datetime.now(timezone.utc).isoformat(),
            "validator": "compare_legacy.require_successful_comparison",
            "bound_sources": sources, "terminal_artifacts": after,
            "readiness_gate_sha256": digest(Path(__file__)),
            "boundary": "This read-only result is not a deployment contract or start authorization. "
                        "Recheck live prerequisites when defining and starting the actual run."}


def main():
    require(len(sys.argv) == 1, "read-only gate accepts no execution or path arguments")
    try:
        result = readiness()
    except (ValueError, KeyError, FileNotFoundError) as exc:
        result = {"status": "REJECTED", "reason": str(exc),
                  "execution_authorized": False, "allowed_for_submission": False}
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if result["status"] == "VERIFIED_D_REBUILD_ELIGIBLE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
