#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
MODEL=HERE.parent
CPPSIM=MODEL/"community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
sys.path.insert(0,str(sorted((CPPSIM/"build").glob("lib.*"))[-1]))
import kagsim  # type: ignore

SHOPS=("BAKERY","BRUNCH_SPOT","FARMERS_MARKET","ICE_CREAM_SHOP","PET_CAFE","PIZZA_SHOP","SMOOTHIE_SHOP","YARN_STORE")
PASS={"farmer":["PASS"],"hands":[],"market":[]}


def weed_bits(obs):
    bits=[]
    for farm in obs.get("farms",[]) or []:
        rows=farm.get("tiles",[]) or []
        for y in range(10):
            for x in range(10):
                tile=rows[y][x] if y<len(rows) and x<len(rows[y]) else "LOCKED"
                bits.append(int(isinstance(tile,dict) and tile.get("kind")=="WEED"))
    return bits


def one(seed):
    game=kagsim.Game(seed);features=None;target=None
    while not game.done and game.step_count<=288:
        if game.step_count==216:
            obs=game.observe(0);shops=list(obs["town"]["unlocked_shops"]);features=[SHOPS.index(shop) for shop in shops[:3]]+weed_bits(obs)
        if game.step_count==288:
            shops=list(game.observe(0)["town"]["unlocked_shops"]);target=SHOPS.index(shops[3]);break
        game.step(PASS,PASS)
    return {"seed":seed,"x":features,"y":target}


def main():
    rows=[one(seed) for seed in range(1070001,1074097)]
    payload={"schema":"kaggriculture-v107-rng-probe-data-v1","strategy_proof":False,"official_evaluation_sources_consumed":0,"seed_range":[1070001,1074096],"train_seeds":3072,"holdout_seeds":1024,"rows":rows}
    (HERE/"rng_probe_data.json").write_text(json.dumps(payload,separators=(",",":"))+"\n")
    print(json.dumps({k:v for k,v in payload.items() if k!="rows"},indent=2))


if __name__=="__main__":main()
