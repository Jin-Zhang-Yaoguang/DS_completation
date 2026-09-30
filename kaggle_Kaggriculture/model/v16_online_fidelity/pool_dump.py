"""dump 指定时刻全体工人的候选池与空地状态。"""
import sys, os, json
os.environ["V22_DUMP_AT"] = sys.argv[2]
from fidelity import make_agent, engine
spec, seed = sys.argv[1], int(sys.argv[3])
a = make_agent(spec)
k = engine.load_kagsim(); g = k.Game(seed=seed)
step = 0; target = int(sys.argv[2])
while not engine._val(g.done) and step <= target:
    o = g.observe(0)
    if step == target:
        tiles = o["farms"][0]["tiles"]
        empty = [(x, y) for y in range(10) for x in range(10) if tiles[y][x] is None]
        print(f"step {step} (d{step//24}h{step%24}) empty tiles: {len(empty)} -> {empty}")
        farm = o["farms"][0]
        print("workers:", [tuple(farm["farmer"])] + [tuple(h) for h in farm["hands"]])
    try: act = a(o)
    except Exception as e: act = {"farmer": ["PASS"], "hands": [], "market": []}
    if step == target:
        al = [act.get("farmer")] + list(act.get("hands") or [])
        print("actions:", al)
    g.step(act, {"farmer": ["PASS"], "hands": [], "market": []})
    step += 1
