"""v0f:修复"重新同步时吞掉补做任务"——内核本步发出工作指令时,同步层不覆盖。"""
import collections, statistics
from concurrent.futures import ProcessPoolExecutor
import sched_proto as sp
from sched_v0c import ExecC
from sched_v0d import record_full, ExecD
from perturb import perturbed, make_plan, play

class ExecF(ExecC):
    def __call__(self, obs):
        t = int(obs.get("step", 0)); day = t // 24
        p = int(obs.get("player", 0)); f = obs["farms"][p]
        units = [tuple(f["farmer"])] + [tuple(h) for h in f["hands"]]
        base = ExecC.__call__(self, obs)
        cmds = [base["farmer"]] + base["hands"]
        tp = self.rec["pos"][t] if t < len(self.rec["pos"]) else []
        tc = self.rec["cmds"][t] if t < len(self.rec["cmds"]) else []
        for i, u in enumerate(units):
            c = cmds[i]
            if c and c[0] not in sp.MOVES and c[0] != "PASS":
                self.stats["kernel_work"] += 1
                continue                                   # 内核已决定干活(含补做),不覆盖
            j = self.map.get(i, i)
            if j < len(tp) and tp[j] == u and j < len(tc):
                tcmd = tc[j]
                if tcmd[0] not in sp.MOVES and tcmd[0] != "PASS":
                    q = self.q[(day, j)]
                    if q and q[0][0] <= t and (q[0][1], q[0][2]) == u and q[0][3][0] == tcmd[0]:
                        q.popleft()
                    else:
                        continue                           # 带子本步的工作不在队首(已完成或次序不同),不盲抄
                cmds[i] = list(tcmd); self.stats["sync"] += 1
            else:
                self.stats["desync"] += 1
        return {"farmer": cmds[0], "hands": cmds[1:], "market": base["market"]}

def one(job):
    seed, seat, opp, k, pd = job
    me = f"sub:{sp.S}/y68x3b13_main.py"; op_spec = f"sub:{sp.S}/{opp}_main.py"
    rec = record_full(me, op_spec, seed, seat)
    plan = make_plan(seed, k, pd) if k else {}
    d0, d1 = play(perturbed(ExecD(rec, 0, "xy", "spawn"), plan), op_spec, seed, seat)
    ex = ExecF(rec, 0, "xy", "spawn"); f0, f1 = play(perturbed(ex, plan), op_spec, seed, seat)
    t0, t1 = play(perturbed(sp.fidelity.make_agent(me), plan), op_spec, seed, seat)
    return seed, opp, k, rec["bank"][0], rec["bank"][0]-rec["bank"][1], d0, d0-d1, f0, f0-f1, t0, t0-t1, ex.stats.get("desync",0)

if __name__ == "__main__":
    cfg = [(0, 0), (1, 2), (3, 2)]
    jobs = [(s, s % 2, o, k, pd) for s in range(1100, 1106) for o in ("y68s2", "y68r2") for k, pd in cfg]
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(one, jobs))
    for k, pd in cfg:
        v = [r for r in res if r[2] == k]
        f = lambda i, j: (statistics.median(r[i]/r[3] for r in v), sum(r[j] > 0 for r in v), statistics.median(r[j]-r[4] for r in v))
        tb = f(9, 10); a = f(5, 6); b = f(7, 8)
        print(f"扰动卡{k}步: 原带子 {tb[0]:.1%} 胜{tb[1]}/{len(v)} {tb[2]:+.0f} | v0d {a[0]:.1%} 胜{a[1]}/{len(v)} {a[2]:+.0f} | v0f修复 {b[0]:.1%} 胜{b[1]}/{len(v)} {b[2]:+.0f} | 失步中位 {statistics.median(r[11] for r in v)}")
