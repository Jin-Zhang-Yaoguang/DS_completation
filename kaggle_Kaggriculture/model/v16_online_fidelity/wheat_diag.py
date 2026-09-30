"""小麦轮作诊断：每次收获的 yield、收获后到补种的间隙、以及全场小麦块数曲线。"""
import sys, collections
from fidelity import make_agent, engine
spec, seed = sys.argv[1], int(sys.argv[2])
a = make_agent(spec)
k = engine.load_kagsim(); g = k.Game(seed=seed)
step = 0
prev = {}
harvest_yield = collections.Counter(); replant_gap = []; empty_since = {}
wheat_n = {}
while not engine._val(g.done):
    o = g.observe(0); day = step // 24
    tiles = o["farms"][0]["tiles"]
    cur = {}
    nw = 0
    for r, row in enumerate(tiles):
        for c, x in enumerate(row):
            if isinstance(x, dict) and x.get("crop") == "WHEAT":
                cur[(r, c)] = x.get("yield_units", 0); nw += 1
            elif x is None:
                if (r, c) in prev:      # 小麦刚被收走 → 空地
                    harvest_yield[prev[(r, c)]] += 1
                    empty_since[(r, c)] = step
                elif (r, c) not in empty_since:
                    empty_since.setdefault((r, c), step)
    for pos in list(empty_since):
        x = tiles[pos[0]][pos[1]]
        if isinstance(x, dict) and x.get("kind") == "PLANT":
            replant_gap.append(step - empty_since.pop(pos))
    if step % 24 == 12: wheat_n[day] = nw
    prev = cur
    try: act = a(o)
    except Exception: act = {"farmer": ["PASS"], "hands": [], "market": []}
    g.step(act, {"farmer": ["PASS"], "hands": [], "market": []})
    step += 1
print(f"{spec.split('/')[-1][:22]} bank={engine._val(g.reward(0)):.0f}")
print("  收获时 yield 分布:", dict(sorted(harvest_yield.items())), " 总收获轮次:", sum(harvest_yield.values()))
if replant_gap:
    rg = sorted(replant_gap)
    print(f"  空地→补种间隙: n={len(rg)} med={rg[len(rg)//2]}h p90={rg[int(len(rg)*0.9)]}h mean={sum(rg)/len(rg):.0f}h")
print("  小麦块数 by day:", {d: wheat_n[d] for d in sorted(wheat_n)})
