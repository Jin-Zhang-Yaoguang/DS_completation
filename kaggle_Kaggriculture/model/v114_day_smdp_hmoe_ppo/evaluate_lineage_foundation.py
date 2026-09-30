"""Evaluate a registered V114 lineage policy under frozen L0/L1 schedules."""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import statistics
import tempfile
import time

from evaluate_event_program import resolve_opponent, score
from opponent_registry import load_registry
from policy_lineage_phase_hmoe import LineagePhaseV114Policy


HERE = Path(__file__).resolve().parent
EXPECTED_STEPS = 719
CATASTROPHE_REWARD = 3000.0


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def percentile_10(values: list[float]) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    return float(values[int(0.10 * (len(values) - 1))])


def evaluate_assignment(checkpoint: str, seed: int, opponent_id: str) -> list[dict]:
    from kaggle_environments import make

    rows = []
    for seat in (0, 1):
        candidate = LineagePhaseV114Policy(Path(checkpoint))
        opponent = resolve_opponent(opponent_id, f"v114_lineage_{seed}_{seat}")
        agents = [None, None]
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
        operations = dict(candidate.operation_counts)
        rows.append({
            "seed": int(seed),
            "seat": seat,
            "opponent_id": opponent_id,
            "candidate_reward": rewards[seat],
            "opponent_reward": rewards[1 - seat],
            "margin": margin,
            "score": score(margin),
            "catastrophe": rewards[seat] < CATASTROPHE_REWARD,
            "statuses": statuses,
            "steps": len(env.steps),
            "action_steps": int(candidate.action_steps),
            "error": error,
            "operation_counts": operations,
            "sell_orders": int(operations.get("market:SELL", 0)),
            "procurement_expansion_orders": int(sum(
                operations.get(f"market:{name}", 0)
                for name in (
                    "HIRE", "BUY_LAND", "BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL",
                )
            )),
            "unit_expert_usage": dict(candidate.unit_expert_usage),
            "market_expert_usage": dict(candidate.market_expert_usage),
        })
    return rows


def valid(row: dict) -> bool:
    return bool(
        row.get("error") is None
        and row.get("statuses") == ["DONE", "DONE"]
        and int(row.get("steps", 0)) == EXPECTED_STEPS + 1
        and int(row.get("action_steps", 0)) == EXPECTED_STEPS
    )


def summarize(rows: list[dict]) -> dict:
    selected = [row for row in rows if valid(row)]
    rewards = [float(row["candidate_reward"]) for row in selected]
    return {
        "games": len(rows),
        "valid_games": len(selected),
        "wins": sum(float(row["score"]) == 1.0 for row in selected),
        "draws": sum(float(row["score"]) == 0.5 for row in selected),
        "losses": sum(float(row["score"]) == 0.0 for row in selected),
        "score_rate": statistics.mean(float(row["score"]) for row in selected) if selected else 0.0,
        "mean_candidate_reward": statistics.mean(rewards) if rewards else 0.0,
        "p10_candidate_reward": percentile_10(rewards),
        "mean_opponent_reward": statistics.mean(float(row["opponent_reward"]) for row in selected) if selected else 0.0,
        "mean_margin": statistics.mean(float(row["margin"]) for row in selected) if selected else 0.0,
        "catastrophe_games": sum(bool(row["catastrophe"]) for row in selected),
        "errors_or_incomplete_games": len(rows) - len(selected),
        "sell_coverage_rate": statistics.mean(row["sell_orders"] > 0 for row in selected) if selected else 0.0,
        "mean_sell_orders": statistics.mean(row["sell_orders"] for row in selected) if selected else 0.0,
        "procurement_expansion_coverage_rate": statistics.mean(
            row["procurement_expansion_orders"] > 0 for row in selected
        ) if selected else 0.0,
        "mean_procurement_expansion_orders": statistics.mean(
            row["procurement_expansion_orders"] for row in selected
        ) if selected else 0.0,
    }


def schedule(mode: str, seed_start: int, registry: dict) -> list[tuple[int, str]]:
    if mode == "engineering":
        return [(seed_start + offset, "builtin:starter") for offset in range(8)]
    if mode == "l0":
        return [(seed_start + offset, "builtin:starter") for offset in range(16)]
    representatives = list(registry["foundation_l1"]["representative_ids"])
    return [
        (seed_start + offset, f"registry:{representatives[offset // 8]}")
        for offset in range(32)
    ]


def gate(mode: str, lineage_id: str, pooled: dict, by_opponent: list[dict]) -> tuple[str, dict]:
    if mode in {"engineering", "l0"}:
        checks = {
            "all_games_valid": pooled["errors_or_incomplete_games"] == 0,
            "score_rate_at_least_75pct": pooled["score_rate"] >= 0.75,
            "p10_at_least_3000": pooled["p10_candidate_reward"] >= 3000,
            "catastrophe_rate_at_most_6_25pct": (
                pooled["catastrophe_games"] / pooled["valid_games"]
                if pooled["valid_games"] else 1.0
            ) <= 0.0625,
        }
        return ("PASS_ENGINEERING_SCREEN" if mode == "engineering" else "PASS_L0") if all(checks.values()) else ("FAIL_ENGINEERING_SCREEN" if mode == "engineering" else "FAIL_L0"), checks
    responsibility_check = (
        pooled["sell_coverage_rate"] >= 0.90 and pooled["mean_sell_orders"] >= 1.0
        if lineage_id == "V10A_DEMAND_TIMING" else
        pooled["procurement_expansion_coverage_rate"] >= 0.90
        and pooled["mean_procurement_expansion_orders"] >= 1.0
        if lineage_id == "V10B_PROCUREMENT_SLOT" else
        pooled["sell_coverage_rate"] >= 0.90
        and pooled["mean_sell_orders"] >= 1.0
        and pooled["procurement_expansion_coverage_rate"] >= 0.90
        and pooled["mean_procurement_expansion_orders"] >= 1.0
    )
    checks = {
        "all_games_valid": pooled["errors_or_incomplete_games"] == 0,
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
        "responsibility_coverage": responsibility_check,
    }
    return ("PASS_L1" if all(checks.values()) else "FAIL_L1"), checks


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as sink:
        json.dump(payload, sink, ensure_ascii=False, indent=2)
        sink.write("\n")
        temporary = Path(sink.name)
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument(
        "--lineage-id",
        choices=(
            "V10A_DEMAND_TIMING", "V10B_PROCUREMENT_SLOT",
            "V11A_V2_REPLAY", "V11B_V8_REPLAY",
        ),
        required=True,
    )
    parser.add_argument("--mode", choices=("engineering", "l0", "l1"), required=True)
    parser.add_argument("--seed-start", type=int, required=True)
    parser.add_argument("--registry", type=Path, default=HERE / "opponent_registry.json")
    parser.add_argument("--workers", type=int, default=max(1, min(4, os.cpu_count() or 1)))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    started = time.time()
    registry = load_registry(args.registry)
    assignments = schedule(args.mode, args.seed_start, registry)
    rows: list[dict] = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(evaluate_assignment, str(args.checkpoint), seed, opponent): (seed, opponent)
            for seed, opponent in assignments
        }
        for future in as_completed(futures):
            result = future.result()
            rows.extend(result)
            print(json.dumps(result, ensure_ascii=False), flush=True)
    rows.sort(key=lambda row: (int(row["seed"]), int(row["seat"])))
    pooled = summarize(rows)
    by_opponent = []
    for opponent_id in sorted({row["opponent_id"] for row in rows}):
        item = summarize([row for row in rows if row["opponent_id"] == opponent_id])
        item["opponent_id"] = opponent_id
        by_opponent.append(item)
    status, checks = gate(args.mode, args.lineage_id, pooled, by_opponent)
    report = {
        "schema": "kaggriculture-v114-lineage-foundation-evaluation-v1",
        "lineage_id": args.lineage_id,
        "mode": args.mode,
        "status": status,
        "checks": checks,
        "checkpoint": str(args.checkpoint.resolve()),
        "checkpoint_sha256": sha256_file(args.checkpoint),
        "registry": str(args.registry.resolve()),
        "registry_sha256": sha256_file(args.registry),
        "seed_start": args.seed_start,
        "seed_blocks": len(assignments),
        "dual_seat_same_opponent": True,
        "pooled": pooled,
        "by_opponent": by_opponent,
        "rows": rows,
        "elapsed_seconds": time.time() - started,
        "qualification_status": "NOT_GOLD",
    }
    atomic_json(args.output, report)
    print(json.dumps({"status": status, "pooled": pooled, "elapsed_seconds": report["elapsed_seconds"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
