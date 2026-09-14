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
Y67 = f"sub:{POOL}/packs/y67_main.py"


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
    ov["tuning"] = {**BASE_TU, "fert_specialist": False}
    mod.KN_OVERRIDE = ov
    if opp_spec:
        opp = fidelity.make_agent(opp_spec)
    else:
        def opp(o):
            return {"farmer": ["PASS"], "hands": [], "market": []}
    b0, b1 = __import__("engine").play(mod.agent, opp, seed=seed)
    return b0


def sample_params(rng):
    p = dict(DEFAULTS)
    for (name, lo, hi, d) in SCHED_SPACE:
        # 以默认为中心的截断高斯（先验保守）
        p[name] = min(hi, max(lo, rng.gauss(d, (hi - lo) / 5)))
    return p


def param_dist(a, b):
    d = 0.0
    for (name, lo, hi, _) in SCHED_SPACE:
        d += abs(a[name] - b[name]) / (hi - lo)
    return d


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 32
    rng = random.Random(20260914)
    cands = [dict(DEFAULTS)] + [sample_params(rng) for _ in range(n - 1)]
    with ProcessPoolExecutor(max_workers=8) as pool:
        jobs = [(c, s, None) for c in cands for s in SOLO_SEEDS] + \
               [(c, s, Y67) for c in cands for s in VS_SEEDS]
        res = list(pool.map(_sim_one, jobs))
    k_solo = len(SOLO_SEEDS)
    solo = [statistics.mean(res[i * k_solo:(i + 1) * k_solo]) for i in range(len(cands))]
    off = len(cands) * k_solo
    k_vs = len(VS_SEEDS)
    vs_own = [statistics.mean(res[off + i * k_vs: off + (i + 1) * k_vs]) for i in range(len(cands))]
    base_solo, base_vs = solo[0], vs_own[0]
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
