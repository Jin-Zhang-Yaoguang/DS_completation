import sys, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "v16_online_fidelity"))
GRAFTS = HERE / "grafts"
def one(job):
    import fidelity
    name, sd = job
    r = fidelity.play(f"tape:{GRAFTS}/{name}.json", "pass:", sd, [])
    return name, sd, int(r["bank"][0])
if __name__ == "__main__":
    names = [p.stem for p in GRAFTS.glob("rbh288_*.json")]
    jobs = [(n, sd) for n in names for sd in (11,22,33)]
    res = {}
    with ProcessPoolExecutor(8) as ex:
        for n, sd, b in ex.map(one, jobs):
            res.setdefault(n, {})[sd] = b
    # rb 本尊基准
    import fidelity
    base = {sd: int(fidelity.play(f"tape:{HERE.parent}/v16_online_fidelity/tapes/rb_7925cb146f.json","pass:",sd,[])["bank"][0]) for sd in (11,22,33)}
    print("rb base:", base)
    for n in sorted(res):
        banks = [res[n][sd] for sd in (11,22,33)]
        diffs = [res[n][sd]-base[sd] for sd in (11,22,33)]
        ok = all(d > -1500 for d in diffs)
        print(f"{n:36s} {banks} diff={diffs} {'OK' if ok else 'LOSSY'}")
