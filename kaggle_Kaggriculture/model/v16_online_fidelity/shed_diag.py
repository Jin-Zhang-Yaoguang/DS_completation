"""对战诊断：逐天 shed 总量、工人随身货值、银行、卖出成交量。"""
import sys, json, collections
from fidelity import make_agent, engine
c0, c1, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
a0, a1 = make_agent(c0), make_agent(c1)
k = engine.load_kagsim(); g = k.Game(seed=seed)
step = 0
while not engine._val(g.done):
    o0 = g.observe(0); o1 = g.observe(1)
    if step % 48 == 24:
        day = step // 24
        p0 = o0["private"]; shed_tot = sum(int(v) for v in p0["shed"].values())
        inv_units = sum(int(v) for i in p0["inventories"] for v in i.values())
        m0 = o0["farms"][0]["money"]; m1 = o0["farms"][1]["money"]
        top=sorted(((k,int(v)) for k,v in p0["shed"].items() if int(v)>0), key=lambda kv:-kv[1])
        print(f"d{day:2d}: shed={shed_tot:3d} carried={inv_units:3d} money={m0:7.0f} vs {m1:7.0f}  {dict(top[:6])}", flush=True)
    try: x0 = a0(o0)
    except Exception: x0 = {"farmer": ["PASS"], "hands": [], "market": []}
    try: x1 = a1(o1)
    except Exception: x1 = {"farmer": ["PASS"], "hands": [], "market": []}
    g.step(x0, x1); step += 1
print("final", engine._val(g.reward(0)), engine._val(g.reward(1)))
