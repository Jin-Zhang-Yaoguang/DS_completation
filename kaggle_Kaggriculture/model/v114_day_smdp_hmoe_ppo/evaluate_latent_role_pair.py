"""Paired fresh-seed comparison of frozen V6 and candidate V8 checkpoints.

One campaign reserves each dual-seat seed block exactly once.  Both checkpoints
then use the same option, seed, seat and opponent assignment.  All statistical
intervals resample complete seed blocks, preserving the two-seat dependency.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
from pathlib import Path
import statistics
from typing import Any, Callable, Iterable, Mapping

from flax import serialization
import numpy as np

from evaluate_latent_role_options import (
    CATASTROPHE_REWARD,
    NUM_OPTIONS,
    _default_registry_sha256,
    atomic_json,
    evaluate_seed,
    summarize_option,
)
from seed_ledger import SeedLedger


SCHEMA = "kaggriculture-v114-latent-role-paired-checkpoint-screen-v1"
PAIR_KEY_FIELDS = ("option_id", "seed", "seat", "opponent_id")
VALID_STATUSES = ["DONE", "DONE"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def checkpoint_metadata(path: Path) -> dict[str, Any]:
    """Load the fail-closed V114 latent-role inference contract."""

    resolved = path.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"checkpoint does not exist: {resolved}")
    payload = serialization.msgpack_restore(resolved.read_bytes())
    model_id = str(payload.get("model_id", ""))
    if not model_id.startswith("v114_") or "latent_role" not in model_id:
        raise ValueError(f"checkpoint is not a V114 latent-role model: {resolved}")
    required_false = (
        "inherits_v113_checkpoint",
        "online_historical_agent_fallback",
        "teacher_role_conditions_action_decoder",
    )
    for field in required_false:
        if payload.get(field) is not False:
            raise ValueError(f"checkpoint field {field!r} must be false: {resolved}")
    if "params" not in payload:
        raise ValueError(f"checkpoint has no params: {resolved}")
    architecture = str(payload.get("architecture", ""))
    if not architecture:
        raise ValueError(f"checkpoint has no architecture: {resolved}")
    return {
        "path": str(resolved),
        "model_id": model_id,
        "architecture": architecture,
        "sha256_before": sha256_file(resolved),
    }


def validate_checkpoint_pair(
    baseline_checkpoint: Path, candidate_checkpoint: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    baseline = checkpoint_metadata(baseline_checkpoint)
    candidate = checkpoint_metadata(candidate_checkpoint)
    if baseline["architecture"] != candidate["architecture"]:
        raise ValueError(
            "baseline/candidate architecture mismatch: "
            f"{baseline['architecture']!r} != {candidate['architecture']!r}"
        )
    return baseline, candidate


def _error_row(
    candidate_id: str,
    checkpoint_sha256: str,
    option_id: int,
    seed: int,
    seat: int,
    opponent_id: str,
    error: str,
) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "checkpoint_sha256": checkpoint_sha256,
        "option_id": int(option_id),
        "seed": int(seed),
        "seat": int(seat),
        "opponent_id": str(opponent_id),
        "candidate_reward": 0.0,
        "opponent_reward": 0.0,
        "margin": 0.0,
        "score": 0.0,
        "statuses": ["ERROR", "ERROR"],
        "steps": 0,
        "error": error,
        "catastrophe": True,
        "option_usage": {},
        "unit_role_usage": {},
        "market_role_usage": {},
        "operation_counts": {},
        "nonpass_unit_orders": 0,
        "market_turns": 0,
        "ten_slot_market_turns": 0,
        "ten_slot_rate": 0.0,
        "market_sequence_lengths": {},
    }


def _job_error_rows(
    checkpoint_specs: Iterable[Mapping[str, str]],
    option_id: int,
    seed: int,
    opponent_id: str,
    error: str,
) -> list[dict[str, Any]]:
    return [
        _error_row(
            str(spec["candidate_id"]),
            str(spec["sha256"]),
            option_id,
            seed,
            seat,
            opponent_id,
            error,
        )
        for spec in checkpoint_specs
        for seat in (0, 1)
    ]


def evaluate_pair_job(
    checkpoint_specs: tuple[dict[str, str], ...],
    option_id: int,
    seed: int,
    opponent_id: str,
    worker_cap: int,
    cash_reserve: float,
    terminal_buy_cutoff: int,
) -> list[dict[str, Any]]:
    """Evaluate both checkpoints; convert per-checkpoint failures into rows."""

    rows: list[dict[str, Any]] = []
    for spec in checkpoint_specs:
        candidate_id = str(spec["candidate_id"])
        checkpoint_sha = str(spec["sha256"])
        try:
            result = evaluate_seed(
                str(spec["path"]),
                option_id,
                seed,
                opponent_id,
                worker_cap,
                cash_reserve,
                terminal_buy_cutoff,
            )
        except Exception as exc:  # The parent still receives a complete pair.
            error = f"{type(exc).__name__}: {exc}"
            rows.extend(
                _error_row(
                    candidate_id,
                    checkpoint_sha,
                    option_id,
                    seed,
                    seat,
                    opponent_id,
                    error,
                )
                for seat in (0, 1)
            )
            continue
        for row in result:
            enriched = dict(row)
            enriched.update({
                "candidate_id": candidate_id,
                "checkpoint_sha256": checkpoint_sha,
                "opponent_id": opponent_id,
            })
            rows.append(enriched)
    return rows


def pair_key(row: Mapping[str, Any]) -> tuple[int, int, int, str]:
    return (
        int(row["option_id"]),
        int(row["seed"]),
        int(row["seat"]),
        str(row["opponent_id"]),
    )


def validate_pair_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    candidate_ids: tuple[str, str],
    options: Iterable[int],
    schedule: Iterable[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Strictly join rows on option/seed/seat/opponent."""

    materialized = [dict(row) for row in rows]
    indexed: dict[tuple[str, tuple[int, int, int, str]], dict[str, Any]] = {}
    errors: list[str] = []
    known_candidates = set(candidate_ids)
    for row in materialized:
        candidate_id = str(row.get("candidate_id", ""))
        if candidate_id not in known_candidates:
            errors.append(f"unknown candidate_id {candidate_id!r}")
            continue
        try:
            key = pair_key(row)
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"invalid pair key for {candidate_id}: {exc}")
            continue
        indexed_key = (candidate_id, key)
        if indexed_key in indexed:
            errors.append(f"duplicate row for {candidate_id}:{key}")
            continue
        indexed[indexed_key] = row

    expected_keys = {
        (int(option), int(item["seed"]), seat, str(item["opponent_id"]))
        for option in options
        for item in schedule
        for seat in (0, 1)
    }
    actual_keys = {key for _, key in indexed}
    for key in sorted(expected_keys - actual_keys):
        errors.append(f"missing pair key {key}")
    for key in sorted(actual_keys - expected_keys):
        errors.append(f"unexpected pair key {key}")

    paired: list[dict[str, Any]] = []
    baseline_id, candidate_id = candidate_ids
    for key in sorted(expected_keys):
        baseline = indexed.get((baseline_id, key))
        candidate = indexed.get((candidate_id, key))
        if baseline is None:
            errors.append(f"missing {baseline_id} row at {key}")
        if candidate is None:
            errors.append(f"missing {candidate_id} row at {key}")
        if baseline is None or candidate is None:
            continue
        valid = bool(
            baseline.get("error") is None
            and candidate.get("error") is None
            and baseline.get("statuses") == VALID_STATUSES
            and candidate.get("statuses") == VALID_STATUSES
        )
        paired.append({
            "option_id": key[0],
            "seed": key[1],
            "seat": key[2],
            "opponent_id": key[3],
            "valid": valid,
            "baseline_score": float(baseline.get("score", 0.0)),
            "candidate_score": float(candidate.get("score", 0.0)),
            "score_gain": float(candidate.get("score", 0.0))
            - float(baseline.get("score", 0.0)),
            "own_reward_gain": float(candidate.get("candidate_reward", 0.0))
            - float(baseline.get("candidate_reward", 0.0)),
            "opponent_reward_gain": float(candidate.get("opponent_reward", 0.0))
            - float(baseline.get("opponent_reward", 0.0)),
            "margin_gain": float(candidate.get("margin", 0.0))
            - float(baseline.get("margin", 0.0)),
            "catastrophe_delta": int(bool(candidate.get("catastrophe", True)))
            - int(bool(baseline.get("catastrophe", True))),
        })
    return paired, errors


def seed_block_bootstrap_ci(
    seed_values: np.ndarray, samples: int, seed: int,
) -> list[float]:
    if samples <= 0:
        raise ValueError("bootstrap samples must be positive")
    values = np.asarray(seed_values, dtype=np.float64)
    if values.size == 0:
        return [0.0, 0.0]
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(values), size=(samples, len(values)))
    boot = values[draws].mean(axis=1)
    return [float(value) for value in np.percentile(boot, [2.5, 97.5])]


def _paired_metric(
    pairs: list[dict[str, Any]], name: str, samples: int, bootstrap_seed: int,
) -> dict[str, Any]:
    values = np.asarray([float(row[name]) for row in pairs], dtype=np.float64)
    by_seed: dict[int, list[float]] = defaultdict(list)
    for row in pairs:
        by_seed[int(row["seed"])].append(float(row[name]))
    seed_block_values = {
        str(seed): float(statistics.mean(by_seed[seed])) for seed in sorted(by_seed)
    }
    block_array = np.asarray(list(seed_block_values.values()), dtype=np.float64)
    return {
        "mean": float(values.mean()) if values.size else 0.0,
        "positive_zero_negative": [
            int(np.sum(values > 0)),
            int(np.sum(values == 0)),
            int(np.sum(values < 0)),
        ],
        "seed_block_values": seed_block_values,
        "seed_block_ci95": seed_block_bootstrap_ci(
            block_array, samples, bootstrap_seed
        ),
    }


def paired_analysis(
    pairs: Iterable[Mapping[str, Any]], samples: int, bootstrap_seed: int,
) -> dict[str, Any]:
    valid = [dict(row) for row in pairs if bool(row.get("valid"))]
    metrics = (
        "score_gain",
        "own_reward_gain",
        "opponent_reward_gain",
        "margin_gain",
        "catastrophe_delta",
    )
    result: dict[str, Any] = {
        "games": len(valid),
        "seed_blocks": len({int(row["seed"]) for row in valid}),
        "bootstrap_unit": "seed_block_preserving_both_seats",
    }
    for offset, name in enumerate(metrics, start=1):
        result[name] = _paired_metric(
            valid, name, samples, bootstrap_seed + offset
        )
    return result


def summarize_candidates(
    rows: Iterable[Mapping[str, Any]],
    candidate_ids: Iterable[str],
    options: Iterable[int],
) -> dict[str, dict[str, Any]]:
    materialized = [dict(row) for row in rows]
    summaries: dict[str, dict[str, Any]] = {}
    for candidate_id in candidate_ids:
        selected = [
            row for row in materialized if row.get("candidate_id") == candidate_id
        ]
        summaries[candidate_id] = {
            str(option): summarize_option(selected, int(option)) for option in options
        }
    return summaries


def _checkpoint_after(metadata: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(metadata)
    path = Path(str(metadata["path"]))
    try:
        after = sha256_file(path)
        result["sha256_after"] = after
        result["unchanged"] = after == metadata["sha256_before"]
        result["integrity_error"] = None
    except Exception as exc:
        result["sha256_after"] = None
        result["unchanged"] = False
        result["integrity_error"] = f"{type(exc).__name__}: {exc}"
    return result


def run_campaign(
    args: argparse.Namespace,
    *,
    worker_fn: Callable[..., list[dict[str, Any]]] = evaluate_pair_job,
    executor_cls=ProcessPoolExecutor,
) -> dict[str, Any]:
    options = [int(option) for option in args.options]
    if not options:
        raise ValueError("at least one option is required")
    if len(options) != len(set(options)):
        raise ValueError("options may not contain duplicates")
    if any(option < 0 or option >= NUM_OPTIONS for option in options):
        raise ValueError(f"options must be in [0, {NUM_OPTIONS})")
    if args.seeds <= 0 or args.workers <= 0:
        raise ValueError("seeds and workers must be positive")
    if args.bootstrap_samples <= 0:
        raise ValueError("bootstrap samples must be positive")

    baseline, candidate = validate_checkpoint_pair(
        args.baseline_checkpoint, args.candidate_checkpoint
    )
    candidate_ids = (str(args.baseline_name), str(args.candidate_name))
    if not all(candidate_ids) or candidate_ids[0] == candidate_ids[1]:
        raise ValueError("baseline and candidate names must be non-empty and distinct")
    checkpoint_specs = (
        {
            "candidate_id": candidate_ids[0],
            "path": baseline["path"],
            "sha256": baseline["sha256_before"],
        },
        {
            "candidate_id": candidate_ids[1],
            "path": candidate["path"],
            "sha256": candidate["sha256_before"],
        },
    )
    seeds = list(range(int(args.seed_start), int(args.seed_start) + int(args.seeds)))
    schedule = [
        {"seed": seed, "opponent_id": str(args.opponent)} for seed in seeds
    ]
    registry_sha = args.registry_sha256 or _default_registry_sha256(args.opponent)
    ledger = SeedLedger(args.ledger)
    ledger.reserve_schedule(
        schedule,
        split=args.split,
        campaign_id=args.campaign,
        registry_sha256=registry_sha,
    )
    ledger_sha_after_reservation = ledger.sha256()

    jobs = [(option, seed) for option in options for seed in seeds]
    rows: list[dict[str, Any]] = []
    worker_failures: list[dict[str, Any]] = []
    submitted_seeds: set[int] = set()
    campaign_error: str | None = None
    try:
        with executor_cls(max_workers=min(int(args.workers), len(jobs))) as pool:
            futures = {}
            for option_id, seed in jobs:
                future = pool.submit(
                    worker_fn,
                    checkpoint_specs,
                    option_id,
                    seed,
                    str(args.opponent),
                    int(args.worker_cap),
                    float(args.cash_reserve),
                    int(args.terminal_buy_cutoff),
                )
                submitted_seeds.add(seed)
                futures[future] = (option_id, seed)
            for future in as_completed(futures):
                option_id, seed = futures[future]
                try:
                    rows.extend(future.result())
                except Exception as exc:
                    error = f"{type(exc).__name__}: {exc}"
                    worker_failures.append({
                        "option_id": option_id,
                        "seed": seed,
                        "error": error,
                    })
                    rows.extend(
                        _job_error_rows(
                            checkpoint_specs,
                            option_id,
                            seed,
                            str(args.opponent),
                            error,
                        )
                    )
    except Exception as exc:
        campaign_error = f"{type(exc).__name__}: {exc}"
    finally:
        exposure_error = None
        if submitted_seeds:
            try:
                ledger.mark_schedule_exposed(
                    [{"seed": seed} for seed in sorted(submitted_seeds)]
                )
            except Exception as exc:
                exposure_error = f"{type(exc).__name__}: {exc}"

    baseline_after = _checkpoint_after(baseline)
    candidate_after = _checkpoint_after(candidate)
    paired_rows, pair_errors = validate_pair_rows(
        rows,
        candidate_ids=candidate_ids,
        options=options,
        schedule=schedule,
    )
    valid_pairs = [row for row in paired_rows if row["valid"]]
    by_option = {
        str(option): paired_analysis(
            [row for row in valid_pairs if row["option_id"] == option],
            int(args.bootstrap_samples),
            int(args.bootstrap_seed) + option * 100,
        )
        for option in options
    }
    integrity_ok = baseline_after["unchanged"] and candidate_after["unchanged"]
    game_errors = sum(
        row.get("error") is not None or row.get("statuses") != VALID_STATUSES
        for row in rows
    )
    validation_errors = list(pair_errors)
    if campaign_error:
        validation_errors.append(f"campaign error: {campaign_error}")
    if exposure_error:
        validation_errors.append(f"ledger exposure error: {exposure_error}")
    if not integrity_ok:
        validation_errors.append("checkpoint SHA256 changed or became unreadable")
    status = "VALID" if not validation_errors and game_errors == 0 else "INVALID"
    report = {
        "schema": SCHEMA,
        "status": status,
        "campaign": args.campaign,
        "split": args.split,
        "pair_key_fields": list(PAIR_KEY_FIELDS),
        "fresh_seed_dual_seat": True,
        "checkpoint_architecture_equal": True,
        "checkpoints": {
            candidate_ids[0]: baseline_after,
            candidate_ids[1]: candidate_after,
        },
        "schedule": {
            "seed_start": int(args.seed_start),
            "seed_blocks": len(seeds),
            "seeds": seeds,
            "seats_per_seed": [0, 1],
            "opponent": str(args.opponent),
            "registry_sha256": registry_sha,
        },
        "seed_ledger": {
            "path": str(Path(args.ledger).resolve()),
            "sha256_after_reservation": ledger_sha_after_reservation,
            "sha256_after_exposure": ledger.sha256(),
            "submitted_and_exposed_seeds": sorted(submitted_seeds),
            "exposure_error": exposure_error,
        },
        "safety": {
            "worker_cap": None if int(args.worker_cap) < 0 else int(args.worker_cap),
            "cash_reserve": float(args.cash_reserve),
            "terminal_buy_cutoff": (
                None
                if int(args.terminal_buy_cutoff) < 0
                else int(args.terminal_buy_cutoff)
            ),
        },
        "bootstrap": {
            "samples": int(args.bootstrap_samples),
            "seed": int(args.bootstrap_seed),
            "unit": "seed_block_preserving_both_seats",
        },
        "worker_failures": worker_failures,
        "campaign_error": campaign_error,
        "game_error_rows": int(game_errors),
        "validation_errors": validation_errors,
        "summaries": summarize_candidates(rows, candidate_ids, options),
        "paired": {
            "valid_pairs": len(valid_pairs),
            "invalid_pairs": len(paired_rows) - len(valid_pairs),
            "by_option": by_option,
            "pooled": paired_analysis(
                valid_pairs, int(args.bootstrap_samples), int(args.bootstrap_seed)
            ),
            "rows": paired_rows,
        },
        "rows": sorted(
            rows,
            key=lambda row: (
                str(row.get("candidate_id", "")),
                int(row.get("option_id", -1)),
                int(row.get("seed", -1)),
                int(row.get("seat", -1)),
                str(row.get("opponent_id", "")),
            ),
        ),
    }
    atomic_json(args.output, report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-checkpoint", type=Path, required=True)
    parser.add_argument("--candidate-checkpoint", type=Path, required=True)
    parser.add_argument("--baseline-name", default="v6_frozen")
    parser.add_argument("--candidate-name", default="v8_awr")
    parser.add_argument("--options", type=int, nargs="+", default=[1, 2])
    parser.add_argument("--seed-start", type=int, required=True)
    parser.add_argument("--seeds", type=int, required=True)
    parser.add_argument("--opponent", default="builtin:starter")
    parser.add_argument("--worker-cap", type=int, default=-1)
    parser.add_argument("--cash-reserve", type=float, default=0.0)
    parser.add_argument("--terminal-buy-cutoff", type=int, default=-1)
    parser.add_argument("--campaign", required=True)
    parser.add_argument(
        "--split", choices=("train", "dev", "blind"), default="train"
    )
    parser.add_argument("--registry-sha256")
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--bootstrap-samples", type=int, default=20_000)
    parser.add_argument("--bootstrap-seed", type=int, default=114890)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    report = run_campaign(args)
    print({
        "status": report["status"],
        "campaign": report["campaign"],
        "game_error_rows": report["game_error_rows"],
        "valid_pairs": report["paired"]["valid_pairs"],
        "validation_errors": report["validation_errors"],
    })


if __name__ == "__main__":
    main()
