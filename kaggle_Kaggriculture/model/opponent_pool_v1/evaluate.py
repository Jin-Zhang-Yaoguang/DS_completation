"""进化线 fitness 评测:候选 main.py -> 分层对手池加权得分。
用法: python evaluate.py <candidate_main.py> [seed0 seed1 ...](默认 11 22)
输出: 每对手 margin + 加权 fitness(margin 截断到 [-20k, +20k] 防单局爆炸主导)。
"""
import sys, os, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

HERE = Path(__file__).resolve().parent
MODEL = HERE.parent

OPP = [
    ("ymg0",   "tape", HERE / "tapes" / "ymg_slice0.json",             2.0),
    ("ymg1",   "tape", HERE / "tapes" / "ymg_slice1.json",             2.0),
    ("spataro","tape", HERE / "tapes" / "nl_SpaTaro_107289135.json",   1.5),
    ("otter",  "tape", HERE / "tapes" / "nl_Otter_Vibe_107377081.json",1.5),
    ("fta0",   "tape", HERE / "tapes" / "fta_slice0.json",             1.5),
    ("y67",    "sub",  HERE / "packs" / "y67_main.py",                 2.0),
    ("p955",   "sub",  HERE / "packs" / "p955_main.py",                1.0),
    ("ult",    "tape", HERE / "tapes" / "ult_normal.json",             0.5),
]

def one(job):
    cand, name, kind, path, sd = job
    sys.path.insert(0, str(MODEL / "v16_online_fidelity"))
    sys.path.insert(0, str(MODEL / "v4_demand_race" / "harness"))
    import fidelity
    r = fidelity.play(f"sub:{cand}", f"{kind}:{path}", sd, [])
    return (name, sd, r["bank"][0] - r["bank"][1])

if __name__ == "__main__":
    cand = str(Path(sys.argv[1]).resolve())
    seeds = [int(x) for x in sys.argv[2:]] or [11, 22]
    jobs = [(cand, n, k, str(p), sd) for n, k, p, w in OPP for sd in seeds]
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(one, jobs))
    from collections import defaultdict
    agg = defaultdict(list)
    for name, sd, m in res:
        agg[name].append(m)
    wmap = {n: w for n, k, p, w in OPP}
    fit, wsum = 0.0, 0.0
    for name, ms in agg.items():
        avg = sum(ms) / len(ms)
        clip = max(-20000, min(20000, avg))
        fit += wmap[name] * clip; wsum += wmap[name]
        print(f"{name:8s} w={wmap[name]:.1f} avg={avg:+9.0f} " + " ".join(f"{m:+.0f}" for m in ms))
    print(f"fitness = {fit / wsum:+.0f}")
