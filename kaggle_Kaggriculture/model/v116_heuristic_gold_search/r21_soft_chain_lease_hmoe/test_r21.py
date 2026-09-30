#!/usr/bin/env python3
"""Behavioral mechanism checks for R21; no match or Replay execution."""

from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
MAIN = HERE / "main.py"
R20_MAIN = HERE.parent / "r20_stateful_feasible_tile_bundle_hmoe" / "main.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def empty_grid(all_open: bool = False) -> list[list[object]]:
    return [[None if all_open or (x < 5 and y < 5) else "LOCKED"
             for x in range(10)] for y in range(10)]


def plant(name: str = "WHEAT", watered: bool = True, yield_units: int = 6) -> dict:
    return {"kind": "PLANT", "crop": name, "watered_today": watered,
            "consecutive_unwatered": 0, "yield_units": yield_units,
            "planted_day": 0}


def cow(fed: bool = False, cared: bool = False, yield_units: int = 4,
        fertilizer: bool = True) -> dict:
    return {"kind": "PASTURE", "animal": {"kind": "COW"},
            "fed_today": fed, "cared_today": cared,
            "yield_units": yield_units, "fertilizer_available": fertilizer}


def static_checks(module, r20) -> dict[str, bool]:
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
    r20_genomes = r20.compile_genomes(r20.DEFAULT_PARAMS)
    same_targets = all(
        module.compile_daily_goals(module_genomes[name])
        == r20.compile_daily_goals(r20_genomes[name])
        for name in module.EXPERT_NAMES)
    return {
        "independent_stdlib_candidate": (
            module.STRATEGY_PARENT is None and imports <= allowed
            and "r20_stateful_feasible_tile_bundle_hmoe" not in source),
        "schema_r21": module.SCHEMA == "v116-r21-soft-chain-lease-hmoe-v1",
        "params_hash_unchanged": module.DEFAULT_PARAMS_HASH == r20.DEFAULT_PARAMS_HASH,
        "router_experts_targets_unchanged": (
            module.EXPERT_NAMES == r20.EXPERT_NAMES and module.MODES == r20.MODES
            and same_targets
            and all(module.route_expert([shop]) == r20.route_expert([shop])
                    for shop in sorted(module.SHOP_PRODUCTS))),
        "market_thresholds_unchanged": (
            all(getattr(module, key) == getattr(r20, key) for key in thresholds)
            and module.MARKET_PARAMS == r20.MARKET_PARAMS
            and module.DEFAULT_PARAMS == r20.DEFAULT_PARAMS),
    }


def parity_checks(module, r20) -> dict[str, bool]:
    grid = empty_grid(all_open=True)
    seeds = {crop: 20 for crop in module.CROPS}
    left = module.build_executor(mode="fixed_grain_egg")
    right = r20.build_executor(mode="fixed_grain_egg")
    left_goal = left.goal(8)
    right_goal = right.goal(8)
    units = [[4, 4], [5, 4], [4, 5]]
    same_jobs = left._jobs(8, 0, units, grid, left_goal, seeds, left_goal) \
        == right._jobs(8, 0, units, grid, right_goal, seeds, right_goal)

    # Compare the actual R20/R21 confirmation state, excluding lease age.
    left_grid = empty_grid()
    right_grid = empty_grid()
    left_grid[2][2] = plant()
    right_grid[2][2] = plant()
    harvest = [(2, 2, 2, ("HARVEST",))]
    left._sync_tile_work(10, left_grid, harvest)
    right._sync_tile_work(10, right_grid, harvest)
    left._mark_tile_work_emitted(10, (2, 2), ["HARVEST"])
    right._mark_tile_work_emitted(10, (2, 2), ["HARVEST"])
    left_grid[2][2] = None
    right_grid[2][2] = None
    left._sync_tile_work(11, left_grid, [])
    right._sync_tile_work(11, right_grid, [])
    lw = left.tile_work[(2, 2)]
    rw = right.tile_work[(2, 2)]
    return {
        "r20_jobs_parity": same_jobs,
        "r20_state_confirmation_parity": (
            lw.phase == rw.phase == "replacement_plant"
            and lw.ready_ops == rw.ready_ops
            and lw.crop_if_needed == rw.crop_if_needed == "WHEAT"),
    }


def mechanism_checks(module) -> dict[str, bool]:
    checks: dict[str, bool] = {}

    far = module.build_executor(mode="fixed_root")
    far_grid = empty_grid()
    far_grid[1][1] = cow(fed=True, cared=False, yield_units=0, fertilizer=False)
    far.tile_work[(1, 1)] = module.TileWork(
        (1, 1), 0, ((6, ("CARE",)),), "animal", 1)
    far_result = far._assign(
        [[9, 9], [1, 2]], [{}, {}], [(6, 1, 1, ("CARE",))],
        10, 1, set(), 0, 2, far_grid, {})
    checks["far_available_owner_yields_to_nearest"] = (
        1 in far_result and far_result[1][3][0] == "CARE"
        and far.tile_work[(1, 1)].owner == 1)

    lease = module.build_executor(mode="fixed_root")
    lease_grid = empty_grid()
    lease_grid[1][1] = cow(fed=True, cared=False, yield_units=0, fertilizer=False)
    lease.tile_work[(2, 2)] = module.TileWork(
        (2, 2), 0, ((1, ("PLANT", "WHEAT")),), "ordinary_plant", 0, "WHEAT")
    lease_result = lease._assign(
        [[1, 1]], [{}], [(6, 1, 1, ("CARE",))],
        10, 1, set(), 0, 2, lease_grid, {})
    checks["one_actor_one_lease"] = (
        lease_result[0][3][0] == "CARE"
        and lease.tile_work[(1, 1)].owner == 0
        and lease.tile_work[(2, 2)].owner is None
        and lease.audit["soft_lease_releases"] == 1)

    replacement = module.build_executor(mode="fixed_root")
    replacement_grid = empty_grid(all_open=True)
    replacement_grid[5][5] = plant()
    replacement._assign(
        [[5, 5]], [{}], [(2, 5, 5, ("HARVEST",))],
        8, 4, set(), 8, 100, replacement_grid, {"WHEAT": 2})
    replacement._mark_tile_work_emitted(100, (5, 5), ["HARVEST"])
    replacement_grid[5][5] = None
    late_ordinary = [(1, 1, 1, ("PLANT", "WHEAT"))]
    inherited = replacement._assign(
        [[1, 1]], [{}], late_ordinary,
        9, 4, set(), 8, 101, replacement_grid, {"WHEAT": 2})
    checks["replacement_chain_age_inherited"] = (
        replacement.tile_work[(5, 5)].ready_since == 100
        and inherited[0][1:3] == (5, 5)
        and inherited[0][3] == ("PLANT", "WHEAT")
        and replacement.tile_work[(1, 1)].ready_since == 101)

    animal = module.build_executor(mode="fixed_root")
    animal_grid = empty_grid()
    animal_grid[2][2] = cow()
    units = [[2, 2], [4, 4]]
    inventories = [{"WHEAT": 1}, {}]
    all_jobs = [(1, 2, 2, ("FEED",)), (6, 2, 2, ("CARE",)),
                (2, 2, 2, ("HARVEST",)),
                (5, 2, 2, ("COLLECT_FERTILIZER",))]
    sequence: list[str] = []
    ages: list[int] = []
    result = animal._assign(units, inventories, all_jobs, 8, 1, set(), 0, 1,
                            animal_grid, {})
    sequence.append(result[0][3][0]); ages.append(animal.tile_work[(2, 2)].ready_since)
    animal._mark_tile_work_emitted(1, (2, 2), ["FEED"])
    animal_grid[2][2]["fed_today"] = True
    result = animal._assign(units, inventories, all_jobs[1:], 9, 1, set(), 0, 2,
                            animal_grid, {})
    sequence.append(result[0][3][0]); ages.append(animal.tile_work[(2, 2)].ready_since)
    animal._mark_tile_work_emitted(2, (2, 2), ["CARE"])
    animal_grid[2][2]["cared_today"] = True
    result = animal._assign(units, inventories, all_jobs[2:], 10, 1, set(), 0, 3,
                            animal_grid, {})
    sequence.append(result[0][3][0]); ages.append(animal.tile_work[(2, 2)].ready_since)
    animal._mark_tile_work_emitted(3, (2, 2), ["HARVEST"])
    animal_grid[2][2]["yield_units"] = 0
    result = animal._assign(units, inventories, all_jobs[3:], 11, 1, set(), 0, 4,
                            animal_grid, {})
    sequence.append(result[0][3][0]); ages.append(animal.tile_work[(2, 2)].ready_since)
    checks["animal_chain_age_inherited_four_stages"] = (
        sequence == ["FEED", "CARE", "HARVEST", "COLLECT_FERTILIZER"]
        and ages == [1, 1, 1, 1])

    bijective = module.build_executor(mode="fixed_root")
    bijective_grid = empty_grid()
    bijective.tile_work[(1, 1)] = module.TileWork(
        (1, 1), 0, ((2, ("PLANT", "WHEAT")),), "ordinary_plant", 1, "WHEAT")
    bijective.tile_work[(2, 2)] = module.TileWork(
        (2, 2), 0, ((2, ("PLANT", "WHEAT")),), "ordinary_plant", 2, "WHEAT")
    bijective._assign([[4, 4]], [{}], [], 8, 1, {0}, 0, 3, bijective_grid, {})
    owners = [work.owner for work in bijective.tile_work.values() if work.owner is not None]
    checks["owner_mapping_bijective"] = (
        len(owners) == len(set(owners)) == 1
        and bijective.audit["soft_lease_duplicate_repairs"] == 1)

    trip = module.build_executor(mode="fixed_root")
    trip_grid = empty_grid()
    plant_jobs = [(1, 3, 3, ("PLANT", "WHEAT"))]
    first = trip._assign([[3, 3]], [{}], plant_jobs, 8, 1, set(), 8, 20,
                         trip_grid, {"WHEAT": 1})
    trip._mark_tile_work_emitted(20, (3, 3), ["PLANT", "WHEAT"])
    trip_grid[3][3] = plant("WHEAT", watered=False, yield_units=0)
    second = trip._assign([[3, 3]], [{}], [], 9, 1, set(), 8, 21,
                          trip_grid, {})
    checks["synthetic_single_trip_no_return"] = (
        first[0][3] == ("PLANT", "WHEAT") and second[0][3][0] == "WATER"
        and first[0][1:3] == second[0][1:3] == (3, 3)
        and trip.tile_work[(3, 3)].owner == 0
        and trip.tile_work[(3, 3)].ready_since == 20)

    # Frontier behavior and parallel growth remain inherited from R20.
    frontier = module.build_executor(mode="fixed_root")
    frontier_grid = empty_grid()
    frontier_grid[1][1] = cow(fed=True, cared=False, yield_units=0, fertilizer=False)
    frontier.tile_work[(2, 2)] = module.TileWork(
        (2, 2), None, ((1, ("PLANT", "WHEAT")),), "ordinary_plant", 0, "WHEAT")
    frontier_result = frontier._assign(
        [[1, 1]], [{}], [(6, 1, 1, ("CARE",))],
        8, 1, set(), 0, 2, frontier_grid, {})
    checks["finite_frontier_never_breaks_scheduler"] = frontier_result[0][3][0] == "CARE"

    parallel = module.build_executor(mode="fixed_root")
    parallel_grid = empty_grid(all_open=True)
    parallel_jobs = [(1, 1, 1, ("PLANT", "WHEAT")),
                     (2, 2, 1, ("PLANT", "MELON")),
                     (2, 3, 1, ("PLANT", "STRAWBERRY"))]
    parallel_result = parallel._assign(
        [[1, 1], [2, 1], [3, 1]], [{}, {}, {}], parallel_jobs,
        8, 4, set(), 8, 30, parallel_grid,
        {"WHEAT": 1, "MELON": 1, "STRAWBERRY": 1})
    checks["three_growth_bundles_parallel"] = len(parallel_result) == 3
    return checks


def main() -> None:
    module = load(MAIN, "r21_candidate")
    r20 = load(R20_MAIN, "r20_reference")
    result = {"schema": module.SCHEMA,
              "static": static_checks(module, r20),
              "parity": parity_checks(module, r20),
              "mechanisms": mechanism_checks(module)}
    result["passed"] = all(
        all(group.values()) for group in (result["static"], result["parity"], result["mechanisms"]))
    (HERE / "mechanism_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
