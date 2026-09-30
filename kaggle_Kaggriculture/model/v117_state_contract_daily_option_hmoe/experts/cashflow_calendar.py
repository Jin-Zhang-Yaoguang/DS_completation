"""I5c-2：只用当前合法状态构造多阶段资产—现金收据日历。"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Mapping

from schema import (ANIMAL_COST, BASE_PRICE, CROP_FACTS, CROPS, LAND_PRICES,
                    PRODUCTS, SEED_COST, CanonicalState, animal_kind, fib)


ANIMAL_RECEIPTS = {
    "GOOSE": (4, 1, "EGG"),
    "COW": (8, 2, "MILK"),
    "SHEEP": (6, 3, "WOOL"),
}


@dataclass(frozen=True)
class CalendarDecision:
    """日初冻结的可审计计划；不保存 Replay 或未来环境信息。"""

    lands: int
    crops: Mapping[str, int]
    animals: Mapping[str, int]
    hands: int
    cash_reserve: int
    purchase_budget: int
    feed_units_per_animal: int
    projected_receipts: int
    liquidatable_value: int
    upfront_commitment: int
    operating_commitment: int
    first_receipt_day: int
    admitted_units: int
    rejected_units: int
    minimum_projected_cash: int


def _staged_target(day: int, initial: int, cap: int, start_day: int,
                   interval_days: int) -> int:
    if day < start_day:
        return min(initial, cap)
    additions = 1 + (day - start_day) // max(1, interval_days)
    return min(cap, initial + additions)


def _inventory(state: CanonicalState) -> Counter[str]:
    result: Counter[str] = Counter({str(k): max(0, int(v)) for k, v in state.shed.items()})
    for inventory in state.inventories:
        result.update({str(k): max(0, int(v)) for k, v in inventory.items()})
    return result


def _liquidatable_value(state: CanonicalState, haircut_percent: int,
                        wheat_reserve: int) -> int:
    inventory = _inventory(state)
    inventory["WHEAT"] = max(0, inventory["WHEAT"] - max(0, wheat_reserve))
    return sum(
        int(quantity) * max(
            1,
            int(state.prices.get(item, BASE_PRICE[item])) * haircut_percent // 100,
        )
        for item, quantity in inventory.items()
        if item in PRODUCTS and quantity > 0
    )


def _existing_receipts(state: CanonicalState, window_days: int,
                       haircut_percent: int) -> tuple[int, int]:
    """保守投影已落地资产；未知年龄不猜，完全由当前 grid 计算。"""

    end_day = min(29, state.day + max(1, window_days))
    receipts = 0
    first_days: list[int] = []
    for row in state.grid:
        for tile in row:
            if not isinstance(tile, Mapping):
                continue
            if tile.get("kind") == "PLANT" and str(tile.get("crop") or "") in CROPS:
                crop = str(tile["crop"])
                facts = CROP_FACTS[crop]
                planted_day = int(tile.get("planted_day", state.day))
                age = max(0, state.day - planted_day)
                current_units = max(0, int(tile.get("yield_units", 0)))
                if current_units > 0:
                    receipt_day = state.day
                    units = current_units
                elif bool(facts["ongoing"]):
                    first_age = int(facts["first"])
                    interval = 1 if crop == "TOMATO" else 2
                    receipt_day = state.day + max(0, first_age - age)
                    units = 1
                    if receipt_day <= end_day:
                        units += min(
                            int(facts["max_yield"]) - 1,
                            max(0, end_day - receipt_day) // interval,
                        )
                else:
                    receipt_day = state.day + max(0, int(facts["mature"]) - age)
                    units = int(facts["max_yield"])
                if receipt_day <= end_day:
                    price = max(1, int(state.prices.get(crop, BASE_PRICE[crop])))
                    receipts += units * price * haircut_percent // 100
                    first_days.append(receipt_day)
                continue
            animal = animal_kind(tile)
            if animal not in ANIMAL_RECEIPTS:
                continue
            first, interval, product = ANIMAL_RECEIPTS[animal]
            placed_day = int(tile.get("placed_day", state.day))
            age = max(0, state.day - placed_day)
            current_units = max(0, int(tile.get("yield_units", 0)))
            receipt_day = state.day if current_units > 0 else state.day + max(0, first - age)
            if receipt_day > end_day:
                continue
            events = 1 + max(0, end_day - receipt_day) // interval
            units = current_units if current_units > 0 else interval + 1
            units += max(0, events - 1) * (interval + 1)
            price = max(1, int(state.prices.get(product, BASE_PRICE[product])))
            receipts += units * price * haircut_percent // 100
            first_days.append(receipt_day)
    return receipts, min(first_days, default=30)


def _candidate_value(state: CanonicalState, kind: str, item: str) -> float:
    horizon = max(0, 29 - state.day)
    if kind == "crop":
        facts = CROP_FACTS[item]
        if bool(facts["ongoing"]):
            interval = 1 if item == "TOMATO" else 2
            events = 0 if horizon < int(facts["first"]) else min(
                int(facts["max_yield"]),
                1 + (horizon - int(facts["first"])) // interval,
            )
            units = events
        else:
            cycle = int(facts["mature"]) + 1
            units = (horizon // cycle) * int(facts["max_yield"])
        return float(units * state.prices.get(item, BASE_PRICE[item]) - SEED_COST[item])
    first, interval, product = ANIMAL_RECEIPTS[item]
    events = 0 if horizon < first else 1 + (horizon - first) // interval
    gross = events * (interval + 1) * state.prices.get(product, BASE_PRICE[product])
    feed = horizon * state.prices.get("WHEAT", BASE_PRICE["WHEAT"])
    return float(gross - feed - ANIMAL_COST[item])


def build_calendar(
    state: CanonicalState,
    base_lands: int,
    base_crops: Mapping[str, int],
    base_animals: Mapping[str, int],
    base_hands: int,
    *,
    stage_assets_enabled: bool,
    opening_assets_enabled: bool,
    asset_admission_enabled: bool,
    receipt_budget_enabled: bool,
    terminal_replant_guard_enabled: bool,
    terminal_buffer_days: int,
    melon_add: int,
    melon_exit_day: int,
    cow_initial: int,
    cow_cap: int,
    cow_ramp_start_day: int,
    cow_ramp_interval_days: int,
    mid_cow_add: int,
    mid_cow_start_day: int,
    mid_cow_interval_days: int,
    sheep_initial: int,
    sheep_cap: int,
    sheep_ramp_start_day: int,
    sheep_ramp_interval_days: int,
    low_cash_reserve: int,
    low_cash_reserve_until_day: int,
    normal_cash_reserve: int,
    feed_units_per_animal: int,
    receipt_window_days: int,
    receipt_haircut_percent: int,
    purchase_budget_cap: int,
) -> CalendarDecision:
    """生成阶段目标，并按现金承诺上限逐单位准入新增资产。"""

    desired_crops = Counter({str(k): max(0, int(v)) for k, v in base_crops.items()})
    if (stage_assets_enabled or opening_assets_enabled) and state.day < melon_exit_day:
        desired_crops["MELON"] += max(0, melon_add)
    desired_animals = (
        {
            "SHEEP": _staged_target(
                state.day, sheep_initial, sheep_cap,
                sheep_ramp_start_day, sheep_ramp_interval_days,
            ),
            "COW": _staged_target(
                state.day, cow_initial, cow_cap,
                cow_ramp_start_day, cow_ramp_interval_days,
            ),
        }
        if stage_assets_enabled else
        {str(key): max(0, int(value)) for key, value in base_animals.items()}
    )
    if opening_assets_enabled and state.day < cow_ramp_start_day:
        desired_animals["COW"] = max(
            int(desired_animals.get("COW", 0)), min(cow_initial, cow_cap),
        )
    if mid_cow_add > 0 and state.day >= mid_cow_start_day:
        additions = min(
            mid_cow_add,
            1 + (state.day - mid_cow_start_day) // max(1, mid_cow_interval_days),
        )
        desired_animals["COW"] = int(desired_animals.get("COW", 0)) + additions
    desired_animals = {key: value for key, value in desired_animals.items() if value > 0}

    if terminal_replant_guard_enabled:
        remaining_days = max(0, 29 - state.day - max(0, terminal_buffer_days))
        for crop in CROPS:
            facts = CROP_FACTS[crop]
            payback_days = int(facts["first"] if bool(facts["ongoing"]) else facts["mature"])
            if remaining_days < payback_days:
                desired_crops[crop] = 0
        inventory = _inventory(state)
        for animal in tuple(desired_animals):
            first_receipt = ANIMAL_RECEIPTS[animal][0]
            if remaining_days < first_receipt:
                desired_animals[animal] = max(
                    int(state.animals.get(animal, 0)), int(inventory.get(animal, 0)),
                )

    reserve = low_cash_reserve if state.day < low_cash_reserve_until_day else normal_cash_reserve
    carried_assets = _inventory(state)
    existing_animals = Counter({str(k): max(0, int(v)) for k, v in state.animals.items()})
    existing_crops = Counter({str(k): max(0, int(v)) for k, v in state.crops.items()})
    wheat_reserve = feed_units_per_animal * sum(desired_animals.values())
    liquidatable = _liquidatable_value(state, receipt_haircut_percent, wheat_reserve)
    projected_receipts, first_receipt_day = _existing_receipts(
        state, receipt_window_days, receipt_haircut_percent,
    )

    current_hands = max(0, len(state.positions) - 1)
    hire_gap = max(0, base_hands - current_hands)
    hire_commitment = sum(fib(state.hires_today + offset) for offset in range(hire_gap))
    operating_commitment = (
        hire_commitment
        + max(0, sum(desired_animals.values()) - desired_crops.get("WHEAT", 0) // 2)
        * max(1, receipt_window_days)
        * state.prices.get("WHEAT", BASE_PRICE["WHEAT"])
    )
    commitment_room = max(
        0,
        state.money + liquidatable + projected_receipts - reserve - operating_commitment,
    )

    lands = max(state.lands, int(base_lands))
    land_cost = sum(
        LAND_PRICES[index]
        for index in range(max(0, state.lands - 1), max(0, lands - 1))
        if index < len(LAND_PRICES)
    )
    if asset_admission_enabled and land_cost > commitment_room:
        lands = state.lands
        land_cost = 0
    commitment_room -= land_cost

    admitted_crops = Counter({
        crop: min(desired_crops[crop], existing_crops[crop] + max(0, int(state.seeds.get(crop, 0))))
        for crop in CROPS
    })
    admitted_animals = Counter({
        animal: existing_animals[animal] + carried_assets[animal]
        for animal in desired_animals
    })
    candidates: list[tuple[float, int, str, str]] = []
    for crop in CROPS:
        have = existing_crops[crop] + max(0, int(state.seeds.get(crop, 0)))
        gap = max(0, desired_crops[crop] - have)
        cost = SEED_COST[crop]
        value = _candidate_value(state, "crop", crop)
        candidates.extend((value / max(1, cost), cost, "crop", crop) for _ in range(gap))
    for animal, target in desired_animals.items():
        gap = max(0, int(target) - admitted_animals[animal])
        cost = ANIMAL_COST[animal]
        value = _candidate_value(state, "animal", animal)
        candidates.extend((value / max(1, cost), cost, "animal", animal) for _ in range(gap))
    candidates.sort(key=lambda row: (-row[0], row[2] != "crop", row[3]))

    admitted_units = 0
    rejected_units = 0
    asset_commitment = land_cost
    for _, cost, kind, item in candidates:
        if asset_admission_enabled and cost > commitment_room:
            rejected_units += 1
            continue
        commitment_room -= cost
        asset_commitment += cost
        admitted_units += 1
        if kind == "crop":
            admitted_crops[item] += 1
        else:
            admitted_animals[item] += 1

    crop_targets = {
        crop: (
            min(desired_crops[crop], admitted_crops[crop])
            if terminal_replant_guard_enabled
            else max(existing_crops[crop], min(desired_crops[crop], admitted_crops[crop]))
        )
        for crop in CROPS
    }
    crops = {crop: target for crop, target in crop_targets.items() if target > 0}
    animals = {
        animal: max(existing_animals[animal], min(int(target), admitted_animals[animal]))
        for animal, target in desired_animals.items()
        if max(existing_animals[animal], min(int(target), admitted_animals[animal])) > 0
    }
    # 当前可变现库存可用于同 turn 的先卖后买；未来投影仅用于目标准入，不能提前支出。
    purchase_budget = min(
        max(0, purchase_budget_cap),
        max(0, state.money + (liquidatable if receipt_budget_enabled else 0) - reserve),
    )
    minimum_projected_cash = (
        state.money + liquidatable + projected_receipts
        - reserve - operating_commitment - asset_commitment
    )
    return CalendarDecision(
        lands=lands,
        crops=crops,
        animals=animals,
        hands=base_hands,
        cash_reserve=reserve,
        purchase_budget=purchase_budget,
        feed_units_per_animal=max(1, feed_units_per_animal),
        projected_receipts=projected_receipts,
        liquidatable_value=liquidatable,
        upfront_commitment=asset_commitment,
        operating_commitment=operating_commitment,
        first_receipt_day=first_receipt_day,
        admitted_units=admitted_units,
        rejected_units=rejected_units,
        minimum_projected_cash=minimum_projected_cash,
    )
