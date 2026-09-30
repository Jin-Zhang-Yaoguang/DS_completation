"""离线重排管线 v1:
Pass1 跑 51k 调度器录事件与动作流;
Pass2 重排 farm 类事件(WATER/HARVEST/PLANT/DIG)为最近邻链,展开成带
      (HARVEST/PLANT 不早于原时刻;其余 unit 动作照抄);
Pass3 kagsim 重放对比 bank。
用法: python replan_build.py <seed> [opp_spec]
"""
import sys, json, collections, importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "v4_demand_race" / "harness"))
sys.path.insert(0, str(HERE.parent / "v16_online_fidelity"))
import engine, fidelity

FARM_OPS = ("WATER", "HARVEST", "PLANT", "DIG")


def pass1(seed, opp_spec):
    spec = importlib.util.spec_from_file_location("sched", HERE / "scheduler.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    cfg = json.load(open(HERE / "best_cfg_51k.json"))["cfg"]
    k = engine.load_kagsim(); g = k.Game(seed=seed)
    s = m.Sched(m.Cfg(**cfg))
    opp = fidelity.make_agent(opp_spec)
    acts_log = []          # 每 turn 原动作(dict)
    farm_events = []       # (t, unit, x, y, op, arg)
    farm_workers = set()
    n_units_t = []
    for step in range(719):
        obs = g.observe(0); obs["player"] = 0
        farm = obs["farms"][0]
        pos = [tuple(farm.get("farmer") or (0, 0))] + [tuple(h) for h in (farm.get("hands") or [])]
        a = s.act(obs)
        acts_log.append(json.loads(json.dumps(a)))
        units = [a.get("farmer") or ["PASS"]] + list(a.get("hands") or [])
        n_units_t.append(len(units))
        n = len(units)
        for i, u in enumerate(units):
            if not u or i >= len(pos):
                continue
            op = str(u[0])
            try:
                role = s.role_of(i, n)
            except Exception:
                role = None
            if role == "farm":
                farm_workers.add(i)
            if op in FARM_OPS and role == "farm":
                farm_events.append((step, i, pos[i][0], pos[i][1], op, u[1] if len(u) > 1 else None))
        try:
            b = opp(g.observe(1))
        except Exception:
            b = {"farmer": ["PASS"], "hands": [], "market": []}
        g.step(a, b)
    return acts_log, farm_events, sorted(farm_workers), n_units_t, float(g.reward(0))


def pass2(acts_log, farm_events, farm_workers, n_units_t):
    """重排:逐天把 farm 事件聚格成包,分给当天在场的 farm 工人,链化展开。"""
    new_acts = [json.loads(json.dumps(a)) for a in acts_log]
    # 清空 farm 工人的农场动作位(保留其非 farm 动作?v1:整位清为 PASS,仅当该位当时是 farm 事件)
    ev_by_day = collections.defaultdict(list)
    for (t, i, x, y, op, arg) in farm_events:
        ev_by_day[t // 24].append((t, i, x, y, op, arg))
    # 先把所有 farm 事件位清空
    for (t, i, x, y, op, arg) in farm_events:
        units = [new_acts[t].get("farmer") or ["PASS"]] + list(new_acts[t].get("hands") or [])
        if i < len(units):
            units[i] = ["PASS"]
        new_acts[t]["farmer"] = units[0]
        new_acts[t]["hands"] = units[1:]
    # 同时清空这些工人的 MOVE(它们的移动大多服务于 farm 事件)
    for t in range(len(new_acts)):
        units = [new_acts[t].get("farmer") or ["PASS"]] + list(new_acts[t].get("hands") or [])
        for i in farm_workers:
            if i < len(units) and units[i] and str(units[i][0]) in ("NORTH", "SOUTH", "EAST", "WEST"):
                units[i] = ["PASS"]
        new_acts[t]["farmer"] = units[0]
        new_acts[t]["hands"] = units[1:]

    stats = {"placed": 0, "dropped": 0}
    for day in sorted(ev_by_day):
        evs = ev_by_day[day]
        day_t0, day_t1 = day * 24, day * 24 + 24
        # 当天在场的 farm 工人(以当天中午的 unit 数为准)
        mid = min(day_t0 + 12, len(n_units_t) - 1)
        avail = [i for i in farm_workers if i < n_units_t[mid]]
        if not avail:
            continue
        # 聚格成包:cell -> [(op, arg, orig_t), ...],约束时刻 = max over HARVEST/PLANT 的 orig_t(不早于)
        cells = collections.defaultdict(list)
        for (t, i, x, y, op, arg) in evs:
            cells[(x, y)].append((op, arg, t))
        cell_list = sorted(cells.keys())
        nw = len(avail)
        per = max(1, (len(cell_list) + nw - 1) // nw)
        for wi, w in enumerate(avail):
            part = cell_list[wi * per:(wi + 1) * per]
            if not part:
                continue
            # 最近邻链
            cur = (4, 4)
            chain = []
            rest = set(part)
            while rest:
                nxt = min(rest, key=lambda c: abs(c[0] - cur[0]) + abs(c[1] - cur[1]))
                chain.append(nxt)
                rest.discard(nxt)
                cur = nxt
            # 展开:游标 tt 从 day_t0(工人到岗 hour1 起)走
            tt = day_t0 + 1
            px, py = 4, 4
            deferred = []
            for cell in chain + ["__deferred__"]:
                todo = deferred if cell == "__deferred__" else [(cell, cells[cell])]
                if cell == "__deferred__":
                    todo = deferred
                for (cx, cy), ops in ([(cell, cells[cell])] if cell != "__deferred__" else deferred):
                    # 移动
                    while (px, py) != (cx, cy) and tt < day_t1:
                        mv = None
                        if px < cx: mv, px = "EAST", px + 1
                        elif px > cx: mv, px = "WEST", px - 1
                        elif py < cy: mv, py = "SOUTH", py + 1
                        else: mv, py = "NORTH", py - 1
                        _put(new_acts, tt, w, [mv]); tt += 1
                    if tt >= day_t1:
                        stats["dropped"] += sum(1 for _ in ops)
                        continue
                    for (op, arg, orig_t) in sorted(ops, key=lambda e: e[2]):
                        # 约束:HARVEST/PLANT 不早于原时刻
                        if op in ("HARVEST", "PLANT") and tt < orig_t:
                            if cell != "__deferred__":
                                deferred.append(((cx, cy), [(op, arg, orig_t)]))
                                continue
                            tt = max(tt, orig_t)
                            if tt >= day_t1:
                                stats["dropped"] += 1
                                continue
                        if tt >= day_t1:
                            stats["dropped"] += 1
                            continue
                        _put(new_acts, tt, w, [op] + ([arg] if arg else []))
                        stats["placed"] += 1
                        tt += 1
                if cell == "__deferred__":
                    break
    return new_acts, stats


def _put(acts, t, i, action):
    if t >= len(acts):
        return
    units = [acts[t].get("farmer") or ["PASS"]] + list(acts[t].get("hands") or [])
    while len(units) <= i:
        units.append(["PASS"])
    if units[i] and str(units[i][0]) != "PASS":
        # 位被占(工人当时有非 farm 动作),顺延由调用方处理;v1 直接覆盖统计
        pass
    units[i] = action
    acts[t]["farmer"] = units[0]
    acts[t]["hands"] = units[1:]


if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 22
    opp_spec = sys.argv[2] if len(sys.argv) > 2 else "tape:../v51_block_router/newpool/op_e3bb880a.json"
    acts_log, evs, fw, nut, bank0 = pass1(seed, opp_spec)
    print(f"pass1: bank={bank0:.0f} farm 事件 {len(evs)} 个, farm 工人 {fw}")
    new_acts, st = pass2(acts_log, evs, fw, nut)
    print(f"pass2: placed={st['placed']} dropped={st['dropped']}")
    out = HERE / f"replan_s{seed}.json"
    json.dump({"actions": new_acts}, out.open("w"))
    r = fidelity.play(f"tape:{out}", opp_spec, seed, [])
    print(f"pass3: 重排带 bank={r['bank'][0]:.0f} (原局 {bank0:.0f})")
