"""对手/市场自适应复核：以 ga1 holdout 最优为对照，逐项强开自适应机制；并与上轮池最优(value)同 seed 对比。24 局/组。"""
import sys, importlib.util, json, statistics
from concurrent.futures import ProcessPoolExecutor
HERE = '/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/serene-cerf-f00e3b/kaggle_Kaggriculture/model/k1_compiled_knowledge'
MOS = '/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v58_mosaic/dist_backup'
POOL = '/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/opponent_pool_v1'
OPPS = [('y68g', f'sub:{MOS}/y68g_main.py'), ('y68c', f'sub:{POOL}/packs/y68c_main.py')]
SEEDS = [710003 + 131 * i for i in range(12)]
OFF = {'price_area_gain': 0, 'opp_counter_gain': 0, 'opp_sell_ahead': 0, 'opp_anim_gain': 0, 'race_on': 0, 'mshift_on': 0, 'doomsday_on': 0}
CONFIGS = {
    'ga1最优(自适应全关)': OFF,
    'ga1最优(原样)': {},
    '上轮池最优value': 'VALUE',
    '价格调面积 g=1': {**OFF, 'price_area_gain': 1.0, 'price_area_from': 6},
    '反跟种 g=0.5': {**OFF, 'opp_counter_gain': 0.5, 'price_area_from': 6},
    '对手挂果抢卖 th=6': {**OFF, 'opp_sell_ahead': 1, 'opp_hang_th': 6},
    '动物随对手 g=0.5': {**OFF, 'opp_anim_gain': 0.5},
    'race 跟卖': {**OFF, 'race_on': 1, 'race_trigger': 3, 'race_decay': 0.6},
    '低价转产 0.5': {**OFF, 'mshift_on': 1, 'price_floor_frac': 0.5},
    '末日抛售': {**OFF, 'doomsday_on': 1},
    '全开': {**OFF, 'price_area_gain': 1.0, 'price_area_from': 6, 'opp_counter_gain': 0.5, 'opp_sell_ahead': 1,
             'opp_hang_th': 6, 'opp_anim_gain': 0.5, 'race_on': 1, 'mshift_on': 1},
}
BASE = 'ga1最优(自适应全关)'


def one(job):
    name, seed, opp_spec = job
    sys.path.insert(0, '/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness')
    sys.path.insert(0, '/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v16_online_fidelity')
    sys.path.insert(0, HERE)
    import engine, fidelity
    from schedule_gen import gen_tables, DEFAULTS
    if CONFIGS[name] == 'VALUE':
        best = max(json.load(open(f'{HERE}/best_iter_value.json'))['candidates'], key=lambda c: c['hold_margin'])
        params = {**DEFAULTS, **best['params']}
    else:
        best = max(json.load(open(f'{HERE}/best_iter_ga1.json'))['candidates'], key=lambda c: c['hold_margin'])
        params = {**best['params'], **CONFIGS[name]}
    spec = importlib.util.spec_from_file_location(f'aab_{seed}_{abs(hash(name + opp_spec))}', f'{HERE}/main.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    base_tu = json.load(open(f'{HERE}/knowledge.json'))['tuning']
    ov = gen_tables(params); te = ov.pop('tuning_extra')
    ov['tuning'] = {**base_tu, 'fert_specialist': False, 't0_pool_select': False, **te}
    mod.KN_OVERRIDE = ov
    opp = fidelity.make_agent(opp_spec)
    b0, b1 = engine.play(mod.agent, opp, seed=seed)
    return name, seed, opp_spec, b0, b0 - b1


def main():
    jobs = [(n, s, o) for n in CONFIGS for s in SEEDS for _, o in OPPS]
    with ProcessPoolExecutor(max_workers=8) as pool:
        res = list(pool.map(one, jobs))
    m = {(n, s, o): (own, mg) for n, s, o, own, mg in res}
    print(f"{'配置':18s} | {'own':>7s} {'分差':>8s} | 分差配对差 (t, 胜/24) | own 配对差")
    for n in CONFIGS:
        keys = [(s, o) for s in SEEDS for _, o in OPPS]
        owns = [m[(n, s, o)][0] for s, o in keys]
        mgs = [m[(n, s, o)][1] for s, o in keys]
        line = f"{n:18s} | {statistics.mean(owns):7.0f} {statistics.mean(mgs):+8.0f} |"
        if n != BASE:
            dm = [m[(n, s, o)][1] - m[(BASE, s, o)][1] for s, o in keys]
            do = [m[(n, s, o)][0] - m[(BASE, s, o)][0] for s, o in keys]
            sd = statistics.stdev(dm)
            t = statistics.mean(dm) / (sd / len(dm) ** 0.5) if sd else 0
            line += f" {statistics.mean(dm):+7.0f} (t={t:+.2f}, {sum(1 for x in dm if x > 0)}) | {statistics.mean(do):+7.0f}"
        print(line)


if __name__ == '__main__':
    main()
