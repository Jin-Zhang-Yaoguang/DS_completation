"""Collect sequence-policy states and label every state with a frozen teacher."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
import time

from kaggle_environments import make
import numpy as np

import action_space as space
from collect_dagger import labelled_row
from collect_rollouts import agent_observations, call_opponent, resolve_opponent
from model_sequence_action import NUM_EXPERTS
from policy_sequence_action import SequenceActionV113Policy, TimedSequenceActionV113Policy


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--teacher", required=True)
    parser.add_argument("--opponent", action="append", required=True)
    parser.add_argument("--seeds", type=int, default=4)
    parser.add_argument("--seed-start", type=int, default=1184000)
    parser.add_argument("--teacher-execution-probability", type=float, default=0.5)
    parser.add_argument("--router-period", type=int, default=24)
    parser.add_argument("--scale-worker-cap", type=int)
    parser.add_argument("--forced-expert", type=int, default=5, choices=range(NUM_EXPERTS))
    parser.add_argument("--timed-sequence-action", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 0.0 <= args.teacher_execution_probability <= 1.0:
        parser.error("teacher execution probability must be in [0, 1]")

    started = time.time()
    rng = np.random.default_rng(args.seed_start)
    rows, games = [], []
    cleaned = 0
    for opponent_index, opponent_name in enumerate(args.opponent):
        for seed in range(args.seed_start, args.seed_start + args.seeds):
            for seat in (0, 1):
                suffix = f"{opponent_index}_{seed}_{seat}"
                policy_class = (
                    TimedSequenceActionV113Policy
                    if args.timed_sequence_action else SequenceActionV113Policy
                )
                candidate = policy_class(
                    args.checkpoint,
                    forced_unit_expert=args.forced_expert,
                    forced_market_expert=args.forced_expert,
                    router_period=args.router_period,
                    scale_worker_cap=args.scale_worker_cap,
                )
                teacher = resolve_opponent(args.teacher, f"v113_sequence_dagger_teacher_{suffix}")
                opponent = resolve_opponent(opponent_name, f"v113_sequence_dagger_opponent_{suffix}")
                env = make("kaggriculture", configuration={"seed": seed}, debug=False)
                env.reset(2)
                game_indices, teacher_steps = [], 0
                while not env.done:
                    observations = agent_observations(env)
                    obs = observations[seat]
                    candidate_action = candidate.act(obs)
                    teacher_action = call_opponent(teacher, obs, env.configuration)
                    row, changed = labelled_row(
                        obs, teacher_action, args.forced_expert, seed, seat
                    )
                    row["unit_expert"] = np.int16(args.forced_expert)
                    row["market_expert"] = np.int16(args.forced_expert)
                    rows.append(row)
                    game_indices.append(len(rows) - 1)
                    cleaned += int(changed)
                    use_teacher = rng.random() < args.teacher_execution_probability
                    teacher_steps += int(use_teacher)
                    actions = [None, None]
                    actions[seat] = teacher_action if use_teacher else candidate_action
                    actions[1 - seat] = call_opponent(
                        opponent, observations[1 - seat], env.configuration
                    )
                    env.step(actions)
                rewards = [float(state.reward or 0.0) for state in env.state]
                margin = rewards[seat] - rewards[1 - seat]
                target = (
                    (1.0 if margin > 0 else (-1.0 if margin < 0 else 0.0))
                    + 0.05 * np.tanh(margin / 25000.0)
                )
                for index in game_indices:
                    rows[index]["value"] = np.float32(target)
                game = {
                    "opponent": opponent_name, "seed": seed, "seat": seat,
                    "candidate_reward": rewards[seat], "opponent_reward": rewards[1 - seat],
                    "margin": margin, "teacher_steps": teacher_steps,
                    "statuses": [str(state.status) for state in env.state],
                    "candidate_operations": dict(candidate.operation_counts),
                }
                games.append(game)
                print(json.dumps(game, ensure_ascii=False), flush=True)

    arrays = {key: np.asarray([row[key] for row in rows]) for key in rows[0]}
    for key in ("global", "board", "units"):
        arrays[key] = arrays[key].astype(np.float16)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".npz", dir=args.output.parent, delete=False) as sink:
        np.savez_compressed(sink, **arrays)
        temporary = Path(sink.name)
    temporary.replace(args.output)
    report = {
        "schema": "kaggriculture-v113-sequence-dagger-v1",
        "checkpoint": str(args.checkpoint), "teacher": args.teacher,
        "opponents": args.opponent,
        "timed_sequence_action": args.timed_sequence_action,
        "forced_expert": args.forced_expert,
        "teacher_execution_probability": args.teacher_execution_probability,
        "rows": len(rows), "games": len(games), "cleaned_actions": cleaned,
        "mean_candidate_reward": float(np.mean([row["candidate_reward"] for row in games])),
        "elapsed_seconds": time.time() - started, "game_rows": games,
    }
    args.output.with_suffix(".json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: report[key] for key in (
        "rows", "games", "cleaned_actions", "mean_candidate_reward", "elapsed_seconds",
    )}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
