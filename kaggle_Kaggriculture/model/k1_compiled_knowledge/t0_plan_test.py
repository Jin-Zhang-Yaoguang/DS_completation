"""T0 规划器概念验证（Majkel 假设 B′ 的框架内复现，P1 阶段用 kagsim 代模拟器）。

流程（模拟线上每局的 t0）：
  对每个正式局：t0 用随机爬山（种群 8 × 3 代，每个体=schedule_gen 12 参数扰动，
  fitness=vs PASS 全季自模拟 bank）选出本局参数 → 用该参数打正式局。
  随机源 per-局独立 → 每局参数不同 → 轨迹逐局不同（门控 2 机制）。

产出三问的答案：
  1. t0 搜出的参数比静态表强多少（solo）？
  2. 对战（vs y67）是否也强（solo-fitness 的对战外推性）？
  3. 重合度降多少？

用法: /opt/anaconda3/bin/python3 t0_plan_test.py
"""
import importlib.util
import itertools
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
EVAL_SEEDS = [1009, 1046, 2083, 3120, 4157, 5194]


def _sim_one(job):
    """一次评估：给定参数与 seed，跑一局，返回 (bank, margin, trace?)"""
    params, seed, opp_spec, record = job
    sys.path.insert(0, "/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness")
    sys.path.insert(0, "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v16_online_fidelity")
    import engine
    import fidelity
    spec = importlib.util.spec_from_file_location(f"k1_t0_{seed}_{record}", HERE / "main.py")
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
    k = engine.load_kagsim()
    g = k.Game(seed=seed)
    tr = []
    fb = {"farmer": ["PASS"], "hands": [], "market": []}
    while not (g.done() if callable(g.done) else g.done):
        o0, o1 = g.observe(0), g.observe(1)
        try:
            a0 = mod.agent(o0)
        except Exception:
            a0 = dict(fb)
        try:
            a1 = opp(o1)
        except Exception:
            a1 = dict(fb)
        if record:
            tr.append(json.dumps([a0.get("farmer") or []] + list(a0.get("hands") or [])))
        g.step(a0, a1)
    return float(g.reward(0)), float(g.reward(0)) - float(g.reward(1)), tr


def t0_search(game_seed, pool, pop=8, gens=3):
    """模拟该局 t0 的随机爬山：fitness = vs PASS 自模拟（用与正式局不同的内部 seed，
    因为线上不知道真 seed——内部模拟只能代表期望局面）。"""
    rng = random.Random()  # 系统熵源：每局不同（B' 机制核心）
    sim_seeds = [rng.randrange(10**6) for _ in range(2)]
    best = dict(DEFAULTS)
    best_fit = None
    for g in range(gens):
        cands = [dict(best)]
        for _ in range(pop - 1):
            c = dict(best)
            for (name, lo, hi, _d) in SCHED_SPACE:
                if rng.random() < 0.4:
                    c[name] = min(hi, max(lo, c[name] + rng.gauss(0, (hi - lo) / 6)))
            cands.append(c)
        jobs = [(c, s, None, False) for c in cands for s in sim_seeds]
        res = list(pool.map(_sim_one, jobs))
        fits = [statistics.mean(res[i * 2 + j][0] for j in range(2)) for i in range(len(cands))]
        bi = max(range(len(cands)), key=lambda i: fits[i])
        best, best_fit = cands[bi], fits[bi]
    return best, best_fit


def main():
    with ProcessPoolExecutor(max_workers=8) as pool:
        # 静态基线
        static_solo = [_r[0] for _r in pool.map(_sim_one, [(None, s, None, False) for s in EVAL_SEEDS])]
        y67 = f"sub:{POOL}/packs/y67_main.py"
        static_vs = [(m, o) for o, m, _ in pool.map(_sim_one, [(None, s, y67, False) for s in EVAL_SEEDS])]
        print(f"静态表: solo {statistics.mean(static_solo):.0f} | vs y67 own "
              f"{statistics.mean(o for _, o in static_vs):.0f}", flush=True)

        # T0 规划：每局独立搜索
        t0_solo, t0_vs_own, traces, chosen = [], [], [], []
        for s in EVAL_SEEDS:
            params, fit = t0_search(s, pool)
            chosen.append(params)
            solo_b, _, tr = _sim_one((params, s, None, True))
            _, mg, _ = _sim_one((params, s, y67, False))
            own = mg + 0  # own 直接再算
            b_vs, _, _ = _sim_one((params, s, y67, False))
            t0_solo.append(solo_b)
            t0_vs_own.append(b_vs)
            traces.append(tr)
            print(f"  seed {s}: t0搜索 fit {fit:.0f} → solo {solo_b:.0f} vs_y67_own {b_vs:.0f} "
                  f"| params straw_peak={params['straw_peak']:.0f} wheat_peak={params['wheat_peak']:.0f} "
                  f"cow={params['cow_total']:.1f}", flush=True)
        print(f"\nT0 规划: solo {statistics.mean(t0_solo):.0f} (静态 {statistics.mean(static_solo):.0f}) "
              f"| vs y67 own {statistics.mean(t0_vs_own):.0f} (静态 {statistics.mean(o for _, o in static_vs):.0f})")
        # 重合度（T0 版之间）
        ovs = []
        for a, b in itertools.combinations(range(len(traces)), 2):
            t1, t2 = traces[a], traces[b]
            n = min(len(t1), len(t2))
            ovs.append(sum(1 for x, y in zip(t1[:n], t2[:n]) if x == y) / max(1, n))
        print(f"T0 版重合中位 {statistics.median(ovs):.3f} 范围 {min(ovs):.3f}-{max(ovs):.3f} "
              f"(静态 RA 后基线 ~0.25)")
        (HERE / "t0_plan_result.json").write_text(json.dumps(
            {"static_solo": statistics.mean(static_solo), "t0_solo": statistics.mean(t0_solo),
             "t0_overlap_median": statistics.median(ovs), "chosen": chosen}, indent=1))


if __name__ == "__main__":
    main()
