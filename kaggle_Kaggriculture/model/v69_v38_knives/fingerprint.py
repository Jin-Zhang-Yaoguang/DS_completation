"""候选包在自然 seed 上的生产指纹(与 gold_extract 同字段):fert_n/fert_first/harvest/plant/feed/collect/卖买/动物/终局 bank。
用法: python fingerprint.py <main.py> <opp_spec> <seed...>
"""
import sys, json, collections, statistics as S
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
MODEL = Path(__file__).resolve().parents[1]

def one(job):
    cand, opp, seed = job
    sys.path.insert(0, str(MODEL / "v16_online_fidelity")); sys.path.insert(0, str(MODEL / "v4_demand_race" / "harness"))
    import engine, fidelity
    a0, a1 = fidelity.make_agent(f"sub:{cand}"), fidelity.make_agent(opp)
    g = engine.load_kagsim().Game(seed=seed)
    fb = {"farmer": ["PASS"], "hands": [], "market": []}
    fp = [dict(fert_n=0, fert_first=-1, harvest_n=0, plant_n=0, feed_n=0, collect_n=0, sell=collections.Counter(),
               buy=collections.Counter(), hires=0, fert_by_day=collections.Counter()) for _ in (0, 1)]
    for t in range(719):
        obs = [g.observe(0), g.observe(1)]
        acts = []
        for p, ag in ((0, a0), (1, a1)):
            try: acts.append(ag(obs[p]))
            except Exception: acts.append(dict(fb))
        for p in (0, 1):
            f = fp[p]
            for u in [acts[p].get("farmer") or []] + list(acts[p].get("hands") or []):
                if not u: continue
                op = u[0]
                if op == "FERTILIZE":
                    f["fert_n"] += 1; f["fert_by_day"][t // 24] += 1
                    if f["fert_first"] < 0: f["fert_first"] = t
                elif op == "HARVEST": f["harvest_n"] += 1
                elif op == "PLANT": f["plant_n"] += 1
                elif op == "FEED": f["feed_n"] += 1
                elif op == "COLLECT_FERTILIZER": f["collect_n"] += 1
            for o in acts[p].get("market") or []:
                if not o: continue
                if o[0] == "SELL" and len(o) > 2: f["sell"][o[1]] += int(o[2])
                elif o[0] == "BUY_PRODUCT" and len(o) > 2: f["buy"][o[1]] += int(o[2])
                elif o[0] == "HIRE": f["hires"] += 1
        g.step(acts[0], acts[1])
    obs = g.observe(0)
    animals = collections.Counter()
    for row in obs["farms"][0]["tiles"]:
        for x in row:
            if isinstance(x, dict) and x.get("animal"): animals[x["animal"]] += 1
    out = fp[0]; out["animals"] = dict(animals)
    out["bank"] = float(g.reward(0)); out["opp_bank"] = float(g.reward(1)); out["seed"] = seed
    out["sell"] = dict(out["sell"]); out["buy"] = dict(out["buy"]); out["fert_by_day"] = dict(out["fert_by_day"])
    return out

if __name__ == "__main__":
    cand = str(Path(sys.argv[1]).resolve()); opp = sys.argv[2]; seeds = [int(s) for s in sys.argv[3:]]
    with ProcessPoolExecutor(14) as ex:
        res = list(ex.map(one, [(cand, opp, s) for s in seeds]))
    m = lambda k: S.mean(r[k] for r in res)
    print(f"n={len(res)} bank={m('bank'):.0f} opp={m('opp_bank'):.0f} margin={m('bank')-m('opp_bank'):+.0f} fert={m('fert_n'):.1f} "
          f"first(med)={S.median(r['fert_first'] for r in res):.0f} harv={m('harvest_n'):.0f} plant={m('plant_n'):.0f} feed={m('feed_n'):.0f} "
          f"collect={m('collect_n'):.0f} hires={m('hires'):.0f}")
    items = sorted({k for r in res for k in r['sell']})
    print("sell:", {k: round(S.mean(r['sell'].get(k, 0) for r in res)) for k in items})
    print("buy:", {k: round(S.mean(r['buy'].get(k, 0) for r in res)) for k in sorted({k for r in res for k in r['buy']})})
    print("animals:", {k: round(S.mean(r['animals'].get(k, 0) for r in res), 1) for k in sorted({k for r in res for k in r['animals']})})
    print("fert_by_day:", {d: round(S.mean(r['fert_by_day'].get(d, 0) for r in res), 1) for d in range(30)})
    json.dump(res, open(Path(__file__).parent / f"fp_{Path(cand).stem}.json", "w"))
