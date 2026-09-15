"""路线规划内核配对复核（方案2）；原模板：面积能否吸收闲置人手：以 ga1 最优（现池主力）为基准，加大作物面积，配对测 分差/own/工作次数/作废移动。
对手 y68g + v2_survival_guard，6 seed × 双席位 = 24 局/组。
"""
import sys, importlib.util, json, statistics, os
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
M = '/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model'
OPPS = [f'sub:{M}/v58_mosaic/dist_backup/y68g_main.py', f'sub:{M}/v2_survival_guard/main.py']
SEEDS = [800057 + 241 * i for i in range(4)]
MOVES = {"NORTH", "SOUTH", "EAST", "WEST"}
IDLE = MOVES | {"PASS", "PICKUP", "DROP"}
CONFIGS = {
    '基准(ga4最优)': {},
    '路线 重规划4 前看3': {'route_on': 1, 'route_replan_h': 4, 'route_look': 3},
    '路线 重规划8 前看1': {'route_on': 1, 'route_replan_h': 8, 'route_look': 1},
    '路线 重规划2 前看5': {'route_on': 1, 'route_replan_h': 2, 'route_look': 5},
    '路线 重规划1 前看2': {'route_on': 1, 'route_replan_h': 1, 'route_look': 2},
    '路线 重规划12 前看2': {'route_on': 1, 'route_replan_h': 12, 'route_look': 2},
}


def one(job):
    name, seed, opp_spec, seat = job
    sys.path.insert(0, '/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness')
    sys.path.insert(0, f'{M}/v16_online_fidelity')
    sys.path.insert(0, HERE)
    import engine, fidelity
    from schedule_gen import gen_tables, DEFAULTS, SCHED_SPACE
    best = max(json.load(open(f'{HERE}/best_iter_ga4.json'))['candidates'], key=lambda c: c['hold_margin'])
    params = {**DEFAULTS, **best['params']}
    bounds = {n: (lo, hi) for n, lo, hi, _ in SCHED_SPACE}
    for k, v in CONFIGS[name].items():
        if isinstance(v, str):
            params[k] = params[k] + float(v)
        else:
            params[k] = v
        lo, hi = bounds[k]
        params[k] = min(hi + 20, max(lo - 5, params[k]))  # 允许越过搜索边界做结构测试
    spec = importlib.util.spec_from_file_location(f'al_{seed}_{seat}_{abs(hash(name + opp_spec))}', f'{HERE}/main.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    base_tu = json.load(open(f'{HERE}/knowledge.json'))['tuning']
    ov = gen_tables(params); te = ov.pop('tuning_extra')
    ov['tuning'] = {**base_tu, 'fert_specialist': False, 't0_pool_select': False, **te}
    mod.KN_OVERRIDE = ov
    opp = fidelity.make_agent(opp_spec)
    agents = [mod.agent, opp] if seat == 0 else [opp, mod.agent]
    g = engine.load_kagsim().Game(seed=seed)
    per_day = defaultdict(lambda: defaultdict(list))
    work = 0
    while not engine._val(g.done):
        o = [g.observe(0), g.observe(1)]
        a = [agents[0](o[0]), agents[1](o[1])]
        day = int(o[0]["day"])
        units = [a[seat].get("farmer") or ["PASS"]] + list(a[seat].get("hands") or [])
        for i, u in enumerate(units):
            op = (u or ["PASS"])[0]
            per_day[day][i].append(op)
            if op not in IDLE:
                work += 1
        g.step(a[0], a[1])
    tail = 0
    for day, us in per_day.items():
        for seq in us.values():
            wi = [i for i, op in enumerate(seq) if op not in IDLE]
            if wi:
                tail += sum(1 for op in seq[wi[-1] + 1:] if op in MOVES)
    mo = [o[0]["farms"][0]["money"], o[0]["farms"][1]["money"]]
    return name, seed, opp_spec, seat, mo[seat], mo[seat] - mo[1 - seat], work, tail


def main():
    jobs = [(n, s, o, seat) for n in CONFIGS for s in SEEDS for o in OPPS for seat in (0, 1)]
    with ProcessPoolExecutor(max_workers=8) as pool:
        res = list(pool.map(one, jobs))
    m = {(n, s, o, seat): (own, mg, w, t) for n, s, o, seat, own, mg, w, t in res}
    keys = [(s, o, seat) for s in SEEDS for o in OPPS for seat in (0, 1)]
    base = '基准(ga4最优)'
    print(f"{'配置':16s} | own    | 分差    | 工作次数 | 作废移动 | 分差配对差 (t) | own 配对差 | vs y68g 分差差 | vs v2 分差差")
    for n in CONFIGS:
        own = statistics.mean(m[(n,) + k][0] for k in keys)
        mg = statistics.mean(m[(n,) + k][1] for k in keys)
        w = statistics.mean(m[(n,) + k][2] for k in keys)
        t = statistics.mean(m[(n,) + k][3] for k in keys)
        line = f"{n:16s} | {own:6.0f} | {mg:+7.0f} | {w:7.0f} | {t:7.0f} |"
        if n != base:
            dm = [m[(n,) + k][1] - m[(base,) + k][1] for k in keys]
            do = [m[(n,) + k][0] - m[(base,) + k][0] for k in keys]
            sd = statistics.stdev(dm)
            tt = statistics.mean(dm) / (sd / len(dm) ** 0.5) if sd else 0
            per = [statistics.mean(m[(n, s, o, seat)][1] - m[(base, s, o, seat)][1] for s in SEEDS for seat in (0, 1)) for o in OPPS]
            line += f" {statistics.mean(dm):+7.0f} (t={tt:+.2f}) | {statistics.mean(do):+6.0f} | {per[0]:+7.0f} | {per[1]:+7.0f}"
        print(line)


if __name__ == '__main__':
    main()
