"""完整对局开局矩阵:我方 6 种买入量 × 对手 5 种开局 × 6 个线上 seed(座位交替)。"""
import sys, json, statistics
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
OURS = [13, 20, 25, 30, 35, 43]
OPPS = {"V38原版": "kernels_0913/v38_main.py", "qq型15+18": "opp_qq_main.py", "V43": "kernels_0915/v43_agent.py",
        "V43+B10": "kernels_0915/v43b10_agent.py", "V43+13/13": "opp_v43_1313_main.py"}
WEIGHT = {"V38原版": 12.1, "qq型15+18": 1.5, "V43": 51.4, "V43+B10": 2.0, "V43+13/13": 6.6}
def one(job):
    b, opp, sd, seat = job
    sys.path.insert(0, str(M / "v16_online_fidelity")); sys.path.insert(0, str(M / "v4_demand_race" / "harness"))
    import fidelity, engine
    me = fidelity.make_agent(f"sub:{S}/op_b{b}_main.py"); op = fidelity.make_agent(f"sub:{S}/{OPPS[opp]}")
    k = engine.load_kagsim(); g = k.Game(seed=sd)
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]
        acts = [None, None]; acts[seat] = me(obs[seat]); acts[1 - seat] = op(obs[1 - seat])
        g.step(acts[0], acts[1])
    return b, opp, sd, g.reward(seat) - g.reward(1 - seat)
if __name__ == "__main__":
    ids = json.load(open(S / "ep_ids9.json")); seeds = []
    for eid in ids["y68s2"][:40]:
        p = S / f"live_replays3/episode-{eid}-replay.json"
        if p.exists():
            sd = json.load(open(p))["info"]["seed"]
            if sd not in seeds: seeds.append(sd)
        if len(seeds) >= 6: break
    jobs = [(b, o, sd, i % 2) for b in OURS for o in OPPS for i, sd in enumerate(seeds)]
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(one, jobs, chunksize=2))
    json.dump(res, open(S / "open_matrix_full.json", "w"), ensure_ascii=False)
    print(f"seeds={seeds}")
    print(f"{'我方买入':8s} " + " ".join(f"{o:>16s}" for o in OPPS) + f" {'加权均margin':>12s} {'加权胜率':>8s}")
    for b in OURS:
        cells = []; wm = ww = wt = 0.0
        for o in OPPS:
            v = [m for bb, oo, sd, m in res if bb == b and oo == o]
            w = sum(x > 0 for x in v)
            cells.append(f"{w}/{len(v)} {statistics.mean(v):+7.0f}")
            wm += WEIGHT[o] * statistics.mean(v); ww += WEIGHT[o] * w / len(v); wt += WEIGHT[o]
        print(f"B{b}/S42   " + " ".join(f"{c:>16s}" for c in cells) + f" {wm/wt:+12.0f} {ww/wt:8.0%}")
