"""Public-observation event aggregation for the V114 day-level SMDP.

Only an explicit allowlist of fields is read.  In particular, environment
seeds, opponent-private state and identity labels are never inspected.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any, Mapping, Optional, Tuple, Union

try:  # Package import.
    from .option_catalog import (
        BudgetTier,
        OptionId,
        OptionState,
        OptionTransition,
        RiskTier,
        transition_option,
    )
except ImportError:  # Direct-file import used by lightweight tooling.
    from option_catalog import (  # type: ignore
        BudgetTier,
        OptionId,
        OptionState,
        OptionTransition,
        RiskTier,
        transition_option,
    )


DEFAULT_EPISODE_STEPS = 720
DEFAULT_TERMINAL_WINDOW = 48
DEFAULT_CASH_ENTER_THRESHOLD = 500.0
DEFAULT_CASH_EXIT_THRESHOLD = 750.0
DEFAULT_SHED_ENTER_RATIO = 0.90
DEFAULT_SHED_EXIT_RATIO = 0.80
_MISSING = object()

_FIRST_YIELD_DAY = {
    "WHEAT": 2,
    "CARROT": 2,
    "MELON": 10,
    "TOMATO": 8,
    "STRAWBERRY": 10,
}
_ONGOING_CROPS = frozenset({"TOMATO", "STRAWBERRY"})


class EventType(str, Enum):
    DAY_BOUNDARY = "DAY_BOUNDARY"
    SHOP_UNLOCKED = "SHOP_UNLOCKED"
    CROP_BECAME_HARVESTABLE = "CROP_BECAME_HARVESTABLE"
    NEW_PRODUCTION_READY = "NEW_PRODUCTION_READY"
    CASH_CRISIS_ENTERED = "CASH_CRISIS_ENTERED"
    CASH_CRISIS_EXITED = "CASH_CRISIS_EXITED"
    SELL_INVENTORY_THRESHOLD_ENTERED = "SELL_INVENTORY_THRESHOLD_ENTERED"
    SELL_INVENTORY_THRESHOLD_EXITED = "SELL_INVENTORY_THRESHOLD_EXITED"
    SHED_CAPACITY_CRISIS = "SHED_CAPACITY_CRISIS"
    SHED_CAPACITY_CRISIS_RESOLVED = "SHED_CAPACITY_CRISIS_RESOLVED"
    OPTION_CONTRACT_FAILED = "OPTION_CONTRACT_FAILED"
    TERMINAL_WINDOW_ENTERED = "TERMINAL_WINDOW_ENTERED"
    EPISODE_DONE = "EPISODE_DONE"


HIGH_LEVEL_BOUNDARY_EVENTS = frozenset(
    {
        EventType.DAY_BOUNDARY,
        EventType.CASH_CRISIS_ENTERED,
        EventType.SELL_INVENTORY_THRESHOLD_ENTERED,
        EventType.SHED_CAPACITY_CRISIS,
        EventType.OPTION_CONTRACT_FAILED,
        EventType.TERMINAL_WINDOW_ENTERED,
        EventType.EPISODE_DONE,
    }
)


@dataclass(frozen=True)
class EventInputs:
    """Optional, observable event signals supplied by the caller.

    These fields deliberately contain no seed, opponent identity or opponent
    private state.  Numeric signals use hysteresis; boolean contract failure is
    latched until the caller explicitly reports ``False``.
    """

    status: Any = None
    done: Optional[bool] = None
    inventory_level: Optional[float] = None
    inventory_threshold: Optional[float] = None
    inventory_release_threshold: Optional[float] = None
    shed_load: Optional[float] = None
    shed_capacity: Optional[float] = None
    option_contract_failed: Optional[bool] = None
    shop_unlocked: Optional[bool] = None
    crop_became_harvestable: Optional[bool] = None
    new_production_ready: Optional[bool] = None


def _read(container: Any, key: str, default: Any = _MISSING) -> Any:
    """Read one field from a mapping or object without recursive discovery."""

    if isinstance(container, Mapping):
        return container.get(key, default)
    getter = getattr(container, "get", None)
    if callable(getter):
        try:
            return getter(key, default)
        except (TypeError, KeyError):
            pass
    return getattr(container, key, default)


def _first(container: Any, keys: tuple[str, ...], default: Any) -> Any:
    for key in keys:
        value = _read(container, key, _MISSING)
        if value is not _MISSING and value is not None:
            return value
    return default


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return default


def _as_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if number == number else None


def _own_farm(observation: Any) -> Any:
    farms = _read(observation, "farms", _MISSING)
    player = _as_int(_read(observation, "player", 0), 0)
    if isinstance(farms, (list, tuple)) and 0 <= player < len(farms):
        return farms[player]
    return _MISSING


def _own_cash(observation: Any) -> Optional[float]:
    """Read official public own cash first, then legacy aliases."""

    own_farm = _own_farm(observation)
    if own_farm is not _MISSING:
        cash = _read(own_farm, "money", _MISSING)
        if cash is not _MISSING:
            return _as_float(cash)

    cash = _first(observation, ("cash", "own_cash"), _MISSING)
    if cash is not _MISSING:
        return _as_float(cash)

    # Legacy fixtures used private.cash/money.  Official private state does not
    # expose cash, but retaining this fallback keeps the old API compatible.
    own_private = _read(observation, "private", _MISSING)
    if own_private is not _MISSING and own_private is not None:
        cash = _first(own_private, ("cash", "money"), _MISSING)
        if cash is not _MISSING:
            return _as_float(cash)
    return None


def _episode_steps(observation: Any) -> int:
    direct = _first(
        observation, ("episode_steps", "episodeSteps", "max_steps"), _MISSING
    )
    if direct is not _MISSING:
        return max(1, _as_int(direct, DEFAULT_EPISODE_STEPS))
    configuration = _read(observation, "configuration", _MISSING)
    if configuration is not _MISSING:
        configured = _first(
            configuration, ("episodeSteps", "episode_steps"), _MISSING
        )
        if configured is not _MISSING:
            return max(1, _as_int(configured, DEFAULT_EPISODE_STEPS))
    return DEFAULT_EPISODE_STEPS


def _coerce_event_inputs(value: Optional[Union[EventInputs, Mapping[str, Any]]]) -> EventInputs:
    if value is None:
        return EventInputs()
    if isinstance(value, EventInputs):
        return value
    if isinstance(value, Mapping):
        allowed = EventInputs.__dataclass_fields__
        return EventInputs(**{key: item for key, item in value.items() if key in allowed})
    raise TypeError("event_inputs must be EventInputs, a mapping, or None")


def _status_is_done(status: Any) -> bool:
    if status is None or status is _MISSING:
        return False
    value = getattr(status, "value", status)
    return str(value).upper() in {"DONE", "ERROR", "INVALID"}


def _shops(observation: Any) -> tuple[str, ...]:
    town = _read(observation, "town", _MISSING)
    shops = _read(town, "unlocked_shops", ()) if town is not _MISSING else ()
    if not isinstance(shops, (list, tuple)):
        return ()
    return tuple(str(shop) for shop in shops)


def _tiles(observation: Any) -> tuple[tuple[int, int, Mapping[str, Any]], ...]:
    farm = _own_farm(observation)
    rows = _read(farm, "tiles", ()) if farm is not _MISSING else ()
    result: list[tuple[int, int, Mapping[str, Any]]] = []
    if not isinstance(rows, (list, tuple)):
        return ()
    for y, row in enumerate(rows):
        if not isinstance(row, (list, tuple)):
            continue
        for x, tile in enumerate(row):
            if isinstance(tile, Mapping):
                result.append((x, y, tile))
    return tuple(result)


def _harvestable_ids(observation: Any) -> frozenset[tuple[int, int, str, int]]:
    day = _as_int(_read(observation, "day", 0), 0)
    result: set[tuple[int, int, str, int]] = set()
    for x, y, tile in _tiles(observation):
        if str(_read(tile, "kind", "")).upper() != "PLANT":
            continue
        crop = str(_read(tile, "crop", "")).upper()
        first_yield = _FIRST_YIELD_DAY.get(crop)
        planted_day = _as_int(_read(tile, "planted_day", day), day)
        yield_units = _as_float(_read(tile, "yield_units", 0)) or 0.0
        if first_yield is not None and day - planted_day >= first_yield and yield_units > 0:
            result.add((x, y, crop, planted_day))
    return frozenset(result)


def _production_levels(observation: Any) -> dict[tuple[int, int, str], float]:
    result: dict[tuple[int, int, str], float] = {}
    for x, y, tile in _tiles(observation):
        kind = str(_read(tile, "kind", "")).upper()
        crop = str(_read(tile, "crop", "")).upper()
        if kind == "PLANT" and crop not in _ONGOING_CROPS:
            continue
        if kind not in {"PLANT", "COOP", "PASTURE"}:
            continue
        units = _as_float(_read(tile, "yield_units", 0)) or 0.0
        result[(x, y, crop or kind)] = max(0.0, units)
    return result


def _own_shed_load(observation: Any) -> Optional[float]:
    private = _read(observation, "private", _MISSING)
    shed = _read(private, "shed", _MISSING) if private is not _MISSING else _MISSING
    if not isinstance(shed, Mapping):
        return None
    values = [_as_float(value) for value in shed.values()]
    return sum(value for value in values if value is not None)


def _shed_capacity(observation: Any) -> Optional[float]:
    direct = _first(observation, ("shed_capacity", "shedCapacity"), _MISSING)
    if direct is not _MISSING:
        return _as_float(direct)
    configuration = _read(observation, "configuration", _MISSING)
    if configuration is not _MISSING:
        configured = _first(configuration, ("shedCapacity", "shed_capacity"), _MISSING)
        if configured is not _MISSING:
            return _as_float(configured)
    return None


@dataclass(frozen=True)
class EventSnapshot:
    step: int
    hour: int
    cash: Optional[float]
    remaining_turns: int
    day_boundary: bool
    terminal_window: bool
    done: bool
    events: Tuple[EventType, ...]
    actions_remaining: int = 0
    boundary_event: Optional[EventType] = None


@dataclass(frozen=True)
class AggregationResult:
    state: OptionState
    snapshot: EventSnapshot
    transition: Optional[OptionTransition]


class EventAggregator:
    """Turn an allowlisted observation into debounced SMDP events."""

    def __init__(
        self,
        *,
        cash_enter_threshold: float = DEFAULT_CASH_ENTER_THRESHOLD,
        cash_exit_threshold: float = DEFAULT_CASH_EXIT_THRESHOLD,
        terminal_window_turns: int = DEFAULT_TERMINAL_WINDOW,
        shed_enter_ratio: float = DEFAULT_SHED_ENTER_RATIO,
        shed_exit_ratio: float = DEFAULT_SHED_EXIT_RATIO,
    ) -> None:
        self.cash_enter_threshold = float(cash_enter_threshold)
        self.cash_exit_threshold = float(cash_exit_threshold)
        self.terminal_window_turns = int(terminal_window_turns)
        self.shed_enter_ratio = float(shed_enter_ratio)
        self.shed_exit_ratio = float(shed_exit_ratio)
        if self.cash_exit_threshold <= self.cash_enter_threshold:
            raise ValueError("cash_exit_threshold must exceed cash_enter_threshold")
        if self.terminal_window_turns < 0:
            raise ValueError("terminal_window_turns must be non-negative")
        if not 0.0 <= self.shed_exit_ratio < self.shed_enter_ratio <= 1.0:
            raise ValueError("shed ratios must satisfy 0 <= exit < enter <= 1")
        self._inventory_latched = False
        self._shed_latched = False
        self._contract_latched = False
        self._last_step: Optional[int] = None
        self._last_shops: Optional[tuple[str, ...]] = None
        self._last_harvestable: Optional[frozenset[tuple[int, int, str, int]]] = None
        self._last_production: Optional[dict[tuple[int, int, str], float]] = None

    def _reset_episode_latches(self) -> None:
        self._inventory_latched = False
        self._shed_latched = False
        self._contract_latched = False
        self._last_shops = None
        self._last_harvestable = None
        self._last_production = None

    def observe(
        self,
        observation: Any,
        state: Optional[OptionState] = None,
        *,
        status: Any = None,
        done: Optional[bool] = None,
        event_inputs: Optional[Union[EventInputs, Mapping[str, Any]]] = None,
    ) -> tuple[OptionState, EventSnapshot]:
        state = OptionState() if state is None else state
        inputs = _coerce_event_inputs(event_inputs)
        step = max(0, _as_int(_first(observation, ("step", "turn"), 0), 0))
        if self._last_step is not None and step < self._last_step:
            self._reset_episode_latches()
        self._last_step = step
        hour = _as_int(_first(observation, ("hour",), step % 24), step % 24) % 24
        cash = _own_cash(observation)
        episode_steps = _episode_steps(observation)
        actions_remaining = max(0, episode_steps - 1 - step)
        if done is not None:
            is_done = bool(done)
        elif inputs.done is not None:
            is_done = bool(inputs.done)
        elif status is not None:
            is_done = _status_is_done(status)
        elif inputs.status is not None:
            is_done = _status_is_done(inputs.status)
        else:
            observed_done = bool(_first(observation, ("done", "terminated"), False))
            is_done = observed_done or _status_is_done(_read(observation, "status", None))
        terminal_window = is_done or actions_remaining <= self.terminal_window_turns

        day_boundary = hour == 0
        context_events: list[EventType] = []
        shops = _shops(observation)
        shop_unlocked = bool(inputs.shop_unlocked)
        if self._last_shops is not None:
            previous = Counter(self._last_shops)
            shop_unlocked = shop_unlocked or any(
                count > previous[name] for name, count in Counter(shops).items()
            )
        self._last_shops = shops

        harvestable = _harvestable_ids(observation)
        crop_ready = bool(inputs.crop_became_harvestable)
        if self._last_harvestable is not None:
            crop_ready = crop_ready or bool(harvestable - self._last_harvestable)
        self._last_harvestable = harvestable

        production = _production_levels(observation)
        production_ready = bool(inputs.new_production_ready)
        if self._last_production is not None:
            production_ready = production_ready or any(
                amount > self._last_production.get(key, 0.0)
                for key, amount in production.items()
            )
        self._last_production = production

        if day_boundary and shop_unlocked:
            context_events.append(EventType.SHOP_UNLOCKED)
        if day_boundary and crop_ready:
            context_events.append(EventType.CROP_BECAME_HARVESTABLE)
        if day_boundary and production_ready:
            context_events.append(EventType.NEW_PRODUCTION_READY)

        cash_crisis = state.cash_crisis
        cash_entered = False
        cash_exited = False
        if cash is not None:
            if not cash_crisis and cash <= self.cash_enter_threshold:
                cash_crisis = True
                cash_entered = True
            elif cash_crisis and cash >= self.cash_exit_threshold:
                cash_crisis = False
                cash_exited = True

        inventory_entered = False
        inventory_exited = False
        inventory_level = _as_float(inputs.inventory_level)
        inventory_threshold = _as_float(inputs.inventory_threshold)
        inventory_release = _as_float(inputs.inventory_release_threshold)
        if inventory_release is None and inventory_threshold is not None:
            inventory_release = 0.8 * inventory_threshold
        if inventory_level is not None and inventory_threshold is not None:
            if not self._inventory_latched and inventory_level >= inventory_threshold:
                self._inventory_latched = True
                inventory_entered = True
            elif (
                self._inventory_latched
                and inventory_release is not None
                and inventory_level <= inventory_release
            ):
                self._inventory_latched = False
                inventory_exited = True

        shed_entered = False
        shed_exited = False
        shed_load = _as_float(inputs.shed_load)
        if shed_load is None:
            shed_load = _own_shed_load(observation)
        shed_capacity = _as_float(inputs.shed_capacity)
        if shed_capacity is None:
            shed_capacity = _shed_capacity(observation)
        if shed_load is not None and shed_capacity is not None and shed_capacity > 0:
            ratio = shed_load / shed_capacity
            if not self._shed_latched and ratio >= self.shed_enter_ratio:
                self._shed_latched = True
                shed_entered = True
            elif self._shed_latched and ratio <= self.shed_exit_ratio:
                self._shed_latched = False
                shed_exited = True

        contract_entered = False
        if inputs.option_contract_failed is True and not self._contract_latched:
            self._contract_latched = True
            contract_entered = True
        elif inputs.option_contract_failed is False:
            self._contract_latched = False

        terminal_entered = terminal_window and not state.terminal_entered
        if is_done:
            boundary = EventType.EPISODE_DONE
        elif terminal_entered:
            boundary = EventType.TERMINAL_WINDOW_ENTERED
        elif cash_entered:
            boundary = EventType.CASH_CRISIS_ENTERED
        elif contract_entered:
            boundary = EventType.OPTION_CONTRACT_FAILED
        elif shed_entered:
            boundary = EventType.SHED_CAPACITY_CRISIS
        elif inventory_entered:
            boundary = EventType.SELL_INVENTORY_THRESHOLD_ENTERED
        elif day_boundary:
            boundary = EventType.DAY_BOUNDARY
        else:
            boundary = None

        events = list(context_events)
        if cash_exited:
            events.append(EventType.CASH_CRISIS_EXITED)
        if inventory_exited:
            events.append(EventType.SELL_INVENTORY_THRESHOLD_EXITED)
        if shed_exited:
            events.append(EventType.SHED_CAPACITY_CRISIS_RESOLVED)
        if boundary is not None:
            events.append(boundary)

        next_state = replace(
            state,
            cash_crisis=cash_crisis,
            last_observed_step=max(state.last_observed_step, step),
        )
        snapshot = EventSnapshot(
            step=step,
            hour=hour,
            cash=cash,
            remaining_turns=actions_remaining,
            day_boundary=day_boundary,
            terminal_window=terminal_window,
            done=is_done,
            events=tuple(events),
            actions_remaining=actions_remaining,
            boundary_event=boundary,
        )
        return next_state, snapshot

    def advance(
        self,
        observation: Any,
        state: Optional[OptionState] = None,
        *,
        requested_option: Union[str, OptionId, None] = None,
        budget_tier: Union[str, BudgetTier, None] = None,
        risk_tier: Union[str, RiskTier, None] = None,
        status: Any = None,
        done: Optional[bool] = None,
        event_inputs: Optional[Union[EventInputs, Mapping[str, Any]]] = None,
    ) -> AggregationResult:
        """Observe one turn and apply at most one deterministic transition.

        Terminal liquidation is forced exactly once.  A newly entered cash
        crisis requests recovery.  Otherwise the manager's request is checked
        against the day-boundary, minimum-duration and cooldown contracts.
        """

        next_state, snapshot = self.observe(
            observation,
            state,
            status=status,
            done=done,
            event_inputs=event_inputs,
        )
        transition: Optional[OptionTransition] = None

        if EventType.TERMINAL_WINDOW_ENTERED in snapshot.events:
            target: Union[str, OptionId, None] = OptionId.TERMINAL_LIQUIDATION
            emergency = True
        elif (
            next_state.cash_crisis
            and next_state.current_option is not OptionId.RECOVERY
        ):
            target = OptionId.RECOVERY
            emergency = True
        else:
            target = requested_option
            emergency = False

        if target is not None:
            transition = transition_option(
                next_state,
                target,
                snapshot.step,
                budget_tier=budget_tier,
                risk_tier=risk_tier,
                day_boundary=snapshot.day_boundary,
                emergency=emergency,
                recovery_resolved=not next_state.cash_crisis,
            )
            next_state = transition.state

        return AggregationResult(next_state, snapshot, transition)


__all__ = [
    "AggregationResult",
    "DEFAULT_CASH_ENTER_THRESHOLD",
    "DEFAULT_CASH_EXIT_THRESHOLD",
    "DEFAULT_EPISODE_STEPS",
    "DEFAULT_SHED_ENTER_RATIO",
    "DEFAULT_SHED_EXIT_RATIO",
    "DEFAULT_TERMINAL_WINDOW",
    "EventAggregator",
    "EventInputs",
    "EventSnapshot",
    "EventType",
    "HIGH_LEVEL_BOUNDARY_EVENTS",
]
