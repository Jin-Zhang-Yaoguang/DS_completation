"""验证正常推送、缺失旧 SHA 和历史重写后的 CI 扫描边界。"""
from pathlib import Path
import subprocess
import tempfile
import unittest

from publication_history_range import history_range


class HistoryRangeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.git("init", "-q")
        self.git("config", "user.name", "History Test")
        self.git("config", "user.email", "test@example.invalid")
        (self.repo / "data.txt").write_text("baseline\n")
        self.git("add", "data.txt")
        self.git("commit", "-qm", "baseline")
        self.base = self.git("rev-parse", "HEAD").strip()
        (self.repo / "data.txt").write_text("updated\n")
        self.git("add", "data.txt")
        self.git("commit", "-qm", "update")

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.repo, text=True)

    def test_normal_push_and_pull_request_use_introduced_commits(self):
        self.assertEqual(history_range(self.repo, {"before": self.base}), self.base + "..HEAD")
        event = {"pull_request": {"base": {"sha": self.base}}}
        self.assertEqual(history_range(self.repo, event), self.base + "..HEAD")

    def test_missing_old_sha_scans_entire_current_history(self):
        self.assertEqual(history_range(self.repo, {"before": "f" * 40}), "HEAD")

    def test_old_sha_present_but_not_ancestor_scans_entire_history(self):
        self.git("checkout", "-q", "--orphan", "sanitized")
        self.git("commit", "-qm", "sanitized root")
        self.assertEqual(history_range(self.repo, {"before": self.base}), "HEAD")

    def test_new_branch_or_invalid_before_scans_entire_history(self):
        for base in ["0" * 40, "--all", None]:
            self.assertEqual(history_range(self.repo, {"before": base}), "HEAD")


if __name__ == "__main__":
    unittest.main()
