import sys, glob, json, time, random, statistics as st, collections
from concurrent.futures import ProcessPoolExecutor
import day_model as dm, planner_v3 as p3
from planner_v1 import to_schedule

def run(job):
    fn, mode, frac, tl = job
    D = dm.load(fn); S = D["steps"]; out = []
    for day in range(30):
        pb = dm.day_problem(D, day)
        inv0 = {i: S[pb["t0"]]["inv"][i] for i in range(len(S[pb["t0"]]["inv"]))}
        plan, ok, mv0 = p3.init_from_tape(pb, inv0)
        if not ok: out.append(dict(day=day, status="init_infeasible")); continue
        t1 = time.time()
        if mode == "improve":
            p3.local_search(plan, time_limit=tl)
        else:
            rnd = random.Random(day * 131 + len(pb["tasks"]))
            drop = {tk["id"] for tk in pb["tasks"] if rnd.random() < frac}
            succ = collections.defaultdict(list)
            for tk in pb["tasks"]:
                if tk["pred"] is not None: succ[tk["pred"]].append(tk["id"])
            from planner_v1 import build_chains
            cmap = {i: g for g in build_chains(pb) for i in g}
            while True:
                n0 = len(drop); stack = list(drop)
                while stack:
                    x = stack.pop()
                    for y in succ[x]:
                        if y not in drop: drop.add(y); stack.append(y)
                for i in list(drop): drop.update(cmap[i])
                if len(drop) == n0: break
            plan.route = {u: [x for x in r if x not in drop] for u, r in plan.route.items()}
            okr, fin, _ = plan.global_eval(plan.route)
            if not okr: out.append(dict(day=day, status="remove_infeasible", dropped=len(drop))); continue
            plan.finish = fin; failed = 0
            for tid in sorted(drop, key=lambda i: pb["tasks"][i]["t"]):
                if not p3.try_insert(plan, tid): failed += 1
            if failed: out.append(dict(day=day, status="insert_fail", failed=failed, dropped=len(drop))); continue
            p3.local_search(plan, time_limit=tl)
        okc, viol, mvc, nd = dm.check(pb, to_schedule(plan), inv0)
        out.append(dict(day=day, status="ok" if okc else "check_fail", tape=pb["tape_moves"], init=mv0, final=mvc, dropped=len(drop) if mode != "improve" else 0,
                        synth=sum(1 for tk in pb["tasks"] if tk.get("synthetic")), sec=time.time() - t1, viol=[v[0] for v in viol][:2]))
    return out

if __name__ == "__main__":
    mode = sys.argv[1]; frac = float(sys.argv[2]); tl = float(sys.argv[3])
    files = sorted(glob.glob("data/tape_*.json.gz"))
    with ProcessPoolExecutor(6) as ex:
        R = [r for rows in ex.map(run, [(f, mode, frac, tl) for f in files]) for r in rows]
    json.dump(R, open(f"data/m1v3_{mode}_{frac}.json", "w"))
    c = collections.Counter(r["status"] for r in R); ok = [r for r in R if r["status"] == "ok"]
    print(f"[{mode} frac={frac}] {dict(c)}")
    if ok: print(f"  成功天 走路/带子 {sum(r['final'] for r in ok)/sum(r['tape'] for r in ok):.3f} 逐天中位 {st.median(r['final']/max(1,r['tape']) for r in ok):.3f};拿掉中位 {st.median(r['dropped'] for r in ok)} 合成取货中位 {st.median(r['synth'] for r in ok)};耗时中位 {st.median(r['sec'] for r in ok):.1f}s 最大 {max(r['sec'] for r in ok):.1f}s")
    print("  失败样例:", [(r['day'], r['status'], r.get('viol') or r.get('failed')) for r in R if r['status'] not in ('ok',)][:6])
