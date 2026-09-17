"""K1（现池上线形态）vs V128（Majkel 复刻原型，只读引用 lucid-germain-bbfdeb）同 seed/席位/对手配对拆解。
口径：终局金币/分差、品类实卖量/收入/均价、作物面积·天、动物·天、动作构成、逐 5 天段卖出、现金低谷。"""
import sys, importlib.util, json, statistics, os
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
M = '/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model'
V128 = '/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/lucid-germain-bbfdeb/kaggle_Kaggriculture/model/v128_majkel_replica/main.py'
OPPS = [f'sub:{M}/v58_mosaic/dist_backup/y68g_main.py', f'sub:{M}/opponent_pool_v1/packs/y68c_main.py']
SEEDS = [1100 + i for i in range(16)]
PRODS = ("WHEAT", "MELON", "STRAWBERRY", "CARROT", "TOMATO", "MILK", "EGG", "WOOL", "FERTILIZER")
MOVES = {"NORTH", "SOUTH", "EAST", "WEST"}


def one(job):
    name, seed, opp_spec, seat = job
    sys.path.insert(0, '/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness')
    sys.path.insert(0, f'{M}/v16_online_fidelity')
    import engine, fidelity
    path = f'{HERE}/main.py' if name == 'k1' else V128
    spec = importlib.util.spec_from_file_location(f'ag_{name}_{seed}_{seat}', path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    me = getattr(mod, '_ENTRY', None) or mod.agent
    opp = fidelity.make_agent(opp_spec)
    agents = [me, opp] if seat == 0 else [opp, me]
    g = engine.load_kagsim().Game(seed=seed)
    c = Counter(); cash_min = defaultdict(lambda: 10**9)
    prev = None
    while not engine._val(g.done):
        o = [g.observe(0), g.observe(1)]
        a = [agents[0](o[0]), agents[1](o[1])]
        me_o = o[seat]; day, hour = int(me_o['day']), int(me_o['hour'])
        farm = me_o['farms'][seat]
        cash_min[day] = min(cash_min[day], farm['money'])
        if prev is not None:
            pshed, pprices, pact, pday = prev
            for od in pact.get('market') or []:
                if od and od[0] == 'SELL' and len(od) >= 3:
                    q = min(int(od[2] or 0), pshed.get(od[1], 0))
                    c[f'sell_{od[1]}'] += q
                    c[f'rev_{od[1]}'] += q * pprices.get(od[1], 0)
                    c[f'seg{pday // 5}_rev'] += q * pprices.get(od[1], 0)
        if hour == 12:
            for row in farm['tiles']:
                for t in row:
                    if isinstance(t, dict):
                        if t.get('kind') == 'PLANT':
                            c[f'area_{t["crop"]}'] += 1
                        elif t.get('animal'):
                            c[f'an_{t["animal"]}'] += 1
        for u in [a[seat].get('farmer') or ['PASS']] + list(a[seat].get('hands') or []):
            op = (u or ['PASS'])[0]
            c['a_MOVE' if op in MOVES else f'a_{op}'] += 1
        prev = (dict((me_o.get('private') or {}).get('shed') or {}),
                dict((me_o.get('market') or {}).get('prices') or {}), a[seat], day)
        g.step(a[0], a[1])
    mo = [o[0]['farms'][0]['money'], o[0]['farms'][1]['money']]
    c['own'] = mo[seat]; c['opp'] = mo[1 - seat]; c['margin'] = mo[seat] - mo[1 - seat]
    c['low_cash_d15'] = sum(1 for d in range(16) if cash_min[d] < 200)
    return name, seed, opp_spec, seat, dict(c)


def main():
    jobs = [(n, s, o, seat) for n in ('k1', 'v128') for s in SEEDS for o in OPPS for seat in (0, 1)]
    with ProcessPoolExecutor(max_workers=8) as pool:
        res = list(pool.map(one, jobs))
    json.dump(res, open(f'{HERE}/v128_vs_k1_rows.json', 'w'))
    agg = {n: defaultdict(list) for n in ('k1', 'v128')}
    for n, s, o, seat, c in res:
        for k, v in c.items():
            agg[n][k].append(v)
    n_g = len(SEEDS) * len(OPPS) * 2
    print(f"每 agent {n_g} 局（同 seed/对手/席位 配对）")
    keys = (['own', 'opp', 'margin', 'low_cash_d15']
            + [f'{p}_{x}' for x in () for p in ()]
            + sorted(k for k in set(agg['k1']) | set(agg['v128'])
                     if k.startswith(('sell_', 'rev_', 'area_', 'an_', 'a_', 'seg'))))
    for k in ['own', 'opp', 'margin', 'low_cash_d15'] + [x for x in keys if x not in ('own', 'opp', 'margin', 'low_cash_d15')]:
        a = statistics.mean(agg['k1'].get(k, [0]) or [0]); b = statistics.mean(agg['v128'].get(k, [0]) or [0])
        if max(abs(a), abs(b)) < 1:
            continue
        print(f"  {k:22s} K1 {a:9.0f} | V128 {b:9.0f} | 差 {b - a:+9.0f}")
    per_seed = []
    for s in SEEDS:
        mk = statistics.mean(c['margin'] for n, ss, o, seat, c in res if n == 'k1' and ss == s)
        mv = statistics.mean(c['margin'] for n, ss, o, seat, c in res if n == 'v128' and ss == s)
        per_seed.append(mv - mk)
    sd = statistics.stdev(per_seed)
    t = statistics.mean(per_seed) / (sd / len(per_seed) ** 0.5) if sd else 0
    print(f"\nV128−K1 分差差 {statistics.mean(per_seed):+.0f}（seed t={t:+.2f}，n={len(per_seed)}）")


if __name__ == '__main__':
    main()
