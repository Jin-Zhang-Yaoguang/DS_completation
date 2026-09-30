"""yhay 马赛克:y61A 的 tape0(mtmr 骨架)day6-26 逐天贪心换入族段。包级口径。
快筛=solo seed11 不掉 1200;复筛=v56@500/v59b@501/v57@500 全胜保持且均值不降 300。
产出 scratchpad/y62_main.py + mosaic_y0.json。
"""
import sys, os, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

HERE = Path(__file__).resolve().parent
S = Path("/private/tmp/claude-501/-Users-a1-6-Desktop-PycharmProjects-DS-completation--claude-worktrees-trusting-carson-f2e0f9/59979e26-3970-412a-b349-4361ccd0c249/scratchpad")
FAM = HERE / "yhay_family"

TEMPLATE = (S / "y61A_main.py").read_text()
LINES = TEMPLATE.split("\n")
AIDX = next(i for i, l in enumerate(LINES) if l.startswith("_ACTIONS_JSON = "))
TAPES0 = json.loads(json.loads(LINES[AIDX][len("_ACTIONS_JSON = "):]))

def build(tape0, out):
    tapes = [tape0] + TAPES0[1:]
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

if __name__ == "__main__":
    d_from = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    d_to = int(sys.argv[2]) if len(sys.argv) > 2 else 26
    fam = []
    for f in sorted(FAM.glob("yh0_*.json")):
        if "106843869_0" in f.name:
            continue
        fam.append((f.stem, json.load(open(f))["actions"][:719]))
    print(f"段库 {len(fam)} 条", flush=True)
    cur = [json.loads(json.dumps(a)) for a in TAPES0[0]]
    GJOBS = lambda p: [("g", p, str(S / "v56_main.py"), 500),
                       ("g", p, str(S / "v59b_main.py"), 501),
                       ("g", p, str(S / "v56_main.py"), 501)]
    base_p = str(S / "_ym_base.py"); build(cur, base_p)
    with ProcessPoolExecutor(8) as ex:
        base_solo = one(("solo", base_p, None, 11))
        base_g = list(ex.map(one, GJOBS(base_p)))
        print(f"base solo={base_solo:.0f} gate={[int(x) for x in base_g]}", flush=True)
        n_swap = 0
        for day in range(d_from, d_to + 1):
            s0, s1 = day * 24, day * 24 + 24
            cands = []
            for name, acts in fam:
                d = seg_diff(acts[s0:s1], cur[s0:s1])
                if d > 0:
                    cands.append((d, name, acts))
            cands.sort(key=lambda t: -t[0])
            cands = cands[:12]
            best = None
            jobs, metas = [], []
            for k, (d, name, acts) in enumerate(cands):
                trial = cur[:s0] + [json.loads(json.dumps(a)) for a in acts[s0:s1]] + cur[s1:]
                tp = str(S / f"_ym_{k}.py"); build(trial, tp)
                jobs += [("solo", tp, None, 11)] + GJOBS(tp)
                metas.append((name, trial))
            res = list(ex.map(one, jobs))
            for k, (name, trial) in enumerate(metas):
                solo, g = res[k * 4], res[k * 4 + 1:k * 4 + 4]
                if solo < base_solo - 1200 or any(x <= 0 for x in g):
                    continue
                gm = sum(g) / 3
                if gm > (best[0] if best else sum(base_g) / 3 - 300):
                    best = (gm, name, trial, solo, g)
            if best:
                gm, name, trial, solo, g = best
                cur = trial; n_swap += 1
                print(f"day{day}: SWAP<-{name[:24]} gate={[int(x) for x in g]} solo={solo:.0f}", flush=True)
            else:
                print(f"day{day}: keep", flush=True)
    json.dump({"tape_idx": 0, "actions": cur}, (HERE / "mosaic_y0.json").open("w"))
    build(cur, str(S / "y62_main.py"))
    print(f"done: {n_swap} 天段替换 -> y62_main.py", flush=True)
