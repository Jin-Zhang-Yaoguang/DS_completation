"""B10 类路线穷举 v2:用 V43+B10 自己的组合扫描 seed;y68x2 仍有输局的 7 个组合 × 41 路线 × ≤8 seed;逐局记真实组合。"""
import sys, json, statistics
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
COMBOS = ["BRUNCH_SPOT|FARMERS_MARKET", "FARMERS_MARKET|YARN_STORE", "FARMERS_MARKET|BAKERY", "FARMERS_MARKET|PET_CAFE",
          "FARMERS_MARKET|PIZZA_SHOP", "ICE_CREAM_SHOP|FARMERS_MARKET", "YARN_STORE|FARMERS_MARKET"]
def one(job):
    combo, sd, seat, ver = job
    sys.path.insert(0, str(M / "v16_online_fidelity")); sys.path.insert(0, str(M / "v4_demand_race" / "harness"))
    import fidelity, engine
    me = fidelity.make_agent(f"sub:{S}/{ver}_main.py"); op = fidelity.make_agent(f"sub:{S}/kernels_0915/v43b10_agent.py")
    k = engine.load_kagsim(); g = k.Game(seed=sd); t = 0; real = None
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]
        acts = [None, None]; acts[seat] = me(obs[seat]); acts[1 - seat] = op(obs[1 - seat])
        g.step(acts[0], acts[1]); t += 1
        if t == 146: real = "|".join(((g.observe(0).get("town") or {}).get("unlocked_shops") or [])[:2])
    return combo, sd, seat, ver, real, g.reward(seat) - g.reward(1 - seat)
if __name__ == "__main__":
    ns = {}; exec((S / "y68v_main.py").read_text(), ns)
    rids = sorted(ns["_IMPL"].chassis.routes)
    by = json.load(open(S / "combo_seeds_by_opp.json"))["V43+B10"]
    vers = ["y68x2"] + [f"fr_{r}" for r in rids]
    jobs = [(c, sd, i % 2, v) for c in COMBOS for i, sd in enumerate(by[c][:8]) for v in vers]
    print(f"任务 {len(jobs)} 局", flush=True)
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(one, jobs, chunksize=8))
    json.dump(res, open(S / "fm_exh_b10_v2.json", "w"), ensure_ascii=False)
    for c in COMBOS:
        def stat(v):
            vals = [m for cc, sd, st, vv, real, m in res if cc == c and vv == v]
            return sum(x > 0 for x in vals), len(vals), min(vals), statistics.mean(vals)
        drift = sum(1 for cc, sd, st, vv, real, m in res if cc == c and vv == "y68x2" and real != c)
        ranked = sorted([v for v in vers if v != "y68x2"], key=lambda v: (stat(v)[0], stat(v)[2]), reverse=True)
        b = stat("y68x2")
        print(f"\n{c}(y68x2 {b[0]}/{b[1]} 最差{b[2]:+.0f};组合漂移 {drift})")
        for v in ranked[:5]:
            w, n, mn, mean = stat(v)
            print(f"   {v:8s} {w}/{n} 最差{mn:+6.0f} 均{mean:+6.0f}")
