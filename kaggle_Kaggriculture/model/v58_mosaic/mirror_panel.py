"""镜像面板:候选 vs v56/v57/v58 @ seed500/501。用法: python mirror_panel.py <cand_path>"""
import sys, os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

HERE = Path(__file__).resolve().parent
S = "/private/tmp/claude-501/-Users-a1-6-Desktop-PycharmProjects-DS-completation--claude-worktrees-trusting-carson-f2e0f9/59979e26-3970-412a-b349-4361ccd0c249/scratchpad"
PACKS = {
    "v56": f"{S}/v56_main.py",
    "v57": f"{S}/yhay81_0908_extract/v57_main.py",
    "v58": f"{S}/v58_main.py",
}

def one(job):
    cand, name, opp, sd = job
    if name == "v57":
        os.chdir(Path(opp).parent)
    sys.path.insert(0, str(HERE.parent / "v16_online_fidelity"))
    sys.path.insert(0, str(HERE.parent / "v4_demand_race" / "harness"))
    import fidelity
    r = fidelity.play(f"sub:{cand}", f"sub:{opp}", sd, [])
    return (name, sd, r["bank"][0] - r["bank"][1])

if __name__ == "__main__":
    cand = str(Path(sys.argv[1]).resolve())
    jobs = [(cand, n, p, sd) for n, p in PACKS.items() for sd in (500, 501)]
    with ProcessPoolExecutor(6) as ex:
        for name, sd, m in ex.map(one, jobs):
            print(f"vs {name} seed{sd}: {m:+.0f}", flush=True)
