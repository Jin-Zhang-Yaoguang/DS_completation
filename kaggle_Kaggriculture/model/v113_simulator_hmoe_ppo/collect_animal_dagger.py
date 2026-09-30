"""DAgger one V113 animal specialist on its own states."""

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
from collect_animal_curriculum import ANIMAL_PRODUCT, animal_teacher
from collect_dagger import labelled_row
from collect_rollouts import agent_observations
from policy_factorized import FactorizedV113Policy


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--animal", choices=tuple(ANIMAL_PRODUCT), required=True)
    parser.add_argument("--seeds", type=int, default=4)
    parser.add_argument("--seed-start", type=int, default=1153000)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--teacher-execution-probability", type=float, default=0.25)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 0 <= args.teacher_execution_probability <= 1:
        parser.error("--teacher-execution-probability must be in [0, 1]")
    started = time.time()
    rng = np.random.default_rng(args.seed_start)
    rows, games = [], []
    for offset in range(args.seeds):
        seed = args.seed_start + offset
        for seat in (0, 1):
            candidate = FactorizedV113Policy(
                args.checkpoint, forced_unit_expert=5, forced_market_expert=5,
                coupled_product_router=True, scale_worker_cap=args.workers,
            )
            env = make("kaggriculture", configuration={"seed": seed}, debug=False)
            env.reset(2)
            indices, teacher_steps = [], 0
            while not env.done:
                observations = agent_observations(env)
                obs = observations[seat]
                candidate_action = candidate.act(obs)
                teacher_action = animal_teacher(obs, args.animal, args.workers)
                step = int(space.get(obs, "step", len(env.steps) - 1) or 0)
                if step % args.stride == 0:
                    row, _ = labelled_row(obs, teacher_action, 5, seed, seat)
                    indices.append(len(rows))
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
            for index in indices:
                rows[index]["value"] = np.float32(target)
            games.append({
                "animal": args.animal, "product": ANIMAL_PRODUCT[args.animal],
                "seed": seed, "seat": seat, "candidate_reward": rewards[seat],
                "margin": margin, "teacher_steps": teacher_steps,
                "statuses": [str(state.status) for state in env.state],
                "operation_counts": dict(candidate.operation_counts),
            })
            print(json.dumps(games[-1], ensure_ascii=False), flush=True)
    arrays = {key: np.asarray([row[key] for row in rows]) for key in rows[0]}
    for key in ("global", "board", "units"):
        arrays[key] = arrays[key].astype(np.float16)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".npz", dir=args.output.parent, delete=False) as sink:
        np.savez_compressed(sink, **arrays)
        temporary = Path(sink.name)
    temporary.replace(args.output)
    report = {
        "schema": "kaggriculture-v113-animal-dagger-v1", "rows": len(rows),
        "games": len(games), "animal": args.animal,
        "teacher_execution_probability": args.teacher_execution_probability,
        "mean_candidate_reward": float(np.mean([game["candidate_reward"] for game in games])),
        "done_done": sum(game["statuses"] == ["DONE", "DONE"] for game in games),
        "elapsed_seconds": time.time() - started, "game_rows": games,
    }
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("rows", "games", "mean_candidate_reward", "done_done", "elapsed_seconds")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
