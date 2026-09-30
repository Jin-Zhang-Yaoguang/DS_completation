"""Collect original multi-worker crop curricula for V113's action experts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
import time

from kaggle_environments import make
from kaggle_environments.envs.kaggriculture.kaggriculture import CROPS, pass_agent
import numpy as np

import action_space as space
from collect_dagger import labelled_row
from collect_rollouts import agent_observations


TARGETS = (
    (4, 4), (3, 4), (4, 3), (3, 3), (2, 4),
    (4, 2), (2, 3), (3, 2), (2, 2),
)
FULL_TARGETS = TARGETS + (
    (1, 4), (4, 1), (1, 3), (3, 1), (1, 2), (2, 1), (1, 1),
)


def move_toward(position: tuple[int, int], target: tuple[int, int]) -> list[str]:
    x, y = position
    tx, ty = target
    if x < tx:
        return ["EAST"]
    if x > tx:
        return ["WEST"]
    if y < ty:
        return ["SOUTH"]
    if y > ty:
        return ["NORTH"]
    return ["PASS"]


def tile_action(obs, crop: str, unit_index: int, target: tuple[int, int]) -> list[str]:
    farm = space.own_farm(obs)
    position = space.unit_position(obs, unit_index)
    if position != target:
        return move_toward(position, target)
    x, y = target
    tile = (space.get(farm, "tiles", []) or [])[y][x]
    seeds = space.get(space.private(obs), "seeds", {}) or {}
    day = int(space.get(obs, "day", 0) or 0)
    if tile is None:
        return ["PLANT", crop] if int(space.get(seeds, crop, 0) or 0) > 0 else ["PASS"]
    if isinstance(tile, dict) and space.get(tile, "kind", "") == "PLANT" and space.get(tile, "crop", "") == crop:
        planted_day = space.get(tile, "planted_day", day)
        age = day - int(day if planted_day is None else planted_day)
        if age >= CROPS[crop]["max_yield_day"] and int(space.get(tile, "yield_units", 0) or 0) > 0:
            return ["HARVEST"]
        if not bool(space.get(tile, "watered_today", False)):
            return ["WATER"]
        return ["PASS"]
    return ["DIG"]


def scale_crop_teacher(obs, crop: str, workers: int = 8, targets=TARGETS):
    farm = space.own_farm(obs)
    private = space.private(obs)
    shed = space.get(private, "shed", {}) or {}
    seeds = space.get(private, "seeds", {}) or {}
    hour = int(space.get(obs, "hour", int(space.get(obs, "step", 0) or 0) % 24) or 0)
    units = min(space.unit_count(obs), 1 + workers, len(targets))
    orders = [tile_action(obs, crop, index, targets[index]) for index in range(units)]
    market = []
    if hour == 0:
        market.extend([["HIRE"] for _ in range(workers)])
    held = int(space.get(shed, crop, 0) or 0)
    if held > 0:
        market.append(["SELL", crop, held])
    planted = 0
    for row in space.get(farm, "tiles", []) or []:
        for tile in row:
            planted += int(isinstance(tile, dict) and space.get(tile, "crop", "") == crop)
    desired_seed_reserve = len(targets) + 2
    missing = max(0, desired_seed_reserve - int(space.get(seeds, crop, 0) or 0) - planted)
    if missing > 0 and len(market) < space.MAX_MARKET_SLOTS:
        market.append(["BUY_SEED", crop, missing])
    return {"farmer": orders[0], "hands": orders[1:], "market": market[:space.MAX_MARKET_SLOTS]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds-per-crop", type=int, default=4)
    parser.add_argument("--seed-start", type=int, default=1141000)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--target-count", type=int, default=len(TARGETS))
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.target_count <= len(FULL_TARGETS):
        parser.error(f"--target-count must be in [1, {len(FULL_TARGETS)}]")
    targets = FULL_TARGETS[:args.target_count]
    if not 1 <= args.workers <= min(15, len(targets) - 1):
        parser.error("--workers must fit the represented units and selected targets")
    started = time.time()
    rows = []
    games = []
    for crop_index, crop in enumerate(space.CROPS):
        for offset in range(args.seeds_per_crop):
            seed = args.seed_start + crop_index * 100 + offset
            for seat in (0, 1):
                env = make("kaggriculture", configuration={"seed": seed}, debug=False)
                env.reset(2)
                indices = []
                while not env.done:
                    observations = agent_observations(env)
                    obs = observations[seat]
                    action = scale_crop_teacher(obs, crop, args.workers, targets)
                    step = int(space.get(obs, "step", len(env.steps) - 1) or 0)
                    if step % args.stride == 0:
                        row, _ = labelled_row(obs, action, crop_index, seed, seat)
                        indices.append(len(rows))
                        rows.append(row)
                    actions = [None, None]
                    actions[seat] = action
                    actions[1 - seat] = pass_agent(observations[1 - seat])
                    env.step(actions)
                rewards = [float(state.reward or 0.0) for state in env.state]
                margin = rewards[seat] - rewards[1 - seat]
                target = (1.0 if margin > 0 else (-1.0 if margin < 0 else 0.0)) + 0.05 * np.tanh(margin / 25000.0)
                for index in indices:
                    rows[index]["value"] = np.float32(target)
                game = {
                    "crop": crop, "seed": seed, "seat": seat,
                    "candidate_reward": rewards[seat], "margin": margin,
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
        "schema": "kaggriculture-v113-scale-curriculum-v1", "rows": len(rows),
        "games": len(games), "workers": args.workers, "targets": targets,
        "mean_reward_by_crop": {
            crop: float(np.mean([game["candidate_reward"] for game in games if game["crop"] == crop]))
            for crop in space.CROPS
        },
        "elapsed_seconds": time.time() - started, "game_rows": games,
    }
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in (
        "rows", "games", "workers", "mean_reward_by_crop", "elapsed_seconds"
    )}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
