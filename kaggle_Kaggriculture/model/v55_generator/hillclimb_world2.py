"""世界爬山 v2:用实局首店表选 (seed,opp) 对;训练 4 对,holdout 4 对验收。"""
import sys, json, random
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "v16_online_fidelity"))
sys.path.insert(0, str(HERE.parent / "v4_demand_race" / "harness"))
from search import SPACE, one

SHOP = sys.argv[1]
table = json.load(open(HERE / "real_shop_table.json"))
pairs = [(int(k.split(":")[0]), k.split(":")[1]) for k, v in sorted(table.items()) if v == SHOP]
TRAIN, HOLD = pairs[:4], pairs[4:8]
BASE = json.load(open(HERE / "best_cfg_58k.json"))["cfg"]
SP = dict(SPACE); SP.update({"pick_qty": [3, 4, 5], "sell_timing": [0, 1]})

def ev(kw, ex, ps):
    banks = list(ex.map(one, [(kw, sd, o) for sd, o in ps]))
    return sum(banks) / len(banks)

if __name__ == "__main__":
    rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    random.seed(int(sys.argv[3]) if len(sys.argv) > 3 else 17)
    cur = dict(BASE)
    with ProcessPoolExecutor(6) as ex:
        base_train = ev(cur, ex, TRAIN)
        print(f"[{SHOP}] base_train={base_train:.0f} train={TRAIN} hold={HOLD}", flush=True)
        cur_score = base_train
        for i in range(rounds):
            kw = dict(cur)
            for k in random.sample(list(SP.keys()), random.choice((1, 2))):
                vs2 = [v for v in SP[k] if v != kw.get(k)]
                if vs2: kw[k] = random.choice(vs2)
            sc = ev(kw, ex, TRAIN)
            if sc > cur_score:
                cur, cur_score = kw, sc
                print(f"[{SHOP}][{i}] {sc:.0f} ACCEPT", flush=True)
        # holdout 验收:世界 cfg vs 全局 cfg
        h_world = ev(cur, ex, HOLD)
        h_base = ev(BASE, ex, HOLD)
        verdict = "KEEP" if h_world > h_base else "DROP"
        print(f"[{SHOP}] train {base_train:.0f}->{cur_score:.0f}; holdout world={h_world:.0f} vs base={h_base:.0f} -> {verdict}", flush=True)
        if verdict == "KEEP":
            json.dump({"score": h_world, "cfg": cur}, open(HERE / f"world2_cfg_{SHOP}.json", "w"))
