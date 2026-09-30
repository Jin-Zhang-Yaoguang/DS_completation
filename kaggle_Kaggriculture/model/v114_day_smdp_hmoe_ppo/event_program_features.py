"""Leakage-safe 427-dimensional features for the event-program Manager."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from enum import Enum
from typing import Any

import numpy as np

try:
    from .build_critic_dataset import critic_features
    from .event_program import (
        CASH_RESERVES,
        CROP_FIRST_YIELD_DAY,
        PRODUCTION_LINES,
        SELL_STYLES,
        TERMINAL_MODES,
        TERMINAL_START_STEP,
        WORKER_CAPS,
        MacroActionMask,
        MacroDecision,
        PlanState,
        observation_day,
        observation_step,
    )
except ImportError:  # Direct-file imports used by local runners.
    from build_critic_dataset import critic_features  # type: ignore
    from event_program import (  # type: ignore
        CASH_RESERVES,
        CROP_FIRST_YIELD_DAY,
        PRODUCTION_LINES,
        SELL_STYLES,
        TERMINAL_MODES,
        TERMINAL_START_STEP,
        WORKER_CAPS,
        MacroActionMask,
        MacroDecision,
        PlanState,
        observation_day,
        observation_step,
    )


CRITIC_FEATURE_DIM = 387
AUX_FEATURE_DIM = 40
MANAGER_FEATURE_DIM = CRITIC_FEATURE_DIM + AUX_FEATURE_DIM
TOTAL_EXECUTABLE_ACTIONS = 719
CASH_CRISIS_THRESHOLD = 500.0

EVENT_BUCKETS = (
    "DAY_BOUNDARY",
    "SHOP_UNLOCKED",
    "CROP_HARVESTABLE",
    "PRODUCTION_READY",
    "CASH_CRISIS",
    "INVENTORY_OR_SHED_CRISIS",
    "CONTRACT_FAILURE",
    "TERMINAL_OR_DONE",
)

SHOP_TYPES = (
    "BAKERY",
    "PIZZA_SHOP",
    "BRUNCH_SPOT",
    "YARN_STORE",
    "ICE_CREAM_SHOP",
    "PET_CAFE",
    "SMOOTHIE_SHOP",
    "FARMERS_MARKET",
)

DECISION_HEAD_VALUES = {
    "production_line": tuple(PRODUCTION_LINES),
    "worker_cap": tuple(WORKER_CAPS),
    "cash_reserve": tuple(CASH_RESERVES),
    "sell_style": tuple(SELL_STYLES),
    "terminal_mode": tuple(TERMINAL_MODES),
}

FEATURE_SCHEMA = {
    "schema": "kaggriculture-v114-event-program-manager-features-v1",
    "input_dim": MANAGER_FEATURE_DIM,
    "critic": {
        "offset": 0,
        "length": CRITIC_FEATURE_DIM,
        "encoder": "v113_public_observation_critic_aggregation",
    },
    "aux": {
        "offset": CRITIC_FEATURE_DIM,
        "length": AUX_FEATURE_DIM,
        "segments": [
            {"name": "current_event", "length": 8, "values": list(EVENT_BUCKETS)},
            {"name": "public_shop_counts", "length": 8, "values": list(SHOP_TYPES)},
            {
                "name": "harvestable_crop_counts",
                "length": 5,
                "values": [item.value for item in PRODUCTION_LINES],
            },
            {
                "name": "current_decision_one_hot",
                "length": 16,
                "values": {
                    name: [getattr(value, "value", value) for value in values]
                    for name, values in DECISION_HEAD_VALUES.items()
                },
            },
            {"name": "day_progress", "length": 1, "formula": "hour/24"},
            {
                "name": "remaining_executable_actions_ratio",
                "length": 1,
                "formula": "max(0,719-step)/719",
            },
            {
                "name": "cash_crisis",
                "length": 1,
                "formula": "own_public_cash<500",
            },
        ],
    },
    "forbidden_inputs": ["environment_seed", "opponent_id", "opponent_private"],
}


def _read(container: Any, key: str, default: Any = None) -> Any:
    if isinstance(container, Mapping):
        return container.get(key, default)
    getter = getattr(container, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(container, key, default)


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError, OverflowError):
        return float(default)


def _own_farm(observation: Any) -> Mapping[str, Any]:
    farms = list(_read(observation, "farms", []) or [])
    player = int(_number(_read(observation, "player", 0), 0))
    if 0 <= player < len(farms) and isinstance(farms[player], Mapping):
        return farms[player]
    return {}


def _event_name(current_event: Any, observation: Any, cash_crisis: bool) -> str:
    if current_event is not None:
        raw = current_event.value if isinstance(current_event, Enum) else current_event
        name = str(raw).upper()
        aliases = {
            "CROP_BECAME_HARVESTABLE": "CROP_HARVESTABLE",
            "NEW_PRODUCTION_READY": "PRODUCTION_READY",
            "CASH_CRISIS_ENTERED": "CASH_CRISIS",
            "CASH_CRISIS_EXITED": "CASH_CRISIS",
            "SELL_INVENTORY_THRESHOLD_ENTERED": "INVENTORY_OR_SHED_CRISIS",
            "SELL_INVENTORY_THRESHOLD_EXITED": "INVENTORY_OR_SHED_CRISIS",
            "SHED_CAPACITY_CRISIS": "INVENTORY_OR_SHED_CRISIS",
            "SHED_CAPACITY_CRISIS_RESOLVED": "INVENTORY_OR_SHED_CRISIS",
            "OPTION_CONTRACT_FAILED": "CONTRACT_FAILURE",
            "TERMINAL_WINDOW_ENTERED": "TERMINAL_OR_DONE",
            "EPISODE_DONE": "TERMINAL_OR_DONE",
        }
        name = aliases.get(name, name)
        if name not in EVENT_BUCKETS:
            raise ValueError(f"unsupported event bucket: {raw!r}")
        return name
    step = observation_step(observation)
    if step >= TERMINAL_START_STEP:
        return "TERMINAL_OR_DONE"
    if cash_crisis:
        return "CASH_CRISIS"
    return "DAY_BOUNDARY"


def _public_shop_counts(observation: Any) -> np.ndarray:
    town = _read(observation, "town", {}) or {}
    shops = list(_read(town, "unlocked_shops", []) or [])
    counts = Counter(str(shop).upper() for shop in shops)
    return np.asarray([counts[name] for name in SHOP_TYPES], dtype=np.float32)


def _harvestable_crop_counts(observation: Any) -> np.ndarray:
    day = observation_day(observation)
    result = Counter()
    tiles = list(_read(_own_farm(observation), "tiles", []) or [])
    for row in tiles:
        for tile in list(row or []):
            if not isinstance(tile, Mapping) or str(_read(tile, "kind", "")).upper() != "PLANT":
                continue
            crop = str(_read(tile, "crop", "")).upper()
            first_yield = CROP_FIRST_YIELD_DAY.get(crop)
            planted_day = int(_number(_read(tile, "planted_day", day), day))
            yield_units = _number(_read(tile, "yield_units", 0), 0)
            if first_yield is not None and day - planted_day >= first_yield and yield_units > 0:
                result[crop] += 1
    return np.asarray([result[line.value] for line in PRODUCTION_LINES], dtype=np.float32)


def _decision(value: MacroDecision | PlanState | None) -> MacroDecision | None:
    if isinstance(value, PlanState):
        return value.decision
    if value is None or isinstance(value, MacroDecision):
        return value
    raise TypeError("current_decision must be MacroDecision, PlanState, or None")


def _decision_one_hot(value: MacroDecision | PlanState | None) -> np.ndarray:
    current = _decision(value)
    result: list[float] = []
    fields = {
        "production_line": None if current is None else current.production_line,
        "worker_cap": None if current is None else current.worker_cap,
        "cash_reserve": None if current is None else current.cash_reserve,
        "sell_style": None if current is None else current.sell_style,
        "terminal_mode": None if current is None else current.terminal_mode,
    }
    for name, values in DECISION_HEAD_VALUES.items():
        result.extend(float(fields[name] == candidate) for candidate in values)
    return np.asarray(result, dtype=np.float32)


def encode_event_program_features(
    observation: Mapping[str, Any],
    *,
    current_decision: MacroDecision | PlanState | None = None,
    current_event: Any = None,
) -> np.ndarray:
    """Encode only fields visible to the acting player into exactly 427 floats."""

    critic = np.asarray(critic_features(observation), dtype=np.float32)
    if critic.shape != (CRITIC_FEATURE_DIM,):
        raise ValueError(
            f"critic encoder must return {CRITIC_FEATURE_DIM} values, got {critic.shape}"
        )
    own_cash = _number(_read(_own_farm(observation), "money", 0), 0)
    cash_crisis = own_cash < CASH_CRISIS_THRESHOLD
    event = _event_name(current_event, observation, cash_crisis)
    event_one_hot = np.asarray(
        [float(name == event) for name in EVENT_BUCKETS], dtype=np.float32
    )
    step = observation_step(observation)
    hour = int(_number(_read(observation, "hour", step % 24), step % 24)) % 24
    scalars = np.asarray(
        [
            hour / 24.0,
            max(0, TOTAL_EXECUTABLE_ACTIONS - step) / TOTAL_EXECUTABLE_ACTIONS,
            float(cash_crisis),
        ],
        dtype=np.float32,
    )
    aux = np.concatenate(
        [
            event_one_hot,
            _public_shop_counts(observation),
            _harvestable_crop_counts(observation),
            _decision_one_hot(current_decision),
            scalars,
        ]
    ).astype(np.float32)
    if aux.shape != (AUX_FEATURE_DIM,):
        raise AssertionError(f"aux feature contract drifted: {aux.shape}")
    features = np.concatenate([critic, aux]).astype(np.float32)
    if features.shape != (MANAGER_FEATURE_DIM,):
        raise AssertionError(f"manager feature contract drifted: {features.shape}")
    if not np.all(np.isfinite(features)):
        raise ValueError("manager features contain non-finite values")
    return features


def macro_action_mask_arrays(mask: MacroActionMask) -> dict[str, np.ndarray]:
    """Convert the semantic mask into the five fixed categorical head masks."""

    allowed = {
        "production_line": set(mask.production_lines),
        "worker_cap": set(mask.worker_caps),
        "cash_reserve": set(mask.cash_reserves),
        "sell_style": set(mask.sell_styles),
        "terminal_mode": set(mask.terminal_modes),
    }
    return {
        name: np.asarray([[candidate in allowed[name] for candidate in values]], dtype=np.bool_)
        for name, values in DECISION_HEAD_VALUES.items()
    }


__all__ = [
    "AUX_FEATURE_DIM",
    "CRITIC_FEATURE_DIM",
    "DECISION_HEAD_VALUES",
    "EVENT_BUCKETS",
    "FEATURE_SCHEMA",
    "MANAGER_FEATURE_DIM",
    "SHOP_TYPES",
    "encode_event_program_features",
    "macro_action_mask_arrays",
]
