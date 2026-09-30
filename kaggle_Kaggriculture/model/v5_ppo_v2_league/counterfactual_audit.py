"""Paired one-day market residual audit against the frozen V1 executor.

Each counterfactual replays the same seed/seat/opponent as a V1 baseline and
changes exactly one macro head for one day.  This is deliberately separate
from PPO rollouts: it measures whether an intervention has causal evidence
before allowing it into a residual policy.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

import base_agent
import main


def _copy(action):
    action = action or {}
    return {
        "farmer": list(action.get("farmer") or ["PASS"]),
        "hands": [list(x or ["PASS"]) for x in action.get("hands", [])],
        "market": [list(x or []) for x in action.get("market", [])],
    }


class OneDayResidual:
    def __init__(self, head, value, day):
        self.head = int(head)
        self.value = int(value)
        self.day = int(day)
        self.macro = main.DEFAULT_MACRO.copy()
        self.route = None

    def __call__(self, obs):
        step = int(obs.get("step", 0) or 0)
        day = int(obs.get("day", step // 24) or 0)
        hour = int(obs.get("hour", step % 24) or 0)
        if step == 0:
            self.macro = main.DEFAULT_MACRO.copy()
            self.route = None
        if hour == 0:
            self.macro = main.DEFAULT_MACRO.copy()
            if day == self.day:
                self.macro[self.head] = self.value
        raw = base_agent.agent(obs)
        return main.apply_macro(obs, raw, self.macro, step)


def _opponent(name):
    from kaggle_environments import make  # noqa: F401, import check for clean env
    from kaggle_environments.envs.kaggriculture import kaggriculture as kg
    if name in {"v1", "v2", "v3", "v4"}:
        from train_ppo import _fixed_opponent
        return _fixed_opponent(name)
    if name == "starter":
        return kg.starter_agent
    if name == "random":
        return kg.random_agent
    if name == "forced_low":
        def low(obs):
            base_agent._ACTIONS = base_agent._LOW_ROUTE_ACTIONS
            return base_agent._CORE_AGENT(obs)
        return low
    if name == "forced_high":
        def high(obs):
            base_agent._ACTIONS = base_agent._HIGH_ROUTE_ACTIONS
            return base_agent._CORE_AGENT(obs)
        return high
    raise ValueError(name)


def _play(seed, seat, opponent_name, residual=None):
    from kaggle_environments import make
    env = make("kaggriculture", configuration={"seed": int(seed)}, debug=False)
    env.reset(2)
    candidate = residual or OneDayResidual(1, 1, -1)
    opponent = _opponent(opponent_name)
    for step in range(719):
        env.state[0].observation.step = step
        env.state[1].observation.step = step
        actions = [None, None]
        actions[seat] = candidate(env.state[seat].observation)
        actions[1 - seat] = opponent(env.state[1 - seat].observation)
        env.step(actions)
    rewards = [float(state.reward or 0.0) for state in env.state]
    return rewards[seat], rewards[1 - seat], [str(state.status) for state in env.state]


def run(seed_start, seeds, days, opponents, output):
    rows = []
    errors = 0
    # We evaluate only heads that can alter a frozen V1 market order.  Head 0
    # is the route expert and is intentionally excluded from this residual audit.
    alternatives = {1: (0, 2), 2: (0, 2), 3: (0, 2), 4: (1, 2), 5: (1, 2)}
    for index in range(int(seeds)):
        seed = int(seed_start) + index * 101
        for seat in (0, 1):
            for opponent_name in opponents:
                baseline_own, baseline_other, baseline_status = _play(seed, seat, opponent_name, None)
                if baseline_status != ["DONE", "DONE"]:
                    errors += 1
                    continue
                for day in days:
                    for head, values in alternatives.items():
                        if not bool(main.macro_action_mask(day, 0)[head]):
                            continue
                        for value in values:
                            try:
                                own, other, status = _play(seed, seat, opponent_name, OneDayResidual(head, value, day))
                            except Exception as exc:
                                errors += 1
                                rows.append({"seed": seed, "seat": seat, "opponent": opponent_name, "day": day, "head": head, "value": value, "error": repr(exc)})
                                continue
                            if status != ["DONE", "DONE"]:
                                errors += 1
                            rows.append({
                                "seed": seed, "seat": seat, "opponent": opponent_name,
                                "day": int(day), "head": int(head), "value": int(value),
                                "baseline_own": baseline_own, "baseline_other": baseline_other,
                                "own": own, "other": other,
                                "uplift": own - baseline_own,
                                "margin_uplift": (own - other) - (baseline_own - baseline_other),
                                "status": status,
                            })
    grouped = {}
    for row in rows:
        if "uplift" not in row:
            continue
        key = f"head{row['head']}_value{row['value']}"
        grouped.setdefault(key, []).append(float(row["uplift"]))
    summary = {}
    for key, values in grouped.items():
        arr = np.asarray(values, dtype=np.float64)
        # Paired bootstrap percentile interval; deterministic seed for audit.
        rng = np.random.default_rng(20260818 + sum(map(ord, key)))
        draws = arr[rng.integers(0, len(arr), size=(2000, len(arr)))].mean(axis=1)
        summary[key] = {"n": int(len(arr)), "mean_uplift": float(arr.mean()), "positive_rate": float(np.mean(arr > 0)), "bootstrap_ci95": [float(np.quantile(draws, .025)), float(np.quantile(draws, .975))]}
    result = {
        "schema": "kaggriculture-ppo-v2-counterfactual-audit-1",
        "baseline": "v1",
        "seed_start": int(seed_start), "seeds": int(seeds), "days": [int(x) for x in days],
        "opponents": list(opponents), "rows": len(rows), "errors": errors,
        "summary": summary,
        "gates": {"zero_errors": errors == 0, "positive_intervention_ci": any(v["bootstrap_ci95"][0] > 0 for v in summary.values())},
    }
    Path(output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-start", type=int, default=96000000)
    parser.add_argument("--seeds", type=int, default=4)
    parser.add_argument("--days", type=int, nargs="+", default=[10, 17, 24])
    parser.add_argument("--opponents", nargs="+", default=["starter", "random", "forced_low", "forced_high"])
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "counterfactual_audit_report.json")
    args = parser.parse_args()
    print(json.dumps(run(args.seed_start, args.seeds, args.days, args.opponents, args.output), ensure_ascii=False, indent=2))
