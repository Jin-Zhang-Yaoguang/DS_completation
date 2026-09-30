"""Collect V114 V8 on-policy self-imitation trajectories.

The frozen V6 latent-role policy controls the official environment.  Its
actual action is canonicalised and encoded as the training target on the state
that produced it.  No teacher policy or teacher label is ever queried.

Only explicitly selected, training-enabled registry members may be opponents.
Gold-Dev and Gold-Blind members are rejected before their artifacts are read.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from flax import serialization
import json
from pathlib import Path
import sys
import time
from typing import Any, Mapping, Sequence

from kaggle_environments import make
import numpy as np


HERE = Path(__file__).resolve().parent
V113 = HERE.parent / "v113_simulator_hmoe_ppo"
if str(V113) not in sys.path:
    sys.path.insert(0, str(V113))

import action_space as space  # noqa: E402
from build_latent_role_dataset import TERMINAL_STEP  # noqa: E402
from collect_dagger import labelled_row  # noqa: E402
from collect_latent_role_dagger import (  # noqa: E402
    FIXED_OPTIONS,
    OPTION_FAMILIES,
    V6_SOURCE_KEYS,
    _apply_v6_derived_contract,
    checkpoint_metadata,
    episode_group_id,
    result_name,
)
from collect_multiteacher_sequence_bc import (  # noqa: E402
    _atomic_json,
    _atomic_npz,
    _string_array,
    canonical_action,
)
from collect_rollouts import (  # noqa: E402
    agent_observations,
    call_opponent,
    resolve_opponent,
)
from opponent_factory import checkpoint_opponent  # noqa: E402
from opponent_registry import (  # noqa: E402
    LAYER_ORDER,
    SCHEMA as REGISTRY_SCHEMA,
    builtin_sha256,
    sha256_file,
)
from policy_latent_role_hmoe import LatentRoleOptionPolicy  # noqa: E402
from policy_v114 import with_observation_step  # noqa: E402
from seed_ledger import SeedLedger  # noqa: E402


SCHEMA = "kaggriculture-v114-v8-latent-self-imitation-v1"
WORKER_CAP = 4
CASH_RESERVE = 0.0
TERMINAL_CUTOFF = 671
CATASTROPHE_REWARD = 3000.0
MARGIN_SCALE = 25000.0
SOURCE_KIND = "candidate_self_imitation"
EXTRA_KEYS = frozenset({
    "candidate_unit_tokens",
    "candidate_unit_quantities",
    "candidate_market_tokens",
    "candidate_market_quantities",
    "candidate_market_mask",
    "episode_return",
    "candidate_reward",
    "margin",
    "result",
    "source_kind",
})
OUTPUT_KEYS = V6_SOURCE_KEYS | EXTRA_KEYS
STRING_KEYS = frozenset({
    "teacher_id", "teacher_family", "teacher_sha256", "result", "source_kind",
})


@dataclass(frozen=True)
class SeedAssignment:
    seed: int
    opponent_id: str
    layer: str
    opponent_sha256: str


class _StepEnrichedCheckpointOpponent:
    """Supply the step field expected by frozen V113 checkpoint opponents."""

    def __init__(self, policy: Any) -> None:
        self.policy = policy

    def __call__(self, obs: Mapping[str, Any], configuration=None):
        return self.policy(with_observation_step(obs), configuration)


def terminal_value(margin: float) -> float:
    """Win/draw/loss objective with a bounded terminal-margin tie breaker."""

    sign = 1.0 if margin > 0 else (-1.0 if margin < 0 else 0.0)
    return float(sign + 0.05 * np.tanh(float(margin) / MARGIN_SCALE))


def _resolve_registry_path(
    registry_path: Path, registry: Mapping[str, Any], value: str,
) -> Path:
    base = (registry_path.parent / str(registry.get("path_base", "."))).resolve()
    return (base / value).resolve()


def load_training_opponents(
    registry_path: Path, requested_ids: Sequence[str],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Verify only requested training opponents and fail closed on Dev/Blind.

    The whole JSON identity manifest is parsed, but artifacts belonging to
    unselected members are never resolved, hashed, imported, or executed.
    """

    registry_path = registry_path.resolve()
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    if registry.get("schema") != REGISTRY_SCHEMA:
        raise ValueError("unsupported V114 opponent registry schema")
    if not requested_ids or any(not str(value) for value in requested_ids):
        raise ValueError("at least one non-empty --opponent id is required")
    members = registry.get("members")
    if not isinstance(members, list):
        raise ValueError("registry members must be a list")

    by_id: dict[str, tuple[int, Mapping[str, Any]]] = {}
    for index, source in enumerate(members):
        member_id = str(source.get("id", ""))
        if not member_id or member_id in by_id:
            raise ValueError(f"missing or duplicate registry member id: {member_id!r}")
        by_id[member_id] = (index, source)

    selected: dict[str, dict[str, Any]] = {}
    for requested in dict.fromkeys(str(value) for value in requested_ids):
        if requested not in by_id:
            raise ValueError(f"unknown registered opponent: {requested}")
        member_index, source = by_id[requested]
        split = source.get("gold_split")
        if split in {"dev", "blind"}:
            raise ValueError(f"Gold-{str(split).title()} opponent is forbidden: {requested}")
        if source.get("training_enabled") is not True:
            raise ValueError(f"opponent is not training-enabled: {requested}")
        layer = str(source.get("training_layer", ""))
        if layer not in LAYER_ORDER:
            raise ValueError(f"opponent has invalid training layer: {requested}")
        if layer == "gold_train" and split != "train":
            raise ValueError(f"Gold-Train opponent has wrong split: {requested}")
        if layer != "gold_train" and split is not None:
            raise ValueError(f"non-Gold opponent has a gold split: {requested}")

        member = dict(source)
        member["member_index"] = int(member_index)
        kind = str(member.get("kind", ""))
        expected_sha = str(member.get("sha256", ""))
        if kind == "builtin":
            spec = str(member.get("spec", ""))
            if not spec.startswith("builtin:"):
                raise ValueError(f"invalid builtin opponent spec: {requested}")
            actual_sha = builtin_sha256(spec)
        elif kind in {"agent", "checkpoint"}:
            artifact = _resolve_registry_path(
                registry_path, registry, str(member.get("path", ""))
            )
            if not artifact.is_file():
                raise FileNotFoundError(f"missing selected opponent: {artifact}")
            actual_sha = sha256_file(artifact)
            member["resolved_path"] = str(artifact)
            if kind == "checkpoint":
                architecture = member.get("architecture")
                if architecture not in {
                    "factorized", "sequence", "timed-sequence",
                    "history-timed-sequence",
                }:
                    raise ValueError(
                        f"unsupported checkpoint architecture for {requested}: {architecture}"
                    )
                has_forced = (
                    member.get("forced_unit_expert") is not None
                    and member.get("forced_market_expert") is not None
                )
                has_schedule = (
                    member.get("unit_expert_schedule") is not None
                    and member.get("market_expert_schedule") is not None
                )
                if has_forced == has_schedule:
                    raise ValueError(
                        f"checkpoint opponent {requested} needs exactly one expert contract"
                    )
        else:
            raise ValueError(f"unsupported selected opponent kind: {kind!r}")
        if actual_sha != expected_sha:
            raise ValueError(
                f"SHA256 mismatch for {requested}: {actual_sha} != {expected_sha}"
            )
        selected[requested] = member

    metadata = {
        "path": str(registry_path),
        "sha256": sha256_file(registry_path),
        "schema": REGISTRY_SCHEMA,
        "selected_ids": list(dict.fromkeys(str(value) for value in requested_ids)),
        "selected_layers": sorted({str(row["training_layer"]) for row in selected.values()}),
        "gold_dev_artifacts_accessed": False,
        "gold_blind_artifacts_accessed": False,
    }
    return metadata, selected


def build_seed_schedule(
    seed_start: int,
    seeds: int,
    opponent_ids: Sequence[str],
    members: Mapping[str, Mapping[str, Any]],
) -> list[SeedAssignment]:
    if seed_start < 0:
        raise ValueError("seed_start must be non-negative")
    if seeds <= 0:
        raise ValueError("seeds must be positive")
    if not opponent_ids:
        raise ValueError("at least one opponent is required")
    schedule: list[SeedAssignment] = []
    for offset in range(int(seeds)):
        opponent_id = str(opponent_ids[offset % len(opponent_ids)])
        if opponent_id not in members:
            raise ValueError(f"opponent is not verified: {opponent_id}")
        member = members[opponent_id]
        schedule.append(SeedAssignment(
            seed=int(seed_start) + offset,
            opponent_id=opponent_id,
            layer=str(member["training_layer"]),
            opponent_sha256=str(member["sha256"]),
        ))
    return schedule


def build_selected_opponent(member: Mapping[str, Any], unique_name: str):
    kind = str(member["kind"])
    if kind == "builtin":
        return resolve_opponent(str(member["spec"]), unique_name)
    if kind == "agent":
        return resolve_opponent(str(member["resolved_path"]), unique_name)
    if kind == "checkpoint":
        policy = checkpoint_opponent(
            Path(str(member["resolved_path"])),
            str(member["architecture"]),
            member.get("forced_unit_expert"),
            member.get("forced_market_expert"),
            unit_expert_schedule=member.get("unit_expert_schedule"),
            market_expert_schedule=member.get("market_expert_schedule"),
        )
        return _StepEnrichedCheckpointOpponent(policy)
    raise ValueError(f"unsupported selected opponent kind: {kind!r}")


def _summary(games: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    valid = [
        game for game in games
        if game.get("statuses") == ["DONE", "DONE"] and game.get("error") is None
    ]
    counts = Counter(str(game["result"]) for game in valid)
    rewards = np.asarray(
        [float(game["candidate_reward"]) for game in valid], dtype=np.float64
    )
    margins = np.asarray([float(game["margin"]) for game in valid], dtype=np.float64)
    catastrophes = int(np.sum(rewards < CATASTROPHE_REWARD)) if len(rewards) else 0
    return {
        "games": len(games),
        "valid_games": len(valid),
        "wdl": {
            "wins": int(counts["win"]),
            "draws": int(counts["draw"]),
            "losses": int(counts["loss"]),
        },
        "score_rate": float(
            np.mean([
                1.0 if game["result"] == "win" else
                (0.5 if game["result"] == "draw" else 0.0)
                for game in valid
            ])
        ) if valid else 0.0,
        "mean_candidate_reward": float(np.mean(rewards)) if len(rewards) else 0.0,
        "p10_candidate_reward": float(np.quantile(rewards, 0.10)) if len(rewards) else 0.0,
        "mean_margin": float(np.mean(margins)) if len(margins) else 0.0,
        "catastrophe_games": catastrophes,
        "catastrophe_rate": catastrophes / len(valid) if valid else 0.0,
        "errors": len(games) - len(valid),
    }


def _grouped_summary(
    games: Sequence[Mapping[str, Any]], key: str,
) -> dict[str, dict[str, Any]]:
    groups: defaultdict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for game in games:
        groups[str(game[key])].append(game)
    return {name: _summary(groups[name]) for name in sorted(groups)}


def _rows_to_arrays(rows: list[dict[str, Any]]) -> dict[str, np.ndarray]:
    if not rows:
        raise RuntimeError("no self-imitation rows were collected")
    keys = set(rows[0])
    if keys != set(OUTPUT_KEYS):
        raise RuntimeError(
            f"V8 row schema mismatch: found={sorted(keys)}, expected={sorted(OUTPUT_KEYS)}"
        )
    if any(set(row) != keys for row in rows):
        raise RuntimeError("self-imitation rows do not share one schema")
    arrays: dict[str, np.ndarray] = {}
    for key in sorted(keys):
        values = [row[key] for row in rows]
        arrays[key] = (
            _string_array([str(value) for value in values])
            if key in STRING_KEYS else np.asarray(values)
        )
    for key in ("global", "board", "units"):
        arrays[key] = arrays[key].astype(np.float16)
    for key in ("value", "episode_return", "candidate_reward", "margin"):
        arrays[key] = arrays[key].astype(np.float32)
    if any(array.dtype == object for array in arrays.values()):
        raise TypeError("object arrays are forbidden in the V8 dataset")
    return arrays


def collect(args: argparse.Namespace) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    started = time.time()
    checkpoint = checkpoint_metadata(Path(args.checkpoint))
    registry, opponents = load_training_opponents(
        Path(args.registry), list(args.opponent)
    )
    schedule = build_seed_schedule(
        int(args.seed_start), int(args.seeds), list(args.opponent), opponents
    )

    ledger = SeedLedger(args.ledger)
    ledger.reserve_schedule(
        [
            {"seed": item.seed, "opponent_id": item.opponent_id}
            for item in schedule
        ],
        split="train",
        campaign_id=str(args.campaign),
        registry_sha256=str(registry["sha256"]),
    )
    ledger_sha_after_reservation = ledger.sha256()

    rows: list[dict[str, Any]] = []
    games: list[dict[str, Any]] = []
    canonical_counts: Counter[str] = Counter()
    status_pairs: Counter[str] = Counter()
    source_ids = {
        option_id: f"{checkpoint['model_id']}:option{option_id}"
        for option_id in FIXED_OPTIONS
    }

    for assignment in schedule:
        seed = int(assignment.seed)
        ledger.mark_exposed(
            seed,
            split="train",
            campaign_id=str(args.campaign),
            opponent_id=assignment.opponent_id,
        )
        member = opponents[assignment.opponent_id]
        for option_id in FIXED_OPTIONS:
            for seat in (0, 1):
                suffix = f"{seed}_{option_id}_{seat}_{assignment.opponent_id}"
                candidate = LatentRoleOptionPolicy(
                    Path(args.checkpoint).resolve(),
                    option_id,
                    worker_cap=WORKER_CAP,
                    cash_reserve=CASH_RESERVE,
                    terminal_buy_cutoff=TERMINAL_CUTOFF,
                )
                opponent = build_selected_opponent(
                    member, f"v114_v8_self_imitation_{suffix}"
                )
                env = make(
                    "kaggriculture", configuration={"seed": seed}, debug=False
                )
                env.reset(2)
                game_indices: list[int] = []
                error: str | None = None

                try:
                    while not env.done:
                        observations = agent_observations(env)
                        obs = observations[seat]
                        candidate_raw = call_opponent(
                            candidate, obs, env.configuration
                        )
                        candidate_canonical, diagnostics = canonical_action(
                            obs, candidate_raw
                        )
                        for key, value in diagnostics.items():
                            canonical_counts[key] += int(value)

                        step = int(
                            space.get(obs, "step", len(env.steps) - 1) or 0
                        )
                        unit_expert = int(
                            space.functional_unit_expert_label(
                                candidate_canonical, step
                            )
                        )
                        market_expert = int(
                            space.functional_market_expert_label(
                                candidate_canonical, step
                            )
                        )
                        row, _ = labelled_row(
                            obs, candidate_canonical, option_id, seed, seat
                        )
                        row.update({
                            "candidate_unit_tokens": np.asarray(
                                row["unit_tokens"]
                            ).copy(),
                            "candidate_unit_quantities": np.asarray(
                                row["unit_quantities"]
                            ).copy(),
                            "candidate_market_tokens": np.asarray(
                                row["market_tokens"]
                            ).copy(),
                            "candidate_market_quantities": np.asarray(
                                row["market_quantities"]
                            ).copy(),
                            "candidate_market_mask": np.asarray(
                                row["market_mask"]
                            ).copy(),
                        })
                        (
                            unit_roles, _, _, market_roles, stop_slots_added,
                        ) = _apply_v6_derived_contract(row)
                        canonical_counts["absorbing_stop_slots_added"] += int(
                            stop_slots_added
                        )
                        row.update({
                            # These legacy V6 field names carry the actual
                            # action source identity; no teacher was queried.
                            "teacher_id": source_ids[option_id],
                            "teacher_family": OPTION_FAMILIES[option_id],
                            "teacher_sha256": str(checkpoint["sha256"]),
                            "option_id": np.int8(option_id),
                            "unit_expert": np.int16(unit_expert),
                            "market_expert": np.int16(market_expert),
                            "unit_roles": unit_roles,
                            "market_roles": market_roles,
                            "terminal_flag": np.int8(step >= TERMINAL_STEP),
                            "episode_return": np.float32(0.0),
                            "candidate_reward": np.float32(0.0),
                            "margin": np.float32(0.0),
                            "result": "pending",
                            "source_kind": SOURCE_KIND,
                        })
                        row["episode"] = np.int64(
                            episode_group_id(seed, option_id)
                        )
                        rows.append(row)
                        game_indices.append(len(rows) - 1)

                        actions: list[Any] = [None, None]
                        # Execute the untouched candidate action.  The
                        # canonical copy above is a label only.
                        actions[seat] = candidate_raw
                        actions[1 - seat] = call_opponent(
                            opponent,
                            observations[1 - seat],
                            env.configuration,
                        )
                        env.step(actions)
                except Exception as exc:  # report then fail closed below
                    error = f"{type(exc).__name__}: {exc}"

                rewards = [float(state.reward or 0.0) for state in env.state]
                statuses = [str(state.status) for state in env.state]
                expected_rows = int(
                    space.get(env.configuration, "episodeSteps", 720)
                ) - 1
                if error is not None:
                    raise RuntimeError(
                        f"rollout failed seed={seed}, option={option_id}, seat={seat}: {error}"
                    )
                if statuses != ["DONE", "DONE"]:
                    raise RuntimeError(
                        f"incomplete rollout seed={seed}, option={option_id}, seat={seat}: {statuses}"
                    )
                if len(game_indices) != expected_rows:
                    raise RuntimeError(
                        f"non-contiguous rollout seed={seed}, option={option_id}, seat={seat}: "
                        f"{len(game_indices)} != {expected_rows}"
                    )
                if not np.all(np.isfinite(rewards)):
                    raise RuntimeError("terminal rewards must be finite")

                candidate_reward = rewards[seat]
                opponent_reward = rewards[1 - seat]
                margin = candidate_reward - opponent_reward
                result = result_name(margin)
                episode_return = terminal_value(margin)
                for index in game_indices:
                    rows[index]["value"] = np.float32(episode_return)
                    rows[index]["episode_return"] = np.float32(episode_return)
                    rows[index]["candidate_reward"] = np.float32(candidate_reward)
                    rows[index]["margin"] = np.float32(margin)
                    rows[index]["result"] = result

                status_pairs["/".join(statuses)] += 1
                game = {
                    "seed": seed,
                    "fresh_seed": True,
                    "option_id": option_id,
                    "seat": seat,
                    "opponent_id": assignment.opponent_id,
                    "opponent_layer": assignment.layer,
                    "opponent_sha256": assignment.opponent_sha256,
                    "rows": len(game_indices),
                    "statuses": statuses,
                    "error": None,
                    "candidate_reward": candidate_reward,
                    "opponent_reward": opponent_reward,
                    "margin": margin,
                    "result": result,
                    "episode_return": episode_return,
                    "catastrophe": candidate_reward < CATASTROPHE_REWARD,
                }
                games.append(game)
                print(json.dumps(game, ensure_ascii=False), flush=True)

    arrays = _rows_to_arrays(rows)
    checkpoint_sha_after_rollout = sha256_file(Path(args.checkpoint).resolve())
    if checkpoint_sha_after_rollout != checkpoint["sha256"]:
        raise RuntimeError("candidate checkpoint changed during rollout")
    report = {
        "schema": SCHEMA,
        "checkpoint": checkpoint,
        "registry": registry,
        "split": "train",
        "options": list(FIXED_OPTIONS),
        "candidate_safety": {
            "worker_cap": WORKER_CAP,
            "cash_reserve": CASH_RESERVE,
            "terminal_buy_cutoff": TERMINAL_CUTOFF,
        },
        "execution_contract": {
            "engine": "official kaggle_environments Kaggriculture",
            "environment_action_source": "frozen V6 candidate plus selected opponent",
            "training_label_source": "canonical encoding of candidate actual action",
            "teacher_policy_calls": 0,
            "teacher_labels": False,
            "candidate_action_copied_before_canonical_label_encoding": True,
            "candidate_reloaded_each_game": True,
            "candidate_checkpoint_unchanged_during_rollout": True,
            "candidate_checkpoint_sha256_after_rollout": checkpoint_sha_after_rollout,
            "opponent_reloaded_each_game": True,
            "dual_seat_same_seed_same_opponent": True,
            "historical_agent_fallback": False,
            "kaggle_submission": False,
        },
        "isolation_contract": {
            "training_opponents_only": True,
            "gold_dev_used": False,
            "gold_blind_used": False,
            "gold_dev_artifacts_accessed": False,
            "gold_blind_artifacts_accessed": False,
        },
        "fresh_seed_contract": {
            "campaign": str(args.campaign),
            "ledger": str(Path(args.ledger).resolve()),
            "ledger_sha256_after_reservation": ledger_sha_after_reservation,
            "ledger_sha256_after_exposure": ledger.sha256(),
            "reserved_seed_blocks": [item.seed for item in schedule],
            "seats_per_seed": [0, 1],
            "episode_group_id": "seed * 3 + option_id; both seats share one group",
        },
        "seed_start": int(args.seed_start),
        "seed_blocks": len(schedule),
        "games": len(games),
        "rows": len(rows),
        "opponent_schedule": [
            {
                "seed": item.seed,
                "opponent_id": item.opponent_id,
                "layer": item.layer,
                "opponent_sha256": item.opponent_sha256,
            }
            for item in schedule
        ],
        "opponent_seed_blocks_by_layer": dict(sorted(Counter(
            item.layer for item in schedule
        ).items())),
        "opponent_seed_blocks_by_id": dict(sorted(Counter(
            item.opponent_id for item in schedule
        ).items())),
        "candidate_summary": {
            "overall": _summary(games),
            "by_option": _grouped_summary(games, "option_id"),
            "by_opponent_layer": _grouped_summary(games, "opponent_layer"),
            "by_opponent": _grouped_summary(games, "opponent_id"),
        },
        "metric_contract": {
            "win": "candidate_reward > opponent_reward",
            "draw": "candidate_reward == opponent_reward",
            "loss": "candidate_reward < opponent_reward",
            "value_and_episode_return": (
                "sign(margin) + 0.05*tanh(margin/25000)"
            ),
            "catastrophe": f"candidate_reward < {CATASTROPHE_REWARD:g}",
            "p10": "linear 10th percentile of candidate_reward",
        },
        "canonicalization": {
            key: int(value) for key, value in sorted(canonical_counts.items())
        },
        "status_pair_counts": {
            key: int(value) for key, value in sorted(status_pairs.items())
        },
        "v6_compatibility": {
            "contains_all_v6_source_keys": V6_SOURCE_KEYS.issubset(arrays),
            "v6_source_keys": sorted(V6_SOURCE_KEYS),
            "additional_terminal_keys": sorted(EXTRA_KEYS),
            "legacy_teacher_fields_are_source_identity_only": True,
        },
        "array_schema": {
            key: {"shape": list(value.shape), "dtype": str(value.dtype)}
            for key, value in arrays.items()
        },
        "elapsed_seconds": time.time() - started,
        "game_rows": games,
    }
    return arrays, report


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--registry", type=Path, required=True)
    result.add_argument("--checkpoint", type=Path, required=True)
    result.add_argument("--seed-start", type=int, required=True)
    result.add_argument("--seeds", type=int, required=True)
    result.add_argument("--opponent", action="append", required=True)
    result.add_argument("--campaign", required=True)
    result.add_argument("--ledger", type=Path, required=True)
    result.add_argument("--output", type=Path, required=True)
    result.add_argument("--report", type=Path)
    return result


def main() -> None:
    argument_parser = parser()
    args = argument_parser.parse_args()
    if not args.registry.is_file():
        argument_parser.error(f"registry does not exist: {args.registry}")
    if not args.checkpoint.is_file():
        argument_parser.error(f"checkpoint does not exist: {args.checkpoint}")
    if args.output.suffix != ".npz":
        argument_parser.error("--output must use the .npz suffix")
    if args.report is None:
        args.report = args.output.with_suffix(".report.json")
    if args.output.resolve() == args.report.resolve():
        argument_parser.error("--output and --report must differ")

    arrays, report = collect(args)
    _atomic_npz(args.output, arrays)
    report = dict(report)
    report["dataset"] = str(args.output.resolve())
    report["dataset_sha256"] = sha256_file(args.output.resolve())
    report["report"] = str(args.report.resolve())
    _atomic_json(args.report, report)
    print(json.dumps({
        "dataset": report["dataset"],
        "report": report["report"],
        "rows": report["rows"],
        "games": report["games"],
        "candidate_summary": report["candidate_summary"],
    }, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
