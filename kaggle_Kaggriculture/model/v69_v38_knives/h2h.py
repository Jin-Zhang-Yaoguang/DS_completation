"""候选包 vs 父包镜像对打(席位对称,只跑 seat0):逐 seed margin、均值、胜局。
用法: python h2h.py <parent.py> <seedlist:start,count> <cand.py ...>
"""
import sys, statistics as S
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
MODEL = Path(__file__).resolve().parents[1]

def one(job):
    cand, parent, seed = job
    sys.path.insert(0, str(MODEL / "v16_online_fidelity")); sys.path.insert(0, str(MODEL / "v4_demand_race" / "harness"))
    import engine, fidelity
    ags = [fidelity.make_agent(f"sub:{cand}"), fidelity.make_agent(f"sub:{parent}")]
    g = engine.load_kagsim().Game(seed=seed); fb = {"farmer": ["PASS"], "hands": [], "market": []}
    for _ in range(719):
        acts = []
        for p in (0, 1):
            try: acts.append(ags[p](g.observe(p)))
            except Exception: acts.append(dict(fb))
        g.step(acts[0], acts[1])
    return cand, seed, float(g.reward(0) - g.reward(1))

if __name__ == "__main__":
    parent = str(Path(sys.argv[1]).resolve()); start, count = (int(x) for x in sys.argv[2].split(","))
    cands = [str(Path(c).resolve()) for c in sys.argv[3:]]
    seeds = [800, 801, 700, 701] + [start + 29 * i for i in range(count)]
    with ProcessPoolExecutor(14) as ex:
        res = list(ex.map(one, [(c, parent, s) for c in cands for s in seeds]))
    for c in cands:
        ms = [(s, m) for cc, s, m in res if cc == c]
        vals = [m for _, m in ms]
        sd = S.stdev(vals); t = S.mean(vals) / (sd / len(vals) ** 0.5) if sd else 0
        print(f"{Path(c).stem:16s} n={len(vals)} mean={S.mean(vals):+7.0f} t={t:+.2f} win={sum(v > 0 for v in vals)} tie={sum(v == 0 for v in vals)} loss={sum(v < 0 for v in vals)} "
              f"| 800:{ms[0][1]:+.0f} 801:{ms[1][1]:+.0f} 700:{ms[2][1]:+.0f} 701:{ms[3][1]:+.0f} worst={min(vals):+.0f}")
