"""y62r 终局段马赛克:tape2/tape3 的 day27-29 段贪心(t648 后 100% 被使用)。
面板按各 tape 实际被路由的局选。产出 scratchpad/y63_main.py。
"""
import sys, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

HERE = Path(__file__).resolve().parent
S = Path("/private/tmp/claude-501/-Users-a1-6-Desktop-PycharmProjects-DS-completation--claude-worktrees-trusting-carson-f2e0f9/59979e26-3970-412a-b349-4361ccd0c249/scratchpad")
FAM = HERE / "yhay_family"

TEMPLATE = (S / "y62r_main.py").read_text()
LINES = TEMPLATE.split("\n")
AIDX = next(i for i, l in enumerate(LINES) if l.startswith("_ACTIONS_JSON = "))
TAPES0 = json.loads(json.loads(LINES[AIDX][len("_ACTIONS_JSON = "):]))

def build(tapes, out):
    lines = list(LINES)
    lines[AIDX] = "_ACTIONS_JSON = " + json.dumps(json.dumps(tapes, separators=(",", ":")))
    Path(out).write_text("\n".join(lines))

def one(job):
    kind, cand, opp, sd = job
    sys.path.insert(0, str(HERE.parent / "v16_online_fidelity"))
    sys.path.insert(0, str(HERE.parent / "v4_demand_race" / "harness"))
    import fidelity
    if kind == "solo":
        return fidelity.play(f"sub:{cand}", "pass:", sd, [])["bank"][0]
    r = fidelity.play(f"sub:{cand}", f"sub:{opp}", sd, [])
    return r["bank"][0] - r["bank"][1]

def seg_diff(a, b):
    return sum(json.dumps(x, sort_keys=True) != json.dumps(y, sort_keys=True) for x, y in zip(a, b))

PANEL = {
    2: [("g", str(S / "v56_main.py"), 501), ("g", str(S / "v59b_main.py"), 501), ("solo", None, 11)],
    3: [("g", str(S / "v56_main.py"), 500), ("g", str(S / "v59b_main.py"), 500), ("solo", None, 22)],
}

if __name__ == "__main__":
    fam = []
    for f in sorted(FAM.glob("yh0_*.json")):
        fam.append((f.stem, json.load(open(f))["actions"][:719]))
    tapes = [json.loads(json.dumps(t)) for t in TAPES0]
    with ProcessPoolExecutor(8) as ex:
        for ti in (2, 3):
            panel = PANEL[ti]
            base_p = str(S / f"_ym2_base{ti}.py"); build(tapes, base_p)
            jb = [(k, base_p, o, sd) for (k, o, sd) in panel]
            base = list(ex.map(one, jb))
            print(f"tape{ti} base: {[int(x) for x in base]}", flush=True)
            for day in (27, 28, 29):
                s0, s1 = day * 24, min(day * 24 + 24, 719)
                cands = []
                for name, acts in fam:
                    d = seg_diff(acts[s0:s1], tapes[ti][s0:s1])
                    if d > 0:
                        cands.append((d, name, acts))
                cands.sort(key=lambda t: -t[0])
                cands = cands[:12]
                jobs, metas = [], []
                for k, (d, name, acts) in enumerate(cands):
                    trial = [json.loads(json.dumps(t)) for t in tapes]
                    trial[ti] = trial[ti][:s0] + [json.loads(json.dumps(a)) for a in acts[s0:s1]] + trial[ti][s1:]
                    tp = str(S / f"_ym2_{ti}_{k}.py"); build(trial, tp)
                    jobs += [(kk, tp, o, sd) for (kk, o, sd) in panel]
                    metas.append((name, trial))
                res = list(ex.map(one, jobs))
                best = None
                np = len(panel)
                for k, (name, trial) in enumerate(metas):
                    r = res[k * np:(k + 1) * np]
                    gs, solo = r[:2], r[2]
                    if solo < base[2] - 1200 or any(x <= 0 for x in gs):
                        continue
                    gm = sum(gs) / 2
                    if gm > (best[0] if best else sum(base[:2]) / 2):
                        best = (gm, name, trial, r)
                if best:
                    gm, name, trial, r = best
                    tapes = trial
                    print(f"tape{ti} day{day}: SWAP<-{name[:24]} panel={[int(x) for x in r]}", flush=True)
                else:
                    print(f"tape{ti} day{day}: keep", flush=True)
    build(tapes, str(S / "y63_main.py"))
    print("done -> y63_main.py", flush=True)
