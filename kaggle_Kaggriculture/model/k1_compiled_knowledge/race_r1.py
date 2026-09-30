"""R1 轮 racing：基线 / R1a(race) / R1b(shift) / R1ab 四配置配对对决。

主指标：vs y67 的 own bank（收入保卫）；次指标：margin。同 seed 配对差分。
"""
import importlib.util
import json
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
POOL = "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/opponent_pool_v1"
BASE_TU = json.loads((HERE / "knowledge.json").read_text()).get("tuning", {})

CONFIGS = {
    "base": {},
    "r1a": {"race_enabled": True},
    "r1b": {"market_shift_enabled": True, "price_floor_frac": 0.5},
    "r1ab": {"race_enabled": True, "market_shift_enabled": True, "price_floor_frac": 0.5},
}
OPPS = [("y67", f"sub:{POOL}/packs/y67_main.py"), ("ult", f"tape:{POOL}/tapes/ult_normal.json")]
SEEDS = [1009 + 37 * i for i in range(16)]


def one(job):
    cfg_name, seed, opp_spec = job
    sys.path.insert(0, "/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness")
    sys.path.insert(0, "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v16_online_fidelity")
    import engine
    import fidelity
    spec = importlib.util.spec_from_file_location(f"k1_{cfg_name}_{seed}", HERE / "main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.KN_OVERRIDE = {"tuning": {**BASE_TU, **CONFIGS[cfg_name]}}
    opp = fidelity.make_agent(opp_spec)
    b0, b1 = engine.play(mod.agent, opp, seed=seed)
    return cfg_name, seed, opp_spec, b0, b0 - b1


def main():
    jobs = [(c, s, o) for c in CONFIGS for s in SEEDS for _, o in OPPS]
    with ProcessPoolExecutor(max_workers=8) as pool:
        res = list(pool.map(one, jobs))
    m = {(c, s, o): (own, mg) for c, s, o, own, mg in res}
    out = {}
    for cfg in CONFIGS:
        print(f"\n== {cfg}")
        out[cfg] = {}
        for name, ospec in OPPS:
            owns = [m[(cfg, s, ospec)][0] for s in SEEDS]
            mgs = [m[(cfg, s, ospec)][1] for s in SEEDS]
            if cfg != "base":
                d_own = [m[(cfg, s, ospec)][0] - m[("base", s, ospec)][0] for s in SEEDS]
                d_mg = [m[(cfg, s, ospec)][1] - m[("base", s, ospec)][1] for s in SEEDS]
                sd = statistics.stdev(d_own)
                t = statistics.mean(d_own) / (sd / len(d_own) ** 0.5) if sd else 0
                extra = (f" | d_own {statistics.mean(d_own):+8.0f} (t={t:.2f}) "
                         f"d_margin {statistics.mean(d_mg):+8.0f} 胜{sum(1 for d in d_own if d > 0)}/16")
            else:
                extra = ""
            print(f"  {name:4s}: own {statistics.mean(owns):8.0f} margin {statistics.mean(mgs):+9.0f}{extra}")
            out[cfg][name] = {"own": statistics.mean(owns), "margin": statistics.mean(mgs)}
    (HERE / "race_r1_result.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
