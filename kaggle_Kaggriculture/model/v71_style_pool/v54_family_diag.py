"""V54 对 V52/V53 循环赛复算 + 输局机制诊断(动物存活/现金曲线/饲料)。"""
import sys, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
def one(job):
    opp, seed, seat = job
    sys.path.insert(0, str(M/"v16_online_fidelity")); sys.path.insert(0, str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    me = fidelity.make_agent(f"sub:{HERE}/agents/v54_main.py")
    op = fidelity.make_agent(f"sub:{HERE}/agents/{opp}_main.py")
    k = engine.load_kagsim(); g = k.Game(seed=seed); o = 1 - seat
    t = 0; snap = {}
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]; a = [None, None]; a[seat] = me(obs[seat]); a[o] = op(obs[o])
        if t in (23, 47, 71, 120, 240, 480):
            f = obs[seat]["farms"][seat]; fo = obs[seat]["farms"][o]
            an = lambda ff: sum(1 for row in ff["tiles"] for c in row if isinstance(c, dict) and c.get("animal"))
            wheat = (obs[seat].get("private") or {}).get("shed", {}).get("WHEAT", 0)
            snap[t] = (round(f["money"]), round(fo["money"]), an(f), an(fo), wheat)
        g.step(a[0], a[1]); t += 1
    return opp, seed, seat, float(g.reward(seat) - g.reward(o)), snap
if __name__ == "__main__":
    jobs = [(o2, s, st) for o2 in ("v52", "v53") for s in range(9000, 9008) for st in (0, 1)]
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(one, jobs))
    for o2 in ("v52", "v53"):
        v = [r for r in res if r[0] == o2]
        w = sum(1 for r in v if r[3] > 0)
        print(f"V54 vs {o2}: {w}/{len(v)}")
        for r in sorted(v, key=lambda x: x[3])[:4]:
            print(f"  seed{r[1]} seat{r[2]} {r[3]:+8.0f}  快照(t:(我钱,他钱,我动物,他动物,我仓麦)):")
            for t2, s2 in sorted(r[4].items()): print(f"    t{t2}: {s2}")
    json.dump([[r[0], r[1], r[2], r[3]] for r in res], open(HERE/"v54_family.json", "w"))
