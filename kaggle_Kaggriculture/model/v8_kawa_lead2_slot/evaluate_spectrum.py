"""V8 全谱系并行评测：下界（弱池+真实线上弱对手）/ 中段（V1–V7 一代）/ 上界（V20/V27）。

目标函数修正（2026-08-20 用户批评后）：最终 Rating ≈ 对「该分段对手池」保持
过半胜率的最高分段。因此必须测整个谱系，而不是单一强参照。
- 下界池：starter/random/pass/v0 + v7 线上真实对手（TraceAgent，用原始 seed）
- 中段池：v1/v2/v3/v4/v5/v7
- 上界池：v20/v27
每池双席位配对；ProcessPoolExecutor spawn 模式，路径放进 job tuple。
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import glob
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))          # .../kaggle_Kaggriculture
MODEL = os.path.join(ROOT, "model")
OPP = os.path.join(os.environ["TMPDIR"], "kagg_survey", "opponents")
V8 = os.path.join(MODEL, "v8_kawa_lead2_slot", "main.py")

SHARED = ("base_agent", "v1_fallback", "routes")


def _load(path, name):
    d = os.path.dirname(path)
    sys.path.insert(0, d)
    for m in SHARED:
        sys.modules.pop(m, None)
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        for m in SHARED:
            sys.modules.pop(m, None)
        sys.path.pop(0)


class TraceAgent:
    def __init__(self, actions):
        self.actions = actions

    def __call__(self, obs, configuration=None):
        step = int(obs.get("step", 0) or 0)
        return self.actions[min(step, len(self.actions) - 1)] or {
            "farmer": ["PASS"], "hands": [], "market": []}


def _make_opponent(kind, arg):
    if kind == "module":
        return _load(arg["path"], arg["name"]).agent
    if kind == "builtin":
        from kaggle_environments.envs.kaggriculture import kaggriculture as kg
        return {"starter": kg.starter_agent, "random": kg.random_agent,
                "pass": kg.pass_agent}[arg]
    if kind == "trace":
        d = json.load(open(arg["path"]))
        seat = arg["seat"]
        actions = [((st or [None, None])[seat] or {}).get("action") for st in d.get("steps", [])]
        return TraceAgent(actions)
    raise ValueError(kind)


def _job(task):
    idx, opp_spec, seed, seat = task
    kind, arg = opp_spec
    label = arg if kind == "builtin" else arg.get("label", kind)
    v8 = _load(V8, f"v8_w{os.getpid()}")
    opp = _make_opponent(kind, arg)
    agents = [v8.agent, opp] if seat == 0 else [opp, v8.agent]
    from kaggle_environments import make
    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    steps = env.run(agents)
    status = [str(s.status) for s in steps[-1]]
    r = [float(s.reward or 0) for s in steps[-1]]
    margin = (r[0] - r[1]) if seat == 0 else (r[1] - r[0])
    return {"idx": idx, "opp": label, "seed": seed,
            "seat": seat, "margin": margin, "status": status}


def real_online_opponents(limit=20):
    """从 v7 线上 replay 提取真实对手（按对手名去重，取前 limit 个）。"""
    rep_dir = os.path.join(ROOT, "model_data", "v7_premium_lead2", "replays")
    seen, out = set(), []
    for p in sorted(glob.glob(os.path.join(rep_dir, "episode-*-replay.json")))[:400]:
        if len(out) >= limit:
            break
        d = json.load(open(p))
        names = (d.get("info") or {}).get("TeamNames") or []
        if len(names) < 2 or "datatuu" not in names:
            continue
        seat = 0 if names[0] == "datatuu" else 1
        opp_seat = 1 - seat
        if names[opp_seat] in seen:
            continue
        seen.add(names[opp_seat])
        out.append(("trace", {"path": p, "seat": opp_seat, "label": names[opp_seat]}))
    return out


def build_tasks():
    tasks, idx = [], 0
    # 下界：内置弱池
    for b in ("starter", "random", "pass"):
        for seed in (991001, 991002, 991003):
            for seat in (0, 1):
                tasks.append((idx, ("builtin", b), seed, seat)); idx += 1
    # 下界：v0
    for seed in (991001, 991002, 991003):
        for seat in (0, 1):
            tasks.append((idx, ("module", {"path": os.path.join(MODEL, "v0_api_smoke", "main.py"),
                                           "name": "v0_w", "label": "v0"}), seed, seat)); idx += 1
    # 下界：真实线上对手
    for spec in real_online_opponents(20):
        for seat in (0, 1):
            d = json.load(open(spec[1]["path"]))
            seed = int((d.get("info") or {}).get("seed", 42))
            tasks.append((idx, spec, seed, seat)); idx += 1
    # 中段
    mid = [("v1", os.path.join(MODEL, "v1_adaptive_market", "main.py")),
           ("v2", os.path.join(MODEL, "v2_survival_guard", "main.py")),
           ("v3", os.path.join(MODEL, "v3_bc_ppo_hybrid", "main.py")),
           ("v4", os.path.join(MODEL, "v4_rule_hybrid", "main.py")),
           ("v5", os.path.join(MODEL, "v5_rule_hybrid", "main.py")),
           ("v7", os.path.join(MODEL, "v7_premium_lead2", "main.py"))]
    for label, path in mid:
        for seed in (992001, 992002, 992003, 992004):
            for seat in (0, 1):
                tasks.append((idx, ("module", {"path": path, "name": f"{label}_w", "label": label}),
                              seed, seat)); idx += 1
    # 上界
    for label, path in (("v20", os.path.join(OPP, "v20_main.py")),
                        ("v27", os.path.join(OPP, "v27_main.py"))):
        for seed in (993001, 993002, 993003, 993004, 993005, 993006):
            for seat in (0, 1):
                tasks.append((idx, ("module", {"path": path, "name": f"{label}_w", "label": label}),
                              seed, seat)); idx += 1
    return tasks


def main():
    tasks = build_tasks()
    print(f"total games: {len(tasks)}", flush=True)
    rows = []
    with ProcessPoolExecutor(max_workers=16) as pool:
        futs = [pool.submit(_job, t) for t in tasks]
        done = 0
        for f in as_completed(futs):
            rows.append(f.result())
            done += 1
            if done % 32 == 0:
                print(f"progress {done}/{len(tasks)}", flush=True)
    rows.sort(key=lambda r: r["idx"])

    pools = {"lower_builtin": [], "lower_online": [], "mid": [], "upper": []}
    for r in rows:
        lab = r["opp"]
        if lab in ("starter", "random", "pass", "v0"):
            pools["lower_builtin"].append(r)
        elif lab in ("v1", "v2", "v3", "v4", "v5", "v7"):
            pools["mid"].append(r)
        elif lab in ("v20", "v27"):
            pools["upper"].append(r)
        else:
            pools["lower_online"].append(r)

    import statistics
    summary = {}
    for name, grp in pools.items():
        if not grp:
            continue
        wins = sum(1 for r in grp if r["margin"] > 0)
        errs = sum(1 for r in grp if r["status"] != ["DONE", "DONE"])
        summary[name] = {
            "games": len(grp), "wins": wins,
            "win_rate": round(wins / len(grp), 3),
            "mean_margin": round(statistics.mean([r["margin"] for r in grp])),
            "errors": errs,
        }
        by_opp = {}
        for r in grp:
            by_opp.setdefault(r["opp"], []).append(r["margin"])
        summary[name]["by_opponent"] = {
            k: {"n": len(v), "wins": sum(1 for m in v if m > 0),
                "mean_margin": round(statistics.mean(v))}
            for k, v in sorted(by_opp.items())}
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    json.dump(summary, open(os.path.join(HERE, "spectrum_report.json"), "w"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
