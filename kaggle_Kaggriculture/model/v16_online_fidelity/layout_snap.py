import sys
from fidelity import make_agent, engine
spec, seed, snapday = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
a = make_agent(spec)
k = engine.load_kagsim(); g = k.Game(seed=seed)
step = 0
while not engine._val(g.done) and step < snapday * 24:
    o = g.observe(0)
    try: act = a(o)
    except Exception: act = {"farmer": ["PASS"], "hands": [], "market": []}
    g.step(act, {"farmer": ["PASS"], "hands": [], "market": []}); step += 1
o = g.observe(0); tiles = o["farms"][0]["tiles"]
SYM = {"WHEAT": "w", "STRAWBERRY": "S", "MELON": "M", "CARROT": "c", "TOMATO": "t"}
print(f"{spec.split('/')[-1][:20]} day{snapday}:")
for row in tiles:
    line = ""
    for x in row:
        if x is None: line += ". "
        elif x == "LOCKED": line += "L "
        elif isinstance(x, dict):
            kd = x.get("kind")
            if kd == "PLANT": line += SYM.get(x.get("crop"), "?") + " "
            elif kd == "PASTURE": line += "P "
            elif kd == "COOP": line += "C "
            elif kd == "WEED": line += "# "
            else: line += kd[0] + " "
    print(" " + line)
