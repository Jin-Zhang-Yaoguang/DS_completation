"""v0d:同步时照抄带子指令(含空走位),走岔后自寻路追回下一个任务。"""
import sys, collections, statistics
from concurrent.futures import ProcessPoolExecutor
import sched_proto as sp
from sched_v0c import ExecC

def record_full(me, opp, seed, seat):
    m = sp.fidelity.make_agent(me); o = sp.fidelity.make_agent(opp)
    k = sp.engine.load_kagsim(); g = k.Game(seed=seed); oo = 1 - seat
    rec = {"market": [], "events": [], "pos": [], "cmds": []}; t = 0
    while not sp.engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]; a = [None, None]; a[seat] = m(obs[seat]); a[oo] = o(obs[oo])
        f = obs[seat]["farms"][seat]; units = [tuple(f["farmer"])] + [tuple(h) for h in f["hands"]]
        cmds = [a[seat].get("farmer") or ["PASS"]] + list(a[seat].get("hands") or [])
        rec["market"].append([list(x) for x in (a[seat].get("market") or [])]); rec["pos"].append(units)
        rec["cmds"].append([list(c) if c else ["PASS"] for c in cmds[:len(units)]])
        for i, c in enumerate(cmds[:len(units)]):
            if c and c[0] not in sp.MOVES and c[0] != "PASS":
                rec["events"].append([t, i, units[i][0], units[i][1], list(c)])
        g.step(a[0], a[1]); t += 1
    rec["bank"] = [float(g.reward(seat)), float(g.reward(oo))]
    return rec

class ExecD(ExecC):
    def __call__(self, obs):
        t = int(obs.get("step", 0)); day = t // 24
        p = int(obs.get("player", 0)); f = obs["farms"][p]
        units = [tuple(f["farmer"])] + [tuple(h) for h in f["hands"]]
        base = ExecC.__call__(self, obs)          # 维护映射与寻路结果
        cmds = [base["farmer"]] + base["hands"]
        tp = self.rec["pos"][t] if t < len(self.rec["pos"]) else []
        tc = self.rec["cmds"][t] if t < len(self.rec["cmds"]) else []
        for i, u in enumerate(units):
            j = self.map.get(i, i)
            if j < len(tp) and tp[j] == u and j < len(tc):
                tcmd = tc[j]
                # 同步:照抄带子;若带子本步是工作,需与队首任务一致才算消费
                if tcmd[0] not in sp.MOVES and tcmd[0] != "PASS":
                    q = self.q[(day, j)]
                    if cmds[i] == tcmd:
                        pass  # ExecC 已经 popleft
                    elif q and q[0][0] == t and (q[0][1], q[0][2]) == u:
                        q.popleft()
                cmds[i] = list(tcmd); self.stats["sync"] += 1
            else:
                self.stats["desync"] += 1
        return {"farmer": cmds[0], "hands": cmds[1:], "market": base["market"]}

def one(job):
    seed, seat, opp, axis = job
    me = f"sub:{sp.S}/y68x3b13_main.py"; op_spec = f"sub:{sp.S}/{opp}_main.py"
    rec = record_full(me, op_spec, seed, seat)
    ex = ExecD(rec, 0, axis, "spawn"); op = sp.fidelity.make_agent(op_spec)
    k = sp.engine.load_kagsim(); g = k.Game(seed=seed); o = 1 - seat
    while not sp.engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]; a = [None, None]; a[seat] = ex(obs[seat]); a[o] = op(obs[o]); g.step(a[0], a[1])
    b0, b1 = float(g.reward(seat)), float(g.reward(o))
    return seed, opp, axis, rec["bank"][0], rec["bank"][0]-rec["bank"][1], b0, b0-b1, ex.stats.get("late",0), ex.leftover(), ex.stats.get("sync",0), ex.stats.get("desync",0)

if __name__ == "__main__":
    jobs = [(s, s % 2, o, ax) for s in range(1100, 1108) for o in ("y68s2","y68r2") for ax in ("xy",)]
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(one, jobs))
    for r in res: print(f"seed{r[0]} vs {r[1]:6s} 带子 {r[3]:7.0f} 分差 {r[4]:+7.0f} | v0d {r[5]:7.0f} ({r[5]/r[3]:.2%}) 分差 {r[6]:+7.0f} 同步 {r[9]} 失步 {r[10]} 剩余 {r[8]}")
    ratio = [r[5]/r[3] for r in res]
    print(f"v0d: 银行比 中位 {statistics.median(ratio):.2%} 最低 {min(ratio):.2%} 最高 {max(ratio):.2%} | 带子胜 {sum(r[4]>0 for r in res)}/16 执行器胜 {sum(r[6]>0 for r in res)}/16 | 分差变化中位 {statistics.median(r[6]-r[4] for r in res):+.0f} | 失步占比中位 {statistics.median(r[10]/(r[9]+r[10]) for r in res):.1%}")
