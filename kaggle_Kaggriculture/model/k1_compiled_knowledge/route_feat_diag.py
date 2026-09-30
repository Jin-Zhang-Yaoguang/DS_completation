"""局面路由特征诊断（不用对手身份）：全部分层对手 × 2 seed × 双席位；同局配对跑 K1 基准 与 回放（按商店切换），
回放局记录 step 72 时的通用可观测特征：自身 金币/作物/动物/工人/建筑、对手 金币/作物/动物/工人、商店序列、回放工作动作有效率、所跟局号；
输出 route_feat_rows.json（每行 = 特征 + 回放相对 K1 的分差变化）。"""
import sys, json, gzip, importlib.util, os, statistics
from concurrent.futures import ProcessPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
TJ = json.load(open(f'{HERE}/opp_tiers.json'))
FMT = lambda x: x.replace('{M}', TJ['M']).replace('{K1}', TJ['K1'])
OPPS = [(tier, FMT(o)) for tier, t in TJ['tiers'].items() for o in t['opps']]
M = TJ['M']
SEEDS = [820063 + 257 * i for i in range(2)]


def farm_sig(f):
    c = {"money": int(f.get("money", 0)), "hands": len(f.get("hands") or []), "crops": 0, "animals": 0, "structs": 0}
    for row in f.get("tiles") or []:
        for t in row:
            if isinstance(t, dict):
                if t.get("kind") == "PLANT":
                    c["crops"] += 1
                elif t.get("animal"):
                    c["animals"] += 1
                elif t.get("kind") in ("PASTURE", "COOP"):
                    c["structs"] += 1
    return c


def one(job):
    name, tier, spec_o, seed, seat = job
    sys.path.insert(0, '/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness')
    sys.path.insert(0, f'{M}/v16_online_fidelity')
    sys.path.insert(0, HERE)
    import engine, fidelity
    from schedule_gen import gen_tables, DEFAULTS
    best = max(json.load(open(f'{HERE}/best_iter_ga4.json'))['candidates'], key=lambda c: c['hold_margin'])
    extra = {} if name == 'k1' else {'eps_on': 1, 'eps_gate': 2}
    params = {**DEFAULTS, **best['params'], **extra}
    spec = importlib.util.spec_from_file_location(f'rf_{seed}_{seat}_{name}_{abs(hash(spec_o))}', f'{HERE}/main.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    base_tu = json.load(open(f'{HERE}/knowledge.json'))['tuning']
    ov = gen_tables(params); te = ov.pop('tuning_extra')
    ov['tuning'] = {**base_tu, 'fert_specialist': False, 't0_pool_select': False, **te}
    mod.KN_OVERRIDE = ov
    opp = fidelity.make_agent(spec_o)
    agents = [mod.agent, opp] if seat == 0 else [opp, mod.agent]
    g = engine.load_kagsim().Game(seed=seed)
    feat = {}
    valid = {"n": 0, "ok": 0}
    t = 0
    while not engine._val(g.done):
        o = [g.observe(0), g.observe(1)]
        a = [agents[0](o[0]), agents[1](o[1])]
        if name != 'k1' and t < 72:
            ob = o[seat]; f = ob['farms'][seat]; tiles = f['tiles']
            pv = ob.get('private') or {}
            poss = [tuple(f['farmer'])] + [tuple(h) for h in f.get('hands') or []]
            units = [a[seat].get('farmer') or ['PASS']] + list(a[seat].get('hands') or [])
            for i, u in enumerate(units):
                if i < len(poss) and u and u[0] in mod._EPS_WORK:
                    valid["n"] += 1
                    valid["ok"] += int(mod._eps_work_valid(list(u), poss[i], tiles, (pv.get('inventories') or [{}] * 30)[i],
                                                           pv.get('seeds') or {}, pv.get('shed') or {}, a[seat].get('market')))
        if t in (23, 47, 71, 72):
            ob = o[seat]
            fs = ob['farms']
            feat[f"me{t}"] = farm_sig(fs[seat]); feat[f"op{t}"] = farm_sig(fs[1 - seat])
            feat[f"shops{t}"] = list((ob.get('town') or {}).get('unlocked_shops') or [])
        g.step(a[0], a[1])
        t += 1
    mo = [o[0]['farms'][0]['money'], o[0]['farms'][1]['money']]
    st = mod._STATE.get(seat, {})
    feat["valid72"] = valid["ok"] / max(1, valid["n"])
    feat["ep"] = st.get("eps_ep")
    return name, tier, spec_o, seed, seat, mo[seat] - mo[1 - seat], feat


def main():
    jobs = [(n, tier, o, s, seat) for tier, o in OPPS for s in SEEDS for seat in (0, 1) for n in ('k1', 'eps')]
    with ProcessPoolExecutor(max_workers=8) as pool:
        res = list(pool.map(one, jobs))
    lib = json.loads(gzip.open(f'{HERE}/route_eps.json.gz').read().decode())
    base = {(r[2], r[3], r[4]): r[5] for r in res if r[0] == 'k1'}
    rows = []
    for r in res:
        if r[0] != 'eps':
            continue
        f = r[6]
        rec = (lib.get('snap', {}).get(str(f.get('ep'))) or {})
        rows.append({"tier": r[1], "opp": r[2].split('/')[-2] if r[2].endswith('main.py') else r[2].split('/')[-1],
                     "seed": r[3], "seat": r[4], "delta": r[5] - base[(r[2], r[3], r[4])], "eps_margin": r[5],
                     "k1_margin": base[(r[2], r[3], r[4])], "feat": f, "rec": rec})
    json.dump(rows, open(f'{HERE}/route_feat_rows.json', 'w'))
    print(f"{len(rows)} 行；回放相对 K1 分差变化均值 {statistics.mean(x['delta'] for x in rows):+.0f}，为正占比 {sum(1 for x in rows if x['delta'] > 0) / len(rows):.2f}")


if __name__ == '__main__':
    main()
