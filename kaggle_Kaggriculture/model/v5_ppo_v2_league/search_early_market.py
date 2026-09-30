"""Screen a few mechanics-generated opening market variants.

The variants preserve the V1 worker route and total hire budget; they only
move or replace one early market order.  No public Replay action is copied.
"""
from __future__ import annotations

import argparse, json
from pathlib import Path
import numpy as np
import base_agent
from train_ppo import _fixed_opponent


def _candidate(name):
    route = [dict(x, hands=[list(a) for a in x.get("hands", [])], market=[list(a) for a in x.get("market", [])])
             for x in base_agent._LOW_ROUTE_ACTIONS]
    if name == "cow_early":
        route[72]["market"] = [["SELL", "FERTILIZER", 4], ["BUY_ANIMAL", "COW", 1], ["HIRE"], ["HIRE"], ["HIRE"], ["HIRE"]]
        route[73]["market"] = [["BUY_SEED", "CARROT", 1]]
    elif name == "cow_delayed":
        route[73]["market"] = [["BUY_SEED", "CARROT", 1]]
        route[74]["market"] = [["BUY_ANIMAL", "COW", 1]]
    elif name == "tomato_seed":
        route[73]["market"] = [["BUY_ANIMAL", "COW", 1], ["BUY_SEED", "TOMATO", 1]]
    elif name == "strawberry_seed":
        route[73]["market"] = [["BUY_ANIMAL", "COW", 1], ["BUY_SEED", "STRAWBERRY", 1]]
    else:
        raise ValueError(name)
    def agent(obs):
        base_agent._ACTIONS = route
        return base_agent._CORE_AGENT(obs)
    return agent


def _play(seed, seat, candidate, opponent_name):
    from kaggle_environments import make
    opponent = _fixed_opponent(opponent_name)
    env = make("kaggriculture", configuration={"seed": int(seed)}, debug=False); env.reset(2)
    for step in range(719):
        env.state[0].observation.step = step; env.state[1].observation.step = step
        own = candidate(env.state[seat].observation); other = opponent(env.state[1-seat].observation)
        env.step([own, other] if seat == 0 else [other, own])
    rewards = [float(s.reward or 0) for s in env.state]; own, other = rewards[seat], rewards[1-seat]
    return {"score": 1.0 if own > other else 0.0 if own < other else .5, "margin": own-other,
            "status": [str(s.status) for s in env.state]}


def run(seeds, opponents, names, output):
    rows=[]
    for name in names:
        cand=_candidate(name)
        for opp in opponents:
            for seed in seeds:
                for seat in (0,1):
                    b=_play(seed,seat,base_agent.agent,opp); c=_play(seed,seat,cand,opp)
                    rows.append({"name":name,"opponent":opp,"seed":seed,"seat":seat,"baseline":b,"candidate":c,
                                 "score_uplift":c["score"]-b["score"],"margin_uplift":c["margin"]-b["margin"]})
    summaries=[]
    for name in names:
        ss=[r for r in rows if r["name"]==name]
        summaries.append({"name":name,"games":len(ss),"baseline_score":float(np.mean([r["baseline"]["score"] for r in ss])),
                          "candidate_score":float(np.mean([r["candidate"]["score"] for r in ss])),
                          "mean_margin_uplift":float(np.mean([r["margin_uplift"] for r in ss])),
                          "errors":sum(r["baseline"]["status"]!=["DONE","DONE"] or r["candidate"]["status"]!=["DONE","DONE"] for r in ss)})
    Path(output).write_text(json.dumps({"schema":"kaggriculture-ppo-v2-early-market-1","summaries":summaries,"rows":rows},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return summaries


if __name__ == "__main__":
    p=argparse.ArgumentParser(); p.add_argument("--seed-start",type=int,default=99300000); p.add_argument("--seeds",type=int,default=2); p.add_argument("--opponents",nargs="+",default=["v1","v2","v3","starter"]); p.add_argument("--names",nargs="+",default=["cow_early","cow_delayed","tomato_seed","strawberry_seed"]); p.add_argument("--output",type=Path,default=Path("early_market_search_2.json")); a=p.parse_args()
    print(json.dumps(run([a.seed_start+7919*i for i in range(a.seeds)],a.opponents,a.names,a.output),ensure_ascii=False,indent=2))
