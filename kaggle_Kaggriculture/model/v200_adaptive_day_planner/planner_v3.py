"""日规划器 v3:背包显式建模(取消链锁定)+ 消耗任务可自动补插取货 + 单任务插入修补。"""
import collections, random, time
import day_model as dm
from planner_v1 import Plan, earliest, dist, build_chains, to_schedule
ANIMALS = ("COW", "SHEEP", "GOOSE", "CHICKEN")
ACCESS_LIST = [(4, 4), (5, 4), (4, 5), (5, 5)]

def need_of(tk):
    if tk["op"] in dm.CONSUME: return dm.CONSUME[tk["op"]], 1
    if tk["op"] == "PLACE" and tk["arg"] and tk["arg"][0] in ANIMALS: return tk["arg"][0], 1
    if tk["op"] in ("DROP", "PLACE"):
        neg = {k: -v for k, v in tk["delta"].items() if v < 0}
        if neg: k = next(iter(neg)); return k, neg[k]
    return None, 0

class PlanR(Plan):
    def __init__(self, pb, inv0):
        super().__init__(pb); self.inv0 = inv0
    def simulate(self, u, route, finish_known, partial=False):
        pos = self.U[u]["pos"]; t = self.U[u]["appear"]; fin = {}; mv = 0
        carry = collections.Counter(self.inv0.get(u, {}) or {})
        for tid in route:
            tk = self.T[tid]; d = dist(pos, tk["cell"])
            s = max(t + d, earliest(self.pb, tk))
            if tk["pred"] is not None:
                pf = fin.get(tk["pred"]) or finish_known.get(tk["pred"])
                if pf is None: return ("blocked", fin, mv) if partial else (False, None, None)
                s = max(s, pf[0] if pf[1] < u else pf[0] + 1)
            if s > self.pb["t_end"]: return False, None, None
            item, q = need_of(tk)
            if item:
                if carry[item] < q: return False, None, None
                carry[item] -= q
            if tk["op"] == "PICKUP" or tk["op"] in ("HARVEST", "COLLECT_FERTILIZER"):
                for k, v in tk["delta"].items():
                    if v > 0: carry[k] += v
            mv += d; fin[tid] = (s, u); pos = tk["cell"]; t = s + 1
        return True, fin, mv

def init_from_tape(pb, inv0):
    plan = PlanR(pb, inv0)
    for tk in sorted(pb["tasks"], key=lambda x: x["t"]): plan.route[tk["unit"]].append(tk["id"])
    ok, fin, mv = plan.global_eval(plan.route)
    plan.finish = fin or {}
    return plan, ok, mv

def add_pickup(pb, item, qty, cell):
    tid = len(pb["tasks"])
    pb["tasks"].append(dict(id=tid, t=pb["t0"] + 1, unit=-1, cell=cell, op="PICKUP", arg=[item, qty], delta={item: qty}, pred=None, pred_op=None, synthetic=True))
    return tid

def try_insert(plan, tid, units=None, topk=8, allow_pickup=True):
    """单任务插入:所有单位×位置;若因缺货失败且允许,在其前补插一次取货。"""
    pb = plan.pb; tk = pb["tasks"][tid]; cands = []
    item, q = need_of(tk)
    for u in (units or list(plan.route)):
        r = plan.route[u]; ok0, _, mv0 = plan.simulate(u, r, plan.finish)
        if not ok0: continue
        for p in range(len(r) + 1):
            trial = r[:p] + [tid] + r[p:]
            ok2, _, mv = plan.simulate(u, trial, plan.finish)
            if ok2: cands.append((mv - mv0, u, trial, None))
    if not cands and allow_pickup and item and tk["op"] != "DROP":
        for u in (units or list(plan.route)):
            r = plan.route[u]; ok0, _, mv0 = plan.simulate(u, r, plan.finish)
            if not ok0: continue
            for p in range(len(r) + 1):
                for qp in range(max(0, p - 3), p + 1):
                    cell = min(ACCESS_LIST, key=lambda c: dist(c, tk["cell"]))
                    pid = add_pickup(pb, item, max(q, 6 if item in ("WHEAT", "FERTILIZER") else q), cell)
                    trial = r[:qp] + [pid] + r[qp:p] + [tid] + r[p:]
                    ok2, _, mv = plan.simulate(u, trial, plan.finish)
                    if ok2: cands.append((mv - mv0 + 0.5, u, trial, pid))
                    else: pb["tasks"].pop()
    for d_, u, trial, pid in sorted(cands, key=lambda x: x[0])[:topk]:
        nr = dict(plan.route); nr[u] = trial
        okg, fin, _ = plan.global_eval(nr)
        if okg:
            plan.route, plan.finish = nr, fin
            # 清理未被采用的合成取货(只保留路线中出现的)
            used = {x for r in plan.route.values() for x in r}
            while pb["tasks"] and pb["tasks"][-1].get("synthetic") and pb["tasks"][-1]["id"] not in used:
                pb["tasks"].pop()
            return True
    used = {x for r in plan.route.values() for x in r}
    while pb["tasks"] and pb["tasks"][-1].get("synthetic") and pb["tasks"][-1]["id"] not in used:
        pb["tasks"].pop()
    return False

def local_search(plan, time_limit=2.0, seed=0):
    """单任务重定位(移除后最优重插),接受减少总移动的改动。"""
    rnd = random.Random(seed); t0 = time.time()
    ok, fin, cur = plan.global_eval(plan.route)
    if not ok: return cur
    plan.finish = fin; improved = True
    while improved and time.time() - t0 < time_limit:
        improved = False
        tids = [x for r in plan.route.values() for x in r]; rnd.shuffle(tids)
        for tid in tids:
            if time.time() - t0 > time_limit: break
            if plan.T[tid].get("synthetic"): continue
            old = {u: list(r) for u, r in plan.route.items()}; oldf = plan.finish
            rem = {u: [x for x in r if x != tid] for u, r in plan.route.items()}
            okr, finr, _ = plan.global_eval(rem)
            if not okr: continue
            plan.route, plan.finish = rem, finr
            if try_insert(plan, tid, allow_pickup=False):
                new = plan.global_eval(plan.route)[2]
                if new < cur: cur = new; improved = True; continue
            plan.route, plan.finish = old, oldf
    return cur
