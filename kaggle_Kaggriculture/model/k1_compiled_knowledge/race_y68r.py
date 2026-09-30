"""y68r vs y68f 配对 racing：同 seed×同对手 margin 差分 + 配对 t + 重合度。"""
import importlib.util
import itertools
import json
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
POOL = "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/opponent_pool_v1"
OPPS = [
    ("ult", f"tape:{POOL}/tapes/ult_normal.json"),
    ("y67", f"sub:{POOL}/packs/y67_main.py"),
    ("mirror", f"sub:{POOL}/packs/y68f_main.py"),
]
SEEDS = [1009 + 37 * i for i in range(16)]


def one(job):
    which, seed, opp_spec = job
    sys.path.insert(0, "/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness")
    sys.path.insert(0, "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v16_online_fidelity")
    import engine
    import fidelity
    if which == "cand":
        spec = importlib.util.spec_from_file_location(f"r_{seed}", HERE / "y68r_race.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        me = m.agent
    else:
        me = fidelity.make_agent(f"sub:{POOL}/packs/y68f_main.py")
    opp = fidelity.make_agent(opp_spec)
    b0, b1 = engine.play(me, opp, seed=seed)
    return which, seed, opp_spec, b0 - b1, b0


def main():
    jobs = [(w, s, o) for w in ("cand", "parent") for s in SEEDS for _, o in OPPS]
    with ProcessPoolExecutor(max_workers=8) as pool:
        res = list(pool.map(one, jobs))
    m = {}
    for which, seed, opp, margin, own in res:
        m[(which, seed, opp)] = (margin, own)
    diffs, by_opp = [], {}
    for name, ospec in OPPS:
        ds = []
        for s in SEEDS:
            d = m[("cand", s, ospec)][0] - m[("parent", s, ospec)][0]
            ds.append(d)
            diffs.append(d)
        by_opp[name] = ds
        mean = statistics.mean(ds)
        wins = sum(1 for d in ds if d > 0)
        zero = sum(1 for d in ds if d == 0)
        print(f"{name:7s}: mean_d {mean:+8.0f} | +{wins}/0:{zero}/-{len(ds)-wins-zero} "
              f"| range {min(ds):+.0f}~{max(ds):+.0f}")
    mean = statistics.mean(diffs)
    sd = statistics.stdev(diffs)
    t = mean / (sd / len(diffs) ** 0.5) if sd else 0
    print(f"\nALL: mean_d {mean:+.0f}  t={t:.2f}  n={len(diffs)}")
    (HERE / "race_y68r_result.json").write_text(json.dumps(
        {"mean_d": mean, "t": t, "by_opp": by_opp}, indent=1))


if __name__ == "__main__":
    main()
