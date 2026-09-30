"""晨间日计划器离线验收：ga4 最优为基准，同局配对（按 seed 聚类统计）。
指标：分差/own、工作次数、移动/工作、作废移动（当天最后工作后）、平均收工小时、每日规划耗时中位/最大（ms）。
对手：y68g（hard）、v2_survival_guard（medium）、v119（medium）、ymg_slice0（tape）；SEEDS 个 seed × 双席位。
用法: /opt/anaconda3/bin/python3 plan_eval.py [nseed]
"""
import sys, importlib.util, json, statistics, os, time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
M = '/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model'
OPPS = [f'sub:{M}/v58_mosaic/dist_backup/y68g_main.py', f'sub:{M}/v2_survival_guard/main.py',
        f'sub:{M}/v119_center_livestock_spatial_moe/main.py', f'tape:{M}/opponent_pool_v1/tapes/ymg_slice0.json']
NSEED = int(sys.argv[1]) if len(sys.argv) > 1 else 4
SEEDS = [930071 + 263 * i for i in range(NSEED)]
MOVES = {"NORTH", "SOUTH", "EAST", "WEST"}
IDLE = MOVES | {"PASS", "PICKUP", "DROP"}
CONFIGS = {
    '基准(ga4最优)': {},
    '计划 看2 早规划': {'plan_on': 1, 'plan_look': 2, 'plan_replan_h': 0},
    '计划 看1 早规划': {'plan_on': 1, 'plan_look': 1, 'plan_replan_h': 0},
    '计划 看3 每4h重规划': {'plan_on': 1, 'plan_look': 3, 'plan_replan_h': 4},
    '计划 看2 无随机': {'plan_on': 1, 'plan_look': 2, 'plan_salt': 0},
}


def one(job):
    name, seed, opp_spec, seat = job
    sys.path.insert(0, '/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness')
    sys.path.insert(0, f'{M}/v16_online_fidelity')
    sys.path.insert(0, HERE)
    import engine, fidelity
    from schedule_gen import gen_tables, DEFAULTS
    best = max(json.load(open(f'{HERE}/best_iter_ga4.json'))['candidates'], key=lambda c: c['hold_margin'])
    params = {**DEFAULTS, **best['params'], **CONFIGS[name]}
    spec = importlib.util.spec_from_file_location(f'pe_{seed}_{seat}_{abs(hash(name + opp_spec))}', f'{HERE}/main.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    base_tu = json.load(open(f'{HERE}/knowledge.json'))['tuning']
    ov = gen_tables(params); te = ov.pop('tuning_extra')
    ov['tuning'] = {**base_tu, 'fert_specialist': False, 't0_pool_select': False, **te}
    mod.KN_OVERRIDE = ov
    # 计时：包装日计划函数
    plan_ms = []
    orig = mod._day_plan
    def timed(*a, **k):
        t0 = time.perf_counter(); r = orig(*a, **k); plan_ms.append((time.perf_counter() - t0) * 1000); return r
    mod._day_plan = timed
    opp = fidelity.make_agent(opp_spec)
    agents = [mod.agent, opp] if seat == 0 else [opp, mod.agent]
    g = engine.load_kagsim().Game(seed=seed)
    per_day = defaultdict(lambda: defaultdict(list))
    work = moves = 0
    step_ms = []
    while not engine._val(g.done):
        o = [g.observe(0), g.observe(1)]
        t0 = time.perf_counter()
        a_me = agents[seat](o[seat])
        step_ms.append((time.perf_counter() - t0) * 1000)
        a_op = agents[1 - seat](o[1 - seat])
        a = [a_me, a_op] if seat == 0 else [a_op, a_me]
        day, hour = int(o[0]['day']), int(o[0]['hour'])
        units = [a_me.get('farmer') or ['PASS']] + list(a_me.get('hands') or [])
        for i, u in enumerate(units):
            op = (u or ['PASS'])[0]
            per_day[day][i].append((hour, op))
            if op in MOVES:
                moves += 1
            elif op not in IDLE:
                work += 1
        g.step(a[0], a[1])
    tail = 0; finish = []
    for day, us in per_day.items():
        last_h = 0
        for seq in us.values():
            wi = [k for k, (_, op) in enumerate(seq) if op not in IDLE]
            if wi:
                tail += sum(1 for _, op in seq[wi[-1] + 1:] if op in MOVES)
                last_h = max(last_h, seq[wi[-1]][0])
        finish.append(last_h)
    mo = [o[0]['farms'][0]['money'], o[0]['farms'][1]['money']]
    return (name, seed, opp_spec, seat, mo[seat], mo[seat] - mo[1 - seat], work, moves, tail,
            statistics.mean(finish) if finish else 0,
            statistics.median(plan_ms) if plan_ms else 0, max(plan_ms) if plan_ms else 0, max(step_ms))


def main():
    jobs = [(n, s, o, seat) for n in CONFIGS for s in SEEDS for o in OPPS for seat in (0, 1)]
    with ProcessPoolExecutor(max_workers=8) as pool:
        res = list(pool.map(one, jobs))
    m = {(r[0], r[1], r[2], r[3]): r for r in res}
    base = '基准(ga4最优)'
    print(f"{len(SEEDS)} seed × {len(OPPS)} 对手 × 双席位；分差差按 seed 聚类（每 seed 一个均值）算 t")
    print(f"{'配置':18s} | own    | 分差    | 工作 | 移动/工作 | 作废移动 | 收工时 | 规划ms中位/最大 | 单步最大ms | 分差差(seed t) | 各对手分差差")
    for n in CONFIGS:
        rr = [r for r in res if r[0] == n]
        mean = lambda k: statistics.mean(r[k] for r in rr)
        line = (f"{n:18s} | {mean(4):6.0f} | {mean(5):+7.0f} | {mean(6):4.0f} | {mean(7) / max(1, mean(6)):8.2f} | "
                f"{mean(8):7.0f} | {mean(9):5.1f} | {mean(10):6.1f}/{max(r[11] for r in rr):6.1f} | {max(r[12] for r in rr):8.1f} |")
        if n != base:
            per_seed = [statistics.mean(m[(n, s, o, st)][5] - m[(base, s, o, st)][5] for o in OPPS for st in (0, 1)) for s in SEEDS]
            sd = statistics.stdev(per_seed) if len(per_seed) > 1 else 0
            t = statistics.mean(per_seed) / (sd / len(per_seed) ** 0.5) if sd else 0
            per_opp = [statistics.mean(m[(n, s, o, st)][5] - m[(base, s, o, st)][5] for s in SEEDS for st in (0, 1)) for o in OPPS]
            line += f" {statistics.mean(per_seed):+7.0f} (t={t:+.2f}) | " + " ".join(f"{x:+6.0f}" for x in per_opp)
        print(line)


if __name__ == '__main__':
    main()
