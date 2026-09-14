"""B 线对表工具：Majkel 289 局全指标曲线 vs K1 对战局同指标 → 缺口表。

指标（逐日）：money、日收入（money 正增量和）、面积、动物数、
卖出成交（品类×数量×实际单价——由 money 增量与订单联立）。
数据源：v71 majkel_state.jsonl（逐步 money/shed/crops）+ majkel_0910_12.jsonl（acts）。

用法: /opt/anaconda3/bin/python3 majkel_fp.py
"""
import importlib.util
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
V71 = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v71_majkel_reverse")
MOS = "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v58_mosaic/dist_backup"


def majkel_curves(max_games=25):
    """从逐步状态抽逐日曲线（中位数聚合）。"""
    day_money = defaultdict(list)
    day_area = defaultdict(list)
    day_animals = defaultdict(list)
    day_income = defaultdict(list)   # 日内 money 正增量和 ≈ 毛收入
    day_spend = defaultdict(list)
    finals = []
    n = 0
    for line in open(V71 / "majkel_state.jsonl"):
        st = json.loads(line)
        rows = {r["t"]: r for r in st["rows"]}
        ts = sorted(rows)
        if len(ts) < 100:
            continue
        n += 1
        if n > max_games:
            break
        prev_m = None
        inc = defaultdict(float)
        spend = defaultdict(float)
        for t in ts:
            r = rows[t]
            d = t // 24
            m = r.get("money")
            if m is None:
                continue
            if prev_m is not None:
                delta = m - prev_m[1]
                if delta > 0:
                    inc[d] += delta
                else:
                    spend[d] -= delta
            prev_m = (t, m)
            if t % 24 == 3:
                day_money[d].append(m)
                crops = r.get("crops") or {}
                area = sum(v for k, v in crops.items()
                           if k in ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"))
                day_area[d].append(area)
                day_animals[d].append(crops.get("PASTURE+", 0) + crops.get("COOP+", 0))
        for d, v in inc.items():
            day_income[d].append(v)
        for d, v in spend.items():
            day_spend[d].append(v)
        last = rows[ts[-1]]
        finals.append(last.get("money", 0))
    med = lambda dd: {d: round(statistics.median(v)) for d, v in sorted(dd.items()) if v}
    return {"money": med(day_money), "area": med(day_area), "animals": med(day_animals),
            "income": med(day_income), "spend": med(day_spend),
            "final_money_median": statistics.median(finals) if finals else None, "n": n}


def k1_curves(seed=1046):
    sys.path.insert(0, "/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness")
    sys.path.insert(0, "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v16_online_fidelity")
    import engine
    import fidelity
    spec = importlib.util.spec_from_file_location("k1_fp", HERE / "main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    tu = {**json.loads((HERE / "knowledge.json").read_text())["tuning"],
          "fert_specialist": False, "t0_pool_select": False}
    mod.KN_OVERRIDE = {"tuning": tu}
    opp = fidelity.make_agent(f"sub:{MOS}/y68g_main.py")
    k = engine.load_kagsim()
    g = k.Game(seed=seed)
    money, area, animals = {}, {}, {}
    income, spend = Counter(), Counter()
    prev_m = None
    while not (g.done() if callable(g.done) else g.done):
        o0, o1 = g.observe(0), g.observe(1)
        day, hour = int(o0["day"]), int(o0["hour"])
        farm = o0["farms"][0]
        m = farm["money"]
        if prev_m is not None:
            delta = m - prev_m
            if delta > 0:
                income[day] += delta
            else:
                spend[day] -= delta
        prev_m = m
        if hour == 3:
            money[day] = round(m)
            a = n_an = 0
            for row in farm["tiles"]:
                for t in row:
                    if isinstance(t, dict):
                        if t.get("kind") == "PLANT":
                            a += 1
                        if "animal" in t:
                            n_an += 1
            area[day], animals[day] = a, n_an
        g.step(mod.agent(o0), opp(o1))
    return {"money": money, "area": area, "animals": animals,
            "income": dict(income), "spend": dict(spend), "final": float(g.reward(0))}


def main():
    mj = majkel_curves()
    k1 = k1_curves()
    print(f"Majkel({mj['n']}局中位) vs K1(seed1046 vs y68g, final {k1['final']:.0f})")
    print(f"{'day':>3} | {'MJ收入':>7} {'K1收入':>7} | {'MJ面积':>5} {'K1':>4} | {'MJ动物':>5} {'K1':>4} | {'MJ钱':>7} {'K1钱':>7}")
    for d in range(30):
        print(f"{d:3d} | {mj['income'].get(d, 0):7d} {k1['income'].get(d, 0):7.0f} | "
              f"{mj['area'].get(d, 0):5d} {k1['area'].get(d, 0):4d} | "
              f"{mj['animals'].get(d, 0):5d} {k1['animals'].get(d, 0):4d} | "
              f"{mj['money'].get(d, 0):7d} {k1['money'].get(d, 0):7.0f}")
    print(f"\n累计收入: MJ {sum(mj['income'].values())} vs K1 {sum(k1['income'].values()):.0f}")
    print(f"累计支出: MJ {sum(mj['spend'].values())} vs K1 {sum(k1['spend'].values()):.0f}")
    (HERE / "majkel_fp_result.json").write_text(json.dumps({"majkel": mj, "k1": k1}, indent=1))


if __name__ == "__main__":
    main()
