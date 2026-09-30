"""连贯单局 Majkel tape 在 kagsim 的上限：tape 当玩家 vs y68g，2 seed × 双席位；另测 tape 首日 3 步后与原局动作是否仍合法（地形/随机是否失配）。"""
import sys, glob, json, statistics
from concurrent.futures import ProcessPoolExecutor
M = '/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model'


def one(job):
    tp, seed, seat = job
    sys.path.insert(0, '/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness')
    sys.path.insert(0, f'{M}/v16_online_fidelity')
    import engine, fidelity
    me = fidelity.make_agent(f'tape:{tp}')
    opp = fidelity.make_agent(f'sub:{M}/v58_mosaic/dist_backup/y68g_main.py')
    if seat == 0:
        b0, b1 = engine.play(me, opp, seed=seed)
        return tp, b0, b0 - b1
    b0, b1 = engine.play(opp, me, seed=seed)
    return tp, b1, b1 - b0


def main():
    tps = [t for t in sorted(glob.glob('opp_tapes/majkel_*.json')) if '107622326' not in t]
    jobs = [(t, s, seat) for t in tps for s in (700001, 700098) for seat in (0, 1)]
    with ProcessPoolExecutor(max_workers=8) as pool:
        res = list(pool.map(one, jobs))
    for t in tps:
        r = [x for x in res if x[0] == t]
        orig = json.load(open(t)).get('final')
        print(f"{t.split('/')[-1]:24s} 线上终局 {orig} | kagsim 自身 {statistics.mean(x[1] for x in r):7.0f} "
              f"分差 {statistics.mean(x[2] for x in r):+8.0f} 胜 {sum(1 for x in r if x[2] > 0)}/4")


if __name__ == '__main__':
    main()
