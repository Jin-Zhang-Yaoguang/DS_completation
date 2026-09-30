"""把本地策略源嵌入单文件 Kaggle Notebook，防止漏传模块。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
source = (ROOT / "adaptive_agent.py").read_text(encoding="utf-8")
source_sha = hashlib.sha256(source.encode()).hexdigest()

setup = '''import subprocess
import sys
from pathlib import Path

# 比赛附件提供离线 wheel；Kaggle 提交时网络保持关闭。
wheel_files = sorted(Path("/kaggle/input").rglob("arc_agi-0.9.8*.whl"))
if not wheel_files:
    mounted = [str(path) for path in Path("/kaggle/input").glob("*")]
    raise RuntimeError(f"找不到比赛附件的 arc-agi wheel；当前 /kaggle/input: {mounted}")
wheel_dir = str(wheel_files[0].parent)
competition_root = wheel_files[0].parent.parent
print("arc-agi wheel directory", wheel_dir)
subprocess.run([sys.executable, "-m", "pip", "install", "--no-index", "--find-links", wheel_dir,
                "arc-agi==0.9.8"], check=True)
'''

runner = '''from concurrent.futures import ThreadPoolExecutor, as_completed
from arc_agi import Arcade, OperationMode

# 普通 Notebook commit 以公开环境离线自测；正式比赛评测注入的
# OPERATION_MODE=competition 会被官方 SDK 优先采用，转向隐藏评测服务。
arc = Arcade(operation_mode=OperationMode.OFFLINE,
             environments_dir=str(competition_root / "environment_files"))
print("operation_mode", arc.operation_mode, "environments", len(arc.get_environments()))
environments = arc.get_environments()
if not environments:
    raise RuntimeError("ARC-AGI-3 未返回可用游戏；检查比赛专用运行环境")

card_id = arc.open_scorecard(tags=["adaptive_exploration_v1", "kaggle"])
results = []
errors = []
def run_one(info):
    game_id = info.game_id
    env = arc.make(game_id, scorecard_id=card_id)
    if env is None:
        raise RuntimeError(f"无法创建游戏 {game_id}")
    result = play_game(env, game_id, max_actions=240)
    return {key: value for key, value in result.items() if key != "history"}

try:
    with ThreadPoolExecutor(max_workers=12) as pool:
        jobs = {pool.submit(run_one, info): info.game_id for info in environments}
        for job in as_completed(jobs):
            game_id = jobs[job]
            try:
                result = job.result()
                results.append(result)
                print(result, flush=True)
            except Exception as exc:
                errors.append({"game_id": game_id, "error": repr(exc)})
                print("GAME_ERROR", errors[-1], flush=True)
finally:
    scorecard = arc.close_scorecard(card_id)

print("games_completed", len(results), "games_failed", len(errors))
print("scorecard", scorecard.model_dump(mode="json") if scorecard else None)
'''

notebook = {
    "cells": [
        {"cell_type": "markdown", "id": "overview", "metadata": {}, "source": [
            "# ARC-AGI-3 反馈探索基线\\n",
            "从局内画面变化和关卡反馈中选择动作；不读取游戏源码或隐藏答案。\\n",
            f"策略源 SHA256：`{source_sha}`。\\n",
        ]},
        {"cell_type": "code", "id": "install-offline-sdk", "execution_count": None, "metadata": {}, "outputs": [],
         "source": setup.splitlines(keepends=True)},
        {"cell_type": "code", "id": "adaptive-policy", "execution_count": None, "metadata": {}, "outputs": [],
         "source": source.splitlines(keepends=True)},
        {"cell_type": "code", "id": "run-games", "execution_count": None, "metadata": {}, "outputs": [],
         "source": runner.splitlines(keepends=True)},
    ],
    "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                 "language_info": {"name": "python"}},
    "nbformat": 4,
    "nbformat_minor": 5,
}

path = ROOT / "submission.ipynb"
path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps({"notebook": str(path), "source_sha256": source_sha,
                  "notebook_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}, ensure_ascii=False))
