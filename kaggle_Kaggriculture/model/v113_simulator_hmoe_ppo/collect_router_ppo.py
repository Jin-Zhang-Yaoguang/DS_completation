"""Collect contextual-bandit rollouts for V113's frozen product experts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
import time

from kaggle_environments import make
import numpy as np

from collect_rollouts import agent_observations, call_opponent, resolve_opponent
from policy_factorized import FactorizedV113Policy


def sample_expert(logits: np.ndarray, temperature: float, rng: np.random.Generator) -> tuple[int, float]:
    if temperature <= 0:
        raise ValueError("temperature must be positive")
    crop_logits = np.asarray(logits[:5], dtype=np.float64) / temperature
    crop_logits -= crop_logits.max()
    probability = np.exp(crop_logits)
    probability /= probability.sum()
    expert = int(rng.choice(5, p=probability))
    return expert, float(np.log(max(1e-30, probability[expert])))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--opponent", default="builtin:starter")
    parser.add_argument("--seeds", type=int, default=16)
    parser.add_argument("--seed-start", type=int, default=1140000)
    parser.add_argument("--router-temperature", type=float, default=1.0)
    parser.add_argument("--margin-scale", type=float, default=500.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.margin_scale <= 0:
        parser.error("--margin-scale must be positive")
    started = time.time()
    rng = np.random.default_rng(args.seed_start)
    traces = []
    games = []
    for seed in range(args.seed_start, args.seed_start + args.seeds):
        for seat in (0, 1):
            policy = FactorizedV113Policy(
                args.checkpoint, coupled_product_router=True, router_period=720,
            )
            opponent = resolve_opponent(args.opponent, f"v113_router_ppo_opponent_{seed}_{seat}")
            env = make("kaggriculture", configuration={"seed": seed}, debug=False)
            env.reset(2)
            observations = agent_observations(env)
            encoded, output = policy._forward(observations[seat])
            expert, logprob = sample_expert(output["unit_router_logits"], args.router_temperature, rng)
            policy.forced_unit_expert = expert
            policy.forced_market_expert = expert
            while not env.done:
                observations = agent_observations(env)
                actions = [None, None]
                actions[seat] = policy.act(observations[seat])
                actions[1 - seat] = call_opponent(opponent, observations[1 - seat], env.configuration)
                env.step(actions)
            rewards = [float(state.reward or 0.0) for state in env.state]
            margin = rewards[seat] - rewards[1 - seat]
            outcome = 1.0 if margin > 0 else (-1.0 if margin < 0 else 0.0)
            advantage = outcome + 0.25 * float(np.tanh(margin / args.margin_scale))
            traces.append({
                **encoded, "unit_expert": np.int16(expert),
                "unit_router_logprob": np.float32(logprob),
                "advantage": np.float32(advantage), "return_target": np.float32(advantage),
            })
            game = {
                "seed": seed, "seat": seat, "expert": expert,
                "candidate_reward": rewards[seat], "opponent_reward": rewards[1 - seat],
                "margin": margin, "score": 1.0 if margin > 0 else (0.5 if margin == 0 else 0.0),
                "statuses": [str(state.status) for state in env.state],
            }
            games.append(game)
            print(json.dumps(game, ensure_ascii=False), flush=True)
    arrays = {key: np.asarray([trace[key] for trace in traces]) for key in traces[0]}
    raw_advantage = arrays["advantage"].copy()
    arrays["advantage"] = (
        arrays["advantage"] - arrays["advantage"].mean()
    ) / max(1e-6, float(arrays["advantage"].std()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".npz", dir=args.output.parent, delete=False) as sink:
        np.savez_compressed(sink, **arrays)
        temporary = Path(sink.name)
    temporary.replace(args.output)
    report = {
        "schema": "kaggriculture-v113-router-ppo-rollout-v1", "games": len(games),
        "opponent": args.opponent, "router_temperature": args.router_temperature,
        "score_rate": float(np.mean([game["score"] for game in games])),
        "mean_margin": float(np.mean([game["margin"] for game in games])),
        "mean_raw_advantage": float(np.mean(raw_advantage)),
        "expert_games": {str(i): int(sum(game["expert"] == i for game in games)) for i in range(5)},
        "expert_mean_margin": {
            str(i): float(np.mean([game["margin"] for game in games if game["expert"] == i]))
            if any(game["expert"] == i for game in games) else None for i in range(5)
        },
        "done_done": sum(game["statuses"] == ["DONE", "DONE"] for game in games),
        "elapsed_seconds": time.time() - started, "rows": games,
    }
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in (
        "games", "score_rate", "mean_margin", "expert_games", "expert_mean_margin", "done_done", "elapsed_seconds"
    )}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
