"""在独立命名空间执行调试包,读取 _R68_GATE 计数:R51/R68 各门禁在哪天、因何拒绝施肥巡回。"""
import sys, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent; MODEL = HERE.parent
sys.path.insert(0, str(HERE)); import race

def one(job):
    opp_spec, seed = job
    sys.path.insert(0, str(MODEL / "v16_online_fidelity")); sys.path.insert(0, str(MODEL / "v4_demand_race" / "harness"))
    import engine, fidelity
    ns = {}; exec(compile((HERE / "dbg_r68.py").read_text(), "dbg_r68.py", "exec"), ns)
    fns = [v for k, v in ns.items() if callable(v) and not k.startswith("__")]
    ags = [fns[-1], fidelity.make_agent(opp_spec)]
    g = engine.load_kagsim().Game(seed=seed); fb = {"farmer": ["PASS"], "hands": [], "market": []}
    for _ in range(719):
        acts = []
        for p in (0, 1):
            try: acts.append(ags[p](g.observe(p)))
            except Exception: acts.append(dict(fb))
        g.step(acts[0], acts[1])
    return dict(ns["_R68_GATE"])

if __name__ == "__main__":
    seeds = race.TRAIN_SEEDS[:8]
    jobs = [(spec, s) for _, spec, _ in race.OPP[:6] for s in seeds]
    with ProcessPoolExecutor(14) as ex:
        res = list(ex.map(one, jobs))
    tot = collections.Counter()
    for r in res:
        for k, v in r.items(): tot[k] += v / len(res)
    groups = collections.defaultdict(dict)
    for k, v in tot.items():
        head, _, tail = k.partition("|"); groups[head][tail] = v
    for head in sorted(groups):
        items = groups[head]
        if "" in items and len(items) == 1: print(f"{head:22s} {items['']:.2f}/game")
        else:
            ks = sorted(items, key=lambda x: int(x[1:]) if x[:1] == "d" else int(x) if x.isdigit() else 0)
            print(f"{head:22s} " + " ".join(f"{k}:{items[k]:.1f}" for k in ks))
