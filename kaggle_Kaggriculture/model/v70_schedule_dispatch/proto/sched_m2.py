"""里程碑2 v1:卖单改为待卖队列(按实际可卖货量发单,余量保留 TTL 步)。"""
import sys, collections, statistics
from concurrent.futures import ProcessPoolExecutor
import sched_proto as sp
from sched_v0d import record_full, ExecD
from perturb import perturbed, make_plan, play

class ExecM(ExecD):
    def __init__(self, rec, ttl=24, **kw):
        super().__init__(rec, 0, "xy", "spawn"); self.ttl = ttl
        self.pend = collections.deque()   # [expire_step, prod, qty]
    def __call__(self, obs):
        a = ExecD.__call__(self, obs)
        t = int(obs.get("step", 0)); pr = obs.get("private") or {}
        avail = collections.Counter(pr.get("shed") or {})
        for inv in (pr.get("inventories") or []): avail.update(inv)
        other = []; tape_sells = []
        for x in a["market"]:
            if x and x[0] == "SELL" and len(x) > 2 and t > 1: tape_sells.append(x)
            else: other.append(x)
        for x in tape_sells: self.pend.append([t + self.ttl, x[1], int(x[2])])
        # 过期清理
        self.pend = collections.deque(p for p in self.pend if p[0] >= t)
        want = collections.Counter()
        for p in self.pend: want[p[1]] += p[2]
        out = []
        for prod, q in want.items():
            n = min(q, avail.get(prod, 0))
            if n > 0: out.append(["SELL", prod, n])
        # 按发出的量从队列头部扣减
        sent = {x[1]: x[2] for x in out}
        for p in self.pend:
            s = sent.get(p[1], 0)
            if s > 0:
                d = min(s, p[2]); p[2] -= d; sent[p[1]] = s - d
        self.pend = collections.deque(p for p in self.pend if p[2] > 0)
        self.stats["sell_sent"] += len(out)
        room = max(0, 10 - len(other))
        a["market"] = other + out[:room]
        return a

def one(job):
    seed, seat, opp, k, pd, ttl = job
    me = f"sub:{sp.S}/y68x3b13_main.py"; op_spec = f"sub:{sp.S}/{opp}_main.py"
    rec = record_full(me, op_spec, seed, seat)
    plan = make_plan(seed, k, pd) if k else {}
    d0, d1 = play(perturbed(ExecD(rec, 0, "xy", "spawn"), plan), op_spec, seed, seat)
    m0, m1 = play(perturbed(ExecM(rec, ttl), plan), op_spec, seed, seat)
    return seed, opp, k, ttl, rec["bank"][0], rec["bank"][0]-rec["bank"][1], d0, d0-d1, m0, m0-m1

if __name__ == "__main__":
    cfg = [(0, 0, 24), (1, 2, 24), (3, 2, 24), (1, 2, 4)]
    jobs = [(s, s % 2, o, k, pd, ttl) for s in range(1100, 1106) for o in ("y68s2", "y68r2") for k, pd, ttl in cfg]
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(one, jobs))
    for k, pd, ttl in cfg:
        v = [r for r in res if r[2] == k and r[3] == ttl]
        f = lambda i, j: (statistics.median(r[i]/r[4] for r in v), sum(r[j] > 0 for r in v), statistics.median(r[j]-r[5] for r in v))
        a = f(6, 7); b = f(8, 9)
        print(f"扰动卡{k}步 ttl={ttl:2d}: v0d 银行 {a[0]:.1%} 胜 {a[1]}/{len(v)} 分差变化 {a[2]:+.0f} | 待卖队列 银行 {b[0]:.1%} 胜 {b[1]}/{len(v)} 分差变化 {b[2]:+.0f}   (无扰动带子胜 {sum(r[5]>0 for r in v)}/{len(v)})")
