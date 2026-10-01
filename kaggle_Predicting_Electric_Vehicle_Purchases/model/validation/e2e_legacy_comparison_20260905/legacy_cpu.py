#!/usr/bin/env python3
"""Conditional C cache: train F, early-stop H, never expose outer U labels."""
from __future__ import annotations
import argparse
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid
import psutil
from legacy_gate import need, number, read, sha, validate_authorization, verify_authorized_ab

OUT = Path(__file__).resolve().parent
AB = OUT.parent / "e2e_v100_20260905"
PROJECT = OUT.parents[2]
THREAD_KEYS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS", "BLIS_NUM_THREADS")


def save(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + f".tmp.{os.getpid()}")
    with temp.open("x") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
    os.replace(temp, path)


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def runtime():
    prior = {key: os.environ.get(key, "2") for key in THREAD_KEYS}
    if str(AB) not in sys.path:
        sys.path.insert(0, str(AB))
    import cpu_runner
    for key, value in prior.items():
        os.environ[key] = value
    return cpu_runner


def owned_sources():
    return ["legacy_cpu.py", "legacy_gate.py", "test_legacy_cpu.py", "PREREGISTRATION.md", "PREREGISTRATION_R01.md", "selection_revision.json"]


def freeze():
    need(not (OUT / "frozen_config.json").exists(), "C config already frozen")
    cpu = runtime(); base = cpu.load_config()
    evidence = read(OUT / "cpu_test_results.json")
    reviewed = read(OUT / "CPU_REVIEW.json")
    hashes = {name: sha(OUT / name) for name in owned_sources()}
    need(evidence.get("status") == "PASS" and evidence.get("failures") == 0 and evidence.get("errors") == 0 and type(evidence.get("tests_run")) is int and evidence["tests_run"] >= 22, "synthetic tests not successful")
    need(evidence.get("code_sha256") == {name: hashes[name] for name in owned_sources() if name.endswith(".py")}, "synthetic test source drift")
    need(reviewed.get("status") == "PASS" and reviewed.get("source_sha256") == hashes, "independent CPU review missing or stale")
    sources = dict(base["sources"])
    for name in [*owned_sources(), "cpu_test_results.json", "CPU_REVIEW.json"]:
        sources[str((OUT / name).relative_to(PROJECT))] = sha(OUT / name)
    for path in (AB / "frozen_config.json", AB / "splits.npz", AB / "assembly_config.json", AB / "orchestration/config.json"):
        sources[str(path.relative_to(PROJECT))] = sha(path)
    config = {"schema_version": 1, "experiment_id": "E2E_LEGACY_C_20260905", "sources": sources,
              "ab_cpu_config_sha256": sha(AB / "frozen_config.json"), "splits_sha256": sha(AB / "splits.npz"),
              "families": base["families"], "outer_plan": base["outer_plan"], "train_rows": base["train_rows"],
              "train_id_sha256": base["train_id_sha256"], "versions": base["versions"],
              "cpu_seconds": 21600, "threads": 8, "memory_bytes": 24 * 1024**3, "outer_seed": 42437,
              "fit_rule": "F_TRAIN_H_EARLY_STOP_SAME_MODEL_NO_REFIT", "expected_atoms": 400, "expected_caches": 10,
              "feature_schema": {"v80": {"columns": 113, "dtype": "float32"}, "v85": {"columns": 148, "dtype": "float64"}},
              "allowed_for_submission": False, "is_new_blind_test": False, "automatic_restart": False}
    save(OUT / "frozen_config.json", config)
    return {"status": "FROZEN_NOT_STARTED", "config_sha256": sha(OUT / "frozen_config.json")}


def load_config():
    c = read(OUT / "frozen_config.json")
    need(c["cpu_seconds"] == 21600 and c["threads"] == 8 and c["memory_bytes"] == 24 * 1024**3, "C resource contract drift")
    need(c["fit_rule"] == "F_TRAIN_H_EARLY_STOP_SAME_MODEL_NO_REFIT" and c["expected_atoms"] == 400 and c["expected_caches"] == 10, "C algorithm drift")
    for name, digest in c["sources"].items():
        need(sha(PROJECT / name) == digest, "C frozen source changed: " + name)
    base = runtime().load_config()
    need(c["families"] == base["families"] and c["versions"] == base["versions"] and c["outer_plan"] == base["outer_plan"], "C differs from fixed CPU recipe")
    need(c["splits_sha256"] == sha(AB / "splits.npz") and c["ab_cpu_config_sha256"] == sha(AB / "frozen_config.json"), "C split/config source drift")
    return c


def authorize(c):
    import numpy as np
    with np.load(AB / "splits.npz", allow_pickle=False) as splits:
        rows = {i: len(splits[f"outer_{i:02d}_valid_idx"]) for i in range(1, 6)}
    ab = module(AB / "assemble_e2e.py", "legacy_bound_ab_gate")
    return verify_authorized_ab(OUT, sha(OUT / "frozen_config.json"), rows, ab)


def cheap_start_config():
    """Small local metadata only; full graph checks run in the supervised worker."""
    c = read(OUT / "frozen_config.json")
    need(c["cpu_seconds"] == 21600 and c["threads"] == 8 and c["memory_bytes"] == 24 * 1024**3, "C fixed supervisor limits")
    for name in owned_sources():
        need(sha(OUT / name) == c["sources"][str((OUT / name).relative_to(PROJECT))], "C entrypoint source drift")
    auth = read(OUT / "START_AUTHORIZATION.json")
    validate_authorization(auth, sha(OUT / "frozen_config.json"))
    return c, {"authorization_sha256": sha(OUT / "START_AUTHORIZATION.json"), "ab_result_sha256": auth["prerequisite_files"]["e2e_results.json"], "prerequisite_files": auth["prerequisite_files"]}


def read_npz(path):
    import numpy as np
    with np.load(path, allow_pickle=False) as archive:
        return {name: archive[name] for name in archive.files}


def probability(values, rows):
    import numpy as np
    need(values.shape == (rows,) and values.dtype == np.dtype("float64") and np.isfinite(values).all() and np.all((values >= 0) & (values <= 1)), "C probability shape/precision/range")


def train_labels(indices, official_ids):
    import numpy as np
    import pandas as pd
    allowed = set(indices.tolist())
    data = pd.read_csv(PROJECT / "data/train.csv", usecols=["id", "Will_Buy_EV"], skiprows=lambda row: row > 0 and row - 1 not in allowed)
    need(np.array_equal(data.id.to_numpy(), official_ids[indices]), "T-only label identity mismatch")
    need(data.Will_Buy_EV.isin(["Yes", "No"]).all(), "T target values")
    return data.Will_Buy_EV.eq("Yes").to_numpy(np.int8)


def fit_legacy_atom(backend, fit_rows, fit_y, hold_rows, hold_y, outer_rows, params, te_seed, patience):
    """H labels intentionally select rounds; outer U labels have no parameter."""
    import numpy as np
    import lightgbm as lgb
    cpu = runtime()
    fit_rows, hold_rows, outer_rows = [np.asarray(x, dtype=np.int64) for x in (fit_rows, hold_rows, outer_rows)]
    fit_y, hold_y = np.asarray(fit_y, dtype=np.int8), np.asarray(hold_y, dtype=np.int8)
    need(len(fit_rows) == len(fit_y) and len(hold_rows) == len(hold_y), "C labels out of scope")
    for left, right in ((fit_rows, hold_rows), (fit_rows, outer_rows), (hold_rows, outer_rows)):
        need(not np.intersect1d(left, right).size, "C F/H/U overlap")
    query = np.concatenate([hold_rows, outer_rows])
    xf, xq, names = backend.encode(fit_rows, fit_y, query, te_seed)
    model = lgb.LGBMClassifier(**params)
    model.fit(xf, fit_y, eval_set=[(xq[:len(hold_rows)], hold_y)], eval_metric="auc", feature_name=names,
              callbacks=[lgb.early_stopping(patience, verbose=False), lgb.log_evaluation(0)])
    selected = int(model.best_iteration_ or params["n_estimators"])
    prediction = np.asarray(model.predict_proba(xq, num_iteration=selected)[:, 1], dtype=np.float64)
    probability(prediction, len(query))
    scope = {"fit_idx_sha256": cpu.arr_sha(fit_rows), "early_stop_hold_idx_sha256": cpu.arr_sha(hold_rows),
             "outer_valid_idx_sha256": cpu.arr_sha(outer_rows), "query_idx_sha256": cpu.arr_sha(query),
             "fit_y_sha256": cpu.arr_sha(fit_y), "early_stop_hold_y_sha256": cpu.arr_sha(hold_y),
             "te_seed": te_seed, "selected_iteration": selected, "params_sha256": cpu.json_sha(params),
             "feature_names": names, "feature_names_sha256": cpu.json_sha(names), "matrix_dtype": str(xq.dtype),
             "atom_hold_labels_used_for_early_stopping": True, "outer_hold_labels_used": False,
             "refit_performed": False, "training_fit_count": 1}
    return prediction, scope, model


def verify_atom(directory, outer, family, atom, fit_rows, hold_rows, outer_rows, ids, fit_y, hold_y, c, config_sha):
    import numpy as np
    cpu = runtime(); directory = Path(directory)
    m = read(directory / "manifest.json")
    expected = {"status": "C_ATOM_COMPLETE", "outer": outer, "family": family, "atom": atom, "config_sha256": config_sha,
                "input_sha256": c["sources"]["data/train.csv"], "splits_sha256": c["splits_sha256"],
                "fit_idx_sha256": cpu.arr_sha(fit_rows), "early_stop_hold_idx_sha256": cpu.arr_sha(hold_rows),
                "outer_valid_idx_sha256": cpu.arr_sha(outer_rows), "query_idx_sha256": cpu.arr_sha(np.concatenate([hold_rows, outer_rows])),
                "fit_y_sha256": cpu.arr_sha(fit_y), "early_stop_hold_y_sha256": cpu.arr_sha(hold_y),
                "fit_id_sha256": cpu.arr_sha(ids[fit_rows]), "early_stop_hold_id_sha256": cpu.arr_sha(ids[hold_rows]),
                "outer_valid_id_sha256": cpu.arr_sha(ids[outer_rows]), "te_seed": c["families"][family]["te_seed_base"] + atom,
                "params_sha256": cpu.json_sha(cpu.atom_params(family, c["families"][family], atom)),
                "atom_hold_labels_used_for_early_stopping": True, "outer_hold_labels_used": False,
                "refit_performed": False, "training_fit_count": 1}
    need(all(m.get(k) == v for k, v in expected.items()), "C atom scope/config mismatch")
    need(m["atom_hold_labels_used_for_early_stopping"] is True and m["outer_hold_labels_used"] is False and m["refit_performed"] is False, "C atom label flags")
    schema = c["feature_schema"][family]
    need(len(m["feature_names"]) == schema["columns"] and m["matrix_dtype"] == schema["dtype"] and cpu.json_sha(m["feature_names"]) == m["feature_names_sha256"], "C atom feature schema")
    need(type(m["selected_iteration"]) is int and 0 < m["selected_iteration"] <= c["families"][family]["params"]["n_estimators"], "C selected iteration")
    need(sha(directory / "model.txt") == m["model_sha256"] and sha(directory / "predictions.npz") == m["prediction_sha256"], "C atom artifact SHA mismatch")
    a = read_npz(directory / "predictions.npz")
    need(set(a) == {"oof_idx", "valid_idx", "oof_id", "valid_id", "oof_proba", "valid_proba"}, "C atom schema")
    for key, value in (("oof_idx", hold_rows), ("valid_idx", outer_rows), ("oof_id", ids[hold_rows]), ("valid_id", ids[outer_rows])):
        need(a[key].dtype.kind in "iu" and np.array_equal(a[key], value), "C atom query identity")
    probability(a["oof_proba"], len(hold_rows)); probability(a["valid_proba"], len(outer_rows))
    return a


def family_arrays(directory, outer, family, train, hold, ids, folds, c, config_sha, labels):
    import numpy as np
    cpu = runtime(); directory = Path(directory)
    need(folds.shape == train.shape and np.array_equal(np.unique(folds), np.arange(40)), "C family fold coverage")
    need(not np.intersect1d(train, hold).size and len(np.unique(train)) == len(train) and len(np.unique(hold)) == len(hold), "C family partition overlap")
    plan = c["outer_plan"][outer - 1]
    for key, value in (("train_idx", train), ("valid_idx", hold), ("train_id", ids[train]), ("valid_id", ids[hold])):
        need(cpu.arr_sha(value) == plan[key + "_sha256"], "C family frozen identity")
    need(cpu.arr_sha(folds) == plan["atoms"][family]["fold_ids_sha256"], "C family frozen atom folds")
    oof = np.full(len(train), np.nan); valid = np.zeros(len(hold)); hashes = {}
    for atom in range(1, 41):
        local = np.flatnonzero(folds == atom - 1); fit = np.flatnonzero(folds != atom - 1)
        part = directory / f"atom_{atom:02d}"
        a = verify_atom(part, outer, family, atom, train[fit], train[local], hold, ids, labels[fit], labels[local], c, config_sha)
        oof[local] = a["oof_proba"]; valid += a["valid_proba"] / 40
        hashes[str(atom)] = sha(part / "manifest.json")
    probability(oof, len(train)); probability(valid, len(hold))
    return {"train_idx": train, "valid_idx": hold, "train_id": ids[train], "valid_id": ids[hold], "oof_proba": oof, "valid_proba": valid, "atom_fold": folds}, hashes


def cache_manifest(outer, family, arrays, hashes, c, config_sha, cache_sha):
    cpu = runtime()
    return {"status": "C_CACHE_COMPLETE_UNSCORED", "outer": outer, "family": family, "config_sha256": config_sha,
            "input_sha256": c["sources"]["data/train.csv"], "splits_sha256": c["splits_sha256"], "cache_sha256": cache_sha,
            **{key + "_sha256": cpu.arr_sha(arrays[key]) for key in ("train_idx", "valid_idx", "train_id", "valid_id")},
            "atom_manifest_sha256": hashes, "outer_hold_labels_used": False,
            "atom_hold_labels_used_for_early_stopping": True, "allowed_for_submission": False}


def check_family_cache(directory, outer, family, train, hold, ids, folds, config_sha, input_sha, splits_sha):
    import numpy as np
    c = read(OUT / "frozen_config.json")
    need(sha(OUT / "frozen_config.json") == config_sha and c["sources"]["data/train.csv"] == input_sha and c["splits_sha256"] == splits_sha, "C cache source contract")
    rebuilt, hashes = family_arrays(directory, outer, family, train, hold, ids, folds, c, config_sha, train_labels(train, ids))
    stored = read_npz(Path(directory) / "cache.npz")
    need(set(stored) == set(rebuilt), "C cache schema")
    for key, value in rebuilt.items():
        need(stored[key].dtype == value.dtype and np.array_equal(stored[key], value), "C cache reconstruction mismatch: " + key)
    expected = cache_manifest(outer, family, rebuilt, hashes, c, config_sha, sha(Path(directory) / "cache.npz"))
    need(read(Path(directory) / "cache_manifest.json") == expected, "C cache manifest mismatch")
    return stored


def preflight_existing_checkpoints(c, splits, ids):
    """Check every existing atom/cache before the first new fit, including gaps."""
    import numpy as np
    count = 0; config_sha = sha(OUT / "frozen_config.json")
    for outer in range(1, 6):
        train, hold = splits[f"outer_{outer:02d}_train_idx"], splits[f"outer_{outer:02d}_valid_idx"]
        directories = [OUT / f"outer_{outer:02d}" / family for family in ("v80", "v85")]
        if not any(directory.exists() for directory in directories):
            continue
        labels = train_labels(train, ids)
        for family, directory in zip(("v80", "v85"), directories):
            if not directory.exists():
                continue
            allowed = {f"atom_{a:02d}" for a in range(1, 41)} | {"cache.npz", "cache_manifest.json"}
            need({path.name for path in directory.iterdir()}.issubset(allowed), "unexpected C checkpoint artifact requires review")
            folds = splits[f"outer_{outer:02d}_{family}_fold"]
            for atom in range(1, 41):
                part = directory / f"atom_{atom:02d}"
                if not part.exists():
                    continue
                need((part / "manifest.json").is_file(), "partial C atom requires explicit recovery review")
                local, fit = np.flatnonzero(folds == atom - 1), np.flatnonzero(folds != atom - 1)
                verify_atom(part, outer, family, atom, train[fit], train[local], hold, ids, labels[fit], labels[local], c, config_sha)
                count += 1
            cache_exists, manifest_exists = (directory / "cache.npz").exists(), (directory / "cache_manifest.json").exists()
            need(cache_exists == manifest_exists, "partial C family cache requires review")
            if cache_exists:
                check_family_cache(directory, outer, family, train, hold, ids, folds, config_sha, c["sources"]["data/train.csv"], c["splits_sha256"])
    return count


def matching_process_alive(pid, created):
    try:
        process = psutil.Process(pid)
        return abs(process.create_time() - created) < .01 and process.is_running() and process.status() != psutil.STATUS_ZOMBIE
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        return False


def process_identity(pid):
    process = psutil.Process(pid)
    return {"pid": pid, "created": process.create_time()}


def watchdog_parent_lost(start):
    return not matching_process_alive(start["supervisor_pid"], start["supervisor_created"])


def parent_guard(parent_pid, parent_created, worker_pid, worker_created, ready_path):
    """A separate process remains responsive during native feature/LightGBM calls."""
    need(os.getppid() == worker_pid, "watchdog must be spawned by its worker")
    need(os.getpgid(worker_pid) == worker_pid, "worker must own an isolated process group")
    save(Path(ready_path), {"worker_pid": worker_pid, "worker_created": worker_created, "watchdog_pid": os.getpid(), "parent_pid": parent_pid, "parent_created": parent_created})
    try:
        while matching_process_alive(worker_pid, worker_created):
            if not matching_process_alive(parent_pid, parent_created):
                os.killpg(worker_pid, signal.SIGKILL)
                return
            time.sleep(.25)
    except BaseException:
        try:
            os.killpg(worker_pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        raise


def spawn_parent_guard(parent_pid, parent_created, ready_path):
    """Caller is a worker with its own process group; caller must stop guard on exit."""
    ready_path = Path(ready_path)
    need(not ready_path.exists() and os.getpgid(os.getpid()) == os.getpid(), "parent guard requires a fresh isolated worker")
    identity = process_identity(os.getpid())
    guard = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "parent-guard", "--parent-pid", str(parent_pid), "--parent-created", str(parent_created),
                              "--worker-pid", str(identity["pid"]), "--worker-created", str(identity["created"]), "--ready-path", str(ready_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.monotonic() + 5
        while not ready_path.exists():
            need(guard.poll() is None and time.monotonic() < deadline and matching_process_alive(parent_pid, parent_created), "parent watchdog failed before preflight")
            time.sleep(.05)
        record = read(ready_path)
        need(record["worker_pid"] == identity["pid"] and record["worker_created"] == identity["created"] and record["parent_pid"] == parent_pid and record["parent_created"] == parent_created and guard.poll() is None, "parent watchdog identity mismatch")
        return guard
    except BaseException:
        guard.terminate()
        try:
            guard.wait(timeout=3)
        except subprocess.TimeoutExpired:
            guard.kill(); guard.wait(timeout=3)
        raise


def worker(attempt):
    attempt = Path(attempt); start = read(attempt / "STARTED.json")
    need(attempt.parent == OUT / "runtime" and os.getppid() == start["supervisor_pid"] and not watchdog_parent_lost(start), "worker parent identity mismatch")
    need(os.environ.get("LEGACY_C_SUPERVISED_TOKEN") == start["worker_token"], "direct unsupervised worker refused")
    guard = spawn_parent_guard(start["supervisor_pid"], start["supervisor_created"], attempt / "WATCHDOG_READY.json")
    try:
        _worker_payload(attempt)
    finally:
        guard.terminate()
        try:
            guard.wait(timeout=3)
        except subprocess.TimeoutExpired:
            guard.kill(); guard.wait(timeout=3)


def _worker_payload(attempt):
    import numpy as np
    import pandas as pd
    import gc
    from threadpoolctl import threadpool_limits
    attempt = Path(attempt)
    need(attempt.parent == OUT / "runtime", "invalid worker attempt path")
    start = read(attempt / "STARTED.json")
    need(os.getppid() == start["supervisor_pid"] and os.environ.get("LEGACY_C_SUPERVISED_TOKEN") == start["worker_token"], "direct unsupervised worker refused")
    c = load_config(); binding = authorize(c); config_sha = sha(OUT / "frozen_config.json")
    need(binding["authorization_sha256"] == start["authorization_sha256"], "worker authorization changed")
    cpu = runtime(); splits = read_npz(AB / "splits.npz")
    ids = pd.read_csv(PROJECT / "data/train.csv", usecols=["id"]).id.to_numpy()
    need(cpu.arr_sha(ids) == c["train_id_sha256"] and len(ids) == c["train_rows"], "C official IDs drift")
    verified_count = preflight_existing_checkpoints(c, splits, ids)
    save(attempt / "PREFLIGHT_PASS.json", {"status": "PREFLIGHT_PASS_UNSCORED", "config_sha256": config_sha,
         "authorization_sha256": binding["authorization_sha256"], "validated_existing_atoms": verified_count, "new_models_fitted": 0})
    counts = 0; caches = {}
    with threadpool_limits(limits=8):
        for outer in range(1, 6):
            train, hold = splits[f"outer_{outer:02d}_train_idx"], splits[f"outer_{outer:02d}_valid_idx"]
            labels = train_labels(train, ids)
            for family in ("v80", "v85"):
                backend = cpu.load_backend(family); folds = splits[f"outer_{outer:02d}_{family}_fold"]
                directory = OUT / f"outer_{outer:02d}" / family
                for atom in range(1, 41):
                    fit = np.flatnonzero(folds != atom - 1); local = np.flatnonzero(folds == atom - 1)
                    part = directory / f"atom_{atom:02d}"
                    if (part / "manifest.json").exists():
                        verify_atom(part, outer, family, atom, train[fit], train[local], hold, ids, labels[fit], labels[local], c, config_sha)
                        counts += 1
                        print(f"RESUME_VERIFIED outer={outer} family={family} atom={atom}", flush=True)
                        continue
                    need(not part.exists(), "partial atom directory requires explicit recovery review")
                    part.mkdir(parents=True)
                    started = time.monotonic(); contract = c["families"][family]
                    prediction, scope, model = fit_legacy_atom(backend, train[fit], labels[fit], train[local], labels[local], hold,
                                                              cpu.atom_params(family, contract, atom), contract["te_seed_base"] + atom, contract["early_stopping_rounds"])
                    schema = c["feature_schema"][family]
                    need(len(scope["feature_names"]) == schema["columns"] and scope["matrix_dtype"] == schema["dtype"], "C actual matrix schema drift")
                    temp = part / f"model.tmp.{os.getpid()}.txt"
                    model.booster_.save_model(str(temp)); os.replace(temp, part / "model.txt")
                    cpu.atomic_npz(part / "predictions.npz", oof_idx=train[local], valid_idx=hold, oof_id=ids[train[local]], valid_id=ids[hold], oof_proba=prediction[:len(local)], valid_proba=prediction[len(local):])
                    save(part / "manifest.json", {"status": "C_ATOM_COMPLETE", "outer": outer, "family": family, "atom": atom,
                         "config_sha256": config_sha, "input_sha256": c["sources"]["data/train.csv"], "splits_sha256": c["splits_sha256"],
                         "fit_id_sha256": cpu.arr_sha(ids[train[fit]]), "early_stop_hold_id_sha256": cpu.arr_sha(ids[train[local]]), "outer_valid_id_sha256": cpu.arr_sha(ids[hold]),
                         **scope, "model_sha256": sha(part / "model.txt"), "prediction_sha256": sha(part / "predictions.npz"), "elapsed_seconds": time.monotonic() - started})
                    verify_atom(part, outer, family, atom, train[fit], train[local], hold, ids, labels[fit], labels[local], c, config_sha)
                    counts += 1
                    del model, prediction; gc.collect()
                    print(f"C_ATOM_COMPLETE outer={outer} family={family} atom={atom} seconds={time.monotonic()-started:.2f}", flush=True)
                arrays, hashes = family_arrays(directory, outer, family, train, hold, ids, folds, c, config_sha, labels)
                if (directory / "cache.npz").exists():
                    prior = read_npz(directory / "cache.npz")
                    need(set(prior) == set(arrays) and all(prior[k].dtype == arrays[k].dtype and np.array_equal(prior[k], arrays[k]) for k in arrays), "existing C cache differs")
                else:
                    cpu.atomic_npz(directory / "cache.npz", **arrays)
                record = cache_manifest(outer, family, arrays, hashes, c, config_sha, sha(directory / "cache.npz"))
                if (directory / "cache_manifest.json").exists():
                    need(read(directory / "cache_manifest.json") == record, "existing C cache manifest differs")
                else:
                    save(directory / "cache_manifest.json", record)
                caches[str((directory / "cache_manifest.json").relative_to(OUT))] = sha(directory / "cache_manifest.json")
                del backend, arrays; gc.collect()
    need(counts == 400 and len(caches) == 10, "C incomplete worker endpoint")
    load_config(); need(authorize(c) == binding, "C sources or complete A/B prerequisites changed during training")
    save(attempt / "WORKER_COMPLETE.json", {"status": "C_WORKER_CACHE_COMPLETE_UNSCORED", "config_sha256": config_sha,
         "authorization_sha256": binding["authorization_sha256"], "completed_atoms": counts, "completed_caches": len(caches), "cache_manifest_sha256": caches,
         "preflight_sha256": sha(attempt / "PREFLIGHT_PASS.json"), "allowed_for_submission": False})


def stop_child(child):
    if child is None:
        return
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        child.wait(timeout=3)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(child.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    child.wait(timeout=5)


def tree_rss():
    parent = psutil.Process(os.getpid()); total = 0
    for process in [parent, *parent.children(recursive=True)]:
        try:
            total += process.memory_info().rss
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            pass
    return total


class SupervisorBudget:
    def __init__(self, c, prior_seconds=0., prior_peak=0, started=None):
        self.c = c; self.prior = prior_seconds; self.peak = prior_peak
        self.started = time.monotonic() if started is None else started
        self.checks = []
    def check(self, phase, *, record=True):
        spent = self.prior + time.monotonic() - self.started
        rss = tree_rss(); self.peak = max(self.peak, rss)
        row = {"phase": phase, "spent_seconds": spent, "rss_bytes": rss, "peak_process_tree_rss_bytes": self.peak}
        if record:
            self.checks.append(row)
        if spent > self.c["cpu_seconds"]:
            raise TimeoutError("C cumulative wall budget exceeded")
        if self.peak > self.c["memory_bytes"]:
            raise MemoryError("C process-tree RSS budget exceeded")
        return row


def check_final_budget(result):
    need(result.get("status") == "LEGACY_CPU_CACHE_RUN_COMPLETE", "C supervisor did not successfully finish")
    spent, peak = result.get("spent_seconds"), result.get("peak_process_tree_rss_bytes")
    need(number(spent) and 0 <= spent <= 21600 and number(peak) and 0 < peak <= 24 * 1024**3, "C final resource budget")
    checks = result.get("resource_checks", [])
    need(checks and checks[-1].get("phase") == "BEFORE_COMPLETE" and checks[-1].get("spent_seconds") == spent, "C final budget boundary absent")
    need({"START", "AFTER_PREFLIGHT", "BEFORE_WORKER", "AFTER_WORKER_EXIT", "AFTER_CLEANUP", "BEFORE_COMPLETE"}.issubset({row.get("phase") for row in checks}), "C lifecycle budget coverage")
    previous = 0.
    for row in checks:
        need(number(row["spent_seconds"]) and previous <= row["spent_seconds"] <= spent and number(row["rss_bytes"]) and 0 < row["rss_bytes"] <= row["peak_process_tree_rss_bytes"] <= peak, "C inconsistent lifecycle budget")
        previous = row["spent_seconds"]


def inspect_attempt_history(config_sha, authorization_sha):
    """Never recover past a hard-killed or still-live unclosed attempt."""
    directories = sorted((OUT / "runtime").glob("attempt_*"))
    need([path.name for path in directories] == [f"attempt_{i:03d}" for i in range(1, len(directories) + 1)], "C attempt sequence requires review")
    if not directories:
        need(not (OUT / "RUN_STARTED.json").exists(), "C start has no closed attempt")
        return None
    need((OUT / "RUN_STARTED.json").is_file(), "C attempt history without original start")
    previous_sha = None
    for index, directory in enumerate(directories, 1):
        need((directory / "STARTED.json").is_file() and (directory / "RUN_RESULT.json").is_file(), "latest C attempt is not closed; parent recovery review required")
        start, result = read(directory / "STARTED.json"), read(directory / "RUN_RESULT.json")
        need(not matching_process_alive(start["supervisor_pid"], start["supervisor_created"]), "a matching C supervisor is still alive")
        if (directory / "WORKER_PROCESS.json").exists():
            process = read(directory / "WORKER_PROCESS.json")
            need(not matching_process_alive(process["pid"], process["created"]), "a matching C worker is still alive")
        need(start["attempt"] == result["attempt"] == index and start["config_sha256"] == result["config_sha256"] == config_sha and start["authorization_sha256"] == result["authorization_sha256"] == authorization_sha, "C attempt identity drift")
        need(start["previous_result_sha256"] == result["previous_result_sha256"] == previous_sha, "C closed failure chain drift")
        previous_sha = sha(directory / "RUN_RESULT.json")
    need((OUT / "RUN_RESULT.json").is_file() and sha(OUT / "RUN_RESULT.json") == previous_sha, "C root result is not the latest closed attempt")
    return read(directories[-1] / "RUN_RESULT.json")


def consume_resume_authorization(receipt, config_sha, prior_sha, next_attempt):
    need(receipt.get("authorized_by") == "parent" and receipt.get("action") == "RESUME_LEGACY_C_ONCE" and receipt.get("config_sha256") == config_sha and receipt.get("prior_run_result_sha256") == prior_sha and receipt.get("next_attempt") == next_attempt, "resume authorization missing, stale, or bound to another attempt")
    digest = sha(OUT / "RESUME_AUTHORIZATION.json")
    path = OUT / "runtime" / f"consumed_resume_{digest}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as handle:
        json.dump({"authorization_sha256": digest, "config_sha256": config_sha, "prior_run_result_sha256": prior_sha, "next_attempt": next_attempt}, handle, indent=2)
        handle.flush(); os.fsync(handle.fileno())
    return digest


def run(resume=False):
    initial = time.monotonic(); child = None
    # Full graph/preexisting-cache checks are supervised; no fit precedes their PASS receipt.
    c, binding = cheap_start_config(); config_sha = sha(OUT / "frozen_config.json")
    with (OUT / "cpu.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        prior = inspect_attempt_history(config_sha, binding["authorization_sha256"])
        attempt_number = len(list((OUT / "runtime").glob("attempt_*"))) + 1
        prior_seconds = 0.; prior_peak = 0; previous_result_sha = None; resume_sha = None
        if (OUT / "RUN_STARTED.json").exists():
            need(resume, "C already started; automatic/repeated launch forbidden")
            need(prior["status"] == "LEGACY_CPU_STOPPED_REVIEW_REQUIRED", "only a reviewed failed C run may resume")
            original = read(OUT / "RUN_STARTED.json")
            need(prior["config_sha256"] == original["config_sha256"] == config_sha and prior["authorization_sha256"] == original["authorization_sha256"] == binding["authorization_sha256"], "resume config/authorization identity changed")
            receipt = read(OUT / "RESUME_AUTHORIZATION.json")
            previous_result_sha = sha(OUT / "RUN_RESULT.json")
            resume_sha = consume_resume_authorization(receipt, config_sha, previous_result_sha, attempt_number)
            prior_seconds, prior_peak = prior["spent_seconds"], prior["peak_process_tree_rss_bytes"]
            need(number(prior_seconds) and 0 <= prior_seconds < c["cpu_seconds"] and number(prior_peak) and 0 <= prior_peak <= c["memory_bytes"], "failed run exhausted cumulative budget")
        else:
            need(not resume, "cannot resume before initial run")
        attempt = OUT / "runtime" / f"attempt_{attempt_number:03d}"
        need(not attempt.exists(), "attempt already exists")
        attempt.mkdir(parents=True)
        start = {"status": "STARTED", "supervisor_pid": os.getpid(), "supervisor_created": psutil.Process().create_time(),
                 "started_unix": time.time(), "config_sha256": config_sha, "authorization_sha256": binding["authorization_sha256"],
                 "worker_token": uuid.uuid4().hex, "attempt": attempt_number, "previous_result_sha256": previous_result_sha, "resume_authorization_sha256": resume_sha}
        save(attempt / "STARTED.json", start)
        if resume_sha is not None:
            save(attempt / "RESUME_AUTHORIZATION.json", receipt)
        if not (OUT / "RUN_STARTED.json").exists():
            save(OUT / "RUN_STARTED.json", {k: v for k, v in start.items() if k != "worker_token"})
        budget = SupervisorBudget(c, prior_seconds, prior_peak, initial)
        try:
            budget.check("START")
            save(OUT / "supervisor_state.json", {"status": "RUNNING", "pid": os.getpid(), "attempt": attempt_number, "config_sha256": config_sha, "authorization_sha256": binding["authorization_sha256"]})
            env = os.environ.copy()
            for key in THREAD_KEYS:
                env[key] = "8"
            env["LEGACY_C_SUPERVISED_TOKEN"] = start["worker_token"]
            budget.check("BEFORE_WORKER")
            with (attempt / "worker.log").open("x") as log:
                child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "worker", "--attempt", str(attempt)], cwd=OUT, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                save(attempt / "WORKER_PROCESS.json", process_identity(child.pid))
                preflight_seen = False
                while child.poll() is None:
                    row = budget.check("WORKER_MONITOR", record=False)
                    if not preflight_seen and (attempt / "PREFLIGHT_PASS.json").exists():
                        budget.check("AFTER_PREFLIGHT"); preflight_seen = True
                    save(OUT / "cpu_budget.json", {**row, "pid": os.getpid(), "attempt": attempt_number})
                    time.sleep(.5)
                if not preflight_seen and (attempt / "PREFLIGHT_PASS.json").exists():
                    budget.check("AFTER_PREFLIGHT")
                budget.check("AFTER_WORKER_EXIT")
                need(child.returncode == 0, "C worker failed; preserve its log and partial checkpoints")
            stop_child(child); budget.check("AFTER_CLEANUP")
            need(sha(OUT / "frozen_config.json") == config_sha and sha(OUT / "START_AUTHORIZATION.json") == binding["authorization_sha256"], "C final config/authorization bytes changed")
            preflight = read(attempt / "PREFLIGHT_PASS.json")
            need(preflight["status"] == "PREFLIGHT_PASS_UNSCORED" and preflight["config_sha256"] == config_sha and preflight["authorization_sha256"] == binding["authorization_sha256"] and preflight["new_models_fitted"] == 0, "C preflight scope mismatch")
            completed = read(attempt / "WORKER_COMPLETE.json")
            need(completed["status"] == "C_WORKER_CACHE_COMPLETE_UNSCORED" and completed["config_sha256"] == config_sha and completed["authorization_sha256"] == binding["authorization_sha256"] and completed["completed_atoms"] == 400 and completed["completed_caches"] == 10, "C worker completion scope")
            need(set(completed["cache_manifest_sha256"]) == {f"outer_{o:02d}/{f}/cache_manifest.json" for o in range(1, 6) for f in ("v80", "v85")}, "C cache completion coverage")
            need(completed["preflight_sha256"] == sha(attempt / "PREFLIGHT_PASS.json"), "C preflight receipt changed")
            for name, digest in completed["cache_manifest_sha256"].items():
                need(sha(OUT / name) == digest, "C cache manifest drift after worker")
            save(OUT / "supervisor_state.json", {"status": "LEGACY_CPU_CACHE_COMPLETE_UNSCORED", "pid": os.getpid(), "attempt": attempt_number,
                 "config_sha256": config_sha, "authorization_sha256": binding["authorization_sha256"], "completed_atoms": 400, "completed_caches": 10, "allowed_for_submission": False})
            final = budget.check("BEFORE_COMPLETE")
            save(OUT / "cpu_budget.json", {**final, "pid": os.getpid(), "attempt": attempt_number})
            result = {"status": "LEGACY_CPU_CACHE_RUN_COMPLETE", "config_sha256": config_sha, "authorization_sha256": binding["authorization_sha256"],
                      "attempt": attempt_number, "pid": os.getpid(), "spent_seconds": final["spent_seconds"], "peak_process_tree_rss_bytes": budget.peak,
                      "resource_checks": budget.checks, "worker_complete_sha256": sha(attempt / "WORKER_COMPLETE.json"), "worker_log_sha256": sha(attempt / "worker.log"),
                      "preflight_sha256": sha(attempt / "PREFLIGHT_PASS.json"), "worker_process_sha256": sha(attempt / "WORKER_PROCESS.json"),
                      "previous_result_sha256": previous_result_sha, "resume_authorization_sha256": resume_sha, "completed_atoms": 400, "completed_caches": 10, "allowed_for_submission": False}
            check_final_budget(result)
            save(attempt / "RUN_RESULT.json", result); save(OUT / "RUN_RESULT.json", result)
            return result
        except BaseException as error:
            stop_child(child)
            spent = prior_seconds + time.monotonic() - initial
            budget.peak = max(budget.peak, tree_rss())
            result = {"status": "LEGACY_CPU_STOPPED_REVIEW_REQUIRED", "config_sha256": config_sha, "authorization_sha256": binding["authorization_sha256"],
                      "attempt": attempt_number, "pid": os.getpid(), "spent_seconds": spent, "peak_process_tree_rss_bytes": budget.peak,
                      "error_type": type(error).__name__, "error": str(error), "resource_checks": budget.checks,
                      "previous_result_sha256": previous_result_sha, "resume_authorization_sha256": resume_sha, "allowed_for_submission": False}
            save(attempt / "RUN_RESULT.json", result); save(OUT / "RUN_RESULT.json", result)
            save(OUT / "cpu_budget.json", {"spent_seconds": spent, "peak_process_tree_rss_bytes": budget.peak, "pid": os.getpid(), "attempt": attempt_number})
            save(OUT / "supervisor_state.json", result)
            raise


def require_successful_completion():
    c = load_config(); binding = authorize(c)
    result = read(OUT / "RUN_RESULT.json"); check_final_budget(result)
    state = read(OUT / "supervisor_state.json"); budget = read(OUT / "cpu_budget.json")
    need(result["config_sha256"] == sha(OUT / "frozen_config.json") and result["authorization_sha256"] == binding["authorization_sha256"], "C final source binding drift")
    original = read(OUT / "RUN_STARTED.json")
    need(original["config_sha256"] == result["config_sha256"] and original["authorization_sha256"] == result["authorization_sha256"] and original["attempt"] == 1, "C original start identity")
    need(state["status"] == "LEGACY_CPU_CACHE_COMPLETE_UNSCORED" and state["completed_atoms"] == result["completed_atoms"] == 400 and state["completed_caches"] == result["completed_caches"] == 10, "C final cache coverage")
    need(state["allowed_for_submission"] is False and result["allowed_for_submission"] is False, "C submission scope drift")
    for key in ("pid", "attempt", "config_sha256", "authorization_sha256"):
        need(state[key] == result[key], "C final state identity")
    need(budget["pid"] == result["pid"] and budget["attempt"] == result["attempt"] and budget["spent_seconds"] == result["spent_seconds"] and budget["peak_process_tree_rss_bytes"] == result["peak_process_tree_rss_bytes"], "C final budget identity")
    paths = ["frozen_config.json", "START_AUTHORIZATION.json", "RUN_STARTED.json", "RUN_RESULT.json", "supervisor_state.json", "cpu_budget.json"]
    attempt = OUT / "runtime" / f"attempt_{result['attempt']:03d}"
    need(read(attempt / "RUN_RESULT.json") == result and sha(attempt / "WORKER_COMPLETE.json") == result["worker_complete_sha256"] and sha(attempt / "worker.log") == result["worker_log_sha256"], "C final attempt provenance")
    need(sha(attempt / "PREFLIGHT_PASS.json") == result["preflight_sha256"] and sha(attempt / "WORKER_PROCESS.json") == result["worker_process_sha256"], "C final preflight/process receipt changed")
    paths += [str((attempt / name).relative_to(OUT)) for name in ("STARTED.json", "RUN_RESULT.json", "WORKER_COMPLETE.json", "worker.log", "PREFLIGHT_PASS.json", "WORKER_PROCESS.json", "WATCHDOG_READY.json")]
    if result["resume_authorization_sha256"] is not None:
        need(sha(OUT / "RESUME_AUTHORIZATION.json") == result["resume_authorization_sha256"], "C resume receipt drift")
        paths.append("RESUME_AUTHORIZATION.json")
    previous_sha = None; previous_seconds = 0.; previous_peak = 0
    for index in range(1, result["attempt"] + 1):
        directory = OUT / "runtime" / f"attempt_{index:03d}"
        launch, record = read(directory / "STARTED.json"), read(directory / "RUN_RESULT.json")
        need(launch["attempt"] == record["attempt"] == index and launch["config_sha256"] == record["config_sha256"] == result["config_sha256"] and launch["authorization_sha256"] == record["authorization_sha256"] == result["authorization_sha256"], "C attempt identity chain")
        need(launch["previous_result_sha256"] == record["previous_result_sha256"] == previous_sha, "C prior failure evidence changed")
        need(record["spent_seconds"] >= previous_seconds and record["peak_process_tree_rss_bytes"] >= previous_peak, "C cumulative resources reset across resume")
        if index < result["attempt"]:
            need(record["status"] == "LEGACY_CPU_STOPPED_REVIEW_REQUIRED", "C resumed successful attempt")
        if index > 1:
            receipt_path = directory / "RESUME_AUTHORIZATION.json"
            receipt = read(receipt_path)
            need(sha(receipt_path) == launch["resume_authorization_sha256"] == record["resume_authorization_sha256"] and receipt["prior_run_result_sha256"] == previous_sha and receipt["next_attempt"] == index, "C resume authorization chain")
            paths.append(str(receipt_path.relative_to(OUT)))
            consumed = OUT / "runtime" / f"consumed_resume_{sha(receipt_path)}.json"
            need(read(consumed) == {"authorization_sha256": sha(receipt_path), "config_sha256": result["config_sha256"], "prior_run_result_sha256": previous_sha, "next_attempt": index}, "C resume exclusive consumption record")
            paths.append(str(consumed.relative_to(OUT)))
        paths += [str((directory / name).relative_to(OUT)) for name in ("STARTED.json", "RUN_RESULT.json")]
        previous_sha, previous_seconds, previous_peak = sha(directory / "RUN_RESULT.json"), record["spent_seconds"], record["peak_process_tree_rss_bytes"]
    return {"status": result["status"], "config_sha256": result["config_sha256"], "authorization_sha256": binding["authorization_sha256"], "files": {name: sha(OUT / name) for name in paths}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["freeze", "preflight", "run", "resume", "worker", "parent-guard", "status"])
    parser.add_argument("--attempt")
    parser.add_argument("--parent-pid", type=int)
    parser.add_argument("--parent-created", type=float)
    parser.add_argument("--worker-pid", type=int)
    parser.add_argument("--worker-created", type=float)
    parser.add_argument("--ready-path")
    args = parser.parse_args()
    if args.mode == "parent-guard":
        parent_guard(args.parent_pid, args.parent_created, args.worker_pid, args.worker_created, args.ready_path)
    elif args.mode == "worker":
        worker(args.attempt)
    elif args.mode == "freeze":
        print(json.dumps(freeze()))
    elif args.mode == "preflight":
        print(json.dumps(authorize(load_config())))
    elif args.mode in ("run", "resume"):
        print(json.dumps(run(resume=args.mode == "resume")))
    else:
        print(json.dumps({"status": "PREPARED_NO_CONFIG" if not (OUT / "frozen_config.json").exists() else "FROZEN_REQUIRES_PARENT_AUTHORIZATION", "training_started": (OUT / "RUN_STARTED.json").exists()}))
