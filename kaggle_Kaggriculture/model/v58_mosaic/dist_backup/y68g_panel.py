import sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
def one(job):
    cand, opp, sd = job
    sys.path.insert(0, str(M / "v16_online_fidelity"))
    sys.path.insert(0, str(M / "v4_demand_race" / "harness"))
    import fidelity
    r = fidelity.play(cand, opp, sd, [])
    return r["bank"][0] - r["bank"][1]
if __name__ == "__main__":
    G = f"sub:{S}/y68g_main.py"; F = f"sub:{S}/y68f_main.py"
    V38 = f"sub:{S}/kernels_0913/v38_main.py"
    jobs = [(G, F, sd) for sd in (500, 501, 600, 601)]
    jobs += [(G, V38, sd) for sd in (500, 501)]
    jobs += [(F, V38, sd) for sd in (500, 501)]
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(one, jobs))
    labs = ["g_vs_f@500","g_vs_f@501","g_vs_f@600","g_vs_f@601","g_vs_v38@500","g_vs_v38@501","f_vs_v38@500","f_vs_v38@501"]
    for l, m in zip(labs, res):
        print(f"{l}: {m:+.0f}")
