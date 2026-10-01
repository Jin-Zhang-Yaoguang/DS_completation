#!/usr/bin/env python3
"""诊断 B113 与冻结 V1 的资本配置漏斗。

只读取已准入的 Development 外生场景，双方从 step 0 独立决策并交换座位。
订单是意图；相邻 observation 的现金和资产变化才用于确认实际结果。
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
LAND_PRICES = (1000, 2000, 4000)
SEED_COST = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
ANIMAL_COST = {"GOOSE": 300, "COW": 400, "SHEEP": 500}
PURCHASE_CATEGORY = {
    "BUY_LAND": "LAND",
    "BUY_SEED": "SEED",
    "BUY_ANIMAL": "ANIMAL",
    "HIRE": "HIRE",
    "BUY_PRODUCT": "PRODUCT",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fib(index: int) -> int:
    left, right = 0, 1
    for _ in range(max(0, int(index))):
        left, right = right, left + right
    return left


def phase(day: int) -> str:
    if day <= 9:
        return "BEFORE_PRIMARY_RECEIPT"
    if day <= 18:
        return "REINVESTMENT"
    return "LATE_SEASON"


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


def parse_orders(action: dict[str, Any], observation: dict[str, Any], seat: int) -> list[dict[str, Any]]:
    farm = (observation.get("farms") or [{}, {}])[seat]
    prices = dict((observation.get("market") or {}).get("prices") or {})
    lands = len(farm.get("unlocked_quadrants", []) or [])
    hires_today = max(0, int(farm.get("hires_today", 0) or 0))
    hire_offset = 0
    rows: list[dict[str, Any]] = []
    for raw in action.get("market", []) or []:
        if not raw:
            continue
        op = str(raw[0])
        item = str(raw[1]) if len(raw) >= 2 else "NONE"
        quantity = max(0, int(raw[2])) if len(raw) >= 3 else 1
        category = PURCHASE_CATEGORY.get(op, "SALE" if op == "SELL" else "OTHER")
        unit_cost = 0
        if op == "BUY_LAND":
            unit_cost = LAND_PRICES[min(max(0, lands - 1), len(LAND_PRICES) - 1)]
            lands += 1
        elif op == "BUY_SEED":
            unit_cost = SEED_COST.get(item, 0)
        elif op == "BUY_ANIMAL":
            unit_cost = ANIMAL_COST.get(item, 0)
        elif op == "BUY_PRODUCT":
            unit_cost = max(1, int(prices.get(item, 1) or 1))
        elif op == "HIRE":
            unit_cost = fib(hires_today + hire_offset)
            hire_offset += 1
        rows.append({
            "op": op,
            "item": item,
            "category": category,
            "requested_units": quantity,
            "public_unit_cost": unit_cost,
            "requested_notional": unit_cost * quantity,
        })
    return rows


def total_owned(snapshot: dict[str, Any], item: str) -> int:
    placed = int((snapshot.get("animals") or {}).get(item, 0))
    shed = int((snapshot.get("shed") or {}).get(item, 0))
    carried = int((snapshot.get("carried") or {}).get(item, 0))
    return placed + shed + carried


def total_stock(snapshot: dict[str, Any], item: str) -> int:
    return int((snapshot.get("shed") or {}).get(item, 0)) + int(
        (snapshot.get("carried") or {}).get(item, 0)
    )


def confirmed_deltas(before: dict[str, Any], after: dict[str, Any]) -> dict[str, int]:
    deltas: dict[str, int] = {
        "LAND:NONE": max(0, int(after["lands"]) - int(before["lands"])),
        "HIRE:NONE": max(0, int(after["actors"]) - int(before["actors"])),
    }
    for item in ANIMAL_COST:
        deltas[f"ANIMAL:{item}"] = max(0, total_owned(after, item) - total_owned(before, item))
    for item in SEED_COST:
        # 同步 PLANT 会消耗种子，因此这里只是 observation 可确认的保守下界。
        deltas[f"SEED:{item}"] = max(
            0,
            int((after.get("seeds") or {}).get(item, 0))
            - int((before.get("seeds") or {}).get(item, 0)),
        )
    product_items = set(before.get("shed") or {}) | set(before.get("carried") or {})
    product_items |= set(after.get("shed") or {}) | set(after.get("carried") or {})
    for item in sorted(product_items - set(ANIMAL_COST)):
        deltas[f"PRODUCT:{item}"] = max(0, total_stock(after, item) - total_stock(before, item))
    return deltas


def empty_role() -> dict[str, Any]:
    return {
        "gross_cash_out": 0,
        "purchase_step_count": 0,
        "request_counts": Counter(),
        "request_units": Counter(),
        "requested_notional": Counter(),
        "requested_notional_by_phase": Counter(),
        "exact_attributed_cash_out": Counter(),
        "unallocated_purchase_cash_out": 0,
        "confirmed_units_lower_bound": Counter(),
        "confirmed_spend_lower_bound": Counter(),
        "first_confirmed_step": {},
        "milestones": {},
        "daily_end": {},
    }


def update_milestones(target: dict[str, int], snapshot: dict[str, Any], step: int) -> None:
    values = {
        "LANDS_2": int(snapshot["lands"]) >= 2,
        "LANDS_3": int(snapshot["lands"]) >= 3,
        "ACTORS_5": int(snapshot["actors"]) >= 5,
        "ACTORS_8": int(snapshot["actors"]) >= 8,
        "ACTORS_11": int(snapshot["actors"]) >= 11,
        "COWS_3": total_owned(snapshot, "COW") >= 3,
        "COWS_4": total_owned(snapshot, "COW") >= 4,
        "COWS_6": total_owned(snapshot, "COW") >= 6,
        "SHEEP_3": total_owned(snapshot, "SHEEP") >= 3,
        "SHEEP_4": total_owned(snapshot, "SHEEP") >= 4,
    }
    for name, reached in values.items():
        if reached and name not in target:
            target[name] = step


def confirmed_cost(key: str, units: int, before: dict[str, Any]) -> int:
    category, item = key.split(":", 1)
    if category == "LAND":
        start = max(0, int(before["lands"]) - 1)
        return sum(LAND_PRICES[min(start + offset, len(LAND_PRICES) - 1)] for offset in range(units))
    if category == "ANIMAL":
        return units * ANIMAL_COST.get(item, 0)
    if category == "SEED":
        return units * SEED_COST.get(item, 0)
    return 0


def play(task: tuple[str, int, dict[str, Any], dict[str, Any], dict[str, Any]]) -> dict[str, Any]:
    scenario_path_raw, candidate_seat, manifest_contract, balanced_genome, executor_tuning = task
    scenario_path = Path(scenario_path_raw)
    scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
    validate_scenario(scenario, manifest_contract)

    identity = f"capital_{os.getpid()}_{scenario['episode_id']}_{candidate_seat}"
    candidate, v1_agent = evaluation.load_agents(identity, balanced_genome, executor_tuning)
    agents = [v1_agent, v1_agent]
    agents[candidate_seat] = candidate.act
    roles = {candidate_seat: "candidate", 1 - candidate_seat: "v1"}
    totals = {"candidate": empty_role(), "v1": empty_role()}

    schedule = list(scenario["realized_public_shops"])
    engine = evaluation.load_scenario_engine()
    game = engine.Game(int(scenario["actual_seed"]), int(scenario.get("step_count", 720)))
    game.force_shops(evaluation.visible_shops(schedule, 0))
    action_violations = 0
    trajectory_mismatches = 0
    calls = 0

    while not game.done:
        step = int(game.step_count)
        day = step // 24
        before_observations = [game.observe(0), game.observe(1)]
        expected_shops = evaluation.visible_shops(schedule, step)
        trajectory_mismatches += sum(
            list((observation.get("town") or {}).get("unlocked_shops") or []) != expected_shops
            for observation in before_observations
        )
        actions = [agents[seat](before_observations[seat]) for seat in (0, 1)]
        action_violations += evaluation.validate_action(
            actions[candidate_seat], before_observations[candidate_seat]
        )
        game.step(actions[0], actions[1])
        after_observations = [game.observe(0), game.observe(1)]

        for seat in (0, 1):
            role = roles[seat]
            row = totals[role]
            before = evaluation.economy_snapshot(before_observations[seat], seat)
            after = evaluation.economy_snapshot(after_observations[seat], seat)
            orders = parse_orders(actions[seat], before_observations[seat], seat)
            purchases = [order for order in orders if order["category"] in PURCHASE_CATEGORY.values()]
            cash_delta = int(after["money"]) - int(before["money"])
            cash_out = max(0, -cash_delta)
            row["gross_cash_out"] += cash_out
            if purchases:
                row["purchase_step_count"] += 1
            categories = {str(order["category"]) for order in purchases}
            has_sale = any(order["category"] == "SALE" for order in orders)
            if purchases and not has_sale and len(categories) == 1:
                row["exact_attributed_cash_out"][next(iter(categories))] += cash_out
            elif purchases and cash_out:
                row["unallocated_purchase_cash_out"] += cash_out

            for order in purchases:
                key = f"{order['category']}:{order['item']}"
                row["request_counts"][key] += 1
                row["request_units"][key] += int(order["requested_units"])
                row["requested_notional"][key] += int(order["requested_notional"])
                phase_key = f"{phase(day)}:{order['category']}"
                row["requested_notional_by_phase"][phase_key] += int(order["requested_notional"])

            deltas = confirmed_deltas(before, after)
            requested_keys = {f"{order['category']}:{order['item']}" for order in purchases}
            if any(order["category"] == "LAND" for order in purchases):
                requested_keys.add("LAND:NONE")
            if any(order["category"] == "HIRE" for order in purchases):
                requested_keys.add("HIRE:NONE")
            for key in sorted(requested_keys):
                units = int(deltas.get(key, 0))
                if units <= 0:
                    continue
                row["confirmed_units_lower_bound"][key] += units
                row["confirmed_spend_lower_bound"][key] += confirmed_cost(key, units, before)
                row["first_confirmed_step"].setdefault(key, step)
            update_milestones(row["milestones"], after, step)
            row["daily_end"][str(day)] = after

        if not game.done:
            game.force_shops(evaluation.visible_shops(schedule, int(game.step_count)))
        calls += 1

    rewards = [float(game.reward(0)), float(game.reward(1))]
    candidate_ledger = (
        candidate.status().get("seats", {}).get(candidate_seat, {}).get("ledger", {})
    )
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
        "candidate_daily_outcomes": candidate_ledger.get("daily_outcomes", []),
        "roles": {role: serialise_role(row) for role, row in totals.items()},
    }


def serialise_role(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    for key in (
        "request_counts", "request_units", "requested_notional",
        "requested_notional_by_phase", "exact_attributed_cash_out",
        "confirmed_units_lower_bound", "confirmed_spend_lower_bound",
    ):
        result[key] = dict(sorted(result[key].items()))
    return result


def mean(values: list[float]) -> float:
    return statistics.mean(values) if values else 0.0


def mean_counters(rows: list[dict[str, Any]], key: str) -> dict[str, float]:
    total: Counter[str] = Counter()
    for row in rows:
        total.update({str(name): float(value) for name, value in (row.get(key) or {}).items()})
    divisor = max(1, len(rows))
    return {name: value / divisor for name, value in sorted(total.items())}


def summarize_role(rows: list[dict[str, Any]]) -> dict[str, Any]:
    milestones = sorted({name for row in rows for name in (row.get("milestones") or {})})
    first_keys = sorted({name for row in rows for name in (row.get("first_confirmed_step") or {})})
    days = sorted({day for row in rows for day in (row.get("daily_end") or {})}, key=int)
    return {
        "games": len(rows),
        "mean_gross_cash_out": mean([float(row["gross_cash_out"]) for row in rows]),
        "mean_purchase_step_count": mean([float(row["purchase_step_count"]) for row in rows]),
        "mean_unallocated_purchase_cash_out": mean([
            float(row["unallocated_purchase_cash_out"]) for row in rows
        ]),
        "mean_request_units": mean_counters(rows, "request_units"),
        "mean_requested_notional": mean_counters(rows, "requested_notional"),
        "mean_requested_notional_by_phase": mean_counters(rows, "requested_notional_by_phase"),
        "mean_exact_attributed_cash_out": mean_counters(rows, "exact_attributed_cash_out"),
        "mean_confirmed_units_lower_bound": mean_counters(rows, "confirmed_units_lower_bound"),
        "mean_confirmed_spend_lower_bound": mean_counters(rows, "confirmed_spend_lower_bound"),
        "milestone_reach_rate": {
            name: sum(name in (row.get("milestones") or {}) for row in rows) / max(1, len(rows))
            for name in milestones
        },
        "mean_first_milestone_day": {
            name: mean([
                float(row["milestones"][name]) / 24.0
                for row in rows if name in (row.get("milestones") or {})
            ]) for name in milestones
        },
        "mean_first_confirmed_day": {
            name: mean([
                float(row["first_confirmed_step"][name]) / 24.0
                for row in rows if name in (row.get("first_confirmed_step") or {})
            ]) for name in first_keys
        },
        "daily_mean_economy": {
            day: {
                "money": mean([
                    float(row["daily_end"][day]["money"])
                    for row in rows if day in (row.get("daily_end") or {})
                ]),
                "lands": mean([
                    float(row["daily_end"][day]["lands"])
                    for row in rows if day in (row.get("daily_end") or {})
                ]),
                "actors": mean([
                    float(row["daily_end"][day]["actors"])
                    for row in rows if day in (row.get("daily_end") or {})
                ]),
                "cows_owned": mean([
                    float(total_owned(row["daily_end"][day], "COW"))
                    for row in rows if day in (row.get("daily_end") or {})
                ]),
                "sheep_owned": mean([
                    float(total_owned(row["daily_end"][day], "SHEEP"))
                    for row in rows if day in (row.get("daily_end") or {})
                ]),
                "crops": mean([
                    float(sum((row["daily_end"][day].get("crops") or {}).values()))
                    for row in rows if day in (row.get("daily_end") or {})
                ]),
            } for day in days
        },
    }


def numeric_gap(candidate: dict[str, Any], v1: dict[str, Any], key: str) -> dict[str, float]:
    names = sorted(set(candidate.get(key) or {}) | set(v1.get(key) or {}))
    return {
        name: float((candidate.get(key) or {}).get(name, 0.0))
        - float((v1.get(key) or {}).get(name, 0.0))
        for name in names
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for source in SOURCES:
        games = [row for row in rows if row["source_class"] == source]
        roles = {
            role: summarize_role([game["roles"][role] for game in games])
            for role in ("candidate", "v1")
        }
        output[source] = {
            "games": len(games),
            "scenario_blocks": len({row["episode_id"] for row in games}),
            "mean_candidate_reward": mean([float(row["candidate_reward"]) for row in games]),
            "mean_v1_reward": mean([float(row["v1_reward"]) for row in games]),
            "mean_margin": mean([float(row["margin"]) for row in games]),
            "roles": roles,
            "candidate_minus_v1": {
                "gross_cash_out": (
                    roles["candidate"]["mean_gross_cash_out"] - roles["v1"]["mean_gross_cash_out"]
                ),
                "request_units": numeric_gap(roles["candidate"], roles["v1"], "mean_request_units"),
                "requested_notional": numeric_gap(
                    roles["candidate"], roles["v1"], "mean_requested_notional"
                ),
                "requested_notional_by_phase": numeric_gap(
                    roles["candidate"], roles["v1"], "mean_requested_notional_by_phase"
                ),
                "exact_attributed_cash_out": numeric_gap(
                    roles["candidate"], roles["v1"], "mean_exact_attributed_cash_out"
                ),
                "confirmed_units_lower_bound": numeric_gap(
                    roles["candidate"], roles["v1"], "mean_confirmed_units_lower_bound"
                ),
                "confirmed_spend_lower_bound": numeric_gap(
                    roles["candidate"], roles["v1"], "mean_confirmed_spend_lower_bound"
                ),
            },
        }
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-dir", type=Path, default=evaluation.DEFAULT_PANEL)
    parser.add_argument("--limit-per-source", type=int, default=8)
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--balanced-genome-json", type=Path)
    parser.add_argument("--executor-tuning-json", type=Path)
    parser.add_argument("--candidate-label", default="B113_CURRENT_DEFAULT_BALANCED_ONLY")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=evaluation.DEFAULT_PANEL / "diagnostics/r2_1_b114_capital_allocation",
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
        (str(row["scenario_path"]), seat, manifest_contract, balanced_genome, executor_tuning)
        for row in scenarios for seat in (0, 1)
    ]
    with concurrent.futures.ProcessPoolExecutor(max_workers=max(1, args.workers)) as pool:
        rows = list(pool.map(play, tasks, chunksize=1))

    integrity = (
        len(tasks) == 2 * len(scenarios)
        and all(row["calls"] == 719 for row in rows)
        and sum(row["action_violations"] for row in rows) == 0
        and sum(row["trajectory_mismatches"] for row in rows) == 0
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "v117-r2.1-b114-capital-allocation-diagnostic-v1",
        "research_version": "V117-R2.1-B114",
        "strength_status": "DEVELOPMENT_DIAGNOSTIC_ONLY",
        "candidate": args.candidate_label,
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
            "gross_cash_out": "相邻 observation 的负 money 变化；含混合订单时不能强拆到类别",
            "exact_attributed_cash_out": "无 SELL 且只有一个采购类别时可精确归类的真实现金流出",
            "requested_notional": "按当步公开价格/规则成本计算的请求金额，不代表成交",
            "confirmed_units_lower_bound": "相邻 observation 确认的正资产增量；同步消耗会导致低估",
            "phase_boundary": "第 0-9 天首轮主收据前；第 10-18 天再投资；第 19-29 天后期",
        },
        "integrity_pass": integrity,
        "scenario_blocks": len(scenarios),
        "games": len(rows),
        "manifest_sha256": sha256_file(args.panel_dir / "replay_panel_manifest_extracted.json"),
        "candidate_runtime_sha256": evaluation.runtime_sha256(),
        "v1_sha256": evaluation.sha256_file(evaluation.V1_PATH),
        "diagnostic_sha256": sha256_file(Path(__file__)),
        "source_summary": summarize(rows),
        "games_detail": rows,
        "limitations": [
            "这是 Development 归因，不是冻结测试、线上结果或金牌证据",
            "订单请求不等于成交；混合 SELL/采购步骤的现金流不强行拆分",
            "种子和产品可能在同一步被使用，确认增量是保守下界",
            "当前只诊断 B113 Balanced，不能证明 HMoE 已触发",
        ],
    }
    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "summary": str(summary_path),
        "integrity_pass": integrity,
        "scenario_blocks": len(scenarios),
        "games": len(rows),
    }, ensure_ascii=False, indent=2))
    return 0 if integrity else 2


if __name__ == "__main__":
    raise SystemExit(main())
