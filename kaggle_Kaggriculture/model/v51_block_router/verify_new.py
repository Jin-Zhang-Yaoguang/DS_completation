import sys, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "v16_online_fidelity"))
TAPES = HERE.parent / "v16_online_fidelity" / "tapes"
GRAFTS = HERE / "grafts"
def one(job):
    import fidelity
    spec, tag, sd = job
    r = fidelity.play(spec, "pass:", sd, [])
    return tag, sd, int(r["bank"][0])
if __name__ == "__main__":
    names = ["rb_fed85a15a6","rb_e2448f1158","rb_84a8a63442","rb_6687cbe0db","rb_837669b4a0","rb_7a938ab7ee"]
    jobs = []
    for n in names:
        for sd in (11,22,33):
            jobs.append((f"tape:{TAPES}/{n}.json", f"{n}|pure", sd))
            for cut in (72,144,288):
                jobs.append((f"tape:{GRAFTS}/gn_{n}_{cut}.json", f"{n}|{cut}", sd))
    res={}
    with ProcessPoolExecutor(8) as ex:
        for tag, sd, b in ex.map(one, jobs, chunksize=2):
            res.setdefault(tag, {})[sd]=b
    for n in names:
        pure=[res[f"{n}|pure"][sd] for sd in (11,22,33)]
        line=f"{n:20s} pure={pure}"
        for cut in (72,144,288):
            g=[res[f"{n}|{cut}"][sd] for sd in (11,22,33)]
            d=[g[i]-pure[i] for i in range(3)]
            ok = all(x>-1500 for x in d)
            line+=f"  @{cut}:{'OK' if ok else 'LOSSY'}({min(d)})"
        print(line)
