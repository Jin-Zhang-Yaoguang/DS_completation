"""I5b：基于公开当前状态的日初资产价值与劳动容量联合准入。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from schema import ANIMAL_COST, BASE_PRICE, CROP_FACTS, CROPS, SEED_COST, CanonicalState


ANIMAL_FACTS = {
    "GOOSE": {"first": 4, "interval": 1, "product": "EGG"},
    "COW": {"first": 8, "interval": 2, "product": "MILK"},
    "SHEEP": {"first": 6, "interval": 3, "product": "WOOL"},
}


@dataclass(frozen=True)
class CapacityDecision:
    crops: Mapping[str, int]
    animals: Mapping[str, int]
    capacity_units: int
    requested_work: int
    admitted_work: int
    rejected_units: int


def _crop_value(state: CanonicalState, crop: str) -> float:
    facts = CROP_FACTS[crop]
    horizon = max(0, 29 - state.day)
    price = max(1, int(state.prices.get(crop, BASE_PRICE[crop])))
    if bool(facts["ongoing"]):
        interval = 1 if crop == "TOMATO" else 2
        events = 0 if horizon < int(facts["first"]) else min(
            int(facts["max_yield"]),
            1 + (horizon - int(facts["first"])) // interval,
        )
        units = events
        seed_uses = int(events > 0)
    else:
        cycle = int(facts["mature"]) + 1
        seed_uses = horizon // cycle
        units = seed_uses * int(facts["max_yield"])
    return float(max(0, units * price - seed_uses * SEED_COST[crop]))


def _animal_value(state: CanonicalState, animal: str) -> float:
    facts = ANIMAL_FACTS[animal]
    horizon = max(0, 29 - state.day)
    first = int(facts["first"])
    interval = int(facts["interval"])
    events = 0 if horizon < first else 1 + (horizon - first) // interval
    # 连续 FEED+CARE 时，生产日兑现此前积累的 care bonus；按完整 interval 保守计入。
    units = events * (interval + 1)
    product = str(facts["product"])
    revenue = units * max(1, int(state.prices.get(product, BASE_PRICE[product])))
    fertilizer = max(0, horizon - 1) * max(1, int(state.prices.get("FERTILIZER", 100)))
    feed = horizon * max(1, int(state.prices.get("WHEAT", BASE_PRICE["WHEAT"])))
    return float(max(0, revenue + fertilizer - feed - ANIMAL_COST[animal]))


def admit_targets(state: CanonicalState, desired_crops: Mapping[str, int],
                  desired_animals: Mapping[str, int], hands: int,
                  capacity_units_per_actor: int) -> CapacityDecision:
    """保留已落地资产，再按剩余生命周期净价值/工作量准入新增目标。"""

    capacity = max(1, hands + 1) * max(1, int(capacity_units_per_actor))
    crops = {crop: min(int(desired_crops.get(crop, 0)), int(state.crops.get(crop, 0))) for crop in CROPS}
    animals = {
        animal: min(int(target), int(state.animals.get(animal, 0)))
        for animal, target in desired_animals.items()
    }
    admitted_work = sum(crops.values()) + 2 * sum(animals.values())
    requested_work = sum(max(0, int(value)) for value in desired_crops.values()) + 2 * sum(
        max(0, int(value)) for value in desired_animals.values()
    )

    candidates: list[tuple[float, int, str, str]] = []
    for crop in CROPS:
        gap = max(0, int(desired_crops.get(crop, 0)) - crops[crop])
        value = _crop_value(state, crop)
        candidates.extend((value, 1, "crop", crop) for _ in range(gap))
    for animal, target in desired_animals.items():
        gap = max(0, int(target) - animals.get(animal, 0))
        value = _animal_value(state, animal) / 2.0
        candidates.extend((value, 2, "animal", animal) for _ in range(gap))
    candidates.sort(key=lambda row: (-row[0], row[2], row[3]))

    rejected = 0
    for _, work, kind, item in candidates:
        if admitted_work + work > capacity:
            rejected += 1
            continue
        admitted_work += work
        if kind == "crop":
            crops[item] = crops.get(item, 0) + 1
        else:
            animals[item] = animals.get(item, 0) + 1

    return CapacityDecision(
        crops={key: value for key, value in crops.items() if value > 0},
        animals={key: value for key, value in animals.items() if value > 0},
        capacity_units=capacity,
        requested_work=requested_work,
        admitted_work=admitted_work,
        rejected_units=rejected,
    )
