#!/usr/bin/env python3
"""Mechanism regression for R11 safety invariants."""

from __future__ import annotations

import ast
from collections import Counter
import importlib.util
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
MAIN = HERE / "main.py"


def load_candidate():
    spec = importlib.util.spec_from_file_location("r11_mechanism_candidate", MAIN)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def grid() -> list[list[object]]:
    return [[None if x < 5 and y < 5 else "LOCKED" for x in range(10)] for y in range(10)]


def observation(step: int, shop: str | None = None) -> dict:
    tiles = grid()
    farm = {"money": 3000, "tiles": tiles, "farmer": [4, 4], "hands": [],
            "unlocked_quadrants": ["NW"], "hires_today": 0}
    rival = {"money": 3000, "tiles": grid(), "farmer": [4, 4], "hands": [],
             "unlocked_quadrants": ["NW"], "hires_today": 0}
    products = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
                "EGG", "MILK", "WOOL", "FERTILIZER")
    return {"step": step, "day": step // 24, "hour": step % 24, "player": 0,
            "farms": [farm, rival],
            "private": {"shed": {}, "seeds": {}, "inventories": [{}]},
            "market": {"inventory": {item: 10000 for item in products},
                       "prices": {item: 25 for item in products}},
            "town": {"unlocked_shops": [] if shop is None else [shop]}}


def static_checks(module) -> dict[str, bool]:
    source = MAIN.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    allowed = {"__future__", "collections", "dataclasses", "hashlib", "json", "math", "typing"}
    return {"strategy_parent_null": module.STRATEGY_PARENT is None,
            "stdlib_only": imports <= allowed,
            "four_modes": tuple(module.MODES) == ("router", "fixed_root_exchange",
                                                   "fixed_dairy_berry", "fixed_fiber_grain"),
            "builder_present": callable(module.build_executor)}


def mechanism_checks(module) -> dict[str, bool]:
    checks: dict[str, bool] = {}
    empty = grid()

    daily = module.build_executor(mode="fixed_root_exchange")
    daily.current_day = 0
    ticket = module.TaskTicket("D0:WATER:0:0", "WATER", (0, 0), ("WATER",),
                               0, 23, 0, state="TRAVEL", owner=0,
                               daily=True, ticket_day=0, asset_target=(0, 0))
    daily.tickets[ticket.ticket_id] = ticket
    daily.actors[0] = module.ActorState(0, 0, 0, "caretaker", active_ticket=ticket.ticket_id)
    daily._day_rebind(1)
    checks["daily_ticket_cancelled_at_rollover"] = ticket.state == "CANCELLED" \
        and daily.diagnostics()["expired_live_tickets"] == 0
    checks["typed_maintenance_guards"] = (
        not daily._live_ticket(module.TaskTicket("W", "WATER", (0, 0), ("WATER",), 0, 1, 0),
                               1, empty)
        and not daily._live_ticket(module.TaskTicket("F", "FEED", (0, 0), ("FEED",), 0, 1, 0),
                                   1, empty)
        and not daily._live_ticket(module.TaskTicket("C", "CARE", (0, 0), ("CARE",), 0, 1, 0),
                                   1, empty))

    orphan = module.build_executor(mode="fixed_root_exchange")
    orphan.current_day = 0
    orphan.leases[(0, 0)] = module.LayoutLease((0, 0), "CROP:WHEAT", "root_exchange", 0, 0)
    old = module.TaskTicket("PLANT:0:0:WHEAT", "PLANT", (0, 0), ("PLANT", "WHEAT"),
                            3, 24, 0, required_item="WHEAT", state="WAIT_RESOURCE",
                            asset_target=(0, 0), lease_asset="CROP:WHEAT")
    orphan.tickets[old.ticket_id] = old
    goal = {"expert": "root_exchange", "phase": 1, "relative_day": 3,
            "crops": {"CARROT": 12}, "animals": {}}
    orphan._ensure_layout(72, empty, goal, 1)
    checks["layout_change_cancels_orphan"] = old.state == "CANCELLED" \
        and orphan.diagnostics()["orphan_live_tickets"] == 0

    failed = module.build_executor(mode="fixed_root_exchange")
    lost = module.TaskTicket("H0", "HARVEST", (0, 0), ("HARVEST",), 2, 12, 0,
                             state="EXECUTE", owner=0, asset_target=(0, 0))
    failed.tickets[lost.ticket_id] = lost
    failed.actors[0] = module.ActorState(0, 0, 0, "harvester", active_ticket=lost.ticket_id)
    failed.pending_unit_intents = {0: {"ticket_id": "H0", "verb": ["HARVEST"],
                                       "position": (0, 0), "distance": 0,
                                       "before_inventory_total": 0,
                                       "harvest_product": "WHEAT", "before_shed_product": 0}}
    failed._reconcile_unit_intents(1, empty, [[0, 0]], [{}], {})
    checks["harvest_loss_is_failed"] = lost.state == "FAILED_ASSET_LOSS"

    chain = module.build_executor(mode="fixed_root_exchange")
    harvested = module.TaskTicket("H1", "HARVEST", (0, 0), ("HARVEST",), 2, 12, 0,
                                  state="EXECUTE", owner=0, asset_target=(0, 0))
    chain.tickets[harvested.ticket_id] = harvested
    chain.actors[0] = module.ActorState(0, 0, 0, "harvester", active_ticket="H1")
    chain.pending_unit_intents = {0: {"ticket_id": "H1", "verb": ["HARVEST"],
                                      "position": (0, 0), "distance": 0,
                                      "before_inventory_total": 0,
                                      "harvest_product": "WHEAT", "before_shed_product": 0}}
    chain._reconcile_unit_intents(1, empty, [[0, 0]], [{"WHEAT": 4}], {})
    entered_delivery = harvested.state == "DELIVER"
    chain.pending_unit_intents = {0: {"ticket_id": "H1", "verb": ["DROP"],
                                      "position": (4, 4), "distance": 0}}
    chain._reconcile_unit_intents(2, empty, [[4, 4]], [{}], {"WHEAT": 4})
    checks["harvest_inventory_then_drop"] = entered_delivery and harvested.state == "COMPLETE"

    router = module.build_executor(mode="router")
    router.act(observation(0))
    router.act(observation(72, "YARN_STORE"))
    phase0 = router._program_goal(72, observation(72, "YARN_STORE"))["phase"]
    phase1 = router._program_goal(144, observation(144, "YARN_STORE"))["phase"]
    checks["router_commit_relative_phase"] = router.commit_step == 72 and phase0 == 0 and phase1 == 1

    gate = module.build_executor(mode="fixed_root_exchange")
    gate.service_cap = 40
    wait = module.TaskTicket("P", "PLANT", (0, 0), ("PLANT", "WHEAT"), 3, 24, 0,
                             required_item="WHEAT", state="WAIT_RESOURCE")
    gate.tickets[wait.ticket_id] = wait
    farm = {"money": 5000, "hires_today": 0, "unlocked_quadrants": ["NW"]}
    orders = gate._purchase_plan(0, 0, 0, farm, {}, empty, [[4, 4]], Counter(), {"WHEAT": 10000})
    raw = [order for _priority, order, _cost in orders]
    checks["wait_resource_only_buys_resource"] = any(order[0] == "BUY_SEED" for order in raw) \
        and not any(order[0] in {"HIRE", "BUY_LAND"} for order in raw)

    preempt = module.build_executor(mode="fixed_root_exchange")
    preempt.current_day = 0
    preempt.leases[(0, 0)] = module.LayoutLease((0, 0), "CROP:WHEAT", "root_exchange", 0, 0)
    production = module.TaskTicket("P0", "PLANT", (0, 0), ("PLANT", "WHEAT"), 3, 20, 0,
                                   state="TRAVEL", owner=0, asset_target=(0, 0),
                                   lease_asset="CROP:WHEAT")
    urgent_grid = grid()
    urgent_grid[0][1] = {"kind": "PLANT", "crop": "WHEAT", "watered_today": False,
                         "consecutive_unwatered": 1, "yield_units": 1, "planted_day": 0}
    urgent = module.TaskTicket("D0:WATER:1:0", "WATER", (1, 0), ("WATER",), 0, 1, 0,
                               state="TRAVEL", asset_target=(1, 0), daily=True, ticket_day=0)
    preempt.tickets = {production.ticket_id: production, urgent.ticket_id: urgent}
    actor = module.ActorState(0, 0, 0, "builder_planter", active_ticket="P0")
    preempt.actors[0] = actor
    preempt._advance_actor(actor, (0, 0), {}, Counter({"WHEAT": 1}), 0, [[0, 0]], 0, urgent_grid)
    checks["safety_preemption"] = actor.active_ticket == urgent.ticket_id \
        and production.owner is None and preempt.audit["safety_preemptions"] == 1
    return checks


def main() -> None:
    module = load_candidate()
    static = static_checks(module)
    mechanisms = mechanism_checks(module)
    result = {"schema": module.SCHEMA, "static": static, "mechanisms": mechanisms,
              "passed": all(static.values()) and all(mechanisms.values())}
    (HERE / "mechanism_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
