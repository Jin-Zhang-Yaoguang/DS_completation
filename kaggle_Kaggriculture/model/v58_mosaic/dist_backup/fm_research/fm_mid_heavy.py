"""5 个弱 FM 组合:y68v 基线与候选路线 vs V43+13/13、qq 型——判定这两类对手该用哪类路线。"""
import sys, json, statistics
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
OPPS = {"V43+13/13": "opp_v43_1313_main.py", "qq型": "opp_qq_main.py"}
CAND = {"BAKERY|FARMERS_MARKET": ["y68v", "fr_112"], "FARMERS_MARKET|FARMERS_MARKET": ["y68v", "fr_112"],
        "FARMERS_MARKET|YARN_STORE": ["y68v", "fr_126", "fr_128"], "PET_CAFE|FARMERS_MARKET": ["y68v", "fr_118", "fr_112"],
        "YARN_STORE|FARMERS_MARKET": ["y68v", "fr_126"], "BRUNCH_SPOT|FARMERS_MARKET": ["y68v", "fr_112", "fr_110"]}
def one(job):
    combo, sd, seat, ver, opp = job
    sys.path.insert(0, str(M / "v16_online_fidelity")); sys.path.insert(0, str(M / "v4_demand_race" / "harness"))
    import fidelity, engine
    me = fidelity.make_agent(f"sub:{S}/{ver}_main.py"); op = fidelity.make_agent(f"sub:{S}/{OPPS[opp]}")
    k = engine.load_kagsim(); g = k.Game(seed=sd)
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]
        acts = [None, None]; acts[seat] = me(obs[seat]); acts[1 - seat] = op(obs[1 - seat])
        g.step(acts[0], acts[1])
    return combo, sd, seat, ver, opp, g.reward(seat) - g.reward(1 - seat)
if __name__ == "__main__":
    by = json.load(open(S / "combo_seeds_y68v.json"))
    jobs = [(c, sd, i % 2, v, o) for c, vs in CAND.items() for i, sd in enumerate(by[c][:10]) for v in vs for o in OPPS]
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(one, jobs, chunksize=4))
    json.dump(res, open(S / "fm_mid_heavy.json", "w"), ensure_ascii=False)
    for c, vs in CAND.items():
        print(f"\n{c}")
        for v in vs:
            cells = []
            for o in OPPS:
                vals = [m for cc, sd, st, vv, oo, m in res if cc == c and vv == v and oo == o]
                cells.append(f"{o} {sum(x>0 for x in vals)}/{len(vals)} 最差{min(vals):+.0f}")
            print(f"   {v:8s} " + " | ".join(cells))
