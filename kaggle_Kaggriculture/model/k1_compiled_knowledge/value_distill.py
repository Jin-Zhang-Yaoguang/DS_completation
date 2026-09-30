"""单位面积产值蒸馏：Majkel vs K1 按作物/产品拆收入、面积·天、施肥覆盖、缺水、卖价与卖出时段。

用法: /opt/anaconda3/bin/python3 value_distill.py [n_majkel] [n_k1]
"""
import json
import statistics
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor

from scale_distill import HERE, IDX, V71, MOS  # noqa: F401

CROPS = ("WHEAT", "MELON", "STRAWBERRY", "CARROT", "TOMATO")
PRODS = CROPS + ("MILK", "EGG", "WOOL")


def game_stats(obs_seq, act_seq, seat):
    s = {"rev": Counter(), "qty": Counter(), "tile_days": Counter(), "fert_days": Counter(),
         "dry_days": Counter(), "harvest": 0, "plant": Counter(), "fertilize": 0,
         "sell_hour": Counter(), "h_crop": Counter(), "h_units": Counter(), "standing": Counter(), "feed": 0, "buy_prod": Counter(), "sell_day_rev": Counter(), "prices_seen": {p: [] for p in PRODS}}
    for obs, act in zip(obs_seq, act_seq):
        if not obs or not act:
            continue
        day, hour = int(obs.get("day", 0)), int(obs.get("hour", 0))
        prices = (obs.get("market") or {}).get("prices") or {}
        farm0 = (obs.get("farms") or [{}, {}])[seat]
        tiles0 = farm0.get("tiles") or []
        poss = [farm0.get("farmer")] + list(farm0.get("hands") or [])
        for i, u in enumerate([act.get("farmer") or ["PASS"]] + list(act.get("hands") or [])):
            if not u:
                continue
            if u[0] == "FEED":
                s["feed"] += 1
            if u[0] == "HARVEST":
                s["harvest"] += 1
                if i < len(poss) and poss[i]:
                    x, y = poss[i]
                    try:
                        t = tiles0[y][x]
                    except (IndexError, TypeError):
                        t = None
                    if isinstance(t, dict) and t.get("kind") == "PLANT":
                        s["h_crop"][t.get("crop")] += 1
                        s["h_units"][t.get("crop")] += t.get("yield_units") or 0
            elif u[0] == "PLANT" and len(u) > 1:
                s["plant"][u[1]] += 1
            elif u[0] == "FERTILIZE":
                s["fertilize"] += 1
        for o in act.get("market") or []:
            if o and o[0] == "BUY_PRODUCT" and len(o) >= 3:
                s["buy_prod"][o[1]] += int(o[2] or 0)
            if o and o[0] == "SELL" and len(o) >= 3:
                q = int(o[2] or 0)
                v = q * prices.get(o[1], 0)
                s["rev"][o[1]] += v
                s["qty"][o[1]] += q
                s["sell_hour"][hour] += v
                s["sell_day_rev"][day // 5] += v
        if hour == 12:
            for p in PRODS:
                if p in prices:
                    s["prices_seen"][p].append(prices[p])
            farm = (obs.get("farms") or [{}, {}])[seat]
            for row in farm.get("tiles") or []:
                for t in row:
                    if isinstance(t, dict) and t.get("kind") == "PLANT":
                        c = t.get("crop")
                        s["tile_days"][c] += 1
                        s["standing"][c] += t.get("yield_units") or 0
                        if (t.get("fertilized_until_day") or -1) >= day:
                            s["fert_days"][c] += 1
                        if (t.get("consecutive_unwatered") or 0) > 0:
                            s["dry_days"][c] += 1
    for p in PRODS:
        pl = s["prices_seen"][p]
        s["prices_seen"][p] = statistics.mean(pl) if pl else 0
    return s


def majkel_one(line):
    g = json.loads(line)
    fp = IDX / g["date"] / "data" / f"{g['ep']}.json"
    if not fp.exists():
        return None
    rep = json.loads(fp.read_text())
    names = (rep.get("info") or {}).get("TeamNames") or []
    if "Majkel1337" not in names:
        return None
    seat = names.index("Majkel1337")
    steps = rep.get("steps") or []
    return game_stats([steps[t - 1][seat].get("observation") for t in range(1, len(steps))],
                      [steps[t][seat].get("action") for t in range(1, len(steps))], seat)


def k1_one(seed):
    sys.path.insert(0, "/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness")
    sys.path.insert(0, "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v16_online_fidelity")
    import importlib.util
    import engine
    import fidelity
    spec = importlib.util.spec_from_file_location(f"k1_vd_{seed}", HERE / "main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    opp = fidelity.make_agent(f"sub:{MOS}/y68g_main.py")
    g = engine.load_kagsim().Game(seed=seed)
    obs_seq, act_seq = [], []
    while not (g.done() if callable(g.done) else g.done):
        o0, o1 = g.observe(0), g.observe(1)
        a0 = mod.agent(o0)
        try:
            a1 = opp(o1)
        except Exception:
            a1 = {"farmer": ["PASS"], "hands": [], "market": []}
        obs_seq.append(o0)
        act_seq.append(a0)
        g.step(a0, a1)
    return game_stats(obs_seq, act_seq, 0)


def med(games, f):
    return statistics.median(f(g) for g in games)


def main():
    n_mj = int(sys.argv[1]) if len(sys.argv) > 1 else 16
    n_k1 = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    lines = []
    with open(V71 / "majkel_0910_12.jsonl") as f:
        for line in f:
            if '"date=2026-09-10"' in line[:200]:
                continue
            lines.append(line)
            if len(lines) >= n_mj:
                break
    with ProcessPoolExecutor(max_workers=8) as pool:
        mj = [r for r in pool.map(majkel_one, lines) if r]
        k1 = list(pool.map(k1_one, [1046 + 137 * i for i in range(n_k1)]))
    G = {"Majkel": mj, "K1": k1}
    out = {}
    print(f"Majkel {len(mj)} 局 / K1 {len(k1)} 局，中位数（收入=卖出量×当步挂牌价，近似）")
    print(f"{'产品':<11}| 收入 M/K        | 卖量 M/K    | 均卖价 M/K  | 面积·天 M/K | 元/面积·天 M/K | 施肥覆盖 M/K | 缺水 M/K | 种植 M/K")
    for p in PRODS:
        r = {}
        for k, gs in G.items():
            td = med(gs, lambda g: g["tile_days"][p])
            r[k] = dict(rev=med(gs, lambda g: g["rev"][p]), qty=med(gs, lambda g: g["qty"][p]),
                        px=med(gs, lambda g: g["rev"][p] / g["qty"][p] if g["qty"][p] else 0),
                        td=td, rpt=med(gs, lambda g: g["rev"][p] / g["tile_days"][p] if g["tile_days"][p] else 0),
                        fert=med(gs, lambda g: g["fert_days"][p] / g["tile_days"][p] if g["tile_days"][p] else 0),
                        dry=med(gs, lambda g: g["dry_days"][p] / g["tile_days"][p] if g["tile_days"][p] else 0),
                        plant=med(gs, lambda g: g["plant"][p]))
        out[p] = r
        m, k = r["Majkel"], r["K1"]
        print(f"{p:<11}| {m['rev']:6.0f}/{k['rev']:<7.0f} | {m['qty']:4.0f}/{k['qty']:<5.0f} | {m['px']:4.0f}/{k['px']:<5.0f} | "
              f"{m['td']:4.0f}/{k['td']:<5.0f} | {m['rpt']:5.1f}/{k['rpt']:<6.1f} | {m['fert']:.2f}/{k['fert']:.2f} | "
              f"{m['dry']:.2f}/{k['dry']:.2f} | {m['plant']:3.0f}/{k['plant']:.0f}")
    print("作物 | 收获次数 M/K | 每次收获单位 M/K | 每面积·天收获次数 M/K | h12 挂果单位/面积·天 M/K")
    for p in CROPS:
        f = lambda gs, fn: med(gs, fn)
        vals = [(f(gs, lambda g: g["h_crop"][p]), f(gs, lambda g: g["h_units"][p] / g["h_crop"][p] if g["h_crop"][p] else 0),
                 f(gs, lambda g: g["h_crop"][p] / g["tile_days"][p] if g["tile_days"][p] else 0),
                 f(gs, lambda g: g["standing"][p] / g["tile_days"][p] if g["tile_days"][p] else 0)) for gs in G.values()]
        (a, b) = vals
        print(f"{p:<10} | {a[0]:4.0f}/{b[0]:<4.0f} | {a[1]:.2f}/{b[1]:.2f} | {a[2]:.3f}/{b[2]:.3f} | {a[3]:.2f}/{b[3]:.2f}")
    for k, gs in G.items():
        print(f"{k}: FEED {med(gs, lambda g: g['feed']):.0f} 买产品 { {p: med(gs, lambda g, p=p: g['buy_prod'][p]) for p in ('WHEAT','FERTILIZER')} }")
    for k, gs in G.items():
        tot = med(gs, lambda g: sum(g["rev"].values()))
        hrs = {h: med(gs, lambda g, h=h: g["sell_hour"][h]) for h in range(24)}
        seg = {d: med(gs, lambda g, d=d: g["sell_day_rev"][d]) for d in range(6)}
        print(f"{k}: 总卖出 {tot:.0f} 收获 {med(gs, lambda g: g['harvest']):.0f} 施肥 {med(gs, lambda g: g['fertilize']):.0f} | "
              f"按5天段 {[round(v) for v in seg.values()]} | 卖出小时峰 {sorted(hrs, key=lambda h: -hrs[h])[:5]}")
        out[k + "_total"] = {"rev": tot, "seg": seg, "hours": hrs}
    (HERE / "value_distill_result.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
