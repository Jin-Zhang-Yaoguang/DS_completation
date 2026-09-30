"""日规划器 v1:链化 + 按时间顺序的最廉价插入。输出逐步动作,用 day_model.check 复核。"""
import collections, time
import day_model as dm
MOVES = dm.MOVES
ANIMALS = ("COW", "SHEEP", "GOOSE", "CHICKEN")

def build_chains(pb):
    """按带子中同单位的物品来源->消耗关系连链(并查集)。"""
    tasks = pb["tasks"]; parent = list(range(len(tasks)))
    def find(a):
        while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
        return a
    by_unit = collections.defaultdict(list)
    for tk in tasks: by_unit[tk["unit"]].append(tk)
    for u, seq in by_unit.items():
        src = collections.defaultdict(list)   # item -> 来源任务栈
        for tk in sorted(seq, key=lambda x: x["t"]):
            need = None
            if tk["op"] in dm.CONSUME: need = dm.CONSUME[tk["op"]]
            elif tk["op"] == "PLACE" and tk["arg"] and tk["arg"][0] in ANIMALS: need = tk["arg"][0]
            elif tk["op"] in ("DROP", "PLACE"): need = next((k for k, v in tk["delta"].items() if v < 0), None)
            if need and src[need]:
                parent[find(tk["id"])] = find(src[need][-1])
            for k, v in tk["delta"].items():
                if v > 0: src[k].append(tk["id"])
    groups = collections.defaultdict(list)
    for tk in tasks: groups[find(tk["id"])].append(tk["id"])
    return [sorted(g, key=lambda i: tasks[i]["t"]) for g in groups.values()]

def earliest(pb, tk):
    e = pb["t0"]
    if tk["op"] == "PLANT" and tk["arg"]:
        bt = pb["buys"].get(f"BUY_SEED|{tk['arg'][0]}")
        if bt and pb.get("seeds0", {}).get(tk["arg"][0], 0) <= 0: e = max(e, min(bt) + 1)
    if tk["op"] == "PLACE" and tk["arg"] and tk["arg"][0] in ANIMALS:
        bt = pb["buys"].get(f"BUY_ANIMAL|{tk['arg'][0]}")
        if bt: e = max(e, min(bt) + 1)
    return e

def dist(a, b): return abs(a[0] - b[0]) + abs(a[1] - b[1])

class Plan:
    def __init__(self, pb):
        self.pb = pb; self.T = pb["tasks"]; self.U = pb["units"]
        self.route = {u: [] for u in self.U}          # task id 列表
        self.finish = {}                               # task id -> (t, u)
    def simulate(self, u, route, finish_known, partial=False):
        """推演单位路线。返回 (状态, 完成时刻 dict, 移动步数)。
        状态: True 可行 / False 超时 / "blocked" 前驱时刻未知(partial=True 时返回已算出的前缀)。"""
        pos = self.U[u]["pos"]; t = self.U[u]["appear"]; fin = {}; mv = 0
        for tid in route:
            tk = self.T[tid]
            d = dist(pos, tk["cell"])
            s = max(t + d, earliest(self.pb, tk))
            if tk["pred"] is not None:
                pf = fin.get(tk["pred"]) or finish_known.get(tk["pred"])
                if pf is None:
                    return ("blocked", fin, mv) if partial else (False, None, None)
                strict = tk.get("pred_op") in dm.STRICT_PRED or tk["op"] in ("PLANT", "PLACE")
                need = pf[0] if pf[1] < u else pf[0] + 1
                s = max(s, need)
            if s > self.pb["t_end"]: return False, None, None
            mv += d; fin[tid] = (s, u); pos = tk["cell"]; t = s + 1
        return True, fin, mv
    def global_eval(self, routes):
        """全员联合推演:允许部分推演逐轮推进,直到全部完成、超时或无进展。"""
        finish = {}
        for _ in range(40):
            progress = False; all_done = True; total = 0
            for u, r in routes.items():
                st_, fin, mv = self.simulate(u, r, finish, partial=True)
                if st_ is False: return False, None, None
                for k, v in fin.items():
                    if finish.get(k) != v: finish[k] = v; progress = True
                if st_ == "blocked": all_done = False
                else: total += mv
            if all_done:
                # 再确认一轮稳定
                return True, finish, sum(self.simulate(u, r, finish)[2] for u, r in routes.items())
            if not progress: return False, None, None
        return False, None, None
    def moves(self):
        return sum(self.simulate(u, r, self.finish)[2] or 0 for u, r in self.route.items())

def solve(pb, time_limit=2.0):
    t_start = time.time()
    plan = Plan(pb); T = pb["tasks"]
    chains = build_chains(pb)
    chains.sort(key=lambda g: min(max(earliest(pb, T[i]), T[i]["t"] - 0 if False else earliest(pb, T[i])) for i in g) * 0 + min(T[i]["t"] for i in g))
    unplaced = []
    for g in chains:
        cands = []
        for u in plan.route:
            r = plan.route[u]
            base_ok, _, base_mv = plan.simulate(u, r, plan.finish)
            if not base_ok: continue
            cand = list(r); pos_min = 0; ok = True
            for tid in g:
                bestp = None
                for p in range(pos_min, len(cand) + 1):
                    trial = cand[:p] + [tid] + cand[p:]
                    ok2, fin, mv = plan.simulate(u, trial, plan.finish)
                    if ok2 and (bestp is None or mv < bestp[0]): bestp = (mv, p)
                if bestp is None: ok = False; break
                cand = cand[:bestp[1]] + [tid] + cand[bestp[1]:]; pos_min = bestp[1] + 1
            if not ok: continue
            ok3, fin, mv = plan.simulate(u, cand, plan.finish)
            if ok3: cands.append((mv - base_mv, u, cand))
        placed = False
        for _, u, cand in sorted(cands, key=lambda x: x[0]):
            routes = dict(plan.route); routes[u] = cand
            okg, finish, _ = plan.global_eval(routes)
            if okg:
                plan.route = routes; plan.finish = finish; placed = True; break
        if not placed: unplaced.append(g)
    return plan, unplaced, time.time() - t_start

def to_schedule(plan):
    pb = plan.pb; sched = {}
    for u, r in plan.route.items():
        ok, fin, _ = plan.simulate(u, r, plan.finish)
        seq = []; pos = pb["units"][u]["pos"]; t = pb["units"][u]["appear"]
        for tid in r:
            tk = pb["tasks"][tid]; s = fin[tid][0]
            while pos != tk["cell"]:
                if pos[0] != tk["cell"][0]: mvn = "EAST" if tk["cell"][0] > pos[0] else "WEST"
                else: mvn = "SOUTH" if tk["cell"][1] > pos[1] else "NORTH"
                seq.append((t, [mvn])); dx, dy = MOVES[mvn]; pos = (pos[0] + dx, pos[1] + dy); t += 1
            while t < s: seq.append((t, ["PASS"])); t += 1
            cmd = [tk["op"]] + list(tk["arg"]); seq.append((t, cmd)); t += 1
        sched[u] = seq
    return sched

if __name__ == "__main__":
    import glob, sys, statistics as st
    files = sorted(glob.glob("data/tape_*.json.gz"))[: int(sys.argv[1]) if len(sys.argv) > 1 else 12]
    days = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else list(range(30))
    R = []
    for fn in files:
        D = dm.load(fn); S = D["steps"]
        for day in days:
            pb = dm.day_problem(D, day)
            inv0 = {i: S[pb["t0"]]["inv"][i] for i in range(len(S[pb["t0"]]["inv"]))}
            plan, unplaced, sec = solve(pb)
            ok, viol, mv, nd = dm.check(pb, to_schedule(plan), inv0)
            R.append(dict(day=day, ok=ok, unplaced=sum(len(g) for g in unplaced), mv=mv, tape=pb["tape_moves"], ntask=len(pb["tasks"]), sec=sec, viol=[v[0] for v in viol][:3]))
    feas = [r for r in R if r["ok"]]
    print(f"天数 {len(R)} 可行 {len(feas)};未排入任务中位 {st.median(r['unplaced'] for r in R)};求解耗时中位 {st.median(r['sec'] for r in R):.2f}s 最大 {max(r['sec'] for r in R):.2f}s")
    if feas: print(f"可行天 移动/带子 中位 {st.median(r['mv']/max(1,r['tape']) for r in feas):.3f} 合计 {sum(r['mv'] for r in feas)}/{sum(r['tape'] for r in feas)}")
    print("违规类型:", collections.Counter(v for r in R for v in r["viol"]).most_common(5))
    for r in R[:8]: print(" ", r)
