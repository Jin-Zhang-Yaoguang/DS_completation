"""日内任务模型:从带子轨迹切出"一天一道题",并提供可行性检查器(用带子原编排自检)。

题目 = 单位(出现步、出生位置) + 任务(格、动作、物品、最早步、同格前驱) + 当日买入(种子/动物/小麦/肥料到货步)。
约束模型:
  - 每单位每步一个动作;移动 1 格(曼哈顿,无障碍);工作在脚下格执行。
  - 背包:取货在仓库口(4,4)(5,4)(4,5)(5,5);喂食需小麦、施肥需肥料、放置动物需该动物;收获/收肥增加物品。
  - 同格多个任务按带子原顺序(前驱必须在更早的步完成)。
  - 种植需种子已买入(当日该作物 BUY_SEED 下单步之后);放置动物需 BUY_ANIMAL 之后。
  - 日终(hour 23)前完成。
"""
import json, gzip, collections
MOVES = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}
ACCESS = {(4, 4), (5, 4), (4, 5), (5, 5)}
CONSUME = {"FEED": "WHEAT", "FERTILIZE": "FERTILIZER"}
STRICT_PRED = {"PLANT", "DIG", "BUILD_PASTURE", "BUILD_COOP", "PLACE"}   # 这些动作之后的同格动作必须在更晚的步

def load(fn):
    return json.load(gzip.open(fn, "rt"))

def task_key(cell, op, arg):
    if op == "PICKUP" and arg: return (tuple(cell), op, str(arg[0]), str(arg[1]) if len(arg) > 1 else "")
    if op in ("PLACE", "PLANT", "DROP") and arg: return (tuple(cell), op, str(arg[0]))
    return (tuple(cell), op)

def day_problem(D, day):
    S = D["steps"]; t0 = day * 24; t1 = min(t0 + 24, len(S))
    units = {}; tasks = []; buys = collections.defaultdict(list); tape_moves = 0; tape_pass = 0
    for t in range(t0, t1):
        st = S[t]
        for x in st["market"]:
            if x and x[0] in ("BUY_SEED", "BUY_ANIMAL", "BUY_PRODUCT") and len(x) > 1: buys[(x[0], x[1])].append(t)
        for i, u in enumerate(st["units"]):
            if i not in units: units[i] = dict(appear=t, pos=tuple(u))
            c = st["cmds"][i] if i < len(st["cmds"]) else ["PASS"]
            op = c[0] if c else "PASS"
            if op in MOVES: tape_moves += 1
            elif op == "PASS": tape_pass += 1
            else:
                nxt = S[t + 1] if t + 1 < len(S) else st
                i0 = st["inv"][i] if i < len(st["inv"]) else {}; i1 = nxt["inv"][i] if i < len(nxt["inv"]) else {}
                delta = {k: i1.get(k, 0) - i0.get(k, 0) for k in set(i0) | set(i1) if i1.get(k, 0) != i0.get(k, 0)} if t % 24 != 23 else {}
                tasks.append(dict(id=len(tasks), t=t, unit=i, cell=tuple(u), op=op, arg=c[1:] if len(c) > 1 else [], delta=delta))
    # 同格前驱
    last_on_cell = {}
    for tk in tasks:
        if tk["cell"] in ACCESS: tk["pred"] = None; continue
        tk["pred"] = last_on_cell.get(tk["cell"]); tk["pred_op"] = tasks[tk["pred"]]["op"] if tk["pred"] is not None else None
        last_on_cell[tk["cell"]] = tk["id"]
    seeds0 = dict(S[t0].get("seeds") or {}) if t0 < len(S) else {}
    return dict(day=day, t0=t0, t_end=t0 + 23, units=units, tasks=tasks, seeds0=seeds0, buys={f"{k[0]}|{k[1]}": v for k, v in buys.items()},
                tape_moves=tape_moves, tape_pass=tape_pass)

def check(problem, schedule, inv0=None):
    """schedule: {unit: [(step, cmd), ...]}。按全局时间顺序模拟。返回 (可行?, 违规列表, 移动数, 完成任务数)。"""
    U = problem["units"]; viol = []; moves = 0
    todo = collections.defaultdict(list)
    for tk in problem["tasks"]:
        if tk.get("skipped"): continue
        todo[task_key(tk["cell"], tk["op"], tk["arg"])].append(tk)
    done_step = {}
    pos = {u: U[u]["pos"] for u in U}
    carry = {u: collections.Counter((inv0 or {}).get(u, {})) for u in U}
    timeline = sorted(((t, u, c) for u, seq in schedule.items() for (t, c) in seq), key=lambda x: (x[0], x[1]))
    seen = set()
    for (t, u, c) in timeline:
        if u not in U: continue
        if t < U[u]["appear"]: viol.append(("单位未出现", u, t)); continue
        if (u, t) in seen: viol.append(("同步两动作", u, t)); continue
        seen.add((u, t))
        op = c[0] if c else "PASS"
        if op in MOVES:
            dx, dy = MOVES[op]; pos[u] = (pos[u][0] + dx, pos[u][1] + dy); moves += 1; continue
        if op == "PASS": continue
        p = pos[u]; cu = carry[u]
        if t > problem["t_end"]: viol.append(("超日终", u, t))
        q = todo.get(task_key(p, op, c[1:])); tk = q.pop(0) if q else None
        if op == "PICKUP":
            if p not in ACCESS: viol.append(("非仓库口取货", u, t, p))
            if tk and tk.get("delta"): cu.update({k: v for k, v in tk["delta"].items() if v > 0})
            else: cu[c[1] if len(c) > 1 else "WHEAT"] += int(c[2]) if len(c) > 2 else 1
        elif op in CONSUME:
            need = CONSUME[op]
            if cu[need] <= 0: viol.append(("缺" + need, u, t, p))
            else: cu[need] -= 1
        elif op == "PLACE" and len(c) > 1 and c[1] in ("COW", "SHEEP", "GOOSE", "CHICKEN"):
            if cu[c[1]] <= 0: viol.append(("缺动物" + c[1], u, t))
            else: cu[c[1]] -= 1
        elif tk and tk.get("delta"):
            for k, v in tk["delta"].items():
                if v > 0: cu[k] += v
                elif op in ("DROP", "PLACE"): cu[k] = max(0, cu[k] + v)
        if tk:
            strict = tk.get("pred_op") in STRICT_PRED or op in ("PLANT", "PLACE")
            ps = done_step.get(tk["pred"]) if tk["pred"] is not None else None
            same_ok = ps is not None and ps[0] == t and (not strict or ps[1] < u)
            if tk["pred"] is not None and not (ps is not None and (ps[0] < t or same_ok)):
                viol.append(("同格前驱未完成", tk["id"], op, p, t))
            done_step[tk["id"]] = (t, u)
    missing = sum(len(v) for v in todo.values())
    if missing: viol.append(("未完成任务", missing))
    return (not viol), viol, moves, len(done_step)

def tape_schedule(D, problem):
    S = D["steps"]; sched = collections.defaultdict(list)
    for t in range(problem["t0"], min(problem["t0"] + 24, len(S))):
        st = S[t]
        for i in range(len(st["units"])):
            c = st["cmds"][i] if i < len(st["cmds"]) else ["PASS"]
            sched[i].append((t, c if c else ["PASS"]))
    return sched

if __name__ == "__main__":
    import glob, sys
    from pathlib import Path
    HERE = Path(__file__).resolve().parent
    tot = collections.Counter(); bad = collections.Counter(); ex = []
    for fn in sorted(glob.glob(str(HERE / "data" / "tape_*.json.gz"))):
        D = load(fn); S = D["steps"]
        for day in range(30):
            pb = day_problem(D, day)
            inv0 = {i: S[pb["t0"]]["inv"][i] for i in range(len(S[pb["t0"]]["inv"]))} if pb["t0"] < len(S) else {}
            ok, viol, mv, nd = check(pb, tape_schedule(D, pb), inv0)
            tot["天"] += 1; tot["可行"] += ok; tot["任务"] += len(pb["tasks"]); tot["完成"] += nd
            for v in viol: bad[v[0]] += 1
            if not ok and len(ex) < 6: ex.append((Path(fn).name[:40], day, viol[:3]))
    print("带子原编排自检:", dict(tot)); print("违规类型:", bad.most_common()); [print("  例", e) for e in ex]
