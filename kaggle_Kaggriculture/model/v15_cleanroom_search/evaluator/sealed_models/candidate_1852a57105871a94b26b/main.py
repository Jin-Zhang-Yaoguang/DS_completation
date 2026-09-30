_PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
_ANIMALS = ("GOOSE", "COW", "SHEEP")
_ANIMAL_COST = {"GOOSE": 300, "COW": 400, "SHEEP": 500}
_SEED_COST = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
_FIRST_YIELD = {"WHEAT": 2, "CARROT": 2, "TOMATO": 8, "STRAWBERRY": 10, "MELON": 10}
_FULL_HARVEST = {"WHEAT": 4, "CARROT": 3, "TOMATO": 8, "STRAWBERRY": 10, "MELON": 10}

# A compact mixed-livestock core leaves nine crop tiles in the initial field.
_ANIMAL_ROLES = {
    (4, 3): "GOOSE",
    (3, 4): "GOOSE",
    (3, 3): "GOOSE",
    (4, 2): "GOOSE",
    (2, 4): "GOOSE",
    (3, 2): "GOOSE",
    (2, 3): "GOOSE",
    (4, 1): "GOOSE",
    (3, 1): "COW",
    (2, 2): "COW",
    (2, 1): "COW",
    (1, 1): "COW",
    (1, 3): "SHEEP",
    (1, 2): "SHEEP",
    (0, 3): "SHEEP",
    (0, 2): "SHEEP",
}


def _empty_action():
    return {"farmer": ["PASS"], "hands": [], "market": []}


def _inventory_list(private, unit_count):
    values = private.get("inventories", [])
    if not isinstance(values, list):
        values = []
    out = []
    for i in range(unit_count):
        value = values[i] if i < len(values) and isinstance(values[i], dict) else {}
        out.append(value)
    return out


def _access_tiles(board_size):
    half = board_size // 2
    return ((half - 1, half - 1), (half, half - 1), (half - 1, half), (half, half))


def _is_access(pos, board_size):
    return tuple(pos) in _access_tiles(board_size)


def _distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _move_toward(pos, target, unit_index):
    dx = target[0] - pos[0]
    dy = target[1] - pos[1]
    if dx == 0 and dy == 0:
        return ["PASS"]
    horizontal_first = abs(dx) > abs(dy) or (abs(dx) == abs(dy) and unit_index % 2 == 0)
    if horizontal_first and dx:
        return ["EAST" if dx > 0 else "WEST"]
    if dy:
        return ["SOUTH" if dy > 0 else "NORTH"]
    return ["EAST" if dx > 0 else "WEST"]


def _nearest_access(pos, board_size):
    return min(_access_tiles(board_size), key=lambda p: (_distance(pos, p), p[1], p[0]))


def _fib(index):
    a, b = 1, 1
    for _ in range(index):
        a, b = b, a + b
    return a


def _installed_animals(tiles):
    counts = {name: 0 for name in _ANIMALS}
    for row in tiles:
        for tile in row:
            if isinstance(tile, dict):
                animal = tile.get("animal")
                if animal in counts:
                    counts[animal] += 1
    return counts


def _animal_totals(tiles, private, inventories):
    counts = _installed_animals(tiles)
    shed = private.get("shed", {})
    if not isinstance(shed, dict):
        shed = {}
    for animal in _ANIMALS:
        counts[animal] += max(0, int(shed.get(animal, 0) or 0))
    for inv in inventories:
        for animal in _ANIMALS:
            counts[animal] += max(0, int(inv.get(animal, 0) or 0))
    return counts


def _goal_animals(day):
    goose = min(8, 5 + max(0, day))
    return {
        "GOOSE": goose,
        "COW": 4 if day >= 2 else 0,
        "SHEEP": 4 if day >= 3 else 0,
    }


def _role_for(x, y):
    return _ANIMAL_ROLES.get((x, y))


def _crop_for_slot(x, y, day, prices):
    if day <= 19:
        carrot_price = int(prices.get("CARROT", 35) or 35)
        melon_price = int(prices.get("MELON", 250) or 250)
        if day <= 2 and y == 0 and x < 3:
            return "CARROT"
        if carrot_price >= 55 or melon_price <= 40:
            return "CARROT"
        return "MELON"
    if day <= 26:
        return "CARROT"
    return None


def _harvest_ready(tile, day, terminal):
    if not isinstance(tile, dict) or tile.get("kind") != "PLANT":
        return False
    if int(tile.get("yield_units", 0) or 0) <= 0:
        return False
    crop = tile.get("crop")
    age = day - int(tile.get("planted_day", day) or 0)
    if crop in ("TOMATO", "STRAWBERRY"):
        return age >= _FIRST_YIELD.get(crop, 99)
    threshold = _FIRST_YIELD.get(crop, 99) if terminal else _FULL_HARVEST.get(crop, 99)
    return age >= threshold


def _normal_tasks(tiles, day, hour, terminal, seed_counts, prices):
    tasks = []
    board_size = len(tiles)
    plant_slots = []
    for y in range(board_size):
        row = tiles[y]
        for x in range(len(row)):
            tile = row[x]
            role = _role_for(x, y)
            if role:
                if isinstance(tile, dict) and tile.get("animal") in _ANIMALS:
                    if terminal:
                        return_distance = min(_distance((x, y), p) for p in _access_tiles(board_size))
                        can_liquidate = hour <= 21 - return_distance
                        if can_liquidate and tile.get("fertilizer_available", False):
                            tasks.append((2, x, y, ["COLLECT_FERTILIZER"], None))
                        if can_liquidate and int(tile.get("yield_units", 0) or 0) > 0:
                            tasks.append((1, x, y, ["HARVEST"], None))
                    else:
                        if not tile.get("fed_today", False):
                            risk = int(tile.get("consecutive_unfed", 0) or 0)
                            tasks.append((3 if risk >= 1 or hour >= 17 else 18, x, y, ["FEED"], "WHEAT"))
                        if tile.get("fertilizer_available", False):
                            tasks.append((5 if hour >= 14 else 10, x, y, ["COLLECT_FERTILIZER"], None))
                        held = int(tile.get("yield_units", 0) or 0)
                        if held > 0:
                            tasks.append((8 if held >= 3 else 14, x, y, ["HARVEST"], None))
                        if not tile.get("cared_today", False):
                            tasks.append((16 if hour < 18 else 7, x, y, ["CARE"], None))
                elif isinstance(tile, dict) and tile.get("kind") == "WEED":
                    if not terminal:
                        tasks.append((24, x, y, ["DIG"], None))
                elif isinstance(tile, dict) and tile.get("kind") in ("COOP", "PASTURE"):
                    if not terminal:
                        tasks.append((25, x, y, ["PLACE", role], role))
                elif tile is None and not terminal:
                    build = "BUILD_COOP" if role == "GOOSE" else "BUILD_PASTURE"
                    tasks.append((26, x, y, [build], role))
                continue

            if isinstance(tile, dict) and tile.get("kind") == "PLANT":
                return_distance = min(_distance((x, y), p) for p in _access_tiles(board_size))
                can_liquidate = not terminal or hour <= 21 - return_distance
                if can_liquidate and _harvest_ready(tile, day, terminal):
                    tasks.append((1 if terminal else 6, x, y, ["HARVEST"], None))
                if not terminal and not tile.get("watered_today", False):
                    risk = int(tile.get("consecutive_unwatered", 0) or 0)
                    planted_now = int(tile.get("planted_day", -1) or -1) == day
                    priority = 2 if risk >= 1 or planted_now or hour >= 17 else 15
                    tasks.append((priority, x, y, ["WATER"], None))
            elif isinstance(tile, dict) and tile.get("kind") == "WEED":
                if not terminal:
                    tasks.append((22, x, y, ["DIG"], None))
            elif tile is None and not terminal and hour < 14:
                plant_slots.append((y, x))

    # Plant requests are capped before assignment, preserving atomic seed validity.
    remaining = {name: max(0, int(seed_counts.get(name, 0) or 0)) for name in _SEED_COST}
    for y, x in sorted(plant_slots):
        crop = _crop_for_slot(x, y, day, prices)
        if crop and remaining.get(crop, 0) > 0:
            tasks.append((30, x, y, ["PLANT", crop], None))
            remaining[crop] -= 1
    return tasks


def _unit_plan(farm, private, day, hour, prices):
    tiles = farm.get("tiles", [])
    if not isinstance(tiles, list) or not tiles:
        return ["PASS"], []
    board_size = len(tiles)
    positions = [farm.get("farmer", [0, 0])]
    hands = farm.get("hands", [])
    if isinstance(hands, list):
        positions.extend(hands)
    unit_count = len(positions)
    inventories = _inventory_list(private, unit_count)
    actions = [["PASS"] for _ in range(unit_count)]
    used = set()
    terminal = day >= 29

    # On the last day, every carried item is routed through the shed for liquidation.
    if terminal:
        for i in range(unit_count):
            if sum(max(0, int(v or 0)) for v in inventories[i].values()) <= 0:
                continue
            pos = positions[i]
            if _is_access(pos, board_size):
                actions[i] = ["DROP"]
            else:
                actions[i] = _move_toward(pos, _nearest_access(pos, board_size), i)
            used.add(i)

    shed = private.get("shed", {})
    if not isinstance(shed, dict):
        shed = {}

    # At the shed, create a small number of multi-feed carriers each morning.
    if not terminal:
        unfed = 0
        for row in tiles:
            for tile in row:
                if isinstance(tile, dict) and tile.get("animal") in _ANIMALS and not tile.get("fed_today", False):
                    unfed += 1
        carried = sum(max(0, int(inv.get("WHEAT", 0) or 0)) for inv in inventories)
        needed = max(0, unfed - carried)
        available = max(0, int(shed.get("WHEAT", 0) or 0))
        for i in range(unit_count):
            if needed <= 0 or available <= 0:
                break
            if i in used or not _is_access(positions[i], board_size):
                continue
            if any(int(inventories[i].get(a, 0) or 0) > 0 for a in _ANIMALS):
                continue
            if int(inventories[i].get("WHEAT", 0) or 0) > 0:
                continue
            quantity = min(3, needed, available)
            actions[i] = ["PICKUP", "WHEAT", quantity]
            used.add(i)
            needed -= quantity
            available -= quantity

        # Pull purchased livestock only when a free worker can carry it to its berth.
        carried_animals = {a: sum(max(0, int(inv.get(a, 0) or 0)) for inv in inventories) for a in _ANIMALS}
        for animal in _ANIMALS:
            count = max(0, int(shed.get(animal, 0) or 0))
            open_roles = 0
            for (x, y), role in _ANIMAL_ROLES.items():
                if role != animal or y >= board_size or x >= len(tiles[y]):
                    continue
                tile = tiles[y][x]
                if not (isinstance(tile, dict) and tile.get("animal") == animal):
                    open_roles += 1
            count = min(count, max(0, open_roles - carried_animals[animal]))
            for i in range(unit_count):
                if count <= 0:
                    break
                if i in used or not _is_access(positions[i], board_size):
                    continue
                if int(inventories[i].get("WHEAT", 0) or 0) > 0:
                    continue
                if any(int(inventories[i].get(a, 0) or 0) > 0 for a in _ANIMALS):
                    continue
                actions[i] = ["PICKUP", animal, 1]
                used.add(i)
                count -= 1

    seed_counts = private.get("seeds", {})
    if not isinstance(seed_counts, dict):
        seed_counts = {}
    tasks = _normal_tasks(tiles, day, hour, terminal, seed_counts, prices)
    tasks.sort(key=lambda t: (t[0], t[2], t[1], t[3][0]))

    for priority, x, y, action, required in tasks:
        choices = []
        for i in range(unit_count):
            if i in used:
                continue
            if required and int(inventories[i].get(required, 0) or 0) <= 0:
                continue
            choices.append((_distance(positions[i], (x, y)), i))
        if not choices:
            continue
        _, i = min(choices)
        if tuple(positions[i]) == (x, y):
            actions[i] = list(action)
        else:
            actions[i] = _move_toward(positions[i], (x, y), i)
        used.add(i)

    return actions[0], actions[1:]


def _sale_quantity(item, count, price, day, crowded):
    if count <= 0:
        return 0
    if day >= 27:
        return count
    if item == "FERTILIZER":
        return min(count, 10 if crowded else 8)
    if item == "EGG":
        return min(count, 12)
    if item in ("CARROT", "TOMATO"):
        return min(count, 12)
    if item == "MELON":
        if price >= 50:
            return min(count, 6)
        if price >= 15 or crowded:
            return min(count, 2)
        return 0
    if item in ("STRAWBERRY", "MILK", "WOOL"):
        if price >= 35:
            return min(count, 4)
        if crowded:
            return min(count, 2)
        return 0
    return 0


def _projected_shed(private, farmer_action, hand_actions):
    shed = private.get("shed", {})
    if not isinstance(shed, dict):
        shed = {}
    projected = {k: max(0, int(v or 0)) for k, v in shed.items()}
    inventories = private.get("inventories", [])
    if not isinstance(inventories, list):
        inventories = []
    actions = [farmer_action] + list(hand_actions)
    for i, action in enumerate(actions):
        if not isinstance(action, list) or not action or action[0] != "DROP":
            continue
        inv = inventories[i] if i < len(inventories) and isinstance(inventories[i], dict) else {}
        for item, value in inv.items():
            projected[item] = projected.get(item, 0) + max(0, int(value or 0))
    return projected


def _desired_seed_counts(tiles, day, prices):
    desired = {name: 0 for name in _SEED_COST}
    board_size = len(tiles)
    for y in range(board_size):
        for x in range(len(tiles[y])):
            if _role_for(x, y):
                continue
            tile = tiles[y][x]
            if tile is None or (isinstance(tile, dict) and tile.get("kind") == "WEED"):
                crop = _crop_for_slot(x, y, day, prices)
                if crop:
                    desired[crop] += 1
    return desired


def _market_plan(obs, farm, private, day, hour, farmer_action, hand_actions):
    market = obs.get("market", {})
    if not isinstance(market, dict):
        market = {}
    prices = market.get("prices", {})
    if not isinstance(prices, dict):
        prices = {}
    tiles = farm.get("tiles", [])
    if not isinstance(tiles, list):
        tiles = []
    positions_count = 1 + len(farm.get("hands", []) if isinstance(farm.get("hands", []), list) else [])
    inventories = _inventory_list(private, positions_count)
    projected = _projected_shed(private, farmer_action, hand_actions)
    crowded = sum(projected.values()) >= 82
    orders = []
    money = float(farm.get("money", 0) or 0)

    # High-value, steep-curve products are offered first and in small lots.
    sell_order = ("MELON", "WOOL", "MILK", "STRAWBERRY", "FERTILIZER", "EGG", "CARROT", "TOMATO", "WHEAT")
    for item in sell_order:
        count = max(0, int(projected.get(item, 0) or 0))
        price = max(1, int(prices.get(item, 1) or 1))
        quantity = _sale_quantity(item, count, price, day, crowded)
        if quantity > 0 and len(orders) < 10:
            orders.append(["SELL", item, quantity])
            money += quantity * max(1, price // 2)

    # Cheap daily labor converts travel-heavy husbandry into reliable care.
    hires_today = max(0, int(farm.get("hires_today", 0) or 0))
    target_hires = 9 if day < 29 else 7
    need_hires = max(0, target_hires - hires_today)
    if hour <= 2:
        cap = 6 if day == 0 and hour == 0 else 5
        for i in range(min(need_hires, cap)):
            if len(orders) >= 10:
                break
            cost = _fib(hires_today + i)
            if money < cost + 80:
                break
            orders.append(["HIRE"])
            money -= cost

    if day >= 29:
        return orders[:10]

    installed = _installed_animals(tiles)
    totals = _animal_totals(tiles, private, inventories)

    # Feed stock includes wheat already carried by workers.
    wheat_stock = max(0, int(projected.get("WHEAT", 0) or 0))
    wheat_stock += sum(max(0, int(inv.get("WHEAT", 0) or 0)) for inv in inventories)
    planned_feeds = int(farmer_action[0] == "FEED") + sum(int(a and a[0] == "FEED") for a in hand_actions)
    wheat_stock = max(0, wheat_stock - planned_feeds)
    feed_target = max(10 if day == 0 else 0, 2 * sum(installed.values()) + 4)
    feed_missing = max(0, feed_target - wheat_stock)
    wheat_price = max(1, int(prices.get("WHEAT", 25) or 25))
    if feed_missing and len(orders) < 10:
        room = max(0, 96 - sum(projected.values()))
        quantity = min(feed_missing, room, max(0, int((money - 100) // wheat_price)))
        if quantity > 0:
            orders.append(["BUY_PRODUCT", "WHEAT", quantity])
            money -= quantity * wheat_price

    # Livestock is staged so the opening keeps enough cash for seed and labor.
    goals = _goal_animals(day)
    for animal in _ANIMALS:
        missing = max(0, goals[animal] - totals[animal])
        if missing <= 0 or len(orders) >= 10 or day > 18:
            continue
        if day == 0 and animal == "GOOSE":
            cap = 5
        else:
            cap = 1
        cost = _ANIMAL_COST[animal]
        quantity = min(missing, cap, max(0, int((money - 180) // cost)))
        if quantity > 0:
            orders.append(["BUY_ANIMAL", animal, quantity])
            money -= quantity * cost

    seeds = private.get("seeds", {})
    if not isinstance(seeds, dict):
        seeds = {}
    after_plants = {name: max(0, int(seeds.get(name, 0) or 0)) for name in _SEED_COST}
    all_actions = [farmer_action] + list(hand_actions)
    for action in all_actions:
        if isinstance(action, list) and len(action) >= 2 and action[0] == "PLANT" and action[1] in after_plants:
            after_plants[action[1]] = max(0, after_plants[action[1]] - 1)
    desired = _desired_seed_counts(tiles, day, prices)
    crop_order = ("CARROT", "MELON") if day <= 2 else ("MELON", "CARROT")
    for crop in crop_order:
        if len(orders) >= 10:
            break
        missing = max(0, desired.get(crop, 0) - after_plants.get(crop, 0))
        if missing <= 0:
            continue
        cap = 4
        if day == 0 and crop == "MELON":
            cap = 8
        cost = _SEED_COST[crop]
        quantity = min(missing, cap, max(0, int((money - 80) // cost)))
        if quantity > 0:
            orders.append(["BUY_SEED", crop, quantity])
            money -= quantity * cost

    return orders[:10]


def agent(obs):
    if not isinstance(obs, dict):
        return _empty_action()
    farms = obs.get("farms", [])
    player = int(obs.get("player", 0) or 0)
    if not isinstance(farms, list) or player < 0 or player >= len(farms):
        return _empty_action()
    farm = farms[player]
    private = obs.get("private", {})
    if not isinstance(farm, dict) or not isinstance(private, dict):
        return _empty_action()
    day = max(0, int(obs.get("day", 0) or 0))
    hour = max(0, int(obs.get("hour", 0) or 0))
    market = obs.get("market", {})
    prices = market.get("prices", {}) if isinstance(market, dict) else {}
    if not isinstance(prices, dict):
        prices = {}
    farmer_action, hand_actions = _unit_plan(farm, private, day, hour, prices)
    market_actions = _market_plan(obs, farm, private, day, hour, farmer_action, hand_actions)
    return {"farmer": farmer_action, "hands": hand_actions, "market": market_actions}
