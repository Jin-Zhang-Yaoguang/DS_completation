"""日规划器(OR-Tools VRPTW):车辆=单位,节点=任务(+可选取货点),时间窗+同格前驱+多物品载货维度,最小化走路。"""
import collections, random, time
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import day_model as dm
from planner_v1 import earliest, dist
from planner_v3 import PlanR, need_of
ACCESS_LIST = [(4, 4), (5, 4), (4, 5), (5, 5)]
ANIMALS = ("COW", "SHEEP", "GOOSE", "CHICKEN")
PICK_QTY = {"WHEAT": 6, "FERTILIZER": 5}
BIG = 100000

def build(pb, inv0, n_extra_pick=3):
    T = [tk for tk in pb["tasks"] if not tk.get("synthetic")]
    units = sorted(pb["units"])
    # 节点:0..V-1 起点,V..2V-1 终点,之后任务,之后可选取货
    V = len(units); nodes = []
    for u in units: nodes.append(dict(kind="start", cell=pb["units"][u]["pos"], u=u))
    for u in units: nodes.append(dict(kind="end", cell=None, u=u))
    task_node = {}
    for tk in T:
        task_node[tk["id"]] = len(nodes)
        optional = (tk["op"] == "PICKUP" and tk["arg"] and tk["arg"][0] in PICK_QTY) or \
                   tk["op"] == "DROP" or (tk["op"] == "PLACE" and not (tk["arg"] and tk["arg"][0] in ANIMALS))
        nodes.append(dict(kind="task", cell=tk["cell"], tk=tk, optional=optional))
    items = set(PICK_QTY)
    for tk in T:
        items.update(tk["delta"].keys())
        it, _ = need_of(tk)
        if it: items.add(it)
    for it in PICK_QTY:
        for k in range(n_extra_pick * V):
            nodes.append(dict(kind="pick", cell=ACCESS_LIST[k % 4], item=it, qty=PICK_QTY[it], optional=True))
    return dict(nodes=nodes, V=V, units=units, task_node=task_node, items=sorted(items))

def demand(node, item):
    if node["kind"] == "pick": return node["qty"] if node["item"] == item else 0
    if node["kind"] != "task": return 0
    tk = node["tk"]; d = 0
    if tk["op"] in ("PICKUP", "HARVEST", "COLLECT_FERTILIZER"): d += max(0, tk["delta"].get(item, 0))
    it, q = need_of(tk)
    if it == item: d -= q
    return d

OPS = ["use_relocate_and_make_active", "use_exchange_and_make_active", "use_extended_swap_active", "use_inactive_lns",
       "use_path_lns", "use_full_path_lns", "use_global_cheapest_insertion_close_nodes_lns", "use_local_cheapest_insertion_close_nodes_lns",
       "use_relocate_path_global_cheapest_insertion_insert_unperformed", "use_global_cheapest_insertion_expensive_chain_lns"]

def solve(pb, inv0, init_routes=None, time_limit=1.0, n_extra_pick=3, spare=False, extra_ops=False):
    M = build(pb, inv0, n_extra_pick); nodes = M["nodes"]; V = M["V"]; units = M["units"]
    starts = list(range(V)); ends = list(range(V, 2 * V))
    man = pywrapcp.RoutingIndexManager(len(nodes), V, starts, ends)
    R = pywrapcp.RoutingModel(man)
    def ddist(i, j):
        a, b = nodes[i], nodes[j]
        if a["cell"] is None or b["cell"] is None: return 0
        return abs(a["cell"][0] - b["cell"][0]) + abs(a["cell"][1] - b["cell"][1])
    dcb = R.RegisterTransitCallback(lambda fi, ti: ddist(man.IndexToNode(fi), man.IndexToNode(ti)))
    R.SetArcCostEvaluatorOfAllVehicles(dcb)
    def ttime(fi, ti):
        i, j = man.IndexToNode(fi), man.IndexToNode(ti)
        return ddist(i, j) + (1 if nodes[i]["kind"] in ("task", "pick") else 0)
    tcb = R.RegisterTransitCallback(ttime)
    horizon = pb["t_end"] + 2
    R.AddDimension(tcb, 24, horizon, False, "Time")
    TD = R.GetDimensionOrDie("Time")
    for v, u in enumerate(units):
        TD.CumulVar(R.Start(v)).SetRange(pb["units"][u]["appear"], pb["units"][u]["appear"])
    for n, nd in enumerate(nodes):
        if nd["kind"] in ("start", "end"): continue
        idx = man.NodeToIndex(n)
        e = earliest(pb, nd["tk"]) if nd["kind"] == "task" else pb["t0"]
        TD.CumulVar(idx).SetRange(e, pb["t_end"])
        if nd["kind"] == "pick" or nd.get("optional"): R.AddDisjunction([idx], 0)
        else: R.AddDisjunction([idx], BIG)
    s = R.solver()
    for tk in pb["tasks"]:
        if tk.get("synthetic") or tk["pred"] is None: continue
        a = man.NodeToIndex(M["task_node"][tk["pred"]]); b = man.NodeToIndex(M["task_node"][tk["id"]])
        before = s.IsLessVar(R.VehicleVar(a), R.VehicleVar(b))
        s.Add(TD.CumulVar(b) >= TD.CumulVar(a) + 1 - before)
    for it in M["items"]:
        cb = R.RegisterUnaryTransitCallback(lambda fi, it=it: demand(nodes[man.IndexToNode(fi)], it))
        R.AddDimensionWithVehicleCapacity(cb, 0, [60] * V, False, "I_" + it)
        D = R.GetDimensionOrDie("I_" + it)
        for v, u in enumerate(units):
            q0 = int((inv0.get(u) or {}).get(it, 0)); D.CumulVar(R.Start(v)).SetRange(q0, q0)
    prm = pywrapcp.DefaultRoutingSearchParameters()
    prm.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
    prm.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    prm.time_limit.FromMilliseconds(int(time_limit * 1000))
    if extra_ops:
        for name in OPS: setattr(prm.local_search_operators, name, 3)   # BOOL_TRUE
    sol = None; init_ok = None
    if init_routes is not None:
        rts = [[man.NodeToIndex(M["task_node"][tid]) for tid in init_routes.get(u, []) if tid in M["task_node"]] for u in units]
        R.CloseModelWithParameters(prm)
        init = None
        if spare:
            pick_nodes = collections.defaultdict(list)
            for n, nd in enumerate(nodes):
                if nd["kind"] == "pick": pick_nodes[nd["item"]].append(n)
            rts_sp = []
            for v, u in enumerate(units):
                extra = []
                if pb["units"][u]["pos"] in ACCESS_LIST:
                    for it in ("WHEAT", "FERTILIZER"):
                        if pick_nodes[it]: extra.append(man.NodeToIndex(pick_nodes[it].pop()))
                rts_sp.append(extra + rts[v])
            init = R.ReadAssignmentFromRoutes(rts_sp, True)
        if init is None:
            init = R.ReadAssignmentFromRoutes(rts, True)
        if init is None:
            # 清理:按单位推演载货,移出会导致载货为负的消耗任务(以及其同格后续),再试一次
            succ = collections.defaultdict(list)
            for tk in pb["tasks"]:
                if tk["pred"] is not None: succ[tk["pred"]].append(tk["id"])
            removed = set()
            for u in units:
                carry = collections.Counter({k: int(v) for k, v in (inv0.get(u) or {}).items()})
                for tid in init_routes.get(u, []):
                    tk = pb["tasks"][tid]; bad = False
                    for it in M["items"]:
                        if carry[it] + demand(dict(kind="task", tk=tk, cell=tk["cell"]), it) < 0: bad = True
                    if bad: removed.add(tid); continue
                    for it in M["items"]: carry[it] += demand(dict(kind="task", tk=tk, cell=tk["cell"]), it)
            stack = list(removed)
            while stack:
                x = stack.pop()
                for y in succ[x]:
                    if y not in removed: removed.add(y); stack.append(y)
            rts = [[man.NodeToIndex(M["task_node"][tid]) for tid in init_routes.get(u, []) if tid in M["task_node"] and tid not in removed] for u in units]
            init = R.ReadAssignmentFromRoutes(rts, True)
        init_ok = init is not None
        if init is not None: sol = R.SolveFromAssignmentWithParameters(init, prm)
    if sol is None: sol = R.SolveWithParameters(prm)
    if sol is None: return None
    # 提取路线;可选取货转成合成任务
    routes = {}; dropped = 0
    for v, u in enumerate(units):
        idx = R.Start(v); seq = []
        while not R.IsEnd(idx):
            idx = sol.Value(R.NextVar(idx)); n = man.IndexToNode(idx)
            nd = nodes[n]
            if nd["kind"] == "task": seq.append(nd["tk"]["id"])
            elif nd["kind"] == "pick":
                tid = len(pb["tasks"])
                pb["tasks"].append(dict(id=tid, t=pb["t0"] + 1, unit=-1, cell=nd["cell"], op="PICKUP", arg=[nd["item"], nd["qty"]], delta={nd["item"]: nd["qty"]}, pred=None, pred_op=None, synthetic=True))
                seq.append(tid)
        routes[u] = seq
    served = {x for r in routes.values() for x in r}
    def is_optional(tk):
        return (tk["op"] == "PICKUP" and tk["arg"] and tk["arg"][0] in PICK_QTY) or tk["op"] == "DROP" or (tk["op"] == "PLACE" and not (tk["arg"] and tk["arg"][0] in ANIMALS))
    missing = [tk["id"] for tk in pb["tasks"] if not tk.get("synthetic") and tk["id"] not in served and not is_optional(tk)]
    skipped_optional = [tk["id"] for tk in pb["tasks"] if not tk.get("synthetic") and tk["id"] not in served and is_optional(tk)]
    for tid in skipped_optional: pb["tasks"][tid]["skipped"] = True
    return dict(routes=routes, missing=missing, cost=sol.ObjectiveValue(), init_ok=init_ok)

def to_plan(pb, inv0, routes):
    plan = PlanR(pb, inv0); plan.route = {u: list(routes.get(u, [])) for u in pb["units"]}
    ok, fin, mv = plan.global_eval(plan.route)
    plan.finish = fin or {}
    return plan, ok, mv
