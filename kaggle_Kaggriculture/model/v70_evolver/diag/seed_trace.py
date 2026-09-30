import sys, json, collections
from pathlib import Path
V = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(V))
import arena, evolve
arena._paths(); import engine, fidelity
cfg = json.load(open(V / 'runs/_funsearch/baseline.json'))['cfg']
seed = evolve.pick_valid_seeds(evolve.load_seed_pool())[0]
ev = [o for o in arena.default_opponents() if 'ev_1072' in o][0]
mod = arena.load_scheduler(); sched = mod.Sched(mod.Cfg(**cfg)); opp = fidelity.make_agent(ev)
k = engine.load_kagsim(); g = k.Game(seed=seed)
o = g.observe(0); print("obs keys:", list(o.keys())); print("market:", json.dumps(o.get("market"))[:600]); print("private keys:", list((o.get("private") or {}).keys()))
buy = [collections.Counter(), collections.Counter()]; plant = [collections.Counter(), collections.Counter()]; hire=[collections.Counter(), collections.Counter()]
for t in range(719):
    o0 = g.observe(0); o0["player"] = 0; o1 = g.observe(1)
    d = t // 24
    if t % 24 == 0 and d <= 12:
        for p, ob in ((0, o0), (1, o1)):
            pr = ob.get("private") or {}
            print(f"d{d} P{p} money={ob['farms'][p]['money']:.0f} seeds={ {k2:v for k2,v in (pr.get('seeds') or {}).items() if v} } hands={len(ob['farms'][p].get('hands') or [])} buySeed={dict(buy[p])} plantOK≈{dict(plant[p])} hireOrders={hire[p]['HIRE']}")
        buy = [collections.Counter(), collections.Counter()]; plant = [collections.Counter(), collections.Counter()]; hire=[collections.Counter(), collections.Counter()]
    a = sched.act(o0); b = opp(o1)
    for p, acts, ob in ((0, a, o0), (1, b, o1)):
        s0 = (ob.get("private") or {}).get("seeds") or {}
        for od in acts.get("market") or []:
            if od and od[0] == "BUY_SEED": buy[p][od[1]] += int(od[2])
            if od and od[0] == "HIRE": hire[p]["HIRE"] += 1
    g.step(a, b)
    for p in (0, 1):
        s1 = (g.observe(p).get("private") or {}).get("seeds") or {}
        s0 = ((o0 if p == 0 else o1).get("private") or {}).get("seeds") or {}
        for c in set(s0) | set(s1):
            dlt = s1.get(c, 0) - s0.get(c, 0)
            if dlt < 0: plant[p][c] += -dlt
