"""Synthetic-only checks for C algorithm, cache, authorization and lifecycle."""
import os
for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[key] = "2"
import copy
import inspect
import json
from pathlib import Path
import tempfile
import time
import sys
import signal
import unittest
from unittest import mock
import numpy as np
import pandas as pd
import lightgbm as lgb
from threadpoolctl import threadpool_limits
import legacy_cpu as runner
import legacy_gate as gate


def gate_fixture():
    rows = {i: 20 for i in range(1, 6)}
    result = {"status": "COMPLETE_E2E_CONFIRMATION_ONLY", "baseline": "V100_E2E_CT_FULLREFIT", "candidate": "V100_E2E_CT_FOLDMEAN",
              "independent_reconstruction_passed": True, "submission_candidate_rebuild_gate_passed": True,
              "allowed_for_submission": False, "actual_test_predictions_generated": False, "is_new_blind_test": False,
              "n_rows": 100, "baseline_auc": .7, "candidate_auc": .71, "delta": .01, "positive_folds": 5,
              "folds": [{"fold": i, "rows": 20, "baseline_auc": .7, "candidate_auc": .71, "delta": .01} for i in rows]}
    independent = {"status": "INDEPENDENT_RECONSTRUCTION_PASS_UNSCORED", "outer_labels_scored": False,
                   "outer_rows": [{"outer": i, "max_abs_errors": {"baseline_proba": 0., "candidate_proba": 0.}} for i in rows]}
    state = {"status": "SCORE_READY_FOR_REVIEW", "pid": 77, "actual_test_predictions": False, "competition_submission": False}
    return result, independent, state, {"pid": 77}, rows


class TestGate(unittest.TestCase):
    def test_complete_gate(self):
        gate.validate_gate_results(*gate_fixture())

    def test_running_failed_or_foreign_pipeline(self):
        for field, value in (("status", "WAITING_EXISTING_TRAINING"), ("status", "STOPPED_REVIEW_REQUIRED"), ("pid", 78)):
            args = list(gate_fixture()); args[2][field] = value
            with self.assertRaises(ValueError): gate.validate_gate_results(*args)

    def test_nonpositive_nonfinite_and_bool_delta(self):
        for value in (0., -.01, float("nan"), float("inf"), True):
            args = list(gate_fixture()); args[0]["delta"] = value
            with self.assertRaises(ValueError): gate.validate_gate_results(*args)

    def test_booleans_do_not_replace_fold_evidence(self):
        for change in ("missing", "duplicate", "zero", "wrong_rows", "wrong_total", "auc_delta"):
            args = list(gate_fixture()); result = args[0]
            if change == "missing": result["folds"].pop()
            elif change == "duplicate": result["folds"][-1]["fold"] = 1
            elif change == "zero": result["folds"][0]["delta"] = 0.
            elif change == "wrong_rows": result["folds"][0]["rows"] = 19
            elif change == "wrong_total": result["n_rows"] = 99
            else: result["candidate_auc"] = .72
            with self.assertRaises(ValueError): gate.validate_gate_results(*args)

    def test_independent_reconstruction_coverage_and_errors(self):
        for change in ("missing", "duplicate", "error", "nan", "wrong_keys"):
            args = list(gate_fixture()); report = args[1]
            if change == "missing": report["outer_rows"].pop()
            elif change == "duplicate": report["outer_rows"][-1]["outer"] = 1
            elif change == "wrong_keys": report["outer_rows"][0]["max_abs_errors"] = {}
            else: report["outer_rows"][0]["max_abs_errors"]["candidate_proba"] = float("nan") if change == "nan" else 1e-6
            with self.assertRaises(ValueError): gate.validate_gate_results(*args)

    def test_no_authorization_and_whitelist_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError): gate.verify_authorized_ab(Path(directory), "cfg", {}, None)
        auth = {"schema_version": 1, "action": "START_LEGACY_C_ONCE", "authorized_by": "parent", "config_sha256": "cfg", "created_unix": 1., "prerequisite_files": {p: "a" * 64 for p in gate.prerequisite_paths()}}
        gate.validate_authorization(auth, "cfg")
        for change in ("wrong_config", "missing_file", "extra_file", "not_parent"):
            value = copy.deepcopy(auth)
            if change == "wrong_config": value["config_sha256"] = "other"
            elif change == "missing_file": value["prerequisite_files"].pop(next(iter(value["prerequisite_files"])))
            elif change == "extra_file": value["prerequisite_files"]["../elsewhere"] = "x"
            else: value["authorized_by"] = "self"
            with self.assertRaises(ValueError): gate.validate_authorization(value, "cfg")


class RecordingBackend:
    family = "synthetic"
    def __init__(self): self.calls = []
    def encode(self, fit, y, query, seed):
        self.calls.append((fit.copy(), y.copy(), query.copy(), seed))
        # Only fit labels are accepted by the encoder interface.
        return np.column_stack([fit, fit % 3]).astype(np.float64), np.column_stack([query, query % 3]).astype(np.float64), ["x", "z"]


class SpyModel:
    calls = []
    def __init__(self, **params): self.params = params
    def fit(self, x, y, **kwargs):
        self.calls.append((x.copy(), y.copy(), kwargs))
        self.best_iteration_ = 3 if kwargs["eval_set"][0][1][0] == 0 else 5
        return self
    def predict_proba(self, x, num_iteration):
        probability = np.full(len(x), num_iteration / 10.)
        return np.column_stack([1 - probability, probability])


class TestAlgorithm(unittest.TestCase):
    def test_one_fit_on_F_and_H_only_early_stopping(self):
        SpyModel.calls = []; backend = RecordingBackend()
        with mock.patch.object(lgb, "LGBMClassifier", SpyModel):
            prediction, scope, _ = runner.fit_legacy_atom(backend, np.arange(10), np.arange(10) % 2, np.arange(10, 14), np.array([0, 1, 0, 1]), np.arange(14, 18), {"n_estimators": 10}, 42, 2)
        self.assertEqual(len(SpyModel.calls), 1)
        self.assertEqual(len(backend.calls), 1)
        np.testing.assert_array_equal(SpyModel.calls[0][1], np.arange(10) % 2)
        np.testing.assert_array_equal(SpyModel.calls[0][2]["eval_set"][0][0][:, 0], np.arange(10, 14))
        self.assertTrue(scope["atom_hold_labels_used_for_early_stopping"])
        self.assertFalse(scope["outer_hold_labels_used"]); self.assertFalse(scope["refit_performed"])
        self.assertEqual(scope["training_fit_count"], 1)
        self.assertNotIn("outer_y", inspect.signature(runner.fit_legacy_atom).parameters)
        self.assertEqual(prediction.shape, (8,))

    def test_H_labels_change_rounds_but_not_TE_fit_input(self):
        backend = RecordingBackend(); fit, h, u = np.arange(10), np.arange(10, 14), np.arange(14, 18)
        with mock.patch.object(lgb, "LGBMClassifier", SpyModel):
            a = runner.fit_legacy_atom(backend, fit, fit % 2, h, np.array([0, 1, 0, 1]), u, {"n_estimators": 10}, 42, 2)
            b = runner.fit_legacy_atom(backend, fit, fit % 2, h, np.array([1, 0, 1, 0]), u, {"n_estimators": 10}, 42, 2)
        self.assertEqual(a[1]["selected_iteration"], 3); self.assertEqual(b[1]["selected_iteration"], 5)
        np.testing.assert_array_equal(backend.calls[0][1], backend.calls[1][1])

    def test_U_features_do_not_enter_early_stop_set(self):
        SpyModel.calls = []; fit, h = np.arange(10), np.arange(10, 14)
        with mock.patch.object(lgb, "LGBMClassifier", SpyModel):
            for u in (np.arange(14, 18), np.arange(1014, 1018)):
                runner.fit_legacy_atom(RecordingBackend(), fit, fit % 2, h, h % 2, u, {"n_estimators": 10}, 42, 2)
        np.testing.assert_array_equal(SpyModel.calls[0][2]["eval_set"][0][0], SpyModel.calls[1][2]["eval_set"][0][0])

    def test_overlap_rejected_before_fit(self):
        with mock.patch.object(lgb, "LGBMClassifier", SpyModel), self.assertRaises(ValueError):
            runner.fit_legacy_atom(RecordingBackend(), np.arange(10), np.arange(10) % 2, np.arange(10, 14), np.arange(4) % 2, np.array([2, 16]), {"n_estimators": 10}, 42, 2)

    def test_real_synthetic_fit_saved_model_replays(self):
        from feature_backends import Backend
        rng = np.random.default_rng(9); x = rng.normal(size=(120, 4)); y = (x[:, 0] > 0).astype(np.int8)
        backend = Backend("v80", pd.DataFrame(x.astype(np.float32), columns=["a", "b", "c", "d"]))
        fit, h, u = np.arange(80), np.arange(80, 100), np.arange(100, 120)
        params = {"n_estimators": 8, "max_depth": 2, "num_leaves": 4, "min_child_samples": 5, "n_jobs": 2, "verbosity": -1, "random_state": 7}
        prediction, scope, model = runner.fit_legacy_atom(backend, fit, y[fit], h, y[h], u, params, 42, 3)
        self.assertEqual(scope["training_fit_count"], 1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.txt"; model.booster_.save_model(str(path))
            loaded = lgb.Booster(model_file=str(path)); _, query, _ = backend.encode(fit, y[fit], np.concatenate([h, u]), 42)
            np.testing.assert_array_equal(loaded.predict(query, num_threads=2), prediction)


class TestCache(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name); self.cpu = runner.runtime()
        self.train, self.hold = np.arange(80), np.arange(80, 100)
        self.ids = np.arange(100) + 1000; self.folds = np.repeat(np.arange(40, dtype=np.int8), 2); self.y = np.arange(80) % 2
        self.c = {"sources": {"data/train.csv": "trainhash"}, "splits_sha256": "splithash", "families": {"v80": {"params": {"n_estimators": 8}, "te_seed_base": 42, "model_seed_base": 42, "seed_fields": []}}, "feature_schema": {"v80": {"columns": 113, "dtype": "float32"}}}
        self.c["outer_plan"] = [{**{k + "_sha256": self.cpu.arr_sha(v) for k, v in (("train_idx", self.train), ("valid_idx", self.hold), ("train_id", self.ids[self.train]), ("valid_id", self.ids[self.hold]))}, "atoms": {"v80": {"fold_ids_sha256": self.cpu.arr_sha(self.folds)}}}]
        runner.save(self.root / "frozen_config.json", self.c); self.config_sha = runner.sha(self.root / "frozen_config.json")
        self.directory = self.root / "outer_01/v80"
        for atom in range(1, 41): self.atom(atom)
        arrays, hashes = runner.family_arrays(self.directory, 1, "v80", self.train, self.hold, self.ids, self.folds, self.c, self.config_sha, self.y)
        self.cpu.atomic_npz(self.directory / "cache.npz", **arrays)
        runner.save(self.directory / "cache_manifest.json", runner.cache_manifest(1, "v80", arrays, hashes, self.c, self.config_sha, runner.sha(self.directory / "cache.npz")))
    def tearDown(self): self.temp.cleanup()
    def atom(self, atom):
        local, fit = np.flatnonzero(self.folds == atom - 1), np.flatnonzero(self.folds != atom - 1)
        h, f = self.train[local], self.train[fit]; part = self.directory / f"atom_{atom:02d}"; part.mkdir(parents=True)
        (part / "model.txt").write_text("synthetic model bytes")
        self.cpu.atomic_npz(part / "predictions.npz", oof_idx=h, valid_idx=self.hold, oof_id=self.ids[h], valid_id=self.ids[self.hold], oof_proba=np.array([.2, .8]), valid_proba=np.linspace(.1, .9, 20))
        names = [f"x{i}" for i in range(113)]
        runner.save(part / "manifest.json", {"status": "C_ATOM_COMPLETE", "outer": 1, "family": "v80", "atom": atom, "config_sha256": self.config_sha, "input_sha256": "trainhash", "splits_sha256": "splithash",
            "fit_idx_sha256": self.cpu.arr_sha(f), "early_stop_hold_idx_sha256": self.cpu.arr_sha(h), "outer_valid_idx_sha256": self.cpu.arr_sha(self.hold), "query_idx_sha256": self.cpu.arr_sha(np.concatenate([h, self.hold])),
            "fit_id_sha256": self.cpu.arr_sha(self.ids[f]), "early_stop_hold_id_sha256": self.cpu.arr_sha(self.ids[h]), "outer_valid_id_sha256": self.cpu.arr_sha(self.ids[self.hold]),
            "fit_y_sha256": self.cpu.arr_sha(self.y[fit]), "early_stop_hold_y_sha256": self.cpu.arr_sha(self.y[local]), "te_seed": 42 + atom,
            "params_sha256": self.cpu.json_sha({"n_estimators": 8}), "atom_hold_labels_used_for_early_stopping": True, "outer_hold_labels_used": False, "refit_performed": False, "training_fit_count": 1,
            "feature_names": names, "feature_names_sha256": self.cpu.json_sha(names), "matrix_dtype": "float32", "selected_iteration": 3,
            "model_sha256": runner.sha(part / "model.txt"), "prediction_sha256": runner.sha(part / "predictions.npz")})
    def check(self):
        with mock.patch.object(runner, "OUT", self.root), mock.patch.object(runner, "train_labels", return_value=self.y):
            return runner.check_family_cache(self.directory, 1, "v80", self.train, self.hold, self.ids, self.folds, self.config_sha, "trainhash", "splithash")
    def test_40_atom_cache_reconstruction(self):
        self.assertEqual(self.check()["oof_proba"].shape, (80,))
    def test_model_and_manifest_tampering(self):
        part = self.directory / "atom_01"
        (part / "model.txt").write_text("changed")
        with self.assertRaises(ValueError): self.check()
    def test_scalar_float32_and_identity_corruption_rejected(self):
        part = self.directory / "atom_01"; baseline = runner.read_npz(part / "predictions.npz"); manifest = runner.read(part / "manifest.json")
        for key, value in (("oof_proba", np.array(.2)), ("oof_proba", np.array([.2, .8], dtype=np.float32)), ("valid_id", np.arange(20))):
            arrays = dict(baseline); arrays[key] = value
            self.cpu.atomic_npz(part / "predictions.npz", **arrays); manifest["prediction_sha256"] = runner.sha(part / "predictions.npz"); runner.save(part / "manifest.json", manifest)
            with self.assertRaises(ValueError): self.check()
    def test_old_A_scope_flags_rejected(self):
        part = self.directory / "atom_01"; manifest = runner.read(part / "manifest.json")
        manifest["atom_hold_labels_used_for_early_stopping"] = False; runner.save(part / "manifest.json", manifest)
        with self.assertRaises(ValueError): self.check()
    def test_changed_H_labels_rejected(self):
        self.y = 1 - self.y
        with self.assertRaises(ValueError): self.check()

    def test_wrong_split_rejected_with_other_inputs_intact(self):
        self.folds = self.folds[::-1]
        with self.assertRaises(ValueError): self.check()

    def test_preflight_finds_later_corruption_before_any_new_fit(self):
        # Atom 1 is missing while atom 40 remains: preflight must inspect the later atom.
        import shutil
        shutil.rmtree(self.directory / "atom_01")
        (self.directory / "cache.npz").unlink(); (self.directory / "cache_manifest.json").unlink()
        (self.directory / "atom_40/model.txt").write_text("corrupt after gap")
        splits = {}
        for outer in range(1, 6):
            splits[f"outer_{outer:02d}_train_idx"] = self.train; splits[f"outer_{outer:02d}_valid_idx"] = self.hold
            for family in ("v80", "v85"): splits[f"outer_{outer:02d}_{family}_fold"] = self.folds
        with mock.patch.object(runner, "OUT", self.root), mock.patch.object(runner, "train_labels", return_value=self.y), mock.patch.object(runner, "fit_legacy_atom") as fit:
            with self.assertRaises(ValueError): runner.preflight_existing_checkpoints(self.c, splits, self.ids)
            fit.assert_not_called()


def successful_budget():
    phases = ["START", "AFTER_PREFLIGHT", "BEFORE_WORKER", "AFTER_WORKER_EXIT", "AFTER_CLEANUP", "BEFORE_COMPLETE"]
    checks = [{"phase": p, "spent_seconds": float(i + 1), "rss_bytes": 100, "peak_process_tree_rss_bytes": 100} for i, p in enumerate(phases)]
    return {"status": "LEGACY_CPU_CACHE_RUN_COMPLETE", "spent_seconds": 6., "peak_process_tree_rss_bytes": 100, "resource_checks": checks}


class TestSupervision(unittest.TestCase):
    def test_success_and_final_budget_failure(self):
        runner.check_final_budget(successful_budget())
        for change in ("failed", "late", "rss", "missing_final", "missing_phase", "nan"):
            value = successful_budget()
            if change == "failed": value["status"] = "LEGACY_CPU_STOPPED_REVIEW_REQUIRED"
            elif change == "late": value["spent_seconds"] = 21601.
            elif change == "rss": value["peak_process_tree_rss_bytes"] = 24 * 1024**3 + 1
            elif change == "missing_final": value["resource_checks"].pop()
            elif change == "missing_phase": value["resource_checks"].pop(2)
            else: value["spent_seconds"] = float("nan")
            with self.assertRaises(ValueError): runner.check_final_budget(value)
    def test_process_tree_peak_and_cumulative_wall(self):
        config = {"cpu_seconds": 10, "memory_bytes": 1000}
        with mock.patch.object(runner, "tree_rss", return_value=200), mock.patch.object(runner.time, "monotonic", return_value=2):
            b = runner.SupervisorBudget(config, prior_seconds=9, prior_peak=100, started=0)
            with self.assertRaises(TimeoutError): b.check("AFTER_CLEANUP")
        with mock.patch.object(runner, "tree_rss", return_value=1001):
            b = runner.SupervisorBudget(config)
            with self.assertRaises(MemoryError): b.check("BEFORE_COMPLETE")
    def test_authorization_failure_never_starts_worker(self):
        with mock.patch.object(runner, "cheap_start_config", side_effect=ValueError("no parent authorization")), mock.patch.object(runner.subprocess, "Popen") as launch:
            with self.assertRaises(ValueError): runner.run()
            launch.assert_not_called()
    def test_direct_worker_entry_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); attempt = root / "runtime/attempt_001"
            runner.save(attempt / "STARTED.json", {"supervisor_pid": -1, "worker_token": "not-present"})
            with mock.patch.object(runner, "OUT", root), self.assertRaises(ValueError): runner.worker(str(attempt))
    def test_completed_worker_then_final_budget_failure_keeps_failed_state(self):
        self.synthetic_run(fail_final=True)
    def test_synthetic_complete_and_duplicate_launch_refused(self):
        self.synthetic_run(fail_final=False)
    def test_expensive_preflight_is_inside_supervisor_budget(self):
        self.synthetic_run(fail_final=False, fail_preflight=True)
    def synthetic_run(self, fail_final, fail_preflight=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); runner.save(root / "frozen_config.json", {"synthetic": True})
            runner.save(root / "START_AUTHORIZATION.json", {"synthetic": True})
            auth_sha = runner.sha(root / "START_AUTHORIZATION.json")
            config = {"cpu_seconds": 21600, "memory_bytes": 24 * 1024**3}
            binding = {"authorization_sha256": auth_sha, "prerequisite_files": {}, "ab_result_sha256": "ab"}
            class Process:
                pid = 99999999; returncode = 0
                def __init__(self, command, **kwargs):
                    attempt = Path(command[-1]); manifests = {}
                    if fail_preflight: return
                    runner.save(attempt / "PREFLIGHT_PASS.json", {"status": "PREFLIGHT_PASS_UNSCORED", "config_sha256": runner.sha(root / "frozen_config.json"), "authorization_sha256": auth_sha, "new_models_fitted": 0})
                    for outer in range(1, 6):
                        for family in ("v80", "v85"):
                            p = root / f"outer_{outer:02d}/{family}/cache_manifest.json"; runner.save(p, {"synthetic": True}); manifests[str(p.relative_to(root))] = runner.sha(p)
                    runner.save(attempt / "WORKER_COMPLETE.json", {"status": "C_WORKER_CACHE_COMPLETE_UNSCORED", "config_sha256": runner.sha(root / "frozen_config.json"), "authorization_sha256": auth_sha, "completed_atoms": 400, "completed_caches": 10, "cache_manifest_sha256": manifests, "preflight_sha256": runner.sha(attempt / "PREFLIGHT_PASS.json")})
                def poll(self): return None if fail_preflight else 0
            original_check = runner.SupervisorBudget.check
            def check(budget, phase, **kwargs):
                value = original_check(budget, phase, **kwargs)
                if phase == "BEFORE_COMPLETE" and fail_final: raise TimeoutError("synthetic final budget failure")
                if phase == "WORKER_MONITOR" and fail_preflight: raise TimeoutError("synthetic stalled preflight")
                return value
            with mock.patch.object(runner, "OUT", root), mock.patch.object(runner, "cheap_start_config", return_value=(config, binding)), mock.patch.object(runner.subprocess, "Popen", Process), mock.patch.object(runner, "process_identity", return_value={"pid": 99999999, "created": 1.}), mock.patch.object(runner, "stop_child"), mock.patch.object(runner, "tree_rss", return_value=100), mock.patch.object(runner.SupervisorBudget, "check", check):
                if fail_final or fail_preflight:
                    with self.assertRaises(TimeoutError): runner.run()
                    self.assertEqual(runner.read(root / "RUN_RESULT.json")["status"], "LEGACY_CPU_STOPPED_REVIEW_REQUIRED")
                    self.assertEqual(runner.read(root / "supervisor_state.json")["status"], "LEGACY_CPU_STOPPED_REVIEW_REQUIRED")
                else:
                    self.assertEqual(runner.run()["status"], "LEGACY_CPU_CACHE_RUN_COMPLETE")
                    with self.assertRaises(ValueError): runner.run()

    def history(self, root):
        common = {"attempt": 1, "config_sha256": "cfg", "authorization_sha256": "auth", "previous_result_sha256": None}
        launch = {**common, "supervisor_pid": 55, "supervisor_created": 1.}
        result = {**common, "status": "LEGACY_CPU_STOPPED_REVIEW_REQUIRED", "spent_seconds": 2., "peak_process_tree_rss_bytes": 100}
        runner.save(root / "runtime/attempt_001/STARTED.json", launch); runner.save(root / "runtime/attempt_001/RUN_RESULT.json", result)
        runner.save(root / "RUN_STARTED.json", launch); runner.save(root / "RUN_RESULT.json", result)

    def test_unclosed_attempt_blocks_old_root_result_and_reused_authorization(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.history(root)
            runner.save(root / "runtime/attempt_002/STARTED.json", {"attempt": 2})
            with mock.patch.object(runner, "OUT", root), mock.patch.object(runner, "matching_process_alive", return_value=False), self.assertRaises(ValueError):
                runner.inspect_attempt_history("cfg", "auth")

    def test_live_supervisor_or_worker_blocks_recovery(self):
        for live in (55, 66):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory); self.history(root)
                runner.save(root / "runtime/attempt_001/WORKER_PROCESS.json", {"pid": 66, "created": 1.})
                with mock.patch.object(runner, "OUT", root), mock.patch.object(runner, "matching_process_alive", side_effect=lambda pid, created: pid == live), self.assertRaises(ValueError):
                    runner.inspect_attempt_history("cfg", "auth")

    def test_resume_authorization_is_consumed_for_exact_attempt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = {"authorized_by": "parent", "action": "RESUME_LEGACY_C_ONCE", "config_sha256": "cfg", "prior_run_result_sha256": "prior", "next_attempt": 2}
            runner.save(root / "RESUME_AUTHORIZATION.json", receipt)
            with mock.patch.object(runner, "OUT", root):
                with self.assertRaises(ValueError): runner.consume_resume_authorization(receipt, "cfg", "prior", 3)
                runner.consume_resume_authorization(receipt, "cfg", "prior", 2)
                with self.assertRaises(FileExistsError): runner.consume_resume_authorization(receipt, "cfg", "prior", 2)

    def test_pid_reuse_is_not_matching_parent(self):
        process = mock.Mock(); process.create_time.return_value = 2.; process.is_running.return_value = True
        with mock.patch.object(runner.psutil, "Process", return_value=process):
            self.assertFalse(runner.matching_process_alive(55, 1.))
            self.assertTrue(runner.watchdog_parent_lost({"supervisor_pid": 55, "supervisor_created": 1.}))

    def test_separate_guard_stops_native_wait_after_supervisor_signals(self):
        # Only fresh synthetic descendants are signaled; no project job is inspected or stopped.
        worker_code = """import sys,time,psutil,os,json\nfrom pathlib import Path\nsys.path.insert(0,sys.argv[1])\nimport legacy_cpu\nroot=Path(sys.argv[2]); parent=os.getppid()\nguard=legacy_cpu.spawn_parent_guard(parent,psutil.Process(parent).create_time(),root/'READY.json')\ntime.sleep(60)\n"""
        supervisor_code = """import sys,time,subprocess,json,psutil\nfrom pathlib import Path\np=subprocess.Popen([sys.executable,'-c',sys.argv[3],sys.argv[1],sys.argv[2]],start_new_session=True)\nPath(sys.argv[2],'WORKER.json').write_text(json.dumps({'pid':p.pid,'created':psutil.Process(p.pid).create_time()}))\ntime.sleep(60)\n"""
        for signum in (signal.SIGTERM, signal.SIGKILL):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                supervisor = runner.subprocess.Popen([sys.executable, "-c", supervisor_code, str(Path(__file__).parent), str(root), worker_code], stdout=runner.subprocess.DEVNULL, stderr=runner.subprocess.DEVNULL)
                worker = None
                try:
                    deadline = time.monotonic() + 5
                    while not (root / "READY.json").exists() and time.monotonic() < deadline: time.sleep(.05)
                    self.assertTrue((root / "READY.json").exists(), "synthetic guard did not become ready")
                    worker = runner.read(root / "WORKER.json")
                    os.kill(supervisor.pid, signum); supervisor.wait(timeout=3)
                    deadline = time.monotonic() + 5
                    while runner.matching_process_alive(worker["pid"], worker["created"]) and time.monotonic() < deadline: time.sleep(.05)
                    self.assertFalse(runner.matching_process_alive(worker["pid"], worker["created"]), "worker survived loss of supervisor")
                finally:
                    if supervisor.poll() is None: supervisor.kill(); supervisor.wait(timeout=3)
                    if worker is None and (root / "WORKER.json").exists(): worker = runner.read(root / "WORKER.json")
                    if worker and runner.matching_process_alive(worker["pid"], worker["created"]): os.killpg(worker["pid"], signal.SIGKILL)


if __name__ == "__main__":
    started = time.monotonic()
    with threadpool_limits(limits=2):
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(__import__(__name__)))
    source_names = [name for name in runner.owned_sources() if name.endswith(".py")]
    runner.save(Path(__file__).parent / "cpu_test_results.json", {"status": "PASS" if result.wasSuccessful() else "FAILED", "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "seconds": time.monotonic() - started, "code_sha256": {name: runner.sha(Path(__file__).parent / name) for name in source_names}, "real_training_performed": False, "synthetic_lightgbm_fit_performed": True})
    raise SystemExit(0 if result.wasSuccessful() else 1)
