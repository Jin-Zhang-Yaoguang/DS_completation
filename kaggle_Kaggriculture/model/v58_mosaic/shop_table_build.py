"""商店条件带表:4 条 y63 带 × 8 强制商店 × 2 seed solo 矩阵 -> shop_tape_table.json"""
import sys, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

HERE = Path(__file__).resolve().parent
SHOPS = ("BAKERY", "BRUNCH_SPOT", "FARMERS_MARKET", "ICE_CREAM_SHOP",
         "PET_CAFE", "PIZZA_SHOP", "SMOOTHIE_SHOP", "YARN_STORE")

def one(job):
    ti, shop, sd = job
    sys.path.insert(0, str(HERE.parent / "v16_online_fidelity"))
    sys.path.insert(0, str(HERE.parent / "v4_demand_race" / "harness"))
    import fidelity
    r = fidelity.play(f"tape:{HERE}/y63_tape{ti}.json", "pass:", sd, [(shop, 0)])
    return (ti, shop, sd, r["bank"][0])

if __name__ == "__main__":
    jobs = [(ti, s, sd) for ti in range(4) for s in SHOPS for sd in (11, 22)]
    agg = {}
    with ProcessPoolExecutor(8) as ex:
        for ti, shop, sd, b in ex.map(one, jobs):
            agg.setdefault(shop, {}).setdefault(ti, []).append(b)
    table = {}
    for shop in SHOPS:
        means = {ti: sum(v) / len(v) for ti, v in agg[shop].items()}
        best = max(means, key=means.get)
        table[shop] = best
        print(f"{shop:16s} best=tape{best}  " + " ".join(f"t{ti}:{means[ti]:.0f}" for ti in range(4)), flush=True)
    json.dump(table, open(HERE / "shop_tape_table.json", "w"))
    print("table:", table, flush=True)
