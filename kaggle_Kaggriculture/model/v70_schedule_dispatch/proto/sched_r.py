"""里程碑2 修正方向:截止任务跨人调度。估算每人剩余队列完成时刻,赶不上日终的可转移任务交给空闲单位。"""
import sys, collections, statistics
from concurrent.futures import ProcessPoolExecutor
import sched_proto as sp
from sched_v0d import record_full, ExecD
from perturb import perturbed, make_plan, play
MOVABLE = {"WATER", "HARVEST", "CARE", "COLLECT_FERTILIZER"}

def dist(a, b): return abs(a[0]-b[0]) + abs(a[1]-b[1])

class ExecR(ExecD):
    def __init__(self, rec, margin=1, movable=MOVABLE):
        super().__init__(rec, 0, "xy", "spawn"); self.margin = margin; self.movable = set(movable)
        self.xq = collections.defaultdict(collections.deque)
    def __call__(self, obs):
        t = int(obs.get("step", 0)); day = t // 24; end = day * 24 + 23
        p = int(obs.get("player", 0)); f = obs["farms"][p]
        units = [tuple(f["farmer"])] + [tuple(h) for h in f["hands"]]
        a = ExecD.__call__(self, obs)          # 先得到带子/同步/寻路结果并维护映射
        cmds = [a["farmer"]] + a["hands"]
        if t % 24 == 0: self.xq.clear()
        # 1) 识别赶不上的任务
        if t % 24 >= 2:
            idle = [i for i in range(len(units)) if not self.q[(day, self.map.get(i, i))] and len(self.xq[(day, i)]) < 3]
            for i, u in enumerate(units):
                q = self.q[(day, self.map.get(i, i))]
                if not q: continue
                cur = t; pos = u; late = []
                for ev in list(q):
                    cur = max(cur + dist(pos, (ev[1], ev[2])), ev[0]) + 1; pos = (ev[1], ev[2])
                    if cur > end - self.margin and ev[3][0] in self.movable: late.append(ev)
                for ev in late:
                    if not idle: break
                    j = min(idle, key=lambda j2: dist(units[j2], (ev[1], ev[2])))
                    q.remove(ev); self.xq[(day, j)].append(ev); self.stats["reassign"] += 1
                    if len(self.xq[(day, j)]) >= 3: idle.remove(j)
        # 2) 空闲单位执行转来的任务(覆盖同步照抄)
        for i, u in enumerate(units):
            if self.q[(day, self.map.get(i, i))]: continue
            xq = self.xq[(day, i)]
            if not xq: continue
            et, x, y, c = xq[0]
            if u == (x, y):
                cmds[i] = list(c); xq.popleft(); self.stats["xdone"] += 1
            else:
                cmds[i] = (["EAST"] if x > u[0] else ["WEST"]) if u[0] != x else (["SOUTH"] if y > u[1] else ["NORTH"])
        return {"farmer": cmds[0], "hands": cmds[1:], "market": a["market"]}

def one(job):
    seed, seat, opp, k, pd, margin = job
    me = f"sub:{sp.S}/y68x3b13_main.py"; op_spec = f"sub:{sp.S}/{opp}_main.py"
    rec = record_full(me, op_spec, seed, seat)
    plan = make_plan(seed, k, pd) if k else {}
    d0, d1 = play(perturbed(ExecD(rec, 0, "xy", "spawn"), plan), op_spec, seed, seat)
    ex = ExecR(rec, margin); r0, r1 = play(perturbed(ex, plan), op_spec, seed, seat)
    return seed, opp, k, margin, rec["bank"][0], rec["bank"][0]-rec["bank"][1], d0, d0-d1, r0, r0-r1, ex.stats.get("reassign",0), ex.stats.get("xdone",0)

if __name__ == "__main__":
    cfg = [(0, 0, 1), (1, 2, 1), (3, 2, 1), (1, 2, 3)]
    jobs = [(s, s % 2, o, k, pd, mg) for s in range(1100, 1106) for o in ("y68s2", "y68r2") for k, pd, mg in cfg]
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(one, jobs))
    for k, pd, mg in cfg:
        v = [r for r in res if r[2] == k and r[3] == mg]
        f = lambda i, j: (statistics.median(r[i]/r[4] for r in v), sum(r[j] > 0 for r in v), statistics.median(r[j]-r[5] for r in v))
        a = f(6, 7); b = f(8, 9)
        print(f"扰动卡{k}步 margin={mg}: v0d 银行 {a[0]:.1%} 胜 {a[1]}/{len(v)} 分差变化 {a[2]:+.0f} | 跨人调度 银行 {b[0]:.1%} 胜 {b[1]}/{len(v)} 分差变化 {b[2]:+.0f} | 转移中位 {statistics.median(r[10] for r in v)} 完成中位 {statistics.median(r[11] for r in v)}")
