"""分层口径自适应复核：以指定 best_iter 的 holdout 最优为基准（自适应全关），逐项强开，按对手层报告分差配对差。
用法: /opt/anaconda3/bin/python3 adapt_ab_tier.py best_iter_ga2.json [seeds]
"""
import sys, importlib.util, json, statistics, os
from concurrent.futures import ProcessPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
TJ = json.load(open(f'{HERE}/opp_tiers.json'))
FMT = lambda x: x.replace('{M}', TJ['M']).replace('{K1}', TJ['K1'])
# 每层取前 2 个对手（hard 取 3 个）作为固定复核集
OPPS = [(tier, FMT(o)) for tier, t in TJ['tiers'].items() for o in t['opps'][:(3 if tier == 'hard' else 2)]]
BEST = sys.argv[1] if len(sys.argv) > 1 else 'best_iter_ga2.json'
NSEED = int(sys.argv[2]) if len(sys.argv) > 2 else 4
SEEDS = [730021 + 149 * i for i in range(NSEED)]
OFF = {'price_area_gain': 0, 'opp_counter_gain': 0, 'opp_sell_ahead': 0, 'opp_anim_gain': 0, 'race_on': 0, 'mshift_on': 0, 'doomsday_on': 0,
       'layout_sector': 0, 'layout_fixed_order': 0, 'layout_animal_last': 0,
       'plant_cap_mid': 0, 'plant_cap_late': 0, 'plant_idle_hour': 24, 'plant_idle_extra': 0, 'seed_lookahead': 0}
CONFIGS = {
    '基准(自适应全关)': OFF,
    '搜索原样': {},
    'ga1最优(旧口径搜出)': 'GA1',
    '价格调面积 g=1': {**OFF, 'price_area_gain': 1.0, 'price_area_from': 6},
    '反跟种 g=0.5': {**OFF, 'opp_counter_gain': 0.5, 'price_area_from': 6},
    '对手挂果抢卖': {**OFF, 'opp_sell_ahead': 1, 'opp_hang_th': 6},
    '动物随对手 g=0.5': {**OFF, 'opp_anim_gain': 0.5, 'opp_anim_from': 6},
    'race 跟卖': {**OFF, 'race_on': 1, 'race_trigger': 3, 'race_decay': 0.6},
    '低价转产 0.8': {**OFF, 'mshift_on': 1, 'price_floor_frac': 0.8},
    # ga3 新候选（布局 + 对手类型乘数）；仅在基准文件含对应维度时有意义
    '布局:扇区4': {**OFF, 'layout_sector': 4},
    '布局:扇区4+服务频率序': {**OFF, 'layout_sector': 4, 'layout_fixed_order': 1},
    '布局:服务频率序': {**OFF, 'layout_fixed_order': 1},
    '布局:动物外环': {**OFF, 'layout_animal_last': 1},
    '动物随对手 仅light+std': {**OFF, 'opp_anim_gain': 0.5, 'tm_anim_light': 1, 'tm_anim_std': 1, 'tm_anim_wheat': 0},
    '动物随对手 仅light': {**OFF, 'opp_anim_gain': 0.5, 'tm_anim_light': 1, 'tm_anim_std': 0, 'tm_anim_wheat': 0},
    # ga4 方案1 候选（种植执行）
    '种植:中期限速8': {**OFF, 'plant_cap_mid': 8},
    '种植:后期限速8': {**OFF, 'plant_cap_late': 8},
    '种植:中后期限速8': {**OFF, 'plant_cap_mid': 8, 'plant_cap_late': 8},
    '种植:15点后+4': {**OFF, 'plant_idle_hour': 15, 'plant_idle_extra': 4},
    '种植:12点后+8': {**OFF, 'plant_idle_hour': 12, 'plant_idle_extra': 8},
    '种植:买种看次日': {**OFF, 'seed_lookahead': 1},
}
# 用法补充：第三个参数给出配置名子串过滤（逗号分隔），如 "基准,布局" 只跑布局组
if len(sys.argv) > 3:
    _keep = sys.argv[3].split(',')
    CONFIGS = {k: v for k, v in CONFIGS.items() if k == '基准(自适应全关)' or any(x in k for x in _keep)}
BASE = '基准(自适应全关)'


def one(job):
    name, seed, tier, opp_spec, seat = job
    sys.path.insert(0, '/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness')
    sys.path.insert(0, f"{TJ['M']}/v16_online_fidelity")
    sys.path.insert(0, HERE)
    import engine, fidelity
    from schedule_gen import gen_tables, DEFAULTS
    if CONFIGS[name] == 'GA1':
        best = max(json.load(open(f'{HERE}/best_iter_ga1.json'))['candidates'], key=lambda c: c['hold_margin'])
        params = {**DEFAULTS, **best['params']}
    else:
        best = max(json.load(open(f'{HERE}/{BEST}'))['candidates'], key=lambda c: c['hold_margin'])
        params = {**DEFAULTS, **best['params'], **CONFIGS[name]}
    spec = importlib.util.spec_from_file_location(f'abt_{seed}_{seat}_{abs(hash(name + opp_spec))}', f'{HERE}/main.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    base_tu = json.load(open(f'{HERE}/knowledge.json'))['tuning']
    ov = gen_tables(params); te = ov.pop('tuning_extra')
    ov['tuning'] = {**base_tu, 'fert_specialist': False, 't0_pool_select': False, **te}
    mod.KN_OVERRIDE = ov
    opp = fidelity.make_agent(opp_spec)
    if seat == 0:
        b0, b1 = engine.play(mod.agent, opp, seed=seed); return name, seed, opp_spec, seat, b0, b0 - b1
    b0, b1 = engine.play(opp, mod.agent, seed=seed); return name, seed, opp_spec, seat, b1, b1 - b0


def main():
    jobs = [(n, s, tier, o, seat) for n in CONFIGS for s in SEEDS for tier, o in OPPS for seat in (0, 1)]
    with ProcessPoolExecutor(max_workers=8) as pool:
        res = list(pool.map(one, jobs))
    m = {(n, s, o, seat): (own, mg) for n, s, o, seat, own, mg in res}
    tiers = list(TJ['tiers'])
    print(f"基准={BEST} holdout 最优；{len(OPPS)} 对手×{NSEED} seed×双席位 = {len(OPPS) * NSEED * 2} 局/配置")
    print(f"{'配置':16s} | 全体分差配对差 (t) | own 差 | " + " | ".join(f"{t:>7s}" for t in tiers))
    for n in CONFIGS:
        keys = [(s, o, seat) for s in SEEDS for _, o in OPPS for seat in (0, 1)]
        if n == BASE:
            per = [statistics.mean(m[(BASE, s, o, seat)][1] for s in SEEDS for tt, o in OPPS if tt == t for seat in (0, 1)) for t in tiers]
            print(f"{n:16s} | 均分差 {statistics.mean(m[(BASE,) + k][1] for k in keys):+8.0f}        |        | " + " | ".join(f"{x:+7.0f}" for x in per))
            continue
        dm = [m[(n,) + k][1] - m[(BASE,) + k][1] for k in keys]
        do = [m[(n,) + k][0] - m[(BASE,) + k][0] for k in keys]
        sd = statistics.stdev(dm)
        t = statistics.mean(dm) / (sd / len(dm) ** 0.5) if sd else 0
        per = [statistics.mean(m[(n, s, o, seat)][1] - m[(BASE, s, o, seat)][1]
                               for s in SEEDS for tt, o in OPPS if tt == tier for seat in (0, 1)) for tier in tiers]
        print(f"{n:16s} | {statistics.mean(dm):+7.0f} (t={t:+.2f}) | {statistics.mean(do):+6.0f} | " + " | ".join(f"{x:+7.0f}" for x in per))


if __name__ == '__main__':
    main()
