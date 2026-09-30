"""日规划器 v2:带子编排为初始解 + 局部搜索(链重定位)+ 修补测试(拿掉部分链再插回)。"""
import collections, random, time, sys, glob, statistics as st
import day_model as dm
from planner_v1 import Plan, build_chains, earliest, dist, to_schedule

def init_from_tape(pb):
    plan = Plan(pb)
    for tk in sorted(pb["tasks"], key=lambda x: x["t"]):
        plan.route[tk["unit"]].append(tk["id"])
    ok, fin, mv = plan.global_eval(plan.route)
    plan.finish = fin or {}
    return plan, ok, mv

def chain_of(chains):
    m = {}
    for g in chains:
        for i in g: m[i] = tuple(g)
    return m

def insert_chain(plan, g, routes):
    """在所有单位的所有位置尝试插入链(链内顺序保持,逐任务贪心定位);返回 (增量, 新 routes) 中全员可行的最佳者。"""
    cands = []
    for u in routes:
        r = routes[u]; ok0, _, mv0 = plan.simulate(u, r, plan.finish)
        if not ok0: continue
        cand = list(r); pmin = 0; ok = True
        for tid in g:
            best = None
            for p in range(pmin, len(cand) + 1):
                trial = cand[:p] + [tid] + cand[p:]
                ok2, _, mv = plan.simulate(u, trial, plan.finish)
                if ok2 and (best is None or mv < best[0]): best = (mv, p)
            if best is None: ok = False; break
            cand = cand[:best[1]] + [tid] + cand[best[1]:]; pmin = best[1] + 1
        if ok:
            ok3, _, mv = plan.simulate(u, cand, plan.finish)
            if ok3: cands.append((mv - mv0, u, cand))
    for d, u, cand in sorted(cands, key=lambda x: x[0]):
        nr = dict(routes); nr[u] = cand
        okg, fin, tot = plan.global_eval(nr)
        if okg: return d, nr, fin, tot
    return None

def local_search(plan, chains, time_limit=3.0, seed=0):
    rnd = random.Random(seed); t0 = time.time()
    ok, fin, cur = plan.global_eval(plan.route)
    if not ok: return cur
    plan.finish = fin; improved = True; rounds = 0
    while improved and time.time() - t0 < time_limit:
        improved = False; rounds += 1
        order = list(chains); rnd.shuffle(order)
        for g in order:
            if time.time() - t0 > time_limit: break
            removed = {u: [x for x in r if x not in g] for u, r in plan.route.items()}
            okr, finr, totr = plan.global_eval(removed)
            if not okr: continue
            saved = plan.finish; plan.finish = finr
            res = insert_chain(plan, g, removed)
            if res and res[3] < cur:
                plan.route, plan.finish, cur = res[1], res[2], res[3]; improved = True
            else:
                plan.finish = saved
    return cur

def repair_test(pb, frac, seed, time_limit):
    plan, ok, tape_mv = init_from_tape(pb)
    if not ok: return None
    chains = build_chains(pb); rnd = random.Random(seed)
    drop = [g for g in chains if rnd.random() < frac]
    dropset = {i for g in drop for i in g}
    plan.route = {u: [x for x in r if x not in dropset] for u, r in plan.route.items()}
    okr, fin, _ = plan.global_eval(plan.route)
    if not okr: return None
    plan.finish = fin; failed = 0
    for g in sorted(drop, key=lambda g: min(earliest(pb, pb["tasks"][i]) for i in g)):
        res = insert_chain(plan, g, plan.route)
        if res is None: failed += len(g); continue
        plan.route, plan.finish = res[1], res[2]
    after_insert = plan.global_eval(plan.route)[2]
    final = local_search(plan, chains, time_limit=time_limit, seed=seed) if failed == 0 else after_insert
    return dict(tape=tape_mv, dropped=len(dropset), failed=failed, insert=after_insert, final=final)

if __name__ == "__main__":
    mode = sys.argv[1]; nfiles = int(sys.argv[2]); days = [int(x) for x in sys.argv[3].split(",")]
    R = []
    for fn in sorted(glob.glob("data/tape_*.json.gz"))[:nfiles]:
        D = dm.load(fn); S = D["steps"]
        for day in days:
            pb = dm.day_problem(D, day)
            inv0 = {i: S[pb["t0"]]["inv"][i] for i in range(len(S[pb["t0"]]["inv"]))}
            if mode == "improve":
                plan, ok, mv0 = init_from_tape(pb)
                if not ok: R.append(dict(day=day, ok=False)); continue
                t1 = time.time(); mv1 = local_search(plan, build_chains(pb), time_limit=float(sys.argv[4]))
                okc, viol, mvc, nd = dm.check(pb, to_schedule(plan), inv0)
                R.append(dict(day=day, ok=okc, tape=pb["tape_moves"], init=mv0, final=mv1, check_mv=mvc, sec=time.time() - t1, viol=[v[0] for v in viol][:2]))
            else:
                r = repair_test(pb, float(sys.argv[4]), seed=day, time_limit=float(sys.argv[5]))
                if r: r["day"] = day; r["tape_real"] = pb["tape_moves"]; R.append(r)
    if mode == "improve":
        good = [r for r in R if r.get("ok")]
        print(f"天 {len(R)} 复核可行 {len(good)};带子实际移动 {sum(r['tape'] for r in good)} | 带子派工重寻路 {sum(r['init'] for r in good)} | 局部搜索后 {sum(r['final'] for r in good)};耗时中位 {st.median(r['sec'] for r in good):.1f}s")
        bad = [r for r in R if not r.get("ok")]; print("不可行样例:", bad[:3])
    else:
        ok = [r for r in R if r["failed"] == 0]
        print(f"修补测试 天 {len(R)} 全部插回 {len(ok)};带子实际移动 {sum(r['tape_real'] for r in ok)} | 重寻路基准 {sum(r['tape'] for r in ok)} | 插回后 {sum(r['insert'] for r in ok)} | 局部搜索后 {sum(r['final'] for r in ok)};拿掉任务中位 {st.median(r['dropped'] for r in R)}")
        print("插不回样例:", [r for r in R if r["failed"]][:4])
