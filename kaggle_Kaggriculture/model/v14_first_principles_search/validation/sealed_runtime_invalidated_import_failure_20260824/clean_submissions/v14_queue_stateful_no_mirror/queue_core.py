"""V14 discovery prototype: stateful opponent-shadow queue best response.

The parent is the complete A2 policy.  We never change production actions or
SELL quantities.  An opposite-seat A2 shadow owns an independent private-state
estimate initialized from the public game start.  After every call, the
official 1.32.7 unit and market transitions advance that estimate using the
candidate action and the predicted opponent action.  The next public opponent
money value must exactly match the prediction; a mismatch permanently falls
back to A2.  Only after a long exact-conformance prefix, and only in V8/V8,
does the compiler search permutations of existing SELL orders.
The objective is evaluated with Kaggriculture's actual per-unit lockstep market
semantics.  A permutation is accepted only when it increases the predicted
head-to-head revenue advantage without reducing our predicted current-turn
SELL revenue.

This module is development-only.  It deliberately has no submission archive.
"""

from __future__ import annotations

from collections import Counter
import copy
import itertools
import json
import math
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

import a2_agent as a2  # type: ignore

try:
    import official_kaggriculture as kg  # type: ignore
except Exception:  # Serving must fail closed if bundled helpers are unavailable.
    kg = None


MODEL_ID = "v14_queue_best_response"
PRICE_FLOOR = 1
HINGE_GAIN = 8.0
MARKET_PARAMS = {
    "WHEAT": (25, 10000, 400, "sqrt", 0.80, "log", 0.20),
    "CARROT": (35, 10000, 450, "hinge", 1.00, "sqrt", 0.70),
    "TOMATO": (60, 10000, 200, "hinge", 0.40, "sqrt", 0.60),
    "STRAWBERRY": (120, 10000, 100, "sqrt", 0.70, "linear", 1.60),
    "MELON": (250, 10000, 300, "log", 0.20, "sq", 3.60),
    "EGG": (50, 10000, 332, "hinge", 0.40, "log", 0.20),
    "MILK": (160, 10000, 122, "sqrt", 0.60, "linear", 1.60),
    "WOOL": (200, 10000, 105, "log", 0.20, "sq", 3.20),
    "FERTILIZER": (100, 10000, 200, "linear", 0.40, "linear", 0.40),
}
SEED_COSTS = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
ANIMAL_COSTS = {"GOOSE": 300, "COW": 400, "SHEEP": 500}
SHED_CAPACITY = 100


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    getter = getattr(value, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(value, key, default)


def _canonical_action(action: Mapping[str, Any] | None) -> dict[str, list[Any]]:
    source = copy.deepcopy(dict(action or {}))
    return {
        "farmer": list(source.get("farmer") or ["PASS"]),
        "hands": [list(item or ["PASS"]) for item in source.get("hands", [])],
        "market": [list(item) for item in source.get("market", [])],
    }


def _seat(obs: Any) -> int:
    return 1 if int(_get(obs, "player", 0) or 0) == 1 else 0


def _public_signature(farm: Any) -> tuple[Any, ...]:
    keys = (
        "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
        "COW", "SHEEP", "GOOSE", "PASTURE", "COOP", "WEED",
    )
    counts = {key: 0 for key in keys}
    for row in (_get(farm, "tiles", []) or []):
        for tile in row if isinstance(row, list) else [row]:
            if not isinstance(tile, Mapping):
                continue
            for field in ("crop", "animal", "kind"):
                value = str(tile.get(field, "")).upper()
                if value in counts:
                    counts[value] += 1
                    break
    return (
        len(_get(farm, "hands", []) or []),
        len(_get(farm, "unlocked_quadrants", []) or []),
        tuple(counts[key] for key in sorted(counts)),
    )


def _clone_distance(obs: Any) -> int:
    farms = list(_get(obs, "farms", []) or [])
    if len(farms) != 2:
        return 10**9
    left, right = _public_signature(farms[0]), _public_signature(farms[1])
    return (
        abs(left[0] - right[0])
        + 3 * abs(left[1] - right[1])
        + sum(abs(a - b) for a, b in zip(left[2], right[2]))
    )


def _public_farm_state(farm: Any) -> str:
    """Canonical public production state, deliberately excluding only money."""

    payload = {
        "farmer": list(_get(farm, "farmer", []) or []),
        "hands": [list(item) for item in (_get(farm, "hands", []) or [])],
        "unlocked_quadrants": list(_get(farm, "unlocked_quadrants", []) or []),
        "hires_today": int(_get(farm, "hires_today", 0) or 0),
        "tiles": _get(farm, "tiles", []) or [],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _public_production_equal(obs: Any) -> bool:
    farms = list(_get(obs, "farms", []) or [])
    return len(farms) == 2 and _public_farm_state(farms[0]) == _public_farm_state(farms[1])


def _has_same_turn_shed_transfer(action: Mapping[str, Any]) -> bool:
    orders = [action.get("farmer", ["PASS"]), *(action.get("hands") or [])]
    return any(
        order and str(order[0]) in {"DROP", "PICKUP", "PLACE"}
        for order in orders
    )


def _shape(name: str, x: float, threshold: float) -> float:
    x = max(0.0, float(x))
    if name == "linear":
        return x
    if name == "sq":
        return x * x
    if name == "sqrt":
        return math.sqrt(x)
    if name == "log":
        return math.log1p(x)
    if name == "hinge":
        u = x / threshold if threshold > 0 else x
        return u + HINGE_GAIN * max(0.0, u - 1.0) ** 2
    return x


def _market_price(item: str, inventory: int) -> int:
    base, initial, threshold, below_func, below_target, above_func, above_target = MARKET_PARAMS[item]
    if inventory < initial:
        amplitude = below_target * base / _shape(below_func, threshold, threshold)
        price = base + amplitude * _shape(below_func, initial - inventory, threshold)
    else:
        amplitude = above_target * base / _shape(above_func, threshold, threshold)
        price = base - amplitude * _shape(above_func, inventory - initial, threshold)
    return max(PRICE_FLOOR, int(round(price)))


def _shed(obs: Any) -> dict[str, int]:
    private = _get(obs, "private", {}) or {}
    raw = _get(private, "shed", {}) or {}
    return {str(key): max(0, int(value or 0)) for key, value in dict(raw).items()}


def _inventory(obs: Any) -> dict[str, int]:
    market = _get(obs, "market", {}) or {}
    raw = _get(market, "inventory", {}) or {}
    return {str(key): int(value or 0) for key, value in dict(raw).items()}


def _parse_sell(order: Sequence[Any] | None) -> tuple[str, int] | None:
    if not order or len(order) < 3 or str(order[0]) != "SELL":
        return None
    item = str(order[1])
    if item not in MARKET_PARAMS:
        return None
    try:
        quantity = max(0, int(order[2]))
    except (TypeError, ValueError):
        return None
    return (item, quantity) if quantity else None


def _simulate_sell_queues(
    candidate: Sequence[Sequence[Any]],
    opponent: Sequence[Sequence[Any]],
    inventory: Mapping[str, int],
    candidate_shed: Mapping[str, int],
    opponent_shed: Mapping[str, int],
) -> tuple[float, float]:
    """Exact SELL-only part of the engine's slot/unit lockstep."""

    inv = {item: int(inventory.get(item, 10000)) for item in MARKET_PARAMS}
    sheds = [Counter(candidate_shed), Counter(opponent_shed)]
    revenues = [0.0, 0.0]
    max_len = max(len(candidate), len(opponent))
    for slot in range(max_len):
        parsed = [
            _parse_sell(candidate[slot] if slot < len(candidate) else None),
            _parse_sell(opponent[slot] if slot < len(opponent) else None),
        ]
        remaining = [parsed[0][1] if parsed[0] else 0, parsed[1][1] if parsed[1] else 0]
        while remaining[0] > 0 or remaining[1] > 0:
            quoted: list[tuple[str, int] | None] = [None, None]
            for player in (0, 1):
                if remaining[player] <= 0 or parsed[player] is None:
                    continue
                item = parsed[player][0]
                if sheds[player][item] <= 0:
                    remaining[player] = 0
                    continue
                quoted[player] = (item, _market_price(item, inv[item]))
            if quoted == [None, None]:
                break
            for player in (0, 1):
                quote = quoted[player]
                if quote is None:
                    continue
                item, price = quote
                sheds[player][item] -= 1
                remaining[player] -= 1
                revenues[player] += float(price)
                if price > PRICE_FLOOR:
                    inv[item] += 1
    return revenues[0], revenues[1]


def _market_multiset(action: Mapping[str, Any]) -> Counter[tuple[Any, ...]]:
    return Counter(tuple(order) for order in action.get("market", []))


def _all_sell(action: Mapping[str, Any]) -> bool:
    market = action.get("market", [])
    return bool(market) and all(_parse_sell(order) is not None for order in market)


def _has_hidden_inventory_buy(action: Mapping[str, Any]) -> bool:
    """Orders whose asymmetric execution can invisibly break the mirror.

    HIRE and BUY_LAND are public on the following observation.  Identical
    farmer/hand transfers preserve an already equal shed.  Product/animal buys
    and seeds can instead diverge because the two public cash balances may
    differ after a queue intervention while their immediate result is private.
    """

    return any(
        order
        and str(order[0]) in {"BUY_PRODUCT", "BUY_ANIMAL", "BUY_SEED"}
        for order in action.get("market", [])
    )


def _hidden_buys_provably_symmetric(
    obs: Any,
    action: Mapping[str, Any],
    opponent_action: Mapping[str, Any],
) -> bool:
    """Exact equality proof for identical queues under market lockstep.

    This models only the hidden state relevant to later A2 actions: shed, seeds
    and cash-dependent execution.  The two queues must be byte-for-byte equal;
    same-turn shed transfers and atomic HIRE/LAND are rejected because they are
    processed outside this small simulator.  For SELL/BUY_* orders we replay
    the official quote-both-then-commit-both unit loop.  Equality is preserved
    whenever both seats can commit, or both fail, on every unit.  A one-sided
    commit is the only failure condition.
    """

    left = _canonical_action(action)
    right = _canonical_action(opponent_action)
    if left["market"] != right["market"]:
        return False
    if _has_same_turn_shed_transfer(left) or _has_same_turn_shed_transfer(right):
        return False
    if any(order and str(order[0]) in {"HIRE", "BUY_LAND"} for order in left["market"]):
        return False
    farms = list(_get(obs, "farms", []) or [])
    if len(farms) != 2:
        return False
    try:
        seat = _seat(obs)
        cash = [
            float(_get(farms[seat], "money", 0.0) or 0.0),
            float(_get(farms[1 - seat], "money", 0.0) or 0.0),
        ]
    except (TypeError, ValueError):
        return False
    inventory = _inventory(obs)
    sheds = [Counter(_shed(obs)), Counter(_shed(obs))]
    for order in left["market"]:
        if not order:
            continue
        op = str(order[0])
        if op in {"HIRE", "BUY_LAND"}:
            return False
        if len(order) < 3:
            continue
        item = str(order[1])
        try:
            remaining = max(0, int(order[2]))
        except (TypeError, ValueError):
            return False
        for _ in range(remaining):
            if op == "SELL" and item in MARKET_PARAMS:
                price = _market_price(item, int(inventory.get(item, 10000)))
                can = [sheds[player][item] > 0 for player in (0, 1)]
            elif op == "BUY_PRODUCT" and item in {"WHEAT", "FERTILIZER"}:
                price = _market_price(item, int(inventory.get(item, 10000)) - 1)
                can = [
                    cash[player] + 1e-9 >= price
                    and sum(sheds[player].values()) < SHED_CAPACITY
                    for player in (0, 1)
                ]
            elif op == "BUY_SEED" and item in SEED_COSTS:
                price = SEED_COSTS[item]
                can = [cash[player] + 1e-9 >= price for player in (0, 1)]
            elif op == "BUY_ANIMAL" and item in ANIMAL_COSTS:
                price = ANIMAL_COSTS[item]
                can = [
                    cash[player] + 1e-9 >= price
                    and sum(sheds[player].values()) < SHED_CAPACITY
                    for player in (0, 1)
                ]
            else:
                return False
            if can[0] != can[1]:
                return False
            if not can[0]:
                break
            if op == "SELL":
                for player in (0, 1):
                    sheds[player][item] -= 1
                    cash[player] += price
                if price > PRICE_FLOOR:
                    inventory[item] = int(inventory.get(item, 10000)) + 2
            elif op == "BUY_PRODUCT":
                for player in (0, 1):
                    cash[player] -= price
                    sheds[player][item] += 1
                inventory[item] = int(inventory.get(item, 10000)) - 2
            elif op == "BUY_SEED":
                for player in (0, 1):
                    cash[player] -= price
            elif op == "BUY_ANIMAL":
                for player in (0, 1):
                    cash[player] -= price
                    sheds[player][item] += 1
    return True


def _opponent_observation(obs: Any, private: Any | None = None) -> Any:
    """Flip the public seat and inject the independently tracked private state."""

    swapped = copy.deepcopy(obs)
    player = 1 - _seat(obs)
    if isinstance(swapped, Mapping):
        swapped["player"] = player
        if private is not None:
            swapped["private"] = copy.deepcopy(private)
    else:
        setattr(swapped, "player", player)
        if private is not None:
            setattr(swapped, "private", copy.deepcopy(private))
    return swapped


def _configuration_supported(configuration: Any) -> bool:
    """Fail closed outside the sealed Kaggriculture 1.32.7 defaults."""

    try:
        shed_capacity = int(_get(configuration, "shedCapacity", SHED_CAPACITY) or SHED_CAPACITY)
        max_orders = int(_get(configuration, "maxMarketOrdersPerTurn", 10) or 10)
    except (TypeError, ValueError):
        return False
    market_params = _get(configuration, "marketParams", {}) or {}
    return shed_capacity == SHED_CAPACITY and max_orders == 10 and not dict(market_params)


def _private_copy(obs: Any) -> Any:
    return copy.deepcopy(_get(obs, "private", {}) or {})


def _apply_unit_queue(
    farm: Any,
    private: Any,
    action: Mapping[str, Any],
    *,
    board_size: int,
    day: int,
    turns_per_day: int,
    shed_capacity: int,
) -> None:
    """Apply the official unit phase, including atomic PLANT validation."""

    if kg is None:
        raise RuntimeError("kaggriculture engine helpers unavailable")
    farmer_action = action.get("farmer", ["PASS"])
    hands_actions = list(action.get("hands", []) or [])
    unit_actions = [farmer_action, *hands_actions]
    plant_demand: Counter[str] = Counter()
    for unit_action in unit_actions:
        if isinstance(unit_action, list) and len(unit_action) >= 2 and unit_action[0] == "PLANT":
            plant_demand[str(unit_action[1])] += 1
    seeds = _get(private, "seeds", {}) or {}
    blocked = {crop for crop, count in plant_demand.items() if count > int(_get(seeds, crop, 0) or 0)}

    def allowed(unit_action: Any) -> Any:
        if (
            isinstance(unit_action, list)
            and len(unit_action) >= 2
            and unit_action[0] == "PLANT"
            and str(unit_action[1]) in blocked
        ):
            return ["PASS"]
        return unit_action

    kg._apply_unit_action(
        farm, private, 0, allowed(farmer_action), board_size, day,
        turns_per_day, shed_capacity,
    )
    for index, hand_action in enumerate(hands_actions, 1):
        kg._apply_unit_action(
            farm, private, index, allowed(hand_action), board_size, day,
            turns_per_day, shed_capacity,
        )


def _advance_opponent_private(
    obs: Any,
    configuration: Any,
    candidate_action: Mapping[str, Any],
    opponent_action: Mapping[str, Any],
    opponent_private: Any,
) -> tuple[Any, float, float, dict[str, int], str | None]:
    """Advance the hidden opponent state with official 1.32.7 helpers."""

    if kg is None or not _configuration_supported(configuration):
        raise RuntimeError("unsupported shadow runtime")
    step = int(_get(obs, "step", 0) or 0)
    seat = _seat(obs)
    opponent = 1 - seat
    board_size = int(_get(configuration, "boardSize", 10) or 10)
    turns_per_day = max(1, int(_get(configuration, "turnsPerDay", 24) or 24))
    shed_capacity = int(_get(configuration, "shedCapacity", SHED_CAPACITY) or SHED_CAPACITY)
    day = step // turns_per_day
    farms = copy.deepcopy(list(_get(obs, "farms", []) or []))
    if len(farms) != 2:
        raise RuntimeError("expected two farms")
    privates = [None, None]
    privates[seat] = _private_copy(obs)
    privates[opponent] = copy.deepcopy(opponent_private)
    actions = [None, None]
    actions[seat] = _canonical_action(candidate_action)
    actions[opponent] = _canonical_action(opponent_action)
    for player in (0, 1):
        _apply_unit_queue(
            farms[player], privates[player], actions[player],
            board_size=board_size, day=day, turns_per_day=turns_per_day,
            shed_capacity=shed_capacity,
        )
    shared = SimpleNamespace(
        market=copy.deepcopy(_get(obs, "market", {}) or {}),
        farms=farms,
        town=copy.deepcopy(_get(obs, "town", {}) or {}),
    )
    states = []
    for player in (0, 1):
        states.append(
            SimpleNamespace(
                observation=SimpleNamespace(
                    market=shared.market,
                    farms=shared.farms,
                    town=shared.town,
                    private=privates[player],
                ),
                action=actions[player],
            )
        )
    env = SimpleNamespace(configuration=configuration)
    kg._process_market(states, env)
    kg._town_consume(env, states, step)
    for farm in farms:
        kg._decay_plants(farm, step)
    day_boundary = (step + 1) % turns_per_day == 0
    if day_boundary:
        kg._drop_inventories_to_shed(privates[opponent], shed_capacity)
        privates[opponent]["inventories"] = [{}]
    market_inventory = {
        str(item): int(quantity or 0)
        for item, quantity in dict(_get(shared.market, "inventory", {}) or {}).items()
    }
    public_state = None if day_boundary else _public_farm_state(farms[opponent])
    return (
        copy.deepcopy(privates[opponent]),
        float(_get(farms[opponent], "money", 0.0) or 0.0),
        float(_get(farms[seat], "money", 0.0) or 0.0),
        market_inventory,
        public_state,
    )


def _best_sell_permutation(
    obs: Any,
    action: Mapping[str, Any],
    opponent_action: Mapping[str, Any],
    opponent_obs: Any,
    max_sell_orders: int = 7,
) -> tuple[dict[str, list[Any]], float, tuple[str, ...]]:
    result = _canonical_action(action)
    market = result["market"]
    # Strict discovery invariant: the simulator below is exact only when the
    # whole queue is SELL-only.  Mixed BUY/HIRE/LAND queues can change cash,
    # shed capacity or shared inventory between SELL slots and are rejected.
    opponent_market = _canonical_action(opponent_action)["market"]
    if (
        not market
        or any(_parse_sell(order) is None for order in market)
        or any(_parse_sell(order) is None for order in opponent_market)
    ):
        return result, 0.0, ()
    if _has_same_turn_shed_transfer(result):
        return result, 0.0, ()
    sell_indices = [index for index, order in enumerate(market) if _parse_sell(order)]
    if (
        len(sell_indices) < 2
        or len(sell_indices) > int(max_sell_orders)
        or len({str(market[index][1]) for index in sell_indices}) < 2
    ):
        return result, 0.0, ()
    sells = [market[index] for index in sell_indices]
    # Repeated identical orders need not create repeated factorial work.
    permutations = sorted(
        {tuple(tuple(value) for value in order) for order in itertools.permutations(sells)},
        key=lambda order: tuple(str(value) for row in order for value in row),
    )
    inventory = _inventory(obs)
    shed = _shed(obs)
    opponent_shed = _shed(opponent_obs)
    base_ours, base_theirs = _simulate_sell_queues(
        market, opponent_market, inventory, shed, opponent_shed
    )
    best_market = market
    best_advantage = base_ours - base_theirs
    best_revenue = base_ours
    best_key: tuple[str, ...] = tuple(str(order[1]) for order in sells)
    for permutation in permutations:
        candidate_market = [list(order) for order in market]
        for index, order in zip(sell_indices, permutation):
            candidate_market[index] = list(order)
        ours, theirs = _simulate_sell_queues(
            candidate_market, opponent_market, inventory, shed, opponent_shed
        )
        advantage = ours - theirs
        key = tuple(str(order[1]) for order in permutation)
        # Never buy a relative advantage by lowering our own immediate SELL
        # revenue.  This keeps production liquidity at least as safe as A2.
        eligible = ours + 1e-9 >= base_ours
        if eligible and (
            advantage > best_advantage + 1e-9
            or (
                abs(advantage - best_advantage) <= 1e-9
                and (ours > best_revenue + 1e-9 or (abs(ours - best_revenue) <= 1e-9 and key < best_key))
            )
        ):
            best_market = candidate_market
            best_advantage = advantage
            best_revenue = ours
            best_key = key
    if best_advantage <= 0 or best_market == market:
        return result, 0.0, ()
    result["market"] = best_market
    return result, float(best_advantage), best_key


class QueueBestResponseAgent:
    def __init__(
        self,
        *,
        max_clone_distance: int = 4,
        start_step: int = 96,
        minimum_conformance_steps: int = 72,
        require_public_mirror: bool = True,
    ) -> None:
        self.parent = a2.make_agent()
        self.opponent_shadow = a2.make_agent()
        self.max_clone_distance = int(max_clone_distance)
        self.start_step = int(start_step)
        self.minimum_conformance_steps = int(minimum_conformance_steps)
        self.require_public_mirror = bool(require_public_mirror)
        self.last_step = -1
        self.calls = 0
        self.reordered_steps = 0
        self.predicted_advantage = 0.0
        self.reordered_products: Counter[str] = Counter()
        self.skip_reasons: Counter[str] = Counter()
        self.own_branch: str | None = None
        self.opponent_branch: str | None = None
        self.opponent_private: Any | None = None
        self.predicted_opponent_money: float | None = None
        self.predicted_own_money: float | None = None
        self.predicted_market_inventory: dict[str, int] | None = None
        self.predicted_opponent_public: str | None = None
        self.expected_next_step: int | None = None
        self.shadow_trusted = True
        self.conformance_steps = 0
        self.shadow_faults = 0
        self.shadow_update_errors = 0

    def _reset(self, obs: Any) -> None:
        self.last_step = -1
        self.calls = 0
        self.reordered_steps = 0
        self.predicted_advantage = 0.0
        self.reordered_products.clear()
        self.skip_reasons.clear()
        self.own_branch = None
        self.opponent_branch = None
        # Both seats start from the same public initial private schema.
        self.opponent_private = _private_copy(obs)
        self.predicted_opponent_money = None
        self.predicted_own_money = None
        self.predicted_market_inventory = None
        self.predicted_opponent_public = None
        self.expected_next_step = None
        self.shadow_trusted = int(_get(obs, "step", 0) or 0) == 0
        self.conformance_steps = 0
        self.shadow_faults = 0
        self.shadow_update_errors = 0

    @staticmethod
    def _selected_branch(agent: Any) -> str | None:
        method = getattr(agent, "_selected_branch", None)
        selected = method() if callable(method) else None
        return str(selected) if selected else None

    def _check_previous_prediction(self, obs: Any) -> None:
        if self.predicted_opponent_money is None:
            return
        step = int(_get(obs, "step", 0) or 0)
        if self.expected_next_step is None or step != self.expected_next_step:
            self.shadow_trusted = False
            self.shadow_faults += 1
            return
        farms = list(_get(obs, "farms", []) or [])
        if len(farms) != 2:
            self.shadow_trusted = False
            self.shadow_faults += 1
            return
        seat = _seat(obs)
        actual_opponent = float(_get(farms[1 - seat], "money", 0.0) or 0.0)
        actual_own = float(_get(farms[seat], "money", 0.0) or 0.0)
        actual_market = {
            str(item): int(quantity or 0)
            for item, quantity in dict(
                _get(_get(obs, "market", {}) or {}, "inventory", {}) or {}
            ).items()
        }
        public_ok = (
            self.predicted_opponent_public is None
            or _public_farm_state(farms[1 - seat]) == self.predicted_opponent_public
        )
        if (
            abs(actual_opponent - self.predicted_opponent_money) <= 1e-9
            and self.predicted_own_money is not None
            and abs(actual_own - self.predicted_own_money) <= 1e-9
            and self.predicted_market_inventory == actual_market
            and public_ok
        ):
            self.conformance_steps += 1
        else:
            self.shadow_trusted = False
            self.shadow_faults += 1

    def __call__(self, obs: Any, configuration: Any = None) -> dict[str, list[Any]]:
        step = int(_get(obs, "step", 0) or 0)
        if step == 0 or step < self.last_step or self.opponent_private is None:
            self._reset(obs)
        self.last_step = step
        self.calls += 1
        self._check_previous_prediction(obs)

        parent_action = _canonical_action(self.parent(obs, configuration))
        opponent_obs = _opponent_observation(obs, self.opponent_private)
        opponent_action = _canonical_action(self.opponent_shadow(opponent_obs, configuration))
        self.own_branch = self._selected_branch(self.parent)
        self.opponent_branch = self._selected_branch(self.opponent_shadow)
        result = parent_action
        advantage = 0.0
        products: tuple[str, ...] = ()

        if kg is None or not _configuration_supported(configuration):
            self.shadow_trusted = False
            self.skip_reasons["unsupported_shadow_runtime"] += 1
        elif step < self.start_step:
            self.skip_reasons["before_start"] += 1
        elif not self.shadow_trusted or self.conformance_steps < self.minimum_conformance_steps:
            self.skip_reasons["insufficient_shadow_conformance"] += 1
        elif self.own_branch != "baseline_v8" or self.opponent_branch != "baseline_v8":
            self.skip_reasons["not_v8_v8"] += 1
        elif (
            (self.require_public_mirror and not _public_production_equal(obs))
            or _clone_distance(obs) > self.max_clone_distance
        ):
            self.skip_reasons["public_production_not_mirror"] += 1
        elif _has_same_turn_shed_transfer(parent_action) or _has_same_turn_shed_transfer(opponent_action):
            self.skip_reasons["same_turn_shed_transfer"] += 1
        else:
            candidate, advantage, products = _best_sell_permutation(
                obs, parent_action, opponent_action, opponent_obs
            )
            if candidate == parent_action:
                self.skip_reasons["no_positive_queue_best_response"] += 1
            else:
                before = Counter(
                    (str(x[0]), str(x[1]), int(x[2]))
                    for x in parent_action["market"] if len(x) >= 3
                )
                after = Counter(
                    (str(x[0]), str(x[1]), int(x[2]))
                    for x in candidate["market"] if len(x) >= 3
                )
                if candidate["farmer"] != parent_action["farmer"] or candidate["hands"] != parent_action["hands"]:
                    self.skip_reasons["production_invariant_failure"] += 1
                elif before != after:
                    self.skip_reasons["quantity_invariant_failure"] += 1
                else:
                    result = candidate
                    self.reordered_steps += 1
                    self.predicted_advantage += float(advantage)
                    self.reordered_products.update(products)

        # Advance even while fail-closed so the full prefix is audited.  Once a
        # mismatch occurs shadow_trusted never becomes true again this episode.
        try:
            (
                self.opponent_private,
                self.predicted_opponent_money,
                self.predicted_own_money,
                self.predicted_market_inventory,
                self.predicted_opponent_public,
            ) = _advance_opponent_private(
                obs, configuration, result, opponent_action, self.opponent_private
            )
            self.expected_next_step = step + 1
        except Exception:
            self.shadow_trusted = False
            self.shadow_update_errors += 1
            self.predicted_opponent_money = None
            self.predicted_own_money = None
            self.predicted_market_inventory = None
            self.predicted_opponent_public = None
            self.expected_next_step = None
        return result

    def diagnostics(self) -> dict[str, Any]:
        method = getattr(self.parent, "diagnostics", None)
        parent_diagnostics = dict(method()) if callable(method) else {}
        return {
            "kind": MODEL_ID,
            "model_id": MODEL_ID,
            "calls": self.calls,
            "reordered_steps": self.reordered_steps,
            "predicted_advantage": self.predicted_advantage,
            "reordered_products": dict(self.reordered_products),
            "skip_reasons": dict(self.skip_reasons),
            "max_clone_distance": self.max_clone_distance,
            "start_step": self.start_step,
            "minimum_conformance_steps": self.minimum_conformance_steps,
            "require_public_mirror": self.require_public_mirror,
            "own_branch": self.own_branch,
            "opponent_branch": self.opponent_branch,
            "shadow_trusted": self.shadow_trusted,
            "conformance_steps": self.conformance_steps,
            "shadow_faults": self.shadow_faults,
            "shadow_update_errors": self.shadow_update_errors,
            "conformance_fields": [
                "step",
                "own_money",
                "opponent_money",
                "market_inventory",
                "opponent_public_farm_non_day_boundary",
            ],
            "parent_diagnostics": parent_diagnostics,
        }


def make_agent() -> QueueBestResponseAgent:
    return QueueBestResponseAgent()
