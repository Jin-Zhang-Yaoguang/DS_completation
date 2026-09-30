"""配对 racing 评估器(successive halving):候选包 vs 父包,同 seed×同对手配对差分。

口径:对手 = opponent_pool_v1/evaluate.py 的 8 个分层对手(同权重);每个(对手, seed)对打一局候选、一局父包,
差分 d = margin(候选) - margin(父包);加权均值 + 配对 t。自然 seed(不 force 商店)。
racing:各候选先跑 rung0 seeds,按加权配对差排序淘汰一半,幸存者追加 seeds,直到剩 1 个或 seeds 用完。
所有局结果缓存到 cache/<pack_stem>.jsonl(父包结果跨候选复用)。

用法: python race.py --parent <main.py> --cands a.py b.py ... --rungs 4,8,16,32 [--holdout]
"""
import sys, json, argparse, statistics as S
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
POOL = MODEL / "opponent_pool_v1"
OPP = [
    ("ymg0", f"tape:{POOL/'tapes/ymg_slice0.json'}", 2.0),
    ("ymg1", f"tape:{POOL/'tapes/ymg_slice1.json'}", 2.0),
    ("spataro", f"tape:{POOL/'tapes/nl_SpaTaro_107289135.json'}", 1.5),
    ("otter", f"tape:{POOL/'tapes/nl_Otter_Vibe_107377081.json'}", 1.5),
    ("fta0", f"tape:{POOL/'tapes/fta_slice0.json'}", 1.5),
    ("y67", f"sub:{POOL/'packs/y67_main.py'}", 2.0),
    ("p955", f"sub:{POOL/'packs/p955_main.py'}", 1.0),
    ("ult", f"tape:{POOL/'tapes/ult_normal.json'}", 0.5),
]
W = {n: w for n, _, w in OPP}
# 自然 seed 序列:训练用 1000+,holdout 用 900000+,互不重叠
TRAIN_SEEDS = [1009 + 37 * i for i in range(64)]
HOLD_SEEDS = [900007 + 53 * i for i in range(64)]
CACHE = HERE / "cache"; CACHE.mkdir(exist_ok=True)

def one(job):
    pack, opp_name, opp_spec, seed, seat = job
    sys.path.insert(0, str(MODEL / "v16_online_fidelity")); sys.path.insert(0, str(MODEL / "v4_demand_race" / "harness"))
    import engine, fidelity
    specs = [None, None]; specs[seat] = f"sub:{pack}"; specs[1 - seat] = opp_spec
    ags = [fidelity.make_agent(specs[0]), fidelity.make_agent(specs[1])]
    g = engine.load_kagsim().Game(seed=seed)
    fb = {"farmer": ["PASS"], "hands": [], "market": []}
    for _ in range(719):
        acts = []
        for p in (0, 1):
            try: acts.append(ags[p](g.observe(p)))
            except Exception: acts.append(dict(fb))
        g.step(acts[0], acts[1])
    return (pack, opp_name, seed, seat, float(g.reward(seat) - g.reward(1 - seat)))

def load_cache(pack):
    f = CACHE / f"{Path(pack).stem}.jsonl"; d = {}
    if f.exists():
        for l in f.open():
            r = json.loads(l); d[(r["opp"], r["seed"], r["seat"])] = r["m"]
    return d

def ensure(packs, seeds, seat, ex):
    jobs = []
    caches = {p: load_cache(p) for p in packs}
    for p in packs:
        for n, spec, _ in OPP:
            for s in seeds:
                if (n, s, seat) not in caches[p]:
                    jobs.append((p, n, spec, s, seat))
    for pack, n, s, st, m in ex.map(one, jobs, chunksize=2):
        caches[pack][(n, s, st)] = m
        with (CACHE / f"{Path(pack).stem}.jsonl").open("a") as f:
            f.write(json.dumps({"opp": n, "seed": s, "seat": st, "m": m}) + "\n")
    return caches

def paired(caches, parent, cand, seeds, seat):
    per_seed = []
    per_opp = {}
    for s in seeds:
        num = sum(W[n] * (caches[cand][(n, s, seat)] - caches[parent][(n, s, seat)]) for n, _, _ in OPP)
        per_seed.append(num / sum(W.values()))
    for n, _, _ in OPP:
        per_opp[n] = S.mean(caches[cand][(n, s, seat)] - caches[parent][(n, s, seat)] for s in seeds)
    m = S.mean(per_seed); sd = S.stdev(per_seed) if len(per_seed) > 1 else 0
    t = m / (sd / len(per_seed) ** 0.5) if sd > 0 else 0.0
    wins = sum(1 for x in per_seed if x > 0)
    return m, t, wins, per_opp

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--parent", required=True); ap.add_argument("--cands", nargs="+", required=True)
    ap.add_argument("--rungs", default="4,8,16,32"); ap.add_argument("--holdout", action="store_true")
    ap.add_argument("--seat", type=int, default=0); ap.add_argument("--workers", type=int, default=14)
    a = ap.parse_args()
    parent = str(Path(a.parent).resolve()); alive = [str(Path(c).resolve()) for c in a.cands]
    pool = HOLD_SEEDS if a.holdout else TRAIN_SEEDS
    rungs = [int(x) for x in a.rungs.split(",")]
    with ProcessPoolExecutor(a.workers) as ex:
        for ri, n_seed in enumerate(rungs):
            seeds = pool[:n_seed]
            caches = ensure([parent] + alive, seeds, a.seat, ex)
            scored = []
            for c in alive:
                m, t, wins, per_opp = paired(caches, parent, c, seeds, a.seat)
                scored.append((m, t, wins, per_opp, c))
            scored.sort(key=lambda x: -x[0])
            print(f"== rung{ri} seeds={n_seed} ({'holdout' if a.holdout else 'train'}) alive={len(alive)}", flush=True)
            for m, t, wins, per_opp, c in scored:
                opp_txt = " ".join(f"{k}:{v:+.0f}" for k, v in per_opp.items())
                print(f"  {Path(c).stem:34s} d={m:+7.0f} t={t:+5.2f} win={wins}/{n_seed} | {opp_txt}", flush=True)
            if ri < len(rungs) - 1 and len(alive) > 1:
                keep = max(1, (len(alive) + 1) // 2)
                alive = [c for _, _, _, _, c in scored[:keep]]
    print("done", flush=True)
