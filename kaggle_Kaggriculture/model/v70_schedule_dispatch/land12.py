import sys, statistics
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE / "proto"))
def one(job):
    seed, seat, opp, kind = job
    import sched_proto as sp
    from sched_v0d import record_full
    from incr_land import IncrLand
    from perturb import play
    me = f"sub:{sp.S}/y68x3b13_main.py"; op_spec = f"sub:{sp.S}/{opp}_main.py"
    rec = record_full(me, op_spec, seed, seat)
    ag = IncrLand(rec, me, nw=0, plant_until=0, active=(kind == "land"))
    b0, b1 = play(ag, op_spec, seed, seat)
    return seed, opp, kind, b0, b0 - b1
if __name__ == "__main__":
    jobs = [(s, s % 2, o, k) for s in range(1100, 1106) for o in ("y68s2", "y68r2") for k in ("hybrid", "land")]
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(one, jobs))
    base = {(r[0], r[1]): r for r in res if r[2] == "hybrid"}
    diffs = []
    for r in res:
        if r[2] != "land": continue
        b = base[(r[0], r[1])]
        diffs.append((r[0], r[1], round(r[3] - b[3]), round(r[4] - b[4]), r[4] > 0, b[4] > 0))
    for d in sorted(diffs, key=lambda x: x[2]): print(f"  seed{d[0]} vs {d[1]:6s} 银行差 {d[2]:+7d} 分差变化 {d[3]:+7d} 胜负 {d[5]}→{d[4]}")
    print(f"银行差 中位 {statistics.median(d[2] for d in diffs):+.0f} 全正 {sum(d[2]>0 for d in diffs)}/12  胜局 {sum(d[5] for d in diffs)}→{sum(d[4] for d in diffs)}")
