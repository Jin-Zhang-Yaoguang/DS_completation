"""Frozen V4-2 L1 gate for V12 shared enterprise-contract experts."""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import random
import statistics
import time
from typing import Any, Mapping

from evaluate_event_program import atomic_json, resolve_opponent, score
from evaluate_foundation_gate import action_sell_units
from opponent_registry import load_registry
from policy_event_ledger_v12 import EventLedgerV12EngineeringPolicy
from seed_ledger import SeedLedger


HERE = Path(__file__).resolve().parent
CONTRACTS = {"WHEAT_CASH": "WHEAT", "MELON_CASH": "MELON"}
SOURCE_PATHS = (
    HERE / "evaluate_v12_contract_l1.py",
    HERE / "enterprise_contracts_v12.py",
    HERE / "persistent_unit_tasks.py",
    HERE / "policy_event_market_hmoe.py",
    HERE / "policy_event_ledger_v12.py",
    HERE / "event_ledger.py",
    HERE / "event_ledger_controller.py",
    HERE / "opponent_registry.json",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def percentile10(values: list[float]) -> float:
    return sorted(values)[int(0.1 * (len(values) - 1))] if values else 0.0


def evaluate_assignment(
    assignment: Mapping[str, Any], unit_checkpoint: str, market_checkpoint: str
) -> list[dict[str, Any]]:
    from kaggle_environments import make

    seed = int(assignment["seed"])
    opponent_id = str(assignment["opponent_id"])
    rows: list[dict[str, Any]] = []
    for contract, duty_product in CONTRACTS.items():
        for seat in (0, 1):
            policy = EventLedgerV12EngineeringPolicy(
                Path(unit_checkpoint), Path(market_checkpoint), contract=contract
            )
            opponent = resolve_opponent(
                opponent_id, f"v114_v12_l1_{contract}_{seed}_{seat}"
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
            margin = rewards[seat] - rewards[1 - seat]
            candidate_sales = action_sell_units(env, seat)
            opponent_sales = action_sell_units(env, 1 - seat)
            audit = policy.audit()
            ledger = audit["events"]["ledger"]
            rows.append({
                "contract": contract,
                "duty_product": duty_product,
                "seed": seed,
                "seat": seat,
                "opponent_id": opponent_id,
                "candidate_reward": rewards[seat],
                "opponent_reward": rewards[1 - seat],
                "margin": margin,
                "score": score(margin),
                "catastrophe": rewards[seat] < 3000,
                "error": error,
                "statuses": statuses,
                "steps": len(env.steps),
                "action_steps": int(policy.action_steps),
                "unauthorized_market_turns": int(
                    audit["events"]["unauthorized_market_turns"]
                ),
                "duplicate_commit_blocks": int(ledger["blocked_duplicate_emits"]),
                "terminal_procurement_rejections": int(
                    ledger["terminal_procurement_rejections"]
                ),
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
        row["error"] is None
        and row["statuses"] == ["DONE", "DONE"]
        and int(row["steps"]) == 720
        and int(row["action_steps"]) == 719
        and int(row["unauthorized_market_turns"]) == 0
        and int(row["duplicate_commit_blocks"]) == 0
        and int(row["terminal_procurement_rejections"]) == 0
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
        "p10_candidate_reward": percentile10(rewards),
        "mean_opponent_reward": statistics.mean(row["opponent_reward"] for row in selected)
        if selected else 0.0,
        "mean_margin": statistics.mean(row["margin"] for row in selected) if selected else 0.0,
        "catastrophe_games": sum(bool(row["catastrophe"]) for row in selected),
        "errors_or_contract_failures": len(rows) - len(selected),
    }


def seed_block_ci(rows: list[dict[str, Any]], field: str) -> list[float]:
    by_seed: dict[int, list[float]] = defaultdict(list)
    for row in rows:
        if valid(row):
            by_seed[int(row["seed"])].append(float(row[field]))
    blocks = [statistics.mean(values) for _, values in sorted(by_seed.items())]
    if not blocks:
        return [0.0, 0.0]
    rng = random.Random(20260830)
    means = sorted(
        statistics.mean(rng.choice(blocks) for _ in blocks) for _ in range(20000)
    )
    return [means[int(0.025 * 19999)], means[int(0.975 * 19999)]]


def contract_gate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    pooled = summary(rows)
    by_opponent = []
    for opponent_id in sorted({row["opponent_id"] for row in rows}):
        item = summary([row for row in rows if row["opponent_id"] == opponent_id])
        item["opponent_id"] = opponent_id
        by_opponent.append(item)
    duty_ci = seed_block_ci(rows, "duty_sell_units_delta")
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
            "definition": "requested SELL units for the fixed enterprise-contract product",
            "product": rows[0]["duty_product"],
            "paired_seed_block_mean_ci95": duty_ci,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unit-checkpoint", type=Path, required=True)
    parser.add_argument("--market-checkpoint", type=Path, required=True)
    parser.add_argument("--seed-start", type=int, required=True)
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--registry", type=Path, default=HERE / "opponent_registry.json")
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=max(1, os.cpu_count() or 1))
    args = parser.parse_args()

    registry = load_registry(args.registry, verify_artifacts=True)
    representatives = list(registry["foundation_l1"]["representative_ids"])
    schedule = [
        {
            "seed": args.seed_start + offset,
            "opponent_id": f"registry:{representatives[offset // 8]}",
        }
        for offset in range(32)
    ]
    source_before = {str(path): sha256_file(path) for path in SOURCE_PATHS}
    fixed = {
        "unit_checkpoint": sha256_file(args.unit_checkpoint),
        "market_checkpoint": sha256_file(args.market_checkpoint),
        "preregistration": sha256_file(args.preregistration),
    }
    ledger = SeedLedger(args.ledger)
    ledger.reserve_schedule(
        schedule, split="train", campaign_id=args.campaign,
        registry_sha256=registry["registry_sha256"],
    )
    reserved_sha = ledger.sha256()
    rows: list[dict[str, Any]] = []
    worker_failures: list[dict[str, Any]] = []
    started = time.time()
    try:
        with ProcessPoolExecutor(max_workers=min(args.workers, len(schedule))) as pool:
            futures = {
                pool.submit(
                    evaluate_assignment, assignment,
                    str(args.unit_checkpoint), str(args.market_checkpoint),
                ): assignment
                for assignment in schedule
            }
            for future in as_completed(futures):
                assignment = futures[future]
                try:
                    batch = future.result()
                    if len(batch) != len(CONTRACTS) * 2:
                        raise ValueError("worker returned an incomplete contract/seat block")
                    rows.extend(batch)
                except Exception as exc:
                    worker_failures.append({
                        **assignment, "error": f"{type(exc).__name__}: {exc}"
                    })
                print(json.dumps(assignment, ensure_ascii=False), flush=True)
    finally:
        ledger.mark_schedule_exposed(schedule)

    source_after = {str(path): sha256_file(path) for path in SOURCE_PATHS}
    expected_rows = len(schedule) * len(CONTRACTS) * 2
    validation_errors = []
    if len(rows) != expected_rows:
        validation_errors.append(f"row count {len(rows)} != {expected_rows}")
    if any(not valid(row) for row in rows):
        validation_errors.append("one or more rows failed execution contract")
    if source_before != source_after:
        validation_errors.append("source changed during evaluation")
    by_contract = {
        contract: contract_gate([row for row in rows if row["contract"] == contract])
        for contract in CONTRACTS
    }
    report = {
        "schema": "kaggriculture-v114-v12-shared-contract-l1-v1",
        "status": "VALID" if not validation_errors else "INVALID",
        "interpretation": "L1 foundation gate only; not G2, Manager PPO, Residual PPO, or gold",
        "campaign": args.campaign,
        "registry_sha256": registry["registry_sha256"],
        "fixed_artifact_sha256": fixed,
        "source_sha256_before": source_before,
        "source_sha256_after": source_after,
        "seed_start": args.seed_start,
        "seed_blocks": len(schedule),
        "dual_seat_same_opponent": True,
        "schedule": schedule,
        "expected_rows": expected_rows,
        "validation_errors": validation_errors,
        "worker_failures": worker_failures,
        "by_contract": by_contract,
        "seed_ledger": {
            "path": str(args.ledger),
            "sha256_after_reservation": reserved_sha,
            "sha256_after_exposure": ledger.sha256(),
        },
        "elapsed_seconds": time.time() - started,
        "rows": sorted(rows, key=lambda row: (row["contract"], row["seed"], row["seat"])),
    }
    atomic_json(args.output, report)
    print(json.dumps({"status": report["status"], "by_contract": by_contract}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
