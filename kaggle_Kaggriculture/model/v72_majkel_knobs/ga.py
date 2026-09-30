"""Majkel 旋钮 GA:y68d 底盘 + build.SPACE 旋钮,配对 racing 逐级淘汰评分。

每代:全员 8 seed 粗筛 → 前 12 名加到 16 seed → 前 6 名加到 32 seed;
排序 = (到达的级数, 该级加权配对差 d)。训练 seed 每 ROTATE 代在 race.TRAIN_SEEDS 两个半区轮换。
父包/候选结果全部缓存(v69_v38_knives/cache),精英复评零成本。
收官:当前前 3 名在 64 holdout seed 上配对复核。

用法: python ga.py --gens 20 [--pop 24] [--seed-cfgs seeds.json] [--fresh]
产物: state.json(断点) history.jsonl(每代) final.json(收官复核)
"""
import sys, json, random, argparse, statistics as S, time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "v69_v38_knives"))
import build, race

PARENT = str((HERE / "y68f_parent.py").resolve())
RUNGS = [(8, None), (16, 12), (32, 6)]   # (seed 数, 进入该级的名额)
ROTATE = 5

def rand_value(k, rng):
    typ, dom, _ = build.SPACE[k]
    if typ == "cat": return rng.choice(dom)
    if typ == "int": return rng.randint(*dom)
    return round(rng.uniform(*dom), 2)

def mutate(cfg, rng, rate):
    c = dict(cfg)
    for k, (typ, dom, _) in build.SPACE.items():
        if rng.random() >= rate: continue
        if typ == "cat": c[k] = rng.choice(dom)
        elif typ == "int":
            span = max(1, (dom[1] - dom[0]) // 4); c[k] = max(dom[0], min(dom[1], c[k] + rng.randint(-span, span)))
        else:
            span = (dom[1] - dom[0]) * 0.2; c[k] = round(max(dom[0], min(dom[1], c[k] + rng.uniform(-span, span))), 2)
    return c

def crossover(a, b, rng):
    return {k: (a[k] if rng.random() < 0.5 else b[k]) for k in build.SPACE}

def key(c): return json.dumps(c, sort_keys=True)

def evaluate(pop, gen, ex):
    half = (gen // ROTATE) % 2
    pool = race.TRAIN_SEEDS[32 * half: 32 * half + 32]
    paths = {key(c): str(build.build(c)[0]) for c in pop}
    alive = list(paths)
    score = {}
    for n_seed, quota in RUNGS:
        if quota is not None:
            alive = sorted(alive, key=lambda k: -score[k][1])[:quota]
        seeds = pool[:n_seed]
        caches = race.ensure([PARENT] + [paths[k] for k in alive], seeds, 0, ex)
        for k in alive:
            m, t, wins, per_opp = race.paired(caches, PARENT, paths[k], seeds, 0)
            score[k] = (n_seed, m, t, wins, per_opp)
    ranked = sorted(pop, key=lambda c: (-score[key(c)][0], -score[key(c)][1]))
    return ranked, score, paths

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gens", type=int, default=20); ap.add_argument("--pop", type=int, default=24)
    ap.add_argument("--elite", type=int, default=4); ap.add_argument("--rate", type=float, default=0.3)
    ap.add_argument("--seed-cfgs", default=""); ap.add_argument("--fresh", action="store_true")
    ap.add_argument("--workers", type=int, default=14)
    a = ap.parse_args()
    state_p, hist_p = HERE / "state.json", HERE / "history.jsonl"
    rng = random.Random(72)
    if state_p.exists() and not a.fresh:
        st = json.loads(state_p.read_text()); gen0, pop = st["gen"] + 1, st["pop"]
        rng.setstate(tuple(st["rng"][0:1] + [tuple(st["rng"][1])] + st["rng"][2:]))
        print(f"resume gen{gen0}", flush=True)
    else:
        gen0 = 0
        seeds = [build.full_cfg(c) for c in (json.loads(Path(a.seed_cfgs).read_text()) if a.seed_cfgs else [])]
        pop = [build.full_cfg({})] + seeds
        while len(pop) < a.pop:
            base = rng.choice(pop)
            pop.append(mutate(base, rng, 0.5))
        pop = pop[:a.pop]
        if hist_p.exists(): hist_p.unlink()
    with ProcessPoolExecutor(a.workers) as ex:
        for gen in range(gen0, gen0 + a.gens):
            t0 = time.time()
            ranked, score, paths = evaluate(pop, gen, ex)
            best = ranked[0]; s = score[key(best)]
            top_d = [score[key(c)][1] for c in ranked if score[key(c)][0] == 32]
            row = {"gen": gen, "seed_half": (gen // ROTATE) % 2, "best_d": round(s[1], 1), "best_t": round(s[2], 2),
                   "best_wins": f"{s[3]}/{s[0]}", "best_cfg": best, "best_pack": Path(paths[key(best)]).name,
                   "top6_mean_d": round(S.mean(top_d), 1) if top_d else None,
                   "pop_mean_d8": round(S.mean(score[key(c)][1] for c in pop), 1),
                   "per_opp": {k: round(v) for k, v in s[4].items()}, "sec": round(time.time() - t0, 1)}
            with hist_p.open("a") as f: f.write(json.dumps(row) + "\n")
            diff = {k: v for k, v in best.items() if v != build.DEFAULT[k]}
            print(f"gen{gen} half{row['seed_half']} best d={s[1]:+.0f} t={s[2]:+.2f} win={s[3]}/{s[0]} top6={row['top6_mean_d']} "
                  f"pop8={row['pop_mean_d8']} {row['sec']}s | {diff}", flush=True)
            elites = ranked[:a.elite]; parents = ranked[:max(a.elite, len(ranked) // 2)]
            children = []
            seen = {key(c) for c in elites}
            while len(children) < a.pop - a.elite:
                c = mutate(crossover(*rng.sample(parents, 2), rng), rng, a.rate)
                if key(c) not in seen: seen.add(key(c)); children.append(c)
            pop = elites + children
            r = rng.getstate()
            state_p.write_text(json.dumps({"gen": gen, "pop": pop, "rng": [r[0], list(r[1]), r[2]]}))
        # 收官:前 3 名 holdout 64
        final = []
        top3 = ranked[:3]
        hold = race.HOLD_SEEDS[:64]
        tpaths = [str(build.build(c)[0]) for c in top3]
        caches = race.ensure([PARENT] + tpaths, hold, 0, ex)
        for c, p in zip(top3, tpaths):
            m, t, wins, per_opp = race.paired(caches, PARENT, p, hold, 0)
            final.append({"cfg": c, "pack": Path(p).name, "holdout_d": round(m, 1), "holdout_t": round(t, 2), "wins": f"{wins}/64",
                          "per_opp": {k: round(v) for k, v in per_opp.items()}})
            print(f"HOLDOUT {Path(p).name} d={m:+.0f} t={t:+.2f} win={wins}/64 | {({k: v for k, v in c.items() if v != build.DEFAULT[k]})}", flush=True)
        (HERE / "final.json").write_text(json.dumps(final, indent=1))
    print("done", flush=True)

if __name__ == "__main__":
    main()
