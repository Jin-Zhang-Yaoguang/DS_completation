"""定向实验：钉无 YARN_STORE 商店序列，比较候选与 V17a 在对轰局（vs 扰动家族）的表现。"""
import sys, json
from concurrent.futures import ProcessPoolExecutor
from fidelity import play
NOYARN = [["BAKERY",72],["PIZZA_SHOP",144],["BRUNCH_SPOT",216],["SMOOTHIE_SHOP",288],["FARMERS_MARKET",360],["ICE_CREAM_SHOP",432],["PET_CAFE",504],["FARMERS_MARKET",576]]
EARLY = [["YARN_STORE",72],["PIZZA_SHOP",144],["BRUNCH_SPOT",216],["SMOOTHIE_SHOP",288],["FARMERS_MARKET",360],["ICE_CREAM_SHOP",432],["PET_CAFE",504],["FARMERS_MARKET",576]]
def one(a):
    cand, opp, seed, sh = a
    r0 = play(cand, opp, seed, sh); r1 = play(opp, cand, seed, sh)
    return (r0["bank"][0], r0["bank"][1]), (r1["bank"][1], r1["bank"][0])
if __name__ == "__main__":
    cands = sys.argv[1].split(","); opp = sys.argv[2]; seeds = [int(x) for x in sys.argv[3].split(",")]
    MID = [["BAKERY",72],["PIZZA_SHOP",144],["YARN_STORE",216],["SMOOTHIE_SHOP",288],["FARMERS_MARKET",360],["ICE_CREAM_SHOP",432],["PET_CAFE",504],["FARMERS_MARKET",576]]
    for label, sh in (("无yarn", NOYARN), ("yarn@3", MID)):
        for cand in cands:
            jobs = [(cand, opp, sd, sh) for sd in seeds]
            res = []
            with ProcessPoolExecutor(8) as ex:
                for pair in ex.map(one, jobs): res += list(pair)
            w = sum(m > t for m, t in res)
            print(f"{label} {cand.split('/')[-2][:18]:18s}: w={w}/{len(res)} mine={sum(m for m,_ in res)/len(res):7.0f} theirs={sum(t for _,t in res)/len(res):7.0f}", flush=True)
