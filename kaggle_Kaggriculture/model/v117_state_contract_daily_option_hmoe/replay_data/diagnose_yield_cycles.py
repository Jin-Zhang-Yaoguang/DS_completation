#!/usr/bin/env python3
"""B110：只读审计关键产品的单位资产生产周期兑现率。

仅在已准入 Development 外生场景中，从 step 0 分别运行当前 B86 与冻结 V1。
动作只作为同时点上下文；维护和收获成功必须由相邻 observation 的地块状态变化确认。
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

import diagnose_market_cash_gap as cash_diagnostic
import evaluate_development as evaluation


HERE = Path(__file__).resolve().parent
SOURCES = evaluation.SOURCES
TARGET_PRODUCTS = ("WHEAT", "MILK", "STRAWBERRY")
ANIMAL_PRODUCTS = {"GOOSE": "EGG", "CHICKEN": "EGG", "COW": "MILK", "SHEEP": "WOOL"}
MAINTENANCE_VERBS = {"WATER", "FERTILIZE", "FEED", "CARE"}


def _animal_kind(tile: dict[str, Any]) -> str:
    raw = tile.get("animal")
    if isinstance(raw, dict):
        return str(raw.get("kind") or "")
    return str(raw or "")


def _product(tile: Any) -> str | None:
    if not isinstance(tile, dict):
        return None
    if tile.get("kind") == "PLANT":
        value = str(tile.get("crop") or "")
        return value if value in TARGET_PRODUCTS else None
    value = ANIMAL_PRODUCTS.get(_animal_kind(tile))
    return value if value in TARGET_PRODUCTS else None


def _identity(x: int, y: int, tile: dict[str, Any]) -> str:
    if tile.get("kind") == "PLANT":
        return ":".join((
            str(x), str(y), "PLANT", str(tile.get("crop") or ""),
            str(tile.get("planted_day", -1)), str(tile.get("max_lifespan_step", -1)),
        ))
    return ":".join((
        str(x), str(y), str(tile.get("kind") or "ANIMAL"), _animal_kind(tile),
        str(tile.get("placed_day", -1)),
    ))


def _tile(farm: dict[str, Any], position: Any) -> dict[str, Any] | None:
    if not isinstance(position, (list, tuple)) or len(position) < 2:
        return None
    x, y = int(position[0]), int(position[1])
    rows = farm.get("tiles", []) or []
    if y < 0 or y >= len(rows) or x < 0 or x >= len(rows[y]):
        return None
    value = rows[y][x]
    return value if isinstance(value, dict) else None


def _positions(farm: dict[str, Any]) -> list[Any]:
    return [farm.get("farmer"), *(farm.get("hands", []) or [])]


def _new_product_row() -> dict[str, Any]:
    return {
        "asset_keys": set(),
        "watered_keys": set(),
        "fertilized_keys": set(),
        "fed_keys": set(),
        "cared_keys": set(),
        "peak_ready_by_asset": {},
        "maintenance_attempts": Counter(),
        "maintenance_confirmed": Counter(),
        "harvest_attempts": 0,
        "harvest_attempted_ready_units": 0,
        "harvest_confirmed_units": 0,
        "unharvested_ready_units_at_day_close": 0,
    }


def _new_day(day: int) -> dict[str, Any]:
    return {"day": day, "products": {item: _new_product_row() for item in TARGET_PRODUCTS}}


def _capture_assets(row: dict[str, Any], farm: dict[str, Any], day: int) -> None:
    for y, values in enumerate(farm.get("tiles", []) or []):
        for x, tile in enumerate(values):
            product = _product(tile)
            if product is None or not isinstance(tile, dict):
                continue
            key = _identity(x, y, tile)
            target = row["products"][product]
            target["asset_keys"].add(key)
            if bool(tile.get("watered_today")):
                target["watered_keys"].add(key)
            if int(tile.get("fertilized_until_day", -1) or -1) >= day:
                target["fertilized_keys"].add(key)
            if bool(tile.get("fed_today")):
                target["fed_keys"].add(key)
            if bool(tile.get("cared_today")):
                target["cared_keys"].add(key)
            target["peak_ready_by_asset"][key] = max(
                int(target["peak_ready_by_asset"].get(key, 0)),
                max(0, int(tile.get("yield_units", 0) or 0)),
            )


def _confirmed(verb: str, before: dict[str, Any], after: dict[str, Any] | None,
               day: int) -> bool:
    if not isinstance(after, dict):
        return False
    if verb == "WATER":
        return not bool(before.get("watered_today")) and bool(after.get("watered_today"))
    if verb == "FERTILIZE":
        return (
            int(before.get("fertilized_until_day", -1) or -1) < day
            and int(after.get("fertilized_until_day", -1) or -1) >= day
        )
    if verb == "FEED":
        return not bool(before.get("fed_today")) and bool(after.get("fed_today"))
    if verb == "CARE":
        return not bool(before.get("cared_today")) and bool(after.get("cared_today"))
    return False


def _record_actions(row: dict[str, Any], before_farm: dict[str, Any],
                    after_farm: dict[str, Any], actions: dict[str, Any], day: int) -> None:
    unit_actions = [actions.get("farmer") or ["PASS"], *(actions.get("hands") or [])]
    for position, action in zip(_positions(before_farm), unit_actions):
        verb = str(action[0]) if action else "INVALID"
        if verb not in MAINTENANCE_VERBS and verb != "HARVEST":
            continue
        before_tile = _tile(before_farm, position)
        product = _product(before_tile)
        if product is None or not isinstance(before_tile, dict):
            continue
        target = row["products"][product]
        x, y = int(position[0]), int(position[1])
        key = _identity(x, y, before_tile)
        after_tile = _tile(after_farm, position)
        if verb in MAINTENANCE_VERBS:
            target["maintenance_attempts"][verb] += 1
            if _confirmed(verb, before_tile, after_tile, day):
                target["maintenance_confirmed"][verb] += 1
                completion_key = {
                    "WATER": "watered_keys", "FERTILIZE": "fertilized_keys",
                    "FEED": "fed_keys", "CARE": "cared_keys",
                }[verb]
                target[completion_key].add(key)
            continue
        target["harvest_attempts"] += 1
        ready = max(0, int(before_tile.get("yield_units", 0) or 0))
        target["harvest_attempted_ready_units"] += ready
        after_ready = (
            max(0, int(after_tile.get("yield_units", 0) or 0))
            if isinstance(after_tile, dict) and _identity(x, y, after_tile) == key else 0
        )
        if ready > 0 and after_ready < ready:
            target["harvest_confirmed_units"] += ready


def _close_day(row: dict[str, Any], before_farm: dict[str, Any],
               after_farm: dict[str, Any], actions: dict[str, Any]) -> None:
    successful_keys: set[str] = set()
    unit_actions = [actions.get("farmer") or ["PASS"], *(actions.get("hands") or [])]
    for position, action in zip(_positions(before_farm), unit_actions):
        if not action or str(action[0]) != "HARVEST":
            continue
        before_tile = _tile(before_farm, position)
        if _product(before_tile) is None or not isinstance(before_tile, dict):
            continue
        x, y = int(position[0]), int(position[1])
        after_tile = _tile(after_farm, position)
        ready = max(0, int(before_tile.get("yield_units", 0) or 0))
        after_ready = (
            max(0, int(after_tile.get("yield_units", 0) or 0))
            if isinstance(after_tile, dict)
            and _identity(x, y, after_tile) == _identity(x, y, before_tile) else 0
        )
        if ready > 0 and after_ready < ready:
            successful_keys.add(_identity(x, y, before_tile))
    for y, values in enumerate(before_farm.get("tiles", []) or []):
        for x, tile in enumerate(values):
            product = _product(tile)
            if product is None or not isinstance(tile, dict):
                continue
            key = _identity(x, y, tile)
            if key not in successful_keys:
                row["products"][product]["unharvested_ready_units_at_day_close"] += max(
                    0, int(tile.get("yield_units", 0) or 0),
                )


def _serialise_day(row: dict[str, Any]) -> dict[str, Any]:
    result = {"day": int(row["day"]), "products": {}}
    for product, raw in row["products"].items():
        asset_days = len(raw["asset_keys"])
        data = {
            "asset_days": asset_days,
            "watered_asset_days": len(raw["watered_keys"]),
            "fertilized_asset_days": len(raw["fertilized_keys"]),
            "fed_asset_days": len(raw["fed_keys"]),
            "cared_asset_days": len(raw["cared_keys"]),
            "peak_ready_yield_units": sum(raw["peak_ready_by_asset"].values()),
            "maintenance_attempts": dict(sorted(raw["maintenance_attempts"].items())),
            "maintenance_confirmed": dict(sorted(raw["maintenance_confirmed"].items())),
            "harvest_attempts": int(raw["harvest_attempts"]),
            "harvest_attempted_ready_units": int(raw["harvest_attempted_ready_units"]),
            "harvest_confirmed_units": int(raw["harvest_confirmed_units"]),
            "unharvested_ready_units_at_day_close": int(
                raw["unharvested_ready_units_at_day_close"]
            ),
        }
        for field in ("watered", "fertilized", "fed", "cared"):
            data[f"{field}_completion_rate"] = (
                data[f"{field}_asset_days"] / asset_days if asset_days else None
            )
        result["products"][product] = data
    return result


def play(task: tuple[str, int, dict[str, Any]]) -> dict[str, Any]:
    scenario_path_raw, candidate_seat, manifest_contract = task
    scenario = json.loads(Path(scenario_path_raw).read_text(encoding="utf-8"))
    cash_diagnostic.validate_scenario(scenario, manifest_contract)
    identity = f"yield_{os.getpid()}_{scenario['episode_id']}_{candidate_seat}"
    candidate, v1_agent = evaluation.load_agents(identity, {}, {})
    agents = [v1_agent, v1_agent]
    agents[candidate_seat] = candidate.act
    roles = {candidate_seat: "candidate", 1 - candidate_seat: "v1"}
    schedule = list(scenario["realized_public_shops"])
    engine = evaluation.load_scenario_engine()
    game = engine.Game(int(scenario["actual_seed"]), int(scenario.get("step_count", 720)))
    game.force_shops(evaluation.visible_shops(schedule, 0))
    daily: dict[str, dict[int, dict[str, Any]]] = {"candidate": {}, "v1": {}}
    calls = action_violations = trajectory_mismatches = 0
    while not game.done:
        step = int(game.step_count)
        day, hour = step // 24, step % 24
        before = [game.observe(0), game.observe(1)]
        expected_shops = evaluation.visible_shops(schedule, step)
        trajectory_mismatches += sum(
            list((obs.get("town") or {}).get("unlocked_shops") or []) != expected_shops
            for obs in before
        )
        actions = [agents[seat](before[seat]) for seat in (0, 1)]
        action_violations += evaluation.validate_action(
            actions[candidate_seat], before[candidate_seat],
        )
        game.step(actions[0], actions[1])
        after = [game.observe(0), game.observe(1)]
        for seat in (0, 1):
            role = roles[seat]
            row = daily[role].setdefault(day, _new_day(day))
            before_farm = (before[seat].get("farms") or [{}, {}])[seat]
            after_farm = (after[seat].get("farms") or [{}, {}])[seat]
            _capture_assets(row, before_farm, day)
            _record_actions(row, before_farm, after_farm, actions[seat], day)
            if hour == 23:
                _close_day(row, before_farm, after_farm, actions[seat])
        if not game.done:
            game.force_shops(evaluation.visible_shops(schedule, int(game.step_count)))
        calls += 1
    rewards = [float(game.reward(0)), float(game.reward(1))]
    return {
        "source_class": scenario["source_class"],
        "episode_id": scenario["episode_id"],
        "observed_date": scenario["observed_date"],
        "scenario_sha256": scenario["scenario_sha256"],
        "candidate_seat": candidate_seat,
        "calls": calls,
        "candidate_reward": rewards[candidate_seat],
        "v1_reward": rewards[1 - candidate_seat],
        "action_violations": action_violations,
        "trajectory_mismatches": trajectory_mismatches,
        "daily": {
            role: [_serialise_day(rows[key]) for key in sorted(rows)]
            for role, rows in daily.items()
        },
    }


def _mean(values: list[float]) -> float:
    return statistics.mean(values) if values else 0.0


def _season(games: list[dict[str, Any]], role: str) -> dict[str, Any]:
    output: dict[str, Any] = {}
    sum_fields = (
        "asset_days", "watered_asset_days", "fertilized_asset_days",
        "fed_asset_days", "cared_asset_days", "peak_ready_yield_units",
        "harvest_attempts", "harvest_attempted_ready_units",
        "harvest_confirmed_units", "unharvested_ready_units_at_day_close",
    )
    for product in TARGET_PRODUCTS:
        per_game = []
        for game in games:
            values = Counter()
            attempts = Counter()
            confirmed = Counter()
            for day in game["daily"][role]:
                raw = day["products"][product]
                values.update({field: float(raw[field]) for field in sum_fields})
                attempts.update({key: float(value) for key, value in raw["maintenance_attempts"].items()})
                confirmed.update({key: float(value) for key, value in raw["maintenance_confirmed"].items()})
            per_game.append((values, attempts, confirmed))
        result = {f"mean_{field}": _mean([row[0][field] for row in per_game])
                  for field in sum_fields}
        result["mean_maintenance_attempts"] = {
            verb: _mean([row[1][verb] for row in per_game])
            for verb in sorted(MAINTENANCE_VERBS)
        }
        result["mean_maintenance_confirmed"] = {
            verb: _mean([row[2][verb] for row in per_game])
            for verb in sorted(MAINTENANCE_VERBS)
        }
        asset_days = result["mean_asset_days"]
        for field in ("watered", "fertilized", "fed", "cared"):
            result[f"{field}_completion_rate"] = (
                result[f"mean_{field}_asset_days"] / asset_days if asset_days else None
            )
        peak_ready = result["mean_peak_ready_yield_units"]
        result["peak_ready_yield_per_asset_day"] = (
            peak_ready / asset_days if asset_days else None
        )
        result["harvest_capture_rate"] = (
            result["mean_harvest_confirmed_units"] / peak_ready if peak_ready else None
        )
        result["day_close_unharvested_share"] = (
            result["mean_unharvested_ready_units_at_day_close"] / peak_ready
            if peak_ready else None
        )
        output[product] = result
    return output


def _gaps(candidate: dict[str, Any], v1: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "mean_asset_days", "mean_peak_ready_yield_units", "mean_harvest_attempts",
        "mean_harvest_confirmed_units", "mean_unharvested_ready_units_at_day_close",
        "watered_completion_rate", "fertilized_completion_rate",
        "fed_completion_rate", "cared_completion_rate",
        "peak_ready_yield_per_asset_day", "harvest_capture_rate",
        "day_close_unharvested_share",
    )
    return {
        product: {
            field: (
                float(candidate[product][field] or 0.0) - float(v1[product][field] or 0.0)
            )
            for field in fields
        }
        for product in TARGET_PRODUCTS
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    output = {}
    for source in SOURCES:
        games = [row for row in rows if row["source_class"] == source]
        candidate = _season(games, "candidate")
        v1 = _season(games, "v1")
        output[source] = {
            "games": len(games),
            "scenario_blocks": len({row["episode_id"] for row in games}),
            "candidate": candidate,
            "v1": v1,
            "candidate_minus_v1": _gaps(candidate, v1),
        }
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-dir", type=Path, default=evaluation.DEFAULT_PANEL)
    parser.add_argument("--limit-per-source", type=int, default=8)
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument(
        "--output-dir", type=Path,
        default=evaluation.DEFAULT_PANEL / "diagnostics/r2_1_b110_yield_cycles",
    )
    args = parser.parse_args()
    manifest, scenarios = evaluation.manifest_scenarios(args.panel_dir, args.limit_per_source)
    contract = {
        "expected_module_version": manifest.get("expected_module_version"),
        "expected_configuration_sha256": manifest.get("expected_configuration_sha256"),
    }
    tasks = [
        (str(row["scenario_path"]), seat, contract)
        for row in scenarios for seat in (0, 1)
    ]
    with concurrent.futures.ProcessPoolExecutor(max_workers=max(1, args.workers)) as pool:
        rows = list(pool.map(play, tasks, chunksize=1))
    integrity = (
        len(rows) == len(tasks)
        and all(row["calls"] == 719 for row in rows)
        and sum(row["action_violations"] for row in rows) == 0
        and sum(row["trajectory_mismatches"] for row in rows) == 0
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    games_path = args.output_dir / "games.jsonl"
    with games_path.open("w", encoding="utf-8") as stream:
        for row in sorted(rows, key=lambda item: (
            item["source_class"], int(item["episode_id"]), int(item["candidate_seat"]),
        )):
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    payload = {
        "schema": "v117-r2.1-b110-yield-cycle-audit-v1",
        "strength_status": "DEVELOPMENT_DIAGNOSTIC_ONLY_NO_STRATEGY_CHANGE",
        "candidate": "B86_CURRENT_DEFAULT_BALANCED_ONLY",
        "opponent": "FROZEN_V1_ADAPTIVE_MARKET",
        "data_contract": {
            "minimum_observed_date": "2026-08-20",
            "split": "development",
            "sources_reported_separately": list(SOURCES),
            "module_version": contract["expected_module_version"],
            "configuration_sha256": contract["expected_configuration_sha256"],
            "historical_actions_results_market_path_loaded": False,
            "agents_restart_from_step_zero": True,
            "two_seats_per_scenario": True,
            "blind_content_accessed": False,
        },
        "semantics": {
            "asset_day": "同一地块、资产类型和种植或放置批次在某日出现一次",
            "completion": "相邻 observation 已出现完成状态，或动作后由状态变化确认",
            "peak_ready_yield": "每个资产日观察到的最大 yield_units 之和，不是现金价值",
            "confirmed_harvest_units": "HARVEST 后同一资产 yield_units 下降时，按动作前 ready units 计",
            "day_close_unharvested": "hour 23 最后动作前仍 ready 且未被该动作确认收获的单位",
        },
        "integrity_pass": integrity,
        "games": len(rows),
        "scenario_blocks": len({row["episode_id"] for row in rows}),
        "summary_by_source": summarize(rows),
        "games_sha256": hashlib.sha256(games_path.read_bytes()).hexdigest(),
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps({
        "integrity_pass": integrity,
        "games": len(rows),
        "summary_by_source": payload["summary_by_source"],
    }, ensure_ascii=False, indent=2))
    return 0 if integrity else 1


if __name__ == "__main__":
    raise SystemExit(main())
