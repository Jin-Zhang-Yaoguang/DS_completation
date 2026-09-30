"""面积目标为何兑现不了：加大面积配置（小麦+12 草莓+10）下，逐日 目标/已种/空地/当天种植/种子/现金/种植限速命中/空闲单位，
并统计每个未兑现缺口日的阻塞原因（缺种子/缺现金/限速/无空地/无空闲单位）。vs v2_survival_guard 与 y68g，各 2 seed。
"""
import sys, importlib.util, json, statistics, os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
M = '/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model'
OPPS = {'y68g': f'sub:{M}/v58_mosaic/dist_backup/y68g_main.py', 'v2': f'sub:{M}/v2_survival_guard/main.py'}
MOVES = {"NORTH", "SOUTH", "EAST", "WEST"}
IDLE = MOVES | {"PASS", "PICKUP", "DROP"}
BIG = {'wheat_peak': 12, 'wheat_base': 4, 'straw_peak': 10}


def one(job):
    oname, seed, big = job
    sys.path.insert(0, '/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness')
    sys.path.insert(0, f'{M}/v16_online_fidelity')
    sys.path.insert(0, HERE)
    import engine, fidelity
    from schedule_gen import gen_tables, DEFAULTS
    best = max(json.load(open(f'{HERE}/best_iter_ga1.json'))['candidates'], key=lambda c: c['hold_margin'])
    params = {**DEFAULTS, **best['params']}
    if big:
        for k, v in BIG.items():
            params[k] += v
    spec = importlib.util.spec_from_file_location(f'pb_{seed}_{oname}_{big}', f'{HERE}/main.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    base_tu = json.load(open(f'{HERE}/knowledge.json'))['tuning']
    ov = gen_tables(params); te = ov.pop('tuning_extra')
    ov['tuning'] = {**base_tu, 'fert_specialist': False, 't0_pool_select': False, **te}
    mod.KN_OVERRIDE = ov
    opp = fidelity.make_agent(OPPS[oname])
    g = engine.load_kagsim().Game(seed=seed)
    days = {}
    plants_today = Counter(); idle_today = Counter()
    while not engine._val(g.done):
        o0, o1 = g.observe(0), g.observe(1)
        a0 = mod.agent(o0); a1 = opp(o1)
        day, hour = int(o0["day"]), int(o0["hour"])
        units = [a0.get("farmer") or ["PASS"]] + list(a0.get("hands") or [])
        plants_today[day] += sum(1 for u in units if u and u[0] == "PLANT")
        if 8 <= hour <= 18:
            idle_today[day] += sum(1 for u in units if (u or ["PASS"])[0] in MOVES | {"PASS"})
        if hour == 12:
            st = mod._STATE.get(0)
            f = o0["farms"][0]; bs = len(f["tiles"]); sheds = set(mod._shed_tiles(bs))
            empty = sum(1 for y, r in enumerate(f["tiles"]) for x, t in enumerate(r) if t is None and (x, y) not in sheds)
            tg = st.get("crop_targets", {}); pl = st.get("planted", {})
            gap = {c: tg.get(c, 0) - pl.get(c, 0) for c in tg if tg.get(c, 0) - pl.get(c, 0) > 0}
            roles = st.get("roles", {})
            role_empty = Counter(r for p, r in roles.items() if f["tiles"][p[1]][p[0]] is None and r != "ANIMAL")
            seeds = dict((o0.get("private") or {}).get("seeds") or {})
            days[day] = {"target": sum(tg.values()), "planted": sum(pl.values()), "empty": empty, "gap": gap,
                         "role_empty": dict(role_empty), "seeds": seeds, "money": round(f["money"]),
                         "cap": st["kn"].get("tuning", {}).get("plant_per_day_cap"), "planted_today_so_far": st.get("planted_today", 0)}
        g.step(a0, a1)
    for d in days:
        days[d]["plants_day"] = plants_today[d]
        days[d]["idle_8_18"] = idle_today[d]
    return oname, seed, big, days, o0["farms"][0]["money"]


def main():
    jobs = [(on, s, big) for on in OPPS for s in (790051, 790297) for big in (False, True)]
    with ProcessPoolExecutor(max_workers=8) as pool:
        res = list(pool.map(one, jobs))
    json.dump([[r[0], r[1], r[2], {str(k): v for k, v in r[3].items()}, r[4]] for r in res],
              open(f'{HERE}/plant_block_diag_result.json', 'w'))
    for oname, seed, big, days, money in res:
        if seed != 790051:
            continue
        print(f"\n== vs {oname} seed {seed} {'加大面积' if big else '基准'}  终局 {money:.0f}")
        for d in range(4, 27, 2):
            r = days.get(d)
            if not r:
                continue
            print(f"  d{d:2d} 目标{r['target']:3d} 已种{r['planted']:3d} 空地{r['empty']:3d} 缺口{r['gap']} 空格角色{r['role_empty']} "
                  f"种子{ {k: v for k, v in r['seeds'].items() if v} } 现金{r['money']:6d} 当天种{r['plants_day']:2d} 限速{r['cap']} 白天闲置步{r['idle_8_18']}")


if __name__ == '__main__':
    main()
