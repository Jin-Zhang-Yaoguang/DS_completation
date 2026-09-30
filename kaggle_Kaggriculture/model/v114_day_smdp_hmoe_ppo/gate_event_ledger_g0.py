"""Run V12's deterministic G0 event-ledger safety gate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile

from event_ledger import (
    EconomySnapshot,
    EventKind,
    MarketEvent,
    TransactionIntent,
    TransactionLedger,
)
from event_ledger_controller import EventLedgerController


HERE = Path(__file__).resolve().parent


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def observation(step: int, money: int = 3000, seeds: int = 0) -> dict:
    return {
        "step": step, "day": step // 24, "hour": step % 24, "player": 0,
        "episode_steps": 720,
        "farms": [
            {"money": money, "hands": [], "unlocked_quadrants": [0], "tiles": []},
            {"money": 3000, "hands": [], "unlocked_quadrants": [0], "tiles": []},
        ],
        "private": {
            "seeds": {"WHEAT": seeds}, "shed": {}, "inventories": [{}],
        },
        "town": {"unlocked_shops": []},
    }


def run_gate() -> dict:
    def unit_policy(_):
        return {"farmer": ["PASS"], "hands": [], "market": []}

    def market_policy(_, event):
        return [TransactionIntent(
            "BUY_SEED", "WHEAT", 5, 10, 50, 1000, event.opened_step
        )]

    controller = EventLedgerController(unit_policy, market_policy)
    repeated = [controller.act(observation(0)) for _ in range(100)]
    repeated_commits = sum(bool(action["market"]) for action in repeated)
    unauthorized_non_event_orders = 0
    for step in range(1, 24):
        unauthorized_non_event_orders += int(bool(controller.act(observation(step))["market"]))

    terminal = EventLedgerController(unit_policy, market_policy)
    terminal_orders = terminal.act(observation(671))["market"]

    budget = TransactionLedger(season_budget=600)
    snapshot = EconomySnapshot(0, 3000, 1, 1, {}, {})
    for index in range(32):
        event = MarketEvent(f"event-{index}", 1, EventKind.DAY_START, index)
        budget.open_event(event)
        intent = TransactionIntent("HIRE", None, 2, 200, 400, 1000, index, worker_cap=16)
        key = budget.propose(event.event_id, intent, snapshot)
        if key is not None:
            budget.emit(key, index)
    budget_audit = budget.audit()

    source_paths = [HERE / "event_ledger.py", HERE / "event_ledger_controller.py"]
    forbidden = ("v11_replay_lineage_bc.msgpack", "v76", "foundation_l1_v2_survival")
    forbidden_hits = {
        path.name: [token for token in forbidden if token in path.read_text(encoding="utf-8").lower()]
        for path in source_paths
    }
    checks = {
        "one_commit_for_100_identical_inputs": repeated_commits == 1,
        "non_event_market_orders_zero": unauthorized_non_event_orders == 0,
        "terminal_procurement_orders_zero": terminal_orders == [],
        "terminal_procurement_rejection_recorded": (
            terminal.audit()["ledger"]["terminal_procurement_rejections"] == 1
        ),
        "season_spend_within_budget": budget_audit["season_spend"] <= 600,
        "maximum_one_commit_per_record": budget_audit["commit_count"] <= budget_audit["records"],
        "forbidden_historical_action_sources_absent": not any(forbidden_hits.values()),
    }
    return {
        "schema": "kaggriculture-v114-v12-event-ledger-g0-v1",
        "status": "PASS_G0" if all(checks.values()) else "FAIL_G0",
        "checks": checks,
        "repeated_inputs": 100,
        "repeated_commits": repeated_commits,
        "non_event_turns_checked": 23,
        "unauthorized_non_event_orders": unauthorized_non_event_orders,
        "terminal_orders": terminal_orders,
        "controller_audit": controller.audit(),
        "terminal_audit": terminal.audit(),
        "budget_audit": budget_audit,
        "source_sha256": {path.name: sha256_file(path) for path in source_paths},
        "forbidden_source_hits": forbidden_hits,
        "fresh_seed_consumed": False,
        "qualification_status": "G0_ONLY_NOT_UNIT_SKILL_NOT_EVENT_MARKET_NOT_FOUNDATION_NOT_GOLD",
    }


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as sink:
        json.dump(payload, sink, ensure_ascii=False, indent=2)
        sink.write("\n")
        temporary = Path(sink.name)
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run_gate()
    atomic_json(args.output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] != "PASS_G0":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
