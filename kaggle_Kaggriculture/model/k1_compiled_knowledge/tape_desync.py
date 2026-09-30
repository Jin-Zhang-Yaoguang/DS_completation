"""Majkel tape 在 kagsim 失配诊断：tape 当玩家（vs y68g），逐步用 K1 的 _lib_valid 检查 tape 单位动作在当前状态是否合法，
按天报告非法率与非法动作类型；并记录 kagsim 本局商店序列与原局商店序列。"""
import sys, glob, json, importlib.util, os
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
M = '/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model'
IDX = '/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model_data/kaggriculture_episodes_index'


def orig_shops(ep):
    for p in glob.glob(f'{IDX}/*/data/{ep}.json'):
        rep = json.load(open(p))
        names = rep['info']['TeamNames']
        seat = names.index('Majkel1337')
        seq = []
        for st in rep['steps']:
            sh = ((st[seat].get('observation') or {}).get('town') or {}).get('unlocked_shops') or []
            if len(sh) > len(seq):
                seq = list(sh)
        return seq
    return None


def one(job):
    tp, seed = job
    sys.path.insert(0, '/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness')
    sys.path.insert(0, f'{M}/v16_online_fidelity')
    import engine, fidelity
    spec = importlib.util.spec_from_file_location(f'td_{seed}', f'{HERE}/main.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    me = fidelity.make_agent(f'tape:{tp}')
    opp = fidelity.make_agent(f'sub:{M}/v58_mosaic/dist_backup/y68g_main.py')
    g = engine.load_kagsim().Game(seed=seed)
    bad = defaultdict(Counter)
    shops = []
    while not engine._val(g.done):
        o0, o1 = g.observe(0), g.observe(1)
        a0 = me(o0); a1 = opp(o1)
        day = int(o0['day'])
        farm = o0['farms'][0]; tiles = farm['tiles']; bs = len(tiles)
        pv = o0.get('private') or {}
        invs = pv.get('inventories') or []
        seeds = pv.get('seeds') or {}; shed = pv.get('shed') or {}
        poss = [tuple(farm['farmer'])] + [tuple(h) for h in farm.get('hands') or []]
        sset = set(mod._shed_tiles(bs))
        units = [a0.get('farmer') or ['PASS']] + list(a0.get('hands') or [])
        for i, u in enumerate(units):
            if not u or u[0] == 'PASS':
                continue
            bad[day]['n'] += 1
            if i >= len(poss):
                bad[day]['bad'] += 1; bad[day]['NOUNIT'] += 1; continue
            if not mod._lib_valid(list(u), poss[i], tiles, invs[i] if i < len(invs) else {}, seeds, shed, sset, bs):
                bad[day]['bad'] += 1; bad[day][u[0]] += 1
        sh = (o0.get('town') or {}).get('unlocked_shops') or []
        if len(sh) > len(shops):
            shops = list(sh)
        g.step(a0, a1)
    return tp, seed, {d: dict(c) for d, c in bad.items()}, shops, len(farm.get('hands') or [])


def main():
    tps = [t for t in sorted(glob.glob(f'{HERE}/opp_tapes/majkel_*.json')) if '107622326' not in t][:4]
    with ProcessPoolExecutor(max_workers=8) as pool:
        res = list(pool.map(one, [(t, 700001) for t in tps]))
    for tp, seed, bad, shops, nh in res:
        ep = int(tp.split('_')[-1].split('.')[0])
        print(f"\n== {os.path.basename(tp)} seed {seed}")
        print(f"   kagsim 商店 {shops[:5]}")
        print(f"   原局商店   {(orig_shops(ep) or [])[:5]}")
        for d in (0, 1, 2, 3, 5, 7, 10, 14, 20, 27):
            c = bad.get(d) or bad.get(str(d)) or {}
            n = max(1, c.get('n', 0))
            top = sorted(((k, v) for k, v in c.items() if k not in ('n', 'bad')), key=lambda kv: -kv[1])[:4]
            print(f"   d{d + 1:2d} 非法率 {c.get('bad', 0) / n:.2f}（{c.get('bad', 0)}/{c.get('n', 0)}） 类型 {top}")


if __name__ == '__main__':
    main()
