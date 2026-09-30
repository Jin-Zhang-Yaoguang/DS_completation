#!/usr/bin/env python3
"""Reproducible P2/P3 arena for the R10 Enterprise Queue HMoE.

This evaluator never reads Replay data and never imports a historical policy
into the candidate.  Each task constructs one fresh candidate executor and one
fresh opponent, then runs both policies live against kagsim 1.32.7.
"""

from __future__ import annotations

import argparse
import concurrent.futures
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import statistics
import sys
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
R10_ROOT = HERE.parent
MODEL_ROOT = R10_ROOT.parents[1]
CPPSIM = MODEL_ROOT / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
FACTORY_ROOT = MODEL_ROOT / "v10_replay_lolo_router"
ENGINE_VERSION = "1.32.7"

MODES = (
    "router",
    "fixed_root_exchange",
    "fixed_dairy_berry",
    "fixed_fiber_grain",
)
FIXED_MODES = MODES[1:]
P2_SEEDS = (7100, 7101, 7102, 7103, 1641819451, 915926955)
P3_SEEDS = (1641819451, 915926955)

GOLD_POOL: dict[str, Path] = {
    "v19": MODEL_ROOT / "v19_hierarchical_moe/main.py",
    "v20": MODEL_ROOT / "v20_demand_timing_moe/main.py",
    "v21": MODEL_ROOT / "v21_top_meta_moe/main.py",
    "v32": MODEL_ROOT / "v32_clone_horizon_preempt/main.py",
    "v33": MODEL_ROOT / "v33_demand_gap_horizon4/main.py",
    "v34": MODEL_ROOT / "v34_demand_boundary_preempt/main.py",
    "v37": MODEL_ROOT / "v37_preterminal_boundary_preempt/main.py",
    "v46": MODEL_ROOT / "v46_full_terminal_front_run/main.py",
    "v51": MODEL_ROOT / "v51_post_action_terminal_sell/main.py",
    "v52": MODEL_ROOT / "v52_terminal_route_acceleration/main.py",
    "v53": MODEL_ROOT / "v53_terminal_access_flush/main.py",
    "v54": MODEL_ROOT / "v54_terminal_water_bypass/main.py",
    "v66": MODEL_ROOT / "v66_margin_gated_sell_bubble/main.py",
    "v70": MODEL_ROOT / "v70_duplicate_wheat_buy_lead/main.py",
    "v71": MODEL_ROOT / "v71_duplicate_wheat_buy_lead_50/main.py",
    "v72": MODEL_ROOT / "v72_duplicate_wheat_buy_lead_75/main.py",
    "v73": MODEL_ROOT / "v73_duplicate_wheat_buy_full_merge/main.py",
    "v76": MODEL_ROOT / "v76_adjacent_safe_buy_lead/main.py",
}

PRODUCTS = {"WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"}
CROPS = {"WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"}
ANIMALS = {"GOOSE", "COW", "SHEEP"}
ITEMS = PRODUCTS | ANIMALS
UNIT_NO_ARG = {
    "NORTH", "SOUTH", "EAST", "WEST", "PASS", "DROP", "WATER", "HARVEST",
    "FERTILIZE", "BUILD_COOP", "BUILD_PASTURE", "DIG", "FEED",
    "COLLECT_FERTILIZER", "CARE",
}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"),
        allow_nan=False, default=str,
    ).encode("utf-8")


def hash_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_python_tree(root: Path) -> str:
    records = []
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        records.append((str(path.relative_to(root)), sha256_file(path)))
    if not records:
        raise ValueError(f"no Python files under {root}")
    return hash_value(records)


def _is_sequence(value: Any) -> bool:
    return isinstance(value, (list, tuple))


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def validate_unit(order: Any, label: str) -> list[str]:
    if not _is_sequence(order) or not order:
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
    if not _is_sequence(order) or not order:
        return [f"{label}:not_nonempty_sequence"]
    op = str(order[0])
    if op in {"HIRE", "BUY_LAND"}:
        return [] if len(order) == 1 else [f"{label}:{op}_arity"]
    if len(order) != 3 or not _positive_int(order[2]):
        return [f"{label}:{op}_schema"]
    item = str(order[1])
    allowed = {
        "SELL": PRODUCTS,
        "BUY_SEED": CROPS,
        "BUY_PRODUCT": {"WHEAT", "FERTILIZER"},
        "BUY_ANIMAL": ANIMALS,
    }
    return [] if op in allowed and item in allowed[op] else [f"{label}:unknown_market_order:{op}:{item}"]


def validate_action(action: Any, observation: Mapping[str, Any]) -> list[str]:
    if not isinstance(action, Mapping):
        return ["action:not_mapping"]
    seat = 1 if int(observation.get("player", 0) or 0) == 1 else 0
    farms = list(observation.get("farms", []) or [])
    expected_hands = len((farms[seat] if seat < len(farms) else {}).get("hands", []) or [])
    issues = validate_unit(action.get("farmer"), "farmer")
    hands = action.get("hands")
    if not _is_sequence(hands):
        issues.append("hands:not_sequence")
    else:
        if len(hands) != expected_hands:
            issues.append(f"hands:length:{len(hands)}!={expected_hands}")
        for index, order in enumerate(hands):
            issues.extend(validate_unit(order, f"hands[{index}]"))
    market = action.get("market")
    if not _is_sequence(market):
        issues.append("market:not_sequence")
    else:
        if len(market) > 10:
            issues.append(f"market:length:{len(market)}>10")
        for index, order in enumerate(market):
            issues.extend(validate_market(order, f"market[{index}]"))
    return issues


def idle_action(observation: Mapping[str, Any]) -> dict[str, Any]:
    seat = 1 if int(observation.get("player", 0) or 0) == 1 else 0
    farms = list(observation.get("farms", []) or [])
    hands = len((farms[seat] if seat < len(farms) else {}).get("hands", []) or [])
    return {"farmer": ["PASS"], "hands": [["PASS"] for _ in range(hands)], "market": []}


def load_runtime() -> tuple[Any, Any, Any, Path]:
    builds = sorted((CPPSIM / "build").glob("lib.*/kagsim*.so"))
    if not builds:
        raise RuntimeError(f"missing kagsim under {CPPSIM / 'build'}")
    build = builds[-1]
    for path in (FACTORY_ROOT, build.parent):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    import kagsim  # type: ignore
    from agent_factory import Registry, create_agent  # type: ignore

    actual = str(getattr(kagsim, "ENGINE_VERSION", ""))
    if actual != ENGINE_VERSION:
        raise RuntimeError(f"engine drift: expected {ENGINE_VERSION}, got {actual}")
    return kagsim, Registry, create_agent, build


def load_candidate_executor(candidate_path: str, mode: str, tag: str) -> Any:
    path = Path(candidate_path).resolve()
    module_name = f"r10_candidate_{os.getpid()}_{hashlib.sha256(tag.encode()).hexdigest()[:16]}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot import candidate: {path}")
    old_path = list(sys.path)
    sys.path.insert(0, str(path.parent))
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
        builder = getattr(module, "build_executor", None)
        if not callable(builder):
            raise AttributeError("candidate must expose build_executor(params=None, mode=...)")
        executor = builder(params=None, mode=str(mode))
        if not callable(getattr(executor, "act", None)):
            raise TypeError("build_executor must return object with act(observation)")
        return executor
    finally:
        sys.path[:] = old_path
        sys.modules.pop(module_name, None)


def _terminal_assets(observation: Mapping[str, Any], seat: int) -> dict[str, Any]:
    farms = list(observation.get("farms", []) or [])
    farm = farms[seat] if seat < len(farms) else {}
    crops: dict[str, int] = {}
    animals: dict[str, int] = {}
    structures: dict[str, int] = {}
    weeds = 0
    for row in farm.get("tiles", []) or []:
        for tile in row or []:
            if not isinstance(tile, Mapping):
                continue
            kind = str(tile.get("kind") or "")
            crop = tile.get("crop")
            if kind == "PLANT" and crop:
                crops[str(crop)] = crops.get(str(crop), 0) + 1
            if kind in {"COOP", "PASTURE"}:
                structures[kind] = structures.get(kind, 0) + 1
            if kind == "WEED":
                weeds += 1
            animal = tile.get("animal")
            if animal:
                animal_kind = animal.get("kind") if isinstance(animal, Mapping) else animal
                animals[str(animal_kind)] = animals.get(str(animal_kind), 0) + 1
    return {
        "production_assets": sum(crops.values()) + sum(animals.values()),
        "crops": dict(sorted(crops.items())),
        "animals": dict(sorted(animals.items())),
        "structures": dict(sorted(structures.items())),
        "weeds": weeds,
        "hands": len(farm.get("hands", []) or []),
        "unlocked_quadrants": list(farm.get("unlocked_quadrants", []) or []),
    }


def _diagnostics(executor: Any) -> dict[str, Any]:
    method = getattr(executor, "diagnostics", None)
    if not callable(method):
        return {"available": False}
    try:
        value = method()
        return dict(value) if isinstance(value, Mapping) else {"available": True, "value": value}
    except BaseException as exc:
        return {"available": False, "error": f"{type(exc).__name__}: {exc}"}


def error_row(task: Mapping[str, Any], error: str, calls: int = 0) -> dict[str, Any]:
    return {
        "schema": "v116-r10-arena-game-v1",
        "task_id": str(task["task_id"]),
        "panel": str(task["panel"]),
        "mode": str(task["mode"]),
        "opponent": str(task["opponent"]),
        "seed": int(task["seed"]),
        "candidate_seat": int(task["candidate_seat"]),
        "status": "ERROR",
        "error": error,
        "calls": int(calls),
        "candidate_schema_violations": 0,
        "opponent_schema_violations": 0,
        "win": 0,
        "tie": 0,
        "loss": 0,
        "score": 0.0,
    }


def play_task(task: Mapping[str, Any]) -> dict[str, Any]:
    calls = 0
    try:
        kagsim, Registry, create_agent, _build = load_runtime()
        executor = load_candidate_executor(str(task["candidate_path"]), str(task["mode"]), str(task["task_id"]))
        opponent_path = task.get("opponent_path")
        opponent = None
        if opponent_path:
            registry = Registry(path=HERE / "runtime_registry.json", models={}, raw={})
            opponent = create_agent(registry, {
                "id": f"r10_opp_{os.getpid()}_{hashlib.sha256(str(task['task_id']).encode()).hexdigest()[:12]}",
                "kind": "python",
                "path": str(opponent_path),
                "entrypoint": "agent",
            })
        game = kagsim.Game(int(task["seed"]))
        seat = int(task["candidate_seat"])
        candidate_violations = 0
        opponent_violations = 0
        candidate_examples: list[str] = []
        opponent_examples: list[str] = []
        shops: list[str] = []
        while not game.done:
            observations = [game.observe(0), game.observe(1)]
            current_shops = list(((observations[seat].get("town") or {}).get("unlocked_shops", [])) or [])
            if len(current_shops) > len(shops):
                shops = [str(item) for item in current_shops]
            own_action = executor.act(observations[seat])
            rival_action = opponent(observations[1 - seat]) if opponent else idle_action(observations[1 - seat])
            own_issues = validate_action(own_action, observations[seat])
            rival_issues = validate_action(rival_action, observations[1 - seat])
            candidate_violations += len(own_issues)
            opponent_violations += len(rival_issues)
            if len(candidate_examples) < 20:
                candidate_examples.extend(f"step={calls}:{item}" for item in own_issues[:20 - len(candidate_examples)])
            if len(opponent_examples) < 20:
                opponent_examples.extend(f"step={calls}:{item}" for item in rival_issues[:20 - len(opponent_examples)])
            actions = [None, None]
            actions[seat], actions[1 - seat] = own_action, rival_action
            game.step(actions[0], actions[1])
            calls += 1
        terminal_observation = game.observe(seat)
        rewards = [float(game.reward(0)), float(game.reward(1))]
        own, rival = rewards[seat], rewards[1 - seat]
        margin = own - rival
        return {
            **error_row(task, "uninitialised", calls),
            "status": "DONE",
            "error": None,
            "candidate_schema_violations": candidate_violations,
            "opponent_schema_violations": opponent_violations,
            "candidate_schema_examples": candidate_examples,
            "opponent_schema_examples": opponent_examples,
            "shops": shops,
            "own_bank": own,
            "opponent_bank": rival,
            "margin": margin,
            "win": int(margin > 0),
            "tie": int(margin == 0),
            "loss": int(margin < 0),
            "score": int(margin > 0) + 0.5 * int(margin == 0),
            "terminal": _terminal_assets(terminal_observation, seat),
            "diagnostics": _diagnostics(executor),
        }
    except BaseException as exc:
        return error_row(task, f"{type(exc).__name__}: {exc}", calls)


def lower_cvar(values: Sequence[float], alpha: float) -> float | None:
    if not values:
        return None
    count = max(1, math.ceil(alpha * len(values)))
    return statistics.mean(sorted(float(value) for value in values)[:count])


def aggregate(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    planned = len(rows)
    done = [row for row in rows if row.get("status") == "DONE"]
    banks = [float(row["own_bank"]) for row in done]
    margins = [float(row["margin"]) for row in done]
    assets = [int((row.get("terminal") or {}).get("production_assets", 0)) for row in done]
    wins = sum(int(row.get("win", 0)) for row in rows)
    ties = sum(int(row.get("tie", 0)) for row in rows)
    return {
        "planned_games": planned,
        "completed_games": len(done),
        "errors_as_nonwins": planned - len(done),
        "wins": wins,
        "ties": ties,
        "losses": sum(int(row.get("loss", 0)) for row in rows),
        "pure_win_rate": wins / planned if planned else 0.0,
        "score_rate": (wins + 0.5 * ties) / planned if planned else 0.0,
        "mean_bank_completed": statistics.mean(banks) if banks else None,
        "cvar25_bank_completed": lower_cvar(banks, 0.25),
        "mean_margin_completed": statistics.mean(margins) if margins else None,
        "median_margin_completed": statistics.median(margins) if margins else None,
        "minimum_terminal_production_assets": min(assets) if assets else None,
        "mean_terminal_production_assets": statistics.mean(assets) if assets else None,
        "candidate_schema_violations": sum(int(row.get("candidate_schema_violations", 0)) for row in rows),
        "opponent_schema_violations": sum(int(row.get("opponent_schema_violations", 0)) for row in rows),
        "all_719_calls": planned > 0 and all(
            row.get("status") == "DONE" and int(row.get("calls", 0)) == 719 for row in rows
        ),
    }


def grouped(rows: Sequence[Mapping[str, Any]], key: str) -> dict[str, Any]:
    values = sorted({str(row.get(key, "UNCLASSIFIED")) for row in rows})
    return {value: aggregate([row for row in rows if str(row.get(key, "UNCLASSIFIED")) == value]) for value in values}


def summarize(rows: Sequence[Mapping[str, Any]], panel: str) -> dict[str, Any]:
    overall = aggregate(rows)
    by_mode = grouped(rows, "mode")
    by_seat = grouped(rows, "candidate_seat")
    by_opponent = grouped(rows, "opponent")
    mechanics_ok = bool(
        overall["errors_as_nonwins"] == 0
        and overall["candidate_schema_violations"] == 0
        and overall["all_719_calls"]
    )
    payload: dict[str, Any] = {
        "schema": "v116-r10-arena-summary-v1",
        "panel": panel,
        "overall": overall,
        "by_mode": by_mode,
        "by_seat": by_seat,
        "by_opponent": by_opponent,
        "mechanics_ok": mechanics_ok,
        "opponent_schema_is_diagnostic_only": True,
    }
    if panel == "p3":
        payload["p3_special"] = p3_special(rows, by_mode)
    return payload


def p3_special(rows: Sequence[Mapping[str, Any]], by_mode: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    index = {
        (str(row["mode"]), str(row["opponent"]), int(row["seed"]), int(row["candidate_seat"])): row
        for row in rows
    }
    matchup_keys = sorted({(str(row["opponent"]), int(row["seed"]), int(row["candidate_seat"])) for row in rows})
    fixed_rank = sorted(
        FIXED_MODES,
        key=lambda mode: (
            float(by_mode.get(mode, {}).get("pure_win_rate", 0.0)),
            float(by_mode.get(mode, {}).get("median_margin_completed") or -math.inf),
            mode,
        ),
        reverse=True,
    )
    best_fixed = fixed_rank[0]
    exclusive = {}
    for mode in FIXED_MODES:
        count = 0
        for opponent, seed, seat in matchup_keys:
            own = index.get((mode, opponent, seed, seat), {})
            others = [index.get((other, opponent, seed, seat), {}) for other in FIXED_MODES if other != mode]
            count += int(int(own.get("win", 0)) == 1 and not any(int(row.get("win", 0)) for row in others))
        exclusive[mode] = count
    oracle_wins = sum(
        int(any(int(index.get((mode, opponent, seed, seat), {}).get("win", 0)) for mode in FIXED_MODES))
        for opponent, seed, seat in matchup_keys
    )
    positive_flips = sum(
        int(
            int(index.get(("router", opponent, seed, seat), {}).get("win", 0)) == 1
            and int(index.get((best_fixed, opponent, seed, seat), {}).get("win", 0)) == 0
        )
        for opponent, seed, seat in matchup_keys
    )
    router_opponent_margins = {}
    for opponent in GOLD_POOL:
        values = [
            float(row["margin"]) for row in rows
            if row.get("status") == "DONE" and row.get("mode") == "router" and row.get("opponent") == opponent
        ]
        router_opponent_margins[opponent] = statistics.median(values) if values else None
    return {
        "matchups": len(matchup_keys),
        "best_fixed_mode": best_fixed,
        "best_fixed_pure_win_rate": float(by_mode.get(best_fixed, {}).get("pure_win_rate", 0.0)),
        "fixed_exclusive_wins": exclusive,
        "fixed_outcome_oracle_wins": oracle_wins,
        "fixed_outcome_oracle_pure_win_rate": oracle_wins / len(matchup_keys) if matchup_keys else 0.0,
        "router_positive_flips_vs_best_fixed": positive_flips,
        "router_opponent_median_margins": router_opponent_margins,
        "router_positive_opponent_medians": sum(int(value is not None and value > 0) for value in router_opponent_margins.values()),
    }


def decide(summary: Mapping[str, Any]) -> dict[str, Any]:
    panel = str(summary["panel"])
    by_mode = summary["by_mode"]
    failures: list[str] = []
    if not summary.get("mechanics_ok"):
        failures.append("mechanics_not_clean")
    if panel == "p2":
        for mode in FIXED_MODES:
            value = by_mode.get(mode, {}).get("mean_bank_completed")
            if value is None or float(value) < 90_000:
                failures.append(f"{mode}_mean_bank_below_90000")
        router = by_mode.get("router", {})
        if router.get("mean_bank_completed") is None or float(router["mean_bank_completed"]) < 100_000:
            failures.append("router_mean_bank_below_100000")
        if router.get("cvar25_bank_completed") is None or float(router["cvar25_bank_completed"]) < 80_000:
            failures.append("router_cvar25_bank_below_80000")
        minimum_assets = summary["overall"].get("minimum_terminal_production_assets")
        if minimum_assets is None or int(minimum_assets) < 58:
            failures.append("minimum_terminal_production_assets_below_58")
        passed = not failures
        status = "PASS_P2_ECONOMIC_HEALTH_NOT_GOLD" if passed else "REJECT_P2_ECONOMIC_HEALTH"
    elif panel == "p3":
        special = summary["p3_special"]
        for mode, wins in special["fixed_exclusive_wins"].items():
            if int(wins) < 2:
                failures.append(f"{mode}_exclusive_wins_below_2")
        if float(special["best_fixed_pure_win_rate"]) < 0.35:
            failures.append("best_fixed_pure_win_rate_below_0.35")
        if float(special["fixed_outcome_oracle_pure_win_rate"]) < 0.80:
            failures.append("fixed_outcome_oracle_pure_win_rate_below_0.80")
        router = by_mode.get("router", {})
        if float(router.get("pure_win_rate", 0.0)) < 0.70:
            failures.append("router_pure_win_rate_below_0.70")
        if router.get("mean_bank_completed") is None or float(router["mean_bank_completed"]) < 110_000:
            failures.append("router_mean_bank_below_110000")
        if int(special["router_positive_opponent_medians"]) < 12:
            failures.append("router_positive_opponent_medians_below_12")
        if float(router.get("pure_win_rate", 0.0)) <= float(special["best_fixed_pure_win_rate"]):
            failures.append("router_not_strictly_better_than_best_fixed")
        if int(special["router_positive_flips_vs_best_fixed"]) < 1:
            failures.append("router_has_no_positive_flip_vs_best_fixed")
        passed = not failures
        status = "PASS_P3_MECHANISM_NOT_GOLD" if passed else "REJECT_P3_MECHANISM"
    else:
        raise ValueError(f"unsupported panel: {panel}")
    return {
        "schema": "v116-r10-arena-decision-v1",
        "panel": panel,
        "status": status,
        "passed": passed,
        "failures": failures,
        "errors_are_nonwins": True,
        "gold_evidence": False,
        "gold_registration_authorized": False,
        "next_step": "P3 exposed gold panel" if passed and panel == "p2" else (
            "Replay development panels, only under separately frozen Replay protocol" if passed else
            "revise R10 executor/experts using exposed evidence; do not open Replay frozen panels"
        ),
    }


def build_tasks(panel: str, candidate: Path) -> list[dict[str, Any]]:
    if panel == "p2":
        seeds = P2_SEEDS
        opponents: dict[str, Path | None] = {"idle": None}
    elif panel == "p3":
        seeds = P3_SEEDS
        opponents = dict(GOLD_POOL)
    else:
        raise ValueError(f"unsupported panel: {panel}")
    tasks = []
    for mode in MODES:
        for opponent, path in opponents.items():
            for seed in seeds:
                for seat in (0, 1):
                    task_id = f"{panel}__{mode}__{opponent}__{seed}__s{seat}"
                    tasks.append({
                        "task_id": task_id,
                        "panel": panel,
                        "mode": mode,
                        "opponent": opponent,
                        "opponent_path": str(path) if path is not None else None,
                        "seed": seed,
                        "candidate_seat": seat,
                        "candidate_path": str(candidate),
                    })
    return tasks


def make_manifest(panel: str, candidate: Path, workers: int, tasks: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    kagsim, _registry, _create_agent, build = load_runtime()
    opponent_paths: dict[str, Path | None] = {"idle": None} if panel == "p2" else dict(GOLD_POOL)
    opponents = {
        name: ({"kind": "deterministic_idle", "version": "idle-v1"} if path is None else {
            "kind": "python",
            "path": str(path),
            "entrypoint_sha256": sha256_file(path),
            "python_tree_sha256": sha256_python_tree(path.parent),
        })
        for name, path in opponent_paths.items()
    }
    manifest = {
        "schema": "v116-r10-arena-manifest-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "panel": panel,
        "candidate": str(candidate),
        "candidate_tree_sha256": sha256_python_tree(candidate.parent),
        "evaluator": str(Path(__file__).resolve()),
        "evaluator_sha256": sha256_file(Path(__file__).resolve()),
        "engine_version": str(getattr(kagsim, "ENGINE_VERSION", "")),
        "engine_binary": str(build),
        "engine_binary_sha256": sha256_file(build),
        "agent_factory": str(FACTORY_ROOT / "agent_factory.py"),
        "agent_factory_sha256": sha256_file(FACTORY_ROOT / "agent_factory.py"),
        "workers": workers,
        "worker_limit": 8,
        "modes": list(MODES),
        "seeds": list(P2_SEEDS if panel == "p2" else P3_SEEDS),
        "opponents": opponents,
        "both_seats": True,
        "planned_games": len(tasks),
        "errors_are_nonwins": True,
        "candidate_interface": "build_executor(params=None, mode=mode).act(current_observation)",
        "boundary": "live kagsim only; no Replay input; no historical candidate parent/wrapper",
        "gold_evidence": False,
    }
    manifest["run_fingerprint"] = hash_value({key: value for key, value in manifest.items() if key != "created_at_utc"})
    return manifest


def preflight(panel: str, candidate: Path, workers: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not 1 <= workers <= 8:
        raise ValueError("workers must be in [1,8]")
    candidate = candidate.expanduser().resolve()
    if not candidate.is_file():
        raise FileNotFoundError(candidate)
    compile(candidate.read_text(encoding="utf-8"), str(candidate), "exec")
    for path in GOLD_POOL.values():
        if panel == "p3" and not path.is_file():
            raise FileNotFoundError(f"missing gold opponent: {path}")
    # Interface and all four modes are checked without consuming a game seed.
    for mode in MODES:
        executor = load_candidate_executor(str(candidate), mode, f"preflight-{mode}")
        if not callable(getattr(executor, "act", None)):
            raise TypeError(f"invalid executor for {mode}")
    tasks = build_tasks(panel, candidate)
    return tasks, make_manifest(panel, candidate, workers, tasks)


def run(panel: str, candidate: Path, output_dir: Path, workers: int) -> int:
    output_dir = output_dir.expanduser().resolve()
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing run: {output_dir}")
    tasks, manifest = preflight(panel, candidate, workers)
    output_dir.mkdir(parents=True)
    (output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8",
    )
    rows: list[dict[str, Any]] = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(play_task, task): task for task in tasks}
        for future in concurrent.futures.as_completed(futures):
            task = futures[future]
            try:
                rows.append(future.result())
            except BaseException as exc:
                rows.append(error_row(task, f"worker:{type(exc).__name__}: {exc}"))
    rows.sort(key=lambda row: str(row["task_id"]))
    with (output_dir / "games.jsonl").open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, default=str) + "\n")
    summary = summarize(rows, panel)
    decision = decide(summary)
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8",
    )
    (output_dir / "decision.json").write_text(
        json.dumps(decision, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8",
    )
    print(json.dumps({"output_dir": str(output_dir), **decision}, ensure_ascii=False, indent=2))
    return 0 if decision["passed"] else 2


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", choices=("p2", "p3"), required=True)
    parser.add_argument("--candidate", type=Path, default=R10_ROOT / "model/main.py")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.dry_run:
        tasks, manifest = preflight(args.panel, args.candidate, args.workers)
        print(json.dumps({**manifest, "writes": False, "task_ids": [task["task_id"] for task in tasks]}, ensure_ascii=False, indent=2))
        return 0
    return run(args.panel, args.candidate, args.output_dir, args.workers)


if __name__ == "__main__":
    raise SystemExit(main())
