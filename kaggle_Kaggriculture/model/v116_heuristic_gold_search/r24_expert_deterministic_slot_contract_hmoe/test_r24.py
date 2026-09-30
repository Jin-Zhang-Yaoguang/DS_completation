#!/usr/bin/env python3
"""Behavioral mechanism checks for R24; no match or Replay execution."""

from __future__ import annotations

import ast
from collections import Counter
import copy
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
          yield_units: int = 0, planted_day: int = 0) -> dict:
    return {"kind": "PLANT", "crop": name, "watered_today": watered,
            "consecutive_unwatered": 0, "yield_units": yield_units,
            "planted_day": planted_day}


def animal(kind: str = "SHEEP", structure: str = "PASTURE",
           fed: bool = True, cared: bool = True) -> dict:
    return {"kind": structure, "animal": {"kind": kind},
            "fed_today": fed, "cared_today": cared,
            "yield_units": 0, "fertilizer_available": False}


def set_tile(grid: list[list[object]], coord: tuple[int, int], value: object) -> None:
    grid[coord[1]][coord[0]] = value


def plant_jobs(jobs):
    return [job for job in jobs if job[3][0] == "PLANT"]


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
    return {
        "independent_stdlib_candidate": (
            module.STRATEGY_PARENT is None and imports <= allowed
            and "r22_observation_valid_frontier_hmoe" not in source),
        "schema_r24": (
            module.SCHEMA
            == "v116-r24-expert-deterministic-slot-contract-hmoe-v1"),
        "params_genomes_daily_targets_unchanged": (
            module.DEFAULT_PARAMS_HASH == r22.DEFAULT_PARAMS_HASH
            and module_genomes == r22_genomes
            and all(module.compile_daily_goals(module_genomes[name])
                    == r22.compile_daily_goals(r22_genomes[name])
                    for name in module.EXPERT_NAMES)),
        "router_market_thresholds_unchanged": (
            all(getattr(module, key) == getattr(r22, key) for key in thresholds)
            and module.MARKET_PARAMS == r22.MARKET_PARAMS
            and module.DEFAULT_PARAMS == r22.DEFAULT_PARAMS
            and all(module.route_expert([shop]) == r22.route_expert([shop])
                    for shop in sorted(module.SHOP_PRODUCTS))),
        "r23_intent_ledger_absent": (
            "pending_intent_key" not in source
            and "intent_ledger" not in source.lower()),
    }


def parity_checks(module, r22) -> dict[str, bool]:
    nearest = []
    for candidate in (module, r22):
        executor = candidate.build_executor(mode="fixed_root")
        grid = empty_grid(False)
        grid[1][1] = animal("COW", fed=True, cared=False)
        executor.tile_work[(1, 1)] = candidate.TileWork(
            (1, 1), 0, ((6, ("CARE",)),), "animal", 1)
        result = executor._assign(
            [[9, 9], [1, 2]], [{}, {}], [(6, 1, 1, ("CARE",))],
            10, 1, set(), 0, 2, grid, {})
        nearest.append((result, executor.tile_work[(1, 1)].owner))

    confirmation = []
    for candidate in (module, r22):
        executor = candidate.build_executor(mode="fixed_root")
        grid = empty_grid(False)
        grid[2][2] = plant("WHEAT", True, 6, 0)
        executor._sync_tile_work(10, grid, [(2, 2, 2, ("HARVEST",))])
        executor._mark_tile_work_emitted(10, (2, 2), ["HARVEST"])
        grid[2][2] = None
        executor._sync_tile_work(11, grid, [])
        work = executor.tile_work[(2, 2)]
        confirmation.append((work.phase, work.ready_ops,
                             work.crop_if_needed, work.ready_since))

    frontier = []
    for candidate in (module, r22):
        executor = candidate.build_executor(mode="fixed_root")
        grid = empty_grid(False)
        executor.tile_work[(1, 1)] = candidate.TileWork(
            (1, 1), 0, ((2, ("PLANT", "WHEAT")),),
            "ordinary_plant", 4, "WHEAT")
        executor._sync_tile_work(
            9, grid, [(1, 1, 1, ("PLANT", "WHEAT"))])
        work = executor.tile_work[(1, 1)]
        frontier.append((work.ready_since, work.owner, work.ready_ops))
    return {
        "soft_nearest_owner_parity": nearest[0] == nearest[1],
        "confirmation_chain_parity": confirmation[0] == confirmation[1],
        "exact_frontier_parity": frontier[0] == frontier[1],
        "market_price_parity": all(
            module.market_price(product, inventory)
            == r22.market_price(product, inventory)
            for product in module.PRODUCTS
            for inventory in (9000, 9999, 10000, 10001, 11000)),
    }


def mechanism_checks(module) -> dict[str, bool]:
    checks: dict[str, bool] = {}
    genomes = module.compile_genomes(module.DEFAULT_PARAMS)
    contracts = module.compile_slot_contracts(genomes)

    final_ok = True
    for name, contract in contracts.items():
        expected_crops: Counter[str] = Counter()
        for block in genomes[name]["crop_blocks"]:
            expected_crops.update(block)
        expected_animals = Counter()
        for _day, kind, count in genomes[name]["animal_waves"]:
            expected_animals[kind] += int(count)
        actual_crops = Counter(slot.crop for slot in contract.crop_slots)
        actual_animals = Counter(slot.animal_kind for slot in contract.animal_slots)
        coords = [slot.coord for slot in (*contract.animal_slots,
                                          *contract.crop_slots)]
        final_ok &= (
            actual_crops == expected_crops and actual_animals == expected_animals
            and len(contract.crop_slots) == 59
            and len(coords) == len(set(coords))
            and set(coords) <= set(module._land_prefix(2))
            and all(slot.coord in module._land_prefix(slot.activation_stage)
                    for slot in (*contract.animal_slots, *contract.crop_slots)))
    checks["final_exact_counts_unique_coordinates_within_75"] = final_ok

    all_prefixes = []
    prefix_ok = True
    for name in module.EXPERT_NAMES:
        fixed = module.build_executor(mode=f"fixed_{name}")
        expert_prefixes = []
        for day in (0, 5, 9, 29):
            animals, crops = fixed.active_slot_contract(day)
            expert_prefixes.append({slot.coord for slot in (*animals, *crops)})
        prefix_ok &= (expert_prefixes[0] < expert_prefixes[1] < expert_prefixes[2]
                      and expert_prefixes[2] == expert_prefixes[3])
        all_prefixes.append(expert_prefixes)
    prefixes = all_prefixes[module.EXPERT_NAMES.index("wool")]
    checks["stage_prefix_immutable_day0_day5_day9_day29"] = prefix_ok

    common_contracts = []
    for name in module.EXPERT_NAMES:
        contract = contracts[name]
        common_animals = tuple(slot for slot in contract.animal_slots
                               if slot.activation_stage == 0)
        common_crops = tuple(slot for slot in contract.crop_slots
                             if slot.activation_stage == 0)
        common_contracts.append((common_animals, common_crops))
    common_animal_counts = Counter(slot.animal_kind for slot in common_contracts[0][0])
    common_crop_counts = Counter(slot.crop for slot in common_contracts[0][1])
    checks["five_experts_common_stage_identical_w8_m7_sheep4"] = (
        len(set(common_contracts)) == 1
        and common_animal_counts == Counter({"SHEEP": 4})
        and common_crop_counts == Counter({"WHEAT": 8, "MELON": 7}))

    router = module.build_executor(mode="router")
    before_animals, before_crops = router.active_slot_contract(9)
    before_coords = {slot.coord for slot in (*before_animals, *before_crops)}
    router._route({"step": 220, "town": {"unlocked_shops": ["YARN_STORE"]}})
    after_animals, after_crops = router.active_slot_contract(9)
    after_coords = {slot.coord for slot in (*after_animals, *after_crops)}
    checks["late_commit_preserves_common_and_has_no_default_extras"] = (
        len(before_animals) == 4 and len(before_crops) == 15
        and router.expert == "wool" and router.committed
        and before_coords < after_coords
        and before_coords == prefixes[0])

    deterministic = module.build_executor(mode="fixed_wool")
    animals0, crops0 = deterministic.active_slot_contract(8)
    calm_grid = empty_grid()
    set_tile(calm_grid, animals0[0].coord, animal("SHEEP", fed=True, cared=True))
    first_wheat = next(slot for slot in crops0 if slot.crop == "WHEAT")
    set_tile(calm_grid, first_wheat.coord, plant("WHEAT", watered=True))
    busy_grid = copy.deepcopy(calm_grid)
    busy_animal = busy_grid[animals0[0].coord[1]][animals0[0].coord[0]]
    busy_animal["fed_today"] = False
    busy_animal["cared_today"] = False
    busy_plant = busy_grid[first_wheat.coord[1]][first_wheat.coord[0]]
    busy_plant["watered_today"] = False
    seeds = {crop: 20 for crop in module.CROPS}
    goal0 = deterministic.goal(8)
    deterministic.crop_cursor = 0
    calm_jobs = deterministic._jobs(
        8, 0, [[0, 0], [1, 0], [2, 0]], calm_grid, goal0, seeds, goal0)
    deterministic.crop_cursor = 4
    busy_jobs = deterministic._jobs(
        8, 0, [[9, 9], [8, 9], [9, 8]], busy_grid, goal0, seeds, goal0)
    calm_keys = [module._job_key(job) for job in plant_jobs(calm_jobs)]
    busy_keys = [module._job_key(job) for job in plant_jobs(busy_jobs)]
    checks["units_cursor_and_maintenance_do_not_change_three_plant_keys"] = (
        len(calm_keys) == len(busy_keys) == 3 and calm_keys == busy_keys
        and plant_jobs(calm_jobs)[0][0] == plant_jobs(busy_jobs)[0][0] == 1)

    admission = module.build_executor(mode="fixed_wool")
    admission_grid = empty_grid()
    _animals, admission_crops = admission.active_slot_contract(0)
    wheat_slots = [slot for slot in admission_crops if slot.crop == "WHEAT"]
    for slot in wheat_slots[:2]:
        set_tile(admission_grid, slot.coord, {"kind": "WEED"})
    wheat_seeds = {crop: (10 if crop == "WHEAT" else 0) for crop in module.CROPS}
    admission_jobs = admission._jobs(
        0, 0, [[4, 4]], admission_grid, admission.goal(0),
        wheat_seeds, admission.goal(0))
    admitted_coords = [(job[1], job[2]) for job in plant_jobs(admission_jobs)]
    checks["three_admission_skips_conflict_to_later_same_crop_slots"] = (
        len(admitted_coords) == 3
        and admitted_coords == [slot.coord for slot in wheat_slots[2:5]])

    lease = module.build_executor(mode="fixed_wool")
    lease_grid = empty_grid()
    lease_jobs = lease._jobs(
        0, 0, [[4, 4]], lease_grid, lease.goal(0), seeds, lease.goal(0))
    lease._sync_tile_work(1, lease_grid, lease_jobs)
    leased_job = plant_jobs(lease_jobs)[0]
    leased_coord = (leased_job[1], leased_job[2])
    lease.tile_work[leased_coord].owner = 0
    lease.crop_cursor = 4
    lease_jobs_again = lease._jobs(
        0, 0, [[9, 9], [8, 8]], lease_grid, lease.goal(0), seeds, lease.goal(0))
    lease._sync_tile_work(2, lease_grid, lease_jobs_again)
    leased_work = lease.tile_work[leased_coord]
    checks["exact_frontier_lease_does_not_expire"] = (
        leased_work.ready_since == 1 and leased_work.owner == 0
        and module._job_key(lease._head_job(leased_work))
        == module._job_key(leased_job))

    finite = module.build_executor(mode="fixed_grain_egg")
    finite_grid = empty_grid()
    _finite_animals, finite_crops = finite.active_slot_contract(8)
    finite_slot = next(slot for slot in finite_crops if slot.crop == "WHEAT")
    set_tile(finite_grid, finite_slot.coord,
             plant("WHEAT", watered=True, yield_units=6, planted_day=0))
    finite_units = [[finite_slot.coord[0], finite_slot.coord[1]]]
    finite_seeds = {crop: (5 if crop == "WHEAT" else 0) for crop in module.CROPS}
    finite_jobs = finite._jobs(
        8, 0, finite_units, finite_grid, finite.goal(8),
        finite_seeds, finite.goal(8))
    harvest = next(job for job in finite_jobs
                   if job[3][0] == "HARVEST"
                   and (job[1], job[2]) == finite_slot.coord)
    finite._sync_tile_work(100, finite_grid, finite_jobs)
    finite._mark_tile_work_emitted(100, finite_slot.coord, ["HARVEST"])
    set_tile(finite_grid, finite_slot.coord, None)
    after_harvest_jobs = finite._jobs(
        8, 1, finite_units, finite_grid, finite.goal(8),
        finite_seeds, finite.goal(8))
    finite._sync_tile_work(101, finite_grid, after_harvest_jobs)
    replacement = finite._head_job(finite.tile_work[finite_slot.coord])
    finite._mark_tile_work_emitted(101, finite_slot.coord, ["PLANT", "WHEAT"])
    set_tile(finite_grid, finite_slot.coord,
             plant("WHEAT", watered=False, yield_units=0, planted_day=8))
    finite._sync_tile_work(102, finite_grid, [])
    water = finite._head_job(finite.tile_work[finite_slot.coord])
    checks["finite_harvest_replants_and_waters_original_coordinate"] = (
        harvest[3][0] == "HARVEST"
        and replacement is not None and replacement[1:3] == finite_slot.coord
        and replacement[3] == ("PLANT", "WHEAT")
        and water is not None and water[1:3] == finite_slot.coord
        and water[3] == ("WATER",))

    conflict = module.build_executor(mode="fixed_wool")
    conflict_grid = empty_grid()
    conflict_animals, conflict_crops = conflict.active_slot_contract(0)
    set_tile(conflict_grid, conflict_animals[0].coord,
             {"kind": "COOP", "animal": None})
    set_tile(conflict_grid, conflict_animals[1].coord,
             animal("COW", "PASTURE"))
    wrong_crop_slot = next(slot for slot in conflict_crops if slot.crop == "WHEAT")
    set_tile(conflict_grid, wrong_crop_slot.coord,
             plant("MELON", True, 6, -20))
    conflict_jobs = conflict._jobs(
        0, 0, [[4, 4]], conflict_grid, conflict.goal(0), seeds,
        conflict.goal(0))
    conflicted = {conflict_animals[0].coord, conflict_animals[1].coord}
    checks["structure_and_animal_conflicts_fail_closed"] = (
        not any((job[1], job[2]) in conflicted
                and job[3][0] in {"BUILD_PASTURE", "BUILD_COOP", "PLACE"}
                for job in conflict_jobs)
        and conflict.audit["slot_structure_conflict"] >= 1
        and conflict.audit["slot_animal_conflict"] >= 1
        and conflict.audit["slot_finite_harvest_conflict"] >= 1
        and not any(job[3][0] == "HARVEST"
                    and (job[1], job[2]) == wrong_crop_slot.coord
                    for job in conflict_jobs))

    capped = module.build_executor(mode="fixed_wool")
    capped_animals, capped_crops = capped.active_slot_contract(0)
    active_coords = {slot.coord for slot in (*capped_animals, *capped_crops)}
    outside = [coord for coord in module._land_prefix(2) if coord not in active_coords]

    full_animal_grid = empty_grid()
    for coord in outside[:4]:
        set_tile(full_animal_grid, coord, animal("SHEEP"))
    full_animal_jobs = capped._jobs(
        0, 0, [[4, 4]], full_animal_grid, capped.goal(0), seeds,
        capped.goal(0))

    full_crop_grid = empty_grid()
    for coord in outside[:8]:
        set_tile(full_crop_grid, coord, plant("WHEAT"))
    for coord in outside[8:15]:
        set_tile(full_crop_grid, coord, plant("MELON"))
    full_crop_jobs = capped._jobs(
        0, 0, [[4, 4]], full_crop_grid, capped.goal(0), seeds,
        capped.goal(0))

    one_build_grid = empty_grid()
    for coord in outside[:3]:
        set_tile(one_build_grid, coord, animal("SHEEP"))
    one_build_jobs = capped._jobs(
        0, 0, [[4, 4]], one_build_grid, capped.goal(0), seeds,
        capped.goal(0))

    one_place_grid = empty_grid()
    for slot in capped_animals:
        set_tile(one_place_grid, slot.coord,
                 {"kind": "PASTURE", "animal": None})
    for coord in outside[:3]:
        set_tile(one_place_grid, coord, animal("SHEEP"))
    one_place_jobs = capped._jobs(
        0, 0, [[4, 4]], one_place_grid, capped.goal(0), seeds,
        capped.goal(0))

    one_plant_grid = empty_grid()
    for coord in outside[:7]:
        set_tile(one_plant_grid, coord, plant("WHEAT"))
    for coord in outside[7:14]:
        set_tile(one_plant_grid, coord, plant("MELON"))
    one_plant_jobs = capped._jobs(
        0, 0, [[4, 4]], one_plant_grid, capped.goal(0), seeds,
        capped.goal(0))
    checks["global_deficits_prevent_overbuild_overplant_overplace"] = (
        not any(job[3][0] in {"BUILD_PASTURE", "BUILD_COOP", "PLACE"}
                for job in full_animal_jobs)
        and not plant_jobs(full_crop_jobs)
        and sum(job[3][0].startswith("BUILD") for job in one_build_jobs) <= 1
        and sum(job[3][0] == "PLACE" for job in one_place_jobs) <= 1
        and len(plant_jobs(one_plant_jobs)) <= 1)
    return checks


def main() -> None:
    module = load(MAIN, "r24_candidate")
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
