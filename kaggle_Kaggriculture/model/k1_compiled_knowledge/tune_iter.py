"""真正的迭代搜索：CEM + 三疫苗，锚定 Majkel 路线；目标 = 分差（门控 1 口径）。

fitness（2026-09-15 修订）：
  fit = margin + OWN_W × own + SOLO_W × solo
  - margin：对 y68g、y68c 两个强对手的平均分差（门控 1 看胜负，分差是真目标）
  - own：自身金币（防「只压对手、自己不涨」的病态解）
  - solo：单打保底（防对特定对手过拟合）
  旧版 fitness 只看 own+solo，实测暴露反向盲区：去除旧乘数后自身 +9.4k、
  对手 +2.4 万、分差反而恶化 1.5 万。

三疫苗：
  1. fitness 同时含分差/自身/单打（双向病态解免疫）
  2. 每代 successive halving：粗筛 → 精评追加 seed（噪声免疫）
  3. 每 3 代轮换训练 seed + 终选 holdout 复核（赢者诅咒免疫）
初始化：warm start（上一轮 holdout 最优），否则 MAJ_ANCHOR；现有池注入首代。
分工：LLM 只做蒸馏与验证；参数全交搜索。

用法: /opt/anaconda3/bin/python3 tune_iter.py [gens] [pop]
产物: tune_iter_log.jsonl、best_iter.json、plan_pool_iter.json
"""
import importlib.util
import json
import random
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from schedule_gen import SCHED_SPACE, DEFAULTS, gen_tables  # noqa: E402
from build_plan_pool import MAJ_ANCHOR, _sim_one, param_dist  # noqa: E402

MOS = "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v58_mosaic/dist_backup"
POOL = "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/opponent_pool_v1"
OPPS = [f"sub:{MOS}/y68g_main.py", f"sub:{POOL}/packs/y68c_main.py"]
import os as _os
# 分层对手池（2026-09-15）：K1_OPP_TIERS=opp_tiers.json 时每代按层抽对手，holdout 用固定跨层集合；
# 未设置时保持旧口径（y68g+y68c 固定）。
TIERS_PATH = _os.environ.get("K1_OPP_TIERS", "")
TIERS = None
if TIERS_PATH:
    _tj = json.loads((HERE / TIERS_PATH).read_text() if not _os.path.isabs(TIERS_PATH) else open(TIERS_PATH).read())
    _fmt = lambda x: x.replace("{M}", _tj["M"]).replace("{K1}", _tj["K1"])
    TIERS = {k: {"per_gen": v["per_gen"], "opps": [_fmt(o) for o in v["opps"]]} for k, v in _tj["tiers"].items()}
    HOLD_OPPS = [_fmt(o) for o in _tj["holdout"]]


def gen_opps(g):
    """第 g 代的训练对手：每层按 per_gen 确定性抽取（同代所有候选同一组，保持可比）。"""
    if not TIERS:
        return list(OPPS)
    r = random.Random(7919 * (g + 1))
    out = []
    for name in sorted(TIERS):
        t = TIERS[name]
        out.extend(r.sample(t["opps"], min(t["per_gen"], len(t["opps"]))))
    return out
OWN_W = float(_os.environ.get("K1_OWN_W", "0.5"))
SOLO_W = float(_os.environ.get("K1_SOLO_W", "0.15"))
TAG = _os.environ.get("K1_TAG", "")
# 预算参数(2026-09-15 修订:单局 ~0.4s,旧 12 代×4 局/候选被噪声支配,每代最优分差 ±10k 无趋势)
VS_N = int(_os.environ.get("K1_VS_N", "2"))      # 每阶段对战 seed 数(×2 对手)
SOLO_N = int(_os.environ.get("K1_SOLO_N", "1"))
HOLD_N = int(_os.environ.get("K1_HOLD_N", "4"))
ROT = int(_os.environ.get("K1_ROT", "3"))         # 每几代轮换训练 seed
SEED_BANK = [1009 + 1037 * i for i in range(400)]
# holdout 轮换（2026-09-17 审计：ga5-7 共用固定 HOLD_SEEDS 终选，赢者诅咒 ~9k——每个 TAG 用不同 seed 段）
_HOLD_BASE = 900007 + (sum(ord(c) for c in TAG) % 89) * 1013
HOLD_SEEDS = [_HOLD_BASE + 53 * i for i in range(2 * HOLD_N + 8)]


# 冻结维度（K1_FREEZE="a,b,c"）：搜索/变异后强制回默认——用于把违反门控的机制（如 eps_on 回放，
# fitness 看不见门控2 重合度、会反复劫持搜索）从空间剔除而不删代码
_FREEZE_IDX = {}
if _os.environ.get("K1_FREEZE"):
    _fr = set(_os.environ["K1_FREEZE"].split(","))
    _FREEZE_IDX = {i: d for i, (n, _, _, d) in enumerate(SCHED_SPACE) if n in _fr}


def clamp(vec):
    out = [min(hi, max(lo, v)) for v, (_, lo, hi, _) in zip(vec, SCHED_SPACE)]
    for i, d in _FREEZE_IDX.items():
        out[i] = d
    return out


def to_params(vec):
    return {name: v for (name, _, _, _), v in zip(SCHED_SPACE, clamp(vec))}


def _sim_pair(job):
    """对战一局，返回 (own, margin)。配置注入与 build_plan_pool._sim_one 一致。"""
    params, seed, opp_spec = job[:3]
    seat = job[3] if len(job) > 3 else 0
    sys.path.insert(0, "/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness")
    sys.path.insert(0, "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v16_online_fidelity")
    import engine
    import fidelity
    base_tu = json.loads((HERE / "knowledge.json").read_text()).get("tuning", {})
    spec = importlib.util.spec_from_file_location(f"k1_ti_{seed}_{abs(hash(str(params))) % 99991}", HERE / "main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ov = gen_tables(params)
    te = ov.pop("tuning_extra", {})
    # tri_day_on 强制关（2026-09-17：knowledge 默认 tri=1 后，单方案评估会被 d3 重选切到池方案，
    # 污染搜索目标——ga7 整轮因此作废；评估语义 = 被评估参数从头跑到尾）
    ov["tuning"] = {**base_tu, "fert_specialist": False, "t0_pool_select": False, "tri_day_on": 0, **te}
    mod.KN_OVERRIDE = ov
    opp = fidelity.make_agent(opp_spec)
    if seat == 0:
        b0, b1 = engine.play(mod.agent, opp, seed=seed)
        return b0, b0 - b1
    b0, b1 = engine.play(opp, mod.agent, seed=seed)
    return b1, b1 - b0


def eval_cands(cands, vs_seeds, solo_seeds, pool, opps=None):
    opps = opps or OPPS
    # 分层模式下双席位轮换（seed 与对手序号奇偶决定席位），旧口径恒 0 号位
    vjobs = [(to_params(c), s, o, ((s + j) % 2 if TIERS else 0))
             for c in cands for s in vs_seeds for j, o in enumerate(opps)]
    sjobs = [(to_params(c), s, None) for c in cands for s in solo_seeds]
    vres = list(pool.map(_sim_pair, vjobs))
    sres = list(pool.map(_sim_one, sjobs))
    kv, ks = len(vs_seeds) * len(opps), len(solo_seeds)
    out = []
    for i in range(len(cands)):
        chunk = vres[i * kv:(i + 1) * kv]
        own = statistics.mean(o for o, _ in chunk)
        margin = statistics.mean(m for _, m in chunk)
        solo = statistics.mean(sres[i * ks:(i + 1) * ks])
        out.append((margin + OWN_W * own + SOLO_W * solo, margin, own, solo))
    return out


def main():
    gens = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    npop = int(sys.argv[2]) if len(sys.argv) > 2 else 28
    elite_n = max(4, npop // 4)
    rng = random.Random()
    mu = [MAJ_ANCHOR.get(n, d) for n, _, _, d in SCHED_SPACE]
    bi = HERE / "best_iter.json"
    if bi.exists():
        prev = json.loads(bi.read_text()).get("candidates") or []
        if prev:
            top_prev = max(prev, key=lambda c: c["hold_fit"])
            mu = [top_prev["params"].get(n, MAJ_ANCHOR.get(n, d)) for n, _, _, d in SCHED_SPACE]
            print(f"warm start from best_iter (旧口径 hold_fit {top_prev['hold_fit']:.0f})", flush=True)
    sd = [(hi - lo) / 5 for _, lo, hi, _ in SCHED_SPACE]
    seed_pool = []
    pp = HERE / "plan_pool.json"
    if pp.exists():
        for p in json.loads(pp.read_text())[:6]:
            seed_pool.append([p["params"].get(n, d) for n, _, _, d in SCHED_SPACE])
    log = open(HERE / f"tune_iter_log{TAG}.jsonl", "a")
    best = (None, -1e18)
    elites = []
    with ProcessPoolExecutor(max_workers=8) as pool:
        for g in range(gens):
            blk = 2 * (VS_N + SOLO_N)
            bank_off = ((g // ROT) * blk) % (len(SEED_BANK) - blk)
            train_vs = SEED_BANK[bank_off:bank_off + VS_N]
            train_solo = SEED_BANK[bank_off + VS_N:bank_off + VS_N + SOLO_N]
            cands = [list(mu)] + seed_pool[:max(0, npop // 4 - 1)]
            while len(cands) < npop:
                cands.append([rng.gauss(m, s) for m, s in zip(mu, sd)])
            seed_pool = []
            f0 = eval_cands(cands, train_vs, train_solo, pool)
            order = sorted(range(len(cands)), key=lambda i: -f0[i][0])
            top = [cands[i] for i in order[:npop // 2]]
            e0 = bank_off + VS_N + SOLO_N
            extra_vs = SEED_BANK[e0:e0 + VS_N]
            extra_solo = SEED_BANK[e0 + VS_N:e0 + VS_N + SOLO_N]
            f1 = eval_cands(top, extra_vs, extra_solo, pool)
            total = [((f0[order[i]][0] + 2 * f1[i][0]) / 3, f1[i][1], f1[i][2], f1[i][3], top[i])
                     for i in range(len(top))]
            total.sort(key=lambda z: -z[0])
            elites = total[:elite_n]
            mu = [statistics.mean(e[4][d] for e in elites) for d in range(len(SCHED_SPACE))]
            sd = [max(0.04 * (hi - lo), statistics.pstdev([e[4][d] for e in elites]))
                  for d, (_, lo, hi, _) in enumerate(SCHED_SPACE)]
            if total[0][0] > best[1]:
                best = (total[0][4], total[0][0])
            bp = to_params(total[0][4])
            print(f"gen {g}: fit {total[0][0]:.0f} (margin {total[0][1]:.0f} own {total[0][2]:.0f} "
                  f"solo {total[0][3]:.0f}) elite_mean {statistics.mean(e[0] for e in elites):.0f} "
                  f"| straw={bp['straw_peak']:.0f} wheat={bp['wheat_peak']:.0f} cow={bp['cow_total']:.1f}",
                  flush=True)
            log.write(json.dumps({"gen": g, "objective": "margin", "fit": total[0][0],
                                  "margin": total[0][1], "vs_own": total[0][2], "params": bp}) + "\n")
            log.flush()
        finals = [best[0]] + [e[4] for e in elites[:4]]
        hv, hs = HOLD_SEEDS[:HOLD_N], HOLD_SEEDS[HOLD_N:HOLD_N + max(2, HOLD_N // 2)]
        fh = eval_cands(finals, hv, hs, pool)
        base_h = eval_cands([[DEFAULTS[n] for n, _, _, _ in SCHED_SPACE]], hv, hs, pool)[0]
        print(f"HOLDOUT baseline: fit {base_h[0]:.0f} margin {base_h[1]:.0f} own {base_h[2]:.0f}", flush=True)
        results = []
        for i, f in enumerate(fh):
            print(f"HOLDOUT cand{i}: fit {f[0]:.0f} margin {f[1]:.0f} own {f[2]:.0f} solo {f[3]:.0f}", flush=True)
            results.append({"params": to_params(finals[i]), "hold_fit": f[0], "hold_margin": f[1],
                            "hold_vs_own": f[2], "hold_solo": f[3]})
        (HERE / f"best_iter{TAG}.json").write_text(json.dumps(
            {"objective": "margin", "baseline_hold": base_h[0], "candidates": results}, indent=1))
        good = sorted((r for r in results if r["hold_fit"] > base_h[0]), key=lambda r: -r["hold_fit"])
        it_pool = []
        for r in good:
            if any(param_dist(r["params"], p["params"]) < 0.4 for p in it_pool):
                continue
            it_pool.append({"params": r["params"], "vs_own": round(r["hold_vs_own"]),
                            "margin": round(r["hold_margin"]), "solo": round(r["hold_solo"]),
                            "tables": gen_tables(r["params"])})
        if it_pool:
            (HERE / f"plan_pool_iter{TAG}.json").write_text(json.dumps(it_pool, indent=1))
            print(f"迭代池 {len(it_pool)} 条 -> plan_pool_iter.json", flush=True)
        log.write(json.dumps({"gen": "final", "objective": "margin",
                              "holdout": [r["hold_fit"] for r in results], "baseline": base_h[0]}) + "\n")
        log.close()


if __name__ == "__main__":
    main()
