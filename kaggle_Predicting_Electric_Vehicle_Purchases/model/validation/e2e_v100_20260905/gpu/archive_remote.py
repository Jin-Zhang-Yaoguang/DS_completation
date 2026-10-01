#!/usr/bin/env python3
"""一次性归档已完成的 GPU 第 1 版；只读远端，不训练、push 或提交。"""
from __future__ import annotations

import argparse
import ctypes
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parent
KERNEL = "yaoguang516/s6e9-v100-e2e-ct-cache-20260905"
VERSION = 1
KAGGLE = "/Users/a1-6/.local/bin/kaggle"
PAYLOAD = ("cache_runner.py", "ct_features.py", "supervisor.py", "bootstrap.py", "frozen_config.json")
PHASES = ("START", "BEFORE_bootstrap.py", "AFTER_START_bootstrap.py", "AFTER_EXIT_bootstrap.py",
          "AFTER_CLEANUP_bootstrap.py", "BEFORE_cache_runner.py", "AFTER_START_cache_runner.py",
          "AFTER_EXIT_cache_runner.py", "AFTER_CLEANUP_cache_runner.py", "BEFORE_COMPLETE")


class Rejected(RuntimeError):
    pass


def need(condition, reason):
    if not condition:
        raise Rejected(reason)


def sha(path):
    path = Path(path)
    need(path.is_file() and not path.is_symlink(), f"缺失普通文件或遇到链接：{path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read(path):
    sha(path)
    return json.loads(Path(path).read_text(), parse_constant=lambda value: (_ for _ in ()).throw(Rejected(value)))


def write_once(path, value):
    with Path(path).open("x") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def digest_valid(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def finite(value):
    return type(value) in (float, int) and math.isfinite(value) and value >= 0


def binding(root):
    """绑定已有第 1 版 push 回执与 revision_01 的全部冻结字节。"""
    rev = root / "revision_01"
    manifest = read(rev / "bundle_manifest.json")
    cfg = read(rev / "frozen_config.json")
    receipt = read(root / "PUSH_RECEIPT.json")
    started = read(root / "PUSH_STARTED.json")
    need(manifest["kernel"] == receipt["kernel"] == started["kernel"] == KERNEL, "kernel 不匹配")
    need(receipt["status"] == "PUSH_RETURNED" and receipt["returncode"] == 0, "没有成功 push 回执")
    need(re.match(r"^Kernel version 1 successfully pushed\.", receipt["stdout"]) is not None,
         "push 回执不是第 1 版")
    for key in ("attempt", "started_unix", "kernel", "bundle_manifest_sha256", "config_sha256"):
        need(receipt[key] == started[key], f"push intent/receipt 不同：{key}")
    need(started["status"] == "PUSH_STARTED", "push intent 状态不明")
    for name, digest in manifest["files"].items():
        need(not Path(name).is_absolute() and ".." not in Path(name).parts, "冻结路径不合法")
        need(sha(rev / name) == digest, f"本地冻结文件漂移：{name}")
    for name in PAYLOAD:
        need(name in manifest["files"], f"冻结 bundle 缺少 {name}")
    need(sha(rev / "bundle_manifest.json") == receipt["bundle_manifest_sha256"], "bundle 回执 SHA 不符")
    need(sha(rev / "frozen_config.json") == receipt["config_sha256"], "配置回执 SHA 不符")
    need(cfg["implementation_revision"] == "R01" and cfg["require_gpu"] is True, "配置不是 R01 GPU")
    need(cfg["outer_folds"] == cfg["inner_folds"] == 5, "折数漂移")
    need(cfg["budget_seconds"] == 7200 and cfg["memory_bytes"] == 24 * 1024**3 and cfg["threads"] == 4,
         "资源合同漂移")
    need(cfg["submission_budget"] == 0 and cfg["outer_scores_not_computed"] is True, "诊断合同漂移")
    need(Path(cfg["remote_output_download_target"]) == root / "remote_output", "归档目标与冻结合同不同")
    for name in PAYLOAD[:-1]:
        need(cfg["code_sha256"][name] == manifest["files"][name], "配置代码 SHA 与 bundle 不同")
    return {"kernel": KERNEL, "version": VERSION,
            "bundle_sha256": sha(rev / "bundle_manifest.json"),
            "config_sha256": sha(rev / "frozen_config.json"),
            "push_receipt_sha256": sha(root / "PUSH_RECEIPT.json"),
            "push_started_sha256": sha(root / "PUSH_STARTED.json"),
            "payload_sha256": {name: manifest["files"][name] for name in PAYLOAD}}, cfg


def tree_hashes(directory, exclude=()):
    need(directory.is_dir() and not directory.is_symlink(), "产物必须是普通目录")
    result = {}
    for path in sorted(directory.rglob("*")):
        need(not path.is_symlink(), f"产物包含符号链接：{path}")
        if path.is_file() and path.relative_to(directory).as_posix() not in exclude:
            result[path.relative_to(directory).as_posix()] = sha(path)
        else:
            need(path.is_dir() or path.is_file(), f"产物包含特殊文件：{path}")
    return result


def verify_payload(directory, expected, cfg):
    """仅验字节、完整性和运行合同；数组内容由下游 assembler 独立核验。"""
    tree_hashes(directory)
    for name, digest in expected["payload_sha256"].items():
        need(sha(directory / name) == digest, f"远端冻结字节不一致：{name}")
    started = read(directory / "GPU_RUN_STARTED.json")
    for key in ("budget_seconds", "memory_bytes", "threads"):
        need(started[key] == cfg[key], f"远端资源启动合同不符：{key}")
    need(started["one_shot"] is True, "不是一次性运行")
    result = read(directory / "GPU_RUN_RESULT.json")
    need(result["status"] == "GPU_CACHE_RUN_COMPLETE", "监督进程未最终成功")
    checks = result["resource_checks"]
    need(isinstance(checks, list) and [row["phase"] for row in checks] == list(PHASES), "资源检查阶段未完整闭合")
    previous_time, previous_peak = -1, -1
    for row in checks:
        elapsed, peak, rss = row["seconds"], row["peak_process_tree_rss"], row["rss_bytes"]
        need(all(finite(v) for v in (elapsed, peak, rss)), "资源记录无效")
        need(previous_time <= elapsed < cfg["budget_seconds"], "超时或时间记录倒退")
        need(previous_peak <= peak <= cfg["memory_bytes"] and rss <= peak, "内存超限或记录不一致")
        previous_time, previous_peak = elapsed, peak
    need(result["seconds"] == checks[-1]["seconds"] and result["peak_process_tree_rss"] == previous_peak,
         "最终资源结果与阶段记录不一致")
    complete = read(directory / "ct_cache/GPU_COMPLETE.json")
    need(complete["status"] == "CT_CACHE_COMPLETE_UNSCORED" and complete["config_sha256"] == expected["config_sha256"],
         "cache 完成合同不符")
    need(complete["complete_v100_score"] is None and complete["submission_created"] is False, "意外评分或提交产物")
    need(complete["versions"] == cfg["remote_versions"], "远端运行时版本不符")
    need(len(complete["outer_results"]) == cfg["outer_folds"], "外层折未全部完成")
    for outer, advertised in enumerate(complete["outer_results"], 1):
        folder = directory / "ct_cache" / f"outer_{outer:02d}"
        summary = read(folder / "cache_manifest.json")
        need(summary == advertised, f"outer {outer} 汇总不符")
        need(summary["status"] == "CT_CACHE_COMPLETE_UNSCORED" and summary["validation_labels_used"] is False
             and summary["allowed_for_submission"] is False, f"outer {outer} 验证合同不符")
        need(summary["source_sha256"] == cfg["source_sha256"], "训练来源 SHA 不符")
        identity = summary["identity"]
        need(identity["config_sha256"] == expected["config_sha256"], "cache 配置 SHA 不符")
        need(all(digest_valid(identity[key]) for key in
                 ("train_idx_sha256", "valid_idx_sha256", "train_id_sha256", "valid_id_sha256")), "行身份摘要不完整")
        need(digest_valid(summary["atom_fold_sha256"]), "内层折摘要缺失")
        need(sha(folder / "cache.npz") == summary["cache_sha256"], "cache 字节损坏")
        need(len(summary["atoms"]) == cfg["inner_folds"], "inner atoms 未全部完成")
        for atom, record in enumerate(summary["atoms"], 1):
            need(record == read(folder / f"atom_{atom:02d}.json") and record["atom"] == atom, "atom manifest 不符")
            need(record["identity"] == identity and finite(record["seconds"]), "atom 身份不符")
            need(sha(folder / f"atom_{atom:02d}.npz") == record["sha256"], "atom 字节损坏")
        record = read(folder / "fullfit.json")
        need(record == summary["fullfit"] and record["identity"] == identity and finite(record["seconds"]), "fullfit 合同不符")
        need(sha(folder / "fullfit.npz") == record["sha256"], "fullfit 字节损坏")
    return {"status": "VERIFIED_GPU_CACHE_UNSCORED", "outer_folds": cfg["outer_folds"],
            "seconds": result["seconds"], "peak_process_tree_rss": previous_peak,
            "file_sha256": tree_hashes(directory, ("ARCHIVE_VERIFICATION.json",))}


def verify_existing(root, expected, cfg):
    directory = root / "remote_output"
    record = read(directory / "ARCHIVE_VERIFICATION.json")
    need(record["binding"] == expected and record["version_before"] == record["version_after"] == VERSION,
         "既有归档版本或冻结绑定不符")
    verified = verify_payload(directory, expected, cfg)
    need(record["verification"] == verified, "既有归档内容漂移；拒绝覆盖")
    return {"status": "EXISTING_ARCHIVE_VERIFIED", "path": str(directory), "verification": verified}


def atomic_publish(source, destination):
    """内核原子 rename 且禁止覆盖，包括空目录；不退化为先删后改名。"""
    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        method, at_fd, flags = libc.renameatx_np, -2, 0x00000004
    elif sys.platform.startswith("linux") and hasattr(libc, "renameat2"):
        method, at_fd, flags = libc.renameat2, -100, 1
    else:
        raise Rejected("当前系统没有已核验的原子禁止覆盖 rename")
    method.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint)
    method.restype = ctypes.c_int
    if method(at_fd, os.fsencode(source), at_fd, os.fsencode(destination), flags) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), str(destination))


def run_logged(command, folder, name, timeout):
    """原始 stdout/stderr 直接落盘；超时/异常也不丢失已下载内容或输出。"""
    info = {"command": command, "started_unix": time.time(), "timeout_seconds": timeout}
    with (folder / f"{name}.stdout").open("xb") as out, (folder / f"{name}.stderr").open("xb") as err:
        try:
            result = subprocess.run(command, stdout=out, stderr=err, timeout=timeout, check=False)
            info["returncode"] = result.returncode
        except BaseException as error:
            info.update(exception_type=type(error).__name__, exception=str(error))
            raise
        finally:
            info["finished_unix"] = time.time()
            write_once(folder / f"{name}.command.json", info)
    need(result.returncode == 0, f"命令 {name} 失败；原始输出已保留于 {folder}")
    return (folder / f"{name}.stdout").read_text()


def current_version(folder, phase, runner):
    # 当前 CLI 的 status/output 忽略 parse 得到的 version，必须额外核 SDK 元数据。
    raw = runner([sys.executable, str(Path(__file__).resolve()), "_remote-version"], folder, phase, 60)
    metadata = json.loads(raw)
    need(metadata["kernel"] == KERNEL and type(metadata["current_version_number"]) is int,
         "官方元数据版本无法确认")
    need(metadata["current_version_number"] == VERSION, "远端当前版本不是第 1 版；拒绝下载/发布")
    return metadata["current_version_number"]


def download(root=ROOT, runner=run_logged):
    root = Path(root).resolve()
    expected, cfg = binding(root)
    if os.path.lexists(root / "remote_output"):
        return verify_existing(root, expected, cfg)
    with (root / "archive.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if os.path.lexists(root / "remote_output"):
            return verify_existing(root, expected, cfg)
        need(not os.path.lexists(root / "DOWNLOAD_STARTED.json"), "下载已尝试；保留原目录与日志，禁止重复下载")
        attempt = uuid.uuid4().hex
        logs = root / "archive_attempts" / attempt
        logs.mkdir(parents=True)
        temp = root / f".remote_output.download.{attempt}"
        try:
            version_before = current_version(logs, "version_before", runner)
            raw = runner([KAGGLE, "kernels", "status", f"{KERNEL}/{VERSION}"], logs, "status", 60)
            accepted = {f'{KERNEL}/{VERSION} has status "complete"',
                        f'{KERNEL}/{VERSION} has status "KernelWorkerStatus.COMPLETE"'}
            need(raw.strip() in accepted, "远端未明确 COMPLETE；RUNNING/未知状态不下载，更不重新 push")
            temp.mkdir()
            write_once(root / "DOWNLOAD_STARTED.json", {"attempt": attempt, "binding": expected,
                       "temporary_directory": str(temp), "logs": str(logs), "started_unix": time.time()})
            # 一次 CLI 调用；不传 page-token，官方实现会遍历所有页。
            runner([KAGGLE, "kernels", "output", f"{KERNEL}/{VERSION}", "-p", str(temp), "--page-size", "200"],
                   logs, "output", 900)
            version_after = current_version(logs, "version_after", runner)
            need(binding(root)[0] == expected, "下载期间本地冻结合同发生漂移")
            verified = verify_payload(temp, expected, cfg)
            write_once(temp / "ARCHIVE_VERIFICATION.json", {"binding": expected,
                       "version_before": version_before, "version_after": version_after,
                       "verification": verified, "archive_script_sha256": sha(Path(__file__)),
                       "logs": str(logs), "attempt": attempt, "verified_unix": time.time(),
                       "limitation": "仅归档字节与完成合同；数组行对齐、概率及端到端分数由 assembler 独立核验"})
            atomic_publish(temp, root / "remote_output")
            return verify_existing(root, expected, cfg)
        except BaseException as error:
            write_once(logs / "REJECTED.json", {"type": type(error).__name__, "error": str(error),
                       "temporary_directory": str(temp), "temporary_directory_preserved": temp.exists(),
                       "finished_unix": time.time()})
            raise


def remote_version():
    """唯一 SDK 调用为只读元数据查询，不绕过官方 CLI 下载。"""
    from kaggle.api.kaggle_api_extended import KaggleApi
    from kagglesdk.kernels.types.kernels_api_service import ApiGetKernelRequest
    api = KaggleApi()
    api.authenticate()
    owner, slug = KERNEL.split("/")
    request = ApiGetKernelRequest()
    request.user_name, request.kernel_slug = owner, slug
    with api.build_kaggle_client() as client:
        response = client.kernels.kernels_api_client.get_kernel(request)
    metadata = response.metadata
    need(metadata.ref == KERNEL, "官方元数据 ref 不符")
    print(json.dumps({"kernel": metadata.ref, "current_version_number": metadata.current_version_number}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("download", "verify", "_remote-version"))
    args = parser.parse_args()
    if args.command == "_remote-version":
        remote_version()
    else:
        expected, cfg = binding(ROOT)
        result = download() if args.command == "download" else verify_existing(ROOT, expected, cfg)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ARCHIVE_REJECTED: {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(2)
