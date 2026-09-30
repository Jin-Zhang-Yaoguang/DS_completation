"""Majkel tape vs K1 探针：每条 tape 4 seed × 双席位。"""
import sys, statistics, glob, os
from concurrent.futures import ProcessPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
M = '/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model'
SEEDS = [720011 + 173 * i for i in range(4)]


def one(job):
    tp, seed, seat = job
    sys.path.insert(0, '/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness')
    sys.path.insert(0, f'{M}/v16_online_fidelity')
    import importlib.util, engine, fidelity
    spec = importlib.util.spec_from_file_location(f'pt_{seed}_{seat}', f'{HERE}/main.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    opp = fidelity.make_agent(f'tape:{tp}')
    if seat == 0:
        b0, b1 = engine.play(mod.agent, opp, seed=seed); return tp, b0, b1
    b0, b1 = engine.play(opp, mod.agent, seed=seed); return tp, b1, b0


def main():
    tps = sorted(glob.glob(f'{HERE}/opp_tapes/majkel_*.json'))
    jobs = [(t, s, seat) for t in tps for s in SEEDS for seat in (0, 1)]
    with ProcessPoolExecutor(max_workers=8) as pool:
        res = list(pool.map(one, jobs))
    for t in tps:
        r = [x for x in res if x[0] == t]
        print(f"{os.path.basename(t):24s} | 胜 {sum(1 for x in r if x[1] > x[2])}/8 | 对手 {statistics.mean(x[2] for x in r):7.0f} | K1 {statistics.mean(x[1] for x in r):7.0f} | 分差 {statistics.mean(x[1]-x[2] for x in r):+8.0f}")


if __name__ == '__main__':
    main()
