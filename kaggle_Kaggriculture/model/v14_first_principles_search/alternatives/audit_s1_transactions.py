"""在 screen36 首个已暴露 source 上核验 S1 的真实两回合闭环。"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import sys
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[3]
MODEL_ROOT = HERE.parents[1]
V10 = MODEL_ROOT / "v10_replay_lolo_router"
for value in (str(WORKSPACE), str(V10)):
    if value not in sys.path:
        sys.path.insert(0, value)

from kaggle_environments import make  # noqa: E402
from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import (  # noqa: E402
    create_agent,
    load_registry,
)
from kaggle_Kaggriculture.model.v14_first_principles_search.alternatives.s1_wheat_squeeze.main import (  # noqa: E402
    _town_wheat_drain,
)


CANDIDATE = "v14_s1_inventory_neutral_wheat_squeeze"
ANCHORS = ("v12a2_no_shop_gate", "v12_incumbent_r002")
PANEL = MODEL_ROOT / "v13_dual_anchor_search" / "protocol" / "screen_panel.json"
REGISTRY = HERE / "dev_registry.json"
OUTPUT = HERE / "s1_transaction_audit.json"


def _canonical(action: Any) -> dict[str, list[Any]]:
    source = dict(action or {})
    return {
        "farmer": list(source.get("farmer") or ["PASS"]),
        "hands": [list(item or ["PASS"]) for item in source.get("hands", [])],
        "market": [list(item) for item in source.get("market", [])],
    }


def _one(task: dict[str, Any]) -> dict[str, Any]:
    registry = load_registry(REGISTRY)
    candidate = create_agent(registry, CANDIDATE)
    opponent = create_agent(registry, task["anchor"])
    seed, seat = int(task["seed"]), int(task["candidate_seat"])
    random.seed(seed * 104729 + seat * 1009)
    np.random.seed((seed + seat * 65537) % (2**32 - 1))
    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    env.reset(2)
    pending: dict[str, Any] | None = None
    events: list[dict[str, Any]] = []
    last_prepared = last_executed = 0
    for step in range(719):
        for state in env.state:
            state.observation.step = step
        candidate_obs = env.state[seat].observation
        opponent_obs = env.state[1 - seat].observation
        candidate_action = _canonical(candidate(candidate_obs, env.configuration))
        opponent_action = _canonical(opponent(opponent_obs, env.configuration))
        diag = candidate.diagnostics()
        prepared = int(diag.get("s1_prepared", 0) or 0)
        executed = int(diag.get("s1_executed", 0) or 0)
        if prepared > last_prepared:
            pending = dict(diag.get("s1_pending") or {})
            if not pending:
                raise AssertionError("prepared without pending payload")
        if executed > last_executed:
            if pending is None:
                raise AssertionError("executed without prior pending payload")
            q, r = int(pending["q"]), int(pending["r"])
            before = int(candidate_obs.market.inventory.WHEAT)
            expected = before + r - q - _town_wheat_drain(candidate_obs, step)
            event = {
                "step": step,
                "q": q,
                "r": r,
                "candidate_action": candidate_action,
                "opponent_action": opponent_action,
                "inventory_before": before,
                "expected_inventory_after": expected,
            }
            events.append(event)
            pending = None
        last_prepared, last_executed = prepared, executed
        actions = (
            [candidate_action, opponent_action]
            if seat == 0
            else [opponent_action, candidate_action]
        )
        env.step(actions)
        if events and "actual_inventory_after" not in events[-1]:
            event = events[-1]
            if int(event["step"]) == step:
                actual = int(env.state[seat].observation.market.inventory.WHEAT)
                event["actual_inventory_after"] = actual
                event["opponent_exact_singleton_buy"] = event["opponent_action"][
                    "market"
                ] == [["BUY_PRODUCT", "WHEAT", int(event["q"])]]
                event["inventory_resynchronised"] = (
                    actual == int(event["expected_inventory_after"])
                )
        if all(str(state.status) == "DONE" for state in env.state):
            break
    final_diag = candidate.diagnostics()
    return {
        **task,
        "events": events,
        "prepared": int(final_diag.get("s1_prepared", 0) or 0),
        "executed": int(final_diag.get("s1_executed", 0) or 0),
        "unwinds": int(final_diag.get("s1_unwinds", 0) or 0),
        "faults": int(final_diag.get("s1_pending_faults", 0) or 0),
        "statuses": [str(state.status) for state in env.state],
        "passed": bool(events)
        and all(
            event["opponent_exact_singleton_buy"]
            and event["inventory_resynchronised"]
            for event in events
        )
        and int(final_diag.get("s1_unwinds", 0) or 0) == 0
        and int(final_diag.get("s1_pending_faults", 0) or 0) == 0,
    }


def main() -> None:
    panel = json.loads(PANEL.read_text(encoding="utf-8"))
    if panel.get("kind") != "screen" or panel.get("test_source_count") != 0:
        raise ValueError("not the exposed screen panel")
    source = panel["records"][0]
    tasks = [
        {
            "anchor": anchor,
            "candidate_seat": seat,
            "seed": int(source["seed"]),
            "episode_id": str(source["episode_id"]),
        }
        for anchor in ANCHORS
        for seat in (0, 1)
    ]
    with ProcessPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(_one, tasks))
    report = {
        "schema": "kaggriculture-v14-s1-real-transaction-audit-1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scope": "first source of already-exposed V13 screen36",
        "new_panel_or_test_used": False,
        "games": rows,
        "games_checked": len(rows),
        "events_checked": sum(len(row["events"]) for row in rows),
        "all_opponent_buys_exact": all(
            event["opponent_exact_singleton_buy"]
            for row in rows
            for event in row["events"]
        ),
        "all_market_inventory_resynchronised": all(
            event["inventory_resynchronised"]
            for row in rows
            for event in row["events"]
        ),
        "passed": all(row["passed"] for row in rows),
    }
    OUTPUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({key: report[key] for key in ("games_checked", "events_checked", "all_opponent_buys_exact", "all_market_inventory_resynchronised", "passed")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
