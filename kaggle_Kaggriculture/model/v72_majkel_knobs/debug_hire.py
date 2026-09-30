import sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from debug_one import load, MODEL, engine, fidelity

def run(pack, seed=1009):
    ag, _ = load(pack); opp = fidelity.make_agent("tape:" + str(MODEL / "opponent_pool_v1/tapes/ymg_slice0.json"))
    g = engine.load_kagsim().Game(seed=seed); fb = {"farmer": ["PASS"], "hands": [], "market": []}
    rows = {}; ops = collections.Counter(); order_pos = []
    for t in range(719):
        o0 = g.observe(0); f = o0["farms"][0]; d = t // 24
        try: a = ag(o0)
        except Exception: a = dict(fb)
        b = opp(g.observe(1))
        for u in [a.get("farmer") or []] + list(a.get("hands") or []):
            if u and u[0] in ("HARVEST", "WATER", "FEED", "COLLECT_FERTILIZER"): ops[(d, u[0])] += 1
        mk = [o[0] for o in a.get("market") or [] if o]
        if t % 24 in (0, 1) and 12 <= d <= 16:
            order_pos.append((t, int(f["money"]), "".join({"SELL": "S", "HIRE": "H", "BUY_PRODUCT": "B", "BUY_SEED": "s", "BUY_ANIMAL": "A", "BUY_LAND": "L"}.get(x, "?") for x in mk)))
        g.step(a, b)
        if t % 24 == 3:
            f2 = g.observe(0)["farms"][0]; rows[d] = (len(f2.get("hands") or []), f2.get("hires_today"))
    return rows, ops, order_pos, g.reward(0)

for label, pack in [("parent", "y68f_parent.py"), ("beat0", "cands/mj_e161725f7a.py")]:
    rows, ops, pos, bank = run(pack)
    print(f"== {label} bank {bank:.0f}")
    print("   hands@hour3 (hands, hires_today) by day:", {d: rows[d] for d in sorted(rows) if d in (6, 9, 10, 12, 14, 16, 18, 20, 24, 27)})
    print("   HARVEST/WATER/FEED/COLLECT by day:", {d: (ops[(d,'HARVEST')], ops[(d,'WATER')], ops[(d,'FEED')], ops[(d,'COLLECT_FERTILIZER')]) for d in (10, 12, 14, 16, 18, 20, 24)})
    print("   market order sequence at hour0/1, d12-16 (t, money, orders):", pos[:10])
