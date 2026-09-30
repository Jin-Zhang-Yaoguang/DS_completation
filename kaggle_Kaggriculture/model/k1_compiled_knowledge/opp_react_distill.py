"""对手/市场反应蒸馏：Majkel 的种植与卖出是否随对手农场状态、市场价格变化。

指标（每局逐日）：
  1. 对手作物面积 vs Majkel 次日该作物种植占比（跨局相关：对手种得多，我少种？）
  2. 市场价/基准 vs Majkel 当天该品卖出量（高价多卖？）
  3. 对手在产挂果单位（即将上市供给） vs Majkel 当步卖出（抢在对手收获前卖？）
  4. 对手动物数 vs Majkel 动物采购
用法: /opt/anaconda3/bin/python3 opp_react_distill.py [n_games]
"""
import json
import statistics
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor

from scale_distill import IDX, V71

BASE = {"WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120, "MELON": 250, "EGG": 50, "MILK": 160, "WOOL": 200}
CROPS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")
ANIM_PROD = {"COW": "MILK", "SHEEP": "WOOL", "GOOSE": "EGG"}


def corr(xs, ys):
    if len(xs) < 5 or statistics.pstdev(xs) == 0 or statistics.pstdev(ys) == 0:
        return float("nan")
    mx, my = statistics.mean(xs), statistics.mean(ys)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (len(xs) * statistics.pstdev(xs) * statistics.pstdev(ys))


def one(line):
    g = json.loads(line)
    fp = IDX / g["date"] / "data" / f"{g['ep']}.json"
    if not fp.exists():
        return None
    rep = json.loads(fp.read_text())
    names = (rep.get("info") or {}).get("TeamNames") or []
    if "Majkel1337" not in names:
        return None
    me = names.index("Majkel1337")
    op = 1 - me
    steps = rep.get("steps") or []
    days = defaultdict(lambda: {"my_area": Counter(), "op_area": Counter(), "op_hang": Counter(), "op_anim": Counter(),
                                "my_anim": Counter(), "plant": Counter(), "sell": Counter(), "buy_anim": Counter(),
                                "price": {}})
    step_rows = []  # (item, op_hang_now, my_sell_qty, price_ratio)
    opp_visible = None
    for t in range(1, len(steps)):
        obs = steps[t - 1][me].get("observation") or {}
        act = steps[t][me].get("action") or {}
        farms = obs.get("farms") or []
        if len(farms) < 2:
            continue
        if opp_visible is None:
            opp_visible = bool(farms[op].get("tiles"))
        day, hour = int(obs.get("day", 0)), int(obs.get("hour", 0))
        prices = (obs.get("market") or {}).get("prices") or {}
        d = days[day]
        for u in [act.get("farmer")] + list(act.get("hands") or []):
            if u and u[0] == "PLANT" and len(u) > 1:
                d["plant"][u[1]] += 1
        sold = Counter()
        for o in act.get("market") or []:
            if o and o[0] == "SELL" and len(o) >= 3:
                sold[o[1]] += int(o[2] or 0)
                d["sell"][o[1]] += int(o[2] or 0)
            elif o and o[0] == "BUY_ANIMAL":
                d["buy_anim"][o[1]] += int(o[2]) if len(o) >= 3 else 1
        hang = Counter()
        for row in farms[op].get("tiles") or []:
            for tl in row:
                if isinstance(tl, dict):
                    if tl.get("kind") == "PLANT":
                        hang[tl.get("crop")] += tl.get("yield_units") or 0
                    elif tl.get("animal"):
                        hang[ANIM_PROD.get(tl["animal"])] += tl.get("yield_units") or 0
        for it in ("STRAWBERRY", "MILK", "WOOL", "MELON", "TOMATO"):
            if it in prices:
                step_rows.append((it, hang[it], sold[it], prices[it] / BASE[it]))
        if hour == 12:
            d["price"] = {k: prices.get(k, BASE[k]) / BASE[k] for k in BASE}
            for s, key_a, key_an in ((me, "my_area", "my_anim"), (op, "op_area", "op_anim")):
                for row in farms[s].get("tiles") or []:
                    for tl in row:
                        if isinstance(tl, dict):
                            if tl.get("kind") == "PLANT":
                                d[key_a][tl.get("crop")] += 1
                            elif tl.get("animal"):
                                d[key_an][tl["animal"]] += 1
            d["op_hang"] = hang
    return {"opp_visible": opp_visible, "opp": names[op],
            "days": {k: {kk: (dict(vv) if isinstance(vv, Counter) else vv) for kk, vv in v.items()} for k, v in days.items()},
            "steps": step_rows}


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    lines = []
    with open(V71 / "majkel_0910_12.jsonl") as f:
        for line in f:
            lines.append(line)
            if len(lines) >= n:
                break
    with ProcessPoolExecutor(max_workers=8) as pool:
        games = [g for g in pool.map(one, lines) if g]
    print(f"{len(games)} 局；对手农场 tiles 可见: {Counter(g['opp_visible'] for g in games)}")
    print(f"对手分布: {Counter(g['opp'] for g in games).most_common(8)}")

    # 1. 跨局：对手 d5-15 作物面积 vs Majkel d5-15 同作物种植数（控制：Majkel 同作物平均）
    print("\n[1] 跨局相关：对手 d3-12 某作物面积·天 vs Majkel d4-13 该作物种植次数 / 面积·天")
    for c in CROPS:
        xs, ys, ya = [], [], []
        for g in games:
            D = g["days"]
            xs.append(sum(D.get(d, {}).get("op_area", {}).get(c, 0) for d in range(3, 13)))
            ys.append(sum(D.get(d, {}).get("plant", {}).get(c, 0) for d in range(4, 14)))
            ya.append(sum(D.get(d, {}).get("my_area", {}).get(c, 0) for d in range(13, 23)))
        print(f"  {c:<10} 种植 r={corr(xs, ys):+.2f}  后期面积 r={corr(xs, ya):+.2f}  (对手中位 {statistics.median(xs):.0f}, Majkel 种植中位 {statistics.median(ys):.0f})")

    # 1b. 局内逐日：对手面积变化 → Majkel 次日种植
    print("\n[1b] 局内逐日：对手该作物面积(当日) vs Majkel 次日该作物种植（逐局相关后取中位）")
    for c in CROPS:
        rs = []
        for g in games:
            D = g["days"]
            xs = [D.get(d, {}).get("op_area", {}).get(c, 0) for d in range(2, 26)]
            ys = [D.get(d + 1, {}).get("plant", {}).get(c, 0) for d in range(2, 26)]
            r = corr(xs, ys)
            if r == r:
                rs.append(r)
        if rs:
            print(f"  {c:<10} 中位 r={statistics.median(rs):+.2f}  (n={len(rs)})")

    # 2. 价格 → 当天卖出
    print("\n[2] 局内逐日：价格/基准 vs Majkel 当天卖出量（逐局相关中位）")
    for it in ("STRAWBERRY", "MILK", "WOOL", "MELON", "TOMATO", "WHEAT"):
        rs = []
        for g in games:
            D = g["days"]
            ds = [d for d in range(3, 27) if D.get(d, {}).get("price")]
            xs = [D[d]["price"].get(it, 1) for d in ds]
            ys = [D[d]["sell"].get(it, 0) for d in ds]
            r = corr(xs, ys)
            if r == r:
                rs.append(r)
        if rs:
            print(f"  {it:<10} 中位 r={statistics.median(rs):+.2f}")

    # 3. 对手挂果 → Majkel 当步卖出（按对手挂果高/低分组的卖出概率与价格）
    print("\n[3] 逐步：对手即将上市供给(挂果单位)高/低时，Majkel 卖出该品的步占比与均价比")
    for it in ("STRAWBERRY", "MILK", "WOOL", "MELON", "TOMATO"):
        rows = [r for g in games for r in g["steps"] if r[0] == it]
        if not rows:
            continue
        hangs = sorted(r[1] for r in rows)
        hi_th = hangs[int(len(hangs) * 0.75)]
        lo_th = hangs[int(len(hangs) * 0.25)]
        hi = [r for r in rows if r[1] >= hi_th and r[1] > 0]
        lo = [r for r in rows if r[1] <= lo_th]
        f = lambda rr: (sum(1 for r in rr if r[2] > 0) / len(rr) if rr else 0, sum(r[2] for r in rr) / max(1, len(rr)))
        print(f"  {it:<10} 对手挂果高(≥{hi_th}): 卖出步占比 {f(hi)[0]:.2f} 每步量 {f(hi)[1]:.2f} | "
              f"低(≤{lo_th}): {f(lo)[0]:.2f} / {f(lo)[1]:.2f}")

    # 4. 对手动物 → Majkel 动物
    print("\n[4] 跨局：对手 d8 动物数 vs Majkel d8 后买动物数")
    for a in ("COW", "SHEEP", "GOOSE"):
        xs = [g["days"].get(8, {}).get("op_anim", {}).get(a, 0) for g in games]
        ys = [sum(g["days"].get(d, {}).get("buy_anim", {}).get(a, 0) for d in range(8, 30)) for g in games]
        ym = [g["days"].get(20, {}).get("my_anim", {}).get(a, 0) for g in games]
        print(f"  {a:<6} 买入 r={corr(xs, ys):+.2f}  d20 存栏 r={corr(xs, ym):+.2f}")

    # 5. 价格 → Majkel 面积（跨局：d10 价格比 vs d10-20 面积）
    print("\n[5] 跨局：d6-10 平均价格比 vs Majkel d11-20 面积·天")
    for c in CROPS:
        xs = [statistics.mean([g["days"].get(d, {}).get("price", {}).get(c, 1) for d in range(6, 11)]) for g in games]
        ys = [sum(g["days"].get(d, {}).get("my_area", {}).get(c, 0) for d in range(11, 21)) for g in games]
        print(f"  {c:<10} r={corr(xs, ys):+.2f}")


if __name__ == "__main__":
    main()
