"""作物置换(计划级编辑 v2:甜瓜):选 N 个 d10-13 首种小麦的格,到访时刻沿用录制,动作按格状态重写为番茄状态机;
d10 买种,番茄随收随卖。底座=混合(ExecF 田间 + 带子市场)。"""
import sys, json, glob, collections, statistics
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE / "proto"))
import sched_proto as sp
from sched_v0d import record_full
from sched_f import ExecF
from perturb import play

WORK = {"PLANT", "WATER", "HARVEST"}
class CropSwap:
    def __init__(self, rec, me_spec, n=10, active=True):
        self.ex = ExecF(rec, 0, "xy", "spawn"); self.base = sp.fidelity.make_agent(me_spec)
        self.rec = rec; self.n = n; self.active = active
        # 选格:d10-13 首次 PLANT WHEAT 的格,按事件顺序取前 n 个
        seen = set(); self.swap = []
        for t, i, x, y, c in rec["events"]:
            if 240 <= t < 336 and c[0] == "PLANT" and len(c) > 1 and c[1] == "WHEAT" and (x, y) not in seen:
                seen.add((x, y))
                if len(self.swap) < n: self.swap.append((x, y))
        self.swap = set(self.swap)
        self.seed_bal = 0; self.pend = 0; self.prev_tom = 0
        self.stats = collections.Counter(); self.err = 0
    def __call__(self, obs):
        try: return self._call(obs)
        except Exception:
            self.err += 1
            if self.err <= 2: import traceback; traceback.print_exc()
            b = self.base(obs); e = self.ex(obs)
            return {"farmer": e["farmer"], "hands": e["hands"], "market": [list(x) for x in (b.get("market") or [])]}
    def _call(self, obs):
        t = int(obs.get("step", 0)); p = int(obs.get("player", 0)); f = obs["farms"][p]
        b = self.base(obs); e = self.ex(obs)
        mk = [list(x) for x in (b.get("market") or [])]
        cmds = [e["farmer"]] + e["hands"]
        if not self.active or not self.swap:
            return {"farmer": cmds[0], "hands": cmds[1:], "market": mk}
        pr = obs.get("private") or {}; tiles = f["tiles"]
        tom = (pr.get("shed") or {}).get("MELON", 0) + sum((inv or {}).get("MELON", 0) for inv in (pr.get("inventories") or []))
        # d10 买种(找空位)
        if 236 <= t <= 260 and not self.stats.get("seed") and len(mk) < 10 and f["money"] > 600:
            mk.append(["BUY_SEED", "MELON", self.n]); self.seed_bal = self.n; self.stats["seed"] = self.n
        # 随收随卖(找空位,最前)
        if self.pend > 0 and len(mk) < 10 and 1 <= t % 24 <= 22:
            q = min(self.pend, tom, 40)
            if q > 0: mk = [["SELL", "MELON", q]] + mk; self.pend -= q; self.stats["sold"] += q
        # 目标格动作重写
        units = [tuple(f["farmer"])] + [tuple(h) for h in f["hands"]]
        for i, u in enumerate(units):
            if u not in self.swap or i >= len(cmds): continue
            c = cmds[i]
            if not c or c[0] not in WORK: continue
            cell = tiles[u[1]][u[0]]
            if cell is None or (isinstance(cell, dict) and cell.get("kind") == "WEED"):
                if self.seed_bal > 0 and (pr.get("seeds") or {}).get("MELON", 0) > 0:
                    new = ["PLANT", "MELON"]; self.seed_bal -= 1
                else: new = list(c)
            elif isinstance(cell, dict) and cell.get("kind") == "PLANT":
                if cell.get("crop") != "MELON":
                    new = list(c)          # 还是旧作物(未收):按原计划(收小麦)
                elif not cell.get("watered_today"):
                    new = ["WATER"]
                elif (cell.get("yield_units") or 0) >= 6:
                    new = ["HARVEST"]; self.pend += int(cell.get("yield_units") or 0)
                else:
                    new = ["PASS"]
            else:
                new = list(c)
            if new != c: self.stats["rw_" + c[0] + "->" + new[0]] += 1
            cmds[i] = new
        return {"farmer": cmds[0], "hands": cmds[1:], "market": mk}

def one(job):
    fn, kind, n = job
    r = json.load(open(fn)); nm = r["info"]["TeamNames"]; s = r["steps"]
    seat = nm.index("datatuu"); o = 1 - seat
    me = str(HERE / "agents" / "y68wk5_main.py")
    rec = record_full(f"sub:{me}", "TAPE", 0, 0, replay=(r, seat))if False else None
    # 直接用动作带做对手,并用 record_full 生成我方录制
    import sched_proto as sp2
    op_tape = sp2.fidelity.tape_agent([s[t+1][o].get("action") or {} for t in range(len(s)-1)])
    # 我方录制:以带子自打一遍(与线上一致,tape 对手)
    m2 = sp2.fidelity.make_agent(f"sub:{me}")
    k2 = sp2.engine.load_kagsim(); g2 = k2.Game(seed=r["info"]["seed"])
    rec2 = {"market": [], "events": [], "pos": [], "cmds": []}
    FIELD = {"PLANT","BUILD_PASTURE","BUILD_COOP","PLACE","DIG","WATER","HARVEST","FEED","CARE","COLLECT_FERTILIZER","PICKUP","DROP","FERTILIZE"}
    t = 0
    while not sp2.engine._val(g2.done):
        obs = [g2.observe(0), g2.observe(1)]; a = [None, None]
        a[seat] = m2(obs[seat]); a[o] = op_tape(obs[o])
        fm = obs[seat]["farms"][seat]; us = [tuple(fm["farmer"])] + [tuple(h) for h in fm["hands"]]
        cs = [a[seat].get("farmer") or ["PASS"]] + list(a[seat].get("hands") or [])
        rec2["market"].append([list(x) for x in (a[seat].get("market") or [])]); rec2["pos"].append(us)
        rec2["cmds"].append([list(c) if c else ["PASS"] for c in cs[:len(us)]])
        for i, c in enumerate(cs[:len(us)]):
            if c and c[0] in FIELD: rec2["events"].append([t, i, us[i][0], us[i][1], list(c)])
        g2.step(a[0], a[1]); t += 1
    base_m = float(g2.reward(seat) - g2.reward(o))
    if kind == "base": return Path(fn).name, kind, n, base_m, 0
    op2 = sp2.fidelity.tape_agent([s[t+1][o].get("action") or {} for t in range(len(s)-1)])
    ag = CropSwap(rec2, f"sub:{me}", n=n)
    m0, m1 = play(ag, None, r["info"]["seed"], seat, opp_agent=op2) if False else (None, None)
    k3 = sp2.engine.load_kagsim(); g3 = k3.Game(seed=r["info"]["seed"])
    while not sp2.engine._val(g3.done):
        obs = [g3.observe(0), g3.observe(1)]; a = [None, None]
        a[seat] = ag(obs[seat]); a[o] = op2(obs[o]); g3.step(a[0], a[1])
    return Path(fn).name, kind, n, float(g3.reward(seat) - g3.reward(o)), dict(ag.stats)
if __name__ == "__main__":
    W = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v71_style_pool/wk5live")
    fs = [f for f in sorted(glob.glob(str(W/"episode-*.json")))
          if json.load(open(f))["info"]["TeamNames"].count("datatuu") == 1]
    if len(sys.argv) > 1 and sys.argv[1] == "smoke":
        print(one((fs[0], "swap", 10))); sys.exit()
    jobs = [(f, "base", 0) for f in fs] + [(f, "swap", n) for f in fs for n in (6, 10, 14)]
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(one, jobs, chunksize=2))
    base = {r[0]: r[3] for r in res if r[1] == "base"}
    for n in (6, 10, 14):
        v = [(r[0], r[3]) for r in res if r[1] == "swap" and r[2] == n]
        d = [m - base[name] for name, m in v]
        wb = sum(1 for name, m in v if base[name] > 0); ws = sum(1 for name, m in v if m > 0)
        print(f"N={n:2d}: {len(v)} 局 基线 {wb} 胜 → 置换 {ws} 胜  净增中位 {statistics.median(d):+.0f} 均值 {sum(d)/len(d):+.0f}")
