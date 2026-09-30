"""定位带子初始解在 OR 模型中读入失败的约束:逐项开关。"""
import glob, collections, json
from ortools.constraint_solver import pywrapcp
import day_model as dm, planner_ortools as po
from planner_v1 import earliest

def try_read(pb, inv0, use_tw=True, use_prec=True, items=None):
    M = po.build(pb, inv0); nodes = M["nodes"]; V = M["V"]; units = M["units"]
    man = pywrapcp.RoutingIndexManager(len(nodes), V, list(range(V)), list(range(V, 2 * V)))
    R = pywrapcp.RoutingModel(man)
    def dd(i, j):
        a, b = nodes[i], nodes[j]
        if a["cell"] is None or b["cell"] is None: return 0
        return abs(a["cell"][0] - b["cell"][0]) + abs(a["cell"][1] - b["cell"][1])
    R.SetArcCostEvaluatorOfAllVehicles(R.RegisterTransitCallback(lambda fi, ti: dd(man.IndexToNode(fi), man.IndexToNode(ti))))
    tcb = R.RegisterTransitCallback(lambda fi, ti: dd(man.IndexToNode(fi), man.IndexToNode(ti)) + (1 if nodes[man.IndexToNode(fi)]["kind"] in ("task", "pick") else 0))
    R.AddDimension(tcb, 24, pb["t_end"] + 2, False, "Time"); TD = R.GetDimensionOrDie("Time")
    for v, u in enumerate(units): TD.CumulVar(R.Start(v)).SetRange(pb["units"][u]["appear"], pb["units"][u]["appear"])
    for n, nd in enumerate(nodes):
        if nd["kind"] in ("start", "end"): continue
        idx = man.NodeToIndex(n)
        if use_tw:
            e = earliest(pb, nd["tk"]) if nd["kind"] == "task" else pb["t0"]
            TD.CumulVar(idx).SetRange(e, pb["t_end"])
        R.AddDisjunction([idx], 0 if nd["kind"] == "pick" or nd.get("optional") else po.BIG)
    if use_prec:
        for tk in pb["tasks"]:
            if tk.get("synthetic") or tk["pred"] is None: continue
            a = man.NodeToIndex(M["task_node"][tk["pred"]]); b = man.NodeToIndex(M["task_node"][tk["id"]])
            before = R.solver().IsLessVar(R.VehicleVar(a), R.VehicleVar(b))
            R.solver().Add(TD.CumulVar(b) >= TD.CumulVar(a) + 1 - before)
    for it in (M["items"] if items is None else items):
        cb = R.RegisterUnaryTransitCallback(lambda fi, it=it: po.demand(nodes[man.IndexToNode(fi)], it))
        R.AddDimensionWithVehicleCapacity(cb, 0, [60] * V, False, "I_" + it); D = R.GetDimensionOrDie("I_" + it)
        for v, u in enumerate(units):
            q0 = int((inv0.get(u) or {}).get(it, 0)); D.CumulVar(R.Start(v)).SetRange(q0, q0)
    prm = pywrapcp.DefaultRoutingSearchParameters(); R.CloseModelWithParameters(prm)
    init = collections.defaultdict(list)
    for tk in sorted(pb["tasks"], key=lambda x: x["t"]): init[tk["unit"]].append(tk["id"])
    rts = [[man.NodeToIndex(M["task_node"][t]) for t in init.get(u, [])] for u in units]
    return R.ReadAssignmentFromRoutes(rts, True) is not None, M["items"]

if __name__ == "__main__":
    cnt = collections.Counter(); ex = []
    for fn in sorted(glob.glob("data/tape_*.json.gz"))[:4]:
        D = dm.load(fn); S = D["steps"]
        for day in range(30):
            pb = dm.day_problem(D, day); inv0 = {i: S[pb["t0"]]["inv"][i] for i in range(len(S[pb["t0"]]["inv"]))}
            ok_all, items = try_read(pb, inv0)
            if ok_all: cnt["全部约束可读"] += 1; continue
            ok_t, _ = try_read(pb, inv0, use_tw=True, use_prec=False, items=[])
            ok_tp, _ = try_read(pb, inv0, use_tw=True, use_prec=True, items=[])
            ok_nt, _ = try_read(pb, inv0, use_tw=False, use_prec=False, items=[])
            culprit = []
            if not ok_nt: culprit.append("仅路径即失败")
            elif not ok_t: culprit.append("时间窗")
            elif not ok_tp: culprit.append("同格前驱")
            else:
                for it in items:
                    if not try_read(pb, inv0, items=[it])[0]: culprit.append("载货:" + it)
            cnt["|".join(culprit) or "组合冲突"] += 1
            if len(ex) < 6: ex.append((fn[-26:], day, culprit))
    print(cnt.most_common()); [print(" ", e) for e in ex]
