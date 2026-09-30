"""Collect clean teacher-executed trajectories for sequence-policy warm starts."""

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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--teacher", required=True)
    parser.add_argument("--opponent", action="append", required=True)
    parser.add_argument("--seeds", type=int, default=4)
    parser.add_argument("--seed-start", type=int, default=1178000)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.seeds < 1 or args.stride < 1:
        parser.error("--seeds and --stride must be positive")

    started = time.time()
    rows, games = [], []
    cleaned = 0
    for opponent_index, opponent_name in enumerate(args.opponent):
        for seed in range(args.seed_start, args.seed_start + args.seeds):
            for seat in (0, 1):
                suffix = f"{opponent_index}_{seed}_{seat}"
                teacher = resolve_opponent(args.teacher, f"v113_sequence_teacher_{suffix}")
                opponent = resolve_opponent(opponent_name, f"v113_sequence_opponent_{suffix}")
                env = make("kaggriculture", configuration={"seed": seed}, debug=False)
                env.reset(2)
                game_indices = []
                while not env.done:
                    observations = agent_observations(env)
                    obs = observations[seat]
                    teacher_action = call_opponent(teacher, obs, env.configuration)
                    step = int(space.get(obs, "step", len(env.steps) - 1) or 0)
                    if step % args.stride == 0:
                        row, changed = labelled_row(obs, teacher_action, 0, seed, seat)
                        rows.append(row)
                        game_indices.append(len(rows) - 1)
                        cleaned += int(changed)
                    actions = [None, None]
                    actions[seat] = teacher_action
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
                    "teacher_reward": rewards[seat], "opponent_reward": rewards[1 - seat],
                    "margin": margin, "statuses": [str(state.status) for state in env.state],
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
        "schema": "kaggriculture-v113-teacher-actions-v1",
        "teacher": args.teacher, "opponents": args.opponent,
        "rows": len(rows), "games": len(games), "cleaned_actions": cleaned,
        "mean_teacher_reward": float(np.mean([row["teacher_reward"] for row in games])),
        "mean_margin": float(np.mean([row["margin"] for row in games])),
        "elapsed_seconds": time.time() - started, "game_rows": games,
    }
    args.output.with_suffix(".json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: report[key] for key in (
        "rows", "games", "cleaned_actions", "mean_teacher_reward", "mean_margin",
        "elapsed_seconds",
    )}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
