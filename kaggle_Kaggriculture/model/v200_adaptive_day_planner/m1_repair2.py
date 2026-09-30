"""修补测试变体:pre=先局部搜索腾空隙;extra=补不回时新增 1 名雇工(t0+2 于仓库口出现)。"""
import sys, glob, json, time, random, statistics as st, collections
from concurrent.futures import ProcessPoolExecutor
import day_model as dm
import planner_v2 as p2
from planner_v1 import build_chains, to_schedule

def closure(pb, chains, frac, rnd):
    ds = {i for g in chains if rnd.random() < frac for i in g}
    succ = collections.defaultdict(list)
    for tk in pb["tasks"]:
        if tk["pred"] is not None: succ[tk["pred"]].append(tk["id"])
    cmap = {i: tuple(g) for g in chains for i in g}
    while True:
        n0 = len(ds); stack = list(ds)
        while stack:
            x = stack.pop()
            for y in succ[x]:
                if y not in ds: ds.add(y); stack.append(y)
        for i in list(ds): ds.update(cmap[i])
        if len(ds) == n0: return ds, cmap

def reinsert(plan, pb, ds, cmap, allow_extra):
    owner = {}; failed = 0; extra_used = 0
    for tid in sorted(ds, key=lambda i: pb["tasks"][i]["t"]):
        g = cmap[tid]; placed = False
        for attempt in range(2):
            fixed = owner.get(g)
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
            for d_, u, trial in sorted(cands, key=lambda x: x[0])[:8]:
                nr = dict(plan.route); nr[u] = trial
                okg, fin2, _ = plan.global_eval(nr)
                if okg: plan.route, plan.finish = nr, fin2; owner[g] = u; placed = True; break
            if placed or not allow_extra or fixed is not None: break
            # 新增一名雇工
            nu = max(plan.U) + 1
            plan.U[nu] = dict(appear=pb["t0"] + 2, pos=(4, 4)); plan.route[nu] = []; extra_used += 1
        if not placed: failed += 1
    return failed, extra_used

def run(job):
    fn, frac, pre, extra, tl = job
    D = dm.load(fn); S = D["steps"]; out = []
    for day in range(30):
        pb = dm.day_problem(D, day)
        inv0 = {i: S[pb["t0"]]["inv"][i] for i in range(len(S[pb["t0"]]["inv"]))}
        plan, ok, mv0 = p2.init_from_tape(pb)
        if not ok: out.append(dict(day=day, status="init_infeasible")); continue
        chains = build_chains(pb)
        if pre: p2.local_search(plan, chains, time_limit=tl)
        base_mv = plan.global_eval(plan.route)[2]
        rnd = random.Random(day * 131 + len(pb["tasks"]))
        ds, cmap = closure(pb, chains, frac, rnd)
        plan.route = {u: [x for x in r if x not in ds] for u, r in plan.route.items()}
        okr, fin, _ = plan.global_eval(plan.route)
        if not okr: out.append(dict(day=day, status="remove_infeasible")); continue
        plan.finish = fin
        failed, extra_used = reinsert(plan, pb, ds, cmap, extra)
        if failed: out.append(dict(day=day, status="insert_fail", failed=failed, dropped=len(ds), extra=extra_used)); continue
        ins = plan.global_eval(plan.route)[2]
        p2.local_search(plan, chains, time_limit=tl)
        okc, viol, mvc, nd = dm.check(pb, to_schedule(plan), inv0)
        out.append(dict(day=day, status="ok" if okc else "check_fail", tape=pb["tape_moves"], base=base_mv, insert=ins, final=mvc, dropped=len(ds), extra=extra_used, viol=[v[0] for v in viol][:2]))
    return out

if __name__ == "__main__":
    frac = float(sys.argv[1]); tl = float(sys.argv[2])
    files = sorted(glob.glob("data/tape_*.json.gz"))
    for pre, extra in ((True, False), (False, True), (True, True)):
        with ProcessPoolExecutor(6) as ex:
            R = [r for rows in ex.map(run, [(f, frac, pre, extra, tl) for f in files]) for r in rows]
        ok = [r for r in R if r["status"] == "ok"]
        c = collections.Counter(r["status"] for r in R)
        line = f"先腾空隙={pre} 可加人={extra}: {dict(c)}"
        if ok:
            line += f" | 成功天 走路/带子 {sum(r['final'] for r in ok)/sum(r['tape'] for r in ok):.3f} 插回时 {sum(r['insert'] for r in ok)/sum(r['tape'] for r in ok):.3f} 拿掉中位 {st.median(r['dropped'] for r in ok)} 加人天数 {sum(1 for r in ok if r['extra'])} 加人合计 {sum(r['extra'] for r in ok)}"
        print(line, flush=True)
        json.dump(R, open(f"data/m1_repair2_pre{int(pre)}_extra{int(extra)}.json", "w"))
