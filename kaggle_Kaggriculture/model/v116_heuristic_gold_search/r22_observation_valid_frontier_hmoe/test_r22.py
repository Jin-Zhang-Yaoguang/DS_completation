#!/usr/bin/env python3
"""Behavioral mechanism checks for R22; no match or Replay execution."""

from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
MAIN = HERE / "main.py"
R21_MAIN = HERE.parent / "r21_soft_chain_lease_hmoe" / "main.py"


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


def plant(name: str = "WHEAT", watered: bool = True,
          yield_units: int = 6) -> dict:
    return {"kind": "PLANT", "crop": name, "watered_today": watered,
            "consecutive_unwatered": 0, "yield_units": yield_units,
            "planted_day": 0}


def pasture(animal: dict | None = None) -> dict:
    return {"kind": "PASTURE", "animal": animal}


def cow(fed: bool = True, cared: bool = False) -> dict:
    return {"kind": "PASTURE", "animal": {"kind": "COW"},
            "fed_today": fed, "cared_today": cared,
            "yield_units": 0, "fertilizer_available": False}


def static_checks(module, r21) -> dict[str, bool]:
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
    r21_genomes = r21.compile_genomes(r21.DEFAULT_PARAMS)
    same_targets = all(
        module.compile_daily_goals(module_genomes[name])
        == r21.compile_daily_goals(r21_genomes[name])
        for name in module.EXPERT_NAMES)
    return {
        "independent_stdlib_candidate": (
            module.STRATEGY_PARENT is None and imports <= allowed
            and "r21_soft_chain_lease_hmoe" not in source),
        "schema_r22": module.SCHEMA == "v116-r22-observation-valid-frontier-hmoe-v1",
        "params_hash_unchanged": module.DEFAULT_PARAMS_HASH == r21.DEFAULT_PARAMS_HASH,
        "router_experts_targets_unchanged": (
            module.EXPERT_NAMES == r21.EXPERT_NAMES and module.MODES == r21.MODES
            and same_targets
            and all(module.route_expert([shop]) == r21.route_expert([shop])
                    for shop in sorted(module.SHOP_PRODUCTS))),
        "market_thresholds_unchanged": (
            all(getattr(module, key) == getattr(r21, key) for key in thresholds)
            and module.MARKET_PARAMS == r21.MARKET_PARAMS
            and module.DEFAULT_PARAMS == r21.DEFAULT_PARAMS),
    }


def parity_checks(module, r21) -> dict[str, bool]:
    grid = empty_grid(all_open=True)
    seeds = {crop: 20 for crop in module.CROPS}
    left = module.build_executor(mode="fixed_grain_egg")
    right = r21.build_executor(mode="fixed_grain_egg")
    goal_left = left.goal(8)
    goal_right = right.goal(8)
    units = [[4, 4], [5, 4], [4, 5]]
    jobs_equal = (
        left._jobs(8, 0, units, grid, goal_left, seeds, goal_left)
        == right._jobs(8, 0, units, grid, goal_right, seeds, goal_right))

    # Emitted replacement confirmation behavior is unchanged from R21.
    grids = [empty_grid(), empty_grid()]
    executors = [left, right]
    for candidate_grid, executor in zip(grids, executors):
        candidate_grid[2][2] = plant()
        executor._sync_tile_work(10, candidate_grid,
                                 [(2, 2, 2, ("HARVEST",))])
        executor._mark_tile_work_emitted(10, (2, 2), ["HARVEST"])
        candidate_grid[2][2] = None
        executor._sync_tile_work(11, candidate_grid, [])
    lw = left.tile_work[(2, 2)]
    rw = right.tile_work[(2, 2)]

    # Soft lease nearest-actor handoff remains byte-for-byte behavioral parity.
    lease_results = []
    for candidate in (module, r21):
        executor = candidate.build_executor(mode="fixed_root")
        candidate_grid = empty_grid()
        candidate_grid[1][1] = cow()
        executor.tile_work[(1, 1)] = candidate.TileWork(
            (1, 1), 0, ((6, ("CARE",)),), "animal", 1)
        result = executor._assign(
            [[9, 9], [1, 2]], [{}, {}], [(6, 1, 1, ("CARE",))],
            10, 1, set(), 0, 2, candidate_grid, {})
        lease_results.append((result, executor.tile_work[(1, 1)].owner))

    return {
        "r21_jobs_parity": jobs_equal,
        "r21_emitted_confirmation_parity": (
            lw.phase == rw.phase == "replacement_plant"
            and lw.ready_ops == rw.ready_ops
            and lw.crop_if_needed == rw.crop_if_needed == "WHEAT"),
        "r21_soft_lease_parity": lease_results[0] == lease_results[1],
    }


def mechanism_checks(module) -> dict[str, bool]:
    checks: dict[str, bool] = {}

    met = module.build_executor(mode="fixed_root")
    met_grid = empty_grid()
    met.tile_work[(2, 2)] = module.TileWork(
        (2, 2), 0, ((4, ("BUILD_PASTURE",)),), "generic", 3)
    met._sync_tile_work(10, met_grid, [])
    checks["structure_target_met_expires_old_build"] = (
        (2, 2) not in met.tile_work
        and met.audit["tile_bundle_stale_intent_expired"] == 1)

    retarget_plant = module.build_executor(mode="fixed_root")
    retarget_grid = empty_grid()
    retarget_plant.tile_work[(1, 1)] = module.TileWork(
        (1, 1), 0, ((2, ("PLANT", "WHEAT")),),
        "ordinary_plant", 2, "WHEAT")
    retarget_plant._sync_tile_work(
        20, retarget_grid, [(2, 2, 2, ("PLANT", "WHEAT"))])
    plant_retargeted = (
        (1, 1) not in retarget_plant.tile_work
        and retarget_plant.tile_work[(2, 2)].ready_since == 20
        and retarget_plant.tile_work[(2, 2)].owner is None)

    retarget_place = module.build_executor(mode="fixed_root")
    retarget_place_grid = empty_grid()
    retarget_place_grid[3][3] = pasture()
    retarget_place.tile_work[(3, 3)] = module.TileWork(
        (3, 3), 0, ((3, ("PLACE", "COW")),), "generic", 4)
    retarget_place._sync_tile_work(
        25, retarget_place_grid, [(3, 3, 3, ("PLACE", "SHEEP"))])
    new_place = retarget_place.tile_work[(3, 3)]
    place_retargeted = (
        new_place.ready_ops == ((3, ("PLACE", "SHEEP")),)
        and new_place.ready_since == 25 and new_place.owner is None)
    checks["planner_retarget_expires_old_ordinary_plant_place"] = (
        plant_retargeted and place_retargeted)

    emitted = module.build_executor(mode="fixed_root")
    emitted_grid = empty_grid()
    emitted_grid[2][2] = plant()
    emitted._sync_tile_work(30, emitted_grid,
                            [(2, 2, 2, ("HARVEST",))])
    emitted._mark_tile_work_emitted(30, (2, 2), ["HARVEST"])
    emitted_grid[2][2] = None
    emitted._sync_tile_work(31, emitted_grid, [])
    after_empty = emitted.tile_work[(2, 2)]
    empty_ok = (after_empty.phase == "replacement_plant"
                and after_empty.ready_since == 30
                and after_empty.ready_ops == ((2, ("PLANT", "WHEAT")),))
    emitted._mark_tile_work_emitted(31, (2, 2), ["PLANT", "WHEAT"])
    emitted_grid[2][2] = plant(watered=False, yield_units=0)
    emitted._sync_tile_work(32, emitted_grid, [])
    after_plant = emitted.tile_work[(2, 2)]
    checks["emitted_replacement_chain_survives_no_planner_job"] = (
        empty_ok and after_plant.phase == "planted_water"
        and after_plant.ready_since == 30
        and after_plant.ready_ops == ((2, ("WATER",)),))

    parallel = module.build_executor(mode="fixed_root")
    parallel_grid = empty_grid(all_open=True)
    zero_crops = {crop: 0 for crop in module.CROPS}
    one_cow_goal = {"crops": zero_crops,
                    "animals": {"GOOSE": 0, "COW": 1, "SHEEP": 0}}
    current_jobs = parallel._jobs(
        0, 0, [[0, 0], [1, 0], [2, 0]], parallel_grid,
        one_cow_goal, zero_crops, one_cow_goal)
    current_builds = [job for job in current_jobs if job[3][0] == "BUILD_PASTURE"]
    assert len(current_builds) == 1
    live_coord = (current_builds[0][1], current_builds[0][2])
    stale_coords = [(8, 8), (9, 9)]
    for age, coord in enumerate(stale_coords, 1):
        parallel.tile_work[coord] = module.TileWork(
            coord, age - 1, ((4, ("BUILD_PASTURE",)),), "generic", age)
    assigned = parallel._assign(
        [[0, 0], [1, 0], [2, 0]], [{}, {}, {}], current_jobs,
        0, 10, set(), 0, 40, parallel_grid, zero_crops)
    assigned_builds = [job for job in assigned.values()
                       if job[3][0] == "BUILD_PASTURE"]
    checks["parallel_builds_never_exceed_current_deficit"] = (
        len(assigned_builds) == len(current_builds) == 1
        and (assigned_builds[0][1], assigned_builds[0][2]) == live_coord
        and all(coord not in parallel.tile_work for coord in stale_coords))

    fresh = module.build_executor(mode="fixed_root")
    fresh_grid = empty_grid()
    fresh.tile_work[(4, 4)] = module.TileWork(
        (4, 4), 0, ((4, ("BUILD_PASTURE",)),), "generic", 1)
    fresh._sync_tile_work(50, fresh_grid,
                          [(4, 4, 4, ("BUILD_COOP",))])
    rebuilt = fresh.tile_work[(4, 4)]
    checks["no_stale_generic_ready_since"] = (
        rebuilt.ready_since == 50 and rebuilt.owner is None
        and rebuilt.ready_ops == ((4, ("BUILD_COOP",)),))

    same = module.build_executor(mode="fixed_root")
    same_grid = empty_grid()
    same.tile_work[(1, 1)] = module.TileWork(
        (1, 1), 0, ((7, ("PLANT", "CARROT")),),
        "ordinary_plant", 6, "CARROT")
    same._sync_tile_work(60, same_grid,
                         [(2, 1, 1, ("PLANT", "CARROT"))])
    retained = same.tile_work[(1, 1)]
    checks["same_semantic_frontier_keeps_age_and_updates_priority"] = (
        retained.ready_since == 6 and retained.owner == 0
        and retained.ready_ops == ((2, ("PLANT", "CARROT")),))
    return checks


def main() -> None:
    module = load(MAIN, "r22_candidate")
    r21 = load(R21_MAIN, "r21_reference")
    result = {"schema": module.SCHEMA,
              "static": static_checks(module, r21),
              "parity": parity_checks(module, r21),
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
