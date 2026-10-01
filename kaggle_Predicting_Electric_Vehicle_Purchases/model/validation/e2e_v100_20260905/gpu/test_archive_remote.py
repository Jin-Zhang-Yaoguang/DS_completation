"""只使用临时合成文件与替身命令；禁止接触真实远端作业。"""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("archive_remote", Path(__file__).with_name("archive_remote.py"))
A = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(A)


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def fixture(base):
    root, payload = base / "gpu", base / "synthetic_remote"
    rev = root / "revision_01"
    rev.mkdir(parents=True)
    payload.mkdir()
    for name in A.PAYLOAD[:-1]:
        (rev / name).write_text("# 合成文件，不运行\n" + name + "\n")
    cfg = {"implementation_revision": "R01", "require_gpu": True, "outer_folds": 5, "inner_folds": 5,
           "budget_seconds": 7200, "memory_bytes": 24 * 1024**3, "threads": 4,
           "submission_budget": 0, "outer_scores_not_computed": True,
           "remote_output_download_target": str(root / "remote_output"),
           "code_sha256": {name: A.sha(rev / name) for name in A.PAYLOAD[:-1]},
           "source_sha256": {"train.csv": "a" * 64, "original.csv": "b" * 64},
           "remote_versions": {"numpy": "2.0.2", "pandas": "2.3.3", "sklearn": "1.6.1"}}
    save(rev / "frozen_config.json", cfg)
    manifest = {"kernel": A.KERNEL, "files": {name: A.sha(rev / name) for name in A.PAYLOAD}}
    save(rev / "bundle_manifest.json", manifest)
    started = {"attempt": "synthetic", "started_unix": 1, "kernel": A.KERNEL, "status": "PUSH_STARTED",
               "bundle_manifest_sha256": A.sha(rev / "bundle_manifest.json"),
               "config_sha256": A.sha(rev / "frozen_config.json")}
    save(root / "PUSH_STARTED.json", started)
    save(root / "PUSH_RECEIPT.json", {**started, "status": "PUSH_RETURNED", "returncode": 0,
                                     "stdout": "Kernel version 1 successfully pushed. synthetic"})
    for name in A.PAYLOAD:
        shutil.copyfile(rev / name, payload / name)
    save(payload / "GPU_RUN_STARTED.json", {key: cfg[key] for key in ("budget_seconds", "memory_bytes", "threads")} | {"one_shot": True})
    checks = [{"phase": phase, "seconds": index + 1., "rss_bytes": 100, "peak_process_tree_rss": 100}
              for index, phase in enumerate(A.PHASES)]
    save(payload / "GPU_RUN_RESULT.json", {"status": "GPU_CACHE_RUN_COMPLETE", "seconds": 10.,
                                          "peak_process_tree_rss": 100, "resource_checks": checks})
    summaries = []
    for outer in range(1, 6):
        folder = payload / "ct_cache" / f"outer_{outer:02d}"
        folder.mkdir(parents=True)
        identity = {key: str(outer) * 64 for key in ("train_idx_sha256", "valid_idx_sha256", "train_id_sha256", "valid_id_sha256")}
        identity["config_sha256"] = started["config_sha256"]
        atoms = []
        for atom in range(1, 6):
            cp = folder / f"atom_{atom:02d}.npz"
            cp.write_bytes(f"synthetic bytes {outer} {atom}".encode())
            record = {"atom": atom, "seconds": 1., "identity": identity, "sha256": A.sha(cp)}
            save(folder / f"atom_{atom:02d}.json", record)
            atoms.append(record)
        cp = folder / "fullfit.npz"
        cp.write_bytes(b"synthetic fullfit")
        record = {"seconds": 1., "identity": identity, "sha256": A.sha(cp)}
        save(folder / "fullfit.json", record)
        (folder / "cache.npz").write_bytes(b"synthetic cache")
        summary = {"status": "CT_CACHE_COMPLETE_UNSCORED", "identity": identity,
                   "cache_sha256": A.sha(folder / "cache.npz"), "atoms": atoms, "fullfit": record,
                   "atom_fold_sha256": "c" * 64, "validation_labels_used": False,
                   "allowed_for_submission": False, "source_sha256": cfg["source_sha256"]}
        save(folder / "cache_manifest.json", summary)
        summaries.append(summary)
    save(payload / "ct_cache/GPU_COMPLETE.json", {"status": "CT_CACHE_COMPLETE_UNSCORED",
         "config_sha256": started["config_sha256"], "outer_results": summaries,
         "versions": cfg["remote_versions"], "complete_v100_score": None, "submission_created": False})
    return root, payload


class FakeCLI:
    def __init__(self, payload, status="KernelWorkerStatus.COMPLETE", before=1, after=1, fail=False):
        self.payload, self.status, self.before, self.after, self.fail = payload, status, before, after, fail
        self.calls = []

    def __call__(self, command, folder, name, timeout):
        self.calls.append((name, command))
        if name.startswith("version_"):
            raw = json.dumps({"kernel": A.KERNEL, "current_version_number": self.before if name == "version_before" else self.after})
        elif name == "status":
            raw = f'{A.KERNEL}/1 has status "{self.status}"\n'
        elif name == "output":
            target = Path(command[command.index("-p") + 1])
            if self.fail:
                (target / "partial.bin").write_bytes(b"unfinished")
            else:
                shutil.copytree(self.payload, target, dirs_exist_ok=True)
            raw = "synthetic output command"
        else:
            raise AssertionError("不允许的命令")
        (folder / f"{name}.stdout").write_bytes(raw.encode())
        (folder / f"{name}.stderr").write_bytes(b"synthetic stderr")
        A.write_once(folder / f"{name}.command.json", {"command": command, "returncode": 9 if name == "output" and self.fail else 0})
        if name == "output" and self.fail:
            raise A.Rejected("synthetic output failure")
        return raw


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="s6e9_archive_synthetic_")
        self.base = Path(self.temp.name).resolve()
        self.root, self.payload = fixture(self.base)
        self.expected, self.cfg = A.binding(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def reject_payload(self):
        with self.assertRaises((A.Rejected, FileNotFoundError)):
            A.verify_payload(self.payload, self.expected, self.cfg)

    def test_valid_synthetic_payload(self):
        self.assertEqual(A.verify_payload(self.payload, self.expected, self.cfg)["outer_folds"], 5)

    def test_each_frozen_file_tamper_rejected(self):
        for name in A.PAYLOAD:
            original = (self.payload / name).read_bytes()
            (self.payload / name).write_bytes(original + b"tampered")
            self.reject_payload()
            (self.payload / name).write_bytes(original)

    def test_local_bundle_drift_rejected(self):
        (self.root / "revision_01/cache_runner.py").write_text("tampered")
        with self.assertRaises(A.Rejected):
            A.binding(self.root)

    def test_push_version_drift_rejected(self):
        path = self.root / "PUSH_RECEIPT.json"
        record = A.read(path)
        record["stdout"] = "Kernel version 2 successfully pushed."
        save(path, record)
        with self.assertRaises(A.Rejected):
            A.binding(self.root)

    def test_failed_supervisor_rejected(self):
        path = self.payload / "GPU_RUN_RESULT.json"
        record = A.read(path)
        record["status"] = "GPU_CACHE_RUN_FAILED"
        save(path, record)
        self.reject_payload()

    def test_budget_and_final_closure_rejections(self):
        path = self.payload / "GPU_RUN_RESULT.json"
        valid = A.read(path)
        changes = [lambda x: x.update(seconds=11),
                   lambda x: x["resource_checks"][-1].update(seconds=7200),
                   lambda x: x["resource_checks"][-1].update(peak_process_tree_rss=24 * 1024**3 + 1),
                   lambda x: x["resource_checks"].pop(),
                   lambda x: x["resource_checks"][-1].update(seconds=float("nan")),
                   lambda x: x["resource_checks"][-1].update(seconds=-1)]
        for change in changes:
            record = copy.deepcopy(valid)
            change(record)
            save(path, record)
            self.reject_payload()

    def test_missing_cache_and_tampered_atom_rejected(self):
        path = self.payload / "ct_cache/outer_05/cache.npz"
        path.unlink()
        self.reject_payload()
        path.write_bytes(b"synthetic cache")
        (self.payload / "ct_cache/outer_01/atom_03.npz").write_bytes(b"corrupt")
        self.reject_payload()

    def test_symlink_rejected(self):
        (self.payload / "link").symlink_to(self.payload / "cache_runner.py")
        self.reject_payload()

    def test_running_unknown_do_not_consume_download(self):
        for status in ("running", "KernelWorkerStatus.RUNNING", "unknown", "COMPLETE maybe"):
            cli = FakeCLI(self.payload, status=status)
            with self.assertRaises(A.Rejected):
                A.download(self.root, cli)
            self.assertNotIn("output", [name for name, _ in cli.calls])
            self.assertFalse((self.root / "DOWNLOAD_STARTED.json").exists())
            self.assertFalse((self.root / "remote_output").exists())

    def test_version_before_after_drift_rejected(self):
        cli = FakeCLI(self.payload, before=2)
        with self.assertRaises(A.Rejected):
            A.download(self.root, cli)
        self.assertEqual([name for name, _ in cli.calls], ["version_before"])
        cli = FakeCLI(self.payload, after=2)
        with self.assertRaises(A.Rejected):
            A.download(self.root, cli)
        self.assertTrue((self.root / "DOWNLOAD_STARTED.json").exists())
        self.assertFalse((self.root / "remote_output").exists())
        self.assertEqual(len(list(self.root.glob(".remote_output.download.*"))), 1)

    def test_output_failure_preserves_raw_and_prevents_retry(self):
        cli = FakeCLI(self.payload, fail=True)
        with self.assertRaises(A.Rejected):
            A.download(self.root, cli)
        started = A.read(self.root / "DOWNLOAD_STARTED.json")
        self.assertEqual((Path(started["temporary_directory"]) / "partial.bin").read_bytes(), b"unfinished")
        logs = Path(started["logs"])
        self.assertEqual((logs / "output.stdout").read_bytes(), b"synthetic output command")
        self.assertEqual((logs / "output.stderr").read_bytes(), b"synthetic stderr")
        count = len(cli.calls)
        with self.assertRaises(A.Rejected):
            A.download(self.root, cli)
        self.assertEqual(len(cli.calls), count)
        self.assertFalse((self.root / "remote_output").exists())

    def test_success_recheck_is_readonly_and_no_second_command(self):
        cli = FakeCLI(self.payload)
        A.download(self.root, cli)
        directory = self.root / "remote_output"
        before = {p.relative_to(directory).as_posix(): (p.stat().st_ino, p.stat().st_mtime_ns, p.read_bytes())
                  for p in directory.rglob("*") if p.is_file()}
        count = len(cli.calls)
        A.download(self.root, cli)
        after = {p.relative_to(directory).as_posix(): (p.stat().st_ino, p.stat().st_mtime_ns, p.read_bytes())
                 for p in directory.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(len(cli.calls), count)
        self.assertEqual([name for name, _ in cli.calls], ["version_before", "status", "output", "version_after"])
        output = next(command for name, command in cli.calls if name == "output")
        self.assertEqual(output[:4], [A.KAGGLE, "kernels", "output", A.KERNEL + "/1"])
        self.assertNotIn("--force", output)
        self.assertFalse(any("push" in command for _, command in cli.calls))

    def test_existing_invalid_directory_not_overwritten(self):
        target = self.root / "remote_output"
        target.mkdir()
        (target / "keep").write_bytes(b"existing")
        cli = FakeCLI(self.payload)
        with self.assertRaises((A.Rejected, FileNotFoundError)):
            A.download(self.root, cli)
        self.assertEqual((target / "keep").read_bytes(), b"existing")
        self.assertEqual(cli.calls, [])

    def test_existing_archive_tampering_rejected_without_overwrite(self):
        cli = FakeCLI(self.payload)
        A.download(self.root, cli)
        path = self.root / "remote_output/cache_runner.py"
        path.write_bytes(b"tampered existing")
        count = len(cli.calls)
        with self.assertRaises(A.Rejected):
            A.download(self.root, cli)
        self.assertEqual(path.read_bytes(), b"tampered existing")
        self.assertEqual(len(cli.calls), count)

    def test_atomic_publish_never_replaces_even_empty_directory(self):
        source, target = self.base / "source", self.base / "existing"
        source.mkdir()
        target.mkdir()
        inode = target.stat().st_ino
        with self.assertRaises(FileExistsError):
            A.atomic_publish(source, target)
        self.assertTrue(source.exists())
        self.assertEqual(target.stat().st_ino, inode)
        target.rmdir()
        A.atomic_publish(source, target)
        self.assertFalse(source.exists())
        self.assertTrue(target.exists())

    def test_real_runner_retains_nonzero_and_timeout_output_locally(self):
        logs = self.base / "logs"
        logs.mkdir()
        with self.assertRaises(A.Rejected):
            A.run_logged([sys.executable, "-c", "import sys;print('out');print('err',file=sys.stderr);sys.exit(3)"], logs, "failed", 5)
        self.assertEqual((logs / "failed.stdout").read_text(), "out\n")
        self.assertEqual((logs / "failed.stderr").read_text(), "err\n")
        with self.assertRaises(subprocess.TimeoutExpired):
            A.run_logged([sys.executable, "-u", "-c", "import time;print('partial');time.sleep(2)"], logs, "timeout", .1)
        self.assertEqual((logs / "timeout.stdout").read_text(), "partial\n")
        self.assertEqual(A.read(logs / "timeout.command.json")["exception_type"], "TimeoutExpired")


if __name__ == "__main__":
    unittest.main(verbosity=2)
