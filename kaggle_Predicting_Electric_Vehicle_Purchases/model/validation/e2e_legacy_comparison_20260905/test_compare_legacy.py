"""只用合成预测、临时目录和 mock；不读真实标签、不训练或真实评分。"""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import numpy as np
from threadpoolctl import threadpool_limits
import compare_legacy as c

sys.path.insert(0, str(c.AB_ROOT))
AB = c.load_module(c.AB_ROOT / "assemble_e2e.py", "comparison_test_shared_ab")
AUC = c.load_module(c.PROJECT / "model/research_runtime/paired_auc.py", "comparison_test_shared_auc")
for key in c.THREAD_KEYS:
    c.os.environ[key] = "2"


def report(base, candidate, fold_deltas=None):
    deltas = [candidate - base] * 5 if fold_deltas is None else fold_deltas
    return {"baseline_auc": base, "candidate_auc": candidate, "delta": candidate - base,
            "folds": [{"fold": i + 1, "baseline_auc": base, "candidate_auc": base + d, "delta": d}
                      for i, d in enumerate(deltas)], "positive_folds": sum(d > 0 for d in deltas)}


def terminal_fixture():
    state = {"status": "SCORE_READY_FOR_REVIEW", "pid": 100, "seconds": 100.,
             "actual_test_predictions": False, "competition_submission": False}
    started = {"pid": 100}
    cfg = {"pipeline_seconds": 15 * 3600}
    score = {**report(.70, .71), "status": "COMPLETE_E2E_CONFIRMATION_ONLY",
             "baseline": "V100_E2E_CT_FULLREFIT", "candidate": "V100_E2E_CT_FOLDMEAN",
             "independent_reconstruction_passed": True, "allowed_for_submission": False,
             "actual_test_predictions_generated": False, "submission_candidate_rebuild_gate_passed": True}
    return state, started, cfg, score


def rebuilt_fixture():
    hold = np.array([2, 3])
    ids = np.array([100, 101, 102, 103])
    prior = {"valid_idx": hold.copy(), "valid_id": ids[hold].copy(),
             "c_proba": np.array([.2, .8]), "d_proba": np.array([.3, .7])}
    meta = {"v90_fold_weights": [.4, .5, .6, .7, .3], "ct_final_weight": .2,
            "meta_weights_reused_from_AB": False, "outer_hold_labels_used": False}
    expected = {"v90_fold_weights": list(meta["v90_fold_weights"]), "ct_final_weight": .2,
                "refit_prediction": prior["c_proba"].copy(), "foldmean_prediction": prior["d_proba"].copy()}
    return prior, meta, expected, hold, ids, AB


class ComparisonBoundaries(unittest.TestCase):
    def test_missing_cache_blocks_before_any_arrays_labels_or_modules(self):
        with patch.object(c, "missing_files", return_value=["outer_05/v85/cache.npz"]), \
             patch.object(c, "modules", side_effect=AssertionError("modules not reached")), \
             patch.object(c.np, "load", side_effect=AssertionError("no array reads")), \
             patch.object(c.pd, "read_csv", side_effect=AssertionError("no label reads")):
            with self.assertRaisesRegex(FileNotFoundError, "NOT_READY"):
                c.checked_context()

    def test_failed_or_running_ab_terminal_rejected(self):
        for status in ("WAITING_EXISTING_TRAINING", "POSTPROCESSING", "STOPPED_REVIEW_REQUIRED"):
            args = terminal_fixture()
            args[0]["status"] = status
            with self.assertRaisesRegex(ValueError, "finally successful"):
                c.require_ab_terminal(*args)

    def test_ab_terminal_budget_and_pid_cannot_be_forgiven(self):
        for field, value in (("pid", 101), ("seconds", 15 * 3600), ("seconds", float("nan"))):
            args = terminal_fixture()
            args[0][field] = value
            with self.assertRaises(ValueError):
                c.require_ab_terminal(*args)

    def test_ab_independent_flag_and_all_folds_required(self):
        args = terminal_fixture()
        c.require_ab_terminal(*args)
        args[3]["independent_reconstruction_passed"] = False
        with self.assertRaises(ValueError):
            c.require_ab_terminal(*args)
        args = terminal_fixture()
        args[3]["folds"][-1]["fold"] = 4
        with self.assertRaises(ValueError):
            c.require_ab_terminal(*args)

    def test_wrong_c_ids_rejected_even_with_same_probabilities(self):
        args = rebuilt_fixture()
        args[0]["valid_id"] = np.array([103, 102])
        with self.assertRaisesRegex(ValueError, "identity"):
            c.validate_c_rebuilt(*args)

    def test_foreign_ab_weights_are_not_valid_c_weights(self):
        args = rebuilt_fixture()
        args[1]["v90_fold_weights"] = [.5] * 5
        with self.assertRaisesRegex(ValueError, "weights mismatch"):
            c.validate_c_rebuilt(*args)
        args = rebuilt_fixture()
        args[1]["meta_weights_reused_from_AB"] = True
        with self.assertRaisesRegex(ValueError, "scope"):
            c.validate_c_rebuilt(*args)

    def test_both_c_and_d_require_independent_reconstruction(self):
        args = rebuilt_fixture()
        self.assertEqual(c.validate_c_rebuilt(*args), {"c_proba": 0., "d_proba": 0.})
        for field in ("c_proba", "d_proba"):
            args = rebuilt_fixture()
            args[0][field] = args[0][field] + .001
            with self.assertRaisesRegex(ValueError, "predictions mismatch"):
                c.validate_c_rebuilt(*args)

    def test_stale_independent_pass_does_not_allow_endpoint_labels(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(c, "OUTPUT", Path(tmp)), \
             patch.object(c, "require_stage_success"), \
             patch.object(c, "verify_readonly", side_effect=ValueError("current rebuild failed")), \
             patch.object(c.pd, "read_csv", side_effect=AssertionError("must not read endpoint labels")):
            (Path(tmp) / "independent_reconstruction.json").write_text('{"status":"old PASS"}')
            with self.assertRaisesRegex(ValueError, "current rebuild failed"):
                c.score()

    def test_previous_stage_failed_or_over_budget_blocks_score(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "comparison_config.json").write_text('{}')
            (root / "verify.log").write_text('synthetic log')
            good = {"status": "COMPARISON_STAGE_COMPLETE", "mode": "verify", "seconds": 1.,
                    "pid": 101, "supervisor_created": 10., "peak_process_tree_rss_bytes": 100, "config_sha256": c.sha(root / "comparison_config.json"),
                    "log_sha256": c.sha(root / "verify.log"), "allowed_for_submission": False,
                    "actual_test_predictions_generated": False,
                    "resource_checks": [{"phase": p, "seconds": 1., "peak_rss_bytes": 100} for p in
                                        ("before_worker", "after_worker", "before_publish", "final")]}
            c.write_json(root / "verify_PARENT_GUARD_READY.json", {"parent_pid": 101, "parent_created": 10.})
            good["parent_guard_ready_sha256"] = c.sha(root / "verify_PARENT_GUARD_READY.json")
            c.write_json(root / "verify_STARTED.json", {"pid": 101, "supervisor_created": 10., "mode": "verify", "config_sha256": good["config_sha256"]})
            with patch.object(c, "ROOT", root), patch.object(c, "OUTPUT", root):
                for update in ({"status": "COMPARISON_STAGE_FAILED"}, {"seconds": c.WALL},
                               {"peak_process_tree_rss_bytes": c.MEMORY + 1}):
                    c.write_json(root / "verify_RUN_RESULT.json", {**good, **update})
                    with self.assertRaises(ValueError):
                        c.require_stage_success("verify")
                c.write_json(root / "verify_RUN_RESULT.json", good)
                c.require_stage_success("verify")
                good["resource_checks"].pop()
                c.write_json(root / "verify_RUN_RESULT.json", good)
                with self.assertRaisesRegex(ValueError, "incomplete"):
                    c.require_stage_success("verify")

    def test_resource_limits_include_supervisor_and_final_boundary(self):
        for rss, now in ((c.MEMORY + 1, 1.), (100, c.WALL)):
            with patch.object(c, "tree_rss", return_value=rss), patch.object(c.time, "monotonic", return_value=now):
                with self.assertRaisesRegex(ValueError, "budget"):
                    c.budget_check(0., 0, "final")
        with patch.object(c, "tree_rss", return_value=10), patch.object(c.time, "monotonic", return_value=1):
            self.assertEqual(c.budget_check(0., 100, "final")["peak_rss_bytes"], 100)

    def test_parent_and_child_rss_are_both_accounted(self):
        child = SimpleNamespace(memory_info=lambda: SimpleNamespace(rss=200))
        parent = SimpleNamespace(memory_info=lambda: SimpleNamespace(rss=100), children=lambda recursive: [child])
        with patch.object(c.psutil, "Process", return_value=parent):
            self.assertEqual(c.tree_rss(), 300)

    def test_successful_worker_late_budget_failure_is_failed_even_if_result_published(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); out = root / "comparison"; out.mkdir()
            (root / "comparison_config.json").write_text('{}')
            c.write_json(out / "results.pending.json", {"status": "UNCOMMITTED_LEGACY_COMPARISON_REQUIRES_SUPERVISOR"})
            process = SimpleNamespace(pid=9999, poll=lambda: 0, returncode=0)
            def launch(*args, **kwargs):
                marker = c.read_json(out / "score_STARTED.json")
                c.write_json(out / "score_PARENT_GUARD_READY.json", {"parent_pid": marker["pid"],
                             "parent_created": marker["supervisor_created"], "worker_pid": process.pid})
                return process
            def boundary(started, peak, phase):
                if phase == "final":
                    raise ValueError("final budget exceeded")
                return {"phase": phase, "seconds": 1., "peak_rss_bytes": 100}
            with patch.object(c, "ROOT", root), patch.object(c, "OUTPUT", out), \
                 patch.object(c, "check_config"), patch.object(c, "insist_complete"), \
                 patch.object(c, "check_snapshot"), patch.object(c, "require_stage_success"), \
                 patch.object(c, "budget_check", side_effect=boundary), patch.object(c, "stop_group"), \
                 patch.object(c.subprocess, "Popen", side_effect=launch):
                with self.assertRaisesRegex(ValueError, "final budget"):
                    c.supervise("score")
            state = c.read_json(out / "score_RUN_RESULT.json")
            self.assertEqual(state["status"], "COMPARISON_STAGE_FAILED")
            self.assertTrue(c.read_json(out / "results.json")["requires_successful_score_stage_result"])
            with patch.object(c, "ROOT", root), patch.object(c, "OUTPUT", out):
                with self.assertRaisesRegex(ValueError, "not successful"):
                    c.require_stage_success("score")

    def test_repeated_stage_does_not_start_a_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); out = root / "comparison"; out.mkdir()
            (out / "assemble_STARTED.json").write_text('{}')
            with patch.object(c, "ROOT", root), patch.object(c, "OUTPUT", out), \
                 patch.object(c, "check_config"), patch.object(c, "insist_complete"), \
                 patch.object(c.subprocess, "Popen", side_effect=AssertionError("duplicate worker")):
                with self.assertRaisesRegex(ValueError, "already attempted"):
                    c.supervise("assemble")

    def test_freeze_requires_complete_tests_and_current_root_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reviewed = ("compare_legacy.py", "test_compare_legacy.py", "COMPARISON_NOTES.md", "PREREGISTRATION_R01.md")
            for name in reviewed:
                (root / name).write_text('synthetic ' + name)
            (root / "comparison_self_test_log.txt").write_text('synthetic test log')
            (root / "legacy_cpu.py").write_text('synthetic guard source')
            test = {"status": "PASS", "real_scores_computed": False, "tests_run": 23, "failures": 0, "errors": 0, "skipped": 0,
                    "code_sha256": {n: c.sha(root / n) for n in reviewed[:2]},
                    "selection_preregistration_sha256": c.sha(root / reviewed[-1]),
                    "log_sha256": c.sha(root / "comparison_self_test_log.txt"),
                    "guard_source_sha256": c.sha(root / "legacy_cpu.py")}
            c.write_json(root / "comparison_test_results.json", test)
            review = {"status": "PASS", "reviewed_by": "parent", "real_scores_computed": False,
                      "source_sha256": {n: c.sha(root / n) for n in reviewed},
                      "synthetic_test_sha256": c.sha(root / "comparison_test_results.json")}
            with patch.object(c, "ROOT", root), patch.object(c, "OUTPUT", root / "comparison"), \
                 patch.object(c, "EXPECTED_SELECTION_R01", c.sha(root / reviewed[-1])), \
                 patch.object(c, "modules", side_effect=AssertionError("freeze cannot reach runtime")):
                with self.assertRaisesRegex(ValueError, "regular file"):
                    c.freeze()
                c.write_json(root / "COMPARISON_REVIEW.json", review)
                c.freeze_evidence()
                for change in ({"tests_run": 0}, {"tests_run": 22}, {"failures": 1}, {"errors": 1}, {"skipped": 1}):
                    c.write_json(root / "comparison_test_results.json", {**test, **change})
                    with self.assertRaisesRegex(ValueError, "complete synthetic"):
                        c.freeze()
                c.write_json(root / "comparison_test_results.json", test)
                changed = copy.deepcopy(review); changed["source_sha256"]["COMPARISON_NOTES.md"] = "0" * 64
                c.write_json(root / "COMPARISON_REVIEW.json", changed)
                with self.assertRaisesRegex(ValueError, "review stale"):
                    c.freeze()
                self.assertFalse((root / "comparison_config.json").exists())

    def test_guarded_worker_refuses_dead_parent_and_stale_handshake(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "comparison_config.json").write_text('{}')
            marker = {"pid": c.os.getppid(), "supervisor_created": 42., "worker_token": "synthetic",
                      "mode": "assemble", "config_sha256": c.sha(root / "comparison_config.json")}
            c.write_json(root / "assemble_STARTED.json", marker)
            guard = Mock(pid=8888); guard.poll.return_value = None
            legacy = Mock(); legacy.matching_process_alive.return_value = False
            def spawn(parent, created, ready):
                c.write_json(ready, {"worker_pid": c.os.getpid(), "worker_created": -1., "watchdog_pid": guard.pid,
                                    "parent_pid": parent, "parent_created": created})
                return guard
            legacy.spawn_parent_guard.side_effect = spawn
            with patch.object(c, "ROOT", root), patch.object(c, "OUTPUT", root), \
                 patch.dict(c.os.environ, {"COMPARISON_SUPERVISED_TOKEN": "synthetic"}), \
                 patch.object(c, "modules", return_value=(None, legacy, None, None)), \
                 patch.object(c, "assemble", side_effect=AssertionError("payload must not start")):
                with self.assertRaisesRegex(ValueError, "parent identity lost"):
                    c.guarded_worker("assemble")
                legacy.spawn_parent_guard.assert_not_called()
                legacy.matching_process_alive.return_value = True
                with self.assertRaisesRegex(ValueError, "handshake invalid"):
                    c.guarded_worker("assemble")
                guard.terminate.assert_called_once()
                guard.wait.assert_called_once_with(timeout=3)

    def test_parent_death_guard_terminates_worker_inside_native_call(self):
        # Separate temporary processes only. PyDLL.sleep holds the worker GIL;
        # this proves monitoring does not rely on a Python worker thread.
        worker_code = '''import ctypes, os, psutil, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import legacy_cpu
parent = os.getppid()
guard = legacy_cpu.spawn_parent_guard(parent, psutil.Process(parent).create_time(), Path(sys.argv[2]))
Path(sys.argv[3]).write_text("native entered")
ctypes.PyDLL(None).sleep(30)
'''
        parent_code = '''import subprocess, sys, time
child = subprocess.Popen([sys.executable, "-c", sys.argv[1], *sys.argv[2:]], start_new_session=True)
time.sleep(30)
'''
        for sig in (c.signal.SIGTERM, c.signal.SIGKILL):
            with self.subTest(signal=sig), tempfile.TemporaryDirectory() as tmp:
                ready, entered = Path(tmp) / 'ready.json', Path(tmp) / 'entered'
                parent = c.subprocess.Popen([sys.executable, '-c', parent_code, worker_code, str(c.ROOT), str(ready), str(entered)],
                                            stdout=c.subprocess.DEVNULL, stderr=c.subprocess.DEVNULL)
                identity = None
                try:
                    deadline = time.monotonic() + 8
                    while not entered.exists() and time.monotonic() < deadline:
                        self.assertIsNone(parent.poll())
                        time.sleep(.02)
                    self.assertTrue(entered.exists(), 'synthetic native worker did not start')
                    identity = c.read_json(ready)
                    c.os.kill(parent.pid, sig); parent.wait(timeout=3)
                    deadline = time.monotonic() + 3
                    alive = True
                    while alive and time.monotonic() < deadline:
                        try:
                            child = c.psutil.Process(identity['worker_pid'])
                            alive = child.is_running() and child.status() != c.psutil.STATUS_ZOMBIE
                        except c.psutil.NoSuchProcess:
                            alive = False
                        if alive:
                            time.sleep(.02)
                    self.assertFalse(alive, 'orphan native worker survived loss of supervisor')
                finally:
                    if parent.poll() is None:
                        parent.kill(); parent.wait(timeout=3)
                    if identity is None and ready.exists():
                        identity = c.read_json(ready)
                    if identity is not None:
                        try:
                            c.os.killpg(identity['worker_pid'], c.signal.SIGKILL)
                        except ProcessLookupError:
                            pass

    def test_score_is_never_repeated_when_result_exists(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(c, "OUTPUT", Path(tmp)), \
             patch.object(c, "verify_readonly", side_effect=AssertionError("must not repeat")):
            path = Path(tmp) / "results.json"
            path.write_text('existing evidence')
            with self.assertRaisesRegex(ValueError, "already scored"):
                c.score()
            self.assertEqual(path.read_text(), 'existing evidence')

    def test_snapshot_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "comparison_config.json").write_text('{}')
            cache = root / "cache.bin"
            cache.write_bytes(b'original')
            c.write_json(root / "comparison_snapshot.json", {"comparison_config_sha256": c.sha(root / "comparison_config.json"),
                         "files": {"cache.bin": c.sha(cache)}})
            with patch.object(c, "ROOT", root), patch.object(c, "PROJECT", root):
                c.check_snapshot()
                cache.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError, "snapshot drift"):
                    c.check_snapshot()

    def test_t_label_reader_excludes_query_rows_at_parser(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data").mkdir()
            (root / "data/train.csv").write_text('id,Will_Buy_EV\n0,Yes\n1,FORBIDDEN_U\n2,No\n3,FORBIDDEN_U\n')
            with patch.object(c, "PROJECT", root):
                np.testing.assert_array_equal(c.t_labels(np.array([0, 2])), np.array([1, 0], dtype=np.int8))
                with self.assertRaisesRegex(ValueError, "schema"):
                    c.t_labels(np.array([0, 1]))

    def test_no_independent_proof_never_opens_any_candidate(self):
        with self.assertRaisesRegex(ValueError, "independent"):
            c.decisions(report(.7, .71), report(.69, .72), report(.69, .71), report(.69, .7), False)

    def test_d_failure_never_switches_to_better_a_or_b(self):
        result = c.decisions(report(.75, .76), report(.70, .69), report(.70, .76), report(.70, .75), True)
        self.assertFalse(result["candidate_rebuild_eligible"])
        self.assertIsNone(result["selected_candidate"])
        self.assertFalse(result["A_can_replace_D"])
        self.assertFalse(result["B_can_replace_D"])
        self.assertFalse(result["allowed_for_submission"])

    def test_two_comparisons_must_pass_and_research_threshold_stays_separate(self):
        args = (report(.70000, .70002), report(.69999, .70002), report(.69999, .70002), report(.69999, .70000), True)
        result = c.decisions(*args)
        self.assertTrue(result["candidate_rebuild_eligible"])
        self.assertEqual(result["selected_candidate"], "D")
        self.assertFalse(result["research_promotion_gate_passed"])
        failed = report(.69999, .70002, [.00003] * 4 + [-.00001])
        self.assertFalse(c.decisions(args[0], failed, *args[2:])["candidate_rebuild_eligible"])
        self.assertFalse(c.decisions(failed, *args[1:])["candidate_rebuild_eligible"])

    def test_dc_research_does_not_require_ba_point0001_or_positive_explanations(self):
        result = c.decisions(report(.7, .70002), report(.8, .8002), report(.8, .70002), report(.8, .7), True)
        self.assertTrue(result["candidate_rebuild_eligible"])
        self.assertTrue(result["research_promotion_gate_passed"])
        self.assertEqual(result["selected_candidate"], "D")

    def test_paired_auc_actual_synthetic_vectors_and_preserved_ba_match(self):
        rng = np.random.default_rng(121)
        y = np.tile([0, 1], 200)
        folds = np.repeat(np.arange(1, 6), 80)
        base = rng.uniform(0, 1, len(y))
        candidate = np.clip(base + .03 * y, 0, 1)
        r = c.paired_report(y, base, candidate, folds, AUC)
        c.match_ba(r, copy.deepcopy(r))
        wrong = copy.deepcopy(r)
        wrong["candidate_auc"] += .001
        with self.assertRaisesRegex(ValueError, "changed"):
            c.match_ba(r, wrong)

    def test_publish_refuses_to_replace_prior_score(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "result.json"
            c.publish_json_once(path, {"result": 1})
            old = path.read_bytes()
            with self.assertRaises(FileExistsError):
                c.publish_json_once(path, {"result": 2})
            self.assertEqual(path.read_bytes(), old)

    def test_full_meta_fit_uses_c_inputs_and_keeps_both_inference_outputs(self):
        rng = np.random.default_rng(909)
        y = np.tile([0, 1], 100)
        cpairs = {"v80": {"oof_proba": rng.uniform(0, 1, len(y)), "valid_proba": np.array([.1, .7])},
                  "v85": {"oof_proba": np.clip(.2 + .6*y + rng.normal(0, .3, len(y)), 0, 1), "valid_proba": np.array([.2, .8])},
                  "ct": {"oof_proba": np.clip(.3 + .4*y + rng.normal(0, .3, len(y)), 0, 1).astype(np.float32),
                         "valid_proba_fullfit": np.array([.15, .65]), "valid_proba_foldmean": np.array([.25, .85])}}
        result = AB.cpu.fit_v100_meta(*AB.meta_inputs(y, cpairs))
        independent = AB.independent_meta(*AB.meta_inputs(y, cpairs))
        prior = {"valid_idx": np.array([2, 3]), "valid_id": np.array([102, 103]),
                 "c_proba": result["refit_prediction"], "d_proba": result["foldmean_prediction"]}
        manifest = {**result, "meta_weights_reused_from_AB": False}
        errors = c.validate_c_rebuilt(prior, manifest, independent, prior["valid_idx"], np.arange(100, 104), AB)
        self.assertTrue(all(x <= 1e-12 for x in errors.values()))


if __name__ == "__main__":
    with threadpool_limits(limits=2):
        unittest.main(verbosity=2)
