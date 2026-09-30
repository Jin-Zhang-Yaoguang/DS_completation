"""调度器参数进化主程序 v2:真实 seed 池轮换 + train/valid 分离 + 断点续跑。

评分:每配置 = 对手池(6,分层)x 当期训练 seed(8,每 10 代从线上真实 seed 池轮换)。
本地引擎席位完全对称(实测同 seed 换席位 margin 逐分相同),故不重复跑双席位。
best_ever 采用 train/valid 分离:训练分创新高的配置须在固定验证 seed 组(8 个,
独立于训练池抽取、从不轮换)复测,验证分也创新高才登记为新冠军(防赢者诅咒)。

用法:
  python evolve.py --generations 150 --run structv3
产物 runs/<run>/:state.json(断点)、history.jsonl(曲线)、best_cfg.json(验证确认的冠军)
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
N_TRAIN_SEEDS = 8
N_VALID_SEEDS = 8


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--generations", type=int, default=10)
    ap.add_argument("--pop", type=int, default=32)
    ap.add_argument("--elite", type=int, default=4)
    ap.add_argument("--mut-rate", type=float, default=0.3)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--run", default="default")
    ap.add_argument("--fresh", action="store_true")
    ap.add_argument("--init-cfg", default="", help="初始配置 JSON(默认取 structv2 冠军,再退 v55 基线)")
    return ap.parse_args()


def initial_cfg(path: str) -> dict:
    for p in ([Path(path)] if path else []) + [
        HERE / "runs" / "structv2" / "best_cfg.json",
        HERE.parent / "v55_generator" / "best_cfg_58k.json",
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


def train_seeds_for(pool: list[int], gen: int, valid: set[int]) -> list[int]:
    epoch = gen // SEED_ROTATE_EVERY
    r = random.Random(1000 + epoch)
    cand = [s for s in pool if s not in valid]
    return r.sample(cand, N_TRAIN_SEEDS)


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


def main():
    args = parse_args()
    rundir = HERE / "runs" / args.run
    rundir.mkdir(parents=True, exist_ok=True)
    state_p, hist_p, best_p = rundir / "state.json", rundir / "history.jsonl", rundir / "best_cfg.json"

    pool = load_seed_pool()
    valid_seeds = pick_valid_seeds(pool)
    rng = random.Random(7)
    gen0, best_ever = 0, None
    if state_p.exists() and not args.fresh:
        st = json.loads(state_p.read_text())
        gen0, pop, best_ever = st["gen"] + 1, st["pop"], st.get("best_ever")
        rng.setstate(tuple(st["rng"][0:1] + [tuple(st["rng"][1])] + st["rng"][2:]))
        print(f"resume from gen{gen0}")
    else:
        base = initial_cfg(args.init_cfg)
        pop = [dict(base)] + [space.mutate(base, 0.5, rng) for _ in range(args.pop - 1)]

    opps = arena.default_opponents()
    print(f"run={args.run} pop={len(pop)} opps={len(opps)} 训练 {N_TRAIN_SEEDS} seed/期(每 {SEED_ROTATE_EVERY} 代轮换) "
          f"valid {N_VALID_SEEDS} seed 固定 -> {len(pop)*len(opps)*N_TRAIN_SEEDS} 局/代", flush=True)

    with ProcessPoolExecutor(args.workers) as ex:
        for gen in range(gen0, gen0 + args.generations):
            seeds = train_seeds_for(pool, gen, set(valid_seeds))
            scored = evaluate(pop, opps, seeds, ex)
            best, mean = scored[0], statistics.mean(s["avg"] for s in scored)
            valid_avg = None
            prev_train = best_ever["train_avg"] if best_ever else None
            if best_ever is None or best["avg"] > (prev_train if prev_train is not None else -1e18):
                valid_avg = eval_one(best["cfg"], opps, valid_seeds, ex)
                if best_ever is None or valid_avg > best_ever.get("valid_avg", -1e18):
                    best_ever = {"gen": gen, "train_avg": best["avg"], "valid_avg": valid_avg,
                                 "cfg": best["cfg"]}
                    best_p.write_text(json.dumps(best_ever, indent=1))
            row = {"gen": gen, "best_avg": best["avg"], "best_min": best["min"], "pop_mean": mean,
                   "seed_epoch": gen // SEED_ROTATE_EVERY}
            if valid_avg is not None:
                row["valid_avg"] = valid_avg
            with hist_p.open("a") as f:
                f.write(json.dumps(row) + "\n")
            vtxt = f" valid={valid_avg:+.0f}" if valid_avg is not None else ""
            print(f"gen{gen}: best_avg={best['avg']:+.0f} pop_mean={mean:+.0f}{vtxt} "
                  f"ever(valid)={best_ever['valid_avg']:+.0f}", flush=True)
            elite = [s["cfg"] for s in scored[:args.elite]]
            parents = [s["cfg"] for s in scored[:max(args.elite, len(pop) // 2)]]
            children = []
            while len(children) < len(pop) - len(elite):
                a, b = rng.sample(parents, 2)
                children.append(space.mutate(space.crossover(a, b, rng), args.mut_rate, rng))
            pop = elite + children
            st_rng = rng.getstate()
            state_p.write_text(json.dumps({"gen": gen, "pop": pop, "best_ever": best_ever,
                                           "rng": [st_rng[0], list(st_rng[1]), st_rng[2]]}))
    print(f"done. best_ever valid={best_ever['valid_avg']:+.0f} -> {best_p}")


if __name__ == "__main__":
    main()
