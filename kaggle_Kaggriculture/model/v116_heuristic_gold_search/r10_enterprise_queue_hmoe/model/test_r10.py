#!/usr/bin/env python3
"""P0/P1 tests for the self-contained R10 enterprise executor.

These are legality and mechanism tests, not a strength evaluation.  The real
engine runs are intentionally limited to one-step and 96-step smoke episodes.
"""

from __future__ import annotations

import ast
from collections import Counter
import copy
import importlib.util
import json
from pathlib import Path
import sys
import traceback


HERE = Path(__file__).resolve().parent
MAIN = HERE / "main.py"
IDLE = {"farmer": ["PASS"], "hands": [], "market": []}
UNIT_ZERO = {"PASS", "NORTH", "SOUTH", "EAST", "WEST", "DROP", "WATER", "HARVEST",
             "DIG", "BUILD_COOP", "BUILD_PASTURE", "FEED", "CARE", "COLLECT_FERTILIZER"}
UNIT_ITEM = {"PLANT", "PLACE"}
UNIT_QUANTITY = {"PICKUP"}
MARKET_ZERO = {"HIRE", "BUY_LAND"}
MARKET_QUANTITY = {"BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL"}


def load_candidate():
    spec = importlib.util.spec_from_file_location("r10_candidate_test", MAIN)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_kagsim():
    cppsim = HERE.parents[3] / "model" / "community_research" / "2026-08-26" \
        / "live_cli" / "external_repos" / "kaggriculture-cppsim"
    candidates = sorted((cppsim / "build").glob("lib*/kagsim*.so")) + sorted(cppsim.glob("kagsim*.so"))
    if not candidates:
        raise RuntimeError("validated local kagsim build not found")
    sys.path.insert(0, str(candidates[0].parent))
    import kagsim  # type: ignore
    return kagsim


def validate_action(action, hand_count):
    errors = []
    if not isinstance(action, dict) or set(action) != {"farmer", "hands", "market"}:
        return ["top-level schema"]
    if not isinstance(action["hands"], list) or len(action["hands"]) != hand_count:
        errors.append("hands length")
    units = [action["farmer"]] + list(action["hands"])
    for verb in units:
        if not isinstance(verb, list) or not verb or not isinstance(verb[0], str):
            errors.append("unit structure")
            continue
        op = verb[0]
        expected = 1 if op in UNIT_ZERO else 2 if op in UNIT_ITEM else 3 if op in UNIT_QUANTITY else -1
        if len(verb) != expected:
            errors.append(f"unit {op} arity")
        if op in UNIT_QUANTITY and (not isinstance(verb[2], int) or verb[2] <= 0):
            errors.append(f"unit {op} quantity")
    if not isinstance(action["market"], list) or len(action["market"]) > 10:
        errors.append("market shape")
    else:
        for order in action["market"]:
            if not isinstance(order, list) or not order or not isinstance(order[0], str):
                errors.append("market structure")
                continue
            op = order[0]
            expected = 1 if op in MARKET_ZERO else 3 if op in MARKET_QUANTITY else -1
            if len(order) != expected:
                errors.append(f"market {op} arity")
            if op in MARKET_QUANTITY and (not isinstance(order[2], int) or order[2] <= 0):
                errors.append(f"market {op} quantity")
    return errors


def synthetic_obs(step=0, shop=None, money=3000, seeds=None, shed=None, hands=None, grid=None):
    if grid is None:
        grid = [[None if x < 5 and y < 5 else "LOCKED" for x in range(10)] for y in range(10)]
    hand_positions = list(hands or [])
    farm = {
        "money": money,
        "tiles": copy.deepcopy(grid),
        "farmer": [4, 4],
        "hands": hand_positions,
        "unlocked_quadrants": ["NW"],
        "hires_today": len(hand_positions),
    }
    empty = {
        "money": 3000,
        "tiles": [[None if x < 5 and y < 5 else "LOCKED" for x in range(10)] for y in range(10)],
        "farmer": [4, 4], "hands": [], "unlocked_quadrants": ["NW"], "hires_today": 0,
    }
    products = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
    return {
        "step": step, "day": step // 24, "hour": step % 24, "player": 0,
        "farms": [farm, empty],
        "market": {"inventory": {item: 10000 for item in products},
                   "prices": {"WHEAT": 25, "CARROT": 35, "TOMATO": 60,
                              "STRAWBERRY": 120, "MELON": 250, "EGG": 50,
                              "MILK": 160, "WOOL": 200, "FERTILIZER": 100}},
        "town": {"unlocked_shops": [] if shop is None else [shop]},
        "private": {"shed": dict(shed or {}), "seeds": dict(seeds or {}),
                    "inventories": [{} for _ in range(1 + len(hand_positions))]},
    }


def static_audit(module):
    source = MAIN.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    allowed = {"__future__", "collections", "dataclasses", "hashlib", "json", "math", "typing"}
    forbidden_tokens = ["replay", "base_agent", "parent_agent", "_actions", "importlib", "sys.path"]
    return {
        "strategy_parent_null": module.STRATEGY_PARENT is None,
        "stdlib_only": imports <= allowed,
        "imports": sorted(imports),
        "forbidden_tokens_absent": not any(token in source.lower() for token in forbidden_tokens),
        "forbidden_hits": [token for token in forbidden_tokens if token in source.lower()],
        "static_coordinates_only_shed_gates": source.count("SHED_GATES") >= 2,
    }


def mechanism_tests(module):
    checks = {}
    modes = {}
    for mode in module.MODES:
        executor = module.build_executor(mode=mode)
        action = executor.act(synthetic_obs())
        modes[mode] = {
            "schema_errors": validate_action(action, 0),
            "expert": executor.diagnostics()["expert"],
            "committed": executor.diagnostics()["committed"],
        }
    checks["modes"] = modes
    checks["interface"] = all(not row["schema_errors"] for row in modes.values())
    checks["fixed_experts"] = all(modes[f"fixed_{expert}"]["expert"] == expert
                                  and modes[f"fixed_{expert}"]["committed"]
                                  for expert in module.EXPERTS)

    router = module.build_executor(mode="router")
    router.act(synthetic_obs(step=0))
    before = router.diagnostics()
    router.act(synthetic_obs(step=72, shop="YARN_STORE", money=5000))
    first = router.diagnostics()
    router.act(synthetic_obs(step=73, shop="PET_CAFE", money=5000))
    after = router.diagnostics()
    checks["router_once"] = (not before["committed"] and first["committed"]
                             and first["expert"] == "fiber_grain"
                             and after["expert"] == first["expert"]
                             and after["commit_step"] == first["commit_step"] == 72)

    mature = synthetic_obs(step=96, money=5000, seeds={})
    mature["farms"][0]["tiles"][4][4] = {
        "kind": "PLANT", "crop": "WHEAT", "planted_day": 0,
        "watered_today": True, "consecutive_unwatered": 0, "yield_units": 6,
        "max_lifespan_step": 120, "fertilized_until_day": -1,
    }
    harvest_executor = module.build_executor(mode="fixed_root_exchange")
    harvest_action = harvest_executor.act(mature)
    checks["mature_crop_path"] = (
        harvest_action["farmer"] == ["HARVEST"]
        or any(ticket.kind == "HARVEST" for ticket in harvest_executor.tickets.values())
    )

    atomic = module.build_executor(mode="fixed_root_exchange")
    atomic_obs = synthetic_obs(step=1, money=5000, seeds={"WHEAT": 1},
                               hands=[[4, 3], [3, 4], [3, 3]])
    atomic_action = atomic.act(atomic_obs)
    planted = Counter(verb[1] for verb in [atomic_action["farmer"]] + atomic_action["hands"]
                      if verb and verb[0] == "PLANT")
    reserved = atomic.diagnostics()["resource_ledger"]["reserved_seeds"]
    checks["atomic_seed_reservation"] = planted["WHEAT"] <= 1 and int(reserved.get("WHEAT", 0)) <= 1

    # Direct state-machine exercise: a harvested load must enter DELIVER and
    # only complete after a shed DROP is observed on the next call.
    chain = module.build_executor(mode="fixed_root_exchange")
    ticket = module.TaskTicket("CHAIN", "HARVEST", (0, 0), ("HARVEST",), 2, 20, 0,
                               state="EXECUTE", owner=0)
    chain.tickets[ticket.ticket_id] = ticket
    chain.actors[0] = module.ActorState(0, 0, 0, "harvester", active_ticket="CHAIN")
    chain.pending_unit_intents = {0: {"ticket_id": "CHAIN", "verb": ["HARVEST"],
                                      "position": (0, 0), "distance": 0}}
    empty_grid = [[None for _ in range(10)] for _ in range(10)]
    chain._reconcile_unit_intents(1, empty_grid, [[0, 0]], [{"WHEAT": 4}])
    deliver = ticket.state == "DELIVER"
    chain._refresh_tickets(1, 0, 1, empty_grid)
    deliver_survives_refresh = ticket.state == "DELIVER"
    chain.pending_unit_intents = {0: {"ticket_id": "CHAIN", "verb": ["DROP"],
                                      "position": (4, 4), "distance": 0}}
    chain._reconcile_unit_intents(2, empty_grid, [[4, 4]], [{}])
    checks["harvest_delivery_chain"] = deliver and deliver_survives_refresh \
        and ticket.state == "COMPLETE"

    checks["diagnostics_json"] = isinstance(json.dumps(atomic.diagnostics(), sort_keys=True), str)
    checks["all_passed"] = all(value for key, value in checks.items()
                                  if key not in {"modes", "all_passed"})
    return checks


def real_engine_tests(module, kagsim):
    one_step = []
    short = []
    for mode in module.MODES:
        game = kagsim.Game(7100, steps=96)
        executor = module.build_executor(mode=mode)
        obs = game.observe(0)
        action = executor.act(obs)
        errors = validate_action(action, len(obs["farms"][0]["hands"]))
        game.step(action, IDLE)
        one_step.append({"mode": mode, "schema_errors": errors,
                         "money_after": game.observe(0)["farms"][0]["money"],
                         "action": action})

        game = kagsim.Game(7100, steps=96)
        executor = module.build_executor(mode=mode)
        calls = 0
        schema_errors = []
        runtime_errors = []
        action_counts = Counter()
        while not game.done:
            obs = game.observe(0)
            try:
                action = executor.act(obs)
                calls += 1
                schema_errors.extend(f"step {game.step_count}: {error}"
                                     for error in validate_action(action, len(obs["farms"][0]["hands"])) )
                action_counts.update([action["farmer"][0]])
                action_counts.update(verb[0] for verb in action["hands"])
            except Exception as exc:  # evidence must preserve any unexpected failure
                runtime_errors.append({"step": game.step_count, "error": repr(exc),
                                       "traceback": traceback.format_exc()})
                action = IDLE
            game.step(action, IDLE)
        diag = executor.diagnostics()
        short.append({
            "mode": mode, "seed": 7100, "opponent": "idle", "configured_steps": 96,
            "agent_calls": calls, "expected_calls": 95, "bank": game.reward(0),
            "schema_errors": schema_errors, "runtime_errors": runtime_errors,
            "action_counts": dict(sorted(action_counts.items())),
            "expert": diag["expert"], "commit_step": diag["commit_step"],
            "layout_lease_count": diag["layout_lease_count"],
            "task_states": diag["task_states"], "audit": diag["audit"],
        })
    return {
        "engine_version": str(kagsim.ENGINE_VERSION),
        "one_step": one_step,
        "short_horizon": short,
        "all_legal": all(not row["schema_errors"] for row in one_step)
                     and all(not row["schema_errors"] and not row["runtime_errors"]
                             and row["agent_calls"] == row["expected_calls"] for row in short),
        "formal_episode_count": 0,
    }


def main():
    module = load_candidate()
    kagsim = load_kagsim()
    result = {
        "candidate_schema": module.SCHEMA,
        "params_hash": module.canonical_hash(module.DEFAULT_PARAMS),
        "static_audit": static_audit(module),
        "mechanism": mechanism_tests(module),
        "real_engine": real_engine_tests(module, kagsim),
    }
    result["passed"] = (all(value for key, value in result["static_audit"].items()
                            if key not in {"imports", "forbidden_hits"})
                        and result["mechanism"]["all_passed"]
                        and result["real_engine"]["all_legal"])
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
