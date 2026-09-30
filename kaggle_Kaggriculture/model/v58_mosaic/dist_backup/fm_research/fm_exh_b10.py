"""B10 类路线穷举:y68x 对 V43+B10 仍有输局的 10 个 FM 组合 × 41 路线 × seed(≤8,座位交替,取扩大扫描 seed)。"""
import sys, json, statistics
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
COMBOS = ["BRUNCH_SPOT|FARMERS_MARKET", "FARMERS_MARKET|BAKERY", "FARMERS_MARKET|BRUNCH_SPOT", "FARMERS_MARKET|ICE_CREAM_SHOP",
          "FARMERS_MARKET|PIZZA_SHOP", "FARMERS_MARKET|SMOOTHIE_SHOP", "FARMERS_MARKET|YARN_STORE", "PIZZA_SHOP|FARMERS_MARKET",
          "SMOOTHIE_SHOP|FARMERS_MARKET", "YARN_STORE|FARMERS_MARKET"]
def one(job):
    combo, sd, seat, ver = job
    sys.path.insert(0, str(M / "v16_online_fidelity")); sys.path.insert(0, str(M / "v4_demand_race" / "harness"))
    import fidelity, engine
    me = fidelity.make_agent(f"sub:{S}/{ver}_main.py"); op = fidelity.make_agent(f"sub:{S}/kernels_0915/v43b10_agent.py")
    k = engine.load_kagsim(); g = k.Game(seed=sd)
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]
        acts = [None, None]; acts[seat] = me(obs[seat]); acts[1 - seat] = op(obs[1 - seat])
        g.step(acts[0], acts[1])
    return combo, sd, seat, ver, g.reward(seat) - g.reward(1 - seat)
if __name__ == "__main__":
    ns = {}; exec((S / "y68v_main.py").read_text(), ns)
    rids = sorted(ns["_IMPL"].chassis.routes)
    by = json.load(open(S / "combo_seeds_y68v_b.json"))
    vers = ["y68x"] + [f"fr_{r}" for r in rids]
    jobs = [(c, sd, i % 2, v) for c in COMBOS for i, sd in enumerate(by[c][:8]) for v in vers]
    print(f"任务 {len(jobs)} 局", flush=True)
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(one, jobs, chunksize=8))
    json.dump(res, open(S / "fm_exh_b10.json", "w"), ensure_ascii=False)
    for c in COMBOS:
        def stat(v):
            vals = [m for cc, sd, st, vv, m in res if cc == c and vv == v]
            return sum(x > 0 for x in vals), len(vals), min(vals), statistics.mean(vals)
        ranked = sorted(vers, key=lambda v: (stat(v)[0], stat(v)[2]), reverse=True)
        print(f"\n{c}(y68x {stat('y68x')[0]}/{stat('y68x')[1]} 最差{stat('y68x')[2]:+.0f})")
        for v in [x for x in ranked if x != "y68x"][:5]:
            w, n, mn, mean = stat(v)
            print(f"   {v:8s} {w}/{n} 最差{mn:+6.0f} 均{mean:+6.0f}")
