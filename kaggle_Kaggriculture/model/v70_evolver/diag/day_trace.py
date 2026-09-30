"""逐日摘要:money/地块数/牧栏/动物/草莓/麦/手数,支持 OVR=k=v,k=v 覆盖基线 cfg。"""
import sys, os, json, collections
from pathlib import Path
V = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(V))
import arena, evolve
arena._paths(); import engine, fidelity
cfg = json.load(open(V / 'runs/_funsearch/baseline.json'))['cfg']
for kv in filter(None, os.environ.get("OVR", "").split(",")):
    k2, v = kv.split("="); cfg[k2] = int(v)
seeds = evolve.pick_valid_seeds(evolve.load_seed_pool())[:int(os.environ.get("NSEED", "1"))]
ev = [o for o in arena.default_opponents() if 'ev_1072' in o][0]
mod = arena.load_scheduler()
rows = collections.defaultdict(lambda: collections.Counter())
for seed in seeds:
    sched = mod.Sched(mod.Cfg(**cfg)); opp = fidelity.make_agent(ev)
    k = engine.load_kagsim(); g = k.Game(seed=seed)
    for t in range(719):
        o0 = g.observe(0); o0["player"] = 0; o1 = g.observe(1)
        if t % 24 == 0:
            for p, ob in ((0, o0), (1, o1)):
                f = ob["farms"][p]; c = collections.Counter()
                for row in f["tiles"]:
                    for x in row:
                        if x == "LOCKED": c["locked"] += 1
                        elif isinstance(x, dict):
                            if x.get("kind") == "PLANT": c[x.get("crop")] += 1
                            elif x.get("kind") in ("PASTURE", "COOP"): c["pen"] += 1; c["animal"] += bool(x.get("animal"))
                r = rows[(t // 24, p)]
                r["money"] += f["money"]; r["tiles"] += 100 - c["locked"]; r["pen"] += c["pen"]; r["animal"] += c["animal"]
                r["STRAW"] += c["STRAWBERRY"]; r["WHEAT"] += c["WHEAT"]; r["hands"] += len(f.get("hands") or [])
        a = sched.act(o0); b = opp(o1); g.step(a, b)
    rows[(30, 0)]["bank"] += g.reward(0); rows[(30, 1)]["bank"] += g.reward(1)
n = len(seeds)
print("day | ours money tiles pen/animal straw wheat hands | ev money tiles pen/animal straw wheat hands")
for d in range(0, 30, 1 if len(sys.argv) < 2 else int(sys.argv[1])):
    a, b = rows[(d, 0)], rows[(d, 1)]
    print(f"d{d:2d} | {a['money']/n:7.0f} {a['tiles']/n:4.0f} {a['pen']/n:3.0f}/{a['animal']/n:3.0f} {a['STRAW']/n:4.0f} {a['WHEAT']/n:4.0f} {a['hands']/n:3.0f} | {b['money']/n:7.0f} {b['tiles']/n:4.0f} {b['pen']/n:3.0f}/{b['animal']/n:3.0f} {b['STRAW']/n:4.0f} {b['WHEAT']/n:4.0f} {b['hands']/n:3.0f}")
print(f"final bank ours {rows[(30,0)]['bank']/n:.0f} ev {rows[(30,1)]['bank']/n:.0f}")
