"""扫描 Git 索引或提交快照；不输出凭证值，扫描器缺失时拒绝发布。"""
import argparse
import json
import os
import re
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tempfile


CONFIG = Path(__file__).resolve().parents[1] / ".gitleaks.toml"


def snapshot_entries(repo, ref):
    if ref:
        tree = subprocess.check_output(
            ["git", "rev-parse", "--verify", "--end-of-options", ref + "^{tree}"],
            cwd=repo, text=True,
        ).strip()
        raw = subprocess.check_output(["git", "ls-tree", "-r", "-z", tree], cwd=repo)
    else:
        raw = subprocess.check_output(["git", "ls-files", "--stage", "-z"], cwd=repo)
    entries = []
    for record in filter(None, raw.split(b"\0")):
        info, path = record.split(b"\t", 1)
        mode, kind_or_sha, sha_or_stage = info.decode().split()
        if ref:
            sha = sha_or_stage
        else:
            if sha_or_stage != "0":
                raise ValueError("索引存在未解决的合并冲突")
            sha = kind_or_sha
        path = path.decode("utf-8", "surrogateescape")
        parts = PurePosixPath(path).parts
        if not parts or PurePosixPath(path).is_absolute() or ".." in parts:
            raise ValueError("Git 快照含不安全路径")
        if mode == "160000":
            raise ValueError("快照包含子模块，需单独扫描后才能发布：" + path)
        entries.append((path, sha))
    return entries


def export_snapshot(repo, entries, target):
    # 从 Git 对象读取，避免未暂存文件、外部符号链接和 smudge filter 改变扫描内容。
    proc = subprocess.Popen(
        ["git", "cat-file", "--batch"], cwd=repo,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
    )
    try:
        for path, sha in entries:
            proc.stdin.write((sha + "\n").encode())
            proc.stdin.flush()
            header = proc.stdout.readline().decode().split()
            if len(header) != 3 or header[1] != "blob":
                raise ValueError("无法读取 Git blob：" + path)
            remaining = int(header[2])
            dest = target / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("wb") as handle:
                while remaining:
                    data = proc.stdout.read(min(remaining, 1024 * 1024))
                    if not data:
                        raise ValueError("Git blob 读取不完整：" + path)
                    handle.write(data)
                    remaining -= len(data)
            if proc.stdout.read(1) != b"\n":
                raise ValueError("Git blob 分隔符异常")
        proc.stdin.close()
        if proc.wait() != 0:
            raise ValueError("Git 快照导出失败")
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        proc.stdout.close()


def scan(repo, ref=None, binary=None, report=None, history_range=None):
    binary = binary or shutil.which("gitleaks")
    if not binary or not Path(binary).is_file():
        raise ValueError("缺少 gitleaks，拒绝发布。请安装后重试，或用 --gitleaks 指定路径。")
    env = os.environ.copy()
    for name in ("GITLEAKS_CONFIG", "GITLEAKS_CONFIG_TOML"):
        env.pop(name, None)
    version = subprocess.check_output([binary, "version"], text=True, env=env).strip()
    entries = snapshot_entries(repo, ref)
    findings = []
    with tempfile.TemporaryDirectory(prefix="ds-publication-scan-") as tmp:
        tmp = Path(tmp)
        snapshot = tmp / "snapshot"
        snapshot.mkdir()
        export_snapshot(repo, entries, snapshot)
        jobs = [("snapshot", ["dir", str(snapshot), "--max-archive-depth=2"])]
        if history_range:
            if history_range.startswith("-") or any(c.isspace() for c in history_range):
                raise ValueError("历史范围必须为一个 Git revision range")
            jobs.append(("pending_history", ["git", str(repo), "--log-opts=" + history_range]))
        for scope, command in jobs:
            raw_report = tmp / (scope + ".json")
            run = subprocess.run(
                [binary, *command, "--config", str(CONFIG), "--redact=100",
                 "--ignore-gitleaks-allow", "--gitleaks-ignore-path", str(tmp / "no-ignore"),
                 "--no-banner", "--no-color", "--report-format=json", "--report-path", str(raw_report)],
                capture_output=True, text=True, env=env,
            )
            if run.returncode not in (0, 1) or not raw_report.exists():
                raise ValueError("gitleaks 执行失败（exit %s），拒绝发布" % run.returncode)
            if re.search(r"\b(?:ERR|FTL)\b", run.stdout + run.stderr):
                raise ValueError("gitleaks 报告读取或解压错误，拒绝把不完整扫描视为通过")
            data = json.loads(raw_report.read_text())
            for item in data:
                file = item.get("File", "")
                prefix = str(snapshot) + "/"
                if file.startswith(prefix):
                    file = file[len(prefix):]
                findings.append({
                    "scope": scope, "rule": item.get("RuleID"), "file": file,
                    "line": item.get("StartLine"), "commit": item.get("Commit", ""),
                })
            # 有命中却没有可审查报告，也不能视为通过。
            if run.returncode == 1 and not data:
                raise ValueError("扫描返回风险状态但报告为空，拒绝发布")
    result = {"scanner": "gitleaks", "version": version, "ref": ref or "index",
              "files": len(entries), "history_range": history_range,
              "finding_count": len(findings), "findings": findings}
    if report:
        Path(report).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print("密钥扫描：%s 个文件，%s 个命中（gitleaks %s）。" % (len(entries), len(findings), version))
    for item in findings[:30]:
        print("%s:%s [%s] %s" % (item["file"], item["line"], item["rule"], item["scope"]))
    return 1 if findings else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--ref", help="指定提交；默认扫描暂存区")
    parser.add_argument("--gitleaks", help="gitleaks 可执行文件路径")
    parser.add_argument("--report", help="写入仅包含位置和类型的 JSON 报告")
    parser.add_argument("--history-range", help="同时扫描待发布历史，例如 origin/main..HEAD")
    args = parser.parse_args()
    try:
        repo = Path(subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], cwd=args.repo, text=True,
        ).strip())
        return scan(repo, args.ref, args.gitleaks, args.report, args.history_range)
    except (ValueError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print("密钥扫描未通过：" + str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
