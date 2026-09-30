"""K1 深度探针：动作计数、买地/建栏/施肥时刻、逐品卖出收入、逐日资产。"""
import sys
import importlib.util
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, "/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness")
import engine  # noqa: E402

MP = None


def main(seed):
    global MP
    spec = importlib.util.spec_from_file_location("k1", HERE / "main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    MP = mod.market_price
    k = engine.load_kagsim()
    g = k.Game(seed=seed)

    def pa(o):
        return {"farmer": ["PASS"], "hands": [], "market": []}

    acts = Counter()
    sell_rev = Counter()
    sell_qty = Counter()
    buy_cost = Counter()
    land_turns = []
    fert_by_day = Counter()
    prev_quads = 1
    while not (g.done() if callable(g.done) else g.done):
        o0 = g.observe(0)
        day, hour = int(o0["day"]), int(o0["hour"])
        turn = day * 24 + hour
        farm = o0["farms"][0]
        quads = len(farm.get("unlocked_quadrants") or ["NW"])
        if quads > prev_quads:
            land_turns.append(turn)
            prev_quads = quads
        inv_mkt = dict((o0.get("market") or {}).get("inventory") or {})
        a = mod.agent(o0)
        for u in [a["farmer"]] + a["hands"]:
            acts[u[0]] += 1
            if u[0] == "FERTILIZE":
                fert_by_day[day] += 1
        for m in a["market"]:
            if m[0] == "SELL":
                it, q = m[1], m[2]
                inv = inv_mkt.get(it, 10000)
                rev = 0
                v = inv
                for _ in range(int(q)):
                    p = MP(it, v)
                    rev += p
                    if p > 1:
                        v += 1
                sell_rev[it] += rev
                sell_qty[it] += q
            elif m[0] == "BUY_SEED":
                buy_cost["seed_" + m[1]] += mod.CROPS[m[1]]["seed"] * m[2]
            elif m[0] == "BUY_ANIMAL":
                buy_cost["animal_" + m[1]] += mod.ANIMALS[m[1]]["cost"]
            elif m[0] == "BUY_PRODUCT":
                buy_cost["buy_" + m[1]] += 25 * m[2]
        g.step(a, pa(o0))
    print(f"seed {seed} bank {g.reward(0):.0f}")
    print("acts:", dict(acts.most_common()))
    print("land buy turns:", land_turns)
    print("sell qty:", dict(sell_qty.most_common()))
    print("sell rev (approx):", {k2: int(v) for k2, v in sell_rev.most_common()})
    print("buy cost (approx):", {k2: int(v) for k2, v in buy_cost.most_common()})
    print("fert by day:", dict(sorted(fert_by_day.items())), "total", sum(fert_by_day.values()))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1046)
