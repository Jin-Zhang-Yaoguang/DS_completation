#!/usr/bin/env python3
"""One pre-registered saved-model replay, never a training or score entrypoint."""
from __future__ import annotations
import os
for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[key] = "2"
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
import pandas as pd
import psutil
import lightgbm as lgb
from sklearn.model_selection import StratifiedShuffleSplit
from threadpoolctl import threadpool_limits

OUT = Path(__file__).resolve().parent
E2E = OUT.parents[1]
PROJECT = E2E.parents[2]
ATOM = E2E / "outer_01/v80/atom_01"
sys.path.insert(0, str(E2E))
import cpu_runner as cpu
for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[key] = "2"


def demand(condition, message):
    if not condition:
        raise ValueError(message)


def partitions():
    with np.load(E2E / "splits.npz", allow_pickle=False) as z:
        train = z["outer_01_train_idx"].copy()
        hold = z["outer_01_valid_idx"].copy()
        fold = z["outer_01_v80_fold"].copy()
    fit = train[fold != 0]
    oof = train[fold == 0]
    return train, hold, fold, fit, oof


def freeze():
    demand(not (OUT / "frozen_config.json").exists(), "audit already frozen")
    cc = cpu.load_config()
    train, hold, fold, fit, oof = partitions()
    ids = pd.read_csv(PROJECT / "data/train.csv", usecols=["id"]).id.to_numpy()
    sources = {str(PROJECT / name): digest for name, digest in cc["sources"].items()}
    for path in (Path(__file__), OUT / "PREREGISTRATION.md", E2E / "frozen_config.json", E2E / "splits.npz", ATOM / "model.txt", ATOM / "predictions.npz", ATOM / "manifest.json"):
        sources[str(path)] = cpu.sha(path)
    selected = np.concatenate([oof[:100], hold[:100]])
    c = {"experiment_id": "FIRST_ATOM_REPLAY_20260905", "sources": sources,
         "query_idx": selected.tolist(), "query_id": ids[selected].tolist(),
         "query_idx_sha256": cpu.arr_sha(selected), "query_id_sha256": cpu.arr_sha(ids[selected]),
         "oof_count": 100, "outer_hold_count": 100, "tolerance": 1e-12,
         "seconds": 180, "process_tree_rss_bytes": 12 * 1024**3, "threads": 2,
         "training_allowed": False, "query_labels_allowed": False, "auc_allowed": False}
    cpu.atomic_json(OUT / "frozen_config.json", c)
    return {"status": "FROZEN_UNSCORED", "config_sha256": cpu.sha(OUT / "frozen_config.json")}


def checked_config():
    c = json.loads((OUT / "frozen_config.json").read_text())
    for name, digest in c["sources"].items():
        demand(cpu.sha(Path(name)) == digest, "source SHA drift: " + name)
    demand(c["seconds"] == 180 and c["threads"] == 2 and c["process_tree_rss_bytes"] == 12 * 1024**3, "budget drift")
    demand(c["tolerance"] == 1e-12 and not any(c[k] for k in ("training_allowed", "query_labels_allowed", "auc_allowed")), "audit boundary drift")
    return c


def forbidden_training(*args, **kwargs):
    raise RuntimeError("training is forbidden in saved-model replay")


def worker():
    started = time.monotonic()
    c = checked_config()
    cc = cpu.load_config()
    train, hold, fold, fit, oof = partitions()
    ids = pd.read_csv(PROJECT / "data/train.csv", usecols=["id"]).id.to_numpy()
    demand(len(np.unique(ids)) == len(ids) == cc["train_rows"], "official ID schema")
    demand(cpu.arr_sha(ids) == cc["train_id_sha256"], "official IDs SHA")
    demand(np.array_equal(np.sort(np.concatenate([train, hold])), np.arange(len(ids))), "outer coverage or overlap")
    demand(fold.shape == train.shape and np.array_equal(np.unique(fold), np.arange(40)), "atom folds")
    plan = cc["outer_plan"][0]
    for name, values in (("train_idx", train), ("valid_idx", hold), ("train_id", ids[train]), ("valid_id", ids[hold])):
        demand(cpu.arr_sha(values) == plan[name + "_sha256"], "outer identity " + name)
    demand(cpu.arr_sha(fold) == plan["atoms"]["v80"]["fold_ids_sha256"], "inner fold SHA")
    all_query = np.concatenate([oof, hold])
    query = np.concatenate([oof[:100], hold[:100]])
    demand(len(query) == 200 and not np.intersect1d(fit, all_query).size, "fit/query isolation")
    demand(query.tolist() == c["query_idx"] and ids[query].tolist() == c["query_id"], "selected query identity")
    expected = {"outer": 1, "family": "v80", "atom": 1, "fit_idx_sha256": cpu.arr_sha(fit), "query_idx_sha256": cpu.arr_sha(all_query)}
    m = cpu.verify_atom(ATOM, cpu.sha(E2E / "frozen_config.json"), expected)
    demand(m["status"] == "COMPLETE" and not any(m[k] for k in ("query_labels_available", "outer_hold_labels_used", "final_fit_eval_set_used")), "checkpoint state")
    with np.load(ATOM / "predictions.npz", allow_pickle=False) as z:
        demand(set(z.files) == {"oof_idx", "valid_idx", "oof_id", "valid_id", "oof_proba", "valid_proba"}, "prediction schema")
        for key, values in (("oof_idx", oof), ("valid_idx", hold), ("oof_id", ids[oof]), ("valid_id", ids[hold])):
            demand(z[key].dtype.kind in "iu" and np.array_equal(z[key], values), "prediction identity: " + key)
        for key, count in (("oof_proba", len(oof)), ("valid_proba", len(hold))):
            demand(z[key].shape == (count,) and z[key].dtype == np.dtype("float64"), "prediction shape/precision")
        expected_prediction = np.concatenate([z["oof_proba"][:100], z["valid_proba"][:100]])
    # CSV rows outside F are skipped before target-column parsing. No query y is materialized.
    fit_set = set(fit.tolist())
    fit_labels = pd.read_csv(PROJECT / "data/train.csv", usecols=["id", "Will_Buy_EV"], skiprows=lambda row: row > 0 and row - 1 not in fit_set)
    demand(np.array_equal(fit_labels.id.to_numpy(), ids[fit]), "F label identity/order")
    demand(fit_labels.Will_Buy_EV.isin(["Yes", "No"]).all(), "F label values")
    y = fit_labels.Will_Buy_EV.eq("Yes").to_numpy(np.int8)
    demand(cpu.arr_sha(y) == m["fit_y_sha256"], "F label SHA")
    contract = cc["families"]["v80"]
    seed = contract["te_seed_base"] + 1
    es_seed = cc["early_stop_seed_base"] + 1000 + cc["early_stop_family_offsets"]["v80"] + 1
    demand(m["te_seed"] == seed and m["early_stop_seed"] == es_seed, "feature seed contract")
    early_fit, early_hold = next(StratifiedShuffleSplit(1, test_size=.1, random_state=es_seed).split(np.zeros(len(y)), y))
    demand(cpu.arr_sha(fit[early_fit]) == m["early_fit_idx_sha256"] and cpu.arr_sha(fit[early_hold]) == m["early_valid_idx_sha256"], "early-stop scope reconstruction")
    params = cpu.atom_params("v80", contract, 1)
    params["n_estimators"] = m["selected_iteration"]
    demand(cpu.json_sha(params) == m["params_sha256"], "frozen model parameters")
    lgb.LGBMClassifier.fit = forbidden_training
    lgb.LGBMRegressor.fit = forbidden_training
    lgb.train = forbidden_training
    lgb.Booster.update = forbidden_training
    cpu.fit_atom = forbidden_training
    backend = cpu.load_backend("v80")
    x_fit, x_query, names = backend.encode(fit, y, query, seed)
    demand(names == m["feature_names"] and cpu.json_sha(names) == m["feature_names_sha256"], "feature schema reconstruction")
    demand(x_query.shape == (200, len(names)), "query feature shape")
    del x_fit, fit_labels
    model = lgb.Booster(params={"num_threads": 2}, model_file=str(ATOM / "model.txt"))
    demand(model.feature_name() == names and model.num_feature() == len(names), "saved model feature schema")
    demand(model.current_iteration() == m["selected_iteration"], "saved model tree count")
    prediction = model.predict(x_query, num_threads=2)
    delta = np.abs(prediction - expected_prediction)
    demand(prediction.shape == (200,) and np.isfinite(prediction).all(), "replay prediction shape")
    evidence = {"status": "REPLAY_VALUES_MATCH_UNSUPERVISED" if np.all(delta <= c["tolerance"]) else "REPLAY_MISMATCH",
                "config_sha256": cpu.sha(OUT / "frozen_config.json"), "fit_rows": len(fit), "query_rows": len(query),
                "oof_rows": 100, "outer_hold_rows": 100, "feature_count": len(names), "saved_iterations": model.current_iteration(),
                "max_abs_oof": float(delta[:100].max()), "max_abs_outer_hold": float(delta[100:].max()),
                "exact_equal_oof": bool(np.array_equal(prediction[:100], expected_prediction[:100])),
                "exact_equal_outer_hold": bool(np.array_equal(prediction[100:], expected_prediction[100:])),
                "fit_y_sha256_verified": True, "early_stop_scope_verified": True, "all_source_sha_verified_before_and_after": True,
                "official_ids_and_scope_verified": True, "training_performed": False, "query_labels_loaded": False,
                "auc_computed": False, "runtime_seconds": time.monotonic() - started, "is_new_blind_test": False}
    checked_config()
    cpu.atomic_json(OUT / "evidence.json", evidence)
    demand(np.all(delta <= c["tolerance"]), "saved-model replay exceeds frozen tolerance")


def run():
    c = checked_config()
    demand(not (OUT / "RUN_STARTED.json").exists(), "one-shot replay has already started; preserve evidence")
    started = time.monotonic()
    cpu.atomic_json(OUT / "RUN_STARTED.json", {"started_unix": time.time(), "config_sha256": cpu.sha(OUT / "frozen_config.json"), "supervisor_pid": os.getpid()})
    peak = 0
    failure = None
    with (OUT / "run.log").open("x") as log:
        child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "worker"], stdout=log, stderr=subprocess.STDOUT)
        try:
            while True:
                processes = [psutil.Process(os.getpid())] + psutil.Process(os.getpid()).children(recursive=True)
                rss = 0
                for process in processes:
                    try:
                        rss += process.memory_info().rss
                    except psutil.NoSuchProcess:
                        pass
                peak = max(peak, rss)
                elapsed = time.monotonic() - started
                if elapsed >= c["seconds"] or peak > c["process_tree_rss_bytes"]:
                    failure = "TIME_BUDGET" if elapsed >= c["seconds"] else "MEMORY_BUDGET"
                    for process in processes[1:]:
                        try:
                            process.kill()
                        except psutil.NoSuchProcess:
                            pass
                    child.wait(timeout=5)
                    break
                if child.poll() is not None:
                    break
                time.sleep(.25)
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=5)
    elapsed = time.monotonic() - started
    if elapsed >= c["seconds"] and failure is None:
        failure = "TIME_BUDGET"
    if child.returncode != 0 and failure is None:
        failure = "WORKER_FAILED"
    result = {"status": "PASS" if failure is None else "FAILED", "failure": failure, "returncode": child.returncode,
              "seconds": elapsed, "peak_process_tree_rss_bytes": peak, "threads": 2,
              "config_sha256": cpu.sha(OUT / "frozen_config.json"), "evidence_sha256": cpu.sha(OUT / "evidence.json") if (OUT / "evidence.json").exists() else None,
              "training_performed": False, "auc_computed": False, "query_labels_loaded": False}
    cpu.atomic_json(OUT / "result.json", result)
    if failure is not None:
        raise RuntimeError(json.dumps(result))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["freeze", "run", "worker"])
    args = parser.parse_args()
    with threadpool_limits(limits=2):
        answer = {"freeze": freeze, "run": run, "worker": worker}[args.mode]()
    if answer is not None:
        print(json.dumps(answer))
