from __future__ import annotations

import json
from pathlib import Path
import tarfile
from tempfile import TemporaryDirectory
import unittest

from kaggle_environments.agent import get_last_callable

from kaggle_Kaggriculture.model.v14_queue_s1 import main


HERE = Path(__file__).resolve().parent


class PackageContractTest(unittest.TestCase):
    def test_source_entry_contract(self) -> None:
        text = (HERE / "main.py").read_text(encoding="utf-8")
        self.assertNotIn("__file__", text)
        self.assertGreater(text.rfind("def agent("), text.rfind("def model_status("))
        self.assertEqual(main.make_agent().diagnostics()["model_id"], "v14_queue_s1")

    def test_real_loader_selects_clean_agent(self) -> None:
        with TemporaryDirectory(prefix="v14_qs1_raw_test_") as directory:
            root = Path(directory)
            with tarfile.open(HERE / "submission.tar.gz", "r:gz") as archive:
                archive.extractall(root, filter="data")
            main_path = root / "main.py"
            loaded = get_last_callable(main_path.read_text(encoding="utf-8"), path=str(main_path))
            self.assertEqual(loaded.__name__, "agent")
            self.assertIs(loaded.__globals__["agent"], loaded)
            self.assertEqual(Path(loaded.__code__.co_filename).resolve(), main_path.resolve())

    def test_generated_qa_is_pass(self) -> None:
        report = json.loads((HERE / "package_qa_report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["verdict"], "PASS")
        self.assertEqual(len(report["games"]), 6)


if __name__ == "__main__":
    unittest.main()

