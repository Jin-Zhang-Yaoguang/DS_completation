"""调度器参数进化主程序 v3(FunSearch 筛选器):配对登基 + 32 验证 seed + 指纹去重 + 早停。

评分:每配置 = 对手池(6,分层)x 当期训练 seed(8,每 10 代从线上真实 seed 池轮换)。
本地引擎席位完全对称,故不重复跑双席位。

登基(v3):
  触发 = 本代最优个体在**本期训练 seed**上超过现冠军(冠军每期复测一次,同尺比较),
         且该配置未验证失败过(指纹去重)。
  判定 = 候选 vs 冠军在 32 个固定验证 seed 上**配对**:均值差 > 0 且 t >= CROWN_T。
  验证 seed 与训练池、holdout 池三者互斥;holdout(64)只给刀级验收用,本程序不碰。

早停:--patience P,连续 P 代无登基即停(0 = 关);--max-gens 上限。summary.json 记录停因。

用法:
  python evolve.py --generations 80 --patience 40 --run k1_harvest --init-best runs/_funsearch/baseline.json
产物 runs/<run>/:state.json(断点)、history.jsonl(曲线)、best_cfg.json(冠军,含验证逐 seed 分)、summary.json
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import arena
import space

HERE = Path(__file__).resolve().parent
SEED_ROTATE_EVERY = 10
N_TRAIN_SEEDS = 16  # 2026-09-13 8->16:压制 8-seed 尺子上的赢者诅咒(第一轮 200 代实证)
N_VALID_SEEDS = 32
N_HOLDOUT_SEEDS = 64
CROWN_T = 1.5


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--generations", type=int, default=10, help="本次最多跑多少代")
    ap.add_argument("--patience", type=int, default=0, help="连续多少代无登基即早停(0=关)")
    ap.add_argument("--pop", type=int, default=32)
    ap.add_argument("--elite", type=int, default=4)
    ap.add_argument("--mut-rate", type=float, default=0.3)
    ap.add_argument("--workers", type=int, default=14)  # 16 核机器,留 2 核给系统/索引进程
    ap.add_argument("--run", default="default")
    ap.add_argument("--fresh", action="store_true")
    ap.add_argument("--init-cfg", default="", help="初始配置 JSON(热启动个体)")
    ap.add_argument("--init-best", default="", help="初始冠军 JSON(best_cfg 格式;含 valid_per_seed 则免复测)")
    return ap.parse_args()


def initial_cfg(path: str) -> dict:
    for p in ([Path(path)] if path else []) + [
        HERE / "runs" / "structv3" / "best_cfg.json",
        HERE / "runs" / "structv2" / "best_cfg.json",
    ]:
        if p and Path(p).exists():
            d = json.loads(Path(p).read_text())
            return space.clamp(d.get("cfg", d))
    raise SystemExit("no initial cfg found")


def load_seed_pool() -> list[int]:
    return json.loads((HERE / "seed_pool.json").read_text())


def pick_valid_seeds(pool: list[int]) -> list[int]:
    r = random.Random(20260911)  # 固定,与训练抽取解耦
    return r.sample(pool, N_VALID_SEEDS)


def pick_holdout_seeds(pool: list[int]) -> list[int]:
    """64 个 holdout:固定、与 valid 互斥;落盘 holdout_seeds.json 供刀级验收。"""
    p = HERE / "holdout_seeds.json"
    if p.exists():
        return json.loads(p.read_text())
    valid = set(pick_valid_seeds(pool))
    r = random.Random(20260913)
    hold = r.sample([s for s in pool if s not in valid], N_HOLDOUT_SEEDS)
    p.write_text(json.dumps(hold))
    return hold


def train_seeds_for(pool: list[int], gen: int, excluded: set[int]) -> list[int]:
    epoch = gen // SEED_ROTATE_EVERY
    r = random.Random(1000 + epoch)
    cand = [s for s in pool if s not in excluded]
    return r.sample(cand, N_TRAIN_SEEDS)


def fingerprint(cfg: dict) -> str:
    return json.dumps(space.clamp(cfg), sort_keys=True)


def evaluate(pop, opps, seeds, ex):
    jobs = [(cfg, op, sd) for cfg in pop for op in opps for sd in seeds]
    res = list(ex.map(arena.play_one, jobs, chunksize=4))
    per = len(opps) * len(seeds)
    scored = []
    for i, cfg in enumerate(pop):
        ms = res[i * per:(i + 1) * per]
        scored.append({"avg": sum(ms) / per, "min": min(ms), "cfg": cfg})
    scored.sort(key=lambda s: -s["avg"])
    return scored


def eval_one(cfg, opps, seeds, ex):
    jobs = [(cfg, op, sd) for op in opps for sd in seeds]
    res = list(ex.map(arena.play_one, jobs, chunksize=4))
    return sum(res) / len(res)


def eval_per_seed(cfg, opps, seeds, ex) -> list[float]:
    """每个 seed 对全对手池的均值(配对比较的基本单元)。"""
    jobs = [(cfg, op, sd) for sd in seeds for op in opps]
    res = list(ex.map(arena.play_one, jobs, chunksize=4))
    n = len(opps)
    return [sum(res[i * n:(i + 1) * n]) / n for i in range(len(seeds))]


def paired_t(a: list[float], b: list[float]) -> tuple[float, float]:
    """返回 (均值差 a-b, t 值)。"""
    d = [x - y for x, y in zip(a, b)]
    m = statistics.mean(d)
    sd = statistics.stdev(d) if len(d) > 1 else 0.0
    t = m / (sd / len(d) ** 0.5) if sd > 0 else (0.0 if m == 0 else float("inf") * (1 if m > 0 else -1))
    return m, t


def main():
    args = parse_args()
    rundir = HERE / "runs" / args.run
    rundir.mkdir(parents=True, exist_ok=True)
    state_p, hist_p, best_p, sum_p = (rundir / "state.json", rundir / "history.jsonl",
                                      rundir / "best_cfg.json", rundir / "summary.json")

    pool = load_seed_pool()
    valid_seeds = pick_valid_seeds(pool)
    holdout = pick_holdout_seeds(pool)
    excluded = set(valid_seeds) | set(holdout)
    opps = arena.default_opponents()
    rng = random.Random(7)
    gen0, best_ever, failed, streak = 0, None, [], 0
    if state_p.exists() and not args.fresh:
        st = json.loads(state_p.read_text())
        gen0, pop, best_ever = st["gen"] + 1, st["pop"], st.get("best_ever")
        failed, streak = st.get("failed", []), st.get("streak", 0)
        rng.setstate(tuple(st["rng"][0:1] + [tuple(st["rng"][1])] + st["rng"][2:]))
        print(f"resume from gen{gen0}", flush=True)
    else:
        if args.init_best:
            best_ever = json.loads(Path(args.init_best).read_text())
            best_ever["cfg"] = space.clamp(best_ever["cfg"])
            best_ever.setdefault("gen", -1)
        base = space.clamp(best_ever["cfg"]) if best_ever else initial_cfg(args.init_cfg)
        pop = [dict(base)] + [space.mutate(base, 0.5, rng) for _ in range(args.pop - 1)]
    failed_set = set(failed)

    print(f"run={args.run} pop={len(pop)} opps={len(opps)} 训练 {N_TRAIN_SEEDS} seed/期(每 {SEED_ROTATE_EVERY} 代轮换) "
          f"valid {N_VALID_SEEDS} 固定(配对 t>={CROWN_T}) holdout {len(holdout)} 不碰 -> {len(pop)*len(opps)*N_TRAIN_SEEDS} 局/代",
          flush=True)

    reason = "budget"
    champ_epoch = None  # (epoch, 冠军在该期训练 seed 上的均值)
    with ProcessPoolExecutor(args.workers) as ex:
        if best_ever is not None and (len(best_ever.get("valid_per_seed") or []) != N_VALID_SEEDS):
            best_ever["valid_per_seed"] = eval_per_seed(best_ever["cfg"], opps, valid_seeds, ex)
            best_ever["valid_avg"] = statistics.mean(best_ever["valid_per_seed"])
            best_p.write_text(json.dumps(best_ever, indent=1))
            print(f"init champion valid={best_ever['valid_avg']:+.0f}", flush=True)
        for gen in range(gen0, gen0 + args.generations):
            epoch = gen // SEED_ROTATE_EVERY
            seeds = train_seeds_for(pool, gen, excluded)
            scored = evaluate(pop, opps, seeds, ex)
            best, mean = scored[0], statistics.mean(s["avg"] for s in scored)
            # 冠军在本期训练 seed 的分数(每期一次,冠军更换时重测)
            if best_ever is not None and (champ_epoch is None or champ_epoch[0] != epoch):
                champ_epoch = (epoch, eval_one(best_ever["cfg"], opps, seeds, ex))
            valid_avg, valid_t, crowned = None, None, False
            fp = fingerprint(best["cfg"])
            trigger = (best_ever is None or
                       (best["avg"] > champ_epoch[1] and fp != fingerprint(best_ever["cfg"]) and fp not in failed_set))
            if trigger:
                per = eval_per_seed(best["cfg"], opps, valid_seeds, ex)
                valid_avg = statistics.mean(per)
                if best_ever is None:
                    crowned = True
                else:
                    diff, valid_t = paired_t(per, best_ever["valid_per_seed"])
                    crowned = diff > 0 and valid_t >= CROWN_T
                if crowned:
                    best_ever = {"gen": gen, "run": args.run, "train_avg": best["avg"], "valid_avg": valid_avg,
                                 "valid_t": valid_t, "valid_per_seed": per, "cfg": best["cfg"]}
                    best_p.write_text(json.dumps(best_ever, indent=1))
                    champ_epoch = (epoch, best["avg"])
                    streak = 0
                else:
                    failed.append(fp)
                    failed_set.add(fp)
            if not crowned:
                streak += 1
            row = {"gen": gen, "run": args.run, "best_avg": best["avg"], "best_min": best["min"], "pop_mean": mean,
                   "seed_epoch": epoch, "champ_train": champ_epoch[1], "crown": crowned}
            if valid_avg is not None:
                row["valid_avg"] = valid_avg
                if valid_t is not None:
                    row["valid_t"] = valid_t
            with hist_p.open("a") as f:
                f.write(json.dumps(row) + "\n")
            vtxt = (f" valid={valid_avg:+.0f}" + (f" t={valid_t:+.2f}" if valid_t is not None else "")
                    + (" CROWN" if crowned else "")) if valid_avg is not None else ""
            print(f"gen{gen}: best_avg={best['avg']:+.0f} champ_train={champ_epoch[1]:+.0f} pop_mean={mean:+.0f}{vtxt} "
                  f"ever(valid)={best_ever['valid_avg']:+.0f} streak={streak}", flush=True)
            elite = [s["cfg"] for s in scored[:args.elite]]
            parents = [s["cfg"] for s in scored[:max(args.elite, len(pop) // 2)]]
            children = []
            while len(children) < len(pop) - len(elite):
                a, b = rng.sample(parents, 2)
                children.append(space.mutate(space.crossover(a, b, rng), args.mut_rate, rng))
            pop = elite + children
            st_rng = rng.getstate()
            state_p.write_text(json.dumps({"gen": gen, "pop": pop, "best_ever": best_ever, "failed": failed,
                                           "streak": streak,
                                           "rng": [st_rng[0], list(st_rng[1]), st_rng[2]]}))
            if args.patience and streak >= args.patience:
                reason = "patience"
                break
    last_gen = json.loads(state_p.read_text())["gen"]
    summary = {"run": args.run, "reason": reason, "gens_done": last_gen - gen0 + 1, "last_gen": last_gen,
               "champion_gen": best_ever["gen"], "champion_run": best_ever.get("run"),
               "valid_avg": best_ever["valid_avg"], "streak": streak, "n_failed": len(failed)}
    sum_p.write_text(json.dumps(summary, indent=1))
    print(f"done({reason}). best_ever valid={best_ever['valid_avg']:+.0f} -> {best_p}", flush=True)


if __name__ == "__main__":
    main()
