"""Independent V114 V9 event-program policy primitives.

The module is deliberately self-contained.  It compiles a day-persistent macro
decision into deterministic Kaggriculture unit and market actions using only the
current, legally visible observation.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Any, Mapping, Sequence


class _StringEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class ProductionLine(_StringEnum):
    WHEAT = "WHEAT"
    CARROT = "CARROT"
    TOMATO = "TOMATO"
    STRAWBERRY = "STRAWBERRY"
    MELON = "MELON"


class SellStyle(_StringEnum):
    IMMEDIATE = "IMMEDIATE"
    PRICE_GATE = "PRICE_GATE"
    HOLD = "HOLD"


class TerminalMode(_StringEnum):
    NORMAL = "NORMAL"
    LIQUIDATE = "LIQUIDATE"


PRODUCTION_LINES = tuple(ProductionLine)
WORKER_CAPS = (1, 2, 4)
CASH_RESERVES = (0, 500, 1500)
SELL_STYLES = tuple(SellStyle)
TERMINAL_MODES = tuple(TerminalMode)

PRODUCTS = (
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

SEED_COST = {
    ProductionLine.WHEAT: 10,
    ProductionLine.CARROT: 20,
    ProductionLine.TOMATO: 50,
    ProductionLine.STRAWBERRY: 100,
    ProductionLine.MELON: 80,
}

BASE_PRICE = {
    "WHEAT": 25,
    "CARROT": 35,
    "TOMATO": 60,
    "STRAWBERRY": 120,
    "MELON": 250,
    "EGG": 50,
    "MILK": 160,
    "WOOL": 200,
    "FERTILIZER": 100,
}

CROP_FIRST_YIELD_DAY = {
    "WHEAT": 2,
    "CARROT": 2,
    "TOMATO": 8,
    "STRAWBERRY": 10,
    "MELON": 10,
}

ONE_TIME_CROPS = frozenset({"WHEAT", "CARROT", "MELON"})
TERMINAL_MANAGER_START_STEP = 648
TERMINAL_START_STEP = 671
MAX_MARKET_ORDERS = 10


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    getter = getattr(value, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(value, key, default)


def _integer(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def observation_step(observation: Any) -> int:
    explicit = _get(observation, "step", None)
    if explicit is not None:
        return max(0, _integer(explicit))
    return max(
        0,
        _integer(_get(observation, "day", 0)) * 24
        + _integer(_get(observation, "hour", 0)),
    )


def observation_day(observation: Any) -> int:
    explicit = _get(observation, "day", None)
    if explicit is not None:
        return max(0, _integer(explicit))
    return observation_step(observation) // 24


def _own_farm(observation: Any) -> Mapping[str, Any]:
    farms = list(_get(observation, "farms", []) or [])
    player = 1 if _integer(_get(observation, "player", 0)) == 1 else 0
    if player < len(farms) and isinstance(farms[player], Mapping):
        return farms[player]
    return {}


def _private(observation: Any) -> Mapping[str, Any]:
    value = _get(observation, "private", {}) or {}
    return value if isinstance(value, Mapping) else {}


def _tiles(observation: Any) -> list[list[Any]]:
    raw = _get(_own_farm(observation), "tiles", []) or []
    return [list(row or []) for row in raw]


def _unit_positions(observation: Any) -> list[tuple[int, int]]:
    farm = _own_farm(observation)
    positions = [_get(farm, "farmer", [0, 0])]
    positions.extend(list(_get(farm, "hands", []) or []))
    result: list[tuple[int, int]] = []
    for position in positions:
        if isinstance(position, Sequence) and len(position) >= 2:
            result.append((_integer(position[0]), _integer(position[1])))
        else:
            result.append((0, 0))
    return result


def _unit_inventory(observation: Any, index: int) -> Mapping[str, Any]:
    inventories = list(_get(_private(observation), "inventories", []) or [])
    if index < len(inventories) and isinstance(inventories[index], Mapping):
        return inventories[index]
    return {}


def _coerce_enum(enum_type: type[_StringEnum], value: Any, field: str) -> _StringEnum:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        allowed = ", ".join(member.value for member in enum_type)
        raise ValueError(f"{field} must be one of: {allowed}") from exc


@dataclass(frozen=True)
class MacroDecision:
    """The complete five-field macro action selected at a day boundary."""

    production_line: ProductionLine
    worker_cap: int
    cash_reserve: int
    sell_style: SellStyle
    terminal_mode: TerminalMode

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "production_line",
            _coerce_enum(ProductionLine, self.production_line, "production_line"),
        )
        object.__setattr__(
            self,
            "sell_style",
            _coerce_enum(SellStyle, self.sell_style, "sell_style"),
        )
        object.__setattr__(
            self,
            "terminal_mode",
            _coerce_enum(TerminalMode, self.terminal_mode, "terminal_mode"),
        )
        if self.worker_cap not in WORKER_CAPS:
            raise ValueError(f"worker_cap must be one of {WORKER_CAPS}")
        if self.cash_reserve not in CASH_RESERVES:
            raise ValueError(f"cash_reserve must be one of {CASH_RESERVES}")


@dataclass(frozen=True)
class MacroActionMask:
    """State-conditioned legal macro choices derived from the current observation."""

    production_lines: tuple[ProductionLine, ...]
    worker_caps: tuple[int, ...]
    cash_reserves: tuple[int, ...]
    sell_styles: tuple[SellStyle, ...]
    terminal_modes: tuple[TerminalMode, ...]

    @classmethod
    def from_observation(cls, observation: Any) -> "MacroActionMask":
        tiles = _tiles(observation)
        active_crops = {
            str(_get(tile, "crop", ""))
            for row in tiles
            for tile in row
            if isinstance(tile, Mapping) and _get(tile, "kind", "") == "PLANT"
        }
        has_convertible_tile = any(
            tile is None
            or (isinstance(tile, Mapping) and _get(tile, "kind", "") == "WEED")
            for row in tiles
            for tile in row
        )
        # A crop route spans several days.  Empty/weed tiles are available for
        # expanding the *current* route, but they must not make every other
        # production line legal while a planted route is still active.
        # Otherwise a day-level exploratory Manager can strand crops by
        # changing line every morning even though every individual action is
        # syntactically legal.
        if active_crops:
            production_lines = tuple(
                line for line in PRODUCTION_LINES if line.value in active_crops
            )
        elif has_convertible_tile:
            production_lines = PRODUCTION_LINES
        else:
            production_lines = PRODUCTION_LINES

        units = len(_unit_positions(observation))
        worker_caps = tuple(cap for cap in WORKER_CAPS if cap >= units)
        money = float(_get(_own_farm(observation), "money", 0.0) or 0.0)
        cash_reserves = tuple(reserve for reserve in CASH_RESERVES if reserve <= money)
        if 0 not in cash_reserves:
            cash_reserves = (0,)

        step = observation_step(observation)
        forced_terminal = step >= TERMINAL_START_STEP
        manager_terminal_window = step >= TERMINAL_MANAGER_START_STEP
        # High-level state safety: LIQUIDATE is not a season-long strategic
        # choice.  Exposing it only on the final day prevents a stochastic
        # Manager from shutting down production in the middle of the season;
        # the executor still forces liquidation from step 671 onward.
        if forced_terminal:
            terminal_modes = (TerminalMode.LIQUIDATE,)
        elif manager_terminal_window:
            terminal_modes = TERMINAL_MODES
        else:
            terminal_modes = (TerminalMode.NORMAL,)
        return cls(
            production_lines=production_lines,
            worker_caps=worker_caps,
            cash_reserves=cash_reserves,
            sell_styles=(SellStyle.IMMEDIATE,) if forced_terminal else SELL_STYLES,
            terminal_modes=terminal_modes,
        )

    def allows(self, decision: MacroDecision) -> bool:
        return bool(
            decision.production_line in self.production_lines
            and decision.worker_cap in self.worker_caps
            and decision.cash_reserve in self.cash_reserves
            and decision.sell_style in self.sell_styles
            and decision.terminal_mode in self.terminal_modes
        )

    def as_dict(self) -> dict[str, list[Any]]:
        return {
            "production_line": [item.value for item in self.production_lines],
            "worker_cap": list(self.worker_caps),
            "cash_reserve": list(self.cash_reserves),
            "sell_style": [item.value for item in self.sell_styles],
            "terminal_mode": [item.value for item in self.terminal_modes],
        }


@dataclass(frozen=True)
class PlanState:
    """Immutable day-level plan state; a proposal cannot alter it mid-day."""

    decision: MacroDecision
    decision_day: int
    activated_step: int
    last_step: int
    generation: int = 0

    def advance(
        self,
        observation: Any,
        daily_decision: MacroDecision | None = None,
    ) -> tuple["PlanState", bool]:
        day = observation_day(observation)
        step = observation_step(observation)
        if day != self.decision_day:
            next_decision = daily_decision if daily_decision is not None else self.decision
            return (
                PlanState(
                    decision=next_decision,
                    decision_day=day,
                    activated_step=step,
                    last_step=step,
                    generation=self.generation + 1,
                ),
                daily_decision is not None and daily_decision != self.decision,
            )
        return replace(self, last_step=step), False


@dataclass(frozen=True)
class RecipeStage:
    name: str
    priority: int
    depends_on: tuple[str, ...]


@dataclass(frozen=True)
class CropTask:
    task_id: str
    stage: str
    priority: int
    target: tuple[int, int]
    action: tuple[str, ...]
    depends_on: tuple[str, ...]


class CropRecipe:
    """Deterministic crop task graph for one production line."""

    GRAPH = (
        RecipeStage("HARVEST", 0, ()),
        RecipeStage("WATER", 1, ("HARVEST",)),
        RecipeStage("CLEAR_WEED", 2, ("WATER",)),
        RecipeStage("PLANT", 3, ("CLEAR_WEED",)),
    )

    def __init__(self, production_line: ProductionLine | str):
        self.production_line = ProductionLine(production_line)

    @property
    def task_graph(self) -> tuple[RecipeStage, ...]:
        return self.GRAPH

    @staticmethod
    def is_mature(tile: Any, day: int) -> bool:
        if not isinstance(tile, Mapping) or _get(tile, "kind", "") != "PLANT":
            return False
        crop = str(_get(tile, "crop", ""))
        if crop not in CROP_FIRST_YIELD_DAY:
            return False
        planted_day = _integer(_get(tile, "planted_day", day), day)
        yield_units = max(0, _integer(_get(tile, "yield_units", 0)))
        return day - planted_day >= CROP_FIRST_YIELD_DAY[crop] and yield_units > 0

    def build_tasks(self, observation: Any) -> tuple[CropTask, ...]:
        day = observation_day(observation)
        tiles = _tiles(observation)
        stage_by_name = {stage.name: stage for stage in self.GRAPH}
        tasks: list[CropTask] = []
        empty: list[tuple[int, int]] = []

        for y, row in enumerate(tiles):
            for x, tile in enumerate(row):
                if tile == "LOCKED":
                    continue
                if self.is_mature(tile, day):
                    stage = stage_by_name["HARVEST"]
                    tasks.append(
                        CropTask(
                            f"harvest:{x}:{y}", stage.name, stage.priority,
                            (x, y), ("HARVEST",), stage.depends_on,
                        )
                    )
                elif isinstance(tile, Mapping) and _get(tile, "kind", "") == "PLANT":
                    if not bool(_get(tile, "watered_today", False)):
                        stage = stage_by_name["WATER"]
                        tasks.append(
                            CropTask(
                                f"water:{x}:{y}", stage.name, stage.priority,
                                (x, y), ("WATER",), stage.depends_on,
                            )
                        )
                elif isinstance(tile, Mapping) and _get(tile, "kind", "") == "WEED":
                    stage = stage_by_name["CLEAR_WEED"]
                    tasks.append(
                        CropTask(
                            f"weed:{x}:{y}", stage.name, stage.priority,
                            (x, y), ("DIG",), stage.depends_on,
                        )
                    )
                elif tile is None:
                    empty.append((x, y))

        seeds = _get(_private(observation), "seeds", {}) or {}
        available = max(0, _integer(_get(seeds, self.production_line.value, 0)))
        positions = _unit_positions(observation)
        empty.sort(
            key=lambda target: (
                min((_manhattan(position, target) for position in positions), default=0),
                target[1],
                target[0],
            )
        )
        stage = stage_by_name["PLANT"]
        for x, y in empty[:available]:
            tasks.append(
                CropTask(
                    f"plant:{self.production_line.value}:{x}:{y}",
                    stage.name,
                    stage.priority,
                    (x, y),
                    ("PLANT", self.production_line.value),
                    stage.depends_on,
                )
            )

        return tuple(
            sorted(tasks, key=lambda task: (task.priority, task.target[1], task.target[0], task.task_id))
        )


@dataclass(frozen=True)
class ExecutionResult:
    action: dict[str, Any]
    state: PlanState
    audit: dict[str, Any]


def _manhattan(left: tuple[int, int], right: tuple[int, int]) -> int:
    return abs(left[0] - right[0]) + abs(left[1] - right[1])


def _one_step_toward(origin: tuple[int, int], target: tuple[int, int]) -> list[str]:
    if origin[0] < target[0]:
        return ["EAST"]
    if origin[0] > target[0]:
        return ["WEST"]
    if origin[1] < target[1]:
        return ["SOUTH"]
    if origin[1] > target[1]:
        return ["NORTH"]
    return ["PASS"]


def _assign_nearest(
    positions: Sequence[tuple[int, int]],
    tasks: Sequence[CropTask],
) -> dict[int, CropTask]:
    remaining_units = set(range(len(positions)))
    assignments: dict[int, CropTask] = {}
    for priority in sorted({task.priority for task in tasks}):
        remaining_tasks = [task for task in tasks if task.priority == priority]
        while remaining_units and remaining_tasks:
            candidates = [
                (
                    _manhattan(positions[unit], task.target),
                    unit,
                    task.target[1],
                    task.target[0],
                    task.task_id,
                    task,
                )
                for unit in remaining_units
                for task in remaining_tasks
            ]
            _, unit, _, _, _, task = min(candidates, key=lambda row: row[:-1])
            assignments[unit] = task
            remaining_units.remove(unit)
            remaining_tasks.remove(task)
    return assignments


def _shed_access_tiles(board_size: int) -> tuple[tuple[int, int], ...]:
    half = max(1, board_size // 2)
    return (
        (half - 1, half - 1),
        (half, half - 1),
        (half - 1, half),
        (half, half),
    )


def _nearest_shed(position: tuple[int, int], board_size: int) -> tuple[int, int]:
    return min(
        _shed_access_tiles(board_size),
        key=lambda target: (_manhattan(position, target), target[1], target[0]),
    )


def _fibonacci(index: int) -> int:
    left, right = 1, 1
    for _ in range(max(0, index)):
        left, right = right, left + right
    return left


class MacroPlanExecutor:
    """Pure compiler from macro plan and observation to an official action."""

    schema = "kaggriculture-v114-v9-event-program-v1"

    def activate(self, observation: Any, decision: MacroDecision) -> PlanState:
        step = observation_step(observation)
        return PlanState(
            decision=decision,
            decision_day=observation_day(observation),
            activated_step=step,
            last_step=step,
        )

    def step(
        self,
        observation: Any,
        state: PlanState,
        daily_decision: MacroDecision | None = None,
    ) -> ExecutionResult:
        next_state, decision_updated = state.advance(observation, daily_decision)
        decision = next_state.decision
        step = observation_step(observation)
        forced_terminal = step >= TERMINAL_START_STEP
        # The mask is the Manager contract, while this time guard is the
        # executor's defence in depth.  A malformed or exploratory mid-season
        # LIQUIDATE proposal cannot disable the production program.
        manager_liquidating = bool(
            step >= TERMINAL_MANAGER_START_STEP
            and decision.terminal_mode is TerminalMode.LIQUIDATE
        )
        liquidating = forced_terminal or manager_liquidating
        mask = MacroActionMask.from_observation(observation)

        if liquidating:
            unit_actions, assignments = self._terminal_unit_actions(observation)
        else:
            unit_actions, assignments = self._crop_unit_actions(observation, decision)

        market, market_audit = self._market_actions(
            observation,
            decision,
            unit_actions,
            liquidating=liquidating,
        )
        action = {
            "farmer": unit_actions[0] if unit_actions else ["PASS"],
            "hands": unit_actions[1:],
            "market": market,
        }
        violations = self._contract_violations(
            observation, decision, action, market_audit, liquidating
        )
        if violations:
            raise RuntimeError("event-program safety contract failed: " + "; ".join(violations))

        audit = {
            "schema": self.schema,
            "step": step,
            "day": observation_day(observation),
            "decision_day": next_state.decision_day,
            "decision_generation": next_state.generation,
            "decision_updated": decision_updated,
            "forced_terminal": forced_terminal,
            "effective_terminal_mode": (
                TerminalMode.LIQUIDATE.value if liquidating else TerminalMode.NORMAL.value
            ),
            "macro_mask": mask.as_dict(),
            "macro_decision_allowed": mask.allows(decision),
            "assignments": assignments,
            "market": market_audit,
            "violations": [],
            "parameter_source": "random_or_external_manager_only",
            "action_fallback": False,
        }
        return ExecutionResult(action=action, state=next_state, audit=audit)

    def _crop_unit_actions(
        self,
        observation: Any,
        decision: MacroDecision,
    ) -> tuple[list[list[str]], list[dict[str, Any]]]:
        positions = _unit_positions(observation)
        recipe = CropRecipe(decision.production_line)
        tasks = recipe.build_tasks(observation)
        assigned = _assign_nearest(positions, tasks)
        seeds = _get(_private(observation), "seeds", {}) or {}
        seeds_remaining = max(
            0, _integer(_get(seeds, decision.production_line.value, 0))
        )
        actions: list[list[str]] = []
        audit: list[dict[str, Any]] = []

        for unit_index, position in enumerate(positions):
            task = assigned.get(unit_index)
            if task is None:
                action = ["PASS"]
                audit.append({"unit": unit_index, "task": None, "action": action})
                actions.append(action)
                continue
            if position != task.target:
                action = _one_step_toward(position, task.target)
            else:
                action = list(task.action)
                if action[0] == "PLANT":
                    if seeds_remaining <= 0:
                        action = ["PASS"]
                    else:
                        seeds_remaining -= 1
            actions.append(action)
            audit.append(
                {
                    "unit": unit_index,
                    "task": task.task_id,
                    "stage": task.stage,
                    "target": list(task.target),
                    "action": list(action),
                }
            )
        return actions, audit

    def _terminal_unit_actions(
        self, observation: Any
    ) -> tuple[list[list[str]], list[dict[str, Any]]]:
        positions = _unit_positions(observation)
        board_size = len(_tiles(observation)) or 10
        access = set(_shed_access_tiles(board_size))
        actions: list[list[str]] = []
        audit: list[dict[str, Any]] = []
        for unit_index, position in enumerate(positions):
            inventory = _unit_inventory(observation, unit_index)
            has_inventory = any(_integer(value) > 0 for value in inventory.values())
            target = _nearest_shed(position, board_size)
            if position in access and has_inventory:
                action = ["DROP"]
            elif position != target:
                action = _one_step_toward(position, target)
            else:
                action = ["PASS"]
            actions.append(action)
            audit.append(
                {
                    "unit": unit_index,
                    "task": "RETURN_TO_SHED",
                    "target": list(target),
                    "action": list(action),
                }
            )
        return actions, audit

    def _projected_shed(
        self,
        observation: Any,
        unit_actions: Sequence[Sequence[str]],
    ) -> dict[str, int]:
        raw_shed = _get(_private(observation), "shed", {}) or {}
        shed = {product: max(0, _integer(_get(raw_shed, product, 0))) for product in PRODUCTS}
        positions = _unit_positions(observation)
        board_size = len(_tiles(observation)) or 10
        access = set(_shed_access_tiles(board_size))
        room = max(
            0,
            100 - sum(max(0, _integer(value)) for value in raw_shed.values()),
        )
        for unit_index, action in enumerate(unit_actions):
            if not action or action[0] != "DROP" or positions[unit_index] not in access:
                continue
            inventory = _unit_inventory(observation, unit_index)
            # Match the official DROP insertion order, including non-sellable
            # animals that may consume the remaining shed capacity first.
            for item, raw_quantity in inventory.items():
                quantity = min(max(0, _integer(raw_quantity)), room)
                if quantity > 0:
                    room -= quantity
                    if item in shed:
                        shed[item] += quantity
        return shed

    def _market_actions(
        self,
        observation: Any,
        decision: MacroDecision,
        unit_actions: Sequence[Sequence[str]],
        *,
        liquidating: bool,
    ) -> tuple[list[list[Any]], dict[str, Any]]:
        farm = _own_farm(observation)
        money = float(_get(farm, "money", 0.0) or 0.0)
        spendable = max(0.0, money - decision.cash_reserve)
        remaining_budget = spendable
        projected_shed = self._projected_shed(observation, unit_actions)
        prices = _get(_get(observation, "market", {}) or {}, "prices", {}) or {}
        orders: list[list[Any]] = []
        sold: dict[str, int] = {}

        sell_style = SellStyle.IMMEDIATE if liquidating else decision.sell_style
        for product in PRODUCTS:
            quantity = projected_shed[product]
            if quantity <= 0:
                continue
            current_price = max(1, _integer(_get(prices, product, BASE_PRICE[product]), BASE_PRICE[product]))
            should_sell = sell_style is SellStyle.IMMEDIATE or (
                sell_style is SellStyle.PRICE_GATE
                and current_price >= BASE_PRICE[product]
            )
            if should_sell and len(orders) < MAX_MARKET_ORDERS:
                orders.append(["SELL", product, quantity])
                sold[product] = quantity

        hires = 0
        planned_spend = 0
        if not liquidating:
            current_units = len(_unit_positions(observation))
            hires_today = max(0, _integer(_get(farm, "hires_today", 0)))
            while current_units + hires < decision.worker_cap and len(orders) < MAX_MARKET_ORDERS:
                cost = _fibonacci(hires_today + hires)
                if cost > remaining_budget:
                    break
                orders.append(["HIRE"])
                remaining_budget -= cost
                planned_spend += cost
                hires += 1

            crop = decision.production_line
            seeds = _get(_private(observation), "seeds", {}) or {}
            current_seeds = max(0, _integer(_get(seeds, crop.value, 0)))
            empty_tiles = sum(tile is None for row in _tiles(observation) for tile in row)
            desired = max(0, empty_tiles - current_seeds)
            affordable = int(remaining_budget // SEED_COST[crop])
            quantity = min(desired, affordable)
            if quantity > 0 and len(orders) < MAX_MARKET_ORDERS:
                orders.append(["BUY_SEED", crop.value, quantity])
                cost = quantity * SEED_COST[crop]
                remaining_budget -= cost
                planned_spend += cost

        audit = {
            "initial_money": money,
            "cash_reserve": decision.cash_reserve,
            "spendable_cash": spendable,
            "planned_spend": planned_spend,
            "remaining_spendable_cash": remaining_budget,
            "projected_shed": projected_shed,
            "sold": sold,
            "planned_hires": hires,
            "market_order_count": len(orders),
        }
        return orders, audit

    def _contract_violations(
        self,
        observation: Any,
        decision: MacroDecision,
        action: Mapping[str, Any],
        market_audit: Mapping[str, Any],
        liquidating: bool,
    ) -> list[str]:
        violations: list[str] = []
        hands = list(action.get("hands", []) or [])
        expected_hands = max(0, len(_unit_positions(observation)) - 1)
        if len(hands) != expected_hands:
            violations.append("hands length does not match public farm")
        market = list(action.get("market", []) or [])
        if len(market) > MAX_MARKET_ORDERS:
            violations.append("market order limit exceeded")

        seeds = _get(_private(observation), "seeds", {}) or {}
        plant_count = sum(
            bool(order and order[0] == "PLANT" and len(order) >= 2 and order[1] == decision.production_line.value)
            for order in [action.get("farmer", ["PASS"]), *hands]
        )
        if plant_count > max(0, _integer(_get(seeds, decision.production_line.value, 0))):
            violations.append("plant actions exceed available seeds")

        projected_shed = market_audit.get("projected_shed", {}) or {}
        sold: dict[str, int] = {}
        for order in market:
            if order and order[0] == "SELL" and len(order) >= 3:
                sold[str(order[1])] = sold.get(str(order[1]), 0) + _integer(order[2])
        for product, quantity in sold.items():
            if quantity > _integer(_get(projected_shed, product, 0)):
                violations.append(f"sell quantity exceeds projected shed for {product}")

        hires = sum(bool(order and order[0] == "HIRE") for order in market)
        if len(_unit_positions(observation)) + hires > decision.worker_cap:
            violations.append("planned hires exceed worker cap")
        if float(market_audit.get("planned_spend", 0.0)) > float(
            market_audit.get("spendable_cash", 0.0)
        ) + 1e-9:
            violations.append("planned spend breaches cash reserve")
        if liquidating and any(
            order and order[0] in {"HIRE", "BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "BUY_LAND"}
            for order in market
        ):
            violations.append("terminal mode contains procurement")
        return violations


__all__ = [
    "CASH_RESERVES",
    "CropRecipe",
    "CropTask",
    "ExecutionResult",
    "MacroActionMask",
    "MacroDecision",
    "MacroPlanExecutor",
    "ONE_TIME_CROPS",
    "PlanState",
    "ProductionLine",
    "RecipeStage",
    "SELL_STYLES",
    "SellStyle",
    "TERMINAL_MODES",
    "TERMINAL_START_STEP",
    "TerminalMode",
    "WORKER_CAPS",
    "observation_day",
    "observation_step",
]
