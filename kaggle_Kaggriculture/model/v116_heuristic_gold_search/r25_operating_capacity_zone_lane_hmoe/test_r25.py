#!/usr/bin/env python3
"""Behavioral mechanism checks for R25; no match or Replay execution."""

from __future__ import annotations

import ast
from collections import Counter
import importlib.util
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
MAIN = HERE / "main.py"
R24_MAIN = HERE.parent / "r24_expert_deterministic_slot_contract_hmoe" / "main.py"


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
           fed: bool = True, cared: bool = True,
           fertilizer: bool = False, yield_units: int = 0) -> dict:
    return {"kind": structure, "animal": {"kind": kind},
            "fed_today": fed, "cared_today": cared,
            "yield_units": yield_units,
            "fertilizer_available": fertilizer}


def set_tile(grid, coord, value) -> None:
    grid[coord[1]][coord[0]] = value


def plant_jobs(jobs):
    return [job for job in jobs if job[3][0] == "PLANT"]


def core_slot(slot) -> tuple:
    if hasattr(slot, "animal_kind"):
        return (slot.coord, slot.structure_kind, slot.animal_kind,
                slot.activation_day, slot.activation_stage, slot.ordinal)
    return (slot.coord, slot.crop, slot.activation_stage, slot.ordinal)


def static_checks(module, r24) -> dict[str, bool]:
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
    r24_genomes = r24.compile_genomes(r24.DEFAULT_PARAMS)
    return {
        "independent_stdlib_candidate": (
            module.STRATEGY_PARENT is None and imports <= allowed
            and "r24_expert_deterministic_slot_contract_hmoe" not in source),
        "schema_r25": module.SCHEMA == "v116-r25-operating-capacity-zone-lane-hmoe-v1",
        "params_genomes_targets_unchanged": (
            module.DEFAULT_PARAMS_HASH == r24.DEFAULT_PARAMS_HASH
            and module_genomes == r24_genomes
            and all(module.compile_daily_goals(module_genomes[name])
                    == r24.compile_daily_goals(r24_genomes[name])
                    for name in module.EXPERT_NAMES)),
        "router_market_thresholds_unchanged": (
            all(getattr(module, key) == getattr(r24, key) for key in thresholds)
            and module.MARKET_PARAMS == r24.MARKET_PARAMS
            and module.DEFAULT_PARAMS == r24.DEFAULT_PARAMS
            and all(module.route_expert([shop]) == r24.route_expert([shop])
                    for shop in sorted(module.SHOP_PRODUCTS))),
        "no_runtime_old_model_or_intent_ledger": (
            "pending_intent_key" not in source and "intent_ledger" not in source.lower()),
    }


def parity_checks(module, r24) -> dict[str, bool]:
    left_contracts = module.compile_slot_contracts(
        module.compile_genomes(module.DEFAULT_PARAMS))
    right_contracts = r24.compile_slot_contracts(
        r24.compile_genomes(r24.DEFAULT_PARAMS))
    same_slots = all(
        [core_slot(slot) for slot in left_contracts[name].animal_slots]
        == [core_slot(slot) for slot in right_contracts[name].animal_slots]
        and [core_slot(slot) for slot in left_contracts[name].crop_slots]
        == [core_slot(slot) for slot in right_contracts[name].crop_slots]
        for name in module.EXPERT_NAMES)

    confirmation = []
    for candidate in (module, r24):
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
    for candidate in (module, r24):
        executor = candidate.build_executor(mode="fixed_root")
        grid = empty_grid(False)
        executor.tile_work[(1, 1)] = candidate.TileWork(
            (1, 1), None, ((2, ("PLANT", "WHEAT")),),
            "ordinary_plant", 4, "WHEAT")
        executor._sync_tile_work(
            9, grid, [(1, 1, 1, ("PLANT", "WHEAT"))])
        work = executor.tile_work[(1, 1)]
        frontier.append((work.ready_since, work.ready_ops))
    return {
        "r24_core_slot_contract_parity": same_slots,
        "r24_confirmation_chain_parity": confirmation[0] == confirmation[1],
        "r24_exact_frontier_parity": frontier[0] == frontier[1],
        "r24_market_price_parity": all(
            module.market_price(product, inventory)
            == r24.market_price(product, inventory)
            for product in module.PRODUCTS
            for inventory in (9000, 9999, 10000, 10001, 11000)),
    }


def mechanism_checks(module) -> dict[str, bool]:
    checks: dict[str, bool] = {}

    def raise_assets_without_wheat(executor, grid, day: int,
                                   protected: set[tuple[int, int]],
                                   target: int = 59) -> None:
        animals, crops = executor.active_slot_contract(day)
        occupied = set(protected)
        for slot in animals:
            if sum(module._counts(grid)[0].values()) \
                    + sum(module._counts(grid)[1].values()) >= target:
                return
            if slot.coord in occupied:
                continue
            set_tile(grid, slot.coord,
                     animal(slot.animal_kind, slot.structure_kind))
            occupied.add(slot.coord)
        for slot in crops:
            if sum(module._counts(grid)[0].values()) \
                    + sum(module._counts(grid)[1].values()) >= target:
                return
            if slot.coord in occupied or slot.crop == "WHEAT":
                continue
            set_tile(grid, slot.coord, plant(slot.crop, True, 0, day))
            occupied.add(slot.coord)
        all_contract = {slot.coord for slot in (*animals, *crops)}
        for y in range(10):
            for x in range(10):
                if sum(module._counts(grid)[0].values()) \
                        + sum(module._counts(grid)[1].values()) >= target:
                    return
                coord = (x, y)
                if coord in occupied or coord in all_contract:
                    continue
                set_tile(grid, coord, plant("TOMATO", True, 0, day))
                occupied.add(coord)

    capacity = module.build_executor(mode="fixed_wool")
    capacity_grid = empty_grid()
    goal0 = capacity.goal(0)
    seeds = {crop: 20 for crop in module.CROPS}
    units = [[4, 4]]
    active_animals, active_crops = capacity.active_slot_contract(0)
    for slot in active_animals:
        set_tile(capacity_grid, slot.coord,
                 animal(slot.animal_kind, slot.structure_kind))
    unloaded = capacity._jobs(0, 0, units, capacity_grid, goal0, seeds, goal0)
    unloaded_keys = [module._job_key(job) for job in plant_jobs(unloaded)]
    loaded_grid = empty_grid()
    for slot in active_animals:
        set_tile(loaded_grid, slot.coord,
                 animal(slot.animal_kind, slot.structure_kind))
    active_coords = {slot.coord for slot in (*active_animals, *active_crops)}
    far = sorted((coord for coord in module._land_prefix(2)
                  if coord not in active_coords),
                 key=lambda coord: (-module._dist((4, 4), coord), coord))
    for coord in far[:5]:
        set_tile(loaded_grid, coord, plant("TOMATO", watered=False))
    overloaded = capacity._jobs(0, 0, units, loaded_grid, goal0, seeds, goal0)
    overloaded_keys = [module._job_key(job) for job in plant_jobs(overloaded)]
    checks["stable_slot_prefix_overload_rejects_unload_accepts"] = (
        len(unloaded_keys) == 3 and len(overloaded_keys) < len(unloaded_keys)
        and overloaded_keys == unloaded_keys[:len(overloaded_keys)])

    animal_capacity = module.build_executor(mode="fixed_wool")
    animal_goal = animal_capacity.goal(0)
    animal_empty = empty_grid()
    ample_jobs = animal_capacity._jobs(
        0, 0, [[4, 4], [4, 4], [4, 4], [4, 4]],
        animal_empty, animal_goal, seeds, animal_goal)
    constrained_jobs = animal_capacity._jobs(
        0, 20, [[4, 4]], animal_empty, animal_goal, seeds, animal_goal)
    ample_build_keys = [module._job_key(job) for job in ample_jobs
                        if job[3][0].startswith("BUILD_")]
    constrained_build_keys = [module._job_key(job) for job in constrained_jobs
                              if job[3][0].startswith("BUILD_")]
    checks["animal_expansion_capacity_prefix_overload_unload"] = (
        len(ample_build_keys) == 4
        and len(constrained_build_keys) < len(ample_build_keys)
        and constrained_build_keys == ample_build_keys[:len(constrained_build_keys)])

    zero_capacity = module.build_executor(mode="fixed_wool")
    zero_goal = zero_capacity.goal(9)
    zero_jobs = zero_capacity._jobs(
        9, 23, [[4, 4]], empty_grid(), zero_goal, seeds, zero_goal)
    checks["zero_capacity_no_expansion_jobs"] = not any(
        job[3][0] in {"BUILD_PASTURE", "BUILD_COOP", "PLACE", "PLANT"}
        for job in zero_jobs)

    zone_ok = True
    for contract in capacity.slot_contracts.values():
        slots = (*contract.animal_slots, *contract.crop_slots)
        zone_ok &= len({slot.coord for slot in slots}) == len(slots)
        for zone in sorted({slot.service_zone for slot in slots}):
            zone_slots = [slot for slot in slots if slot.service_zone == zone]
            circuits = sorted(slot.circuit_ordinal for slot in zone_slots)
            lanes = sorted({slot.service_lane for slot in zone_slots})
            zone_ok &= (
                circuits == list(range(len(zone_slots)))
                and lanes == list(range(max(lanes) + 1))
                and all(slot.service_zone == module._quadrant(slot.coord)
                        for slot in zone_slots))
            for lane in lanes:
                lane_slots = sorted(
                    (slot for slot in zone_slots if slot.service_lane == lane),
                    key=lambda slot: slot.circuit_ordinal)
                zone_ok &= len(lane_slots) <= 5
                zone_ok &= all(
                    module._dist(left.coord, right.coord) == 1
                    for left, right in zip(lane_slots, lane_slots[1:]))
    checks["zone_lane_unique_and_continuous"] = zone_ok

    # The route proof must consume compiled lane/circuit metadata, not merely
    # expose it as inert dataclass fields.
    route_slots = sorted(
        (slot for slot in (*active_animals, *active_crops)
         if slot.service_zone == 0 and slot.service_lane == 0),
        key=lambda slot: slot.circuit_ordinal)
    route_jobs = [(2, slot.coord[0], slot.coord[1], ("WATER",))
                  for slot in route_slots[:3]]
    traversal = sum(module._dist(left.coord, right.coord)
                    for left, right in zip(route_slots[:3], route_slots[1:3]))
    expected_route = (
        min(module._dist((4, 4), route_slots[0].coord) + traversal
            + module._dist(route_slots[min(2, len(route_slots) - 1)].coord, (4, 4)),
            module._dist((4, 4), route_slots[min(2, len(route_slots) - 1)].coord)
            + traversal + module._dist(route_slots[0].coord, (4, 4)))
        + len(route_jobs))
    checks["capacity_uses_compiled_lane_route"] = (
        len(route_slots) >= 3
        and capacity._service_route_work(route_jobs, [(4, 4)], 0) == expected_route)

    route_proof = module.build_executor(mode="fixed_wool")
    proof_slot = next(slot for slot in route_proof.active_slot_contract(9)[1]
                      if slot.crop == "WHEAT")
    proof_frontier = [
        (2, 0, 0, ("WATER",)), (2, 9, 1, ("WATER",)),
        (2, proof_slot.coord[0], proof_slot.coord[1], ("PLANT", "WHEAT")),
        (2, proof_slot.coord[0], proof_slot.coord[1], ("WATER",)),
    ]
    checks["multi_lane_route_does_not_reuse_actor_start"] = (
        not route_proof._service_capacity_fits(
            proof_frontier, [proof_slot.coord], 4, 9))

    rollover = module.build_executor(mode="fixed_root")
    rollover_grid = empty_grid()
    rollover_grid[1][1] = animal("COW", fed=True, cared=False)
    rollover.tile_work[(1, 1)] = module.TileWork(
        (1, 1), 0, ((6, ("CARE",)),), "animal", 1, None, 0)
    rollover._assign(
        [[1, 2]], [{}], [(6, 1, 1, ("CARE",))],
        10, 1, {0}, 1, 25, rollover_grid, {})
    rollover_work = rollover.tile_work[(1, 1)]
    checks["owner_clears_at_day_boundary"] = (
        rollover_work.owner is None and rollover_work.owner_day is None
        and rollover.audit["owner_day_boundary_releases"] == 1)

    safe_owner = module.build_executor(mode="fixed_root")
    safe_grid = empty_grid()
    safe_grid[1][1] = animal("COW", fed=True, cared=False)
    safe_owner.tile_work[(1, 1)] = module.TileWork(
        (1, 1), 0, ((6, ("CARE",)),), "animal", 1, None, 0)
    safe_result = safe_owner._assign(
        [[1, 2], [1, 1]], [{}, {}], [(6, 1, 1, ("CARE",))],
        10, 1, set(), 0, 2, safe_grid, {})

    takeover = module.build_executor(mode="fixed_root")
    takeover_grid = empty_grid()
    takeover_grid[1][1] = animal("COW", fed=True, cared=False)
    takeover.tile_work[(1, 1)] = module.TileWork(
        (1, 1), 0, ((6, ("CARE",)),), "animal", 1, None, 0)
    takeover_result = takeover._assign(
        [[9, 9], [1, 1]], [{}, {}], [(6, 1, 1, ("CARE",))],
        22, 1, set(), 0, 2, takeover_grid, {})
    checks["deadline_safe_owner_holds_and_unsafe_owner_takeover"] = (
        0 in safe_result and 1 not in safe_result
        and 1 in takeover_result and takeover.tile_work[(1, 1)].owner == 1
        and takeover.audit["tile_bundle_owner_takeovers"] == 1)

    owner_risk = module.build_executor(mode="fixed_root")
    owner_risk_grid = empty_grid()
    owner_risk_grid[1][1] = animal("COW", fed=True, cared=False)
    owner_risk_grid[1][2] = animal("SHEEP", fed=False, cared=True)
    owner_risk.tile_work[(1, 1)] = module.TileWork(
        (1, 1), 0, ((6, ("CARE",)),), "animal", 1, None, 0)
    owner_risk.tile_work[(2, 1)] = module.TileWork(
        (2, 1), None, ((1, ("FEED",)),), "animal", 2)
    owner_risk_result = owner_risk._assign(
        [[1, 1], [9, 9]], [{"WHEAT": 1}, {}],
        [(6, 1, 1, ("CARE",)), (1, 2, 1, ("FEED",))],
        10, 1, set(), 0, 3, owner_risk_grid, {})
    checks["feed_risk_preempts_low_risk_owner"] = (
        owner_risk_result[0][3][0] == "FEED")

    nearest = module.build_executor(mode="fixed_root")
    nearest_grid = empty_grid()
    nearest_grid[1][1] = animal("COW", fed=True, cared=False)
    nearest_result = nearest._assign(
        [[1, 1], [9, 9]], [{}, {}], [(6, 1, 1, ("CARE",))],
        10, 1, set(), 0, 4, nearest_grid, {})
    checks["same_tile_actor_beats_far_actor"] = (
        set(nearest_result) == {0})

    full_edge = module.build_executor(mode="fixed_root")
    edge_grid = empty_grid()
    edge_grid[1][1] = animal("COW", fed=False, cared=True)
    edge_grid[8][8] = plant("TOMATO", watered=False)
    full_edge.tile_work[(8, 8)] = module.TileWork(
        (8, 8), None, ((2, ("WATER",)),), "ongoing_crop", 100)
    full_edge.tile_work[(1, 1)] = module.TileWork(
        (1, 1), None, ((1, ("FEED",)),), "animal", 1)
    full_result = full_edge._assign(
        [[8, 8], [1, 1]], [{}, {"WHEAT": 1}],
        [(2, 8, 8, ("WATER",)), (1, 1, 1, ("FEED",))],
        10, 1, set(), 0, 101, edge_grid, {})
    checks["full_edge_cost_and_feasibility_assigns_complete_pair"] = (
        len(full_result) == 2
        and full_result[0][3][0] == "WATER"
        and full_result[1][3][0] == "FEED"
        and full_edge.audit["scheduler_full_edges_evaluated"] >= 2)

    maximum = module.build_executor(mode="fixed_root")
    maximum_grid = empty_grid()
    maximum_grid[0][0] = {"kind": "PASTURE", "animal": None}
    maximum_grid[0][2] = {"kind": "PASTURE", "animal": None}
    maximum_jobs = [(3, 2, 0, ("PLACE", "COW")),
                    (3, 0, 0, ("PLACE", "SHEEP"))]
    maximum_result = maximum._assign(
        [[0, 0], [2, 0]], [{"COW": 1, "SHEEP": 1}, {"COW": 1}],
        maximum_jobs, 10, 1, set(), 0, 5, maximum_grid, {})
    checks["all_edge_matching_maximizes_cardinality"] = (
        len(maximum_result) == 2
        and maximum_result[0][3] == ("PLACE", "SHEEP")
        and maximum_result[1][3] == ("PLACE", "COW"))

    runtime = module.build_executor(mode="fixed_root")
    runtime_grid = empty_grid()
    coords = [(x, y) for y in range(10) for x in range(10)]
    runtime_jobs = []
    runtime_crops = ("WHEAT", "CARROT", "MELON")
    for offset, coord in enumerate(coords[:14]):
        runtime_jobs.append((2, coord[0], coord[1],
                             ("PLANT", runtime_crops[offset % 3])))
    for coord in coords[14:59]:
        set_tile(runtime_grid, coord, plant("TOMATO", watered=False))
        runtime_jobs.append((2, coord[0], coord[1], ("WATER",)))
    for coord in coords[59:69]:
        set_tile(runtime_grid, coord, animal("COW", fed=True, cared=False))
        runtime_jobs.append((6, coord[0], coord[1], ("CARE",)))
    runtime_units = [[4 + (index % 2), 4 + ((index // 2) % 2)]
                     for index in range(11)]
    started = time.perf_counter()
    runtime_result = runtime._assign(
        runtime_units, [{} for _ in runtime_units], runtime_jobs,
        0, 3, set(), 0, 6, runtime_grid,
        {"WHEAT": 5, "CARROT": 5, "MELON": 4})
    elapsed = time.perf_counter() - started
    checks["polynomial_frontier_runtime_under_100ms"] = (
        len(runtime_result) == 11 and elapsed < 0.100)

    no_age = module.build_executor(mode="fixed_root")
    age_grid = empty_grid()
    age_grid[1][1] = animal("COW", fed=True, cared=False)
    age_grid[1][2] = plant("TOMATO", watered=False)
    no_age.tile_work[(1, 1)] = module.TileWork(
        (1, 1), None, ((6, ("CARE",)),), "animal", 0)
    no_age.tile_work[(2, 1)] = module.TileWork(
        (2, 1), None, ((0, ("WATER",)),), "ongoing_crop", 100)
    age_result = no_age._assign(
        [[1, 1]], [{}],
        [(6, 1, 1, ("CARE",)), (0, 2, 1, ("WATER",))],
        10, 1, set(), 0, 101, age_grid, {})
    checks["current_observation_risk_not_permanent_ready_since"] = (
        age_result[0][3][0] == "WATER")

    feeder = module.build_executor(mode="fixed_root")
    feed_jobs = [(1, index, 0, ("FEED",)) for index in range(5)]
    feed_override = feeder._feeder_overrides(
        feed_jobs, [[4, 4], [5, 4]], [{"WHEAT": 2}, {}], {"WHEAT": 10})
    checks["feeder_reserves_global_unfed_minus_carried_gap"] = (
        feed_override == {1: ["PICKUP", "WHEAT", 3]}
        and feeder.audit["feeder_reserved_wheat_units"] == 3)

    finite = module.build_executor(mode="fixed_grain_egg")
    finite_grid = empty_grid()
    _finite_animals, finite_crops = finite.active_slot_contract(8)
    finite_slot = next(slot for slot in finite_crops if slot.crop == "WHEAT")
    set_tile(finite_grid, finite_slot.coord,
             plant("WHEAT", True, 6, 0))
    finite_units = [[finite_slot.coord[0], finite_slot.coord[1]]]
    finite_seeds = {crop: (5 if crop == "WHEAT" else 0) for crop in module.CROPS}
    finite_jobs = finite._jobs(
        8, 0, finite_units, finite_grid, finite.goal(8),
        finite_seeds, finite.goal(8))
    finite._sync_tile_work(100, finite_grid, finite_jobs)
    finite._mark_tile_work_emitted(100, finite_slot.coord, ["HARVEST"])
    set_tile(finite_grid, finite_slot.coord, None)
    after_harvest = finite._jobs(
        8, 1, finite_units, finite_grid, finite.goal(8),
        finite_seeds, finite.goal(8))
    finite._sync_tile_work(101, finite_grid, after_harvest)
    replacement = finite._head_job(finite.tile_work[finite_slot.coord])
    finite._mark_tile_work_emitted(101, finite_slot.coord,
                                   ["PLANT", "WHEAT"])
    set_tile(finite_grid, finite_slot.coord,
             plant("WHEAT", False, 0, 8))
    finite._sync_tile_work(102, finite_grid, [])
    water = finite._head_job(finite.tile_work[finite_slot.coord])
    checks["finite_original_coordinate_chain_preserved"] = (
        replacement is not None and replacement[1:3] == finite_slot.coord
        and replacement[3] == ("PLANT", "WHEAT")
        and water is not None and water[1:3] == finite_slot.coord
        and water[3] == ("WATER",))

    reserve = module.build_executor(mode="fixed_grain_egg")
    reserve_grid = empty_grid()
    _reserve_animals, reserve_crops = reserve.active_slot_contract(27)
    reserve_slot = next(slot for slot in reserve_crops if slot.crop == "WHEAT")
    set_tile(reserve_grid, reserve_slot.coord, plant("WHEAT", True, 6, 0))
    raise_assets_without_wheat(reserve, reserve_grid, 27, {reserve_slot.coord})
    reserve_jobs = reserve._jobs(
        27, 0, [[reserve_slot.coord[0], reserve_slot.coord[1]]],
        reserve_grid, reserve.goal(27),
        {crop: (1 if crop == "WHEAT" else 0) for crop in module.CROPS},
        reserve.goal(27))
    checks["finite_seed_reserved_before_ordinary_plant"] = (
        any(job[3][0] == "HARVEST" for job in reserve_jobs)
        and not any(job[3] == ("PLANT", "WHEAT") for job in reserve_jobs))

    no_seed = module.build_executor(mode="fixed_grain_egg")
    no_seed_grid = empty_grid()
    no_seed_slot = next(slot for slot in no_seed.active_slot_contract(4)[1]
                        if slot.crop == "WHEAT")
    set_tile(no_seed_grid, no_seed_slot.coord, plant("WHEAT", True, 6, 0))
    no_seed_jobs = no_seed._jobs(
        4, 0, [[no_seed_slot.coord[0], no_seed_slot.coord[1]]],
        no_seed_grid, no_seed.goal(4), {crop: 0 for crop in module.CROPS},
        no_seed.goal(4))
    checks["finite_harvest_without_seed_is_withheld_all_days"] = (
        not any(job[3][0] == "HARVEST" for job in no_seed_jobs)
        and no_seed.audit["finite_seed_reserve_withheld"] >= 1)

    late = module.build_executor(mode="fixed_grain_egg")
    late_grid = empty_grid()
    late_slot = next(slot for slot in late.active_slot_contract(27)[1]
                     if slot.crop == "WHEAT")
    set_tile(late_grid, late_slot.coord, plant("WHEAT", True, 6, 0))
    raise_assets_without_wheat(late, late_grid, 27, {late_slot.coord})
    late_jobs = late._jobs(
        27, 21, [[late_slot.coord[0], late_slot.coord[1]]],
        late_grid, late.goal(27), {crop: 5 for crop in module.CROPS},
        late.goal(27))
    checks["late_finite_closure_three_action_reserve"] = (
        not any(job[3][0] == "HARVEST" for job in late_jobs)
        and late.audit["finite_closure_capacity_withheld"] >= 1)

    shared = module.build_executor(mode="fixed_grain_egg")
    shared_grid = empty_grid()
    wheat_slots = [slot for slot in shared.active_slot_contract(27)[1]
                   if slot.crop == "WHEAT"]
    first_wheat, second_wheat = wheat_slots[:2]
    set_tile(shared_grid, first_wheat.coord, plant("WHEAT", True, 6, 0))
    raise_assets_without_wheat(shared, shared_grid, 27, {first_wheat.coord,
                                                         second_wheat.coord})
    shared_jobs = shared._jobs(
        27, 9, [[first_wheat.coord[0], first_wheat.coord[1]]],
        shared_grid, shared.goal(27),
        {crop: (2 if crop == "WHEAT" else 0) for crop in module.CROPS},
        shared.goal(27))
    checks["finite_and_ordinary_share_one_capacity_ledger"] = (
        any(job[3][0] == "HARVEST" and job[1:3] == first_wheat.coord
            for job in shared_jobs)
        and not any(job[3] == ("PLANT", "WHEAT") for job in shared_jobs)
        and shared.audit["plant_capacity_prefix_withheld"] >= 1)

    blocked = module.build_executor(mode="fixed_wool")
    blocked_grid = empty_grid()
    first_crop_slot = min(blocked.active_slot_contract(0)[1],
                          key=lambda slot: slot.ordinal)
    set_tile(blocked_grid, first_crop_slot.coord, {"kind": "WEED"})
    blocked_jobs = blocked._jobs(
        0, 0, [[4, 4]], blocked_grid, blocked.goal(0),
        {crop: 20 for crop in module.CROPS}, blocked.goal(0))
    checks["fixed_slot_prefix_stops_at_first_conflict"] = (
        not plant_jobs(blocked_jobs)
        and blocked.audit["slot_crop_prefix_conflict_blocked"] == 1)

    terminal = module.build_executor(mode="fixed_wool")
    terminal_grid = empty_grid()
    terminal_animals, terminal_crops = terminal.active_slot_contract(29)
    for slot in terminal_crops:
        facts = module.CROPS[slot.crop]
        set_tile(terminal_grid, slot.coord,
                 plant(slot.crop, True, int(facts["max_yield"]), 0))
    set_tile(terminal_grid, terminal_animals[0].coord,
             animal(terminal_animals[0].animal_kind,
                    terminal_animals[0].structure_kind))
    many_units = [[4, 4] for _ in range(12)]
    terminal_jobs = terminal._jobs(
        29, 0, many_units, terminal_grid, terminal.goal(29),
        {crop: 20 for crop in module.CROPS}, terminal.goal(29))
    finite_harvests = [job for job in terminal_jobs
                       if job[3][0] == "HARVEST"
                       and isinstance(terminal_grid[job[2]][job[1]], dict)
                       and terminal_grid[job[2]][job[1]].get("crop")
                       in module.NON_ONGOING]
    checks["terminal_concurrent_finite_floor_and_closure_reserved"] = (
        len(finite_harvests) == 2
        and 60 - len(finite_harvests) >= module.TERMINAL_ASSET_FLOOR
        and terminal.audit["terminal_finite_floor_withheld"] > 0)

    safe_grid = empty_grid()
    safe_grid[1][1] = plant("WHEAT", False, 2)
    safe_grid[1][2] = animal("COW", fed=False, cared=False,
                             fertilizer=True, yield_units=2)
    safe_grid[1][3] = {"kind": "WEED"}
    safe_grid[1][4] = {"kind": "PASTURE", "animal": None}
    safe_grid[0][1] = "LOCKED"
    safe = module.ShopRouterExecutor._safe_unit_verb
    valid_typed = (
        safe(["WATER"], (1, 1), safe_grid, {}, {})
        and safe(["FEED"], (2, 1), safe_grid, {"WHEAT": 1}, {})
        and safe(["CARE"], (2, 1), safe_grid, {}, {})
        and safe(["HARVEST"], (1, 1), safe_grid, {}, {})
        and safe(["COLLECT_FERTILIZER"], (2, 1), safe_grid, {}, {})
        and safe(["DIG"], (3, 1), safe_grid, {}, {})
        and safe(["FERTILIZE"], (1, 1), safe_grid, {"FERTILIZER": 1}, {})
        and safe(["PLACE", "COW"], (4, 1), safe_grid, {"COW": 1}, {})
        and safe(["PLANT", "WHEAT"], (0, 0), safe_grid, {}, {"WHEAT": 1})
        and safe(["BUILD_PASTURE"], (0, 0), safe_grid, {}, {})
        and safe(["PICKUP", "WHEAT", 3], (4, 4), safe_grid, {}, {}, {"WHEAT": 3})
        and safe(["DROP"], (4, 4), safe_grid, {"WHEAT": 1}, {}, {})
        and safe(["PASS"], (0, 0), safe_grid, {}, {})
        and safe(["SOUTH"], (0, 0), safe_grid, {}, {}))
    invalid_typed = (
        not safe(["WATER"], (0, 0), safe_grid, {}, {})
        and not safe(["FEED"], (2, 1), safe_grid, {}, {})
        and not safe(["DIG"], (0, 0), safe_grid, {}, {})
        and not safe(["FERTILIZE"], (1, 1), safe_grid, {}, {})
        and not safe(["PICKUP", "WHEAT", "3"], (4, 4), safe_grid, {}, {}, {"WHEAT": 3})
        and not safe(["PICKUP", "WHEAT", 3], (0, 0), safe_grid, {}, {}, {"WHEAT": 3})
        and not safe(["CARE", "junk"], (2, 1), safe_grid, {}, {})
        and not safe(["PLANT", "ALIEN", "junk"], (0, 0), safe_grid, {}, {})
        and not safe(["DROP", "junk"], (4, 4), safe_grid, {}, {}, {})
        and not safe(["PICKUP", "ALIEN", 999], (4, 4), safe_grid, {}, {}, {"ALIEN": 999})
        and not safe(["PICKUP", "WHEAT", 4], (4, 4), safe_grid, {}, {}, {"WHEAT": 3})
        and not safe(["NORTH"], (1, 1), safe_grid, {}, {})
        and not safe(["UNKNOWN"], (0, 0), safe_grid, {}, {}))
    checks["typed_actions_complete_fail_closed"] = valid_typed and invalid_typed
    return checks


def main() -> None:
    module = load(MAIN, "r25_candidate")
    r24 = load(R24_MAIN, "r24_reference")
    result = {"schema": module.SCHEMA,
              "static": static_checks(module, r24),
              "parity": parity_checks(module, r24),
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
