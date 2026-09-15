"""路线内核改变了「做什么」：基准 vs 路线（重规划8 前看1），逐动作计数、生存事件、双方卖出量。4 seed × y68g/v2 × 双席位。"""
import sys, importlib.util, json, statistics, os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
M = '/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model'
OPPS = [f'sub:{M}/v58_mosaic/dist_backup/y68g_main.py', f'sub:{M}/v2_survival_guard/main.py']
SEEDS = [800057 + 241 * i for i in range(4)]
CFG = {'base': {}, 'route': {'route_on': 1, 'route_replan_h': 8, 'route_look': 1}}


def one(job):
    name, seed, opp_spec, seat = job
    sys.path.insert(0, '/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness')
    sys.path.insert(0, f'{M}/v16_online_fidelity')
    sys.path.insert(0, HERE)
    import engine, fidelity
    from schedule_gen import gen_tables, DEFAULTS
    best = max(json.load(open(f'{HERE}/best_iter_ga4.json'))['candidates'], key=lambda c: c['hold_margin'])
    params = {**DEFAULTS, **best['params'], **CFG[name]}
    spec = importlib.util.spec_from_file_location(f'rod_{seed}_{seat}_{name}_{abs(hash(opp_spec))}', f'{HERE}/main.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    base_tu = json.load(open(f'{HERE}/knowledge.json'))['tuning']
    ov = gen_tables(params); te = ov.pop('tuning_extra')
    ov['tuning'] = {**base_tu, 'fert_specialist': False, 't0_pool_select': False, **te}
    mod.KN_OVERRIDE = ov
    opp = fidelity.make_agent(opp_spec)
    agents = [mod.agent, opp] if seat == 0 else [opp, mod.agent]
    g = engine.load_kagsim().Game(seed=seed)
    c = Counter()
    while not engine._val(g.done):
        o = [g.observe(0), g.observe(1)]
        a = [agents[0](o[0]), agents[1](o[1])]
        hour = int(o[0]["hour"])
        for s in (0, 1):
            who = "k1" if s == seat else "op"
            for od in a[s].get("market") or []:
                if od and od[0] == "SELL" and len(od) >= 3:
                    c[f"{who}_sell_{od[1]}"] += int(od[2] or 0)
        for u in [a[seat].get("farmer") or ["PASS"]] + list(a[seat].get("hands") or []):
            c["op_" + (u or ["PASS"])[0]] += 1
        if hour == 21:
            f = o[0]["farms"][seat]
            for row in f["tiles"]:
                for t in row:
                    if isinstance(t, dict):
                        if t.get("animal"):
                            c["an21"] += 1
                            c["unfed21"] += 0 if t.get("fed_today") else 1
                            c["uncared21"] += 0 if t.get("cared_today") else 1
                        elif t.get("kind") == "PLANT":
                            c["pl21"] += 1
                            c["unwat21"] += 0 if t.get("watered_today") else 1
        g.step(a[0], a[1])
    mo = [o[0]["farms"][0]["money"], o[0]["farms"][1]["money"]]
    c["own"] = mo[seat]; c["opp"] = mo[1 - seat]
    return name, seed, opp_spec, seat, dict(c)


def main():
    jobs = [(n, s, o, seat) for n in CFG for s in SEEDS for o in OPPS for seat in (0, 1)]
    with ProcessPoolExecutor(max_workers=8) as pool:
        res = list(pool.map(one, jobs))
    agg = {n: Counter() for n in CFG}
    for n, s, o, seat, c in res:
        agg[n].update(c)
    k = len(SEEDS) * len(OPPS) * 2
    keys = sorted(set(agg['base']) | set(agg['route']))
    print(f"每局均值（{k} 局/配置）")
    for key in keys:
        b, r = agg['base'][key] / k, agg['route'][key] / k
        if max(abs(b), abs(r)) >= 1:
            print(f"  {key:26s} 基准 {b:9.1f} | 路线 {r:9.1f} | 差 {r - b:+9.1f}")
    for n in CFG:
        a = agg[n]
        print(f"{n}: 21点 未喂 {a['unfed21'] / max(1, a['an21']):.2%} 未照料 {a['uncared21'] / max(1, a['an21']):.2%} 未浇 {a['unwat21'] / max(1, a['pl21']):.2%}")


if __name__ == '__main__':
    main()
