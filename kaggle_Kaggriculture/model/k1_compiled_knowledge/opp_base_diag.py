"""双线诊断（2026-09-15）：
 A 对手识别特征：K1 vs 各层对手，记录对手 d2-8 可观测特征（动物数/各作物面积/金币/象限），看能否区分「动物随对手」正收益层(easy/hard)与负收益层(medium/tape/mixed)。
 B 基础产出蒸馏：K1 vs 中等层对手同局双方按产品拆卖出收入、面积·天、动物·天、人手动作。
用法: /opt/anaconda3/bin/python3 opp_base_diag.py [seeds]
"""
import sys, json, statistics, os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
TJ = json.load(open(f'{HERE}/opp_tiers.json'))
FMT = lambda x: x.replace('{M}', TJ['M']).replace('{K1}', TJ['K1'])
OPPS = [(tier, FMT(o)) for tier, t in TJ['tiers'].items() for o in t['opps'][:(3 if tier == 'hard' else 2)]]
NSEED = int(sys.argv[1]) if len(sys.argv) > 1 else 3
SEEDS = [740017 + 211 * i for i in range(NSEED)]
MOVES = {"NORTH", "SOUTH", "EAST", "WEST"}
PRODS = ("WHEAT", "MELON", "STRAWBERRY", "CARROT", "TOMATO", "MILK", "EGG", "WOOL")


def farm_feat(farm):
    c = Counter()
    for row in farm.get("tiles") or []:
        for t in row:
            if isinstance(t, dict):
                if t.get("kind") == "PLANT":
                    c["a_" + t["crop"]] += 1
                elif t.get("animal"):
                    c["n_" + t["animal"]] += 1
    c["quads"] = len(farm.get("unlocked_quadrants") or [])
    c["hands"] = len(farm.get("hands") or [])
    return c


def one(job):
    tier, spec_o, seed = job
    sys.path.insert(0, '/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness')
    sys.path.insert(0, f"{TJ['M']}/v16_online_fidelity")
    import importlib.util, engine, fidelity
    spec = importlib.util.spec_from_file_location(f'obd_{seed}_{abs(hash(spec_o))}', f'{HERE}/main.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    opp = fidelity.make_agent(spec_o)
    g = engine.load_kagsim().Game(seed=seed)
    fb = {"farmer": ["PASS"], "hands": [], "market": []}
    S = [Counter(), Counter()]
    feat = {}
    while not engine._val(g.done):
        o = [g.observe(0), g.observe(1)]
        a0 = mod.agent(o[0])
        try:
            a1 = opp(o[1])
        except Exception:
            a1 = dict(fb)
        day, hour = int(o[0].get("day", 0)), int(o[0].get("hour", 0))
        prices = (o[0].get("market") or {}).get("prices") or {}
        for s, a in ((0, a0), (1, a1)):
            units = [a.get("farmer") or ["PASS"]] + list(a.get("hands") or [])
            S[s]["steps"] += len(units)
            for u in units:
                op = (u or ["PASS"])[0]
                S[s]["act_" + ("MOVE" if op in MOVES else op)] += 1
            for od in a.get("market") or []:
                if od and od[0] == "SELL" and len(od) >= 3:
                    S[s]["rev_" + od[1]] += int(od[2] or 0) * prices.get(od[1], 0)
                elif od and od[0] in ("BUY_ANIMAL", "BUY_LAND", "BUY_SEED", "BUY_PRODUCT", "HIRE"):
                    S[s]["buy_" + od[0]] += 1
        if hour == 12:
            for s in (0, 1):
                f = farm_feat(o[0]["farms"][s])
                for k, v in f.items():
                    if k.startswith("a_") or k.startswith("n_"):
                        S[s]["days_" + k] += v
                if s == 1 and day in (2, 4, 6, 8, 12):
                    for k, v in f.items():
                        feat[f"d{day}_{k}"] = v
                    feat[f"d{day}_money"] = o[0]["farms"][1].get("money", 0)
        g.step(a0, a1)
    fin = [engine._val(g.scores)[0] if hasattr(g, "scores") else 0, 0]
    m0, m1 = o[0]["farms"][0]["money"], o[0]["farms"][1]["money"]
    return tier, spec_o, seed, m0, m1, dict(S[0]), dict(S[1]), feat


def main():
    jobs = [(t, o, s) for t, o in OPPS for s in SEEDS]
    with ProcessPoolExecutor(max_workers=8) as pool:
        res = list(pool.map(one, jobs))
    json.dump(res, open(f'{HERE}/opp_base_diag_result.json', 'w'))
    tiers = list(TJ['tiers'])
    # A：对手早期特征按层
    keys = ["d4_n_COW", "d4_n_SHEEP", "d6_n_COW", "d6_n_SHEEP", "d6_n_GOOSE", "d8_n_COW", "d8_n_SHEEP",
            "d6_a_WHEAT", "d6_a_STRAWBERRY", "d6_a_MELON", "d8_a_STRAWBERRY", "d8_quads", "d8_hands", "d6_money", "d12_n_COW", "d12_a_STRAWBERRY"]
    print("[A] 对手可观测特征（层内中位）")
    print(f"{'特征':18s} | " + " | ".join(f"{t:>7s}" for t in tiers))
    for k in keys:
        print(f"{k:18s} | " + " | ".join(f"{statistics.median([r[7].get(k, 0) for r in res if r[0] == t]):7.0f}" for t in tiers))
    print("\n[A2] 逐对手 d8 动物(牛+羊) / d8 草莓 / 终局分差")
    for t, o in OPPS:
        rr = [r for r in res if r[1] == o]
        nm = o.split('/')[-2] if o.endswith('main.py') else o.split('/')[-1]
        print(f"  {t:6s} {nm[:30]:30s} 动物 {statistics.median(r[7].get('d8_n_COW', 0) + r[7].get('d8_n_SHEEP', 0) for r in rr):4.0f}"
              f" 草莓 {statistics.median(r[7].get('d8_a_STRAWBERRY', 0) for r in rr):4.0f} 麦 {statistics.median(r[7].get('d6_a_WHEAT', 0) for r in rr):4.0f}"
              f" 分差 {statistics.mean(r[3] - r[4] for r in rr):+8.0f}")
    # B：中等+混合层 同局双方拆解
    print("\n[B] 同局双方：K1 / 对手（medium+mixed 层中位；卖出收入、面积·天、动物·天、动作）")
    rows = [f"rev_{p}" for p in PRODS] + [f"days_a_{c}" for c in ("WHEAT", "MELON", "STRAWBERRY", "CARROT", "TOMATO")] + \
           ["days_n_COW", "days_n_SHEEP", "days_n_GOOSE", "act_MOVE", "act_HARVEST", "act_WATER", "act_PLANT", "act_FEED",
            "act_CARE", "act_FERTILIZE", "act_COLLECT_FERTILIZER", "act_PASS", "steps", "buy_HIRE", "buy_BUY_LAND", "buy_BUY_ANIMAL"]
    for tsel in (("medium",), ("mixed",), ("hard",)):
        rr = [r for r in res if r[0] in tsel]
        print(f"  -- {tsel[0]}（{len(rr)} 局）终局金币 K1 {statistics.median(r[3] for r in rr):.0f} / 对手 {statistics.median(r[4] for r in rr):.0f}")
        for k in rows:
            a, b = statistics.median(r[5].get(k, 0) for r in rr), statistics.median(r[6].get(k, 0) for r in rr)
            if a or b:
                print(f"     {k:26s} {a:8.0f} / {b:<8.0f} 差 {b - a:+.0f}")


if __name__ == '__main__':
    main()
