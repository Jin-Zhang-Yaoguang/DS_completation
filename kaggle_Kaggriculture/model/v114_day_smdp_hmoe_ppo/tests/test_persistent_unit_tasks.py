import copy

from persistent_unit_tasks import PersistentUnitTaskExecutor, UnitTask


def empty_board():
    return [[None if x < 5 and y < 5 else "LOCKED" for x in range(10)] for y in range(10)]


def observation(step=0, farmer=(0, 0), tiles=None):
    products = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
    own = {
        "money": 3000, "tiles": copy.deepcopy(tiles or empty_board()),
        "farmer": list(farmer), "hands": [], "unlocked_quadrants": ["NW"],
        "hires_today": 0,
    }
    return {
        "step": step, "day": step // 24, "hour": step % 24, "player": 0,
        "farms": [own, copy.deepcopy(own)],
        "private": {
            "shed": {name: 0 for name in products},
            "seeds": {name: (1 if name == "WHEAT" else 0) for name in products[:5]},
            "inventories": [{}],
        },
        "market": {
            "inventory": {name: 10000 for name in products},
            "prices": {name: 25 for name in products},
        },
        "town": {"unlocked_shops": []},
    }


def test_task_is_held_across_moves_and_compiled_at_target():
    calls = []
    def planner(_, index):
        calls.append(index)
        return UnitTask("CROP_PRODUCTION", "PLANT", "WHEAT", 0, 2, 0, 8)
    executor = PersistentUnitTaskExecutor(planner)
    assert executor.act(observation(0, (0, 0)))["farmer"] == ["EAST"]
    assert executor.act(observation(1, (1, 0)))["farmer"] == ["EAST"]
    assert executor.act(observation(2, (2, 0)))["farmer"] == ["PLANT", "WHEAT"]
    assert calls == [0]
    assert executor.audit()["completed_tasks"] == 1
    assert executor.audit()["market_actions"] == 0


def test_invalid_terminal_operation_fails_closed_and_replans():
    calls = []
    def planner(_, index):
        calls.append(index)
        return UnitTask("CROP_PRODUCTION", "HARVEST", "NONE", 0, 0, 0, 2)
    executor = PersistentUnitTaskExecutor(planner)
    assert executor.act(observation(0))["farmer"] == ["PASS"]
    assert executor.audit()["failed_tasks"] == 1
    assert executor.act(observation(1))["farmer"] == ["PASS"]
    assert calls == [0, 0]
