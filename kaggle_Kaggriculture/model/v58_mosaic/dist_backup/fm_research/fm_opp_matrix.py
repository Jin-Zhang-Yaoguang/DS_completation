"""补齐 FM 对手矩阵:①15 个 FM 组合 y68v 基线 vs V38原版/V41/V43+B10;②6 个弱组合的候选路线 vs V41。每组合 ≤10 seed,座位交替。"""
import sys, json, statistics
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
OPPS = {"V38原版": "kernels_0913/v38_main.py", "V41": "kernels_0914/v41_agent.py", "V43+B10": "kernels_0915/v43b10_agent.py"}
WEAK = {"FARMERS_MARKET|FARMERS_MARKET", "FARMERS_MARKET|YARN_STORE", "BRUNCH_SPOT|FARMERS_MARKET", "BAKERY|FARMERS_MARKET", "PET_CAFE|FARMERS_MARKET", "YARN_STORE|FARMERS_MARKET"}
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
    fm = sorted(c for c in by if "FARMERS_MARKET" in c.split("|"))
    robust = json.load(open(S / "fm_route_robust.json"))
    cand = {c: sorted({r[3] for r in robust if r[0] == c and r[3] != "y68v"}) for c in WEAK}
    jobs = []
    for c in fm:
        for i, sd in enumerate(by[c][:10]):
            opps = ["V41"] if c in WEAK else list(OPPS)
            for o in opps: jobs.append((c, sd, i % 2, "y68v", o))
            if c in WEAK:
                for v in cand[c]: jobs.append((c, sd, i % 2, v, "V41"))
    print(f"任务 {len(jobs)} 局", flush=True)
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(one, jobs, chunksize=4))
    json.dump(res, open(S / "fm_opp_matrix.json", "w"), ensure_ascii=False)
    ex43 = json.load(open(S / "fm_route_exhaustive.json")) + json.load(open(S / "fm_route_exhaustive_rest.json"))
    for c in fm:
        vers = ["y68v"] + (cand[c] if c in WEAK else [])
        print(f"\n{c}")
        for v in vers:
            cells = []
            a43 = [r[4] for r in ex43 if r[0] == c and r[3] == v]
            if a43: cells.append(f"V43 {sum(x>0 for x in a43)}/{len(a43)}")
            for o in ("V38原版", "V41", "V43+B10"):
                vals = [m for cc, sd, st, vv, oo, m in res if cc == c and vv == v and oo == o]
                if not vals and c in WEAK and o != "V41":
                    vals = [r[5] for r in robust if r[0] == c and r[3] == v and r[4] == o]
                if vals: cells.append(f"{o} {sum(x>0 for x in vals)}/{len(vals)} 最差{min(vals):+.0f}")
            print(f"   {v:8s} " + " | ".join(cells))
