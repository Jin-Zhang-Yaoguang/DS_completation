#!/usr/bin/env python3
"""Audit route-boundary identity and repaired-action executability."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[4]
MODEL = ROOT / "kaggle_Kaggriculture" / "model"
CPPSIM = MODEL / "community_research" / "2026-08-26" / "live_cli" / "external_repos" / "kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
sys.path.insert(0, str(HERE))
from portfolio_policy import ROUTER_STEP, _DEFAULT_ACTIONS, _YARN_ACTIONS, make_agent


MOVES = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}


def tile_at(farm, position):
    x, y = map(int, position)
    return farm["tiles"][y][x]


def shed_access(position, size):
    x, y = map(int, position)
    h = size // 2
    return (x, y) in {(h - 1, h - 1), (h, h - 1), (h - 1, h), (h, h)}


def audit_units(obs, action, counts, examples):
    seat = int(obs["player"])
    farm = obs["farms"][seat]
    positions = [farm["farmer"], *farm["hands"]]
    inventories = obs["private"]["inventories"]
    orders = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
    counts["turns"] += 1
    counts["hand_count_expected"] += len(farm["hands"])
    counts["hand_count_returned"] += len(action.get("hands") or [])
    if len(action.get("hands") or []) != len(farm["hands"]):
        counts["hand_count_mismatch_turns"] += 1
    seed_demand = Counter(o[1] for o in orders if len(o) >= 2 and o[0] == "PLANT")
    seeds = obs["private"]["seeds"]
    for index, (position, order) in enumerate(zip(positions, orders)):
        op = order[0] if order else "PASS"
        if op == "PASS":
            continue
        counts["unit_orders"] += 1
        tile = tile_at(farm, position)
        inv = inventories[index] if index < len(inventories) else {}
        valid = True
        if op in MOVES:
            dx, dy = MOVES[op]
            x, y = map(int, position)
            valid = 0 <= x + dx < len(farm["tiles"][0]) and 0 <= y + dy < len(farm["tiles"])
        elif op == "PLANT":
            valid = tile is None and seed_demand[order[1]] <= int(seeds.get(order[1], 0) or 0)
        elif op == "WATER":
            valid = isinstance(tile, dict) and tile.get("kind") == "PLANT" and not tile.get("watered_today")
        elif op == "HARVEST":
            valid = isinstance(tile, dict) and int(tile.get("yield_units", 0) or 0) > 0
        elif op == "FERTILIZE":
            valid = isinstance(tile, dict) and tile.get("kind") == "PLANT" and int(inv.get("FERTILIZER", 0) or 0) > 0
        elif op == "DIG":
            valid = tile is not None and not (isinstance(tile, dict) and tile.get("animal")) and tile != "LOCKED"
        elif op == "BUILD_COOP" or op == "BUILD_PASTURE":
            valid = tile is None
        elif op == "FEED":
            valid = isinstance(tile, dict) and bool(tile.get("animal")) and not tile.get("fed_today") and int(inv.get("WHEAT", 0) or 0) > 0
        elif op == "CARE":
            valid = isinstance(tile, dict) and bool(tile.get("animal")) and not tile.get("cared_today")
        elif op == "COLLECT_FERTILIZER":
            valid = isinstance(tile, dict) and bool(tile.get("fertilizer_available"))
        elif op == "PICKUP":
            valid = shed_access(position, len(farm["tiles"])) and len(order) >= 3 and int(obs["private"]["shed"].get(order[1], 0) or 0) > 0
        elif op == "DROP":
            valid = shed_access(position, len(farm["tiles"])) and sum(int(v or 0) for v in inv.values()) > 0
        elif op == "PLACE":
            valid = len(order) >= 2 and int(inv.get(order[1], 0) or 0) > 0
        if valid:
            counts["unit_precondition_valid"] += 1
        else:
            counts["unit_precondition_invalid"] += 1
            counts[f"unit_invalid_{op}"] += 1
            if len(examples["unit_invalid"]) < 30:
                examples["unit_invalid"].append({"step": int(obs["step"]), "seat": seat, "actor": index, "position": position, "order": order, "tile": tile, "inventory": inv})


def market_before(obs, action, counts):
    seat = int(obs["player"])
    farm = obs["farms"][seat]
    market = action.get("market") or []
    counts["market_orders"] += len(market)
    if len(market) > 10:
        counts["market_overflow_turns"] += 1
    for order in market:
        if not order:
            continue
        op = order[0]
        if op == "BUY_LAND":
            counts["land_requests"] += 1
            extra = len(farm["unlocked_quadrants"]) - 1
            price = (1000, 2000, 4000)[extra] if 0 <= extra < 3 else 10**18
            if int(farm["money"]) < price:
                counts["land_precheck_unaffordable"] += 1
        elif op == "HIRE":
            counts["hire_requests"] += 1
            n = int(farm.get("hires_today", 0) or 0)
            a, b = 0, 1
            for _ in range(n):
                a, b = b, a + b
            if int(farm["money"]) < a:
                counts["hire_precheck_unaffordable"] += 1
        elif op in {"BUY_SEED", "BUY_ANIMAL", "BUY_PRODUCT"}:
            counts[f"{op.lower()}_requested_units"] += max(0, int(order[2] or 0))
        elif op == "SELL":
            counts["sell_requested_units"] += max(0, int(order[2] or 0))


def projected_shed_after_units(obs, action):
    seat = int(obs["player"])
    farm = obs["farms"][seat]
    size = len(farm["tiles"])
    shed = {key: int(value or 0) for key, value in obs["private"]["shed"].items()}
    positions = [farm["farmer"], *farm["hands"]]
    inventories = obs["private"]["inventories"]
    orders = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
    for index, (position, order) in enumerate(zip(positions, orders)):
        inv = inventories[index] if index < len(inventories) else {}
        if not order:
            continue
        if order[0] == "PICKUP" and len(order) >= 3 and shed_access(position, size):
            item = order[1]
            shed[item] = max(0, shed.get(item, 0) - min(int(order[2] or 0), shed.get(item, 0)))
        elif order[0] == "DROP" and shed_access(position, size):
            for item, raw in inv.items():
                room = max(0, 100 - sum(shed.values()))
                shed[item] = shed.get(item, 0) + min(max(0, int(raw or 0)), room)
        elif order[0] == "PLACE" and len(order) >= 3 and shed_access(position, size):
            item = order[1]
            tile = tile_at(farm, position)
            animal_structure = item in {"GOOSE", "COW", "SHEEP"} and isinstance(tile, dict) and not tile.get("animal") and tile.get("kind") in {"COOP", "PASTURE"}
            if not animal_structure:
                room = max(0, 100 - sum(shed.values()))
                shed[item] = shed.get(item, 0) + min(max(0, int(order[2] or 0)), int(inv.get(item, 0) or 0), room)
    return shed


def purchase_success(before, after, action, counts, examples):
    before_seeds = before["private"]["seeds"]
    after_seeds = after["private"]["seeds"]
    seat = int(before["player"])
    farm = before["farms"][seat]
    positions = [farm["farmer"], *farm["hands"]]
    orders = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
    demand = Counter(o[1] for o in orders if len(o) >= 2 and o[0] == "PLANT")
    consumed = Counter()
    for position, order in zip(positions, orders):
        if len(order) >= 2 and order[0] == "PLANT" and tile_at(farm, position) is None and demand[order[1]] <= int(before_seeds.get(order[1], 0) or 0):
            consumed[order[1]] += 1
    requested_seed = Counter()
    requested_animal = Counter()
    for order in action.get("market") or []:
        if len(order) >= 3 and order[0] == "BUY_SEED":
            requested_seed[order[1]] += max(0, int(order[2] or 0))
        elif len(order) >= 3 and order[0] == "BUY_ANIMAL":
            requested_animal[order[1]] += max(0, int(order[2] or 0))
    for item, requested in requested_seed.items():
        bought = max(0, int(after_seeds.get(item, 0) or 0) - int(before_seeds.get(item, 0) or 0) + consumed[item])
        counts["buy_seed_success_units"] += min(requested, bought)
        counts["buy_seed_failed_units"] += max(0, requested - bought)
        if requested > bought and len(examples["buy_seed_failed"]) < 30:
            examples["buy_seed_failed"].append({"step": int(before["step"]), "seat": seat, "item": item, "requested": requested, "bought": bought, "money": int(farm["money"]), "market": action.get("market") or []})
    projected = projected_shed_after_units(before, action)
    after_shed = after["private"]["shed"]
    for item, requested in requested_animal.items():
        bought = max(0, int(after_shed.get(item, 0) or 0) - int(projected.get(item, 0) or 0))
        counts["buy_animal_success_units"] += min(requested, bought)
        counts["buy_animal_failed_units"] += max(0, requested - bought)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-start", type=int, default=21000)
    parser.add_argument("--seeds", type=int, default=16)
    parser.add_argument("--output", default=str(HERE / "compatibility_audit_results.json"))
    args = parser.parse_args()
    builds = sorted((CPPSIM / "build").glob("lib.*"))
    sys.path.insert(0, str(builds[-1]))
    sys.path.insert(0, str(FACTORY))
    import kagsim  # type: ignore
    from agent_factory import Registry, create_agent  # type: ignore
    registry = Registry(path=Path(__file__).resolve(), models={}, raw={})

    prefix_mismatches = [step for step in range(ROUTER_STEP) if _DEFAULT_ACTIONS[step] != _YARN_ACTIONS[step]]
    counts = Counter()
    examples = {"unit_invalid": [], "buy_seed_failed": []}
    rewards = []
    for seed in range(args.seed_start, args.seed_start + args.seeds):
        for seat in (0, 1):
            policy = make_agent("router")
            opponent = create_agent(registry, {
                "id": f"audit_kawa_{seed}_{seat}", "kind": "python",
                "path": str(MODEL / "v8_kawa_lead2_slot" / "main.py"), "entrypoint": "agent",
            })
            game = kagsim.Game(seed)
            while not game.done:
                pair = [None, None]
                obs = game.observe(seat)
                action = policy(obs)
                if game.step_count >= ROUTER_STEP:
                    audit_units(obs, action, counts, examples)
                    market_before(obs, action, counts)
                pair[seat] = action
                pair[1 - seat] = opponent(game.observe(1 - seat))
                before = obs
                game.step(pair[0], pair[1])
                if before["step"] >= ROUTER_STEP and game.step_count < 720:
                    after = game.observe(seat)
                    purchase_success(before, after, action, counts, examples)
                    land_requests = sum(bool(order and order[0] == "BUY_LAND") for order in action.get("market") or [])
                    if land_requests:
                        counts["land_success"] += min(land_requests, max(0, len(after["farms"][seat]["unlocked_quadrants"]) - len(before["farms"][seat]["unlocked_quadrants"])))
                    if before["hour"] != 23:
                        hire_requests = sum(bool(order and order[0] == "HIRE") for order in action.get("market") or [])
                        counts["hire_auditable_requests"] += hire_requests
                        counts["hire_success"] += min(hire_requests, max(0, len(after["farms"][seat]["hands"]) - len(before["farms"][seat]["hands"])))
            rewards.append(float(game.reward(seat)))

    unit_total = counts["unit_orders"]
    result = {
        "status": "HELD_OUT_L1_ACTION_COMPATIBILITY_AUDIT",
        "engine": str(kagsim.ENGINE_VERSION),
        "seed_range": [args.seed_start, args.seed_start + args.seeds - 1],
        "games": len(rewards),
        "route_boundary": {
            "step": ROUTER_STEP,
            "prefix_action_mismatches": prefix_mismatches,
            "exact_prefix": not prefix_mismatches,
            "state_identity_implication": "identical actions under identical engine/opponent imply exact money, coordinates, inventory, land, labour and shed state at decision",
        },
        "action_audit": {
            **dict(counts),
            "hand_count_match_rate": 1.0 - counts["hand_count_mismatch_turns"] / max(1, counts["turns"]),
            "unit_precondition_valid_rate": counts["unit_precondition_valid"] / max(1, unit_total),
            "land_success_rate": counts["land_success"] / max(1, counts["land_requests"]),
            "hire_success_rate_non_dayend": counts["hire_success"] / max(1, counts["hire_auditable_requests"]),
            "buy_seed_success_rate": counts["buy_seed_success_units"] / max(1, counts["buy_seed_requested_units"]),
            "buy_animal_success_rate": counts["buy_animal_success_units"] / max(1, counts["buy_animal_requested_units"]),
        },
        "examples": examples,
        "mean_bank": statistics.mean(rewards),
    }
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
