"""扩面积为什么亏：同局配对拆解收入/成本/现金/作物损失/市场价/对手。
基准 = ga4 最优；对手 y68g + v2_survival_guard；4 seed × 双席位 = 16 局/配置。
收入 = 实际卖出量（按仓库减少量核实，防超量卖单）× 当步挂牌价；成本按市场单 × 当步价格（种子价取 CROPS 表）；
作物损失 = 上一步是作物、本步该格不是作物且本步该格无人 HARVEST。"""
import sys, importlib.util, json, statistics, os
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
M = '/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model'
OPPS = [f'sub:{M}/v58_mosaic/dist_backup/y68g_main.py', f'sub:{M}/v2_survival_guard/main.py']
SEEDS = [970081 + 281 * i for i in range(4)]
CONFIGS = {
    '基准': {},
    '速率 share1.0': {'sell_demand_on': 1, 'sell_demand_rate': 1},
    '速率 share1.5': {'sell_demand_on': 1, 'sell_demand_rate': 1, 'sell_share': 1.5},
    '速率 share2.0 lot8': {'sell_demand_on': 1, 'sell_demand_rate': 1, 'sell_share': 2.0, 'sell_demand_lot': 8},
    '速率 share1.5 不留低价': {'sell_demand_on': 1, 'sell_demand_rate': 1, 'sell_share': 1.5, 'sell_hold_low': 0},
    '速率 share1.5 瓜肥20': {'sell_demand_on': 1, 'sell_demand_rate': 1, 'sell_share': 1.5, 'sell_melon_cap': 20, 'sell_fert_cap': 20},
}
PRODS = ("WHEAT", "MELON", "STRAWBERRY", "CARROT", "TOMATO", "MILK", "EGG", "WOOL", "FERTILIZER")


def one(job):
    name, seed, opp_spec, seat = job
    sys.path.insert(0, '/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness')
    sys.path.insert(0, f'{M}/v16_online_fidelity')
    sys.path.insert(0, HERE)
    import engine, fidelity
    from schedule_gen import gen_tables, DEFAULTS
    best = max(json.load(open(f'{HERE}/best_iter_ga4.json'))['candidates'], key=lambda c: c['hold_margin'])
    params = {**DEFAULTS, **best['params']}
    for k, v in CONFIGS[name].items():
        params[k] = v
    spec = importlib.util.spec_from_file_location(f'acd_{seed}_{seat}_{abs(hash(name + opp_spec))}', f'{HERE}/main.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    base_tu = json.load(open(f'{HERE}/knowledge.json'))['tuning']
    ov = gen_tables(params); te = ov.pop('tuning_extra')
    ov['tuning'] = {**base_tu, 'fert_specialist': False, 't0_pool_select': False, **te}
    mod.KN_OVERRIDE = ov
    opp = fidelity.make_agent(opp_spec)
    agents = [mod.agent, opp] if seat == 0 else [opp, mod.agent]
    g = engine.load_kagsim().Game(seed=seed)
    c = Counter()
    price_sum = Counter(); price_n = Counter()
    cash_min = defaultdict(lambda: 10 ** 9)
    prev_obs = None; prev_act = None
    while not engine._val(g.done):
        o = [g.observe(0), g.observe(1)]
        a = [agents[0](o[0]), agents[1](o[1])]
        me = o[seat]
        day, hour = int(me['day']), int(me['hour'])
        farm = me['farms'][seat]
        prices = (me.get('market') or {}).get('prices') or {}
        pv = me.get('private') or {}
        shed = pv.get('shed') or {}
        cash_min[day] = min(cash_min[day], farm['money'])
        if hour == 12:
            for p in PRODS:
                if p in prices:
                    price_sum[p] += prices[p]; price_n[p] += 1
            for row in farm['tiles']:
                for t in row:
                    if isinstance(t, dict) and t.get('kind') == 'PLANT':
                        c['crop_tile_days'] += 1
        # 结算上一步：卖出（按仓库减少核实）、作物损失
        if prev_obs is not None:
            pshed = (prev_obs.get('private') or {}).get('shed') or {}
            pprices = (prev_obs.get('market') or {}).get('prices') or {}
            sold_req = Counter()
            for od in prev_act.get('market') or []:
                if od and od[0] == 'SELL' and len(od) >= 3:
                    sold_req[od[1]] += int(od[2] or 0)
            for p, q in sold_req.items():
                q_real = min(q, pshed.get(p, 0))
                c[f'sell_{p}'] += q_real
                c[f'rev_{p}'] += q_real * pprices.get(p, 0)
            pf = prev_obs['farms'][seat]
            if int(prev_obs['day']) == day:
                ppos = [tuple(pf['farmer'])] + [tuple(h) for h in pf.get('hands') or []]
                harvested = {ppos[i] for i, u in enumerate([prev_act.get('farmer') or ['PASS']] + list(prev_act.get('hands') or []))
                             if i < len(ppos) and u and u[0] == 'HARVEST'}
                for y, row in enumerate(pf['tiles']):
                    for x, t in enumerate(row):
                        if isinstance(t, dict) and t.get('kind') == 'PLANT':
                            nt = farm['tiles'][y][x]
                            if not (isinstance(nt, dict) and nt.get('kind') == 'PLANT') and (x, y) not in harvested:
                                c['crop_lost'] += 1
                                c[f'lost_{t["crop"]}'] += 1
        for od in a[seat].get('market') or []:
            if not od:
                continue
            k = od[0]
            if k == 'BUY_SEED' and len(od) >= 3:
                c[f'seed_{od[1]}'] += int(od[2]) * mod.CROPS[od[1]]['seed']
                c['cost_seed'] += int(od[2]) * mod.CROPS[od[1]]['seed']
            elif k == 'BUY_ANIMAL':
                c['cost_animal'] += mod.ANIMALS[od[1]]['cost'] * (int(od[2]) if len(od) >= 3 else 1)
            elif k == 'BUY_PRODUCT' and len(od) >= 3:
                c['cost_product'] += int(od[2]) * prices.get(od[1], 0)
            elif k == 'HIRE':
                c['hire_n'] += 1
            elif k == 'BUY_LAND':
                c['land_n'] += 1
        units = [a[seat].get('farmer') or ['PASS']] + list(a[seat].get('hands') or [])
        c['work'] += sum(1 for u in units if u and u[0] not in ('PASS', 'NORTH', 'SOUTH', 'EAST', 'WEST', 'PICKUP', 'DROP'))
        prev_obs, prev_act = me, a[seat]
        g.step(a[0], a[1])
    mo = [o[0]['farms'][0]['money'], o[0]['farms'][1]['money']]
    c['own'] = mo[seat]; c['opp'] = mo[1 - seat]
    c['low_cash_days_0_15'] = sum(1 for d in range(16) if cash_min[d] < 200)
    for p in PRODS:
        c[f'price_{p}'] = price_sum[p] / max(1, price_n[p])
    return name, seed, opp_spec, seat, dict(c)


def main():
    jobs = [(n, s, o, seat) for n in CONFIGS for s in SEEDS for o in OPPS for seat in (0, 1)]
    with ProcessPoolExecutor(max_workers=8) as pool:
        res = list(pool.map(one, jobs))
    json.dump(res, open(f'{HERE}/area_cost_diag_result.json', 'w'))
    agg = defaultdict(lambda: defaultdict(list))
    for n, s, o, seat, c in res:
        on = 'y68g' if 'y68g' in o else 'v2'
        for k, v in c.items():
            agg[(n, on)][k].append(v)
            agg[(n, 'all')][k].append(v)
    keys = (['own', 'opp', 'work', 'crop_tile_days', 'crop_lost', 'low_cash_days_0_15', 'hire_n', 'land_n',
             'cost_seed', 'cost_animal', 'cost_product']
            + [f'lost_{p}' for p in ('WHEAT', 'STRAWBERRY', 'MELON', 'CARROT', 'TOMATO')]
            + [f'sell_{p}' for p in PRODS] + [f'rev_{p}' for p in PRODS] + [f'price_{p}' for p in PRODS])
    for scope in ('all', 'y68g', 'v2'):
        print(f"\n===== 对手范围 {scope}（每局均值；括号内 = 相对基准差）=====")
        print(f"{'指标':20s}" + "".join(f"{n:>22s}" for n in CONFIGS))
        for k in keys:
            vals = [statistics.mean(agg[(n, scope)].get(k, [0])) for n in CONFIGS]
            if max(abs(v) for v in vals) < 0.5:
                continue
            cells = [f"{vals[0]:>22.0f}"] + [f"{v:>12.0f}({v - vals[0]:+8.0f})" for v in vals[1:]]
            print(f"{k:20s}" + "".join(cells))


if __name__ == '__main__':
    main()
