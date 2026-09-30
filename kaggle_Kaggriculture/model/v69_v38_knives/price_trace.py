"""y68a 对局逐日价格与自家肥料库存:FERTILIZER/WHEAT/STRAWBERRY/CARROT 价格(每日 hour0)、shed 肥料、当日卖肥/买肥下单量。"""
import sys, collections, statistics as S
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent; MODEL = HERE.parent
sys.path.insert(0, str(HERE)); import race
ITEMS = ("FERTILIZER", "WHEAT", "STRAWBERRY", "CARROT")

def one(job):
    pack, opp_name, opp_spec, seed = job
    sys.path.insert(0, str(MODEL / "v16_online_fidelity")); sys.path.insert(0, str(MODEL / "v4_demand_race" / "harness"))
    import engine, fidelity
    ags = [fidelity.make_agent(f"sub:{pack}"), fidelity.make_agent(opp_spec)]
    g = engine.load_kagsim().Game(seed=seed); fb = {"farmer": ["PASS"], "hands": [], "market": []}
    out = collections.defaultdict(dict); sold = collections.Counter(); bought = collections.Counter()
    for t in range(719):
        o0 = g.observe(0); d = t // 24
        if t % 24 == 0:
            pr = o0["market"]["prices"]
            for it in ITEMS: out[d][it] = pr[it]
            out[d]["shedFER"] = (o0["private"].get("shed") or {}).get("FERTILIZER", 0)
        acts = []
        for p in (0, 1):
            try: acts.append(ags[p](g.observe(p)))
            except Exception: acts.append(dict(fb))
        money0 = g.observe(0)["farms"][0]["money"]
        for o in acts[0].get("market") or []:
            if o and len(o) > 2 and o[1] == "FERTILIZER":
                (sold if o[0] == "SELL" else bought)[d] += 0 if o[0] not in ("SELL", "BUY_PRODUCT") else 1
        g.step(acts[0], acts[1])
    for d in out: out[d]["sellFERturns"] = sold[d]; out[d]["buyFERturns"] = bought[d]
    return dict(out)

if __name__ == "__main__":
    pack = str(Path(sys.argv[1]).resolve()); seeds = [int(s) for s in sys.argv[2:]]
    jobs = [(pack, n, spec, s) for n, spec, _ in race.OPP[:6] for s in seeds]
    with ProcessPoolExecutor(14) as ex:
        res = list(ex.map(one, jobs))
    keys = ITEMS + ("shedFER", "sellFERturns", "buyFERturns")
    print("day " + " ".join(f"{k[:10]:>10s}" for k in keys))
    for d in range(30):
        vals = [S.mean(r[d][k] for r in res if d in r) for k in keys]
        print(f"d{d:2d} " + " ".join(f"{v:10.1f}" for v in vals))
