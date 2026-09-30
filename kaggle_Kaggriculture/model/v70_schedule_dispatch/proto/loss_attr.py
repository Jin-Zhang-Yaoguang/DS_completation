import collections, json
import sched_proto as sp
from sched_v0d import record_full, ExecD
from perturb import perturbed, make_plan
SEED, SEAT = 1101, 0
me = f"sub:{sp.S}/y68x3b13_main.py"; opp = f"sub:{sp.S}/y68s2_main.py"
rec = record_full(me, opp, SEED, SEAT)
def run(agent, tag):
    op = sp.fidelity.make_agent(opp); k = sp.engine.load_kagsim(); g = k.Game(seed=SEED)
    st = collections.Counter(); daily = []; t = 0; prev = None
    while not sp.engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]; a0 = agent(obs[0]); a1 = op(obs[1])
        f = obs[0]["farms"][0]
        cells = {(y, x): c for y, row in enumerate(f["tiles"]) for x, c in enumerate(row) if isinstance(c, dict)}
        if t % 24 == 23:
            weeds = sum(1 for c in cells.values() if c.get("kind") == "WEED")
            crops = sum(1 for c in cells.values() if c.get("kind") == "PLANT")
            animals = sum(1 for c in cells.values() if c.get("animal"))
            unw = sum(1 for c in cells.values() if c.get("kind") == "PLANT" and not c.get("watered_today"))
            unfed = sum(1 for c in cells.values() if c.get("animal") and not c.get("fed_today"))
            daily.append((t // 24, round(f["money"]), crops, weeds, animals, unw, unfed))
        if prev is not None:
            for key, c in cells.items():
                p = prev.get(key)
                if isinstance(p, dict) and p.get("kind") == "PLANT" and c.get("kind") == "WEED": st["作物变杂草"] += 1
                if isinstance(p, dict) and p.get("animal") and not c.get("animal"): st["动物消失"] += 1
                if (not isinstance(p, dict) or p.get("kind") != "PLANT") and c.get("kind") == "PLANT": st["新种作物"] += 1
        for c in [a0.get("farmer")] + list(a0.get("hands") or []):
            if c and c[0] not in sp.MOVES and c[0] != "PASS": st["工作:"+c[0]] += 1
        prev = cells; g.step(a0, a1); t += 1
    return float(g.reward(0)), st, daily
b0, s0, d0 = run(ExecD(rec, 0, "xy", "spawn"), "clean")
b1, s1, d1 = run(perturbed(ExecD(rec, 0, "xy", "spawn"), make_plan(SEED, 1, 2)), "pert")
print(f"银行 无扰动 {b0:.0f} 扰动 {b1:.0f}")
for k in sorted(set(s0) | set(s1)): print(f"  {k:26s} {s0[k]:6d} {s1[k]:6d} 差 {s1[k]-s0[k]:+d}")
print("日终 (天, 现金, 作物, 杂草, 动物, 未浇水, 未喂) 无扰动 vs 扰动:")
for a, b in list(zip(d0, d1))[:16]: print("  ", a, b)
