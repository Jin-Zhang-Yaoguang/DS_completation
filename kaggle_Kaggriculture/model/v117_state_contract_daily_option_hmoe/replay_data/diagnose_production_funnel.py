#!/usr/bin/env python3
"""B109：在准入 Development 场景中构造生产动作到现金的只读转化漏斗。

库存变化来自相邻 observation；动作和订单只作为同时点上下文。脚本不把请求当成交，
也不把含采购/出售的库存正增量直接解释成纯生产量。
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
PRODUCTS = (
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
    "EGG", "MILK", "WOOL", "FERTILIZER",
)
PRODUCTION_ACTIONS = {"HARVEST", "COLLECT_FERTILIZER"}


def _stocks(snapshot: dict[str, Any]) -> tuple[Counter[str], Counter[str], Counter[str]]:
    shed = Counter({item: int(snapshot.get("shed", {}).get(item, 0)) for item in PRODUCTS})
    carried = Counter({item: int(snapshot.get("carried", {}).get(item, 0)) for item in PRODUCTS})
    return shed, carried, shed + carried


def _empty_day(day: int, snapshot: dict[str, Any]) -> dict[str, Any]:
    _, _, total = _stocks(snapshot)
    return {
        "day": day,
        "production_action_attempts": Counter(),
        "all_unit_action_attempts": Counter(),
        "observed_stock_gain": Counter(),
        "observed_stock_gain_on_production_step": Counter(),
        "ambiguous_gain_with_market_order": Counter(),
        "observed_stock_loss": Counter(),
        "observed_stock_loss_on_sell_step": Counter(),
        "backpack_to_shed_transfer": Counter(),
        "sell_requested_units": Counter(),
        "buy_product_requested_units": Counter(),
        "gross_cash_in": 0,
        "gross_cash_out": 0,
        "start_total_stock": dict(total),
        "end_total_stock": dict(total),
    }


def _serialise_day(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    for key in (
        "production_action_attempts", "all_unit_action_attempts",
        "observed_stock_gain", "observed_stock_gain_on_production_step",
        "ambiguous_gain_with_market_order", "observed_stock_loss",
        "observed_stock_loss_on_sell_step", "backpack_to_shed_transfer",
        "sell_requested_units", "buy_product_requested_units",
    ):
        result[key] = dict(sorted(result[key].items()))
    return result


def play(task: tuple[str, int, dict[str, Any]]) -> dict[str, Any]:
    scenario_path_raw, candidate_seat, manifest_contract = task
    scenario_path = Path(scenario_path_raw)
    scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
    cash_diagnostic.validate_scenario(scenario, manifest_contract)

    identity = f"funnel_{os.getpid()}_{scenario['episode_id']}_{candidate_seat}"
    candidate, v1_agent = evaluation.load_agents(identity, {}, {})
    agents = [v1_agent, v1_agent]
    agents[candidate_seat] = candidate.act
    roles = {candidate_seat: "candidate", 1 - candidate_seat: "v1"}

    schedule = list(scenario["realized_public_shops"])
    engine = evaluation.load_scenario_engine()
    game = engine.Game(int(scenario["actual_seed"]), int(scenario.get("step_count", 720)))
    game.force_shops(evaluation.visible_shops(schedule, 0))
    daily: dict[str, dict[int, dict[str, Any]]] = {"candidate": {}, "v1": {}}
    calls = 0
    action_violations = 0
    trajectory_mismatches = 0

    while not game.done:
        step = int(game.step_count)
        day = step // 24
        before = [game.observe(0), game.observe(1)]
        expected_shops = evaluation.visible_shops(schedule, step)
        trajectory_mismatches += sum(
            list((observation.get("town") or {}).get("unlocked_shops") or [])
            != expected_shops
            for observation in before
        )
        actions = [agents[seat](before[seat]) for seat in (0, 1)]
        action_violations += evaluation.validate_action(
            actions[candidate_seat], before[candidate_seat],
        )
        game.step(actions[0], actions[1])
        after = [game.observe(0), game.observe(1)]

        for seat in (0, 1):
            role = roles[seat]
            before_snapshot = evaluation.economy_snapshot(before[seat], seat)
            after_snapshot = evaluation.economy_snapshot(after[seat], seat)
            row = daily[role].setdefault(day, _empty_day(day, before_snapshot))
            unit_actions = [
                actions[seat].get("farmer") or ["PASS"],
                *(actions[seat].get("hands") or []),
            ]
            verbs = [str(action[0]) if action else "INVALID" for action in unit_actions]
            row["all_unit_action_attempts"].update(verbs)
            row["production_action_attempts"].update(
                verb for verb in verbs if verb in PRODUCTION_ACTIONS
            )
            orders = cash_diagnostic.market_orders(actions[seat])
            has_market_order = bool(orders)
            has_sell = any(order["op"] == "SELL" for order in orders)
            for order in orders:
                item = str(order["item"])
                if item not in PRODUCTS:
                    continue
                if order["op"] == "SELL":
                    row["sell_requested_units"][item] += int(order["requested_units"])
                elif order["op"] == "BUY_PRODUCT":
                    row["buy_product_requested_units"][item] += int(order["requested_units"])

            before_shed, before_carried, before_total = _stocks(before_snapshot)
            after_shed, after_carried, after_total = _stocks(after_snapshot)
            production_step = any(verb in PRODUCTION_ACTIONS for verb in verbs)
            for item in PRODUCTS:
                total_delta = after_total[item] - before_total[item]
                shed_delta = after_shed[item] - before_shed[item]
                carried_delta = after_carried[item] - before_carried[item]
                if total_delta > 0:
                    row["observed_stock_gain"][item] += total_delta
                    if production_step:
                        row["observed_stock_gain_on_production_step"][item] += total_delta
                    if has_market_order:
                        row["ambiguous_gain_with_market_order"][item] += total_delta
                elif total_delta < 0:
                    row["observed_stock_loss"][item] += -total_delta
                    if has_sell:
                        row["observed_stock_loss_on_sell_step"][item] += -total_delta
                transfer = min(max(0, shed_delta), max(0, -carried_delta))
                if transfer:
                    row["backpack_to_shed_transfer"][item] += transfer
            cash_delta = int(after_snapshot["money"]) - int(before_snapshot["money"])
            row["gross_cash_in"] += max(0, cash_delta)
            row["gross_cash_out"] += min(0, cash_delta)
            row["end_total_stock"] = dict(after_total)

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
        "margin": rewards[candidate_seat] - rewards[1 - candidate_seat],
        "action_violations": action_violations,
        "trajectory_mismatches": trajectory_mismatches,
        "daily": {
            role: [_serialise_day(rows[day_key]) for day_key in sorted(rows)]
            for role, rows in daily.items()
        },
    }


def _mean(values: list[float]) -> float:
    return statistics.mean(values) if values else 0.0


def _mean_counter(rows: list[dict[str, Any]], key: str) -> dict[str, float]:
    total: Counter[str] = Counter()
    for row in rows:
        total.update({str(item): float(value) for item, value in row.get(key, {}).items()})
    return {item: total[item] / max(1, len(rows)) for item in sorted(total)}


def _mean_counter_total(rows: list[dict[str, Any]], key: str) -> float:
    return _mean([sum(float(value) for value in row.get(key, {}).values()) for row in rows])


def _summarize_day(rows: list[dict[str, Any]]) -> dict[str, Any]:
    keys = (
        "production_action_attempts", "observed_stock_gain",
        "observed_stock_gain_on_production_step", "ambiguous_gain_with_market_order",
        "observed_stock_loss", "observed_stock_loss_on_sell_step",
        "backpack_to_shed_transfer", "sell_requested_units",
        "buy_product_requested_units",
    )
    result = {
        "games": len(rows),
        "mean_gross_cash_in": _mean([float(row["gross_cash_in"]) for row in rows]),
        "mean_gross_cash_out": _mean([float(row["gross_cash_out"]) for row in rows]),
        "mean_end_total_stock_units": _mean([
            sum(float(value) for value in row.get("end_total_stock", {}).values())
            for row in rows
        ]),
    }
    for key in keys:
        result[f"mean_{key}"] = _mean_counter(rows, key)
        result[f"mean_{key}_units"] = _mean_counter_total(rows, key)
    return result


def _role_days(games: list[dict[str, Any]], role: str) -> dict[str, Any]:
    days: dict[int, list[dict[str, Any]]] = {}
    for game in games:
        for row in game["daily"][role]:
            days.setdefault(int(row["day"]), []).append(row)
    return {str(day): _summarize_day(days[day]) for day in sorted(days)}


def _gap(candidate: dict[str, Any], v1: dict[str, Any]) -> dict[str, float]:
    fields = (
        "mean_production_action_attempts_units",
        "mean_observed_stock_gain_units",
        "mean_observed_stock_gain_on_production_step_units",
        "mean_ambiguous_gain_with_market_order_units",
        "mean_backpack_to_shed_transfer_units",
        "mean_sell_requested_units_units",
        "mean_observed_stock_loss_on_sell_step_units",
        "mean_gross_cash_in",
        "mean_end_total_stock_units",
    )
    return {
        f"candidate_minus_v1_{field.removeprefix('mean_')}": (
            float(candidate.get(field, 0.0)) - float(v1.get(field, 0.0))
        )
        for field in fields
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for source in SOURCES:
        games = [row for row in rows if row["source_class"] == source]
        candidate = _role_days(games, "candidate")
        v1 = _role_days(games, "v1")
        days = sorted(set(candidate) & set(v1), key=int)
        output[source] = {
            "games": len(games),
            "scenario_blocks": len({row["episode_id"] for row in games}),
            "candidate": candidate,
            "v1": v1,
            "daily_candidate_minus_v1": {
                day: _gap(candidate[day], v1[day]) for day in days
            },
        }
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-dir", type=Path, default=evaluation.DEFAULT_PANEL)
    parser.add_argument("--limit-per-source", type=int, default=8)
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument(
        "--output-dir", type=Path,
        default=evaluation.DEFAULT_PANEL / "diagnostics/r2_1_b109_production_funnel",
    )
    args = parser.parse_args()
    manifest, scenarios = evaluation.manifest_scenarios(
        args.panel_dir, args.limit_per_source,
    )
    manifest_contract = {
        "expected_module_version": manifest.get("expected_module_version"),
        "expected_configuration_sha256": manifest.get("expected_configuration_sha256"),
    }
    tasks = [
        (str(row["scenario_path"]), seat, manifest_contract)
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
        "schema": "v117-r2.1-b109-production-funnel-v1",
        "strength_status": "DEVELOPMENT_DIAGNOSTIC_ONLY_NO_STRATEGY_CHANGE",
        "candidate": "B86_CURRENT_DEFAULT_BALANCED_ONLY",
        "opponent": "FROZEN_V1_ADAPTIVE_MARKET",
        "data_contract": {
            "minimum_observed_date": "2026-08-20",
            "split": "development",
            "sources_reported_separately": list(SOURCES),
            "module_version": manifest_contract["expected_module_version"],
            "configuration_sha256": manifest_contract["expected_configuration_sha256"],
            "historical_actions_results_market_path_loaded": False,
            "agents_restart_from_step_zero": True,
            "two_seats_per_scenario": True,
            "blind_content_accessed": False,
        },
        "semantics": {
            "action_attempt": "模型发出的动作，不保证引擎成功执行",
            "observed_stock_gain": "相邻 observation 的 shed+carried 正增量，可能含 BUY_PRODUCT",
            "gain_on_production_step": "同一步含 HARVEST/COLLECT 的库存正增量，仍是保守关联而非逐动作因果",
            "ambiguous_gain_with_market_order": "同一步存在任意市场订单的库存正增量，不解释为纯生产",
            "backpack_to_shed_transfer": "shed 正增量与 carried 负增量的逐产品最小值",
            "cash": "相邻 observation 的实际 money 变化",
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
    compact = {
        "integrity_pass": integrity,
        "games": len(rows),
        "sources": {
            source: {
                "games": payload["summary_by_source"][source]["games"],
                "day10_gap": payload["summary_by_source"][source][
                    "daily_candidate_minus_v1"
                ].get("10", {}),
                "day29_gap": payload["summary_by_source"][source][
                    "daily_candidate_minus_v1"
                ].get("29", {}),
            }
            for source in SOURCES
        },
    }
    print(json.dumps(compact, ensure_ascii=False, indent=2))
    return 0 if integrity else 1


if __name__ == "__main__":
    raise SystemExit(main())
