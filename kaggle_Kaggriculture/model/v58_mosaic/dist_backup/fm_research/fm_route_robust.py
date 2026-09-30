"""弱 FM 组合候选路线跨对手验证:每组合前 4 路线(按 V43 穷举排名)+ y68v 基线,对手 V38 原版 / V43+B10,每组合全部 seed(≤10,座位交替)。"""
import sys, json, statistics
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
OPPS = {"V38原版": "kernels_0913/v38_main.py", "V43+B10": "kernels_0915/v43b10_agent.py"}
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
    ex_res = json.load(open(S / "fm_route_exhaustive.json"))
    by = json.load(open(S / "combo_seeds_y68v.json"))
    combos = sorted({r[0] for r in ex_res})
    top = {}
    for c in combos:
        vers = sorted({r[3] for r in ex_res if r[0] == c and r[3].startswith("fr_")})
        def key(ver):
            v = [r[4] for r in ex_res if r[0] == c and r[3] == ver]
            return (sum(x > 0 for x in v), statistics.mean(v))
        top[c] = sorted(vers, key=key, reverse=True)[:4]
    jobs = []
    for c in combos:
        for i, sd in enumerate(by[c][:10]):
            for ver in ["y68v"] + top[c]:
                for opp in OPPS:
                    jobs.append((c, sd, i % 2, ver, opp))
    print(f"任务 {len(jobs)} 局", flush=True)
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(one, jobs, chunksize=4))
    json.dump(res, open(S / "fm_route_robust.json", "w"), ensure_ascii=False)
    for c in combos:
        print(f"\n{c}")
        for ver in ["y68v"] + top[c]:
            cells = []
            for opp in OPPS:
                v = [m for cc, sd, st, vv, oo, m in res if cc == c and vv == ver and oo == opp]
                cells.append(f"{opp} {sum(x>0 for x in v)}/{len(v)} 均{statistics.mean(v):+6.0f} 最差{min(v):+6.0f}")
            vv43 = [r[4] for r in ex_res if r[0] == c and r[3] == ver]
            print(f"   {ver:8s} V43 {sum(x>0 for x in vv43)}/{len(vv43)} | " + " | ".join(cells))
