"""DAgger the scale policy on its own states with the original crop teacher."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
import time

from kaggle_environments import make
from kaggle_environments.envs.kaggriculture.kaggriculture import pass_agent
import numpy as np

import action_space as space
from collect_dagger import labelled_row
from collect_rollouts import agent_observations
from collect_scale_curriculum import scale_crop_teacher
from policy_factorized import FactorizedV113Policy
from policy_sequence_action import SequenceActionV113Policy


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--seeds-per-crop", type=int, default=1)
    parser.add_argument("--seed-start", type=int, default=1143000)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--teacher-execution-probability", type=float, default=0.25)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sequence-action", action="store_true")
    args = parser.parse_args()
    if not 0 <= args.teacher_execution_probability <= 1:
        parser.error("--teacher-execution-probability must be in [0, 1]")
    started = time.time()
    rng = np.random.default_rng(args.seed_start)
    rows = []
    games = []
    for crop_index, crop in enumerate(space.CROPS):
        for offset in range(args.seeds_per_crop):
            seed = args.seed_start + crop_index * 100 + offset
            for seat in (0, 1):
                policy_class = SequenceActionV113Policy if args.sequence_action else FactorizedV113Policy
                candidate = policy_class(
                    args.checkpoint, forced_unit_expert=crop_index,
                    forced_market_expert=crop_index,
                    scale_worker_cap=args.workers,
                    scale_seed_capacity=11,
                )
                env = make("kaggriculture", configuration={"seed": seed}, debug=False)
                env.reset(2)
                game_indices = []
                teacher_steps = 0
                while not env.done:
                    observations = agent_observations(env)
                    obs = observations[seat]
                    candidate_action = candidate.act(obs)
                    teacher_action = scale_crop_teacher(obs, crop, args.workers)
                    step = int(space.get(obs, "step", len(env.steps) - 1) or 0)
                    if step % args.stride == 0:
                        row, _ = labelled_row(obs, teacher_action, crop_index, seed, seat)
                        game_indices.append(len(rows))
                        rows.append(row)
                    use_teacher = rng.random() < args.teacher_execution_probability
                    teacher_steps += int(use_teacher)
                    actions = [None, None]
                    actions[seat] = teacher_action if use_teacher else candidate_action
                    actions[1 - seat] = pass_agent(observations[1 - seat])
                    env.step(actions)
                rewards = [float(state.reward or 0.0) for state in env.state]
                margin = rewards[seat] - rewards[1 - seat]
                target = (1.0 if margin > 0 else (-1.0 if margin < 0 else 0.0)) + 0.05 * np.tanh(margin / 25000.0)
                for index in game_indices:
                    rows[index]["value"] = np.float32(target)
                game = {
                    "crop": crop, "seed": seed, "seat": seat,
                    "candidate_reward": rewards[seat], "margin": margin,
                    "teacher_steps": teacher_steps,
                    "statuses": [str(state.status) for state in env.state],
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
        "schema": "kaggriculture-v113-scale-dagger-v1", "rows": len(rows),
        "games": len(games), "teacher_execution_probability": args.teacher_execution_probability,
        "mean_reward_by_crop": {
            crop: float(np.mean([game["candidate_reward"] for game in games if game["crop"] == crop]))
            for crop in space.CROPS
        },
        "elapsed_seconds": time.time() - started, "game_rows": games,
    }
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in (
        "rows", "games", "teacher_execution_probability", "mean_reward_by_crop", "elapsed_seconds"
    )}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
