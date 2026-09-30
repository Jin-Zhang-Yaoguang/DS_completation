"""早期策略/混合策略探针：自动找各版本入口 main.py，能加载的与 K1 打 4 seed × 双席位。"""
import sys, statistics, os
from concurrent.futures import ProcessPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
M = '/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model'
DIRS = ['v1_adaptive_market', 'v2_survival_guard', 'v5_rule_hybrid', 'v12_crop_dusta', 'v14_rule_search', 'v17_market_guard',
        'v18_planner_scheduler', 'v21_crop_scheduler', 'v22_global_scheduler', 'v23_plan_scheduler', 'v24_hybrid',
        'v25_market_maker', 'v29_adaptive', 'v30_sched_market', 'v31_sell_timing', 'v33_opp_router', 'v36_day_planner',
        'v4h_tape_ledger_hybrid', 'v5_tape_tree_hmoe', 'v6_v120exec_tape', 'v4h_demand_race_hybrid', 'v39_pure_tape',
        'v43_translator', 'v49_shop_router', 'v72_majkel_knobs', 'v119_center_livestock_spatial_moe',
        'v120_hierarchical_top5_distillation', 'v116_heuristic_gold_search']
SEEDS = [720011 + 173 * i for i in range(4)]


def find_main(d):
    p = f'{M}/{d}'
    for cand in ('main.py', f'{d}.py'):
        if os.path.exists(f'{p}/{cand}'):
            return f'{p}/{cand}'
    for root, _, files in os.walk(p):
        if 'main.py' in files and 'pycache' not in root:
            return f'{root}/main.py'
    return None


def one(job):
    d, path, seed, seat = job
    sys.path.insert(0, '/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness')
    sys.path.insert(0, f'{M}/v16_online_fidelity')
    import importlib.util, engine, fidelity, signal
    spec = importlib.util.spec_from_file_location(f'pe_{seed}_{seat}_{d}', f'{HERE}/main.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    signal.alarm(60)
    try:
        os.chdir(os.path.dirname(path))
        opp = fidelity.make_agent(f'sub:{path}')
        if seat == 0:
            b0, b1 = engine.play(mod.agent, opp, seed=seed); me, op = b0, b1
        else:
            b0, b1 = engine.play(opp, mod.agent, seed=seed); me, op = b1, b0
        return d, me, op, None
    except BaseException as e:
        return d, 0, 0, repr(e)[:90]
    finally:
        signal.alarm(0)


def main():
    found = {d: find_main(d) for d in DIRS}
    jobs = [(d, p, s, seat) for d, p in found.items() if p for s in SEEDS for seat in (0, 1)]
    print("无入口:", [d for d, p in found.items() if not p])
    with ProcessPoolExecutor(max_workers=8) as pool:
        res = list(pool.map(one, jobs))
    rows = []
    for d, p in found.items():
        if not p:
            continue
        r = [x for x in res if x[0] == d]
        ok = [x for x in r if not x[3]]
        err = next((x[3] for x in r if x[3]), '')
        if not ok:
            print(f"{d:40s} 失败 {err}"); continue
        rows.append((statistics.mean(x[1] - x[2] for x in ok), d, sum(1 for x in ok if x[1] > x[2]), len(ok),
                     statistics.mean(x[2] for x in ok), statistics.mean(x[1] for x in ok), p.replace(M + '/', ''), err))
    for mg, d, w, k, op, me, p, err in sorted(rows, reverse=True):
        print(f"{d:40s} | {w}/{k} | 对手 {op:7.0f} | K1 {me:7.0f} | 分差 {mg:+8.0f} | {p} {err}")


if __name__ == '__main__':
    main()
