"""自然 seed 下 y68a 在 step144 选到的路由分布(按 V38 路由表映射),重点看 route 0/1 占比。"""
import sys, re, ast, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent; MODEL = HERE.parent
sys.path.insert(0, str(HERE)); import race
src = (MODEL / "opponent_pool_v1/packs/v38_main.py").read_text().splitlines()[950]
TABLE = ast.literal_eval(re.search(r"state\['route'\]=(\{.*\})\.get", src).group(1))
PACK = str(MODEL / "opponent_pool_v1/packs/y68a_main.py")

def one(job):
    opp_name, opp_spec, seed = job
    sys.path.insert(0, str(MODEL / "v16_online_fidelity")); sys.path.insert(0, str(MODEL / "v4_demand_race" / "harness"))
    import engine, fidelity
    ags = [fidelity.make_agent(f"sub:{PACK}"), fidelity.make_agent(opp_spec)]
    g = engine.load_kagsim().Game(seed=seed); fb = {"farmer": ["PASS"], "hands": [], "market": []}
    for t in range(145):
        obs = g.observe(0)
        if t == 144:
            shops = (obs.get("town") or {}).get("unlocked_shops") or []
            return (opp_name, seed, tuple(shops[:2]), TABLE.get(tuple(shops[:2]), 0))
        acts = []
        for p in (0, 1):
            try: acts.append(ags[p](g.observe(p)))
            except Exception: acts.append(dict(fb))
        g.step(acts[0], acts[1])

if __name__ == "__main__":
    seeds = race.TRAIN_SEEDS[:32]
    jobs = [(n, spec, s) for n, spec, _ in race.OPP for s in seeds]
    with ProcessPoolExecutor(14) as ex:
        res = list(ex.map(one, jobs))
    c = collections.Counter(r[3] for r in res); print("route dist:", dict(sorted(c.items())), "n=", len(res))
    pairs = collections.Counter((r[2], r[3]) for r in res if r[3] in (0, 1)); print("route0/1 pairs:", pairs.most_common(10))
    byopp = collections.defaultdict(collections.Counter)
    for r in res: byopp[r[0]][r[3]] += 1
    for k, v in byopp.items(): print(k, "route0/1 share:", round((v[0] + v[1]) / sum(v.values()), 2))
