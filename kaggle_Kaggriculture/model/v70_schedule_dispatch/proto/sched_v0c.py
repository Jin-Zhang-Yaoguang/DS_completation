"""v0c:任务按"出生位置"绑定到带子单位(而非编号) + 先纵后横寻路。"""
import sys, collections, statistics
from concurrent.futures import ProcessPoolExecutor
import sched_proto as sp

def record_pos(me, opp, seed, seat):
    m = sp.fidelity.make_agent(me); o = sp.fidelity.make_agent(opp)
    k = sp.engine.load_kagsim(); g = k.Game(seed=seed); oo = 1 - seat
    rec = {"market": [], "events": [], "pos": []}; t = 0
    while not sp.engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]; a = [None, None]; a[seat] = m(obs[seat]); a[oo] = o(obs[oo])
        f = obs[seat]["farms"][seat]; units = [tuple(f["farmer"])] + [tuple(h) for h in f["hands"]]
        cmds = [a[seat].get("farmer") or ["PASS"]] + list(a[seat].get("hands") or [])
        rec["market"].append([list(x) for x in (a[seat].get("market") or [])]); rec["pos"].append(units)
        for i, c in enumerate(cmds[:len(units)]):
            if c and c[0] not in sp.MOVES and c[0] != "PASS":
                rec["events"].append([t, i, units[i][0], units[i][1], list(c)])
        g.step(a[0], a[1]); t += 1
    rec["bank"] = [float(g.reward(seat)), float(g.reward(oo))]
    return rec

class ExecC(sp.Executor):
    def __init__(self, rec, slack=0, axis="yx", bind="spawn"):
        super().__init__(rec, slack); self.axis = axis; self.bind = bind
        self.map = {}; self.prev_n = 0
    def __call__(self, obs):
        t = int(obs.get("step", 0)); day = t // 24
        p = int(obs.get("player", 0)); f = obs["farms"][p]
        units = [tuple(f["farmer"])] + [tuple(h) for h in f["hands"]]
        tp = self.rec["pos"][t] if t < len(self.rec["pos"]) else []
        if t % 24 == 0 or len(units) < self.prev_n:
            self.map = {}
        self.map[0] = 0
        new = [i for i in range(len(units)) if i not in self.map]
        if new:
            used = set(self.map.values())
            free = [j for j in range(len(tp)) if j not in used]
            for i in new:
                j = None
                if self.bind == "spawn":
                    cand = [j2 for j2 in free if tp[j2] == units[i]]
                    j = cand[0] if cand else None
                if j is None and free:
                    j = min(free, key=lambda j2: abs(tp[j2][0]-units[i][0]) + abs(tp[j2][1]-units[i][1]) if j2 < len(tp) else 99)
                if j is None: j = i
                self.map[i] = j
                if j in free: free.remove(j)
        self.prev_n = len(units)
        cmds = []
        for i, (ux, uy) in enumerate(units):
            q = self.q[(day, self.map.get(i, i))]; cmd = ["PASS"]
            if q:
                et, x, y, c = q[0]
                if (ux, uy) == (x, y):
                    if t >= et - self.slack:
                        cmd = list(c); q.popleft(); self.stats["work"] += 1; self.stats["late"] += (t > et)
                    else: self.stats["wait"] += 1
                else:
                    if self.axis == "yx":
                        cmd = (["SOUTH"] if y > uy else ["NORTH"]) if uy != y else (["EAST"] if x > ux else ["WEST"])
                    else:
                        cmd = (["EAST"] if x > ux else ["WEST"]) if ux != x else (["SOUTH"] if y > uy else ["NORTH"])
                    self.stats["move"] += 1
            else: self.stats["idle"] += 1
            cmds.append(cmd)
        mk = self.rec["market"][t] if t < len(self.rec["market"]) else []
        return {"farmer": cmds[0], "hands": cmds[1:], "market": [list(x) for x in mk]}

def one(job):
    seed, seat, opp, axis, bind = job
    me = f"sub:{sp.S}/y68x3b13_main.py"; op_spec = f"sub:{sp.S}/{opp}_main.py"
    rec = record_pos(me, op_spec, seed, seat)
    ex = ExecC(rec, 0, axis, bind); op = sp.fidelity.make_agent(op_spec)
    k = sp.engine.load_kagsim(); g = k.Game(seed=seed); o = 1 - seat
    while not sp.engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]; a = [None, None]; a[seat] = ex(obs[seat]); a[o] = op(obs[o]); g.step(a[0], a[1])
    b0, b1 = float(g.reward(seat)), float(g.reward(o))
    return seed, opp, axis, bind, rec["bank"][0], rec["bank"][0]-rec["bank"][1], b0, b0-b1, ex.stats.get("late",0), ex.leftover()

if __name__ == "__main__":
    variants = [("yx","index"), ("xy","spawn"), ("yx","spawn")]
    jobs = [(s, s % 2, o, ax, bd) for s in range(1100, 1108) for o in ("y68s2","y68r2") for ax, bd in variants]
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(one, jobs))
    for ax, bd in variants:
        v = [r for r in res if r[2] == ax and r[3] == bd]
        ratio = [r[6]/r[4] for r in v]
        print(f"axis={ax} bind={bd:5s}: 银行比 中位 {statistics.median(ratio):.2%} 最低 {min(ratio):.2%} 最高 {max(ratio):.2%} | 带子胜 {sum(r[5]>0 for r in v)}/16 执行器胜 {sum(r[7]>0 for r in v)}/16 | 分差变化中位 {statistics.median(r[7]-r[5] for r in v):+.0f} | 迟到中位 {statistics.median(r[8] for r in v)} 剩余中位 {statistics.median(r[9] for r in v)}")
