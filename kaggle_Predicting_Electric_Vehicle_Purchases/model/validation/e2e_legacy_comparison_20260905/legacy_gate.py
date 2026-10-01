"""Read-only authorization and completed A/B evidence checks for legacy C."""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path


def need(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def prerequisite_paths():
    paths = ["orchestration/config.json", "orchestration/STARTED.json", "orchestration/state.json",
             "e2e_results.json", "independent_reconstruction.json", "cache_snapshot.json",
             "assembly_config.json", "frozen_config.json", "splits.npz", "supervisor_state.json", "cpu_budget.json",
             "gpu/remote_output/ARCHIVE_VERIFICATION.json", "gpu/remote_output/GPU_RUN_RESULT.json",
             "gpu/remote_output/ct_cache/GPU_COMPLETE.json", "gpu/PUSH_RECEIPT.json",
             "gpu/revision_01/frozen_config.json", "gpu/revision_01/bundle_manifest.json"]
    for stage in ("archive", "audit", "assemble", "score"):
        paths += [f"orchestration/{stage}_COMPLETE.json", f"orchestration/{stage}.log"]
    for outer in range(1, 6):
        paths += [f"assembled/outer_{outer:02d}/predictions.npz", f"assembled/outer_{outer:02d}/manifest.json"]
    return paths


def validate_gate_results(result, independent, state, started, expected_rows):
    need(state.get("status") == "SCORE_READY_FOR_REVIEW" and state.get("pid") == started.get("pid"), "A/B pipeline not successfully complete")
    need(state.get("actual_test_predictions") is False and state.get("competition_submission") is False, "A/B pipeline scope drift")
    need(result.get("status") == "COMPLETE_E2E_CONFIRMATION_ONLY", "A/B endpoint incomplete")
    need(result.get("baseline") == "V100_E2E_CT_FULLREFIT" and result.get("candidate") == "V100_E2E_CT_FOLDMEAN", "A/B roles changed")
    for field in ("independent_reconstruction_passed", "submission_candidate_rebuild_gate_passed"):
        need(result.get(field) is True, "A/B prerequisite gate missing")
    for field in ("allowed_for_submission", "actual_test_predictions_generated", "is_new_blind_test"):
        need(result.get(field) is False, "A/B scope flag drift")
    rows = result.get("folds", [])
    need(len(rows) == 5 and {r.get("fold") for r in rows} == set(range(1, 6)), "A/B requires five distinct outer folds")
    need(result.get("positive_folds") == 5, "A/B is not 5/5 positive")
    need(result.get("n_rows") == sum(expected_rows.values()), "A/B total row count mismatch")
    for row in [result, *rows]:
        a, b, delta = (row.get(k) for k in ("baseline_auc", "candidate_auc", "delta"))
        need(all(number(v) for v in (a, b, delta)) and 0 <= a <= 1 and 0 <= b <= 1 and delta > 0, "A/B nonpositive or invalid endpoint")
        need(abs((b - a) - delta) <= 1e-12, "A/B delta inconsistent with AUCs")
    for row in rows:
        need(row.get("rows") == expected_rows[row["fold"]], "A/B outer row count mismatch")
    need(independent.get("status") == "INDEPENDENT_RECONSTRUCTION_PASS_UNSCORED" and independent.get("outer_labels_scored") is False, "A/B independent reconstruction incomplete")
    checks = independent.get("outer_rows", [])
    need(len(checks) == 5 and {row.get("outer") for row in checks} == set(range(1, 6)), "A/B reconstruction outer coverage")
    for row in checks:
        errors = row.get("max_abs_errors", {})
        need(set(errors) == {"baseline_proba", "candidate_proba"}, "A/B reconstruction schema")
        need(all(number(v) and 0 <= v <= 1e-12 for v in errors.values()), "A/B reconstruction error")


def validate_authorization(auth, config_sha):
    need(auth.get("schema_version") == 1 and auth.get("action") == "START_LEGACY_C_ONCE" and auth.get("authorized_by") == "parent", "parent start authorization missing")
    need(auth.get("config_sha256") == config_sha, "authorization binds another C config")
    need(number(auth.get("created_unix")) and auth["created_unix"] > 0, "authorization timestamp invalid")
    need(set(auth.get("prerequisite_files", {})) == set(prerequisite_paths()), "authorization prerequisite whitelist mismatch")


def verify_authorized_ab(root, config_sha, expected_rows, ab):
    """No training, no score recomputation, no writing A/B verification receipts."""
    root = Path(root)
    auth_path = root / "START_AUTHORIZATION.json"
    auth = read(auth_path)
    validate_authorization(auth, config_sha)
    base = ab.OUT
    for name, digest in auth["prerequisite_files"].items():
        need(sha(base / name) == digest, "authorized prerequisite SHA changed: " + name)
    ab.config()  # source checks only; never ab.verify_all()/audit_all().
    pipeline = read(base / "orchestration/config.json")
    for name, digest in pipeline["sources"].items():
        need(sha(base / name) == digest, "A/B pipeline frozen source drift")
    need(pipeline["version"] == 1, "A/B GPU version changed")
    started = read(base / "orchestration/STARTED.json")
    need(started["config_sha256"] == sha(base / "orchestration/config.json"), "A/B pipeline start config drift")
    state = read(base / "orchestration/state.json")
    need(number(state.get("seconds")) and 0 <= state["seconds"] < pipeline["pipeline_seconds"], "A/B pipeline final budget")
    for stage in ("archive", "audit", "assemble", "score"):
        marker = read(base / f"orchestration/{stage}_COMPLETE.json")
        limit = pipeline["download_seconds"] if stage == "archive" else pipeline["stage_seconds"]
        need(marker["status"] == "COMPLETE" and number(marker["elapsed"]) and 0 <= marker["elapsed"] < limit, "A/B stage completion/budget")
        need(number(marker["peak_rss_bytes"]) and 0 <= marker["peak_rss_bytes"] <= pipeline["stage_memory_bytes"], "A/B stage RSS budget")
        need(marker["log_sha256"] == sha(base / f"orchestration/{stage}.log"), "A/B stage log drift")
    result = read(base / "e2e_results.json")
    independent = read(base / "independent_reconstruction.json")
    validate_gate_results(result, independent, state, started, expected_rows)
    need(result["independent_reconstruction_sha256"] == sha(base / "independent_reconstruction.json"), "A/B independent receipt changed")
    for record in (result, independent):
        need(record["assembly_config_sha256"] == sha(base / "assembly_config.json") and record["cache_snapshot_sha256"] == sha(base / "cache_snapshot.json"), "A/B endpoint provenance drift")
    snapshot = read(base / "cache_snapshot.json")
    required = {str(path.relative_to(base)) for path in ab.required_files()}
    need(snapshot["status"] == "ALL_15_CACHES_REBUILT_UNSCORED" and set(snapshot["files"]) == required, "A/B complete cache snapshot coverage")
    need(snapshot["assembly_config_sha256"] == sha(base / "assembly_config.json"), "A/B snapshot config drift")
    for name, digest in snapshot["files"].items():
        need(sha(base / name) == digest, "A/B cache source changed")
    ab.require_supervisors(read(base / "supervisor_state.json"), read(base / "cpu_budget.json"), read(base / "gpu/remote_output/GPU_RUN_RESULT.json"), sha(base / "frozen_config.json"))
    for row in independent["outer_rows"]:
        folder = base / f"assembled/outer_{row['outer']:02d}"
        need(sha(folder / "predictions.npz") == row["prediction_sha256"] and sha(folder / "manifest.json") == row["manifest_sha256"], "A/B independent output SHA drift")
        manifest = read(folder / "manifest.json")
        need(manifest["prediction_sha256"] == row["prediction_sha256"] and manifest["outer_hold_labels_used"] is False, "A/B assembled scope drift")
        need(manifest["assembly_config_sha256"] == result["assembly_config_sha256"] and manifest["cache_snapshot_sha256"] == result["cache_snapshot_sha256"], "A/B assembled provenance drift")
    archive = read(base / "gpu/remote_output/ARCHIVE_VERIFICATION.json")
    need(archive["verification"]["status"] == "VERIFIED_GPU_CACHE_UNSCORED", "GPU archive not verified")
    need(archive["binding"]["config_sha256"] == sha(base / "gpu/revision_01/frozen_config.json") and archive["binding"]["push_receipt_sha256"] == sha(base / "gpu/PUSH_RECEIPT.json"), "GPU archive revision binding")
    for name, digest in archive["verification"]["file_sha256"].items():
        path = Path(name)
        need(not path.is_absolute() and ".." not in path.parts, "GPU archive path escapes output")
        need(sha(base / "gpu/remote_output" / path) == digest, "GPU archive content changed")
    return {"authorization_sha256": sha(auth_path), "ab_result_sha256": sha(base / "e2e_results.json"), "prerequisite_files": auth["prerequisite_files"]}
