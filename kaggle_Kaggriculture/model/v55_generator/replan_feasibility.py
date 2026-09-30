"""离线重排可行性:记录一局生效农场事件,按天做工人重分配+最近邻链,
对比实际移动步数 vs 重排后理论移动步数。"""
import sys, json, collections, importlib.util
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "v4_demand_race" / "harness"))
sys.path.insert(0, str(HERE.parent / "v16_online_fidelity"))
import engine, fidelity

spec = importlib.util.spec_from_file_location("sched", HERE / "scheduler.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
cfg = json.load(open(HERE / "best_cfg_51k.json"))["cfg"]
k = engine.load_kagsim(); g = k.Game(seed=22)
s = m.Sched(m.Cfg(**cfg))
opp = fidelity.make_agent("tape:../v51_block_router/newpool/op_e3bb880a.json")
events = collections.defaultdict(list)   # day -> [(x,y,op)]
moves_actual = collections.Counter()     # day -> 实际移动步数
workers_day = collections.Counter()      # day -> 人日(工人数)
for step in range(719):
    obs = g.observe(0); obs["player"] = 0
    farm = obs["farms"][0]
    pos = [tuple(farm.get("farmer") or (0, 0))] + [tuple(h) for h in (farm.get("hands") or [])]
    day = int(obs.get("day", 0))
    a = s.act(obs)
    units = [a.get("farmer") or ["PASS"]] + list(a.get("hands") or [])
    if int(obs.get("hour", 0)) == 12:
        workers_day[day] = len(units)
    for i, u in enumerate(units):
        if not u or i >= len(pos):
            continue
        op = str(u[0])
        if op in ("NORTH", "SOUTH", "EAST", "WEST"):
            moves_actual[day] += 1
        elif op in ("WATER", "HARVEST", "FEED", "CARE", "COLLECT_FERTILIZER", "FERTILIZE", "PLANT", "DIG", "PLACE", "BUILD_PASTURE", "BUILD_COOP"):
            events[day].append((pos[i][0], pos[i][1], op))
    try: b = opp(g.observe(1))
    except Exception: b = {"farmer": ["PASS"], "hands": [], "market": []}
    g.step(a, b)
print(f"bank={int(g.reward(0))}")
tot_actual = tot_replan = 0
for day in sorted(events):
    evs = events[day]
    nw = max(workers_day.get(day, 6), 1)
    # 事件按格聚合(同格多动作零移动)
    cells = sorted({(x, y) for x, y, _ in evs})
    # 均衡分给 nw 个工人:按 x 排序切片,每人最近邻链
    per = max(1, (len(cells) + nw - 1) // nw)
    replan_moves = 0
    for wi in range(nw):
        part = cells[wi * per:(wi + 1) * per]
        if not part:
            continue
        cur = (4, 4)
        rest = set(part)
        while rest:
            nxt = min(rest, key=lambda c: abs(c[0] - cur[0]) + abs(c[1] - cur[1]))
            replan_moves += abs(nxt[0] - cur[0]) + abs(nxt[1] - cur[1])
            cur = nxt
            rest.discard(nxt)
    tot_actual += moves_actual[day]
    tot_replan += replan_moves
print(f"实际总移动 {tot_actual} vs 重排理论移动 {tot_replan}  可省 {tot_actual - tot_replan} 步 ({(tot_actual-tot_replan)/max(tot_actual,1):.0%})")
print(f"(等效人力 +{(tot_actual - tot_replan)/24/30:.1f} 人/天)")
