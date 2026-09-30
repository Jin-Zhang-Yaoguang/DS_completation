"""Collect independent V9 fixed-program demonstrations for Manager BC.

Only the four V9-1-qualified production programs are admitted.  Every fresh
environment seed is reserved once as a dual-seat block and is run against the
same opponent in both seats for all four programs.  Both decision rows and a
complete game table are stored so failed games cannot disappear silently.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
from typing import Any, Callable, Mapping, Sequence

import numpy as np

try:
    from .evaluate_event_program import (
        CATASTROPHE_REWARD,
        EXPECTED_ACTION_STEPS,
        default_registry_sha256,
        file_sha256,
        opponent_artifact,
        resolve_opponent,
    )
    from .event_program import (
        TERMINAL_START_STEP,
        MacroActionMask,
        MacroDecision,
        observation_day,
        observation_step,
    )
    from .event_program_features import (
        DECISION_HEAD_VALUES,
        FEATURE_SCHEMA,
        MANAGER_FEATURE_DIM,
        encode_event_program_features,
        macro_action_mask_arrays,
    )
    from .policy_event_program import FixedEventProgramPolicy, decision_as_dict
    from .seed_ledger import SeedLedger
except ImportError:  # Direct-file CLI execution.
    from evaluate_event_program import (  # type: ignore
        CATASTROPHE_REWARD,
        EXPECTED_ACTION_STEPS,
        default_registry_sha256,
        file_sha256,
        opponent_artifact,
        resolve_opponent,
    )
    from event_program import (  # type: ignore
        TERMINAL_START_STEP,
        MacroActionMask,
        MacroDecision,
        observation_day,
        observation_step,
    )
    from event_program_features import (  # type: ignore
        DECISION_HEAD_VALUES,
        FEATURE_SCHEMA,
        MANAGER_FEATURE_DIM,
        encode_event_program_features,
        macro_action_mask_arrays,
    )
    from policy_event_program import FixedEventProgramPolicy, decision_as_dict  # type: ignore
    from seed_ledger import SeedLedger  # type: ignore


HERE = Path(__file__).resolve().parent
DATASET_SCHEMA = "kaggriculture-v114-event-program-manager-bc-v1"
REPORT_SCHEMA = "kaggriculture-v114-event-program-manager-bc-collection-v1"
QUALIFIED_LINES = ("WHEAT", "TOMATO", "STRAWBERRY", "MELON")
FORBIDDEN_LINES = frozenset({"CARROT"})
FIXED_FIELDS = {
    "worker_cap": 4,
    "cash_reserve": 500,
    "sell_style": "IMMEDIATE",
    "terminal_mode": "NORMAL",
}
SOURCE_FILES = (
    "event_program.py",
    "event_program_features.py",
    "policy_event_program.py",
    "collect_event_program_warmstart.py",
)


def qualified_decision_specs() -> list[dict[str, Any]]:
    return [
        {
            "name": f"{line.lower()}_v9_1_fixed",
            "decision": {"production_line": line, **FIXED_FIELDS},
        }
        for line in QUALIFIED_LINES
    ]


def validate_decision_specs(specs: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if len(specs) != len(QUALIFIED_LINES):
        raise ValueError("warm-start requires exactly four V9-1-qualified programs")
    parsed: list[dict[str, Any]] = []
    seen: set[str] = set()
    for spec in specs:
        decision = MacroDecision(**dict(spec["decision"]))
        payload = decision_as_dict(decision)
        line = payload["production_line"]
        if line in FORBIDDEN_LINES:
            raise ValueError("CARROT is forbidden by the V9-1 qualification gate")
        if line not in QUALIFIED_LINES or line in seen:
            raise ValueError(f"unexpected or duplicate production line: {line}")
        for name, expected in FIXED_FIELDS.items():
            if payload[name] != expected:
                raise ValueError(f"{line} {name} must equal {expected!r}")
        parsed.append({"name": str(spec["name"]), "decision": payload})
        seen.add(line)
    if seen != set(QUALIFIED_LINES):
        raise ValueError("all four qualified production lines are required")
    return parsed


def source_hashes(root: Path = HERE) -> tuple[dict[str, str], str]:
    per_file: dict[str, str] = {}
    combined = hashlib.sha256()
    for name in SOURCE_FILES:
        digest = file_sha256(root / name)
        per_file[name] = digest
        combined.update(name.encode("utf-8"))
        combined.update(b"\0")
        combined.update(bytes.fromhex(digest))
    return per_file, combined.hexdigest()


def action_indices(decision: MacroDecision) -> dict[str, int]:
    return {
        name: int(values.index(getattr(decision, name)))
        for name, values in DECISION_HEAD_VALUES.items()
    }


class RecordingFixedPolicy:
    """Record every Manager boundary before delegating to the fixed executor."""

    def __init__(self, decision: Mapping[str, Any], *, name: str) -> None:
        self.policy = FixedEventProgramPolicy(decision, name=name)
        self.records: list[dict[str, Any]] = []

    def __getattr__(self, name: str) -> Any:
        return getattr(self.policy, name)

    def act(self, observation: Mapping[str, Any]) -> dict[str, Any]:
        day = observation_day(observation)
        step = observation_step(observation)
        boundary = (
            step < TERMINAL_START_STEP
            and (self.policy.state is None or day != self.policy.state.decision_day)
        )
        if boundary:
            decision = self.policy.fixed_decision
            semantic_mask = MacroActionMask.from_observation(observation)
            masks = macro_action_mask_arrays(semantic_mask)
            indices = action_indices(decision)
            legal = all(bool(masks[name][0, index]) for name, index in indices.items())
            self.records.append({
                "features": encode_event_program_features(
                    observation,
                    current_decision=self.policy.state,
                    current_event="DAY_BOUNDARY",
                ),
                "masks": {name: value[0].copy() for name, value in masks.items()},
                "actions": indices,
                "day": int(day),
                "step": int(step),
                "target_legal": bool(legal),
            })
        return self.policy.act(observation)

    def __call__(self, observation: Mapping[str, Any], configuration: Any = None) -> dict[str, Any]:
        del configuration
        return self.act(observation)


def _game_row(
    *,
    spec: Mapping[str, Any],
    seed: int,
    seat: int,
    opponent_id: str,
    candidate_reward: float,
    opponent_reward: float,
    statuses: Sequence[str],
    candidate: RecordingFixedPolicy,
    error: str | None,
) -> dict[str, Any]:
    margin = float(candidate_reward - opponent_reward)
    return {
        "line": str(spec["decision"]["production_line"]),
        "decision_name": str(spec["name"]),
        "seed": int(seed),
        "seat": int(seat),
        "opponent_id": str(opponent_id),
        "candidate_reward": float(candidate_reward),
        "opponent_reward": float(opponent_reward),
        "margin": margin,
        "catastrophe": bool(candidate_reward < CATASTROPHE_REWARD),
        "error": error or "",
        "statuses": list(statuses),
        "action_steps": int(candidate.action_steps),
        "contract_violations": int(candidate.contract_violation_count),
        "terminal_procurement_count": int(candidate.terminal_procurement_count),
        "decision_rows": len(candidate.records),
    }


def collect_line_seed(
    decision_spec: Mapping[str, Any], seed: int, opponent_id: str
) -> dict[str, list[dict[str, Any]]]:
    """Run one qualified program in both seats for one seed block."""

    from kaggle_environments import make

    games: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    for seat in (0, 1):
        candidate = RecordingFixedPolicy(
            dict(decision_spec["decision"]), name=str(decision_spec["name"])
        )
        opponent = resolve_opponent(
            opponent_id,
            f"v114_event_bc_{decision_spec['name']}_{seed}_{seat}",
        )
        agents: list[Any] = [None, None]
        agents[seat], agents[1 - seat] = candidate, opponent
        env = make("kaggriculture", configuration={"seed": int(seed)}, debug=False)
        error: str | None = None
        try:
            env.run(agents)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        rewards = [float(state.reward or 0.0) for state in env.state]
        statuses = [str(state.status) for state in env.state]
        game = _game_row(
            spec=decision_spec,
            seed=seed,
            seat=seat,
            opponent_id=opponent_id,
            candidate_reward=rewards[seat],
            opponent_reward=rewards[1 - seat],
            statuses=statuses,
            candidate=candidate,
            error=error,
        )
        games.append(game)
        for record in candidate.records:
            samples.append({
                **record,
                "seed": int(seed),
                "seat": int(seat),
                "line": game["line"],
                "opponent_id": str(opponent_id),
                "candidate_reward": game["candidate_reward"],
                "opponent_reward": game["opponent_reward"],
                "margin": game["margin"],
                "catastrophe": game["catastrophe"],
                "error": game["error"],
            })
    return {"games": games, "samples": samples}


def failure_games(
    spec: Mapping[str, Any], seed: int, opponent_id: str, error: str
) -> list[dict[str, Any]]:
    return [
        {
            "line": str(spec["decision"]["production_line"]),
            "decision_name": str(spec["name"]),
            "seed": int(seed),
            "seat": seat,
            "opponent_id": str(opponent_id),
            "candidate_reward": 0.0,
            "opponent_reward": 0.0,
            "margin": 0.0,
            "catastrophe": True,
            "error": str(error),
            "statuses": ["ERROR", "ERROR"],
            "action_steps": 0,
            "contract_violations": 0,
            "terminal_procurement_count": 0,
            "decision_rows": 0,
        }
        for seat in (0, 1)
    ]


def _strings(values: Sequence[Any]) -> np.ndarray:
    return np.asarray([str(value) for value in values], dtype=np.str_)


def build_dataset_arrays(
    samples: Sequence[Mapping[str, Any]], games: Sequence[Mapping[str, Any]]
) -> dict[str, np.ndarray]:
    sample_count = len(samples)
    arrays: dict[str, np.ndarray] = {
        "schema": np.asarray(DATASET_SCHEMA),
        "feature_schema_json": np.asarray(
            json.dumps(FEATURE_SCHEMA, ensure_ascii=False, sort_keys=True)
        ),
        "features": (
            np.stack([np.asarray(row["features"], dtype=np.float32) for row in samples])
            if samples else np.empty((0, MANAGER_FEATURE_DIM), dtype=np.float32)
        ),
        "seed": np.asarray([row["seed"] for row in samples], dtype=np.int64),
        "seat": np.asarray([row["seat"] for row in samples], dtype=np.int8),
        "day": np.asarray([row["day"] for row in samples], dtype=np.int16),
        "step": np.asarray([row["step"] for row in samples], dtype=np.int16),
        "line": _strings([row["line"] for row in samples]),
        "opponent_id": _strings([row["opponent_id"] for row in samples]),
        "candidate_reward": np.asarray(
            [row["candidate_reward"] for row in samples], dtype=np.float32
        ),
        "opponent_reward": np.asarray(
            [row["opponent_reward"] for row in samples], dtype=np.float32
        ),
        "margin": np.asarray([row["margin"] for row in samples], dtype=np.float32),
        "catastrophe": np.asarray(
            [row["catastrophe"] for row in samples], dtype=np.bool_
        ),
        "error": _strings([row["error"] for row in samples]),
        "target_legal": np.asarray(
            [row["target_legal"] for row in samples], dtype=np.bool_
        ),
    }
    for name, values in DECISION_HEAD_VALUES.items():
        arrays[f"mask_{name}"] = (
            np.stack([np.asarray(row["masks"][name], dtype=np.bool_) for row in samples])
            if samples else np.empty((0, len(values)), dtype=np.bool_)
        )
        arrays[f"action_{name}"] = np.asarray(
            [row["actions"][name] for row in samples], dtype=np.int32
        )

    arrays.update({
        "game_seed": np.asarray([row["seed"] for row in games], dtype=np.int64),
        "game_seat": np.asarray([row["seat"] for row in games], dtype=np.int8),
        "game_line": _strings([row["line"] for row in games]),
        "game_opponent_id": _strings([row["opponent_id"] for row in games]),
        "game_candidate_reward": np.asarray(
            [row["candidate_reward"] for row in games], dtype=np.float32
        ),
        "game_opponent_reward": np.asarray(
            [row["opponent_reward"] for row in games], dtype=np.float32
        ),
        "game_margin": np.asarray([row["margin"] for row in games], dtype=np.float32),
        "game_catastrophe": np.asarray(
            [row["catastrophe"] for row in games], dtype=np.bool_
        ),
        "game_error": _strings([row["error"] for row in games]),
        "game_statuses_json": _strings(
            [json.dumps(row["statuses"], separators=(",", ":")) for row in games]
        ),
        "game_action_steps": np.asarray(
            [row["action_steps"] for row in games], dtype=np.int16
        ),
        "game_contract_violations": np.asarray(
            [row["contract_violations"] for row in games], dtype=np.int16
        ),
        "game_terminal_procurement_count": np.asarray(
            [row["terminal_procurement_count"] for row in games], dtype=np.int16
        ),
        "game_decision_rows": np.asarray(
            [row["decision_rows"] for row in games], dtype=np.int16
        ),
    })
    if arrays["features"].shape != (sample_count, MANAGER_FEATURE_DIM):
        raise ValueError("decision feature matrix violates the 427-dimensional contract")
    return arrays


def atomic_npz(path: Path, arrays: Mapping[str, np.ndarray]) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", suffix=".npz", dir=path.parent, delete=False) as sink:
        np.savez_compressed(sink, **arrays)
        temporary = Path(sink.name)
    os.replace(temporary, path)


def atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as sink:
        json.dump(payload, sink, ensure_ascii=False, indent=2, sort_keys=True)
        sink.write("\n")
        temporary = Path(sink.name)
    os.replace(temporary, path)


def run_campaign(
    args: argparse.Namespace,
    *,
    worker_fn: Callable[..., dict[str, list[dict[str, Any]]]] = collect_line_seed,
    executor_cls: type = ProcessPoolExecutor,
    ledger_cls: type = SeedLedger,
) -> dict[str, Any]:
    if int(args.seeds) <= 0 or int(args.workers) <= 0:
        raise ValueError("seeds and workers must be positive")
    if int(args.seed_start) < 0:
        raise ValueError("seed_start must be non-negative")
    specs = validate_decision_specs(
        getattr(args, "decision_specs", None) or qualified_decision_specs()
    )
    seeds = list(range(int(args.seed_start), int(args.seed_start) + int(args.seeds)))
    opponent = opponent_artifact(str(args.opponent))
    file_hashes_before, source_sha_before = source_hashes()
    registry_sha = getattr(args, "registry_sha256", None) or default_registry_sha256(
        opponent, source_sha_before
    )
    schedule = [{"seed": seed, "opponent_id": str(args.opponent)} for seed in seeds]
    ledger = ledger_cls(Path(args.ledger))
    ledger.reserve_schedule(
        schedule,
        split=str(args.split),
        campaign_id=str(args.campaign),
        registry_sha256=registry_sha,
    )
    reserved_sha = ledger.sha256()

    started = time.time()
    games: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    worker_failures: list[dict[str, Any]] = []
    exposure_error: str | None = None
    try:
        jobs = [(spec, seed) for spec in specs for seed in seeds]
        with executor_cls(max_workers=min(int(args.workers), len(jobs))) as pool:
            futures = {
                pool.submit(worker_fn, spec, seed, str(args.opponent)): (spec, seed)
                for spec, seed in jobs
            }
            for future in as_completed(futures):
                spec, seed = futures[future]
                try:
                    result = future.result()
                    result_games = list(result["games"])
                    if len(result_games) != 2 or sorted(row["seat"] for row in result_games) != [0, 1]:
                        raise ValueError("worker must expose exactly both candidate seats")
                    games.extend(result_games)
                    samples.extend(result["samples"])
                except Exception as exc:
                    error = f"{type(exc).__name__}: {exc}"
                    worker_failures.append({
                        "line": spec["decision"]["production_line"],
                        "seed": seed,
                        "error": error,
                    })
                    games.extend(failure_games(spec, seed, str(args.opponent), error))
    finally:
        try:
            ledger.mark_schedule_exposed(schedule)
        except Exception as exc:
            exposure_error = f"{type(exc).__name__}: {exc}"

    games.sort(key=lambda row: (row["line"], row["seed"], row["seat"]))
    samples.sort(key=lambda row: (row["line"], row["seed"], row["seat"], row["day"]))
    arrays = build_dataset_arrays(samples, games)
    atomic_npz(Path(args.output), arrays)
    dataset_sha = file_sha256(Path(args.output).expanduser().resolve())
    file_hashes_after, source_sha_after = source_hashes()
    expected_games = len(specs) * len(seeds) * 2
    errors = [row for row in games if row["error"]]
    incomplete = [
        row for row in games
        if row["statuses"] != ["DONE", "DONE"]
        or row["action_steps"] != EXPECTED_ACTION_STEPS
        or row["contract_violations"] != 0
        or row["terminal_procurement_count"] != 0
    ]
    illegal = sum(not bool(row["target_legal"]) for row in samples)
    validation_errors: list[str] = []
    if len(games) != expected_games:
        validation_errors.append(f"game count mismatch: {len(games)} != {expected_games}")
    if errors:
        validation_errors.append(f"{len(errors)} game rows contain errors")
    if incomplete:
        validation_errors.append(f"{len(incomplete)} games violate completion contracts")
    if illegal:
        validation_errors.append(f"{illegal} teacher decisions are illegal under recorded masks")
    if source_sha_before != source_sha_after:
        validation_errors.append("source files changed during collection")
    if exposure_error:
        validation_errors.append("seed ledger exposure failed")

    report = {
        "schema": REPORT_SCHEMA,
        "status": "VALID" if not validation_errors else "INVALID",
        "dataset": {
            "path": str(Path(args.output).expanduser().resolve()),
            "schema": DATASET_SCHEMA,
            "sha256": dataset_sha,
            "compression": "np.savez_compressed",
            "decision_rows": len(samples),
            "game_rows": len(games),
            "includes_failed_game_table": True,
        },
        "checkpoint": {"applicable": False, "reason": "fixed checkpoint-free V9 programs"},
        "source_files_sha256_before": file_hashes_before,
        "source_files_sha256_after": file_hashes_after,
        "source_sha256_before": source_sha_before,
        "source_sha256_after": source_sha_after,
        "campaign": str(args.campaign),
        "split": str(args.split),
        "seed_ledger": {
            "path": str(Path(args.ledger).expanduser().resolve()),
            "campaign": str(args.campaign),
            "reserved_seed_blocks": seeds,
            "sha256_after_reservation": reserved_sha,
            "sha256_after_exposure": ledger.sha256(),
            "exposure_error": exposure_error,
        },
        "fresh_seed_dual_seat": True,
        "same_seed_same_opponent": True,
        "opponent": opponent,
        "registry_sha256": registry_sha,
        "qualified_programs": specs,
        "forbidden_programs": sorted(FORBIDDEN_LINES),
        "expected_games": expected_games,
        "elapsed_seconds": time.time() - started,
        "worker_failures": worker_failures,
        "game_errors": errors,
        "validation_errors": validation_errors,
        "target_legal_rows": len(samples) - illegal,
        "target_illegal_rows": illegal,
        "line_decision_rows": {
            line: sum(row["line"] == line for row in samples) for line in QUALIFIED_LINES
        },
    }
    atomic_json(Path(args.report), report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-start", type=int, required=True)
    parser.add_argument("--seeds", type=int, required=True)
    parser.add_argument("--opponent", default="builtin:starter")
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--split", choices=("train", "dev", "blind"), default="train")
    parser.add_argument("--registry-sha256")
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=max(1, os.cpu_count() or 1))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    report = run_campaign(args)
    print(json.dumps({
        "status": report["status"],
        "dataset": report["dataset"],
        "validation_errors": report["validation_errors"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


__all__ = [
    "DATASET_SCHEMA",
    "FIXED_FIELDS",
    "FORBIDDEN_LINES",
    "QUALIFIED_LINES",
    "RecordingFixedPolicy",
    "action_indices",
    "atomic_npz",
    "build_dataset_arrays",
    "qualified_decision_specs",
    "run_campaign",
    "validate_decision_specs",
]
