"""评分竞技场:一个配置 vs 对手池的对战 margin。

对手池用 fidelity spec 字符串描述(tape:/sub:/mod:/pass:),在 opponents.json 配置。
worker 为进程安全设计(所有 import 在函数内),供 ProcessPoolExecutor 调用。
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL = HERE.parent


def _paths():
    sys.path.insert(0, str(MODEL / "v16_online_fidelity"))
    sys.path.insert(0, str(MODEL / "v4_demand_race" / "harness"))


def load_scheduler():
    spec = importlib.util.spec_from_file_location("v70_sched", HERE / "scheduler.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def play_one(job) -> float:
    """job = (cfg_dict, opp_spec, seed) -> margin(我方 bank - 对手 bank)。

    opp_spec 支持 "cwd:<dir>|<真实 spec>" 前缀:某些包(如 yhay81 v57)靠
    exec 编译时的默认 co_filename("<string>")+cwd 推断自身文件夹来读取同目录
    JSON 资产,cwd 不对时会静默抛异常、被下方 except 吞掉退化成全 PASS
    (实测已验证会静默产生假胜局,勿去掉这层 chdir)。
    """
    cfg_d, opp_spec, seed = job
    _paths()
    import os
    import engine
    import fidelity

    mod = load_scheduler()
    sched = mod.Sched(mod.Cfg(**cfg_d))
    cwd_dir = None
    if opp_spec.startswith("cwd:"):
        cwd_dir, _, opp_spec = opp_spec[4:].partition("|")
    prev_cwd = os.getcwd()
    try:
        if cwd_dir:
            os.chdir(cwd_dir)
        opp = fidelity.make_agent(opp_spec)
        k = engine.load_kagsim()
        g = k.Game(seed=seed)
        fallback = {"farmer": ["PASS"], "hands": [], "market": []}
        for _ in range(719):
            o0 = g.observe(0)
            o0["player"] = 0
            try:
                a = sched.act(o0)
            except Exception:
                a = fallback
            try:
                b = opp(g.observe(1))
            except Exception:
                b = fallback
            g.step(a, b)
        return float(g.reward(0) - g.reward(1))
    finally:
        if cwd_dir:
            os.chdir(prev_cwd)


def default_opponents() -> list[str]:
    p = HERE / "opponents.json"
    if p.exists():
        return json.loads(p.read_text())
    return [
        f"tape:{MODEL / 'v51_block_router' / 'newpool' / 'op_e3bb880a.json'}",
        f"tape:{MODEL / 'v16_online_fidelity' / 'tapes' / 'pub_t955_0.json'}",
        f"tape:{MODEL / 'v16_online_fidelity' / 'tapes' / 'pub_yhay_0.json'}",
    ]
