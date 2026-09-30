#!/usr/bin/env python3
"""Frozen V29 champion tournament across V19/V20/V21/V27."""

from __future__ import annotations

import concurrent.futures
import json
import math
import os
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent; PROJECT = HERE.parents[1]; MODEL = PROJECT / "model"
V19 = MODEL / "v19_hierarchical_moe"; V21 = MODEL / "v21_top_meta_moe"
CPPSIM = MODEL / "community_research" / "2026-08-26" / "live_cli" / "external_repos" / "kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
sys.path[:0] = [str(PROJECT.parent), str(V21), str(V19), str(FACTORY), str(sorted((CPPSIM / "build").glob("lib.*"))[-1])]

import kagsim  # type: ignore
from agent_factory import Registry, create_agent  # type: ignore
from hierarchical_policy import make_agent
from top_route_panel import make_compatible_shop_router, make_lucaskna_hybrid


OPPONENTS = {
    "adaptive_market": MODEL / "v1_adaptive_market" / "main.py", "bc_ppo": MODEL / "v3_bc_ppo_hybrid" / "main.py",
    "anti_mirror": MODEL / "v9_anti_mirror" / "main.py", "incumbent_r002": MODEL / "v12_incumbent_r002" / "main.py",
    "ppo_topdays": MODEL / "v5_ppo_v2_league" / "v5_ppo_v2_topdays" / "main.py", "rule_hybrid": MODEL / "v5_rule_hybrid" / "main.py",
    "kawa_lead2": MODEL / "v8_kawa_lead2_slot" / "main.py", "v13c_a2": MODEL / "v13c_a2_v8_no_wool_throttle" / "main.py",
    "v16_town_drain": MODEL / "v16_s2_town_drain_challenger" / "main.py", "v17_portfolio": MODEL / "v16_gold_strategy_research" / "top_complete_portfolio" / "main.py",
    "v18_shop_moe": MODEL / "v18_shop_demand_moe" / "main.py", "v19_gold": MODEL / "v19_hierarchical_moe" / "main.py",
}


def score(margin): return 1.0 if margin > 0 else .5 if margin == 0 else 0.0
def quantile(v, p):
    v=sorted(v); x=(len(v)-1)*p; lo,hi=math.floor(x),math.ceil(x)
    return v[lo] if lo==hi else v[lo]*(hi-x)+v[hi]*(x-lo)


def policy(mode):
    if mode=="v19": return make_agent("switch_360", seller_mode="none")
    if mode=="v20": return make_agent("switch_360", seller_mode="demand_delay_25")
    if mode=="v21": return make_lucaskna_hybrid(216)
    if mode=="v27": return make_compatible_shop_router("SMOOTHIE_SHOP", "lucaskna", 100501596)
    raise ValueError(mode)


def play(candidate, opponent, seed, seat):
    agents=[None,None]; agents[seat],agents[1-seat]=candidate,opponent; game=kagsim.Game(seed)
    while not game.done:
        obs=[game.observe(0),game.observe(1)]; game.step(agents[0](obs[0]),agents[1](obs[1]))
    return float(game.reward(seat)),float(game.reward(1-seat))


def run_job(payload):
    mode,family,seed,seat=payload; registry=Registry(path=Path(__file__).resolve(),models={},raw={})
    opp=create_agent(registry,{"id":f"v29_{mode}_{family}_{seed}_{seat}_{os.getpid()}","kind":"python","path":str(OPPONENTS[family]),"entrypoint":"agent"})
    own,rival=play(policy(mode),opp,seed,seat)
    return {"mode":mode,"family":family,"seed":seed,"seat":seat,"own":own,"opp":rival,"margin":own-rival}


def summarize(rows):
    return {"games":len(rows),"wins_ties_losses":[sum(r["margin"]>0 for r in rows),sum(r["margin"]==0 for r in rows),sum(r["margin"]<0 for r in rows)],"score_rate":statistics.mean(score(r["margin"]) for r in rows),"mean_bank":statistics.mean(r["own"] for r in rows),"mean_margin":statistics.mean(r["margin"] for r in rows)}


def compare(rows,candidate,baseline):
    base={(r["family"],r["seed"],r["seat"]):r for r in rows if r["mode"]==baseline}; pairs=[]
    for r in rows:
        if r["mode"]!=candidate: continue
        b=base[(r["family"],r["seed"],r["seat"])]
        pairs.append({"family":r["family"],"seed":r["seed"],"score":score(r["margin"])-score(b["margin"]),"margin":r["margin"]-b["margin"],"own":r["own"]-b["own"]})
    by_seed=defaultdict(list)
    for r in pairs: by_seed[r["seed"]].append(r["score"])
    sd={s:statistics.mean(v) for s,v in by_seed.items()}; rng=random.Random(29001+sum(map(ord,candidate+baseline)))
    boot=[statistics.mean(sd[s] for s in rng.choices(list(sd),k=len(sd))) for _ in range(10000)]
    by_family={}
    for f in OPPONENTS:
        z=[r for r in pairs if r["family"]==f]
        by_family[f]={"score_uplift_pp":100*statistics.mean(r["score"] for r in z),"positive_zero_negative":[sum(r["score"]>0 for r in z),sum(r["score"]==0 for r in z),sum(r["score"]<0 for r in z)]}
    return {"candidate":candidate,"baseline":baseline,"cells":len(pairs),"score_uplift_pp":100*statistics.mean(r["score"] for r in pairs),"score_uplift_ci95_pp":[100*quantile(boot,.025),100*quantile(boot,.975)],"positive_zero_negative":[sum(r["score"]>0 for r in pairs),sum(r["score"]==0 for r in pairs),sum(r["score"]<0 for r in pairs)],"margin_delta_mean":statistics.mean(r["margin"] for r in pairs),"own_delta_mean":statistics.mean(r["own"] for r in pairs),"guardrail_pass":all(v["score_uplift_pp"]>=-2 for v in by_family.values()),"by_family":by_family}


def main():
    m=json.loads((HERE/"v29_champion_seeds.json").read_text()); seeds=range(m["seed_range"][0],m["seed_range"][1]+1)
    jobs=[(mode,f,s,seat) for mode in m["modes"] for f in m["opponent_families"] for s in seeds for seat in (0,1)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=max(1,os.cpu_count() or 1)) as pool: rows=list(pool.map(run_job,jobs,chunksize=4))
    absolute={mode:summarize([r for r in rows if r["mode"]==mode]) for mode in m["modes"]}
    comparisons={"v21_vs_v19":compare(rows,"v21","v19"),"v21_vs_v20":compare(rows,"v21","v20"),"v27_vs_v21":compare(rows,"v27","v21")}
    passes=(comparisons["v21_vs_v19"]["score_uplift_ci95_pp"][0]>0 and comparisons["v21_vs_v20"]["score_uplift_ci95_pp"][0]>0 and comparisons["v21_vs_v19"]["guardrail_pass"] and comparisons["v21_vs_v20"]["guardrail_pass"])
    v27_significant=comparisons["v27_vs_v21"]["score_uplift_ci95_pp"][0]>0 and comparisons["v27_vs_v21"]["guardrail_pass"]
    selected="v27" if passes and v27_significant else "v21" if passes else "NONE"
    result={"schema":"kaggriculture-v29-champion-selection-v1","status":"FROZEN_CHAMPION_TOURNAMENT","engine":str(kagsim.ENGINE_VERSION),"manifest":m,"absolute":absolute,"comparisons":comparisons,"selected":selected,"decision":"QUALIFY_SELECTED_FOR_V30" if selected!="NONE" else "NO_GOLD_CHAMPION","rows":rows}
    (HERE/"v29_champion_results.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"absolute":absolute,"comparisons":{k:{kk:vv for kk,vv in v.items() if kk!="by_family"} for k,v in comparisons.items()},"selected":selected,"decision":result["decision"]},ensure_ascii=False,indent=2)); return 0


if __name__=="__main__": raise SystemExit(main())
