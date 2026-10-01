"""检查发布树中的本地 AI 配置和凭证；忽略规则不会移除已跟踪文件。"""
import argparse
import subprocess
from pathlib import PurePosixPath
from scan_secrets import scan
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--ref", help="核对指定提交；默认核对 Git 索引")
parser.add_argument("--gitleaks", help="gitleaks 可执行文件路径")
parser.add_argument("--report", help="写入脱敏的密钥扫描 JSON 报告")
parser.add_argument("--history-range", help="同时扫描待发布历史，例如 origin/main..HEAD")
args = parser.parse_args()
command = ["git", "ls-tree", "-r", "--name-only", "-z", args.ref] if args.ref else ["git", "ls-files", "-z"]
paths = subprocess.check_output(command).decode().split("\0")
blocked = []
for path in filter(None, paths):
    parts = [p.casefold() for p in PurePosixPath(path).parts]
    if any(p in {".claude", ".codex", ".agents"} for p in parts) or parts[-1] in {"claude.md", ".claude.md", ".claude"}:
        blocked.append(path)
if blocked:
    print("发布树包含本地 AI 配置：")
    print("\n".join(blocked))
    raise SystemExit(1)
print("发布树检查通过：不含 .claude / .codex / .agents / CLAUDE.md。历史提交未重写。")
repo = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
try:
    raise SystemExit(scan(repo, args.ref, args.gitleaks, args.report, args.history_range))
except (ValueError, OSError, subprocess.CalledProcessError) as exc:
    print("发布检查未通过：" + str(exc))
    raise SystemExit(2)
