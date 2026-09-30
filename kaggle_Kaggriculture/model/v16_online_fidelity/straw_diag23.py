"""V23 草莓执行诊断：种植时刻/在场块数/肥效覆盖/死亡。"""
import sys, collections
from fidelity import make_agent, engine
spec, seed = sys.argv[1], int(sys.argv[2])
a = make_agent(spec)
k = engine.load_kagsim(); g = k.Game(seed=seed)
step = 0; sb = {}; fert_cov = [0, 0]; died = 0; prev = set()
plant_day = collections.Counter()
while not engine._val(g.done):
    o = g.observe(0); day = step // 24
    tiles = o["farms"][0]["tiles"]
    cur = set()
    if step % 24 == 12:
        n = 0
        for r, row in enumerate(tiles):
            for c, x in enumerate(row):
                if isinstance(x, dict) and x.get("crop") == "STRAWBERRY":
                    n += 1; cur.add((r, c))
                    age = day - x.get("planted_day", day)
                    if age >= 9:
                        fert_cov[1] += 1
                        if x.get("fertilized_until_day", -1) >= day: fert_cov[0] += 1
        sb[day] = n
        for pos in prev - cur:
            x = tiles[pos[0]][pos[1]]
            if isinstance(x, dict) and x.get("kind") == "WEED": died += 1
        prev = cur
    try: act = a(o)
    except Exception: act = {"farmer": ["PASS"], "hands": [], "market": []}
    for x in [act.get("farmer")] + list(act.get("hands") or []):
        if x and str(x[0]) == "PLANT" and len(x) > 1 and x[1] == "STRAWBERRY": plant_day[day] += 1
    g.step(act, {"farmer": ["PASS"], "hands": [], "market": []}); step += 1
print("straw tiles by day:", {d: sb[d] for d in sorted(sb) if d <= 22})
print("PLANT STRAWBERRY by day:", dict(sorted(plant_day.items())))
print(f"fert coverage on prod days: {fert_cov[0]}/{fert_cov[1]} died={died}")
