"""v0f + 修正后的标志位校验:跳过日终最后一步;收获前产量为0不重试;最多重试 R 次。"""
import collections, statistics, json
from concurrent.futures import ProcessPoolExecutor
import sched_proto as sp
from sched_v0d import record_full
from sched_f import ExecF
from perturb import perturbed, make_plan, play
CHECK = {"WATER", "FEED", "CARE", "COLLECT_FERTILIZER", "HARVEST"}

def failed(cmd, before, after):
    if not isinstance(before, dict) or not isinstance(after, dict): return False
    op = cmd[0]
    if op == "WATER": return before.get("kind") == "PLANT" and not before.get("watered_today") and not after.get("watered_today")
    if op == "FEED": return bool(before.get("animal")) and not before.get("fed_today") and not after.get("fed_today")
    if op == "CARE": return bool(before.get("animal")) and not before.get("cared_today") and not after.get("cared_today")
    if op == "COLLECT_FERTILIZER": return bool(before.get("fertilizer_available")) and bool(after.get("fertilizer_available")) and after.get("yield_units", 0) == before.get("yield_units", 0)
    if op == "HARVEST": return (before.get("yield_units") or 0) > 0 and json.dumps(before, sort_keys=True) == json.dumps(after, sort_keys=True)
    return False

class ExecFV2(ExecF):
    def __init__(self, *a, max_retry=1, **kw):
        super().__init__(*a, **kw); self.watch = []; self.max_retry = max_retry; self.tries = collections.Counter()
    def __call__(self, obs):
        t = int(obs.get("step", 0)); day = t // 24
        p = int(obs.get("player", 0)); f = obs["farms"][p]; tiles = f["tiles"]
        for (d, j, ev, before) in self.watch:
            if d != day: continue
            if failed(ev[3], before, tiles[ev[2]][ev[1]]):
                key = (d, j, ev[0], ev[1], ev[2], ev[3][0]); self.tries[key] += 1
                if self.tries[key] <= self.max_retry: self.q[(d, j)].appendleft(ev); self.stats["requeue"] += 1
                else: self.stats["giveup"] += 1
        self.watch = []
        units = [tuple(f["farmer"])] + [tuple(h) for h in f["hands"]]
        snap = {i: (self.map[i], self.q[(day, self.map[i])][0]) for i in range(len(units)) if i in self.map and self.q[(day, self.map[i])]}
        a = ExecF.__call__(self, obs)
        if t % 24 == 23: return a
        cmds = [a["farmer"]] + a["hands"]
        for i, (j, ev) in snap.items():
            c = cmds[i] if i < len(cmds) else None
            q = self.q[(day, j)]
            if c and c[0] == ev[3][0] and c[0] in CHECK and units[i] == (ev[1], ev[2]) and (not q or q[0] is not ev):
                self.watch.append((day, j, ev, tiles[ev[2]][ev[1]]))
        return a

def one(job):
    seed, seat, opp, k, pd = job
    me = f"sub:{sp.S}/y68x3b13_main.py"; op_spec = f"sub:{sp.S}/{opp}_main.py"
    rec = record_full(me, op_spec, seed, seat)
    plan = make_plan(seed, k, pd) if k else {}
    f0, f1 = play(perturbed(ExecF(rec, 0, "xy", "spawn"), plan), op_spec, seed, seat)
    ex = ExecFV2(rec, 0, "xy", "spawn"); v0, v1 = play(perturbed(ex, plan), op_spec, seed, seat)
    return seed, opp, k, rec["bank"][0], rec["bank"][0]-rec["bank"][1], f0, f0-f1, v0, v0-v1, ex.stats.get("requeue",0), ex.stats.get("giveup",0)

if __name__ == "__main__":
    cfg = [(0, 0), (1, 2), (3, 2)]
    jobs = [(s, s % 2, o, k, pd) for s in range(1100, 1106) for o in ("y68s2", "y68r2") for k, pd in cfg]
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(one, jobs))
    for k, pd in cfg:
        v = [r for r in res if r[2] == k]
        f = lambda i, j: (statistics.median(r[i]/r[3] for r in v), sum(r[j] > 0 for r in v), statistics.median(r[j]-r[4] for r in v))
        a = f(5, 6); b = f(7, 8)
        print(f"扰动卡{k}步: v0f {a[0]:.1%} 胜{a[1]}/{len(v)} 分差变化 {a[2]:+.0f} | v0f+修正校验 {b[0]:.1%} 胜{b[1]}/{len(v)} 分差变化 {b[2]:+.0f} | 重排中位 {statistics.median(r[9] for r in v)} 放弃中位 {statistics.median(r[10] for r in v)}")
