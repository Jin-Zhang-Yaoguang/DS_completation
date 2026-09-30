"""End-to-end paired evaluation of a fixed animal-sale residual."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

import base_agent
import main


class MultiDayResidual:
    def __init__(self, days=(10, 17, 24), head=3, value=0):
        self.days = set(int(day) for day in days)
        self.head = int(head)
        self.value = int(value)
        self.macro = main.DEFAULT_MACRO.copy()

    def __call__(self, obs):
        step = int(obs.get("step", 0) or 0)
        day = int(obs.get("day", step // 24) or 0)
        hour = int(obs.get("hour", step % 24) or 0)
        if step == 0:
            self.macro = main.DEFAULT_MACRO.copy()
        if hour == 0:
            self.macro = main.DEFAULT_MACRO.copy()
            if day in self.days:
                self.macro[self.head] = self.value
        return main.apply_macro(obs, base_agent.agent(obs), self.macro, step)


def _play(seed, seat, candidate, opponent_name="v3"):
    from kaggle_environments import make
    from train_ppo import _fixed_opponent

    opponent = _fixed_opponent(opponent_name)
    env = make("kaggriculture", configuration={"seed": int(seed)}, debug=False)
    env.reset(2)
    for step in range(719):
        env.state[0].observation.step = step
        env.state[1].observation.step = step
        own = candidate(env.state[seat].observation)
        other = opponent(env.state[1 - seat].observation)
        env.step([own, other] if seat == 0 else [other, own])
    rewards = np.asarray([float(state.reward or 0.0) for state in env.state], dtype=np.float64)
    own, other = rewards[seat], rewards[1 - seat]
    return {"own": own, "other": other, "margin": own - other,
            "score": 1.0 if own > other else 0.0 if own < other else 0.5,
            "status": [str(state.status) for state in env.state]}


def run(seeds, output, days=(10, 17, 24), head=3, value=0, opponent="v3"):
    rows = []
    for seed in seeds:
        for seat in (0, 1):
            baseline = _play(seed, seat, base_agent.agent, opponent)
            candidate = _play(seed, seat, MultiDayResidual(days=days, head=head, value=value), opponent)
            rows.append({"seed": int(seed), "seat": seat, "baseline": baseline, "candidate": candidate,
                         "score_uplift": candidate["score"] - baseline["score"],
                         "margin_uplift": candidate["margin"] - baseline["margin"]})
    score_uplift = np.asarray([row["score_uplift"] for row in rows], dtype=np.float64)
    margin_uplift = np.asarray([row["margin_uplift"] for row in rows], dtype=np.float64)
    rng = np.random.default_rng(20260819)
    draws = score_uplift[rng.integers(0, len(score_uplift), size=(5000, len(score_uplift)))].mean(axis=1)
    result = {
        "schema": "kaggriculture-ppo-v2-residual-end-to-end-1",
        "seeds": len(seeds), "games": len(rows), "opponent": opponent,
        "residual": {"head": int(head), "value": int(value), "days": [int(day) for day in days]},
        "baseline_score_rate": float(np.mean([row["baseline"]["score"] for row in rows])),
        "candidate_score_rate": float(np.mean([row["candidate"]["score"] for row in rows])),
        "score_uplift_mean": float(score_uplift.mean()),
        "score_uplift_bootstrap_ci95": [float(np.quantile(draws, .025)), float(np.quantile(draws, .975))],
        "margin_uplift_mean": float(margin_uplift.mean()),
        "errors": sum(row["baseline"]["status"] != ["DONE", "DONE"] or row["candidate"]["status"] != ["DONE", "DONE"] for row in rows),
    }
    Path(output).write_text(json.dumps({"result": result, "rows": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-start", type=int, default=98500000)
    parser.add_argument("--seeds", type=int, default=32)
    parser.add_argument("--output", type=Path, default=Path("residual_eval_v3.json"))
    parser.add_argument("--days", type=int, nargs="+", default=[10, 17, 24])
    parser.add_argument("--head", type=int, default=3)
    parser.add_argument("--value", type=int, default=0)
    parser.add_argument("--opponent", default="v3")
    args = parser.parse_args()
    print(json.dumps(run([args.seed_start + 7919 * i for i in range(args.seeds)], args.output,
                         days=args.days, head=args.head, value=args.value, opponent=args.opponent), ensure_ascii=False, indent=2))
