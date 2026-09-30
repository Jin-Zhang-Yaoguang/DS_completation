"""回放动作真实生效诊断：Majkel 默认整局 tape 当玩家（vs y68g / v2），逐步比较执行前后状态判断每个单位动作是否真正生效，
并与两种判断器预测对照：V0 = 现 _lib_valid（上一步观测），V1 = 市场感知（先把本步 BUY/HIRE 计入种子/仓库/单位数）。
按天、按动作类型报告：真实无效率、V0/V1 的误判（有效判无效 / 无效判有效）。"""
import sys, json, gzip, importlib.util, os
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
M = '/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model'
MOVES = {"NORTH": (0, -1), "SOUTH": (0, 1), "WEST": (-1, 0), "EAST": (1, 0)}


def effective(op, i, o0, o1, seat):
    f0, f1 = o0['farms'][seat], o1['farms'][seat]
    p0 = ([f0['farmer']] + list(f0.get('hands') or []))
    p1 = ([f1['farmer']] + list(f1.get('hands') or []))
    if i >= len(p0):
        return False
    x, y = p0[i]
    k = op[0]
    if o1['day'] != o0['day']:
        return None  # 跨天复位，不判
    if k in MOVES:
        return i < len(p1) and tuple(p1[i]) != tuple(p0[i])
    t0 = f0['tiles'][y][x]; t1 = f1['tiles'][y][x]
    inv0 = ((o0.get('private') or {}).get('inventories') or [{}] * 20)
    inv1 = ((o1.get('private') or {}).get('inventories') or [{}] * 20)
    i0 = inv0[i] if i < len(inv0) else {}
    i1 = inv1[i] if i < len(inv1) else {}
    if k == 'WATER':
        return isinstance(t1, dict) and t1.get('watered_today') and not (isinstance(t0, dict) and t0.get('watered_today'))
    if k in ('HARVEST', 'COLLECT_FERTILIZER', 'PICKUP'):
        return sum(i1.values()) > sum(i0.values())
    if k in ('DROP', 'PLACE'):
        return sum(i1.values()) < sum(i0.values()) or t1 != t0
    if k == 'FEED':
        return isinstance(t1, dict) and t1.get('fed_today') and not (isinstance(t0, dict) and t0.get('fed_today'))
    if k == 'CARE':
        return isinstance(t1, dict) and t1.get('cared_today') and not (isinstance(t0, dict) and t0.get('cared_today'))
    if k in ('PLANT', 'BUILD_PASTURE', 'BUILD_COOP', 'DIG', 'FERTILIZE'):
        return t1 != t0
    return None


def v1_valid(mod, op, pos, tiles, inv, seeds, shed, sset, bs, market):
    seeds2, shed2 = dict(seeds), dict(shed)
    for od in market or []:
        if od and od[0] == 'BUY_SEED' and len(od) >= 3:
            seeds2[od[1]] = seeds2.get(od[1], 0) + int(od[2])
        elif od and od[0] in ('BUY_PRODUCT', 'BUY_ANIMAL') and len(od) >= 2:
            shed2[od[1]] = shed2.get(od[1], 0) + (int(od[2]) if len(od) >= 3 else 1)
    k = op[0]
    if k in MOVES:
        dx, dy = MOVES[k]
        return 0 <= pos[0] + dx < bs and 0 <= pos[1] + dy < bs
    if k in ('BUILD_PASTURE', 'BUILD_COOP'):
        t = tiles[pos[1]][pos[0]]
        return t is None or (isinstance(t, dict) and t.get('kind') == 'WEED')
    if k == 'PLACE':
        return True
    if k == 'PICKUP':
        return pos in sset and len(op) >= 2 and shed2.get(op[1], 0) > 0
    if k == 'FEED':
        t = tiles[pos[1]][pos[0]]
        return isinstance(t, dict) and 'animal' in t and not t.get('fed_today')
    return mod._lib_valid(op, pos, tiles, inv, seeds2, shed2, sset, bs)


def one(job):
    oname, seed = job
    sys.path.insert(0, '/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness')
    sys.path.insert(0, f'{M}/v16_online_fidelity')
    import engine, fidelity
    spec = importlib.util.spec_from_file_location(f'nt_{seed}_{oname}', f'{HERE}/main.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    lib = json.loads(gzip.open(f'{HERE}/route_eps.json.gz').read().decode())
    me = fidelity.tape_agent(lib['eps'][lib['default']])
    opp = fidelity.make_agent({'y68g': f'sub:{M}/v58_mosaic/dist_backup/y68g_main.py', 'v2': f'sub:{M}/v2_survival_guard/main.py'}[oname])
    g = engine.load_kagsim().Game(seed=seed)
    c = defaultdict(Counter)
    o0 = g.observe(0)
    while not engine._val(g.done):
        o1b = g.observe(1)
        a0 = me(o0); a1 = opp(o1b)
        g.step(a0, a1)
        if engine._val(g.done):
            break
        on = g.observe(0)
        f = o0['farms'][0]; tiles = f['tiles']; bs = len(tiles); sset = set(mod._shed_tiles(bs))
        pv = o0.get('private') or {}
        invs = pv.get('inventories') or []
        poss = [tuple(f['farmer'])] + [tuple(h) for h in f.get('hands') or []]
        day = int(o0['day'])
        for i, u in enumerate([a0.get('farmer') or ['PASS']] + list(a0.get('hands') or [])):
            if not u or u[0] in ('PASS',):
                continue
            eff = effective(list(u), i, o0, on, 0)
            if eff is None:
                continue
            key = (day // 5, u[0])
            c[key]['n'] += 1
            c[key]['noop'] += int(not eff)
            if i < len(poss):
                v0 = mod._lib_valid(list(u), poss[i], tiles, invs[i] if i < len(invs) else {}, pv.get('seeds') or {}, pv.get('shed') or {}, sset, bs)
                v1 = v1_valid(mod, list(u), poss[i], tiles, invs[i] if i < len(invs) else {}, pv.get('seeds') or {}, pv.get('shed') or {}, sset, bs, a0.get('market'))
            else:
                v0 = v1 = False
            c[key]['v0_fn'] += int(eff and not v0); c[key]['v0_fp'] += int((not eff) and v0)
            c[key]['v1_fn'] += int(eff and not v1); c[key]['v1_fp'] += int((not eff) and v1)
        o0 = on
    return oname, seed, {f"{k[0]}|{k[1]}": dict(v) for k, v in c.items()}


def main():
    jobs = [(on, s) for on in ('y68g', 'v2') for s in (700001, 700098)]
    with ProcessPoolExecutor(max_workers=4) as pool:
        res = list(pool.map(one, jobs))
    tot = defaultdict(Counter)
    for _, _, c in res:
        for k, v in c.items():
            tot[k].update(v)
    print("键=5天段|动作：n 真实无效率 | V0 有效判无效 / 无效判有效 | V1 同")
    for k in sorted(tot, key=lambda s: (int(s.split('|')[0]), s)):
        v = tot[k]
        if v['n'] < 20:
            continue
        n = v['n']
        print(f"  d{int(k.split('|')[0]) * 5:2d}+ {k.split('|')[1]:20s} n={n:5d} 无效 {v['noop'] / n:.2f} | V0 {v['v0_fn'] / n:.2f}/{v['v0_fp'] / n:.2f} | V1 {v['v1_fn'] / n:.2f}/{v['v1_fp'] / n:.2f}")


if __name__ == '__main__':
    main()
