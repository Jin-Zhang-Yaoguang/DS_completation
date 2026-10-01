"""用临时 Git 仓库验证密钥门禁，所有凭证均为现场构造的无效样例。"""
from pathlib import Path
import contextlib
import io
import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest

from scan_secrets import scan


class SecretScanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.binary = shutil.which("gitleaks")
        self.assertIsNotNone(self.binary, "测试需要安装 gitleaks")
        self.git("init", "-q")
        self.git("config", "user.name", "Security Test")
        self.git("config", "user.email", "test@example.invalid")
        self.file = self.repo / "page.html"
        self.file.write_text("No credentials\n")
        self.git("add", "page.html")
        self.git("commit", "-qm", "baseline")
        self.base = self.git("rev-parse", "HEAD").strip()
        # 不是从任何账户取得的 Key，也不把完整格式凭证写进测试源码。
        self.fake = "AI" + "za" + "A1b2C3d4E5f6G7h8I9j0K_l-MnOpQrStUvW"

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.repo, text=True)

    def run_scan(self, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            code = scan(self.repo, binary=self.binary, **kwargs)
        self.assertNotIn(self.fake, output.getvalue())
        return code

    def test_commit_snapshot_detects_and_redacts_google_key(self):
        self.file.write_text("key: '" + self.fake + "'\n")
        self.git("add", "page.html")
        self.git("commit", "-qm", "invalid key fixture")
        report = self.repo / "report.json"
        self.assertEqual(self.run_scan(ref="HEAD", report=report), 1)
        self.assertNotIn(self.fake, report.read_text())
        self.assertIn("ds-google-api-key", report.read_text())

    def test_scan_reads_index_even_when_worktree_is_clean(self):
        self.file.write_text("key: '" + self.fake + "'\n")
        self.git("add", "page.html")
        self.file.write_text("No credentials\n")
        self.assertEqual(self.run_scan(), 1)
        self.git("add", "page.html")
        self.assertEqual(self.run_scan(), 0)

    def test_pending_history_detects_key_removed_before_head(self):
        self.file.write_text("key: '" + self.fake + "'\n")
        self.git("add", "page.html")
        self.git("commit", "-qm", "invalid key fixture")
        self.file.write_text("No credentials\n")
        self.git("add", "page.html")
        self.git("commit", "-qm", "redact fixture")
        self.assertEqual(self.run_scan(ref="HEAD"), 0)
        self.assertEqual(self.run_scan(ref="HEAD", history_range=self.base + "..HEAD"), 1)

    def test_missing_scanner_blocks_publication(self):
        with self.assertRaisesRegex(ValueError, "拒绝发布"):
            scan(self.repo, binary=str(self.repo / "missing-gitleaks"))

    def test_hash_metadata_allowlist_does_not_hide_api_credentials(self):
        value = hashlib.sha256(b"invalid cache fixture").hexdigest()
        self.file.write_text(json.dumps({"cache_key": value, "api_sha256": value}))
        self.git("add", "page.html")
        self.assertEqual(self.run_scan(), 0)
        self.file.write_text(json.dumps({"api_key": value}))
        self.git("add", "page.html")
        self.assertEqual(self.run_scan(), 1)

    def test_kaggle_credentials_in_both_json_orders(self):
        value = hashlib.md5(b"invalid credential fixture").hexdigest()
        for fields in [
            {"username": "fixture_user", "key": value},
            {"key": value, "username": "fixture_user"},
        ]:
            self.file.write_text(json.dumps(fields))
            self.git("add", "page.html")
            self.assertEqual(self.run_scan(), 1)
        for prefix in ["KG" + "AT_", "KG" + "RT_"]:
            self.file.write_text(json.dumps({"credential": prefix + value}))
            self.git("add", "page.html")
            self.assertEqual(self.run_scan(), 1)

    def test_incomplete_scan_cannot_pass_with_zero_exit_code(self):
        fake_scanner = self.repo / "scanner-with-read-error"
        fake_scanner.write_text(
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "from pathlib import Path\n"
            "if sys.argv[1] == 'version':\n"
            "    print('fixture')\n"
            "else:\n"
            "    report = sys.argv[sys.argv.index('--report-path') + 1]\n"
            "    Path(report).write_text('[]')\n"
            "    print('ERR compressed file read failed', file=sys.stderr)\n"
        )
        fake_scanner.chmod(0o755)
        with self.assertRaisesRegex(ValueError, "不完整扫描"):
            scan(self.repo, binary=str(fake_scanner))


if __name__ == "__main__":
    unittest.main()
