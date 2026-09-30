import glob, random, collections, sys, statistics as st
from concurrent.futures import ProcessPoolExecutor
import day_model as dm, planner_ortools as po
from planner_v1 import to_schedule
def run(job):
    fn, day, extra, tl = job
    D = dm.load(fn); S = D["steps"]; pb = dm.day_problem(D, day)
    inv0 = {i: S[pb["t0"]]["inv"][i] for i in range(len(S[pb["t0"]]["inv"]))}
    init = collections.defaultdict(list)
    for tk in sorted(pb["tasks"], key=lambda x: x["t"]): init[tk["unit"]].append(tk["id"])
    rnd = random.Random(day * 131 + len(pb["tasks"])); drop = {tk["id"] for tk in pb["tasks"] if rnd.random() < 0.2}
    init = {u: [x for x in r if x not in drop] for u, r in init.items()}
    res = po.solve(pb, inv0, init_routes=init, time_limit=tl, extra_ops=extra)
    if res is None: return (extra, "nosol", None, None)
    if res["missing"]: return (extra, "missing", len(res["missing"]), sum(1 for t in pb["tasks"] if t.get("synthetic")))
    plan, okp, _ = po.to_plan(pb, inv0, res["routes"])
    okc, viol, mvc, _ = dm.check(pb, to_schedule(plan), inv0) if okp else (False, [], None, None)
    return (extra, "ok" if okc else "check_fail", mvc / max(1, pb["tape_moves"]) if okc else None, sum(1 for t in pb["tasks"] if t.get("synthetic")))
if __name__ == "__main__":
    tl = float(sys.argv[1])
    files = sorted(glob.glob("data/tape_*.json.gz"))[:2]
    jobs = [(f, d, e, tl) for f in files for d in range(0, 30, 2) for e in (False, True)]
    with ProcessPoolExecutor(6) as ex: R = list(ex.map(run, jobs))
    for e in (False, True):
        v = [r for r in R if r[0] == e]
        ok = [r for r in v if r[1] == "ok"]
        print(f"额外算子={e} 限时{tl}s: {collections.Counter(r[1] for r in v)} 成功天走路/带子中位 {st.median(r[2] for r in ok) if ok else '-'} 合成取货中位 {st.median(r[3] for r in v if r[3] is not None)}")
