"""番茄机制受控实验:农夫种 1 格番茄+1 格草莓对照,每天浇水,每步尝试收获,记录全程。"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE / "proto"))
import sched_proto as sp
k = sp.engine.load_kagsim(); g = k.Game(seed=11)
CELL = {(4, 3): "TOMATO", (3, 4): "STRAWBERRY"}
log = {cr: [] for cr in CELL.values()}
t = 0; planted = set()
def path(src, dst):
    if src[1] != dst[1]: return ["SOUTH"] if dst[1] > src[1] else ["NORTH"]
    if src[0] != dst[0]: return ["EAST"] if dst[0] > src[0] else ["WEST"]
    return None
plan = []
while not sp.engine._val(g.done):
    o = g.observe(0); f = o["farms"][0]; pos = tuple(f["farmer"]); hour = t % 24
    mk = []
    if t == 0: mk = [["BUY_SEED", "TOMATO", 1], ["BUY_SEED", "STRAWBERRY", 1]]
    if hour == 1:
        plan = []
        for cell, cr in CELL.items():
            tile = f["tiles"][cell[1]][cell[0]]
            if not isinstance(tile, dict): plan.append((cell, ["PLANT", cr]))
            plan.append((cell, ["WATER"]))
            plan.append((cell, ["HARVEST"]))
    cmd = ["PASS"]
    if plan:
        cell, c = plan[0]; mv = path(pos, cell)
        if mv: cmd = mv
        else:
            cmd = c; before = f["tiles"][cell[1]][cell[0]]
            inv0 = sum((o["private"].get("inventories") or [{}])[0].values())
            plan.pop(0)
    g.step({"farmer": cmd, "hands": [], "market": mk}, {"farmer": ["PASS"], "hands": [], "market": []})
    if cmd[0] == "HARVEST":
        o2 = g.observe(0); after = o2["farms"][0]["tiles"][cell[1]][cell[0]]
        inv1 = sum((o2["private"].get("inventories") or [{}])[0].values())
        cr = CELL[cell]
        b = before if isinstance(before, dict) else {}
        a2 = after if isinstance(after, dict) else {}
        log[cr].append((t, b.get("yield_units"), inv1 - inv0, a2.get("yield_units"), a2.get("kind"), b.get("max_lifespan_step")))
    t += 1
for cr, v in log.items():
    got = [(x[0], x[1], x[2]) for x in v if x[2] and x[2] > 0]
    print(f"{cr}: 首次收获 {got[0] if got else None};全部成功收获(t,收前yield,件): {got[:14]}")
    print(f"   寿命 max_lifespan_step={v[0][5] if v else None};收获后格状态样例 {[x[4] for x in v[-3:]]}")
