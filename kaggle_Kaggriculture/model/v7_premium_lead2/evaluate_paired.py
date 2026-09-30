"""V7 对 V5 的双席位配对评测（同 seed、交换席位、paired margin）。"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

import numpy as np

from kaggle_environments import make


HERE = Path(__file__).resolve().parent
MODEL_DIR = HERE.parent
_CACHE = {}
# v5 与 v7 共享 base_agent/v1_fallback/routes 模块名；同进程加载两个版本时
# 必须在 sys.modules 中清理这些名字，强制每个 main.py 重新导入自己目录的副本。
_SHARED_MODULE_NAMES = ("base_agent", "v1_fallback", "routes")


def _seed_bucket(seed):
    digest = hashlib.sha256(str(int(seed)).encode("ascii")).digest()
    return int.from_bytes(digest[:8], "big") % 100


def _partition_seeds(start, count, low=70, high=90):
    result = []
    candidate = int(start)
    while len(result) < count:
        if low <= _seed_bucket(candidate) < high:
            result.append(candidate)
        candidate += 7919
    return result


def _load(path, name):
    directory = str(path.parent)
    sys.path.insert(0, directory)
    for shared in _SHARED_MODULE_NAMES:
        sys.modules.pop(shared, None)
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise RuntimeError(path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        # 清理共享模块名，避免污染下一个版本的导入；已加载的 main 通过
        # 模块对象引用保持正确绑定。
        for shared in _SHARED_MODULE_NAMES:
            sys.modules.pop(shared, None)
        if sys.path and sys.path[0] == directory:
            sys.path.pop(0)


def _modules():
    process = os.getpid()
    if "v7" not in _CACHE:
        _CACHE["v7"] = _load(HERE / "main.py", f"v7_eval_{process}")
        _CACHE["v5"] = _load(MODEL_DIR / "v5_rule_hybrid" / "main.py", f"v5_eval_{process}")
    return _CACHE


def _match(candidate, opponent, seed, seat):
    agents = [candidate, opponent] if seat == 0 else [opponent, candidate]
    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    steps = env.run(agents)
    assert len(steps) == 720, (seed, seat, len(steps))
    assert [str(state.status) for state in steps[-1]] == ["DONE", "DONE"], (seed, seat)
    rewards = [float(state.reward or 0) for state in steps[-1]]
    return rewards[seat], rewards[1 - seat]


def _paired_row(seed):
    modules = _modules()
    candidate = modules["v7"].agent
    opponent = modules["v5"].agent
    c0, o0 = _match(candidate, opponent, seed, 0)
    c1, o1 = _match(candidate, opponent, seed, 1)
    margin = (c0 - o0) + (c1 - o1)
    win = int(c0 > o0) + int(c1 > o1)
    return {
        "seed": seed,
        "rewards": [c0, o0, c1, o1],
        "paired_margin": margin,
        "wins": win,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=30)
    parser.add_argument("--start", type=int, default=970001)
    args = parser.parse_args()

    seeds = _partition_seeds(args.start, args.count)
    rows = [_paired_row(seed) for seed in seeds]

    margins = np.array([row["paired_margin"] for row in rows], dtype=float)
    wins = int(sum(row["wins"] for row in rows))
    games = len(rows) * 2
    win_rate = wins / games if games else 0.0

    # paired bootstrap 95% CI on seed-level paired margins
    rng = np.random.default_rng(0)
    boots = []
    for _ in range(2000):
        sample = rng.choice(margins, size=len(margins), replace=True)
        boots.append(sample.mean())
    lo, hi = np.percentile(boots, [2.5, 97.5])

    result = {
        "schema": "kaggriculture-v7-paired-1",
        "candidate": "v7_premium_lead2",
        "baseline": "v5_rule_hybrid",
        "seeds": len(rows),
        "games": games,
        "wins": wins,
        "losses": games - wins,
        "win_rate": win_rate,
        "mean_paired_margin": float(margins.mean()),
        "bootstrap95_mean_margin": [float(lo), float(hi)],
        "rows": rows,
    }
    (HERE / "evaluation_paired_v5_report.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
