"""检查 Git 发布树是否含本地 AI 配置；忽略规则不会自动移除已跟踪文件。"""
import argparse
import subprocess
from pathlib import PurePosixPath

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--ref", help="核对指定提交；默认核对 Git 索引")
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
