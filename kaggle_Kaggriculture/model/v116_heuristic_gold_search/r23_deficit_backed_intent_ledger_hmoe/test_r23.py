#!/usr/bin/env python3
"""Behavioral mechanism checks for R23; no match or Replay execution."""

from __future__ import annotations

import ast
from collections import Counter
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
MAIN = HERE / "main.py"
R22_MAIN = HERE.parent / "r22_observation_valid_frontier_hmoe" / "main.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def empty_grid(all_open: bool = True) -> list[list[object]]:
    return [[None if all_open or (x < 5 and y < 5) else "LOCKED"
             for x in range(10)] for y in range(10)]


def plant(name: str = "WHEAT", watered: bool = True,
          yield_units: int = 6) -> dict:
    return {"kind": "PLANT", "crop": name, "watered_today": watered,
            "consecutive_unwatered": 0, "yield_units": yield_units,
            "planted_day": 0}


def pasture() -> dict:
    return {"kind": "PASTURE", "animal": None}


def cow() -> dict:
    return {"kind": "PASTURE", "animal": {"kind": "COW"},
            "fed_today": True, "cared_today": False,
            "yield_units": 0, "fertilizer_available": False}


def head_key(module, work):
    return module.ShopRouterExecutor._intent_key(
        module.ShopRouterExecutor._head_job(work))


def unissued_counts(module, executor) -> Counter:
    return Counter(
        head_key(module, work)
        for work in executor.tile_work.values()
        if work.phase in {"ordinary_plant", "generic"}
        and work.pending_intent_key is None and work.ready_ops)


def static_checks(module, r22) -> dict[str, bool]:
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
    thresholds = ("PLANT_CUTOFF_HOUR", "MAX_PARALLEL_PLANT", "DELIVERY_BATCH",
                  "FINANCE_DROP_FLOOR", "TERMINAL_ASSET_FLOOR", "LABOR_HAND_CAP",
                  "SETTLEMENT_PURCHASE_CUTOFF_STEP", "TOUR_MAX_STEPS",
                  "GROWTH_DEBT_START_DAY")
    module_genomes = module.compile_genomes(module.DEFAULT_PARAMS)
    r22_genomes = r22.compile_genomes(r22.DEFAULT_PARAMS)
    same_targets = all(
        module.compile_daily_goals(module_genomes[name])
        == r22.compile_daily_goals(r22_genomes[name])
        for name in module.EXPERT_NAMES)
    return {
        "independent_stdlib_candidate": (
            module.STRATEGY_PARENT is None and imports <= allowed
            and "r22_observation_valid_frontier_hmoe" not in source),
        "schema_r23": module.SCHEMA == "v116-r23-deficit-backed-intent-ledger-hmoe-v1",
        "params_hash_unchanged": module.DEFAULT_PARAMS_HASH == r22.DEFAULT_PARAMS_HASH,
        "router_experts_targets_unchanged": (
            module.EXPERT_NAMES == r22.EXPERT_NAMES and module.MODES == r22.MODES
            and same_targets
            and all(module.route_expert([shop]) == r22.route_expert([shop])
                    for shop in sorted(module.SHOP_PRODUCTS))),
        "market_thresholds_unchanged": (
            all(getattr(module, key) == getattr(r22, key) for key in thresholds)
            and module.MARKET_PARAMS == r22.MARKET_PARAMS
            and module.DEFAULT_PARAMS == r22.DEFAULT_PARAMS),
    }


def parity_checks(module, r22) -> dict[str, bool]:
    grid = empty_grid()
    seeds = {crop: 20 for crop in module.CROPS}
    left = module.build_executor(mode="fixed_grain_egg")
    right = r22.build_executor(mode="fixed_grain_egg")
    left_goal = left.goal(8)
    right_goal = right.goal(8)
    units = [[4, 4], [5, 4], [4, 5]]
    same_jobs = (
        left._jobs(8, 0, units, grid, left_goal, seeds, left_goal)
        == right._jobs(8, 0, units, grid, right_goal, seeds, right_goal))

    confirmation = []
    for candidate in (module, r22):
        executor = candidate.build_executor(mode="fixed_root")
        candidate_grid = empty_grid(False)
        candidate_grid[2][2] = plant()
        executor._sync_tile_work(10, candidate_grid,
                                 [(2, 2, 2, ("HARVEST",))])
        executor._mark_tile_work_emitted(10, (2, 2), ["HARVEST"])
        candidate_grid[2][2] = None
        executor._sync_tile_work(11, candidate_grid, [])
        work = executor.tile_work[(2, 2)]
        confirmation.append((work.phase, work.ready_ops,
                             work.crop_if_needed, work.ready_since))

    nearest = []
    for candidate in (module, r22):
        executor = candidate.build_executor(mode="fixed_root")
        candidate_grid = empty_grid(False)
        candidate_grid[1][1] = cow()
        executor.tile_work[(1, 1)] = candidate.TileWork(
            (1, 1), 0, ((6, ("CARE",)),), "animal", 1)
        result = executor._assign(
            [[9, 9], [1, 2]], [{}, {}], [(6, 1, 1, ("CARE",))],
            10, 1, set(), 0, 2, candidate_grid, {})
        nearest.append((result, executor.tile_work[(1, 1)].owner))
    return {
        "r22_jobs_parity": same_jobs,
        "r22_confirmation_chain_parity": confirmation[0] == confirmation[1],
        "soft_nearest_owner_parity": nearest[0] == nearest[1],
    }


def mechanism_checks(module) -> dict[str, bool]:
    checks: dict[str, bool] = {}

    quota = module.build_executor(mode="fixed_root")
    quota_grid = empty_grid()
    old_coords = [(1, 1), (2, 1), (3, 1)]
    for age, coord in enumerate(old_coords, 1):
        quota.tile_work[coord] = module.TileWork(
            coord, None, ((2, ("PLANT", "WHEAT")),),
            "ordinary_plant", age, "WHEAT")
    new_jobs = [(2, 6 + index, 1, ("PLANT", "WHEAT")) for index in range(3)]
    quota._sync_tile_work(10, quota_grid, new_jobs)
    retained_three = set(quota.tile_work) == set(old_coords)
    quota._sync_tile_work(11, quota_grid, new_jobs[:1])
    retained_one = set(quota.tile_work) == {old_coords[0]}
    quota._sync_tile_work(12, quota_grid, [])
    checks["three_plant_quota_retarget_retains_exactly_three_not_six"] = retained_three
    checks["quota_three_to_one_to_zero"] = retained_three and retained_one \
        and not quota.tile_work

    builds = module.build_executor(mode="fixed_root")
    build_grid = empty_grid()
    build_old = [(1, 2), (2, 2), (3, 2), (4, 2), (5, 2), (6, 2)]
    for age, coord in enumerate(build_old):
        builds.tile_work[coord] = module.TileWork(
            coord, age, ((4, ("BUILD_PASTURE",)),), "generic", age)
    build_jobs = [(4, x, 7, ("BUILD_PASTURE",)) for x in range(4)]
    builds._sync_tile_work(20, build_grid, build_jobs)
    live_builds = [work for work in builds.tile_work.values()
                   if head_key(module, work) == ("BUILD_PASTURE",)]
    max_four = len(live_builds) == 4
    builds._sync_tile_work(21, build_grid, [])
    checks["build_deficit_four_max_four_and_zero_expires"] = (
        max_four and not builds.tile_work)

    isolated = module.build_executor(mode="fixed_root")
    isolated_grid = empty_grid()
    intent_specs = [
        ((1, 1), ("PLANT", "WHEAT"), "ordinary_plant", "WHEAT"),
        ((2, 1), ("PLANT", "WHEAT"), "ordinary_plant", "WHEAT"),
        ((3, 1), ("PLANT", "CARROT"), "ordinary_plant", "CARROT"),
        ((4, 1), ("PLANT", "CARROT"), "ordinary_plant", "CARROT"),
        ((1, 3), ("PLACE", "COW"), "generic", None),
        ((2, 3), ("PLACE", "COW"), "generic", None),
        ((3, 3), ("PLACE", "SHEEP"), "generic", None),
    ]
    for age, (coord, verb, phase, crop_name) in enumerate(intent_specs):
        if verb[0] == "PLACE":
            isolated_grid[coord[1]][coord[0]] = pasture()
        isolated.tile_work[coord] = module.TileWork(
            coord, None, ((2, verb),), phase, age, crop_name)
    isolated_jobs = [
        (2, 8, 1, ("PLANT", "WHEAT")),
        (2, 8, 2, ("PLANT", "CARROT")),
        (2, 8, 3, ("PLANT", "CARROT")),
        (3, 1, 3, ("PLACE", "COW")),
    ]
    isolated._sync_tile_work(30, isolated_grid, isolated_jobs)
    counts = unissued_counts(module, isolated)
    checks["crop_and_animal_keys_are_isolated"] = (
        counts[("PLANT", "WHEAT")] == 1
        and counts[("PLANT", "CARROT")] == 2
        and counts[("PLACE", "COW")] == 1
        and counts[("PLACE", "SHEEP")] == 0)

    oldest = module.build_executor(mode="fixed_root")
    oldest_grid = empty_grid()
    invalid_coord = (1, 5)
    oldest_grid[5][1] = {"kind": "COOP", "animal": None}
    valid_coords = [(2, 5), (3, 5)]
    oldest.tile_work[invalid_coord] = module.TileWork(
        invalid_coord, 0, ((2, ("PLANT", "WHEAT")),),
        "ordinary_plant", 0, "WHEAT")
    for age, coord in enumerate(valid_coords, 1):
        oldest.tile_work[coord] = module.TileWork(
            coord, None, ((2, ("PLANT", "WHEAT")),),
            "ordinary_plant", age, "WHEAT")
    fill_jobs = [(2, x, 8, ("PLANT", "WHEAT")) for x in (6, 7, 8)]
    oldest._sync_tile_work(40, oldest_grid, fill_jobs)
    wheat_coords = {
        coord for coord, work in oldest.tile_work.items()
        if head_key(module, work) == ("PLANT", "WHEAT")
    }
    checks["oldest_structural_invalid_then_planner_fills_slot"] = (
        invalid_coord not in oldest.tile_work
        and set(valid_coords) <= wheat_coords and len(wheat_coords) == 3
        and len(wheat_coords & {(6, 8), (7, 8), (8, 8)}) == 1)

    oscillation = module.build_executor(mode="fixed_root")
    oscillation_grid = empty_grid()
    side_a = [(2, x, 1, ("PLANT", "MELON")) for x in (1, 2, 3)]
    side_b = [(2, x, 8, ("PLANT", "MELON")) for x in (6, 7, 8)]
    oscillation._sync_tile_work(50, oscillation_grid, side_a)
    stable_coords = set(oscillation.tile_work)
    stable_ages = {coord: work.ready_since
                   for coord, work in oscillation.tile_work.items()}
    stable = True
    quota_safe = True
    for offset in range(1, 11):
        current = side_b if offset % 2 else side_a
        oscillation._sync_tile_work(50 + offset, oscillation_grid, current)
        stable &= (set(oscillation.tile_work) == stable_coords
                   and {coord: work.ready_since
                        for coord, work in oscillation.tile_work.items()} == stable_ages)
        quota_safe &= unissued_counts(module, oscillation)[("PLANT", "MELON")] <= 3
    checks["planner_coordinate_oscillation_ten_times_lease_stable"] = stable
    checks["ordinary_live_never_exceeds_quota"] = quota_safe

    pending = module.build_executor(mode="fixed_root")
    pending_grid = empty_grid()
    pending_coord = (1, 1)
    pending.tile_work[pending_coord] = module.TileWork(
        pending_coord, 0, (), "await_ordinary_plant", 70, "WHEAT",
        ("PLANT", "WHEAT"))
    pending_jobs = [(2, x, 3, ("PLANT", "WHEAT")) for x in (5, 6, 7)]
    pending._sync_tile_work(71, pending_grid, pending_jobs)
    chain = pending.tile_work[pending_coord]
    unissued_after_three = unissued_counts(module, pending)[("PLANT", "WHEAT")]
    pending._sync_tile_work(72, pending_grid, [])
    chain_after_zero = pending.tile_work[pending_coord]
    checks["await_chain_survives_and_is_excluded_from_unissued_quota"] = (
        chain.pending_intent_key == ("PLANT", "WHEAT")
        and chain.ready_since == 70 and unissued_after_three == 2
        and chain_after_zero.pending_intent_key == ("PLANT", "WHEAT")
        and chain_after_zero.ready_since == 70
        and unissued_counts(module, pending)[("PLANT", "WHEAT")] == 0)

    pending_build = module.build_executor(mode="fixed_root")
    pending_build_grid = empty_grid()
    pending_build.tile_work[(2, 2)] = module.TileWork(
        (2, 2), 0, (), "await_confirm", 73, None,
        ("BUILD_PASTURE",))
    pending_build._sync_tile_work(
        74, pending_build_grid, [(4, 8, 8, ("BUILD_PASTURE",))])
    pending_build_work = pending_build.tile_work[(2, 2)]
    checks["await_generic_borrows_quota_across_planner_retarget"] = (
        set(pending_build.tile_work) == {(2, 2)}
        and pending_build_work.pending_intent_key == ("BUILD_PASTURE",)
        and pending_build_work.ready_ops == ((4, ("BUILD_PASTURE",)),)
        and pending_build_work.ready_since == 73)

    oldest_valid = module.build_executor(mode="fixed_root")
    oldest_valid_grid = empty_grid()
    for age, coord in ((9, (1, 7)), (2, (2, 7)), (5, (3, 7))):
        oldest_valid.tile_work[coord] = module.TileWork(
            coord, None, ((2, ("PLANT", "CARROT")),),
            "ordinary_plant", age, "CARROT")
    oldest_valid._sync_tile_work(
        80, oldest_valid_grid, [(2, 9, 9, ("PLANT", "CARROT"))])
    checks["oldest_valid_intent_retained"] = set(oldest_valid.tile_work) == {(2, 7)}
    return checks


def main() -> None:
    module = load(MAIN, "r23_candidate")
    r22 = load(R22_MAIN, "r22_reference")
    result = {"schema": module.SCHEMA,
              "static": static_checks(module, r22),
              "parity": parity_checks(module, r22),
              "mechanisms": mechanism_checks(module)}
    result["passed"] = all(
        all(group.values())
        for group in (result["static"], result["parity"], result["mechanisms"]))
    (HERE / "mechanism_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
