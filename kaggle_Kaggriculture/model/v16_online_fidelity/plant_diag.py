"""种植时刻诊断：逐天统计 PLANT 品种、草莓种子购买、在场草莓块数。"""
import sys, collections
from fidelity import make_agent, engine
spec = sys.argv[1]; seed = int(sys.argv[2])
a = make_agent(spec)
SH=[("ICE_CREAM_SHOP",72),("BRUNCH_SPOT",144),("YARN_STORE",216),("PIZZA_SHOP",288),("ICE_CREAM_SHOP",360),("PIZZA_SHOP",432),("PIZZA_SHOP",504),("SMOOTHIE_SHOP",576)]
if len(sys.argv)>3 and sys.argv[3]=="teacher":
    k = engine.load_scenario(); g = k.Game(seed=seed); g.force_shops([n for n,st0 in SH if st0<=0])
else:
    k = engine.load_kagsim(); g = k.Game(seed=seed); SH=None
plants = collections.defaultdict(collections.Counter); step = 0
straw_by_day = {}; seed_buys = []
while not engine._val(g.done):
    o = g.observe(0); day = step // 24
    if step % 24 == 12:
        n = sum(1 for row in o["farms"][0]["tiles"] for x in row if isinstance(x, dict) and x.get("crop") == "STRAWBERRY")
        straw_by_day[day] = n
    try: act = a(o)
    except Exception: act = {"farmer": ["PASS"], "hands": [], "market": []}
    for x in [act.get("farmer") or []] + list(act.get("hands") or []):
        if x and str(x[0]) == "PLANT" and len(x) > 1: plants[day][x[1]] += 1
    for m in act.get("market") or []:
        if m and m[0] == "BUY_SEED" and m[1] == "STRAWBERRY": seed_buys.append((day, m[2]))
    g.step(act, {"farmer": ["PASS"], "hands": [], "market": []})
    step += 1
    if SH is not None: g.force_shops([n for n,st0 in SH if st0<=step])
print("straw seed buys:", seed_buys)
print("PLANT by day:")
for d in sorted(plants): print(f"  d{d:2d}: {dict(plants[d])}")
print("straw tiles by day:", {d: straw_by_day[d] for d in sorted(straw_by_day) if d <= 20})
