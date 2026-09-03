"""Kaggriculture v0: a conservative, stateless wheat-loop agent.

The submission intentionally uses only the stable public protocol.  It manages
three plots in the initially unlocked quadrant, never hires farm hands, and
always returns the complete farmer/hands/market action schema.
"""

CROP = "WHEAT"
SEED_PRICE = 10
TARGET_PLOT_COUNT = 3
TURNS_PER_DAY = 24
LAST_DAY = 29
LAST_PLANT_DAY = 27
LAST_ACTION_HOUR = 22  # episodeSteps=720 leaves day 29/hour 23 as terminal state

SELLABLE_PRODUCTS = (
    "WHEAT",
    "CARROT",
    "TOMATO",
    "STRAWBERRY",
    "MELON",
    "EGG",
    "MILK",
    "WOOL",
    "FERTILIZER",
)

MOVE_DELTAS = (
    ("NORTH", 0, -1),
    ("WEST", -1, 0),
    ("EAST", 1, 0),
    ("SOUTH", 0, 1),
)


def _get(value, key, default=None):
    """Read dict-like Kaggle Struct values without assuming a concrete type."""
    try:
        getter = getattr(value, "get", None)
        if getter is not None:
            return getter(key, default)
    except Exception:
        pass
    try:
        return value[key]
    except Exception:
        return default


def _nonnegative_int(value):
    try:
        return max(0, int(value))
    except (TypeError, ValueError, OverflowError):
        return 0


def _positive_total(inventory):
    try:
        values = inventory.values()
    except Exception:
        return 0
    return sum(_nonnegative_int(value) for value in values)


def _hands_pass(me):
    hands = _get(me, "hands", [])
    if not isinstance(hands, (list, tuple)):
        return []
    return [["PASS"] for _ in hands]


def _board_shape(tiles):
    if not isinstance(tiles, (list, tuple)) or not tiles:
        return 0, 0
    widths = [len(row) for row in tiles if isinstance(row, (list, tuple))]
    if len(widths) != len(tiles) or not widths:
        return 0, 0
    return min(widths), len(tiles)


def _tile_at(tiles, position):
    x, y = position
    width, height = _board_shape(tiles)
    if not (0 <= x < width and 0 <= y < height):
        return "LOCKED"
    return tiles[y][x]


def _kind(tile):
    return _get(tile, "kind")


def _is_wheat(tile):
    return _kind(tile) == "PLANT" and _get(tile, "crop") == CROP


def _distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _position(raw_position):
    if not isinstance(raw_position, (list, tuple)) or len(raw_position) < 2:
        raise ValueError("missing farmer position")
    return int(raw_position[0]), int(raw_position[1])


def _target_plots(tiles):
    """Pick three stable, usable plots nearest the NW shed-access tile."""
    width, height = _board_shape(tiles)
    if width < 2 or height < 2:
        return []

    half_x = max(1, width // 2)
    half_y = max(1, height // 2)
    anchor = (half_x - 1, half_y - 1)
    candidates = []
    for y in range(half_y):
        for x in range(half_x):
            tile = _tile_at(tiles, (x, y))
            usable = tile is None or _kind(tile) == "WEED" or _is_wheat(tile)
            if usable and tile != "LOCKED":
                candidates.append((x, y))

    candidates.sort(key=lambda point: (_distance(point, anchor), point[1], point[0]))
    return candidates[:TARGET_PLOT_COUNT]


def _wheat_tiles(tiles):
    width, height = _board_shape(tiles)
    result = []
    for y in range(height):
        for x in range(width):
            tile = _tile_at(tiles, (x, y))
            if _is_wheat(tile):
                result.append(((x, y), tile))
    return result


def _shed_access_tiles(tiles):
    width, height = _board_shape(tiles)
    if width < 2 or height < 2:
        return []
    left = width // 2 - 1
    top = height // 2 - 1
    candidates = (
        (left, top),
        (left + 1, top),
        (left, top + 1),
        (left + 1, top + 1),
    )
    in_bounds = [
        point
        for point in candidates
        if 0 <= point[0] < width and 0 <= point[1] < height
    ]
    unlocked = [point for point in in_bounds if _tile_at(tiles, point) != "LOCKED"]
    return unlocked or in_bounds


def _nearest(origin, positions):
    if not positions:
        return None
    return min(positions, key=lambda point: (_distance(origin, point), point[1], point[0]))


def _step_toward(origin, target, tiles):
    """Return a deterministic shortest legal step without entering locked land."""
    if origin == target:
        return ["PASS"]

    width, height = _board_shape(tiles)
    if width == 0 or height == 0:
        return ["PASS"]

    queue = [(origin, None)]
    visited = {origin}
    cursor = 0
    while cursor < len(queue):
        current, first_move = queue[cursor]
        cursor += 1
        neighbors = []
        for priority, (op, dx, dy) in enumerate(MOVE_DELTAS):
            nxt = (current[0] + dx, current[1] + dy)
            if not (0 <= nxt[0] < width and 0 <= nxt[1] < height):
                continue
            if nxt in visited or _tile_at(tiles, nxt) == "LOCKED":
                continue
            neighbors.append((_distance(nxt, target), priority, op, nxt))
        neighbors.sort()
        for _, _, op, nxt in neighbors:
            visited.add(nxt)
            move = first_move or op
            if nxt == target:
                return [move]
            queue.append((nxt, move))
    return ["PASS"]


def _inventory(private, index=0):
    inventories = _get(private, "inventories", [])
    if not isinstance(inventories, (list, tuple)) or index >= len(inventories):
        return {}
    inventory = inventories[index]
    return inventory if hasattr(inventory, "values") else {}


def _market_orders(me, private, plots, tiles, day, hour):
    orders = []
    shed = _get(private, "shed", {})
    for item in SELLABLE_PRODUCTS:
        amount = _nonnegative_int(_get(shed, item, 0))
        if amount > 0:
            orders.append(["SELL", item, amount])

    seeds = _nonnegative_int(_get(_get(private, "seeds", {}), CROP, 0))
    active = sum(1 for point in plots if _is_wheat(_tile_at(tiles, point)))
    needed = max(0, len(plots) - active - seeds)
    money = _nonnegative_int(_get(me, "money", 0))
    affordable = money // SEED_PRICE
    may_buy = day < LAST_PLANT_DAY or (
        day == LAST_PLANT_DAY and hour <= TURNS_PER_DAY - 6
    )
    quantity = min(needed, affordable)
    if may_buy and quantity > 0 and len(orders) < 10:
        orders.append(["BUY_SEED", CROP, quantity])
    return orders[:10]


def _go_to_shed(position, tiles, carried):
    access = _shed_access_tiles(tiles)
    if position in access:
        return ["DROP"] if carried > 0 else ["PASS"]
    target = _nearest(position, access)
    return _step_toward(position, target, tiles) if target is not None else ["PASS"]


def _final_crop_action(position, wheat, tiles, day, hour):
    """Choose only a crop cycle that can still be sold before terminal state."""
    access = _shed_access_tiles(tiles)
    if not access:
        return None

    plans = []
    for point, tile in wheat:
        age = day - _nonnegative_int(_get(tile, "planted_day", day))
        distance_to_crop = _distance(position, point)
        distance_to_shed = min(_distance(point, shed) for shed in access)
        yield_units = _nonnegative_int(_get(tile, "yield_units", 0))
        watered = bool(_get(tile, "watered_today", False))

        # A WATER action at wheat age 2..4 creates/increases harvestable yield.
        if not watered and 2 <= age <= 4:
            sell_hour = hour + distance_to_crop + 1 + 1 + distance_to_shed + 1
            if sell_hour <= LAST_ACTION_HOUR:
                plans.append((distance_to_crop, point[1], point[0], 0, point, "WATER"))

        # Existing yield may be harvested without spending a turn watering.
        if yield_units > 0 and age >= 2:
            sell_hour = hour + distance_to_crop + 1 + distance_to_shed + 1
            if sell_hour <= LAST_ACTION_HOUR:
                plans.append((distance_to_crop, point[1], point[0], 1, point, "HARVEST"))

    if not plans:
        return None
    plans.sort()
    _, _, _, _, target, operation = plans[0]
    if position == target:
        return [operation]
    return _step_toward(position, target, tiles)


def _decide(obs):
    player = int(_get(obs, "player", 0))
    farms = _get(obs, "farms", [])
    if not isinstance(farms, (list, tuple)) or not (0 <= player < len(farms)):
        raise ValueError("missing farm")

    me = farms[player]
    private = _get(obs, "private", {})
    tiles = _get(me, "tiles", [])
    if _board_shape(tiles) == (0, 0):
        raise ValueError("missing tiles")
    position = _position(_get(me, "farmer"))
    day = _nonnegative_int(_get(obs, "day", 0))
    hour = _nonnegative_int(_get(obs, "hour", 0))
    hands = _hands_pass(me)
    plots = _target_plots(tiles)
    market = _market_orders(me, private, plots, tiles, day, hour)
    wheat = _wheat_tiles(tiles)
    carried = _positive_total(_inventory(private, 0))

    def emit(farmer_action):
        return {"farmer": farmer_action, "hands": hands, "market": market}

    if day >= LAST_DAY:
        if carried > 0:
            return emit(_go_to_shed(position, tiles, carried))
        final_action = _final_crop_action(position, wheat, tiles, day, hour)
        if final_action is not None:
            return emit(final_action)
        return emit(_go_to_shed(position, tiles, 0))

    unwatered = [
        (point, tile)
        for point, tile in wheat
        if not bool(_get(tile, "watered_today", False))
    ]
    if unwatered:
        point, _ = min(
            unwatered,
            key=lambda entry: (
                -_nonnegative_int(_get(entry[1], "consecutive_unwatered", 0)),
                _distance(position, entry[0]),
                entry[0][1],
                entry[0][0],
            ),
        )
        return emit(["WATER"] if position == point else _step_toward(position, point, tiles))

    harvestable = [
        point
        for point, tile in wheat
        if _nonnegative_int(_get(tile, "yield_units", 0)) > 0
        and day - _nonnegative_int(_get(tile, "planted_day", day)) >= 2
    ]
    if harvestable:
        target = _nearest(position, harvestable)
        return emit(["HARVEST"] if position == target else _step_toward(position, target, tiles))

    if carried > 0:
        return emit(_go_to_shed(position, tiles, carried))

    diggable = []
    if day <= LAST_PLANT_DAY:
        for point in plots:
            distance = _distance(position, point)
            enough_time = hour + distance + 2 <= TURNS_PER_DAY - 1
            if _kind(_tile_at(tiles, point)) == "WEED" and enough_time:
                diggable.append(point)
    if diggable:
        target = _nearest(position, diggable)
        return emit(["DIG"] if position == target else _step_toward(position, target, tiles))

    seeds = _nonnegative_int(_get(_get(private, "seeds", {}), CROP, 0))
    plantable = []
    if seeds > 0 and day <= LAST_PLANT_DAY:
        for point in plots:
            distance = _distance(position, point)
            enough_time = hour + distance + 1 <= TURNS_PER_DAY - 1
            if _tile_at(tiles, point) is None and enough_time:
                plantable.append(point)
    if plantable:
        target = _nearest(position, plantable)
        action = ["PLANT", CROP] if position == target else _step_toward(position, target, tiles)
        return emit(action)

    return emit(_go_to_shed(position, tiles, 0))


def _safe_pass(obs):
    try:
        player = int(_get(obs, "player", 0))
        farms = _get(obs, "farms", [])
        me = farms[player] if isinstance(farms, (list, tuple)) and 0 <= player < len(farms) else {}
        hands = _hands_pass(me)
    except Exception:
        hands = []
    return {"farmer": ["PASS"], "hands": hands, "market": []}


def agent(obs):
    """Kaggle entry point.  Keep this as the final callable in the file."""
    try:
        return _decide(obs)
    except Exception:
        return _safe_pass(obs)
