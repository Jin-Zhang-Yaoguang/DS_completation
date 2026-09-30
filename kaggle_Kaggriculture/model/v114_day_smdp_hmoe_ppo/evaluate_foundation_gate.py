"""Run V4-2 L0 extensions and the frozen V1-V10 foundation L1 gate."""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import os
from pathlib import Path
import random
import statistics
import time
from typing import Any, Mapping

from evaluate_event_program import (
    CATASTROPHE_REWARD,
    EXPECTED_ACTION_STEPS,
    atomic_json,
    file_sha256,
    percentile_10,
    resolve_opponent,
    score,
)
from opponent_registry import load_registry
from policy_enterprise_event_program import EnterpriseEventProgramPolicy
from policy_exposure_adaptive_poultry import ExposureAdaptivePoultryPolicy
from seed_ledger import SeedLedger


HERE = Path(__file__).resolve().parent
DEFAULT_REGISTRY = HERE / "opponent_registry.json"
CANDIDATES = (
    {"name": "DAIRY_BERRY", "family": "ENTERPRISE", "duty_product": "MILK"},
    {"name": "WOOL_MELON", "family": "ENTERPRISE", "duty_product": "WOOL"},
    {"name": "EXPOSURE_ADAPTIVE_POULTRY", "family": "POULTRY", "duty_product": "EGG"},
)
SOURCE_PATHS = (
    HERE / "evaluate_foundation_gate.py",
    HERE / "policy_enterprise_event_program.py",
    HERE / "policy_exposure_adaptive_poultry.py",
    HERE / "event_program.py",
    HERE / "market_residual.py",
    HERE / "opponent_registry.py",
    HERE / "opponent_registry.json",
)


def candidate_policy(name: str) -> Any:
    if name in {"DAIRY_BERRY", "WOOL_MELON"}:
        return EnterpriseEventProgramPolicy(name)
    if name == "EXPOSURE_ADAPTIVE_POULTRY":
        return ExposureAdaptivePoultryPolicy()
    raise ValueError(f"unknown foundation candidate: {name}")


def action_sell_units(env: Any, seat: int) -> dict[str, int]:
    result: dict[str, int] = defaultdict(int)
    for states in env.steps[:-1]:
        action = states[seat].action or {}
        if not isinstance(action, Mapping):
            continue
        for order in action.get("market", []) or []:
            if isinstance(order, (list, tuple)) and len(order) >= 3 and order[0] == "SELL":
                try:
                    result[str(order[1])] += max(0, int(order[2]))
                except (TypeError, ValueError):
                    continue
    return dict(result)


def evaluate_assignment(
    candidate: Mapping[str, Any], assignment: Mapping[str, Any]
) -> list[dict[str, Any]]:
    from kaggle_environments import make

    name = str(candidate["name"])
    seed = int(assignment["seed"])
    opponent_id = str(assignment["opponent_id"])
    rows: list[dict[str, Any]] = []
    for seat in (0, 1):
        policy = candidate_policy(name)
        opponent = resolve_opponent(
            opponent_id, f"v114_foundation_{name}_{seed}_{seat}"
        )
        agents: list[Any] = [None, None]
        agents[seat], agents[1 - seat] = policy, opponent
        env = make("kaggriculture", configuration={"seed": seed}, debug=False)
        error = None
        try:
            env.run(agents)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        rewards = [float(state.reward or 0.0) for state in env.state]
        statuses = [str(state.status) for state in env.state]
        candidate_sales = action_sell_units(env, seat)
        opponent_sales = action_sell_units(env, 1 - seat)
        duty_product = str(candidate["duty_product"])
        margin = rewards[seat] - rewards[1 - seat]
        rows.append({
            "candidate_name": name,
            "candidate_family": candidate["family"],
            "duty_product": duty_product,
            "seed": seed,
            "seat": seat,
            "opponent_id": opponent_id,
            "candidate_reward": rewards[seat],
            "opponent_reward": rewards[1 - seat],
            "margin": margin,
            "score": score(margin),
            "catastrophe": rewards[seat] < CATASTROPHE_REWARD,
            "error": error,
            "statuses": statuses,
            "action_steps": int(policy.action_steps),
            "contract_violations": int(policy.contract_violation_count),
            "terminal_procurement_count": int(policy.terminal_procurement_count),
            "manager_decision_count": int(policy.manager_decision_count),
            "terminal_execution_steps": int(policy.terminal_execution_steps),
            "candidate_sell_units": candidate_sales,
            "opponent_sell_units": opponent_sales,
            "candidate_duty_sell_units": int(candidate_sales.get(duty_product, 0)),
            "opponent_duty_sell_units": int(opponent_sales.get(duty_product, 0)),
            "duty_sell_units_delta": int(candidate_sales.get(duty_product, 0))
            - int(opponent_sales.get(duty_product, 0)),
        })
    return rows


def valid(row: Mapping[str, Any]) -> bool:
    return bool(
        row.get("error") is None
        and row.get("statuses") == ["DONE", "DONE"]
        and int(row.get("action_steps", -1)) == EXPECTED_ACTION_STEPS
        and int(row.get("contract_violations", -1)) == 0
        and int(row.get("terminal_procurement_count", -1)) == 0
        and int(row.get("manager_decision_count", -1)) == 29
        and int(row.get("terminal_execution_steps", -1)) == 48
    )


def summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    selected = [row for row in rows if valid(row)]
    rewards = [float(row["candidate_reward"]) for row in selected]
    return {
        "games": len(rows),
        "valid_games": len(selected),
        "wins": sum(row["score"] == 1.0 for row in selected),
        "draws": sum(row["score"] == 0.5 for row in selected),
        "losses": sum(row["score"] == 0.0 for row in selected),
        "score_rate": statistics.mean(row["score"] for row in selected) if selected else 0.0,
        "mean_candidate_reward": statistics.mean(rewards) if rewards else 0.0,
        "p10_candidate_reward": percentile_10(rewards),
        "mean_opponent_reward": statistics.mean(row["opponent_reward"] for row in selected)
        if selected else 0.0,
        "mean_margin": statistics.mean(row["margin"] for row in selected) if selected else 0.0,
        "catastrophe_games": sum(bool(row["catastrophe"]) for row in selected),
        "errors_or_contract_failures": len(rows) - len(selected),
        "mean_manager_decisions": statistics.mean(row["manager_decision_count"] for row in selected)
        if selected else 0.0,
        "mean_terminal_execution_steps": statistics.mean(
            row["terminal_execution_steps"] for row in selected
        ) if selected else 0.0,
    }


def seed_block_bootstrap_ci(
    rows: list[dict[str, Any]], field: str, *, samples: int = 20000
) -> list[float]:
    by_seed: dict[int, list[float]] = defaultdict(list)
    for row in rows:
        if valid(row):
            by_seed[int(row["seed"])].append(float(row[field]))
    blocks = [statistics.mean(values) for _, values in sorted(by_seed.items())]
    if not blocks:
        return [0.0, 0.0]
    rng = random.Random(20260830)
    means = sorted(
        statistics.mean(rng.choice(blocks) for _ in blocks) for _ in range(samples)
    )
    return [means[int(0.025 * (samples - 1))], means[int(0.975 * (samples - 1))]]


def l1_gate(candidate_rows: list[dict[str, Any]]) -> dict[str, Any]:
    pooled = summary(candidate_rows)
    by_opponent: list[dict[str, Any]] = []
    for opponent_id in sorted({row["opponent_id"] for row in candidate_rows}):
        item = summary([row for row in candidate_rows if row["opponent_id"] == opponent_id])
        item["opponent_id"] = opponent_id
        by_opponent.append(item)
    duty_ci = seed_block_bootstrap_ci(candidate_rows, "duty_sell_units_delta")
    checks = {
        "pooled_score_rate_at_least_60pct": pooled["score_rate"] >= 0.60,
        "worst_opponent_score_rate_at_least_45pct": min(
            item["score_rate"] for item in by_opponent
        ) >= 0.45,
        "pooled_catastrophe_rate_at_most_5pct": (
            pooled["catastrophe_games"] / pooled["valid_games"]
            if pooled["valid_games"] else 1.0
        ) <= 0.05,
        "every_opponent_p10_at_least_3000": all(
            item["p10_candidate_reward"] >= 3000 for item in by_opponent
        ),
        "zero_execution_or_contract_failures": pooled["errors_or_contract_failures"] == 0,
        "duty_sell_units_paired_ci_lower_above_zero": duty_ci[0] > 0.0,
        "not_margin_only_economic_suppression": pooled["mean_candidate_reward"] >= 3000.0
        and duty_ci[0] > 0.0,
    }
    return {
        "status": "PASS_L1" if all(checks.values()) else "FAIL_L1",
        "checks": checks,
        "pooled": pooled,
        "by_opponent": by_opponent,
        "duty_metric": {
            "definition": "requested SELL units for the preregistered responsibility product",
            "product": candidate_rows[0]["duty_product"],
            "paired_seed_block_mean_ci95": duty_ci,
            "warning": "order-volume responsibility proxy; not a claim of filled market volume",
        },
    }


def build_schedule(mode: str, seed_start: int, registry: Mapping[str, Any]) -> list[dict[str, Any]]:
    if mode == "l0_extension":
        return [
            {"seed": seed_start + offset, "opponent_id": "builtin:starter"}
            for offset in range(8)
        ]
    representatives = list(registry["foundation_l1"]["representative_ids"])
    return [
        {
            "seed": seed_start + offset,
            "opponent_id": f"registry:{representatives[offset // 8]}",
        }
        for offset in range(32)
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("l0_extension", "l1"), required=True)
    parser.add_argument("--seed-start", type=int, required=True)
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=max(1, os.cpu_count() or 1))
    args = parser.parse_args()

    registry = load_registry(args.registry, verify_artifacts=True)
    schedule = build_schedule(args.mode, int(args.seed_start), registry)
    source_before = {str(path): file_sha256(path) for path in SOURCE_PATHS}
    ledger = SeedLedger(args.ledger)
    ledger.reserve_schedule(
        schedule,
        split="train",
        campaign_id=str(args.campaign),
        registry_sha256=registry["registry_sha256"],
    )
    ledger_reserved_sha = ledger.sha256()
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    started = time.time()
    try:
        jobs = [(candidate, assignment) for candidate in CANDIDATES for assignment in schedule]
        with ProcessPoolExecutor(max_workers=min(int(args.workers), len(jobs))) as pool:
            futures = {
                pool.submit(evaluate_assignment, candidate, assignment): (candidate, assignment)
                for candidate, assignment in jobs
            }
            for future in as_completed(futures):
                candidate, assignment = futures[future]
                try:
                    result = future.result()
                    if len(result) != 2 or sorted(row["seat"] for row in result) != [0, 1]:
                        raise ValueError("worker did not return both seats")
                    rows.extend(result)
                except Exception as exc:
                    failures.append({
                        "candidate_name": candidate["name"],
                        "seed": assignment["seed"],
                        "opponent_id": assignment["opponent_id"],
                        "error": f"{type(exc).__name__}: {exc}",
                    })
                print(json.dumps({
                    "candidate": candidate["name"],
                    "seed": assignment["seed"],
                    "opponent": assignment["opponent_id"],
                }, ensure_ascii=False), flush=True)
    finally:
        ledger.mark_schedule_exposed(schedule)

    source_after = {str(path): file_sha256(path) for path in SOURCE_PATHS}
    by_candidate: dict[str, Any] = {}
    for candidate in CANDIDATES:
        selected = [row for row in rows if row["candidate_name"] == candidate["name"]]
        by_candidate[candidate["name"]] = (
            l1_gate(selected) if args.mode == "l1" else summary(selected)
        )
    expected_rows = len(CANDIDATES) * len(schedule) * 2
    validation_errors = []
    if len(rows) != expected_rows:
        validation_errors.append(f"row count {len(rows)} != {expected_rows}")
    if any(not valid(row) for row in rows):
        validation_errors.append("one or more rows failed the execution contract")
    if source_before != source_after:
        validation_errors.append("source changed during evaluation")
    report = {
        "schema": "kaggriculture-v114-foundation-gate-v1",
        "status": "VALID" if not validation_errors else "INVALID",
        "mode": args.mode,
        "campaign": args.campaign,
        "registry_path": str(args.registry),
        "registry_sha256": registry["registry_sha256"],
        "source_sha256_before": source_before,
        "source_sha256_after": source_after,
        "seed_start": int(args.seed_start),
        "seed_blocks": len(schedule),
        "schedule": schedule,
        "dual_seat_same_opponent": True,
        "candidate_specs": list(CANDIDATES),
        "expected_rows": expected_rows,
        "elapsed_seconds": time.time() - started,
        "seed_ledger": {
            "path": str(args.ledger),
            "sha256_after_reservation": ledger_reserved_sha,
            "sha256_after_exposure": ledger.sha256(),
        },
        "validation_errors": validation_errors,
        "worker_failures": failures,
        "by_candidate": by_candidate,
        "rows": sorted(
            rows,
            key=lambda row: (
                row["candidate_name"], row["seed"], row["seat"]
            ),
        ),
    }
    atomic_json(args.output, report)
    print(json.dumps({
        "status": report["status"],
        "mode": args.mode,
        "by_candidate": by_candidate,
    }, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
