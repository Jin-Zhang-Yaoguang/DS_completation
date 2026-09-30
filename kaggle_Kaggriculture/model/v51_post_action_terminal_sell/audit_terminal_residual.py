#!/usr/bin/env python3
"""Audit terminal carried inventory and executable shed residual on internal seeds."""

from __future__ import annotations

import concurrent.futures
from collections import Counter, defaultdict
import json
import os
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
CPPSIM = MODEL / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
sys.path[:0] = [str(FACTORY), str(sorted((CPPSIM / "build").glob("lib.*"))[-1])]
import kagsim  # type: ignore
from agent_factory import Registry, create_agent  # type: ignore


POLICY = HERE / "main.py"
SEEDS = range(52001, 52065)


def access_tiles(size: int) -> set[tuple[int, int]]:
    half = size // 2
    return {(half - 1, half - 1), (half, half - 1), (half - 1, half), (half, half)}


def distance(position: list[int] | tuple[int, int], access: set[tuple[int, int]]) -> int:
    x, y = int(position[0]), int(position[1])
    return min(abs(x - ax) + abs(y - ay) for ax, ay in access)


def projected_shed(obs: dict, action: dict) -> dict[str, int]:
    seat = int(obs.get("player", 0) or 0)
    farm = obs["farms"][seat]
    private = obs.get("private", {}) or {}
    projected = {str(k): max(0, int(v or 0)) for k, v in (private.get("shed", {}) or {}).items()}
    inventories = list(private.get("inventories", []) or [])
    positions = [farm.get("farmer", [0, 0]), *list(farm.get("hands", []) or [])]
    orders = [action.get("farmer", ["PASS"]), *list(action.get("hands", []) or [])]
    tiles = list(farm.get("tiles", []) or [])
    access = access_tiles(len(tiles) or 10)
    for index, order in enumerate(orders):
        if index >= len(positions) or index >= len(inventories):
            continue
        pos = positions[index]
        if tuple(pos) not in access:
            continue
        inventory = {str(k): max(0, int(v or 0)) for k, v in dict(inventories[index] or {}).items()}
        if order and order[0] == "DROP":
            deposits = inventory.items()
        elif order and order[0] == "PLACE" and len(order) >= 2:
            item = str(order[1])
            requested = int(order[2]) if len(order) >= 3 else 1
            deposits = ((item, min(max(0, requested), inventory.get(item, 0))),)
        else:
            continue
        for item, quantity in deposits:
            room = max(0, 100 - sum(projected.values()))
            amount = min(max(0, int(quantity or 0)), room)
            projected[item] = projected.get(item, 0) + amount
    return projected


def snapshot(obs: dict, action: dict) -> dict:
    seat = int(obs.get("player", 0) or 0)
    farm = obs["farms"][seat]
    private = obs.get("private", {}) or {}
    inventories = list(private.get("inventories", []) or [])
    positions = [farm.get("farmer", [0, 0]), *list(farm.get("hands", []) or [])]
    orders = [action.get("farmer", ["PASS"]), *list(action.get("hands", []) or [])]
    access = access_tiles(len(farm.get("tiles", []) or []) or 10)
    actors = []
    for index, inventory in enumerate(inventories):
        carried = {str(k): max(0, int(v or 0)) for k, v in dict(inventory or {}).items() if int(v or 0) > 0}
        if not carried:
            continue
        actors.append({
            "actor": index,
            "position": positions[index],
            "distance": distance(positions[index], access),
            "order": list(orders[index] or ["PASS"]),
            "carried": carried,
            "units": sum(carried.values()),
        })
    projected = projected_shed(obs, action)
    planned = Counter()
    for order in action.get("market", []) or []:
        if order and order[0] == "SELL" and len(order) >= 3:
            planned[str(order[1])] += max(0, int(order[2] or 0))
    residual = {item: max(0, quantity - planned[item]) for item, quantity in projected.items()}
    return {
        "step": int(obs.get("step", 0) or 0),
        "actors": actors,
        "carried_units": sum(row["units"] for row in actors),
        "projected_units": sum(projected.values()),
        "planned_sell_units": sum(planned.values()),
        "executable_residual_units": sum(residual.values()),
        "market_slots": len(action.get("market", []) or []),
    }


def play(task: tuple[int, int]) -> list[dict]:
    seed, seat = task
    registry = Registry(path=HERE / "audit_registry.json", models={}, raw={})
    own = create_agent(registry, {"id": f"own_{seed}_{seat}_{os.getpid()}", "kind": "python", "path": str(POLICY), "entrypoint": "agent"})
    rival = create_agent(registry, {"id": f"rival_{seed}_{seat}_{os.getpid()}", "kind": "python", "path": str(POLICY), "entrypoint": "agent"})
    agents = [None, None]
    agents[seat], agents[1 - seat] = own, rival
    game = kagsim.Game(seed)
    rows = []
    while not game.done:
        observations = [game.observe(0), game.observe(1)]
        actions = [agents[0](observations[0]), agents[1](observations[1])]
        if int(observations[seat].get("step", 0) or 0) >= 712:
            rows.append({"seed": seed, "seat": seat, **snapshot(observations[seat], actions[seat])})
        game.step(actions[0], actions[1])
    return rows


def main() -> None:
    tasks = [(seed, seat) for seed in SEEDS for seat in (0, 1)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=min(16, os.cpu_count() or 1)) as pool:
        rows = [row for batch in pool.map(play, tasks, chunksize=1) for row in batch]
    by_step = defaultdict(list)
    for row in rows:
        by_step[row["step"]].append(row)
    summary = {}
    for step, values in sorted(by_step.items()):
        actor_rows = [actor for row in values for actor in row["actors"]]
        distance_units = Counter()
        order_units = Counter()
        distance_order_units = Counter()
        for actor in actor_rows:
            distance_units[int(actor["distance"])] += int(actor["units"])
            order_units[str(actor["order"][0])] += int(actor["units"])
            distance_order_units[f"d{int(actor['distance'])}:{str(actor['order'][0])}"] += int(actor["units"])
        summary[str(step)] = {
            "games": len(values),
            "games_with_carried": sum(row["carried_units"] > 0 for row in values),
            "carried_units": sum(row["carried_units"] for row in values),
            "distance_units": dict(sorted(distance_units.items())),
            "order_units": dict(sorted(order_units.items())),
            "distance_order_units": dict(sorted(distance_order_units.items())),
            "executable_residual_units": sum(row["executable_residual_units"] for row in values),
            "full_market_games": sum(row["market_slots"] >= 10 for row in values),
        }
    result = {
        "schema": "kaggriculture-v51-terminal-residual-audit-v1",
        "engine": str(kagsim.ENGINE_VERSION),
        "games": len(tasks),
        "summary": summary,
        "step718_carried_samples": [row for row in rows if row["step"] == 718 and row["carried_units"] > 0][:32],
    }
    (HERE / "terminal_residual_audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "step718_carried_samples"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
