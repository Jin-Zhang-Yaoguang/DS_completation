"""跨人调度 v2:仅当单位已失步(位置≠带子)且估算完成时刻超过当天最后一步时才转移;转移目标=当前同步但剩余队列为空、且离任务最近的单位;完成率统计。"""
import collections, statistics
from concurrent.futures import ProcessPoolExecutor
import sched_proto as sp
from sched_v0d import record_full, ExecD
from perturb import perturbed, make_plan, play
MOVABLE = {"WATER", "HARVEST", "CARE", "COLLECT_FERTILIZER"}
def dist(a, b): return abs(a[0]-b[0]) + abs(a[1]-b[1])

class ExecR2(ExecD):
    def __init__(self, rec):
        super().__init__(rec, 0, "xy", "spawn"); self.xq = collections.defaultdict(collections.deque)
    def __call__(self, obs):
        t = int(obs.get("step", 0)); day = t // 24; end = day * 24 + 23
        p = int(obs.get("player", 0)); f = obs["farms"][p]
        units = [tuple(f["farmer"])] + [tuple(h) for h in f["hands"]]
        a = ExecD.__call__(self, obs); cmds = [a["farmer"]] + a["hands"]
        if t % 24 == 0: self.xq.clear()
        tp = self.rec["pos"][t] if t < len(self.rec["pos"]) else []
        if t % 24 >= 2:
            helpers = [i for i in range(len(units)) if not self.q[(day, self.map.get(i, i))] and not self.xq[(day, i)]]
            for i, u in enumerate(units):
                j = self.map.get(i, i)
                if j < len(tp) and tp[j] == u: continue          # 同步中,不干预
                q = self.q[(day, j)]
                if not q: continue
                cur = t; pos = u; late = []
                for ev in q:
                    cur = max(cur + dist(pos, (ev[1], ev[2])), ev[0]) + 1; pos = (ev[1], ev[2])
                    if cur > end and ev[3][0] in MOVABLE: late.append(ev)
                for ev in late:
                    if not helpers: break
                    h = min(helpers, key=lambda h2: dist(units[h2], (ev[1], ev[2])))
                    if t + dist(units[h], (ev[1], ev[2])) + 1 > end: continue
                    q.remove(ev); self.xq[(day, h)].append(ev); helpers.remove(h); self.stats["reassign"] += 1
        for i, u in enumerate(units):
            xq = self.xq[(day, i)]
            if not xq: continue
            et, x, y, c = xq[0]
            if u == (x, y): cmds[i] = list(c); xq.popleft(); self.stats["xdone"] += 1
            else: cmds[i] = (["EAST"] if x > u[0] else ["WEST"]) if u[0] != x else (["SOUTH"] if y > u[1] else ["NORTH"])
        return {"farmer": cmds[0], "hands": cmds[1:], "market": a["market"]}

def one(job):
    seed, seat, opp, k, pd = job
    me = f"sub:{sp.S}/y68x3b13_main.py"; op_spec = f"sub:{sp.S}/{opp}_main.py"
    rec = record_full(me, op_spec, seed, seat)
    plan = make_plan(seed, k, pd) if k else {}
    d0, d1 = play(perturbed(ExecD(rec, 0, "xy", "spawn"), plan), op_spec, seed, seat)
    ex = ExecR2(rec); r0, r1 = play(perturbed(ex, plan), op_spec, seed, seat)
    return seed, opp, k, rec["bank"][0], rec["bank"][0]-rec["bank"][1], d0, d0-d1, r0, r0-r1, ex.stats.get("reassign",0), ex.stats.get("xdone",0)

if __name__ == "__main__":
    cfg = [(0, 0), (1, 2), (3, 2)]
    jobs = [(s, s % 2, o, k, pd) for s in range(1100, 1106) for o in ("y68s2", "y68r2") for k, pd in cfg]
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(one, jobs))
    for k, pd in cfg:
        v = [r for r in res if r[2] == k]
        f = lambda i, j: (statistics.median(r[i]/r[3] for r in v), sum(r[j] > 0 for r in v), statistics.median(r[j]-r[4] for r in v))
        a = f(5, 6); b = f(7, 8)
        print(f"扰动卡{k}步: v0d 银行 {a[0]:.1%} 胜 {a[1]}/{len(v)} 分差变化 {a[2]:+.0f} | 跨人调度v2 银行 {b[0]:.1%} 胜 {b[1]}/{len(v)} 分差变化 {b[2]:+.0f} | 转移中位 {statistics.median(r[9] for r in v)} 完成中位 {statistics.median(r[10] for r in v)}")
