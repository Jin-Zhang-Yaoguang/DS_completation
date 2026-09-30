"""Evaluate four fixed routes after a common 24-step safe probe."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from evaluate_event_program import (
    EXPECTED_ACTION_STEPS,
    resolve_opponent,
    run_campaign,
    score,
)
from policy_deferred_event_program import DeferredFixedEventProgramPolicy


def evaluate_deferred_seed(
    decision_spec: Mapping[str, Any], seed: int, opponent_id: str
) -> list[dict[str, Any]]:
    from kaggle_environments import make

    name = str(decision_spec["name"])
    decision = dict(decision_spec["decision"])
    rows: list[dict[str, Any]] = []
    for seat in (0, 1):
        candidate = DeferredFixedEventProgramPolicy(
            decision, name=name, probe_steps=24
        )
        opponent = resolve_opponent(
            opponent_id, f"v114_deferred_{name}_{seed}_{seat}"
        )
        agents: list[Any] = [None, None]
        agents[seat], agents[1 - seat] = candidate, opponent
        env = make("kaggriculture", configuration={"seed": int(seed)}, debug=False)
        error = None
        try:
            env.run(agents)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        rewards = [float(state.reward or 0.0) for state in env.state]
        statuses = [str(state.status) for state in env.state]
        margin = rewards[seat] - rewards[1 - seat]
        rows.append({
            "decision_name": name,
            "decision": decision,
            "seed": int(seed),
            "seat": int(seat),
            "opponent_id": opponent_id,
            "candidate_reward": rewards[seat],
            "opponent_reward": rewards[1 - seat],
            "margin": margin,
            "score": score(margin),
            "catastrophe": rewards[seat] < 3000.0,
            "error": error,
            "statuses": statuses,
            "action_steps": int(candidate.action_steps),
            "expected_action_steps": EXPECTED_ACTION_STEPS,
            "environment_states": len(env.steps),
            "contract_violations": int(candidate.contract_violation_count),
            "manager_decision_count": int(candidate.manager_decision_count),
            "terminal_procurement_count": int(candidate.terminal_procurement_count),
            "probe_action_steps": int(candidate.probe_action_steps),
            "probe_features": None if candidate.probe_features is None else candidate.probe_features.tolist(),
        })
    return rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decision-spec-json", required=True)
    parser.add_argument("--seed-start", type=int, required=True)
    parser.add_argument("--seeds", type=int, required=True)
    parser.add_argument("--opponent", required=True)
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--split", choices=("train",), default="train")
    parser.add_argument("--registry-sha256")
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    report = run_campaign(args, worker_fn=evaluate_deferred_seed)
    print(json.dumps({"status": report["status"], "summaries": report["summaries"]}, indent=2))
