"""动作带的 seed 稳健性：同一动作带在多个 seed 下（对手 PASS，钉教师商店）的产量与银行。"""
import sys, json
from concurrent.futures import ProcessPoolExecutor
from fidelity import play
SH=[["ICE_CREAM_SHOP",72],["BRUNCH_SPOT",144],["YARN_STORE",216],["PIZZA_SHOP",288],["ICE_CREAM_SHOP",360],["PIZZA_SHOP",432],["PIZZA_SHOP",504],["SMOOTHIE_SHOP",576]]
def one(a):
    spec, seed = a
    r = play(spec, "pass:", seed, SH)
    return {"spec": spec, "seed": seed, "bank": r["bank"][0], "prod": r["prod"][0], "zero": r["zero_sell_steps"][0]}
if __name__ == "__main__":
    specs = sys.argv[1].split(","); seeds = [int(x) for x in sys.argv[2].split(",")]
    jobs = [(s, sd) for s in specs for sd in seeds]
    with ProcessPoolExecutor(8) as ex:
        for r in ex.map(one, jobs):
            pr = r["prod"]; print(json.dumps({"spec": r["spec"].split("/")[-1], "seed": r["seed"], "bank": r["bank"], "STRAW": pr.get("STRAWBERRY",0), "WOOL": pr.get("WOOL",0), "MILK": pr.get("MILK",0), "FERT": pr.get("FERTILIZER",0), "WHEAT": pr.get("WHEAT",0), "MELON": pr.get("MELON",0), "zero": r["zero"]}), flush=True)
