"""y68v 开局下的实战商店组合重扫:y68v vs V43 跑到 t146,600 seed;输出含 FARMERS_MARKET 的组合 → seed。"""
import sys, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
def one(sd):
    sys.path.insert(0, str(M / "v16_online_fidelity")); sys.path.insert(0, str(M / "v4_demand_race" / "harness"))
    import fidelity, engine
    a = fidelity.make_agent(f"sub:{S}/y68v_main.py"); b = fidelity.make_agent(f"sub:{S}/kernels_0915/v43_agent.py")
    k = engine.load_kagsim(); g = k.Game(seed=sd)
    for _ in range(146):
        g.step(a(g.observe(0)), b(g.observe(1)))
    return sd, "|".join(((g.observe(0).get("town") or {}).get("unlocked_shops") or [])[:2])
if __name__ == "__main__":
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(one, range(3600, 4800), chunksize=4))
    by = {}
    for sd, c in res: by.setdefault(c, []).append(sd)
    json.dump(by, open(S / "combo_seeds_y68v_b.json", "w"))
    old = json.load(open(S / "combo_seeds_y68v.json"))
    old_map = {sd: c for c, v in old.items() for sd in v}
    changed = sum(1 for sd, c in res if sd in old_map and old_map[sd] != c)
    print(f"与 y68r2 开局扫描相比,组合改变的 seed:{changed}/{sum(1 for sd,_ in res if sd in old_map)}(非YARN 可比部分)")
    fm = {c: v for c, v in by.items() if "FARMERS_MARKET" in c.split("|")}
    print(f"含 FARMERS_MARKET 的组合 {len(fm)} 种,共 {sum(len(v) for v in fm.values())} seed / 600:")
    for c, v in sorted(fm.items(), key=lambda kv: -len(kv[1])):
        print(f"   {c:34s} {len(v):3d}")
