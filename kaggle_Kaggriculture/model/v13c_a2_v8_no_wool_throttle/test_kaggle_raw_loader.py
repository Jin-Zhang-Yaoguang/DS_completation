from __future__ import annotations

import json
from pathlib import Path
import tarfile
from tempfile import TemporaryDirectory
import unittest

from kaggle_environments.agent import get_last_callable


HERE = Path(__file__).resolve().parent


class RawLoaderTest(unittest.TestCase):
    def test_real_loader_selects_agent_from_clean_archive(self) -> None:
        with TemporaryDirectory(prefix="v13c_raw_") as directory:
            root = Path(directory)
            with tarfile.open(HERE / "submission.tar.gz", "r:gz") as archive:
                archive.extractall(root, filter="data")
            main_path = root / "main.py"
            loaded = get_last_callable(main_path.read_text(encoding="utf-8"), path=str(main_path))
            self.assertEqual(loaded.__name__, "agent")
            self.assertIs(loaded.__globals__["agent"], loaded)
            self.assertEqual(Path(loaded.__code__.co_filename).resolve(), main_path.resolve())

    def test_package_qa_passes(self) -> None:
        report = json.loads((HERE / "package_qa_report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["verdict"], "PASS")
        self.assertEqual(len(report["games"]), 6)


if __name__ == "__main__":
    unittest.main()
