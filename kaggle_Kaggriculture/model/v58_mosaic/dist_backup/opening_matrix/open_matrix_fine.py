"""开局悬崖细化:我方买 13/30/35/38 × 对手 5 种 × 12 个新线上 seed(座位交替)。"""
import sys, json, statistics
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
OURS = [13, 30, 35, 38]
OPPS = {"V38原版": "kernels_0913/v38_main.py", "V43": "kernels_0915/v43_agent.py", "V43+B10/S10": "kernels_0915/v43b10_agent.py",
        "V43+B10/S5": "opp_v43_b10s5_main.py", "V43+13/13": "opp_v43_1313_main.py"}
WEIGHT = {"V38原版": 12.1, "V43": 51.4, "V43+B10/S10": 1.2, "V43+B10/S5": 0.8, "V43+13/13": 6.6}
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
    used = set(json.load(open(S / "open_matrix_full.json")) and [r[2] for r in json.load(open(S / "open_matrix_full.json"))])
    ids = json.load(open(S / "ep_ids8.json")); seeds = []
    for tag in ("y68r2", "y68j"):
        for eid in ids[tag]:
            p = S / f"live_replays3/episode-{eid}-replay.json"
            if not p.exists(): continue
            sd = json.load(open(p))["info"]["seed"]
            if sd not in used and sd not in seeds: seeds.append(sd)
            if len(seeds) >= 12: break
        if len(seeds) >= 12: break
    jobs = [(b, o, sd, i % 2) for b in OURS for o in OPPS for i, sd in enumerate(seeds)]
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(one, jobs, chunksize=2))
    json.dump(res, open(S / "open_matrix_fine.json", "w"), ensure_ascii=False)
    allres = res + [tuple(r) for r in json.load(open(S / "open_matrix_full.json")) if r[0] in OURS and r[1] in OPPS]
    for lab, R in (("新 12 seed", res), ("合并 18 seed(含上轮)", allres)):
        print(f"\n== {lab}")
        print(f"{'我方':6s} " + " ".join(f"{o:>17s}" for o in OPPS) + f" {'加权均margin':>12s} {'加权胜率':>8s}")
        for b in OURS:
            cells = []; wm = ww = wt = 0.0
            for o in OPPS:
                v = [m for bb, oo, sd, m in R if bb == b and oo == o]
                if not v: cells.append("-"); continue
                w = sum(x > 0 for x in v); med = statistics.median(v)
                cells.append(f"{w}/{len(v)} 中位{med:+6.0f}")
                wm += WEIGHT[o] * med; ww += WEIGHT[o] * w / len(v); wt += WEIGHT[o]
            print(f"买{b:<4d} " + " ".join(f"{c:>17s}" for c in cells) + f" {wm/wt:+12.0f} {ww/wt:8.0%}")
