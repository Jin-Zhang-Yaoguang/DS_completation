"""逐 tick 现金追踪:记录双方每 tick 的 money 变化与当 tick 市场单,按单类型归因(同 tick 混合时标 mixed)。"""
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
d0, d1 = int(sys.argv[1]), int(sys.argv[2])
attr = [collections.Counter(), collections.Counter()]
for t in range(719):
    o0 = g.observe(0); o0["player"] = 0; o1 = g.observe(1)
    m = [o0["farms"][0]["money"], o1["farms"][1]["money"]]
    a = sched.act(o0); b = opp(o1)
    g.step(a, b)
    n0 = g.observe(0)["farms"][0]["money"]; n1 = g.observe(1)["farms"][1]["money"]
    for p, acts, mb, ma in ((0, a, m[0], n0), (1, b, m[1], n1)):
        od = acts.get("market") or []
        kinds = sorted({str(o[0]) + ("/" + str(o[1]) if o[0] in ("SELL", "BUY_SEED", "BUY_ANIMAL") else "") for o in od if o})
        delta = ma - mb
        key = kinds[0] if len(kinds) == 1 else ("mixed:" + "+".join(kinds) if kinds else "none")
        if d0 <= t // 24 <= d1:
            attr[p][key] += delta
            if delta != 0 and p == int(sys.argv[3]) if len(sys.argv) > 3 else False:
                print(f"t{t} d{t//24}h{t%24} money {mb:.0f}->{ma:.0f} ({delta:+.0f}) {od}")
for p, name in ((0, "OURS"), (1, "EV")):
    print(f"== {name} d{d0}-{d1} 现金归因:")
    for kk, v in sorted(attr[p].items(), key=lambda x: x[1]):
        if v: print(f"   {kk:40s} {v:+8.0f}")
