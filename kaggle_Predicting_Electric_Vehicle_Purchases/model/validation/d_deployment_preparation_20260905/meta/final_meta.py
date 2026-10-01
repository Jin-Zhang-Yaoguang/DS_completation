#!/usr/bin/env python3
"""PREPARATION_ONLY_NOT_AUTHORIZED. Pure D final-meta primitives; no real run CLI."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import platform
from pathlib import Path
import sys
import numpy as np
import sklearn
from sklearn.model_selection import StratifiedKFold

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[3]
REFERENCE = PROJECT / "model/v100_v90_ctboost_nested_cv_blend/v100_v90_ctboost_nested_cv_blend.py"
REFERENCE_SHA = "ad5cd07b64bf69fd08b9636c0a72138463b2506987155d3939395b5ce246a817"
R01_SHA = "5d8ecfad981e7de6be27181c2d14f7ca962f68a954235917a5601bbc5f572388"
V90_OOF = "model/v90_v89_member_verify_budget_retry/oof_proba.npy"
V90_TEST = "model/v90_v89_member_verify_budget_retry/test_proba.npy"
V90_SOURCES = "model/v90_v89_member_verify_budget_retry/sources.json"
V90_SOURCES_SHA = "57e7a7713386b1a1e8f6429f54ed88fcddba1c802811d72f628fdb8c7a775b70"
V90_DIGESTS = {V90_OOF: "c0057fc23fb130cd0bbbc05c6849893d5b79ff3a7ad786715d68fc1a6de4628f",
               V90_TEST: "6fa740955ac5997455e8e4b18aa181adbd9dd6da719e0cc80d858963e002f363"}
GRID = np.arange(0.0, 0.5000001, 0.025)
STATUS = "PREPARATION_ONLY_NOT_AUTHORIZED"
_REFERENCE = None


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), "missing regular file: " + str(path))
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path):
    sha(path)
    return json.loads(Path(path).read_text(), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def source_path(root, relative):
    relative = Path(relative)
    require(not relative.is_absolute() and ".." not in relative.parts, "unsafe source path")
    path = Path(root) / relative
    require(path.resolve() == path.absolute(), "symlinked source path")
    return path


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def reference():
    global _REFERENCE
    require(sha(REFERENCE) == REFERENCE_SHA, "historical V100 reference changed")
    if _REFERENCE is None:
        _REFERENCE = module(REFERENCE, "d_final_meta_v100_reference")
    require(np.array_equal(_REFERENCE.WEIGHT_GRID, GRID), "historical final grid differs")
    return _REFERENCE


def probability(array, rows, dtype, name):
    require(isinstance(array, np.ndarray) and array.dtype == np.dtype(dtype) and array.shape == (rows,), name + " dtype/shape")
    require(np.isfinite(array).all() and np.all((array >= 0) & (array <= 1)), name + " probability range")


def ids(array, rows, name):
    require(isinstance(array, np.ndarray) and array.dtype == np.dtype("int64") and array.shape == (rows,), name + " dtype/shape")
    require(len(np.unique(array)) == rows, name + " duplicate IDs")


def binary_target(y):
    require(isinstance(y, np.ndarray) and y.ndim == 1 and y.dtype.kind in "iu", "binary target dtype/shape")
    require(set(np.unique(y).tolist()) == {0, 1}, "both binary classes required")


def final_fit(y, v90_oof, ct_oof, v90_test, ct_test):
    """Only the historical full-training final stage; never refits V90's inner meta folds."""
    binary_target(y)
    n, m = len(y), len(v90_test)
    require(n > 0 and m > 0, "empty final-meta inputs")
    probability(v90_oof, n, "float64", "V90 OOF")
    probability(ct_oof, n, "float32", "CT OOF")
    probability(v90_test, m, "float64", "V90 test")
    probability(ct_test, m, "float64", "CT test")
    old = reference()
    core_state, ct_state = old.fit_mid_ecdf(v90_oof), old.fit_mid_ecdf(ct_oof.astype(np.float64))
    core_rank = old.transform_mid_ecdf(core_state, v90_oof)
    ct_rank = old.transform_mid_ecdf(ct_state, ct_oof.astype(np.float64))
    weight, apparent = old.choose_weight(y, core_rank, ct_rank)
    result = (1.0 - weight) * old.transform_mid_ecdf(core_state, v90_test) + weight * old.transform_mid_ecdf(ct_state, ct_test)
    probability(result, m, "float64", "D test")
    return {"test_proba": result, "v90_ecdf_state": core_state, "ct_ecdf_state": ct_state,
            "selected_ct_weight": weight, "full_fit_apparent_auc": apparent,
            "weight_grid": GRID.tolist(), "tie_break": "smallest CT weight on exactly equal AUC",
            "is_unbiased_validation": False, "allowed_for_submission": False}


def independent_ecdf(reference_values, query):
    """Count mass strictly below/equal query using unique bins, independent of V100 searchsorted helpers."""
    values, count = np.unique(np.asarray(reference_values, np.float64), return_counts=True)
    cumulative = np.r_[0, np.cumsum(count, dtype=np.int64)]
    below = np.digitize(query, values, right=True)
    through = np.digitize(query, values, right=False)
    return (cumulative[below] + cumulative[through]) / (2.0 * len(reference_values))


def independent_auc(y, score):
    """Unweighted ROC trapezoids; no sklearn/reference scoring calls.

    Dropping collinear points retains sklearn's arithmetic order, so the old
    exact-AUC tie rule is checked without introducing a new tie tolerance.
    """
    binary_target(y)
    order = np.argsort(score, kind="mergesort")[::-1]
    sorted_score, positives = score[order], y[order]
    endpoints = np.r_[np.flatnonzero(np.diff(sorted_score)), len(score) - 1]
    tp = np.cumsum(positives, dtype=np.float64)[endpoints]
    fp = 1 + endpoints - tp
    if len(fp) > 2:
        keep = np.r_[True, np.logical_or(np.diff(fp, 2), np.diff(tp, 2)), True]
        fp, tp = fp[keep], tp[keep]
    fp, tp = np.r_[0., fp], np.r_[0., tp]
    return float(np.trapezoid(tp / tp[-1], fp / fp[-1]))


def independent_fit(y, v90_oof, ct_oof, v90_test, ct_test):
    core = independent_ecdf(v90_oof, v90_oof)
    ct = independent_ecdf(ct_oof.astype(np.float64), ct_oof.astype(np.float64))
    scores = [independent_auc(y, (1.0 - weight) * core + weight * ct) for weight in GRID]
    best = 0
    for index in range(1, len(GRID)):
        if scores[index] > scores[best]:
            best = index
    weight = float(GRID[best])
    prediction = (1.0 - weight) * independent_ecdf(v90_oof, v90_test) + weight * independent_ecdf(ct_oof.astype(np.float64), ct_test)
    return {"test_proba": prediction, "selected_ct_weight": weight,
            "full_fit_apparent_auc": scores[best], "grid_apparent_auc": scores}


def verify_final(actual, y, v90_oof, ct_oof, v90_test, ct_test):
    binary_target(y)
    for value, rows, dtype, name in ((v90_oof, len(y), "float64", "V90 OOF"), (ct_oof, len(y), "float32", "CT OOF"),
                                     (v90_test, len(v90_test), "float64", "V90 test"),
                                     (ct_test, len(v90_test), "float64", "CT test"),
                                     (actual["test_proba"], len(v90_test), "float64", "D test")):
        probability(value, rows, dtype, name)
    require(all(actual[key].dtype == np.dtype("float64") and actual[key].shape == (len(y),)
                for key in ("v90_ecdf_state", "ct_ecdf_state")), "ECDF state dtype/shape differs")
    rebuilt = independent_fit(y, v90_oof, ct_oof, v90_test, ct_test)
    require(actual["selected_ct_weight"] == rebuilt["selected_ct_weight"], "independent selected weight differs")
    require(abs(actual["full_fit_apparent_auc"] - rebuilt["full_fit_apparent_auc"]) <= 1e-12, "independent apparent AUC differs")
    require(np.array_equal(actual["v90_ecdf_state"], np.sort(v90_oof))
            and np.array_equal(actual["ct_ecdf_state"], np.sort(ct_oof.astype(np.float64))), "ECDF state source differs")
    require(np.array_equal(actual["test_proba"], rebuilt["test_proba"]), "independent D prediction differs")
    require(actual["weight_grid"] == GRID.tolist() and actual["is_unbiased_validation"] is False
            and actual["allowed_for_submission"] is False, "final-meta method/scope differs")
    return {"status": "INDEPENDENT_FINAL_META_PASS", "max_abs_error": 0.,
            "selected_ct_weight": rebuilt["selected_ct_weight"], "is_unbiased_validation": False,
            "allowed_for_submission": False}


def validate_global_arrays(train_id, test_id, y, v90_oof, v90_test, cache, fold_predictions):
    """Byte/source authorization is checked separately, before loading these arrays."""
    n, m = len(y), len(test_id)
    require(n > 0 and m > 0, "empty global inputs")
    ids(train_id, n, "official train IDs"); ids(test_id, m, "official test IDs")
    require(not np.intersect1d(train_id, test_id).size, "train/test ID overlap")
    binary_target(y)
    probability(v90_oof, n, "float64", "old V90 OOF"); probability(v90_test, m, "float64", "old V90 test")
    require(set(cache) == {"train_id", "test_id", "oof_proba", "test_proba_foldmean", "atom_fold"}, "CT cache schema")
    require(np.array_equal(cache["train_id"], train_id) and np.array_equal(cache["test_id"], test_id), "CT global IDs differ")
    ids(cache["train_id"], n, "CT train IDs"); ids(cache["test_id"], m, "CT test IDs")
    probability(cache["oof_proba"], n, "float32", "CT global OOF")
    probability(cache["test_proba_foldmean"], m, "float64", "CT global test")
    require(cache["atom_fold"].dtype == np.dtype("int8") and cache["atom_fold"].shape == (n,), "CT folds dtype/shape")
    require(len(fold_predictions) == 5, "exactly five CT folds required")
    expected_fold = np.full(n, -1, np.int8)
    rebuilt_oof, mean = np.full(n, np.nan, np.float32), np.zeros(m, np.float64)
    for fold, ((fit, hold), atom) in enumerate(zip(StratifiedKFold(5, shuffle=True, random_state=42).split(np.zeros(n), y), fold_predictions)):
        require(set(atom) == {"fit_idx", "hold_idx", "fit_id", "hold_id", "test_id", "oof_proba", "test_proba"}, "CT atom schema")
        for key, expected in (("fit_idx", fit), ("hold_idx", hold), ("fit_id", train_id[fit]), ("hold_id", train_id[hold]), ("test_id", test_id)):
            require(atom[key].dtype == np.dtype("int64") and np.array_equal(atom[key], expected), "CT atom identity/fold differs: " + key)
        probability(atom["oof_proba"], len(hold), "float64", "CT atom OOF")
        probability(atom["test_proba"], m, "float64", "CT atom test")
        expected_fold[hold] = fold
        rebuilt_oof[hold] = atom["oof_proba"].astype(np.float32)
        mean += atom["test_proba"] / 5
    require(np.array_equal(cache["atom_fold"], expected_fold), "CT global fold labels differ")
    require(np.array_equal(cache["oof_proba"], rebuilt_oof), "CT OOF does not come from this batch")
    require(np.array_equal(cache["test_proba_foldmean"], mean), "CT test mean does not come from this batch/order")
    return mean


def validate_readiness(live, receipt):
    for record in (live, receipt):
        require(record.get("status") == "VERIFIED_D_REBUILD_ELIGIBLE" and record.get("candidate_rebuild_eligible") is True
                and record.get("selected_candidate") == record.get("candidate") == "D" and record.get("baseline") == "C",
                "D has not qualified")
        require(record.get("execution_authorized") is False and record.get("allowed_for_submission") is False,
                "qualification is not execution/submission authorization")
        require(record.get("bound_sources") and record.get("terminal_artifacts") and record.get("readiness_gate_sha256"),
                "qualification source closure missing")
    for key in ("bound_sources", "terminal_artifacts", "readiness_gate_sha256"):
        require(live[key] == receipt[key], "live qualification differs from authorized receipt: " + key)


def authorize_production(contract_path, authorization_path, expected_contract_sha, expected_authorization_sha):
    """Future supervised parent supplies trusted expected hashes; no CLI or implicit unlock."""
    require(Path(contract_path).is_file() and Path(authorization_path).is_file(), STATUS + ": final contract/START_AUTHORIZATION missing")
    require(isinstance(expected_contract_sha, str) and len(expected_contract_sha) == 64
            and isinstance(expected_authorization_sha, str) and len(expected_authorization_sha) == 64,
            STATUS + ": trusted expected hashes required")
    require(sha(contract_path) == expected_contract_sha and sha(authorization_path) == expected_authorization_sha,
            "final authorization bytes differ")
    config, auth = read_json(contract_path), read_json(authorization_path)
    require(config.get("status") == "FROZEN_D_FINAL_META_CONTRACT" and config.get("candidate") == "D"
            and config.get("method") == "OLD_V90_NEW_CT_FULL_TRAIN_V100_FINAL_META"
            and config.get("weight_grid") == GRID.tolist() and config.get("submission_allowed") is False
            and config.get("synthetic") is False,
            "future final meta contract scope invalid")
    require(auth.get("action") == "RUN_D_FINAL_META_ONCE" and auth.get("authorized_by") == "parent"
            and auth.get("contract_sha256") == expected_contract_sha and auth.get("competition_submission") is False
            and auth.get("preparation_only") is False,
            "future START_AUTHORIZATION invalid")
    require(config.get("meta_runtime_versions") == {"python": platform.python_version(), "numpy": np.__version__,
                                                    "scikit_learn": sklearn.__version__}, "meta runtime versions differ")
    required = {str(Path(__file__).relative_to(PROJECT)), str((ROOT / "test_final_meta.py").relative_to(PROJECT)),
                str((ROOT / "INTERFACE.md").relative_to(PROJECT)), str((ROOT / "PREPARATION.md").relative_to(PROJECT)),
                str(REFERENCE.relative_to(PROJECT)), "model/validation/e2e_legacy_comparison_20260905/PREREGISTRATION_R01.md",
                "data/train.csv", "data/test.csv", "data/sample_submission.csv", V90_OOF, V90_TEST, V90_SOURCES,
                config["readiness_gate"], config["qualification_receipt"], config["ct_adapter"],
                config["ct_config"], config["ct_start_authorization"], config["ct_archive_map"], config["v90_verified_sources"]}
    require(required <= set(config["source_files"]), "future source closure incomplete")
    for name, wanted in config["source_files"].items():
        require(sha(source_path(PROJECT, name)) == wanted, "future source drift: " + name)
    require(config["source_files"][str(REFERENCE.relative_to(PROJECT))] == REFERENCE_SHA
            and config["source_files"]["model/validation/e2e_legacy_comparison_20260905/PREREGISTRATION_R01.md"] == R01_SHA,
            "historical method/R01 contract differs")
    for name, wanted in V90_DIGESTS.items():
        require(config["source_files"][name] == wanted, "old V90 artifact changed")
    require(config["source_files"][V90_SOURCES] == V90_SOURCES_SHA, "old V90 source anchor changed")
    expected_gate = ROOT.parent / "readiness_gate.py"
    require(source_path(PROJECT, config["readiness_gate"]) == expected_gate, "foreign readiness gate")
    live = module(expected_gate, "d_meta_live_readiness").readiness()
    receipt = read_json(source_path(PROJECT, config["qualification_receipt"]))
    validate_readiness(live, receipt)
    require(auth.get("qualification_receipt_sha256") == config["source_files"][config["qualification_receipt"]],
            "authorization qualification changed")
    return {"config": config, "config_sha256": expected_contract_sha,
            "authorization_sha256": expected_authorization_sha, "readiness": live}


def id_text_sha(values):
    digest = hashlib.sha256()
    for value in values:
        digest.update(str(int(value)).encode("utf-8")); digest.update(b"\n")
    return digest.hexdigest()


def nested_source_references(value):
    references = {}
    def visit(node):
        if isinstance(node, dict):
            if "path" in node or "sha256" in node:
                require("path" in node and "sha256" in node, "incomplete V90 source reference")
                name, digest = node["path"], node["sha256"]
                require(isinstance(name, str) and not Path(name).is_absolute() and ".." not in Path(name).parts,
                        "unsafe V90 source reference")
                require(isinstance(digest, str) and len(digest) == 64 and all(c in "0123456789abcdef" for c in digest),
                        "invalid V90 source digest")
                require(name not in references or references[name] == digest, "conflicting V90 reference hashes")
                references[name] = digest
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)
    visit(value)
    return references


def verify_v90_receipt(receipt, config, train_id, test_id):
    require(receipt.get("status") == "VERIFIED_OLD_V90_GLOBAL_INPUTS"
            and receipt.get("independent_reconstruction_passed") is True
            and receipt.get("cpu_fit_rule") == "F_TRAIN_H_EARLY_STOP_SAME_MODEL_NO_REFIT"
            and receipt.get("v90_test_aggregation") == "five_meta_folds_mean", "old V90 verification scope invalid")
    require(receipt.get("train_rows") == len(train_id) and receipt.get("test_rows") == len(test_id)
            and receipt.get("train_id_sha256") == id_text_sha(train_id)
            and receipt.get("test_id_sha256") == id_text_sha(test_id), "old V90 official row mapping differs")
    source_file = source_path(PROJECT, V90_SOURCES)
    require(sha(source_file) == V90_SOURCES_SHA, "old V90 source anchor changed")
    original = read_json(source_file)
    required_references = nested_source_references(original)
    require(required_references, "old V90 source lineage empty")
    required_references[V90_SOURCES] = V90_SOURCES_SHA
    sources = receipt["source_files"]
    require(all(sources.get(name) == digest and config["source_files"].get(name) == digest
                for name, digest in required_references.items()), "old V90 deep source lineage incomplete or changed")
    identity = {"train_rows": len(train_id), "test_rows": len(test_id),
                "train_id_sha256": id_text_sha(train_id), "test_id_sha256": id_text_sha(test_id)}
    require(original["row_identity"] == identity
            and original["row_identity_hash_contract"]["expected_row_identity"] == identity
            and original["member_row_identities"] and all(row == identity for row in original["member_row_identities"].values()),
            "old V90 bound row identity differs")
    require(all(config["source_files"].get(name) == digest for name, digest in sources.items()), "old V90 receipt/source mismatch")
    require(all(sources[name] == wanted for name, wanted in V90_DIGESTS.items()), "old V90 prediction identity changed")


def load_npz(path):
    with np.load(path, allow_pickle=False) as archive:
        return {name: archive[name] for name in archive.files}


def verified_ct(config):
    adapter_path = source_path(PROJECT, config["ct_adapter"])
    require(adapter_path == ROOT.parent / "ct/ct_runner.py", "foreign CT adapter")
    adapter = module(adapter_path, "d_meta_verified_ct_adapter")
    ct_context = adapter.authorize_archived(source_path(PROJECT, config["ct_config"]),
        source_path(PROJECT, config["ct_start_authorization"]), config["source_files"][config["ct_config"]],
        config["source_files"][config["ct_start_authorization"]], source_path(PROJECT, config["ct_archive_map"]),
        config["source_files"][config["ct_archive_map"]])
    require(ct_context["mode"] == "ARCHIVE_READ_ONLY", "CT archive context required")
    require(ct_context["config"]["qualification_receipt"]["sha256"] == config["source_files"][config["qualification_receipt"]],
            "CT and final-meta qualification receipts differ")
    output = Path(ct_context["artifact_root"])
    proof = adapter.require_successful_completion(output, ct_context)
    require(proof["status"] == "CT_GLOBAL5_SUPERVISED_COMPLETE_UNSCORED" and proof["allowed_for_submission"] is False,
            "CT final supervision/verification incomplete")
    require(proof["identity"]["cohort_id"] == config["ct_cohort_id"]
            and proof["identity"]["config_sha256"] == ct_context["config_sha256"]
            and proof["identity"]["start_authorization_sha256"] == ct_context["start_authorization_sha256"],
            "CT mixed cohort/config/authorization")
    # Verify the helper's complete file snapshot again before reading the five test arrays.
    for name, digest in proof["files"].items():
        require(sha(source_path(output, name)) == digest, "CT verified artifact changed: " + name)
    return proof, output


def load_authorized_inputs(context):
    """Internal after-authorize loader; CT terminal verifier runs before CT arrays are used."""
    import pandas as pd
    config = context["config"]
    train = pd.read_csv(source_path(PROJECT, "data/train.csv"), usecols=["id", "Will_Buy_EV"])
    test = pd.read_csv(source_path(PROJECT, "data/test.csv"), usecols=["id"])
    sample = pd.read_csv(source_path(PROJECT, "data/sample_submission.csv"), usecols=["id"])
    require(len(train) == 668665 and len(test) == 286571 and train.Will_Buy_EV.isin(["Yes", "No"]).all(), "official data schema/rows")
    require(np.array_equal(test.id.to_numpy(), sample.id.to_numpy()), "official sample/test identity mismatch")
    train_id, test_id, y = train.id.to_numpy(), test.id.to_numpy(), train.Will_Buy_EV.eq("Yes").to_numpy(np.int32)
    old_receipt = read_json(source_path(PROJECT, config["v90_verified_sources"]))
    verify_v90_receipt(old_receipt, config, train_id, test_id)
    proof, output = verified_ct(config)
    atoms = [load_npz(output / f"folds/fold_{fold:02d}/predictions.npz") for fold in range(1, 6)]
    v90_oof = np.load(source_path(PROJECT, V90_OOF), allow_pickle=False)
    v90_test = np.load(source_path(PROJECT, V90_TEST), allow_pickle=False)
    cache = proof["arrays"]
    validate_global_arrays(train_id, test_id, y, v90_oof, v90_test, cache, atoms)
    provenance = {"ct_identity": proof["identity"], "ct_files": proof["files"], "ct_output_dir": str(output),
                  "v90_source_files": old_receipt["source_files"], "train_id_sha256": id_text_sha(train_id),
                  "test_id_sha256": id_text_sha(test_id)}
    return (y, v90_oof, cache["oof_proba"], v90_test, cache["test_proba_foldmean"]), test_id, provenance


def compute_authorized(contract_path, authorization_path, expected_contract_sha, expected_authorization_sha):
    """Future supervised-library entry. Returns arrays/proof; never publishes or submits.

    The future parent must provide the frozen budget, one-attempt marker and
    lifecycle supervision. This preparation contains no standalone production runner.
    """
    context = authorize_production(contract_path, authorization_path, expected_contract_sha, expected_authorization_sha)
    args, test_id, provenance = load_authorized_inputs(context)
    result = final_fit(*args)
    independent = verify_final(result, *args)
    after = authorize_production(contract_path, authorization_path, expected_contract_sha, expected_authorization_sha)
    require(context["readiness"]["terminal_artifacts"] == after["readiness"]["terminal_artifacts"], "qualification changed during final fit")
    for name, digest in provenance["ct_files"].items():
        require(sha(source_path(Path(provenance["ct_output_dir"]), name)) == digest, "CT source changed during final fit")
    return {"status": "D_FINAL_META_REBUILT_REQUIRES_PARENT_FINALIZATION", "candidate": "D", "test_id": test_id,
            "meta": result, "independent_verification": independent, "provenance": provenance,
            "contract_sha256": context["config_sha256"], "authorization_sha256": context["authorization_sha256"],
            "allowed_for_submission": False, "requires_successful_parent_supervisor": True,
            "actual_test_predictions_generated": True,
            "is_unbiased_validation": False, "historical_ct_bitwise_reproduction_claimed": False}


def preparation_status():
    return {"status": STATUS, "real_fit_performed": False, "actual_test_predictions_generated": False,
            "competition_submission": False, "real_execution_cli": False}


if __name__ == "__main__":
    require(len(sys.argv) == 1, "preparation CLI accepts no run, path or authorization flags")
    print(json.dumps(preparation_status(), ensure_ascii=False))
