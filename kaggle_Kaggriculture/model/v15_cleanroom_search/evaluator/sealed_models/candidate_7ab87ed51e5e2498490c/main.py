_PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
_SALE_PRODUCTS = ("FERTILIZER", "WOOL", "MILK", "EGG", "MELON", "STRAWBERRY", "TOMATO", "CARROT", "WHEAT")
_ANIMALS = ("GOOSE", "COW", "SHEEP")
_ANIMAL_COST = {"GOOSE": 300, "COW": 400, "SHEEP": 500}
_PRODUCT_FOR = {"GOOSE": "EGG", "COW": "MILK", "SHEEP": "WOOL"}
_FIRST_YIELD = {"GOOSE": 4, "COW": 8, "SHEEP": 6}
_INTERVAL = {"GOOSE": 1, "COW": 2, "SHEEP": 3}
_MAX_HELD = {"GOOSE": 4, "COW": 6, "SHEEP": 6}
_SEED_COST = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
_CROP_READY = {"WHEAT": 4, "CARROT": 3, "TOMATO": 8, "STRAWBERRY": 10, "MELON": 10}

# Cells are ranked from the shed-facing corner of each quadrant outwards.  The
# first quadrant is diversified; later land leans toward eggs, whose market can
# absorb sustained production better than the premium-product curves.
_FIRST_ROLES = (
    "GOOSE", "GOOSE", "GOOSE", "GOOSE", "GOOSE",
    "GOOSE", None, None, None, None,
    None, None, None, None, None,
    None, None, None, None, None,
    None, None, None, None, None,
)
_LATER_ROLES = (
    None, None, None, None, None,
    None, None, None, None, None,
    None, None, None, None, None,
    None, None, None, None, None,
    None, None, None, None, None,
)


def _empty_action():
    return {"farmer": ["PASS"], "hands": [], "market": []}


def _number(value, default=0):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return default


def _access_tiles(board_size):
    half = board_size // 2
    return ((half - 1, half - 1), (half, half - 1), (half - 1, half), (half, half))


def _is_access(pos, board_size):
    return tuple(pos) in _access_tiles(board_size)


def _distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _nearest_access(pos, board_size):
    return min(_access_tiles(board_size), key=lambda p: (_distance(pos, p), p[1], p[0]))


def _move_toward(pos, target, unit_index):
    dx = target[0] - pos[0]
    dy = target[1] - pos[1]
    if dx == 0 and dy == 0:
        return ["PASS"]
    horizontal = abs(dx) > abs(dy) or (abs(dx) == abs(dy) and unit_index % 2 == 0)
    if horizontal and dx:
        return ["EAST" if dx > 0 else "WEST"]
    if dy:
        return ["SOUTH" if dy > 0 else "NORTH"]
    return ["EAST" if dx > 0 else "WEST"]


def _fib(index):
    a, b = 1, 1
    for _ in range(max(0, index)):
        a, b = b, a + b
    return a


def _inventories(private, count):
    raw = private.get("inventories", [])
    if not isinstance(raw, list):
        raw = []
    result = []
    for i in range(count):
        result.append(raw[i] if i < len(raw) and isinstance(raw[i], dict) else {})
    return result


def _inventory_total(inv):
    return sum(max(0, _number(v)) for v in inv.values()) if isinstance(inv, dict) else 0


def _has_animal(inv):
    if not isinstance(inv, dict):
        return False
    return any(_number(inv.get(a, 0)) > 0 for a in _ANIMALS)


def _sale_inventory(inv):
    if not isinstance(inv, dict):
        return 0
    return sum(max(0, _number(inv.get(item, 0))) for item in _PRODUCTS)


def _cell_rank(x, y, board_size):
    half = board_size // 2
    lx, ly = x % half, y % half
    inner_x = half - 1 if x < half else 0
    inner_y = half - 1 if y < half else 0
    cells = []
    for cy in range(half):
        for cx in range(half):
            cells.append((abs(cx - inner_x) + abs(cy - inner_y), cy, cx))
    cells.sort()
    key = (abs(lx - inner_x) + abs(ly - inner_y), ly, lx)
    return cells.index(key)


def _role_at(x, y, board_size):
    half = board_size // 2
    rank = _cell_rank(x, y, board_size)
    if x < half and y < half:
        return _FIRST_ROLES[rank % len(_FIRST_ROLES)]
    return _LATER_ROLES[rank % len(_LATER_ROLES)]


def _role_counts(tiles):
    counts = {a: 0 for a in _ANIMALS}
    board_size = len(tiles)
    for y, row in enumerate(tiles):
        if not isinstance(row, list):
            continue
        for x, tile in enumerate(row):
            if tile == "LOCKED":
                continue
            role = _role_at(x, y, board_size)
            if role in counts:
                counts[role] += 1
    return counts


def _installed_counts(tiles):
    counts = {a: 0 for a in _ANIMALS}
    for row in tiles:
        if not isinstance(row, list):
            continue
        for tile in row:
            if isinstance(tile, dict) and tile.get("animal") in counts:
                counts[tile["animal"]] += 1
    return counts


def _pipeline_counts(tiles, private, inventories):
    counts = _installed_counts(tiles)
    shed = private.get("shed", {})
    if not isinstance(shed, dict):
        shed = {}
    for animal in _ANIMALS:
        counts[animal] += max(0, _number(shed.get(animal, 0)))
        for inv in inventories:
            counts[animal] += max(0, _number(inv.get(animal, 0)))
    return counts


def _production_due(tile, day):
    animal = tile.get("animal")
    if animal not in _ANIMALS:
        return False
    placed = _number(tile.get("placed_day", day), day)
    elapsed = day + 1 - placed - _FIRST_YIELD[animal]
    return elapsed >= 0 and elapsed % _INTERVAL[animal] == 0


def _crop_choice(day, prices):
    if day <= 3 and max(1, _number(prices.get("MELON", 250), 250)) >= 120:
        return "MELON"
    choices = []
    if day <= 26:
        carrot = max(1, _number(prices.get("CARROT", 35), 35))
        choices.append(((3 * carrot - 20) / 3.0, "CARROT"))
    if day <= 25:
        wheat = max(1, _number(prices.get("WHEAT", 25), 25))
        choices.append(((4 * wheat - 10) / 4.0, "WHEAT"))
    if day <= 17:
        tomato = max(1, _number(prices.get("TOMATO", 60), 60))
        choices.append(((4 * tomato - 50) / 12.0, "TOMATO"))
    if day <= 13:
        strawberry = max(1, _number(prices.get("STRAWBERRY", 120), 120))
        choices.append(((4 * strawberry - 100) / 16.0, "STRAWBERRY"))
    if not choices:
        return None
    score, crop = max(choices)
    return crop if score > 0 else None


def _crop_harvestable(tile, day):
    if not (isinstance(tile, dict) and tile.get("kind") == "PLANT"):
        return False
    if _number(tile.get("yield_units", 0)) <= 0:
        return False
    crop = tile.get("crop")
    age = day - _number(tile.get("planted_day", day), day)
    if crop in ("TOMATO", "STRAWBERRY"):
        return age >= _CROP_READY.get(crop, 99)
    return age >= _CROP_READY.get(crop, 99)


def _projected_shed(private, actions):
    shed = private.get("shed", {})
    if not isinstance(shed, dict):
        shed = {}
    projected = {k: max(0, _number(v)) for k, v in shed.items()}
    raw = private.get("inventories", [])
    if not isinstance(raw, list):
        raw = []
    for i, action in enumerate(actions):
        if not (isinstance(action, list) and action and action[0] == "DROP"):
            continue
        inv = raw[i] if i < len(raw) and isinstance(raw[i], dict) else {}
        room = max(0, 100 - sum(projected.values()))
        for item, value in inv.items():
            n = min(room, max(0, _number(value)))
            if n > 0:
                projected[item] = projected.get(item, 0) + n
                room -= n
            if room <= 0:
                break
    return projected


def _unit_plan(farm, private, day, hour, prices):
    tiles = farm.get("tiles", [])
    if not isinstance(tiles, list) or not tiles:
        return ["PASS"], []
    board_size = len(tiles)
    positions = [farm.get("farmer", [0, 0])]
    hands = farm.get("hands", [])
    if isinstance(hands, list):
        positions.extend(hands)
    positions = [p if isinstance(p, list) and len(p) >= 2 else [0, 0] for p in positions]
    count = len(positions)
    inventories = _inventories(private, count)
    actions = [["PASS"] for _ in range(count)]
    used = set()
    terminal = day >= 29
    shed = private.get("shed", {})
    if not isinstance(shed, dict):
        shed = {}

    carried_products = sum(_sale_inventory(inv) for inv in inventories)
    shed_products = sum(max(0, _number(shed.get(item, 0))) for item in _PRODUCTS)
    crowded = carried_products + shed_products >= 82

    # Make every final-day collection liquidatable.  On ordinary days an early
    # mid-day unload activates only when the next automatic drop risks overflow.
    for i, pos in enumerate(positions):
        if _sale_inventory(inventories[i]) <= 0 or _has_animal(inventories[i]):
            continue
        dist = _distance(pos, _nearest_access(pos, board_size))
        final_return = terminal and hour >= max(10, 22 - dist)
        pressure_return = (not terminal) and crowded and hour >= max(12, 18 - dist)
        if final_return or pressure_return:
            if _is_access(pos, board_size):
                actions[i] = ["DROP"]
            else:
                actions[i] = _move_toward(pos, _nearest_access(pos, board_size), i)
            used.add(i)

    feed_targets = []
    if not terminal:
        for y, row in enumerate(tiles):
            if not isinstance(row, list):
                continue
            for x, tile in enumerate(row):
                if not (isinstance(tile, dict) and tile.get("animal") in _ANIMALS):
                    continue
                if tile.get("fed_today", False):
                    continue
                feed_targets.append((x, y))

    carried_wheat = sum(max(0, _number(inv.get("WHEAT", 0))) for inv in inventories)
    wheat_needed = max(0, len(feed_targets) - carried_wheat)
    wheat_available = max(0, _number(shed.get("WHEAT", 0)))
    for i, pos in enumerate(positions):
        if wheat_needed <= 0 or wheat_available <= 0:
            break
        if i in used or not _is_access(pos, board_size) or _has_animal(inventories[i]):
            continue
        if _number(inventories[i].get("WHEAT", 0)) > 0:
            continue
        quantity = min(2, wheat_needed, wheat_available)
        actions[i] = ["PICKUP", "WHEAT", quantity]
        used.add(i)
        wheat_needed -= quantity
        wheat_available -= quantity

    # Pull livestock only into workers that are not already serving as feeders.
    role_counts = _role_counts(tiles)
    pipeline = _pipeline_counts(tiles, private, inventories)
    carried = {a: sum(max(0, _number(inv.get(a, 0))) for inv in inventories) for a in _ANIMALS}
    for animal in _ANIMALS:
        available = min(max(0, _number(shed.get(animal, 0))), max(0, role_counts[animal] - pipeline[animal] + carried[animal]))
        for i, pos in enumerate(positions):
            if available <= 0:
                break
            if i in used or not _is_access(pos, board_size) or _has_animal(inventories[i]):
                continue
            if _number(inventories[i].get("WHEAT", 0)) > 0:
                continue
            actions[i] = ["PICKUP", animal, 1]
            used.add(i)
            available -= 1

    tasks = []
    plant_slots = []
    for y, row in enumerate(tiles):
        if not isinstance(row, list):
            continue
        for x, tile in enumerate(row):
            if tile == "LOCKED":
                continue
            role = _role_at(x, y, board_size)
            if isinstance(tile, dict) and tile.get("animal") in _ANIMALS:
                animal = tile["animal"]
                held = max(0, _number(tile.get("yield_units", 0)))
                if terminal:
                    dist = min(_distance((x, y), p) for p in _access_tiles(board_size))
                    if hour <= 20 - dist and held > 0:
                        tasks.append((0, x, y, ["HARVEST"], None))
                    if hour <= 20 - dist and tile.get("fertilizer_available", False):
                        tasks.append((1, x, y, ["COLLECT_FERTILIZER"], None))
                    continue
                if not tile.get("fed_today", False):
                    tasks.append((-2, x, y, ["FEED"], "WHEAT"))
                threshold = 3 if animal == "GOOSE" else 2
                if held >= _MAX_HELD[animal] - 1:
                    tasks.append((1, x, y, ["HARVEST"], None))
                elif held >= threshold:
                    tasks.append((5, x, y, ["HARVEST"], None))
                if tile.get("fertilizer_available", False):
                    tasks.append((3, x, y, ["COLLECT_FERTILIZER"], None))
                if tile.get("fed_today", False) and not tile.get("cared_today", False):
                    tasks.append((7, x, y, ["CARE"], None))
                continue

            if role is None:
                if isinstance(tile, dict) and tile.get("kind") == "PLANT":
                    dist = min(_distance((x, y), p) for p in _access_tiles(board_size))
                    if terminal:
                        if hour <= 20 - dist and _crop_harvestable(tile, day):
                            tasks.append((0, x, y, ["HARVEST"], None))
                    else:
                        if not tile.get("watered_today", False):
                            tasks.append((0, x, y, ["WATER"], None))
                        elif _crop_harvestable(tile, day):
                            tasks.append((4, x, y, ["HARVEST"], None))
                elif not terminal and isinstance(tile, dict) and tile.get("kind") == "WEED":
                    tasks.append((6, x, y, ["DIG"], None))
                elif not terminal and isinstance(tile, dict):
                    tasks.append((6, x, y, ["DIG"], None))
                elif not terminal and tile is None and hour < 18:
                    plant_slots.append((y, x))
                continue

            if terminal:
                continue
            if isinstance(tile, dict) and tile.get("kind") in ("COOP", "PASTURE"):
                expected = "COOP" if role == "GOOSE" else "PASTURE"
                if tile.get("kind") == expected:
                    tasks.append((2, x, y, ["PLACE", role], role))
                else:
                    tasks.append((2, x, y, ["DIG"], role))
            elif isinstance(tile, dict) and tile.get("kind") == "WEED":
                tasks.append((2, x, y, ["DIG"], role))
            elif isinstance(tile, dict):
                tasks.append((2, x, y, ["DIG"], role))
            elif tile is None:
                build = "BUILD_COOP" if role == "GOOSE" else "BUILD_PASTURE"
                tasks.append((2, x, y, [build], role))

    seeds = private.get("seeds", {})
    if not isinstance(seeds, dict):
        seeds = {}
    remaining_seeds = {crop: max(0, _number(seeds.get(crop, 0))) for crop in _SEED_COST}
    crop = _crop_choice(day, prices)
    if crop:
        for y, x in sorted(plant_slots):
            if remaining_seeds.get(crop, 0) <= 0:
                break
            tasks.append((8, x, y, ["PLANT", crop], None))
            remaining_seeds[crop] -= 1

    tasks.sort(key=lambda t: (t[0], t[2], t[1], t[3][0]))
    for priority, x, y, action, required in tasks:
        choices = []
        for i, pos in enumerate(positions):
            if i in used:
                continue
            inv = inventories[i]
            if required and _number(inv.get(required, 0)) <= 0:
                continue
            if not required and _has_animal(inv):
                continue
            choices.append((_distance(pos, (x, y)), i))
        if not choices:
            continue
        _, i = min(choices)
        if tuple(positions[i]) == (x, y):
            actions[i] = list(action)
        else:
            actions[i] = _move_toward(positions[i], (x, y), i)
        used.add(i)

    # A surplus carrier returns unused livestock instead of holding it forever.
    for i, pos in enumerate(positions):
        if i in used or not _has_animal(inventories[i]):
            continue
        target = _nearest_access(pos, board_size)
        if _is_access(pos, board_size):
            animal = next((a for a in _ANIMALS if _number(inventories[i].get(a, 0)) > 0), None)
            actions[i] = ["PLACE", animal, 1] if animal else ["PASS"]
        else:
            actions[i] = _move_toward(pos, target, i)

    return actions[0], actions[1:]


def _target_hands(animal_count, terminal):
    if terminal:
        return 12
    if animal_count < 16:
        return 8
    if animal_count < 31:
        return 10
    if animal_count < 46:
        return 11
    return 12


def _animal_value(animal, day, prices):
    remaining = max(0, 29 - day)
    if remaining <= 0:
        return -1
    wheat = max(1, _number(prices.get("WHEAT", 25), 25))
    fertilizer = max(1, _number(prices.get("FERTILIZER", 100), 100))
    product = max(1, _number(prices.get(_PRODUCT_FOR[animal], 1), 1))
    active = max(0, remaining - 1)
    productions = max(0, active - _FIRST_YIELD[animal] + 1)
    productions = (productions + _INTERVAL[animal] - 1) // _INTERVAL[animal]
    gross = active * fertilizer * 0.85 + productions * product * 1.45
    feed = active * wheat
    return gross - feed - _ANIMAL_COST[animal]


def _market_plan(obs, farm, private, day, hour, unit_actions):
    market = obs.get("market", {})
    if not isinstance(market, dict):
        market = {}
    prices = market.get("prices", {})
    if not isinstance(prices, dict):
        prices = {}
    tiles = farm.get("tiles", [])
    if not isinstance(tiles, list):
        tiles = []
    count = 1 + len(farm.get("hands", []) if isinstance(farm.get("hands", []), list) else [])
    inventories = _inventories(private, count)
    projected = _projected_shed(private, unit_actions)
    orders = []
    money = float(farm.get("money", 0) or 0)

    for item in _SALE_PRODUCTS:
        quantity = max(0, _number(projected.get(item, 0)))
        if item == "WHEAT" and day < 29:
            quantity = 0
        if quantity <= 0 or len(orders) >= 10:
            continue
        orders.append(["SELL", item, quantity])
        price = max(1, _number(prices.get(item, 1), 1))
        money += quantity * max(1, price // 2)
        projected[item] = max(0, projected.get(item, 0) - quantity)

    pipeline = _pipeline_counts(tiles, private, inventories)
    animal_count = sum(pipeline.values())
    target_hands = _target_hands(animal_count, day >= 29)
    hires_today = max(0, _number(farm.get("hires_today", 0)))
    if hour <= 2 and hires_today < target_hands:
        cap = 6
        for offset in range(min(cap, target_hands - hires_today)):
            if len(orders) >= 10:
                break
            cost = _fib(hires_today + offset)
            if money < cost + (0 if day >= 29 else 80):
                break
            orders.append(["HIRE"])
            money -= cost

    if day >= 29:
        return orders[:10]

    installed = _installed_counts(tiles)
    feed_basis = max(sum(installed.values()), animal_count)
    carried_wheat = sum(max(0, _number(inv.get("WHEAT", 0))) for inv in inventories)
    wheat_stock = max(0, _number(projected.get("WHEAT", 0))) + carried_wheat
    wheat_target = min(68, max(8, feed_basis + 6))
    wheat_missing = max(0, wheat_target - wheat_stock)
    wheat_price = max(1, _number(prices.get("WHEAT", 25), 25))
    if wheat_missing > 0 and len(orders) < 10:
        room = max(0, 96 - sum(max(0, _number(v)) for v in projected.values()))
        quantity = min(wheat_missing, room, max(0, int((money - 120) // wheat_price)))
        if quantity > 0:
            orders.append(["BUY_PRODUCT", "WHEAT", quantity])
            money -= quantity * wheat_price

    crop = _crop_choice(day, prices)
    if crop and len(orders) < 10:
        desired = 0
        board_size = len(tiles)
        for y, row in enumerate(tiles):
            if not isinstance(row, list):
                continue
            for x, tile in enumerate(row):
                if tile == "LOCKED" or _role_at(x, y, board_size) is not None:
                    continue
                if tile is None or (isinstance(tile, dict) and tile.get("kind") == "WEED"):
                    desired += 1
        seeds = private.get("seeds", {})
        if not isinstance(seeds, dict):
            seeds = {}
        available_seeds = max(0, _number(seeds.get(crop, 0)))
        for action in unit_actions:
            if isinstance(action, list) and len(action) >= 2 and action[0] == "PLANT" and action[1] == crop:
                available_seeds = max(0, available_seeds - 1)
        missing = max(0, desired - available_seeds)
        seed_cost = _SEED_COST[crop]
        cap = 12 if day <= 3 else 8
        quantity = min(missing, cap, max(0, int((money - 180) // seed_cost)))
        if quantity > 0:
            orders.append(["BUY_SEED", crop, quantity])
            money -= quantity * seed_cost

    # Expand only while enough season remains to repay both land and livestock.
    unlocked = farm.get("unlocked_quadrants", ["NW"])
    unlocked_count = len(unlocked) if isinstance(unlocked, list) else 1
    role_counts = _role_counts(tiles)
    slots = sum(role_counts.values())
    utilization = animal_count / max(1, slots)
    land_costs = (1000, 2000, 4000)
    if False and unlocked_count < 4 and day <= 14 and utilization >= 0.72 and len(orders) < 10:
        land_cost = land_costs[unlocked_count - 1]
        reserve = 600 if unlocked_count < 3 else 1100
        if money >= land_cost + reserve:
            orders.append(["BUY_LAND"])
            money -= land_cost

    # Fill the least represented role first, breaking ties by conservative
    # remaining-season value.  Per-turn caps prevent one purchase from starving
    # feed and the other product lines.
    deficits = {a: max(0, role_counts[a] - pipeline[a]) for a in _ANIMALS}
    ranked = []
    for animal in _ANIMALS:
        ratio = pipeline[animal] / max(1, role_counts[animal])
        ranked.append((ratio, -_animal_value(animal, day, prices), animal))
    ranked.sort()
    caps = {"GOOSE": 8 if day == 0 else 5, "COW": 2, "SHEEP": 2}
    for _, neg_value, animal in ranked:
        if len(orders) >= 10 or deficits[animal] <= 0:
            continue
        if day > 14 and -neg_value <= 0:
            continue
        cost = _ANIMAL_COST[animal]
        quantity = min(deficits[animal], caps[animal], max(0, int((money - 160) // cost)))
        if quantity > 0:
            orders.append(["BUY_ANIMAL", animal, quantity])
            money -= quantity * cost

    return orders[:10]


def agent(obs):
    if not isinstance(obs, dict):
        return _empty_action()
    farms = obs.get("farms", [])
    player = _number(obs.get("player", 0))
    if not isinstance(farms, list) or player < 0 or player >= len(farms):
        return _empty_action()
    farm = farms[player]
    private = obs.get("private", {})
    if not isinstance(farm, dict) or not isinstance(private, dict):
        return _empty_action()
    day = max(0, _number(obs.get("day", 0)))
    hour = max(0, _number(obs.get("hour", 0)))
    market = obs.get("market", {})
    prices = market.get("prices", {}) if isinstance(market, dict) else {}
    if not isinstance(prices, dict):
        prices = {}
    farmer_action, hand_actions = _unit_plan(farm, private, day, hour, prices)
    unit_actions = [farmer_action] + list(hand_actions)
    market_actions = _market_plan(obs, farm, private, day, hour, unit_actions)
    return {"farmer": farmer_action, "hands": hand_actions, "market": market_actions}
