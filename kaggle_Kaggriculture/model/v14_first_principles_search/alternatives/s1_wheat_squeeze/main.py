"""V14-S1：A2 上的库存中性 WHEAT squeeze 最小可证伪原型。

严格门控下，把下一回合双方同槽同量买 WHEAT 的父策略改写为：本回合
先买 q+r，下一回合把我方 BUY(q) 原槽替换成 SELL(r)。两回合我方仍净买
q，目标回合后共享市场库存恢复父路径；只改变双方现金成本。

本文件是开发候选，不是提交包。
"""

from __future__ import annotations

from collections import Counter
import copy
import json
import math
from typing import Any, Mapping, Sequence

from kaggle_Kaggriculture.model.v12a2_no_shop_gate import main as a2
from kaggle_Kaggriculture.model.v8_kawa_lead2_slot import main as v8


MODEL_ID = "v14_s1_inventory_neutral_wheat_squeeze"
PRICE_FLOOR = 1
WHEAT_PARAMS = {
    "base": 25,
    "I0": 10000,
    "T": 400,
    "below_func": "sqrt",
    "below_target": 0.80,
    "above_func": "log",
    "above_target": 0.20,
}
WHEAT_SHOPS = frozenset(
    {"BAKERY", "PIZZA_SHOP", "BRUNCH_SPOT", "ICE_CREAM_SHOP", "FARMERS_MARKET"}
)


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


def _opponent_observation(obs: Any) -> Any:
    swapped = copy.deepcopy(obs)
    player = 1 - _seat(obs)
    if isinstance(swapped, Mapping):
        swapped["player"] = player
    else:
        setattr(swapped, "player", player)
    return swapped


def _shape(name: str, value: float) -> float:
    value = max(0.0, float(value))
    if name == "sqrt":
        return math.sqrt(value)
    if name == "log":
        return math.log1p(value)
    raise ValueError(f"unsupported WHEAT price shape: {name}")


def market_price_wheat(inventory: int) -> int:
    """与官方引擎默认 WHEAT 参数逐整数一致。"""

    p = WHEAT_PARAMS
    base = float(p["base"])
    initial = int(p["I0"])
    threshold = float(p["T"])
    if int(inventory) < initial:
        amplitude = float(p["below_target"]) * base / _shape(
            str(p["below_func"]), threshold
        )
        price = base + amplitude * _shape(
            str(p["below_func"]), initial - int(inventory)
        )
    else:
        amplitude = float(p["above_target"]) * base / _shape(
            str(p["above_func"]), threshold
        )
        price = base - amplitude * _shape(
            str(p["above_func"]), int(inventory) - initial
        )
    return max(PRICE_FLOOR, int(round(price)))


def _town_wheat_drain(obs: Any, step: int) -> int:
    drain = 1 if int(step) % 24 == 0 else 0
    if int(step) % 4 == 0:
        town = _get(obs, "town", {}) or {}
        for shop in (_get(town, "unlocked_shops", []) or []):
            if str(shop) in WHEAT_SHOPS:
                drain += 1
    return drain


def simulate_squeeze(
    inventory: int, q: int, r: int, drain: int
) -> dict[str, int]:
    """精确模拟父交易与 squeeze 的 WHEAT 现金、库存结果。"""

    inventory, q, r, drain = int(inventory), int(q), int(r), int(drain)
    if q <= 0 or r <= 0 or r > q or drain < 0:
        raise ValueError("invalid squeeze quantities")
    baseline_cost = sum(
        market_price_wheat(inventory - drain - 2 * index + 1)
        for index in range(1, q + 1)
    )
    prep_quantity = q + r
    prep_cost = sum(
        market_price_wheat(inventory - index)
        for index in range(1, prep_quantity + 1)
    )
    target_inventory = inventory - prep_quantity - drain
    sale_price = market_price_wheat(target_inventory)
    own_revenue = r * sale_price
    opponent_cost = r * market_price_wheat(target_inventory - 1) + sum(
        market_price_wheat(target_inventory - index)
        for index in range(1, q - r + 1)
    )
    candidate_own_cost = prep_cost - own_revenue
    own_gain = baseline_cost - candidate_own_cost
    opponent_penalty = opponent_cost - baseline_cost
    return {
        "inventory_before": inventory,
        "drain": drain,
        "q": q,
        "r": r,
        "prep_quantity": prep_quantity,
        "prep_cost": prep_cost,
        "baseline_own_cost": baseline_cost,
        "candidate_own_cost": candidate_own_cost,
        "candidate_opponent_cost": opponent_cost,
        "sale_price": sale_price,
        "own_gain": own_gain,
        "opponent_penalty": opponent_penalty,
        "relative_margin_gain": own_gain + opponent_penalty,
        "baseline_final_inventory": inventory - drain - 2 * q,
        "candidate_final_inventory": target_inventory - (q - r),
        "baseline_net_wheat": q,
        "candidate_net_wheat": prep_quantity - r,
    }


def choose_squeeze(
    inventory: int,
    q: int,
    drain: int,
    *,
    max_r: int = 12,
    minimum_relative_gain: int = 1,
) -> dict[str, int] | None:
    candidates = sorted(
        {
            value
            for value in (1, 2, 4, 8, min(int(q), int(max_r)), int(q))
            if 1 <= int(value) <= int(q) and int(value) <= int(max_r)
        }
    )
    for r in candidates:
        result = simulate_squeeze(inventory, q, r, drain)
        if (
            result["sale_price"] > PRICE_FLOOR
            and result["own_gain"] >= 0
            and result["opponent_penalty"] >= 0
            and result["relative_margin_gain"] >= int(minimum_relative_gain)
            and result["baseline_final_inventory"]
            == result["candidate_final_inventory"]
            and result["baseline_net_wheat"] == result["candidate_net_wheat"]
        ):
            return result
    return None


def _public_farm_state(farm: Any) -> str:
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


def _route_action(obs: Any, step: int) -> dict[str, list[Any]]:
    actions = v8._kawa_actions(obs)
    index = min(max(0, int(step)), len(actions) - 1)
    return _canonical_action(actions[index] or {})


def _singleton_wheat_buy(action: Mapping[str, Any]) -> int | None:
    market = list(action.get("market", []) or [])
    if len(market) != 1:
        return None
    order = market[0]
    if (
        len(order) < 3
        or str(order[0]) != "BUY_PRODUCT"
        or str(order[1]) != "WHEAT"
    ):
        return None
    quantity = max(0, int(order[2] or 0))
    return quantity if quantity else None


def _has_shed_deposit(action: Mapping[str, Any]) -> bool:
    orders = [action.get("farmer", ["PASS"]), *(action.get("hands") or [])]
    return any(order and str(order[0]) in {"DROP", "PLACE"} for order in orders)


def _shed(obs: Any) -> dict[str, int]:
    private = _get(obs, "private", {}) or {}
    return {
        str(key): max(0, int(value or 0))
        for key, value in dict(_get(private, "shed", {}) or {}).items()
    }


def _money(obs: Any) -> float:
    farms = list(_get(obs, "farms", []) or [])
    seat = _seat(obs)
    farm = farms[seat] if seat < len(farms) else {}
    return float(_get(farm, "money", 0.0) or 0.0)


def _wheat_after_pickups(obs: Any, action: Mapping[str, Any]) -> int:
    available = int(_shed(obs).get("WHEAT", 0))
    orders = [action.get("farmer", ["PASS"]), *(action.get("hands") or [])]
    for order in orders:
        if order and str(order[0]) == "PICKUP" and len(order) >= 2 and str(order[1]) == "WHEAT":
            requested = int(order[2]) if len(order) >= 3 else 1
            available -= min(max(0, requested), max(0, available))
    return max(0, available)


class InventoryNeutralWheatSqueezeAgent(a2.NoShopGateAgent):
    """完整继承 A2，只增加 S1 两回合市场残差。"""

    def __init__(
        self,
        *,
        cash_reserve: int = 1500,
        maximum_shed_after_prep: int = 90,
        max_r: int = 12,
        minimum_relative_gain: int = 1,
    ) -> None:
        self.cash_reserve = int(cash_reserve)
        self.maximum_shed_after_prep = int(maximum_shed_after_prep)
        self.max_r = int(max_r)
        self.minimum_relative_gain = int(minimum_relative_gain)
        super().__init__()

    def _reset(self) -> None:
        super()._reset()
        self.s1_pending: dict[str, Any] | None = None
        self.s1_disabled = False
        self.s1_prepared = 0
        self.s1_executed = 0
        self.s1_unwinds = 0
        self.s1_pending_faults = 0
        self.s1_predicted_own_gain = 0
        self.s1_predicted_opponent_penalty = 0
        self.s1_predicted_relative_gain = 0
        self.s1_skip_reasons: Counter[str] = Counter()

    def _router(self) -> Any:
        current: Any = self.parent
        visited: set[int] = set()
        for _ in range(6):
            if current is None or id(current) in visited:
                break
            visited.add(id(current))
            if hasattr(current, "selector") and hasattr(current, "experts"):
                return current
            inner = getattr(current, "agent", None)
            current = inner if inner is not None else getattr(current, "parent", None)
        return None

    def _predict_opponent_branch(self, obs: Any) -> str | None:
        router = self._router()
        if router is None:
            return None
        eligible = list(getattr(router, "selection_eligible", []) or [])
        if not eligible:
            eligible = list(getattr(router, "experts", {}) or {})
        if not eligible:
            return None
        selector = router.selector
        old_scores = copy.deepcopy(getattr(selector, "last_scores", None))
        old_reason = getattr(selector, "last_reason", None)
        try:
            selected = str(selector.choose(_opponent_observation(obs), eligible))
            return selected if selected in eligible else None
        except Exception:
            return None
        finally:
            if old_scores is not None:
                selector.last_scores = old_scores
            if old_reason is not None:
                selector.last_reason = old_reason

    def _unwind(
        self, obs: Any, parent_action: Mapping[str, Any], pending: Mapping[str, Any]
    ) -> dict[str, list[Any]]:
        result = _canonical_action(parent_action)
        amount = int(pending["prep_quantity"])
        if len(result["market"]) < 10 and _wheat_after_pickups(obs, result) >= amount:
            result["market"].append(["SELL", "WHEAT", amount])
            self.s1_unwinds += 1
            return result
        self.s1_pending_faults += 1
        self.s1_disabled = True
        return result

    def _execute_pending(
        self,
        obs: Any,
        parent_action: Mapping[str, Any],
        own_route: Mapping[str, Any],
        opponent_route: Mapping[str, Any],
        own_branch: str | None,
        opponent_branch: str | None,
    ) -> dict[str, list[Any]]:
        assert self.s1_pending is not None
        pending = self.s1_pending
        self.s1_pending = None
        expected_q = int(pending["q"])
        parent_q = _singleton_wheat_buy(parent_action)
        opponent_q = _singleton_wheat_buy(opponent_route)
        route_q = _singleton_wheat_buy(own_route)
        exact = (
            own_branch == "baseline_v8"
            and opponent_branch == "baseline_v8"
            and _public_production_equal(obs)
            and parent_q == expected_q
            and route_q == expected_q
            and opponent_q == expected_q
            and _wheat_after_pickups(obs, parent_action) >= int(pending["r"])
        )
        if not exact:
            self.s1_skip_reasons["pending_prediction_mismatch"] += 1
            return self._unwind(obs, parent_action, pending)
        result = _canonical_action(parent_action)
        result["market"] = [["SELL", "WHEAT", int(pending["r"])]]
        self.s1_executed += 1
        self.s1_predicted_own_gain += int(pending["own_gain"])
        self.s1_predicted_opponent_penalty += int(pending["opponent_penalty"])
        self.s1_predicted_relative_gain += int(pending["relative_margin_gain"])
        return result

    def __call__(self, obs: Any, configuration: Any = None) -> dict[str, list[Any]]:
        step = int(_get(obs, "step", 0) or 0)
        parent_action = _canonical_action(super().__call__(obs, configuration))
        opponent_obs = _opponent_observation(obs)
        # 每回合都调用两侧纯路线选择，确保 V8 的 legacy-layout latch 与真实
        # step 0..71 轨迹同步；从不调用 V8 的有状态 agent。
        own_route = _route_action(obs, step)
        opponent_route = _route_action(opponent_obs, step)
        own_branch = self._selected_branch()
        opponent_branch = self._predict_opponent_branch(obs) if step >= 72 else None

        try:
            if self.s1_pending is not None:
                if step != int(self.s1_pending["target_step"]):
                    pending = self.s1_pending
                    self.s1_pending = None
                    self.s1_skip_reasons["pending_step_mismatch"] += 1
                    return self._unwind(obs, parent_action, pending)
                return self._execute_pending(
                    obs,
                    parent_action,
                    own_route,
                    opponent_route,
                    own_branch,
                    opponent_branch,
                )
            if self.s1_disabled:
                self.s1_skip_reasons["disabled_after_fault"] += 1
                return parent_action
            if step < 72 or step >= 700:
                self.s1_skip_reasons["outside_discovery_window"] += 1
                return parent_action
            hour = int(_get(obs, "hour", step % 24) or 0)
            if hour >= 22:
                self.s1_skip_reasons["near_day_boundary"] += 1
                return parent_action
            if own_branch != "baseline_v8" or opponent_branch != "baseline_v8":
                self.s1_skip_reasons["not_both_v8"] += 1
                return parent_action
            if not _public_production_equal(obs):
                self.s1_skip_reasons["public_production_not_mirror"] += 1
                return parent_action
            if parent_action["market"] or own_route["market"] or opponent_route["market"]:
                self.s1_skip_reasons["prep_market_not_empty"] += 1
                return parent_action
            if _has_shed_deposit(parent_action):
                self.s1_skip_reasons["same_turn_shed_deposit"] += 1
                return parent_action

            own_next = _route_action(obs, step + 1)
            opponent_next = _route_action(opponent_obs, step + 1)
            q = _singleton_wheat_buy(own_next)
            opponent_q = _singleton_wheat_buy(opponent_next)
            if q is None or opponent_q != q:
                self.s1_skip_reasons["next_not_same_singleton_wheat_buy"] += 1
                return parent_action
            next_units = [own_next["farmer"], *own_next["hands"]]
            if any(order and str(order[0]) == "PICKUP" for order in next_units):
                self.s1_skip_reasons["target_has_pickup"] += 1
                return parent_action

            market = _get(obs, "market", {}) or {}
            inventory = int(_get(_get(market, "inventory", {}) or {}, "WHEAT", 10000) or 10000)
            plan = choose_squeeze(
                inventory,
                q,
                _town_wheat_drain(obs, step),
                max_r=self.max_r,
                minimum_relative_gain=self.minimum_relative_gain,
            )
            if plan is None:
                self.s1_skip_reasons["no_integer_price_edge"] += 1
                return parent_action
            shed_total = sum(_shed(obs).values())
            if shed_total + int(plan["prep_quantity"]) > self.maximum_shed_after_prep:
                self.s1_skip_reasons["shed_headroom_guard"] += 1
                return parent_action
            if _money(obs) < float(plan["prep_cost"] + self.cash_reserve):
                self.s1_skip_reasons["cash_reserve_guard"] += 1
                return parent_action

            result = _canonical_action(parent_action)
            result["market"] = [
                ["BUY_PRODUCT", "WHEAT", int(plan["prep_quantity"])]
            ]
            self.s1_pending = {**plan, "target_step": step + 1}
            self.s1_prepared += 1
            return result
        except Exception:
            self.s1_pending_faults += 1
            self.s1_disabled = True
            return parent_action

    def diagnostics(self) -> dict[str, Any]:
        payload = copy.deepcopy(super().diagnostics())
        payload.update(
            {
                "kind": MODEL_ID,
                "model_id": MODEL_ID,
                "parent_id": a2.MODEL_ID,
                "s1_disabled": self.s1_disabled,
                "s1_pending": copy.deepcopy(self.s1_pending),
                "s1_prepared": self.s1_prepared,
                "s1_executed": self.s1_executed,
                "s1_unwinds": self.s1_unwinds,
                "s1_pending_faults": self.s1_pending_faults,
                "s1_predicted_own_gain": self.s1_predicted_own_gain,
                "s1_predicted_opponent_penalty": self.s1_predicted_opponent_penalty,
                "s1_predicted_relative_gain": self.s1_predicted_relative_gain,
                "s1_skip_reasons": dict(self.s1_skip_reasons),
                "cash_reserve": self.cash_reserve,
                "maximum_shed_after_prep": self.maximum_shed_after_prep,
                "max_r": self.max_r,
                "minimum_relative_gain": self.minimum_relative_gain,
            }
        )
        return payload


def make_agent() -> InventoryNeutralWheatSqueezeAgent:
    return InventoryNeutralWheatSqueezeAgent()


_AGENT: InventoryNeutralWheatSqueezeAgent | None = None


def agent(obs: Any, configuration: Any = None) -> dict[str, list[Any]]:
    global _AGENT
    step = int(_get(obs, "step", 0) or 0)
    if _AGENT is None or step == 0 or step < _AGENT.last_step:
        _AGENT = make_agent()
    return _AGENT(obs, configuration)
