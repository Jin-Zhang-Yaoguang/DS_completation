"""gate9(重建):候选 vs 9 个 2200+ 线上模型,seed1100-1115 × 双席位。用法: python gate9.py 候选_main.py"""
import sys, statistics, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
DB = M / "v58_mosaic" / "dist_backup"
VERS = ["y68a", "y68c", "y68f", "y68g", "y68h", "y68i", "y68j", "y68r2", "y68s2"]
def one(job):
    cand, opp, seed, seat = job
    sys.path.insert(0, str(M/"v16_online_fidelity")); sys.path.insert(0, str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    me = fidelity.make_agent(f"sub:{cand}"); op = fidelity.make_agent(f"sub:{DB}/{opp}_main.py")
    k = engine.load_kagsim(); g = k.Game(seed=seed); o = 1 - seat
    a = [None, None]
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]; a[seat] = me(obs[seat]); a[o] = op(obs[o]); g.step(a[0], a[1])
    return opp, seed, seat, float(g.reward(seat) - g.reward(o))
if __name__ == "__main__":
    cand = str(Path(sys.argv[1]).resolve())
    jobs = [(cand, v, s, st_) for v in VERS for s in range(1100, 1116) for st_ in (0, 1)]
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(one, jobs, chunksize=2))
    json.dump([list(r) for r in res], open(HERE/"gate9_last.json", "w"))
    tot = 0
    for v in VERS:
        ms = sorted(m for o2, sd, st_, m in res if o2 == v)
        w = sum(1 for m in ms if m > 0); tot += w
        print(f"{v:6s} {w:2d}/32 中位 {statistics.median(ms):+8.0f} 最差 {ms[0]:+8.0f}")
    print(f"gate: {tot}/288")
