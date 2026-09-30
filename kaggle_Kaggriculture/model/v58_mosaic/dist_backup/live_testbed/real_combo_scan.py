"""按实战行为扫 seed 的商店组合:y68r2 vs V41 跑到 t145 读 unlocked_shops[:2];前 40 seed 另跑 y68r2 自对局交叉核对。"""
import sys, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
def one(job):
    sd, opp = job
    sys.path.insert(0, str(M / "v16_online_fidelity")); sys.path.insert(0, str(M / "v4_demand_race" / "harness"))
    import fidelity, engine
    a = fidelity.make_agent(f"sub:{S}/y68r2_main.py")
    b = fidelity.make_agent(f"sub:{S}/{opp}")
    k = engine.load_kagsim(); g = k.Game(seed=sd)
    for _ in range(145):
        g.step(a(g.observe(0)), b(g.observe(1)))
    return sd, opp, "|".join(((g.observe(0).get("town") or {}).get("unlocked_shops") or [])[:2])
if __name__ == "__main__":
    seeds = list(range(3000, 3600))
    jobs = [(sd, "kernels_0914/v41_agent.py") for sd in seeds] + [(sd, "y68r2_main.py") for sd in seeds[:40]]
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(one, jobs, chunksize=4))
    main = {sd: c for sd, o, c in res if "v41" in o}
    cross = {sd: c for sd, o, c in res if "y68r2" in o}
    agree = sum(main[s] == cross[s] for s in cross)
    print(f"交叉核对:vs V41 与 自对局 组合一致 {agree}/{len(cross)}")
    by = {}
    for sd, c in main.items():
        if "YARN_STORE" in c.split("|"): continue
        by.setdefault(c, []).append(sd)
    json.dump(by, open(S / "real_combo_seeds.json", "w"))
    print(f"非YARN 组合 {len(by)} 种;YARN 局占比 {sum('YARN_STORE' in c for c in main.values())/len(main):.0%}")
    print("每组合 seed 数:", {c: len(v) for c, v in sorted(by.items(), key=lambda kv: len(kv[1]))})
