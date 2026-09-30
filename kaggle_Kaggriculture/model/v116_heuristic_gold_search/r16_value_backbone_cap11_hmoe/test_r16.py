#!/usr/bin/env python3
"""Mechanism checks for the R16 value-backbone cap-11 HMoE."""

from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
MAIN = HERE / "main.py"


def load_candidate():
    spec = importlib.util.spec_from_file_location("r16_mechanism_candidate", MAIN)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def empty_grid(unlocked_all: bool = False) -> list[list[object]]:
    return [[None if unlocked_all or (x < 5 and y < 5) else "LOCKED"
             for x in range(10)] for y in range(10)]


def plant(crop: str = "WHEAT", watered: bool = False) -> dict:
    return {"kind": "PLANT", "crop": crop, "watered_today": watered,
            "consecutive_unwatered": 0, "yield_units": 6, "planted_day": 0}


def static_checks(module) -> dict[str, bool]:
    source = MAIN.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    allowed = {"__future__", "collections", "copy", "dataclasses", "hashlib", "json",
               "math", "os", "pathlib", "typing"}
    forbidden_tokens = ("TaskTicket", "tranche_cap", "open_successor", "golden_model")
    return {
        "strategy_parent_null": module.STRATEGY_PARENT is None,
        "stdlib_only": imports <= allowed,
        "five_complete_experts": tuple(module.EXPERT_NAMES) == (
            "wool", "dairy_berry", "tomato_market", "root", "grain_egg"),
        "six_modes": len(module.MODES) == 6 and module.MODES[0] == "router",
        "no_ticket_tranche_or_gold_wrapper": not any(token in source for token in forbidden_tokens),
        "p0034_auction_frozen": module.DEFAULT_PARAMS["auction"] == {
            "harvest_priority": 2, "plant_priority": 2, "place_priority": 3,
            "sticky_bonus": 3, "role_penalty": 0,
            "replacement": "same_turn_seed_reserve_only"},
        "labor_cap_eleven_without_r14_adaptive_formula": (
            module.LABOR_HAND_CAP == 11
            and "_adaptive_labor_target" not in source
            and "LABOR_PRODUCTIVE_FRACTION" not in source),
        "settlement_purchase_cutoff_696": module.SETTLEMENT_PURCHASE_CUTOFF_STEP == 696,
        "act_uses_true_harvest_chain": (
            "self._true_eligible_harvests(grid, units, verbs)" in source),
        "budget_audit_renamed": "market_withheld" not in source
            and "purchase_withheld_budget" in source,
    }


def mechanism_checks(module) -> dict[str, bool]:
    checks: dict[str, bool] = {}
    executor = module.build_executor(mode="fixed_grain_egg")
    genomes = module.compile_genomes(module.DEFAULT_PARAMS)
    checks["healthy_bootstrap_shared_by_all_experts"] = all(
        genome["crop_blocks"][0] == module.COMMON_OPENING
        and genome["animal_waves"][0] == (0, "SHEEP", 4)
        for genome in genomes.values())
    checks["r13_p2_shallow_route_mapping"] = (
        module.route_expert(["PET_CAFE"]) == "dairy_berry"
        and module.route_expert(["PIZZA_SHOP"]) == "wool"
        and module.route_expert(["YARN_STORE"]) == "wool"
        and module.route_expert(["ICE_CREAM_SHOP"]) == "dairy_berry"
        and module.route_expert(["FARMERS_MARKET"]) == "tomato_market"
        and module.route_expert(["BAKERY"]) == "grain_egg")

    grid = empty_grid()
    goal = executor.goal(0)
    jobs = executor._jobs(0, 0, [[4, 4]], grid, goal,
                          {crop: 20 for crop in module.CROPS}, goal)
    plants = [job for job in jobs if job[3][0] == "PLANT"]
    checks["parallel_plant_hard_cap_three"] = 1 < len(plants) <= module.MAX_PARALLEL_PLANT
    late = executor._jobs(0, 19, [[4, 4]], grid, goal,
                          {crop: 20 for crop in module.CROPS}, goal)
    checks["no_plant_after_cutoff"] = not any(job[3][0] == "PLANT" for job in late)

    burdened = empty_grid()
    for index in range(12):
        x, y = index % 5, index // 5
        burdened[y][x] = plant(watered=False)
    constrained = executor._jobs(0, 18, [[4, 4]], burdened, goal,
                                 {crop: 20 for crop in module.CROPS}, goal)
    checks["maintenance_and_distance_consume_bundle_budget"] = (
        sum(job[3][0] == "WATER" for job in constrained) == 12
        and not any(job[3][0] == "PLANT" for job in constrained))

    checks["typed_guard_rejects_invalid"] = (
        not executor._safe_unit_verb(["WATER"], (0, 0), grid, {}, {})
        and not executor._safe_unit_verb(["FEED"], (0, 0), grid, {"WHEAT": 1}, {})
        and not executor._safe_unit_verb(["PLANT", "WHEAT"], (0, 0), grid, {}, {})
        and not executor._safe_unit_verb(["PLACE", "COW"], (0, 0), grid, {"COW": 1}, {}))

    receipt = module.build_executor(mode="fixed_root")
    receipt._record_receipts(5, [["BUY_SEED", "WHEAT", 2], ["SELL", "WHEAT", 1]])
    recorded = len(receipt.pending_receipts) == 1
    receipt._reconcile_receipts(6)
    checks["purchase_receipt_one_boundary"] = recorded and not receipt.pending_receipts \
        and receipt.audit["receipts_reconciled"] == 1

    success = module.build_executor(mode="fixed_root")
    success.pending_harvests.append(module.PendingHarvestBatch(
        10, {"WHEAT": 5}, {"WHEAT": 0}))
    success._reconcile_harvests(11, {}, [{"WHEAT": 5}])
    checks["successful_replacement_is_bounded"] = (
        success.replacement_credits["WHEAT"] == module.MAX_PARALLEL_PLANT
        and success.audit["replacement_success_overflow"] == 2)
    failed = module.build_executor(mode="fixed_root")
    failed.pending_harvests.append(module.PendingHarvestBatch(
        10, {"WHEAT": 1}, {"WHEAT": 0}))
    failed._reconcile_harvests(11, {}, [{}])
    checks["failed_harvest_registers_no_replacement"] = (
        not failed.replacement_credits
        and failed.audit["replacement_failed_not_registered"] == 1)

    terminal_grid = empty_grid(unlocked_all=True)
    for index in range(module.TERMINAL_ASSET_FLOOR):
        terminal_grid[index // 10][index % 10] = plant(watered=True)
    terminal_goal = {"lands": 4, "hands": 11, "crops": {"WHEAT": 58},
                     "animals": {}, "feed_reserve": 0, "cash_reserve": 100,
                     "day": 29}
    terminal_jobs = executor._jobs(29, 19, [[4, 4]], terminal_grid,
                                   terminal_goal, {}, terminal_goal)
    checks["terminal_asset_floor_blocks_unreplaceable_harvest"] = (
        not any(job[3][0] == "HARVEST" for job in terminal_jobs)
        and executor.audit["terminal_asset_harvest_protected"] >= 1)

    delivery = module.build_executor(mode="fixed_root")
    no_drop = delivery._delivery_overrides(100, {"money": 2000}, [[4, 4]],
                                           [{"WHEAT": 20}], {})
    finance_drop = delivery._delivery_overrides(100, {"money": 100}, [[4, 4]],
                                                [{"WHEAT": 20}], {})
    checks["harvest_delivery_is_batched_not_forced"] = not no_drop and finance_drop == {0: ["DROP"]}

    # The schedule reaches eleven.  Because the market accepts ten orders per
    # step, a second observation admits exactly the eleventh and no twelfth.
    schedules = [module.compile_daily_goals(genome) for genome in genomes.values()]
    cap_executor = module.build_executor(mode="fixed_root")
    cap_goal = {"day": 7, "lands": 1, "hands": 99, "crops": {}, "animals": {},
                "feed_reserve": 0, "cash_reserve": 100}
    rich_farm = {"money": 1_000_000, "hands": [], "hires_today": 0,
                 "unlocked_quadrants": ["NW"]}
    base_obs = {"step": 168, "day": 7, "hour": 0,
                "town": {"unlocked_shops": []},
                "market": {"prices": {}, "inventory": {}}}
    cap_orders_first = cap_executor._market(
        base_obs, rich_farm, empty_grid(), cap_goal, {}, {}, [{}],
        module.Counter(), module.Counter())
    ten_hands_farm = {**rich_farm, "hands": [[4, 4] for _ in range(10)],
                      "hires_today": 10}
    cap_orders_second = cap_executor._market(
        {**base_obs, "step": 169, "hour": 1}, ten_hands_farm, empty_grid(),
        cap_goal, {}, {}, [{} for _ in range(11)], module.Counter(),
        module.Counter())
    checks["hands_cap_eleven_is_reached_and_enforced"] = (
        all(max(goal["hands"] for goal in schedule) == module.LABOR_HAND_CAP
            and all(goal["hands"] <= module.LABOR_HAND_CAP for goal in schedule)
            for schedule in schedules)
        and sum(order[0] == "HIRE" for order in cap_orders_first) == 10
        and sum(order[0] == "HIRE" for order in cap_orders_second) == 1)

    final_goals = {name: module.daily_goal(genome, 29)
                   for name, genome in genomes.items()}
    goal_signatures = {
        json.dumps({"crops": goal["crops"], "animals": goal["animals"]},
                   sort_keys=True)
        for goal in final_goals.values()
    }
    checks["value_backbone_preserves_independent_focus_quotas"] = (
        len(goal_signatures) == len(module.EXPERT_NAMES)
        and all(goal["crops"].get("MELON", 0) >= 18
                and goal["animals"].get("SHEEP", 0)
                + goal["animals"].get("COW", 0) >= 6
                for goal in final_goals.values())
        and final_goals["root"]["crops"].get("CARROT", 0) >= 8
        and final_goals["tomato_market"]["crops"].get("TOMATO", 0) >= 6
        and final_goals["grain_egg"]["crops"].get("WHEAT", 0) >= 24
        and final_goals["grain_egg"]["animals"].get("GOOSE", 0) >= 2)

    plan_farm = {**rich_farm, "hands": [[4, 4] for _ in range(11)],
                 "hires_today": 11, "unlocked_quadrants": ["NW", "NE", "SW", "SE"]}
    plan_actions = []
    for name in module.EXPERT_NAMES:
        planner = module.build_executor(mode=f"fixed_{name}")
        goal = final_goals[name]
        orders = planner._market(
            {**base_obs, "step": 240, "day": 10}, plan_farm,
            empty_grid(unlocked_all=True), goal, {}, {"WHEAT": 20},
            [{} for _ in range(12)], module.Counter(), module.Counter())
        plan_actions.append(json.dumps(orders, sort_keys=True))
    checks["five_fixed_market_actions_are_distinct"] = (
        len(set(plan_actions)) == len(module.EXPERT_NAMES))

    # All purchase kinds are closed from step 696, independently of deficits.
    settlement_executor = module.build_executor(mode="fixed_root")
    settlement_goal = {"day": 29, "lands": 4, "hands": 11,
                       "crops": {"WHEAT": 58}, "animals": {"COW": 6},
                       "feed_reserve": 12, "cash_reserve": 100}
    settlement_obs = {"step": 696, "day": 29, "hour": 0,
                      "town": {"unlocked_shops": []},
                      "market": {"prices": {}, "inventory": {}}}
    settlement_orders = settlement_executor._market(
        settlement_obs, rich_farm, empty_grid(), settlement_goal, {}, {}, [{}],
        module.Counter(), module.Counter())
    purchase_ops = {"BUY_PRODUCT", "BUY_SEED", "BUY_ANIMAL", "BUY_LAND", "HIRE"}
    checks["settlement_emits_zero_purchases"] = (
        not any(order and order[0] in purchase_ops for order in settlement_orders)
        and settlement_executor.audit["settlement_purchases_suppressed"] > 0)

    # Engine quotes BUY_PRODUCT after each unit reduces inventory: I-1, I-2...
    inventory = 9900
    quotes = [module.market_price("WHEAT", inventory - offset - 1)
              for offset in range(4)]
    quantity, cost = cap_executor._wheat_buy_plan(
        4, inventory, sum(quotes[:2]), 100)
    wheat_executor = module.build_executor(mode="fixed_root")
    wheat_goal = {"day": 0, "lands": 1, "hands": 0, "crops": {}, "animals": {},
                  "feed_reserve": 3, "cash_reserve": 100}
    wheat_obs = {"step": 0, "day": 0, "hour": 0,
                 "town": {"unlocked_shops": []},
                 "market": {"prices": {"WHEAT": quotes[0]},
                            "inventory": {"WHEAT": inventory}}}
    wheat_orders = wheat_executor._market(
        wheat_obs, {**rich_farm, "money": 10_000}, empty_grid(), wheat_goal,
        {}, {}, [{}], module.Counter(), module.Counter())
    wheat_buys = [order for order in wheat_orders
                  if order[:2] == ["BUY_PRODUCT", "WHEAT"]]
    checks["wheat_buy_uses_per_unit_decrement_quotes"] = (
        quantity == 2 and cost == sum(quotes[:2])
        and cost + quotes[2] > sum(quotes[:2])
        and wheat_buys == [["BUY_PRODUCT", "WHEAT", 3]]
        and wheat_executor.audit["wheat_buy_quoted_cost"] == sum(quotes[:3]))

    # A genuinely selected non-ongoing harvest is removed from crop_have before
    # seed-gap calculation, preserving the same-turn replacement chain.
    chain_executor = module.build_executor(mode="fixed_root")
    chain_executor.first_shops = ("BAKERY",)
    chain_grid = empty_grid()
    chain_grid[4][4] = plant("WHEAT", watered=True)
    chain_units = [[4, 4]]
    chain_verbs = [["HARVEST"]]
    true_harvests = chain_executor._true_eligible_harvests(
        chain_grid, chain_units, chain_verbs)
    chain_goal = {"day": 0, "lands": 1, "hands": 0,
                  "crops": {"WHEAT": 1}, "animals": {},
                  "feed_reserve": 0, "cash_reserve": 100}
    chain_orders = chain_executor._market(
        {**base_obs, "step": 0, "day": 0}, rich_farm, chain_grid, chain_goal,
        {}, {}, [{}], module.Counter(), true_harvests)
    checks["true_harvests_nonempty_reaches_seed_gap"] = (
        true_harvests == {"WHEAT": 1}
        and any(order[:2] == ["BUY_SEED", "WHEAT"] for order in chain_orders))
    return checks


def main() -> None:
    module = load_candidate()
    result = {"schema": module.SCHEMA, "static": static_checks(module),
              "mechanisms": mechanism_checks(module)}
    result["passed"] = all(result["static"].values()) and all(result["mechanisms"].values())
    (HERE / "mechanism_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
