"""里程碑2 v2:只把"本步因缺货没卖成"的非小麦、非清仓卖单差额延续到后续步。"""
import sys, collections, statistics
from concurrent.futures import ProcessPoolExecutor
import sched_proto as sp
from sched_v0d import record_full, ExecD
from perturb import perturbed, make_plan, play

class ExecM2(ExecD):
    def __init__(self, rec, ttl=6, exclude=("WHEAT",), cap=500):
        super().__init__(rec, 0, "xy", "spawn"); self.ttl = ttl; self.exclude = set(exclude); self.cap = cap
        self.pend = []   # [expire, prod, qty]
    def __call__(self, obs):
        a = ExecD.__call__(self, obs)
        t = int(obs.get("step", 0)); pr = obs.get("private") or {}
        avail = collections.Counter(pr.get("shed") or {})
        for inv in (pr.get("inventories") or []): avail.update(inv)
        mk = [list(x) for x in a["market"]]
        tape_want = collections.Counter()
        for x in mk:
            if x and x[0] == "SELL" and len(x) > 2: tape_want[x[1]] += int(x[2])
        # 过期
        self.pend = [p for p in self.pend if p[0] >= t]
        # 先尝试补发延续单(货够才发)
        extra = collections.Counter()
        for p in self.pend:
            spare = avail.get(p[1], 0) - tape_want.get(p[1], 0) - extra.get(p[1], 0)
            n = min(p[2], max(0, spare))
            if n > 0: extra[p[1]] += n; p[2] -= n
        self.pend = [p for p in self.pend if p[2] > 0]
        # 本步带子卖单中缺货的差额 -> 进入延续队列
        if t > 1:
            for prod, q in tape_want.items():
                if prod in self.exclude or q >= self.cap: continue
                short = q - avail.get(prod, 0)
                if short > 0: self.pend.append([t + self.ttl, prod, short]); self.stats["short"] += short
        for prod, n in extra.items():
            if len(mk) < 10: mk.append(["SELL", prod, n]); self.stats["extra"] += n
        a["market"] = mk
        return a

def one(job):
    seed, seat, opp, k, pd, ttl = job
    me = f"sub:{sp.S}/y68x3b13_main.py"; op_spec = f"sub:{sp.S}/{opp}_main.py"
    rec = record_full(me, op_spec, seed, seat)
    plan = make_plan(seed, k, pd) if k else {}
    d0, d1 = play(perturbed(ExecD(rec, 0, "xy", "spawn"), plan), op_spec, seed, seat)
    ex = ExecM2(rec, ttl)
    m0, m1 = play(perturbed(ex, plan), op_spec, seed, seat)
    return seed, opp, k, ttl, rec["bank"][0], rec["bank"][0]-rec["bank"][1], d0, d0-d1, m0, m0-m1, ex.stats.get("short",0), ex.stats.get("extra",0)

if __name__ == "__main__":
    cfg = [(0, 0, 6), (1, 2, 6), (3, 2, 6), (1, 2, 24)]
    jobs = [(s, s % 2, o, k, pd, ttl) for s in range(1100, 1106) for o in ("y68s2", "y68r2") for k, pd, ttl in cfg]
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(one, jobs))
    for k, pd, ttl in cfg:
        v = [r for r in res if r[2] == k and r[3] == ttl]
        f = lambda i, j: (statistics.median(r[i]/r[4] for r in v), sum(r[j] > 0 for r in v), statistics.median(r[j]-r[5] for r in v))
        a = f(6, 7); b = f(8, 9)
        print(f"扰动卡{k}步 ttl={ttl:2d}: v0d 银行 {a[0]:.1%} 胜 {a[1]}/{len(v)} 分差变化 {a[2]:+.0f} | 延续缺货 银行 {b[0]:.1%} 胜 {b[1]}/{len(v)} 分差变化 {b[2]:+.0f} | 缺货件中位 {statistics.median(r[10] for r in v)} 补卖件中位 {statistics.median(r[11] for r in v)}")
