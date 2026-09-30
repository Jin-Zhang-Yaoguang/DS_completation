"""y68a 施肥来源归因:每个 FERTILIZE 指令的日、执行者、脚下作物、是否与原生路由带同步同指令(native)还是层追加(layer)。
另验 V219 番茄投资是否曾触发(tomato 地块数)。用法: python fert_source.py <main.py> <seeds...>
"""
import sys, re, ast, json, collections, statistics as S
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent; MODEL = HERE.parent
sys.path.insert(0, str(HERE)); import race
R = {int(k): v for k, v in json.load(open(HERE / "v38_routes.json")).items()}
TABLE = ast.literal_eval(re.search(r"state\['route'\]=(\{.*\})\.get", (MODEL / "opponent_pool_v1/packs/v38_main.py").read_text().splitlines()[950]).group(1))

def units(a): return [a.get("farmer") or ["PASS"]] + list(a.get("hands") or [])

def one(job):
    pack, opp_name, opp_spec, seed = job
    sys.path.insert(0, str(MODEL / "v16_online_fidelity")); sys.path.insert(0, str(MODEL / "v4_demand_race" / "harness"))
    import engine, fidelity
    ags = [fidelity.make_agent(f"sub:{pack}"), fidelity.make_agent(opp_spec)]
    g = engine.load_kagsim().Game(seed=seed); fb = {"farmer": ["PASS"], "hands": [], "market": []}
    route = 0; rows = collections.Counter(); tomato_tiles = 0
    for t in range(719):
        o0 = g.observe(0)
        if t == 144:
            route = TABLE.get(tuple(((o0.get("town") or {}).get("unlocked_shops") or [])[:2]), 0)
        acts = []
        for p in (0, 1):
            try: acts.append(ags[p](g.observe(p)))
            except Exception: acts.append(dict(fb))
        eff = 2 if t >= 648 else route
        native = units(R[eff][t])
        farm = o0["farms"][0]; pos = [farm["farmer"]] + list(farm.get("hands") or [])
        for i, u in enumerate(units(acts[0])):
            if u and u[0] == "FERTILIZE" and i < len(pos):
                x, y = pos[i]; tile = farm["tiles"][y][x]
                crop = tile.get("crop") if isinstance(tile, dict) else str(tile)
                src = "native" if i < len(native) and native[i] == u else "layer"
                rows[(t // 24, crop, src)] += 1
        if t == 700:
            tomato_tiles = sum(1 for row in farm["tiles"] for x in row if isinstance(x, dict) and x.get("crop") == "TOMATO")
        g.step(acts[0], acts[1])
    return opp_name, seed, route, dict((f"{d}|{c}|{s}", n) for (d, c, s), n in rows.items()), tomato_tiles

if __name__ == "__main__":
    pack = str(Path(sys.argv[1]).resolve()); seeds = [int(s) for s in sys.argv[2:]]
    jobs = [(pack, n, spec, s) for n, spec, _ in race.OPP[:6] for s in seeds]
    with ProcessPoolExecutor(14) as ex:
        res = list(ex.map(one, jobs))
    tot = collections.Counter(); byday = collections.defaultdict(collections.Counter)
    for _, _, route, rows, tt in res:
        for k, n in rows.items():
            d, c, s = k.split("|"); tot[(c, s)] += n / len(res); byday[int(d)][s] += n / len(res)
    print("games", len(res), "tomato tiles@t700 (mean):", round(S.mean(r[4] for r in res), 2))
    print("fert per game by (crop, source):", {f"{c}/{s}": round(v, 1) for (c, s), v in tot.most_common()})
    print("per day native/layer:", {d: (round(v['native'], 1), round(v['layer'], 1)) for d, v in sorted(byday.items())})
