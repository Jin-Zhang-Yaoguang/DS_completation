import sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
PACKS = {
    
    "y63": str(S / "y63_main.py"),
    "y66": str(S / "y66_main.py"),
    "y67": str(S / "y67_main.py"),
    "y68a": str(S / "y68a_main.py"),
    "y68c": str(S / "y68c_main.py"),
    "y68f": str(S / "y68f_main.py"),
}
def one(job):
    cand, name, opp, sd, seat = job
    sys.path.insert(0, str(M / "v16_online_fidelity"))
    sys.path.insert(0, str(M / "v4_demand_race" / "harness"))
    import fidelity
    specs = [None, None]
    specs[seat] = f"sub:{cand}"
    specs[1 - seat] = f"sub:{opp}"
    r = fidelity.play(specs[0], specs[1], sd, [])
    return (name, sd, seat, r["bank"][seat] - r["bank"][1 - seat])
if __name__ == "__main__":
    cand = str(Path(sys.argv[1]).resolve())
    seeds = [int(x) for x in sys.argv[2:4]] or [700, 701]
    jobs = [(cand, n, p, sd, seat) for n, p in PACKS.items() for sd in seeds for seat in (0, 1)]
    wins = 0
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(one, jobs))
    for name, sd, seat, m in res:
        ok = m > 0; wins += ok
        print(f"{name} seed{sd} seat{seat}: {'WIN ' if ok else 'LOSS'} {m:+.0f}", flush=True)
    print(f"gate: {wins}/{len(jobs)}", flush=True)
