"""整局回放跟随冒烟：ga4 最优参数 vs y68g，2 seed × 双席位；打印 own/分差/回放命中与修复次数。"""
import sys, json, importlib.util, statistics, os
from concurrent.futures import ProcessPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
M = '/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model'
CFGS = {
    '关(基准)': {},
    '不检查 不切换(=纯tape)': {'eps_on': 1, 'eps_gate': 2, 'eps_switch1': 0, 'eps_switch2': 0},
    '不检查 商店切换': {'eps_on': 1, 'eps_gate': 2},
    '坐标门 K1修复 商店切换': {'eps_on': 1, 'eps_gate': 1, 'eps_repair': 0},
    '坐标门 走回修复 商店切换': {'eps_on': 1, 'eps_gate': 1, 'eps_repair': 2},
    '坐标门 K1修复 至d16': {'eps_on': 1, 'eps_gate': 1, 'eps_repair': 0, 'eps_until_day': 16},
    '坐标门 K1修复 K1市场': {'eps_on': 1, 'eps_gate': 1, 'eps_repair': 0, 'eps_market': 0},
}


def one(job):
    name, seed, seat = job
    sys.path.insert(0, '/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness')
    sys.path.insert(0, f'{M}/v16_online_fidelity')
    sys.path.insert(0, HERE)
    import engine, fidelity
    from schedule_gen import gen_tables, DEFAULTS
    best = max(json.load(open(f'{HERE}/best_iter_ga4.json'))['candidates'], key=lambda c: c['hold_margin'])
    params = {**DEFAULTS, **best['params'], **CFGS[name]}
    spec = importlib.util.spec_from_file_location(f'es_{seed}_{seat}_{abs(hash(name))}', f'{HERE}/main.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    base_tu = json.load(open(f'{HERE}/knowledge.json'))['tuning']
    ov = gen_tables(params); te = ov.pop('tuning_extra')
    ov['tuning'] = {**base_tu, 'fert_specialist': False, 't0_pool_select': False, **te}
    mod.KN_OVERRIDE = ov
    opp = fidelity.make_agent(f'sub:{M}/v58_mosaic/dist_backup/y68g_main.py')
    if seat == 0:
        b0, b1 = engine.play(mod.agent, opp, seed=seed); own, mg = b0, b0 - b1
    else:
        b0, b1 = engine.play(opp, mod.agent, seed=seed); own, mg = b1, b1 - b0
    st = mod._STATE.get(seat, {})
    return name, own, mg, st.get('eps_hit', 0), st.get('eps_miss', 0), st.get('eps_ep')


def tape_ref(job):
    seed, seat = job
    sys.path.insert(0, '/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness')
    sys.path.insert(0, f'{M}/v16_online_fidelity')
    import engine, fidelity, gzip
    lib = json.loads(gzip.open(f'{HERE}/route_eps.json.gz').read().decode())
    acts = lib['eps'][lib['default']]
    me = fidelity.tape_agent(acts)
    opp = fidelity.make_agent(f'sub:{M}/v58_mosaic/dist_backup/y68g_main.py')
    if seat == 0:
        b0, b1 = engine.play(me, opp, seed=seed); return b0, b0 - b1
    b0, b1 = engine.play(opp, me, seed=seed); return b1, b1 - b0


def main():
    jobs = [(n, s, seat) for n in CFGS for s in (700001, 700098) for seat in (0, 1)]
    with ProcessPoolExecutor(max_workers=8) as pool:
        res = list(pool.map(one, jobs))
    with ProcessPoolExecutor(max_workers=4) as pool:
        tr = list(pool.map(tape_ref, [(s_, seat) for s_ in (700001, 700098) for seat in (0, 1)]))
    print(f"{'纯 tape(默认局)':22s} own {statistics.mean(x[0] for x in tr):7.0f} 分差 {statistics.mean(x[1] for x in tr):+8.0f}")
    for n in CFGS:
        r = [x for x in res if x[0] == n]
        print(f"{n:22s} own {statistics.mean(x[1] for x in r):7.0f} 分差 {statistics.mean(x[2] for x in r):+8.0f} 胜 {sum(1 for x in r if x[2] > 0)}/4 "
              f"| 回放采用 {statistics.mean(x[3] for x in r):6.0f} 不合法修复 {statistics.mean(x[4] for x in r):5.0f} 末局 {[x[5] for x in r]}")


if __name__ == '__main__':
    main()
