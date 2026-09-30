"""Compare PPO rollout sampling with deterministic deployment argmax.

The audit holds the environment state fixed by executing the frozen V1
executor, then asks the same NumPy policy for a stochastic training action and
the deterministic submission action on each daily observation.  It measures
whether exploration can actually reach a different deployed macro decision.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

import base_agent
import main


def _masked(policy, features, hidden, history, macro, day, rng, stochastic):
    selected, logp, value, hidden_next, logits = policy.act(
        features, hidden, stochastic=stochastic, rng=rng,
        route_enabled=(day == 7), temperature=1.0,
    )
    if day < 7:
        selected[0] = 0
    elif day > 7:
        selected[0] = int(macro[0])
    mask = main.macro_action_mask(day, selected[0])
    for head in range(len(main.HEAD_SIZES)):
        if not mask[head]:
            selected[head] = main.DEFAULT_MACRO[head]
    return selected, hidden_next


def run(weights, seeds, output):
    from kaggle_environments import make

    policy = main.NumpyPolicy(weights)
    rows = []
    total = 0
    different = 0
    for seed in seeds:
        for seat in (0, 1):
            env = make("kaggriculture", configuration={"seed": int(seed)}, debug=False)
            env.reset(2)
            hidden_d = np.zeros(main.HIDDEN_SIZE, dtype=np.float32)
            hidden_s = np.zeros(main.HIDDEN_SIZE, dtype=np.float32)
            history_d = {}
            history_s = {}
            macro_d = main.DEFAULT_MACRO.copy()
            macro_s = main.DEFAULT_MACRO.copy()
            rng = np.random.default_rng(int(seed) ^ (0x51 if seat == 0 else 0xA7))
            for step in range(719):
                env.state[0].observation.step = step
                env.state[1].observation.step = step
                obs = env.state[seat].observation
                day = int(obs.get("day", step // 24) or 0)
                hour = int(obs.get("hour", step % 24) or 0)
                if hour == 0:
                    fd = main.encode_observation(obs, history_d, macro_d)
                    fs = main.encode_observation(obs, history_s, macro_s)
                    selected_d, hidden_d = _masked(policy, fd, hidden_d, history_d, macro_d, day, rng, False)
                    selected_s, hidden_s = _masked(policy, fs, hidden_s, history_s, macro_s, day, rng, True)
                    # Keep route sticky exactly as deployment does.
                    if day == 7:
                        macro_d[0] = selected_d[0]
                        macro_s[0] = selected_s[0]
                    elif day > 7:
                        selected_d[0] = macro_d[0]
                        selected_s[0] = macro_s[0]
                    changed = not np.array_equal(selected_d, selected_s)
                    total += 1
                    different += int(changed)
                    if len(rows) < 100:
                        rows.append({"seed": int(seed), "seat": seat, "day": day, "deterministic": selected_d.tolist(), "stochastic": selected_s.tolist(), "changed": changed})
                    history_d = main.update_history(obs, selected_d)
                    history_s = main.update_history(obs, selected_s)
                    macro_d = selected_d.copy()
                    macro_s = selected_s.copy()
                own = base_agent.agent(obs)
                other_obs = env.state[1 - seat].observation
                other = base_agent.agent(other_obs)
                env.step([own, other])
    result = {
        "schema": "kaggriculture-ppo-v2-action-closure-1",
        "weights": str(weights), "seeds": len(seeds), "games": len(seeds) * 2,
        "macro_decisions": total, "stochastic_vs_deterministic_different": different,
        "difference_rate": different / max(1, total), "examples": rows,
    }
    Path(output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", type=Path, default=Path("checkpoints/full28q_s17/policy_iter_005.npz"))
    parser.add_argument("--seed-start", type=int, default=93100000)
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--output", type=Path, default=Path("action_closure_audit.json"))
    args = parser.parse_args()
    print(run(args.weights, [args.seed_start + i * 101 for i in range(args.seeds)], args.output))
