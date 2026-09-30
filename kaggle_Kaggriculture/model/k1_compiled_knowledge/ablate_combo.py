"""单品压制消融：每次只倾销一个品，测 y68g 掉血量（真实成交口径）。"""
import importlib.util
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
MOS = "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v58_mosaic/dist_backup"


def one(job):
    target, seed = job
    sys.path.insert(0, "/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness")
    sys.path.insert(0, "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v16_online_fidelity")
    import engine
    import fidelity
    spec = importlib.util.spec_from_file_location(f"k1_{seed}_{target}", HERE / "main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    tu = {**json.loads((HERE / "knowledge.json").read_text())["tuning"],
          "fert_specialist": False, "t0_pool_select": False}
    ov = {"tuning": tu}
    if target == "COMBO4":
        tu["dump_mode"] = "targets"
        ov["suppress_targets"] = ["WHEAT", "MILK", "EGG", "WOOL"]
    elif target == "COMBO4_POOL":
        tu["dump_mode"] = "targets"
        tu["t0_pool_select"] = True
        ov["suppress_targets"] = ["WHEAT", "MILK", "EGG", "WOOL"]
    elif target == "ALL_POOL":
        tu["dump_mode"] = True
        tu["t0_pool_select"] = True
    mod.KN_OVERRIDE = ov
    opp = fidelity.make_agent(f"sub:{MOS}/y68g_main.py")
    b0, b1 = engine.play(mod.agent, opp, seed=seed)
    return target, seed, b0, b1


def main():
    targets = [None, "COMBO4", "COMBO4_POOL", "ALL_POOL"]
    seeds = (1009, 1046, 2083, 3120)
    jobs = [(t, s) for t in targets for s in seeds]
    with ProcessPoolExecutor(max_workers=8) as pool:
        res = list(pool.map(one, jobs))
    agg = {}
    for t, s, b0, b1 in res:
        agg.setdefault(t, []).append((b0, b1))
    base_opp = sum(b for _, b in agg[None]) / len(seeds)
    for t in targets:
        v = agg[t]
        me = sum(a for a, _ in v) / len(v)
        opp = sum(b for _, b in v) / len(v)
        print(f"{str(t):11s}: me {me:8.0f} opp {opp:8.0f} (opp掉 {base_opp - opp:+7.0f}) margin {me - opp:+.0f}")


if __name__ == "__main__":
    main()
