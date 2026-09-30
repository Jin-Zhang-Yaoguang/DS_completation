"""V121 原生规则 HMoE：冠军布局先验 + 状态闭环生产，不读取动作带。"""

from __future__ import annotations

from typing import Any, Mapping


CROPS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")
PRODUCTS = ("EGG", "MILK", "WOOL", "FERTILIZER", "CARROT", "TOMATO", "STRAWBERRY", "MELON")
SHED = {(4, 4), (5, 4), (4, 5), (5, 5)}
LIVESTOCK_SLOTS = ((4, 4), (3, 4), (4, 3), (3, 3), (2, 4))
CROP_SLOTS = tuple((x, y) for y in (0, 1, 2) for x in range(5))
_STATE = {0: {"last_step": -1}, 1: {"last_step": -1}}


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _seat(obs: Mapping[str, Any]) -> int:
    return 1 if _int(obs.get("player")) == 1 else 0


def _farm(obs: Mapping[str, Any]) -> Mapping[str, Any]:
    return list(obs.get("farms") or [{}, {}])[_seat(obs)]


def _positions(farm: Mapping[str, Any]) -> list[tuple[int, int]]:
    raw = [farm.get("farmer") or [4, 4], *list(farm.get("hands") or [])]
    return [(_int(value[0], 4), _int(value[1], 4)) for value in raw]


def _tile(grid: list, point: tuple[int, int]):
    x, y = point
    return grid[y][x] if 0 <= y < len(grid) and 0 <= x < len(grid[y]) else "LOCKED"


def _kind(tile: Any) -> str:
    if tile is None:
        return "EMPTY"
    return str(tile.get("kind") or "EMPTY") if isinstance(tile, Mapping) else str(tile)


def _animal(tile: Any) -> str:
    if not isinstance(tile, Mapping):
        return ""
    value = tile.get("animal")
    return str(value.get("kind") or "") if isinstance(value, Mapping) else str(value or "")


def _move(position: tuple[int, int], target: tuple[int, int]) -> list[str]:
    x, y = position
    tx, ty = target
    if x < tx: return ["EAST"]
    if x > tx: return ["WEST"]
    if y < ty: return ["SOUTH"]
    if y > ty: return ["NORTH"]
    return ["PASS"]


def _nearest(position: tuple[int, int], points: list[tuple[int, int]]) -> tuple[int, int] | None:
    return min(points, key=lambda p: (abs(position[0] - p[0]) + abs(position[1] - p[1]), p[1], p[0])) if points else None


def _inventory(obs: Mapping[str, Any], actor: int) -> dict:
    values = list((obs.get("private") or {}).get("inventories") or [])
    return dict(values[actor] or {}) if actor < len(values) else {}


def _desired_crop(day: int) -> str:
    # Top5 三日刷新后的共同相位：开局小麦，早中期草莓/西瓜，后期回到高周转作物。
    if day == 0: return "WHEAT"
    if day < 7: return "MELON" if day in (3, 4, 5, 6) else "STRAWBERRY"
    if day < 13: return "STRAWBERRY"
    if day < 24: return "WHEAT"
    return "CARROT" if day < 27 else "WHEAT"


def _crop_action(obs: Mapping[str, Any], actor: int, hour: int) -> list:
    farm, private = _farm(obs), dict(obs.get("private") or {})
    grid, pos = list(farm.get("tiles") or []), _positions(farm)[actor]
    desired = _desired_crop(_int(obs.get("day")))
    tile, inv = _tile(grid, pos), _inventory(obs, actor)
    if hour >= 18 and sum(_int(v) for v in inv.values()) > 0:
        if pos in SHED: return ["DROP"]
        target = _nearest(pos, list(SHED))
        return _move(pos, target or pos)
    if isinstance(tile, Mapping):
        if _int(tile.get("yield_units")) >= 2: return ["HARVEST"]
        if _kind(tile) == "PLANT" and str(tile.get("crop") or "") != desired and hour < 15:
            return ["DIG"]
        if _kind(tile) == "PLANT" and not bool(tile.get("watered_today")): return ["WATER"]
    seeds = dict(private.get("seeds") or {})
    if pos in CROP_SLOTS and _kind(tile) == "EMPTY":
        crop = desired if _int(seeds.get(desired)) > 0 else max(CROPS, key=lambda item: (_int(seeds.get(item)), -CROPS.index(item)))
        if _int(seeds.get(crop)) > 0: return ["PLANT", crop]
    harvest, water, empty = [], [], []
    for point in CROP_SLOTS:
        value = _tile(grid, point)
        if isinstance(value, Mapping) and _int(value.get("yield_units")) >= 2:
            harvest.append(point)
        elif isinstance(value, Mapping) and _kind(value) == "PLANT" and str(value.get("crop") or "") != desired and hour < 15:
            water.insert(0, point)
        elif isinstance(value, Mapping) and _kind(value) == "PLANT" and not bool(value.get("watered_today")):
            water.append(point)
        elif _kind(value) == "EMPTY" and sum(_int(seeds.get(item)) for item in CROPS) > 0:
            empty.append(point)
    target = _nearest(pos, harvest or water or empty)
    if target is not None: return _move(pos, target)
    if sum(_int(v) for v in inv.values()) > 0:
        if pos in SHED: return ["DROP"]
        return _move(pos, _nearest(pos, list(SHED)) or pos)
    return ["PASS"]


def _farmer_action(obs: Mapping[str, Any], hour: int) -> list:
    farm, private = _farm(obs), dict(obs.get("private") or {})
    grid, pos = list(farm.get("tiles") or []), _positions(farm)[0]
    inv, shed = _inventory(obs, 0), dict(private.get("shed") or {})
    product_load = sum(_int(inv.get(item)) for item in PRODUCTS)
    if product_load >= 8 or (hour >= 20 and product_load > 0):
        if pos in SHED: return ["DROP"]
        return _move(pos, _nearest(pos, list(SHED)) or pos)
    carried_animals = sum(_int(inv.get(item)) for item in ("COW", "SHEEP", "GOOSE"))
    shed_animals = sum(_int(shed.get(item)) for item in ("COW", "SHEEP", "GOOSE"))
    placed = [point for point in LIVESTOCK_SLOTS if _animal(_tile(grid, point))]
    if len(placed) < len(LIVESTOCK_SLOTS):
        if shed_animals > 0 and pos in SHED:
            item = max(("SHEEP", "COW", "GOOSE"), key=lambda value: _int(shed.get(value)))
            if _int(shed.get(item)) > 0: return ["PICKUP", item, _int(shed.get(item))]
        if shed_animals > 0 and carried_animals == 0:
            return _move(pos, _nearest(pos, list(SHED)) or pos)
        if _int(inv.get("WHEAT")) < 8 and _int(shed.get("WHEAT")) > 0 and pos in SHED:
            return ["PICKUP", "WHEAT", min(12, _int(shed.get("WHEAT")))]
        targets = [point for point in LIVESTOCK_SLOTS if not _animal(_tile(grid, point))]
        target = _nearest(pos, targets)
        if target is not None and pos != target: return _move(pos, target)
        tile = _tile(grid, pos)
        if _kind(tile) == "EMPTY": return ["BUILD_PASTURE"]
        if _kind(tile) == "PASTURE" and not _animal(tile):
            item = "SHEEP" if _int(inv.get("SHEEP")) > 0 else "COW" if _int(inv.get("COW")) > 0 else "GOOSE"
            if _int(inv.get(item)) > 0: return ["PLACE", item]
    tile = _tile(grid, pos)
    if _animal(tile):
        if not bool(tile.get("fed_today")) and _int(inv.get("WHEAT")) > 0: return ["FEED"]
        if not bool(tile.get("cared_today")): return ["CARE"]
        if bool(tile.get("fertilizer_available")): return ["COLLECT_FERTILIZER"]
        if _int(tile.get("yield_units")) >= 2: return ["HARVEST"]
    if _int(inv.get("WHEAT")) < 3 and _int(shed.get("WHEAT")) > 0:
        if pos in SHED: return ["PICKUP", "WHEAT", min(12, _int(shed.get("WHEAT")))]
        return _move(pos, _nearest(pos, list(SHED)) or pos)
    tasks = []
    for point in placed:
        value = _tile(grid, point)
        need = (not bool(value.get("fed_today")) and _int(inv.get("WHEAT")) > 0) or not bool(value.get("cared_today")) or bool(value.get("fertilizer_available")) or _int(value.get("yield_units")) >= 2
        if need: tasks.append(point)
    target = _nearest(pos, tasks)
    return _move(pos, target) if target is not None else ["PASS"]


def _market(obs: Mapping[str, Any], day: int, hour: int) -> list[list]:
    farm, private = _farm(obs), dict(obs.get("private") or {})
    money, shed = _int(farm.get("money")), dict(private.get("shed") or {})
    seeds = dict(private.get("seeds") or {})
    orders: list[list] = []
    # Top1 开局合同：5 个中心劳动力、5 个牲畜、上方两行小麦。
    if day == 0 and hour == 0 and not farm.get("hands") and sum(_int(v) for v in shed.values()) == 0:
        return [["BUY_PRODUCT", "WHEAT", 5], ["BUY_ANIMAL", "COW", 2], ["BUY_ANIMAL", "SHEEP", 1], ["BUY_SEED", "WHEAT", 10], *[["HIRE"] for _ in range(5)], ["BUY_PRODUCT", "WHEAT", 48]]
    if day == 0 and hour == 2 and _int(shed.get("WHEAT")) >= 48:
        return [["SELL", "WHEAT", 48], ["BUY_ANIMAL", "SHEEP", 2]]
    # 产品一进入仓库就兑现，抢在固定路线对手之前占用高价库存。
    for item in PRODUCTS:
        quantity = _int(shed.get(item))
        if quantity > 0: orders.append(["SELL", item, quantity])
    if hour == 0:
        wheat_need = max(0, 14 - _int(shed.get("WHEAT")))
        if wheat_need and money > 100: orders.append(["BUY_PRODUCT", "WHEAT", min(8, wheat_need)])
        desired = _desired_crop(day)
        seed_need = max(0, 18 - _int(seeds.get(desired)))
        if seed_need and money > 100: orders.append(["BUY_SEED", desired, min(18, seed_need)])
        orders.extend([ ["HIRE"] for _ in range(7) ])
    return orders[:10]


def agent(obs, configuration=None):
    del configuration
    seat, day, hour = _seat(obs), _int(obs.get("day")), _int(obs.get("hour"))
    step = day * 24 + hour
    if step == 0 or step <= _int(_STATE[seat].get("last_step"), -1): _STATE[seat] = {"last_step": step}
    else: _STATE[seat]["last_step"] = step
    farm = _farm(obs)
    count = 1 + len(list(farm.get("hands") or []))
    units = [_farmer_action(obs, hour)] + [_crop_action(obs, actor, hour) for actor in range(1, count)]
    return {"farmer": units[0], "hands": units[1:], "market": _market(obs, day, hour)}


def model_status() -> dict:
    return {"kind": "v121_native_rule_hmoe", "tape": False, "step_action_lookup": False, "primary_action_source": "state_conditioned_router_and_experts"}
