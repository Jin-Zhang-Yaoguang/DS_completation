"""经验性产量普查:逐日对比每块作物 yield_units 增量,按(作物, 当日是否处于施肥期)汇总;统计未施肥的产出事件 = 施肥可翻倍的空间。
用法: python yield_census.py <main.py> <seeds...>
"""
import sys, collections, statistics as S
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent; MODEL = HERE.parent
sys.path.insert(0, str(HERE)); import race

def one(job):
    pack, opp_name, opp_spec, seed = job
    sys.path.insert(0, str(MODEL / "v16_online_fidelity")); sys.path.insert(0, str(MODEL / "v4_demand_race" / "harness"))
    import engine, fidelity
    ags = [fidelity.make_agent(f"sub:{pack}"), fidelity.make_agent(opp_spec)]
    g = engine.load_kagsim().Game(seed=seed); fb = {"farmer": ["PASS"], "hands": [], "market": []}
    rows = collections.Counter(); prev = {}
    for t in range(719):
        o0 = g.observe(0); day = t // 24
        tiles = o0["farms"][0]["tiles"]
        cur = {}
        for y, row in enumerate(tiles):
            for x, tile in enumerate(row):
                if isinstance(tile, dict) and tile.get("kind") == "PLANT":
                    cur[(x, y)] = (tile["crop"], tile.get("planted_day"), int(tile.get("yield_units", 0)), int(tile.get("fertilized_until_day", -1)))
        for xy, (crop, birth, yu, fu) in cur.items():
            p = prev.get(xy)
            if p and p[0] == crop and p[1] == birth and yu > p[2]:
                inc = yu - p[2]
                rows[(crop, day - 1, "fert" if inc >= 2 else "plain", inc)] += 1
        prev = cur
        acts = []
        for p in (0, 1):
            try: acts.append(ags[p](g.observe(p)))
            except Exception: acts.append(dict(fb))
        g.step(acts[0], acts[1])
    return dict((f"{c}|{d}|{f}|{i}", n) for (c, d, f, i), n in rows.items())

if __name__ == "__main__":
    pack = str(Path(sys.argv[1]).resolve()); seeds = [int(s) for s in sys.argv[2:]]
    jobs = [(pack, n, spec, s) for n, spec, _ in race.OPP[:6] for s in seeds]
    with ProcessPoolExecutor(14) as ex:
        res = list(ex.map(one, jobs))
    tot = collections.Counter(); byday = collections.defaultdict(collections.Counter)
    for r in res:
        for k, n in r.items():
            c, d, f, i = k.split("|")
            tot[(c, f, int(i))] += n / len(res)
            byday[(c, int(d))][f] += n / len(res)
    print("games", len(res))
    print("yield increment events per game (crop, fert?, +units):")
    for (c, f, i), v in sorted(tot.items()): print(f"  {c:10s} {f:5s} +{i}: {v:6.1f}")
    for crop in ("STRAWBERRY", "WHEAT", "CARROT", "TOMATO"):
        print(crop, "plain/fert events by day:", " ".join(f"d{d}:{byday[(crop, d)]['plain']:.0f}/{byday[(crop, d)]['fert']:.0f}" for d in range(6, 30) if byday[(crop, d)]))
