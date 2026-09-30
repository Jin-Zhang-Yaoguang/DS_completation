"""对手强弱探针：K1（当前池，t0 抽方案）vs 各候选对手，4 seed × 双席位，用于分层。"""
import sys, statistics
from concurrent.futures import ProcessPoolExecutor
HERE = '/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/serene-cerf-f00e3b/kaggle_Kaggriculture/model/k1_compiled_knowledge'
M = '/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model'
PK, TP = f'{M}/opponent_pool_v1/packs', f'{M}/opponent_pool_v1/tapes'
OPPS = {
    'v1_baseline': f'sub:{M}/v1_baseline_scheduler/main.py',
    'ult_tape': f'tape:{TP}/ult_normal.json',
    'v35': f'sub:{PK}/v35_main.py', 'v38': f'sub:{PK}/v38_main.py', 'p955': f'sub:{PK}/p955_main.py',
    'v58_rebuild': f'sub:{PK}/v58_rebuild.py', 'v59b': f'sub:{PK}/v59b_approx.py', 'm2448': f'sub:{PK}/m2448_main.py',
    'y60m': f'sub:{PK}/y60m_main.py', 'y63': f'sub:{PK}/y63_main.py', 'y66': f'sub:{PK}/y66_main.py',
    'y67': f'sub:{PK}/y67_main.py', 'y68a': f'sub:{PK}/y68a_main.py', 'y68b': f'sub:{PK}/y68b_main.py',
    'y68c': f'sub:{PK}/y68c_main.py', 'y68e': f'sub:{PK}/y68e_main.py', 'y68f': f'sub:{PK}/y68f_main.py',
    'y68g': f'sub:{M}/v58_mosaic/dist_backup/y68g_main.py',
    'fta0_tape': f'tape:{TP}/fta_slice0.json', 'fta1_tape': f'tape:{TP}/fta_slice1.json',
    'ymg0_tape': f'tape:{TP}/ymg_slice0.json', 'ymg1_tape': f'tape:{TP}/ymg_slice1.json',
    'spataro_tape': f'tape:{TP}/nl_SpaTaro_107289135.json', 'otter_tape': f'tape:{TP}/nl_Otter_Vibe_107377081.json',
}
SEEDS = [720011 + 173 * i for i in range(4)]


def one(job):
    name, seed, seat = job
    sys.path.insert(0, '/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness')
    sys.path.insert(0, f'{M}/v16_online_fidelity')
    import importlib.util, engine, fidelity
    spec = importlib.util.spec_from_file_location(f'pr_{seed}_{seat}_{name}', f'{HERE}/main.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    try:
        opp = fidelity.make_agent(OPPS[name])
        if seat == 0:
            b0, b1 = engine.play(mod.agent, opp, seed=seed); me, op = b0, b1
        else:
            b0, b1 = engine.play(opp, mod.agent, seed=seed); me, op = b1, b0
        return name, me, op, None
    except Exception as e:
        return name, 0, 0, repr(e)[:120]


def main():
    jobs = [(n, s, seat) for n in OPPS for s in SEEDS for seat in (0, 1)]
    with ProcessPoolExecutor(max_workers=8) as pool:
        res = list(pool.map(one, jobs))
    print(f"{'对手':14s} | 胜/8 | 对手金币均值 | K1 金币 | 分差均值 | 错误")
    rows = []
    for n in OPPS:
        r = [x for x in res if x[0] == n]
        err = next((x[3] for x in r if x[3]), '')
        ok = [x for x in r if not x[3]]
        if not ok:
            print(f"{n:14s} | 失败 {err}"); continue
        w = sum(1 for x in ok if x[1] > x[2])
        rows.append((statistics.mean(x[1] - x[2] for x in ok), n, w, len(ok), statistics.mean(x[2] for x in ok), statistics.mean(x[1] for x in ok), err))
    for mg, n, w, k, op, me, err in sorted(rows, reverse=True):
        print(f"{n:14s} | {w}/{k} | {op:9.0f} | {me:7.0f} | {mg:+8.0f} | {err}")


if __name__ == '__main__':
    main()
