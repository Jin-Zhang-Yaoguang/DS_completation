import sys, importlib.util, json, statistics
from concurrent.futures import ProcessPoolExecutor
HERE = '/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/serene-cerf-f00e3b/kaggle_Kaggriculture/model/k1_compiled_knowledge'
MOS = '/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v58_mosaic/dist_backup'
POOL = '/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/opponent_pool_v1'
OPPS = [('y68g', f'sub:{MOS}/y68g_main.py'), ('y68c', f'sub:{POOL}/packs/y68c_main.py')]
SEEDS = [700001 + 97 * i for i in range(8)]
ON = {'wheat_keep_frac': 0.0, 'wheat_lot_max': 25, 'feed_buy_cap': 70}
CONFIGS = {'全关(对照)': {}, '全开': ON, '只卖麦不留饲料': {'wheat_keep_frac': 0.0}, '半留': {'wheat_keep_frac': 0.5}, '大批卖麦': {'wheat_lot_max': 25}, '饲料价上限70': {'feed_buy_cap': 70}}

def one(job):
    name, seed, opp_spec = job
    sys.path.insert(0, '/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness')
    sys.path.insert(0, '/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v16_online_fidelity')
    sys.path.insert(0, HERE)
    import engine, fidelity
    from schedule_gen import gen_tables
    best = max(json.load(open(f'{HERE}/best_iter_scale.json'))['candidates'], key=lambda c: c['hold_margin'])
    params = {**best['params'], 'wheat_keep_frac': 1, 'wheat_lot_max': 10, 'feed_buy_cap': 55, 'fill_ratio': 0, 'burst_cap': 6, 'late_carrot_day': 28,
              'late_carrot_area': 0, 'endgame_slack': 0, **CONFIGS[name]}
    spec = importlib.util.spec_from_file_location(f'ab_{seed}_{abs(hash(name + opp_spec))}', f'{HERE}/main.py')
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
    base = '全关(对照)'
    print(f"{'配置':14s} | {'own':>7s} {'分差':>8s} | 分差配对差 (t, 胜) | own 配对差")
    for n in CONFIGS:
        owns = [m[(n, s, o)][0] for s in SEEDS for _, o in OPPS]
        mgs = [m[(n, s, o)][1] for s in SEEDS for _, o in OPPS]
        line = f"{n:14s} | {statistics.mean(owns):7.0f} {statistics.mean(mgs):+8.0f} |"
        if n != base:
            dm = [m[(n, s, o)][1] - m[(base, s, o)][1] for s in SEEDS for _, o in OPPS]
            do = [m[(n, s, o)][0] - m[(base, s, o)][0] for s in SEEDS for _, o in OPPS]
            sd = statistics.stdev(dm)
            t = statistics.mean(dm) / (sd / len(dm) ** 0.5) if sd else 0
            line += f" {statistics.mean(dm):+7.0f} (t={t:+.2f}, {sum(1 for x in dm if x > 0)}/{len(dm)}) | {statistics.mean(do):+7.0f}"
        print(line)

if __name__ == '__main__':
    main()
