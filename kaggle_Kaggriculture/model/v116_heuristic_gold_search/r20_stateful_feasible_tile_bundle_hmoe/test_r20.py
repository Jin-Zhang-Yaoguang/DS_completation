#!/usr/bin/env python3
"""Behavioral mechanism checks for R20; no match or Replay execution."""

from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
MAIN = HERE / "main.py"
R19_MAIN = HERE.parent / "r19_growth_debt_throughput_hmoe" / "main.py"


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


def crop(crop_name: str = "WHEAT", watered: bool = True,
         ongoing_yield: int = 6) -> dict:
    return {"kind": "PLANT", "crop": crop_name, "watered_today": watered,
            "consecutive_unwatered": 0, "yield_units": ongoing_yield,
            "planted_day": 0}


def cow(fed: bool = False, cared: bool = False, product: int = 4,
        fertilizer: bool = True) -> dict:
    return {"kind": "PASTURE", "animal": {"kind": "COW"},
            "fed_today": fed, "cared_today": cared,
            "yield_units": product, "fertilizer_available": fertilizer}


def static_checks(module, r19) -> dict[str, bool]:
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
    same_targets = all(
        module.compile_daily_goals(module.compile_genomes(module.DEFAULT_PARAMS)[name])
        == r19.compile_daily_goals(r19.compile_genomes(r19.DEFAULT_PARAMS)[name])
        for name in module.EXPERT_NAMES)
    shops = sorted(module.SHOP_PRODUCTS)
    return {
        "independent_stdlib_candidate": (
            module.STRATEGY_PARENT is None and imports <= allowed
            and "r19_growth_debt_throughput_hmoe" not in source),
        "schema_r20": module.SCHEMA == "v116-r20-stateful-feasible-tile-bundle-hmoe-v1",
        "params_hash_unchanged": module.DEFAULT_PARAMS_HASH == r19.DEFAULT_PARAMS_HASH,
        "router_and_experts_unchanged": (
            module.EXPERT_NAMES == r19.EXPERT_NAMES
            and module.MODES == r19.MODES
            and all(module.route_expert([shop]) == r19.route_expert([shop]) for shop in shops)),
        "expert_targets_unchanged": same_targets,
        "thresholds_market_growth_unchanged": (
            all(getattr(module, key) == getattr(r19, key) for key in thresholds)
            and module.MARKET_PARAMS == r19.MARKET_PARAMS
            and module.DEFAULT_PARAMS == r19.DEFAULT_PARAMS),
    }


def mechanism_checks(module) -> dict[str, bool]:
    checks: dict[str, bool] = {}

    # An infeasible persistent PLANT head does not stop a feasible animal CARE.
    executor = module.build_executor(mode="fixed_root")
    grid = empty_grid()
    grid[1][1] = cow(fed=True, cared=False, product=0, fertilizer=False)
    executor.tile_work[(2, 2)] = module.TileWork(
        (2, 2), 0, ((1, ("PLANT", "WHEAT")),), "ordinary_plant", 0, "WHEAT")
    fallthrough = executor._assign(
        [[1, 1]], [{}], [(6, 1, 1, ("CARE",))], 10, 1, set(), 0, 1, grid, {})
    checks["infeasible_primary_falls_through"] = (
        fallthrough[0][3][0] == "CARE"
        and (2, 2) in executor.tile_work
        and bool(executor.tile_work[(2, 2)].ready_ops))

    # The same animal owner executes FEED->CARE->HARVEST->COLLECT at one tile.
    animal = module.build_executor(mode="fixed_root")
    animal_grid = empty_grid()
    animal_grid[2][2] = cow()
    units = [[2, 2], [4, 4]]
    inventories = [{"WHEAT": 1}, {}]
    sequence: list[str] = []
    jobs = [(1, 2, 2, ("FEED",)), (6, 2, 2, ("CARE",)),
            (2, 2, 2, ("HARVEST",)), (5, 2, 2, ("COLLECT_FERTILIZER",))]
    first = animal._assign(units, inventories, jobs, 8, 1, set(), 0, 1,
                           animal_grid, {})
    sequence.append(first[0][3][0])
    animal._mark_tile_work_emitted(1, (2, 2), ["FEED"])
    animal_grid[2][2]["fed_today"] = True
    second_jobs = jobs[1:]
    second = animal._assign(units, inventories, second_jobs, 9, 1, set(), 0, 2,
                            animal_grid, {})
    sequence.append(second[0][3][0])
    animal._mark_tile_work_emitted(2, (2, 2), ["CARE"])
    animal_grid[2][2]["cared_today"] = True
    third = animal._assign(units, inventories, second_jobs[1:], 10, 1, set(), 0, 3,
                           animal_grid, {})
    sequence.append(third[0][3][0])
    animal._mark_tile_work_emitted(3, (2, 2), ["HARVEST"])
    animal_grid[2][2]["yield_units"] = 0
    fourth = animal._assign(units, inventories, [second_jobs[-1]], 11, 1, set(), 0, 4,
                            animal_grid, {})
    sequence.append(fourth[0][3][0])
    checks["animal_bundle_single_trip"] = sequence == [
        "FEED", "CARE", "HARVEST", "COLLECT_FERTILIZER"]
    checks["persistent_primary_cannot_starve_animal"] = (
        animal.tile_work[(2, 2)].owner == 0
        and animal.audit["tile_bundle_assigned_owner"] == 3)

    # Non-ongoing replacement is confirmed at the original coordinate.
    replacement = module.build_executor(mode="fixed_root")
    replacement_grid = empty_grid()
    replacement_grid[3][3] = crop("WHEAT", watered=True)
    harvest = replacement._assign(
        [[3, 3], [4, 4]], [{}, {}], [(2, 3, 3, ("HARVEST",))],
        10, 1, set(), 8, 200, replacement_grid, {"WHEAT": 1})
    replacement._mark_tile_work_emitted(200, (3, 3), ["HARVEST"])
    replacement_grid[3][3] = None
    repl_plant = replacement._assign(
        [[3, 3], [4, 4]], [{}, {}], [], 11, 1, set(), 8, 201,
        replacement_grid, {"WHEAT": 1})
    replacement._mark_tile_work_emitted(201, (3, 3), ["PLANT", "WHEAT"])
    replacement_grid[3][3] = crop("WHEAT", watered=False, ongoing_yield=0)
    repl_water = replacement._assign(
        [[3, 3], [4, 4]], [{}, {}], [], 12, 1, set(), 8, 202,
        replacement_grid, {})
    checks["replacement_same_coord_chain"] = (
        harvest[0][3][0] == "HARVEST"
        and repl_plant[0][1:3] == (3, 3)
        and repl_plant[0][3] == ("PLANT", "WHEAT")
        and repl_water[0][1:3] == (3, 3)
        and repl_water[0][3][0] == "WATER")

    # Three planned bundles are simultaneously assigned; no global chain cap.
    parallel = module.build_executor(mode="fixed_root")
    parallel_grid = empty_grid(all_open=True)
    plant_jobs = [(1, 1, 1, ("PLANT", "WHEAT")),
                  (2, 2, 1, ("PLANT", "MELON")),
                  (2, 3, 1, ("PLANT", "STRAWBERRY"))]
    parallel_result = parallel._assign(
        [[1, 1], [2, 1], [3, 1]], [{}, {}, {}], plant_jobs,
        8, 4, set(), 8, 210, parallel_grid,
        {"WHEAT": 1, "MELON": 1, "STRAWBERRY": 1})
    checks["three_growth_bundles_parallel"] = (
        len(parallel_result) == module.MAX_PARALLEL_PLANT == 3
        and {job[1:3] for job in parallel_result.values()} == {(1, 1), (2, 1), (3, 1)})

    # One coordinate gets one actor while its remaining operations persist.
    retained = module.build_executor(mode="fixed_root")
    retained_grid = empty_grid()
    retained_grid[1][1] = cow()
    retained_jobs = [(1, 1, 1, ("FEED",)), (6, 1, 1, ("CARE",)),
                     (2, 1, 1, ("HARVEST",)),
                     (5, 1, 1, ("COLLECT_FERTILIZER",))]
    retained_result = retained._assign(
        [[1, 1], [1, 2]], [{"WHEAT": 1}, {"WHEAT": 1}], retained_jobs,
        8, 1, set(), 0, 1, retained_grid, {})
    retained_work = retained.tile_work[(1, 1)]
    checks["one_coord_one_actor_but_ops_retained"] = (
        len(retained_result) == 1 and len(retained_work.ready_ops) == 4
        and retained_work.ready_ops[1][1][0] == "CARE")

    # An unassigned ordinary WATER remains pending into the next observation.
    water = module.build_executor(mode="fixed_root")
    water_grid = empty_grid()
    water_grid[1][1] = crop("TOMATO", watered=False, ongoing_yield=0)
    no_actor = water._assign(
        [[4, 4]], [{}], [(2, 1, 1, ("WATER",))],
        8, 1, {0}, 8, 220, water_grid, {})
    next_obs = water._assign(
        [[4, 4]], [{}], [(2, 1, 1, ("WATER",))],
        9, 1, set(), 8, 221, water_grid, {})
    checks["ordinary_water_never_dropped"] = (
        not no_actor and next_obs[0][3][0] == "WATER"
        and water.tile_work[(1, 1)].ready_since == 220)

    # Unavailable owners transfer to the closest feasible actor.
    takeover = module.build_executor(mode="fixed_root")
    takeover_grid = empty_grid()
    takeover_grid[1][1] = crop("TOMATO", watered=False, ongoing_yield=0)
    takeover.tile_work[(1, 1)] = module.TileWork(
        (1, 1), 0, ((2, ("WATER",)),), "ongoing_crop", 1, "TOMATO")
    takeover_result = takeover._assign(
        [[8, 8], [1, 2]], [{}, {}], [(2, 1, 1, ("WATER",))],
        9, 1, {0}, 8, 222, takeover_grid, {})
    checks["unavailable_owner_closest_actor_takeover"] = (
        takeover_result[1][3][0] == "WATER"
        and takeover.tile_work[(1, 1)].owner == 1
        and takeover.audit["tile_bundle_owner_takeovers"] == 1)
    return checks


def main() -> None:
    module = load(MAIN, "r20_candidate")
    r19 = load(R19_MAIN, "r19_reference")
    result = {"schema": module.SCHEMA,
              "static": static_checks(module, r19),
              "mechanisms": mechanism_checks(module)}
    result["passed"] = all(result["static"].values()) and all(result["mechanisms"].values())
    (HERE / "mechanism_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
