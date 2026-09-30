"""Standalone daily-target rule/shallow-tree Hierarchical MoE."""

import base64
import copy
import json
import zlib


__version__ = "v116-daily-aggregate-heuristic-moe-prototype-2"
_REFERENCE = json.loads(zlib.decompress(base64.b85decode("__TARGET_STATE_PAYLOAD__")).decode("utf-8"))
_DAY_TARGETS = _REFERENCE["targets"]
_PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
_CROPS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")
_ANIMALS = ("GOOSE", "COW", "SHEEP")
_SEED_COST = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
_ANIMAL_COST = {"GOOSE": 300, "COW": 400, "SHEEP": 500}
_FIRST_YIELD = {"WHEAT": 2, "CARROT": 2, "TOMATO": 8, "STRAWBERRY": 10, "MELON": 10}
_FULL_YIELD = {"WHEAT": 4, "CARROT": 3, "TOMATO": 8, "STRAWBERRY": 10, "MELON": 10}
_PROFILES = {
    "balanced": {"animal": "SHEEP", "crop": "MELON", "sales": ("FERTILIZER", "WOOL", "MILK", "MELON", "STRAWBERRY", "EGG", "CARROT", "TOMATO")},
    "wool": {"animal": "SHEEP", "crop": "WHEAT", "sales": ("WOOL", "FERTILIZER", "MILK", "MELON", "STRAWBERRY", "EGG", "CARROT", "TOMATO")},
    "dairy": {"animal": "COW", "crop": "WHEAT", "sales": ("MILK", "FERTILIZER", "WOOL", "MELON", "STRAWBERRY", "EGG", "CARROT", "TOMATO")},
    "orchard": {"animal": "SHEEP", "crop": "STRAWBERRY", "sales": ("MELON", "STRAWBERRY", "FERTILIZER", "MILK", "WOOL", "CARROT", "TOMATO", "EGG")},
}
_STATE = {0: {}, 1: {}}


def _get(value, key, default=None):
    if isinstance(value, dict):
        return value.get(key, default)
    getter = getattr(value, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(value, key, default)


def _seat(obs):
    return 1 if int(_get(obs, "player", 0) or 0) == 1 else 0


def _farm(obs):
    farms = list(_get(obs, "farms", []) or [])
    seat = _seat(obs)
    return farms[seat] if seat < len(farms) else {}


def _private(obs):
    return _get(obs, "private", {}) or {}


def _day(obs):
    return min(29, max(0, int(_get(obs, "day", 0) or 0)))


def _hour(obs):
    return max(0, int(_get(obs, "hour", 0) or 0))


def _target(obs):
    return _DAY_TARGETS[min(len(_DAY_TARGETS) - 1, _day(obs))]


def _positions(obs):
    farm = _farm(obs)
    return [tuple(map(int, value)) for value in [_get(farm, "farmer", [4, 4]), *list(_get(farm, "hands", []) or [])]]


def _inventories(obs, count):
    values = [dict(value or {}) for value in list(_get(_private(obs), "inventories", []) or [])]
    values.extend({} for _ in range(max(0, count - len(values))))
    return values[:count]


def _rows(obs):
    return list(_get(_farm(obs), "tiles", []) or [])


def _access(obs):
    half = (len(_rows(obs)) or 10) // 2
    return {(half - 1, half - 1), (half, half - 1), (half - 1, half), (half, half)}


def _tile(obs, position):
    try:
        x, y = position
        rows = _rows(obs)
        return rows[y][x] if 0 <= y < len(rows) and 0 <= x < len(rows[y]) else "LOCKED"
    except (IndexError, TypeError):
        return "LOCKED"


def _distance(left, right):
    return abs(left[0] - right[0]) + abs(left[1] - right[1])


def _toward(obs, source, target, actor):
    dx, dy = target[0] - source[0], target[1] - source[1]
    horizontal = abs(dx) > abs(dy) or (abs(dx) == abs(dy) and actor % 2 == 0)
    names = []
    if horizontal and dx:
        names.append("EAST" if dx > 0 else "WEST")
    if dy:
        names.append("SOUTH" if dy > 0 else "NORTH")
    if dx:
        names.append("EAST" if dx > 0 else "WEST")
    delta = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}
    for name in names:
        mx, my = delta[name]
        if _tile(obs, (source[0] + mx, source[1] + my)) != "LOCKED":
            return [name]
    return ["PASS"]


def _nearest_access(obs, position):
    return min(_access(obs), key=lambda value: (_distance(position, value), value[1], value[0]))


def _router(obs, state):
    shops = set(str(value) for value in list(_get(_get(obs, "town", {}) or {}, "unlocked_shops", []) or []))
    scores = {
        "wool": 6 * int("YARN_STORE" in shops) + int("PET_CAFE" in shops),
        "dairy": 5 * int("ICE_CREAM_SHOP" in shops) + 2 * int("BRUNCH_SPOT" in shops),
        "orchard": 5 * int("SMOOTHIE_SHOP" in shops) + 2 * int("PIZZA_SHOP" in shops) + int("FARMERS_MARKET" in shops),
    }
    desired = max(scores, key=scores.get) if max(scores.values()) > 0 else "balanced"
    if state.get("profile") is None and _day(obs) >= 3 and desired != "balanced":
        state["profile"] = desired
        state["commits"][desired] = int(state["commits"].get(desired, 0)) + 1
    route = str(state.get("profile") or desired)
    state["routes"][route] = int(state["routes"].get(route, 0)) + 1
    return route


def _installed(obs):
    animals = {name: 0 for name in _ANIMALS}
    crops = {name: 0 for name in _CROPS}
    for row in _rows(obs):
        for tile in row:
            if not isinstance(tile, dict):
                continue
            if tile.get("animal") in animals:
                animals[str(tile["animal"])] += 1
            if tile.get("crop") in crops:
                crops[str(tile["crop"])] += 1
    return animals, crops


def _totals(obs, names):
    inventories = _inventories(obs, len(_positions(obs)))
    shed = dict(_get(_private(obs), "shed", {}) or {})
    result = {name: max(0, int(shed.get(name, 0) or 0)) for name in names}
    for inventory in inventories:
        for name in names:
            result[name] += max(0, int(inventory.get(name, 0) or 0))
    return result


def _animal_slots(obs, profile):
    rows = _rows(obs)
    open_cells = [(x, y) for y, row in enumerate(rows) for x, tile in enumerate(row) if tile != "LOCKED"]
    center = ((len(rows) or 10) - 1) / 2.0
    ordered = sorted(open_cells, key=lambda p: (abs(p[0] - center) + abs(p[1] - center), p[1], p[0]))
    teacher = _target(obs).get("animals", {})
    total_goal = min(18, max(8, sum(max(0, int(value or 0)) for value in teacher.values())))
    primary = _PROFILES[profile]["animal"]
    secondary = "COW" if primary == "SHEEP" else "SHEEP"
    return {position: primary if index < max(5, total_goal * 2 // 3) else secondary for index, position in enumerate(ordered[:total_goal])}


def _crop_for(obs, profile, position):
    day = _day(obs)
    if day >= 27:
        return "CARROT"
    if profile in ("wool", "dairy"):
        return "WHEAT" if (position[0] + position[1]) % 3 == 0 else ("MELON" if day < 8 else "STRAWBERRY")
    if profile == "orchard":
        return "MELON" if day < 8 else "STRAWBERRY"
    return "MELON" if day < 7 else "STRAWBERRY"


def _tasks(obs, profile):
    tasks = []
    terminal = _day(obs) >= 29
    slots = _animal_slots(obs, profile)
    seeds = dict(_get(_private(obs), "seeds", {}) or {})
    remaining = {crop: max(0, int(seeds.get(crop, 0) or 0)) for crop in _CROPS}
    for y, row in enumerate(_rows(obs)):
        for x, tile in enumerate(row):
            if tile == "LOCKED":
                continue
            position = (x, y)
            role = slots.get(position)
            if role:
                if isinstance(tile, dict) and tile.get("animal"):
                    if int(tile.get("yield_units", 0) or 0) > 0:
                        tasks.append((1 if terminal else 8, position, ["HARVEST"], None))
                    if tile.get("fertilizer_available"):
                        tasks.append((2 if terminal else 6, position, ["COLLECT_FERTILIZER"], None))
                    if not terminal and not tile.get("fed_today"):
                        tasks.append((3 if _hour(obs) >= 16 or int(tile.get("consecutive_unfed", 0) or 0) else 14, position, ["FEED"], "WHEAT"))
                    if not terminal and not tile.get("cared_today"):
                        tasks.append((7 if _hour(obs) >= 18 else 16, position, ["CARE"], None))
                elif not terminal and isinstance(tile, dict) and tile.get("kind") == "WEED":
                    tasks.append((20, position, ["DIG"], None))
                elif not terminal and isinstance(tile, dict) and tile.get("kind") in ("PASTURE", "COOP"):
                    tasks.append((23, position, ["PLACE", role], role))
                elif not terminal and tile is None:
                    tasks.append((24, position, ["BUILD_PASTURE" if role != "GOOSE" else "BUILD_COOP"], None))
                continue
            if isinstance(tile, dict) and tile.get("kind") == "PLANT":
                crop = str(tile.get("crop", ""))
                age = _day(obs) - int(tile.get("planted_day", _day(obs)) or 0)
                limit = _FIRST_YIELD.get(crop, 99) if terminal else _FULL_YIELD.get(crop, 99)
                if int(tile.get("yield_units", 0) or 0) > 0 and age >= limit:
                    tasks.append((1 if terminal else 5, position, ["HARVEST"], None))
                if not terminal and not tile.get("watered_today"):
                    tasks.append((2 if int(tile.get("consecutive_unwatered", 0) or 0) or _hour(obs) >= 17 else 13, position, ["WATER"], None))
            elif not terminal and isinstance(tile, dict) and tile.get("kind") == "WEED":
                tasks.append((19, position, ["DIG"], None))
            elif not terminal and tile is None and _hour(obs) < 15:
                crop = _crop_for(obs, profile, position)
                if remaining.get(crop, 0) > 0:
                    tasks.append((26, position, ["PLANT", crop], None))
                    remaining[crop] -= 1
    return sorted(tasks, key=lambda value: (value[0], value[1][1], value[1][0], value[2][0]))


def _unit_plan(obs, profile, state):
    positions = _positions(obs)
    inventories = _inventories(obs, len(positions))
    actions = [["PASS"] for _ in positions]
    used = set()
    terminal = _day(obs) >= 29
    shed = dict(_get(_private(obs), "shed", {}) or {})
    if terminal:
        for actor, inventory in enumerate(inventories):
            if sum(max(0, int(value or 0)) for value in inventory.values()) <= 0:
                continue
            actions[actor] = ["DROP"] if positions[actor] in _access(obs) else _toward(obs, positions[actor], _nearest_access(obs, positions[actor]), actor)
            used.add(actor)

    installed, _ = _installed(obs)
    feed_need = max(0, sum(installed.values()) - sum(int(inv.get("WHEAT", 0) or 0) for inv in inventories))
    animal_need = _totals(obs, _ANIMALS)
    for actor, position in enumerate(positions):
        if actor in used or position not in _access(obs):
            continue
        inventory = inventories[actor]
        if feed_need > 0 and int(inventory.get("WHEAT", 0) or 0) == 0 and int(shed.get("WHEAT", 0) or 0) > 0:
            quantity = min(4, feed_need, int(shed.get("WHEAT", 0) or 0))
            actions[actor] = ["PICKUP", "WHEAT", quantity]
            shed["WHEAT"] -= quantity
            feed_need -= quantity
            used.add(actor)
            continue
        for animal in _ANIMALS:
            if animal_need.get(animal, 0) > installed.get(animal, 0) and int(shed.get(animal, 0) or 0) > 0:
                actions[actor] = ["PICKUP", animal, 1]
                shed[animal] -= 1
                used.add(actor)
                break

    for _, destination, operation, required in _tasks(obs, profile):
        choices = []
        for actor, position in enumerate(positions):
            if actor in used:
                continue
            if required and int(inventories[actor].get(required, 0) or 0) <= 0:
                continue
            choices.append((_distance(position, destination), actor))
        if not choices:
            continue
        _, actor = min(choices)
        actions[actor] = list(operation) if positions[actor] == destination else _toward(obs, positions[actor], destination, actor)
        used.add(actor)
    for action in actions:
        expert = "move" if action[0] in ("NORTH", "SOUTH", "EAST", "WEST") else "inventory" if action[0] in ("PICKUP", "DROP") else "production" if action[0] != "PASS" else "idle"
        state["unit_experts"][expert] = int(state["unit_experts"].get(expert, 0)) + 1
    return actions[0] if actions else ["PASS"], actions[1:]


def _projected_shed(obs, farmer, hands):
    shed = {key: max(0, int(value or 0)) for key, value in dict(_get(_private(obs), "shed", {}) or {}).items()}
    positions = _positions(obs)
    inventories = _inventories(obs, len(positions))
    for actor, action in enumerate([farmer, *hands]):
        if actor >= len(positions) or positions[actor] not in _access(obs):
            continue
        if action and action[0] == "DROP":
            for item, value in inventories[actor].items():
                room = max(0, 100 - sum(shed.values()))
                shed[item] = shed.get(item, 0) + min(room, max(0, int(value or 0)))
        elif len(action) >= 3 and action[0] == "PICKUP":
            item = str(action[1])
            shed[item] = max(0, shed.get(item, 0) - min(shed.get(item, 0), max(0, int(action[2] or 0))))
    return shed


def _fib(index):
    a, b = 0, 1
    for _ in range(max(0, int(index))):
        a, b = b, a + b
    return a


def _market_plan(obs, profile, farmer, hands, state):
    farm = _farm(obs)
    target = _target(obs)
    projected = _projected_shed(obs, farmer, hands)
    prices = dict(_get(_get(obs, "market", {}) or {}, "prices", {}) or {})
    orders = []
    money = max(0, int(_get(farm, "money", 0) or 0))
    terminal = _day(obs) >= 29
    crowded = sum(projected.values()) >= 82
    for item in _PROFILES[profile]["sales"]:
        available = max(0, int(projected.get(item, 0) or 0))
        if available <= 0:
            continue
        if terminal:
            quantity = available
        elif item == "FERTILIZER":
            quantity = min(10, available)
        elif item in ("WOOL", "MILK", "STRAWBERRY", "MELON"):
            base = {"WOOL": 200, "MILK": 160, "STRAWBERRY": 120, "MELON": 250}[item]
            quantity = min(6, available) if int(prices.get(item, 0) or 0) >= base // 3 or crowded else 0
        else:
            quantity = min(12, available)
        if quantity > 0 and len(orders) < 10:
            orders.append(["SELL", item, quantity])
            projected[item] -= quantity
            money += quantity * max(1, int(prices.get(item, 1) or 1))

    if terminal:
        return orders[:10]

    hands_now = len(list(_get(farm, "hands", []) or []))
    target_hands = min(10, max(5, int(target.get("max_hands", 8) or 8)))
    hires_today = max(0, int(_get(farm, "hires_today", 0) or 0))
    if _hour(obs) <= 3:
        while hands_now < target_hands and len(orders) < 10:
            cost = _fib(hires_today)
            if money < cost + 80:
                break
            orders.append(["HIRE"])
            money -= cost
            hires_today += 1
            hands_now += 1

    quads = len(list(_get(farm, "unlocked_quadrants", []) or []))
    land_cost = (1000, 2000, 4000)
    target_quads = min(4, max(1, int(target.get("quadrants", quads) or quads)))
    while quads < target_quads and len(orders) < 10:
        cost = land_cost[quads - 1]
        if money < cost + 200:
            break
        orders.append(["BUY_LAND"])
        money -= cost
        quads += 1

    installed, crops = _installed(obs)
    animal_totals = _totals(obs, _ANIMALS)
    slots = _animal_slots(obs, profile)
    desired = {animal: sum(role == animal for role in slots.values()) for animal in _ANIMALS}
    for animal in _ANIMALS:
        missing = max(0, desired[animal] - animal_totals[animal])
        if missing <= 0 or len(orders) >= 10 or _day(obs) > 18:
            continue
        room = max(0, 96 - sum(projected.values()))
        quantity = min(missing, 4 if _day(obs) == 0 else 1, room, max(0, (money - 180) // _ANIMAL_COST[animal]))
        if quantity > 0:
            orders.append(["BUY_ANIMAL", animal, quantity])
            projected[animal] = projected.get(animal, 0) + quantity
            money -= quantity * _ANIMAL_COST[animal]

    feed_goal = 2 * sum(installed.values()) + 6
    inventories = _inventories(obs, len(_positions(obs)))
    wheat = projected.get("WHEAT", 0) + sum(max(0, int(inv.get("WHEAT", 0) or 0)) for inv in inventories)
    missing = max(0, feed_goal - wheat)
    if missing > 0 and len(orders) < 10:
        price = max(1, int(prices.get("WHEAT", 25) or 25))
        quantity = min(missing, max(0, 96 - sum(projected.values())), max(0, (money - 100) // price))
        if quantity > 0:
            orders.append(["BUY_PRODUCT", "WHEAT", quantity])
            money -= quantity * price

    seeds = {crop: max(0, int((_get(_private(obs), "seeds", {}) or {}).get(crop, 0) or 0)) for crop in _CROPS}
    for action in [farmer, *hands]:
        if len(action) >= 2 and action[0] == "PLANT":
            seeds[str(action[1])] = max(0, seeds.get(str(action[1]), 0) - 1)
    open_count = sum(tile is None or isinstance(tile, dict) and tile.get("kind") == "WEED" for row in _rows(obs) for tile in row)
    crop_order = (_PROFILES[profile]["crop"], "WHEAT", "MELON", "STRAWBERRY", "CARROT")
    for crop in dict.fromkeys(crop_order):
        missing = max(0, min(12, open_count - sum(crops.values())) - seeds.get(crop, 0))
        if crop == "WHEAT":
            missing = min(missing, 6)
        if missing <= 0 or len(orders) >= 10:
            continue
        quantity = min(missing, max(0, (money - 80) // _SEED_COST[crop]))
        if quantity > 0:
            orders.append(["BUY_SEED", crop, quantity])
            money -= quantity * _SEED_COST[crop]
    state["market_calls"][profile] = int(state["market_calls"].get(profile, 0)) + int(bool(orders))
    return orders[:10]


def _safe(obs, action, state):
    expected = len(list(_get(_farm(obs), "hands", []) or []))
    hands = [list(value or ["PASS"]) for value in list(action.get("hands", []) or [])]
    hands.extend([["PASS"] for _ in range(max(0, expected - len(hands)))])
    market = []
    for raw in list(action.get("market", []) or [])[:10]:
        order = list(raw)
        if len(order) >= 3:
            try:
                order[2] = max(0, min(100, int(order[2] or 0)))
            except (TypeError, ValueError):
                state["safety_rewrites"] += 1
                continue
            if order[2] <= 0:
                continue
        market.append(order)
    return {"farmer": list(action.get("farmer") or ["PASS"]), "hands": hands[:expected], "market": market}


def _reset(obs):
    seat = _seat(obs)
    step = _day(obs) * 24 + _hour(obs)
    state = _STATE[seat]
    if step == 0 or step < int(state.get("last", -1)):
        state.clear()
        state.update(last=step, calls=0, profile=None, routes={}, commits={}, unit_experts={}, market_calls={}, safety_rewrites=0, fallback=0)
    state["last"] = step
    state["calls"] = int(state.get("calls", 0)) + 1
    return state


def _fallback(obs):
    return {"farmer": ["PASS"], "hands": [["PASS"] for _ in list(_get(_farm(obs), "hands", []) or [])], "market": []}


def model_status():
    return {
        "kind": "v116_daily_aggregate_heuristic_moe_prototype",
        "model_id": "v116_target_state_heuristic_moe_prototype",
        "strategy_parent": None,
        "strength_comparator": "v76_adjacent_safe_buy_lead",
        "embedded_replay_actions": False,
        "teacher": "30-daily-aggregate-assets-topology-capacity-targets",
        "target_granularity": "daily",
        "target_count": len(_DAY_TARGETS),
        "router": "unlocked-shop-shallow-score-commitment-router",
        "production_experts": list(_PROFILES),
        "executor": "current-state-task-assignment-and-schema-safety",
        "stats": copy.deepcopy(_STATE),
    }


def agent(obs, configuration=None):
    del configuration
    state = _reset(obs)
    try:
        profile = _router(obs, state)
        farmer, hands = _unit_plan(obs, profile, state)
        market = _market_plan(obs, profile, farmer, hands, state)
        return _safe(obs, {"farmer": farmer, "hands": hands, "market": market}, state)
    except Exception:
        state["fallback"] = int(state.get("fallback", 0)) + 1
        return _fallback(obs)
