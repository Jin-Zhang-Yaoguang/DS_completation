"""真正的迭代搜索（用户 2026-09-15 升级指令）：CEM + 三疫苗，锚定 Majkel 路线。

三疫苗（本项目付过学费的）：
  1. fitness = 对战 own 为主 + solo 保底（病态解免疫：压对手不涨自己不算好）
  2. 每代 successive halving 评估（噪声免疫：粗筛 2seed → 精评再加 4seed）
  3. 每 3 代轮换训练 seed + 终选 8 holdout 复核（赢者诅咒免疫）
初始化：mu = MAJ_ANCHOR（贴近 Majkel 路线），现有 plan_pool 方案注入首代。
分工：LLM 只做蒸馏（维度进 SCHED_SPACE）与验证（判读结果）；参数全交搜索。

用法: /opt/anaconda3/bin/python3 tune_iter.py [gens] [pop]
产物: tune_iter_log.jsonl、best_iter.json、迭代后的 plan_pool_iter.json（top6 入池）
"""
import json
import random
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from schedule_gen import SCHED_SPACE, DEFAULTS, gen_tables  # noqa: E402
from build_plan_pool import MAJ_ANCHOR, _sim_one, Y67, param_dist  # noqa: E402

BASE_SOLO_W = 0.25   # fitness = vs_own + 0.25*solo
SEED_BANK = [1009, 1046, 2083, 3120, 5194, 6231, 7268, 8305, 9342, 10379, 11416, 12453]
HOLD_SEEDS = [900007, 900060, 900113, 900166, 900219, 900272, 900325, 900378]


def clamp(vec):
    return [min(hi, max(lo, v)) for v, (_, lo, hi, _) in zip(vec, SCHED_SPACE)]


def to_params(vec):
    return {name: v for (name, _, _, _), v in zip(SCHED_SPACE, clamp(vec))}


def eval_cands(cands, vs_seeds, solo_seeds, pool):
    jobs = [(to_params(c), s, Y67) for c in cands for s in vs_seeds] + \
           [(to_params(c), s, None) for c in cands for s in solo_seeds]
    res = list(pool.map(_sim_one, jobs))
    kv, ks = len(vs_seeds), len(solo_seeds)
    out = []
    for i in range(len(cands)):
        vs = statistics.mean(res[i * kv:(i + 1) * kv])
        off = len(cands) * kv
        so = statistics.mean(res[off + i * ks: off + (i + 1) * ks])
        out.append((vs + BASE_SOLO_W * so, vs, so))
    return out


def main():
    gens = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    npop = int(sys.argv[2]) if len(sys.argv) > 2 else 28
    elite_n = max(4, npop // 4)
    rng = random.Random()
    mu = [MAJ_ANCHOR.get(n, d) for n, _, _, d in SCHED_SPACE]
    bi = HERE / "best_iter.json"
    if bi.exists():  # warm start:上轮 holdout 最优作起点
        cands_prev = json.loads(bi.read_text()).get("candidates") or []
        if cands_prev:
            top_prev = max(cands_prev, key=lambda c: c["hold_fit"])
            mu = [top_prev["params"].get(n, MAJ_ANCHOR.get(n, d)) for n, _, _, d in SCHED_SPACE]
            print(f"warm start from best_iter (hold_fit {top_prev['hold_fit']:.0f})", flush=True)
    sd = [(hi - lo) / 5 for _, lo, hi, _ in SCHED_SPACE]
    # 首代注入现有池（先验保留）
    seed_pool = []
    pp = HERE / "plan_pool.json"
    if pp.exists():
        for p in json.loads(pp.read_text())[:6]:
            seed_pool.append([p["params"].get(n, d) for n, _, _, d in SCHED_SPACE])
    log = open(HERE / "tune_iter_log.jsonl", "a")
    best = (None, -1e18, None)
    with ProcessPoolExecutor(max_workers=8) as pool:
        for g in range(gens):
            bank_off = (g // 3) * 2 % 6
            train_vs = SEED_BANK[bank_off:bank_off + 2]
            train_solo = SEED_BANK[bank_off + 6:bank_off + 7]
            cands = [list(mu)] + seed_pool[:max(0, npop // 4 - 1)]
            while len(cands) < npop:
                cands.append([rng.gauss(m, s) for m, s in zip(mu, sd)])
            seed_pool = []
            # halving: rung0 粗筛
            f0 = eval_cands(cands, train_vs, train_solo, pool)
            order = sorted(range(len(cands)), key=lambda i: -f0[i][0])
            top = [cands[i] for i in order[:npop // 2]]
            # rung1 精评（追加 seed）
            extra_vs = SEED_BANK[(bank_off + 2) % 6:(bank_off + 2) % 6 + 3]
            extra_solo = SEED_BANK[(bank_off + 7) % 12:(bank_off + 7) % 12 + 1]
            f1 = eval_cands(top, extra_vs, extra_solo, pool)
            total = [( (f0[order[i]][0] + 2 * f1[i][0]) / 3, f1[i][1], f1[i][2], top[i])
                     for i in range(len(top))]
            total.sort(key=lambda z: -z[0])
            elites = total[:elite_n]
            mu = [statistics.mean(e[3][d] for e in elites) for d in range(len(SCHED_SPACE))]
            sd = [max(0.04 * (hi - lo),
                      statistics.pstdev([e[3][d] for e in elites]))
                  for d, (_, lo, hi, _) in enumerate(SCHED_SPACE)]
            if total[0][0] > best[1]:
                best = (total[0][3], total[0][0], to_params(total[0][3]))
            print(f"gen {g}: fit {total[0][0]:.0f} (vs_own {total[0][1]:.0f} solo {total[0][2]:.0f}) "
                  f"elite_mean {statistics.mean(e[0] for e in elites):.0f} "
                  f"| cow={to_params(total[0][3])['cow_total']:.1f} "
                  f"straw={to_params(total[0][3])['straw_peak']:.0f} "
                  f"fert_start={to_params(total[0][3])['fert_start_day']:.0f}", flush=True)
            log.write(json.dumps({"gen": g, "fit": total[0][0], "vs_own": total[0][1],
                                  "params": to_params(total[0][3])}) + "\n")
            log.flush()
        # holdout 终选：best + 最终精英 top4
        finals = [best[0]] + [e[3] for e in elites[:4]]
        fh = eval_cands(finals, HOLD_SEEDS[:5], HOLD_SEEDS[5:], pool)
        base_h = eval_cands([[DEFAULTS[n] for n, _, _, _ in SCHED_SPACE]],
                            HOLD_SEEDS[:5], HOLD_SEEDS[5:], pool)[0]
        print(f"HOLDOUT baseline: fit {base_h[0]:.0f} vs_own {base_h[1]:.0f}", flush=True)
        results = []
        for i, f in enumerate(fh):
            print(f"HOLDOUT cand{i}: fit {f[0]:.0f} vs_own {f[1]:.0f} solo {f[2]:.0f}", flush=True)
            results.append({"params": to_params(finals[i]), "hold_fit": f[0],
                            "hold_vs_own": f[1], "hold_solo": f[2]})
        (HERE / "best_iter.json").write_text(json.dumps(
            {"baseline_hold": base_h[0], "candidates": results}, indent=1))
        # top 过基线者入迭代池（多样性过滤）
        good = [r for r in results if r["hold_fit"] > base_h[0]]
        good.sort(key=lambda r: -r["hold_fit"])
        it_pool = []
        for r in good:
            if any(param_dist(r["params"], p["params"]) < 0.4 for p in it_pool):
                continue
            it_pool.append({"params": r["params"], "vs_own": round(r["hold_vs_own"]),
                            "solo": round(r["hold_solo"]), "tables": gen_tables(r["params"])})
        if it_pool:
            (HERE / "plan_pool_iter.json").write_text(json.dumps(it_pool, indent=1))
            print(f"迭代池 {len(it_pool)} 条 -> plan_pool_iter.json", flush=True)
        log.write(json.dumps({"gen": "final", "holdout": [r["hold_fit"] for r in results],
                              "baseline": base_h[0]}) + "\n")
        log.close()


if __name__ == "__main__":
    main()
