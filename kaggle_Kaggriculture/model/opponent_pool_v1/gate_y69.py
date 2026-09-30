"""y69 系门控:最近六提交包(v59b~近似/y60m/y63/y66/y67/y68a)× 双 seed × 双席位。
用法: /opt/anaconda3/bin/python3 gate_y69.py <cand_main.py> <sd0> <sd1>
全胜口径:两轮(如 700/701 与 800/801)各 24/24。注:H3(外部提交)包不可得,已知缺口。
"""
import sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
PACKS = {
    "v59b~": str(HERE / "packs" / "v59b_approx.py"),
    "y60m": str(HERE / "packs" / "y60m_main.py"),
    "y63": str(HERE / "packs" / "y63_main.py"),
    "y66": str(HERE / "packs" / "y66_main.py"),
    "y67": str(HERE / "packs" / "y67_main.py"),
    "y68a": str(HERE / "packs" / "y68a_main.py"),
}
def one(job):
    cand, name, opp, sd, seat = job
    sys.path.insert(0, str(MODEL / "v16_online_fidelity"))
    sys.path.insert(0, str(MODEL / "v4_demand_race" / "harness"))
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
