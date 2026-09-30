#!/usr/bin/env python3
"""Extract executable daily task DAGs and worker tours from the two V17 routes.

The replay observation immediately before an action supplies the absolute tile
of every worker.  This lets the online repairer reason about a missed service
without attempting to regenerate the successful farm blueprint.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parents[1]
ROOT = HERE.parents[4]
DATA = ROOT / "kaggle_Kaggriculture" / "model_data" / "kaggriculture_episodes_index" / "date=2026-08-25" / "data"
FROZEN_PARENT = RESEARCH / "top_complete_portfolio" / "main.py"
FROZEN_SHA256 = "b52e62545fb6bdc93f9e947f9a829e348dd6119ee9daf7d8eba7df9aec29a4b1"

ROUTES = {
    "default": {"prefix": ("tyz123456", 99609968), "tail": ("tyz123456", 99609968), "split": 72},
    "yarn": {"prefix": ("tyz123456", 99609968), "tail": ("Kronki", 99596430), "split": 72},
}

SERVICE = {
    "DIG", "PLANT", "WATER", "HARVEST", "FERTILIZE", "BUILD_COOP",
    "BUILD_PASTURE", "FEED", "CARE", "COLLECT_FERTILIZER", "PLACE",
    "PICKUP", "DROP",
}
DAILY_DEADLINE = {"DIG", "PLANT", "WATER", "FEED", "CARE", "PLACE"}
VALUE = {
    "DIG": 35, "PLANT": 45, "WATER": 80, "HARVEST": 95,
    "FERTILIZE": 15, "BUILD_COOP": 65, "BUILD_PASTURE": 65,
    "FEED": 85, "CARE": 20, "COLLECT_FERTILIZER": 12,
    "PLACE": 75, "PICKUP": 20, "DROP": 20,
}


def _load(team: str, episode: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    replay = json.loads((DATA / f"{episode}.json").read_text())
    seat = replay["info"]["TeamNames"].index(team)
    actions = [copy.deepcopy(pair[seat].get("action") or {}) for pair in replay["steps"][1:720]]
    # action[t] transforms replay observation t into observation t+1.
    observations = [copy.deepcopy(pair[seat].get("observation") or {}) for pair in replay["steps"][:719]]
    return actions, observations


def load_frozen_parent():
    digest = hashlib.sha256(FROZEN_PARENT.read_bytes()).hexdigest()
    if digest != FROZEN_SHA256:
        raise RuntimeError(f"frozen V17 parent hash mismatch: {digest}")
    spec = importlib.util.spec_from_file_location(f"v17_frozen_{uuid.uuid4().hex}", FROZEN_PARENT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


_FROZEN = load_frozen_parent()


def route_stream(name: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cfg = ROUTES[name]
    pa, po = _load(*cfg["prefix"])
    ta, to = _load(*cfg["tail"])
    split = int(cfg["split"])
    replay_actions = pa[:split] + ta[split:]
    exact_actions = copy.deepcopy(_FROZEN._PORT_YARN if name == "yarn" else _FROZEN._PORT_DEFAULT)
    if replay_actions != exact_actions:
        bad = [i for i, (a, b) in enumerate(zip(replay_actions, exact_actions)) if a != b]
        raise RuntimeError(f"{name} route provenance mismatch at {bad[:5]}")
    return exact_actions, po[:split] + to[split:]


def _position(obs: dict[str, Any], actor: int) -> list[int] | None:
    seat = int(obs.get("player", 0) or 0)
    farm = obs["farms"][seat]
    positions = [farm.get("farmer"), *(farm.get("hands") or [])]
    if actor >= len(positions) or not positions[actor]:
        return None
    return [int(positions[actor][0]), int(positions[actor][1])]


def extract(name: str) -> dict[str, Any]:
    actions, observations = route_stream(name)
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    last_actor: dict[tuple[int, int], str] = {}
    last_build: dict[tuple[int, int], str] = {}
    last_pickup: dict[tuple[int, str], str] = {}
    last_harvest: dict[str, str] = {}
    last_buy: dict[str, str] = {}

    for step, (action, obs) in enumerate(zip(actions, observations)):
        day, hour = divmod(step, 24)
        orders = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
        for actor, order in enumerate(orders):
            if not order or order[0] not in SERVICE:
                continue
            op = str(order[0])
            pos = _position(obs, actor)
            node_id = f"{name}:s{step}:u{actor}:{op}"
            node = {
                "id": node_id, "route": name, "step": step, "day": day,
                "hour": hour, "actor": actor, "position": pos,
                "order": list(order), "release": step,
                "deadline": day * 24 + (23 if op in DAILY_DEADLINE else 24),
                "value": VALUE.get(op, 1),
            }
            nodes.append(node)
            tour_key = (day, actor)
            if tour_key in last_actor:
                edges.append({"from": last_actor[tour_key], "to": node_id, "kind": "worker_tour"})
            last_actor[tour_key] = node_id
            if pos is not None:
                tile_key = tuple(pos)
                if op.startswith("BUILD_"):
                    last_build[tile_key] = node_id
                elif op == "PLACE" and tile_key in last_build:
                    edges.append({"from": last_build[tile_key], "to": node_id, "kind": "build_before_place"})
            item = str(order[1]) if len(order) > 1 else ""
            if op == "PICKUP" and item:
                last_pickup[(actor, item)] = node_id
            elif op in {"FEED", "PLACE"}:
                need = "WHEAT" if op == "FEED" else item
                if (actor, need) in last_pickup:
                    edges.append({"from": last_pickup[(actor, need)], "to": node_id, "kind": "inventory_before_service"})
            if op == "PLANT" and item in last_buy:
                edges.append({"from": last_buy[item], "to": node_id, "kind": "seed_before_plant"})
            if op == "HARVEST" and pos is not None:
                # Crop is observable in the pre-action replay state.
                seat = int(obs.get("player", 0) or 0)
                tile = obs["farms"][seat]["tiles"][pos[1]][pos[0]]
                crop = tile.get("crop") if isinstance(tile, dict) else None
                if crop:
                    last_harvest[str(crop)] = node_id

        for slot, order in enumerate(action.get("market") or []):
            if not order:
                continue
            op = str(order[0])
            node_id = f"{name}:s{step}:m{slot}:{op}"
            node = {
                "id": node_id, "route": name, "step": step, "day": day,
                "hour": hour, "actor": "market", "position": None,
                "order": list(order), "release": step, "deadline": step,
                "value": 0,
            }
            nodes.append(node)
            item = str(order[1]) if len(order) > 1 else ""
            if op == "BUY_SEED" and item:
                last_buy[item] = node_id
            elif op == "SELL" and item in last_harvest:
                edges.append({"from": last_harvest[item], "to": node_id, "kind": "harvest_before_sell"})

    by_step: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for node in nodes:
        if node["actor"] != "market":
            by_step[str(node["step"])].append(node)
    return {
        "route": name,
        "source": ROUTES[name],
        "nodes": nodes,
        "edges": edges,
        "by_step": dict(by_step),
        "counts": {
            "nodes": len(nodes), "edges": len(edges),
            "worker_service_nodes": sum(n["actor"] != "market" for n in nodes),
            "market_nodes": sum(n["actor"] == "market" for n in nodes),
        },
    }


def build_all() -> dict[str, Any]:
    return {
        "schema": "kaggriculture-v18-task-dag-v1",
        "contract": "V17 production blueprint is immutable; DAG is used only for local recovery.",
        "frozen_parent": {"path": str(FROZEN_PARENT), "sha256": FROZEN_SHA256},
        "routes": {name: extract(name) for name in ROUTES},
    }


def main() -> None:
    payload = build_all()
    (HERE / "task_dag.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v["counts"] for k, v in payload["routes"].items()}, indent=2))


if __name__ == "__main__":
    main()
