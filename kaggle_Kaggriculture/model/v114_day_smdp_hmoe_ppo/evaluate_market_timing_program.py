"""Fresh-seed dual-seat mechanism evaluator for market timing experts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from evaluate_event_program import (
    CATASTROPHE_REWARD,
    EXPECTED_ACTION_STEPS,
    atomic_json,
    file_sha256,
    resolve_opponent,
    run_campaign,
    score,
)
from policy_market_timing_event_program import MarketTimingEventProgramPolicy


HERE = Path(__file__).resolve().parent
ADDITIONAL_SOURCES = (
    HERE / "policy_market_timing_event_program.py",
    HERE / "evaluate_market_timing_program.py",
)


def parse_variant(name: str) -> tuple[str, str, float, str]:
    parts = str(name).split("__")
    if len(parts) == 2:
        return parts[0], parts[1], 1.0, "FRONT"
    if len(parts) != 4 or not parts[2].startswith("Q"):
        raise ValueError(
            "variant name must be PRODUCT__TIMING_MODE or "
            "PRODUCT__TIMING_MODE__Q{percent}__{FRONT|BACK}"
        )
    try:
        quantity_fraction = int(parts[2][1:]) / 100.0
    except ValueError as exc:
        raise ValueError("quantity token must be Q followed by an integer percent") from exc
    if not 0.0 < quantity_fraction <= 1.0:
        raise ValueError("quantity percent must be in [1, 100]")
    if parts[3] not in {"FRONT", "BACK"}:
        raise ValueError("queue placement must be FRONT or BACK")
    return parts[0], parts[1], quantity_fraction, parts[3]


def evaluate_market_seed(
    decision_spec: Mapping[str, Any], seed: int, opponent_id: str
) -> list[dict[str, Any]]:
    from kaggle_environments import make

    name = str(decision_spec["name"])
    decision = dict(decision_spec["decision"])
    product, mode, quantity_fraction, queue_placement = parse_variant(name)
    if product != str(decision["production_line"]):
        raise ValueError("variant product differs from decision production line")
    rows: list[dict[str, Any]] = []
    for seat in (0, 1):
        candidate = MarketTimingEventProgramPolicy(
            decision,
            mode=mode,
            quantity_fraction=quantity_fraction,
            queue_placement=queue_placement,
            name=name,
        )
        opponent = resolve_opponent(opponent_id, f"v114_market_timing_{name}_{seed}_{seat}")
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
            "market_timing_mode": mode,
            "quantity_fraction": quantity_fraction,
            "queue_placement": queue_placement,
            "seed": int(seed),
            "seat": int(seat),
            "opponent_id": opponent_id,
            "candidate_reward": rewards[seat],
            "opponent_reward": rewards[1 - seat],
            "margin": margin,
            "score": score(margin),
            "catastrophe": rewards[seat] < CATASTROPHE_REWARD,
            "error": error,
            "statuses": statuses,
            "action_steps": int(candidate.action_steps),
            "expected_action_steps": EXPECTED_ACTION_STEPS,
            "environment_states": len(env.steps),
            "contract_violations": int(candidate.contract_violation_count + candidate.route.contract_violation_count),
            "manager_decision_count": int(candidate.manager_decision_count),
            "terminal_procurement_count": int(candidate.terminal_procurement_count),
            "sale_events": int(candidate.sale_events),
            "units_offered": int(candidate.units_offered),
        })
    return rows


def main() -> None:
    from evaluate_event_program import build_parser

    args = build_parser().parse_args()
    before = {str(path): file_sha256(path) for path in ADDITIONAL_SOURCES}
    report = run_campaign(args, worker_fn=evaluate_market_seed)
    after = {str(path): file_sha256(path) for path in ADDITIONAL_SOURCES}
    unchanged = before == after
    report["additional_sources"] = {
        path: {"sha256_before": before[path], "sha256_after": after[path], "unchanged": before[path] == after[path]}
        for path in before
    }
    if not unchanged:
        report["status"] = "INVALID"
        report["validation_errors"].append("market timing source changed during evaluation")
    atomic_json(Path(args.output), report)
    print(json.dumps({
        "status": report["status"],
        "summaries": report["summaries"],
        "validation_errors": report["validation_errors"],
    }, indent=2))


if __name__ == "__main__":
    main()
