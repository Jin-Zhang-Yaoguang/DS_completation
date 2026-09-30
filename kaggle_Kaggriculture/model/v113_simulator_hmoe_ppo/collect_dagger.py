"""Collect on-policy states and label them with the official starter agent."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import time

from kaggle_environments import make
import numpy as np

import action_space as space
from collect_rollouts import agent_observations, call_opponent, resolve_opponent
import features
from policy import V113Policy


DEFAULT_PHASE_SCHEDULE = (0, 0, 0, 0, 0, 0, 0, 3, 3, 3, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 4, 4, 4, 5, 4, 4, 4, 2, 2)


def split_for_seed(seed: int) -> int:
    bucket = int(hashlib.sha256(f"v113-dagger:{seed}".encode()).hexdigest()[:8], 16) % 5
    return 1 if bucket == 0 else 0


def labelled_row(obs, action, expert, seed, seat, opponent_blind=False):
    source = space.normalise_action(action or {}, space.unit_count(obs) - 1)
    clean = space.decode_action(obs, space.encode_action(obs, source))
    encoded_action = space.encode_action(obs, clean)
    state = features.encode_observation(obs, opponent_blind=opponent_blind)
    unit_tokens = np.full((features.MAX_UNITS,), space.UNIT_INDEX["PASS"], dtype=np.int16)
    unit_quantities = np.zeros((features.MAX_UNITS,), dtype=np.int16)
    count = min(features.MAX_UNITS, len(encoded_action["unit_tokens"]))
    unit_tokens[:count] = encoded_action["unit_tokens"][:count]
    unit_quantities[:count] = encoded_action["unit_quantities"][:count]
    market_mask = np.zeros((space.MAX_MARKET_SLOTS,), dtype=np.uint8)
    market_mask[:min(space.MAX_MARKET_SLOTS, len(clean["market"]) + 1)] = 1
    return {
        **state,
        "unit_tokens": unit_tokens,
        "unit_quantities": unit_quantities,
        "market_tokens": np.asarray(encoded_action["market_tokens"], dtype=np.int16),
        "market_quantities": np.asarray(encoded_action["market_quantities"], dtype=np.int16),
        "market_mask": market_mask,
        "expert": np.int16(expert),
        "value": np.float32(0.0),
        "split": np.int8(split_for_seed(seed)),
        "episode": np.int64(seed),
        "step": np.int16(int(space.get(obs, "step", 0) or 0)),
        "seat": np.int8(seat),
    }, clean != source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--seeds", type=int, default=8)
    parser.add_argument("--seed-start", type=int, default=1139500)
    parser.add_argument("--teacher", default="builtin:starter")
    parser.add_argument("--opponent", default="builtin:pass")
    parser.add_argument("--teacher-execution-probability", type=float, default=0.5)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--opponent-blind", action="store_true")
    args = parser.parse_args()
    if not 0.0 <= args.teacher_execution_probability <= 1.0:
        parser.error("teacher execution probability must be in [0, 1]")
    started = time.time()
    rng = np.random.default_rng(args.seed_start)
    rows = []
    games = []
    cleaned = 0
    for seed in range(args.seed_start, args.seed_start + args.seeds):
        for seat in (0, 1):
            candidate = V113Policy(
                args.checkpoint, expert_schedule=DEFAULT_PHASE_SCHEDULE,
                opponent_blind=args.opponent_blind,
            )
            teacher = resolve_opponent(args.teacher, f"v113_dagger_teacher_{seed}_{seat}")
            opponent = resolve_opponent(args.opponent, f"v113_dagger_opponent_{seed}_{seat}")
            env = make("kaggriculture", configuration={"seed": seed}, debug=False)
            env.reset(2)
            game_row_indices = []
            teacher_steps = 0
            while not env.done:
                observations = agent_observations(env)
                obs = observations[seat]
                candidate_action, _ = candidate.act(obs, rng, deterministic=True)
                teacher_action = call_opponent(teacher, obs, env.configuration)
                step = int(space.get(obs, "step", len(env.steps) - 1) or 0)
                if step % args.stride == 0:
                    row, changed = labelled_row(
                        obs, teacher_action, DEFAULT_PHASE_SCHEDULE[min(29, step // 24)], seed, seat,
                        opponent_blind=args.opponent_blind,
                    )
                    cleaned += int(changed)
                    game_row_indices.append(len(rows))
                    rows.append(row)
                use_teacher = rng.random() < args.teacher_execution_probability
                teacher_steps += int(use_teacher)
                actions = [None, None]
                actions[seat] = teacher_action if use_teacher else candidate_action
                actions[1 - seat] = call_opponent(opponent, observations[1 - seat], env.configuration)
                env.step(actions)
            rewards = [float(state.reward or 0.0) for state in env.state]
            margin = rewards[seat] - rewards[1 - seat]
            target = (1.0 if margin > 0 else (-1.0 if margin < 0 else 0.0)) + 0.05 * np.tanh(margin / 25000.0)
            for index in game_row_indices:
                rows[index]["value"] = np.float32(target)
            game = {
                "seed": seed, "seat": seat, "candidate_reward": rewards[seat],
                "opponent_reward": rewards[1 - seat], "margin": margin,
                "teacher_steps": teacher_steps, "steps": len(env.steps) - 1,
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
        "schema": "kaggriculture-v113-dagger-v1", "rows": len(rows), "games": len(games),
        "teacher": args.teacher, "opponent": args.opponent,
        "teacher_execution_probability": args.teacher_execution_probability,
        "opponent_blind": args.opponent_blind,
        "cleaned_teacher_actions": cleaned,
        "split_rows": {"train": int(np.sum(arrays["split"] == 0)), "validation": int(np.sum(arrays["split"] == 1))},
        "mean_candidate_reward": float(np.mean([game["candidate_reward"] for game in games])),
        "elapsed_seconds": time.time() - started, "game_rows": games,
    }
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("rows", "games", "split_rows", "mean_candidate_reward", "elapsed_seconds")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
