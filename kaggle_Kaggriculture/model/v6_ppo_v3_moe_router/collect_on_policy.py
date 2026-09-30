"""Collect D3 trajectories from the exact stochastic MoVE Router policy.

This is intentionally gated by the caller: it must only be used after the
deterministic Router has passed G1.  It records sampled actions, legal masks,
old log probabilities, values and action closure so PPO never optimises a
different policy from the one it will deploy deterministically.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path

import numpy as np

from action_compiler import ActionCompiler
from catalog import Catalog
from features import encode_observation, get, potential, update_history
from router_numpy import NumpyRouter
from runtime import set_step_for_both_seats


HERE = Path(__file__).resolve().parent
V1_SOURCE = HERE.parent / "v1_adaptive_market" / "main.py"


def _load_v1(name):
    spec = importlib.util.spec_from_file_location(name, V1_SOURCE)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _sample(logits, mask, rng):
    mask = np.asarray(mask, dtype=bool)
    scores = np.where(mask, np.asarray(logits, dtype=np.float64), -np.inf)
    if not np.any(np.isfinite(scores)):
        raise ValueError("empty action mask")
    scores -= np.max(scores[np.isfinite(scores)])
    p = np.exp(np.where(np.isfinite(scores), scores, -1e9))
    p /= p.sum()
    action = int(rng.choice(len(p), p=p))
    return action, float(math.log(max(1e-12, p[action])))


class StochasticRouterAgent:
    def __init__(self, weights: Path, rng: np.random.Generator):
        self.router = NumpyRouter(weights)
        self.rng = rng
        self.catalog = Catalog("ppo_v3_rollout_%s" % int(rng.integers(1_000_000_000)))
        self.compiler = ActionCompiler()
        self.history = {}
        self.previous = (0, 0)
        self.production_id = "E_V1"
        self.market_id = "M_NONE"
        self.rows = []

    def __call__(self, obs):
        step = int(get(obs, "step", 0) or 0)
        day = int(get(obs, "day", step // 24) or 0)
        hour = int(get(obs, "hour", step % 24) or 0)
        proposals = {name: self.catalog.production_proposal(name, obs) for name in self.catalog.production_names}
        baseline = proposals["E_V1"]
        if not baseline.eligible or baseline.plan is None:
            raise RuntimeError("baseline unavailable")
        if hour == 0:
            features = encode_observation(obs, self.history, self.previous)
            p_logits, m_logits, value = self.router.predict(features)
            p_mask = np.asarray([bool(proposals[name].eligible and proposals[name].plan is not None) for name in self.catalog.production_names])
            # Only the day-3 commitment is an active production decision; on
            # all other days the selected complete plan remains fixed.
            if step == 72:
                production_action, p_lp = _sample(p_logits, p_mask, self.rng)
                self.production_id = self.catalog.production_names[production_action]
            else:
                production_action = self.catalog.production_names.index(self.production_id)
                p_mask = np.zeros_like(p_mask)
                p_mask[production_action] = True
                p_lp = 0.0
            selected = proposals[self.production_id]
            market_mask = np.zeros(len(self.catalog.market_names), dtype=bool)
            market_mask[0] = True
            market_options = [(None, None)]
            for name in self.catalog.market_names[1:]:
                expert, proposal = self.catalog.market_proposal(name, obs, selected)
                market_options.append((expert, proposal))
                market_mask[len(market_options) - 1] = bool(proposal is not None and proposal.eligible)
            if day >= 3:
                market_action, m_lp = _sample(m_logits, market_mask, self.rng)
            else:
                market_action, m_lp = 0, 0.0
                market_mask[:] = False
                market_mask[0] = True
            self.market_id = self.catalog.market_names[market_action]
            self.rows.append({
                "features": features, "production_actions": production_action, "market_actions": market_action,
                "production_mask": p_mask, "market_mask": market_mask, "old_logprob": p_lp + m_lp,
                "value": value, "potential": potential(obs), "day": day,
            })
            self.previous = (production_action, market_action)
            self.history = update_history(obs)
        selected = proposals.get(self.production_id, baseline)
        market_expert, market_proposal = self.catalog.market_proposal(self.market_id, obs, selected)
        result = self.compiler.compile(obs, baseline_action=baseline.plan.action, production=selected, market_expert=market_expert, market=market_proposal)
        if hour == 0:
            self.rows[-1]["effective_action_change"] = result.effective_intervention
            self.rows[-1]["selected_market"] = self.market_id
        return result.action


def _episode(seed, seat, weights):
    from kaggle_environments import make
    agent = StochasticRouterAgent(weights, np.random.default_rng(int(seed) * 3 + int(seat)))
    opponent = _load_v1("ppo_v3_d3_v1_%s_%s" % (seed, seat))
    env = make("kaggriculture", configuration={"seed": int(seed)}, debug=False)
    env.reset(2)
    for step in range(719):
        set_step_for_both_seats(env, step)
        own = agent(env.state[seat].observation)
        other = opponent.agent(env.state[1 - seat].observation)
        env.step([own, other] if seat == 0 else [other, own])
    if [str(state.status) for state in env.state] != ["DONE", "DONE"]:
        raise RuntimeError("episode did not finish")
    rewards = [float(state.reward or 0.0) for state in env.state]
    margin = rewards[seat] - rewards[1 - seat]
    terminal = (1.0 if margin > 0 else -1.0 if margin < 0 else 0.0) + 0.02 * math.tanh(margin / 25000.0)
    rows = agent.rows
    for index, row in enumerate(rows):
        if index + 1 < len(rows):
            reward = 0.995 * float(rows[index + 1]["potential"]) - float(row["potential"])
        else:
            reward = terminal - float(row["potential"])
        row["reward"] = reward
        row["seed"] = int(seed)
        row["seat"] = int(seat)
        row["margin"] = margin
    # GAE at the daily macro scale.
    carry = 0.0
    next_value = 0.0
    for row in reversed(rows):
        delta = float(row["reward"]) + 0.995 * next_value - float(row["value"])
        carry = delta + 0.995 * 0.95 * carry
        row["advantages"] = carry
        row["returns"] = carry + float(row["value"])
        next_value = float(row["value"])
    return rows


def collect(weights: Path, seeds, output: Path):
    all_rows = []
    for seed in seeds:
        for seat in (0, 1):
            all_rows.extend(_episode(seed, seat, weights))
    if not all_rows:
        raise RuntimeError("empty D3 rollout")
    router = NumpyRouter(weights)
    arrays = {
        "features": np.stack([row["features"] for row in all_rows]),
        "production_actions": np.asarray([row["production_actions"] for row in all_rows], dtype=np.int32),
        "market_actions": np.asarray([row["market_actions"] for row in all_rows], dtype=np.int32),
        "production_mask": np.stack([row["production_mask"] for row in all_rows]),
        "market_mask": np.stack([row["market_mask"] for row in all_rows]),
        "old_logprob": np.asarray([row["old_logprob"] for row in all_rows], dtype=np.float32),
        "advantages": np.asarray([row["advantages"] for row in all_rows], dtype=np.float32),
        "returns": np.asarray([row["returns"] for row in all_rows], dtype=np.float32),
        "effective_action_change": np.asarray([row["effective_action_change"] for row in all_rows], dtype=bool),
        "seed": np.asarray([row["seed"] for row in all_rows], dtype=np.int64),
        "seat": np.asarray([row["seat"] for row in all_rows], dtype=np.int8),
        "production_names": np.asarray(router.production_names), "market_names": np.asarray(router.market_names),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output, **arrays)
    report = {"schema": "kaggriculture-ppo-v3-d3-1", "rows": len(all_rows), "seeds": len(seeds), "effective_action_change_rate": float(np.mean(arrays["effective_action_change"])), "output": str(output)}
    output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=HERE / "data" / "d3_on_policy_pilot.npz")
    parser.add_argument("--seed-start", type=int, default=98200000)
    parser.add_argument("--seeds", type=int, default=8)
    args = parser.parse_args()
    seeds = [int(args.seed_start) + 7919 * index for index in range(int(args.seeds))]
    print(json.dumps(collect(args.weights, seeds, args.output), ensure_ascii=False, indent=2))
