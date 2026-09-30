"""Causal trigger audit for archived B-v1 using only the exposed screen18 panel.

The frozen formal panel is deliberately never opened.  Candidate outcomes and
their same-source/seat baseline-V8 controls come from ``runs_v3``.  Only tasks
whose archived diagnostics report at least one trigger are replayed, with the
archived decision function instrumented to recover product and public-bank
state at each trigger.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import copy
import json
from pathlib import Path
from typing import Any

from kaggle_environments import make

from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import (
    Registry,
    create_agent,
    load_registry,
)


HERE = Path(__file__).resolve().parent
RUNS = HERE.parent / "v12_validation" / "runs_v3"
COMBINED_REGISTRY = HERE.parent / "v12_validation" / "frozen_v3" / "combined_registry.json"
ARCHIVED_CLEAN = HERE / "archived" / "v1_market_feedback" / "clean_package"
OUTPUT = HERE / "archived" / "v1_market_feedback" / "screen_trigger_diagnosis.json"

PAIR_FILES = {
    "baseline_v1": (
        "screen_pool/v12b_market_feedback_router__vs__baseline_v1/games.jsonl",
        "screen_control/baseline_v8__vs__baseline_v1/games.jsonl",
    ),
    "baseline_v5": (
        "screen_pool/v12b_market_feedback_router__vs__baseline_v5/games.jsonl",
        "screen_control/baseline_v8__vs__baseline_v5/games.jsonl",
    ),
    "learned_router": (
        "screen_pool/v12b_market_feedback_router__vs__learned_router/games.jsonl",
        "screen_control/learned_router__vs__baseline_v8/games.jsonl",
    ),
    "r002_learned_router_topday_animal_throttle": (
        "screen_pool/v12b_market_feedback_router__vs__r002_learned_router_topday_animal_throttle/games.jsonl",
        "screen_control/r002_learned_router_topday_animal_throttle__vs__baseline_v8/games.jsonl",
    ),
    "rule_router": (
        "screen_pool/v12b_market_feedback_router__vs__rule_router/games.jsonl",
        "screen_control/baseline_v8__vs__rule_router/games.jsonl",
    ),
    "v5_topdays": (
        "screen_pool/v12b_market_feedback_router__vs__v5_topdays/games.jsonl",
        "screen_control/baseline_v8__vs__v5_topdays/games.jsonl",
    ),
    "v8_topdays": (
        "screen_pool/v12b_market_feedback_router__vs__v8_topdays/games.jsonl",
        "screen_control/v8_topdays__vs__baseline_v8/games.jsonl",
    ),
}


def _rows(relative: str) -> list[dict[str, Any]]:
    with (RUNS / relative).open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _subject(row: dict[str, Any], model_id: str) -> tuple[int, float, float]:
    seat = list(row["seat_models"]).index(model_id)
    rewards = [float(value) for value in row["rewards"]]
    margin = rewards[seat] - rewards[1 - seat]
    score = 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0
    return seat, margin, score


def _label(score: float) -> str:
    return "W" if score == 1.0 else "T" if score == 0.5 else "L"


def build_tasks() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    all_rows: list[dict[str, Any]] = []
    triggered: list[dict[str, Any]] = []
    for opponent, (candidate_file, control_file) in PAIR_FILES.items():
        controls = {}
        for row in _rows(control_file):
            seat, margin, score = _subject(row, "baseline_v8")
            key = (str(row["source"]["date"]), int(row["source"]["seed"]), seat)
            controls[key] = (margin, score)
        for row in _rows(candidate_file):
            seat, margin, score = _subject(row, "v12b_market_feedback_router")
            key = (str(row["source"]["date"]), int(row["source"]["seed"]), seat)
            control_margin, control_score = controls[key]
            status = row["agent_diagnostics"]["v12b_market_feedback_router"]["underlying"]["model_status"]
            record = {
                "opponent": opponent,
                "date": key[0],
                "seed": key[1],
                "candidate_seat": seat,
                "episode_id": str(row["source"].get("episode_id") or ""),
                "raw_candidate_rewards": [float(value) for value in row["rewards"]],
                "candidate_margin": margin,
                "candidate_score": score,
                "control_margin": control_margin,
                "control_score": control_score,
                "margin_delta": margin - control_margin,
                "score_delta": score - control_score,
                "transition": f"{_label(control_score)}→{_label(score)}",
                "trigger_count": int(status["trigger_count"]),
                "held_quantity": int(status["held_quantity"]),
            }
            all_rows.append(record)
            if record["trigger_count"] > 0:
                triggered.append(record)
    return all_rows, triggered


def _fresh_archived_candidate():
    spec = {
        "id": "v12b_market_feedback_router",
        "kind": "python",
        "path": str((ARCHIVED_CLEAN / "main.py").resolve()),
        "entrypoint": "agent",
        "family": "archived_v12b_v1",
        "lineage": ["baseline_v8", "v12b_market_feedback_router"],
        "code_paths": [
            str((ARCHIVED_CLEAN / "main.py").resolve()),
            str((ARCHIVED_CLEAN / "parent_agent.py").resolve()),
        ],
    }
    registry = Registry(
        path=(ARCHIVED_CLEAN / "_instrumented_registry.json").resolve(),
        models={spec["id"]: spec},
        raw={"models": [spec]},
    )
    return create_agent(registry, spec["id"])


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    getter = getattr(value, "get", None)
    return getter(key, default) if callable(getter) else getattr(value, key, default)


def replay_task(task: dict[str, Any]) -> dict[str, Any]:
    candidate = _fresh_archived_candidate()
    opponents = load_registry(COMBINED_REGISTRY)
    opponent = create_agent(opponents, task["opponent"])
    events: list[dict[str, Any]] = []
    module = candidate.module
    original = module.feedback_decision

    def instrumented(obs: Any, item: str, quantity: int, previous: Any):
        decision = original(obs, item, quantity, previous)
        if decision.get("triggered"):
            seat = 1 if int(_get(obs, "player", 0) or 0) == 1 else 0
            farms = list(_get(obs, "farms", []) or [])
            own_bank = float(_get(farms[seat], "money", 0) or 0) if len(farms) == 2 else 0.0
            opponent_bank = float(_get(farms[1 - seat], "money", 0) or 0) if len(farms) == 2 else 0.0
            bank_margin = own_bank - opponent_bank
            private = _get(obs, "private", {}) or {}
            shed = _get(private, "shed", {}) or {}
            event = copy.deepcopy(decision)
            event.update(
                step=int(_get(obs, "step", 0) or 0),
                day=int(_get(obs, "day", 0) or 0),
                seat=seat,
                own_public_bank=own_bank,
                opponent_public_bank=opponent_bank,
                public_bank_margin=bank_margin,
                public_bank_state="ahead" if bank_margin > 0 else "behind" if bank_margin < 0 else "tied",
                own_shed_item=int(_get(shed, item, 0) or 0),
                shops=[str(value) for value in (_get(_get(obs, "town", {}) or {}, "unlocked_shops", []) or [])],
            )
            events.append(event)
        return decision

    module.feedback_decision = instrumented
    agents = [candidate, opponent]
    if int(task["candidate_seat"]) == 1:
        agents.reverse()
    env = make("kaggriculture", configuration={"seed": int(task["seed"])}, debug=True)
    steps = env.run(agents)
    rewards = [float(state.reward or 0) for state in steps[-1]]
    statuses = [str(state.status) for state in steps[-1]]
    replayed = {
        **task,
        "replay_steps": len(steps),
        "replay_statuses": statuses,
        "replay_rewards": rewards,
        "reward_exact": rewards == list(task["raw_candidate_rewards"]),
        "events": events,
        "event_count_exact": len(events) == int(task["trigger_count"]),
    }
    return replayed


def _counter(rows: list[dict[str, Any]], key) -> dict[str, int]:
    return dict(sorted(Counter(key(row) for row in rows).items()))


def main() -> None:
    all_rows, triggered = build_tasks()
    with ProcessPoolExecutor(max_workers=8) as executor:
        traced = list(executor.map(replay_task, triggered))
    if not all(row["reward_exact"] and row["event_count_exact"] for row in traced):
        raise RuntimeError("instrumented replay did not exactly reproduce archived screen")
    events = [
        {**event, "opponent": row["opponent"], "transition": row["transition"], "seed": row["seed"], "date": row["date"], "candidate_seat": row["candidate_seat"]}
        for row in traced
        for event in row["events"]
    ]
    payload = {
        "schema": "kaggriculture-v12b-v1-screen-trigger-diagnosis-1",
        "data_scope": "frozen_v3 screen18 only",
        "formal_panel_accessed": False,
        "raw_tasks": len(all_rows),
        "triggered_tasks": len(triggered),
        "trigger_events": len(events),
        "all_replays_exact": True,
        "transition_counts_all": _counter(all_rows, lambda row: row["transition"]),
        "transition_counts_triggered_tasks": _counter(triggered, lambda row: row["transition"]),
        "events_by_product": _counter(events, lambda row: row["item"]),
        "events_by_bank_state": _counter(events, lambda row: row["public_bank_state"]),
        "events_by_transition": _counter(events, lambda row: row["transition"]),
        "events_by_product_and_transition": _counter(events, lambda row: f"{row['item']}|{row['transition']}"),
        "events_by_product_and_bank_state": _counter(events, lambda row: f"{row['item']}|{row['public_bank_state']}"),
        "events_by_opponent": _counter(events, lambda row: row["opponent"]),
        "score_changed_tasks": [row for row in traced if row["score_delta"] != 0],
        "traced_tasks": traced,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in (
        "raw_tasks", "triggered_tasks", "trigger_events", "transition_counts_all",
        "transition_counts_triggered_tasks", "events_by_product", "events_by_bank_state",
        "events_by_transition", "events_by_product_and_transition",
    )}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
