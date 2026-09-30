"""家族 tape 对战矩阵：不钉商店（引擎自然 RNG），多 seed 双席位。"""
import sys, json
from concurrent.futures import ProcessPoolExecutor
from fidelity import play
def one(a):
    s0, s1, seed = a
    r = play(s0, s1, seed, [])
    return (s0, s1, seed, r["bank"], r["prod"])
if __name__ == "__main__":
    cand, opps, seeds = sys.argv[1], sys.argv[2].split(","), [int(x) for x in sys.argv[3].split(",")]
    jobs = []
    for o in opps:
        for sd in seeds:
            jobs.append((cand, o, sd)); jobs.append((o, cand, sd))
    res = {}
    with ProcessPoolExecutor(8) as ex:
        for s0, s1, seed, bank, prod in ex.map(one, jobs):
            opp = s1 if s0 == cand else s0
            mine = bank[0] if s0 == cand else bank[1]
            theirs = bank[1] if s0 == cand else bank[0]
            pm = prod[0] if s0 == cand else prod[1]
            res.setdefault(opp, []).append((mine, theirs, pm))
    for opp, rs in res.items():
        w = sum(m > t for m, t, _ in rs); n = len(rs)
        mm = sum(m for m, _, _ in rs) / n; tt = sum(t for _, t, _ in rs) / n
        straw = sum(p.get("STRAWBERRY", 0) for _, _, p in rs) / n; wool = sum(p.get("WOOL", 0) for _, _, p in rs) / n
        name = opp.split("/")[-1].replace(".json", "")
        print(f"{name:22s} w={w}/{n} mine={mm:7.0f} theirs={tt:7.0f} my_straw={straw:.0f} my_wool={wool:.0f}", flush=True)
