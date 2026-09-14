"""T0v2 离线方案池生成：随机采样日程参数组 → 双口径评估 → 过滤入池。

池 = t0 随机选择的候选方案集合（写入 knowledge.json 的 plan_pool 键）。
质量地板：vs y67 own 不低于静态表 -2k 且 solo 不低于 -6k；
多样性：入池方案两两参数距离达标（避免池退化成一个点）。

用法: /opt/anaconda3/bin/python3 build_plan_pool.py [n_samples]
"""
import importlib.util
import json
import random
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
POOL = "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/opponent_pool_v1"
sys.path.insert(0, str(HERE))
from schedule_gen import SCHED_SPACE, DEFAULTS, gen_tables  # noqa: E402

BASE_TU = json.loads((HERE / "knowledge.json").read_text()).get("tuning", {})
SOLO_SEEDS = [1009, 2083]
VS_SEEDS = [1046, 3120]
Y67 = "sub:/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v58_mosaic/dist_backup/y68g_main.py"


def _sim_one(job):
    params, seed, opp_spec = job
    sys.path.insert(0, "/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness")
    sys.path.insert(0, "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v16_online_fidelity")
    import engine
    import fidelity
    spec = importlib.util.spec_from_file_location(f"k1_pp_{seed}_{abs(hash(str(params)))%9999}", HERE / "main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ov = gen_tables(params) if params else {}
    te = ov.pop("tuning_extra", {}) if isinstance(ov, dict) else {}
    ov["tuning"] = {**BASE_TU, "fert_specialist": False, "t0_pool_select": False, **te}
    # ^ 必须关 t0 池选择：否则 t0 又随机覆盖候选表，评估被旧池污染（2026-09-15 bug）
    mod.KN_OVERRIDE = ov
    if opp_spec:
        opp = fidelity.make_agent(opp_spec)
    else:
        def opp(o):
            return {"farmer": ["PASS"], "hands": [], "market": []}
    b0, b1 = __import__("engine").play(mod.agent, opp, seed=seed)
    return b0


MAJ_ANCHOR = {**DEFAULTS, "melon_d0": 6, "wheat_d0": 8, "sheep_d0": 3, "sheep_total": 3,
              "cow_total": 8, "batch2_day": 7, "day0_animal_frac": 1.0, "goose_total": 2,
              "cash_floor_early": 150}


def sample_params(rng, anchor=None):
    center = anchor or DEFAULTS
    p = dict(center)
    for (name, lo, hi, _d) in SCHED_SPACE:
        p[name] = min(hi, max(lo, rng.gauss(center[name], (hi - lo) / (8 if anchor else 5))))
    return p


def param_dist(a, b):
    d = 0.0
    for (name, lo, hi, _) in SCHED_SPACE:
        d += abs(a[name] - b[name]) / (hi - lo)
    return d


def eval_batch(cands, solo_seeds, vs_seeds, pool):
    jobs = [(c, s, None) for c in cands for s in solo_seeds] + \
           [(c, s, Y67) for c in cands for s in vs_seeds]
    res = list(pool.map(_sim_one, jobs))
    ks = len(solo_seeds)
    solo = [statistics.mean(res[i * ks:(i + 1) * ks]) for i in range(len(cands))]
    off = len(cands) * ks
    kv = len(vs_seeds)
    vs_own = [statistics.mean(res[off + i * kv: off + (i + 1) * kv]) for i in range(len(cands))]
    return solo, vs_own


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 32
    rng = random.Random(20260915)
    half = (n - 2) // 2
    cands = [dict(DEFAULTS), dict(MAJ_ANCHOR)] + \
        [sample_params(rng) for _ in range(half)] + \
        [sample_params(rng, MAJ_ANCHOR) for _ in range(n - 2 - half)]
    with ProcessPoolExecutor(max_workers=8) as pool:
        # successive halving：rung0 粗筛（2+2 seed）→ top32 精筛（+2 solo +4 vs）
        solo0, vs0 = eval_batch(cands, SOLO_SEEDS, VS_SEEDS, pool)
        order = sorted(range(len(cands)), key=lambda i: -(vs0[i] + 0.3 * solo0[i]))
        keep = sorted(order[:32] + [0])          # 静态基线保留对照
        cands2 = [cands[i] for i in keep]
        solo1, vs1 = eval_batch(cands2, [5194, 6231], [7268, 8305, 9342, 1009], pool)
        # 总评 = 两轮加权（rung1 seed 多，权重 2）
        solo = [(solo0[keep[i]] + 2 * solo1[i]) / 3 for i in range(len(cands2))]
        vs_own = [(vs0[keep[i]] + 2 * vs1[i]) / 3 for i in range(len(cands2))]
        cands = cands2
    base_i = keep.index(0)
    base_solo, base_vs = solo[base_i], vs_own[base_i]
    print(f"静态表: solo {base_solo:.0f} vs_own {base_vs:.0f}")
    # 过滤 + 多样化入池
    scored = sorted(range(len(cands)), key=lambda i: -(vs_own[i] + 0.3 * solo[i]))
    plan_pool = []
    for i in scored:
        if vs_own[i] < base_vs - 2000 or solo[i] < base_solo - 6000:
            continue
        if any(param_dist(cands[i], p["params"]) < 0.8 for p in plan_pool):
            continue
        plan_pool.append({"params": cands[i], "solo": round(solo[i]), "vs_own": round(vs_own[i]),
                          "tables": gen_tables(cands[i])})
        print(f"  入池 #{len(plan_pool)}: solo {solo[i]:.0f} vs_own {vs_own[i]:.0f} "
              f"straw_peak={cands[i]['straw_peak']:.0f} wheat_peak={cands[i]['wheat_peak']:.0f} "
              f"cow={cands[i]['cow_total']:.1f} goose={cands[i]['goose_total']:.1f}")
        if len(plan_pool) >= 10:
            break
    (HERE / "plan_pool.json").write_text(json.dumps(plan_pool, indent=1))
    print(f"\n方案池 {len(plan_pool)} 条 -> plan_pool.json")


if __name__ == "__main__":
    main()
