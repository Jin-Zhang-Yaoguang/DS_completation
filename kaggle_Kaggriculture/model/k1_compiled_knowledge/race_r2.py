"""R2 轮 racing：低弹性锚——A2 收敛方向的表修订变体对决。

变体（假设出处：A2 十代一致收敛 sheep→0/goose→顶格；Majkel 卡片 428 麦/局）：
  v2a 羊换鹅：SHEEP 0、GOOSE 6、COW 8
  v2b 羊换鹅 + 麦锚：同上 + crop_scale.WHEAT 0.5→0.85
  v2c 麦锚单独：仅 crop_scale.WHEAT 0.85
基线继承 R1 判定后的 knowledge.json（含已采纳层）。
"""
import importlib.util
import json
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
POOL = "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/opponent_pool_v1"
KN = json.loads((HERE / "knowledge.json").read_text())
BASE_TU = KN.get("tuning", {})

AB_NEW = [
    {"day": 0, "buys": {"COW": 2}},
    {"day": 2, "buys": {"GOOSE": 3}},
    {"day": 6, "buys": {"COW": 4, "GOOSE": 3}},
    {"day": 9, "buys": {"COW": 2}},
]
CONFIGS = {
    "base": {},
    "v2a": {"kn": {"animal_buys": AB_NEW}},
    "v2b": {"kn": {"animal_buys": AB_NEW},
            "tu": {"crop_scale": {**BASE_TU.get("crop_scale", {}), "WHEAT": 0.85}}},
    "v2c": {"tu": {"crop_scale": {**BASE_TU.get("crop_scale", {}), "WHEAT": 0.85}}},
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
    cfg = CONFIGS[cfg_name]
    ov = dict(cfg.get("kn", {}))
    ov["tuning"] = {**BASE_TU, **cfg.get("tu", {})}
    mod.KN_OVERRIDE = ov
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
            extra = ""
            if cfg != "base":
                d_own = [m[(cfg, s, ospec)][0] - m[("base", s, ospec)][0] for s in SEEDS]
                sd = statistics.stdev(d_own)
                t = statistics.mean(d_own) / (sd / len(d_own) ** 0.5) if sd else 0
                extra = f" | d_own {statistics.mean(d_own):+8.0f} (t={t:.2f}) 胜{sum(1 for d in d_own if d > 0)}/16"
            print(f"  {name:4s}: own {statistics.mean(owns):8.0f} margin {statistics.mean(mgs):+9.0f}{extra}")
            out[cfg][name] = {"own": statistics.mean(owns), "margin": statistics.mean(mgs)}
    (HERE / "race_r2_result.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
