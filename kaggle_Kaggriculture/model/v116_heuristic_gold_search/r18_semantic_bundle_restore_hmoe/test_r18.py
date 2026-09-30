#!/usr/bin/env python3
"""Deterministic mechanism checks for independent R18; no match/replay work."""

from __future__ import annotations

import ast
import copy
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
MAIN = HERE / "main.py"


def load_candidate():
    spec = importlib.util.spec_from_file_location("r18_mechanism_candidate", MAIN)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def empty_grid(unlocked_all: bool = False) -> list[list[object]]:
    return [[None if unlocked_all or (x < 5 and y < 5) else "LOCKED"
             for x in range(10)] for y in range(10)]


def plant(crop: str = "WHEAT", watered: bool = True) -> dict:
    return {"kind": "PLANT", "crop": crop, "watered_today": watered,
            "consecutive_unwatered": 0, "yield_units": 6, "planted_day": 0}


def goal(day: int, crops: dict[str, int]) -> dict:
    return {"day": day, "lands": 4, "hands": 11, "crops": crops,
            "animals": {}, "feed_reserve": 0, "cash_reserve": 100}


def static_checks(module) -> dict[str, bool]:
    source = MAIN.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    allowed = {"__future__", "collections", "copy", "dataclasses", "hashlib",
               "json", "math", "os", "pathlib", "typing"}
    forbidden = ("TaskTicket", "tranche_cap", "open_successor", "golden_model",
                 "accounting_engine", "evaluator")
    return {
        "r18_schema_and_independent_lineage": (
            module.SCHEMA == "v116-r18-semantic-bundle-restore-hmoe-v1"
            and module.STRATEGY_PARENT is None),
        "stdlib_only_and_no_runtime_parent": imports <= allowed,
        "five_experts_six_modes": tuple(module.EXPERT_NAMES) == (
            "wool", "dairy_berry", "tomato_market", "root", "grain_egg")
            and len(module.MODES) == 6,
        "no_wrapper_or_evaluator_packaging": not any(token in source for token in forbidden),
        "cap11_and_settlement_cutoff": (
            module.LABOR_HAND_CAP == 11
            and module.SETTLEMENT_PURCHASE_CUTOFF_STEP == 696),
        "ordinary_three_restoration_one": (
            module.MAX_PARALLEL_PLANT == 3 and module.GROWTH_LANE_CAP == 1),
        "candidate_ledger_never_claims_exact": (
            "expected_demand" not in source and "sell_confirmed" not in source
            and "buy_confirmed" not in source and "harvest_confirmed" not in source),
    }


def mechanism_checks(module) -> dict[str, bool]:
    checks: dict[str, bool] = {}
    executor = module.build_executor(mode="fixed_grain_egg")

    grid = empty_grid(unlocked_all=True)
    target = goal(0, {crop: 5 for crop in module.CROPS})
    before = (executor.crop_cursor, copy.deepcopy(executor.audit),
              copy.deepcopy(executor.daily_operations))
    jobs_a = executor._jobs(0, 0, [[4, 4], [5, 4], [4, 5]], grid, target,
                            {crop: 20 for crop in module.CROPS}, target)
    jobs_b = executor._jobs(0, 0, [[4, 4], [5, 4], [4, 5]], grid, target,
                            {crop: 20 for crop in module.CROPS}, target)
    after = (executor.crop_cursor, executor.audit, executor.daily_operations)
    checks["pure_planning_does_not_advance_cursor_or_audit"] = jobs_a == jobs_b and before == after
    checks["ordinary_parallel_plant_cap_remains_three"] = (
        sum(job[3][0] == "PLANT" for job in jobs_a) == module.MAX_PARALLEL_PLANT == 3)

    lock = module.build_executor(mode="fixed_root")
    old = (6, 1, 1, ("CARE",))
    changed = (2, 1, 1, ("CARE",))
    lock.sticky[0] = module._job_key(old)
    locked = lock._assign([[0, 1]], [{}], [changed, (2, 8, 8, ("HARVEST",))],
                          10, 4, set(), 0, 10)
    checks["semantic_key_excludes_priority_and_hard_locks"] = (
        module._job_key(old) == module._job_key(changed)
        and locked[0][1:3] == (1, 1)
        and lock.audit["exact_target_continuations"] == 1)

    priority = module.build_executor(mode="fixed_root")
    priority.tours[0] = module.ActorTour(0, 0, 0, 9, module._job_key(old))
    priority.sticky[0] = module._job_key(old)
    picked = priority._assign([[1, 1]], [{}], [old, (2, 8, 8, ("PLANT", "WHEAT"))],
                              2, 4, set(), 0, 10)
    checks["local_tour_cannot_invert_global_priority"] = picked[0][3][0] == "PLANT"

    scoped = module.build_executor(mode="fixed_root")
    scoped.tours[0] = module.ActorTour(0, 0, 0, 9, ("CARE", 1, 1))
    normal = scoped._assign([[1, 1]], [{}], [(2, 8, 8, ("WATER",))],
                            12, 4, set(), 0, 10)
    urgent = scoped._assign([[1, 1]], [{}], [(0, 8, 8, ("WATER",))],
                            12, 4, set(), 0, 11)
    checks["ordinary_water_scoped_but_urgent_water_global"] = (
        not normal and urgent[0][3][0] == "WATER")

    bundled = module._bundle_jobs([
        (2, 3, 3, ("HARVEST",)), (2, 3, 3, ("WATER",)),
        (6, 3, 3, ("CARE",)), (2, 7, 7, ("PLANT", "WHEAT"))])
    bundle_assign = module.build_executor(mode="fixed_root")._assign(
        [[2, 3], [4, 3]], [{}, {}], bundled, 10, 4, set(), 0, 10)
    checks["same_coordinate_has_unique_owner_and_top_op"] = (
        sum(job[1:3] == (3, 3) for job in bundled) == 1
        and next(job for job in bundled if job[1:3] == (3, 3))[3][0] == "WATER"
        and sum(job[1:3] == (3, 3) for job in bundle_assign.values()) == 1)

    follow = module.build_executor(mode="fixed_root")
    follow.bundle_followups[1] = (20, 3, 3)
    follow_jobs = [(2, 3, 3, ("HARVEST",)), (2, 8, 8, ("HARVEST",))]
    claims = follow._ready_bundle_followups(21, follow_jobs)
    follow_assign = follow._assign([[3, 2], [8, 8]], [{}, {}], follow_jobs,
                                   10, 4, set(), 0, 21, None, claims)
    checks["water_feed_successor_keeps_same_owner"] = (
        follow_assign[1][1:3] == (3, 3)
        and follow.audit["bundle_owner_followups"] == 1)

    full = empty_grid(unlocked_all=True)
    for i in range(60):
        full[i // 10][i % 10] = plant()
    late_goal = goal(27, {"WHEAT": 60})
    late_jobs = executor._jobs(27, 0, [[4, 9]], full, late_goal,
                               {crop: 20 for crop in module.CROPS}, late_goal)
    floor = empty_grid(unlocked_all=True)
    for i in range(58):
        floor[i // 10][i % 10] = plant()
    floor_jobs = executor._jobs(27, 0, [[4, 9]], floor, late_goal,
                                {crop: 20 for crop in module.CROPS}, late_goal)
    restore = empty_grid(unlocked_all=True)
    for i in range(57):
        restore[i // 10][i % 10] = plant()
    restore_jobs = executor._jobs(27, 0, [[4, 9], [5, 9], [6, 9]], restore,
                                  late_goal, {crop: 20 for crop in module.CROPS}, late_goal)
    checks["strict_late_harvest_budget"] = (
        sum(job[3][0] == "HARVEST" for job in late_jobs) == 2
        and not any(job[3][0] == "HARVEST" for job in floor_jobs))
    checks["restoration_lane_is_exactly_one_priority1_plant"] = (
        [(job[0], job[3][0]) for job in restore_jobs if job[3][0] == "PLANT"] == [(1, "PLANT")])

    chain = module.build_executor(mode="fixed_root")
    chain.growth_chains = [module.GrowthChain(1, 2, 2, "WHEAT", "await_empty", 30, 30)]
    empty = empty_grid(unlocked_all=True)
    chain._reconcile_growth_chains(31, empty)
    first = chain._ready_chain_job(empty, {"WHEAT": 1})
    owned_plant = chain._assign([[2, 2], [9, 9]], [{}, {}], [first[1]],
                                10, 4, set(), 1, 31, first)
    chain.growth_chains[0].state = "await_plant"
    chain.growth_chains[0].action_step = 31
    planted_grid = empty_grid(unlocked_all=True)
    planted_grid[2][2] = plant("WHEAT", watered=False)
    chain._reconcile_growth_chains(32, planted_grid)
    second = chain._ready_chain_job(planted_grid, {})
    owned_water = chain._assign([[2, 2], [9, 9]], [{}, {}], [second[1]],
                                10, 4, set(), 1, 32, second)
    chain.growth_chains[0].state = "await_water"
    chain.growth_chains[0].action_step = 32
    planted_grid[2][2]["watered_today"] = True
    chain._reconcile_growth_chains(33, planted_grid)
    failed = module.build_executor(mode="fixed_root")
    failed.growth_chains = [module.GrowthChain(0, 2, 2, "WHEAT", "await_empty", 30, 30)]
    occupied = empty_grid(unlocked_all=True)
    occupied[2][2] = plant("WHEAT")
    failed._reconcile_growth_chains(31, occupied)
    checks["confirmed_harvest_plant_water_chain"] = (
        first is not None and owned_plant[1][3][0] == "PLANT"
        and second is not None and owned_water[1][3][0] == "WATER"
        and not chain.growth_chains and chain.audit["growth_chain_completed"] == 1)
    checks["failed_chain_does_not_fake_success"] = (
        not failed.growth_chains and failed.audit["growth_chain_harvest_unconfirmed"] == 1)

    buffer = module.build_executor(mode="fixed_root")
    buffer.growth_chains = [module.GrowthChain(i, i, 0, "WHEAT", "await_empty", 1, 1)
                            for i in range(5)]
    needs = buffer._chain_seed_needs()
    market_goal = goal(28, {})
    farm = {"money": 100000, "hands": [[4, 4] for _ in range(11)], "hires_today": 11,
            "unlocked_quadrants": ["NW", "NE", "SW", "SE"]}
    base_obs = {"step": 695, "day": 28, "hour": 23,
                "town": {"unlocked_shops": []},
                "market": {"prices": {}, "inventory": {"WHEAT": 10000}}}
    before_cutoff = buffer._market(base_obs, farm, empty_grid(), market_goal, {}, {}, [{}],
                                   module.Counter(), module.Counter(), needs)
    after_cutoff = buffer._market({**base_obs, "step": 696, "day": 29, "hour": 0},
                                  farm, empty_grid(), market_goal, {}, {}, [{}],
                                  module.Counter(), module.Counter(), needs)
    seed_quantities = [order[2] for order in before_cutoff if order[:2] == ["BUY_SEED", "WHEAT"]]
    checks["chain_seed_buffer_cap_and_696_cutoff"] = (
        needs["WHEAT"] == 3 and seed_quantities and 0 < seed_quantities[0] <= 3
        and not any(order[0].startswith("BUY") for order in after_cutoff))

    actor = module.build_executor(mode="fixed_grain_egg")
    actor_grid = empty_grid(unlocked_all=True)
    actor_goal = actor.goal(0)
    seed_stock = {crop: 20 for crop in module.CROPS}
    planned = actor._jobs(0, 0, [[4, 4]], actor_grid, actor_goal, seed_stock, actor_goal)
    plant_job = next(job for job in planned if job[3][0] == "PLANT")
    px, py = plant_job[1], plant_job[2]
    obs = {"step": 0, "day": 0, "hour": 0, "player_index": 0,
           "town": {"unlocked_shops": []},
           "farms": [{"farmer": [px, py], "hands": [], "tiles": actor_grid,
                       "money": 100000, "hires_today": 0,
                       "unlocked_quadrants": ["NW", "NE", "SW", "SE"]}, {}],
           "private": {"seeds": seed_stock, "shed": {}, "inventories": [{}]},
           "market": {"prices": {}, "inventory": {}}}
    action = actor.act(obs)
    checks["typed_safe_actual_plant_advances_cursor_and_audits"] = (
        action["farmer"][0] == "PLANT" and actor.crop_cursor == 1
        and len(actor.actual_plant_events) == 1
        and {"crop", "zone", "shed_distance"} <= set(actor.actual_plant_events[0])
        and actor.audit["plant_jobs_planned"] >= 1
        and actor.audit["job_generated_plant"] >= 1
        and actor.audit["job_assigned_plant"] == 1
        and actor.audit["job_emitted_plant"] == 1)

    genomes = module.compile_genomes(module.DEFAULT_PARAMS)
    actions: list[str] = []
    for name in module.EXPERT_NAMES:
        planner = module.build_executor(mode=f"fixed_{name}")
        final_goal = module.daily_goal(genomes[name], 29)
        orders = planner._market(
            {**base_obs, "step": 240, "day": 10},
            {**farm, "hands": [[4, 4] for _ in range(11)], "hires_today": 11},
            empty_grid(unlocked_all=True), final_goal, {}, {"WHEAT": 20},
            [{} for _ in range(12)], module.Counter(), module.Counter())
        actions.append(json.dumps(orders, sort_keys=True))
    checks["five_fixed_actions_are_distinct"] = len(set(actions)) == len(module.EXPERT_NAMES)

    ledger = module.build_executor(mode="fixed_root")
    ledger._record_product_batch(5, 0, {"WHEAT": 10}, [{}], empty_grid(), [[4, 4]],
                                 [["PASS"]], [["SELL", "WHEAT", 4]])
    ledger._reconcile_product_batches(6, {"WHEAT": 6}, [{}])
    fields = ledger.product_ledger["WHEAT"]
    checks["product_ledger_is_directional_not_exact"] = (
        fields["sell_requested_units"] == 4
        and fields["sell_direction_compatible_units"] == 4
        and fields["negative_delta_ambiguous_boundaries"] == 1
        and "sell_confirmed_units" not in fields)
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
