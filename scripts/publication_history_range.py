"""为 CI 选择历史扫描范围；旧 SHA 不可达时扫描当前完整历史。"""
import json
from pathlib import Path
import re
import subprocess
import sys


def history_range(repo, event):
    pull = event.get("pull_request") or {}
    base = (pull.get("base") or {}).get("sha") or event.get("before", "")
    if not isinstance(base, str) or not re.fullmatch(r"[0-9a-f]{40}", base) or base == "0" * 40:
        return "HEAD"
    exists = subprocess.run(
        ["git", "cat-file", "-e", base + "^{commit}"], cwd=repo, capture_output=True,
    ).returncode == 0
    if not exists:
        return "HEAD"
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", base, "HEAD"], cwd=repo, capture_output=True,
    ).returncode == 0
    return base + "..HEAD" if ancestor else "HEAD"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("用法：publication_history_range.py EVENT_JSON")
    event = json.loads(Path(sys.argv[1]).read_text())
    print(history_range(Path.cwd(), event))
