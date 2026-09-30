"""标志位校验 + 过期任务优先(不再被同步照抄覆盖)。"""
import collections, statistics
from concurrent.futures import ProcessPoolExecutor
import sched_proto as sp
from sched_v0d import record_full, ExecD
from sched_v import ExecV, done_ok
from perturb import perturbed, make_plan, play

class ExecV2(ExecV):
    def __call__(self, obs):
        a = ExecV.__call__(self, obs)
        t = int(obs.get("step", 0)); day = t // 24
        p = int(obs.get("player", 0)); f = obs["farms"][p]
        units = [tuple(f["farmer"])] + [tuple(h) for h in f["hands"]]
        cmds = [a["farmer"]] + a["hands"]
        tiles = f["tiles"]
        for i, u in enumerate(units):
            j = self.map.get(i, i); q = self.q[(day, j)]
            if not q: continue
            et, x, y, c = q[0]
            if et >= t: continue                       # 未过期,保持原逻辑
            if u == (x, y):
                if cmds[i] != list(c):
                    cmds[i] = list(c); q.popleft(); self.stats["catchup"] += 1
                    if c[0] in self.CHECK: self.watch.append((day, j, (et, x, y, c), tiles[y][x]))
            else:
                mv = (["EAST"] if x > u[0] else ["WEST"]) if u[0] != x else (["SOUTH"] if y > u[1] else ["NORTH"])
                if cmds[i] != mv: cmds[i] = mv; self.stats["chase"] += 1
        return {"farmer": cmds[0], "hands": cmds[1:], "market": a["market"]}

def one(job):
    seed, seat, opp, k, pd = job
    me = f"sub:{sp.S}/y68x3b13_main.py"; op_spec = f"sub:{sp.S}/{opp}_main.py"
    rec = record_full(me, op_spec, seed, seat)
    plan = make_plan(seed, k, pd) if k else {}
    d0, d1 = play(perturbed(ExecD(rec, 0, "xy", "spawn"), plan), op_spec, seed, seat)
    ex = ExecV2(rec); v0, v1 = play(perturbed(ex, plan), op_spec, seed, seat)
    return seed, opp, k, rec["bank"][0], rec["bank"][0]-rec["bank"][1], d0, d0-d1, v0, v0-v1, ex.stats.get("requeue",0), ex.stats.get("catchup",0), ex.stats.get("chase",0)

if __name__ == "__main__":
    cfg = [(0, 0), (1, 2), (3, 2)]
    jobs = [(s, s % 2, o, k, pd) for s in range(1100, 1106) for o in ("y68s2", "y68r2") for k, pd in cfg]
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(one, jobs))
    for k, pd in cfg:
        v = [r for r in res if r[2] == k]
        f = lambda i, j: (statistics.median(r[i]/r[3] for r in v), sum(r[j] > 0 for r in v), statistics.median(r[j]-r[4] for r in v))
        a = f(5, 6); b = f(7, 8)
        print(f"扰动卡{k}步: v0d 银行 {a[0]:.1%} 胜 {a[1]}/{len(v)} 分差变化 {a[2]:+.0f} | 校验+过期优先 银行 {b[0]:.1%} 胜 {b[1]}/{len(v)} 分差变化 {b[2]:+.0f} | 重排 {statistics.median(r[9] for r in v)} 补做 {statistics.median(r[10] for r in v)} 追赶 {statistics.median(r[11] for r in v)}")
