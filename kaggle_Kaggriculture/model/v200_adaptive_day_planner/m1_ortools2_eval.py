import sys, glob, json, time, random, statistics as st, collections, copy
from concurrent.futures import ProcessPoolExecutor
import day_model as dm, planner_ortools2 as po2, planner_ortools as po
from planner_v1 import to_schedule

def run(job):
    fn, mode, frac, tl, days = job
    D = dm.load(fn); S = D["steps"]; out = []
    for day in days:
        pb = dm.day_problem(D, day)
        inv0 = {i: S[pb["t0"]]["inv"][i] for i in range(len(S[pb["t0"]]["inv"]))}
        init = collections.defaultdict(list)
        for tk in sorted(pb["tasks"], key=lambda x: x["t"]): init[tk["unit"]].append(tk["id"])
        ndrop = 0
        if mode == "repair":
            rnd = random.Random(day * 131 + len(pb["tasks"]))
            drop = {tk["id"] for tk in pb["tasks"] if rnd.random() < frac}; ndrop = len(drop)
            init = {u: [x for x in r if x not in drop] for u, r in init.items()}
        t1 = time.time()
        res = po2.solve(pb, inv0, init_routes=dict(init), time_limit=tl)
        sec = time.time() - t1
        if res is None: out.append(dict(day=day, status="no_solution", sec=sec)); continue
        if res["missing"]: out.append(dict(day=day, status="missing", missing=len(res["missing"]), init_ok=res.get("init_ok"), sec=sec)); continue
        plan, okp, mvp = po.to_plan(pb, inv0, res["routes"])
        okc, viol, mvc, nd = dm.check(pb, to_schedule(plan), inv0) if okp else (False, [("规划器推演不可行",)], None, None)
        out.append(dict(day=day, status="ok" if okc else "check_fail", tape=pb["tape_moves"], final=mvc, dropped=ndrop, synth=sum(1 for tk in pb["tasks"] if tk.get("synthetic")), sec=sec, viol=[v[0] for v in viol][:2]))
    return out

if __name__ == "__main__":
    mode = sys.argv[1]; frac = float(sys.argv[2]); tl = float(sys.argv[3]); nf = int(sys.argv[4]); days = [int(x) for x in sys.argv[5].split(",")] if len(sys.argv) > 5 else list(range(30))
    files = sorted(glob.glob("data/tape_*.json.gz"))[:nf]
    with ProcessPoolExecutor(6) as ex:
        R = [r for rows in ex.map(run, [(f, mode, frac, tl, days) for f in files]) for r in rows]
    json.dump(R, open(f"data/m1or2_{mode}_{frac}_{tl}.json", "w"))
    c = collections.Counter(r["status"] for r in R); ok = [r for r in R if r["status"] == "ok"]
    print(f"[OR-Tools配对 {mode} frac={frac} 限时{tl}s] {dict(c)}")
    if ok: print(f"  成功天 走路/带子 {sum(r['final'] for r in ok)/sum(r['tape'] for r in ok):.3f} 逐天中位 {st.median(r['final']/max(1,r['tape']) for r in ok):.3f};拿掉中位 {st.median(r['dropped'] for r in ok)};合成取货中位 {st.median(r['synth'] for r in ok)};求解耗时中位 {st.median(r['sec'] for r in ok):.2f}s")
    print("  失败样例:", [(r['day'], r['status'], r.get('viol') or r.get('missing'), r.get('init_ok')) for r in R if r['status'] != 'ok'][:8])
