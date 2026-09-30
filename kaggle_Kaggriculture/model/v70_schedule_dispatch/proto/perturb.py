"""扰动测试:每天 hour H 起,指定单位强制 PASS K 步。比较原带子 vs v0d 执行器在同扰动下的损失。"""
import sys, statistics, random
from concurrent.futures import ProcessPoolExecutor
import sched_proto as sp
from sched_v0d import record_full, ExecD

def perturbed(agent, plan):
    def f(obs):
        a = agent(obs); t = int(obs.get("step", 0))
        units = [a.get("farmer") or ["PASS"]] + list(a.get("hands") or [])
        for (tt, i) in plan.get(t, []):
            if i < len(units): units[i] = ["PASS"]
        return {"farmer": units[0], "hands": units[1:], "market": a.get("market") or []}
    return f

def make_plan(seed, k, per_day):
    rnd = random.Random(seed * 7 + k); plan = {}
    for d in range(1, 29):
        for _ in range(per_day):
            h = rnd.randint(3, 18); i = rnd.randint(0, 5)
            for s in range(k): plan.setdefault(d*24+h+s, []).append((d*24+h+s, i))
    return plan

def play(agent, opp_spec, seed, seat):
    op = sp.fidelity.make_agent(opp_spec); k = sp.engine.load_kagsim(); g = k.Game(seed=seed); o = 1 - seat
    while not sp.engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]; a = [None, None]; a[seat] = agent(obs[seat]); a[o] = op(obs[o]); g.step(a[0], a[1])
    return float(g.reward(seat)), float(g.reward(o))

def one(job):
    seed, seat, opp, k, per_day = job
    me = f"sub:{sp.S}/y68x3b13_main.py"; op_spec = f"sub:{sp.S}/{opp}_main.py"
    rec = record_full(me, op_spec, seed, seat); plan = make_plan(seed, k, per_day)
    t0, t1 = play(perturbed(sp.fidelity.make_agent(me), plan), op_spec, seed, seat)
    ex = ExecD(rec, 0, "xy", "spawn")
    e0, e1 = play(perturbed(ex, plan), op_spec, seed, seat)
    return seed, opp, k, per_day, rec["bank"][0], rec["bank"][0]-rec["bank"][1], t0, t0-t1, e0, e0-e1, ex.stats.get("desync",0)

if __name__ == "__main__":
    jobs = [(s, s % 2, o, k, pd) for s in range(1100, 1106) for o in ("y68s2", "y68r2") for k, pd in ((1, 2), (3, 2))]
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(one, jobs))
    for k, pd in ((1, 2), (3, 2)):
        v = [r for r in res if r[2] == k and r[3] == pd]
        tb = [r[6]/r[4] for r in v]; eb = [r[8]/r[4] for r in v]
        print(f"扰动 每天{pd}次×卡{k}步: 原带子 银行比中位 {statistics.median(tb):.1%} 胜 {sum(r[7]>0 for r in v)}/{len(v)} 分差变化中位 {statistics.median(r[7]-r[5] for r in v):+.0f} | v0d 执行器 银行比中位 {statistics.median(eb):.1%} 胜 {sum(r[9]>0 for r in v)}/{len(v)} 分差变化中位 {statistics.median(r[9]-r[5] for r in v):+.0f} 失步步数中位 {statistics.median(r[10] for r in v)}")
    print("无扰动带子胜", sum(r[5]>0 for r in res if r[2]==1), "/", len([r for r in res if r[2]==1]))
