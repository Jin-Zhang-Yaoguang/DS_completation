#!/usr/bin/env python3
"""RC9 read-only paired mechanism diagnosis on the exposed RC8 R3 panel."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import statistics
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
MODEL = HERE.parents[2]
RC8 = MODEL / "v116_heuristic_gold_search/rc8_parametric_search"
RUN = RC8 / "search/runs/rc8_r1r2r3_global_001"
R3_SUMMARY = RUN / "R3_summary.json"
RUN_MANIFEST = RUN / "run_manifest.json"
CANDIDATE = RC8 / "candidate/candidate.py"
V21 = MODEL / "v21_top_meta_moe/main.py"
CPPSIM = MODEL / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
ENGINE_VERSION = "1.32.7"

CROPS = {"WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"}
ANIMALS = {"GOOSE", "COW", "SHEEP"}
PRODUCTS = CROPS | {"EGG", "MILK", "WOOL", "FERTILIZER"}
ITEMS = PRODUCTS | ANIMALS
UNIT_NO_ARG = {
    "NORTH", "SOUTH", "EAST", "WEST", "PASS", "DROP", "WATER", "HARVEST",
    "FERTILIZE", "BUILD_COOP", "BUILD_PASTURE", "DIG", "FEED",
    "COLLECT_FERTILIZER", "CARE",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _sequence(value: Any) -> bool:
    return isinstance(value, (list, tuple))


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def validate_unit(order: Any, label: str) -> list[str]:
    if not _sequence(order) or not order:
        return [f"{label}:not_nonempty_sequence"]
    op = str(order[0])
    if op in UNIT_NO_ARG:
        return [] if len(order) == 1 else [f"{label}:{op}_arity"]
    if op == "PLANT":
        return [] if len(order) == 2 and str(order[1]) in CROPS else [f"{label}:PLANT_schema"]
    if op in {"PICKUP", "PLACE"}:
        valid = len(order) in {2, 3} and str(order[1]) in ITEMS
        valid = valid and (len(order) == 2 or _positive_int(order[2]))
        return [] if valid else [f"{label}:{op}_schema"]
    return [f"{label}:unknown_unit_op:{op}"]


def validate_market(order: Any, label: str) -> list[str]:
    if not _sequence(order) or not order:
        return [f"{label}:not_nonempty_sequence"]
    op = str(order[0])
    if op in {"HIRE", "BUY_LAND"}:
        return [] if len(order) == 1 else [f"{label}:{op}_arity"]
    if len(order) != 3 or not _positive_int(order[2]):
        return [f"{label}:{op}_schema:order={list(order)!r}"]
    item = str(order[1])
    allowed = {
        "SELL": PRODUCTS, "BUY_SEED": CROPS,
        "BUY_PRODUCT": {"WHEAT", "FERTILIZER"}, "BUY_ANIMAL": ANIMALS,
    }
    return ([] if op in allowed and item in allowed[op]
            else [f"{label}:unknown_market:{op}:{item}:order={list(order)!r}"])


def validate_action(action: Any, observation: Mapping[str, Any], seat: int) -> list[str]:
    if not isinstance(action, Mapping):
        return ["action:not_mapping"]
    farms = list(observation.get("farms", []) or [])
    expected_hands = len((farms[seat] if seat < len(farms) else {}).get("hands", []) or [])
    issues = validate_unit(action.get("farmer"), "farmer")
    hands = action.get("hands")
    if not _sequence(hands):
        issues.append("hands:not_sequence")
    else:
        if len(hands) != expected_hands:
            issues.append(f"hands:length:{len(hands)}!={expected_hands}")
        for index, order in enumerate(hands):
            issues.extend(validate_unit(order, f"hands[{index}]"))
    market = action.get("market")
    if not _sequence(market):
        issues.append("market:not_sequence")
    else:
        if len(market) > 10:
            issues.append(f"market:length:{len(market)}>10")
        for index, order in enumerate(market):
            issues.extend(validate_market(order, f"market[{index}]"))
    return issues


def idle_action(observation: Mapping[str, Any], seat: int) -> dict[str, Any]:
    farms = list(observation.get("farms", []) or [])
    hands = len((farms[seat] if seat < len(farms) else {}).get("hands", []) or [])
    return {"farmer": ["PASS"], "hands": [["PASS"] for _ in range(hands)], "market": []}


def load_runtime() -> tuple[Any, Any, Any]:
    builds = sorted((CPPSIM / "build").glob("lib.*/kagsim*.so"))
    if not builds:
        raise RuntimeError("cppsim build missing")
    for path in (FACTORY, builds[-1].parent):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    import kagsim  # type: ignore
    from agent_factory import Registry, create_agent  # type: ignore
    if str(getattr(kagsim, "ENGINE_VERSION", "")) != ENGINE_VERSION:
        raise RuntimeError(f"engine drift: {getattr(kagsim, 'ENGINE_VERSION', None)}")
    return kagsim, Registry, create_agent


def load_candidate(params: dict[str, Any], tag: str) -> Any:
    name = f"rc9_candidate_{os.getpid()}_{hashlib.sha256(tag.encode()).hexdigest()[:12]}"
    spec = importlib.util.spec_from_file_location(name, CANDIDATE)
    if spec is None or spec.loader is None:
        raise ImportError(CANDIDATE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    executor = module.build_executor(params, "router")
    if module.canonical_hash(params) != tag.split("__", 1)[0]:
        raise ValueError("p0064 parameter hash drift")
    return executor


def tile_counts(tiles: Sequence[Sequence[Any]]) -> tuple[dict[str, int], dict[str, int]]:
    crops: Counter[str] = Counter()
    animals: Counter[str] = Counter()
    for row in tiles:
        for tile in row:
            if not isinstance(tile, Mapping):
                continue
            if tile.get("kind") == "PLANT" and str(tile.get("crop")) in CROPS:
                crops[str(tile["crop"])] += 1
            animal = tile.get("animal")
            if animal:
                kind = animal.get("kind") if isinstance(animal, Mapping) else str(animal)
                if str(kind) in ANIMALS:
                    animals[str(kind)] += 1
    return dict(sorted(crops.items())), dict(sorted(animals.items()))


def public_farm(farm: Mapping[str, Any]) -> dict[str, Any]:
    crops, animals = tile_counts(list(farm.get("tiles", []) or []))
    return {
        "money": float(farm.get("money", 0) or 0),
        "crops": crops,
        "animals": animals,
        "land": len(farm.get("unlocked_quadrants", []) or []),
        "hands": len(farm.get("hands", []) or []),
    }


def count_actions(action: Mapping[str, Any], unit_counts: Counter[str],
                  market_counts: Counter[str], market_units: Counter[str]) -> None:
    for order in [action.get("farmer"), *list(action.get("hands", []) or [])]:
        if _sequence(order) and order:
            unit_counts[str(order[0])] += 1
    for order in list(action.get("market", []) or []):
        if not _sequence(order) or not order:
            continue
        op = str(order[0])
        item = str(order[1]) if len(order) > 1 else ""
        key = f"{op}:{item}" if item else op
        market_counts[key] += 1
        market_units[key] += int(order[2]) if len(order) > 2 and _positive_int(order[2]) else 1


def closing_snapshot(day: int, state: Mapping[str, Any], seat: int,
                     unit_counts: Counter[str], market_counts: Counter[str],
                     market_units: Counter[str], order_trace: list[dict[str, Any]],
                     terminal: bool) -> dict[str, Any]:
    farms = list(state.get("farms", []) or [{}, {}])
    private = state.get("private", {}) or {}
    market = state.get("market", {}) or {}
    return {
        "day": day,
        "terminal_boundary": terminal,
        "candidate_money": float(farms[seat].get("money", 0) or 0),
        "public_candidate": public_farm(farms[seat]),
        "public_opponent": public_farm(farms[1 - seat]),
        "market": {
            "inventory": {str(k): int(v or 0) for k, v in sorted((market.get("inventory", {}) or {}).items())},
            "prices": {str(k): float(v or 0) for k, v in sorted((market.get("prices", {}) or {}).items())},
        },
        "own": {
            "shed": {str(k): int(v or 0) for k, v in sorted((private.get("shed", {}) or {}).items())},
            "seeds": {str(k): int(v or 0) for k, v in sorted((private.get("seeds", {}) or {}).items())},
        },
        "candidate_unit_action_counts": dict(sorted(unit_counts.items())),
        "candidate_market_order_counts": dict(sorted(market_counts.items())),
        "candidate_market_order_units": dict(sorted(market_units.items())),
        "candidate_market_orders": order_trace,
    }


def error_row(task: Mapping[str, Any], error: str) -> dict[str, Any]:
    return {
        "task_id": task["task_id"], "opponent": task["opponent"],
        "seed": int(task["seed"]), "candidate_seat": int(task["seat"]),
        "status": "ERROR", "error": error, "calls": 0,
        "candidate_schema_violations": 0, "opponent_schema_violations": 0,
        "daily": [],
    }


def play(task: Mapping[str, Any]) -> dict[str, Any]:
    try:
        kagsim, Registry, create_agent = load_runtime()
        executor = load_candidate(dict(task["params"]), f"{task['param_hash']}__{task['task_id']}")
        opponent = None
        if task["opponent"] == "v21":
            registry = Registry(path=HERE / "runtime_registry.json", models={}, raw={})
            opponent = create_agent(registry, {
                "id": f"rc9_v21_{os.getpid()}_{task['seed']}_{task['seat']}",
                "kind": "python", "path": str(V21), "entrypoint": "agent",
            })
        game = kagsim.Game(int(task["seed"]))
        seat = int(task["seat"])
        calls = 0
        candidate_violations = 0
        opponent_violations = 0
        candidate_examples: list[str] = []
        opponent_examples: list[str] = []
        daily: list[dict[str, Any]] = []
        unit_counts: Counter[str] = Counter()
        market_counts: Counter[str] = Counter()
        market_units: Counter[str] = Counter()
        order_trace: list[dict[str, Any]] = []
        first_shop: str | None = None
        while not game.done:
            observations = [game.observe(0), game.observe(1)]
            own_obs, rival_obs = observations[seat], observations[1 - seat]
            day = int(own_obs.get("day", 0) or 0)
            hour = int(own_obs.get("hour", 0) or 0)
            shops = list(((own_obs.get("town") or {}).get("unlocked_shops", [])) or [])
            if first_shop is None and shops:
                first_shop = str(shops[0])
            own_action = executor.act(own_obs)
            rival_action = (opponent(rival_obs) if opponent is not None
                            else idle_action(rival_obs, 1 - seat))
            own_found = validate_action(own_action, own_obs, seat)
            rival_found = validate_action(rival_action, rival_obs, 1 - seat)
            candidate_violations += len(own_found)
            opponent_violations += len(rival_found)
            if len(candidate_examples) < 20:
                candidate_examples.extend(f"step={calls}:{x}" for x in own_found[:20-len(candidate_examples)])
            if len(opponent_examples) < 20:
                opponent_examples.extend(f"step={calls}:{x}" for x in rival_found[:20-len(opponent_examples)])
            count_actions(own_action, unit_counts, market_counts, market_units)
            if own_action.get("market"):
                order_trace.append({"step": calls, "hour": hour,
                                    "orders": [list(order) for order in own_action["market"]]})
            actions: list[Any] = [None, None]
            actions[seat], actions[1 - seat] = own_action, rival_action
            game.step(actions[0], actions[1])
            calls += 1
            boundary = hour == 23 or game.done
            if boundary:
                closing = game.observe(seat)
                daily.append(closing_snapshot(day, closing, seat, unit_counts, market_counts,
                                              market_units, order_trace, game.done))
                unit_counts, market_counts, market_units = Counter(), Counter(), Counter()
                order_trace = []
        rewards = [float(game.reward(0)), float(game.reward(1))]
        margin = rewards[seat] - rewards[1 - seat]
        return {
            "task_id": task["task_id"], "opponent": task["opponent"],
            "seed": int(task["seed"]), "candidate_seat": seat,
            "status": "DONE", "error": None, "calls": calls,
            "candidate_schema_violations": candidate_violations,
            "candidate_schema_examples": candidate_examples,
            "opponent_schema_violations": opponent_violations,
            "opponent_schema_examples": opponent_examples,
            "first_shop": first_shop or "NO_SHOP", "router_expert": executor.expert,
            "candidate_bank": rewards[seat], "opponent_bank": rewards[1 - seat],
            "margin": margin, "win": int(margin > 0), "tie": int(margin == 0),
            "loss": int(margin < 0), "daily": daily,
        }
    except BaseException as exc:
        return error_row(task, f"{type(exc).__name__}: {exc}")


def diff_map(gold: Mapping[str, Any], idle: Mapping[str, Any]) -> dict[str, float]:
    keys = sorted(set(gold) | set(idle))
    return {key: float(gold.get(key, 0) or 0) - float(idle.get(key, 0) or 0) for key in keys}


def paired_difference(gold: Mapping[str, Any], idle: Mapping[str, Any]) -> dict[str, Any]:
    idle_days = {int(row["day"]): row for row in idle["daily"]}
    gold_days = {int(row["day"]): row for row in gold["daily"]}
    days: list[dict[str, Any]] = []
    for day in sorted(set(idle_days) | set(gold_days)):
        g, i = gold_days[day], idle_days[day]
        days.append({
            "day": day,
            "candidate_money": float(g["candidate_money"]) - float(i["candidate_money"]),
            "public_candidate": {
                "crops": diff_map(g["public_candidate"]["crops"], i["public_candidate"]["crops"]),
                "animals": diff_map(g["public_candidate"]["animals"], i["public_candidate"]["animals"]),
                "land": int(g["public_candidate"]["land"]) - int(i["public_candidate"]["land"]),
                "hands": int(g["public_candidate"]["hands"]) - int(i["public_candidate"]["hands"]),
            },
            "public_opponent": {
                "crops": diff_map(g["public_opponent"]["crops"], i["public_opponent"]["crops"]),
                "animals": diff_map(g["public_opponent"]["animals"], i["public_opponent"]["animals"]),
                "land": int(g["public_opponent"]["land"]) - int(i["public_opponent"]["land"]),
                "hands": int(g["public_opponent"]["hands"]) - int(i["public_opponent"]["hands"]),
            },
            "market_inventory": diff_map(g["market"]["inventory"], i["market"]["inventory"]),
            "market_prices": diff_map(g["market"]["prices"], i["market"]["prices"]),
            "own_shed": diff_map(g["own"]["shed"], i["own"]["shed"]),
            "own_seeds": diff_map(g["own"]["seeds"], i["own"]["seeds"]),
            "candidate_unit_action_counts": diff_map(
                g["candidate_unit_action_counts"], i["candidate_unit_action_counts"]),
            "candidate_market_order_counts": diff_map(
                g["candidate_market_order_counts"], i["candidate_market_order_counts"]),
            "candidate_market_order_units": diff_map(
                g["candidate_market_order_units"], i["candidate_market_order_units"]),
        })
    return {
        "seed": gold["seed"], "candidate_seat": gold["candidate_seat"],
        "direction": "v21_minus_idle",
        "candidate_bank": float(gold["candidate_bank"]) - float(idle["candidate_bank"]),
        "opponent_bank": float(gold["opponent_bank"]) - float(idle["opponent_bank"]),
        "margin": float(gold["margin"]) - float(idle["margin"]),
        "daily": days,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--output", type=Path, default=HERE / "diagnosis_results.json")
    args = parser.parse_args()
    if not 1 <= args.workers <= 4:
        raise SystemExit("workers must be in [1,4]")
    r3 = json.loads(R3_SUMMARY.read_text(encoding="utf-8"))
    selected = [row for row in r3["results"] if str(row["config_id"]).startswith("p0064_")]
    if len(selected) != 1 or r3["results"][0]["config_id"] != selected[0]["config_id"]:
        raise SystemExit("R3 best p0064 is not uniquely first-ranked")
    config = selected[0]
    manifest = json.loads(RUN_MANIFEST.read_text(encoding="utf-8"))
    seed_rows = manifest["seed_panels"]["R3"]
    seeds = [int(row["seed"] if isinstance(row, Mapping) else row) for row in seed_rows]
    if len(seeds) != 2:
        raise SystemExit("R3 must expose exactly two seeds")
    tasks = [
        {"task_id": f"{opponent}__{seed}__s{seat}", "opponent": opponent,
         "seed": seed, "seat": seat, "params": config["params"],
         "param_hash": config["param_hash"]}
        for opponent in ("idle", "v21") for seed in seeds for seat in (0, 1)
    ]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(play, tasks))
    rows.sort(key=lambda row: (row["opponent"], row["seed"], row["candidate_seat"]))
    indexed = {(row["opponent"], row["seed"], row["candidate_seat"]): row for row in rows}
    pairs: list[dict[str, Any]] = []
    if all(row["status"] == "DONE" for row in rows):
        for seed in seeds:
            for seat in (0, 1):
                pairs.append(paired_difference(indexed[("v21", seed, seat)],
                                               indexed[("idle", seed, seat)]))
    done = [row for row in rows if row["status"] == "DONE"]
    by_opponent: dict[str, Any] = {}
    for opponent in ("idle", "v21"):
        subset = [row for row in rows if row["opponent"] == opponent]
        completed = [row for row in subset if row["status"] == "DONE"]
        by_opponent[opponent] = {
            "planned": 4, "completed": len(completed),
            "errors": 4 - len(completed),
            "all_719_calls": all(row.get("calls") == 719 and row["status"] == "DONE" for row in subset),
            "candidate_schema_violations": sum(row["candidate_schema_violations"] for row in subset),
            "opponent_schema_violations": sum(row["opponent_schema_violations"] for row in subset),
            "mean_candidate_bank": statistics.mean(row["candidate_bank"] for row in completed) if completed else None,
            "mean_margin": statistics.mean(row["margin"] for row in completed) if completed else None,
        }
    payload = {
        "schema": "v116-rc9-opponent-path-diagnosis-v1",
        "purpose": "mechanism_diagnosis_only_not_advancement",
        "source": {
            "r3_summary": str(R3_SUMMARY), "r3_summary_sha256": sha256_file(R3_SUMMARY),
            "candidate": str(CANDIDATE), "candidate_sha256": sha256_file(CANDIDATE),
            "v21": str(V21), "v21_sha256": sha256_file(V21),
            "config_id": config["config_id"], "param_hash": config["param_hash"],
            "params": config["params"], "r3_exposed_seeds": seeds,
        },
        "contract": {"opponents": ["idle", "v21"], "both_seats": True,
                     "planned_games": 8, "workers": args.workers,
                     "uses_development": False, "uses_confirmation": False},
        "summary": {
            "planned_games": 8, "completed_games": len(done),
            "errors": 8 - len(done), "by_opponent": by_opponent,
            "all_719_calls": len(done) == 8 and all(row["calls"] == 719 for row in rows),
            "candidate_schema_violations": sum(row["candidate_schema_violations"] for row in rows),
            "opponent_schema_violations": sum(row["opponent_schema_violations"] for row in rows),
            "mean_paired_v21_minus_idle_candidate_bank": (
                statistics.mean(pair["candidate_bank"] for pair in pairs) if pairs else None),
            "mean_paired_v21_minus_idle_margin": (
                statistics.mean(pair["margin"] for pair in pairs) if pairs else None),
        },
        "games": rows,
        "paired_v21_minus_idle": pairs,
        "decision": "DIAGNOSTIC_ONLY_NOT_AN_ADVANCEMENT_RESULT",
    }
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({"summary": payload["summary"], "decision": payload["decision"]},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
