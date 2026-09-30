#!/usr/bin/env python3
"""Evaluator-only exact economic ledger for R17/R18/R19.

Scope is deliberately narrow: seed 7100, both candidate seats, router versus an
idle opponent.  This is a causal diagnostic, not P2, Replay, or gold evidence.
The candidate acts from the standard observation before the evaluator reads the
separate accounting channel.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import statistics
import sys
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
SEARCH_ROOT = HERE.parents[2]
ACCOUNTING_ROOT = (
    SEARCH_ROOT
    / "r17_local_tour_ledger_hmoe/evaluation/accounting_engine"
)
ACCOUNTING_MODULE_SHA256 = "cfc6708a693b04cd34fcb3b8d60c90d54c5c6b8d64bc6b9be1eb900ad5dd8ba2"
ENGINE_VERSION = "1.32.7"
SEED = 7100
SEATS = (0, 1)
MODE = "router"
PRODUCTS = (
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
    "EGG", "MILK", "WOOL", "FERTILIZER",
)
ANIMALS = ("GOOSE", "COW", "SHEEP")
ITEMS = PRODUCTS + ANIMALS
CROPS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")

CANDIDATES: dict[str, tuple[Path, str]] = {
    "R17": (
        SEARCH_ROOT / "r17_local_tour_ledger_hmoe/main.py",
        "7d6504512aac7bb39fdf49718022e3ae6c61353ffe0589efd3ce2fd5e333d908",
    ),
    "R18": (
        SEARCH_ROOT / "r18_semantic_bundle_restore_hmoe/main.py",
        "55fa7ba1aa6f8791cf208441b3d9ed740e6f99e48038dd3c71580d2e93bf2511",
    ),
    "R19": (
        SEARCH_ROOT / "r19_growth_debt_throughput_hmoe/main.py",
        "45e48f244123334329e9f35dd01d461ffc2919eac0ffaff4ce7d471cdb802ed7",
    ),
}

FORBIDDEN_CANDIDATE_TOKENS = (
    "kagsim_accounting",
    "INSTRUMENTATION_SCHEMA",
    "game.accounting(",
    "sys.modules",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): canonical(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [canonical(item) for item in value]
    return value


def recursive_has_accounting_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            str(key).lower() == "accounting" or recursive_has_accounting_key(item)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(recursive_has_accounting_key(item) for item in value)
    return False


def load_accounting_engine() -> tuple[Any, dict[str, Any]]:
    build = json.loads((ACCOUNTING_ROOT / "build_manifest.json").read_text(encoding="utf-8"))
    verification = json.loads(
        (ACCOUNTING_ROOT / "verification_report.json").read_text(encoding="utf-8")
    )
    module_path = Path(str(build["module_path"]))
    if not module_path.is_file():
        raise FileNotFoundError(f"accounting module missing: {module_path}")
    actual_hash = sha256(module_path)
    if actual_hash != ACCOUNTING_MODULE_SHA256:
        raise RuntimeError(
            f"accounting module drift: expected {ACCOUNTING_MODULE_SHA256}, got {actual_hash}"
        )
    if str(build.get("engine_version")) != ENGINE_VERSION:
        raise RuntimeError("accounting build engine drift")
    if not verification.get("successful") or int(verification.get("tests_run", 0)) < 6:
        raise RuntimeError("accounting engine is not verified by the six-test contract")
    if str(verification.get("module_sha256")) != actual_hash:
        raise RuntimeError("accounting verification/module hash mismatch")
    sys.path.insert(0, str(module_path.parent))
    engine = importlib.import_module("kagsim_accounting")
    if str(engine.ENGINE_VERSION) != ENGINE_VERSION:
        raise RuntimeError(f"loaded engine drift: {engine.ENGINE_VERSION}")
    return engine, {
        "module_path": str(module_path),
        "module_sha256": actual_hash,
        "build_manifest_sha256": sha256(ACCOUNTING_ROOT / "build_manifest.json"),
        "verification_report_sha256": sha256(ACCOUNTING_ROOT / "verification_report.json"),
        "verification_status": str(verification.get("status")),
        "verification_tests": int(verification.get("tests_run", 0)),
    }


def audit_candidate(version: str, path: Path, expected_hash: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    actual_hash = sha256(path)
    if actual_hash != expected_hash:
        raise RuntimeError(
            f"{version} candidate drift: expected {expected_hash}, got {actual_hash}"
        )
    source = path.read_text(encoding="utf-8")
    hits = [token for token in FORBIDDEN_CANDIDATE_TOKENS if token in source]
    if hits:
        raise RuntimeError(f"{version} candidate crosses accounting boundary: {hits}")
    return {
        "path": str(path),
        "sha256": actual_hash,
        "forbidden_accounting_tokens": hits,
        "boundary_static_ok": not hits,
    }


def load_executor(version: str, path: Path) -> Any:
    name = f"economic_ledger_{version.lower()}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    if getattr(module, "STRATEGY_PARENT", "MISSING") is not None:
        raise RuntimeError(f"{version} strategy parent is not null")
    builder = getattr(module, "build_executor", None)
    if not callable(builder):
        raise RuntimeError(f"{version} has no build_executor")
    executor = builder(params=None, mode=MODE)
    if not callable(getattr(executor, "act", None)):
        raise RuntimeError(f"{version} executor has no act")
    return executor


def idle_action(observation: Mapping[str, Any]) -> dict[str, Any]:
    seat = int(observation.get("player", 0) or 0)
    farms = list(observation.get("farms", []) or [])
    farm = farms[seat]
    return {
        "farmer": ["PASS"],
        "hands": [["PASS"] for _ in list(farm.get("hands", []) or [])],
        "market": [],
    }


def validate_action(action: Any, observation: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    if not isinstance(action, Mapping):
        return ["action_not_mapping"]
    if set(action) != {"farmer", "hands", "market"}:
        issues.append("top_level_keys")
    seat = int(observation.get("player", 0) or 0)
    farm = list(observation.get("farms", []) or [])[seat]
    expected_hands = len(list(farm.get("hands", []) or []))
    farmer = action.get("farmer")
    if not isinstance(farmer, (list, tuple)) or not farmer:
        issues.append("farmer_shape")
    hands = action.get("hands")
    if not isinstance(hands, (list, tuple)) or len(hands) != expected_hands:
        issues.append("hands_shape")
    elif any(not isinstance(order, (list, tuple)) or not order for order in hands):
        issues.append("hand_order_shape")
    market = action.get("market")
    if not isinstance(market, (list, tuple)) or len(market) > 10:
        issues.append("market_shape")
    elif any(not isinstance(order, (list, tuple)) or not order for order in market):
        issues.append("market_order_shape")
    return issues


def asset_snapshot(observation: Mapping[str, Any], seat: int) -> dict[str, Any]:
    farm = list(observation.get("farms", []) or [])[seat]
    private = dict(observation.get("private", {}) or {})
    crops: Counter[str] = Counter()
    animals: Counter[str] = Counter()
    structures: Counter[str] = Counter()
    weeds = 0
    for row in list(farm.get("tiles", []) or []):
        for tile in list(row or []):
            if not isinstance(tile, Mapping):
                continue
            kind = str(tile.get("kind") or "")
            if kind == "PLANT" and tile.get("crop"):
                crops[str(tile["crop"])] += 1
            if kind in {"COOP", "PASTURE"}:
                structures[kind] += 1
            if tile.get("animal"):
                value = tile["animal"]
                animal = value.get("kind") if isinstance(value, Mapping) else value
                animals[str(animal)] += 1
            if kind == "WEED":
                weeds += 1
    shed = {str(key): int(value or 0) for key, value in dict(private.get("shed", {}) or {}).items()}
    inventories = list(private.get("inventories", []) or [])
    carried: Counter[str] = Counter()
    for inventory in inventories:
        carried.update({str(key): int(value or 0) for key, value in dict(inventory or {}).items()})
    return {
        "step": int(observation.get("step", 0) or 0),
        "day": int(observation.get("day", 0) or 0),
        "hour": int(observation.get("hour", 0) or 0),
        "money": float(farm.get("money", 0) or 0),
        "production_assets": sum(crops.values()) + sum(animals.values()),
        "crops": dict(sorted(crops.items())),
        "animals": dict(sorted(animals.items())),
        "structures": dict(sorted(structures.items())),
        "weeds": weeds,
        "hands": len(list(farm.get("hands", []) or [])),
        "lands": len(list(farm.get("unlocked_quadrants", []) or [])),
        "shed_total": sum(shed.values()),
        "carried_total": sum(carried.values()),
        "shed": dict(sorted(shed.items())),
        "carried": dict(sorted(carried.items())),
        "seeds": {
            str(key): int(value or 0)
            for key, value in dict(private.get("seeds", {}) or {}).items()
        },
    }


def compact_truth(truth: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "sell_revenue": float(truth["sell_revenue"]),
        "total_spend": float(truth["total_spend"]),
        "produced_total": sum(int(value) for value in truth["produced"].values()),
        "sold_total": sum(int(value) for value in truth["sold_units"].values()),
        "discarded_total": sum(int(value) for value in truth["discarded"].values()),
        "successful_hires": int(truth["successful_hires"]),
        "seed_units_bought": sum(int(value) for value in truth["bought_seed_units"].values()),
        "animal_units_bought": sum(int(truth["bought_units"].get(item, 0)) for item in ANIMALS),
    }


def count_action(action: Mapping[str, Any], unit_counts: Counter[str],
                 market_orders: Counter[str], market_units: Counter[str]) -> None:
    for order in [action.get("farmer"), *list(action.get("hands", []) or [])]:
        if order:
            unit_counts[str(order[0])] += 1
    for order in list(action.get("market", []) or []):
        if not order:
            continue
        op = str(order[0])
        item = str(order[1]) if len(order) >= 2 else "_NONE"
        quantity = int(order[2]) if len(order) >= 3 else 1
        market_orders[op] += 1
        market_units[f"{op}:{item}"] += quantity


def item_conservation(initial: Mapping[str, Any], terminal: Mapping[str, Any]) -> dict[str, int]:
    residuals: dict[str, int] = {}
    for item in ITEMS:
        lhs = (
            int(initial["total_inventory"].get(item, 0))
            + int(terminal["produced"].get(item, 0))
            + int(terminal["bought_units"].get(item, 0))
        )
        rhs = (
            int(terminal["total_inventory"].get(item, 0))
            + int(terminal["sold_units"].get(item, 0))
            + int(terminal["consumed_units"].get(item, 0))
            + int(terminal["discarded"].get(item, 0))
        )
        residuals[item] = lhs - rhs
    return residuals


def run_game(engine: Any, version: str, candidate_path: Path, seat: int) -> dict[str, Any]:
    executor = load_executor(version, candidate_path)
    game = engine.Game(SEED, steps=720)
    initial_observation = canonical(game.observe(seat))
    initial_truth = canonical(game.accounting(seat))
    unit_counts: Counter[str] = Counter()
    market_orders: Counter[str] = Counter()
    market_units: Counter[str] = Counter()
    schema_issues: list[dict[str, Any]] = []
    daily: list[dict[str, Any]] = []
    calls = 0
    observation_boundary_clean = True

    while not game.done:
        observations = [canonical(game.observe(0)), canonical(game.observe(1))]
        own_observation = observations[seat]
        observation_boundary_clean &= not recursive_has_accounting_key(own_observation)

        # Information boundary: the candidate commits its action before the
        # evaluator reads the privileged accounting channel for this boundary.
        action = executor.act(own_observation)
        issues = validate_action(action, own_observation)
        if issues:
            schema_issues.append({"step": calls, "issues": issues})
        count_action(action, unit_counts, market_orders, market_units)
        if int(own_observation.get("hour", 0) or 0) == 0:
            truth_before = canonical(game.accounting(seat))
            daily.append({
                **asset_snapshot(own_observation, seat),
                "economy_cumulative": compact_truth(truth_before),
            })

        rival_action = idle_action(observations[1 - seat])
        actions = [None, None]
        actions[seat] = action
        actions[1 - seat] = rival_action
        game.step(actions[0], actions[1])
        calls += 1

    terminal_observation = canonical(game.observe(seat))
    terminal_truth = canonical(game.accounting(seat))
    terminal_assets = asset_snapshot(terminal_observation, seat)
    conservation = item_conservation(initial_truth, terminal_truth)
    initial_seeds = dict(initial_observation.get("private", {}).get("seeds", {}) or {})
    terminal_seeds = terminal_assets["seeds"]
    seed_residuals = {
        crop: int(initial_seeds.get(crop, 0) or 0)
        + int(terminal_truth["bought_seed_units"].get(crop, 0))
        - int(terminal_truth["planted_seed_units"].get(crop, 0))
        - int(terminal_seeds.get(crop, 0) or 0)
        for crop in CROPS
    }
    cash_residual = (
        float(initial_truth["money"])
        + float(terminal_truth["sell_revenue"])
        - float(terminal_truth["total_spend"])
        - float(game.reward(seat))
    )
    diagnostics_method = getattr(executor, "diagnostics", None)
    diagnostics = diagnostics_method() if callable(diagnostics_method) else {}
    audit = dict(diagnostics.get("audit", {}) or {}) if isinstance(diagnostics, Mapping) else {}
    return {
        "schema": "v116-r19-economic-ledger-game-v1",
        "version": version,
        "candidate_sha256": sha256(candidate_path),
        "seed": SEED,
        "candidate_seat": seat,
        "opponent": "idle",
        "mode": MODE,
        "status": "DONE",
        "calls": calls,
        "bank": float(game.reward(seat)),
        "observation_boundary_clean": observation_boundary_clean,
        "schema_issues": schema_issues,
        "unit_action_counts": dict(sorted(unit_counts.items())),
        "market_request_order_counts": dict(sorted(market_orders.items())),
        "market_request_units": dict(sorted(market_units.items())),
        "daily_assets": daily,
        "terminal_assets": terminal_assets,
        "truth": terminal_truth,
        "truth_compact": compact_truth(terminal_truth),
        "successful_seed_units_by_crop": dict(sorted(terminal_truth["bought_seed_units"].items())),
        "successful_animal_units_by_type": {
            animal: int(terminal_truth["bought_units"].get(animal, 0)) for animal in ANIMALS
        },
        "item_conservation_residuals": conservation,
        "seed_conservation_residuals": seed_residuals,
        "cash_conservation_residual": cash_residual,
        "diagnostic_audit": dict(sorted(audit.items())),
        "checks": {
            "calls_719": calls == 719,
            "schema_clean": not schema_issues,
            "observation_has_no_accounting": observation_boundary_clean,
            "item_conservation_zero": all(value == 0 for value in conservation.values()),
            "seed_conservation_zero": all(value == 0 for value in seed_residuals.values()),
            "cash_conservation_zero": cash_residual == 0,
        },
    }


def mean_counter(rows: Sequence[Mapping[str, Any]], path: Sequence[str], keys: Sequence[str]) -> dict[str, float]:
    result: dict[str, float] = {}
    for key in keys:
        values: list[float] = []
        for row in rows:
            current: Any = row
            for part in path:
                current = current[part]
            values.append(float(current.get(key, 0)))
        result[key] = statistics.mean(values)
    return result


def summarize_version(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    scalars = (
        "sell_revenue", "total_spend", "produced_total", "sold_total",
        "discarded_total", "successful_hires", "seed_units_bought", "animal_units_bought",
    )
    summary = {
        "games": len(rows),
        "banks": [float(row["bank"]) for row in rows],
        "bank_mean": statistics.mean(float(row["bank"]) for row in rows),
        "bank_min": min(float(row["bank"]) for row in rows),
        "bank_max": max(float(row["bank"]) for row in rows),
        "all_checks_pass": all(all(row["checks"].values()) for row in rows),
        "schema_issues": sum(len(row["schema_issues"]) for row in rows),
        "economy_mean": {
            key: statistics.mean(float(row["truth_compact"][key]) for row in rows)
            for key in scalars
        },
        "produced_by_item_mean": mean_counter(rows, ("truth", "produced"), ITEMS),
        "sold_by_item_mean": mean_counter(rows, ("truth", "sold_units"), ITEMS),
        "discarded_by_item_mean": mean_counter(rows, ("truth", "discarded"), ITEMS),
        "successful_seed_units_by_crop_mean": mean_counter(
            rows, ("successful_seed_units_by_crop",), CROPS
        ),
        "successful_animal_units_by_type_mean": mean_counter(
            rows, ("successful_animal_units_by_type",), ANIMALS
        ),
        "unit_action_counts_mean": mean_counter(
            rows,
            ("unit_action_counts",),
            sorted({key for row in rows for key in row["unit_action_counts"]}),
        ),
    }
    summary["economy_mean"]["net_cash_flow"] = (
        summary["economy_mean"]["sell_revenue"] - summary["economy_mean"]["total_spend"]
    )
    summary["economy_mean"]["sale_through_rate"] = (
        summary["economy_mean"]["sold_total"]
        / max(1.0, summary["economy_mean"]["produced_total"])
    )
    daily_mean: list[dict[str, Any]] = []
    for day in range(30):
        values = [row["daily_assets"][day] for row in rows]
        daily_mean.append({
            "day": day,
            "money": statistics.mean(float(value["money"]) for value in values),
            "production_assets": statistics.mean(
                float(value["production_assets"]) for value in values
            ),
            "hands": statistics.mean(float(value["hands"]) for value in values),
            "weeds": statistics.mean(float(value["weeds"]) for value in values),
            "shed_total": statistics.mean(float(value["shed_total"]) for value in values),
            "carried_total": statistics.mean(float(value["carried_total"]) for value in values),
            "sell_revenue_cumulative": statistics.mean(
                float(value["economy_cumulative"]["sell_revenue"]) for value in values
            ),
            "total_spend_cumulative": statistics.mean(
                float(value["economy_cumulative"]["total_spend"]) for value in values
            ),
            "produced_cumulative": statistics.mean(
                float(value["economy_cumulative"]["produced_total"]) for value in values
            ),
            "sold_cumulative": statistics.mean(
                float(value["economy_cumulative"]["sold_total"]) for value in values
            ),
            "discarded_cumulative": statistics.mean(
                float(value["economy_cumulative"]["discarded_total"]) for value in values
            ),
        })
    summary["daily_mean"] = daily_mean
    return summary


def numeric_delta(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, float]:
    return {
        key: float(right[key]) - float(left[key])
        for key in sorted(set(left) & set(right))
        if isinstance(left[key], (int, float)) and isinstance(right[key], (int, float))
    }


def main() -> int:
    engine, accounting_evidence = load_accounting_engine()
    candidate_evidence = {
        version: audit_candidate(version, path, expected)
        for version, (path, expected) in CANDIDATES.items()
    }
    rows: list[dict[str, Any]] = []
    for version, (path, _expected) in CANDIDATES.items():
        for seat in SEATS:
            rows.append(run_game(engine, version, path, seat))
    by_version = {
        version: summarize_version([row for row in rows if row["version"] == version])
        for version in CANDIDATES
    }
    summary = {
        "schema": "v116-r19-economic-ledger-summary-v1",
        "scope": {
            "seed": SEED,
            "seats": list(SEATS),
            "mode": MODE,
            "opponent": "idle",
            "games": len(rows),
            "p2": False,
            "replay": False,
            "gold_evidence": False,
        },
        "all_games_clean": all(all(row["checks"].values()) for row in rows),
        "by_version": by_version,
        "deltas_vs_R17": {
            version: {
                "bank_mean": by_version[version]["bank_mean"] - by_version["R17"]["bank_mean"],
                "economy_mean": numeric_delta(
                    by_version["R17"]["economy_mean"], by_version[version]["economy_mean"]
                ),
                "unit_action_counts_mean": numeric_delta(
                    by_version["R17"]["unit_action_counts_mean"],
                    by_version[version]["unit_action_counts_mean"],
                ),
            }
            for version in ("R18", "R19")
        },
    }
    games_path = HERE / "games.jsonl"
    games_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    summary_path = HERE / "summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "schema": "v116-r19-economic-ledger-run-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "engine_version": ENGINE_VERSION,
        "accounting_engine": accounting_evidence,
        "candidates": candidate_evidence,
        "evaluator_path": str(Path(__file__).resolve()),
        "evaluator_sha256": sha256(Path(__file__).resolve()),
        "games_sha256": sha256(games_path),
        "summary_sha256": sha256(summary_path),
        "single_process": True,
        "candidate_truth_visibility": "NONE",
        "truth_read_order": "candidate_action_first_then_evaluator_accounting",
        "status": "COMPLETE_DIAGNOSTIC_NOT_P2_NOT_REPLAY_NOT_GOLD",
    }
    (HERE / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    decision = {
        "schema": "v116-r19-economic-ledger-decision-v1",
        "status": "DIAGNOSTIC_COMPLETE_NOT_GOLD_EVIDENCE" if summary["all_games_clean"]
        else "FAIL_CLOSED_ECONOMIC_LEDGER",
        "passed_accounting_integrity": bool(summary["all_games_clean"]),
        "p2_authorized_by_this_evidence": False,
        "replay_authorized_by_this_evidence": False,
        "gold_registration_authorized": False,
    }
    (HERE / "decision.json").write_text(
        json.dumps(decision, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary["all_games_clean"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
