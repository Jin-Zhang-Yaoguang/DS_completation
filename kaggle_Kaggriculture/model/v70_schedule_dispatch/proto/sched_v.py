"""完成校验(标志位):WATER/FEED/CARE/COLLECT_FERTILIZER/HARVEST 下一步看状态,未完成则放回队首重试。"""
import collections, statistics, json
from concurrent.futures import ProcessPoolExecutor
import sched_proto as sp
from sched_v0d import record_full, ExecD
from perturb import perturbed, make_plan, play

def done_ok(cmd, before, after):
    if not isinstance(after, dict): return after != before
    op = cmd[0]
    if op == "WATER": return bool(after.get("watered_today"))
    if op == "FEED": return bool(after.get("fed_today"))
    if op == "CARE": return bool(after.get("cared_today"))
    if op == "COLLECT_FERTILIZER": return not after.get("fertilizer_available")
    if op == "HARVEST": return json.dumps(after, sort_keys=True) != json.dumps(before, sort_keys=True)
    return True

class ExecV(ExecD):
    CHECK = {"WATER", "FEED", "CARE", "COLLECT_FERTILIZER", "HARVEST"}
    def __init__(self, rec, max_retry=3):
        super().__init__(rec, 0, "xy", "spawn"); self.watch = []; self.max_retry = max_retry; self.tries = collections.Counter()
    def __call__(self, obs):
        t = int(obs.get("step", 0)); day = t // 24
        p = int(obs.get("player", 0)); f = obs["farms"][p]
        tiles = f["tiles"]
        # 校验上一步
        for (d, j, ev, before) in self.watch:
            if d != day: continue
            after = tiles[ev[2]][ev[1]]
            if not done_ok(ev[3], before, after):
                key = (d, j, ev[0], ev[1], ev[2], ev[3][0])
                self.tries[key] += 1
                if self.tries[key] <= self.max_retry:
                    self.q[(d, j)].appendleft(ev); self.stats["requeue"] += 1
                else: self.stats["giveup"] += 1
        self.watch = []
        units = [tuple(f["farmer"])] + [tuple(h) for h in f["hands"]]
        # 记录本步将要执行的工作(发指令前的队首)
        heads = {}
        for i, u in enumerate(units):
            j = self.map.get(i, i) if i in self.map else None
            if j is None: continue
            q = self.q[(day, j)]
            if q: heads[i] = (j, q[0])
        a = ExecD.__call__(self, obs)
        cmds = [a["farmer"]] + a["hands"]
        for i, (j, ev) in heads.items():
            if i < len(cmds) and cmds[i] and cmds[i][0] == ev[3][0] and ev[3][0] in self.CHECK and units[i] == (ev[1], ev[2]):
                if ev not in self.q[(day, j)]:
                    self.watch.append((day, j, ev, tiles[ev[2]][ev[1]]))
        a["__cmds_ref"] = None
        return {"farmer": cmds[0], "hands": cmds[1:], "market": a["market"]}

def perturbed_v(ex, plan):
    """扰动发生在执行器之后;执行器通过下一步状态校验感知失败。"""
    return perturbed(ex, plan)

def one(job):
    seed, seat, opp, k, pd = job
    me = f"sub:{sp.S}/y68x3b13_main.py"; op_spec = f"sub:{sp.S}/{opp}_main.py"
    rec = record_full(me, op_spec, seed, seat)
    plan = make_plan(seed, k, pd) if k else {}
    d0, d1 = play(perturbed(ExecD(rec, 0, "xy", "spawn"), plan), op_spec, seed, seat)
    ex = ExecV(rec); v0, v1 = play(perturbed_v(ex, plan), op_spec, seed, seat)
    return seed, opp, k, rec["bank"][0], rec["bank"][0]-rec["bank"][1], d0, d0-d1, v0, v0-v1, ex.stats.get("requeue",0), ex.stats.get("giveup",0)

if __name__ == "__main__":
    cfg = [(0, 0), (1, 2), (3, 2)]
    jobs = [(s, s % 2, o, k, pd) for s in range(1100, 1106) for o in ("y68s2", "y68r2") for k, pd in cfg]
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(one, jobs))
    for k, pd in cfg:
        v = [r for r in res if r[2] == k]
        f = lambda i, j: (statistics.median(r[i]/r[3] for r in v), sum(r[j] > 0 for r in v), statistics.median(r[j]-r[4] for r in v))
        a = f(5, 6); b = f(7, 8)
        print(f"扰动卡{k}步: v0d 银行 {a[0]:.1%} 胜 {a[1]}/{len(v)} 分差变化 {a[2]:+.0f} | 标志位校验 银行 {b[0]:.1%} 胜 {b[1]}/{len(v)} 分差变化 {b[2]:+.0f} | 重排中位 {statistics.median(r[9] for r in v)} 放弃中位 {statistics.median(r[10] for r in v)}")
