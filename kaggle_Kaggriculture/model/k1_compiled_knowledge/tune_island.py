"""多岛遗传搜索（GA island model）：替代单分布 CEM，负责「收敛」；LLM 只负责扩展维度。

为什么换（2026-09-15）：
  CEM 各维独立采样、单峰收拢——「多养牛+多建栏+多买饲料」这类必须同时动的结构组合
  单独动都亏，会被拉回默认；两个风格不同的好方案会被平均到中间。
设计：
  - 多岛：ISLANDS 个子种群独立进化，初始化来源不同（warm start / 现有方案池 / MAJ_ANCHOR / 默认+大扰动），
    每 MIGRATE 代环形迁移（岛 i 最优替换岛 i+1 最差）——保留多峰，天然给门控2 的方案池提供风格多样性。
  - 交叉：按「维度块」均匀交叉（日程/内核结构/规模/产值/产出侧各为一块），块内整体继承，保住结构组合。
  - 变异：逐维概率 PM 的高斯扰动（sd = 区间宽 × MUT_SD）。
  - 噪声免疫：精英每代在新 seed 上复评、fitness 取累计均值（老个体靠多次评估才站得住，抑制赢者诅咒）；
    fitness 与 tune_iter 同口径 margin + OWN_W×own + SOLO_W×solo；终选 holdout 复核。
用法: K1_TAG=_ga /opt/anaconda3/bin/python3 tune_island.py [gens] [pop_per_island]
环境: K1_ISLANDS(4) K1_MIGRATE(5) K1_VS_N(4) K1_SOLO_N(1) K1_HOLD_N(8) K1_PM(0.15) K1_MUT_SD(0.12)
产物: best_iter{TAG}.json、plan_pool_iter{TAG}.json、tune_island_log{TAG}.jsonl
"""
import json
import os
import random
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tune_iter as TI  # noqa: E402
from schedule_gen import SCHED_SPACE, DEFAULTS, gen_tables  # noqa: E402
from build_plan_pool import MAJ_ANCHOR, param_dist  # noqa: E402

TAG = os.environ.get("K1_TAG", "_ga")
ISLANDS = int(os.environ.get("K1_ISLANDS", "4"))
MIGRATE = int(os.environ.get("K1_MIGRATE", "5"))
PM = float(os.environ.get("K1_PM", "0.15"))
MUT_SD = float(os.environ.get("K1_MUT_SD", "0.12"))
ELITE = 2
NAMES = [n for n, _, _, _ in SCHED_SPACE]
# 维度块边界（按 schedule_gen 分节）：块内整体交叉继承
BLOCK_STARTS = ["hands_peak", "cash_pump_until", "kernel_majkel", "fill_ratio", "wheat_keep_frac", "straw_ramp_days", "price_area_gain", "opp_id_day", "layout_sector", "plant_cap_mid", "route_on", "lib_on", "eps_on", "plan_on", "sell_demand_on", "dp_on"]


def blocks():
    starts = [NAMES.index(n) for n in BLOCK_STARTS if n in NAMES] + [len(NAMES)]
    return [list(range(a, b)) for a, b in zip(starts, starts[1:])]


def mutate(vec, rng):
    out = list(vec)
    for d, (_, lo, hi, _) in enumerate(SCHED_SPACE):
        if rng.random() < PM:
            out[d] = rng.gauss(out[d], (hi - lo) * MUT_SD)
    return TI.clamp(out)


def crossover(a, b, rng, blks):
    child = list(a)
    for blk in blks:
        if rng.random() < 0.5:
            for d in blk:
                child[d] = b[d]
    return child


def tournament(pop, rng, k=3):
    return max(rng.sample(pop, min(k, len(pop))), key=lambda ind: ind["fit"])


def init_islands(npop, rng):
    sources = []
    bi = HERE / "best_iter.json"
    if bi.exists():
        cands = json.loads(bi.read_text()).get("candidates") or []
        sources.append([[c["params"].get(n, DEFAULTS[n]) for n in NAMES] for c in cands])
    pp = HERE / "plan_pool.json"
    if pp.exists():
        sources.append([[p["params"].get(n, DEFAULTS[n]) for n in NAMES] for p in json.loads(pp.read_text())])
    sources.append([[MAJ_ANCHOR.get(n, DEFAULTS[n]) for n in NAMES]])
    sources.append([[DEFAULTS[n] for n in NAMES]])
    islands = []
    for i in range(ISLANDS):
        seeds = sources[i % len(sources)] or [[DEFAULTS[n] for n in NAMES]]
        if i > 0 and any(param_dist(TI.to_params(seeds[0]), TI.to_params(isl[0]["vec"])) < 0.05 for isl in islands):
            seeds = []  # 与前面岛同源：改为纯扰动岛
            base0 = sources[-1][0]
        sd_mult = 1.0 + i  # 越后的岛扰动越大，探索更远
        pop = []
        for j in range(npop):
            base = seeds[j % len(seeds)] if seeds else base0
            if seeds and j < len(seeds):
                vec = TI.clamp(list(base))
            else:
                vec = TI.clamp([rng.gauss(v, (hi - lo) * MUT_SD * sd_mult)
                                for v, (_, lo, hi, _) in zip(base, SCHED_SPACE)])
            pop.append({"vec": vec, "fit": None, "n": 0, "sum": 0.0, "m": 0.0, "own": 0.0, "solo": 0.0})
        islands.append(pop)
    return islands


def evaluate(inds, vs, solo, pool, opps=None):
    """评估并把结果累加进个体（累计均值 fitness）。
    分层对手模式下每代对手不同、难度不同：fitness 先减当代种群均值（相对分）再累计，
    否则老个体的累计分会被「抽到易/难对手的那几代」系统性抬高或压低。"""
    if not inds:
        return
    res = TI.eval_cands([ind["vec"] for ind in inds], vs, solo, pool, opps=opps)
    if TI.TIERS:
        fm = statistics.mean(r[0] for r in res)
        mm = statistics.mean(r[1] for r in res)
        res = [(f - fm, m - mm, own, s) for f, m, own, s in res]
    for ind, (f, m, own, s) in zip(inds, res):
        k = ind["n"]
        ind["sum"] += f
        ind["m"] = (ind["m"] * k + m) / (k + 1)
        ind["own"] = (ind["own"] * k + own) / (k + 1)
        ind["solo"] = (ind["solo"] * k + s) / (k + 1)
        ind["n"] = k + 1
        ind["fit"] = ind["sum"] / ind["n"]


def main():
    gens = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    npop = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    rng = random.Random()
    blks = blocks()
    islands = init_islands(npop, rng)
    log = open(HERE / f"tune_island_log{TAG}.jsonl", "a")
    blk_sz = TI.VS_N + TI.SOLO_N
    with ProcessPoolExecutor(max_workers=8) as pool:
        for g in range(gens):
            off = (g * blk_sz) % (len(TI.SEED_BANK) - blk_sz)
            vs = TI.SEED_BANK[off:off + TI.VS_N]
            solo = TI.SEED_BANK[off + TI.VS_N:off + blk_sz]
            # 所有个体（含老精英）在本代新 seed 上评估一次：老个体 fitness 变成多 seed 均值
            opps_g = TI.gen_opps(g)
            evaluate([ind for isl in islands for ind in isl], vs, solo, pool, opps=opps_g)
            summary = []
            for i, isl in enumerate(islands):
                isl.sort(key=lambda ind: -ind["fit"])
                summary.append((round(isl[0]["fit"]), round(isl[0]["m"]), isl[0]["n"]))
            best = max((ind for isl in islands for ind in isl), key=lambda ind: (ind["n"] >= 3, ind["fit"]))
            bp = TI.to_params(best["vec"])
            print(f"gen {g}: 对手 {[(o.split('/')[-2] if o.endswith('main.py') else o.split('/')[-1])[:16] for o in opps_g]} | 各岛最优(相对fit,相对margin,评估次数) {summary} | 全局 margin {best['m']:.0f} own {best['own']:.0f} "
                  f"n={best['n']} | straw={bp['straw_peak']:.0f} cow={bp['cow_total']:.1f} "
                  f"岛间距 {param_dist(TI.to_params(islands[0][0]['vec']), TI.to_params(islands[-1][0]['vec'])):.2f}",
                  flush=True)
            log.write(json.dumps({"gen": g, "islands": summary, "best_margin": best["m"], "best_n": best["n"],
                                  "params": bp}) + "\n")
            log.flush()
            if g == gens - 1:
                break
            # 迁移（环形）
            if MIGRATE and (g + 1) % MIGRATE == 0 and ISLANDS > 1:
                bests = [dict(isl[0], vec=list(isl[0]["vec"])) for isl in islands]
                for i in range(ISLANDS):
                    islands[(i + 1) % ISLANDS][-1] = bests[i]
            # 繁殖：精英保留（带累计评估），其余由锦标赛+块交叉+变异生成
            for i, isl in enumerate(islands):
                isl.sort(key=lambda ind: -(ind["fit"] if ind["fit"] is not None else -1e18))
                nxt = isl[:ELITE]
                while len(nxt) < npop:
                    pa, pb = tournament(isl, rng), tournament(isl, rng)
                    child = mutate(crossover(pa["vec"], pb["vec"], rng, blks), rng)
                    nxt.append({"vec": child, "fit": None, "n": 0, "sum": 0.0, "m": 0.0, "own": 0.0, "solo": 0.0})
                islands[i] = nxt
        # 终选：每岛前 2（评估次数≥2 优先）进 holdout
        finals, seen = [], []
        for isl in islands:
            ranked = sorted(isl, key=lambda ind: (ind["n"] >= 2, ind["fit"]), reverse=True)
            k = 0
            for ind in ranked:
                if k >= 2:
                    break
                p_ = TI.to_params(ind["vec"])
                if any(param_dist(p_, q) < 0.05 for q in seen):  # 迁移副本去重
                    continue
                seen.append(p_)
                finals.append(dict(ind, island=islands.index(isl)))
                k += 1
        hv, hs = TI.HOLD_SEEDS[:TI.HOLD_N], TI.HOLD_SEEDS[TI.HOLD_N:TI.HOLD_N + max(2, TI.HOLD_N // 2)]
        fh = TI.eval_cands([f["vec"] for f in finals], hv, hs, pool,
                           opps=(TI.HOLD_OPPS if TI.TIERS else None))
        results = []
        for i, (ind, f) in enumerate(zip(finals, fh)):
            print(f"HOLDOUT 岛{ind['island']} cand{i}: fit {f[0]:.0f} margin {f[1]:.0f} own {f[2]:.0f} solo {f[3]:.0f} "
                  f"(训练 margin {ind['m']:.0f} n={ind['n']})", flush=True)
            results.append({"island": ind["island"], "params": TI.to_params(ind["vec"]), "hold_fit": f[0],
                            "hold_margin": f[1], "hold_vs_own": f[2], "hold_solo": f[3]})
        (HERE / f"best_iter{TAG}.json").write_text(json.dumps({"objective": "margin", "algo": "island_ga",
                                                               "candidates": results}, indent=1))
        top_m = max(r["hold_margin"] for r in results)
        it_pool = []
        for r in sorted(results, key=lambda r: -r["hold_margin"]):
            if r["hold_margin"] < top_m - 8000:
                continue
            if any(param_dist(r["params"], p["params"]) < 0.4 for p in it_pool):
                continue
            it_pool.append({"params": r["params"], "vs_own": round(r["hold_vs_own"]), "margin": round(r["hold_margin"]),
                            "solo": round(r["hold_solo"]), "island": r["island"], "tables": gen_tables(r["params"])})
        (HERE / f"plan_pool_iter{TAG}.json").write_text(json.dumps(it_pool, indent=1))
        print(f"迭代池 {len(it_pool)} 条（来自岛 {sorted({p['island'] for p in it_pool})}）", flush=True)
        log.write(json.dumps({"gen": "final", "holdout": [r["hold_margin"] for r in results]}) + "\n")
        log.close()


if __name__ == "__main__":
    main()
