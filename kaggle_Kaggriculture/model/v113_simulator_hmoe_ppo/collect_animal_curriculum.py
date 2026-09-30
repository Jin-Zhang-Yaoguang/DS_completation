"""Collect original multi-worker EGG/MILK/WOOL curricula for V113."""

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
import features
from collect_dagger import labelled_row
from collect_rollouts import agent_observations
from collect_scale_curriculum import move_toward


ANIMAL_PRODUCT = {"GOOSE": "EGG", "COW": "MILK", "SHEEP": "WOOL"}
ANIMAL_STRUCTURE = {"GOOSE": "COOP", "COW": "PASTURE", "SHEEP": "PASTURE"}
TARGETS = ((2, 2), (3, 2), (2, 3))
SHED_TARGET = (4, 4)


def _inventory(obs, unit_index: int) -> dict:
    inventories = list(space.get(space.private(obs), "inventories", []) or [])
    return inventories[unit_index] if unit_index < len(inventories) else {}


def _tile(obs, target):
    x, y = target
    return (space.get(space.own_farm(obs), "tiles", []) or [])[y][x]


def animal_role_decision(obs, animal: str, unit_index: int, target) -> tuple[list, tuple[int, int]]:
    position = space.unit_position(obs, unit_index)
    inventory = _inventory(obs, unit_index)
    tile = _tile(obs, target)
    shed = space.get(space.private(obs), "shed", {}) or {}

    if int(space.get(inventory, animal, 0) or 0) > 0:
        if position != target:
            return move_toward(position, target), target
        if isinstance(tile, dict) and space.get(tile, "kind", "") == ANIMAL_STRUCTURE[animal] and not space.get(tile, "animal", None):
            return ["PLACE", animal, 1], target

    if not (isinstance(tile, dict) and space.get(tile, "animal", "") == animal):
        if tile is None and position == target:
            return ["BUILD_" + ANIMAL_STRUCTURE[animal]], target
        if isinstance(tile, dict) and space.get(tile, "kind", "") == ANIMAL_STRUCTURE[animal]:
            if position == SHED_TARGET and int(space.get(shed, animal, 0) or 0) > 0:
                return ["PICKUP", animal, 1], SHED_TARGET
            return (move_toward(position, SHED_TARGET) if position != SHED_TARGET else ["PASS"]), SHED_TARGET
        if position != target:
            return move_toward(position, target), target
        return ["DIG"], target

    if position != target:
        if int(space.get(inventory, "WHEAT", 0) or 0) <= 0:
            if position == SHED_TARGET and int(space.get(shed, "WHEAT", 0) or 0) > 0:
                return ["PICKUP", "WHEAT", 1], SHED_TARGET
            return move_toward(position, SHED_TARGET), SHED_TARGET
        return move_toward(position, target), target
    if not bool(space.get(tile, "fed_today", False)):
        if int(space.get(inventory, "WHEAT", 0) or 0) > 0:
            return ["FEED"], target
        return move_toward(position, SHED_TARGET), SHED_TARGET
    if not bool(space.get(tile, "cared_today", False)):
        return ["CARE"], target
    if int(space.get(tile, "yield_units", 0) or 0) > 0:
        return ["HARVEST"], target
    if bool(space.get(tile, "fertilizer_available", False)):
        return ["COLLECT_FERTILIZER"], target
    return ["PASS"], target


def animal_role_action(obs, animal: str, unit_index: int, target) -> list:
    return animal_role_decision(obs, animal, unit_index, target)[0]


def animal_option_labels(obs, animal: str) -> tuple[np.ndarray, np.ndarray]:
    roles = np.zeros((features.MAX_UNITS,), dtype=np.int16)
    targets = np.full((len(roles),), SHED_TARGET[1] * 10 + SHED_TARGET[0], dtype=np.int16)
    for unit_index in range(min(space.unit_count(obs), len(TARGETS))):
        _, subgoal = animal_role_decision(obs, animal, unit_index, TARGETS[unit_index])
        roles[unit_index] = 1
        targets[unit_index] = subgoal[1] * 10 + subgoal[0]
    return roles, targets


def animal_teacher(obs, animal: str, workers: int = 8):
    animal_count = len(TARGETS)
    unit_count = space.unit_count(obs)
    orders = []
    for unit_index in range(unit_count):
        orders.append(
            animal_role_action(obs, animal, unit_index, TARGETS[unit_index])
            if unit_index < animal_count else ["PASS"]
        )

    private = space.private(obs)
    shed = space.get(private, "shed", {}) or {}
    inventories = list(space.get(private, "inventories", []) or [])
    product = ANIMAL_PRODUCT[animal]
    hour = int(space.get(obs, "hour", int(space.get(obs, "step", 0) or 0) % 24) or 0)
    market = []
    if hour == 0:
        market.extend([["HIRE"] for _ in range(workers)])
        placed = sum(
            int(isinstance(_tile(obs, target), dict) and space.get(_tile(obs, target), "animal", "") == animal)
            for target in TARGETS
        )
        carried_animals = sum(int(space.get(inv, animal, 0) or 0) for inv in inventories)
        missing_animals = max(0, animal_count - placed - int(space.get(shed, animal, 0) or 0) - carried_animals)
        if missing_animals > 0:
            market.append(["BUY_ANIMAL", animal, missing_animals])
        else:
            held = int(space.get(shed, product, 0) or 0)
            if held > 0:
                market.append(["SELL", product, held])
        carried_wheat = sum(int(space.get(inv, "WHEAT", 0) or 0) for inv in inventories)
        wheat_missing = max(0, animal_count + 2 - int(space.get(shed, "WHEAT", 0) or 0) - carried_wheat)
        if wheat_missing > 0:
            market.append(["BUY_PRODUCT", "WHEAT", wheat_missing])
    return {"farmer": orders[0], "hands": orders[1:], "market": market[:space.MAX_MARKET_SLOTS]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds-per-animal", type=int, default=4)
    parser.add_argument("--seed-start", type=int, default=1149000)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--animals", default="GOOSE,COW,SHEEP")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not len(TARGETS) - 1 <= args.workers <= 15:
        parser.error(f"--workers must be in [{len(TARGETS) - 1}, 15]")
    started = time.time()
    rows, games = [], []
    animals = tuple(item.strip().upper() for item in args.animals.split(",") if item.strip())
    invalid = [animal for animal in animals if animal not in ANIMAL_PRODUCT]
    if not animals or invalid:
        parser.error(f"--animals contains invalid values: {invalid}")
    for animal_index, animal in enumerate(animals):
        for offset in range(args.seeds_per_animal):
            seed = args.seed_start + animal_index * 100 + offset
            for seat in (0, 1):
                env = make("kaggriculture", configuration={"seed": seed}, debug=False)
                env.reset(2)
                indices = []
                while not env.done:
                    observations = agent_observations(env)
                    obs = observations[seat]
                    action = animal_teacher(obs, animal, args.workers)
                    step = int(space.get(obs, "step", len(env.steps) - 1) or 0)
                    if step % args.stride == 0:
                        row, _ = labelled_row(obs, action, 5, seed, seat)
                        row["option_roles"], row["option_targets"] = animal_option_labels(obs, animal)
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
                games.append({
                    "animal": animal, "product": ANIMAL_PRODUCT[animal], "seed": seed, "seat": seat,
                    "candidate_reward": rewards[seat], "margin": margin,
                    "statuses": [str(state.status) for state in env.state],
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
        "schema": "kaggriculture-v113-animal-curriculum-v1", "rows": len(rows),
        "games": len(games), "workers": args.workers, "targets": TARGETS,
        "mean_reward_by_animal": {
            animal: float(np.mean([game["candidate_reward"] for game in games if game["animal"] == animal]))
            for animal in animals
        },
        "elapsed_seconds": time.time() - started, "game_rows": games,
    }
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("rows", "games", "mean_reward_by_animal", "elapsed_seconds")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
