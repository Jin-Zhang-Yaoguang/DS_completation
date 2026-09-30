"""S0 对战口径搜索：CEM 调 K1 旋钮，fitness = 对分层对手的平均 margin。

solo 口径已证伪（solo 93k → 对战 17-40k：对 PASS 优化出的高价品集中组合
在共享市场竞争下崩溃）。本搜索用真实对手做 fitness。

用法: /opt/anaconda3/bin/python3 tune_vs.py [gens] [pop]
产出: tune_vs_log.jsonl、best_tuning_vs.json
"""
import json
import random
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
POOL = "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/opponent_pool_v1"

from tune_cem import SPACE, to_tuning  # noqa: E402

OPPONENTS = [
    ("ult", f"tape:{POOL}/tapes/ult_normal.json"),
    ("y67", f"sub:{POOL}/packs/y67_main.py"),
]
TRAIN_SEEDS = [1009, 2083]
HOLD_SEEDS = [900007, 900060, 900113, 900166]


def eval_one(job):
    tuning, seed, opp_spec = job
    import importlib.util
    sys.path.insert(0, "/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness")
    sys.path.insert(0, "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v16_online_fidelity")
    import engine
    import fidelity
    spec = importlib.util.spec_from_file_location(f"k1_vs{seed}", HERE / "main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.KN_OVERRIDE = {"tuning": tuning}
    opp = fidelity.make_agent(opp_spec)
    b0, b1 = engine.play(mod.agent, opp, seed=seed)
    return b0 - b1, b0


def eval_pop(pop, seeds, pool):
    jobs = [(to_tuning(vec), s, ospec) for vec in pop for s in seeds for _, ospec in OPPONENTS]
    results = list(pool.map(eval_one, jobs))
    k = len(seeds) * len(OPPONENTS)
    fits, owns = [], []
    for i in range(len(pop)):
        chunk = results[i * k:(i + 1) * k]
        fits.append(sum(m for m, _ in chunk) / k)
        owns.append(sum(o for _, o in chunk) / k)
    return fits, owns


def main():
    gens = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    npop = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    elite = max(3, npop // 4)
    rng = random.Random(20260914)
    start = json.loads((HERE / "knowledge.json").read_text()).get("tuning", {})
    defaults = {"plant_per_day_cap": start.get("plant_per_day_cap", 6),
                "water_deadline_hour": start.get("water_deadline_hour", 16),
                "feed_deadline_hour": start.get("feed_deadline_hour", 18),
                "harvest_yield_min": start.get("harvest_yield_min", 2),
                "feeder_mode": start.get("feeder_mode", 1),
                "cash_floor": start.get("cash_floor", 300),
                "straw_scale": start.get("crop_scale", {}).get("STRAWBERRY", 1.0),
                "wheat_scale": start.get("crop_scale", {}).get("WHEAT", 1.0),
                "animal_scale": start.get("animal_scale", 1.0),
                "fert_scale": start.get("fert_scale", 1.0)}
    mu = [defaults[n] for n, _, _, _ in SPACE]
    sd = [(hi - lo) / 4 for _, _, lo, hi in SPACE]
    log = open(HERE / "tune_vs_log.jsonl", "a")
    best = (list(mu), -1e18)
    with ProcessPoolExecutor(max_workers=8) as pool:
        base_fit, base_own = eval_pop([mu], TRAIN_SEEDS, pool)
        print(f"baseline margin {base_fit[0]:.0f} own {base_own[0]:.0f}", flush=True)
        log.write(json.dumps({"gen": -1, "margin": base_fit[0], "own": base_own[0],
                              "tuning": to_tuning(mu)}) + "\n")
        log.flush()
        for g in range(gens):
            pop = [list(mu)]
            for _ in range(npop - 1):
                pop.append([rng.gauss(m, s) for m, s in zip(mu, sd)])
            fits, owns = eval_pop(pop, TRAIN_SEEDS, pool)
            ranked = sorted(zip(fits, owns, pop), key=lambda z: -z[0])
            top = ranked[:elite]
            mu = [sum(v[i] for _, _, v in top) / elite for i in range(len(SPACE))]
            sd = [max(0.05 * (hi - lo),
                      (sum((v[i] - mu[i]) ** 2 for _, _, v in top) / elite) ** 0.5)
                  for i, (_, _, lo, hi) in enumerate(SPACE)]
            if ranked[0][0] > best[1]:
                best = (ranked[0][2], ranked[0][0])
            print(f"gen {g}: best margin {ranked[0][0]:.0f} own {ranked[0][1]:.0f} "
                  f"| {to_tuning(ranked[0][2])}", flush=True)
            log.write(json.dumps({"gen": g, "margin": ranked[0][0], "own": ranked[0][1],
                                  "tuning": to_tuning(ranked[0][2])}) + "\n")
            log.flush()
        hold_best, hb_own = eval_pop([best[0]], HOLD_SEEDS, pool)
        hold_base, _ = eval_pop([[defaults[n] for n, _, _, _ in SPACE]], HOLD_SEEDS, pool)
        print(f"HOLDOUT best margin {hold_best[0]:.0f} (own {hb_own[0]:.0f}) vs baseline {hold_base[0]:.0f}", flush=True)
        out = {"train_margin": best[1], "holdout_margin": hold_best[0], "holdout_own": hb_own[0],
               "holdout_baseline_margin": hold_base[0], "tuning": to_tuning(best[0])}
        (HERE / "best_tuning_vs.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
        log.write(json.dumps({"gen": "final", **out}) + "\n")
        log.close()


if __name__ == "__main__":
    main()
