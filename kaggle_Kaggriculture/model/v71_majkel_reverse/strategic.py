"""战略层参数:雇工日程方差、买地/买动物/建栏精确时点、作物地块随商店变化、买饲料麦触发、卖肥门槛、卖单相位。"""
import json, collections, statistics as S
acts = {}; meta = {}
for l in open("majkel_0910_12.jsonl"):
    g = json.loads(l)
    if g["date"] != "date=2026-09-10": acts[g["ep"]] = g["acts"]; meta[g["ep"]] = g
hands_day = collections.defaultdict(list); land = []; animal_buy = collections.defaultdict(list); builds = collections.defaultdict(list)
crop_day = collections.defaultdict(lambda: collections.defaultdict(list)); wheat_buy = []; fert_sell = []; fert_hold = []
phase = collections.defaultdict(collections.Counter); unlock_phase = collections.defaultdict(collections.Counter)
for l in open("majkel_state.jsonl"):
    st = json.loads(l); A = acts.get(st["ep"])
    if not A: continue
    rows = {r["t"]: r for r in st["rows"]}; g = meta[st["ep"]]
    for d in range(30):
        r = rows.get(d * 24 + 3)
        if r: hands_day[d].append(r["hands"])
    sh6 = set((rows.get(150) or {}).get("shops") or [])
    tag = ("PET" if "PET_CAFE" in sh6 else "-") + ("/PIZ" if "PIZZA_SHOP" in sh6 else "") + ("/YARN" if "YARN_STORE" in sh6 else "")
    for d in (6, 9, 12, 16, 20, 24):
        r = rows.get(d * 24)
        if r:
            for c in ("WHEAT", "STRAWBERRY", "CARROT", "TOMATO", "MELON", "PASTURE+", "COOP+"):
                crop_day[(d, c)]["all"].append(r["crops"].get(c, 0)); crop_day[(d, c)][tag].append(r["crops"].get(c, 0))
    unlocks = [t for t, s in g["shops"] if t > 0]
    for t, a in enumerate(A[:719]):
        units = [a.get("farmer") or []] + list(a.get("hands") or [])
        for u in units:
            if u and u[0] in ("BUILD_PASTURE", "BUILD_COOP"): builds[u[0]].append(t)
        r = rows.get(t)
        for o in a.get("market") or []:
            if not o: continue
            if o[0] == "BUY_LAND": land.append(t)
            elif o[0] == "BUY_ANIMAL" and len(o) > 2: animal_buy[o[1]].append(t // 24)
            elif o[0] == "BUY_PRODUCT" and len(o) > 2 and o[1] == "WHEAT" and r and r["shed"] is not None:
                animals = sum(v for k, v in r["crops"].items() if k.endswith("+"))
                wheat_buy.append((r["shed"].get("WHEAT", 0), animals, int(o[2]), t // 24, r["p"]["WHEAT"]))
            elif o[0] == "SELL" and len(o) > 2 and 72 <= t < 700:
                phase[o[1]][t % 4] += 1
                if unlocks:
                    last_u = max([u for u in unlocks if u <= t], default=None)
                    if last_u is not None: unlock_phase[o[1]][(t - last_u) % 4] += 1
        if r and r["shed"] is not None and 72 <= t < 700 and r["p"]:
            q = r["shed"].get("FERTILIZER", 0)
            sold = any(o and o[0] == "SELL" and o[1] == "FERTILIZER" for o in a.get("market") or [])
            if q > 0: (fert_sell if sold else fert_hold).append(r["p"]["FERTILIZER"])
print("hands at hour3 by day (mean/sd/min/max):", {d: (round(S.mean(v), 2), round(S.pstdev(v), 2), min(v), max(v)) for d, v in sorted(hands_day.items()) if d <= 12 or d >= 27})
lc = collections.Counter(land); print("BUY_LAND steps top:", lc.most_common(10))
print("BUY_ANIMAL by day:", {k: sorted(collections.Counter(v).items()) for k, v in animal_buy.items()})
print("BUILD steps quantiles:", {k: [sorted(v)[int(len(v) * q)] for q in (0.05, 0.25, 0.5, 0.75, 0.95)] for k, v in builds.items()})
print("\ncrop tiles at day start (all / by shop tag at t150):")
for (d, c), dd in sorted(crop_day.items()):
    parts = " ".join(f"{k}:{S.mean(v):.1f}(n{len(v)})" for k, v in sorted(dd.items()) if k != "all" and len(v) >= 15)
    print(f"  d{d:2d} {c:11s} all={S.mean(dd['all']):5.1f} sd={S.pstdev(dd['all']):4.1f} | {parts}")
wb = wheat_buy
print("\nBUY_PRODUCT WHEAT: n", len(wb), "shed WHEAT at buy (median)", S.median(x[0] for x in wb), "animals (median)", S.median(x[1] for x in wb),
      "qty dist", collections.Counter(x[2] for x in wb).most_common(8), "shed/animal ratio quantiles", [round(sorted(x[0] / max(1, x[1]) for x in wb)[int(len(wb) * q)], 2) for q in (0.1, 0.5, 0.9)])
print("  price at buy quantiles", [sorted(x[4] for x in wb)[int(len(wb) * q)] for q in (0.1, 0.5, 0.9)], "by day", sorted(collections.Counter(x[3] for x in wb).items()))
fs = sorted(fert_sell); fh = sorted(fert_hold)
print("\nFERTILIZER price when held & sold (quantiles):", [fs[int(len(fs) * q)] for q in (0.05, 0.25, 0.5)], "held not sold:", [fh[int(len(fh) * q)] for q in (0.5, 0.75, 0.95)])
print("\nSELL phase t%4:", {k: [v[i] for i in range(4)] for k, v in phase.items()})
print("SELL phase (t - last shop unlock)%4:", {k: [v[i] for i in range(4)] for k, v in unlock_phase.items()})
