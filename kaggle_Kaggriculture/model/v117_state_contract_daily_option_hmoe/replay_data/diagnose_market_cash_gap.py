#!/usr/bin/env python3
"""诊断 B75 与冻结 V1 的真实现金流断点。

只读取已准入的 Development 外生场景，候选与 V1 从 step 0 独立决策并交换座位。
逐步现金差来自引擎执行后的 observation，因此是实际净现金变化；订单字段仅作为
当步意图上下文，不把重复或未成交订单冒充实际成交量。
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import statistics
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

import evaluate_development as evaluation


HERE = Path(__file__).resolve().parent
SOURCES = evaluation.SOURCES
MIN_REPLAY_DATE = date(2026, 8, 20)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def market_orders(action: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for order in action.get("market", []) or []:
        if not order:
            continue
        rows.append({
            "op": str(order[0]),
            "item": str(order[1]) if len(order) >= 2 else "NONE",
            "requested_units": int(order[2]) if len(order) >= 3 else 1,
        })
    return rows


def empty_day(day: int, cash: int, snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "day": day,
        "start_cash": cash,
        "end_cash": cash,
        "net_cash_delta": 0,
        "gross_cash_in": 0,
        "gross_cash_out": 0,
        "positive_cash_steps": 0,
        "negative_cash_steps": 0,
        "emitted_market_order_counts": Counter(),
        "emitted_market_order_units": Counter(),
        "orders_on_positive_cash_steps": Counter(),
        "orders_on_negative_cash_steps": Counter(),
        "single_order_realized_cash": Counter(),
        "unit_action_counts": Counter(),
        "start_economy": snapshot,
        "end_economy": snapshot,
    }


def serialise_day(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    for key in (
        "emitted_market_order_counts",
        "emitted_market_order_units",
        "orders_on_positive_cash_steps",
        "orders_on_negative_cash_steps",
        "single_order_realized_cash",
        "unit_action_counts",
    ):
        result[key] = dict(sorted(result[key].items()))
    return result


def validate_scenario(scenario: dict[str, Any], manifest: dict[str, Any]) -> None:
    if scenario.get("split") != "development":
        raise PermissionError("只允许 Development 场景")
    if scenario.get("historical_player_fields_materialized") is not False:
        raise RuntimeError("场景包含或未声明排除历史玩家字段")
    if date.fromisoformat(str(scenario.get("observed_date"))) < MIN_REPLAY_DATE:
        raise RuntimeError("Replay 日期早于 2026-08-20")
    if str(scenario.get("module_version")) != str(manifest.get("expected_module_version")):
        raise RuntimeError("module_version 不一致")
    if str(scenario.get("configuration_sha256")) != str(manifest.get("expected_configuration_sha256")):
        raise RuntimeError("configuration 不一致")
    if not scenario.get("realized_public_shops"):
        raise RuntimeError("缺少商店轨迹")


def play(task: tuple[
    str, int, dict[str, Any], dict[str, Any], dict[str, Any],
]) -> dict[str, Any]:
    scenario_path_raw, candidate_seat, manifest_contract, balanced_genome, executor_tuning = task
    scenario_path = Path(scenario_path_raw)
    scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
    validate_scenario(scenario, manifest_contract)

    identity = f"cash_{os.getpid()}_{scenario['episode_id']}_{candidate_seat}"
    candidate, v1_agent = evaluation.load_agents(
        identity, balanced_genome, executor_tuning,
    )
    agents = [v1_agent, v1_agent]
    agents[candidate_seat] = candidate.act

    schedule = list(scenario["realized_public_shops"])
    engine = evaluation.load_scenario_engine()
    game = engine.Game(int(scenario["actual_seed"]), int(scenario.get("step_count", 720)))
    game.force_shops(evaluation.visible_shops(schedule, 0))

    roles = {candidate_seat: "candidate", 1 - candidate_seat: "v1"}
    daily: dict[str, dict[int, dict[str, Any]]] = {"candidate": {}, "v1": {}}
    cash_events: list[dict[str, Any]] = []
    calls = 0
    action_violations = 0
    trajectory_mismatches = 0

    while not game.done:
        step = int(game.step_count)
        day = step // 24
        hour = step % 24
        before = [game.observe(0), game.observe(1)]
        expected_shops = evaluation.visible_shops(schedule, step)
        trajectory_mismatches += sum(
            list((observation.get("town") or {}).get("unlocked_shops") or []) != expected_shops
            for observation in before
        )
        actions = [agents[seat](before[seat]) for seat in (0, 1)]
        action_violations += evaluation.validate_action(actions[candidate_seat], before[candidate_seat])
        game.step(actions[0], actions[1])
        after = [game.observe(0), game.observe(1)]

        for seat in (0, 1):
            role = roles[seat]
            before_snapshot = evaluation.economy_snapshot(before[seat], seat)
            after_snapshot = evaluation.economy_snapshot(after[seat], seat)
            before_cash = int(before_snapshot["money"])
            after_cash = int(after_snapshot["money"])
            delta = after_cash - before_cash
            day_row = daily[role].setdefault(day, empty_day(day, before_cash, before_snapshot))
            day_row["end_cash"] = after_cash
            day_row["end_economy"] = after_snapshot
            day_row["net_cash_delta"] += delta
            day_row["gross_cash_in"] += max(0, delta)
            day_row["gross_cash_out"] += min(0, delta)
            day_row["positive_cash_steps"] += int(delta > 0)
            day_row["negative_cash_steps"] += int(delta < 0)

            unit_actions = [actions[seat].get("farmer") or ["PASS"], *(actions[seat].get("hands") or [])]
            day_row["unit_action_counts"].update(
                str(unit_action[0]) if unit_action else "INVALID" for unit_action in unit_actions
            )
            orders = market_orders(actions[seat])
            for order in orders:
                key = f"{order['op']}:{order['item']}"
                day_row["emitted_market_order_counts"][key] += 1
                day_row["emitted_market_order_units"][key] += int(order["requested_units"])
                if delta > 0:
                    day_row["orders_on_positive_cash_steps"][key] += int(order["requested_units"])
                elif delta < 0:
                    day_row["orders_on_negative_cash_steps"][key] += int(order["requested_units"])
            if len(orders) == 1 and delta:
                key = f"{orders[0]['op']}:{orders[0]['item']}"
                day_row["single_order_realized_cash"][key] += delta
            if delta:
                cash_events.append({
                    "role": role,
                    "step": step,
                    "day": day,
                    "hour": hour,
                    "cash_before": before_cash,
                    "cash_after": after_cash,
                    "net_cash_delta": delta,
                    "orders": orders,
                })

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
            role: [serialise_day(rows[day]) for day in sorted(rows)]
            for role, rows in daily.items()
        },
        "cash_events": cash_events,
    }


def mean(values: list[float]) -> float:
    return statistics.mean(values) if values else 0.0


def sum_counters(rows: list[dict[str, Any]], key: str) -> dict[str, float]:
    total: Counter[str] = Counter()
    for row in rows:
        total.update({name: float(value) for name, value in (row.get(key) or {}).items()})
    divisor = max(1, len(rows))
    return {name: value / divisor for name, value in sorted(total.items())}


def summarize_role_day(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "games": len(rows),
        "mean_start_cash": mean([float(row["start_cash"]) for row in rows]),
        "mean_end_cash": mean([float(row["end_cash"]) for row in rows]),
        "mean_net_cash_delta": mean([float(row["net_cash_delta"]) for row in rows]),
        "mean_gross_cash_in": mean([float(row["gross_cash_in"]) for row in rows]),
        "mean_gross_cash_out": mean([float(row["gross_cash_out"]) for row in rows]),
        "mean_positive_cash_steps": mean([float(row["positive_cash_steps"]) for row in rows]),
        "mean_negative_cash_steps": mean([float(row["negative_cash_steps"]) for row in rows]),
        "mean_emitted_market_order_units": sum_counters(rows, "emitted_market_order_units"),
        "mean_orders_on_positive_cash_steps": sum_counters(rows, "orders_on_positive_cash_steps"),
        "mean_orders_on_negative_cash_steps": sum_counters(rows, "orders_on_negative_cash_steps"),
        "mean_single_order_realized_cash": sum_counters(rows, "single_order_realized_cash"),
        "mean_unit_action_counts": sum_counters(rows, "unit_action_counts"),
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for source in SOURCES:
        source_rows = [row for row in rows if row["source_class"] == source]
        by_role: dict[str, Any] = {}
        for role in ("candidate", "v1"):
            days: dict[int, list[dict[str, Any]]] = {}
            for game in source_rows:
                for day_row in game["daily"][role]:
                    days.setdefault(int(day_row["day"]), []).append(day_row)
            by_role[role] = {
                str(day): summarize_role_day(days[day])
                for day in sorted(days)
            }
        gaps: dict[str, Any] = {}
        shared_days = sorted(set(by_role["candidate"]) & set(by_role["v1"]), key=int)
        for day in shared_days:
            candidate = by_role["candidate"][day]
            v1 = by_role["v1"][day]
            gaps[day] = {
                "candidate_minus_v1_end_cash": candidate["mean_end_cash"] - v1["mean_end_cash"],
                "candidate_minus_v1_net_cash_delta": (
                    candidate["mean_net_cash_delta"] - v1["mean_net_cash_delta"]
                ),
                "candidate_minus_v1_gross_cash_in": (
                    candidate["mean_gross_cash_in"] - v1["mean_gross_cash_in"]
                ),
                "candidate_minus_v1_gross_cash_out": (
                    candidate["mean_gross_cash_out"] - v1["mean_gross_cash_out"]
                ),
            }
        output[source] = {
            "games": len(source_rows),
            "scenario_blocks": len({row["episode_id"] for row in source_rows}),
            "roles": by_role,
            "daily_gaps": gaps,
        }
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-dir", type=Path, default=evaluation.DEFAULT_PANEL)
    parser.add_argument("--limit-per-source", type=int, default=8)
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--balanced-genome-json", type=Path)
    parser.add_argument("--executor-tuning-json", type=Path)
    parser.add_argument("--candidate-label", default="B75_CURRENT_DEFAULT_BALANCED_ONLY")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=evaluation.DEFAULT_PANEL / "diagnostics/r2_1_b81_market_cash_gap",
    )
    args = parser.parse_args()

    manifest, scenarios = evaluation.manifest_scenarios(args.panel_dir, args.limit_per_source)
    balanced_genome = (
        json.loads(args.balanced_genome_json.read_text(encoding="utf-8"))
        if args.balanced_genome_json else {}
    )
    executor_tuning = (
        json.loads(args.executor_tuning_json.read_text(encoding="utf-8"))
        if args.executor_tuning_json else {}
    )
    manifest_contract = {
        "expected_module_version": manifest.get("expected_module_version"),
        "expected_configuration_sha256": manifest.get("expected_configuration_sha256"),
    }
    tasks = [
        (
            str(row["scenario_path"]), seat, manifest_contract,
            balanced_genome, executor_tuning,
        )
        for row in scenarios for seat in (0, 1)
    ]
    with concurrent.futures.ProcessPoolExecutor(max_workers=max(1, args.workers)) as pool:
        rows = list(pool.map(play, tasks, chunksize=1))

    integrity = (
        all(row["calls"] == 719 for row in rows)
        and sum(row["action_violations"] for row in rows) == 0
        and sum(row["trajectory_mismatches"] for row in rows) == 0
        and len(tasks) == 2 * len(scenarios)
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    events_path = args.output_dir / "cash_events.jsonl"
    with events_path.open("w", encoding="utf-8") as stream:
        for row in sorted(rows, key=lambda value: (
            value["source_class"], int(value["episode_id"]), int(value["candidate_seat"]),
        )):
            for event in row.pop("cash_events"):
                stream.write(json.dumps({
                    "source_class": row["source_class"],
                    "episode_id": row["episode_id"],
                    "candidate_seat": row["candidate_seat"],
                    **event,
                }, ensure_ascii=False) + "\n")

    payload = {
        "schema": "v117-r2.1-b81-realized-net-cash-diagnostic-v1",
        "research_version": "V117-R2.1-B81",
        "strength_status": "DEVELOPMENT_DIAGNOSTIC_ONLY",
        "candidate": args.candidate_label,
        "balanced_genome": balanced_genome or "R2.1_B_CURRENT_DEFAULT",
        "executor_tuning": executor_tuning or "R2.1_B_CURRENT_DEFAULT",
        "opponent": "FROZEN_V1_ADAPTIVE_MARKET",
        "engine": "1.32.7-scenario",
        "data_contract": {
            "minimum_observed_date": "2026-08-20",
            "split": "development",
            "sources_reported_separately": list(SOURCES),
            "module_version": manifest_contract["expected_module_version"],
            "configuration_sha256": manifest_contract["expected_configuration_sha256"],
            "historical_actions_results_market_path_loaded": False,
            "agents_restart_from_step_zero": True,
            "two_seats_per_scenario": True,
        },
        "semantics": {
            "net_cash_delta": "相邻 observation 的 money 差，属于引擎实际执行结果",
            "emitted_order_units": "模型请求量，仅作上下文，不代表实际成交量",
            "single_order_realized_cash": "当步仅一个市场订单时的实际净现金变化",
        },
        "integrity_pass": integrity,
        "scenario_blocks": len(scenarios),
        "games": len(rows),
        "manifest_sha256": sha256_file(args.panel_dir / "replay_panel_manifest_extracted.json"),
        "candidate_runtime_sha256": evaluation.runtime_sha256(),
        "v1_sha256": evaluation.sha256_file(evaluation.V1_PATH),
        "diagnostic_sha256": sha256_file(Path(__file__)),
        "cash_events_sha256": sha256_file(events_path),
        "source_summary": summarize(rows),
        "games_detail": rows,
        "limitations": [
            "这是 Development 归因，不是冻结测试或金牌证据",
            "多订单同一步时只报告真实净现金，不能把净额强行拆到某个商品",
            "当前只诊断 B75 均衡专家，不证明 HMoE 已触发",
        ],
    }
    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "integrity_pass": integrity,
        "scenario_blocks": len(scenarios),
        "games": len(rows),
        "output": str(summary_path),
    }, ensure_ascii=False, indent=2))
    return 0 if integrity else 1


if __name__ == "__main__":
    raise SystemExit(main())
