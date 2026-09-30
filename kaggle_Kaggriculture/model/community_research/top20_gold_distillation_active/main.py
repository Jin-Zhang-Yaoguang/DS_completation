"""V122 Top20 合同 HMoE：规则树路由 + 独立状态恢复执行器。"""

from __future__ import annotations

import copy
from collections import Counter
import json
import os
from pathlib import Path
from typing import Any, Mapping

from contract_features import ANIMALS, CROPS, PRODUCTS, state_features
from goal_features import unit_context, unit_features


HERE = Path(__file__).resolve().parent
MODEL = json.loads((HERE / "contract_hmoe_model.json").read_text(encoding="utf-8"))
SPATIAL = json.loads((HERE / "spatial_priors.json").read_text(encoding="utf-8"))
GOAL_ROUTER = json.loads((HERE / "unit_goal_router.json").read_text(encoding="utf-8"))
TARGET_ROUTERS = json.loads((HERE / "goal_target_routers.json").read_text(encoding="utf-8"))["routers"]
SHED_POINTS = ((4, 4), (5, 4), (4, 5), (5, 5))
SELLABLE = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
ANIMAL_STRUCTURE = {"COW": "PASTURE", "SHEEP": "PASTURE", "GOOSE": "COOP"}
_STATE = {0: {}, 1: {}}


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return default


def _seat(obs: Mapping[str, Any]) -> int:
    return 1 if _int(obs.get("player")) == 1 else 0


def _farm(obs: Mapping[str, Any]) -> Mapping[str, Any]:
    farms = list(obs.get("farms") or [{}, {}])
    return farms[_seat(obs)]


def _features(obs: dict, previous: dict | None) -> dict[str, float]:
    return state_features(obs, previous)


def _tree_leaf(tree: dict, features: dict[str, float]) -> dict:
    node = tree["root"]
    while "feature" in node:
        node = node["left"] if float(features.get(node["feature"], 0.0)) <= float(node["threshold"]) else node["right"]
    return node


def _classify(tree: dict, features: dict[str, float]) -> tuple[int, dict[int, float]]:
    leaf = _tree_leaf(tree, features)
    return int(leaf["leaf"]), {int(key): float(value) for key, value in leaf.get("probabilities", {}).items()}


def _regress(tree: dict, features: dict[str, float]) -> dict[str, float]:
    return {str(key): float(value) for key, value in _tree_leaf(tree, features)["value"].items()}


def _choose_macro(features: dict[str, float]) -> int:
    routed, probabilities = _classify(MODEL["macro_router"], features)
    if not probabilities:
        return routed
    best_probability = max(probabilities.values())
    candidates = [cluster for cluster, probability in probabilities.items() if probability >= max(0.10, best_probability * 0.35)]
    baseline_features = dict(features)
    routed_features = {**baseline_features, **{f"macro_contract_{i}": float(i == routed) for i in range(8)}}
    routed_value = _regress(MODEL["global_value_critic"], routed_features)["money_gap_delta"]
    selected, selected_value = routed, routed_value
    for cluster in candidates:
        candidate = {**baseline_features, **{f"macro_contract_{i}": float(i == cluster) for i in range(8)}}
        value = _regress(MODEL["global_value_critic"], candidate)["money_gap_delta"]
        # critic 只有明显优势才覆盖 Router，抑制观察性数据的反事实外推。
        if value > selected_value + 1800.0:
            selected, selected_value = cluster, value
    return selected


def _reset(obs: dict, step: int) -> dict:
    seat = _seat(obs)
    state = _STATE[seat]
    if step == 0 or step <= _int(state.get("last_step"), -1):
        state = {"last_step": step, "previous_day": None, "day_start": None, "macro": 4, "daily": 4, "daily_counts": {}, "intents": {}}
        _STATE[seat] = state
    return state


def _select_contracts(obs: dict, state: dict, day: int, hour: int) -> None:
    if hour != 0:
        return
    previous = state.get("day_start")
    state["previous_day"] = previous
    features = _features(obs, previous)
    if day % 3 == 0 or "macro" not in state:
        state["macro"] = _choose_macro(features)
    daily_features = dict(features)
    for cluster in range(8):
        daily_features[f"macro_contract_{cluster}"] = float(cluster == state["macro"])
    state["daily"], _ = _classify(MODEL["daily_router"], daily_features)
    state["global"] = _regress(MODEL["global_daily_expert"], daily_features)
    state["daily_counts"] = {}
    state["intents"] = {}
    state["day_start"] = copy.deepcopy(obs)


def _tile(grid: list, point: tuple[int, int]) -> Any:
    x, y = point
    if not (0 <= y < len(grid) and 0 <= x < len(grid[y])):
        return "LOCKED"
    return grid[y][x]


def _kind(tile: Any) -> str:
    if tile is None:
        return "EMPTY"
    return str(tile.get("kind") or "EMPTY") if isinstance(tile, Mapping) else str(tile)


def _animal(tile: Any) -> str:
    if not isinstance(tile, Mapping):
        return ""
    animal = tile.get("animal")
    return str(animal.get("kind") or "") if isinstance(animal, Mapping) else str(animal or "")


def _positions(farm: Mapping[str, Any]) -> list[tuple[int, int]]:
    raw = [farm.get("farmer") or [4, 4], *(farm.get("hands") or [])]
    return [(_int(value[0], 4), _int(value[1], 4)) for value in raw]


def _inventories(obs: Mapping[str, Any], count: int) -> list[dict[str, int]]:
    values = list((obs.get("private") or {}).get("inventories") or [])
    return [{str(k): _int(v) for k, v in dict(values[i] if i < len(values) else {}).items()} for i in range(count)]


def _distance(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _move(position: tuple[int, int], target: tuple[int, int]) -> list[str]:
    x, y = position
    tx, ty = target
    if x < tx: return ["EAST"]
    if x > tx: return ["WEST"]
    if y < ty: return ["SOUTH"]
    if y > ty: return ["NORTH"]
    return ["PASS"]


def _unlocked(grid: list) -> list[tuple[int, int]]:
    return [(x, y) for y, row in enumerate(grid) for x, tile in enumerate(row) if tile != "LOCKED"]


def _spatial_day(day: int) -> dict:
    return SPATIAL["days"][str(min(29, day + 1))]


def _livestock_slots(grid: list, day: int) -> list[tuple[int, int]]:
    points = _unlocked(grid)
    prior = [tuple(map(int, key.split(","))) for key in _spatial_day(day)["animal_rank"]]
    order = {point: index for index, point in enumerate(prior)}
    return sorted(points, key=lambda p: (order.get(p, 1000), min(_distance(p, s) for s in SHED_POINTS), abs(p[1] - 4), -p[1], -p[0]))


def _desired_animals(day: int) -> int:
    return max(4, _int(_spatial_day(day).get("target_animals"), 4))


def _desired_lands(day: int) -> int:
    return max(1, _int(_spatial_day(day).get("target_lands"), 1))


def _crop_for(day: int, point: tuple[int, int]) -> str:
    x, y = point
    learned = _spatial_day(day).get("crop_map", {}).get(f"{x},{y}")
    if learned in CROPS:
        return str(learned)
    if day < 6:
        return "MELON" if (x + 2 * y) % 4 == 0 else "WHEAT"
    if day < 11:
        return "MELON" if (x + y) % 5 == 0 else "STRAWBERRY"
    if day < 22:
        return "WHEAT" if (x + y) % 3 == 0 else "STRAWBERRY"
    if day < 27:
        return "CARROT" if (x + y) % 7 == 0 else "WHEAT"
    return "WHEAT"


def _animal_counts(grid: list) -> dict[str, int]:
    result = {animal: 0 for animal in ANIMALS}
    for point in _unlocked(grid):
        animal = _animal(_tile(grid, point))
        if animal in result:
            result[animal] += 1
    return result


def _crop_counts(grid: list) -> dict[str, int]:
    result = {crop: 0 for crop in CROPS}
    for point in _unlocked(grid):
        tile = _tile(grid, point)
        if isinstance(tile, Mapping) and tile.get("crop") in result:
            result[str(tile["crop"])] += 1
    return result


def _desired_crop_counts(day: int) -> Counter:
    prior = _spatial_day(day)
    scores = prior.get("crop_score", {})
    mapping = prior.get("crop_map", {})
    limit = _int(prior.get("target_crops"), 20)
    cells = sorted(mapping, key=lambda key: (-float(scores.get(key, 0.0)), key))[:limit]
    return Counter(str(mapping[key]) for key in cells)


def _all_stock(obs: Mapping[str, Any], inventories: list[dict[str, int]]) -> dict[str, int]:
    shed = {str(k): _int(v) for k, v in dict((obs.get("private") or {}).get("shed") or {}).items()}
    result = dict(shed)
    for inventory in inventories:
        for item, quantity in inventory.items():
            result[item] = result.get(item, 0) + quantity
    return result


def _task_for_tile(tile: Any, inventory: dict[str, int], day: int) -> list | None:
    animal = _animal(tile)
    if animal:
        if not bool(tile.get("fed_today")) and inventory.get("WHEAT", 0) > 0:
            return ["FEED"]
        if not bool(tile.get("cared_today")):
            return ["CARE"]
        if bool(tile.get("fertilizer_available")):
            return ["COLLECT_FERTILIZER"]
        if _int(tile.get("yield_units")) >= 2 or day >= 29 and _int(tile.get("yield_units")) > 0:
            return ["HARVEST"]
    if _kind(tile) == "PLANT":
        if _int(tile.get("yield_units")) >= 2 or day >= 28 and _int(tile.get("yield_units")) > 0:
            return ["HARVEST"]
        if not bool(tile.get("watered_today")):
            return ["WATER"]
    return None


def _fallback_unit_actions(obs: dict, day: int, hour: int) -> list[list]:
    farm = _farm(obs)
    grid = list(farm.get("tiles") or [])
    positions = _positions(farm)
    inventories = _inventories(obs, len(positions))
    shed = {str(k): _int(v) for k, v in dict((obs.get("private") or {}).get("shed") or {}).items()}
    stock = _all_stock(obs, inventories)
    animal_counts = _animal_counts(grid)
    animal_total = sum(animal_counts.values())
    livestock_slots = _livestock_slots(grid, day)[:_desired_animals(day)]
    livestock_set = set(livestock_slots)
    livestock_workers = min(max(2, (animal_total + 3) // 4), max(2, len(positions) // 3))
    actions: list[list] = [["PASS"] for _ in positions]
    reserved: set[tuple[int, int]] = set()

    if day == 0 and hour == 0 and positions and _kind(_tile(grid, positions[0])) == "EMPTY":
        actions[0] = ["BUILD_PASTURE"]
        reserved.add(positions[0])

    # 先处理站在目标格上的即时动作，每步都从真实状态重新判定。
    for actor, (position, inventory) in enumerate(zip(positions, inventories)):
        if actions[actor] != ["PASS"]:
            continue
        tile = _tile(grid, position)
        animal_role = actor < livestock_workers
        immediate = _task_for_tile(tile, inventory, day)
        if immediate and bool(_animal(tile)) != animal_role:
            immediate = None
        if immediate and position not in reserved:
            actions[actor], reserved = immediate, reserved | {position}
            continue
        carried_animal = next((a for a in ("SHEEP", "COW", "GOOSE") if inventory.get(a, 0) > 0), None)
        if animal_role and carried_animal and position in livestock_set:
            structure = ANIMAL_STRUCTURE[carried_animal]
            if _kind(tile) == "EMPTY":
                actions[actor], reserved = (["BUILD_COOP"] if structure == "COOP" else ["BUILD_PASTURE"]), reserved | {position}
                continue
            if _kind(tile) == structure and not _animal(tile):
                actions[actor], reserved = ["PLACE", carried_animal], reserved | {position}
                continue
        if day < 28 and position not in livestock_set and _kind(tile) == "EMPTY":
            seeds = {str(k): _int(v) for k, v in dict((obs.get("private") or {}).get("seeds") or {}).items()}
            crop = _crop_for(day, position)
            if seeds.get(crop, 0) > 0:
                actions[actor], reserved = ["PLANT", crop], reserved | {position}
                continue
        if position in SHED_POINTS:
            carried_products = sum(quantity for item, quantity in inventory.items() if item in SELLABLE and not (item == "WHEAT" and animal_total > 0))
            if carried_products > 0 or hour >= 21 and sum(inventory.values()) > 0:
                actions[actor] = ["DROP"]
                continue
            if animal_role and not carried_animal and sum(shed.get(a, 0) for a in ANIMALS) > 0 and animal_total < _desired_animals(day):
                choice = max(("SHEEP", "COW", "GOOSE"), key=lambda a: (shed.get(a, 0), a == "COW"))
                if shed.get(choice, 0) > 0:
                    actions[actor] = ["PICKUP", choice, 1]
                    shed[choice] -= 1
                    continue
            if animal_role and inventory.get("WHEAT", 0) == 0 and shed.get("WHEAT", 0) > 0 and animal_total:
                quantity = min(6, shed["WHEAT"])
                actions[actor] = ["PICKUP", "WHEAT", quantity]
                shed["WHEAT"] -= quantity
                continue

    # 为未分配单位生成状态任务，贪心匹配最近的高优先级目标。
    for actor, (position, inventory) in enumerate(zip(positions, inventories)):
        if actions[actor] != ["PASS"]:
            continue
        animal_role = actor < livestock_workers
        carried_animal = next((a for a in ("SHEEP", "COW", "GOOSE") if inventory.get(a, 0) > 0), None)
        carried_products = sum(quantity for item, quantity in inventory.items() if item in SELLABLE and not (item == "WHEAT" and animal_total > 0))
        if hour >= 19 and carried_products > 0:
            actions[actor] = _move(position, min(SHED_POINTS, key=lambda p: _distance(position, p)))
            continue
        candidates: list[tuple[int, int, tuple[int, int], list]] = []
        for point in _unlocked(grid):
            if point in reserved:
                continue
            tile = _tile(grid, point)
            animal = _animal(tile)
            if animal and animal_role:
                if not bool(tile.get("fed_today")) and inventory.get("WHEAT", 0) > 0: priority, order = 0, ["FEED"]
                elif not bool(tile.get("cared_today")): priority, order = 1, ["CARE"]
                elif bool(tile.get("fertilizer_available")): priority, order = 2, ["COLLECT_FERTILIZER"]
                elif _int(tile.get("yield_units")) >= 2: priority, order = 3, ["HARVEST"]
                else: continue
                candidates.append((priority, _distance(position, point), point, order))
            elif _kind(tile) == "PLANT" and not animal_role:
                if _int(tile.get("yield_units")) >= 2: candidates.append((4, _distance(position, point), point, ["HARVEST"]))
                elif not bool(tile.get("watered_today")): candidates.append((7, _distance(position, point), point, ["WATER"]))
        if animal_role and carried_animal:
            structure = ANIMAL_STRUCTURE[carried_animal]
            for point in livestock_slots:
                if point in reserved or _animal(_tile(grid, point)):
                    continue
                kind = _kind(_tile(grid, point))
                if kind in {"EMPTY", structure}:
                    candidates.append((2, _distance(position, point), point, ["PLACE", carried_animal]))
        elif animal_role and animal_total < _desired_animals(day) and sum(stock.get(a, 0) for a in ANIMALS) > 0:
            for point in SHED_POINTS:
                if _tile(grid, point) != "LOCKED":
                    candidates.append((3, _distance(position, point), point, ["PICKUP_ANIMAL"]))
        if animal_role and inventory.get("WHEAT", 0) == 0 and animal_total and shed.get("WHEAT", 0) > 0:
            for point in SHED_POINTS:
                if _tile(grid, point) != "LOCKED":
                    candidates.append((5, _distance(position, point), point, ["PICKUP_WHEAT"]))
        if day < 28 and not animal_role:
            seeds = {str(k): _int(v) for k, v in dict((obs.get("private") or {}).get("seeds") or {}).items()}
            crop_slots = sorted((p for p in _unlocked(grid) if p not in livestock_set and _kind(_tile(grid, p)) == "EMPTY"), key=lambda p: (p[1] % 5 > 1, p[1], p[0]))
            for point in crop_slots:
                crop = _crop_for(day, point)
                if seeds.get(crop, 0) > 0:
                    candidates.append((6, _distance(position, point), point, ["PLANT", crop]))
        if candidates:
            _, _, target, _ = min(candidates, key=lambda item: (item[0], item[1], item[2][1], item[2][0]))
            reserved.add(target)
            actions[actor] = _move(position, target)
            if position == target:
                # 实际动作在下一轮仍会由即时规则复核；这里处理普通农事。
                tile = _tile(grid, target)
                actions[actor] = _task_for_tile(tile, inventory, day) or ["PASS"]
        elif sum(inventory.values()) > 0:
            target = min(SHED_POINTS, key=lambda p: _distance(position, p))
            actions[actor] = ["DROP"] if position in SHED_POINTS else _move(position, target)
    return actions


def _goal_candidates(label: str, obs: dict, actor: int, day: int, livestock_slots: list[tuple[int, int]]) -> list[tuple[tuple[int, int], list]]:
    farm = _farm(obs); grid = list(farm.get("tiles") or []); positions = _positions(farm)
    inventories = _inventories(obs, len(positions)); inventory = inventories[actor]
    shed = {str(k): _int(v) for k, v in dict((obs.get("private") or {}).get("shed") or {}).items()}
    seeds = {str(k): _int(v) for k, v in dict((obs.get("private") or {}).get("seeds") or {}).items()}
    result: list[tuple[tuple[int, int], list]] = []
    if label == "DROP" and sum(inventory.values()) > 0:
        return [(point, ["DROP"]) for point in SHED_POINTS if _tile(grid, point) != "LOCKED"]
    if label.startswith("PICKUP_"):
        item = label.removeprefix("PICKUP_")
        if item == "OUTPUT":
            choices = [value for value in SELLABLE if value != "WHEAT" and shed.get(value, 0) > 0]
            item = max(choices, key=lambda value: shed[value]) if choices else ""
        if item and shed.get(item, 0) > 0:
            quantity = 1 if item in ANIMALS else min(8, shed[item])
            return [(point, ["PICKUP", item, quantity]) for point in SHED_POINTS if _tile(grid, point) != "LOCKED"]
        return []
    for point in _unlocked(grid):
        tile = _tile(grid, point); animal = _animal(tile); kind = _kind(tile)
        if label == "FEED" and animal and not bool(tile.get("fed_today")) and inventory.get("WHEAT", 0) > 0:
            result.append((point, ["FEED"]))
        elif label == "CARE" and animal and not bool(tile.get("cared_today")):
            result.append((point, ["CARE"]))
        elif label == "COLLECT_FERTILIZER" and animal and bool(tile.get("fertilizer_available")):
            result.append((point, ["COLLECT_FERTILIZER"]))
        elif label == "HARVEST_ANIMAL" and animal and _int(tile.get("yield_units")) >= 2:
            result.append((point, ["HARVEST"]))
        elif label == "HARVEST_CROP" and kind == "PLANT" and _int(tile.get("yield_units")) >= 2:
            result.append((point, ["HARVEST"]))
        elif label == "WATER" and kind == "PLANT" and not bool(tile.get("watered_today")):
            result.append((point, ["WATER"]))
        elif label == "FERTILIZE" and kind == "PLANT" and inventory.get("FERTILIZER", 0) > 0:
            result.append((point, ["FERTILIZE"]))
        elif label == "DIG" and kind in {"PLANT", "WEED"}:
            result.append((point, ["DIG"]))
        elif label == "BUILD_PASTURE" and point in livestock_slots and kind == "EMPTY":
            result.append((point, ["BUILD_PASTURE"]))
        elif label == "BUILD_COOP" and point in livestock_slots and kind == "EMPTY":
            result.append((point, ["BUILD_COOP"]))
        elif label.startswith("PLACE_"):
            item = label.removeprefix("PLACE_")
            if item in ANIMALS and inventory.get(item, 0) > 0 and point in livestock_slots and kind == ANIMAL_STRUCTURE[item] and not animal:
                result.append((point, ["PLACE", item]))
        elif label.startswith("PLANT_") and day < 28:
            crop = label.removeprefix("PLANT_")
            if crop in CROPS and seeds.get(crop, 0) > 0 and point not in livestock_slots and kind == "EMPTY":
                result.append((point, ["PLANT", crop]))
    return result


def _unit_actions(obs: dict, day: int, hour: int, state: dict) -> list[list]:
    farm = _farm(obs); positions = _positions(farm); grid = list(farm.get("tiles") or [])
    previous = state.get("previous_day")
    context = unit_context(obs, previous)
    livestock_slots = _livestock_slots(grid, day)[:_desired_animals(day)]
    fallback = _fallback_unit_actions(obs, day, hour)
    actions: list[list] = []
    reserved: set[tuple[int, int]] = set()
    intents = state.setdefault("intents", {})
    for actor, position in enumerate(positions):
        features = unit_features(obs, actor, previous, context)
        leaf = _tree_leaf(GOAL_ROUTER, features)
        probabilities = {str(k): float(v) for k, v in leaf.get("probabilities", {}).items()}
        labels = [str(leaf["leaf"]), *[key for key, _ in sorted(probabilities.items(), key=lambda item: item[1], reverse=True) if key != leaf["leaf"]]]
        selected = None
        stored = intents.get(actor)
        if stored:
            label = str(stored["label"]); target = tuple(stored["target"])
            matches = [(point, order) for point, order in _goal_candidates(label, obs, actor, day, livestock_slots) if point == target and point not in reserved]
            if matches and _int(stored.get("age"), 0) < 16:
                target, order = matches[0]; reserved.add(target)
                selected = order if position == target else _move(position, target)
                stored["age"] = _int(stored.get("age"), 0) + 1
            else:
                intents.pop(actor, None)
        for label in labels:
            if selected is not None:
                break
            if label == "IDLE":
                if selected is None:
                    selected = ["PASS"]
                continue
            candidates = [(target, order) for target, order in _goal_candidates(label, obs, actor, day, livestock_slots) if target not in reserved]
            if label == "FEED" and not candidates:
                candidates = [(target, order) for target, order in _goal_candidates("PICKUP_WHEAT", obs, actor, day, livestock_slots) if target not in reserved]
            if not candidates:
                continue
            target_scores = {}
            if label in TARGET_ROUTERS:
                target_leaf = _tree_leaf(TARGET_ROUTERS[label], features)
                target_scores = {str(k): float(v) for k, v in target_leaf.get("probabilities", {}).items()}
            target, order = max(candidates, key=lambda item: (
                target_scores.get(f"{item[0][0]},{item[0][1]}", 0.0),
                -_distance(position, item[0]), -item[0][1], -item[0][0],
            ))
            reserved.add(target)
            selected = order if position == target else _move(position, target)
            intents[actor] = {"label": label, "target": list(target), "age": 0}
            break
        if selected is None or selected == ["PASS"] and leaf.get("leaf") != "IDLE":
            selected = fallback[actor] if actor < len(fallback) else ["PASS"]
        actions.append(selected)
    return actions


def _market(obs: dict, state: dict, day: int, hour: int, inventories: list[dict[str, int]]) -> list[list]:
    farm = _farm(obs)
    money = _int(farm.get("money"))
    shed = {str(k): _int(v) for k, v in dict((obs.get("private") or {}).get("shed") or {}).items()}
    seeds = {str(k): _int(v) for k, v in dict((obs.get("private") or {}).get("seeds") or {}).items()}
    grid = list(farm.get("tiles") or [])
    animals = _animal_counts(grid)
    crops_now = _crop_counts(grid)
    total_animals = sum(animals.values())
    if day == 0 and hour == 0 and not farm.get("hands") and not any(shed.values()):
        return [["HIRE"], ["HIRE"], ["HIRE"], ["HIRE"], ["BUY_ANIMAL", "COW", 1], ["BUY_ANIMAL", "COW", 1],
                ["BUY_ANIMAL", "SHEEP", 1], ["BUY_ANIMAL", "SHEEP", 1], ["BUY_SEED", "MELON", 5], ["BUY_SEED", "WHEAT", 9]]
    sell_orders: list[list] = []
    global_target = state.get("global") or {}
    # 由全局专家的双方卖出预测决定兑现顺序；仍只卖真实仓库库存。
    priority = sorted(SELLABLE, key=lambda item: (
        global_target.get(f"rival_sell_{item}", 0.0) + global_target.get(f"own_early_sell_{item}", 0.0),
        (obs.get("market") or {}).get("prices", {}).get(item, 0),
    ), reverse=True)
    for item in priority:
        quantity = shed.get(item, 0)
        configured_reserve = _int(os.environ.get("V122_WHEAT_RESERVE"), 8)
        wheat_reserve = configured_reserve if day >= 8 else min(configured_reserve, 8)
        if quantity > 0 and (item != "WHEAT" or quantity > wheat_reserve or day >= 28):
            sell_orders.append(["SELL", item, quantity if day >= 28 else min(quantity, 40)])
    orders: list[list] = []
    if hour == 0:
        prototype = MODEL["daily_contract_prototypes"].get(str(state.get("daily", 0)), {})
        desired_hires = max(4, min(12, int(round(prototype.get("market_HIRE", 6)))))
        affordable_hires = max(0, min(desired_hires, money // 45))
        lands = len(farm.get("unlocked_quadrants") or [])
        missing_animals = max(0, _desired_animals(day) - total_animals - sum(shed.get(a, 0) for a in ANIMALS))
        crop_targets = _desired_crop_counts(day)
        deficits = sorted(CROPS, key=lambda crop: (crop_targets.get(crop, 0) - crops_now.get(crop, 0) - seeds.get(crop, 0), crop_targets.get(crop, 0)), reverse=True)
        if day < 6:
            # 低资本阶段先确保当天劳动力，再小批补种，防止一次买种吃光现金。
            orders.extend([["HIRE"] for _ in range(affordable_hires)])
            crop = deficits[0]
            missing = max(0, crop_targets.get(crop, 0) - crops_now.get(crop, 0) - seeds.get(crop, 0))
            if day < 28 and missing > 0 and len(orders) < 10:
                orders.append(["BUY_SEED", crop, min(missing, 5)])
            if seeds.get("WHEAT", 0) < 5 and len(orders) < 10:
                orders.append(["BUY_SEED", "WHEAT", min(5 - seeds.get("WHEAT", 0), 5)])
            missing_animals = min(missing_animals, 1)
        else:
            # 资本扩张阶段先锁定土地和生产资料，再用剩余订单雇工。
            if lands < _desired_lands(day) and money > (500 if lands == 1 else 2500):
                orders.append(["BUY_LAND"])
            for crop in deficits[:2]:
                missing = max(0, crop_targets.get(crop, 0) - crops_now.get(crop, 0) - seeds.get(crop, 0))
                if day < 28 and missing > 0 and len(orders) < 10:
                    orders.append(["BUY_SEED", crop, min(missing, 12)])
            missing_animals = min(missing_animals, 2)
        while missing_animals > 0 and len(orders) < 10 and day < 13:
            kind = "COW" if animals.get("COW", 0) <= animals.get("SHEEP", 0) + 2 else "SHEEP"
            orders.append(["BUY_ANIMAL", kind, 1]); missing_animals -= 1
        if day >= 6:
            orders.extend([["HIRE"] for _ in range(min(affordable_hires, 10 - len(orders)))])
    orders.extend(sell_orders)
    wheat_stock = shed.get("WHEAT", 0) + sum(inv.get("WHEAT", 0) for inv in inventories)
    if total_animals and wheat_stock < max(2, total_animals // 2) and len(orders) < 10:
        orders.append(["BUY_PRODUCT", "WHEAT", 1])
    return orders[:10]


def agent(obs, configuration=None):
    del configuration
    obs = dict(obs)
    seat, day, hour = _seat(obs), _int(obs.get("day")), _int(obs.get("hour"))
    step = day * 24 + hour
    state = _reset(obs, step)
    _select_contracts(obs, state, day, hour)
    farm = _farm(obs)
    positions = _positions(farm)
    inventories = _inventories(obs, len(positions))
    units = _unit_actions(obs, day, hour, state)
    action = {"farmer": units[0], "hands": units[1:], "market": _market(obs, state, day, hour, inventories)}
    counts = state.setdefault("daily_counts", {})
    for order in units:
        counts[order[0]] = counts.get(order[0], 0) + 1
    state["last_step"] = step
    return action


def model_status() -> dict:
    return {
        "kind": "v122_top20_contract_hmoe", "tape": False, "step_action_lookup": False,
        "primary_action_source": "independent_state_recovery_executor",
        "layers": ["3day_contract_router", "daily_contract_router", "global_value_and_market_expert"],
        "teacher_scope": "Top20 Replay distillation",
    }
