"""OR-Tools 日规划器 v2:喂食/施肥与专属取货节点做取送配对(同车、先取后送);连续取货合并为一次。"""
import collections
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import day_model as dm
from planner_v1 import earliest
from planner_v3 import PlanR, need_of
ACCESS_LIST = [(4, 4), (5, 4), (4, 5), (5, 5)]
ANIMALS = ("COW", "SHEEP", "GOOSE", "CHICKEN")
PAIRED = {"FEED": "WHEAT", "FERTILIZE": "FERTILIZER"}
BIG = 100000

def is_optional(tk):
    return (tk["op"] == "PICKUP" and tk["arg"] and tk["arg"][0] in ("WHEAT", "FERTILIZER")) or tk["op"] == "DROP" or \
           (tk["op"] == "PLACE" and not (tk["arg"] and tk["arg"][0] in ANIMALS))

def solve(pb, inv0, init_routes=None, time_limit=2.0, use_pd=True, use_extra=True, use_prec=True, use_items=True, read_only=False):
    T = [tk for tk in pb["tasks"] if not tk.get("synthetic")]
    units = sorted(pb["units"]); V = len(units)
    nodes = [dict(kind="start", cell=pb["units"][u]["pos"]) for u in units] + [dict(kind="end", cell=None) for u in units]
    tnode = {}; pair_of = {}
    for tk in T:
        tnode[tk["id"]] = len(nodes); nodes.append(dict(kind="task", cell=tk["cell"], tk=tk, optional=is_optional(tk)))
    for tk in T:
        if tk["op"] in PAIRED:
            cell = min(ACCESS_LIST, key=lambda c: abs(c[0] - tk["cell"][0]) + abs(c[1] - tk["cell"][1]))
            pair_of[tk["id"]] = len(nodes); nodes.append(dict(kind="pick", cell=cell, item=PAIRED[tk["op"]], for_task=tk["id"]))
    items = set()
    for tk in T:
        if tk["op"] in PAIRED or (tk["op"] == "PICKUP" and tk["arg"] and tk["arg"][0] in ("WHEAT", "FERTILIZER")): continue
        for k, v in tk["delta"].items():
            if k not in ("WHEAT", "FERTILIZER"): items.add(k)
        it, _ = need_of(tk)
        if it and it not in ("WHEAT", "FERTILIZER"): items.add(it)
    man = pywrapcp.RoutingIndexManager(len(nodes), V, list(range(V)), list(range(V, 2 * V)))
    R = pywrapcp.RoutingModel(man); s = R.solver()
    def dd(i, j):
        a, b = nodes[i], nodes[j]
        if a["cell"] is None or b["cell"] is None: return 0
        return abs(a["cell"][0] - b["cell"][0]) + abs(a["cell"][1] - b["cell"][1])
    R.SetArcCostEvaluatorOfAllVehicles(R.RegisterTransitCallback(lambda fi, ti: dd(man.IndexToNode(fi), man.IndexToNode(ti))))
    def tt(fi, ti):
        i, j = man.IndexToNode(fi), man.IndexToNode(ti); a, b = nodes[i], nodes[j]
        svc = 1 if a["kind"] == "task" else 0
        if a["kind"] == "pick" and not (b["kind"] == "pick" and b["cell"] == a["cell"]): svc = 1   # 一批取货结束算 1 步
        return dd(i, j) + svc
    R.AddDimension(R.RegisterTransitCallback(tt), 24, pb["t_end"] + 2, False, "Time"); TD = R.GetDimensionOrDie("Time")
    for v, u in enumerate(units): TD.CumulVar(R.Start(v)).SetRange(pb["units"][u]["appear"], pb["units"][u]["appear"])
    for n, nd in enumerate(nodes):
        if nd["kind"] in ("start", "end"): continue
        idx = man.NodeToIndex(n)
        TD.CumulVar(idx).SetRange(earliest(pb, nd["tk"]) if nd["kind"] == "task" else pb["t0"], pb["t_end"])
        if nd["kind"] == "pick": continue          # 配对节点跟随其任务
        R.AddDisjunction([idx], 0 if nd["optional"] else BIG)
    for tid, pn in pair_of.items():
        pi, di = man.NodeToIndex(pn), man.NodeToIndex(tnode[tid])
        if use_pd: R.AddPickupAndDelivery(pi, di)
        if use_extra:
            s.Add(R.VehicleVar(pi) == R.VehicleVar(di))
            s.Add(TD.CumulVar(pi) <= TD.CumulVar(di))
            s.Add(R.ActiveVar(pi) == R.ActiveVar(di))
    for tk in T:
        if tk["pred"] is None or not use_prec: continue
        a, b = man.NodeToIndex(tnode[tk["pred"]]), man.NodeToIndex(tnode[tk["id"]])
        before = s.IsLessVar(R.VehicleVar(a), R.VehicleVar(b))
        s.Add(TD.CumulVar(b) >= TD.CumulVar(a) + 1 - before)
    def dem(n, it):
        nd = nodes[n]
        if nd["kind"] != "task": return 0
        tk = nd["tk"]; d = 0
        if tk["op"] in ("PICKUP", "HARVEST", "COLLECT_FERTILIZER"): d += max(0, tk["delta"].get(it, 0))
        x, q = need_of(tk)
        if x == it: d -= q
        return d
    for it in (sorted(items) if use_items else []):
        cb = R.RegisterUnaryTransitCallback(lambda fi, it=it: dem(man.IndexToNode(fi), it))
        R.AddDimensionWithVehicleCapacity(cb, 0, [60] * V, False, "I_" + it); D = R.GetDimensionOrDie("I_" + it)
        for v, u in enumerate(units):
            q0 = int((inv0.get(u) or {}).get(it, 0)); D.CumulVar(R.Start(v)).SetRange(q0, q0)
    prm = pywrapcp.DefaultRoutingSearchParameters()
    prm.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
    prm.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    prm.time_limit.FromMilliseconds(int(time_limit * 1000))
    R.CloseModelWithParameters(prm)
    sol = None; init_ok = None
    if init_routes is not None:
        # 消耗任务的取货节点放到带子中"为它供货的那次取货"位置;无来源(早上背包/自产)时放在该消耗任务前
        from planner_v1 import build_chains
        src_of = {}
        for u in units:
            last_src = {}
            for tid in init_routes.get(u, []):
                tk = pb["tasks"][tid]
                if tk["op"] == "PICKUP" and tk["arg"] and tk["arg"][0] in ("WHEAT", "FERTILIZER"): last_src[tk["arg"][0]] = tid
                if tk["op"] in PAIRED and PAIRED[tk["op"]] in last_src: src_of[tid] = last_src[PAIRED[tk["op"]]]
        attach = collections.defaultdict(list)
        for tid, src in src_of.items():
            if tid in pair_of: attach[src].append(pair_of[tid])
        rts = []
        for u in units:
            seq = []
            for tid in init_routes.get(u, []):
                if tid not in tnode: continue
                tk = pb["tasks"][tid]
                if tid in attach:
                    seq.extend(man.NodeToIndex(p) for p in attach[tid])
                    if is_optional(tk): continue          # 原取货由配对节点替代
                if tk["op"] in PAIRED and tid in pair_of and tid not in src_of:
                    seq.append(man.NodeToIndex(pair_of[tid]))
                seq.append(man.NodeToIndex(tnode[tid]))
            rts.append(seq)
        init = R.ReadAssignmentFromRoutes(rts, True); init_ok = init is not None
        if read_only: return dict(init_ok=init_ok)
        if init is not None: sol = R.SolveFromAssignmentWithParameters(init, prm)
    if sol is None: sol = R.SolveWithParameters(prm)
    if sol is None: return None
    routes = {}
    for v, u in enumerate(units):
        idx = R.Start(v); seq = []; batch = None
        while True:
            idx = sol.Value(R.NextVar(idx))
            if R.IsEnd(idx): break
            nd = nodes[man.IndexToNode(idx)]
            if nd["kind"] == "pick":
                if batch and batch["cell"] == nd["cell"] and batch["arg"][0] == nd["item"]:
                    batch["arg"][1] += 1; batch["delta"][nd["item"]] += 1
                else:
                    tid = len(pb["tasks"])
                    batch = dict(id=tid, t=pb["t0"], unit=-1, cell=nd["cell"], op="PICKUP", arg=[nd["item"], 1], delta={nd["item"]: 1}, pred=None, pred_op=None, synthetic=True)
                    pb["tasks"].append(batch); seq.append(tid)
                continue
            batch = None
            seq.append(nd["tk"]["id"])
        routes[u] = seq
    served = {x for r in routes.values() for x in r}
    missing = [tk["id"] for tk in T if tk["id"] not in served and not is_optional(tk)]
    for tk in T:
        if tk["id"] not in served and is_optional(tk): tk["skipped"] = True
    return dict(routes=routes, missing=missing, init_ok=init_ok)
