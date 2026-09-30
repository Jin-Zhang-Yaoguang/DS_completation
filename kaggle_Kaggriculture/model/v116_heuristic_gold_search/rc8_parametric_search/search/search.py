#!/usr/bin/env python3
"""R8 parameter search and CRN arena skeleton.

This module is research infrastructure only.  It never imports Island-GA,
Replay actions, or a historical agent into the candidate.  A candidate must
expose ``build_executor(params, mode)`` and return a fresh object with
``act(observation)``.
"""

from __future__ import annotations

import argparse
import ast
import copy
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
from typing import Any, Iterable, Mapping, Sequence


HERE = Path(__file__).resolve().parent
MODEL = HERE.parents[2]
CPPSIM = MODEL / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
ENGINE_VERSION = "1.32.7"

FULL_GOLD = {
    "v19": MODEL / "v19_hierarchical_moe/main.py",
    "v20": MODEL / "v20_demand_timing_moe/main.py",
    "v21": MODEL / "v21_top_meta_moe/main.py",
    "v32": MODEL / "v32_clone_horizon_preempt/main.py",
    "v33": MODEL / "v33_demand_gap_horizon4/main.py",
    "v34": MODEL / "v34_demand_boundary_preempt/main.py",
    "v37": MODEL / "v37_preterminal_boundary_preempt/main.py",
    "v46": MODEL / "v46_full_terminal_front_run/main.py",
    "v51": MODEL / "v51_post_action_terminal_sell/main.py",
    "v52": MODEL / "v52_terminal_route_acceleration/main.py",
    "v53": MODEL / "v53_terminal_access_flush/main.py",
    "v54": MODEL / "v54_terminal_water_bypass/main.py",
    "v66": MODEL / "v66_margin_gated_sell_bubble/main.py",
    "v70": MODEL / "v70_duplicate_wheat_buy_lead/main.py",
    "v71": MODEL / "v71_duplicate_wheat_buy_lead_50/main.py",
    "v72": MODEL / "v72_duplicate_wheat_buy_lead_75/main.py",
    "v73": MODEL / "v73_duplicate_wheat_buy_full_merge/main.py",
    "v76": MODEL / "v76_adjacent_safe_buy_lead/main.py",
}
# Counts are intentionally research-sized.  These are not the protocol's
# untouched 64/128-seed development/confirmation panels.
STAGE_SPECS: dict[str, dict[str, Any]] = {
    "R1": {"label": "idle_race", "pool": "idle", "seeds": 8, "keep": 32},
    "R2": {"label": "idle_confirm", "pool": "idle", "seeds": 24, "keep": 12},
    "R3": {"label": "gold_scout", "pool": "gold_full", "seeds": 2, "keep": 4},
    "R4": {"label": "gold_confirm", "pool": "gold_full", "seeds": 8, "keep": 1},
}
STAGE_ORDER = tuple(STAGE_SPECS)
DEFAULT_SEED_MANIFEST = HERE.parent / "protocol/seed_manifest.json"
PARAM_HASH_DOMAIN = "v116-rc8-param-spec-v1"

PRODUCTS = {"WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"}
CROPS = {"WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"}
ANIMALS = {"GOOSE", "COW", "SHEEP"}
ITEMS = PRODUCTS | ANIMALS
UNIT_NO_ARG = {
    "NORTH", "SOUTH", "EAST", "WEST", "PASS", "DROP", "WATER", "HARVEST",
    "FERTILIZE", "BUILD_COOP", "BUILD_PASTURE", "DIG", "FEED",
    "COLLECT_FERTILIZER", "CARE",
}


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str,
    ).encode("utf-8")


def hash_value(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_python_tree(root: Path) -> str:
    """Hash all Python sources beside the candidate, not only main.py."""
    records = []
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        records.append((str(path.relative_to(root)), sha256_file(path)))
    if not records:
        raise ValueError(f"no Python sources under candidate directory: {root}")
    return hash_value(records)


def read_seed_manifest(path: Path) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    """Read preregistered splits; first shop is deliberately not an input."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, Mapping) and "splits" in payload:
        raw_panels = payload["splits"]
    elif isinstance(payload, Mapping) and "stages" in payload:
        raw_panels = payload["stages"]
    else:
        raw_panels = payload
    if not isinstance(raw_panels, Mapping):
        raise ValueError("seed manifest must contain protocol 'splits'")
    panels: dict[str, list[dict[str, Any]]] = {}
    all_seeds: set[int] = set()
    for stage in STAGE_ORDER:
        raw = raw_panels.get(stage.lower(), raw_panels.get(stage))
        if isinstance(raw, Mapping):
            raw = raw.get("seeds")
        if not isinstance(raw, list) or not raw:
            raise ValueError(f"seed manifest missing non-empty {stage} panel")
        records = []
        for item in raw:
            if isinstance(item, Mapping):
                seed = int(item["seed"])
            else:
                seed = int(item)
            if seed <= 0 or seed in all_seeds:
                raise ValueError(f"seed must be positive and globally disjoint across stages: {seed}")
            all_seeds.add(seed)
            records.append({"seed": seed})
        expected = int(STAGE_SPECS[stage]["seeds"])
        if len(records) != expected:
            raise ValueError(f"{stage} requires {expected} preregistered seeds, got {len(records)}")
        panels[stage] = records
    return panels, []


def _first_primes(count: int) -> list[int]:
    primes: list[int] = []
    candidate = 2
    while len(primes) < count:
        if all(candidate % prime for prime in primes if prime * prime <= candidate):
            primes.append(candidate)
        candidate += 1
    return primes


def _radical_inverse(index: int, base: int) -> float:
    value = 0.0
    factor = 1.0 / base
    while index:
        index, digit = divmod(index, base)
        value += digit * factor
        factor /= base
    return value


def _coordinate(spec: Mapping[str, Any], u: float) -> Any:
    kind = str(spec.get("type", "float"))
    if kind == "fixed":
        return spec.get("value")
    if kind == "choice":
        values = list(spec.get("values") or [])
        if not values:
            raise ValueError("choice dimension requires non-empty values")
        return values[min(len(values) - 1, int(u * len(values)))]
    if kind == "bool":
        return bool(u >= 0.5)
    low, high = float(spec["low"]), float(spec["high"])
    if not math.isfinite(low) or not math.isfinite(high) or high < low:
        raise ValueError(f"invalid bounds: {low}, {high}")
    if kind == "int":
        lo, hi = int(low), int(high)
        return min(hi, lo + int(u * (hi - lo + 1)))
    if kind == "float":
        return low + u * (high - low)
    if kind == "log_float":
        if low <= 0:
            raise ValueError("log_float low must be positive")
        return math.exp(math.log(low) + u * (math.log(high) - math.log(low)))
    raise ValueError(f"unsupported parameter type: {kind}")


def _set_dotted(target: dict[str, Any], dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    node = target
    for part in parts[:-1]:
        child = node.get(part)
        if not isinstance(child, dict):
            raise ValueError(f"dotted parameter has no object parent: {dotted}")
        node = child
    node[parts[-1]] = value


def parameter_hash(params: Mapping[str, Any], domain: str = PARAM_HASH_DOMAIN) -> str:
    body = json.dumps(
        params, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(domain.encode("utf-8") + b"\0" + body).hexdigest()


def generate_configs(
    space: Mapping[str, Mapping[str, Any]], count: int, scramble_seed: int,
    base_params: Mapping[str, Any] | None = None, hash_domain: str = PARAM_HASH_DOMAIN,
) -> list[dict[str, Any]]:
    """Generate a deterministic shifted-Halton low-discrepancy design."""
    if count <= 0:
        raise ValueError("config count must be positive")
    names = sorted(space)
    if not names:
        raise ValueError("parameter space is empty")
    bases = _first_primes(len(names))
    shifts = {
        name: int.from_bytes(hashlib.sha256(f"{scramble_seed}:{name}".encode()).digest()[:8], "big") / 2**64
        for name in names
    }
    configs: list[dict[str, Any]] = []
    seen: set[str] = set()
    index = 1
    max_attempts = max(count * 100, 1000)
    while len(configs) < count and index <= max_attempts:
        coordinates = {
            name: _coordinate(space[name], (_radical_inverse(index, base) + shifts[name]) % 1.0)
            for name, base in zip(names, bases)
        }
        params = copy.deepcopy(dict(base_params)) if base_params is not None else {}
        for name, value in coordinates.items():
            if "." in name:
                _set_dotted(params, name, value)
            else:
                params[name] = value
        param_hash = parameter_hash(params, hash_domain)
        if param_hash not in seen:
            seen.add(param_hash)
            configs.append({"config_id": f"p{len(configs):04d}_{param_hash[:10]}", "param_hash": param_hash, "params": params})
        index += 1
    if len(configs) != count:
        raise ValueError(f"parameter space produced only {len(configs)} unique configs; requested {count}")
    return configs


def candidate_literal(path: Path, name: str) -> Any:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = node.value
            if isinstance(node, ast.Assign):
                names = [target.id for target in node.targets if isinstance(target, ast.Name)]
            else:
                names = [node.target.id] if isinstance(node.target, ast.Name) else []
            if name in names and value is not None:
                return ast.literal_eval(value)
    raise ValueError(f"candidate has no literal {name}")


def validate_candidate_interface(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    functions = [
        node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "build_executor"
    ]
    if not functions:
        raise ValueError("candidate must define build_executor(params, mode)")
    positional = len(functions[0].args.posonlyargs) + len(functions[0].args.args)
    if positional < 2:
        raise ValueError("build_executor must accept params and mode")


def load_space(
    path: Path, candidate: Path,
) -> tuple[dict[str, Mapping[str, Any]], dict[str, Any] | None, str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw = payload.get("parameters") if isinstance(payload, Mapping) and "parameters" in payload else payload
    if not isinstance(raw, Mapping) or not raw:
        raise ValueError("space must be a non-empty mapping or {'parameters': mapping}")
    space = {str(name): value for name, value in raw.items()}
    if not all(isinstance(value, Mapping) for value in space.values()):
        raise ValueError("each parameter specification must be an object")
    base_raw = payload.get("base_params") if isinstance(payload, Mapping) else None
    if base_raw == "candidate.DEFAULT_PARAMS":
        base_params = candidate_literal(candidate, "DEFAULT_PARAMS")
    elif base_raw is None:
        base_params = None
    elif isinstance(base_raw, Mapping):
        base_params = copy.deepcopy(dict(base_raw))
    else:
        raise ValueError("base_params must be an object or 'candidate.DEFAULT_PARAMS'")
    domain = str(payload.get("hash_domain", PARAM_HASH_DOMAIN)) if isinstance(payload, Mapping) else PARAM_HASH_DOMAIN
    return space, base_params, domain


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
            issues.extend(validate_unit(order, f"hands[{index}]") )
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


def load_runtime() -> tuple[Any, Any, Any]:
    builds = sorted((CPPSIM / "build").glob("lib.*/kagsim*.so"))
    if not builds:
        raise RuntimeError(f"missing kagsim under {CPPSIM / 'build'}")
    for path in (FACTORY, builds[-1].parent):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    import kagsim  # type: ignore
    from agent_factory import Registry, create_agent  # type: ignore

    if str(getattr(kagsim, "ENGINE_VERSION", "")) != ENGINE_VERSION:
        raise RuntimeError(f"engine drift: expected {ENGINE_VERSION}, got {getattr(kagsim, 'ENGINE_VERSION', None)}")
    return kagsim, Registry, create_agent


def load_candidate_executor(candidate_path: str, params: Mapping[str, Any], mode: str, tag: str) -> Any:
    path = Path(candidate_path).resolve()
    module_name = f"r8_candidate_{os.getpid()}_{hashlib.sha256(tag.encode()).hexdigest()[:16]}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot import candidate: {path}")
    if str(path.parent) not in sys.path:
        sys.path.insert(0, str(path.parent))
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
        builder = getattr(module, "build_executor", None)
        if not callable(builder):
            raise AttributeError("candidate must expose callable build_executor(params, mode)")
        executor = builder(dict(params), str(mode))
        if not callable(getattr(executor, "act", None)):
            raise TypeError("build_executor must return an object with callable act(observation)")
        return executor
    finally:
        sys.modules.pop(module_name, None)


def error_row(task: Mapping[str, Any], error: str) -> dict[str, Any]:
    return {
        "schema": "r8-parametric-game-v1",
        "task_id": task["task_id"],
        "cache_key": task["cache_key"],
        "stage": task["stage"],
        "config_id": task["config_id"],
        "param_hash": task["param_hash"],
        "executor_hash": task["executor_hash"],
        "evaluator_hash": task["evaluator_hash"],
        "mode": task["mode"],
        "opponent": task["opponent"],
        "opponent_hash": task["opponent_hash"],
        "seed": int(task["seed"]),
        "expected_shop": task.get("expected_shop"),
        "observed_shop": None,
        "candidate_seat": int(task["candidate_seat"]),
        "status": "ERROR",
        "error": error,
        "calls": 0,
        "schema_violations": 0,
        "shop_mismatch": False,
        "win": 0,
        "tie": 0,
        "loss": 0,
        "score": 0.0,
        "cache_hit": False,
    }


def play_task(task: Mapping[str, Any]) -> dict[str, Any]:
    base = error_row(task, "uninitialised")
    try:
        kagsim, Registry, create_agent = load_runtime()
        executor = load_candidate_executor(
            str(task["candidate_path"]), task["params"], str(task["mode"]), str(task["task_id"]),
        )
        opponent_path = task.get("opponent_path")
        opponent = None
        if opponent_path:
            registry = Registry(path=HERE / "runtime_registry.json", models={}, raw={})
            opponent = create_agent(registry, {
                "id": f"r8_opp_{os.getpid()}_{hashlib.sha256(str(task['task_id']).encode()).hexdigest()[:12]}",
                "kind": "python", "path": str(opponent_path), "entrypoint": "agent",
            })
        game = kagsim.Game(int(task["seed"]))
        seat = int(task["candidate_seat"])
        calls = 0
        issues: list[str] = []
        violation_count = 0
        first_shop: str | None = None
        while not game.done:
            observations = [game.observe(0), game.observe(1)]
            shops = list(((observations[seat].get("town") or {}).get("unlocked_shops", [])) or [])
            if first_shop is None and shops:
                first_shop = str(shops[0])
            own_action = executor.act(observations[seat])
            found = validate_action(own_action, observations[seat])
            violation_count += len(found)
            if len(issues) < 20:
                issues.extend(f"step={calls}:{item}" for item in found[:20 - len(issues)])
            rival_action = opponent(observations[1 - seat]) if opponent else idle_action(observations[1 - seat])
            actions = [None, None]
            actions[seat], actions[1 - seat] = own_action, rival_action
            game.step(actions[0], actions[1])
            calls += 1
        rewards = [float(game.reward(0)), float(game.reward(1))]
        own, rival = rewards[seat], rewards[1 - seat]
        margin = own - rival
        win, tie, loss = int(margin > 0), int(margin == 0), int(margin < 0)
        expected_shop = task.get("expected_shop")
        mismatch = bool(expected_shop is not None and str(expected_shop) != first_shop)
        return {
            **base,
            "status": "DONE",
            "error": None,
            "calls": calls,
            "schema_violations": violation_count,
            "schema_issue_examples": issues,
            "observed_shop": first_shop or "NO_SHOP",
            "shop_mismatch": mismatch,
            "own_bank": own,
            "opponent_bank": rival,
            "margin": margin,
            "win": win,
            "tie": tie,
            "loss": loss,
            "score": win + 0.5 * tie,
        }
    except BaseException as exc:
        return error_row(task, f"{type(exc).__name__}: {exc}")


def lower_cvar(values: Sequence[float], alpha: float = 0.20) -> float | None:
    if not values:
        return None
    count = max(1, math.ceil(alpha * len(values)))
    return statistics.mean(sorted(float(value) for value in values)[:count])


def aggregate(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    planned = len(rows)
    done = [row for row in rows if row.get("status") == "DONE"]
    wins = sum(int(row.get("win", 0)) for row in rows)
    ties = sum(int(row.get("tie", 0)) for row in rows)
    losses = sum(int(row.get("loss", 0)) for row in rows)
    banks = [float(row["own_bank"]) for row in done]
    margins = [float(row["margin"]) for row in done]
    return {
        "planned_games": planned,
        "completed_games": len(done),
        "errors_as_nonwins": planned - len(done),
        "wins": wins,
        "ties": ties,
        "losses": losses,
        "pure_win_rate": wins / planned if planned else 0.0,
        "score_rate": (wins + 0.5 * ties) / planned if planned else 0.0,
        "mean_bank_completed": statistics.mean(banks) if banks else None,
        "cvar25_bank_completed": lower_cvar(banks, 0.25),
        "mean_margin_completed": statistics.mean(margins) if margins else None,
        "median_margin_completed": statistics.median(margins) if margins else None,
        "cvar10_margin_completed": lower_cvar(margins, 0.10),
        "schema_violations": sum(int(row.get("schema_violations", 0)) for row in rows),
        "shop_mismatches": sum(int(bool(row.get("shop_mismatch", False))) for row in rows),
        "all_719_calls": planned > 0 and all(
            row.get("status") == "DONE" and int(row.get("calls", 0)) == 719 for row in rows
        ),
    }


def grouped(rows: Sequence[Mapping[str, Any]], key: str) -> dict[str, Any]:
    values = sorted({str(row.get(key) if row.get(key) is not None else "UNCLASSIFIED") for row in rows})
    return {
        value: aggregate([
            row for row in rows
            if str(row.get(key) if row.get(key) is not None else "UNCLASSIFIED") == value
        ])
        for value in values
    }


def summarize_config(rows: Sequence[Mapping[str, Any]], stage: str) -> dict[str, Any]:
    overall = aggregate(rows)
    by_shop = grouped(rows, "observed_shop")
    by_opponent = grouped(rows, "opponent")
    by_seat = grouped(rows, "candidate_seat")
    shop_rates = [value["pure_win_rate"] for value in by_shop.values()]
    opponent_rates = [value["pure_win_rate"] for value in by_opponent.values()]
    mechanics_ok = bool(
        not overall["errors_as_nonwins"]
        and not overall["schema_violations"]
        and not overall["shop_mismatches"]
        and overall["all_719_calls"]
    )
    positive_opponent_medians = sum(
        int(value["median_margin_completed"] is not None and value["median_margin_completed"] > 0)
        for value in by_opponent.values()
    )
    wilson_lcb = wilson_lower(overall["wins"], overall["planned_games"])
    mean_bank = overall["mean_bank_completed"]
    cvar25_bank = overall["cvar25_bank_completed"]
    idle_objective = (
        0.5 * float(mean_bank) + 0.5 * float(cvar25_bank)
        if mean_bank is not None and cvar25_bank is not None else None
    )
    futility_reasons = []
    if not mechanics_ok:
        futility_reasons.append("mechanics_or_manifest_failure")
    if stage == "R2":
        if overall["pure_win_rate"] < 1.0:
            futility_reasons.append("idle_pure_win_below_1.00")
        if mean_bank is None or mean_bank < 70_000:
            futility_reasons.append("idle_mean_bank_below_70000")
        if cvar25_bank is None or cvar25_bank < 55_000:
            futility_reasons.append("idle_cvar25_bank_below_55000")
    elif stage == "R3":
        if overall["pure_win_rate"] < 0.65:
            futility_reasons.append("pure_win_rate_below_0.65")
        if positive_opponent_medians < 10:
            futility_reasons.append("positive_opponent_medians_below_10")
    elif stage == "R4":
        if overall["pure_win_rate"] < 0.72:
            futility_reasons.append("pure_win_rate_below_0.72")
        if wilson_lcb < 0.68:
            futility_reasons.append("wilson_lcb_below_0.68")
        if positive_opponent_medians < 12:
            futility_reasons.append("positive_opponent_medians_below_12")
    return {
        **overall,
        "by_shop": by_shop,
        "by_opponent": by_opponent,
        "by_seat": by_seat,
        "macro_shop_win_rate": statistics.mean(shop_rates) if shop_rates else 0.0,
        "worst_shop_win_rate": min(shop_rates) if shop_rates else 0.0,
        "macro_opponent_win_rate": statistics.mean(opponent_rates) if opponent_rates else 0.0,
        "wilson95_lower": wilson_lcb,
        "positive_opponent_medians": positive_opponent_medians,
        "idle_objective_mean_cvar25": idle_objective,
        "mechanics_ok": mechanics_ok,
        "futility_failed": bool(futility_reasons),
        "futility_reasons": futility_reasons,
        "success_claim": False,
    }


def wilson_lower(wins: int, games: int, z: float = 1.6448536269514722) -> float:
    """One-sided 95% Wilson lower confidence bound."""
    if games <= 0:
        return 0.0
    p = wins / games
    denominator = 1.0 + z * z / games
    midpoint = p + z * z / (2.0 * games)
    radius = z * math.sqrt(p * (1.0 - p) / games + z * z / (4.0 * games * games))
    return (midpoint - radius) / denominator


def rank_key(summary: Mapping[str, Any], stage: str) -> tuple[Any, ...]:
    def number(name: str, default: float = -math.inf) -> float:
        value = summary.get(name)
        return float(value) if value is not None else default

    if stage in {"R1", "R2"}:
        return (
            int(bool(summary.get("mechanics_ok"))),
            number("idle_objective_mean_cvar25"),
            number("mean_bank_completed"),
            number("cvar25_bank_completed"),
        )
    return (
        int(bool(summary.get("mechanics_ok"))),
        number("wilson95_lower", 0.0),
        number("median_margin_completed"),
        number("cvar10_margin_completed"),
    )


def opponent_pool(name: str) -> dict[str, Path | None]:
    if name == "idle":
        return {"idle": None}
    if name == "gold_full":
        return dict(FULL_GOLD)
    raise ValueError(f"unknown pool: {name}")


def make_cache_key(
    *, param_hash: str, executor_hash: str, evaluator_hash: str,
    opponent_hash: str, seed: int, seat: int, mode: str,
) -> str:
    return hash_value({
        "param_hash": param_hash,
        "executor_hash": executor_hash,
        "evaluator_hash": evaluator_hash,
        "opponent_hash": opponent_hash,
        "seed": int(seed),
        "seat": int(seat),
        "mode": mode,
    })


def build_tasks(
    stage: str,
    configs: Sequence[Mapping[str, Any]],
    seeds: Sequence[Mapping[str, Any]],
    candidate: Path,
    mode: str,
    executor_hash: str,
    evaluator_hash: str,
) -> list[dict[str, Any]]:
    opponents = opponent_pool(str(STAGE_SPECS[stage]["pool"]))
    tasks = []
    for config in configs:
        for opponent, path in opponents.items():
            opponent_hash = hash_value("idle-v1") if path is None else sha256_file(path)
            for seed_record in seeds:
                for seat in (0, 1):
                    cache_key = make_cache_key(
                        param_hash=str(config["param_hash"]), executor_hash=executor_hash,
                        evaluator_hash=evaluator_hash, opponent_hash=opponent_hash,
                        seed=int(seed_record["seed"]), seat=seat, mode=mode,
                    )
                    tasks.append({
                        "task_id": f"{stage}__{config['config_id']}__{opponent}__{seed_record['seed']}__s{seat}",
                        "cache_key": cache_key,
                        "stage": stage,
                        "config_id": config["config_id"],
                        "param_hash": config["param_hash"],
                        "executor_hash": executor_hash,
                        "evaluator_hash": evaluator_hash,
                        "params": config["params"],
                        "candidate_path": str(candidate),
                        "mode": mode,
                        "opponent": opponent,
                        "opponent_path": str(path) if path is not None else None,
                        "opponent_hash": opponent_hash,
                        "seed": int(seed_record["seed"]),
                        "expected_shop": seed_record.get("shop"),
                        "candidate_seat": seat,
                    })
    return tasks


def load_cache(path: Path) -> dict[str, dict[str, Any]]:
    cache: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return cache
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid cache JSONL line {line_number}: {exc}") from exc
            if row.get("status") == "DONE" and row.get("cache_key"):
                cache[str(row["cache_key"])] = row
    return cache


def read_stage_selection(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    values = payload.get("survivors") if isinstance(payload, Mapping) else payload
    if not isinstance(values, list) or not values:
        raise ValueError("selection must be a non-empty list or {'survivors': [...]}")
    return [str(value) for value in values]


def validate_stage_prefix(stages: Sequence[str]) -> tuple[str, ...]:
    values = tuple(stages)
    if not values or any(stage not in STAGE_ORDER for stage in values):
        raise ValueError(f"stages must come from {STAGE_ORDER}")
    expected = STAGE_ORDER[: len(values)]
    if values != expected:
        raise ValueError(f"stages must be an ordered prefix: expected {expected}, got {values}")
    return values


def dry_plan(
    stages: Sequence[str], config_count: int, panels: Mapping[str, Sequence[Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    active = config_count
    result = []
    for stage in stages:
        opponents = opponent_pool(str(STAGE_SPECS[stage]["pool"]))
        games_per_config = len(panels[stage]) * len(opponents) * 2
        result.append({
            "stage": stage,
            "label": STAGE_SPECS[stage]["label"],
            "maximum_configs": active,
            "seeds": len(panels[stage]),
            "opponents": list(opponents),
            "games_per_config": games_per_config,
            "maximum_planned_games": active * games_per_config,
            "keep": min(active, int(STAGE_SPECS[stage]["keep"])),
        })
        active = min(active, int(STAGE_SPECS[stage]["keep"]))
    return result


def preflight(args: argparse.Namespace) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    if not 1 <= args.workers <= 8:
        raise ValueError("workers must be in [1,8]")
    candidate = args.candidate.expanduser().resolve()
    if not candidate.is_file():
        raise FileNotFoundError(f"candidate not found: {candidate}")
    compile(candidate.read_text(encoding="utf-8"), str(candidate), "exec")
    validate_candidate_interface(candidate)
    space_path = args.space.expanduser().resolve()
    space, base_params, hash_domain = load_space(space_path, candidate)
    configs = generate_configs(space, args.configs, args.design_seed, base_params, hash_domain)
    seed_manifest = args.seed_manifest.expanduser().resolve()
    panels, warnings = read_seed_manifest(seed_manifest)
    stages = validate_stage_prefix(args.stages)
    executor_hash = sha256_python_tree(candidate.parent)
    evaluator_hash = sha256_file(Path(__file__).resolve())
    opponents = {
        name: {opp: (str(path) if path else None) for opp, path in opponent_pool(str(STAGE_SPECS[name]["pool"])).items()}
        for name in stages
    }
    for mapping in opponents.values():
        for opponent, raw in mapping.items():
            if raw is not None and not Path(raw).is_file():
                raise FileNotFoundError(f"missing gold opponent {opponent}: {raw}")
    manifest = {
        "schema": "r8-parametric-search-manifest-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate": str(candidate),
        "candidate_executor_tree_sha256": executor_hash,
        "evaluator_sha256": evaluator_hash,
        "space": str(space_path),
        "space_sha256": sha256_file(space_path),
        "design": "deterministic_shifted_halton",
        "design_seed": args.design_seed,
        "config_count": len(configs),
        "mode": args.mode,
        "workers": args.workers,
        "stages": list(stages),
        "stage_plan": dry_plan(stages, len(configs), panels),
        "seed_panels": panels,
        "seed_manifest": str(seed_manifest),
        "seed_manifest_sha256": sha256_file(seed_manifest),
        "first_shop_usage": "post_hoc_stratified_reporting_only",
        "warnings": warnings,
        "opponents": opponents,
        "boundary": "current-observation candidate only; no Replay, Island compiler/evaluator, or parent agent",
        "gold_evidence": False,
    }
    manifest["run_fingerprint"] = hash_value(manifest)
    return manifest, configs, panels


def run(args: argparse.Namespace) -> int:
    manifest, configs, panels = preflight(args)
    if args.dry_run:
        print(json.dumps({"dry_run": True, "writes": False, **manifest}, ensure_ascii=False, indent=2))
        return 0

    output_dir = args.output_dir.expanduser().resolve()
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing run directory: {output_dir}")
    output_dir.mkdir(parents=True)
    (output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    (output_dir / "configs.json").write_text(
        json.dumps({"configs": configs}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )

    cache_path = args.cache.expanduser().resolve() if args.cache else output_dir / "cache.jsonl"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache = load_cache(cache_path)
    candidate = args.candidate.expanduser().resolve()
    executor_hash = str(manifest["candidate_executor_tree_sha256"])
    evaluator_hash = str(manifest["evaluator_sha256"])
    active = list(configs)
    stage_payloads = []
    raw_path = output_dir / "games.jsonl"

    # A single process pool services every stage; there is no nested executor.
    with raw_path.open("x", encoding="utf-8", buffering=1) as raw_stream, \
            cache_path.open("a", encoding="utf-8", buffering=1) as cache_stream, \
            concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as executor:
        for stage in manifest["stages"]:
            tasks = build_tasks(
                stage, active, panels[stage], candidate, args.mode, executor_hash, evaluator_hash,
            )
            rows: list[dict[str, Any]] = []
            pending: dict[concurrent.futures.Future[Any], Mapping[str, Any]] = {}
            for task in tasks:
                cached = cache.get(str(task["cache_key"]))
                if cached is not None:
                    row = dict(cached)
                    row.update({
                        "task_id": task["task_id"], "stage": stage,
                        "config_id": task["config_id"], "cache_hit": True,
                    })
                    rows.append(row)
                    raw_stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                else:
                    pending[executor.submit(play_task, task)] = task
            for future in concurrent.futures.as_completed(pending):
                task = pending[future]
                try:
                    row = future.result()
                except BaseException as exc:
                    row = error_row(task, f"worker:{type(exc).__name__}: {exc}")
                rows.append(row)
                raw_stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                if row.get("status") == "DONE":
                    cache[str(row["cache_key"])] = dict(row)
                    cache_stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

            by_config = []
            for config in active:
                config_rows = [row for row in rows if row["config_id"] == config["config_id"]]
                summary = summarize_config(config_rows, stage)
                by_config.append({
                    "config_id": config["config_id"], "param_hash": config["param_hash"],
                    "params": config["params"], "summary": summary,
                })
            eligible = [item for item in by_config if not item["summary"]["futility_failed"]]
            eligible.sort(key=lambda item: rank_key(item["summary"], stage), reverse=True)
            keep = min(int(STAGE_SPECS[stage]["keep"]), len(eligible))
            survivors = [item["config_id"] for item in eligible[:keep]]
            payload = {
                "schema": "r8-parametric-stage-summary-v1",
                "stage": stage,
                "label": STAGE_SPECS[stage]["label"],
                "futility_semantics": "failure-only; no stage can establish gold success",
                "planned_games": len(tasks),
                "cache_hits": sum(int(bool(row.get("cache_hit"))) for row in rows),
                "configs_entered": len(active),
                "configs_futility_failed": len(by_config) - len(eligible),
                "survivors": survivors,
                "results": by_config,
            }
            (output_dir / f"{stage}_summary.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
            )
            stage_payloads.append(payload)
            active_lookup = {config["config_id"]: config for config in active}
            active = [active_lookup[config_id] for config_id in survivors]
            if not active:
                break

    final = {
        "schema": "r8-parametric-search-summary-v1",
        "run_fingerprint": manifest["run_fingerprint"],
        "stages_completed": [payload["stage"] for payload in stage_payloads],
        "final_survivors": [config["config_id"] for config in active],
        "stage_files": [f"{payload['stage']}_summary.json" for payload in stage_payloads],
        "raw_games": str(raw_path),
        "raw_games_sha256": sha256_file(raw_path),
        "gold_evidence": False,
        "decision": "RESEARCH_SURVIVOR_ONLY_NOT_GOLD" if active else "FUTILITY_ALL_CONFIGS_FAILED",
    }
    (output_dir / "summary.json").write_text(
        json.dumps(final, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps(final, ensure_ascii=False, indent=2))
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="R8 low-discrepancy heuristic search with paired CRN and planned-denominator evaluation.",
    )
    result.add_argument(
        "--candidate", type=Path, default=HERE.parent / "candidate/candidate.py",
        help="candidate module exposing build_executor(params, mode)",
    )
    result.add_argument("--space", type=Path, default=HERE / "space.example.json", help="JSON parameter space")
    result.add_argument("--configs", type=int, default=128, help="unique shifted-Halton configurations")
    result.add_argument("--design-seed", type=int, default=20260830)
    result.add_argument("--mode", default="router", help="candidate executor mode")
    result.add_argument("--workers", type=int, default=min(8, max(1, int((os.cpu_count() or 1) * 0.60))))
    result.add_argument(
        "--stages", nargs="+", choices=STAGE_ORDER, default=list(STAGE_ORDER),
        help="ordered prefix of R1 R2 R3 R4",
    )
    result.add_argument(
        "--seed-manifest", type=Path, default=DEFAULT_SEED_MANIFEST,
        help="preregistered protocol seed_manifest.json; first shop is post-hoc only",
    )
    result.add_argument("--cache", type=Path, help="append-only DONE-row JSONL cache")
    result.add_argument("--output-dir", type=Path, default=HERE / "runs/latest")
    result.add_argument("--dry-run", action="store_true", help="validate and print the plan without writes or games")
    return result


def main() -> int:
    return run(parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
