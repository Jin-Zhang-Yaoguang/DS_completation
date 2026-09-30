"""Collect fresh-seed, dual-seat on-policy day-level SMDP rollouts for V114 V9.

This collector is deliberately trainer-free.  It persists exact behavior-policy
records, raw public money deltas, and final game outcomes without calculating
advantages or tuning reward coefficients.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import statistics
import sys
import tempfile
import time
from typing import Any, Callable, Iterable, Mapping

import numpy as np

try:
    from .event_ppo_math import HEAD_NAMES, HEAD_SIZES
    from .policy_trainable_event_program import TrainableEventProgramPolicy
    from .seed_ledger import SeedLedger
except ImportError:  # Direct-file imports used by local runners.
    from event_ppo_math import HEAD_NAMES, HEAD_SIZES  # type: ignore
    from policy_trainable_event_program import TrainableEventProgramPolicy  # type: ignore
    from seed_ledger import SeedLedger  # type: ignore


HERE = Path(__file__).resolve().parent
NPZ_SCHEMA = "kaggriculture-v114-event-program-smdp-rollouts-v1"
REPORT_SCHEMA = "kaggriculture-v114-event-program-smdp-collection-v1"
EXPECTED_ACTION_STEPS = 719
EXPECTED_DAY_TRANSITIONS = 28
SOURCE_FILES = (
    "event_program.py",
    "event_program_features.py",
    "event_ppo_math.py",
    "model_event_program_ppo.py",
    "policy_trainable_event_program.py",
    "collect_event_program_ppo_rollouts.py",
    "seed_ledger.py",
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_hashes() -> dict[str, str]:
    return {name: file_sha256(HERE / name) for name in SOURCE_FILES}


def _load_path_agent(path: Path, module_name: str) -> Callable[..., Any]:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"opponent agent does not exist: {path}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load opponent agent: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        try:
            sys.path.remove(str(path.parent))
        except ValueError:
            pass
    agent = getattr(module, "agent", None)
    if not callable(agent):
        raise ValueError(f"opponent module has no callable agent: {path}")
    return agent


def resolve_opponent(value: str, module_name: str) -> Callable[..., Any]:
    if value.startswith("registry:"):
        from evaluate_league import build_registered_opponent
        from opponent_registry import load_registry

        member_id = value.split(":", 1)[1]
        registry = load_registry(HERE / "opponent_registry.json", verify_artifacts=True)
        return build_registered_opponent(registry, member_id, module_name)
    if value.startswith("builtin:"):
        from kaggle_environments.envs.kaggriculture import kaggriculture

        builtins = {
            "pass": kaggriculture.pass_agent,
            "random": kaggriculture.random_agent,
            "starter": kaggriculture.starter_agent,
        }
        name = value.split(":", 1)[1]
        if name not in builtins:
            raise ValueError(f"unknown builtin opponent: {name}")
        return builtins[name]
    return _load_path_agent(Path(value), module_name)


def opponent_artifact(value: str) -> dict[str, Any]:
    if value.startswith("registry:"):
        from opponent_registry import load_registry

        member_id = value.split(":", 1)[1]
        registry = load_registry(HERE / "opponent_registry.json", verify_artifacts=True)
        try:
            member = next(row for row in registry["members"] if row["id"] == member_id)
        except StopIteration as exc:
            raise ValueError(f"unknown registry opponent: {member_id}") from exc
        return {
            "id": member_id,
            "kind": f"registry_{member['kind']}",
            "path": member.get("resolved_path"),
            "sha256": member["sha256"],
            "architecture": member.get("architecture"),
            "training_layer": member.get("training_layer"),
            "lineage": member["lineage"],
            "behavior_family": member["behavior_family"],
            "registry_sha256": registry["registry_sha256"],
        }
    if value.startswith("builtin:"):
        try:
            import kaggle_environments

            version = getattr(kaggle_environments, "__version__", "unknown")
        except Exception:
            version = "unavailable"
        return {"id": value, "kind": "builtin", "version": version}
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"opponent agent does not exist: {path}")
    return {
        "id": value,
        "kind": "python_agent",
        "path": str(path),
        "sha256": file_sha256(path),
    }


def _final_observation(env: Any, seat: int) -> Any:
    state = env.state[seat]
    observation = getattr(state, "observation", None)
    if observation is not None:
        return observation
    if getattr(env, "steps", None):
        return getattr(env.steps[-1][seat], "observation", None)
    return None


def _episode_id(campaign: str, seed: int, seat: int) -> str:
    return f"{campaign}:seed-{int(seed)}:seat-{int(seat)}"


def failure_episode(
    *,
    campaign: str,
    seed: int,
    seat: int,
    opponent_id: str,
    error: str,
) -> dict[str, Any]:
    return {
        "episode_id": _episode_id(campaign, seed, seat),
        "seed": int(seed),
        "seat": int(seat),
        "opponent_id": opponent_id,
        "status": "ERROR",
        "opponent_status": "ERROR",
        "statuses": ["ERROR", "ERROR"],
        "candidate_reward": 0.0,
        "opponent_reward": 0.0,
        "margin": 0.0,
        "score": 0.0,
        "catastrophe": True,
        "action_steps": 0,
        "transition_count": 0,
        "duration_turns_sum": 0,
        "contract_violations": 0,
        "terminal_procurement": 0,
        "error": error,
        "transitions": [],
    }


def collect_seed_block(
    checkpoint: str,
    seed: int,
    opponent_id: str,
    rollout_seed: int,
    campaign: str,
) -> list[dict[str, Any]]:
    """Run the same fresh environment seed in candidate seat 0 and seat 1."""

    from kaggle_environments import make

    episodes: list[dict[str, Any]] = []
    for seat in (0, 1):
        episode_id = _episode_id(campaign, seed, seat)
        policy = TrainableEventProgramPolicy(
            checkpoint,
            rollout_seed=int(rollout_seed),
            episode_key=episode_id,
        )
        opponent = resolve_opponent(
            opponent_id,
            f"v114_v9_ppo_opponent_{int(seed)}_{seat}",
        )
        agents: list[Any] = [None, None]
        agents[seat], agents[1 - seat] = policy, opponent
        env = make("kaggriculture", configuration={"seed": int(seed)}, debug=False)
        try:
            env.run(agents)
            rewards = [float(state.reward or 0.0) for state in env.state]
            statuses = [str(state.status) for state in env.state]
            candidate_reward = rewards[seat]
            opponent_reward = rewards[1 - seat]
            transitions = policy.finalize_episode(
                candidate_reward=candidate_reward,
                opponent_reward=opponent_reward,
                final_observation=_final_observation(env, seat),
                terminal_step=policy.action_steps,
            )
            margin = candidate_reward - opponent_reward
            episodes.append(
                {
                    "episode_id": episode_id,
                    "seed": int(seed),
                    "seat": int(seat),
                    "opponent_id": opponent_id,
                    "status": statuses[seat],
                    "opponent_status": statuses[1 - seat],
                    "statuses": statuses,
                    "candidate_reward": candidate_reward,
                    "opponent_reward": opponent_reward,
                    "margin": margin,
                    "score": 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0,
                    "catastrophe": candidate_reward < 3000.0,
                    "action_steps": policy.action_steps,
                    "transition_count": len(transitions),
                    "duration_turns_sum": sum(
                        int(row["duration_turns"]) for row in transitions
                    ),
                    "contract_violations": policy.contract_violation_count,
                    "terminal_procurement": policy.terminal_procurement_count,
                    "error": None,
                    "transitions": transitions,
                }
            )
        except Exception as exc:
            episodes.append(
                failure_episode(
                    campaign=campaign,
                    seed=seed,
                    seat=seat,
                    opponent_id=opponent_id,
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
    return episodes


def valid_episode(episode: Mapping[str, Any]) -> bool:
    transitions = list(episode.get("transitions", []) or [])
    return bool(
        episode.get("error") is None
        and episode.get("statuses") == ["DONE", "DONE"]
        and int(episode.get("action_steps", -1)) == EXPECTED_ACTION_STEPS
        and int(episode.get("transition_count", -1)) == EXPECTED_DAY_TRANSITIONS
        and int(episode.get("duration_turns_sum", -1)) == EXPECTED_ACTION_STEPS
        and len(transitions) == EXPECTED_DAY_TRANSITIONS
        and sum(bool(row.get("terminal")) for row in transitions) == 1
        and bool(transitions[-1].get("terminal"))
        and int(episode.get("contract_violations", -1)) == 0
        and int(episode.get("terminal_procurement", -1)) == 0
    )


def _unicode(values: Iterable[Any]) -> np.ndarray:
    strings = ["" if value is None else str(value) for value in values]
    width = max([1, *(len(value) for value in strings)])
    return np.asarray(strings, dtype=f"<U{width}")


def build_npz_arrays(episodes: list[dict[str, Any]]) -> dict[str, np.ndarray]:
    """Flatten episodes into a fixed, pickle-free NPZ schema."""

    ordered = sorted(episodes, key=lambda row: (int(row["seed"]), int(row["seat"])))
    transitions: list[dict[str, Any]] = []
    transition_episode_index: list[int] = []
    offsets = [0]
    for episode_index, episode in enumerate(ordered):
        rows = list(episode.get("transitions", []) or [])
        transitions.extend(rows)
        transition_episode_index.extend([episode_index] * len(rows))
        offsets.append(len(transitions))

    count = len(transitions)
    arrays: dict[str, np.ndarray] = {
        "schema": np.asarray(NPZ_SCHEMA),
        "feature_dim": np.asarray(427, dtype=np.int32),
        "episode_offsets": np.asarray(offsets, dtype=np.int64),
        "episode_ids": _unicode(row["episode_id"] for row in ordered),
        "episode_seed": np.asarray([row["seed"] for row in ordered], dtype=np.int64),
        "episode_seat": np.asarray([row["seat"] for row in ordered], dtype=np.int8),
        "episode_opponent_id": _unicode(row["opponent_id"] for row in ordered),
        "episode_status": _unicode(row["status"] for row in ordered),
        "episode_error": _unicode(row.get("error") for row in ordered),
        "transition_episode_index": np.asarray(transition_episode_index, dtype=np.int32),
        "features": np.asarray(
            [row["features"] for row in transitions], dtype=np.float32
        ).reshape(count, 427),
        "old_joint_logp": np.asarray(
            [row["old_joint_logp"] for row in transitions], dtype=np.float32
        ),
        "value": np.asarray([row["value"] for row in transitions], dtype=np.float32),
        "constraint_value": np.asarray(
            [row["constraint_value"] for row in transitions], dtype=np.float32
        ),
        "start_step": np.asarray(
            [row["start_step"] for row in transitions], dtype=np.int32
        ),
        "start_day": np.asarray(
            [row["start_day"] for row in transitions], dtype=np.int16
        ),
        "end_step": np.asarray(
            [row["end_step"] for row in transitions], dtype=np.int32
        ),
        "duration_turns": np.asarray(
            [row["duration_turns"] for row in transitions], dtype=np.int16
        ),
        "next_value": np.asarray(
            [row["next_value"] for row in transitions], dtype=np.float32
        ),
        "next_constraint_value": np.asarray(
            [row["next_constraint_value"] for row in transitions], dtype=np.float32
        ),
        "terminal": np.asarray(
            [row["terminal"] for row in transitions], dtype=np.bool_
        ),
        "own_money_start": np.asarray(
            [row["own_money_start"] for row in transitions], dtype=np.float32
        ),
        "own_money_end": np.asarray(
            [row["own_money_end"] for row in transitions], dtype=np.float32
        ),
        "reward_delta_money": np.asarray(
            [row["reward_delta_money"] for row in transitions], dtype=np.float32
        ),
        "training_reward_raw": np.asarray(
            [row["training_reward_raw"] for row in transitions], dtype=np.float32
        ),
        "training_reward_source": _unicode(
            row["training_reward_source"] for row in transitions
        ),
        "candidate_reward": np.asarray(
            [row["candidate_reward"] for row in transitions], dtype=np.float32
        ),
        "opponent_reward": np.asarray(
            [row["opponent_reward"] for row in transitions], dtype=np.float32
        ),
        "margin": np.asarray([row["margin"] for row in transitions], dtype=np.float32),
        "score": np.asarray([row["score"] for row in transitions], dtype=np.float32),
        "catastrophe": np.asarray(
            [row["catastrophe"] for row in transitions], dtype=np.bool_
        ),
    }
    for head in HEAD_NAMES:
        arrays[f"mask_{head}"] = np.asarray(
            [row["masks"][head] for row in transitions], dtype=np.bool_
        ).reshape(count, HEAD_SIZES[head])
        arrays[f"action_{head}"] = np.asarray(
            [row["actions"][head] for row in transitions], dtype=np.int8
        )
        arrays[f"old_logits_{head}"] = np.asarray(
            [row["old_logits"][head] for row in transitions], dtype=np.float32
        ).reshape(count, HEAD_SIZES[head])
    return arrays


def atomic_npz(path: Path, arrays: Mapping[str, np.ndarray]) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".npz", delete=False) as sink:
        temporary = Path(sink.name)
        np.savez_compressed(sink, **arrays)
        sink.flush()
        os.fsync(sink.fileno())
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


def _registry_sha(
    checkpoint_sha: str,
    sources: Mapping[str, str],
    opponent: Mapping[str, Any],
) -> str:
    payload = {
        "checkpoint_sha256": checkpoint_sha,
        "source_sha256": dict(sources),
        "opponent": dict(opponent),
        "seats": [0, 1],
        "qualified_production_lines": ["WHEAT", "TOMATO", "STRAWBERRY", "MELON"],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _summary(episodes: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [row for row in episodes if valid_episode(row)]
    rewards = [float(row["candidate_reward"]) for row in valid]
    return {
        "episodes": len(episodes),
        "valid_episodes": len(valid),
        "invalid_episodes": len(episodes) - len(valid),
        "transitions": sum(int(row.get("transition_count", 0)) for row in episodes),
        "errors": sum(row.get("error") is not None for row in episodes),
        "wdl": {
            "wins": sum(float(row["score"]) == 1.0 for row in valid),
            "draws": sum(float(row["score"]) == 0.5 for row in valid),
            "losses": sum(float(row["score"]) == 0.0 for row in valid),
        },
        "score_rate": statistics.mean(float(row["score"]) for row in valid) if valid else 0.0,
        "mean_candidate_reward": statistics.mean(rewards) if rewards else 0.0,
        "catastrophes": sum(bool(row["catastrophe"]) for row in valid),
        "raw_reward_contract": "public own-money end minus start; NaN if unavailable",
    }


def _public_episode_row(episode: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in episode.items() if key != "transitions"}


def _validate_args(args: argparse.Namespace) -> Path:
    checkpoint = Path(args.checkpoint).expanduser().resolve()
    if not checkpoint.is_file():
        raise ValueError(f"checkpoint does not exist: {checkpoint}")
    if int(args.seed_start) < 0 or int(args.seeds) <= 0:
        raise ValueError("seed_start must be non-negative and seeds must be positive")
    if int(args.workers) <= 0:
        raise ValueError("workers must be positive")
    if str(args.split) != "train":
        raise ValueError("this collector is train-only; Gold Dev/Blind are forbidden")
    if not str(args.campaign).strip():
        raise ValueError("campaign is required")
    return checkpoint


def run_campaign(
    args: argparse.Namespace,
    *,
    worker_fn: Callable[..., list[dict[str, Any]]] = collect_seed_block,
    executor_cls: type = ProcessPoolExecutor,
    ledger_cls: type = SeedLedger,
) -> dict[str, Any]:
    checkpoint = _validate_args(args)
    seeds = list(range(int(args.seed_start), int(args.seed_start) + int(args.seeds)))
    checkpoint_sha_before = file_sha256(checkpoint)
    sources_before = source_hashes()
    opponent = opponent_artifact(str(args.opponent))
    registry_sha = getattr(args, "registry_sha256", None) or _registry_sha(
        checkpoint_sha_before, sources_before, opponent
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
    episodes: list[dict[str, Any]] = []
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
                        str(checkpoint),
                        seed,
                        str(args.opponent),
                        int(args.rollout_seed),
                        str(args.campaign),
                    ): seed
                    for seed in seeds
                }
                for future in as_completed(futures):
                    seed = futures[future]
                    try:
                        result = future.result()
                        if (
                            len(result) != 2
                            or sorted(int(row.get("seat", -1)) for row in result) != [0, 1]
                        ):
                            raise ValueError("worker must return exactly seat 0 and seat 1")
                        episodes.extend(result)
                    except Exception as exc:
                        error = f"{type(exc).__name__}: {exc}"
                        worker_failures.append({"seed": seed, "error": error})
                        episodes.extend(
                            failure_episode(
                                campaign=str(args.campaign),
                                seed=seed,
                                seat=seat,
                                opponent_id=str(args.opponent),
                                error=error,
                            )
                            for seat in (0, 1)
                        )
                    completed.add(seed)
        except Exception as exc:
            campaign_error = f"{type(exc).__name__}: {exc}"
            for seed in seeds:
                if seed in completed:
                    continue
                worker_failures.append({"seed": seed, "error": campaign_error})
                episodes.extend(
                    failure_episode(
                        campaign=str(args.campaign),
                        seed=seed,
                        seat=seat,
                        opponent_id=str(args.opponent),
                        error=campaign_error,
                    )
                    for seat in (0, 1)
                )
    finally:
        try:
            ledger.mark_schedule_exposed(schedule)
        except Exception as exc:
            exposure_error = f"{type(exc).__name__}: {exc}"

    episodes.sort(key=lambda row: (int(row["seed"]), int(row["seat"])))
    arrays = build_npz_arrays(episodes)
    npz_path = Path(args.output_npz).expanduser().resolve()
    atomic_npz(npz_path, arrays)
    npz_sha = file_sha256(npz_path)
    checkpoint_sha_after = file_sha256(checkpoint)
    sources_after = source_hashes()

    validation_errors: list[str] = []
    expected_episodes = len(seeds) * 2
    if len(episodes) != expected_episodes:
        validation_errors.append(
            f"episode count mismatch: {len(episodes)} != {expected_episodes}"
        )
    if checkpoint_sha_after != checkpoint_sha_before:
        validation_errors.append("checkpoint SHA256 changed during collection")
    for name in SOURCE_FILES:
        if sources_after.get(name) != sources_before.get(name):
            validation_errors.append(f"source changed during collection: {name}")
    if campaign_error is not None:
        validation_errors.append("process pool campaign failed")
    if exposure_error is not None:
        validation_errors.append("seed ledger exposure failed")
    if any(not valid_episode(row) for row in episodes):
        validation_errors.append("one or more episodes failed rollout contract")

    report = {
        "schema": REPORT_SCHEMA,
        "status": "VALID" if not validation_errors else "INVALID",
        "campaign": str(args.campaign),
        "split": "train",
        "fresh_seed_dual_seat": True,
        "seed_start": int(args.seed_start),
        "seed_blocks": len(seeds),
        "seats": [0, 1],
        "rollout_seed": int(args.rollout_seed),
        "checkpoint": {
            "path": str(checkpoint),
            "sha256_before": checkpoint_sha_before,
            "sha256_after": checkpoint_sha_after,
            "unchanged": checkpoint_sha_before == checkpoint_sha_after,
        },
        "sources": {
            name: {
                "path": str(HERE / name),
                "sha256_before": sources_before[name],
                "sha256_after": sources_after[name],
                "unchanged": sources_before[name] == sources_after[name],
            }
            for name in SOURCE_FILES
        },
        "opponent": opponent,
        "registry_sha256": registry_sha,
        "seed_ledger": {
            "path": str(Path(args.ledger).expanduser().resolve()),
            "sha256_after_reservation": ledger_sha_reserved,
            "sha256_after_exposure": ledger.sha256(),
            "reserved_seed_blocks": seeds,
            "exposure_error": exposure_error,
        },
        "artifact": {
            "path": str(npz_path),
            "sha256": npz_sha,
            "schema": NPZ_SCHEMA,
            "pickle_required": False,
            "episode_offsets": len(episodes) + 1,
            "transitions": int(arrays["features"].shape[0]),
        },
        "reward_contract": {
            "training_reward_raw": "public own_money_end - own_money_start",
            "unavailable": "NaN; never imputed from final reward",
            "collector_shaping": False,
            "episode_outcomes": "stored unchanged on every transition",
        },
        "mask_contract": {
            "production_head_size": 5,
            "carrot_index": 1,
            "carrot_legal": False,
            "state_macro_action_mask": True,
        },
        "expected_action_steps": EXPECTED_ACTION_STEPS,
        "expected_day_transitions": EXPECTED_DAY_TRANSITIONS,
        "elapsed_seconds": time.time() - started,
        "validation_errors": validation_errors,
        "campaign_error": campaign_error,
        "worker_failures": worker_failures,
        "summary": _summary(episodes),
        "episodes": [_public_episode_row(row) for row in episodes],
    }
    atomic_json(Path(args.output_report), report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--seed-start", type=int, required=True)
    parser.add_argument("--seeds", type=int, required=True)
    parser.add_argument("--rollout-seed", type=int, required=True)
    parser.add_argument("--opponent", default="builtin:starter")
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--split", choices=("train",), default="train")
    parser.add_argument("--registry-sha256")
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output-npz", type=Path, required=True)
    parser.add_argument("--output-report", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=max(1, os.cpu_count() or 1))
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
                "artifact": report["artifact"],
                "summary": report["summary"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()


__all__ = [
    "EXPECTED_ACTION_STEPS",
    "EXPECTED_DAY_TRANSITIONS",
    "NPZ_SCHEMA",
    "REPORT_SCHEMA",
    "atomic_npz",
    "build_npz_arrays",
    "collect_seed_block",
    "failure_episode",
    "run_campaign",
    "valid_episode",
]
