"""v59 六包门控:最近六次提交(v53d/v54c/v54d/v56/v57/v58)包级对打。
每包 2 全新 seed × 双席位 = 4 局,24 局全胜放行。
用法: python gate_v59.py <cand_path> [seed0 seed1]
"""
import sys, os, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

HERE = Path(__file__).resolve().parent
SCRATCH = Path("/private/tmp/claude-501/-Users-a1-6-Desktop-PycharmProjects-DS-completation--claude-worktrees-trusting-carson-f2e0f9/59979e26-3970-412a-b349-4361ccd0c249/scratchpad")
BR = HERE.parent / "v51_block_router"

PACKS = {
    "v54c": str(BR / "dist_v54c" / "main.py"),
    "v54d": str(BR / "dist_v54d" / "main.py"),
    "v56": str(SCRATCH / "v56_main.py"),
    "v57": str(SCRATCH / "yhay81_0908_extract" / "v57_main.py"),
    "v58": str(SCRATCH / "v58_main.py"),
    "v59b": str(SCRATCH / "v59b_main.py"),
}

def one(job):
    cand, name, opp, sd, seat = job
    if name == "v57":
        os.chdir(Path(opp).parent)
    sys.path.insert(0, str(HERE.parent / "v16_online_fidelity"))
    sys.path.insert(0, str(HERE.parent / "v4_demand_race" / "harness"))
    import fidelity
    specs = [None, None]
    specs[seat] = f"sub:{cand}"
    specs[1 - seat] = f"sub:{opp}"
    r = fidelity.play(specs[0], specs[1], sd, [])
    m = r["bank"][seat] - r["bank"][1 - seat]
    return (name, sd, seat, m)

if __name__ == "__main__":
    cand = str(Path(sys.argv[1]).resolve())
    seeds = [int(x) for x in sys.argv[2:4]] or [500, 501]
    jobs = [(cand, n, p, sd, seat) for n, p in PACKS.items() for sd in seeds for seat in (0, 1)]
    wins = 0
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(one, jobs))
    for name, sd, seat, m in res:
        ok = m > 0
        wins += ok
        print(f"{name} seed{sd} seat{seat}: {'WIN ' if ok else 'LOSS'} {m:+.0f}", flush=True)
    print(f"gate: {wins}/{len(jobs)}", flush=True)
