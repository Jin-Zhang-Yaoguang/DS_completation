#!/usr/bin/env python3
"""Mechanism checks for the R13 safe-throughput HMoE."""

from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
MAIN = HERE / "main.py"


def load_candidate():
    spec = importlib.util.spec_from_file_location("r13_mechanism_candidate", MAIN)
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
    }


def mechanism_checks(module) -> dict[str, bool]:
    checks: dict[str, bool] = {}
    executor = module.build_executor(mode="fixed_grain_egg")
    genomes = module.compile_genomes(module.DEFAULT_PARAMS)
    checks["healthy_bootstrap_shared_by_all_experts"] = all(
        genome["crop_blocks"][0] == module.COMMON_OPENING
        and genome["animal_waves"][0] == (0, "SHEEP", 4)
        for genome in genomes.values())

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
    terminal_goal = {"lands": 4, "hands": 14, "crops": {"WHEAT": 58},
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
