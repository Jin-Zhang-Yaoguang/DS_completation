"""世界参数爬山:每个首店世界用其 seed 组(×ch/rb)爬专属配置。
用法: python hillclimb_world.py <SHOP> <rounds> <rng>
"""
import sys, json, random
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "v16_online_fidelity"))
sys.path.insert(0, str(HERE.parent / "v4_demand_race" / "harness"))
from search import SPACE, one

SHOP = sys.argv[1]
seed_shop = json.load(open(HERE / "seed_shop.json"))
SEEDS = [int(k) for k, v in seed_shop.items() if v == SHOP][:3]
BASE = json.load(open(HERE / "best_cfg_58k.json"))["cfg"]
SP = dict(SPACE)
SP.update({"pick_qty": [3, 4, 5], "sell_timing": [0, 1]})

def evaluate(kw, ex):
    jobs = [(kw, sd, o) for sd in SEEDS for o in ("ch", "rb")]
    banks = list(ex.map(one, jobs))
    return sum(banks) / len(banks)

if __name__ == "__main__":
    rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 25
    random.seed(int(sys.argv[3]) if len(sys.argv) > 3 else 11)
    cur = dict(BASE)
    with ProcessPoolExecutor(6) as ex:
        cur_score = evaluate(cur, ex)
        print(f"[{SHOP}] base={cur_score:.0f} seeds={SEEDS}", flush=True)
        for i in range(rounds):
            kw = dict(cur)
            for k in random.sample(list(SP.keys()), random.choice((1, 2))):
                vs2 = [v for v in SP[k] if v != kw.get(k)]
                if vs2:
                    kw[k] = random.choice(vs2)
            sc = evaluate(kw, ex)
            if sc > cur_score:
                ch = {k: v for k, v in kw.items() if cur.get(k) != v}
                cur, cur_score = kw, sc
                print(f"[{SHOP}][{i}] {sc:.0f} ACCEPT {ch}", flush=True)
    print(f"[{SHOP}] FINAL {cur_score:.0f}")
    json.dump({"score": cur_score, "cfg": cur}, open(HERE / f"world_cfg_{SHOP}.json", "w"))
