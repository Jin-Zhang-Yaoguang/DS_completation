"""M1 正式评估:12 局×30 天。improve=带子初始解+局部搜索;repair=拿掉 frac 比例链再插回+局部搜索。均用 day_model.check 复核。"""
import sys, glob, json, time, statistics as st
from concurrent.futures import ProcessPoolExecutor
import day_model as dm
import planner_v2 as p2
from planner_v1 import build_chains, to_schedule

def run_file(job):
    fn, mode, frac, tl = job
    D = dm.load(fn); S = D["steps"]; out = []
    for day in range(30):
        pb = dm.day_problem(D, day)
        inv0 = {i: S[pb["t0"]]["inv"][i] for i in range(len(S[pb["t0"]]["inv"]))}
        t1 = time.time()
        if mode == "improve":
            plan, ok, mv0 = p2.init_from_tape(pb)
            if not ok: out.append(dict(fn=fn, day=day, status="init_infeasible")); continue
            mv1 = p2.local_search(plan, build_chains(pb), time_limit=tl)
            okc, viol, mvc, nd = dm.check(pb, to_schedule(plan), inv0)
            out.append(dict(fn=fn, day=day, status="ok" if okc else "check_fail", tape=pb["tape_moves"], init=mv0, final=mvc, ntask=len(pb["tasks"]), sec=time.time() - t1, viol=[v[0] for v in viol][:2]))
        else:
            plan, ok, mv0 = p2.init_from_tape(pb)
            if not ok: out.append(dict(fn=fn, day=day, status="init_infeasible")); continue
            import random
            chains = build_chains(pb); rnd = random.Random(day * 131 + len(pb["tasks"]))
            drop = [g for g in chains if rnd.random() < frac]; ds = {i for g in drop for i in g}
            succ = {}
            for tk in pb["tasks"]:
                if tk["pred"] is not None: succ.setdefault(tk["pred"], []).append(tk["id"])
            cmap = {i: tuple(g) for g in chains for i in g}
            while True:
                n0 = len(ds)
                stack = list(ds)
                while stack:
                    x = stack.pop()
                    for y in succ.get(x, []):
                        if y not in ds: ds.add(y); stack.append(y)
                for i in list(ds): ds.update(cmap[i])
                if len(ds) == n0: break
            drop = list({cmap[i] for i in ds})
            plan.route = {u: [x for x in r if x not in ds] for u, r in plan.route.items()}
            okr, fin, _ = plan.global_eval(plan.route)
            if not okr: out.append(dict(fn=fn, day=day, status="remove_infeasible")); continue
            plan.finish = fin; failed = 0
            owner = {}   # 链 -> 单位
            for tid in sorted(ds, key=lambda i: pb["tasks"][i]["t"]):
                g = cmap[tid]; fixed = owner.get(g)
                units = [fixed] if fixed is not None else list(plan.route)
                cands = []
                for u in units:
                    r = plan.route[u]; ok0, _, mv0 = plan.simulate(u, r, plan.finish)
                    if not ok0: continue
                    pmin = 0
                    if fixed is not None:
                        mates = [x for x in g if x in r]
                        if mates: pmin = max(r.index(x) for x in mates) + 1
                    for p in range(pmin, len(r) + 1):
                        trial = r[:p] + [tid] + r[p:]
                        ok2, _, mv = plan.simulate(u, trial, plan.finish)
                        if ok2: cands.append((mv - mv0, u, trial))
                placed = False
                for d_, u, trial in sorted(cands, key=lambda x: x[0])[:6]:
                    nr = dict(plan.route); nr[u] = trial
                    okg, fin2, _ = plan.global_eval(nr)
                    if okg:
                        plan.route, plan.finish = nr, fin2; owner[g] = u; placed = True; break
                if not placed: failed += 1
            ins = plan.global_eval(plan.route)[2] if failed == 0 else None
            fin_mv = p2.local_search(plan, chains, time_limit=tl) if failed == 0 else None
            okc, viol, mvc, nd = dm.check(pb, to_schedule(plan), inv0) if failed == 0 else (False, [("插不回",)], None, None)
            out.append(dict(fn=fn, day=day, status="ok" if okc else ("insert_fail" if failed else "check_fail"), tape=pb["tape_moves"], init=mv0, dropped=len(ds), failed=failed, insert=ins, final=mvc, ntask=len(pb["tasks"]), sec=time.time() - t1, viol=[v[0] for v in viol][:2]))
    return out

if __name__ == "__main__":
    mode = sys.argv[1]; frac = float(sys.argv[2]); tl = float(sys.argv[3])
    files = sorted(glob.glob("data/tape_*.json.gz"))
    with ProcessPoolExecutor(6) as ex:
        R = [r for rows in ex.map(run_file, [(f, mode, frac, tl) for f in files]) for r in rows]
    json.dump(R, open(f"data/m1_{mode}_{frac}_{tl}.json", "w"))
    from collections import Counter
    print("状态:", Counter(r["status"] for r in R))
    ok = [r for r in R if r["status"] == "ok"]
    if ok:
        print(f"可行天 {len(ok)}/{len(R)};带子实际移动 {sum(r['tape'] for r in ok)} | 带子派工重寻路 {sum(r['init'] for r in ok)} | 最终 {sum(r['final'] for r in ok)} (相对带子 {sum(r['final'] for r in ok)/sum(r['tape'] for r in ok):.3f});逐天比中位 {st.median(r['final']/max(1,r['tape']) for r in ok):.3f} 90分位 {sorted(r['final']/max(1,r['tape']) for r in ok)[int(len(ok)*0.9)]:.3f};耗时中位 {st.median(r['sec'] for r in ok):.1f}s 最大 {max(r['sec'] for r in ok):.1f}s")
    if mode == "repair":
        dr = [r['dropped'] for r in R if 'dropped' in r]
        if dr and ok: print(f"拿掉任务中位 {st.median(dr)};插回后(局部搜索前)相对带子 {sum(r['insert'] for r in ok)/sum(r['tape'] for r in ok):.3f}")
    print("失败样例:", [ (r['fn'][-28:], r['day'], r['status'], r.get('viol')) for r in R if r['status'] != 'ok'][:6])
