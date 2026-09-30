"""Generate deployable route-choice labels from paired low/high games.

This is a counterfactual pilot, not a replacement for the full BC corpus. For
each seed/seat/opponent, both existing V1 production routes are played from
the same initial environment seed. The route with the larger terminal margin
becomes the day-7 route label. The observation sequence is taken from the low
route run up to the route decision, so the label cannot depend on post-choice
state. Ties default to low and are retained with an explicit tie flag.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

import base_agent
import main


def _copy_action(action):
    return {
        "farmer": list((action or {}).get("farmer") or ["PASS"]),
        "hands": [list(x or ["PASS"]) for x in (action or {}).get("hands", [])],
        "market": [list(x or []) for x in (action or {}).get("market", [])],
    }


def _route_agent(route):
    actions = base_agent._HIGH_ROUTE_ACTIONS if int(route) else base_agent._LOW_ROUTE_ACTIONS

    def agent(obs):
        base_agent._ACTIONS = actions
        return _copy_action(base_agent._CORE_AGENT(obs))

    return agent


def _play(seed, seat, route, opponent_name):
    from kaggle_environments import make
    from train_ppo import _fixed_opponent

    candidate = _route_agent(route)
    opponent = _fixed_opponent(opponent_name)
    env = make("kaggriculture", configuration={"seed": int(seed)}, debug=False)
    env.reset(2)
    history = {}
    macro = main.DEFAULT_MACRO.copy()
    features, actions, masks, potentials = [], [], [], []
    for step in range(719):
        env.state[0].observation.step = step
        env.state[1].observation.step = step
        obs = env.state[seat].observation
        day = int(obs.get("day", step // 24) or 0)
        hour = int(obs.get("hour", step % 24) or 0)
        if hour == 0:
            features.append(main.encode_observation(obs, history, macro))
            label = main.DEFAULT_MACRO.copy()
            label[0] = int(route)
            actions.append(label)
            masks.append(day == 7)
            potentials.append(main.potential(obs))
            history = main.update_history(obs, label)
            macro = label
        own_action = candidate(obs)
        other_action = opponent(env.state[1 - seat].observation)
        env.step([own_action, other_action] if seat == 0 else [other_action, own_action])
    statuses = [str(state.status) for state in env.state]
    if statuses != ["DONE", "DONE"] or len(features) != 30:
        raise RuntimeError((seed, seat, route, statuses, len(features)))
    rewards = np.asarray([float(state.reward or 0.0) for state in env.state], dtype=np.float32)
    return {
        "features": np.asarray(features, dtype=np.float32),
        "actions": np.asarray(actions, dtype=np.int16),
        "route_mask": np.asarray(masks, dtype=np.bool_),
        "potentials": np.asarray(potentials, dtype=np.float32),
        "rewards": rewards,
        "margin": float(rewards[seat] - rewards[1 - seat]),
    }


def collect(seeds, opponents, output):
    rows = []
    ties = 0
    for seed in seeds:
        for seat in (0, 1):
            for opponent in opponents:
                low = _play(seed, seat, 0, opponent)
                high = _play(seed, seat, 1, opponent)
                if high["margin"] > low["margin"]:
                    winner = high
                    route = 1
                else:
                    winner = low
                    route = 0
                    ties += int(high["margin"] == low["margin"])
                # Only the route label is counterfactual. Keep all non-route
                # heads at their safe default and preserve the low-run state
                # features before the decision point.
                actions = low["actions"].copy()
                actions[7, 0] = route
                rows.append({
                    "seed": int(seed), "seat": int(seat), "opponent": opponent,
                    "source": "generated_route_counterfactual",
                    "strategy_family": f"route_cf/{opponent}",
                    "episode_id": f"route-cf-{seed}-{seat}-{opponent}",
                    "features": low["features"], "actions": actions,
                    "route_mask": low["route_mask"], "potentials": low["potentials"],
                    "rewards": winner["rewards"], "route_label": route,
                    "low_margin": low["margin"], "high_margin": high["margin"],
                })
                if len(rows) % 10 == 0:
                    print(json.dumps({"rows": len(rows), "route_high_rate": float(np.mean([r["route_label"] for r in rows]))}), flush=True)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output,
        features=np.stack([r["features"] for r in rows]),
        actions=np.stack([r["actions"] for r in rows]),
        route_mask=np.stack([r["route_mask"] for r in rows]),
        potentials=np.stack([r["potentials"] for r in rows]),
        seeds=np.asarray([r["seed"] for r in rows], dtype=np.int64),
        seats=np.asarray([r["seat"] for r in rows], dtype=np.int8),
        opponents=np.asarray([r["opponent"] for r in rows]),
        sources=np.asarray([r["source"] for r in rows]),
        strategy_families=np.asarray([r["strategy_family"] for r in rows]),
        episode_ids=np.asarray([r["episode_id"] for r in rows]),
        lineages=np.asarray(["v1_route_counterfactual" for _ in rows]),
        rewards=np.stack([r["rewards"] for r in rows]),
        route_labels=np.asarray([r["route_label"] for r in rows], dtype=np.int8),
        low_margins=np.asarray([r["low_margin"] for r in rows], dtype=np.float32),
        high_margins=np.asarray([r["high_margin"] for r in rows], dtype=np.float32),
    )
    report = {
        "schema": "kaggriculture-ppo-v2-route-counterfactual-1",
        "rows": len(rows), "seeds": len(seeds), "opponents": list(opponents),
        "route_high_rate": float(np.mean([r["route_label"] for r in rows])) if rows else 0.0,
        "ties": ties, "output": str(output),
        "training_policy": "pilot_only; no champion replay used",
    }
    output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-start", type=int, default=97300000)
    parser.add_argument("--seeds", type=int, default=8)
    parser.add_argument("--opponents", nargs="+", default=["v1", "v2", "v3", "starter"])
    parser.add_argument("--output", type=Path, default=Path("data/route_cf_pilot.npz"))
    args = parser.parse_args()
    seeds = [args.seed_start + 7919 * i for i in range(args.seeds)]
    print(json.dumps(collect(seeds, args.opponents, args.output), ensure_ascii=False, indent=2))
