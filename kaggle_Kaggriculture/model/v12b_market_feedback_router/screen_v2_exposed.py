"""Development screen for B-v2 on the already exposed frozen-v3 screen18.

This script does not open or derive the formal panel.  It reuses the exact
source/opponent/seat tasks visible in B-v1's screen raw and pairs B-v2 against
the existing baseline-V8 controls.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
from typing import Any

from kaggle_environments import make

from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import (
    create_agent,
    load_registry,
)


HERE = Path(__file__).resolve().parent
RUNS = HERE.parent / "v12_validation" / "runs_v3"
CANDIDATE_REGISTRY = HERE / "registry_entry.json"
OPPONENT_REGISTRY = HERE.parent / "v12_validation" / "frozen_v3" / "combined_registry.json"
OUTPUT = HERE / "screen_v2_report.json"
CANDIDATE_ID = "v12b_v2_winrisk_feedback_gate"

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
DIRECT_SOURCE = "screen_parent/v12b_market_feedback_router__vs__baseline_v8/games.jsonl"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _rows(relative: str) -> list[dict[str, Any]]:
    with (RUNS / relative).open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _subject(row: dict[str, Any], model_id: str) -> tuple[int, float, float]:
    seat = list(row["seat_models"]).index(model_id)
    rewards = [float(value) for value in row["rewards"]]
    margin = rewards[seat] - rewards[1 - seat]
    return seat, margin, 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0


def _label(score: float) -> str:
    return "W" if score == 1.0 else "T" if score == 0.5 else "L"


def build_tasks() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    common: list[dict[str, Any]] = []
    for opponent, (source_file, control_file) in PAIR_FILES.items():
        source_rows = _rows(source_file)
        control_rows = _rows(control_file)
        controls = {}
        for row in control_rows:
            seat, margin, score = _subject(row, "baseline_v8")
            controls[(str(row["source"]["date"]), int(row["source"]["seed"]), seat)] = (margin, score)
        source_keys = set()
        for row in source_rows:
            seat = int(row["model_a_seat"])
            key = (str(row["source"]["date"]), int(row["source"]["seed"]), seat)
            source_keys.add(key)
            margin, score = controls[key]
            common.append(
                {
                    "kind": "common",
                    "opponent": opponent,
                    "date": key[0],
                    "seed": key[1],
                    "candidate_seat": seat,
                    "episode_id": str(row["source"].get("episode_id") or ""),
                    "control_margin": margin,
                    "control_score": score,
                }
            )
        if len(source_rows) != 36 or len(control_rows) != 36:
            raise RuntimeError(f"unexpected screen cardinality for {opponent}")
        if len(source_keys) != 36 or source_keys != set(controls):
            raise RuntimeError(f"source/control pairing mismatch for {opponent}")

    direct = []
    seen = set()
    for row in _rows(DIRECT_SOURCE):
        key = (
            str(row["source"]["date"]),
            int(row["source"]["seed"]),
            int(row["model_a_seat"]),
        )
        if key in seen:
            continue
        seen.add(key)
        direct.append(
            {
                "kind": "direct",
                "opponent": "baseline_v8",
                "date": key[0],
                "seed": key[1],
                "candidate_seat": key[2],
                "episode_id": str(row["source"].get("episode_id") or ""),
            }
        )
    return common, direct


def run_task(task: dict[str, Any]) -> dict[str, Any]:
    candidates = load_registry(CANDIDATE_REGISTRY)
    opponents = load_registry(OPPONENT_REGISTRY)
    candidate = create_agent(candidates, CANDIDATE_ID)
    opponent = create_agent(opponents, task["opponent"])
    agents = [candidate, opponent]
    if int(task["candidate_seat"]) == 1:
        agents.reverse()
    env = make("kaggriculture", configuration={"seed": int(task["seed"])}, debug=True)
    steps = env.run(agents)
    rewards = [float(state.reward or 0) for state in steps[-1]]
    statuses = [str(state.status) for state in steps[-1]]
    seat = int(task["candidate_seat"])
    margin = rewards[seat] - rewards[1 - seat]
    score = 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0
    diagnostics = candidate.diagnostics().get("model_status", {})
    result = {
        **task,
        "steps": len(steps),
        "statuses": statuses,
        "rewards": rewards,
        "candidate_margin": margin,
        "candidate_score": score,
        "diagnostics": diagnostics,
    }
    if task["kind"] == "common":
        result.update(
            margin_delta=margin - float(task["control_margin"]),
            score_delta=score - float(task["control_score"]),
            transition=f"{_label(float(task['control_score']))}→{_label(score)}",
        )
    return result


def _common_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    transitions = Counter(row["transition"] for row in rows)
    history = [event for row in rows for event in row["diagnostics"].get("trigger_history", [])]
    return {
        "tasks": len(rows),
        "score_uplift": sum(row["score_delta"] for row in rows) / len(rows),
        "margin_uplift": sum(row["margin_delta"] for row in rows) / len(rows),
        "transitions": dict(sorted(transitions.items())),
        "w_to_l": int(transitions.get("W→L", 0)),
        "t_or_l_to_w": int(transitions.get("T→W", 0) + transitions.get("L→W", 0)),
        "triggered_tasks": sum(int(row["diagnostics"].get("trigger_count", 0)) > 0 for row in rows),
        "trigger_events": len(history),
        "trigger_by_bank_state": dict(sorted(Counter(event["bank_state"] for event in history).items())),
        "lead_protection_bypasses": sum(int(row["diagnostics"].get("lead_protection_bypasses", 0)) for row in rows),
    }


def _direct_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "games": len(rows),
        "score_rate": sum(row["candidate_score"] for row in rows) / len(rows),
        "mean_margin": sum(row["candidate_margin"] for row in rows) / len(rows),
        "wins": sum(row["candidate_score"] == 1.0 for row in rows),
        "ties": sum(row["candidate_score"] == 0.5 for row in rows),
        "losses": sum(row["candidate_score"] == 0.0 for row in rows),
    }


def main() -> None:
    common_tasks, direct_tasks = build_tasks()
    tasks = [*common_tasks, *direct_tasks]
    with ProcessPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(run_task, tasks))
    if any(row["steps"] != 720 or row["statuses"] != ["DONE", "DONE"] for row in results):
        raise RuntimeError("incomplete screen game")
    if any(row["diagnostics"].get("errors") for row in results):
        raise RuntimeError("candidate serving error")
    common = [row for row in results if row["kind"] == "common"]
    direct = [row for row in results if row["kind"] == "direct"]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in common:
        grouped[row["opponent"]].append(row)
    overall = _common_summary(common)
    by_opponent = {key: _common_summary(value) for key, value in grouped.items()}
    sources = sorted(
        {(row["date"], row["seed"], row["episode_id"]) for row in results},
        key=lambda item: (item[0], item[1]),
    )
    gates = {
        "w_to_l_zero": overall["w_to_l"] == 0,
        "at_least_one_t_or_l_to_w": overall["t_or_l_to_w"] >= 1,
        "overall_score_nonnegative": overall["score_uplift"] >= 0,
        "every_opponent_score_nonnegative": all(row["score_uplift"] >= 0 for row in by_opponent.values()),
    }
    payload = {
        "schema": "kaggriculture-v12b-v2-exposed-screen18-1",
        "candidate": CANDIDATE_ID,
        "parent": "baseline_v8",
        "data_scope": "frozen_v3 screen18 and existing controls only",
        "formal_panel_accessed": False,
        "new_seed_draw": False,
        "audit_bindings": {
            "candidate_main_sha256": _sha256(HERE / "main.py"),
            "candidate_registry_sha256": _sha256(CANDIDATE_REGISTRY),
            "opponent_registry_sha256": _sha256(OPPONENT_REGISTRY),
            "input_sha256": {
                relative: _sha256(RUNS / relative)
                for relative in sorted(
                    {
                        DIRECT_SOURCE,
                        *(
                            value
                            for pair in PAIR_FILES.values()
                            for value in pair
                        ),
                    }
                )
            },
        },
        "sources": [
            {"date": date, "seed": seed, "episode_id": episode}
            for date, seed, episode in sources
        ],
        "common_summary": overall,
        "by_opponent": by_opponent,
        "direct_parent": _direct_summary(direct),
        "gates": gates,
        "all_gates_passed": all(gates.values()),
        "results": results,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "sources": len(sources),
        "common_summary": overall,
        "by_opponent": by_opponent,
        "direct_parent": payload["direct_parent"],
        "gates": gates,
        "all_gates_passed": payload["all_gates_passed"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
