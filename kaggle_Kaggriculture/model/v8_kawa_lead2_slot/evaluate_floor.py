"""v8 下界测量：对 v7 线上真实对手池（trace）+ 内置弱对手的并行配对评测。"""
from __future__ import annotations

import glob
import importlib.util
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))  # .../kaggle_Kaggriculture


def _load(path, name):
    d = os.path.dirname(path)
    sys.path.insert(0, d)
    for m in ("base_agent", "v1_fallback", "routes"):
        sys.modules.pop(m, None)
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        for m in ("base_agent", "v1_fallback", "routes"):
            sys.modules.pop(m, None)
        sys.path.pop(0)


class TraceAgent:
    def __init__(self, actions):
        self.actions = actions

    def __call__(self, obs, configuration=None):
        step = int(obs.get("step", 0) or 0)
        return self.actions[min(step, len(self.actions) - 1)] or {
            "farmer": ["PASS"], "hands": [], "market": []}


def _game(task):
    kind, payload, seed, seat = task
    from kaggle_environments import make
    v8 = _load(os.path.join(HERE, "main.py"), f"v8_{os.getpid()}")
    if kind == "trace":
        opp = TraceAgent(payload)
    elif kind == "starter":
        from kaggle_environments.envs.kaggriculture import kaggriculture as kg
        opp = kg.starter_agent
    else:
        from kaggle_environments.envs.kaggriculture import kaggriculture as kg
        opp = kg.random_agent
    agents = [v8.agent, opp] if seat == 0 else [opp, v8.agent]
    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    steps = env.run(agents)
    if [str(s.status) for s in steps[-1]] != ["DONE", "DONE"]:
        return None
    r = [float(s.reward or 0) for s in steps[-1]]
    return (r[0] - r[1]) if seat == 0 else (r[1] - r[0])


def main():
    traces = {}
    for p in sorted(glob.glob(os.path.join(
            ROOT, "model_data/v7_premium_lead2/replays/episode-*-replay.json"))):
        d = json.load(open(p))
        names = (d.get("info") or {}).get("TeamNames") or ["?", "?"]
        our = 0 if names[0] == "datatuu" else (1 if names[1] == "datatuu" else None)
        if our is None or names[1 - our] in traces:
            continue
        acts = []
        for st in d.get("steps") or []:
            a = (st[1 - our] or {}).get("action") or {}
            acts.append({"farmer": list(a.get("farmer") or ["PASS"]),
                         "hands": [list(h or ["PASS"]) for h in (a.get("hands") or [])],
                         "market": [list(mk) for mk in (a.get("market") or [])]})
        traces[names[1 - our]] = acts
    print("真实线上对手数:", len(traces), flush=True)

    tasks = []
    for opp, acts in traces.items():
        for seat in (0, 1):
            tasks.append(("trace", (opp, acts), 970001, seat))
    for kind in ("starter", "random"):
        for seed in (970011, 970012, 970013):
            for seat in (0, 1):
                tasks.append((kind, None, seed, seat))

    rows, losses = [], []
    with ProcessPoolExecutor(max_workers=6) as pool:
        futs = {pool.submit(_game, t): t for t in tasks}
        for fut in as_completed(futs):
            t = futs[fut]
            m = fut.result()
            if m is None:
                continue
            rows.append((t[0], t[1][0] if t[0] == "trace" else t[0], t[3], m))
            if m <= 0:
                losses.append((t[0], t[1][0] if t[0] == "trace" else t[0], t[3], round(m)))

    tot = len(rows)
    wins = sum(1 for r in rows if r[3] > 0)
    print(f"v8 vs 全部下界池: {tot} 局, 胜 {wins} ({wins / tot * 100:.1f}%)")
    tr = [r for r in rows if r[0] == "trace"]
    tw = sum(1 for r in tr if r[3] > 0)
    print(f"  其中真实线上对手: {len(tr)} 局, 胜 {tw} ({tw / len(tr) * 100:.1f}%)")
    weak = [r for r in rows if r[0] != "trace"]
    ww = sum(1 for r in weak if r[3] > 0)
    print(f"  内置弱对手(starter/random): {len(weak)} 局, 胜 {ww} ({ww / len(weak) * 100:.1f}%)")
    print("败局:", losses[:20])


if __name__ == "__main__":
    main()
