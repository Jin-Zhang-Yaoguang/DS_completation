#!/usr/bin/env python3
"""R19 mechanism checks only; this file never runs matches or Replay."""

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
    spec = importlib.util.spec_from_file_location("r19_candidate", MAIN)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def empty_grid(all_open: bool = False) -> list[list[object]]:
    return [[None if all_open or (x < 5 and y < 5) else "LOCKED"
             for x in range(10)] for y in range(10)]


def plant(crop: str = "WHEAT", watered: bool = True) -> dict:
    return {"kind": "PLANT", "crop": crop, "watered_today": watered,
            "consecutive_unwatered": 0, "yield_units": 6, "planted_day": 0}


def target(day: int, crops: dict[str, int], animals: dict[str, int] | None = None) -> dict:
    return {"day": day, "lands": 4, "hands": 11, "crops": crops,
            "animals": animals or {}, "feed_reserve": 0, "cash_reserve": 100}


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
    return {
        "r19_independent_schema": (
            module.SCHEMA == "v116-r19-growth-debt-throughput-hmoe-v1"
            and module.STRATEGY_PARENT is None),
        "stdlib_runtime_only": imports <= allowed,
        "five_experts_and_router": tuple(module.EXPERT_NAMES) == (
            "wool", "dairy_berry", "tomato_market", "root", "grain_egg")
            and len(module.MODES) == 6,
        "cap11_cutoff696": module.LABOR_HAND_CAP == 11
            and module.SETTLEMENT_PURCHASE_CUTOFF_STEP == 696,
        "no_r18_destructive_mechanisms": not any(token in source for token in (
            "GrowthChain", "growth_chain", "bundle_followup", "_bundle_jobs", "ordinary_water")),
        "candidate_ledger_has_no_exact_claims": (
            "expected_demand" not in source and "sell_confirmed" not in source
            and "buy_confirmed" not in source and "harvest_confirmed" not in source),
    }


def mechanism_checks(module) -> dict[str, bool]:
    checks: dict[str, bool] = {}
    executor = module.build_executor(mode="fixed_grain_egg")
    grid = empty_grid(all_open=True)
    plan_goal = target(8, {crop: 5 for crop in module.CROPS})
    seeds = {crop: 20 for crop in module.CROPS}

    before = (executor.crop_cursor, copy.deepcopy(executor.audit),
              copy.deepcopy(executor.daily_operations))
    jobs1 = executor._jobs(8, 0, [[4, 4], [5, 4], [4, 5]], grid,
                           plan_goal, seeds, plan_goal)
    jobs2 = executor._jobs(8, 0, [[4, 4], [5, 4], [4, 5]], grid,
                           plan_goal, seeds, plan_goal)
    checks["jobs_is_pure_and_deterministic"] = (
        jobs1 == jobs2
        and before == (executor.crop_cursor, executor.audit, executor.daily_operations))
    plants = [job for job in jobs1 if job[3][0] == "PLANT"]
    checks["growth_debt_one_p1_but_total_three"] = (
        len(plants) == module.MAX_PARALLEL_PLANT == 3
        and sum(job[0] == 1 for job in plants) == 1
        and sum(job[0] == 2 for job in plants) == 2)
    pre_debt = executor._jobs(7, 0, [[4, 4], [5, 4], [4, 5]], grid,
                              plan_goal, seeds, plan_goal)
    checks["growth_debt_starts_day8"] = not any(
        job[3][0] == "PLANT" and job[0] == 1 for job in pre_debt)

    semantic_a = (6, 1, 1, ("CARE",))
    semantic_b = (2, 1, 1, ("CARE",))
    checks["semantic_key_excludes_priority"] = (
        module._job_key(semantic_a) == module._job_key(semantic_b))

    # Debt guard requires seed, empty tile and room for PLANT plus WATER.
    debt_grid = empty_grid()
    debt_grid[0][0] = plant("WHEAT")
    debt_goal = target(8, {"WHEAT": 2})
    no_seed = executor._jobs(8, 0, [[4, 4]], debt_grid, debt_goal, {}, debt_goal)
    too_late = executor._jobs(8, 22, [[4, 4]], debt_grid, debt_goal,
                              {"WHEAT": 1}, debt_goal)
    guarded = executor._jobs(8, 0, [[4, 4]], debt_grid, debt_goal,
                             {"WHEAT": 1}, debt_goal)
    no_debt_goal = target(8, {"WHEAT": 1})
    no_debt = executor._jobs(8, 0, [[4, 4]], debt_grid, no_debt_goal, {}, no_debt_goal)
    checks["finite_harvest_growth_debt_guard"] = (
        not any(job[3][0] == "HARVEST" for job in no_seed)
        and not any(job[3][0] == "HARVEST" for job in too_late)
        and any(job[3][0] == "HARVEST" for job in guarded)
        and any(job[3][0] == "HARVEST" for job in no_debt))

    # An infeasible FEED never erases the feasible HARVEST at its coordinate.
    one_tile = module.build_executor(mode="fixed_root")
    same_coord = [(1, 2, 2, ("FEED",)), (2, 2, 2, ("HARVEST",)),
                  (6, 2, 2, ("CARE",))]
    assigned = one_tile._assign([[2, 1], [2, 3]], [{}, {}], same_coord,
                                10, 4, set(), 0, 10)
    checks["claimed_coord_after_feasible_selection_only"] = (
        len(assigned) == 1
        and next(iter(assigned.values()))[3][0] == "HARVEST"
        and one_tile.audit["claimed_coordinates"] == 1)

    # Both ordinary WATER and FEED can break a live cross-zone tour.
    maintenance = module.build_executor(mode="fixed_root")
    for index in (0, 1):
        maintenance.tours[index] = module.ActorTour(0, 0, 0, 9, ("CARE", 1, 1))
    maintenance_jobs = [(2, 8, 8, ("WATER",)), (1, 7, 8, ("FEED",))]
    maintenance_result = maintenance._assign(
        [[1, 1], [1, 2]], [{}, {"WHEAT": 1}], maintenance_jobs,
        10, 4, set(), 0, 10)
    checks["all_water_feed_are_global_maintenance"] = (
        {job[3][0] for job in maintenance_result.values()} == {"WATER", "FEED"}
        and maintenance.audit["tour_maintenance_preemptions"] == 2)

    # Primary work wins over local secondary work; within primary raw priority
    # is neutral, so nearby BUILD is not starved by a far HARVEST.
    tiered = module.build_executor(mode="fixed_root")
    tiered.tours[0] = module.ActorTour(0, 0, 0, 9, module._job_key(semantic_a))
    tiered_result = tiered._assign(
        [[1, 1]], [{}], [semantic_a, (4, 1, 2, ("BUILD_PASTURE",)),
                         (2, 8, 8, ("HARVEST",))],
        10, 4, set(), 0, 10)
    checks["economic_tier_prevents_secondary_and_raw_priority_starvation"] = (
        tiered_result[0][3][0] == "BUILD_PASTURE")

    # Only a typed-safe emitted PLANT advances the cursor and emits its audit.
    actor = module.build_executor(mode="fixed_grain_egg")
    actor_grid = empty_grid(all_open=True)
    actor_goal = actor.goal(0)
    actor_seeds = {crop: 20 for crop in module.CROPS}
    planned = actor._jobs(0, 0, [[4, 4]], actor_grid, actor_goal,
                          actor_seeds, actor_goal)
    plant_job = next(job for job in planned if job[3][0] == "PLANT")
    px, py = plant_job[1], plant_job[2]
    obs = {"step": 0, "day": 0, "hour": 0, "player_index": 0,
           "town": {"unlocked_shops": []},
           "farms": [{"farmer": [px, py], "hands": [], "tiles": actor_grid,
                       "money": 100000, "hires_today": 0,
                       "unlocked_quadrants": ["NW", "NE", "SW", "SE"]}, {}],
           "private": {"seeds": actor_seeds, "shed": {}, "inventories": [{}]},
           "market": {"prices": {}, "inventory": {}}}
    action = actor.act(obs)
    checks["actual_typed_plant_only_cursor_and_audit"] = (
        action["farmer"][0] == "PLANT" and actor.crop_cursor == 1
        and len(actor.actual_plant_events) == 1
        and {"crop", "zone", "shed_distance"} <= set(actor.actual_plant_events[0])
        and actor.audit["job_emitted_plant"] == 1)

    # Five fixed experts must still emit distinct executable purchase plans.
    genomes = module.compile_genomes(module.DEFAULT_PARAMS)
    farm = {"money": 1_000_000, "hands": [[4, 4] for _ in range(11)],
            "hires_today": 11, "unlocked_quadrants": ["NW", "NE", "SW", "SE"]}
    market_obs = {"step": 240, "day": 10, "hour": 0,
                  "town": {"unlocked_shops": []},
                  "market": {"prices": {}, "inventory": {}}}
    fixed_actions = []
    for name in module.EXPERT_NAMES:
        planner = module.build_executor(mode=f"fixed_{name}")
        expert_goal = module.daily_goal(genomes[name], 29)
        orders = planner._market(
            market_obs, farm, empty_grid(all_open=True), expert_goal, {}, {"WHEAT": 20},
            [{} for _ in range(12)], module.Counter(), module.Counter())
        fixed_actions.append(json.dumps(orders, sort_keys=True))
    checks["five_fixed_actions_are_distinct"] = (
        len(set(fixed_actions)) == len(module.EXPERT_NAMES))

    ledger = module.build_executor(mode="fixed_root")
    ledger._record_product_batch(5, 0, {"WHEAT": 10}, [{}], empty_grid(), [[4, 4]],
                                 [["PASS"]], [["SELL", "WHEAT", 4]])
    ledger._reconcile_product_batches(6, {"WHEAT": 6}, [{}])
    fields = ledger.product_ledger["WHEAT"]
    checks["directional_ledger_never_claims_exact_sale"] = (
        fields["sell_requested_units"] == 4
        and fields["sell_direction_compatible_units"] == 4
        and fields["negative_delta_ambiguous_boundaries"] == 1
        and "sell_confirmed_units" not in fields)

    settlement = module.build_executor(mode="fixed_root")
    settlement_orders = settlement._market(
        {**market_obs, "step": 696, "day": 29},
        {"money": 1_000_000, "hands": [], "hires_today": 0,
         "unlocked_quadrants": ["NW"]}, empty_grid(),
        target(29, {"WHEAT": 58}, {"COW": 6}), {}, {}, [{}],
        module.Counter(), module.Counter())
    checks["step696_purchase_cutoff"] = not any(
        order[0] in {"BUY_PRODUCT", "BUY_SEED", "BUY_ANIMAL", "BUY_LAND", "HIRE"}
        for order in settlement_orders)
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
