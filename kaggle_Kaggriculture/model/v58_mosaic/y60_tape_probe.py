"""整带替换探测:tape0 <- yhay_family 强带,测痛点局 v56@500 / 保护局 v59b@501 / solo。
用法: python y60_tape_probe.py [topN]
"""
import sys, os, json, subprocess
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

HERE = Path(__file__).resolve().parent
S = "/private/tmp/claude-501/-Users-a1-6-Desktop-PycharmProjects-DS-completation--claude-worktrees-trusting-carson-f2e0f9/59979e26-3970-412a-b349-4361ccd0c249/scratchpad"
FAM = HERE / "yhay_family"
PY = "/opt/anaconda3/bin/python3"

def one(job):
    cand, opp, sd, tag = job
    sys.path.insert(0, str(HERE.parent / "v16_online_fidelity"))
    sys.path.insert(0, str(HERE.parent / "v4_demand_race" / "harness"))
    import fidelity
    if opp == "pass:":
        r = fidelity.play(f"sub:{cand}", "pass:", sd, [])
        return (tag, r["bank"][0])
    r = fidelity.play(f"sub:{cand}", f"sub:{opp}", sd, [])
    return (tag, r["bank"][0] - r["bank"][1])

if __name__ == "__main__":
    topn = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    cands = []
    for f in FAM.glob("yh0_*.json"):
        d = json.load(open(f))
        cands.append((d.get("bank", 0), f))
    cands.sort(reverse=True)
    print("top 段库带:", [(f.name, int(b)) for b, f in cands[:topn]], flush=True)
    jobs = []
    variants = [("base", None)] + [(f.stem, f) for b, f in cands[:topn]]
    for tag, f in variants:
        out = Path(S) / f"y60p_{tag}.py"
        if f is None:
            out.write_text((Path(S) / "y60_main.py").read_text())
        else:
            # 719 步对齐:族带 acts 是 719 条(replay steps1..719)
            acts = json.load(open(f))["actions"][:719]
            tmp = Path(S) / f"_probe_{tag}.json"
            json.dump({"tape_idx": 0, "actions": acts}, tmp.open("w"))
            r = subprocess.run([PY, str(HERE / "build_y60.py"), str(tmp)], capture_output=True, text=True)
            assert "written" in r.stdout, r.stdout + r.stderr
            (Path(S) / "y60_main.py").rename(out)
        jobs += [
            (str(out), str(Path(S) / "v56_main.py"), 500, f"{tag}|v56@500"),
            (str(out), str(Path(S) / "v59b_main.py"), 501, f"{tag}|v59b@501"),
            (str(out), "pass:", 11, f"{tag}|solo11"),
        ]
    with ProcessPoolExecutor(8) as ex:
        for tag, m in ex.map(one, jobs):
            print(f"{tag}: {m:+.0f}", flush=True)
