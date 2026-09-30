"""Collect coherent on-policy crop-cycle curricula for five product experts."""

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


def crop_teacher(obs, crop: str):
    farms = space.get(obs, "farms", []) or []
    player = int(space.get(obs, "player", 0) or 0)
    private = space.get(obs, "private", {}) or {}
    farm = farms[player]
    x, y = space.get(farm, "farmer", [0, 0])
    tile = (space.get(farm, "tiles", []) or [])[y][x]
    day = int(space.get(obs, "day", 0) or 0)
    seeds = space.get(private, "seeds", {}) or {}
    shed = space.get(private, "shed", {}) or {}
    market = []
    if int(space.get(shed, crop, 0) or 0) > 0:
        market.append(["SELL", crop, int(space.get(shed, crop, 0) or 0)])
    if int(space.get(seeds, crop, 0) or 0) == 0 and float(space.get(farm, "money", 0) or 0) >= CROPS[crop]["seed"]:
        market.append(["BUY_SEED", crop, 1])
    farmer = ["PASS"]
    if tile is None and int(space.get(seeds, crop, 0) or 0) > 0:
        farmer = ["PLANT", crop]
    elif isinstance(tile, dict) and space.get(tile, "kind", "") == "PLANT" and space.get(tile, "crop", "") == crop:
        planted_day = space.get(tile, "planted_day", day)
        age = day - int(day if planted_day is None else planted_day)
        if age >= CROPS[crop]["max_yield_day"]:
            farmer = ["HARVEST"]
        elif not bool(space.get(tile, "watered_today", False)):
            farmer = ["WATER"]
    return {"farmer": farmer, "hands": [], "market": market}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds-per-crop", type=int, default=4)
    parser.add_argument("--seed-start", type=int, default=1139000)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
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
                    action = crop_teacher(obs, crop)
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
        "schema": "kaggriculture-v113-product-curriculum-v1", "rows": len(rows),
        "games": len(games), "crops": list(space.CROPS),
        "mean_reward_by_crop": {
            crop: float(np.mean([game["candidate_reward"] for game in games if game["crop"] == crop]))
            for crop in space.CROPS
        },
        "elapsed_seconds": time.time() - started, "game_rows": games,
    }
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("rows", "games", "mean_reward_by_crop", "elapsed_seconds")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
