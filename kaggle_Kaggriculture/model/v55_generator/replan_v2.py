"""重排 v2:同工人同日内重排——每 (day, worker) 的 farm 事件格链化,
在该工人当日原动作槽(事件槽+服务性 MOVE 槽)内重新展开;起点=当日首槽实际位置。"""
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
    acts_log, pos_log, fresh_log = [], [], []
    for step in range(719):
        obs = g.observe(0); obs["player"] = 0
        farm = obs["farms"][0]
        pos = [tuple(farm.get("farmer") or (0, 0))] + [tuple(h) for h in (farm.get("hands") or [])]
        a = s.act(obs)
        acts_log.append(json.loads(json.dumps(a)))
        pos_log.append(pos)
        day = step // 24
        fresh = set()
        for y in range(10):
            for x in range(10):
                t2 = farm["tiles"][y][x]
                if isinstance(t2, dict) and t2.get("kind") == "PLANT" and int(t2.get("planted_day", -1)) == day:
                    fresh.add((x, y))
        fresh_log.append(fresh)
        try: b = opp(g.observe(1))
        except Exception: b = {"farmer": ["PASS"], "hands": [], "market": []}
        g.step(a, b)
    return acts_log, pos_log, fresh_log, float(g.reward(0))

def replan(acts_log, pos_log, fresh_log):
    new_acts = [json.loads(json.dumps(a)) for a in acts_log]
    n_placed = n_dropped = 0
    # 收集 (day, unit):纯农活日(无非 farm/MOVE/PASS 动作)才可重排;槽=当日全部 turn
    slots = collections.defaultdict(list)
    evs = collections.defaultdict(list)
    impure = set()
    for t in range(len(acts_log)):
        units = [acts_log[t].get("farmer") or ["PASS"]] + list(acts_log[t].get("hands") or [])
        for i, u in enumerate(units):
            if i == 0 or i >= len(pos_log[t]):
                continue
            op = str(u[0]) if u else "PASS"
            key = (t // 24, i)
            slots[key].append(t)
            if op in FARM_OPS:
                x2, y2 = pos_log[t][i]
                constrained = op in ("HARVEST", "PLANT") or (op == "WATER" and (x2, y2) in fresh_log[t])
                evs[key].append((t, op, u[1] if len(u) > 1 else None, x2, y2, constrained))
            elif op not in ("NORTH", "SOUTH", "EAST", "WEST", "PASS"):
                impure.add(key)
    for key in impure:
        evs.pop(key, None)
    for key in evs:
        day, i = key
        events = evs[key]
        slot_ts = sorted(slots[key])
        if len(events) < 3 or not slot_ts:
            continue
        # 格聚合
        cells = collections.defaultdict(list)
        for (t, op, arg, x, y, cons) in events:
            cells[(x, y)].append((op, arg, t if cons else 0))
        # 起点=首槽时刻位置
        t0 = slot_ts[0]
        px, py = pos_log[t0][i] if i < len(pos_log[t0]) else (4, 4)
        chain = []
        rest = set(cells)
        cur = (px, py)
        while rest:
            nxt = min(rest, key=lambda c: abs(c[0]-cur[0])+abs(c[1]-cur[1]))
            chain.append(nxt); rest.discard(nxt); cur = nxt
        # 展开进槽
        plan = []   # 动作序列
        cx, cy = px, py
        ok = True
        for cell in chain:
            tx, ty = cell
            while (cx, cy) != (tx, ty):
                if cx < tx: plan.append(["EAST"]); cx += 1
                elif cx > tx: plan.append(["WEST"]); cx -= 1
                elif cy < ty: plan.append(["SOUTH"]); cy += 1
                else: plan.append(["NORTH"]); cy -= 1
            for (op, arg, ot) in sorted(cells[cell], key=lambda e: e[2]):
                plan.append([op] + ([arg] if arg else []) + [("__min_t__", ot)])
        if len(plan) > len(slot_ts):
            n_dropped += len(events)
            continue  # 重排更长(异常),放弃该组
        # 填槽:约束动作等到 >= min_t 的槽
        si = 0
        feasible = []
        for act in plan:
            min_t = 0
            if act and isinstance(act[-1], tuple) and act[-1][0] == "__min_t__":
                min_t = act[-1][1]
                act = act[:-1]
            while si < len(slot_ts) and slot_ts[si] < min_t:
                feasible.append((slot_ts[si], ["PASS"]))
                si += 1
            if si >= len(slot_ts):
                feasible = None
                break
            feasible.append((slot_ts[si], act))
            si += 1
        if feasible is None:
            n_dropped += len(events)
            continue
        # 剩余槽置 PASS
        for rest_t in slot_ts[si:]:
            feasible.append((rest_t, ["PASS"]))
        for (t, act) in feasible:
            units = [new_acts[t].get("farmer") or ["PASS"]] + list(new_acts[t].get("hands") or [])
            if i < len(units):
                units[i] = act
            new_acts[t]["farmer"] = units[0]
            new_acts[t]["hands"] = units[1:]
        n_placed += len(events)
    return new_acts, n_placed, n_dropped

if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 22
    opp_spec = sys.argv[2] if len(sys.argv) > 2 else "tape:../v51_block_router/newpool/op_e3bb880a.json"
    acts_log, pos_log, fresh_log, bank0 = pass1(seed, opp_spec)
    new_acts, pl, dr = replan(acts_log, pos_log, fresh_log)
    print(f"pass1 bank={bank0:.0f}; replan placed={pl} dropped={dr}")
    out = HERE / f"replan2_s{seed}.json"
    json.dump({"actions": new_acts}, out.open("w"))
    r = fidelity.play(f"tape:{out}", opp_spec, seed, [])
    print(f"重排带 bank={r['bank'][0]:.0f} (原局 {bank0:.0f})")
