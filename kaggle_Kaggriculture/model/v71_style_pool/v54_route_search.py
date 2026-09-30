"""B 阶段·同族子集:V54 基线,vs V52/V53,seed 扫商店组合 → 每格 基线+全部候选带 t144 强制。"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
CAND = [-1, 0, 1, 3, 5, 7, 9, 100, 101, 103, 107, 110, 112, 115, 118, 120, 123, 126, 128]
def one(job):
    opp, seed, rid = job
    os.environ["KAG_FORCE_ROUTE"] = str(rid)
    sys.path.insert(0, str(M/"v16_online_fidelity")); sys.path.insert(0, str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    me = fidelity.make_agent(f"sub:{HERE}/agents/v54fr_main.py")
    op = fidelity.make_agent(f"sub:{HERE}/agents/{opp}_main.py")
    k = engine.load_kagsim(); g = k.Game(seed=seed); t = 0; combo = None
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]; a = [me(obs[0]), op(obs[1])]; g.step(a[0], a[1]); t += 1
        if t == 146: combo = "|".join(((g.observe(0).get("town") or {}).get("unlocked_shops") or [])[:2])
    return opp, seed, rid, combo, float(g.reward(0) - g.reward(1))
if __name__ == "__main__":
    jobs = [(o2, s, r) for o2 in ("v52", "v53") for s in range(9100, 9152) for r in CAND]
    print("任务", len(jobs), flush=True)
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(one, jobs, chunksize=3))
    json.dump([list(r) for r in res], open(HERE/"v54_route_search.json", "w"))
    per = collections.defaultdict(dict)
    for opp, sd, rid, c, m in res:
        if m is not None: per[(opp, sd, c)][rid] = m
    base_w = sum(1 for v in per.values() if v.get(-1, 0) > 0)
    orc = sum(1 for v in per.values() if max(v.values()) > 0)
    print(f"格 {len(per)};基线胜 {base_w};逐格事后最优胜 {orc}")
    print("done")
