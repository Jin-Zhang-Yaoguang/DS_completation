from __future__ import annotations

import json
from pathlib import Path
import tarfile
from tempfile import TemporaryDirectory
import unittest

from kaggle_environments.agent import get_last_callable


HERE = Path(__file__).resolve().parent


class KaggleRawLoaderTest(unittest.TestCase):
    def test_clean_archive_last_callable_is_agent(self) -> None:
        with TemporaryDirectory(prefix="v12a2_raw_loader_test_") as directory:
            root = Path(directory)
            with tarfile.open(HERE / "submission.tar.gz", "r:gz") as archive:
                archive.extractall(root, filter="data")
            main_path = root / "main.py"
            loaded = get_last_callable(
                main_path.read_text(encoding="utf-8"), path=str(main_path)
            )
            self.assertEqual(loaded.__name__, "agent")
            self.assertIs(loaded.__globals__["agent"], loaded)
            self.assertIsNot(loaded.__globals__["model_status"], loaded)
            self.assertEqual(
                Path(loaded.__code__.co_filename).resolve(), main_path.resolve()
            )

    def test_package_qa_proves_raw_loader_policy_equivalence(self) -> None:
        report = json.loads(
            (HERE / "package_qa_report.json").read_text(encoding="utf-8")
        )
        self.assertEqual(report["verdict"], "PASS")
        self.assertEqual(report["policy_equivalence"]["verdict"], "EXACT")
        self.assertEqual(len(report["games"]), 6)
        for game in report["games"]:
            self.assertEqual(game["steps"], 720)
            self.assertEqual(game["calls"], 719)
            self.assertEqual(game["statuses"], ["DONE", "DONE"])
            self.assertGreater(game["non_noop_action_count"], 0)
            self.assertTrue(game["formal_factory_stepwise_action_equal"])
            self.assertTrue(game["formal_factory_reward_equal"])
            self.assertIsNone(game["first_action_mismatch_step"])
            self.assertEqual(game["stderr"], "")
            self.assertEqual(game["formal_stderr"], "")


if __name__ == "__main__":
    unittest.main()
