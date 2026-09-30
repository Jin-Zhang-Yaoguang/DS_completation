"""Auditable market residuals for V11 candidate generation.

Every mutation wraps a complete parent agent.  None of the functions changes
farmer movement, hand tasks, land use, hiring, animal purchases, seed
purchases, or the parent's production route.  A catalog entry states exactly
which part of the existing market action it may change.
"""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass
from typing import Any, Callable, Mapping, Sequence


PRODUCTS = (
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
    "EGG", "MILK", "WOOL", "FERTILIZER",
)
ANIMAL_PRODUCTS = frozenset({"EGG", "MILK", "WOOL"})
PREMIUM_PRODUCTS = frozenset({"STRAWBERRY", "MELON", "MILK", "WOOL"})
BASE_PRICES = {
    "WHEAT": 25.0,
    "CARROT": 35.0,
    "TOMATO": 60.0,
    "STRAWBERRY": 120.0,
    "MELON": 250.0,
    "EGG": 50.0,
    "MILK": 160.0,
    "WOOL": 200.0,
    "FERTILIZER": 100.0,
}


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    getter = getattr(value, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(value, key, default)


def canonical_action(action: Mapping[str, Any] | None) -> dict[str, list[Any]]:
    """Deep-copy a Kaggriculture action into its three canonical fields."""

    source = copy.deepcopy(dict(action or {}))
    return {
        "farmer": list(source.get("farmer") or ["PASS"]),
        "hands": [list(item or ["PASS"]) for item in (source.get("hands") or [])],
        "market": [list(item) for item in (source.get("market") or [])],
    }


def _step(obs: Any) -> int:
    return int(_get(obs, "step", 0) or 0)


def _prices(obs: Any) -> Mapping[str, Any]:
    market = _get(obs, "market", {}) or {}
    return _get(market, "prices", {}) or {}


def _price_ratio(product: str, obs: Any) -> float:
    return float(_get(_prices(obs), product, 0.0) or 0.0) / max(
        1.0, BASE_PRICES.get(product, 1.0)
    )


def value_slot_priority(
    action: Mapping[str, Any], obs: Any, params: Mapping[str, Any]
) -> dict[str, list[Any]]:
    """Reorder existing SELL slots by live value; preserve all order multisets."""

    result = canonical_action(action)
    indices = [
        index
        for index, order in enumerate(result["market"])
        if len(order) >= 3 and str(order[0]) == "SELL" and int(order[2] or 0) > 0
    ]
    if len(indices) < int(params.get("min_sell_orders", 2)):
        return result
    ranked = [list(result["market"][index]) for index in indices]
    ranked.sort(
        key=lambda order: (
            _price_ratio(str(order[1]), obs),
            float(_get(_prices(obs), str(order[1]), 0.0) or 0.0)
            * int(order[2] or 0),
            str(order[1]) in PREMIUM_PRODUCTS,
            str(order[1]),
        ),
        reverse=True,
    )
    for index, order in zip(indices, ranked):
        result["market"][index] = order
    return result


def premium_floor_guard(
    action: Mapping[str, Any], obs: Any, params: Mapping[str, Any]
) -> dict[str, list[Any]]:
    """Withhold only low-price premium SELLs before the protected endgame."""

    result = canonical_action(action)
    if _step(obs) >= int(params.get("release_step", 696)):
        return result
    minimum_ratio = float(params.get("minimum_price_ratio", 0.55))
    result["market"] = [
        order
        for order in result["market"]
        if not (
            len(order) >= 3
            and str(order[0]) == "SELL"
            and str(order[1]) in PREMIUM_PRODUCTS
            and _price_ratio(str(order[1]), obs) < minimum_ratio
        )
    ]
    result["market"] = result["market"][:10]
    return result


def animal_batch_cap(
    action: Mapping[str, Any], obs: Any, params: Mapping[str, Any]
) -> dict[str, list[Any]]:
    """Cap an existing animal-product SELL batch outside the final day."""

    result = canonical_action(action)
    if _step(obs) >= int(params.get("release_step", 696)):
        return result
    cap = max(1, int(params.get("max_batch", 12)))
    for order in result["market"]:
        if (
            len(order) >= 3
            and str(order[0]) == "SELL"
            and str(order[1]) in ANIMAL_PRODUCTS
        ):
            order[2] = min(int(order[2] or 0), cap)
    return result


def topday_animal_throttle(
    action: Mapping[str, Any], obs: Any, params: Mapping[str, Any]
) -> dict[str, list[Any]]:
    """Reduce existing animal-product SELLs on explicit audited days."""

    result = canonical_action(action)
    days = {int(value) for value in params.get("days", (10, 17, 24))}
    day = int(_get(obs, "day", _step(obs) // 24) or 0)
    if day not in days:
        return result
    fraction = min(1.0, max(0.0, float(params.get("fraction", 0.5))))
    filtered = []
    for order in result["market"]:
        if (
            len(order) >= 3
            and str(order[0]) == "SELL"
            and str(order[1]) in ANIMAL_PRODUCTS
        ):
            order[2] = int(round(int(order[2] or 0) * fraction))
            if int(order[2]) <= 0:
                continue
        filtered.append(order)
    result["market"] = filtered[:10]
    return result


def terminal_clearance_fill(
    action: Mapping[str, Any], obs: Any, params: Mapping[str, Any]
) -> dict[str, list[Any]]:
    """Fill unused final market slots with the agent's own unsold shed stock."""

    result = canonical_action(action)
    if _step(obs) < int(params.get("start_step", 716)):
        return result
    private = _get(obs, "private", {}) or {}
    shed = _get(private, "shed", {}) or {}
    already = {}
    for order in result["market"]:
        if len(order) >= 3 and str(order[0]) == "SELL":
            product = str(order[1])
            already[product] = already.get(product, 0) + int(order[2] or 0)
    candidates = []
    for product in PRODUCTS:
        remaining = max(0, int(_get(shed, product, 0) or 0) - already.get(product, 0))
        if remaining:
            candidates.append(
                (
                    float(_get(_prices(obs), product, 0.0) or 0.0) * remaining,
                    product,
                    remaining,
                )
            )
    candidates.sort(reverse=True)
    for _, product, quantity in candidates:
        if len(result["market"]) >= 10:
            break
        result["market"].append(["SELL", product, quantity])
    return result


def terminal_value_priority(
    action: Mapping[str, Any], obs: Any, params: Mapping[str, Any]
) -> dict[str, list[Any]]:
    """Apply value-slot ordering only during the terminal clearance window."""

    if _step(obs) < int(params.get("start_step", 696)):
        return canonical_action(action)
    return value_slot_priority(action, obs, params)


def premium_slot_priority(
    action: Mapping[str, Any], obs: Any, params: Mapping[str, Any]
) -> dict[str, list[Any]]:
    """Move existing premium SELLs ahead of commodity SELLs, preserving orders."""

    result = canonical_action(action)
    indices = [
        index
        for index, order in enumerate(result["market"])
        if len(order) >= 3 and str(order[0]) == "SELL" and int(order[2] or 0) > 0
    ]
    if len(indices) < int(params.get("min_sell_orders", 2)):
        return result
    ranked = [list(result["market"][index]) for index in indices]
    ranked.sort(
        key=lambda order: (
            str(order[1]) in PREMIUM_PRODUCTS,
            _price_ratio(str(order[1]), obs),
            int(order[2] or 0),
        ),
        reverse=True,
    )
    for index, order in zip(indices, ranked):
        result["market"][index] = order
    return result


def general_batch_cap(
    action: Mapping[str, Any], obs: Any, params: Mapping[str, Any]
) -> dict[str, list[Any]]:
    """Cap every existing SELL order outside the terminal release window."""

    result = canonical_action(action)
    if _step(obs) >= int(params.get("release_step", 696)):
        return result
    cap = max(1, int(params.get("max_batch", 20)))
    for order in result["market"]:
        if len(order) >= 3 and str(order[0]) == "SELL":
            order[2] = min(int(order[2] or 0), cap)
    return result


def price_sensitive_batch_cap(
    action: Mapping[str, Any], obs: Any, params: Mapping[str, Any]
) -> dict[str, list[Any]]:
    """Cap only SELLs whose live price ratio is below an explicit threshold."""

    result = canonical_action(action)
    if _step(obs) >= int(params.get("release_step", 696)):
        return result
    cap = max(1, int(params.get("max_batch", 10)))
    maximum_ratio = float(params.get("maximum_price_ratio", 0.75))
    for order in result["market"]:
        if (
            len(order) >= 3
            and str(order[0]) == "SELL"
            and _price_ratio(str(order[1]), obs) < maximum_ratio
        ):
            order[2] = min(int(order[2] or 0), cap)
    return result


def lead_aware_animal_cap(
    action: Mapping[str, Any], obs: Any, params: Mapping[str, Any]
) -> dict[str, list[Any]]:
    """Cap animal-product SELLs only while the public money lead is large."""

    result = canonical_action(action)
    if _step(obs) >= int(params.get("release_step", 696)):
        return result
    player = int(_get(obs, "player", 0) or 0)
    farms = _get(obs, "farms", []) or []
    if len(farms) != 2:
        return result
    own = float(_get(farms[player], "money", 0.0) or 0.0)
    other = float(_get(farms[1 - player], "money", 0.0) or 0.0)
    if own - other < float(params.get("minimum_money_lead", 5000.0)):
        return result
    cap = max(1, int(params.get("max_batch", 10)))
    for order in result["market"]:
        if (
            len(order) >= 3
            and str(order[0]) == "SELL"
            and str(order[1]) in ANIMAL_PRODUCTS
        ):
            order[2] = min(int(order[2] or 0), cap)
    return result


def duplicate_sell_merge(
    action: Mapping[str, Any], obs: Any, params: Mapping[str, Any]
) -> dict[str, list[Any]]:
    """Merge duplicate same-product SELLs while preserving total quantities."""

    del obs, params
    result = canonical_action(action)
    first_index: dict[str, int] = {}
    remove: set[int] = set()
    for index, order in enumerate(result["market"]):
        if len(order) < 3 or str(order[0]) != "SELL":
            continue
        product = str(order[1])
        if product not in first_index:
            first_index[product] = index
            continue
        target = result["market"][first_index[product]]
        target[2] = int(target[2] or 0) + int(order[2] or 0)
        remove.add(index)
    result["market"] = [
        order for index, order in enumerate(result["market"]) if index not in remove
    ][:10]
    return result


MutationFn = Callable[[Mapping[str, Any], Any, Mapping[str, Any]], dict[str, list[Any]]]


@dataclass(frozen=True)
class MutationSpec:
    name: str
    change_scope: str
    hypothesis: str
    risk: str
    default_params: dict[str, Any]
    trigger: str
    function: MutationFn
    aliases: tuple[str, ...] = ()
    parameter_templates: tuple[dict[str, Any], ...] = ()

    def public_record(self) -> dict[str, Any]:
        record = asdict(self)
        record.pop("function", None)
        return record


CATALOG: dict[str, MutationSpec] = {
    "value_slot_priority": MutationSpec(
        name="value_slot_priority",
        change_scope="仅重排父策略已有 SELL 槽位；订单集合和数量不变",
        hypothesis="高价值商品更早进入同回合市场，降低被对手先行订单压价的损失。",
        risk="若低价高数量订单本应先卖，价值排序可能牺牲其成交价。",
        default_params={"min_sell_orders": 2},
        trigger="席位劣势或多商品同回合出售竞争",
        function=value_slot_priority,
        aliases=("price_slot", "slot"),
        parameter_templates=({"min_sell_orders": 3},),
    ),
    "premium_floor_guard": MutationSpec(
        name="premium_floor_guard",
        change_scope="仅撤回父策略已有的低价 premium SELL；不改生产动作",
        hypothesis="避开异常低价出售，等待后续价格恢复。",
        risk="价格不恢复时会形成终局库存。",
        default_params={"minimum_price_ratio": 0.55, "release_step": 696},
        trigger="败局含大量低价 premium 出售且终局库存安全",
        function=premium_floor_guard,
        aliases=("floor", "delay"),
        parameter_templates=(
            {"minimum_price_ratio": 0.45, "release_step": 696},
            {"minimum_price_ratio": 0.65, "release_step": 696},
        ),
    ),
    "animal_batch_cap": MutationSpec(
        name="animal_batch_cap",
        change_scope="仅限制父策略已有的动物品 SELL 单批数量",
        hypothesis="减少 EGG/MILK/WOOL 集中抛售造成的价格冲击。",
        risk="积压库存并增加终局清仓压力。",
        default_params={"max_batch": 12, "release_step": 696},
        trigger="惨败局中动物品大批量出售集中",
        function=animal_batch_cap,
        aliases=("batch", "conservative"),
        parameter_templates=(
            {"max_batch": 8, "release_step": 696},
            {"max_batch": 16, "release_step": 696},
        ),
    ),
    "topday_animal_throttle": MutationSpec(
        name="topday_animal_throttle",
        change_scope="仅在显式日期缩减父策略已有动物品 SELL",
        hypothesis="在反复出现价格冲击的季中节点延迟一部分供给。",
        risk="固定日期规律可能不迁移到下一轮 seed。",
        default_params={"days": [10, 17, 24], "fraction": 0.5},
        trigger="日期分层显示稳定、可重复的季中失败簇",
        function=topday_animal_throttle,
        aliases=("topdays",),
        parameter_templates=(
            {"days": [9, 16, 23], "fraction": 0.5},
            {"days": [10, 17, 24], "fraction": 0.75},
        ),
    ),
    "terminal_clearance_fill": MutationSpec(
        name="terminal_clearance_fill",
        change_scope="只在最后 4 回合用空闲市场槽出售父策略遗漏的自有库存",
        hypothesis="消除终局仍有可售库存导致的直接金币损失。",
        risk="最后回合集中出售可能获得较差价格。",
        default_params={"start_step": 716},
        trigger="代表性败局出现终局未清仓",
        function=terminal_clearance_fill,
        aliases=("clearance", "liquidation"),
        parameter_templates=({"start_step": 714}, {"start_step": 718}),
    ),
    "terminal_value_priority": MutationSpec(
        name="terminal_value_priority",
        change_scope="只在最后一天重排父策略已有 SELL 槽位",
        hypothesis="在清仓拥挤时优先成交总价值最高的订单。",
        risk="可能让数量更大但单价较低的订单排后。",
        default_params={"start_step": 696, "min_sell_orders": 2},
        trigger="终局市场槽拥挤但没有库存遗漏",
        function=terminal_value_priority,
        aliases=("terminal_slot",),
        parameter_templates=(
            {"start_step": 672, "min_sell_orders": 2},
            {"start_step": 708, "min_sell_orders": 2},
        ),
    ),
    "premium_slot_priority": MutationSpec(
        name="premium_slot_priority",
        change_scope="仅重排父策略已有 SELL；premium 商品优先，数量不变",
        hypothesis="premium 订单更早成交可降低同回合竞争导致的价格冲击。",
        risk="可能推迟低价但大数量的基础作物订单。",
        default_params={"min_sell_orders": 2},
        trigger="premium 与普通商品同回合争抢有限 SELL 槽",
        function=premium_slot_priority,
        aliases=("premium_slot",),
        parameter_templates=({"min_sell_orders": 3},),
    ),
    "general_batch_cap": MutationSpec(
        name="general_batch_cap",
        change_scope="仅限制父策略已有 SELL 的单批数量，终局解除",
        hypothesis="减少任何单品大批量抛售造成的即时价格冲击。",
        risk="过度节流会增加仓库压力。",
        default_params={"max_batch": 20, "release_step": 696},
        trigger="败局呈现跨商品的大批量集中出售",
        function=general_batch_cap,
        aliases=("all_batch_cap",),
        parameter_templates=(
            {"max_batch": 12, "release_step": 696},
            {"max_batch": 28, "release_step": 696},
        ),
    ),
    "price_sensitive_batch_cap": MutationSpec(
        name="price_sensitive_batch_cap",
        change_scope="只对低价格比的父策略已有 SELL 限量",
        hypothesis="低价时少卖、高价时保持父策略原量，可改善成交均价。",
        risk="持续低价环境会积压库存。",
        default_params={"max_batch": 10, "maximum_price_ratio": 0.75, "release_step": 696},
        trigger="低价出售与负金币差同时出现",
        function=price_sensitive_batch_cap,
        aliases=("price_cap",),
        parameter_templates=(
            {"max_batch": 8, "maximum_price_ratio": 0.65, "release_step": 696},
            {"max_batch": 16, "maximum_price_ratio": 0.85, "release_step": 696},
        ),
    ),
    "lead_aware_animal_cap": MutationSpec(
        name="lead_aware_animal_cap",
        change_scope="仅在公开金币领先时限制父策略已有动物品 SELL",
        hypothesis="领先时降低供给冲击并保留库存选择权，落后时不牺牲现金流。",
        risk="公开金币领先不等于最终资产领先。",
        default_params={"minimum_money_lead": 5000, "max_batch": 10, "release_step": 696},
        trigger="领先后被逆转且动物品抛售集中",
        function=lead_aware_animal_cap,
        aliases=("lead_cap",),
        parameter_templates=(
            {"minimum_money_lead": 2500, "max_batch": 8, "release_step": 696},
            {"minimum_money_lead": 10000, "max_batch": 12, "release_step": 696},
        ),
    ),
    "duplicate_sell_merge": MutationSpec(
        name="duplicate_sell_merge",
        change_scope="仅合并同回合重复的同商品 SELL，保持总出售量",
        hypothesis="释放市场槽并避免同商品订单自相压价。",
        risk="合并后的单批订单可能仍造成价格冲击。",
        default_params={},
        trigger="动作重跑检测到重复同商品 SELL",
        function=duplicate_sell_merge,
        aliases=("merge_sell",),
    ),
}


def mutation_record(name: str) -> dict[str, Any]:
    try:
        return CATALOG[str(name)].public_record()
    except KeyError as exc:
        raise ValueError(f"unknown mutation {name!r}; choices={sorted(CATALOG)}") from exc


def apply_mutation(
    name: str,
    action: Mapping[str, Any],
    obs: Any,
    params: Mapping[str, Any] | None = None,
) -> dict[str, list[Any]]:
    try:
        spec = CATALOG[str(name)]
    except KeyError as exc:
        raise ValueError(f"unknown mutation {name!r}; choices={sorted(CATALOG)}") from exc
    merged = dict(spec.default_params)
    merged.update(dict(params or {}))
    result = spec.function(action, obs, merged)
    if result["farmer"] != canonical_action(action)["farmer"]:
        raise AssertionError(f"{name} changed farmer production action")
    if result["hands"] != canonical_action(action)["hands"]:
        raise AssertionError(f"{name} changed farm-hand production actions")
    if len(result["market"]) > 10:
        raise AssertionError(f"{name} emitted more than ten market orders")
    return result


def _canonical_params(params: Mapping[str, Any]) -> str:
    import json

    return json.dumps(dict(params), sort_keys=True, separators=(",", ":"))


def mutation_signature(parent_id: str, name: str, params: Mapping[str, Any]) -> str:
    """Uniqueness is parent + mechanism + canonical parameters, never name-only."""

    return f"{parent_id}\0{name}\0{_canonical_params(params)}"


def parameterizations(name: str) -> list[dict[str, Any]]:
    spec = CATALOG[str(name)]
    values = [dict(spec.default_params), *(dict(item) for item in spec.parameter_templates)]
    unique = []
    seen = set()
    for params in values:
        key = _canonical_params(params)
        if key not in seen:
            seen.add(key)
            unique.append(params)
    return unique


def _registered_parent(spec: Mapping[str, Any]) -> str:
    parents = spec.get("parent_models") or []
    if parents:
        return str(parents[0])
    kwargs = spec.get("factory_kwargs") or {}
    if kwargs.get("parent_id"):
        return str(kwargs["parent_id"])
    lineage = spec.get("lineage") or []
    if isinstance(lineage, (list, tuple)) and lineage:
        return str(lineage[0])
    model_id = str(spec.get("id") or "")
    for prefix in ("v1", "v2", "v5", "v8"):
        if model_id.startswith(prefix + "_"):
            return f"baseline_{prefix}"
    return ""


def tried_mutations(registry_specs: Sequence[Mapping[str, Any]]) -> set[str]:
    """Return exact tried signatures, scoped to parent and canonical params."""

    tried: set[str] = set()
    for registered in registry_specs:
        parent = _registered_parent(registered)
        if not parent:
            continue
        name = str(registered.get("mutation") or "")
        kwargs = registered.get("factory_kwargs") or {}
        params = kwargs.get("mutation_params") or registered.get("mutation_params") or {}
        if name in CATALOG:
            tried.add(mutation_signature(parent, name, params or CATALOG[name].default_params))
            continue
        text = " ".join(
            [
                str(registered.get("id", "")),
                str(registered.get("family", "")),
                " ".join(str(item) for item in (registered.get("tags") or [])),
            ]
        ).lower()
        for candidate_name, candidate in CATALOG.items():
            if candidate_name.lower() in text or any(
                alias.lower() in text for alias in candidate.aliases
            ):
                tried.add(
                    mutation_signature(parent, candidate_name, candidate.default_params)
                )
    return tried


def choose_mutation(
    diagnosis: Mapping[str, Any], registry_specs: Sequence[Mapping[str, Any]]
) -> tuple[MutationSpec, dict[str, Any], list[str]]:
    """Choose one falsifiable residual from diagnosed failure evidence."""

    findings = diagnosis.get("replay_findings") or {}
    tried = tried_mutations(registry_specs)
    parent_id = str(diagnosis.get("leader") or "")
    reasons: list[str] = []
    priority: list[str] = []
    if int(findings.get("terminal_unsold_events", 0)) > 0:
        priority.append("terminal_clearance_fill")
        reasons.append("代表性败局检测到终局仍有可售库存。")
    if int(findings.get("low_price_premium_sells", 0)) > 0:
        priority.append("premium_floor_guard")
        reasons.append("代表性败局检测到低于基准价阈值的 premium 出售。")
    if int(findings.get("large_animal_sell_batches", 0)) > 0:
        priority.append("animal_batch_cap")
        reasons.append("代表性败局检测到动物品大批量抛售。")
    if int(findings.get("large_general_sell_batches", 0)) > 0:
        priority.append("general_batch_cap")
        reasons.append("代表性败局检测到跨商品的大批量抛售。")
    if int(findings.get("duplicate_sell_order_events", 0)) > 0:
        priority.append("duplicate_sell_merge")
        reasons.append("代表性败局检测到同回合同商品重复 SELL。")
    if (
        int(findings.get("public_money_lead_reversals", 0)) > 0
        and int(findings.get("large_animal_sell_batches", 0)) > 0
    ):
        priority.append("lead_aware_animal_cap")
        reasons.append("代表性败局同时出现公开金币领先反转与动物品集中出售。")
    seat = diagnosis.get("leader_diagnostics", {}).get("by_seat", {})
    seat0 = float((seat.get("0") or {}).get("score_rate", 0.5))
    seat1 = float((seat.get("1") or {}).get("score_rate", 0.5))
    if abs(seat0 - seat1) >= 0.02:
        priority.append("value_slot_priority")
        reasons.append(f"领先模型先后手得分率相差 {abs(seat0-seat1):.3f}。")
    priority.extend(
        [
            "value_slot_priority",
            "premium_slot_priority",
            "terminal_value_priority",
            "animal_batch_cap",
            "general_batch_cap",
            "price_sensitive_batch_cap",
            "lead_aware_animal_cap",
            "premium_floor_guard",
            "topday_animal_throttle",
            "terminal_clearance_fill",
            "duplicate_sell_merge",
        ]
    )
    ordered = list(dict.fromkeys(priority))
    selected_name = ordered[0]
    selected_params = dict(CATALOG[selected_name].default_params)
    found_untried = False
    for name in ordered:
        for params in parameterizations(name):
            signature = mutation_signature(parent_id, name, params)
            if signature not in tried:
                selected_name = name
                selected_params = params
                found_untried = True
                break
        if found_untried:
            break
    selected = CATALOG[selected_name]
    if found_untried:
        reasons.append(
            f"模型池尚无 parent={parent_id}、mutation={selected_name}、params={_canonical_params(selected_params)} 的候选。"
        )
    else:
        reasons.append("当前父版本的全部目录参数已试过，保留证据优先项但不得自动重复注册。")
    return selected, dict(selected_params), reasons
