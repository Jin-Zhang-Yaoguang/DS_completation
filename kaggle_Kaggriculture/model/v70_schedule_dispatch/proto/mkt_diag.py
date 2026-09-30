import collections, json
import sched_proto as sp
from perturb import perturbed, make_plan
SEED, SEAT = 1101, 0
me = f"sub:{sp.S}/y68x3b13_main.py"; opp = f"sub:{sp.S}/y68s2_main.py"
def run(agent):
    op = sp.fidelity.make_agent(opp); k = sp.engine.load_kagsim(); g = k.Game(seed=SEED)
    st = collections.Counter(); money = []; t = 0
    while not sp.engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]; a0 = agent(obs[0]); a1 = op(obs[1])
        pr = obs[0]["private"]; shed = pr.get("shed") or {}; m = obs[0]["farms"][0]["money"]
        for x in (a0.get("market") or []):
            if not x: continue
            kind = x[0]; st[kind+":下单"] += 1
            if kind == "SELL" and len(x) > 2:
                have = shed.get(x[1], 0)
                st["SELL:件数请求"] += x[2]; st["SELL:仓库有货件数"] += min(have, x[2])
                if have == 0: st["SELL:仓库无货单"] += 1
        g.step(a0, a1)
        m2 = g.observe(0)["farms"][0]["money"]
        if t % 24 == 23: money.append(m2)
        t += 1
    return float(g.reward(0)), st, money
b0, s0, m0 = run(sp.fidelity.make_agent(me))
b1, s1, m1 = run(perturbed(sp.fidelity.make_agent(me), make_plan(SEED, 1, 2)))
print(f"银行 无扰动 {b0:.0f}  扰动 {b1:.0f}")
keys = sorted(set(s0) | set(s1))
for k in keys: print(f"  {k:22s} {s0[k]:8d} {s1[k]:8d}  差 {s1[k]-s0[k]:+d}")
print("每日终现金(前14天) 无扰动:", [round(x) for x in m0[:14]])
print("每日终现金(前14天) 扰动  :", [round(x) for x in m1[:14]])
