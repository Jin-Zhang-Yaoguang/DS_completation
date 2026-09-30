#!/usr/bin/env python3
"""R2.1-A 七类损失归因的确定性触发、去重和信息边界测试。"""

from __future__ import annotations

import ast
import importlib.util
import json
import sys
import sysconfig
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
CPPSIM = (MODEL / "community_research" / "2026-08-26" / "live_cli" /
          "external_repos" / "kaggriculture-cppsim")
RESULTS = HERE / "loss_attribution_test_results.json"
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


def load_engine() -> Any:
    builds = sorted((CPPSIM / "build").glob("lib.*"))
    suffix = sysconfig.get_config_var("EXT_SUFFIX") or ".so"
    for build in reversed(builds):
        extension = build / f"kagsim{suffix}"
        if extension.is_file():
            sys.path.insert(0, str(build))
            import kagsim  # type: ignore
            return kagsim
    scenario = (MODEL / "v116_heuristic_gold_search/replay_arena/build" /
                f"kagsim_scenario{suffix}")
    spec = importlib.util.spec_from_file_location("kagsim_scenario", scenario)
    if spec is None or spec.loader is None:
        raise RuntimeError("缺少当前 Python ABI 的 kagsim/kagsim_scenario")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def dummy_executor(*, target: tuple[int, int] | None = None,
                   overdue: tuple[dict[str, Any], ...] = ()) -> Any:
    return SimpleNamespace(
        actor_targets=(target,), actor_tasks=("test-task",), overdue_task_details=overdue,
    )


def dummy_market(finance: int = 0, high_price_unsold: dict[str, int] | None = None) -> Any:
    return SimpleNamespace(
        budget_spent=0,
        diagnostics={
            "financing_shortfall_value": finance,
            "cash_shortfall_value": finance,
            "contract_budget_shortfall_value": 0,
            "purchase_execution_shortfall_value": 0,
            "desired_purchase_value": finance,
            "high_price_unsold": dict(high_price_unsold or {}),
        },
    )


def dummy_control(action: list[Any], *, market: list[list[Any]] | None = None,
                  mode: str = "NORMAL") -> Any:
    return SimpleNamespace(
        action={"farmer": list(action), "hands": [], "market": list(market or [])},
        mode=SimpleNamespace(value=mode),
    )


def main() -> int:
    from diagnostics.loss_attribution import LOSS_CATEGORIES, LossAttributionLedger
    from experts import BalancedExpert
    from state_ledger import StateLedger

    kagsim = load_engine()
    observation = kagsim.Game(117210).observe(0)
    state_ledger = StateLedger()
    initial, feedback = state_ledger.observe(observation)
    prices = dict(initial.prices)
    prices["TOMATO"] = max(100, prices.get("TOMATO", 60))
    base = replace(
        initial, prices=prices, shed={"TOMATO": 10}, shed_used=10,
        inventories=tuple({} for _ in initial.inventories),
        day=0, hour=0, step=0, remaining_steps=719,
    )
    contract = BalancedExpert().propose(base, feedback, None)
    contract = replace(contract, inventory_reserves={}, cash_reserve=0, purchase_budget=10_000)
    ledger = LossAttributionLedger()

    source = base.positions[0]
    target = (source[0] + 1, source[1])
    overdue = ({
        "signature": "harvest:0:0:0:0", "verb": "HARVEST", "x": 0, "y": 0,
        "deadline": 0, "task_value": 4.0, "estimated_value": 100.0,
    },)
    ledger.observe(base)
    ledger.record_decision(
        base, contract, feedback, dummy_executor(target=target, overdue=overdue),
        dummy_market(500, {"TOMATO": 5}), dummy_control(["EAST"]),
    )

    lowered_prices = dict(base.prices)
    lowered_prices["TOMATO"] = base.prices["TOMATO"] - 20
    after_move = replace(base, step=1, hour=1, prices=lowered_prices, price_delta={"TOMATO": -20})
    ledger.observe(after_move)
    ledger.record_decision(
        after_move, contract, feedback, dummy_executor(overdue=overdue),
        dummy_market(300), dummy_control(["PASS"]),
    )

    grid = [list(row) for row in base.grid]
    grid[0][0] = {"kind": "PASTURE", "animal": {"kind": "SHEEP"},
                  "fed_today": False, "yield_units": 1}
    grid[0][1] = {"kind": "COOP", "animal": {"kind": "GOOSE"},
                  "fed_today": False, "yield_units": 1}
    day_end = replace(
        after_move, grid=tuple(tuple(row) for row in grid), step=23, hour=23,
        shed={"TOMATO": 10}, shed_used=10,
        inventories=tuple({} for _ in after_move.inventories),
    )
    ledger.observe(day_end)
    ledger.record_decision(
        day_end, contract, feedback, dummy_executor(), dummy_market(), dummy_control(["PASS"]),
    )

    next_day = replace(day_end, step=24, day=1, hour=0, remaining_steps=695)
    ledger.observe(next_day)
    ledger.record_decision(
        next_day, replace(contract, issued_day=1, issued_at=24), feedback,
        dummy_executor(), dummy_market(), dummy_control(["PASS"]),
    )

    terminal = replace(
        next_day, step=718, day=29, hour=22, remaining_steps=1,
        seeds={"MELON": 2}, shed={"TOMATO": 10}, shed_used=10,
    )
    terminal_contract = replace(contract, issued_day=29, issued_at=718)
    ledger.observe(terminal)
    ledger.record_decision(
        terminal, terminal_contract, feedback, dummy_executor(), dummy_market(),
        dummy_control(["PASS"], market=[]),
    )

    status = ledger.status()
    totals = dict(status["totals"])
    source = (HERE / "diagnostics" / "loss_attribution.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    attribute_reads = [
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    ]
    checks = {
        "all_seven_categories_defined": set(totals) == set(LOSS_CATEGORIES),
        "all_seven_categories_triggered": all(float(totals[key]["estimated_value"]) > 0 for key in LOSS_CATEGORIES),
        "financing_uses_daily_peak_not_turn_sum": float(totals["FINANCING_SHORTFALL"]["estimated_value"]) == 500.0,
        "overdue_task_is_deduplicated": int(totals["OVERDUE_TASK"]["events"]) == 1,
        "blocked_move_is_detected": int(totals["UNPRODUCTIVE_MOVE"]["events"]) == 1,
        "high_price_loss_requires_observed_drop": int(totals["MISSED_HIGH_PRICE_SALE"]["events"]) == 1,
        "terminal_is_recorded_once": int(totals["TERMINAL_UNREALIZED"]["events"]) == 1,
        "top_three_are_ranked": [row["estimated_value"] for row in status["top_losses"]]
                                  == sorted((row["estimated_value"] for row in status["top_losses"]), reverse=True),
        "diagnostics_forbidden_as_strategy_input": status["forbidden_as_strategy_input"] is True,
        "no_replay_or_future_runtime_attribute": not any(
            name in {"replay_id", "seed", "future_shop", "teacher_id", "reward", "winner"}
            for name in attribute_reads
        ),
    }
    payload = {
        "schema": "v117-r2.1-a-loss-attribution-tests-v1",
        "checks": checks,
        "totals": totals,
        "top_losses": status["top_losses"],
        "event_count": len(status["recent_events"]),
        "pass": all(checks.values()),
    }
    RESULTS.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
