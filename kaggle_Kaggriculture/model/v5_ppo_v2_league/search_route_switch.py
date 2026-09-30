"""Search mechanically generated season-route switches, not Replay templates.

Each candidate starts with the V1 low route and switches once to the V1 high
route (or the reverse) at a fixed later step.  This expands the deployable
route action space without copying champion actions or changing the low-level
executor.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

import base_agent
from train_ppo import _fixed_opponent


def _candidate(direction: str, switch_step: int):
    def agent(obs):
        step = int(obs.get("step", 0) or 0)
        if step == 0:
            base_agent._ACTIONS = base_agent._LOW_ROUTE_ACTIONS
        if direction == "low_to_high":
            base_agent._ACTIONS = (base_agent._HIGH_ROUTE_ACTIONS
                                   if step >= switch_step else base_agent._LOW_ROUTE_ACTIONS)
        else:
            base_agent._ACTIONS = (base_agent._LOW_ROUTE_ACTIONS
                                   if step >= switch_step else base_agent._HIGH_ROUTE_ACTIONS)
        return base_agent._CORE_AGENT(obs)
    return agent


def _play(seed, seat, candidate, opponent_name):
    from kaggle_environments import make
    opponent = _fixed_opponent(opponent_name)
    env = make("kaggriculture", configuration={"seed": int(seed)}, debug=False)
    env.reset(2)
    for step in range(719):
        env.state[0].observation.step = step
        env.state[1].observation.step = step
        own = candidate(env.state[seat].observation)
        other = opponent(env.state[1 - seat].observation)
        env.step([own, other] if seat == 0 else [other, own])
    rewards = [float(state.reward or 0.0) for state in env.state]
    own, other = rewards[seat], rewards[1 - seat]
    return {"score": 1.0 if own > other else 0.0 if own < other else .5,
            "margin": own - other,
            "status": [str(state.status) for state in env.state]}


def run(seeds, opponents, switch_steps, output):
    rows = []
    for direction in ("low_to_high", "high_to_low"):
        for switch_step in switch_steps:
            candidate = _candidate(direction, int(switch_step))
            for opponent in opponents:
                for seed in seeds:
                    for seat in (0, 1):
                        baseline = _play(seed, seat, base_agent.agent, opponent)
                        cand = _play(seed, seat, candidate, opponent)
                        rows.append({"direction": direction, "switch_step": int(switch_step),
                                     "opponent": opponent, "seed": int(seed), "seat": seat,
                                     "baseline": baseline, "candidate": cand,
                                     "score_uplift": cand["score"] - baseline["score"],
                                     "margin_uplift": cand["margin"] - baseline["margin"]})
    summaries = []
    for direction in ("low_to_high", "high_to_low"):
        for switch_step in switch_steps:
            subset = [r for r in rows if r["direction"] == direction and r["switch_step"] == switch_step]
            summaries.append({"direction": direction, "switch_step": int(switch_step),
                              "games": len(subset),
                              "baseline_score": float(np.mean([r["baseline"]["score"] for r in subset])),
                              "candidate_score": float(np.mean([r["candidate"]["score"] for r in subset])),
                              "mean_margin_uplift": float(np.mean([r["margin_uplift"] for r in subset])),
                              "errors": sum(r["baseline"]["status"] != ["DONE", "DONE"] or
                                             r["candidate"]["status"] != ["DONE", "DONE"] for r in subset)})
    result = {"schema": "kaggriculture-ppo-v2-route-switch-1", "seeds": len(seeds),
              "opponents": list(opponents), "switch_steps": [int(x) for x in switch_steps],
              "summaries": summaries, "rows": rows}
    Path(output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-start", type=int, default=99200000)
    parser.add_argument("--seeds", type=int, default=8)
    parser.add_argument("--opponents", nargs="+", default=["v1", "v2", "v3", "starter"])
    parser.add_argument("--switch-steps", nargs="+", type=int, default=[168, 240, 312, 384, 480, 576])
    parser.add_argument("--output", type=Path, default=Path("route_switch_search_8.json"))
    args = parser.parse_args()
    seeds = [args.seed_start + 7919 * i for i in range(args.seeds)]
    print(json.dumps(run(seeds, args.opponents, args.switch_steps, args.output), ensure_ascii=False, indent=2))
