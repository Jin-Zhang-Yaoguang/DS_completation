"""A2 日程表搜索：CEM 调 schedule_gen 的 12 个结构参数，对战口径 fitness。

框架内实现：参数经 gen_tables 生成日程表 → KN_OVERRIDE 注入 knowledge 顶层键；
采纳只认 holdout 正增量（写回 knowledge.json 由人工确认后进行）。

用法: /opt/anaconda3/bin/python3 tune_schedule.py [gens] [pop]
产物: tune_schedule_log.jsonl、best_schedule.json
"""
import json
import random
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
POOL = "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/opponent_pool_v1"

from schedule_gen import SCHED_SPACE, DEFAULTS, gen_tables  # noqa: E402

OPPONENTS = [
    ("ult", f"tape:{POOL}/tapes/ult_normal.json"),
    ("y67", f"sub:{POOL}/packs/y67_main.py"),
]
TRAIN_SEEDS = [1009, 2083]
HOLD_SEEDS = [900007, 900060, 900113, 900166]


def vec_to_params(vec):
    p = {}
    for (name, lo, hi, _), v in zip(SCHED_SPACE, vec):
        p[name] = max(lo, min(hi, v))
    return p


def eval_one(job):
    params, seed, opp_spec = job
    import importlib.util
    sys.path.insert(0, "/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness")
    sys.path.insert(0, "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v16_online_fidelity")
    import engine
    import fidelity
    spec = importlib.util.spec_from_file_location(f"k1_s{seed}", HERE / "main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.KN_OVERRIDE = gen_tables(params)
    opp = fidelity.make_agent(opp_spec)
    b0, b1 = engine.play(mod.agent, opp, seed=seed)
    return b0 - b1, b0


def eval_pop(pop, seeds, pool):
    jobs = [(vec_to_params(v), s, o) for v in pop for s in seeds for _, o in OPPONENTS]
    res = list(pool.map(eval_one, jobs))
    k = len(seeds) * len(OPPONENTS)
    fits = [sum(m for m, _ in res[i * k:(i + 1) * k]) / k for i in range(len(pop))]
    owns = [sum(o for _, o in res[i * k:(i + 1) * k]) / k for i in range(len(pop))]
    return fits, owns


def main():
    gens = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    npop = int(sys.argv[2]) if len(sys.argv) > 2 else 14
    elite = max(3, npop // 4)
    rng = random.Random(20260915)
    mu = [DEFAULTS[n] for n, _, _, _ in SCHED_SPACE]
    sd = [(hi - lo) / 4 for _, lo, hi, _ in SCHED_SPACE]
    log = open(HERE / "tune_schedule_log.jsonl", "a")
    best = (list(mu), -1e18)
    with ProcessPoolExecutor(max_workers=8) as pool:
        base_fit, base_own = eval_pop([mu], TRAIN_SEEDS, pool)
        print(f"baseline margin {base_fit[0]:.0f} own {base_own[0]:.0f}", flush=True)
        log.write(json.dumps({"gen": -1, "margin": base_fit[0], "own": base_own[0]}) + "\n")
        log.flush()
        for g in range(gens):
            pop = [list(mu)]
            for _ in range(npop - 1):
                pop.append([rng.gauss(m, s) for m, s in zip(mu, sd)])
            fits, owns = eval_pop(pop, TRAIN_SEEDS, pool)
            ranked = sorted(zip(fits, owns, pop), key=lambda z: -z[0])
            top = ranked[:elite]
            mu = [sum(v[i] for _, _, v in top) / elite for i in range(len(SCHED_SPACE))]
            sd = [max(0.05 * (hi - lo),
                      (sum((v[i] - mu[i]) ** 2 for _, _, v in top) / elite) ** 0.5)
                  for i, (_, lo, hi, _) in enumerate(SCHED_SPACE)]
            if ranked[0][0] > best[1]:
                best = (ranked[0][2], ranked[0][0])
            print(f"gen {g}: best margin {ranked[0][0]:.0f} own {ranked[0][1]:.0f} "
                  f"| {json.dumps(vec_to_params(ranked[0][2]))}", flush=True)
            log.write(json.dumps({"gen": g, "margin": ranked[0][0], "own": ranked[0][1],
                                  "params": vec_to_params(ranked[0][2])}) + "\n")
            log.flush()
        hb, hb_own = eval_pop([best[0]], HOLD_SEEDS, pool)
        hbase, hbase_own = eval_pop([[DEFAULTS[n] for n, _, _, _ in SCHED_SPACE]], HOLD_SEEDS, pool)
        print(f"HOLDOUT best margin {hb[0]:.0f} (own {hb_own[0]:.0f}) "
              f"vs baseline {hbase[0]:.0f} (own {hbase_own[0]:.0f})", flush=True)
        out = {"train_margin": best[1], "holdout_margin": hb[0], "holdout_own": hb_own[0],
               "holdout_baseline_margin": hbase[0], "holdout_baseline_own": hbase_own[0],
               "params": vec_to_params(best[0]), "tables": gen_tables(vec_to_params(best[0]))}
        (HERE / "best_schedule.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
        log.write(json.dumps({"gen": "final", "holdout": hb[0], "baseline": hbase[0]}) + "\n")
        log.close()


if __name__ == "__main__":
    main()
