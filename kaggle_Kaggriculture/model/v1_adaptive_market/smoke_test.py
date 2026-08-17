"""Acceptance tests for the v1 adaptive Kaggriculture submission."""

from __future__ import annotations

import json
import math
import tarfile
import tempfile
from collections import Counter
from pathlib import Path

from kaggle_environments import make
from kaggle_environments.envs.kaggriculture import kaggriculture as official

from build_submission import build as build_submission
import main


SCHEME_DIR = Path(__file__).resolve().parent
V0_PATH = SCHEME_DIR.parent / "v0_api_smoke" / "main.py"

UNIT_OPERATIONS = {
    "NORTH", "SOUTH", "EAST", "WEST", "PASS", "DROP", "WATER",
    "HARVEST", "FERTILIZE", "BUILD_COOP", "BUILD_PASTURE", "DIG",
    "FEED", "COLLECT_FERTILIZER", "CARE", "PLANT", "PICKUP", "PLACE",
}
MARKET_OPERATIONS = {
    "BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL", "HIRE", "BUY_LAND",
}


def get(value, key, default=None):
    if isinstance(value, dict):
        return value.get(key, default)
    getter = getattr(value, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(value, key, default)


def validate_unit_action(action):
    assert isinstance(action, list) and action
    assert action[0] in UNIT_OPERATIONS, action
    if action[0] in {"PLANT", "PICKUP", "PLACE"}:
        assert len(action) in {2, 3}, action
    else:
        assert len(action) == 1, action


def validate_action(obs, action):
    assert isinstance(action, dict)
    assert set(action) == {"farmer", "hands", "market"}
    json.dumps(action, allow_nan=False)
    validate_unit_action(action["farmer"])

    player = 1 if int(get(obs, "player", 0) or 0) == 1 else 0
    farms = list(get(obs, "farms", []) or [])
    expected_hands = len(get(farms[player], "hands", []) or [])
    assert len(action["hands"]) == expected_hands
    for hand_action in action["hands"]:
        validate_unit_action(hand_action)

    assert isinstance(action["market"], list)
    assert len(action["market"]) <= 10
    for order in action["market"]:
        assert isinstance(order, list) and order
        assert order[0] in MARKET_OPERATIONS, order


class ActionAudit:
    def __init__(self):
        self.calls = 0
        self.events = Counter()

    def __call__(self, obs, configuration=None):
        action = main.agent(obs)
        validate_action(obs, action)
        self.calls += 1
        self.events[action["farmer"][0]] += 1
        for hand_action in action["hands"]:
            self.events[f"HAND:{hand_action[0]}"] += 1
        for order in action["market"]:
            self.events[f"MARKET:{order[0]}"] += 1
        return action


def route_for(shops):
    main._ROUTE_STATE[0] = {"last_step": -1, "shops": (), "expert": None}
    opening = {"player": 0, "step": 0, "town": {"unlocked_shops": []}}
    decision = {"player": 0, "step": 168, "town": {"unlocked_shops": shops}}
    assert main._selected_route(opening) == "low"
    return main._selected_route(decision)


def run_unit_tests():
    assert main.__version__ == "market-route-moe-v3-hinge"
    assert len(main._LOW_ROUTE_ACTIONS) == len(main._HIGH_ROUTE_ACTIONS) == 719
    assert route_for(["YARN_STORE", "BAKERY"]) == "high"
    assert route_for(["ICE_CREAM_SHOP", "YARN_STORE"]) == "low"
    assert route_for(["PET_CAFE", "BAKERY"]) == "low"

    inventories = (8500, 9000, 9500, 9800, 9999, 10000, 10200, 11000)
    for item in main._MARKET_PARAMS:
        for inventory in inventories:
            actual = main._market_price(item, inventory)
            expected = official.market_price(item, inventory)
            assert actual == expected, (item, inventory, actual, expected)


def run_match(opponent, seat, seed):
    audit = ActionAudit()
    agents = [audit, opponent] if seat == 0 else [opponent, audit]
    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    steps = env.run(agents)
    final = steps[-1]
    rewards = [float(state.reward or 0) for state in final]
    statuses = [str(state.status) for state in final]
    assert len(steps) == 720
    assert statuses == ["DONE", "DONE"], statuses
    assert audit.calls == 719
    assert all(math.isfinite(value) for value in rewards)
    return {
        "opponent": str(opponent),
        "seat": seat,
        "seed": seed,
        "reward": rewards[seat],
        "opponent_reward": rewards[1 - seat],
        "margin": rewards[seat] - rewards[1 - seat],
        "events": dict(sorted(audit.events.items())),
    }


def run_self_play(seed):
    left, right = ActionAudit(), ActionAudit()
    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    steps = env.run([left, right])
    final = steps[-1]
    rewards = [float(state.reward or 0) for state in final]
    assert len(steps) == 720
    assert [str(state.status) for state in final] == ["DONE", "DONE"]
    assert left.calls == right.calls == 719
    return {"opponent": "self", "seed": seed, "reward": rewards}


def run_clean_archive(seed):
    report = build_submission()
    with tempfile.TemporaryDirectory(prefix="kaggriculture-v1-") as temporary:
        clean_main = Path(temporary) / "main.py"
        with tarfile.open(report["archive"], "r:gz") as archive:
            assert archive.getnames() == ["main.py"]
            source = archive.extractfile("main.py")
            assert source is not None
            clean_main.write_bytes(source.read())
        env = make("kaggriculture", configuration={"seed": seed}, debug=False)
        steps = env.run([str(clean_main), "starter"])
        final = steps[-1]
        assert len(steps) == 720
        assert [str(state.status) for state in final] == ["DONE", "DONE"]
        return {
            "archive_sha256": report["sha256"],
            "archive_bytes": report["bytes"],
            "reward": [float(state.reward or 0) for state in final],
        }


def run():
    run_unit_tests()
    matches = []
    opponents = ((str(V0_PATH), 8100), ("random", 8200), ("starter", 8300))
    for opponent, seed_base in opponents:
        for seat in (0, 1):
            matches.append(run_match(opponent, seat, seed_base + seat))

    v0_matches = [match for match in matches if match["opponent"] == str(V0_PATH)]
    assert all(match["margin"] > 0 for match in v0_matches), v0_matches
    assert all("MARKET:SELL" in match["events"] for match in matches)

    self_play = run_self_play(8400)
    archive = run_clean_archive(8500)
    return {"ok": True, "matches": matches, "self_play": self_play, "archive": archive}


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
