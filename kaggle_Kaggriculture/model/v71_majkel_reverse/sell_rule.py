"""卖单决策是否是清晰阈值:按(价格/基价,仓库库存)分箱,统计卖出概率与批量;检验批量是否为库存/价格的确定函数。"""
import json, collections, statistics as S
BASE = {"WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120, "MELON": 250, "EGG": 50, "MILK": 160, "WOOL": 200, "FERTILIZER": 100}
acts = {}
for l in open("majkel_0910_12.jsonl"):
    g = json.loads(l)
    if g["date"] != "date=2026-09-10": acts[g["ep"]] = g["acts"]
stat = collections.defaultdict(lambda: [0, 0]); lots = collections.defaultdict(collections.Counter)
lot_vs_stock = collections.defaultdict(list); price_at_sell = collections.defaultdict(list); price_hold = collections.defaultdict(list)
for l in open("majkel_state.jsonl"):
    st = json.loads(l); A = acts.get(st["ep"])
    if not A: continue
    for r in st["rows"]:
        t = r["t"]
        if t >= 719 or t < 72 or not r["p"] or r["shed"] is None: continue
        sells = collections.Counter()
        for o in A[t].get("market") or []:
            if o and o[0] == "SELL" and len(o) > 2: sells[o[1]] += int(o[2])
        for it, base in BASE.items():
            q = r["shed"].get(it, 0)
            if q <= 0 and not sells[it]: continue
            ratio = r["p"][it] / base; rb = min(int(ratio * 10) / 10, 2.0); qb = min(q, 20) // 5 * 5
            k = (it, rb, qb); stat[k][1] += 1
            if sells[it]:
                stat[k][0] += 1; lots[it][min(sells[it], 30)] += 1
                lot_vs_stock[it].append((q, sells[it], r["p"][it], t % 24)); price_at_sell[it].append(ratio)
            else: price_hold[it].append(ratio)
for it in ("WHEAT", "STRAWBERRY", "MILK", "WOOL", "EGG", "FERTILIZER", "CARROT"):
    print(f"== {it}: sell-steps {len(price_at_sell[it])} hold-steps {len(price_hold[it])} | price ratio at sell med {S.median(price_at_sell[it]) if price_at_sell[it] else 0:.2f} vs hold med {S.median(price_hold[it]) if price_hold[it] else 0:.2f}")
    rows = sorted((k, v) for k, v in stat.items() if k[0] == it and v[1] >= 200)
    grid = collections.defaultdict(dict)
    for (_, rb, qb), (s, n) in rows: grid[rb][qb] = s / n
    qbs = sorted({qb for d in grid.values() for qb in d})
    print("   ratio\\stock " + " ".join(f"{q:>5d}" for q in qbs))
    for rb in sorted(grid): print(f"   {rb:>5.1f}      " + " ".join(f"{grid[rb].get(q, float('nan')):5.2f}" for q in qbs))
    lv = lot_vs_stock[it]
    if lv:
        full = sum(1 for q, s, p, h in lv if s >= q) / len(lv)
        one = sum(1 for q, s, p, h in lv if s == 1) / len(lv)
        print(f"   lot == whole stock: {full:.2f}   lot == 1: {one:.2f}   lot dist: {lots[it].most_common(8)}")
        hours = collections.Counter(h for _, _, _, h in lv); print("   sell hour dist:", [hours[h] for h in range(24)])
