"""派活结构对照：K1 vs v2_survival_guard 同局对打（双席位），逐单位统计。
指标：每次工作前的移动步数分布、同格连做率、单位平均服务半径（离仓距离）、单位专业化（每单位工作类型熵）、
PASS 时刻分布、d12/d20 布局（作物/动物格到仓库距离）、每格被访问次数。
用法: /opt/anaconda3/bin/python3 dispatch_diff.py [seeds]
"""
import sys, json, math, statistics, os
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
M = '/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model'
OPP = f'{M}/v2_survival_guard/main.py'
NSEED = int(sys.argv[1]) if len(sys.argv) > 1 else 4
SEEDS = [750029 + 197 * i for i in range(NSEED)]
MOVES = {"NORTH", "SOUTH", "EAST", "WEST"}


def shed_center(bs):
    c = bs // 2
    return (c - 0.5, c - 0.5)


def agg_side(obs_seq, act_seq, seat):
    st = Counter()
    since = defaultdict(int)          # 单位自上次工作以来的移动步
    last_work = {}
    pre_move = Counter()              # 工作前移动步数分布
    spec = defaultdict(Counter)       # 单位 → 工作类型
    radius = []
    pass_hour = Counter()
    visits = Counter()
    for obs, act in zip(obs_seq, act_seq):
        farm = obs["farms"][seat]
        bs = len(farm["tiles"])
        cx, cy = shed_center(bs)
        poss = [tuple(farm["farmer"])] + [tuple(h) for h in (farm.get("hands") or [])]
        units = [act.get("farmer") or ["PASS"]] + list(act.get("hands") or [])
        hour = int(obs.get("hour", 0))
        for i, u in enumerate(units):
            op = (u or ["PASS"])[0]
            if op in MOVES:
                st["move"] += 1
                since[i] += 1
            elif op == "PASS":
                st["pass"] += 1
                pass_hour[hour] += 1
            elif op in ("PICKUP", "DROP"):
                st["carry"] += 1
            else:
                st["work"] += 1
                pre_move[min(since[i], 10)] += 1
                p = poss[i] if i < len(poss) else None
                if p:
                    if last_work.get(i) == p:
                        st["same_tile"] += 1
                    last_work[i] = p
                    radius.append(abs(p[0] - cx) + abs(p[1] - cy))
                    visits[p] += 1
                spec[i][op] += 1
                since[i] = 0
    ent = []
    for i, c in spec.items():
        tot = sum(c.values())
        if tot > 50:
            ent.append(-sum(v / tot * math.log2(v / tot) for v in c.values()))
    return {"st": dict(st), "pre_move": dict(pre_move), "radius": statistics.mean(radius) if radius else 0,
            "entropy": statistics.mean(ent) if ent else 0, "pass_hour": dict(pass_hour),
            "n_units_final": len(spec), "visit_tiles": len(visits)}


def layout(obs, seat):
    farm = obs["farms"][seat]
    bs = len(farm["tiles"])
    cx, cy = shed_center(bs)
    d = defaultdict(list)
    grid = []
    for y, row in enumerate(farm["tiles"]):
        line = []
        for x, t in enumerate(row):
            if t == "LOCKED":
                line.append("###"); continue
            if isinstance(t, dict):
                k = t.get("crop") or t.get("animal") or t.get("kind")
                d[k].append(abs(x - cx) + abs(y - cy))
                line.append(str(k)[:3])
            else:
                line.append(" . ")
        grid.append(" ".join(line))
    return {k: (len(v), round(statistics.mean(v), 1)) for k, v in d.items()}, grid


def one(job):
    seed, k1_seat = job
    sys.path.insert(0, '/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness')
    sys.path.insert(0, f'{M}/v16_online_fidelity')
    import importlib.util, engine, fidelity
    spec = importlib.util.spec_from_file_location(f'dd_{seed}_{k1_seat}', f'{HERE}/main.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    opp = fidelity.make_agent(f'sub:{OPP}')
    agents = [mod.agent, opp] if k1_seat == 0 else [opp, mod.agent]
    g = engine.load_kagsim().Game(seed=seed)
    obs_seq, act_seq = [[], []], [[], []]
    lay = {}
    while not engine._val(g.done):
        o = [g.observe(0), g.observe(1)]
        a = [agents[0](o[0]), agents[1](o[1])]
        for s in (0, 1):
            obs_seq[s].append(o[s]); act_seq[s].append(a[s])
        if int(o[0]["day"]) in (12, 20) and int(o[0]["hour"]) == 12:
            lay[int(o[0]["day"])] = [layout(o[0], 0), layout(o[0], 1)]
        g.step(a[0], a[1])
    money = [o[0]["farms"][0]["money"], o[0]["farms"][1]["money"]]
    side = [agg_side(obs_seq[s], act_seq[s], s) for s in (0, 1)]
    op_seat = 1 - k1_seat
    return {"seed": seed, "k1": side[k1_seat], "v2": side[op_seat], "money_k1": money[k1_seat], "money_v2": money[op_seat],
            "lay_k1": {d: v[k1_seat] for d, v in lay.items()}, "lay_v2": {d: v[op_seat] for d, v in lay.items()}}


def main():
    jobs = [(s, seat) for s in SEEDS for seat in (0, 1)]
    with ProcessPoolExecutor(max_workers=8) as pool:
        res = list(pool.map(one, jobs))
    json.dump(res, open(f'{HERE}/dispatch_diff_result.json', 'w'), default=str)
    med = lambda f, who: statistics.median(f(r[who]) for r in res)
    print(f"{len(res)} 局  终局金币 K1 {statistics.median(r['money_k1'] for r in res):.0f} / v2 {statistics.median(r['money_v2'] for r in res):.0f}")
    rows = [("工作步", lambda s: s["st"].get("work", 0)), ("移动步", lambda s: s["st"].get("move", 0)),
            ("PASS 步", lambda s: s["st"].get("pass", 0)), ("搬运步", lambda s: s["st"].get("carry", 0)),
            ("同格连做", lambda s: s["st"].get("same_tile", 0) / max(1, s["st"].get("work", 1))),
            ("移动/工作", lambda s: s["st"].get("move", 0) / max(1, s["st"].get("work", 1))),
            ("工作格离仓距离", lambda s: s["radius"]), ("单位工作类型熵", lambda s: s["entropy"]),
            ("被服务过的格数", lambda s: s["visit_tiles"])]
    for name, f in rows:
        a, b = med(f, "k1"), med(f, "v2")
        fmt = "{:.2f}" if max(abs(a), abs(b)) < 10 else "{:.0f}"
        print(f"  {name:14s} K1 {fmt.format(a):>8} | v2 {fmt.format(b):>8}")
    print("  工作前移动步数分布（占比）:")
    for who in ("k1", "v2"):
        tot = Counter()
        for r in res:
            tot.update({int(k): v for k, v in r[who]["pre_move"].items()})
        s = sum(tot.values())
        print(f"    {who}: " + " ".join(f"{k}:{tot[k] / s:.2f}" for k in range(11)))
    print("  PASS 按小时（v2 前 8 个高峰）:")
    for who in ("k1", "v2"):
        tot = Counter()
        for r in res:
            tot.update({int(k): v for k, v in r[who]["pass_hour"].items()})
        print(f"    {who}: {sorted(tot.items(), key=lambda kv: -kv[1])[:8]}")
    r0 = res[0]
    for d in ("12", "20"):
        for who in ("lay_k1", "lay_v2"):
            lay = r0[who].get(d) or r0[who].get(int(d))
            if lay:
                print(f"\n  seed {r0['seed']} d{d} {who} 各类格(数量, 平均离仓距离): {lay[0]}")
                print("   " + "\n   ".join(lay[1]))


if __name__ == '__main__':
    main()
