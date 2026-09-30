import collections, json, statistics
import sched_proto as sp
me = sp.fidelity.make_agent(f"sub:{sp.S}/y68x3b13_main.py"); op = sp.fidelity.make_agent(f"sub:{sp.S}/y68s2_main.py")
k = sp.engine.load_kagsim(); g = k.Game(seed=1101)
planted = {}; grow = collections.defaultdict(list); ready_fields = collections.defaultdict(collections.Counter)
harv_yield = collections.defaultdict(list); keys_seen = collections.defaultdict(set); notready = collections.defaultdict(collections.Counter)
t = 0
while not sp.engine._val(g.done):
    o = g.observe(0); a0 = me(o); a1 = op(g.observe(1))
    f = o["farms"][0]; units = [tuple(f["farmer"])] + [tuple(h) for h in f["hands"]]
    cmds = [a0.get("farmer") or ["PASS"]] + list(a0.get("hands") or [])
    tiles0 = f["tiles"]; inv0 = [dict(x) for x in (o["private"].get("inventories") or [])]
    g.step(a0, a1); o2 = g.observe(0); tiles1 = o2["farms"][0]["tiles"]; inv1 = o2["private"].get("inventories") or []
    for i, c in enumerate(cmds):
        if not c or i >= len(units): continue
        x, y = units[i]; b = tiles0[y][x]; af = tiles1[y][x]
        if c[0] == "PLANT" and isinstance(af, dict) and af.get("kind") == "PLANT":
            planted[(x, y)] = (t, af.get("crop"))
        if c[0] == "HARVEST" and isinstance(b, dict) and b.get("kind") == "PLANT":
            crop = b.get("crop")
            got = sum(inv1[i].values()) - sum(inv0[i].values()) if i < len(inv1) and i < len(inv0) else None
            keys_seen[crop] |= set(b.keys())
            succ = json.dumps(b, sort_keys=True) != json.dumps(af, sort_keys=True)
            snap = {k2: b.get(k2) for k2 in b if k2 not in ("watered_today", "consecutive_unwatered")}
            if succ:
                harv_yield[crop].append(got)
                if (x, y) in planted and planted[(x, y)][1] == crop: grow[crop].append(t - planted[(x, y)][0])
                ready_fields[crop][json.dumps({k2: snap[k2] for k2 in ("yield_units",)}, sort_keys=True)] += 1
            else:
                notready[crop][json.dumps({k2: snap[k2] for k2 in ("yield_units",)}, sort_keys=True)] += 1
    t += 1
for crop in grow:
    print(f"{crop:10s} 种到首收步数 中位 {statistics.median(grow[crop])} 分布 {sorted(collections.Counter(grow[crop]).items())[:6]}  收获件数 {collections.Counter(harv_yield[crop]).most_common(4)}")
    print(f"    成功收获时 yield_units {dict(ready_fields[crop])}  失败收获时 {dict(notready[crop])}  字段 {sorted(keys_seen[crop])}")
