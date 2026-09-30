"""Fresh-seed dual-seat evaluator for independent enterprise experts."""

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
from policy_enterprise_event_program import EnterpriseEventProgramPolicy, PROFILES


HERE = Path(__file__).resolve().parent
ADDITIONAL_SOURCES = (
    HERE / "policy_enterprise_event_program.py",
    HERE / "evaluate_enterprise_program.py",
)


def evaluate_enterprise_seed(
    decision_spec: Mapping[str, Any], seed: int, opponent_id: str
) -> list[dict[str, Any]]:
    from kaggle_environments import make

    name = str(decision_spec["name"])
    if name not in PROFILES:
        raise ValueError(f"unknown enterprise profile {name}")
    rows: list[dict[str, Any]] = []
    for seat in (0, 1):
        candidate = EnterpriseEventProgramPolicy(name)
        opponent = resolve_opponent(opponent_id, f"v114_enterprise_{name}_{seed}_{seat}")
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
        sold = {product: int(quantity) for product, quantity in candidate.sale_units.items() if quantity > 0}
        rows.append({
            "decision_name": name,
            "decision": dict(decision_spec["decision"]),
            "enterprise_profile": name,
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
            "contract_violations": int(candidate.contract_violation_count),
            "manager_decision_count": int(candidate.manager_decision_count),
            "terminal_procurement_count": int(candidate.terminal_procurement_count),
            "sale_units": sold,
            "distinct_products_sold": len(sold),
            "animal_product_sold": int(sold.get(ANIMAL_PRODUCT_BY_PROFILE.get(name, ""), 0)),
        })
    return rows


ANIMAL_PRODUCT_BY_PROFILE = {"DAIRY_BERRY": "MILK", "WOOL_MELON": "WOOL"}


def main() -> None:
    from evaluate_event_program import build_parser

    args = build_parser().parse_args()
    before = {str(path): file_sha256(path) for path in ADDITIONAL_SOURCES}
    report = run_campaign(args, worker_fn=evaluate_enterprise_seed)
    after = {str(path): file_sha256(path) for path in ADDITIONAL_SOURCES}
    report["additional_sources"] = {
        path: {
            "sha256_before": before[path],
            "sha256_after": after[path],
            "unchanged": before[path] == after[path],
        }
        for path in before
    }
    if before != after:
        report["status"] = "INVALID"
        report["validation_errors"].append("enterprise source changed during evaluation")
    atomic_json(Path(args.output), report)
    print(json.dumps({
        "status": report["status"],
        "summaries": report["summaries"],
        "validation_errors": report["validation_errors"],
    }, indent=2))


if __name__ == "__main__":
    main()
