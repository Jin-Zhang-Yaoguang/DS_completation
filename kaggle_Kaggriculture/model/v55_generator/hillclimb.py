"""局部爬山:从 best_cfg 出发,每轮扰动 1-2 参数,8 局评价(ch/rb × 11,22,33,44),只接受改善。"""
import sys, json, random
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "v16_online_fidelity"))
sys.path.insert(0, str(HERE.parent / "v4_demand_race" / "harness"))
from search import SPACE, one

EXTRA_SPACE = {"pick_qty": [3, 4, 5], "sell_timing": [0, 1]}
BASE = {"hire_per_day": 12, "fert_lo": 10, "fert_hi": 27, "feed_reserve": 2, "tomato_from": 14, "carrot_from": 21, "plant_stop": 26, "sell_every": 3, "keep_fert": 8, "prem_lot": 8, "wheat_sell_th": 25, "seed_money": 300, "feed_money": 100, "early_hands": 6, "pasture_target": 8, "animal_workers": 3, "fert_workers": 1, "coop_target": 4, "build_until": 11, "cow_until": 6, "goose_until": 16, "patrol": 0, "share_wheat": 8, "share_straw": 30, "share_tomato": 12, "share_carrot": 12, "own_opening": 0, "sell_timing": 1, "pick_qty": 4, "prio_band": 0, "inertia": 0, "core_ring": 0, "day_chain": 0}

def evaluate(kw, ex):
    jobs = [(kw, sd, o) for sd in (11, 22, 33, 44) for o in ("ch", "rb")]
    banks = list(ex.map(one, jobs))
    return sum(banks) / len(banks)

if __name__ == "__main__":
    random.seed(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
    n_rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    cur = dict(BASE)
    with ProcessPoolExecutor(8) as ex:
        cur_score = evaluate(cur, ex)
        print(f"base score={cur_score:.0f}", flush=True)
        for i in range(n_rounds):
            kw = dict(cur)
            space = dict(SPACE); space.update(EXTRA_SPACE)
            for k in random.sample(list(space.keys()), random.choice((1, 2))):
                vs2 = [v for v in space[k] if v != kw.get(k)]
                if vs2:
                    kw[k] = random.choice(vs2)
            sc = evaluate(kw, ex)
            if sc > cur_score:
                changed = {k: v for k, v in kw.items() if cur.get(k) != v}
                cur, cur_score = kw, sc
                print(f"[{i}] {sc:.0f} ACCEPT {changed}", flush=True)
            elif i % 10 == 0:
                print(f"[{i}] {sc:.0f}", flush=True)
    print("FINAL:", cur_score, json.dumps(cur))
    json.dump({"avg": cur_score, "cfg": cur}, open(HERE / "best_cfg_B.json", "w"))
