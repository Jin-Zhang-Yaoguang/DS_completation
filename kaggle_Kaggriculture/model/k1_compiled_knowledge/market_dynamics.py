"""市场规则实测（kagsim，K1 vs PASS 对手，排除对手卖出）：逐步 消耗量 = inv(t) + 本方实卖(t) - inv(t+1)。
按产品回归：消耗量 ~ 常数（城镇中心）+ 需求商店数 × 单店速率 + 回归系数 × (inv - I0)；
并测 价格冲击：卖 1 件的价格下降（按 market_price 公式在 inv≈I0 处的斜率）与实测卖后价格变化。"""
import sys, json, importlib.util, os, statistics
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
M = '/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model'
SHOPS = {"BAKERY": ["EGG", "WHEAT"], "PIZZA_SHOP": ["MILK", "TOMATO", "WHEAT"], "BRUNCH_SPOT": ["EGG", "WHEAT", "STRAWBERRY"],
         "YARN_STORE": ["WOOL"], "ICE_CREAM_SHOP": ["STRAWBERRY", "MILK", "WHEAT"], "PET_CAFE": ["CARROT"],
         "SMOOTHIE_SHOP": ["STRAWBERRY", "MILK"], "FARMERS_MARKET": ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY"]}
PRODS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]


def one(seed):
    sys.path.insert(0, '/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness')
    sys.path.insert(0, f'{M}/v16_online_fidelity')
    import engine, fidelity
    spec = importlib.util.spec_from_file_location(f'md_{seed}', f'{HERE}/main.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    opp = fidelity.make_agent('pass:')
    g = engine.load_kagsim().Game(seed=seed)
    rows = []
    prev = None
    while not engine._val(g.done):
        o0, o1 = g.observe(0), g.observe(1)
        a0 = mod.agent(o0)
        inv = dict((o0.get('market') or {}).get('inventory') or {})
        prices = dict((o0.get('market') or {}).get('prices') or {})
        shed = dict((o0.get('private') or {}).get('shed') or {})
        shops = list((o0.get('town') or {}).get('unlocked_shops') or [])
        if prev is not None:
            pinv, pprice, pshed, pact, pshops, pt, phour = prev
            sold = defaultdict(int)
            for od in pact.get('market') or []:
                if od and od[0] == 'SELL' and len(od) >= 3:
                    sold[od[1]] += int(od[2] or 0)
            buy = defaultdict(int)
            for od in pact.get('market') or []:
                if od and od[0] == 'BUY_PRODUCT' and len(od) >= 3:
                    buy[od[1]] += int(od[2] or 0)
            for p in PRODS:
                s_real = min(sold[p], pshed.get(p, 0))
                cons = pinv.get(p, 10000) + s_real - buy[p] - inv.get(p, 10000)
                rows.append({"t": pt, "hour": phour, "p": p, "inv": pinv.get(p, 10000), "sold": s_real, "bought": buy[p],
                             "cons": cons, "nshops": sum(1 for s in pshops if p in SHOPS.get(s, [])),
                             "shops_total": len(pshops), "price0": pprice.get(p, 0), "price1": prices.get(p, 0)})
        prev = (inv, prices, shed, a0, shops, int(o0['day']) * 24 + int(o0['hour']), int(o0['hour']))
        g.step(a0, opp(o1))
    return rows


def ols(X, y):
    import numpy as np
    X = np.array(X, dtype=float); y = np.array(y, dtype=float)
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    pred = X @ coef
    ss = ((y - y.mean()) ** 2).sum()
    return coef, 1 - ((y - pred) ** 2).sum() / ss if ss else 0


def main():
    with ProcessPoolExecutor(max_workers=6) as pool:
        allrows = [r for rows in pool.map(one, [960079 + 277 * i for i in range(6)]) for r in rows]
    json.dump(allrows[:20000], open(f'{HERE}/market_dynamics_rows.json', 'w'))
    sys.path.insert(0, HERE)
    import main as K
    print("按产品：每步消耗量 ~ a + b·需求店数 + c·(inv-I0) + d·[hour==0]；R²；卖 1 件价格冲击（公式在 I0 处）；实测卖出步 Δ价/件")
    for p in PRODS:
        rr = [r for r in allrows if r['p'] == p]
        X = [[1, r['nshops'], r['inv'] - 10000, 1 if r['hour'] == 0 else 0] for r in rr]
        y = [r['cons'] for r in rr]
        coef, r2 = ols(X, y)
        by_hour = defaultdict(list)
        for r in rr:
            by_hour[r['hour']].append(r['cons'])
        nz_hours = sorted(h for h, v in by_hour.items() if statistics.mean(v) > 0.05)
        imp = K.market_price(p, 10000) - K.market_price(p, 10001)
        imp10 = (K.market_price(p, 10000) - K.market_price(p, 10010)) / 10
        sells = [r for r in rr if r['sold'] > 0]
        dpx = statistics.mean((r['price1'] - r['price0']) / r['sold'] for r in sells) if sells else 0
        cons_day_by_shops = defaultdict(list)
        for r in rr:
            cons_day_by_shops[r['nshops']].append(r['cons'])
        print(f"  {p:10s} a={coef[0]:+.3f} b(每店)={coef[1]:+.3f} c(回归)={coef[2]:+.5f} d(0点)={coef[3]:+.2f} R²={r2:.2f} | "
              f"公式冲击 1件 {imp} / 10件均 {imp10:.1f} 金 | 实测 Δ价/件 {dpx:+.1f} | 有消耗的小时 {nz_hours[:8]} | "
              f"日消耗 按需求店数 " + " ".join(f"{k}店:{24 * statistics.mean(v):.1f}" for k, v in sorted(cons_day_by_shops.items())))


if __name__ == '__main__':
    main()
