"""FM|YARN 对 V38+13/13:候选路线在全部 seed(旧扫+扩大扫,≤16,座位交替)。"""
import sys, json, statistics
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
VERS = ["y68x", "fr_5", "fr_1", "fr_9", "fr_11", "fr_126", "fr_128", "fr_0", "fr_114"]
def one(job):
    sd, seat, ver = job
    sys.path.insert(0, str(M / "v16_online_fidelity")); sys.path.insert(0, str(M / "v4_demand_race" / "harness"))
    import fidelity, engine
    me = fidelity.make_agent(f"sub:{S}/{ver}_main.py"); op = fidelity.make_agent(f"sub:{S}/opp_v38_1313_main.py")
    k = engine.load_kagsim(); g = k.Game(seed=sd)
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]
        acts = [None, None]; acts[seat] = me(obs[seat]); acts[1 - seat] = op(obs[1 - seat])
        g.step(acts[0], acts[1])
    return sd, seat, ver, g.reward(seat) - g.reward(1 - seat)
if __name__ == "__main__":
    c = "FARMERS_MARKET|YARN_STORE"
    seeds = json.load(open(S / "combo_seeds_y68v.json"))[c][:10] + json.load(open(S / "combo_seeds_y68v_b.json"))[c][:6]
    jobs = [(sd, i % 2, v) for i, sd in enumerate(seeds) for v in VERS]
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(one, jobs, chunksize=4))
    for v in VERS:
        vals = [m for sd, st, vv, m in res if vv == v]
        print(f"{v:8s} {sum(x>0 for x in vals)}/{len(vals)} 最差{min(vals):+6.0f} 均{statistics.mean(vals):+6.0f}")
