"""V14-S0：A2 上的 hour=23 肥料拾取安全消融。

只把日末会被统一重置的位置动作（移动或 PASS）替换为
COLLECT_FERTILIZER。父策略的市场、其它工人动作和全部跨日状态机均不变。
"""

from __future__ import annotations

from collections import Counter
import copy
from typing import Any, Mapping, Sequence

from kaggle_Kaggriculture.model.v12a2_no_shop_gate import main as a2


MODEL_ID = "v14_s0_eod_fertilizer"
RESET_ACTIONS = frozenset({"PASS", "NORTH", "SOUTH", "EAST", "WEST"})


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


def _own_farm(obs: Any) -> Any:
    farms = list(_get(obs, "farms", []) or [])
    seat = _seat(obs)
    return farms[seat] if seat < len(farms) else {}


def _tile_at(farm: Any, position: Sequence[Any]) -> Any:
    try:
        x, y = int(position[0]), int(position[1])
        return (_get(farm, "tiles", []) or [])[y][x]
    except (IndexError, TypeError, ValueError):
        return "LOCKED"


def _private_total(obs: Any) -> int:
    private = _get(obs, "private", {}) or {}
    shed = dict(_get(private, "shed", {}) or {})
    inventories = list(_get(private, "inventories", []) or [])
    return sum(max(0, int(value or 0)) for value in shed.values()) + sum(
        max(0, int(value or 0))
        for inventory in inventories
        for value in dict(inventory or {}).values()
    )


def _worst_case_parent_additions(
    obs: Any, action: Mapping[str, Any]
) -> int:
    """父动作本回合可能新增到私有商品总量的保守上界。

    不扣除 FEED/FERTILIZE/SELL 等消耗，所以这是上界；DROP/PICKUP 只在
    仓库与携带间搬运，不改变总量。这样即使市场买单全部成功也不会把
    新拾取的肥料挤出仓库。
    """

    farm = _own_farm(obs)
    positions = [
        list(_get(farm, "farmer", [4, 4]) or [4, 4]),
        *[list(value) for value in (_get(farm, "hands", []) or [])],
    ]
    unit_orders = [action.get("farmer", ["PASS"]), *(action.get("hands") or [])]
    additions = 0
    collected_tiles: set[tuple[int, int]] = set()
    for index, order in enumerate(unit_orders):
        if index >= len(positions) or not order:
            continue
        tile = _tile_at(farm, positions[index])
        op = str(order[0])
        if op == "HARVEST" and isinstance(tile, Mapping):
            additions += max(0, int(tile.get("yield_units", 0) or 0))
        elif (
            op == "COLLECT_FERTILIZER"
            and isinstance(tile, Mapping)
            and bool(tile.get("fertilizer_available", False))
        ):
            coordinate = (int(positions[index][0]), int(positions[index][1]))
            if coordinate not in collected_tiles:
                additions += 1
                collected_tiles.add(coordinate)
    for order in action.get("market", []):
        if (
            len(order) >= 3
            and str(order[0]) in {"BUY_PRODUCT", "BUY_ANIMAL"}
        ):
            additions += max(0, int(order[2] or 0))
    return additions


def apply_eod_fertilizer_collect(
    obs: Any,
    parent_action: Mapping[str, Any],
    *,
    maximum_private_total: int = 90,
) -> tuple[dict[str, list[Any]], dict[str, Any]]:
    """返回修改动作与可审计的单回合诊断。"""

    result = _canonical_action(parent_action)
    diagnostic = {
        "eligible_actors": 0,
        "collected_units": 0,
        "projected_private_total": _private_total(obs),
        "skip_reason": "not_hour_23",
    }
    if int(_get(obs, "hour", int(_get(obs, "step", 0) or 0) % 24) or 0) != 23:
        return result, diagnostic

    farm = _own_farm(obs)
    positions = [
        list(_get(farm, "farmer", [4, 4]) or [4, 4]),
        *[list(value) for value in (_get(farm, "hands", []) or [])],
    ]
    orders = [result["farmer"], *result["hands"]]
    projected = _private_total(obs) + _worst_case_parent_additions(obs, result)
    diagnostic["projected_private_total"] = projected
    used_tiles: set[tuple[int, int]] = set()
    for index, order in enumerate(orders):
        if index >= len(positions) or not order or str(order[0]) not in RESET_ACTIONS:
            continue
        tile = _tile_at(farm, positions[index])
        if not (
            isinstance(tile, Mapping)
            and tile.get("animal")
            and bool(tile.get("fertilizer_available", False))
        ):
            continue
        coordinate = (int(positions[index][0]), int(positions[index][1]))
        if coordinate in used_tiles:
            continue
        diagnostic["eligible_actors"] += 1
        if projected + 1 > int(maximum_private_total):
            diagnostic["skip_reason"] = "private_headroom_guard"
            continue
        orders[index] = ["COLLECT_FERTILIZER"]
        used_tiles.add(coordinate)
        projected += 1
        diagnostic["collected_units"] += 1

    result["farmer"] = orders[0] if orders else ["PASS"]
    result["hands"] = orders[1:]
    diagnostic["projected_private_total"] = projected
    diagnostic["skip_reason"] = (
        "collected" if diagnostic["collected_units"] else "no_resettable_animal_actor"
    )
    return result, diagnostic


class EodFertilizerAgent(a2.NoShopGateAgent):
    """完整继承 A2，只增加 S0 残差。"""

    def __init__(self, *, maximum_private_total: int = 90) -> None:
        self.maximum_private_total = int(maximum_private_total)
        super().__init__()

    def _reset(self) -> None:
        super()._reset()
        self.s0_changed_steps = 0
        self.s0_collected_units = 0
        self.s0_eligible_actors = 0
        self.s0_residual_fallbacks = 0
        self.s0_skip_reasons: Counter[str] = Counter()

    def __call__(self, obs: Any, configuration: Any = None) -> dict[str, list[Any]]:
        parent_action = _canonical_action(super().__call__(obs, configuration))
        try:
            result, diag = apply_eod_fertilizer_collect(
                obs,
                parent_action,
                maximum_private_total=self.maximum_private_total,
            )
            self.s0_eligible_actors += int(diag["eligible_actors"])
            self.s0_collected_units += int(diag["collected_units"])
            self.s0_skip_reasons[str(diag["skip_reason"])] += 1
            if result["market"] != parent_action["market"]:
                raise AssertionError("S0 changed market orders")
            if len(result["hands"]) != len(parent_action["hands"]):
                raise AssertionError("S0 changed hand count")
            if result != parent_action:
                self.s0_changed_steps += 1
            return result
        except Exception:
            self.s0_residual_fallbacks += 1
            return parent_action

    def diagnostics(self) -> dict[str, Any]:
        payload = copy.deepcopy(super().diagnostics())
        payload.update(
            {
                "kind": MODEL_ID,
                "model_id": MODEL_ID,
                "parent_id": a2.MODEL_ID,
                "s0_changed_steps": self.s0_changed_steps,
                "s0_collected_units": self.s0_collected_units,
                "s0_eligible_actors": self.s0_eligible_actors,
                "s0_residual_fallbacks": self.s0_residual_fallbacks,
                "s0_skip_reasons": dict(self.s0_skip_reasons),
                "maximum_private_total": self.maximum_private_total,
            }
        )
        return payload


def make_agent() -> EodFertilizerAgent:
    return EodFertilizerAgent()


_AGENT: EodFertilizerAgent | None = None


def agent(obs: Any, configuration: Any = None) -> dict[str, list[Any]]:
    global _AGENT
    step = int(_get(obs, "step", 0) or 0)
    if _AGENT is None or step == 0 or step < _AGENT.last_step:
        _AGENT = make_agent()
    return _AGENT(obs, configuration)
