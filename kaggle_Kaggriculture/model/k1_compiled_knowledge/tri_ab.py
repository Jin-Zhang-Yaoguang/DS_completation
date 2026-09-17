"""三天级方案重选 A/B：tri_day_on 0/1 同 seed 配对，y68g+y68c × 8 seed × 双席位。"""
import sys, json, importlib.util, statistics, os
from concurrent.futures import ProcessPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
M = '/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model'


def one(job):
    sd, tri, seat, on = job
    sys.path.insert(0, '/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness')
    sys.path.insert(0, f'{M}/v16_online_fidelity')
    import engine, fidelity
    spec = importlib.util.spec_from_file_location(f'x{sd}{tri}{seat}{on}', f'{HERE}/main.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    kn = json.load(open(f'{HERE}/knowledge.json'))
    kn['tuning']['tri_day_on'] = 1 if tri else 0
    if os.environ.get('TRI_T0FIX'):
        kn['tuning']['t0_pool_select'] = False  # 两组同起点（默认表），只比 tri 开关——干净配对
    if os.environ.get('TRI_GAIN') is not None:
        kn['tuning']['tri_min_gain'] = float(os.environ['TRI_GAIN'])
    if os.environ.get('TRI_SWC') is not None:
        kn['tuning']['tri_sw_cost'] = float(os.environ['TRI_SWC'])
    mod.KN_OVERRIDE = kn
    O = {'g': f'sub:{M}/v58_mosaic/dist_backup/y68g_main.py', 'c': f'sub:{M}/opponent_pool_v1/packs/y68c_main.py',
         'v2': f'sub:{M}/v2_survival_guard/main.py', 'v119': f'sub:{M}/v119_center_livestock_spatial_moe/main.py',
         'ymg': f'tape:{M}/opponent_pool_v1/tapes/ymg_slice0.json', 'fta': f'tape:{M}/opponent_pool_v1/tapes/fta_slice0.json'}
    opp = fidelity.make_agent(O[on])
    if seat == 0:
        b0, b1 = engine.play(mod.agent, opp, seed=sd); return sd, tri, b0, b0 - b1
    b0, b1 = engine.play(opp, mod.agent, seed=sd); return sd, tri, b1, b1 - b0


def main():
    seeds = list(range(1100, 1108))
    jobs = [(sd, tri, seat, on) for sd in seeds for tri in (0, 1) for seat in (0, 1) for on in os.environ.get('TRI_OPPS', 'g,c').split(',')]
    with ProcessPoolExecutor(max_workers=8) as pool:
        res = list(pool.map(one, jobs))
    for tri in (0, 1):
        r = [(a, m) for s2, t2, a, m in res if t2 == tri]
        print(f"tri={tri} own {statistics.mean(a for a, _ in r):7.0f} margin {statistics.mean(m for _, m in r):+8.0f} (n={len(r)})")
    for on in os.environ.get('TRI_OPPS', 'g,c').split(','):
        d = [m for s2, t2, a, m in res if t2 == 1] and [
            statistics.mean(m for s2, t2, a, m, in [] ) ] if False else None
    per = [statistics.mean(m for s2, t2, a, m in res if t2 == 1 and s2 == sd)
           - statistics.mean(m for s2, t2, a, m in res if t2 == 0 and s2 == sd) for sd in seeds]
    sd_ = statistics.stdev(per)
    t = statistics.mean(per) / (sd_ / len(per) ** 0.5) if sd_ else 0
    print(f"配对分差差 {statistics.mean(per):+.0f} (seed t={t:+.2f}) per-seed {[round(x) for x in per]}")


if __name__ == '__main__':
    main()
