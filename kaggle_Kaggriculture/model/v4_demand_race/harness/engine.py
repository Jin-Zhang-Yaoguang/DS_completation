"""kagsim / 官方引擎统一封装。

- kagsim: 1.32.7 bit-exact C++ 扩展（CPython 3.12），live 双席位 ~0.3s/局。
- kagsim_scenario: 同引擎 + force_shops（钉商店序列）。
- 官方 kaggle_environments: 仅作最终 parity 抽检。
属性/方法形态不一致（done/reward 等），统一用 _val() 兼容。
"""
from __future__ import annotations

import importlib.util
import sys
import sysconfig
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL = HERE.parent.parent                      # kaggle_Kaggriculture/model/
CPPSIM = MODEL / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
SCENARIO_BUILD = MODEL / "v116_heuristic_gold_search/replay_arena/build"

_cache: dict[str, object] = {}


def _val(x):
    return x() if callable(x) else x


def _load(name: str, path: Path):
    key = f"{name}:{path}"
    if key not in _cache:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _cache[key] = mod
    return _cache[key]


def load_kagsim():
    so = CPPSIM / "kagsim.cpython-312-darwin.so"
    if not so.exists():
        cands = sorted((CPPSIM / "build").glob("lib.*/kagsim*.so"))
        so = cands[-1]
    return _load("kagsim", so)


def load_scenario():
    suffix = sysconfig.get_config_var("EXT_SUFFIX") or ".so"
    cands = sorted(SCENARIO_BUILD.glob(f"kagsim_scenario*{suffix}")) or \
        sorted(SCENARIO_BUILD.glob("kagsim_scenario*.so"))
    return _load("kagsim_scenario", cands[-1])


def load_agent(path, name=None):
    """加载一个 main.py 风格的 agent 模块，返回其 agent 函数。"""
    path = Path(path)
    mod = _load(name or f"agent_{abs(hash(str(path)))}", path)
    return mod


def fresh_agent(path):
    """每局独立状态：绕过缓存重新 exec。"""
    path = Path(path)
    spec = importlib.util.spec_from_file_location(f"fresh_{abs(hash(str(path)))}_{id(object())}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def play(agent0, agent1, seed: int, shops: list | None = None) -> tuple[float, float]:
    """跑一整局，返回 (bank0, bank1)。

    shops: 钉住的商店序列，元素为 "NAME" 或 (NAME, step)（step 被忽略——
    解锁时刻由引擎规则固定为 day 2,5,8,...，与线上一致）。"""
    if shops:
        k = load_scenario()
        g = k.Game(seed=seed)
        names = [s[0] if isinstance(s, (list, tuple)) else s for s in shops]
        g.force_shops(names)
    else:
        k = load_kagsim()
        g = k.Game(seed=seed)
    fallback0 = {"farmer": ["PASS"], "hands": [], "market": []}
    while not _val(g.done):
        o0, o1 = g.observe(0), g.observe(1)
        try:
            a0 = agent0(o0)
        except Exception:
            a0 = dict(fallback0)
        try:
            a1 = agent1(o1)
        except Exception:
            a1 = dict(fallback0)
        g.step(a0, a1)
    return float(g.reward(0)), float(g.reward(1))
