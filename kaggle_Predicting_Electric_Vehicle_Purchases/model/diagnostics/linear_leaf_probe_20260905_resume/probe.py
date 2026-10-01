#!/usr/bin/env python3
"""strict-v96 常数叶子与线性叶子的配对诊断；资源监督与历史产物隔离。"""
from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time
from typing import Any

for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "6"

import lightgbm as lgb
import numpy as np
import pandas as pd
import psutil
import scipy
import sklearn
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

OUT = Path(__file__).resolve().parent
PROJECT = OUT.parents[2]
MODEL = PROJECT / "model"
V96 = MODEL / "v96_strict_v80_outer42_matched_control_40f"
V100 = MODEL / "v100_v90_ctboost_nested_cv_blend"
EXPERIMENT = "TEMP_STRICT_LINEAR_LEAF_AB_SEED42_RESUME"
CONFIG = OUT / "frozen_config.json"
MARKER = OUT / "RUN_STARTED.json"
EVIDENCE = OUT / "evidence.json"
PENDING = OUT / "evidence.pending.json"
WALL = 1800.0
MEMORY = 8 * 1024**3
COMMON = {"n_jobs": 6, "device_type": "cpu", "tree_learner": "serial", "linear_lambda": 0.0}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def array_sha(value: np.ndarray) -> str:
    value = np.ascontiguousarray(value)
    h = hashlib.sha256(f"{value.dtype}|{value.shape}".encode())
    h.update(memoryview(value).cast("B"))
    return h.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with tmp.open("x", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def load_module(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("linear_leaf_v96", path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_paths() -> dict[str, Path]:
    return {
        "runner": Path(__file__),
        "preregistration": OUT / "PREREGISTRATION.md",
        "v96_runner": V96 / "v96_strict_v80_outer42_matched_control_40f.py",
        "v96_config": V96 / "frozen_config.json",
        "v29_recipe": MODEL / "v29_income_bin10_te_lgbm/v29_income_bin10_te_lgbm.py",
        "v6_static_recipe_only": MODEL / "v6_multiscale_te_lgbm/v6_multiscale_te_lgbm.py",
        "train": PROJECT / "data/train.csv",
        "test_features_only": PROJECT / "data/test.csv",
        "sample_identity_only": PROJECT / "data/sample_submission.csv",
        "v100_oof": V100 / "oof_proba.npy",
        "v100_cv": V100 / "cv_results.json",
        "v100_sources": V100 / "sources.json",
    }


def design() -> dict[str, Any]:
    base = json.loads((V96 / "frozen_config.json").read_text())
    params = dict(base["lightgbm_params"]) | COMMON
    return {
        "experiment_id": EXPERIMENT,
        "outer_folds": 5, "outer_seed": 42,
        "n_inner_folds": base["n_inner_folds"],
        "inner_te_seed_base": base["inner_te_seed_base"], "smooths": base["smooths"],
        "lightgbm_params_common": params,
        "arm_a": {"linear_tree": False}, "arm_b": {"linear_tree": True},
        "early_stopping_rounds": base["early_stopping_rounds"],
        "scaler": "StandardScaler fitted to outer-fit only, shared A/B, float32 output",
        "static_features": 62, "te_features": 51,
        "strength_gate": {"delta": 0.0001, "minimum_positive_folds": 4},
        "wall_budget_seconds": WALL, "peak_rss_budget_bytes": MEMORY,
        "cpu_threads": 6, "submission_budget": 0, "test_predictions": False,
        "checkpoint_role": "DIAGNOSTIC_ONLY_NOT_ELIGIBLE_FOR_FUSION_OR_SUBMISSION",
        "counts_toward_c01": False,
        "environment": {"python": platform.python_version(), "lightgbm": lgb.__version__,
                        "numpy": np.__version__, "pandas": pd.__version__,
                        "sklearn": sklearn.__version__, "scipy": scipy.__version__},
        "sources": {key: {"path": str(path), "sha256": sha(path)} for key, path in source_paths().items()},
    }


def verify_contract(config: dict[str, Any]) -> None:
    if config["environment"]["lightgbm"] != "4.6.0" or lgb.__version__ != "4.6.0":
        raise ValueError("LightGBM 版本不匹配")
    for entry in config["sources"].values():
        if sha(Path(entry["path"])) != entry["sha256"]:
            raise ValueError(f"输入/源码发生漂移：{entry['path']}")
    v100 = json.loads((V100 / "cv_results.json").read_text())
    src = json.loads((V100 / "sources.json").read_text())
    if v100["status"] != "COMPLETE":
        raise ValueError("v100 不是 COMPLETE")
    if v100["artifact_sha256"]["oof_proba.npy"] != config["sources"]["v100_oof"]["sha256"]:
        raise ValueError("v100 OOF 与已完成产物哈希不一致")
    if src["source_sha256"]["train.csv"] != config["sources"]["train"]["sha256"]:
        raise ValueError("v100 与本次 train 数据身份不一致")
    a = config["lightgbm_params_common"] | config["arm_a"]
    b = config["lightgbm_params_common"] | config["arm_b"]
    if {k for k in a if a[k] != b[k]} != {"linear_tree"}:
        raise ValueError("A/B 差异超出线性叶子")


def audit() -> dict[str, Any]:
    current = design()
    verify_contract(current)
    if CONFIG.exists():
        if json.loads(CONFIG.read_text()) != current:
            raise ValueError("已有冻结合同与当前设计不同，拒绝覆盖")
    else:
        atomic_json(CONFIG, current)
    return {"status": "AUDIT_PASS", "config_sha256": sha(CONFIG), "environment": current["environment"]}


def smoke() -> dict[str, Any]:
    rng = np.random.default_rng(319)
    fit = rng.normal(size=(768, 6)).astype(np.float32)
    hold = (rng.normal(size=(128, 6)) + 5).astype(np.float32)
    y = (fit[:, 0] + 0.5 * fit[:, 1] + rng.normal(size=768) > 0).astype(np.int8)
    scaler = StandardScaler().fit(fit)
    assert np.allclose(scaler.mean_, fit.mean(axis=0, dtype=np.float64))
    assert not np.allclose(scaler.mean_, np.concatenate([fit, hold]).mean(axis=0))
    fit = scaler.transform(fit).astype(np.float32)
    hold = scaler.transform(hold).astype(np.float32)
    config = design()
    outcomes = {}
    for arm, linear in (("a", False), ("b", True)):
        params = config["lightgbm_params_common"] | {"n_estimators": 8, "linear_tree": linear}
        model = lgb.LGBMClassifier(**params).fit(fit, y)
        p = model.predict_proba(hold)[:, 1]
        assert p.shape == (128,) and np.isfinite(p).all() and ((p >= 0) & (p <= 1)).all()
        def leaves(node):
            if "leaf_value" in node:
                return [node]
            return leaves(node["left_child"]) + leaves(node["right_child"])
        nodes = [n for t in model.booster_.dump_model()["tree_info"] for n in leaves(t["tree_structure"])]
        linear_nodes = sum(bool(n.get("leaf_coeff", [])) for n in nodes)
        assert bool(linear_nodes) == linear
        outcomes[arm] = {"linear_tree": linear, "finite_probabilities": True, "nonconstant_linear_leaves": linear_nodes}
    source = load_module(V96 / "v96_strict_v80_outer42_matched_control_40f.py")
    source.strict_prior_self_check()
    result = {"status": "SMOKE_PASS", "synthetic_only": True, "scaler_fit_only": True,
              "strict_prior_self_check": True, "arms": outcomes, "runner_sha256": sha(Path(__file__))}
    atomic_json(OUT / "smoke.json", result)
    return result


def check_budget(start_epoch: float, phase: str) -> None:
    elapsed = time.time() - start_epoch
    rss = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    if sys.platform != "darwin":
        rss *= 1024
    if elapsed > WALL or rss > MEMORY:
        raise RuntimeError(f"RESOURCE_BUDGET {phase} elapsed={elapsed} peak_rss={rss}")


def checkpoint(fold: int, arrays: dict[str, np.ndarray], row: dict[str, Any], contract_sha: str) -> None:
    folder = OUT / "checkpoints"
    folder.mkdir(exist_ok=True)
    path = folder / f"fold_{fold:02d}.npz"
    meta = folder / f"fold_{fold:02d}.json"
    if path.exists() or meta.exists():
        raise FileExistsError("不覆盖已有 checkpoint")
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with tmp.open("xb") as handle:
        np.savez_compressed(handle, **arrays)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    atomic_json(meta, {"diagnostic_only": True, "config_sha256": contract_sha,
                       "checkpoint_sha256": sha(path), "array_sha256": {k: array_sha(v) for k, v in arrays.items()},
                       "row": row})


def load_checkpoint(fold: int, valid: np.ndarray, contract_sha: str) -> tuple[dict, dict] | None:
    path = OUT / f"checkpoints/fold_{fold:02d}.npz"
    meta_path = path.with_suffix(".json")
    if not path.exists() and not meta_path.exists():
        return None
    meta = json.loads(meta_path.read_text())
    if meta["config_sha256"] != contract_sha or sha(path) != meta["checkpoint_sha256"]:
        raise ValueError("checkpoint 合同或文件哈希不一致")
    with np.load(path, allow_pickle=False) as raw:
        arrays = {k: raw[k] for k in raw.files}
    for key, value in arrays.items():
        if array_sha(value) != meta["array_sha256"][key]:
            raise ValueError("checkpoint 数组哈希不一致")
    if not np.array_equal(arrays["valid_idx"], valid):
        raise ValueError("checkpoint 行序不一致")
    return arrays, meta["row"]


def slice_metrics(train: pd.DataFrame, y: np.ndarray, a: np.ndarray, b: np.ndarray, core: np.ndarray) -> list[dict]:
    masks = {"income_30000": train.Annual_Income_USD.eq(30000), "income_not_30000": train.Annual_Income_USD.ne(30000)}
    for col, values in (("Environmental_Concern_Level", [1, 2, 3, 4, 5]), ("Subsidy_Available", ["Yes", "No"]), ("Range_Anxiety_Level", ["Low", "Medium", "High"])):
        for value in values:
            masks[f"{col}={value}"] = train[col].eq(value)
    freq = train.Annual_Income_USD.map(train.Annual_Income_USD.value_counts()).to_numpy()
    masks |= {"income_freq_lt10": freq < 10, "income_freq_10_99": (freq >= 10) & (freq < 100),
              "income_freq_100_499": (freq >= 100) & (freq < 500), "income_freq_ge500": freq >= 500}
    rows = []
    for name, mask in masks.items():
        mask = np.asarray(mask)
        row = {"slice": name, "n": int(mask.sum()), "positive": int(y[mask].sum())}
        if len(np.unique(y[mask])) == 2:
            aa, bb, cc = [float(roc_auc_score(y[mask], p[mask])) for p in (a, b, core)]
            row |= {"auc_a": aa, "auc_b": bb, "auc_v100": cc, "delta_b_minus_a": bb-aa,
                    "delta_b_minus_v100": bb-cc, "delta_a_minus_v100": aa-cc}
        else:
            row["auc_unavailable_reason"] = "切片标签不足两类"
        rows.append(row)
    return rows


def worker() -> None:
    config = json.loads(CONFIG.read_text())
    contract_sha = sha(CONFIG)
    verify_contract(config)
    marker = json.loads(MARKER.read_text())
    started = marker["start_epoch"]
    atomic_json(OUT / "worker.json", {"pid": os.getpid(), "config_sha256": contract_sha})
    source = load_module(V96 / "v96_strict_v80_outer42_matched_control_40f.py")
    recipe = source.load_recipe()
    train, test, sample = recipe.base.load_data()
    y = train.Will_Buy_EV.eq("Yes").to_numpy(np.int8)
    train_ids = train.id.to_numpy(np.int64)
    static, static_test, keys, test_keys = recipe.base.build_static_features(train, test)
    del static_test, sample, test
    if len(y) != 668665 or static.shape[1] != 62 or len(keys) != 17:
        raise ValueError("数据规模或特征合同漂移")
    core = np.load(V100 / "oof_proba.npy", allow_pickle=False)
    expected = json.loads((V100 / "cv_results.json").read_text())["oof_auc"]
    if core.shape != y.shape or not np.isfinite(core).all() or ((core < 0) | (core > 1)).any():
        raise ValueError("v100 概率非法")
    if abs(float(roc_auc_score(y, core)) - expected) > 1e-14:
        raise ValueError("v100 AUC 与冻结数据不一致")
    oof = {arm: np.full(len(y), np.nan) for arm in ("a", "b")}
    rows = []
    for fold, (fit_idx, valid_idx) in enumerate(StratifiedKFold(5, shuffle=True, random_state=42).split(static, y), 1):
        check_budget(started, f"FOLD_{fold}_START")
        saved = load_checkpoint(fold, valid_idx, contract_sha)
        if saved is not None:
            arrays, row = saved
            if not np.array_equal(arrays["train_id"], train_ids[valid_idx]):
                raise ValueError("checkpoint ID 不匹配")
            for arm in oof:
                oof[arm][valid_idx] = arrays[arm]
            rows.append(row)
            continue
        inner = list(StratifiedKFold(config["n_inner_folds"], shuffle=True,
                       random_state=config["inner_te_seed_base"] + fold).split(np.zeros(len(fit_idx)), y[fit_idx]))
        fit_te, valid_te = [], []
        for key in recipe.base.TE_KEYS:
            fit_block, valid_block, _ = source.strict_encode_key(keys[key], test_keys[key], y, fit_idx, valid_idx, inner, tuple(config["smooths"]))
            fit_te.append(fit_block)
            valid_te.append(valid_block)
        xfit = np.column_stack([static.iloc[fit_idx].to_numpy(np.float32), *fit_te])
        xvalid = np.column_stack([static.iloc[valid_idx].to_numpy(np.float32), *valid_te])
        del fit_te, valid_te
        if xfit.shape[1] != 113 or not np.isfinite(xfit).all() or not np.isfinite(xvalid).all():
            raise ValueError("输入矩阵非法")
        scaler = StandardScaler(copy=False)
        xfit = np.ascontiguousarray(scaler.fit_transform(xfit), dtype=np.float32)
        xvalid = np.ascontiguousarray(scaler.transform(xvalid), dtype=np.float32)
        fit_sha, valid_sha = array_sha(xfit), array_sha(xvalid)
        row = {"fold": fold, "fit_n": len(fit_idx), "valid_n": len(valid_idx),
               "input_fit_sha256": fit_sha, "input_valid_sha256": valid_sha,
               "scaler_mean_sha256": array_sha(scaler.mean_), "scaler_scale_sha256": array_sha(scaler.scale_),
               "scaler_fit_rows": int(scaler.n_samples_seen_),
               "auc_v100_same_rows": float(roc_auc_score(y[valid_idx], core[valid_idx]))}
        def budget_callback(env):
            check_budget(started, f"FOLD_{fold}_ITER_{env.iteration}")
        budget_callback.order = 0
        for arm in ("a", "b"):
            check_budget(started, f"FOLD_{fold}_{arm}_START")
            arm_start = time.monotonic()
            params = config["lightgbm_params_common"] | config[f"arm_{arm}"]
            model = lgb.LGBMClassifier(**params)
            with threadpool_limits(limits=6):
                model.fit(xfit, y[fit_idx], eval_set=[(xvalid, y[valid_idx])], eval_metric="auc",
                    callbacks=[budget_callback, lgb.early_stopping(config["early_stopping_rounds"], verbose=False), lgb.log_evaluation(0)])
                pred = model.predict_proba(xvalid, num_iteration=model.best_iteration_)[:, 1]
            if not np.isfinite(pred).all() or ((pred < 0) | (pred > 1)).any():
                raise ValueError("模型概率非法")
            if array_sha(xfit) != fit_sha or array_sha(xvalid) != valid_sha:
                raise ValueError("某臂训练意外修改了共用输入")
            oof[arm][valid_idx] = pred
            row |= {f"auc_{arm}": float(roc_auc_score(y[valid_idx], pred)),
                    f"best_iteration_{arm}": int(model.best_iteration_), f"elapsed_seconds_{arm}": time.monotonic()-arm_start}
            print(json.dumps({"event": "ARM_COMPLETE", "fold": fold, "arm": arm, "auc": row[f"auc_{arm}"], "best_iteration": row[f"best_iteration_{arm}"]}), flush=True)
            del model
            gc.collect()
        row |= {"delta_b_minus_a": row["auc_b"] - row["auc_a"],
                "delta_b_minus_v100_same_rows": row["auc_b"] - row["auc_v100_same_rows"],
                "elapsed_since_start": time.time()-started}
        checkpoint(fold, {"valid_idx": valid_idx, "train_id": train_ids[valid_idx], "y": y[valid_idx],
                           "a": oof["a"][valid_idx], "b": oof["b"][valid_idx]}, row, contract_sha)
        rows.append(row)
        atomic_json(OUT / "progress.json", {"status": "RUNNING", "config_sha256": contract_sha, "folds": rows})
        print(json.dumps({"event": "FOLD_COMPLETE", **row}), flush=True)
        del xfit, xvalid
        gc.collect()
    if any(not np.isfinite(p).all() for p in oof.values()):
        raise ValueError("OOF coverage 不完整")
    aa, bb, cc = [float(roc_auc_score(y, p)) for p in (oof["a"], oof["b"], core)]
    wins = sum(r["delta_b_minus_a"] > 0 for r in rows)
    passed = bb-aa >= 0.0001 and wins >= 4
    payload = {"status": "WORKER_COMPLETE_PENDING_RESOURCE_AUDIT", "experiment_id": EXPERIMENT,
               "config_sha256": contract_sha, "diagnostic_only": True, "counts_toward_c01": False,
               "test_generated": False, "submission_generated": False, "reusable_oof_saved": False,
               "folds": rows, "train_id_sha256": array_sha(train_ids),
               "aggregate": {"auc_a": aa, "auc_b": bb, "auc_v100": cc, "delta_b_minus_a": bb-aa,
                 "delta_b_minus_v100": bb-cc, "winning_folds": wins,
                 "spearman_b_vs_v100": float(spearmanr(oof["b"], core).statistic),
                 "strength_gate_passed": passed, "decision": "FORMAL_40F_PREREGISTRATION_GO" if passed else "NO_GO"},
               "slices": slice_metrics(train, y, oof["a"], oof["b"], core),
               "comparability_note": "仅 A/B 是同训练合同配对；v100 使用不同家族及原始折数，仅按同行掩码诊断差距，不据此归因或调权"}
    verify_contract(config)
    check_budget(started, "WORKER_COMPLETE")
    atomic_json(PENDING, payload)


def supervise(resume: bool) -> dict[str, Any]:
    config = json.loads(CONFIG.read_text())
    verify_contract(config)
    smoke_result = json.loads((OUT / "smoke.json").read_text())
    if smoke_result["status"] != "SMOKE_PASS" or smoke_result["runner_sha256"] != sha(Path(__file__)):
        raise ValueError("必须先完成当前源码的合成 smoke")
    if EVIDENCE.exists():
        raise RuntimeError("诊断已关闭，禁止重跑")
    if MARKER.exists():
        marker = json.loads(MARKER.read_text())
        if not resume or marker["config_sha256"] != sha(CONFIG):
            raise RuntimeError("实例 marker 已存在或恢复合同不一致")
        for path in (MARKER, OUT / "worker.json"):
            if path.exists() and psutil.pid_exists(json.loads(path.read_text())["pid"]):
                raise RuntimeError("已有同一实例仍在运行")
        marker["resume_pid"] = os.getpid()
    else:
        marker = {"pid": os.getpid(), "start_epoch": time.time(), "config_sha256": sha(CONFIG), "status": "ONE_SHOT_STARTED"}
        with MARKER.open("x") as f:
            json.dump(marker, f, indent=2)
    started = marker["start_epoch"]
    child = subprocess.Popen([sys.executable, "-u", str(Path(__file__)), "--mode", "worker"], env=os.environ.copy())
    process = psutil.Process(os.getpid())
    peak = 0
    breach = None
    print(json.dumps({"event": "STARTED", "supervisor_pid": os.getpid(), "worker_pid": child.pid, "config_sha256": sha(CONFIG)}), flush=True)
    try:
        while child.poll() is None:
            rss = process.memory_info().rss
            for descendant in process.children(recursive=True):
                try:
                    rss += descendant.memory_info().rss
                except psutil.Error:
                    pass
            peak = max(peak, rss)
            elapsed = time.time()-started
            if peak > MEMORY or elapsed > WALL:
                breach = {"attribution": "MEMORY_BUDGET" if peak > MEMORY else "WALL_BUDGET", "elapsed_seconds": elapsed, "rss_bytes": rss}
                child.terminate()
                try:
                    child.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
                break
            time.sleep(0.5)
    except BaseException:
        child.terminate()
        try:
            child.wait(timeout=2)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
        raise
    elapsed = time.time()-started
    if child.returncode != 0 or breach or not PENDING.exists() or elapsed > WALL:
        progress = json.loads((OUT / "progress.json").read_text()) if (OUT / "progress.json").exists() else {"folds": []}
        payload = {"status": "FAILED_RESOURCE_BUDGET" if breach or elapsed > WALL else "FAILED_IMPLEMENTATION",
                   "experiment_id": EXPERIMENT, "diagnostic_only": True, "decision": "STOP_NO_SAME_CONFIG_RERUN",
                   "config_sha256": sha(CONFIG), "returncode": child.returncode, "breach": breach,
                   "elapsed_seconds": elapsed, "peak_process_tree_rss_bytes": peak, "folds": progress["folds"]}
    else:
        verify_contract(config)
        payload = json.loads(PENDING.read_text())
        payload |= {"status": "COMPLETE", "elapsed_seconds": elapsed, "peak_process_tree_rss_bytes": peak,
                    "resource_budget_passed": True, "supervisor_pid": os.getpid(), "worker_pid": child.pid}
    atomic_json(EVIDENCE, payload)
    return payload


def verify() -> dict[str, Any]:
    config = json.loads(CONFIG.read_text())
    verify_contract(config)
    evidence = json.loads(EVIDENCE.read_text())
    if evidence["status"] != "COMPLETE":
        return {"status": "CLOSED_FAILURE", "evidence_status": evidence["status"], "completed_folds": len(evidence["folds"])}
    train = pd.read_csv(PROJECT / "data/train.csv")
    y = train.Will_Buy_EV.eq("Yes").to_numpy(np.int8)
    a, b, coverage = np.full(len(y), np.nan), np.full(len(y), np.nan), np.zeros(len(y), np.int8)
    for fold, (_, valid) in enumerate(StratifiedKFold(5, shuffle=True, random_state=42).split(np.zeros(len(y)), y), 1):
        arrays, row = load_checkpoint(fold, valid, sha(CONFIG))
        assert np.array_equal(arrays["y"], y[valid]) and np.array_equal(arrays["train_id"], train.id.to_numpy()[valid])
        a[valid], b[valid] = arrays["a"], arrays["b"]
        coverage[valid] += 1
        for arm in ("a", "b"):
            assert abs(float(roc_auc_score(y[valid], arrays[arm])) - row[f"auc_{arm}"]) < 1e-14
        assert row == evidence["folds"][fold-1]
    assert (coverage == 1).all()
    assert abs(float(roc_auc_score(y, a))-evidence["aggregate"]["auc_a"]) < 1e-14
    assert abs(float(roc_auc_score(y, b))-evidence["aggregate"]["auc_b"]) < 1e-14
    return {"status": "VERIFY_PASS", "coverage_exactly_once": True, "config_sha256": sha(CONFIG), "evidence_sha256": sha(EVIDENCE)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("audit", "smoke", "run", "worker", "verify"), default="audit")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.mode == "worker":
        worker()
        return
    result = {"audit": audit, "smoke": smoke, "run": lambda: supervise(args.resume), "verify": verify}[args.mode]()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2), flush=True)


if __name__ == "__main__":
    main()
