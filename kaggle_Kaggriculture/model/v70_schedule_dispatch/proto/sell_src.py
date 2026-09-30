import collections
import sched_proto as sp
me = sp.fidelity.make_agent(f"sub:{sp.S}/y68x3b13_main.py"); op = sp.fidelity.make_agent(f"sub:{sp.S}/y68s2_main.py")
k = sp.engine.load_kagsim(); g = k.Game(seed=1101)
st = collections.Counter(); ex = []; t = 0
while not sp.engine._val(g.done) and t < 400:
    o = g.observe(0); a0 = me(o); a1 = op(g.observe(1))
    pr = o["private"]; shed0 = dict(pr.get("shed") or {}); inv0 = [dict(x) for x in (pr.get("inventories") or [])]; m0 = o["farms"][0]["money"]
    sells = [x for x in (a0.get("market") or []) if x and x[0] == "SELL" and len(x) > 2]
    g.step(a0, a1); t += 1
    if not sells: continue
    o2 = g.observe(0); pr2 = o2["private"]; shed1 = pr2.get("shed") or {}; inv1 = pr2.get("inventories") or []
    for x in sells:
        prod = x[1]
        ds = shed0.get(prod, 0) - shed1.get(prod, 0)
        dh = sum(a.get(prod, 0) for a in inv0) - sum(b.get(prod, 0) for b in inv1)
        key = ("仓库减少" if ds > 0 else "仓库不变") + "/" + ("背包减少" if dh > 0 else "背包不变")
        st[key] += 1
        if shed0.get(prod, 0) == 0 and sum(a.get(prod, 0) for a in inv0) == 0: st["下单时仓库和背包都没货"] += 1
        if len(ex) < 10 and shed0.get(prod, 0) == 0:
            ex.append((t-1, t % 24, x, "仓库前", shed0.get(prod, 0), "背包前", sum(a.get(prod, 0) for a in inv0), "现金变化", o2["farms"][0]["money"] - m0, "仓库变化", -ds, "背包变化", -dh))
print(st)
for e in ex: print(" ", e)
