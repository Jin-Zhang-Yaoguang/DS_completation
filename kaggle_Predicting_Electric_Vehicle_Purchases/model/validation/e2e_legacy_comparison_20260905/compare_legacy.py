#!/usr/bin/env python3
"""旧算法 C 的完整缓存对照；R01 固定 D 唯一候选，没有实际 test 或提交入口。"""
from __future__ import annotations
import os
THREAD_KEYS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
               "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS")
for _name in THREAD_KEYS:
    os.environ[_name] = "2"
import argparse
import fcntl
import hashlib
import importlib.util
import json
import signal
import subprocess
import sys
import time
from pathlib import Path
import numpy as np
import pandas as pd
import psutil
from sklearn.metrics import roc_auc_score
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
AB_ROOT = ROOT.parent / "e2e_v100_20260905"
OUTPUT = ROOT / "comparison"
WALL = 1800.0
MEMORY = 16 * 1024**3
EXPECTED_AB_ASSEMBLER = "edc5c90e7e7cd708b25f2159abe84b881e8278d0471e4435868f4300ffc85e4f"
EXPECTED_SHARED_AUC = "3ef014613e5bdc2754dd42e1a60cece23e81b888043d6d2cfc71de3d7a52d550"
EXPECTED_SELECTION_R01 = "5d8ecfad981e7de6be27181c2d14f7ca962f68a954235917a5601bbc5f572388"
_MODULES = None


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(path):
    path = Path(path)
    need(path.is_file() and not path.is_symlink(), "missing regular file: " + str(path))
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path):
    sha(path)
    return json.loads(Path(path).read_text(), parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    with tmp.open("x") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def immutable_json(path, value):
    if Path(path).exists():
        need(read_json(path) == value, "existing evidence differs: " + str(path))
    else:
        write_json(path, value)


def publish_json_once(path, value):
    """完整 JSON 原子发布；hard link 的目标已存在时失败，不覆盖旧证据。"""
    path = Path(path)
    tmp = path.with_name(path.name + f".publish.{os.getpid()}.tmp")
    with tmp.open("x") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.link(tmp, path)
    finally:
        tmp.unlink()


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def modules():
    global _MODULES
    if _MODULES is None:
        need(sha(AB_ROOT / "assemble_e2e.py") == EXPECTED_AB_ASSEMBLER, "shared assembler drift")
        need(sha(PROJECT / "model/research_runtime/paired_auc.py") == EXPECTED_SHARED_AUC, "shared AUC drift")
        sys.path.insert(0, str(AB_ROOT))
        sys.path.insert(0, str(ROOT))
        ab = load_module(AB_ROOT / "assemble_e2e.py", "legacy_comparison_ab")
        legacy = load_module(ROOT / "legacy_cpu.py", "legacy_comparison_cpu")
        archive = load_module(AB_ROOT / "gpu/archive_remote.py", "legacy_comparison_archive")
        auc = load_module(PROJECT / "model/research_runtime/paired_auc.py", "legacy_comparison_auc")
        for key in THREAD_KEYS:
            os.environ[key] = "2"
        _MODULES = ab, legacy, archive, auc
    return _MODULES


def static_sources():
    return [Path(__file__), ROOT / "test_compare_legacy.py", ROOT / "COMPARISON_NOTES.md",
            ROOT / "COMPARISON_REVIEW.json",
            ROOT / "PREREGISTRATION.md", ROOT / "PREREGISTRATION_R01.md", ROOT / "selection_revision.json",
            ROOT / "legacy_cpu.py", ROOT / "legacy_gate.py", ROOT / "frozen_config.json",
            AB_ROOT / "assemble_e2e.py", AB_ROOT / "assembly_config.json", AB_ROOT / "cpu_runner.py",
            AB_ROOT / "frozen_config.json", AB_ROOT / "splits.npz",
            AB_ROOT / "orchestration/config.json", AB_ROOT / "orchestration/pipeline.py",
            AB_ROOT / "gpu/archive_remote.py", AB_ROOT / "gpu/PUSH_RECEIPT.json",
            AB_ROOT / "gpu/revision_01/frozen_config.json", AB_ROOT / "gpu/revision_01/bundle_manifest.json",
            PROJECT / "model/research_runtime/paired_auc.py"]


def freeze_evidence():
    test = read_json(ROOT / "comparison_test_results.json")
    need(test["status"] == "PASS" and test["real_scores_computed"] is False
         and type(test["tests_run"]) is int and test["tests_run"] >= 23
         and test["failures"] == 0 and test["errors"] == 0 and test["skipped"] == 0,
         "complete synthetic tests not passed")
    need(set(test["code_sha256"]) == {"compare_legacy.py", "test_compare_legacy.py"}, "test source closure incomplete")
    for name, digest in test["code_sha256"].items():
        need(sha(ROOT / name) == digest, "stale comparison tests")
    need(test["selection_preregistration_sha256"] == sha(ROOT / "PREREGISTRATION_R01.md") == EXPECTED_SELECTION_R01,
         "test selection contract drift")
    need(test["log_sha256"] == sha(ROOT / "comparison_self_test_log.txt"), "test log drift")
    need(test["guard_source_sha256"] == sha(ROOT / "legacy_cpu.py"), "tested parent guard source drift")
    review = read_json(ROOT / "COMPARISON_REVIEW.json")
    reviewed = ("compare_legacy.py", "test_compare_legacy.py", "COMPARISON_NOTES.md", "PREREGISTRATION_R01.md")
    need(review["status"] == "PASS" and review["reviewed_by"] == "parent"
         and review["real_scores_computed"] is False, "independent root review missing")
    need(review["source_sha256"] == {name: sha(ROOT / name) for name in reviewed}, "independent comparison review stale")
    need(review["synthetic_test_sha256"] == sha(ROOT / "comparison_test_results.json"), "review test evidence stale")


def freeze():
    dest = ROOT / "comparison_config.json"
    need(not dest.exists() and not OUTPUT.exists(), "comparison already frozen or started")
    freeze_evidence()
    ab, _, _, _ = modules()
    ab.config()
    need(sha(ROOT / "PREREGISTRATION_R01.md") == EXPECTED_SELECTION_R01, "R01 selection contract drift")
    cfg = {"experiment_id": "E2E_LEGACY_COMPARISON_20260905", "candidate": "D", "baseline": "C",
           "explanatory_only": ["A_MINUS_C", "B_MINUS_C"], "primary_comparison": "D_MINUS_C",
           "prerequisite_comparison": "B_MINUS_A", "research_gate_applies_to": "D_MINUS_C",
           "required_positive_folds": 5, "candidate_delta_strictly_above": 0.0,
           "research_delta": 0.0001, "wall_seconds_per_stage": WALL, "memory_bytes": MEMORY,
           "threads": 2, "is_new_blind_test": False, "actual_test_predictions_generated": False,
           "allowed_for_submission": False,
           "sources": {str(p.relative_to(PROJECT)): sha(p) for p in static_sources()},
           "synthetic_test_sha256": sha(ROOT / "comparison_test_results.json")}
    write_json(dest, cfg)
    return {"status": "COMPARISON_FROZEN_UNSCORED", "sha256": sha(dest)}


def check_config():
    freeze_evidence()
    cfg = read_json(ROOT / "comparison_config.json")
    need((cfg["candidate"], cfg["baseline"], cfg["primary_comparison"], cfg["explanatory_only"]) ==
         ("D", "C", "D_MINUS_C", ["A_MINUS_C", "B_MINUS_C"]), "fixed comparison roles drift")
    need(cfg["prerequisite_comparison"] == "B_MINUS_A" and cfg["research_gate_applies_to"] == "D_MINUS_C",
         "R01 prerequisite/research gate drift")
    need(sha(ROOT / "PREREGISTRATION_R01.md") == EXPECTED_SELECTION_R01, "R01 selection contract drift")
    need(cfg["required_positive_folds"] == 5 and cfg["candidate_delta_strictly_above"] == 0.0
         and cfg["research_delta"] == .0001, "fixed thresholds drift")
    need(cfg["wall_seconds_per_stage"] == WALL and cfg["memory_bytes"] == MEMORY and cfg["threads"] == 2,
         "comparison budget drift")
    need(cfg["allowed_for_submission"] is False and cfg["actual_test_predictions_generated"] is False,
         "submission boundary drift")
    need(cfg["is_new_blind_test"] is False, "blind-test boundary drift")
    need(set(cfg["sources"]) == {str(p.relative_to(PROJECT)) for p in static_sources()}, "source closure incomplete")
    for name, digest in cfg["sources"].items():
        need(not Path(name).is_absolute() and ".." not in Path(name).parts, "invalid source path")
        need(sha(PROJECT / name) == digest, "comparison source drift: " + name)
    need(sha(ROOT / "comparison_test_results.json") == cfg["synthetic_test_sha256"], "test evidence drift")
    return cfg


def required_files():
    files = [ROOT / name for name in ("frozen_config.json", "START_AUTHORIZATION.json", "RUN_STARTED.json",
             "RUN_RESULT.json", "supervisor_state.json", "cpu_budget.json")]
    files += [AB_ROOT / name for name in ("e2e_results.json", "independent_reconstruction.json",
              "cache_snapshot.json", "orchestration/config.json", "orchestration/STARTED.json",
              "orchestration/state.json", "gpu/remote_output/ARCHIVE_VERIFICATION.json",
              "gpu/remote_output/GPU_RUN_RESULT.json", "gpu/remote_output/ct_cache/GPU_COMPLETE.json")]
    for mode in ("archive", "audit", "assemble", "score"):
        files += [AB_ROOT / f"orchestration/{mode}_COMPLETE.json", AB_ROOT / f"orchestration/{mode}.log"]
    for outer in range(1, 6):
        for base in (ROOT, AB_ROOT):
            for family in ("v80", "v85"):
                folder = base / f"outer_{outer:02d}" / family
                files += [folder / "cache.npz", folder / "cache_manifest.json"]
                for atom in range(1, 41):
                    files += [folder / f"atom_{atom:02d}" / name for name in
                              ("model.txt", "predictions.npz", "manifest.json")]
        gpu = AB_ROOT / f"gpu/remote_output/ct_cache/outer_{outer:02d}"
        files += [gpu / "cache.npz", gpu / "cache_manifest.json", gpu / "fullfit.npz", gpu / "fullfit.json"]
        for atom in range(1, 6):
            files += [gpu / f"atom_{atom:02d}.{ext}" for ext in ("npz", "json")]
        files += [AB_ROOT / f"assembled/outer_{outer:02d}/{name}" for name in ("predictions.npz", "manifest.json")]
    return files


def missing_files():
    return [str(p.relative_to(PROJECT)) for p in required_files() if not p.is_file()]


def insist_complete():
    missing = missing_files()
    if missing:
        raise FileNotFoundError("NOT_READY: " + ", ".join(missing))


def report_gate(report, threshold=0.0, strict=True):
    rows = report["folds"]
    need(len(rows) == 5 and [r["fold"] for r in rows] == [1, 2, 3, 4, 5], "all five ordered folds required")
    for row in [report, *rows]:
        need(all(np.isfinite(row[k]) for k in ("baseline_auc", "candidate_auc", "delta")), "nonfinite AUC report")
        need(0 <= row["baseline_auc"] <= 1 and 0 <= row["candidate_auc"] <= 1, "invalid AUC report")
        need(abs(row["delta"] - (row["candidate_auc"] - row["baseline_auc"])) <= 1e-12, "inconsistent AUC delta")
    positive = sum(r["delta"] > 0 for r in rows)
    need(report["positive_folds"] == positive, "positive-fold count mismatch")
    return bool((report["delta"] > threshold if strict else report["delta"] >= threshold) and positive == 5)


def decisions(ba, dc, bc, ac, independently_rebuilt):
    need(independently_rebuilt is True, "independent reconstruction required")
    ga, gd = report_gate(ba), report_gate(dc)
    report_gate(bc)
    report_gate(ac)  # Explanatory comparisons never change the selected candidate.
    rd = report_gate(dc, .0001, False)
    return {"B_minus_A_prerequisite_gate_passed": ga, "D_minus_C_gate_passed": gd,
            "candidate_rebuild_eligible": ga and gd, "selected_candidate": "D" if ga and gd else None,
            "A_minus_C_explanatory_only": True, "B_minus_C_explanatory_only": True,
            "A_can_replace_D": False, "B_can_replace_D": False,
            "D_minus_C_research_gate_passed": rd, "research_promotion_gate_passed": ga and rd,
            "allowed_for_submission": False, "actual_test_predictions_generated": False}


def require_ab_terminal(state, started, pipeline_config, score):
    need(state["status"] == "SCORE_READY_FOR_REVIEW" and state["pid"] == started["pid"], "AB pipeline not finally successful")
    need(np.isfinite(state["seconds"]) and 0 <= state["seconds"] < pipeline_config["pipeline_seconds"] == 15 * 3600,
         "AB pipeline final budget invalid")
    need(state["actual_test_predictions"] is False and state["competition_submission"] is False, "AB action boundary invalid")
    need(score["status"] == "COMPLETE_E2E_CONFIRMATION_ONLY" and score["baseline"] == "V100_E2E_CT_FULLREFIT"
         and score["candidate"] == "V100_E2E_CT_FOLDMEAN", "AB identities invalid")
    need(score["independent_reconstruction_passed"] is True and score["allowed_for_submission"] is False
         and score["actual_test_predictions_generated"] is False, "AB independent/submission boundary invalid")
    need(report_gate(score) and score["submission_candidate_rebuild_gate_passed"] is True, "B-A prerequisite gate failed")


def checked_context():
    insist_complete()  # Must run before loading any arrays or labels.
    check_config()
    ab, legacy, archive, _ = modules()
    pc = read_json(AB_ROOT / "orchestration/config.json")
    ps = read_json(AB_ROOT / "orchestration/STARTED.json")
    state = read_json(AB_ROOT / "orchestration/state.json")
    ba = read_json(AB_ROOT / "e2e_results.json")
    need(ps["config_sha256"] == sha(AB_ROOT / "orchestration/config.json"), "AB pipeline startup drift")
    for name, digest in pc["sources"].items():
        need(sha(AB_ROOT / name) == digest, "AB pipeline source drift")
    require_ab_terminal(state, ps, pc, ba)
    for mode in ("archive", "audit", "assemble", "score"):
        r = read_json(AB_ROOT / f"orchestration/{mode}_COMPLETE.json")
        limit = pc["download_seconds"] if mode == "archive" else pc["stage_seconds"]
        need(r["status"] == "COMPLETE" and np.isfinite(r["elapsed"]) and 0 <= r["elapsed"] < limit,
             "AB stage completion/budget invalid")
        need(np.isfinite(r["peak_rss_bytes"]) and 0 <= r["peak_rss_bytes"] <= pc["stage_memory_bytes"], "AB stage memory invalid")
        need(r["log_sha256"] == sha(AB_ROOT / f"orchestration/{mode}.log"), "AB stage log drift")
    acfg = ab.config()
    need(ba["assembly_config_sha256"] == sha(AB_ROOT / "assembly_config.json"), "AB score contract drift")
    need(ba["cache_snapshot_sha256"] == ab.check_snapshot(), "AB score cache snapshot drift")
    need(ba["independent_reconstruction_sha256"] == sha(AB_ROOT / "independent_reconstruction.json"), "AB verification drift")
    old_verify = read_json(AB_ROOT / "independent_reconstruction.json")
    need(old_verify["status"] == "INDEPENDENT_RECONSTRUCTION_PASS_UNSCORED" and old_verify["outer_labels_scored"] is False,
         "AB independent record invalid")
    need(old_verify["assembly_config_sha256"] == ba["assembly_config_sha256"]
         and old_verify["cache_snapshot_sha256"] == ba["cache_snapshot_sha256"], "AB independent inputs mismatch")
    rows = old_verify["outer_rows"]
    need(len(rows) == 5 and [r["outer"] for r in rows] == list(range(1, 6)), "AB verification folds incomplete")
    for r in rows:
        folder = AB_ROOT / f"assembled/outer_{r['outer']:02d}"
        need(r["prediction_sha256"] == sha(folder / "predictions.npz") and r["manifest_sha256"] == sha(folder / "manifest.json"), "AB assembled bytes drift")
        need(set(r["max_abs_errors"]) == {"baseline_proba", "candidate_proba"}
             and all(np.isfinite(v) and 0 <= v <= 1e-12 for v in r["max_abs_errors"].values()), "AB reconstruction errors invalid")
    cc, gc, ids, splits = ab.inputs()
    need(read_json(AB_ROOT / "supervisor_state.json")["pid"] == pc["cpu_pid"], "AB CPU instance changed")
    expected, gpu_cfg = archive.binding(AB_ROOT / "gpu")
    archive.verify_existing(AB_ROOT / "gpu", expected, gpu_cfg)
    legacy_completion = legacy.require_successful_completion()
    need(legacy_completion["status"] == "LEGACY_CPU_CACHE_RUN_COMPLETE"
         and legacy_completion["config_sha256"] == sha(ROOT / "frozen_config.json"), "C completion contract invalid")
    return {"ab": ab, "legacy": legacy, "ab_score": ba, "ab_cpu": cc, "gpu": gc, "ids": ids,
            "splits": splits, "legacy_completion": legacy_completion, "ab_config": acfg}


def load_outer(context, outer):
    ab, legacy = context["ab"], context["legacy"]
    pairs, train, hold = ab.load_checked_outer(outer, context["ab_cpu"], context["gpu"], context["ids"], context["splits"])
    cpairs = {"ct": pairs["ct"]}
    for family in ("v80", "v85"):
        cpairs[family] = legacy.check_family_cache(ROOT / f"outer_{outer:02d}" / family, outer, family,
            train, hold, context["ids"], context["splits"][f"outer_{outer:02d}_{family}_fold"],
            sha(ROOT / "frozen_config.json"), context["ab_cpu"]["sources"]["data/train.csv"],
            context["ab_cpu"]["splits_sha256"])
    return pairs, cpairs, train, hold


def snapshot(context):
    files = {str(p.relative_to(PROJECT)): sha(p) for p in required_files()}
    for name, digest in context["legacy_completion"]["files"].items():
        need(sha(ROOT / name) == digest, "C completion file drift")
        files[str((ROOT / name).relative_to(PROJECT))] = digest
    value = {"status": "COMPLETE_ABCD_INPUTS_UNSCORED", "comparison_config_sha256": sha(ROOT / "comparison_config.json"),
             "files": files, "outer_labels_scored": False}
    immutable_json(ROOT / "comparison_snapshot.json", value)
    return sha(ROOT / "comparison_snapshot.json")


def check_snapshot():
    snap = read_json(ROOT / "comparison_snapshot.json")
    need(snap["comparison_config_sha256"] == sha(ROOT / "comparison_config.json"), "comparison snapshot contract drift")
    for name, digest in snap["files"].items():
        need(not Path(name).is_absolute() and ".." not in Path(name).parts, "invalid snapshot path")
        need(sha(PROJECT / name) == digest, "comparison snapshot drift: " + name)
    return sha(ROOT / "comparison_snapshot.json")


def audit_inputs():
    context = checked_context()
    for outer in range(1, 6):
        load_outer(context, outer)
    snapshot(context)
    return context


def t_labels(rows):
    # The CSV parser never loads the complementary U target values.
    selected = set((np.asarray(rows, dtype=np.int64) + 1).tolist())
    values = pd.read_csv(PROJECT / "data/train.csv", usecols=["Will_Buy_EV"],
                         skiprows=lambda line: line != 0 and line not in selected).Will_Buy_EV
    need(len(values) == len(rows) and values.isin(["Yes", "No"]).all(), "T target identity/schema invalid")
    need(np.all(np.diff(rows) > 0), "T rows must be ordered")
    return values.eq("Yes").to_numpy(np.int8)


def validate_rebuilt(prior, manifest, expected, hold, ids, ab):
    need(set(prior) == {"valid_idx", "valid_id", "baseline_proba", "candidate_proba"}, "AB assembled schema invalid")
    need(np.array_equal(prior["valid_idx"], hold) and np.array_equal(prior["valid_id"], ids[hold]), "AB assembled identity invalid")
    for key in ("v90_fold_weights", "ct_final_weight"):
        need(manifest[key] == expected[key], "independent AB weights mismatch")
    for field, key in (("baseline_proba", "refit_prediction"), ("candidate_proba", "foldmean_prediction")):
        ab.probability(prior[field], len(hold), "float64")
        error = float(np.max(np.abs(prior[field] - expected[key])))
        need(np.isfinite(error) and error <= 1e-12, "independent AB prediction mismatch")


def read_rebuilt_ab(context, outer, pairs, y, hold):
    ab = context["ab"]
    folder = AB_ROOT / f"assembled/outer_{outer:02d}"
    prior, manifest = ab.read_npz(folder / "predictions.npz"), read_json(folder / "manifest.json")
    need(manifest["status"] == "ASSEMBLED_UNSCORED" and manifest["outer"] == outer
         and manifest["outer_hold_labels_used"] is False, "AB assembled scope invalid")
    need(manifest["prediction_sha256"] == sha(folder / "predictions.npz")
         and manifest["assembly_config_sha256"] == context["ab_score"]["assembly_config_sha256"]
         and manifest["cache_snapshot_sha256"] == context["ab_score"]["cache_snapshot_sha256"], "AB assembled inputs mismatch")
    expected = ab.independent_meta(*ab.meta_inputs(y, pairs))
    validate_rebuilt(prior, manifest, expected, hold, context["ids"], ab)
    return prior


def assemble():
    context = audit_inputs()
    ab = context["ab"]
    snap = check_snapshot()
    for outer in range(1, 6):
        pairs, cpairs, train, hold = load_outer(context, outer)
        y = t_labels(train)
        read_rebuilt_ab(context, outer, pairs, y, hold)
        result = ab.cpu.fit_v100_meta(*ab.meta_inputs(y, cpairs))
        ab.probability(result["refit_prediction"], len(hold), "float64")
        folder = OUTPUT / f"outer_{outer:02d}"
        path = folder / "predictions.npz"
        ab.probability(result["foldmean_prediction"], len(hold), "float64")
        arrays = {"valid_idx": hold, "valid_id": context["ids"][hold], "c_proba": result["refit_prediction"],
                  "d_proba": result["foldmean_prediction"]}
        need(not path.exists(), "C assembled output already exists; preserve evidence")
        ab.cpu.atomic_npz(path, **arrays)
        write_json(folder / "manifest.json", {"status": "C_ASSEMBLED_UNSCORED", "outer": outer,
            "comparison_config_sha256": sha(ROOT / "comparison_config.json"), "snapshot_sha256": snap,
            "prediction_sha256": sha(path), "v90_fold_weights": result["v90_fold_weights"],
            "ct_final_weight": result["ct_final_weight"], "meta_weights_reused_from_AB": False,
            "outer_hold_labels_used": False})
    check_snapshot()
    return {"status": "ALL_C_OUTERS_ASSEMBLED_UNSCORED", "outer_folds": 5}


def verify_readonly():
    context = audit_inputs()
    ab, rows = context["ab"], []
    snap = check_snapshot()
    for outer in range(1, 6):
        pairs, cpairs, train, hold = load_outer(context, outer)
        y = t_labels(train)
        ab_prior = read_rebuilt_ab(context, outer, pairs, y, hold)
        folder = OUTPUT / f"outer_{outer:02d}"
        prior, meta = ab.read_npz(folder / "predictions.npz"), read_json(folder / "manifest.json")
        need(meta["status"] == "C_ASSEMBLED_UNSCORED" and meta["outer"] == outer
             and meta["comparison_config_sha256"] == sha(ROOT / "comparison_config.json")
             and meta["snapshot_sha256"] == snap and meta["prediction_sha256"] == sha(folder / "predictions.npz"), "C assembled source mismatch")
        expected = ab.independent_meta(*ab.meta_inputs(y, cpairs))
        error = validate_c_rebuilt(prior, meta, expected, hold, context["ids"], ab)
        rows.append({"outer": outer, "max_abs_errors_CD": error,
                     "ab_prediction_sha256": sha(AB_ROOT / f"assembled/outer_{outer:02d}/predictions.npz"),
                     "c_prediction_sha256": sha(folder / "predictions.npz"),
                     "c_manifest_sha256": sha(folder / "manifest.json")})
    check_snapshot()
    return {"status": "ABCD_INDEPENDENT_RECONSTRUCTION_PASS_UNSCORED",
            "comparison_config_sha256": sha(ROOT / "comparison_config.json"), "snapshot_sha256": snap,
            "outer_rows": rows, "outer_labels_scored": False}, context


def validate_c_rebuilt(prior, meta, expected, hold, ids, ab):
    need(meta["meta_weights_reused_from_AB"] is False and meta["outer_hold_labels_used"] is False, "C meta scope invalid")
    need(set(prior) == {"valid_idx", "valid_id", "c_proba", "d_proba"}
         and np.array_equal(prior["valid_idx"], hold)
         and np.array_equal(prior["valid_id"], ids[hold]), "C assembled identity mismatch")
    for key in ("v90_fold_weights", "ct_final_weight"):
        need(meta[key] == expected[key], "independent C weights mismatch")
    errors = {}
    for field, key in (("c_proba", "refit_prediction"), ("d_proba", "foldmean_prediction")):
        ab.probability(prior[field], len(hold), "float64")
        errors[field] = float(np.max(np.abs(prior[field] - expected[key])))
        need(np.isfinite(errors[field]) and errors[field] <= 1e-12, "independent C/D predictions mismatch")
    return errors


def verify():
    require_stage_success("assemble")
    result, _ = verify_readonly()
    immutable_json(OUTPUT / "independent_reconstruction.json", result)
    return result


def paired_report(y, baseline, candidate, folds, shared):
    result = shared.paired_auc(y, baseline, candidate, folds)
    for row, selected in [(result, np.ones(len(y), bool)), *[(r, folds == r["fold"]) for r in result["folds"]]]:
        for field, pred in (("baseline_auc", baseline), ("candidate_auc", candidate)):
            need(abs(row[field] - roc_auc_score(y[selected], pred[selected])) <= 1e-12, "sklearn paired AUC mismatch")
    report_gate(result)
    return result


def match_ba(rebuilt, frozen):
    for field in ("n_rows", "n_positive", "n_negative", "positive_folds"):
        need(rebuilt[field] == frozen[field], "B-A report identity changed")
    for left, right in [(rebuilt, frozen), *zip(rebuilt["folds"], frozen["folds"])]:
        for field in ("baseline_auc", "candidate_auc", "delta"):
            need(abs(left[field] - right[field]) <= 1e-12, "B-A recomputed score changed")


def score():
    need(not (OUTPUT / "results.json").exists(), "comparison already scored")
    require_stage_success("verify")
    verification, context = verify_readonly()  # Current execution, never trust an old PASS alone.
    need(read_json(OUTPUT / "independent_reconstruction.json") == verification, "independent verify stage missing or stale")
    ab, _, _, shared = modules()
    n = len(context["ids"])
    vectors = {k: np.full(n, np.nan) for k in ("A", "B", "C", "D")}
    covered = np.zeros(n, np.int8)
    for row in verification["outer_rows"]:
        outer = row["outer"]
        ap = AB_ROOT / f"assembled/outer_{outer:02d}/predictions.npz"
        cp = OUTPUT / f"outer_{outer:02d}/predictions.npz"
        need(sha(ap) == row["ab_prediction_sha256"] and sha(cp) == row["c_prediction_sha256"], "prediction changed after independent verification")
        a, c = ab.read_npz(ap), ab.read_npz(cp)
        hold = context["splits"][f"outer_{outer:02d}_valid_idx"]
        need(np.array_equal(a["valid_idx"], hold) and np.array_equal(c["valid_idx"], hold), "score row identity changed")
        need(np.array_equal(a["valid_id"], context["ids"][hold]) and np.array_equal(c["valid_id"], context["ids"][hold]), "score IDs changed")
        vectors["A"][hold], vectors["B"][hold], vectors["C"][hold] = a["baseline_proba"], a["candidate_proba"], c["c_proba"]
        vectors["D"][hold] = c["d_proba"]
        covered[hold] += 1
    need(np.all(covered == 1), "all rows must be covered exactly once")
    check_snapshot()
    # First endpoint use of U labels, only after all C outputs and current independent reconstruction.
    raw = pd.read_csv(PROJECT / "data/train.csv", usecols=["Will_Buy_EV"]).Will_Buy_EV
    need(raw.isin(["Yes", "No"]).all() and len(raw) == n, "endpoint labels invalid")
    y, folds = raw.eq("Yes").to_numpy(np.int8), context["splits"]["outer_fold"]
    ba = paired_report(y, vectors["A"], vectors["B"], folds, shared)
    match_ba(ba, context["ab_score"])
    dc = paired_report(y, vectors["C"], vectors["D"], folds, shared)
    bc = paired_report(y, vectors["C"], vectors["B"], folds, shared)
    ac = paired_report(y, vectors["C"], vectors["A"], folds, shared)
    result = {"status": "UNCOMMITTED_LEGACY_COMPARISON_REQUIRES_SUPERVISOR", "primary_comparison": "D_MINUS_C",
              "candidate": "D", "baseline": "C", "selection_revision": "R01",
              "D_minus_C": dc, "B_minus_C": bc, "A_minus_C": ac, "B_minus_A": context["ab_score"],
              "B_minus_A_recomputed": ba, **decisions(ba, dc, bc, ac, True),
              "comparison_config_sha256": sha(ROOT / "comparison_config.json"),
              "snapshot_sha256": check_snapshot(),
              "independent_reconstruction_sha256": sha(OUTPUT / "independent_reconstruction.json"),
              "is_new_blind_test": False}
    write_json(OUTPUT / "results.pending.json", result)
    return result


def require_stage_success(mode):
    prior = read_json(OUTPUT / f"{mode}_RUN_RESULT.json")
    launch = read_json(OUTPUT / f"{mode}_STARTED.json")
    need(prior["status"] == "COMPARISON_STAGE_COMPLETE" and prior["mode"] == mode
         and prior["config_sha256"] == sha(ROOT / "comparison_config.json"), "previous comparison stage not successful")
    need(launch["mode"] == mode and launch["pid"] == prior["pid"]
         and launch["supervisor_created"] == prior["supervisor_created"]
         and launch["config_sha256"] == prior["config_sha256"], "previous stage instance mismatch")
    need(np.isfinite(prior["seconds"]) and 0 <= prior["seconds"] < WALL
         and np.isfinite(prior["peak_process_tree_rss_bytes"])
         and 0 <= prior["peak_process_tree_rss_bytes"] <= MEMORY, "previous comparison stage exceeded budget")
    need(prior["log_sha256"] == sha(OUTPUT / f"{mode}.log"), "previous stage log drift")
    ready_path = OUTPUT / f"{mode}_PARENT_GUARD_READY.json"
    ready = read_json(ready_path)
    need(prior["parent_guard_ready_sha256"] == sha(ready_path)
         and ready["parent_pid"] == launch["pid"] and ready["parent_created"] == launch["supervisor_created"],
         "previous stage parent guard provenance invalid")
    need(prior["allowed_for_submission"] is False and prior["actual_test_predictions_generated"] is False,
         "previous stage submission boundary invalid")
    checks = prior["resource_checks"]
    need([r["phase"] for r in checks] == ["before_worker", "after_worker", "before_publish", "final"],
         "previous stage final budget evidence incomplete")
    need(all(np.isfinite(r["seconds"]) and 0 <= r["seconds"] < WALL
             and np.isfinite(r["peak_rss_bytes"]) and 0 <= r["peak_rss_bytes"] <= MEMORY for r in checks),
         "previous stage resource evidence exceeded budget")
    need([r["seconds"] for r in checks] == sorted(r["seconds"] for r in checks)
         and [r["peak_rss_bytes"] for r in checks] == sorted(r["peak_rss_bytes"] for r in checks)
         and checks[-1]["seconds"] == prior["seconds"]
         and checks[-1]["peak_rss_bytes"] == prior["peak_process_tree_rss_bytes"], "previous stage resource evidence inconsistent")
    if mode == "score":
        need(prior["result_sha256"] == sha(OUTPUT / "results.json"), "completed comparison result drift")


def tree_rss():
    """包括本监督器和其全部子孙；短暂退出的子进程不算采样异常。"""
    parent = psutil.Process(os.getpid())
    total = 0
    for process in [parent, *parent.children(recursive=True)]:
        try:
            total += process.memory_info().rss
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            pass
    return total


def budget_check(started, peak, phase):
    peak = max(peak, tree_rss())
    elapsed = time.monotonic() - started
    need(np.isfinite(elapsed) and 0 <= elapsed < WALL, "comparison stage wall budget exceeded: " + phase)
    need(peak <= MEMORY, "comparison memory budget exceeded: " + phase)
    return {"phase": phase, "seconds": elapsed, "peak_rss_bytes": peak}


def require_successful_comparison():
    """下游唯一合格结果入口；结果文件单独存在不等于成功。"""
    check_config()
    check_snapshot()
    require_stage_success("assemble")
    require_stage_success("verify")
    require_stage_success("score")
    result = read_json(OUTPUT / "results.json")
    need(result["status"] == "COMPLETE_LEGACY_COMPARISON_CONFIRMATION_ONLY"
         and result["requires_successful_score_stage_result"] is True
         and result["candidate"] == "D" and result["baseline"] == "C"
         and result["primary_comparison"] == "D_MINUS_C" and result["selection_revision"] == "R01",
         "completed comparison roles/status invalid")
    need(result["comparison_config_sha256"] == sha(ROOT / "comparison_config.json")
         and result["snapshot_sha256"] == check_snapshot()
         and result["independent_reconstruction_sha256"] == sha(OUTPUT / "independent_reconstruction.json"),
         "completed comparison evidence drift")
    expected = decisions(result["B_minus_A_recomputed"], result["D_minus_C"], result["B_minus_C"], result["A_minus_C"], True)
    need(all(result[key] == value for key, value in expected.items()), "completed comparison gate drift")
    return result


def stop_group(process):
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


def supervise(mode):
    started = time.monotonic()
    check_config()
    insist_complete()
    OUTPUT.mkdir(exist_ok=True)
    with (OUTPUT / "comparison.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        marker = OUTPUT / f"{mode}_STARTED.json"
        need(not marker.exists(), "stage already attempted; preserve evidence and request review")
        if mode in ("verify", "score"):
            prerequisite = "assemble" if mode == "verify" else "verify"
            require_stage_success(prerequisite)
        with marker.open("x") as handle:
            launch = {"pid": os.getpid(), "supervisor_created": psutil.Process(os.getpid()).create_time(),
                      "worker_token": os.urandom(24).hex(), "mode": mode,
                      "config_sha256": sha(ROOT / "comparison_config.json"), "started_unix": time.time()}
            json.dump(launch, handle)
            handle.flush()
            os.fsync(handle.fileno())
        peak, process, checks = 0, None, []
        try:
            env = os.environ.copy()
            env.update({key: "2" for key in THREAD_KEYS})
            env["COMPARISON_SUPERVISED_TOKEN"] = launch["worker_token"]
            checks.append(budget_check(started, peak, "before_worker"))
            peak = checks[-1]["peak_rss_bytes"]
            with (OUTPUT / f"{mode}.log").open("x") as log:
                process = subprocess.Popen([sys.executable, "-u", str(Path(__file__).resolve()), "_worker", "--stage", mode],
                           cwd=ROOT, env=env, start_new_session=True, stdout=log, stderr=subprocess.STDOUT)
                try:
                    while process.poll() is None:
                        peak = budget_check(started, peak, "worker_running")["peak_rss_bytes"]
                        time.sleep(.25)
                    if process.returncode:
                        raise RuntimeError("comparison worker failed; preserved log")
                finally:
                    stop_group(process)
            checks.append(budget_check(started, peak, "after_worker"))
            peak = checks[-1]["peak_rss_bytes"]
            check_config()
            check_snapshot()
            ready_path = OUTPUT / f"{mode}_PARENT_GUARD_READY.json"
            ready = read_json(ready_path)
            need(ready["parent_pid"] == launch["pid"] and ready["parent_created"] == launch["supervisor_created"]
                 and ready["worker_pid"] == process.pid, "comparison parent guard missing or mismatched")
            guard_sha = sha(ready_path)
            config_sha, log_sha = sha(ROOT / "comparison_config.json"), sha(OUTPUT / f"{mode}.log")
            result = None
            if mode == "score":
                need(not (OUTPUT / "results.json").exists(), "score result already exists")
                result = read_json(OUTPUT / "results.pending.json")
                need(result["status"] == "UNCOMMITTED_LEGACY_COMPARISON_REQUIRES_SUPERVISOR", "pending score state invalid")
                result["status"] = "COMPLETE_LEGACY_COMPARISON_CONFIRMATION_ONLY"
                result["requires_successful_score_stage_result"] = True
            checks.append(budget_check(started, peak, "before_publish"))
            peak = checks[-1]["peak_rss_bytes"]
            if result is not None:
                publish_json_once(OUTPUT / "results.json", result)
            result_sha = sha(OUTPUT / "results.json") if result is not None else None
            checks.append(budget_check(started, peak, "final"))
            peak = checks[-1]["peak_rss_bytes"]
            write_json(OUTPUT / f"{mode}_RUN_RESULT.json", {"status": "COMPARISON_STAGE_COMPLETE", "mode": mode,
                       "pid": os.getpid(), "seconds": checks[-1]["seconds"], "peak_process_tree_rss_bytes": peak,
                       "supervisor_created": launch["supervisor_created"], "parent_guard_ready_sha256": guard_sha,
                       "config_sha256": config_sha, "log_sha256": log_sha, "resource_checks": checks,
                       "result_sha256": result_sha,
                       "actual_test_predictions_generated": False, "allowed_for_submission": False})
            return {"status": "COMPARISON_STAGE_COMPLETE", "stage": mode}
        except BaseException as exc:
            write_json(OUTPUT / f"{mode}_RUN_RESULT.json", {"status": "COMPARISON_STAGE_FAILED", "mode": mode,
                       "seconds": time.monotonic() - started, "peak_process_tree_rss_bytes": peak,
                       "pid": os.getpid(), "resource_checks": checks,
                       "config_sha256": sha(ROOT / "comparison_config.json"), "error_type": type(exc).__name__,
                       "error": str(exc), "allowed_for_submission": False})
            raise


def guarded_worker(stage):
    marker = read_json(OUTPUT / f"{stage}_STARTED.json")
    need(marker["pid"] == os.getppid() and marker["mode"] == stage
         and marker["config_sha256"] == sha(ROOT / "comparison_config.json")
         and marker["worker_token"] == os.environ.get("COMPARISON_SUPERVISED_TOKEN"),
         "worker not launched by registered supervisor")
    _, legacy, _, _ = modules()
    need(legacy.matching_process_alive(marker["pid"], marker["supervisor_created"]), "worker parent identity lost")
    ready_path = OUTPUT / f"{stage}_PARENT_GUARD_READY.json"
    # Independent process keeps checking PID + create_time during long native calls.
    guard = legacy.spawn_parent_guard(marker["pid"], marker["supervisor_created"], ready_path)
    try:
        ready = read_json(ready_path)
        need(ready["watchdog_pid"] == guard.pid and ready["worker_pid"] == os.getpid()
             and ready["worker_created"] == psutil.Process(os.getpid()).create_time()
             and ready["parent_pid"] == marker["pid"] and ready["parent_created"] == marker["supervisor_created"]
             and guard.poll() is None, "parent guard handshake invalid")
        with threadpool_limits(limits=2):
            return {"assemble": assemble, "verify": verify, "score": score}[stage]()
    finally:
        guard.terminate()
        try:
            guard.wait(timeout=3)
        except subprocess.TimeoutExpired:
            guard.kill()
            guard.wait(timeout=3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("freeze", "status", "assemble", "verify", "score", "_worker"))
    parser.add_argument("--stage", choices=("assemble", "verify", "score"))
    args = parser.parse_args()
    if args.mode == "status":
        missing = missing_files()
        print(json.dumps({"status": "NOT_READY" if missing else "FILES_PRESENT_AUDIT_REQUIRED", "missing": missing,
                          "partial_scores_computed": False}))
        return
    if args.mode == "freeze":
        result = freeze()
    elif args.mode == "_worker":
        need(args.stage is not None, "worker stage required")
        result = guarded_worker(args.stage)
    else:
        result = supervise(args.mode)
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
