"""共享硬风险覆盖层：不伪装成生产专家。"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from contracts import DailyContract
from executor import ExecutorResult
from market import MarketResult
from schema import (ANIMALS, CROPS, LAND_PRICES, PASS, PRODUCTS, SHED_CAPACITY, SHED_TILES,
                    UNIT_NO_ARG, CanonicalState, animal_kind, distance, fib, integer, path_toward, shed_gate)
from state_ledger import RuntimeFeedback


class ControlMode(str, Enum):
    NORMAL = "NORMAL"
    CASH_RECOVERY = "CASH_RECOVERY"
    FEED_RECOVERY = "FEED_RECOVERY"
    SHED_RECOVERY = "SHED_RECOVERY"
    TERMINAL = "TERMINAL"


@dataclass(frozen=True)
class ControlResult:
    action: Mapping[str, Any]
    mode: ControlMode
    rewrites: int
    reasons: tuple[str, ...]


class SafetyRecoveryTerminalController:
    def __init__(self, terminal_return_buffer: int = 2,
                 terminal_hire_cap: int = 0) -> None:
        self.audit: Counter[str] = Counter()
        self.terminal_return_buffer = max(0, int(terminal_return_buffer))
        self.terminal_hire_cap = max(0, min(15, int(terminal_hire_cap)))

    @staticmethod
    def mode(state: CanonicalState, feedback: RuntimeFeedback) -> ControlMode:
        if feedback.terminal:
            return ControlMode.TERMINAL
        if feedback.cash_risk >= 0.85:
            return ControlMode.CASH_RECOVERY
        if feedback.feed_risk >= 0.8:
            return ControlMode.FEED_RECOVERY
        if feedback.shed_pressure >= 0.92:
            return ControlMode.SHED_RECOVERY
        return ControlMode.NORMAL

    def _terminal_units(self, state: CanonicalState,
                        proposed: Sequence[Sequence[Any]]) -> list[list[Any]]:
        actions = [list(action) for action in proposed]
        for actor, (position, inventory) in enumerate(zip(state.positions, state.inventories)):
            carried = sum(max(0, int(value)) for value in inventory.values())
            travel = distance(position, shed_gate(position))
            if carried <= 0 or state.remaining_steps > travel + self.terminal_return_buffer:
                continue
            actions[actor] = (["DROP"] if position in SHED_TILES
                              else path_toward(state.grid, position, shed_gate(position), actor))
        return actions

    @staticmethod
    def _feed_units(state: CanonicalState, proposed: Sequence[Sequence[Any]]) -> list[list[Any]]:
        actions = [list(action) for action in proposed]
        if state.shed.get("WHEAT", 0) <= 0 or not state.positions:
            return actions
        actor = min(range(len(state.positions)), key=lambda index: distance(state.positions[index], shed_gate(state.positions[index])))
        position = state.positions[actor]
        if state.inventories[actor].get("WHEAT", 0) <= 0:
            actions[actor] = (["PICKUP", "WHEAT", min(12, state.shed["WHEAT"])]
                              if position in SHED_TILES else path_toward(state.grid, position, shed_gate(position), actor))
        return actions

    @staticmethod
    def _projected_shed(state: CanonicalState, units: Sequence[Sequence[Any]]) -> dict[str, int]:
        shed = dict(state.shed)
        used = sum(shed.values())
        for actor, action in enumerate(units):
            if not action:
                continue
            if action[0] == "DROP" and actor < len(state.inventories):
                for item, quantity in state.inventories[actor].items():
                    take = min(max(0, int(quantity)), max(0, SHED_CAPACITY - used))
                    shed[item] = shed.get(item, 0) + take
                    used += take
            elif action[0] == "PICKUP" and len(action) == 3:
                item = str(action[1])
                shed[item] = max(0, shed.get(item, 0) - integer(action[2]))
        return shed

    def _terminal_market(self, state: CanonicalState, contract: DailyContract,
                         units: Sequence[Sequence[Any]]) -> list[list[Any]]:
        shed = SafetyRecoveryTerminalController._projected_shed(state, units)
        ranked = sorted(PRODUCTS, key=lambda item: (-state.prices.get(item, 1), PRODUCTS.index(item)))
        hire_gap = max(
            0,
            min(int(contract.hands), self.terminal_hire_cap)
            - max(0, len(state.positions) - 1),
        )
        # 先卖高价库存形成现金，再雇当日劳力。后续回合会继续卖剩余品类；
        # 仍受 10 条市场订单和语义校验约束。
        sale_slots = max(0, 10 - hire_gap)
        orders = [
            ["SELL", item, int(shed.get(item, 0))]
            for item in ranked if shed.get(item, 0) > 0
        ][:sale_slots]
        orders.extend([["HIRE"] for _ in range(hire_gap)])
        self.audit["terminal_hire_requested"] += hire_gap
        return orders

    @staticmethod
    def _valid_unit(state: CanonicalState, actor: int, action: Any) -> bool:
        if not isinstance(action, (list, tuple)) or not action or not isinstance(action[0], str):
            return False
        op = action[0]
        if actor >= len(state.positions):
            return False
        position = state.positions[actor]
        x, y = position
        tile = state.grid[y][x] if 0 <= y < len(state.grid) and 0 <= x < len(state.grid[y]) else None
        inventory = state.inventories[actor]
        if op in {"NORTH", "SOUTH", "EAST", "WEST"}:
            dx, dy = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}[op]
            nx, ny = x + dx, y + dy
            return len(action) == 1 and 0 <= ny < len(state.grid) and 0 <= nx < len(state.grid[ny]) and state.grid[ny][nx] != "LOCKED"
        if op == "PASS":
            return len(action) == 1
        if op == "PICKUP":
            return (len(action) == 3 and position in SHED_TILES and action[1] in set(PRODUCTS) | set(ANIMALS)
                    and integer(action[2]) > 0 and state.shed.get(str(action[1]), 0) >= integer(action[2]))
        if op == "DROP":
            return len(action) == 1 and position in SHED_TILES and any(int(value) > 0 for value in inventory.values())
        if op == "PLANT":
            return len(action) == 2 and action[1] in CROPS and tile is None and state.seeds.get(str(action[1]), 0) > 0
        if op == "WATER":
            return len(action) == 1 and isinstance(tile, Mapping) and tile.get("kind") == "PLANT" and not tile.get("watered_today")
        if op == "HARVEST":
            return len(action) == 1 and isinstance(tile, Mapping) and integer(tile.get("yield_units")) > 0
        if op == "FEED":
            return (len(action) == 1 and isinstance(tile, Mapping) and animal_kind(tile) is not None
                    and not tile.get("fed_today") and inventory.get("WHEAT", 0) > 0)
        if op == "CARE":
            return len(action) == 1 and isinstance(tile, Mapping) and animal_kind(tile) is not None and not tile.get("cared_today")
        if op == "COLLECT_FERTILIZER":
            return len(action) == 1 and isinstance(tile, Mapping) and bool(tile.get("fertilizer_available"))
        if op == "DIG":
            return len(action) == 1 and isinstance(tile, Mapping) and tile.get("kind") == "WEED"
        if op in {"BUILD_COOP", "BUILD_PASTURE"}:
            return len(action) == 1 and tile is None
        if op == "PLACE":
            return len(action) in {2, 3} and action[1] in ANIMALS and inventory.get(str(action[1]), 0) > 0
        if op == "FERTILIZE":
            return len(action) == 1 and inventory.get("FERTILIZER", 0) > 0 and isinstance(tile, Mapping)
        return op in UNIT_NO_ARG and len(action) == 1

    def _sanitize_units(self, state: CanonicalState, units: Sequence[Sequence[Any]]) -> tuple[list[list[Any]], int]:
        expected = len(state.positions)
        normalized: list[list[Any]] = []
        rewrites = 0
        for actor in range(expected):
            action = list(units[actor]) if actor < len(units) and isinstance(units[actor], (list, tuple)) else PASS.copy()
            if not self._valid_unit(state, actor, action):
                original_op = str(action[0]).lower() if action else "invalid"
                action = PASS.copy()
                rewrites += 1
                self.audit["unit_semantic_rewrite"] += 1
                self.audit[f"rewrite_{original_op}"] += 1
            normalized.append(action)
        if len(units) != expected:
            self.audit["unit_shape_rewrite"] += 1
            rewrites += abs(len(units) - expected)
        return normalized, rewrites

    def _sanitize_market(self, state: CanonicalState, units: Sequence[Sequence[Any]], orders: Sequence[Sequence[Any]]) -> tuple[list[list[Any]], int]:
        shed = self._projected_shed(state, units)
        capacity = sum(shed.values())
        money = state.money
        valid: list[list[Any]] = []
        rewrites = 0
        for raw in list(orders)[:10]:
            if not isinstance(raw, (list, tuple)) or not raw:
                rewrites += 1
                continue
            op = str(raw[0])
            order = list(raw)
            ok = False
            if op == "SELL" and len(order) == 3 and order[1] in PRODUCTS:
                quantity = min(max(0, integer(order[2])), shed.get(str(order[1]), 0))
                ok = quantity > 0
                if ok:
                    order[2] = quantity
                    shed[str(order[1])] -= quantity
                    capacity -= quantity
                    money += quantity * state.prices.get(str(order[1]), 1)
            elif op in {"BUY_PRODUCT", "BUY_ANIMAL"} and len(order) == 3:
                item = str(order[1])
                allowed = item in PRODUCTS if op == "BUY_PRODUCT" else item in ANIMALS
                unit_cost = state.prices.get(item, 1) if op == "BUY_PRODUCT" else {"GOOSE": 300, "COW": 400, "SHEEP": 500}.get(item, 10**9)
                quantity = min(max(0, integer(order[2])), max(0, SHED_CAPACITY - capacity), money // max(1, unit_cost))
                ok = allowed and quantity > 0
                if ok:
                    order[2] = quantity
                    money -= quantity * unit_cost
                    capacity += quantity
            elif op == "BUY_SEED" and len(order) == 3 and order[1] in CROPS:
                unit_cost = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}[str(order[1])]
                quantity = min(max(0, integer(order[2])), money // unit_cost)
                ok = quantity > 0
                if ok:
                    order[2] = quantity
                    money -= quantity * unit_cost
            elif op == "HIRE" and len(order) == 1:
                cost = fib(state.hires_today + sum(int(item[0] == "HIRE") for item in valid))
                ok = money >= cost
                if ok:
                    money -= cost
            elif op == "BUY_LAND" and len(order) == 1 and state.lands < 4:
                cost = LAND_PRICES[max(0, state.lands - 1)]
                ok = money >= cost
                if ok:
                    money -= cost
            if ok:
                valid.append(order)
            else:
                rewrites += 1
                self.audit["market_semantic_rewrite"] += 1
        if len(orders) > 10:
            rewrites += len(orders) - 10
            self.audit["market_order_cap_rewrite"] += len(orders) - 10
        return valid, rewrites

    def apply(self, state: CanonicalState, contract: DailyContract, feedback: RuntimeFeedback,
              executor: ExecutorResult, market: MarketResult) -> ControlResult:
        mode = self.mode(state, feedback)
        units = [list(action) for action in executor.unit_actions]
        orders = [list(order) for order in market.orders]
        reasons: list[str] = []
        if mode == ControlMode.TERMINAL:
            units = self._terminal_units(state, units)
            orders = self._terminal_market(state, contract, units)
            reasons.append("STOP_EXPANSION_RETURN_DROP_SELL")
        elif mode == ControlMode.FEED_RECOVERY:
            units = self._feed_units(state, units)
            reasons.append("PROTECT_ANIMAL_FEED_CHAIN")
        elif mode == ControlMode.CASH_RECOVERY:
            reasons.append("RESTORE_CASH_RESERVE")
        elif mode == ControlMode.SHED_RECOVERY:
            reasons.append("REDUCE_SHED_PRESSURE")
        safe_units, unit_rewrites = self._sanitize_units(state, units)
        safe_market, market_rewrites = self._sanitize_market(state, safe_units, orders)
        self.audit[f"mode_{mode.value.lower()}"] += 1
        rewrites = unit_rewrites + market_rewrites
        action = {
            "farmer": safe_units[0] if safe_units else PASS.copy(),
            "hands": safe_units[1:],
            "market": safe_market,
        }
        return ControlResult(action, mode, rewrites, tuple(reasons))
