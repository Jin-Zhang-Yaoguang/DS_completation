"""精确逐单位收入归因：复刻引擎 _process_market 的 lockstep 结算，用引擎自身 market_price。"""
import os, sys, json, collections, importlib
import kaggle_environments
_KE = importlib.import_module("kaggle_environments.envs.kaggriculture.kaggriculture")
PRODUCTS = _KE.PRODUCTS; CROPS = _KE.CROPS; ANIMALS = _KE.ANIMALS; SHOPS = _KE.SHOPS; TOWN_CENTER = _KE.TOWN_CENTER_PRODUCTS
market_price = _KE.market_price

def _parse(o):
    if not isinstance(o, list) or not o: return None
    op = o[0]
    if op in ("HIRE", "BUY_LAND"): return {"type": op, "item": None, "remaining": 1}
    if len(o) < 3: return None
    try: n = int(o[2])
    except Exception: return None
    if n <= 0: return None
    return {"type": op, "item": o[1], "remaining": n}

def settle(orders, inv, sheds, moneys, params=None, max_orders=10):
    """orders: [list0, list1]; inv: dict 产品->市场库存（会被修改）; sheds/moneys 会被修改。
    返回 rev[p][item] 收入, qty[p][item] 数量, spend[p][kind] 支出。"""
    rev = [collections.Counter(), collections.Counter()]; qty = [collections.Counter(), collections.Counter()]; spend = [collections.Counter(), collections.Counter()]
    queues = [list(o or [])[:max_orders] for o in orders]
    hires = [0, 0]
    for i in range(max(len(q) for q in queues) if queues else 0):
        st = [(_parse(q[i]) if i < len(q) else None) for q in queues]
        for p, s in enumerate(st):
            if s is None: continue
            if s["type"] == "HIRE":
                spend[p]["HIRE"] += 1; st[p] = None   # 费用另算（fib），此处只计数
            elif s["type"] == "BUY_LAND":
                spend[p]["LAND"] += 1; st[p] = None
        guard = 0
        while True:
            guard += 1
            if guard > 100000: break
            quoted = [None, None]
            for p, s in enumerate(st):
                if s is None or s["remaining"] <= 0: continue
                op, it = s["type"], s["item"]
                if op == "SELL" and it in PRODUCTS: quoted[p] = ("SELL", it, market_price(it, inv[it], params), s)
                elif op == "BUY_PRODUCT" and it in ("WHEAT", "FERTILIZER"): quoted[p] = ("BUY_PRODUCT", it, market_price(it, inv[it] - 1, params), s)
                elif op == "BUY_SEED" and it in CROPS: quoted[p] = ("BUY_SEED", it, CROPS[it]["seed"], s)
                elif op == "BUY_ANIMAL" and it in ANIMALS: quoted[p] = ("BUY_ANIMAL", it, ANIMALS[it]["cost"], s)
                else: st[p] = None
            if all(q is None for q in quoted): break
            any_ok = False
            for p, q in enumerate(quoted):
                if q is None: continue
                op, it, price, s = q; ok = False
                if op == "SELL":
                    if sheds[p].get(it, 0) > 0:
                        sheds[p][it] -= 1; moneys[p] += price; rev[p][it] += price; qty[p][it] += 1
                        if price > 1: inv[it] += 1
                        ok = True
                elif op == "BUY_PRODUCT":
                    if moneys[p] >= price and sum(sheds[p].values()) < 100:
                        moneys[p] -= price; sheds[p][it] = sheds[p].get(it, 0) + 1; inv[it] -= 1; spend[p]["BP_" + it] += price; ok = True
                elif op == "BUY_SEED":
                    if moneys[p] >= price: moneys[p] -= price; spend[p]["SEED"] += price; ok = True
                elif op == "BUY_ANIMAL":
                    if moneys[p] >= price and sum(sheds[p].values()) < 100: moneys[p] -= price; spend[p]["ANIMAL"] += price; ok = True
                if ok: s["remaining"] -= 1; any_ok = True
                else: st[p] = None
            if not any_ok: break
    return rev, qty, spend

def demand_absorption(shops_sched, total_steps=720):
    """各产品全局城镇吸纳量（单位）：商店每 4 步各消耗 1（单品店 2），城镇中心每 24 步各 1。"""
    absorb = collections.Counter()
    for step in range(1, total_steps + 1):
        if step % 4 == 0:
            for name, st in shops_sched:
                if st <= step:
                    prods = SHOPS[name]; mult = 2 if len(prods) == 1 else 1
                    for it in prods: absorb[it] += mult
        if step % 24 == 0:
            for it in TOWN_CENTER: absorb[it] += 1
    return absorb

def play_attributed(agent_paths, sc, W):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from engine import fresh_agent, load_scenario
    def val(x): return x() if callable(x) else x
    ags = [fresh_agent(p) for p in agent_paths]
    k = load_scenario(); g = k.Game(seed=sc["seed"]); sched = sc["shops"]; g.force_shops([n for n, st in sched if st <= 0]); step = 0
    REV = [collections.Counter(), collections.Counter()]; QTY = [collections.Counter(), collections.Counter()]; SP = [collections.Counter(), collections.Counter()]
    mism = 0
    while not val(g.done):
        obs = [g.observe(0), g.observe(1)]
        acts = [ags[i].agent(obs[i]) for i in range(2)]
        inv = dict(obs[0]["market"]["inventory"]); params = obs[0]["market"].get("params")
        sheds = [dict(obs[i]["private"]["shed"]) for i in range(2)]; moneys = [obs[i]["farms"][i]["money"] for i in range(2)]
        rev, qty, spend = settle([a.get("market") or [] for a in acts], inv, sheds, moneys, params)
        g.step(acts[0], acts[1]); step += 1; g.force_shops([n for n, st in sched if st <= step])
        for i in range(2):
            REV[i].update(rev[i]); QTY[i].update(qty[i]); SP[i].update(spend[i])
    return g, REV, QTY, SP

if __name__ == "__main__":
    W = "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture"
    a0, a1, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
    sc = [s for s in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "scenarios_64.json"))) if s["seed"] == seed][0]
    g, REV, QTY, SP = play_attributed([a0, a1], sc, W)
    ab = demand_absorption(sc["shops"])
    print("shops:", sc["shops"]); print("吸纳量:", dict(ab))
    for i in range(2):
        tot = sum(REV[i].values())
        print(f"\nP{i} bank {g.reward(i):.0f}  总收入 {tot:.0f}  支出 {dict(SP[i])}")
        for it in PRODUCTS:
            if QTY[i][it]: print(f"   {it:11s} 量 {QTY[i][it]:5d}  收入 {REV[i][it]:8.0f}  均价 {REV[i][it]/QTY[i][it]:6.1f}  (吸纳 {ab.get(it,0)})")
