"""方案池对比（都按 knowledge 默认 tri_day_on=1）：A=现池 plan_pool.json，B=ga7 分风格池；同 seed/席位/对手配对，记录切换次数。"""
import sys, json, importlib.util, statistics, os
from concurrent.futures import ProcessPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
M = '/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model'
OPPS = {'g': f'sub:{M}/v58_mosaic/dist_backup/y68g_main.py', 'c': f'sub:{M}/opponent_pool_v1/packs/y68c_main.py',
        'v2': f'sub:{M}/v2_survival_guard/main.py', 'ymg': f'tape:{M}/opponent_pool_v1/tapes/ymg_slice0.json'}


def one(job):
    sd, which, seat, on = job
    sys.path.insert(0, '/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness')
    sys.path.insert(0, f'{M}/v16_online_fidelity')
    import engine, fidelity
    spec = importlib.util.spec_from_file_location(f'p{sd}{which}{seat}{on}', f'{HERE}/main.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    kn = json.load(open(f'{HERE}/knowledge.json'))
    kn['plan_pool'] = json.load(open(f'{HERE}/plan_pool.json' if which == 'A' else f'{HERE}/plan_pool_iter_ga7.json'))
    if which == 'C':
        kn['tuning']['tri_day_on'] = 0  # C = 风格池纯 t0 盲抽（无重选）
    if which == 'D':
        kn['tuning']['tri_day_on'] = 0
        kn['plan_pool'] = [json.load(open(f'{HERE}/plan_pool_iter_ga7.json'))[0]]  # D = 仅 ga7 均衡最优单方案
    mod.KN_OVERRIDE = kn
    opp = fidelity.make_agent(OPPS[on])
    me = mod.agent
    if seat == 0:
        b0, b1 = engine.play(me, opp, seed=sd); own, mg = b0, b0 - b1
    else:
        b0, b1 = engine.play(opp, me, seed=sd); own, mg = b1, b1 - b0
    st = mod._STATE.get(seat, {})
    return sd, which, own, mg, st.get('tri_switches', 0)


def main():
    seeds = [1200 + 7 * i for i in range(10)]
    jobs = [(sd, w, seat, on) for sd in seeds for w in ('A', 'B', 'C', 'D') for seat in (0, 1) for on in OPPS]
    with ProcessPoolExecutor(max_workers=8) as pool:
        res = list(pool.map(one, jobs))
    for w in ('A', 'B', 'C', 'D'):
        r = [(o, m, s) for sd, ww, o, m, s in res if ww == w]
        lab = {'A': 'A 现池+tri', 'B': 'B 风格池+tri', 'C': 'C 风格池盲抽', 'D': 'D ga7均衡单方案'}[w]
        print(f"{lab}: own {statistics.mean(x[0] for x in r):7.0f} "
              f"margin {statistics.mean(x[1] for x in r):+8.0f} 切换/局 {statistics.mean(x[2] for x in r):.2f} (n={len(r)})")
    per = [statistics.mean(m for sd2, w, o, m, s in res if w == 'B' and sd2 == sd)
           - statistics.mean(m for sd2, w, o, m, s in res if w == 'A' and sd2 == sd) for sd in seeds]
    sd_ = statistics.stdev(per)
    t = statistics.mean(per) / (sd_ / len(per) ** 0.5) if sd_ else 0
    print(f"B−A 配对分差差 {statistics.mean(per):+.0f} (seed t={t:+.2f}) per-seed {[round(x) for x in per]}")


if __name__ == '__main__':
    main()
