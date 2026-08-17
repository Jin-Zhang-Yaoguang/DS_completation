"""Strict local acceptance tests for the v0 Kaggriculture submission."""

from __future__ import annotations

import argparse
import copy
import json
import math
import tarfile
import tempfile
from collections import Counter
from pathlib import Path

from kaggle_environments import make

from build_submission import build as build_submission
from main import agent


FARMER_ZERO_ARG = {
    "NORTH",
    "SOUTH",
    "EAST",
    "WEST",
    "PASS",
    "DROP",
    "WATER",
    "HARVEST",
    "FERTILIZE",
    "BUILD_COOP",
    "BUILD_PASTURE",
    "DIG",
    "FEED",
    "COLLECT_FERTILIZER",
    "CARE",
}
MOVES = {
    "NORTH": (0, -1),
    "SOUTH": (0, 1),
    "EAST": (1, 0),
    "WEST": (-1, 0),
}
CROPS = {"WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"}
PRODUCTS = CROPS | {"EGG", "MILK", "WOOL", "FERTILIZER"}
MARKET_ITEMS = {
    "BUY_SEED": CROPS,
    "BUY_PRODUCT": {"WHEAT", "FERTILIZER"},
    "BUY_ANIMAL": {"GOOSE", "COW", "SHEEP"},
    "SELL": PRODUCTS,
}


def get(value, key, default=None):
    getter = getattr(value, "get", None)
    if getter is not None:
        try:
            return getter(key, default)
        except Exception:
            pass
    try:
        return value[key]
    except Exception:
        return default


def positive_total(inventory):
    return sum(max(0, int(value)) for value in inventory.values())


def board_shape(tiles):
    return len(tiles[0]), len(tiles)


def shed_access(tiles):
    width, height = board_shape(tiles)
    left, top = width // 2 - 1, height // 2 - 1
    return {(left, top), (left + 1, top), (left, top + 1), (left + 1, top + 1)}


def validate_unit_shape(action):
    assert isinstance(action, list) and action, f"unit action must be a non-empty list: {action!r}"
    op = action[0]
    if op in FARMER_ZERO_ARG:
        assert len(action) == 1, f"{op} takes no arguments: {action!r}"
    elif op == "PLANT":
        assert len(action) == 2 and action[1] in CROPS, f"invalid PLANT: {action!r}"
    elif op in {"PICKUP", "PLACE"}:
        assert len(action) in {2, 3}, f"invalid {op}: {action!r}"
        if len(action) == 3:
            assert isinstance(action[2], int) and action[2] > 0
    else:
        raise AssertionError(f"unknown unit operation: {action!r}")


def validate_market_shape(order):
    assert isinstance(order, list) and order, f"market order must be a non-empty list: {order!r}"
    op = order[0]
    if op in {"HIRE", "BUY_LAND"}:
        assert len(order) == 1, f"{op} takes no arguments: {order!r}"
        return
    assert op in MARKET_ITEMS, f"unknown market operation: {order!r}"
    assert len(order) == 3, f"market order needs item and quantity: {order!r}"
    assert order[1] in MARKET_ITEMS[op], f"invalid item for {op}: {order!r}"
    assert isinstance(order[2], int) and order[2] > 0, f"invalid quantity: {order!r}"


def validate_farmer_legality(obs, action):
    player = int(get(obs, "player", 0))
    me = get(obs, "farms")[player]
    private = get(obs, "private", {})
    tiles = get(me, "tiles")
    x, y = map(int, get(me, "farmer"))
    tile = tiles[y][x]
    op = action[0]

    if op in MOVES:
        dx, dy = MOVES[op]
        nx, ny = x + dx, y + dy
        width, height = board_shape(tiles)
        assert 0 <= nx < width and 0 <= ny < height, f"out-of-bounds move from {(x, y)}: {action}"
        assert tiles[ny][nx] != "LOCKED", f"v0 entered version-sensitive locked land: {(nx, ny)}"
    elif op == "PLANT":
        assert tile is None, f"PLANT on occupied tile: {tile!r}"
        assert int(get(get(private, "seeds", {}), action[1], 0)) > 0, "PLANT without seed"
    elif op == "WATER":
        assert isinstance(tile, dict) and tile.get("kind") == "PLANT", f"WATER on {tile!r}"
        assert not tile.get("watered_today", False), "duplicate WATER"
    elif op == "HARVEST":
        assert isinstance(tile, dict) and tile.get("kind") == "PLANT", f"HARVEST on {tile!r}"
        assert int(tile.get("yield_units", 0)) > 0, "HARVEST without yield"
        assert int(get(obs, "day", 0)) - int(tile.get("planted_day", 0)) >= 2, "immature HARVEST"
    elif op == "DROP":
        assert (x, y) in shed_access(tiles), f"DROP away from shed: {(x, y)}"
        inventories = get(private, "inventories", [])
        assert inventories and positive_total(inventories[0]) > 0, "DROP with empty inventory"
    elif op == "DIG":
        assert tile is not None and tile != "LOCKED", f"DIG on {tile!r}"
        assert not (isinstance(tile, dict) and "animal" in tile), "DIG on occupied animal tile"


def validate_action(obs, action):
    assert isinstance(action, dict), f"top-level action must be a dict: {action!r}"
    assert set(action) == {"farmer", "hands", "market"}, f"incomplete action keys: {action!r}"
    json.dumps(action, allow_nan=False)

    validate_unit_shape(action["farmer"])
    validate_farmer_legality(obs, action["farmer"])

    player = int(get(obs, "player", 0))
    hands = get(get(obs, "farms")[player], "hands", [])
    assert isinstance(action["hands"], list), "hands actions must be a list"
    assert len(action["hands"]) == len(hands), "hands action count does not match hired hands"
    for hand_action in action["hands"]:
        validate_unit_shape(hand_action)

    assert isinstance(action["market"], list), "market must be a list"
    assert len(action["market"]) <= 10, "too many market orders"
    shed = get(get(obs, "private", {}), "shed", {})
    sold = Counter()
    for order in action["market"]:
        validate_market_shape(order)
        if order[0] == "SELL":
            sold[order[1]] += order[2]
            assert sold[order[1]] <= int(get(shed, order[1], 0)), f"SELL exceeds shed: {order!r}"


class ActionAudit:
    def __init__(self, wrapped=agent):
        self.wrapped = wrapped
        self.calls = 0
        self.events = Counter()

    def __call__(self, obs, configuration=None):
        action = self.wrapped(obs)
        validate_action(obs, action)
        self.calls += 1
        self.events[action["farmer"][0]] += 1
        for hand_action in action["hands"]:
            self.events[f"HAND:{hand_action[0]}"] += 1
        for order in action["market"]:
            self.events[order[0]] += 1
        return action


def make_observation(
    *,
    day=0,
    hour=0,
    position=(4, 4),
    seeds=0,
    shed=None,
    inventory=None,
    hands=None,
    tile=None,
):
    tiles = [
        [None if x < 5 and y < 5 else "LOCKED" for x in range(10)]
        for y in range(10)
    ]
    if tile is not None:
        tiles[position[1]][position[0]] = tile
    farm = {
        "money": 3000,
        "tiles": tiles,
        "farmer": list(position),
        "hands": list(hands or []),
        "unlocked_quadrants": ["NW"],
        "hires_today": 0,
    }
    other = copy.deepcopy(farm)
    return {
        "player": 0,
        "step": day * 24 + hour,
        "day": day,
        "hour": hour,
        "farms": [farm, other],
        "private": {
            "shed": dict(shed or {}),
            "seeds": {"WHEAT": seeds},
            "inventories": [dict(inventory or {})] + [{} for _ in (hands or [])],
        },
        "market": {"inventory": {}, "prices": {}},
        "town": {"unlocked_shops": []},
    }


def run_synthetic_tests():
    initial = make_observation()
    before = copy.deepcopy(initial)
    action = agent(initial)
    assert initial == before, "agent mutated its observation"
    assert action["farmer"] == ["PASS"]
    assert action["market"] == [["BUY_SEED", "WHEAT", 3]]

    seeded = make_observation(seeds=3)
    assert agent(seeded)["farmer"] == ["PLANT", "WHEAT"]

    young = {
        "kind": "PLANT",
        "crop": "WHEAT",
        "planted_day": 0,
        "watered_today": False,
        "consecutive_unwatered": 0,
        "yield_units": 0,
        "max_lifespan_step": 120,
        "fertilized_until_day": -1,
    }
    assert agent(make_observation(tile=young))["farmer"] == ["WATER"]

    ripe = dict(young, watered_today=True, yield_units=2)
    assert agent(make_observation(day=2, tile=ripe))["farmer"] == ["HARVEST"]

    carrying = make_observation(position=(3, 3), inventory={"WHEAT": 2})
    assert agent(carrying)["farmer"][0] in MOVES
    at_shed = make_observation(position=(4, 4), inventory={"WHEAT": 2})
    assert agent(at_shed)["farmer"] == ["DROP"]

    stocked = make_observation(shed={"WHEAT": 5})
    assert ["SELL", "WHEAT", 5] in agent(stocked)["market"]

    with_hands = make_observation(hands=[(4, 4), (3, 4)])
    assert agent(with_hands)["hands"] == [["PASS"], ["PASS"]]

    weed = {"kind": "WEED"}
    assert agent(make_observation(seeds=1, tile=weed))["farmer"] == ["DIG"]
    assert agent(make_observation(hour=22, seeds=1, tile=weed))["farmer"] == ["PASS"]

    strange = make_observation(seeds=1, tile={"kind": "UNKNOWN"})
    assert agent(strange)["farmer"] not in (["PLANT", "WHEAT"], ["WATER"], ["HARVEST"], ["DIG"])

    too_late = make_observation(day=29, hour=22, tile=ripe)
    assert agent(too_late)["farmer"] == ["PASS"]

    final_crop = dict(young, planted_day=27, yield_units=1)
    assert agent(make_observation(day=29, hour=19, tile=final_crop))["farmer"] == ["WATER"]
    final_crop["watered_today"] = True
    final_crop["yield_units"] = 2
    assert agent(make_observation(day=29, hour=20, tile=final_crop))["farmer"] == ["HARVEST"]
    assert agent(make_observation(day=29, hour=21, inventory={"WHEAT": 2}))["farmer"] == ["DROP"]
    final_sale = agent(make_observation(day=29, hour=22, shed={"WHEAT": 2}))
    assert ["SELL", "WHEAT", 2] in final_sale["market"]

    assert agent({}) == {"farmer": ["PASS"], "hands": [], "market": []}


def run_match(opponent, seat, episode_steps, seed):
    audit = ActionAudit()
    agents = [audit, opponent] if seat == 0 else [opponent, audit]
    env = make(
        "kaggriculture",
        configuration={"episodeSteps": episode_steps, "seed": seed},
        debug=True,
    )
    steps = env.run(agents)
    final = steps[-1]
    statuses = [state.status for state in final]
    rewards = [float(state.reward) for state in final]
    assert len(steps) == episode_steps, (len(steps), episode_steps)
    assert statuses == ["DONE", "DONE"], statuses
    assert all(math.isfinite(reward) for reward in rewards), rewards
    assert audit.calls == episode_steps - 1, audit.calls
    if episode_steps == 720:
        assert int(final[0].observation.day) == 29
        assert int(final[0].observation.hour) == 23
    return {
        "opponent": opponent,
        "seat": seat,
        "steps": len(steps),
        "calls": audit.calls,
        "reward": rewards[seat],
        "opponent_reward": rewards[1 - seat],
        "events": dict(sorted(audit.events.items())),
    }


def run_self_play(seed):
    left, right = ActionAudit(), ActionAudit()
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=True)
    steps = env.run([left, right])
    final = steps[-1]
    rewards = [float(state.reward) for state in final]
    assert len(steps) == 720
    assert [state.status for state in final] == ["DONE", "DONE"]
    assert all(math.isfinite(reward) for reward in rewards), rewards
    assert left.calls == right.calls == 719
    return {
        "opponent": "self",
        "seat": "both",
        "steps": len(steps),
        "calls": [left.calls, right.calls],
        "reward": rewards,
        "events": [dict(sorted(left.events.items())), dict(sorted(right.events.items()))],
    }


def run_clean_archive(seed):
    report = build_submission()
    archive_path = Path(report["archive"])
    with tempfile.TemporaryDirectory(prefix="kaggriculture-v0-") as temporary:
        clean_dir = Path(temporary)
        with tarfile.open(archive_path, "r:gz") as archive:
            members = archive.getmembers()
            assert [member.name for member in members] == ["main.py"]
            source = archive.extractfile(members[0])
            assert source is not None
            clean_main = clean_dir / "main.py"
            clean_main.write_bytes(source.read())

        env = make(
            "kaggriculture",
            configuration={"episodeSteps": 720, "seed": seed},
            debug=True,
        )
        steps = env.run([str(clean_main), "starter"])
        final = steps[-1]
        rewards = [float(state.reward) for state in final]
        assert len(steps) == 720
        assert [state.status for state in final] == ["DONE", "DONE"]
        assert all(math.isfinite(reward) for reward in rewards), rewards
        return {
            "archive_sha256": report["sha256"],
            "members": report["members"],
            "steps": len(steps),
            "statuses": [state.status for state in final],
            "reward": rewards,
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="run synthetic and 48-step tests only")
    args = parser.parse_args()

    run_synthetic_tests()
    results = []
    for opponent_index, opponent in enumerate(("pass", "random", "starter")):
        for seat in (0, 1):
            results.append(run_match(opponent, seat, 48, 100 + opponent_index * 2 + seat))

    archive_result = None
    if not args.quick:
        for opponent_index, opponent in enumerate(("pass", "random", "starter")):
            for seat in (0, 1):
                results.append(run_match(opponent, seat, 720, 200 + opponent_index * 2 + seat))
        results.append(run_self_play(300))

        required = {"BUY_SEED", "PLANT", "WATER", "HARVEST", "DROP", "SELL"}
        pass_game = next(
            result
            for result in results
            if result["opponent"] == "pass" and result["seat"] == 0 and result["steps"] == 720
        )
        missing = required - set(pass_game["events"])
        assert not missing, f"wheat loop did not close; missing events: {sorted(missing)}"
        assert pass_game["reward"] > 3000, "legal-looking loop did not produce net proceeds"
        archive_result = run_clean_archive(601)

    print(
        json.dumps(
            {"ok": True, "quick": args.quick, "matches": results, "clean_archive": archive_result},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
