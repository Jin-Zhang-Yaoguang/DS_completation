"""Evaluate a rule-generated early animal template without Replay actions.

The template only changes the market plan at steps 72 and 73: buy one cow and
reserve three hires, while retaining the frozen V1 farmer/hand executor. It
is an independent mechanics-based candidate, not a transcription of a public
Replay route.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

import base_agent


def cow_opening(obs):
    step = int(obs.get("step", 0) or 0)
    action = {
        "farmer": list((base_agent.agent(obs) or {}).get("farmer") or ["PASS"]),
        "hands": [list(x or ["PASS"]) for x in (base_agent.agent(obs) or {}).get("hands", [])],
        "market": [list(x or []) for x in (base_agent.agent(obs) or {}).get("market", [])],
    }
    # base_agent.agent is called twice above only to keep the mutation local;
    # replace with a single-call action below for deterministic state safety.
    return action


def _agent(obs):
    step = int(obs.get("step", 0) or 0)
    raw = base_agent.agent(obs)
    action = {
        "farmer": list((raw or {}).get("farmer") or ["PASS"]),
        "hands": [list(x or ["PASS"]) for x in (raw or {}).get("hands", [])],
        "market": [list(x or []) for x in (raw or {}).get("market", [])],
    }
    if step == 72:
        action["market"] = [["SELL", "FERTILIZER", 4], ["BUY_ANIMAL", "COW", 1], ["HIRE"], ["HIRE"], ["HIRE"]]
    elif step == 73:
        action["market"] = [["HIRE"], ["HIRE"], ["HIRE"]]
    return action


def _play(seed, seat, candidate, opponent_name):
    from kaggle_environments import make
    from train_ppo import _fixed_opponent
    opponent = _fixed_opponent(opponent_name)
    env = make("kaggriculture", configuration={"seed": int(seed)}, debug=False)
    env.reset(2)
    for step in range(719):
        env.state[0].observation.step = step; env.state[1].observation.step = step
        own = candidate(env.state[seat].observation); other = opponent(env.state[1-seat].observation)
        env.step([own, other] if seat == 0 else [other, own])
    rewards = [float(s.reward or 0.0) for s in env.state]
    own, other = rewards[seat], rewards[1-seat]
    return {"score": 1.0 if own > other else 0.0 if own < other else .5, "margin": own-other,
            "status": [str(s.status) for s in env.state]}


def run(seeds, opponents, output):
    rows=[]
    for opponent in opponents:
        for seed in seeds:
            for seat in (0,1):
                base=_play(seed,seat,base_agent.agent,opponent)
                cand=_play(seed,seat,_agent,opponent)
                rows.append({"opponent":opponent,"seed":seed,"seat":seat,"baseline":base,"candidate":cand,
                             "score_uplift":cand["score"]-base["score"],"margin_uplift":cand["margin"]-base["margin"]})
    result={"schema":"kaggriculture-ppo-v2-cow-opening-1","games":len(rows),"opponents":list(opponents),
            "baseline_score":float(np.mean([r["baseline"]["score"] for r in rows])),
            "candidate_score":float(np.mean([r["candidate"]["score"] for r in rows])),
            "mean_margin_uplift":float(np.mean([r["margin_uplift"] for r in rows])),
            "errors":sum(r["candidate"]["status"]!=["DONE","DONE"] or r["baseline"]["status"]!=["DONE","DONE"] for r in rows)}
    Path(output).write_text(json.dumps({"result":result,"rows":rows},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return result


if __name__ == "__main__":
    p=argparse.ArgumentParser(); p.add_argument("--seed-start",type=int,default=99100000); p.add_argument("--seeds",type=int,default=16); p.add_argument("--opponents",nargs="+",default=["v1","v2","v3","starter"]); p.add_argument("--output",type=Path,default=Path("cow_opening_eval.json")); a=p.parse_args()
    print(json.dumps(run([a.seed_start+7919*i for i in range(a.seeds)],a.opponents,a.output),ensure_ascii=False,indent=2))
