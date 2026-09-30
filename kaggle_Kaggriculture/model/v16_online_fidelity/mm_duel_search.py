"""做市参数搜索（正确场景：钉无 yarn 对轰）。"""
import os, json, sys
from concurrent.futures import ProcessPoolExecutor
W = "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model"
from fidelity import play
NOYARN = [["BAKERY",72],["PIZZA_SHOP",144],["BRUNCH_SPOT",216],["SMOOTHIE_SHOP",288],["FARMERS_MARKET",360],["ICE_CREAM_SHOP",432],["PET_CAFE",504],["FARMERS_MARKET",576]]
CAND = f"sub:{W}/v25_market_maker/main.py"
def one(a):
    cfg, opp, sd = a
    os.environ["MM_PARAMS"] = json.dumps(cfg)
    r0 = play(CAND, opp, sd, NOYARN); r1 = play(opp, CAND, sd, NOYARN)
    return (r0["bank"][0] - r0["bank"][1], r1["bank"][1] - r1["bank"][0])
def score(cfg, opp):
    jobs = [(cfg, opp, sd) for sd in (41, 42, 43, 44, 45, 46)]
    with ProcessPoolExecutor(6) as ex:
        res = [d for pair in ex.map(one, jobs) for d in pair]
    return sum(r > 0 for r in res), len(res), sum(res) / len(res)
if __name__ == "__main__":
    opp = "tape:tapes/fam_C_0w5l.json"
    for cfg in ({}, {"buy":0.88,"sell":0.96}, {"buy":0.9,"sell":1.0,"lot":12}, {"buy":0.95,"sell":1.05,"lot":12,"budget":0.4}, {"buy":0.85,"sell":1.0,"cap":40,"budget":0.4}):
        w, n, m = score(cfg, opp)
        print(f"C {json.dumps(cfg):55s} w={w}/{n} margin={m:+.0f}", flush=True)
    opp = "tape:tapes/fam_F_new.json"
    for cfg in ({}, {"buy":0.9,"sell":1.0,"lot":12}, {"buy":0.95,"sell":1.05,"lot":12,"budget":0.4}):
        w, n, m = score(cfg, opp)
        print(f"F {json.dumps(cfg):55s} w={w}/{n} margin={m:+.0f}", flush=True)
