"""Development-only V12A mechanism ablations.

These factories are deliberately excluded from the submission archive.  They
exist only to identify which guard changes outcomes on the already-exposed
V12 frozen_v3/v4 screen panels.
"""

from __future__ import annotations

from typing import Any, Mapping

from kaggle_Kaggriculture.model.v12a_terminal_branch_guard import main as base


class ProductExclusionAgent(base.BranchGuardAgent):
    def __init__(self, excluded: frozenset[str], **kwargs: Any) -> None:
        self.excluded = excluded
        super().__init__(**kwargs)

    def _should_throttle(
        self, obs: Any, action: Mapping[str, Any], branch: str | None
    ) -> tuple[bool, str, frozenset[str]]:
        throttle, reason, products = super()._should_throttle(obs, action, branch)
        if not throttle:
            return throttle, reason, products
        products = frozenset(products - self.excluded)
        if not products:
            return False, "ablation_excluded_all_products", products
        return True, reason, products


class GuardAblationAgent(base.BranchGuardAgent):
    def __init__(
        self,
        *,
        disable_small_sale_guard: bool = False,
        disable_deposit_guard: bool = False,
        **kwargs: Any,
    ) -> None:
        self.disable_small_sale_guard = bool(disable_small_sale_guard)
        self.disable_deposit_guard = bool(disable_deposit_guard)
        super().__init__(**kwargs)

    def _should_throttle(
        self, obs: Any, action: Mapping[str, Any], branch: str | None
    ) -> tuple[bool, str, frozenset[str]]:
        if base._day(obs) not in {
            int(value) for value in self.config["top_days"]
        }:
            return False, "not_top_day", frozenset()
        if branch not in {
            str(value) for value in self.config["throttled_branches"]
        }:
            return False, "non_v5_v8_branch", frozenset()
        products = base.ANIMAL_PRODUCTS
        if bool(self.config.get("require_unlocked_shop_demand", True)):
            products = frozenset(
                base.ANIMAL_PRODUCTS & base._shop_demand_products(obs)
            )
            if not products:
                return False, "no_unlocked_animal_shop_demand", frozenset()
        if not self.disable_deposit_guard and base._has_drop(action):
            return False, "same_turn_shed_deposit", frozenset()
        total = base._animal_sell_total(action, products)
        if (
            not self.disable_small_sale_guard
            and total < int(self.config["minimum_animal_sell"])
        ):
            return False, "small_animal_sale", frozenset()
        if total <= 0:
            return False, "no_animal_sale", frozenset()
        projected = base._post_sale_shed(
            obs, action, float(self.config["fraction"]), products
        )
        if projected > int(self.config["maximum_post_sale_shed"]):
            return False, "shed_headroom_guard", frozenset()
        return True, "ablation_shop_demand_and_shed_safe", products


def make_agent(variant: str = "current") -> base.BranchGuardAgent:
    variant = str(variant)
    if variant == "current":
        return base.make_agent()
    if variant == "no_terminal":
        return base.make_agent(enable_terminal=False)
    if variant == "no_shed_guard":
        return base.make_agent(config={"maximum_post_sale_shed": 10**9})
    if variant == "no_shop_gate":
        return base.make_agent(config={"require_unlocked_shop_demand": False})
    if variant == "no_wool_throttle":
        return ProductExclusionAgent(frozenset({"WOOL"}))
    if variant == "no_milk_throttle":
        return ProductExclusionAgent(frozenset({"MILK"}))
    if variant == "no_small_sale_guard":
        return GuardAblationAgent(disable_small_sale_guard=True)
    if variant == "no_deposit_guard":
        return GuardAblationAgent(disable_deposit_guard=True)
    if variant == "pure_shop_gate":
        return GuardAblationAgent(
            disable_small_sale_guard=True,
            disable_deposit_guard=True,
        )
    raise ValueError(f"unknown ablation variant: {variant}")
