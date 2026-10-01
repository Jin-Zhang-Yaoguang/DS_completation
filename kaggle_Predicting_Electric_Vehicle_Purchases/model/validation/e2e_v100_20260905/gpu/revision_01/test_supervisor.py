"""只测试监督协议；不导入 CTBoost，不训练比赛数据。"""
import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import supervisor as s
import build_kernel as b


class SupervisorTests(unittest.TestCase):
    def test_exact_wall_boundary_and_final_stage(self):
        clock = [s.LIMIT - 0.1]
        budget = s.Budget(started=0, clock=lambda: clock[0], rss=lambda: 12)
        budget.check("BEFORE_COMPLETE")
        clock[0] = s.LIMIT
        with self.assertRaises(TimeoutError):
            budget.check("BEFORE_COMPLETE")

    def test_rss_budget_and_persistent_peak(self):
        memory = [s.MEMORY]
        budget = s.Budget(started=0, clock=lambda: 1, rss=lambda: memory[0])
        budget.check("START")
        memory[0] += 1
        with self.assertRaises(MemoryError):
            budget.check("AFTER_EXIT")
        memory[0] = 1
        with self.assertRaises(MemoryError):
            budget.check("BEFORE_COMPLETE")

    def test_supervisor_rss_is_included(self):
        child = SimpleNamespace(memory_info=lambda: SimpleNamespace(rss=17))
        root = SimpleNamespace(memory_info=lambda: SimpleNamespace(rss=11), children=lambda recursive: [child])
        with patch.object(s.psutil, "Process", return_value=root):
            self.assertEqual(s.process_tree_rss(), 28)

    def test_exited_child_does_not_cause_false_failure(self):
        class Gone:
            def memory_info(self):
                raise s.psutil.NoSuchProcess(99999999)
        root = SimpleNamespace(memory_info=lambda: SimpleNamespace(rss=11), children=lambda recursive: [Gone()])
        with patch.object(s.psutil, "Process", return_value=root):
            self.assertEqual(s.process_tree_rss(), 11)

    def test_exit_between_polls_still_checks_budget(self):
        clock = [0.0]
        budget = s.Budget(started=0, clock=lambda: clock[0], rss=lambda: 12)
        class Finished:
            returncode = 0
            pid = 99999999
            def poll(self):
                clock[0] = s.LIMIT
                return 0
        with patch.object(s, "kill_tree"):
            with self.assertRaises(TimeoutError):
                s.guarded("cache_runner.py", budget, popen=lambda *a, **k: Finished())
        self.assertIn("AFTER_EXIT_cache_runner.py", [row["phase"] for row in budget.checks])

    def test_budget_checked_before_starting_next_stage(self):
        budget = s.Budget(started=0, clock=lambda: s.LIMIT, rss=lambda: 12)
        with patch.object(s.subprocess, "Popen") as start:
            with self.assertRaises(TimeoutError):
                s.guarded("bootstrap.py", budget, popen=start)
            start.assert_not_called()

    def test_four_thread_environment_for_bootstrap_and_cache(self):
        with patch.dict(os.environ, {key: "99" for key in s.THREAD_KEYS}):
            env = s.child_environment()
            self.assertTrue(all(env[key] == "4" for key in s.THREAD_KEYS))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "bootstrap.py").write_text(
                "import os,json\nfrom pathlib import Path\n"
                f"Path('env.json').write_text(json.dumps({{k:os.environ.get(k) for k in {s.THREAD_KEYS!r}}}))\n")
            budget = s.Budget()
            s.guarded("bootstrap.py", budget, root)
            observed = json.loads((root / "env.json").read_text())
            self.assertTrue(all(observed[key] == "4" for key in s.THREAD_KEYS))
            self.assertIn("AFTER_EXIT_bootstrap.py", [row["phase"] for row in budget.checks])
            self.assertIn("AFTER_CLEANUP_bootstrap.py", [row["phase"] for row in budget.checks])

    def test_one_shot_does_not_launch_second_time(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(s, "guarded") as guarded:
                s.main(root)
                self.assertEqual(guarded.call_count, 2)
                with self.assertRaises(FileExistsError):
                    s.main(root)
                self.assertEqual(guarded.call_count, 2)
            result = json.loads((root / "GPU_RUN_RESULT.json").read_text())
            self.assertEqual(result["status"], "GPU_CACHE_RUN_COMPLETE")
            self.assertEqual(result["resource_checks"][-1]["phase"], "BEFORE_COMPLETE")

    def test_failure_persists_result(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(s, "guarded", side_effect=MemoryError("synthetic boundary")):
                with self.assertRaises(MemoryError):
                    s.main(root)
            result = json.loads((root / "GPU_RUN_RESULT.json").read_text())
            self.assertEqual(result["status"], "GPU_CACHE_RUN_FAILED")
            self.assertEqual(result["type"], "MemoryError")

    def test_nearest_ancestor_project(self):
        expected = Path(__file__).resolve().parents[5]
        self.assertEqual(b.find_project(Path(__file__).resolve().parent), expected)
        self.assertEqual(b.PROJECT, expected)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                b.find_project(Path(directory))


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SupervisorTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
    root = Path(__file__).resolve().parent
    payload = {"status": "SUPERVISOR_BOUNDARY_TEST_PASS", "tests_run": result.testsRun,
               "real_training_performed": False, "supervisor_rss_included": True,
               "before_after_and_final_budget_checked": True, "bootstrap_env_limited": True,
               "one_shot_guard_tested": True, "local_push_owned_by_parent": True,
               "code_sha256": {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                               for name in ("supervisor.py", "test_supervisor.py", "build_kernel.py")}}
    (root / "supervisor_test_results.json").write_text(json.dumps(payload, indent=2) + "\n")
