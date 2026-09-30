"""Paired fresh-seed evaluator for two V114 V9 Event-Program checkpoints.

Each seed block is reserved once and contains four games: incumbent and
challenger in seat 0 and seat 1 against the same opponent.  The two policies
share an explicit rollout seed and a checkpoint-independent episode key, so
their categorical draws are paired while different logits may still produce
different macro actions.  Confidence intervals resample complete seed blocks
and therefore preserve the two-seat dependency.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import statistics
import time
from typing import Any, Callable, Iterable, Mapping

from flax import serialization
import numpy as np

try:
    from .collect_event_program_ppo_rollouts import (
        EXPECTED_ACTION_STEPS,
        EXPECTED_DAY_TRANSITIONS,
        SOURCE_FILES as ROLLOUT_SOURCE_FILES,
        atomic_json,
        file_sha256,
        opponent_artifact,
        resolve_opponent,
    )
    from .event_program_features import FEATURE_SCHEMA, MANAGER_FEATURE_DIM
    from .model_event_program_ppo import validate_checkpoint_metadata
    from .policy_trainable_event_program import (
        CATASTROPHE_REWARD,
        TrainableEventProgramPolicy,
    )
    from .seed_ledger import SeedLedger
except ImportError:  # Direct-file imports used by local runners.
    from collect_event_program_ppo_rollouts import (  # type: ignore
        EXPECTED_ACTION_STEPS,
        EXPECTED_DAY_TRANSITIONS,
        SOURCE_FILES as ROLLOUT_SOURCE_FILES,
        atomic_json,
        file_sha256,
        opponent_artifact,
        resolve_opponent,
    )
    from event_program_features import FEATURE_SCHEMA, MANAGER_FEATURE_DIM  # type: ignore
    from model_event_program_ppo import validate_checkpoint_metadata  # type: ignore
    from policy_trainable_event_program import (  # type: ignore
        CATASTROPHE_REWARD,
        TrainableEventProgramPolicy,
    )
    from seed_ledger import SeedLedger  # type: ignore


HERE = Path(__file__).resolve().parent
SCHEMA = "kaggriculture-v114-event-program-paired-checkpoint-evaluation-v1"
PAIR_KEY_FIELDS = ("seed", "seat", "opponent_id")
CHECKPOINT_ROLES = ("incumbent", "challenger")
VALID_STATUSES = ["DONE", "DONE"]
CRITICAL_SOURCE_FILES = tuple(
    dict.fromkeys((
        *ROLLOUT_SOURCE_FILES,
        "evaluate_event_program_pair.py",
        "policy_delayed_trainable_event_program.py",
        "evaluate_delayed_route_pair.py",
    ))
)


def checkpoint_independent_episode_key(seed: int, seat: int, opponent_id: str) -> str:
    """Return a pairing key with no checkpoint or campaign identity."""

    opponent_digest = hashlib.sha256(str(opponent_id).encode("utf-8")).hexdigest()[:16]
    return f"event-program-pair:seed-{int(seed)}:seat-{int(seat)}:opponent-{opponent_digest}"


def source_hashes() -> dict[str, str]:
    return {name: file_sha256(HERE / name) for name in CRITICAL_SOURCE_FILES}


def checkpoint_metadata(path: Path) -> dict[str, Any]:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise ValueError(f"checkpoint does not exist: {resolved}")
    payload = serialization.msgpack_restore(resolved.read_bytes())
    validate_checkpoint_metadata(payload)
    if int(payload.get("input_dim", -1)) != MANAGER_FEATURE_DIM:
        raise ValueError(f"checkpoint input_dim is not {MANAGER_FEATURE_DIM}: {resolved}")
    if payload.get("feature_schema") != FEATURE_SCHEMA:
        raise ValueError(f"checkpoint feature schema mismatch: {resolved}")
    if "params" not in payload:
        raise ValueError(f"checkpoint has no params: {resolved}")
    if "policy_seed" not in payload:
        raise ValueError(f"checkpoint has no policy_seed: {resolved}")
    return {
        "path": str(resolved),
        "sha256_before": file_sha256(resolved),
        "model_id": payload.get("model_id"),
        "architecture": payload.get("architecture"),
        "policy_seed": int(payload["policy_seed"]),
        "strategy_parent": payload.get("strategy_parent"),
    }


def validate_checkpoint_pair(
    incumbent_path: Path, challenger_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    incumbent = checkpoint_metadata(incumbent_path)
    challenger = checkpoint_metadata(challenger_path)
    if incumbent["architecture"] != challenger["architecture"]:
        raise ValueError("incumbent/challenger architecture mismatch")
    if incumbent["policy_seed"] != challenger["policy_seed"]:
        raise ValueError(
            "incumbent/challenger policy_seed mismatch; paired random streams require equality"
        )
    return incumbent, challenger


def game_score(margin: float) -> float:
    return 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0


def percentile_10(values: Iterable[float]) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    index = max(0, min(len(ordered) - 1, int(0.1 * (len(ordered) - 1))))
    return ordered[index]


def _final_observation(env: Any, seat: int) -> Any:
    state = env.state[seat]
    observation = getattr(state, "observation", None)
    if observation is not None:
        return observation
    if getattr(env, "steps", None):
        return getattr(env.steps[-1][seat], "observation", None)
    return None


def _error_side(error: str) -> dict[str, Any]:
    return {
        "reward": 0.0,
        "opponent_reward": 0.0,
        "margin": 0.0,
        "score": 0.0,
        "catastrophe": True,
        "action_steps": 0,
        "decision_count": 0,
        "contract_violations": 0,
        "terminal_procurement": 0,
        "status": "ERROR",
        "opponent_status": "ERROR",
        "statuses": ["ERROR", "ERROR"],
        "environment_states": 0,
        "error": error,
    }


def _evaluate_one(
    checkpoint: str,
    *,
    seed: int,
    seat: int,
    opponent_id: str,
    rollout_seed: int,
    episode_key: str,
    deterministic: bool = False,
) -> dict[str, Any]:
    """Run one checkpoint without allowing its identity into the RNG key."""

    try:
        from kaggle_environments import make

        policy = TrainableEventProgramPolicy(
            checkpoint,
            rollout_seed=int(rollout_seed),
            episode_key=episode_key,
            deterministic=deterministic,
        )
        opponent = resolve_opponent(
            opponent_id,
            f"v114_event_pair_opponent_{int(seed)}_{int(seat)}",
        )
        agents: list[Any] = [None, None]
        agents[seat], agents[1 - seat] = policy, opponent
        env = make("kaggriculture", configuration={"seed": int(seed)}, debug=False)
        env.run(agents)
        rewards = [float(state.reward or 0.0) for state in env.state]
        statuses = [str(state.status) for state in env.state]
        reward = rewards[seat]
        opponent_reward = rewards[1 - seat]
        policy.finalize_episode(
            candidate_reward=reward,
            opponent_reward=opponent_reward,
            final_observation=_final_observation(env, seat),
            terminal_step=policy.action_steps,
        )
        margin = reward - opponent_reward
        return {
            "reward": reward,
            "opponent_reward": opponent_reward,
            "margin": margin,
            "score": game_score(margin),
            "catastrophe": reward < CATASTROPHE_REWARD,
            "action_steps": int(policy.action_steps),
            "decision_count": int(policy.manager_decision_count),
            "contract_violations": int(policy.contract_violation_count),
            "terminal_procurement": int(policy.terminal_procurement_count),
            "status": statuses[seat],
            "opponent_status": statuses[1 - seat],
            "statuses": statuses,
            "environment_states": len(env.steps),
            "error": None,
        }
    except Exception as exc:
        return _error_side(f"{type(exc).__name__}: {exc}")


def _paired_row(
    *,
    seed: int,
    seat: int,
    opponent_id: str,
    episode_key: str,
    incumbent: Mapping[str, Any],
    challenger: Mapping[str, Any],
) -> dict[str, Any]:
    incumbent_side = dict(incumbent)
    challenger_side = dict(challenger)
    return {
        "seed": int(seed),
        "seat": int(seat),
        "opponent_id": str(opponent_id),
        "episode_key": str(episode_key),
        "incumbent": incumbent_side,
        "challenger": challenger_side,
        "score_delta": float(challenger_side["score"])
        - float(incumbent_side["score"]),
        "reward_delta": float(challenger_side["reward"])
        - float(incumbent_side["reward"]),
        "margin_delta": float(challenger_side["margin"])
        - float(incumbent_side["margin"]),
        "catastrophe_delta": int(bool(challenger_side["catastrophe"]))
        - int(bool(incumbent_side["catastrophe"])),
    }


def evaluate_pair_seed(
    checkpoint_specs: tuple[dict[str, str], ...],
    seed: int,
    opponent_id: str,
    rollout_seed: int,
) -> list[dict[str, Any]]:
    """Run incumbent/challenger in both seats of one environment seed."""

    specs = {str(item["role"]): dict(item) for item in checkpoint_specs}
    if set(specs) != set(CHECKPOINT_ROLES):
        raise ValueError("checkpoint_specs must contain incumbent and challenger")
    rows: list[dict[str, Any]] = []
    for seat in (0, 1):
        episode_key = checkpoint_independent_episode_key(seed, seat, opponent_id)
        sides = {
            role: _evaluate_one(
                str(specs[role]["path"]),
                seed=seed,
                seat=seat,
                opponent_id=opponent_id,
                rollout_seed=rollout_seed,
                episode_key=episode_key,
                deterministic=bool(specs[role].get("deterministic", False)),
            )
            for role in CHECKPOINT_ROLES
        }
        rows.append(
            _paired_row(
                seed=seed,
                seat=seat,
                opponent_id=opponent_id,
                episode_key=episode_key,
                incumbent=sides["incumbent"],
                challenger=sides["challenger"],
            )
        )
    return rows


def failure_pair_rows(seed: int, opponent_id: str, error: str) -> list[dict[str, Any]]:
    return [
        _paired_row(
            seed=seed,
            seat=seat,
            opponent_id=opponent_id,
            episode_key=checkpoint_independent_episode_key(seed, seat, opponent_id),
            incumbent=_error_side(error),
            challenger=_error_side(error),
        )
        for seat in (0, 1)
    ]


def valid_side(side: Mapping[str, Any]) -> bool:
    expected_decisions = int(
        side.get("expected_decision_count", EXPECTED_DAY_TRANSITIONS)
    )
    return bool(
        side.get("error") is None
        and side.get("statuses") == VALID_STATUSES
        and int(side.get("action_steps", -1)) == EXPECTED_ACTION_STEPS
        and int(side.get("decision_count", -1)) == expected_decisions
        and int(side.get("contract_violations", -1)) == 0
        and int(side.get("terminal_procurement", -1)) == 0
    )


def valid_pair(row: Mapping[str, Any]) -> bool:
    return valid_side(row.get("incumbent", {})) and valid_side(
        row.get("challenger", {})
    )


def summarize_checkpoint(
    rows: Iterable[Mapping[str, Any]], role: str,
) -> dict[str, Any]:
    materialized = [dict(row) for row in rows]
    sides = [dict(row.get(role, {})) for row in materialized]
    valid = [side for side in sides if valid_side(side)]
    rewards = [float(side["reward"]) for side in valid]
    margins = [float(side["margin"]) for side in valid]
    catastrophes = sum(bool(side["catastrophe"]) for side in valid)
    return {
        "games": len(sides),
        "valid_games": len(valid),
        "invalid_games": len(sides) - len(valid),
        "wdl": {
            "wins": sum(float(side["score"]) == 1.0 for side in valid),
            "draws": sum(float(side["score"]) == 0.5 for side in valid),
            "losses": sum(float(side["score"]) == 0.0 for side in valid),
        },
        "score_rate": statistics.mean(float(side["score"]) for side in valid)
        if valid
        else 0.0,
        "mean_reward": statistics.mean(rewards) if rewards else 0.0,
        "p10_reward": percentile_10(rewards),
        "mean_opponent_reward": statistics.mean(
            float(side["opponent_reward"]) for side in valid
        )
        if valid
        else 0.0,
        "mean_margin": statistics.mean(margins) if margins else 0.0,
        "catastrophe_games": catastrophes,
        "catastrophe_rate": catastrophes / len(valid) if valid else 0.0,
        "errors": sum(side.get("error") is not None for side in sides),
        "contract_violations": sum(
            int(side.get("contract_violations", 0)) for side in sides
        ),
        "terminal_procurement": sum(
            int(side.get("terminal_procurement", 0)) for side in sides
        ),
    }


def seed_block_bootstrap_ci(
    seed_block_values: Iterable[float], *, samples: int, seed: int,
) -> list[float]:
    if int(samples) <= 0:
        raise ValueError("bootstrap samples must be positive")
    values = np.asarray(list(seed_block_values), dtype=np.float64)
    if values.size == 0:
        return [0.0, 0.0]
    rng = np.random.default_rng(int(seed))
    draws = rng.integers(0, values.size, size=(int(samples), values.size))
    means = values[draws].mean(axis=1)
    return [float(value) for value in np.percentile(means, [2.5, 97.5])]


def _complete_valid_blocks(
    rows: Iterable[Mapping[str, Any]],
) -> dict[int, list[dict[str, Any]]]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[int(row["seed"])].append(dict(row))
    return {
        seed: sorted(block, key=lambda row: int(row["seat"]))
        for seed, block in grouped.items()
        if sorted(int(row["seat"]) for row in block) == [0, 1]
        and all(valid_pair(row) for row in block)
    }


def paired_analysis(
    rows: Iterable[Mapping[str, Any]], *, bootstrap_samples: int, bootstrap_seed: int,
) -> dict[str, Any]:
    materialized = [dict(row) for row in rows]
    blocks = _complete_valid_blocks(materialized)
    valid_rows = [row for seed in sorted(blocks) for row in blocks[seed]]
    metrics = ("score_delta", "reward_delta", "margin_delta", "catastrophe_delta")
    result: dict[str, Any] = {
        "valid_seed_blocks": len(blocks),
        "valid_pairs": len(valid_rows),
        "excluded_seed_blocks": len({int(row["seed"]) for row in materialized})
        - len(blocks),
        "bootstrap_unit": "seed_block_preserving_both_seats",
    }
    for offset, metric in enumerate(metrics, start=1):
        values = [float(row[metric]) for row in valid_rows]
        block_values = {
            str(seed): float(statistics.mean(float(row[metric]) for row in blocks[seed]))
            for seed in sorted(blocks)
        }
        result[metric] = {
            "mean": statistics.mean(values) if values else 0.0,
            "positive_zero_negative": [
                sum(value > 0 for value in values),
                sum(value == 0 for value in values),
                sum(value < 0 for value in values),
            ],
            "seed_block_values": block_values,
            "seed_block_ci95": seed_block_bootstrap_ci(
                block_values.values(),
                samples=bootstrap_samples,
                seed=bootstrap_seed + offset,
            ),
        }
    return result


def _checkpoint_after(before: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(before)
    try:
        after = file_sha256(Path(str(before["path"])))
        result.update(
            {
                "sha256_after": after,
                "unchanged": after == before["sha256_before"],
                "integrity_error": None,
            }
        )
    except Exception as exc:
        result.update(
            {
                "sha256_after": None,
                "unchanged": False,
                "integrity_error": f"{type(exc).__name__}: {exc}",
            }
        )
    return result


def _registry_sha256(
    checkpoints: Mapping[str, Mapping[str, Any]],
    sources: Mapping[str, str],
    opponent: Mapping[str, Any],
    rollout_seed: int,
    deterministic: bool = False,
) -> str:
    payload = {
        "checkpoints": {
            role: checkpoints[role]["sha256_before"] for role in CHECKPOINT_ROLES
        },
        "sources": dict(sources),
        "opponent": dict(opponent),
        "rollout_seed": int(rollout_seed),
        "pair_key_fields": list(PAIR_KEY_FIELDS),
        "deterministic": bool(deterministic),
        "seats": [0, 1],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validate_args(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if int(args.seed_start) < 0 or int(args.seeds) <= 0:
        raise ValueError("seed_start must be non-negative and seeds must be positive")
    if int(args.workers) <= 0:
        raise ValueError("workers must be positive")
    if int(args.bootstrap_samples) <= 0:
        raise ValueError("bootstrap_samples must be positive")
    if str(args.split) != "train":
        raise ValueError("this evaluator is train-only; Dev/Blind are forbidden")
    if not str(args.campaign).strip():
        raise ValueError("campaign is required")
    return validate_checkpoint_pair(Path(args.incumbent), Path(args.challenger))


def run_campaign(
    args: argparse.Namespace,
    *,
    worker_fn: Callable[..., list[dict[str, Any]]] = evaluate_pair_seed,
    executor_cls: type = ProcessPoolExecutor,
    ledger_cls: type = SeedLedger,
) -> dict[str, Any]:
    """Reserve once, evaluate paired games, expose once, and atomically report."""

    incumbent_before, challenger_before = _validate_args(args)
    deterministic = bool(getattr(args, "deterministic", False))
    checkpoints_before = {
        "incumbent": incumbent_before,
        "challenger": challenger_before,
    }
    checkpoint_specs = tuple(
        {
            "role": role,
            "path": str(checkpoints_before[role]["path"]),
            "sha256": str(checkpoints_before[role]["sha256_before"]),
            "deterministic": deterministic,
        }
        for role in CHECKPOINT_ROLES
    )
    seeds = list(range(int(args.seed_start), int(args.seed_start) + int(args.seeds)))
    sources_before = source_hashes()
    opponent = opponent_artifact(str(args.opponent))
    registry_sha = _registry_sha256(
        checkpoints_before,
        sources_before,
        opponent,
        int(args.rollout_seed),
        deterministic,
    )
    schedule = [{"seed": seed, "opponent_id": str(args.opponent)} for seed in seeds]
    ledger = ledger_cls(Path(args.ledger))
    ledger.reserve_schedule(
        schedule,
        split="train",
        campaign_id=str(args.campaign),
        registry_sha256=registry_sha,
    )
    ledger_sha_reserved = ledger.sha256()

    started = time.time()
    rows: list[dict[str, Any]] = []
    worker_failures: list[dict[str, Any]] = []
    campaign_error: str | None = None
    exposure_error: str | None = None
    completed: set[int] = set()
    try:
        try:
            with executor_cls(max_workers=min(int(args.workers), len(seeds))) as pool:
                futures = {
                    pool.submit(
                        worker_fn,
                        checkpoint_specs,
                        seed,
                        str(args.opponent),
                        int(args.rollout_seed),
                    ): seed
                    for seed in seeds
                }
                for future in as_completed(futures):
                    seed = futures[future]
                    try:
                        result = future.result()
                        if (
                            len(result) != 2
                            or sorted(int(row.get("seat", -1)) for row in result)
                            != [0, 1]
                            or any(int(row.get("seed", -1)) != seed for row in result)
                            or any(
                                str(row.get("opponent_id", "")) != str(args.opponent)
                                for row in result
                            )
                        ):
                            raise ValueError(
                                "worker must return exact seat 0/1 paired rows for its seed/opponent"
                            )
                        rows.extend(result)
                    except Exception as exc:
                        error = f"{type(exc).__name__}: {exc}"
                        worker_failures.append({"seed": seed, "error": error})
                        rows.extend(failure_pair_rows(seed, str(args.opponent), error))
                    completed.add(seed)
        except Exception as exc:
            campaign_error = f"{type(exc).__name__}: {exc}"
            for seed in seeds:
                if seed in completed:
                    continue
                worker_failures.append({"seed": seed, "error": campaign_error})
                rows.extend(failure_pair_rows(seed, str(args.opponent), campaign_error))
    finally:
        try:
            ledger.mark_schedule_exposed(schedule)
        except Exception as exc:
            exposure_error = f"{type(exc).__name__}: {exc}"

    rows.sort(key=lambda row: (int(row["seed"]), int(row["seat"])))
    checkpoints_after = {
        role: _checkpoint_after(checkpoints_before[role]) for role in CHECKPOINT_ROLES
    }
    sources_after: dict[str, str | None] = {}
    source_read_errors: list[str] = []
    for name in CRITICAL_SOURCE_FILES:
        try:
            sources_after[name] = file_sha256(HERE / name)
        except Exception as exc:
            sources_after[name] = None
            source_read_errors.append(f"source post-run SHA failed for {name}: {exc}")

    validation_errors = list(source_read_errors)
    expected_rows = len(seeds) * 2
    if len(rows) != expected_rows:
        validation_errors.append(f"paired row count mismatch: {len(rows)} != {expected_rows}")
    for role in CHECKPOINT_ROLES:
        if not checkpoints_after[role]["unchanged"]:
            validation_errors.append(f"{role} checkpoint SHA256 changed during evaluation")
    for name in CRITICAL_SOURCE_FILES:
        if sources_after.get(name) != sources_before.get(name):
            validation_errors.append(f"source changed during evaluation: {name}")
    if campaign_error is not None:
        validation_errors.append("process pool campaign failed")
    if exposure_error is not None:
        validation_errors.append("seed ledger exposure failed")
    if any(not valid_pair(row) for row in rows):
        validation_errors.append("one or more checkpoint pairs failed execution contract")

    report = {
        "schema": SCHEMA,
        "status": "VALID" if not validation_errors else "INVALID",
        "campaign": str(args.campaign),
        "split": "train",
        "pair_key_fields": list(PAIR_KEY_FIELDS),
        "fresh_seed_dual_seat": True,
        "seed_start": int(args.seed_start),
        "seed_blocks": len(seeds),
        "seats_per_seed": [0, 1],
        "games_per_seed_block": 4,
        "rollout_seed": int(args.rollout_seed),
        "action_selection": "masked_argmax" if deterministic else "categorical_sample",
        "rng_pairing_contract": {
            "same_rollout_seed": True,
            "same_checkpoint_policy_seed": True,
            "episode_key_excludes": ["checkpoint path", "checkpoint SHA", "checkpoint role", "campaign"],
            "different_logits_may_change_actions": True,
        },
        "checkpoints": checkpoints_after,
        "sources": {
            name: {
                "path": str(HERE / name),
                "sha256_before": sources_before[name],
                "sha256_after": sources_after[name],
                "unchanged": sources_before[name] == sources_after[name],
            }
            for name in CRITICAL_SOURCE_FILES
        },
        "opponent": opponent,
        "registry_sha256": registry_sha,
        "seed_ledger": {
            "path": str(Path(args.ledger).expanduser().resolve()),
            "reserve_schedule_calls_expected": 1,
            "mark_schedule_exposed_calls_expected": 1,
            "sha256_after_reservation": ledger_sha_reserved,
            "sha256_after_exposure": ledger.sha256(),
            "reserved_and_exposed_seed_blocks": seeds,
            "exposure_error": exposure_error,
        },
        "bootstrap": {
            "seed": int(args.bootstrap_seed),
            "samples": int(args.bootstrap_samples),
            "unit": "seed_block_preserving_both_seats",
        },
        "metric_contract": {
            "win": "reward > opponent_reward",
            "draw": "reward == opponent_reward",
            "loss": "reward < opponent_reward",
            "catastrophe": f"reward < {CATASTROPHE_REWARD:g}",
            "delta_direction": "challenger - incumbent",
            "valid_game": (
                f"DONE, {EXPECTED_ACTION_STEPS} actions, "
                "the policy-declared expected decision count, zero violations/procurement"
            ),
        },
        "elapsed_seconds": time.time() - started,
        "expected_paired_rows": expected_rows,
        "validation_errors": validation_errors,
        "campaign_error": campaign_error,
        "worker_failures": worker_failures,
        "summaries": {
            role: summarize_checkpoint(rows, role) for role in CHECKPOINT_ROLES
        },
        "paired": paired_analysis(
            rows,
            bootstrap_samples=int(args.bootstrap_samples),
            bootstrap_seed=int(args.bootstrap_seed),
        ),
        "rows": rows,
    }
    atomic_json(Path(args.output), report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--incumbent", type=Path, required=True)
    parser.add_argument("--challenger", type=Path, required=True)
    parser.add_argument("--seed-start", type=int, required=True)
    parser.add_argument("--seeds", type=int, required=True)
    parser.add_argument("--opponent", default="builtin:starter")
    parser.add_argument("--rollout-seed", type=int, required=True)
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--split", choices=("train",), default="train")
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=max(1, os.cpu_count() or 1))
    parser.add_argument("--bootstrap-seed", type=int, default=114920)
    parser.add_argument("--bootstrap-samples", type=int, default=20_000)
    parser.add_argument("--deterministic", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        report = run_campaign(args)
    except (TypeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(
        json.dumps(
            {
                "status": report["status"],
                "summaries": report["summaries"],
                "paired": report["paired"],
                "validation_errors": report["validation_errors"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()


__all__ = [
    "checkpoint_independent_episode_key",
    "evaluate_pair_seed",
    "failure_pair_rows",
    "paired_analysis",
    "run_campaign",
    "seed_block_bootstrap_ci",
    "summarize_checkpoint",
    "valid_pair",
]
