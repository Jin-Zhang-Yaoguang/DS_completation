"""Research-only non-WHEAT sale-timing planner.

The planner is intentionally an adapter over an already-produced parent action.
It never edits farmer/hand actions or protected market orders.  Its first
mechanism moves an executable non-WHEAT sale from a town-consumption step to the
following step when the exact integer price curve predicts a positive gain.
"""

from __future__ import annotations

import copy
import math
from collections import Counter
from dataclasses import dataclass
from typing import Any, Callable, Mapping


NON_WHEAT = (
    "CARROT",
    "TOMATO",
    "STRAWBERRY",
    "MELON",
    "EGG",
    "MILK",
    "WOOL",
)


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    getter = getattr(value, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(value, key, default)


def canonical_action(action: Mapping[str, Any] | None) -> dict[str, list[Any]]:
    source = copy.deepcopy(dict(action or {}))
    return {
        "farmer": list(source.get("farmer") or ["PASS"]),
        "hands": [list(row or ["PASS"]) for row in source.get("hands", [])],
        "market": [list(row) for row in source.get("market", [])],
    }


def _sell_revenue(price: Callable[[str, int], int], item: str, inventory: int, quantity: int) -> int:
    revenue = 0
    level = int(inventory)
    for _ in range(max(0, int(quantity))):
        quote = int(price(item, level))
        revenue += quote
        if quote > 1:
            level += 1
    return revenue


def _unit_orders(action: Mapping[str, Any]) -> list[list[Any]]:
    return [list(action.get("farmer") or ["PASS"]), *[list(x or ["PASS"]) for x in action.get("hands", [])]]


def _pickup_reserve(action: Mapping[str, Any], item: str) -> int:
    total = 0
    for order in _unit_orders(action):
        if len(order) >= 2 and order[0] == "PICKUP" and order[1] == item:
            total += max(0, int(order[2])) if len(order) >= 3 else 1
    return total


def _requested_sells(action: Mapping[str, Any], item: str) -> int:
    return sum(
        max(0, int(order[2] or 0))
        for order in action.get("market", [])
        if len(order) >= 3 and order[0] == "SELL" and order[1] == item
    )


def _reduce_sells(market: list[list[Any]], item: str, quantity: int) -> int:
    """Reduce from later duplicate orders first while retaining every slot."""
    remaining = max(0, int(quantity))
    for order in reversed(market):
        if remaining <= 0:
            break
        if len(order) < 3 or order[0] != "SELL" or order[1] != item:
            continue
        current = max(0, int(order[2] or 0))
        take = min(current, remaining)
        order[2] = current - take
        remaining -= take
    return max(0, int(quantity)) - remaining


def _editable_totals(action: Mapping[str, Any]) -> Counter[str]:
    result: Counter[str] = Counter()
    for order in action.get("market", []):
        if len(order) >= 3 and order[0] == "SELL" and order[1] in NON_WHEAT:
            result[str(order[1])] += max(0, int(order[2] or 0))
    return result


def _protected_market(action: Mapping[str, Any]) -> list[tuple[int, tuple[Any, ...]]]:
    rows = []
    for index, order in enumerate(action.get("market", [])):
        if not (len(order) >= 3 and order[0] == "SELL" and order[1] in NON_WHEAT):
            rows.append((index, tuple(order)))
    return rows


@dataclass(frozen=True)
class DelayConfig:
    fraction: float = 1.0
    max_batch: int = 30
    min_predicted_gain: int = 2
    cash_floor: int = 5000
    shed_soft_cap: int = 96
    opponent_buffer_multiplier: float = 0.0
    opponent_flow_decay: float = 0.75
    start_step: int = 96
    stop_step: int = 712
    target_items: tuple[str, ...] = ("STRAWBERRY", "MILK", "WOOL")
    require_sell_only_window: bool = False


class DemandDelayPlanner:
    """One-step price-aware temporal allocator for existing non-WHEAT sales."""

    def __init__(self, parent_module: Any, config: DelayConfig | None = None) -> None:
        self.parent = parent_module
        self.config = config or DelayConfig()
        self.pending: dict[int, dict[str, int]] = {0: {}, 1: {}}
        self.last_step = {0: -1, 1: -1}
        self.flow_ewma = {0: Counter(), 1: Counter()}
        self.last_market: dict[int, dict[str, int] | None] = {0: None, 1: None}
        self.last_own_supply = {0: Counter(), 1: Counter()}
        self.last_demand = {0: Counter(), 1: Counter()}
        self.stats = {0: Counter(), 1: Counter()}

    def _reset(self, seat: int) -> None:
        self.pending[seat] = {}
        self.last_step[seat] = -1
        self.flow_ewma[seat] = Counter()
        self.last_market[seat] = None
        self.last_own_supply[seat] = Counter()
        self.last_demand[seat] = Counter()
        self.stats[seat] = Counter()

    def _observe_opponent_flow(self, obs: Any, seat: int, step: int) -> None:
        current = {
            item: int(_get(_get(_get(obs, "market", {}) or {}, "inventory", {}) or {}, item, 10000) or 0)
            for item in NON_WHEAT
        }
        previous = self.last_market[seat]
        if previous is not None and step == self.last_step[seat] + 1:
            decay = min(1.0, max(0.0, float(self.config.opponent_flow_decay)))
            for item in NON_WHEAT:
                inferred = (
                    current[item]
                    - previous[item]
                    - int(self.last_own_supply[seat].get(item, 0))
                    + int(self.last_demand[seat].get(item, 0))
                )
                inferred = max(0, inferred)
                old = float(self.flow_ewma[seat].get(item, 0.0))
                self.flow_ewma[seat][item] = decay * old + (1.0 - decay) * inferred
        self.last_market[seat] = current

    def _projected_available(self, obs: Any, action: Mapping[str, Any], item: str) -> int:
        projected = self.parent._projected_shed(obs, action)
        return max(0, int(projected.get(item, 0) or 0) - _pickup_reserve(action, item))

    def _unwind(self, obs: Any, action: dict[str, list[Any]], seat: int) -> dict[str, list[Any]]:
        pending = dict(self.pending[seat])
        if not pending:
            return action
        market = [list(order) for order in action["market"]]
        inserted = 0
        for item in NON_WHEAT:
            quantity = max(0, int(pending.get(item, 0)))
            if quantity <= 0:
                continue
            available = self._projected_available(obs, action, item)
            base_requested = _requested_sells(action, item)
            executable = min(quantity, max(0, available - base_requested))
            existing = next(
                (order for order in market if len(order) >= 3 and order[0] == "SELL" and order[1] == item),
                None,
            )
            if executable > 0 and existing is not None:
                existing[2] = max(0, int(existing[2] or 0)) + executable
            elif executable > 0 and len(market) < 10:
                market.append(["SELL", item, executable])
                inserted += 1
            else:
                executable = 0
            self.stats[seat]["unwound_units"] += executable
            if executable < quantity:
                self.stats[seat]["unwind_shortfall_units"] += quantity - executable
        action["market"] = market[:10]
        self.pending[seat] = {}
        self.stats[seat]["unwind_steps"] += 1
        self.stats[seat]["new_slots"] += inserted
        return action

    def _consider_delay(
        self,
        obs: Any,
        action: dict[str, list[Any]],
        seat: int,
        step: int,
        oracle_decisions: Mapping[str, tuple[int, int]] | None = None,
    ) -> dict[str, list[Any]]:
        cfg = self.config
        if not (cfg.start_step <= step < cfg.stop_step) or step % 4 != 0:
            return action
        if float(_get((_get(obs, "farms", []) or [])[seat], "money", 0) or 0) < cfg.cash_floor:
            self.stats[seat]["skip_cash"] += 1
            return action
        projected = self.parent._projected_shed(obs, action)
        projected_total = sum(max(0, int(value or 0)) for value in projected.values())
        if projected_total > cfg.shed_soft_cap:
            self.stats[seat]["skip_shed"] += 1
            return action

        next_base = self.parent._ACTIONS[step + 1] if step + 1 < len(self.parent._ACTIONS) else {"market": []}
        next_market = list(next_base.get("market") or [])
        market = [list(order) for order in action["market"]]
        if cfg.require_sell_only_window and (
            any(not order or order[0] != "SELL" for order in market)
            or any(not order or order[0] != "SELL" for order in next_market)
        ):
            self.stats[seat]["skip_mixed_window"] += 1
            return action
        next_items = {
            str(order[1])
            for order in next_market
            if len(order) >= 3 and order[0] == "SELL" and order[1] in NON_WHEAT
        }
        free_slots = max(0, 10 - len(next_market))
        inventory = _get(_get(obs, "market", {}) or {}, "inventory", {}) or {}
        delayed: dict[str, int] = {}
        predicted_gain = 0

        candidates = []
        for item in NON_WHEAT:
            if item not in cfg.target_items:
                continue
            requested = _requested_sells(action, item)
            if requested <= 0:
                continue
            demand = int(self.parent._v17_town_demand_at(obs, item, step))
            if demand <= 0:
                continue
            available = self._projected_available(obs, action, item)
            executable = min(requested, available)
            if executable <= 0:
                continue
            if oracle_decisions is not None:
                oracle = oracle_decisions.get(item)
                if oracle is None:
                    continue
                quantity = min(executable, max(0, int(oracle[0])))
                gain = int(oracle[1])
            else:
                quantity = min(cfg.max_batch, executable, max(1, int(math.floor(executable * cfg.fraction))))
                start = int(_get(inventory, item, 10000) or 0)
                buffer = int(math.ceil(
                    max(0.0, float(self.flow_ewma[seat].get(item, 0.0)))
                    * max(0.0, float(cfg.opponent_buffer_multiplier))
                ))
                now = _sell_revenue(self.parent._market_price, item, start, quantity)
                later = _sell_revenue(self.parent._market_price, item, start - demand + buffer, quantity)
                gain = later - now
            if gain >= cfg.min_predicted_gain:
                candidates.append((gain, item, quantity))

        candidates.sort(reverse=True)
        for gain, item, quantity in candidates:
            if item not in next_items and free_slots <= 0:
                self.stats[seat]["skip_next_slot"] += 1
                continue
            removed = _reduce_sells(market, item, quantity)
            if removed <= 0:
                continue
            delayed[item] = removed
            predicted_gain += int(round(gain * removed / quantity))
            if item not in next_items:
                next_items.add(item)
                free_slots -= 1

        if delayed:
            action["market"] = market
            self.pending[seat] = delayed
            self.stats[seat]["delay_steps"] += 1
            self.stats[seat]["delayed_units"] += sum(delayed.values())
            self.stats[seat]["predicted_gain"] += predicted_gain
            for item, quantity in delayed.items():
                self.stats[seat][f"delayed_{item}"] += quantity
        return action

    def adapt(
        self,
        obs: Any,
        base_action: Mapping[str, Any],
        oracle_decisions: Mapping[str, tuple[int, int]] | None = None,
    ) -> dict[str, list[Any]]:
        seat = 1 if int(_get(obs, "player", 0) or 0) == 1 else 0
        step = int(_get(obs, "step", 0) or 0)
        if step == 0 or step < self.last_step[seat]:
            self._reset(seat)
        self._observe_opponent_flow(obs, seat, step)

        base = canonical_action(base_action)
        result = canonical_action(base)
        had_pending = bool(self.pending[seat])
        if had_pending:
            result = self._unwind(obs, result, seat)
        else:
            result = self._consider_delay(obs, result, seat, step, oracle_decisions)

        if result["farmer"] != base["farmer"] or result["hands"] != base["hands"]:
            raise AssertionError("production action changed")
        before_protected = _protected_market(base)
        after_protected = _protected_market(result)
        if before_protected != after_protected[: len(before_protected)]:
            raise AssertionError("protected market order or slot changed")
        if len(result["market"]) > 10:
            raise AssertionError("market queue exceeds official limit")

        projected = self.parent._projected_shed(obs, result)
        own_supply: Counter[str] = Counter()
        for item in NON_WHEAT:
            available = max(0, int(projected.get(item, 0) or 0) - _pickup_reserve(result, item))
            own_supply[item] = min(available, _requested_sells(result, item))
        self.last_own_supply[seat] = own_supply
        self.last_demand[seat] = Counter(
            {item: int(self.parent._v17_town_demand_at(obs, item, step)) for item in NON_WHEAT}
        )
        self.last_step[seat] = step
        self.stats[seat]["calls"] += 1
        self.stats[seat]["editable_units_before"] += sum(_editable_totals(base).values())
        self.stats[seat]["editable_units_after"] += sum(_editable_totals(result).values())
        return result

    def act(self, obs: Any) -> dict[str, list[Any]]:
        return self.adapt(obs, self.parent.agent(obs))

    def diagnostics(self, seat: int) -> dict[str, Any]:
        result = dict(self.stats[int(seat)])
        result["pending"] = dict(self.pending[int(seat)])
        result["flow_ewma"] = {
            item: float(self.flow_ewma[int(seat)].get(item, 0.0)) for item in NON_WHEAT
        }
        return result
