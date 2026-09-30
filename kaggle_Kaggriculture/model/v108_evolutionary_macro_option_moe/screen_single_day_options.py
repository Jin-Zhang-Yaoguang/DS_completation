#!/usr/bin/env python3
from __future__ import annotations

import concurrent.futures
from functools import lru_cache
import importlib.util
import json
import os
from pathlib import Path
import statistics
import sys

HERE=Path(__file__).resolve().parent
MODEL=HERE.parent
PROJECT=MODEL.parent
REPLAYS=PROJECT/"model_data/v17_rc1_online_2026-08-27/top5_leaderboard_replays"
CPPSIM=MODEL/"community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
sys.path.insert(0,str(sorted((CPPSIM/"build").glob("lib.*"))[-1]))
import kagsim  # type: ignore

BASE=100439801
EXPERTS=(100501596,100398798,100414724,100410172,100458412,100446711,100465032)
DAYS=tuple(range(9,29))
MODES=("base",)+tuple(f"d{day}_e{expert}" for day in DAYS for expert in EXPERTS)
SEEDS=tuple(range(108101,108109))
OPPONENTS={"v20":MODEL/"v20_demand_timing_moe/main.py","v76":MODEL/"v76_adjacent_safe_buy_lead/main.py"}


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);assert spec and spec.loader;spec.loader.exec_module(module);return module


@lru_cache(maxsize=None)
def route(episode):
    replay=json.loads((REPLAYS/f"episode-{episode}-replay.json").read_text());seat=replay["info"]["TeamNames"].index("lucaskna");return tuple(step[seat].get("action") or {} for step in replay["steps"][1:720])


def action_for(mode,step):
    if mode=="base":return route(BASE)[step]
    left,right=mode.split("_e");day=int(left[1:]);expert=int(right)
    return route(expert)[step] if day*24<=step<min(719,(day+1)*24) else route(BASE)[step]


def normalize(action,obs):
    seat=int(obs.get("player",0) or 0);n=len(obs["farms"][seat].get("hands",[]) or []);hands=[list(x or ["PASS"]) for x in action.get("hands",[])];hands.extend([["PASS"] for _ in range(max(0,n-len(hands)))])
    return {"farmer":list(action.get("farmer") or ["PASS"]),"hands":hands[:n],"market":[list(x) for x in (action.get("market",[]) or [])[:10]]}


def play(task):
    mode,family,seed,seat=task;rival=load(OPPONENTS[family],f"v108_{mode}_{family}_{seed}_{seat}_{os.getpid()}");game=kagsim.Game(seed)
    while not game.done:
        pair=[None,None];pair[seat]=normalize(action_for(mode,game.step_count),game.observe(seat));pair[1-seat]=rival.agent(game.observe(1-seat));game.step(pair[0],pair[1])
    own,opponent=float(game.reward(seat)),float(game.reward(1-seat));margin=own-opponent
    return {"mode":mode,"family":family,"seed":seed,"seat":seat,"margin":margin,"score":1 if margin>0 else .5 if margin==0 else 0,"catastrophic":margin < -10000}


def main():
    tasks=[(mode,family,seed,seat) for mode in MODES for family in OPPONENTS for seed in SEEDS for seat in (0,1)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=min(16,os.cpu_count() or 1)) as pool:rows=list(pool.map(play,tasks,chunksize=2))
    index={(r["mode"],r["family"],r["seed"],r["seat"]):r for r in rows};base=[r for r in rows if r["mode"]=="base"];base_score=statistics.mean(r["score"] for r in base);base_cat=statistics.mean(r["catastrophic"] for r in base);stats={}
    for mode in MODES[1:]:
        deltas=[];margins=[];current=[]
        for family in OPPONENTS:
            for seed in SEEDS:
                for seat in (0,1):
                    a=index[(mode,family,seed,seat)];b=index[("base",family,seed,seat)];current.append(a);deltas.append(a["score"]-b["score"]);margins.append(a["margin"]-b["margin"])
        stats[mode]={"score":statistics.mean(r["score"] for r in current),"uplift_pp":100*statistics.mean(deltas),"positive_zero_negative":[sum(x>0 for x in deltas),sum(x==0 for x in deltas),sum(x<0 for x in deltas)],"mean_margin_delta":statistics.mean(margins),"catastrophic_rate":statistics.mean(r["catastrophic"] for r in current),"catastrophic_delta_pp":100*(statistics.mean(r["catastrophic"] for r in current)-base_cat)}
    qualified=[mode for mode,s in stats.items() if s["uplift_pp"]>0 and s["positive_zero_negative"][0]>s["positive_zero_negative"][2] and s["catastrophic_delta_pp"]<=1]
    ranked=sorted(stats,key=lambda mode:(stats[mode]["uplift_pp"],-stats[mode]["catastrophic_delta_pp"],stats[mode]["mean_margin_delta"]),reverse=True)
    payload={"schema":"kaggriculture-v108-single-day-option-screen-v1","status":"PASS_OPTION_SOURCE_QUALIFICATION" if qualified else "REJECT_OPTION_SOURCE_QUALIFICATION","strategy_proof":False,"official_evaluation_sources_consumed":0,"synthetic_seed_range":[min(SEEDS),max(SEEDS)],"games":len(rows),"base_score":base_score,"base_catastrophic_rate":base_cat,"qualified":qualified,"top20":[{"mode":mode,**stats[mode]} for mode in ranked[:20]],"stats":stats,"rows":rows}
    (HERE/"single_day_option_screen.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n");print(json.dumps({k:v for k,v in payload.items() if k not in {"stats","rows"}},ensure_ascii=False,indent=2))


if __name__=="__main__":main()
