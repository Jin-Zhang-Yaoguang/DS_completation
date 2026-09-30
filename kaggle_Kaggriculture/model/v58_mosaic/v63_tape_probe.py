"""v63 探测:v59b 的 SCHEDULES[0] <- t955_family top 强带。
面板:v56@500(镜像薄格)/ v57@501(遗留痛点)/ y62r@501(未来门控)/ solo11。
用法: python v63_tape_probe.py [topN]
"""
import sys, os, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

HERE = Path(__file__).resolve().parent
S = Path("/private/tmp/claude-501/-Users-a1-6-Desktop-PycharmProjects-DS-completation--claude-worktrees-trusting-carson-f2e0f9/59979e26-3970-412a-b349-4361ccd0c249/scratchpad")
FAM = HERE / "t955_family"

SRC = (S / "v59b_main.py").read_text()
LINES = SRC.split("\n")
MIDX = next(i for i, l in enumerate(LINES) if l.startswith("_MOSAIC_T0 = "))

def build(acts, out):
    lines = list(LINES)
    lines[MIDX] = "_MOSAIC_T0 = " + json.dumps(json.dumps(acts, separators=(",", ":")))
    Path(out).write_text("\n".join(lines))

def one(job):
    kind, cand, opp, sd, tag = job
    if "v57" in str(opp):
        os.chdir(S / "yhay81_0908_extract")
    sys.path.insert(0, str(HERE.parent / "v16_online_fidelity"))
    sys.path.insert(0, str(HERE.parent / "v4_demand_race" / "harness"))
    import fidelity
    if kind == "solo":
        return (tag, fidelity.play(f"sub:{cand}", "pass:", sd, [])["bank"][0])
    r = fidelity.play(f"sub:{cand}", f"sub:{opp}", sd, [])
    return (tag, r["bank"][0] - r["bank"][1])

if __name__ == "__main__":
    if sys.argv[1:] and sys.argv[1].endswith(".json") and Path(sys.argv[1]).exists():
        names = json.loads(Path(sys.argv[1]).read_text())
        variants = [(n, FAM / f"{n}.json") for n in names]
    else:
        topn = int(sys.argv[1]) if len(sys.argv) > 1 else 6
        cands = []
        for f in FAM.glob("t90_*.json"):
            d = json.load(open(f))
            cands.append((d.get("bank", 0), f))
        cands.sort(reverse=True)
        variants = [("base", None)] + [(f.stem, f) for b, f in cands[:topn]]
    jobs = []
    for tag, f in variants:
        out = S / f"v63p_{tag}.py"
        if f is None:
            out.write_text(SRC)
        else:
            build(json.load(open(f))["actions"][:719], out)
        jobs += [
            ("g", str(out), str(S / "v56_main.py"), 500, f"{tag}|v56@500"),
            ("g", str(out), str(S / "yhay81_0908_extract" / "v57_main.py"), 501, f"{tag}|v57@501"),
            ("g", str(out), str(S / "y62r_main.py"), 501, f"{tag}|y62r@501"),
            ("solo", str(out), None, 11, f"{tag}|solo11"),
        ]
    with ProcessPoolExecutor(8) as ex:
        for tag, m in ex.map(one, jobs):
            print(f"{tag}: {m:+.0f}", flush=True)
