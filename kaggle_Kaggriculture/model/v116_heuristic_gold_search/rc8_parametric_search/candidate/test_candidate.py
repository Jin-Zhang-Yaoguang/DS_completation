#!/usr/bin/env python3
"""Mechanism, interface, freeze, and static-origin checks for RC8."""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import importlib.util
import json
import py_compile
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import candidate  # noqa: E402


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def crop_tile(crop: str) -> dict[str, Any]:
    return {"kind": "PLANT", "crop": crop, "planted_day": 0,
            "yield_units": candidate.CROPS[crop]["max_yield"], "watered_today": True}


def mechanism_checks() -> dict[str, bool]:
    params = copy.deepcopy(candidate.DEFAULT_PARAMS)
    genomes = candidate.compile_genomes(params)
    goals = {name: candidate.compile_daily_goals(genome) for name, genome in genomes.items()}
    hard_floors = {
        name: (len(rows) == 30 and sum(rows[-1]["crops"].values()) == 59
               and rows[-1]["crops"].get("WHEAT", 0) >= 18)
        for name, rows in goals.items()
    }
    common_opening = all(genome["crop_blocks"][0] == {"WHEAT": 8, "MELON": 7}
                         and genome["animal_waves"][0] == (0, "SHEEP", 4)
                         for genome in genomes.values())
    stage_sizes = all([sum(block.values()) for block in genome["crop_blocks"]] == [15, 19, 25]
                      for genome in genomes.values())
    routes = {
        "YARN_STORE": "wool", "SMOOTHIE_SHOP": "dairy_berry",
        "ICE_CREAM_SHOP": "dairy_berry", "PIZZA_SHOP": "tomato_market",
        "FARMERS_MARKET": "tomato_market", "PET_CAFE": "root",
        "BAKERY": "grain_egg", "BRUNCH_SPOT": "grain_egg",
        "UNKNOWN": "grain_egg",
    }
    router_mapping = all(candidate.route_expert([shop]) == expert
                         for shop, expert in routes.items())
    first_shop_only = candidate.route_expert(["PET_CAFE", "YARN_STORE"]) == "root"
    fixed_support = all(candidate.build_executor(params, f"fixed_{name}").expert == name
                        for name in candidate.EXPERT_NAMES)

    tuned = copy.deepcopy(params)
    tuned["auction"].update({"harvest_priority": 3, "plant_priority": 4,
                              "place_priority": 2, "sticky_bonus": 0,
                              "role_penalty": 0})
    executor = candidate.build_executor(tuned, "fixed_root")
    grid = [[None for _ in range(10)] for _ in range(10)]
    grid[0][0] = crop_tile("CARROT")
    grid[0][1] = {"kind": "PASTURE"}
    goal = {"lands": 1, "hands": 4, "crops": {"CARROT": 2},
            "animals": {"SHEEP": 1}, "feed_reserve": 2, "cash_reserve": 100}
    jobs = executor._jobs(4, grid, goal, {"CARROT": 1}, goal)
    auction_wiring = (
        any(job[0] == 3 and job[3][0] == "HARVEST" for job in jobs)
        and any(job[0] == 4 and job[3][0] == "PLANT" for job in jobs)
        and any(job[0] == 2 and job[3][0] == "PLACE" for job in jobs)
    )

    reserve_params = copy.deepcopy(params)
    reserve_params["auction"]["replacement"] = "same_turn_seed_reserve_only"
    reserve = candidate.build_executor(reserve_params, "fixed_root")
    reserve.first_shops = ("PET_CAFE",)
    one_crop = [[None for _ in range(10)] for _ in range(10)]
    one_crop[0][0] = crop_tile("CARROT")
    true_harvest = reserve._true_eligible_harvests(
        one_crop, [(0, 0)], [["HARVEST"]]
    )
    simple_goal = {"lands": 0, "hands": 0, "crops": {"CARROT": 1},
                   "animals": {}, "feed_reserve": 0, "cash_reserve": 100}
    obs = {"step": 100, "day": 4, "hour": 4,
           "town": {"unlocked_shops": ["PET_CAFE"]},
           "market": {"prices": {}, "inventory": {}}}
    farm = {"money": 10_000, "hires_today": 0, "hands": [],
            "unlocked_quadrants": []}
    orders = reserve._market(obs, farm, one_crop, simple_goal, {}, {}, [],
                             Counter(), true_harvest)
    replacement_wiring = (true_harvest == {"CARROT": 1}
                          and ["BUY_SEED", "CARROT", 1] in orders)

    invalid = copy.deepcopy(params)
    invalid["market"]["sale_floor"] = .50
    invalid_rejected = bool(candidate.validate_params(invalid))
    bool_alias = copy.deepcopy(params)
    bool_alias["experts"]["root"]["focus2"] = False
    strict_types = bool(candidate.validate_params(bool_alias))
    reversed_params = {
        key: {inner: copy.deepcopy(value[inner]) for inner in reversed(list(value))}
        for key, value in reversed(list(params.items()))
    }
    canonical_stable = (candidate.canonical_hash(params)
                        == candidate.canonical_hash(reversed_params))
    return {
        "default_params_valid": not candidate.validate_params(params),
        "five_experts": set(genomes) == set(candidate.EXPERT_NAMES) and len(genomes) == 5,
        "common_opening_w8_m7_sheep4": common_opening,
        "stage_block_sizes_15_19_25": stage_sizes,
        "all_30_day_59_crop_wheat_floor": all(hard_floors.values()),
        "expert_specific_hard_floors": (
            goals["root"][-1]["crops"].get("CARROT", 0) >= 8
            and goals["dairy_berry"][-1]["crops"].get("STRAWBERRY", 0) >= 12
            and goals["dairy_berry"][-1]["animals"].get("COW", 0) >= 4
            and goals["tomato_market"][-1]["crops"].get("TOMATO", 0) >= 6
            and goals["wool"][-1]["animals"].get("SHEEP", 0) >= 5
            and goals["grain_egg"][-1]["crops"].get("WHEAT", 0) >= 24
            and goals["grain_egg"][-1]["animals"].get("GOOSE", 0) >= 2
        ),
        "router_first_shop_mapping": router_mapping and first_shop_only,
        "fixed_expert_modes": fixed_support,
        "auction_six_dim_wiring": auction_wiring,
        "market_replacement_wiring": replacement_wiring,
        "invalid_discrete_value_rejected": invalid_rejected,
        "bool_int_alias_rejected": strict_types,
        "canonical_hash_key_order_stable": canonical_stable,
    }


def static_audit(path: Path) -> dict[str, Any]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    allowed = {"__future__", "math", "copy", "hashlib", "json", "os",
               "collections", "pathlib", "typing"}
    forbidden_imports = sorted(name for name in imports
                               if name.split(".")[0] not in allowed)
    forbidden_symbols = [symbol for symbol in
                         ("_ACTIONS", "replacement_claims", "parent_agent", "historical_agent")
                         if symbol in source]
    largest_literal = max((len(node.elts) for node in ast.walk(tree)
                           if isinstance(node, (ast.List, ast.Tuple))), default=0)
    return {
        "path": str(path),
        "sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "imports": imports,
        "forbidden_imports": forbidden_imports,
        "forbidden_symbols": forbidden_symbols,
        "largest_list_or_tuple_literal": largest_literal,
        "self_contained_stdlib_only": not forbidden_imports,
        "no_recorded_action_table_or_parent_agent": not forbidden_symbols,
        "pass": not forbidden_imports and not forbidden_symbols and largest_literal <= 30,
    }


def engine_one_step(module: Any) -> dict[str, Any]:
    model = HERE.parents[2]
    cppsim = (model / "community_research" / "2026-08-26" / "live_cli" /
              "external_repos" / "kaggriculture-cppsim")
    builds = sorted((cppsim / "build").glob("lib.*"))
    if not builds:
        return {"available": False, "pass": False, "reason": "cppsim build missing"}
    sys.path.insert(0, str(builds[-1]))
    import kagsim  # type: ignore
    game = kagsim.Game(88001)
    obs = game.observe(0)
    action = module.build_executor(module.DEFAULT_PARAMS).act(obs)
    farm = obs["farms"][0]
    passed = (set(action) == {"farmer", "hands", "market"}
              and len(action["hands"]) == len(farm.get("hands", []) or [])
              and len(action["market"]) <= 10)
    return {"available": True, "engine": getattr(kagsim, "ENGINE_VERSION", "unknown"),
            "schema": {"farmer": action["farmer"], "hands_count": len(action["hands"]),
                       "market_orders": len(action["market"])}, "pass": passed}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=HERE / "test_results.json")
    parser.add_argument("--audit-output", type=Path, default=HERE / "originality_audit.json")
    args = parser.parse_args()
    frozen = HERE / "main.py"
    if not frozen.exists():
        raise SystemExit("freeze main.py before running tests")
    py_compile.compile(str(HERE / "candidate.py"), doraise=True)
    py_compile.compile(str(frozen), doraise=True)
    frozen_module = load_module(frozen, "rc8_frozen_main")
    with tempfile.TemporaryDirectory(prefix="rc8-freeze-") as directory:
        alternative = copy.deepcopy(candidate.DEFAULT_PARAMS)
        alternative["market"]["finance_stress"] = 24
        alt_path = Path(directory) / "main.py"
        returned_hash = candidate.freeze_candidate(alternative, alt_path)
        alt_module = load_module(alt_path, "rc8_alt_main")
        freeze_check = {
            "returned_hash_matches": returned_hash == candidate.canonical_hash(alternative),
            "frozen_default_hash_matches": alt_module.DEFAULT_PARAMS_HASH == returned_hash,
            "frozen_builds_executor": type(alt_module.build_executor(
                alt_module.DEFAULT_PARAMS)).__name__ == "ShopRouterExecutor",
        }
    mechanism = mechanism_checks()
    audit = static_audit(frozen)
    engine = engine_one_step(frozen_module)
    passed = (all(mechanism.values()) and all(freeze_check.values())
              and audit["pass"] and engine["pass"])
    payload = {
        "schema": "v116-rc8-candidate-test-v1",
        "default_params_hash": candidate.DEFAULT_PARAMS_HASH,
        "py_compile": {"candidate.py": True, "main.py": True},
        "mechanism_checks": mechanism,
        "freeze_checks": freeze_check,
        "static_originality": audit,
        "engine_one_step": engine,
        "large_evaluation_run": False,
        "pass": passed,
    }
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    args.audit_output.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
                                 encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
