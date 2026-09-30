#!/usr/bin/env python3
"""Behavioral mechanism checks for R26; no match or Replay execution."""
from __future__ import annotations
import ast
from collections import Counter
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
MAIN = HERE / "main.py"
R25_MAIN = HERE.parent / "r25_operating_capacity_zone_lane_hmoe" / "main.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def empty_grid():
    return [[None for _x in range(10)] for _y in range(10)]


def plant(name="WHEAT", watered=True, yield_units=0, planted_day=0,
          max_lifespan_step=-1):
    return {"kind": "PLANT", "crop": name, "watered_today": watered,
            "consecutive_unwatered": 0, "yield_units": yield_units,
            "planted_day": planted_day,
            "max_lifespan_step": max_lifespan_step}


def animal(kind="SHEEP", structure="PASTURE", fed=True, cared=True,
           fertilizer=False, yield_units=0):
    return {"kind": structure, "animal": {"kind": kind},
            "fed_today": fed, "cared_today": cared,
            "fertilizer_available": fertilizer, "yield_units": yield_units}


def set_tile(grid, coord, value):
    grid[coord[1]][coord[0]] = value


def core_slot(slot):
    if hasattr(slot, "animal_kind"):
        return (slot.coord, slot.structure_kind, slot.animal_kind,
                slot.activation_day, slot.activation_stage, slot.ordinal,
                slot.service_zone, slot.service_lane, slot.circuit_ordinal)
    return (slot.coord, slot.crop, slot.activation_stage, slot.ordinal,
            slot.service_zone, slot.service_lane, slot.circuit_ordinal)


def static_checks(module):
    source = MAIN.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    allowed = {"__future__", "collections", "copy", "dataclasses", "hashlib",
               "json", "math", "os", "pathlib", "typing"}
    return {
        "schema_r26": module.SCHEMA ==
            "v116-r26-persistent-feasible-option-graph-hmoe-v1",
        "independent_stdlib": module.STRATEGY_PARENT is None and imports <= allowed,
        "no_runtime_old_model_import": (
            "r25_operating_capacity_zone_lane_hmoe" not in source
            and "r24_expert_deterministic_slot_contract_hmoe" not in source),
        "no_replay_dependency": "replay" not in source.lower(),
        "five_modes_and_experts": len(module.EXPERT_NAMES) == 5 and len(module.MODES) == 6,
    }


def parity_checks(module, r25):
    lg = module.compile_genomes(module.DEFAULT_PARAMS)
    rg = r25.compile_genomes(r25.DEFAULT_PARAMS)
    lc = module.compile_slot_contracts(lg)
    rc = r25.compile_slot_contracts(rg)
    thresholds = ("PLANT_CUTOFF_HOUR", "MAX_PARALLEL_PLANT", "DELIVERY_BATCH",
                  "FINANCE_DROP_FLOOR", "TERMINAL_ASSET_FLOOR", "LABOR_HAND_CAP",
                  "SETTLEMENT_PURCHASE_CUTOFF_STEP", "TOUR_MAX_STEPS",
                  "GROWTH_DEBT_START_DAY")
    return {
        "r25_params_router_market_parity": (
            module.DEFAULT_PARAMS == r25.DEFAULT_PARAMS
            and module.DEFAULT_PARAMS_HASH == r25.DEFAULT_PARAMS_HASH
            and module.MARKET_PARAMS == r25.MARKET_PARAMS
            and all(module.route_expert([shop]) == r25.route_expert([shop])
                    for shop in module.SHOP_PRODUCTS)),
        "r25_genome_goal_parity": (
            lg == rg and all(module.compile_daily_goals(lg[name])
                             == r25.compile_daily_goals(rg[name])
                             for name in module.EXPERT_NAMES)),
        "r25_slot_contract_parity": all(
            [core_slot(s) for s in lc[name].animal_slots]
            == [core_slot(s) for s in rc[name].animal_slots]
            and [core_slot(s) for s in lc[name].crop_slots]
            == [core_slot(s) for s in rc[name].crop_slots]
            for name in module.EXPERT_NAMES),
        "r25_threshold_parity": all(getattr(module, k) == getattr(r25, k)
                                    for k in thresholds),
        "r25_market_price_parity": all(
            module.market_price(p, inv) == r25.market_price(p, inv)
            for p in module.PRODUCTS for inv in (9000, 9999, 10000, 10001, 11000)),
    }


def fill_to_assets(module, executor, grid, day, protected, target=58):
    occupied = set(protected)
    animals, crops = executor.active_slot_contract(day)
    for slot in animals:
        if sum(map(sum, (module._counts(grid)[0].values(),
                         module._counts(grid)[1].values()))) >= target:
            return
        if slot.coord not in occupied:
            set_tile(grid, slot.coord, animal(slot.animal_kind, slot.structure_kind))
            occupied.add(slot.coord)
    for slot in crops:
        if sum(map(sum, (module._counts(grid)[0].values(),
                         module._counts(grid)[1].values()))) >= target:
            return
        if slot.coord not in occupied:
            set_tile(grid, slot.coord, plant(slot.crop, True, 0, day, -1))
            occupied.add(slot.coord)


def mechanism_checks(module):
    checks = {}
    seeds1 = {crop: (1 if crop == "WHEAT" else 0) for crop in module.CROPS}

    persistent = module.build_executor(mode="fixed_grain_egg")
    persistent.day = 8
    grid = empty_grid()
    wheat_slots = [s for s in persistent.active_slot_contract(8)[1] if s.crop == "WHEAT"]
    source, other = wheat_slots[:2]
    set_tile(grid, source.coord, plant("WHEAT", True, 6, 0, 240))
    jobs0 = persistent._jobs(8, 0, [[*source.coord]], grid,
                             persistent.goal(8), seeds1, persistent.goal(8))
    a0 = persistent._assign([[*source.coord]], [{}], jobs0, 0, 2, set(),
                            8, 192, grid, seeds1)
    persistent._mark_tile_work_emitted(192, source.coord, ["HARVEST"])
    set_tile(grid, source.coord, None)
    jobs1 = persistent._jobs(8, 1, [None, [*other.coord]], grid,
                             persistent.goal(8), seeds1, persistent.goal(8))
    a1 = persistent._assign([None, [*other.coord]], [{}, {}], jobs1, 1, 2,
                            set(), 8, 193, grid, seeds1)
    persistent._mark_tile_work_emitted(193, source.coord, ["PLANT", "WHEAT"])
    set_tile(grid, source.coord, plant("WHEAT", False, 1, 8, 312))
    jobs2 = persistent._jobs(8, 2, [None, [*source.coord]], grid,
                             persistent.goal(8), seeds1, persistent.goal(8))
    a2 = persistent._assign([None, [*source.coord]], [{}, {}], jobs2, 2, 2,
                            set(), 8, 194, grid, seeds1)
    checks["replacement_two_tiles_owner_unavailable_three_ticks"] = (
        a0[0][3] == ("HARVEST",) and a1[1][1:3] == source.coord
        and a1[1][3] == ("PLANT", "WHEAT")
        and a2[1][1:3] == source.coord and a2[1][3] == ("WATER",)
        and not any(j[1:3] == other.coord and j[3][0] == "PLANT" for j in jobs1))
    checks["seed_reservation_cross_tick_exclusive"] = (
        persistent.audit["persistent_seed_reserved"] == 1
        and source.coord not in persistent.seed_reservations
        and persistent.audit["persistent_seed_released_plant_success"] == 1)

    idem = module.build_executor(mode="fixed_grain_egg")
    idem.day = 8
    ig = empty_grid()
    slot = next(s for s in idem.active_slot_contract(8)[1] if s.crop == "WHEAT")
    set_tile(ig, slot.coord, plant("WHEAT", True, 6, 0, 240))
    ij = idem._jobs(8, 0, [[*slot.coord]], ig, idem.goal(8), seeds1, idem.goal(8))
    idem._assign([[*slot.coord]], [{}], ij, 0, 2, set(), 8, 192, ig, seeds1)
    before = (len(idem.tile_work), dict(idem.seed_reservations),
              idem.audit["persistent_seed_reserved"])
    idem._assign([[*slot.coord]], [{}], ij, 0, 2, set(), 8, 192, ig, seeds1)
    after = (len(idem.tile_work), dict(idem.seed_reservations),
             idem.audit["persistent_seed_reserved"])
    checks["same_observation_idempotent"] = before == after

    row = [[None, "LOCKED", None]]
    drow = [[None, {"kind": "LOCKED"}, None]]
    locked_cross = empty_grid()
    center = (4, 4)
    for coord, tile in (((4, 3), "LOCKED"), ((4, 5), {"kind": "LOCKED"}),
                        ((3, 4), "LOCKED"), ((5, 4), {"kind": "LOCKED"})):
        set_tile(locked_cross, coord, tile)
    checks["bfs_locked_in_bounds_legal"] = (
        module.ShopRouterExecutor._bfs_first_step(row, (0, 0), (2, 0)) == (2, ["EAST"])
        and module.ShopRouterExecutor._bfs_first_step(drow, (0, 0), (2, 0)) == (2, ["EAST"])
        and all(module.ShopRouterExecutor._safe_unit_verb([verb], center,
                                                          locked_cross, {}, {})
                for verb in ("NORTH", "SOUTH", "WEST", "EAST")))
    checks["movement_out_of_bounds_rejected"] = (
        not module.ShopRouterExecutor._safe_unit_verb(["WEST"], (0, 0), row, {}, {})
        and module.ShopRouterExecutor._bfs_first_step(row, (0, 0), (3, 0)) is None)
    pe = module.build_executor(mode="fixed_root")
    pg = [[None, "LOCKED", plant("TOMATO", False)]]
    pr = pe._assign([[0, 0]], [{}], [(0, 2, 0, ("WATER",))], 10, 1,
                    set(), 0, 10, pg, {})
    checks["mcmf_bfs_first_step_no_invalid_move"] = (
        pr[0][3] == ("WATER",) and pe._assigned_first_steps[0] == ["EAST"]
        and module.ShopRouterExecutor._safe_unit_verb(["EAST"], (0, 0), pg, {}, {}))
    ne = module.build_executor(mode="fixed_root")
    checks["out_of_grid_target_has_no_edge"] = ne._assign(
        [[0, 0]], [{}], [(4, 12, 0, ("BUILD_PASTURE",))], 10, 1,
        set(), 0, 10, empty_grid(), {}) == {}

    lanes = module.build_executor(mode="fixed_wool")
    lg = empty_grid()
    cs = lanes.active_slot_contract(9)[1]
    by_lane = {}
    for s in cs:
        by_lane.setdefault((s.service_zone, s.service_lane), []).append(s)
    keys = [k for k, v in sorted(by_lane.items()) if v]
    blocked = sorted(by_lane[keys[0]], key=lambda s: s.circuit_ordinal)[0]
    opened = sorted(by_lane[keys[1]], key=lambda s: s.circuit_ordinal)[0]
    set_tile(lg, blocked.coord, {"kind": "WEED"})
    many_seeds = {crop: 20 for crop in module.CROPS}
    lj = lanes._jobs(9, 0, [[4, 4]], lg, lanes.goal(9), many_seeds, lanes.goal(9))
    checks["lane_a_blocked_lane_b_progresses"] = (
        any(j[1:3] == blocked.coord and j[3][0] == "DIG" for j in lj)
        and any(j[1:3] == opened.coord and j[3][0] == "PLANT" for j in lj))
    checks["ordinary_three_parallel_without_global_prefix"] = (
        len([j for j in lj if j[3][0] == "PLANT"]) == module.MAX_PARALLEL_PLANT)

    weed = module.build_executor(mode="fixed_wool")
    weed.day = 9
    wg = empty_grid()
    weed_slots = weed.active_slot_contract(9)[1]
    weed_lanes = {}
    for candidate in weed_slots:
        weed_lanes.setdefault((candidate.service_zone, candidate.service_lane), []).append(candidate)
    ws = sorted(next(iter(sorted(weed_lanes.items())))[1],
                key=lambda s: s.circuit_ordinal)[0]
    set_tile(wg, ws.coord, {"kind": "WEED"})
    weed_seeds = {crop: (1 if crop == ws.crop else 0) for crop in module.CROPS}
    wj = weed._jobs(9, 0, [[*ws.coord]], wg, weed.goal(9), weed_seeds, weed.goal(9))
    wa0 = weed._assign([[*ws.coord]], [{}], wj, 0, 2, set(), 9, 216, wg, weed_seeds)
    weed._mark_tile_work_emitted(216, ws.coord, ["DIG"])
    set_tile(wg, ws.coord, None)
    wa1 = weed._assign([[*ws.coord]], [{}], [], 1, 2, set(), 9, 217, wg, weed_seeds)
    checks["weed_dependency_dig_then_same_slot_plant"] = (
        wa0[0][3] == ("DIG",) and wa1[0][1:3] == ws.coord
        and wa1[0][3] == ("PLANT", ws.crop)
        and weed.seed_reservations[ws.coord] == ws.crop)
    nw = module.build_executor(mode="fixed_wool")
    nwg = empty_grid(); set_tile(nwg, ws.coord, {"kind": "WEED"})
    nwj = nw._jobs(9, 0, [[*ws.coord]], nwg, nw.goal(9),
                   {c: 0 for c in module.CROPS}, nw.goal(9))
    checks["weed_destructive_head_requires_seed"] = not any(
        j[1:3] == ws.coord and j[3][0] == "DIG" for j in nwj)

    species = module.build_executor(mode="fixed_wool")
    species.day = 9
    sg = empty_grid()
    animal_slots = species.active_slot_contract(9)[0]
    cow = next(s for s in animal_slots if s.animal_kind == "COW")
    bj = species._jobs(9, 0, [[*cow.coord]], sg, species.goal(9), many_seeds,
                       species.goal(9))
    build = next(j for j in bj if j[1:3] == cow.coord and j[3][0] == "BUILD_PASTURE")
    species._assign([[*cow.coord]], [{}], bj, 0, 3, set(), 9, 216, sg, many_seeds)
    species._mark_tile_work_emitted(216, cow.coord, ["BUILD_PASTURE"])
    set_tile(sg, cow.coord, {"kind": "PASTURE"})
    off = next(c for c in module._land_prefix(2)
               if c not in {s.coord for s in (*animal_slots, *cs)})
    set_tile(sg, off, animal("COW"))
    pa = species._assign([[*cow.coord]], [{"COW": 1}], [], 1, 3, set(),
                         9, 217, sg, many_seeds)
    checks["build_option_species_binding_survives_external_animal"] = (
        build[3] == ("BUILD_PASTURE",) and pa[0][3] == ("PLACE", "COW")
        and species.tile_work[cow.coord].species == "COW")

    coupling = module.build_executor(mode="fixed_wool")
    cg = empty_grid()
    ca, cc = coupling.active_slot_contract(9)
    cow_target = sum(s.animal_kind == "COW" for s in ca)
    free_coords = [c for c in module._land_prefix(2)
                   if c not in {s.coord for s in (*ca, *cc)}]
    for c in free_coords[:cow_target]: set_tile(cg, c, animal("COW"))
    cj = coupling._jobs(9, 0, [[4, 4]], cg, coupling.goal(9), many_seeds,
                        coupling.goal(9))
    cows = {s.coord for s in ca if s.animal_kind == "COW"}
    sheep = {s.coord for s in ca if s.animal_kind == "SHEEP"}
    checks["offcontract_cow_does_not_create_unbound_pasture"] = (
        not any(j[1:3] in cows and j[3][0] == "BUILD_PASTURE" for j in cj)
        and any(j[1:3] in sheep and j[3][0] == "BUILD_PASTURE" for j in cj))

    feeder = module.build_executor(mode="fixed_root")
    fj = [(1, 5, 4, ("FEED",))]
    checks["hour22_pickup_move_feed_rejected"] = feeder._feeder_overrides(
        fj, [[4, 4]], [{}], {"WHEAT": 1}, hour=22) == {}
    checks["hour22_direct_carried_feed_offsets_gap"] = feeder._feeder_overrides(
        fj, [[5, 4]], [{"WHEAT": 1}], {"WHEAT": 1}, hour=22) == {}
    parallel = feeder._feeder_overrides(
        [(1, 5, 4, ("FEED",)), (1, 4, 5, ("FEED",))],
        [[4, 4], [5, 5]], [{}, {}], {"WHEAT": 2}, hour=21)
    checks["parallel_feeder_pickup_reservations"] = (
        len(parallel) == 2 and all(v == ["PICKUP", "WHEAT", 1]
                                   for v in parallel.values()))
    far_carrier = feeder._feeder_overrides(
        fj, [[9, 9], [4, 4]], [{"WHEAT": 1}, {}], {"WHEAT": 1}, hour=21)
    checks["unreachable_carried_wheat_does_not_offset_pickup"] = (
        far_carrier == {1: ["PICKUP", "WHEAT", 1]})

    working = module.build_executor(mode="fixed_wool")
    wjobs = working._jobs(9, 23, [[4, 4]], empty_grid(), working.goal(9),
                          many_seeds, working.goal(9))
    checks["current_frontier_work_conserving_hour23"] = any(
        j[3][0] in {"BUILD_PASTURE", "BUILD_COOP"} for j in wjobs)

    exp = module.build_executor(mode="fixed_grain_egg")
    eg = empty_grid()
    es = next(s for s in exp.active_slot_contract(28)[1] if s.crop == "WHEAT")
    set_tile(eg, es.coord, plant("WHEAT", True, 1, 0, 696))
    fill_to_assets(module, exp, eg, 28, {es.coord}, 58)
    e_seeds = {c: (2 if c == "WHEAT" else 0) for c in module.CROPS}
    ej = exp._jobs(28, 21, [[*es.coord]], eg, exp.goal(28), e_seeds, exp.goal(28))
    late = exp._jobs(28, 22, [[*es.coord]], eg, exp.goal(28), e_seeds, exp.goal(28))
    checks["known_expiry_bypasses_terminal_floor"] = (
        any(j[1:3] == es.coord and j[3][0] == "HARVEST" for j in ej)
        and exp.audit["terminal_expiry_floor_bypass"] >= 1)
    checks["expiry_chain_one_step_short_withheld"] = not any(
        j[1:3] == es.coord and j[3][0] == "HARVEST" for j in late)
    unk = module.build_executor(mode="fixed_grain_egg")
    ug = [row[:] for row in eg]
    set_tile(ug, es.coord, plant("WHEAT", True, 6, 0, -1))
    uj = unk._jobs(28, 0, [[*es.coord]], ug, unk.goal(28), e_seeds, unk.goal(28))
    checks["unknown_expiry_keeps_floor"] = not any(
        j[1:3] == es.coord and j[3][0] == "HARVEST" for j in uj)

    hire = module.build_executor(mode="fixed_grain_egg")
    hg = empty_grid()
    hs = [s for s in hire.active_slot_contract(29)[1] if s.crop == "WHEAT"][:2]
    for s in hs: set_tile(hg, s.coord, plant("WHEAT", True, 1, 0, 702))
    farm = {"farmer": list(hs[0].coord), "hands": [], "hires_today": 0,
            "money": 1000}
    before = hire._terminal_closure_cardinality(
        696, hg, {"WHEAT": 2}, [(hs[0].coord, 696)])
    occ = Counter({hs[0].coord: 1})
    spawn = min(module.SHED_TILES,
                key=lambda c: (occ[c], module.SHED_TILES.index(c)))
    after = hire._terminal_closure_cardinality(
        696, hg, {"WHEAT": 2}, [(hs[0].coord, 696), (spawn, 697)])
    checks["step696_minimal_hire_strictly_improves_closure"] = (
        before == 1 and after == 2 and hire._safe_terminal_hire(
            696, farm, hg, {"WHEAT": 2}, 1000, 100)
        and len(hs) - after == 0)
    projected = {product: 0 for product in module.PRODUCTS}
    market_orders = hire._market(
        {"step": 696, "day": 29, "hour": 0,
         "market": {"prices": {}, "inventory": {}}},
        farm, hg, hire.goal(29), {"WHEAT": 2}, projected, [{}],
        Counter(), Counter())
    checks["step696_market_only_safe_hire_exception"] = market_orders == [["HIRE"]]
    checks["step696_hire_no_seed_gain_rejected"] = not hire._safe_terminal_hire(
        696, farm, hg, {"WHEAT": 1}, 1000, 100)
    checks["step696_hire_unaffordable_rejected"] = not hire._safe_terminal_hire(
        696, farm, hg, {"WHEAT": 2}, 100, 100)

    tg = empty_grid(); tg[0][1] = "LOCKED"
    safe = module.ShopRouterExecutor._safe_unit_verb
    checks["typed_locked_move_and_exact_arity"] = (
        safe(["EAST"], (0, 0), tg, {}, {})
        and not safe(["CARE", "junk"], (0, 0), tg, {}, {})
        and not safe(["PLANT", "ALIEN"], (0, 0), tg, {}, {})
        and not safe(["WEST"], (0, 0), tg, {}, {}))
    return checks


def main():
    module = load(MAIN, "r26_candidate")
    r25 = load(R25_MAIN, "r25_reference")
    result = {"schema": module.SCHEMA, "static": static_checks(module),
              "parity": parity_checks(module, r25),
              "mechanisms": mechanism_checks(module)}
    result["passed"] = all(all(group.values()) for group in
                           (result["static"], result["parity"], result["mechanisms"]))
    result["test_count"] = sum(len(group) for group in
                               (result["static"], result["parity"], result["mechanisms"]))
    (HERE / "mechanism_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
