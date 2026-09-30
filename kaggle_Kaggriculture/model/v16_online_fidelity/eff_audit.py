"""有效动作率审计：WATER 是否增产、HARVEST 平均 yield、PLANT 存活、PASS/MOVE 结构。"""
import sys, collections
from fidelity import make_agent, engine
spec, seed = sys.argv[1], int(sys.argv[2])
a = make_agent(spec)
k = engine.load_kagsim(); g = k.Game(seed=seed)
step = 0
water = {"window": 0, "ongoing": 0, "waste": 0, "dead_save": 0}
harv = collections.Counter(); harv_y = collections.Counter()
plant_pos = {}   # (r,c) -> plant step
died = 0; planted = 0; verbs = collections.Counter()
CROPS = {"WHEAT": (2,4,0,6,False), "CARROT": (2,3,0,4,False), "TOMATO": (8,8,1,4,True), "STRAWBERRY": (10,10,2,4,True), "MELON": (10,12,0,6,False)}
while not engine._val(g.done):
    o = g.observe(0); day = step // 24
    tiles = o["farms"][0]["tiles"]
    farm = o["farms"][0]
    pos = [tuple(farm["farmer"])] + [tuple(h) for h in farm["hands"]]
    try: act = a(o)
    except Exception: act = {"farmer": ["PASS"], "hands": [], "market": []}
    alist = [act.get("farmer") or ["PASS"]] + list(act.get("hands") or [])
    for i, x in enumerate(alist):
        if not x: continue
        v = str(x[0]); verbs["MOVE" if v in ("NORTH","SOUTH","EAST","WEST") else v] += 1
        if i >= len(pos): continue
        px, py = pos[i]
        t0 = tiles[py][px] if 0 <= py < 10 and 0 <= px < 10 else None
        if v == "WATER" and isinstance(t0, dict) and t0.get("kind") == "PLANT":
            crop = t0["crop"]; first, maxd, inter, maxy, ongoing = CROPS[crop]
            age = day - t0.get("planted_day", day)
            if t0.get("watered_today"): water["waste"] += 1
            elif ongoing: water["ongoing"] += 1
            elif (maxd + 1) // 2 <= age <= maxd: water["window"] += 1
            elif t0.get("consecutive_unwatered", 0) >= 1: water["dead_save"] += 1
            else: water["waste"] += 1
        if v == "HARVEST" and isinstance(t0, dict):
            y = int(t0.get("yield_units", 0))
            key = t0.get("crop") or t0.get("animal") or "?"
            if y > 0: harv[key] += 1; harv_y[key] += y
        if v == "PLANT": planted += 1
    prev_plants = {(r, c) for r, row in enumerate(tiles) for c, x in enumerate(row) if isinstance(x, dict) and x.get("kind") == "PLANT"}
    g.step(act, {"farmer": ["PASS"], "hands": [], "market": []})
    step += 1
    if not engine._val(g.done):
        t2 = g.observe(0)["farms"][0]["tiles"]
        for (r, c) in prev_plants:
            x2 = t2[r][c]
            if isinstance(x2, dict) and x2.get("kind") == "WEED": died += 1
print(f"{spec.split('/')[-1][:22]} bank={engine._val(g.reward(0)):.0f}")
tot = sum(verbs.values())
work = tot - verbs["MOVE"] - verbs["PASS"]
print(f"  total={tot} MOVE={verbs['MOVE']} PASS={verbs['PASS']} work={work} (work%={work/tot:.0%})")
print(f"  WATER: window={water['window']} ongoing={water['ongoing']} dead_save={water['dead_save']} WASTE={water['waste']}")
print(f"  HARVEST: " + " ".join(f"{k}:{harv[k]}x avg_y={harv_y[k]/harv[k]:.2f}" for k in harv))
print(f"  PLANT={planted} died_to_weed={died}")
