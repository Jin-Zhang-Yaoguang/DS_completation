"""受控实验:农夫在 (4,3)(3,4)(4,2)(2,4) 各种一种作物,每天浇水;对照格每天中午尝试收获,记录产量演化。"""
import json, sys
import sched_proto as sp
CROPS = sys.argv[1].split(",") if len(sys.argv) > 1 else ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY"]
CELLS = [(4, 3), (3, 4), (4, 2), (2, 4)]
def path(src, dst):
    x, y = src
    if y != dst[1]: return ["SOUTH"] if dst[1] > y else ["NORTH"]
    if x != dst[0]: return ["EAST"] if dst[0] > x else ["WEST"]
    return None
k = sp.engine.load_kagsim(); g = k.Game(seed=7)
plan = []      # 当天要做的 (cell, cmd) 顺序
log = {c: [] for c in CROPS}
t = 0; mode = {}
while not sp.engine._val(g.done) and t < 24 * 22:
    o = g.observe(0); f = o["farms"][0]; pos = tuple(f["farmer"]); hour = t % 24; day = t // 24
    mk = []
    if t == 0:
        mk = [["BUY_SEED", c, 1] for c in CROPS]
    if hour == 1:
        plan = []
        for c, cell in zip(CROPS, CELLS):
            tile = f["tiles"][cell[1]][cell[0]]
            if not isinstance(tile, dict) or tile.get("kind") != "PLANT":
                plan.append((cell, ["PLANT", c]))
            plan.append((cell, ["WATER"]))
        for c, cell in zip(CROPS, CELLS):
            plan.append((cell, ["HARVEST"]))
    cmd = ["PASS"]
    if plan:
        cell, c = plan[0]
        mv = path(pos, cell)
        if mv: cmd = mv
        else:
            cmd = c; before = f["tiles"][cell[1]][cell[0]]; inv0 = sum((o["private"].get("inventories") or [{}])[0].values())
            plan.pop(0)
    g.step({"farmer": cmd, "hands": [], "market": mk}, {"farmer": ["PASS"], "hands": [], "market": []})
    if cmd[0] == "HARVEST":
        o2 = g.observe(0); after = o2["farms"][0]["tiles"][cell[1]][cell[0]]; inv1 = sum((o2["private"].get("inventories") or [{}])[0].values())
        crop = CROPS[CELLS.index(cell)]
        log[crop].append((day, (before or {}).get("yield_units") if isinstance(before, dict) else None,
                          (before or {}).get("kind") if isinstance(before, dict) else before,
                          inv1 - inv0, (after or {}).get("kind") if isinstance(after, dict) else after,
                          (after or {}).get("yield_units") if isinstance(after, dict) else None))
    t += 1
for c in CROPS:
    print(c, "(天, 收前产量, 收前类型, 拿到件数, 收后类型, 收后产量):")
    print("   ", log[c][:22])
