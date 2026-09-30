"""逐日经济行为与反应性信号。"""
import json, collections, statistics as S
G = [json.loads(l) for l in open("majkel_0910_12.jsonl")]
G = [g for g in G if g["date"] != "date=2026-09-10"]; n = len(G)
M = lambda xs: S.mean(xs) if xs else 0
daily = collections.defaultdict(lambda: collections.defaultdict(list))
sell_eq_shed = [0, 0]; lot_sizes = collections.Counter(); orders_per_step = []
land_steps = []; first_hire = []; buy_animal = collections.Counter(); buy_seed = collections.Counter()
over_used = []
for g in G:
    per = collections.defaultdict(collections.Counter)
    for t, a in enumerate(g["acts"][:719]):
        d = t // 24; units = [a.get("farmer") or []] + list(a.get("hands") or [])
        per[d]["units"] = max(per[d]["units"], len(units))
        for u in units:
            if u: per[d]["op_" + u[0]] += 1
            if u and u[0] == "PLANT" and len(u) > 1: per[d]["plant_" + u[1]] += 1
        mk = [o for o in a.get("market") or [] if o]; orders_per_step.append(len(mk))
        for o in mk:
            if o[0] == "HIRE": per[d]["hire"] += 1
            elif o[0] == "BUY_LAND": land_steps.append(t)
            elif o[0] == "BUY_ANIMAL" and len(o) > 2: buy_animal[o[1]] += int(o[2]) / n; per[d]["animal_" + o[1]] += int(o[2])
            elif o[0] == "BUY_SEED" and len(o) > 2: buy_seed[o[1]] += int(o[2]) / n; per[d]["seed_" + o[1]] += int(o[2])
            elif o[0] == "SELL" and len(o) > 2:
                per[d]["sell_" + o[1]] += min(int(o[2]), 100000); lot_sizes[int(o[2]) if int(o[2]) < 50 else (50 if int(o[2]) < 1000 else 1000)] += 1
            elif o[0] == "BUY_PRODUCT" and len(o) > 2: per[d]["buyprod_" + o[1]] += int(o[2])
    for d, c in per.items():
        for k, v in c.items(): daily[d][k].append(v)
    ov = [x for x in g["overage"] if x is not None]
    if ov: over_used.append(ov[0] - ov[-1])
    hires = [t for t, a in enumerate(g["acts"]) if any(o and o[0] == "HIRE" for o in a.get("market") or [])]
    first_hire.append(hires[0] if hires else -1)
keys = ["units", "hire", "op_WATER", "op_HARVEST", "op_PLANT", "op_FERTILIZE", "op_FEED", "op_CARE", "op_COLLECT_FERTILIZER", "op_BUILD_PASTURE", "op_BUILD_COOP", "op_PICKUP", "op_DROP", "op_PASS"]
print("games", n)
print("day " + " ".join(f"{k.replace('op_','')[:7]:>7s}" for k in keys))
for d in range(30):
    print(f"d{d:2d} " + " ".join(f"{M([x for x in daily[d][k]] + [0]*(n-len(daily[d][k]))):7.1f}" for k in keys))
crops = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"]
print("\nplant by crop/day:"); [print(f"d{d:2d} " + " ".join(f"{c[:4]}:{sum(daily[d]['plant_'+c])/n:4.1f}" for c in crops)) for d in range(30)]
items = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]
print("\nsell qty by item/day (capped 1e5):"); [print(f"d{d:2d} " + " ".join(f"{i[:4]}:{sum(daily[d]['sell_'+i])/n:6.0f}" for i in items)) for d in range(30)]
print("\nbuy animals/game:", {k: round(v, 1) for k, v in buy_animal.items()}, "buy seeds/game:", {k: round(v, 1) for k, v in buy_seed.items()})
print("BUY_PRODUCT by day:", {d: {k[8:]: round(sum(v)/n, 1) for k, v in daily[d].items() if k.startswith("buyprod_")} for d in range(30) if any(k.startswith("buyprod_") for k in daily[d])})
print("land buy steps: quantiles", [sorted(land_steps)[int(len(land_steps)*q)] for q in (0.1, 0.5, 0.9)] if land_steps else None, "per game", round(len(land_steps)/n, 2))
print("first hire step:", collections.Counter(first_hire).most_common(5))
print("market orders/step:", collections.Counter(orders_per_step).most_common(8))
print("sell lot sizes:", lot_sizes.most_common(15))
print("overage seconds used per game: median", S.median(over_used) if over_used else None, "max", max(over_used) if over_used else None)
print("statuses:", collections.Counter(tuple(g["statuses"]) for g in G).most_common(3))
print("config:", json.dumps(G[0]["config"])[:400])
# 终局与关键时刻资产
for t in ("144", "288", "432", "576", "700"):
    tiles = collections.Counter(); money = []; hands = []
    for g in G:
        s = g["snaps"].get(t)
        if not s: continue
        f = s["farm"]; money.append(f["money"]); hands.append(len(f.get("hands") or []))
        for row in f["tiles"]:
            for x in row:
                if x == "LOCKED": tiles["LOCKED"] += 1 / n
                elif isinstance(x, dict): tiles[x.get("crop") or (x.get("kind") + ("+" if x.get("animal") else ""))] += 1 / n
    print(f"t{t}: money={M(money):.0f} hands={M(hands):.1f} tiles={ {k: round(v, 1) for k, v in tiles.most_common(10)} }")
