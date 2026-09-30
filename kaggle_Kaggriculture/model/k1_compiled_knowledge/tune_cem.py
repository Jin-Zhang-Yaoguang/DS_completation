"""S0 离线搜索：CEM 调 K1 tuning 旋钮，fitness = solo(vs PASS) 多 seed 均值。

用法: /opt/anaconda3/bin/python3 tune_cem.py [gens] [pop]
产出: tune_log.jsonl（每代记录）、best_tuning.json（终选+holdout 复核）
"""
import json
import random
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent

# (name, kind, lo, hi)  kind: i=int, f=float, b=0/1
SPACE = [
    ("plant_per_day_cap", "i", 4, 10),
    ("water_deadline_hour", "i", 12, 20),
    ("feed_deadline_hour", "i", 14, 20),
    ("harvest_yield_min", "i", 1, 3),
    ("feeder_mode", "b", 0, 1),
    ("cash_floor", "i", 150, 800),
    ("straw_scale", "f", 0.6, 1.4),
    ("wheat_scale", "f", 0.5, 1.6),
    ("animal_scale", "f", 0.6, 1.5),
    ("fert_scale", "f", 0.4, 2.0),
]
TRAIN_SEEDS = [1009, 1046, 2083, 3120]
HOLD_SEEDS = [900007, 900060, 900113, 900166, 900219, 900272, 900325, 900378]


def to_tuning(vec):
    tu = {}
    cs = {}
    for (name, kind, lo, hi), v in zip(SPACE, vec):
        v = max(lo, min(hi, v))
        if kind in ("i", "b"):
            v = int(round(v))
        if name == "straw_scale":
            cs["STRAWBERRY"] = round(v, 3)
        elif name == "wheat_scale":
            cs["WHEAT"] = round(v, 3)
        else:
            tu[name] = round(v, 3) if kind == "f" else v
    tu["crop_scale"] = cs
    return tu


def eval_one(job):
    tuning, seed = job
    import importlib.util
    sys.path.insert(0, "/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness")
    import engine
    spec = importlib.util.spec_from_file_location(f"k1_t{seed}", HERE / "main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.KN_OVERRIDE = {"tuning": tuning}

    def pa(o):
        return {"farmer": ["PASS"], "hands": [], "market": []}

    b0, _ = engine.play(mod.agent, pa, seed=seed)
    return b0


def eval_pop(pop, seeds, pool):
    jobs = [(to_tuning(vec), s) for vec in pop for s in seeds]
    results = list(pool.map(eval_one, jobs))
    fits = []
    k = len(seeds)
    for i in range(len(pop)):
        fits.append(sum(results[i * k:(i + 1) * k]) / k)
    return fits


def main():
    gens = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    npop = int(sys.argv[2]) if len(sys.argv) > 2 else 16
    elite = max(3, npop // 4)
    rng = random.Random(20260913)
    mu = [(lo + hi) / 2 for _, _, lo, hi in SPACE]
    # 以当前默认为初始均值
    defaults = {"plant_per_day_cap": 6, "water_deadline_hour": 16, "feed_deadline_hour": 18,
                "harvest_yield_min": 2, "feeder_mode": 1, "cash_floor": 300,
                "straw_scale": 1.0, "wheat_scale": 1.0, "animal_scale": 1.0, "fert_scale": 1.0}
    mu = [defaults[n] for n, _, _, _ in SPACE]
    sd = [(hi - lo) / 4 for _, _, lo, hi in SPACE]
    log = open(HERE / "tune_log.jsonl", "a")
    best = (None, -1e18)
    with ProcessPoolExecutor(max_workers=8) as pool:
        # 基线（当前默认）
        base_fit = eval_pop([mu], TRAIN_SEEDS, pool)[0]
        print(f"baseline fitness {base_fit:.0f}", flush=True)
        log.write(json.dumps({"gen": -1, "fit": base_fit, "tuning": to_tuning(mu)}) + "\n")
        log.flush()
        for g in range(gens):
            pop = [mu]  # 精英保留当前均值
            for _ in range(npop - 1):
                pop.append([rng.gauss(m, s) for m, s in zip(mu, sd)])
            fits = eval_pop(pop, TRAIN_SEEDS, pool)
            ranked = sorted(zip(fits, pop), key=lambda z: -z[0])
            top = ranked[:elite]
            mu = [sum(v[i] for _, v in top) / elite for i in range(len(SPACE))]
            sd = [max(0.05 * (hi - lo),
                      (sum((v[i] - mu[i]) ** 2 for _, v in top) / elite) ** 0.5)
                  for i, (_, _, lo, hi) in enumerate(SPACE)]
            if ranked[0][0] > best[1]:
                best = (ranked[0][1], ranked[0][0])
            print(f"gen {g}: best {ranked[0][0]:.0f} elite_mean {sum(f for f, _ in top)/elite:.0f} "
                  f"| {to_tuning(ranked[0][1])}", flush=True)
            log.write(json.dumps({"gen": g, "fit": ranked[0][0], "tuning": to_tuning(ranked[0][1])}) + "\n")
            log.flush()
        # holdout 复核：best vs baseline
        hold_best = eval_pop([best[0]], HOLD_SEEDS, pool)[0]
        hold_base = eval_pop([[defaults[n] for n, _, _, _ in SPACE]], HOLD_SEEDS, pool)[0]
        print(f"HOLDOUT best {hold_best:.0f} vs baseline {hold_base:.0f} (train best {best[1]:.0f})", flush=True)
        out = {"train_fit": best[1], "holdout_fit": hold_best, "holdout_baseline": hold_base,
               "tuning": to_tuning(best[0])}
        (HERE / "best_tuning.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
        log.write(json.dumps({"gen": "final", **out}) + "\n")
        log.close()


if __name__ == "__main__":
    main()
