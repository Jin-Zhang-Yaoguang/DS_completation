"""Collect V114 V6 candidate-state DAgger labels from Gold-Train teachers.

The frozen latent-role candidate, not the teacher, controls the official
environment.  On every state actually reached by the candidate, one fixed
Gold-Train teacher is queried for a canonical supervision action.  Teacher
actions are never inserted into ``env.step`` and there is no historical-agent
fallback.
"""

from __future__ import annotations

import argparse
from collections import Counter
import copy
from dataclasses import dataclass
from flax import serialization
import json
from pathlib import Path
import sys
import tempfile
import time
from typing import Any, Mapping, Sequence

from kaggle_environments import make
import numpy as np


HERE = Path(__file__).resolve().parent
V113 = HERE.parent / "v113_simulator_hmoe_ppo"
if str(V113) not in sys.path:
    sys.path.insert(0, str(V113))

import action_space as space  # noqa: E402
from build_latent_role_dataset import (  # noqa: E402
    TERMINAL_STEP,
    market_role,
    unit_role,
)
from collect_dagger import labelled_row  # noqa: E402
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
from opponent_pool import (  # noqa: E402
    LAYER_IDS,
    PoolAssignment,
    build_opponent,
    sha256_file,
)
from policy_latent_role_hmoe import LatentRoleOptionPolicy  # noqa: E402
from seed_ledger import SeedLedger  # noqa: E402


SCHEMA = "kaggriculture-v114-v6-candidate-state-dagger-v1"
REGISTRY_SCHEMA = "kaggriculture-v114-opponent-registry-v1"
FIXED_OPTIONS = (1, 2)
OPTION_FAMILIES = {
    1: "procurement-slot-ordering",
    2: "production-route-router",
}
OPTION_TEACHERS = {
    1: ("gold_v76_adjacent_buy",),
    2: ("gold_v19_route_hmoe", "gold_v21_top_meta"),
}
REQUIRED_TEACHER_IDS = frozenset(
    teacher_id
    for teacher_ids in OPTION_TEACHERS.values()
    for teacher_id in teacher_ids
)
WORKER_CAP = 4
CASH_RESERVE = 0.0
TERMINAL_CUTOFF = 671
CATASTROPHE_REWARD = 3000.0
V6_SOURCE_KEYS = frozenset({
    "global", "board", "units", "unit_mask", "unit_tokens",
    "unit_quantities", "market_tokens", "market_quantities", "market_mask",
    "expert", "value", "split", "episode", "step", "seat", "unit_expert",
    "market_expert", "teacher_id", "teacher_family", "teacher_sha256",
    "option_id", "unit_roles", "market_roles", "terminal_flag",
})


@dataclass(frozen=True)
class SeedAssignment:
    seed: int
    opponent_id: str


def result_name(margin: float) -> str:
    if margin > 0:
        return "win"
    if margin < 0:
        return "loss"
    return "draw"


def checkpoint_metadata(path: Path) -> dict[str, Any]:
    """Fail closed unless ``path`` is a frozen, fallback-free V114 V6 model."""

    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(f"candidate checkpoint does not exist: {path}")
    payload = serialization.msgpack_restore(path.read_bytes())
    model_id = str(payload.get("model_id", ""))
    if not model_id.startswith("v114_") or "latent_role" not in model_id:
        raise ValueError("candidate must be a V114 latent-role checkpoint")
    if payload.get("inherits_v113_checkpoint") is not False:
        raise ValueError("candidate may not inherit a V113 checkpoint")
    if payload.get("online_historical_agent_fallback") is not False:
        raise ValueError("candidate may not use historical-agent fallback")
    if payload.get("teacher_role_conditions_action_decoder") is not False:
        raise ValueError("candidate action decoder may not consume teacher roles")
    if "params" not in payload:
        raise ValueError("candidate checkpoint has no params")
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "model_id": model_id,
        "architecture": payload.get("architecture"),
        "dataset_sha256": payload.get("dataset_sha256"),
        "inherits_v113_checkpoint": False,
        "online_historical_agent_fallback": False,
        "teacher_role_conditions_action_decoder": False,
        "frozen": True,
    }


def load_required_gold_train_teachers(
    registry_path: Path,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Load only the three explicitly authorised Gold-Train agent artifacts."""

    registry_path = registry_path.resolve()
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    if registry.get("schema") != REGISTRY_SCHEMA:
        raise ValueError("unsupported V114 opponent registry schema")
    base = (registry_path.parent / registry.get("path_base", ".")).resolve()
    selected: dict[str, dict[str, Any]] = {}
    for member_index, source in enumerate(registry.get("members", [])):
        member_id = str(source.get("id", ""))
        if member_id not in REQUIRED_TEACHER_IDS:
            continue
        if member_id in selected:
            raise ValueError(f"duplicate required teacher id: {member_id}")
        if (
            source.get("kind") != "agent"
            or source.get("gold_split") != "train"
            or source.get("training_layer") != "gold_train"
            or source.get("training_enabled") is not True
        ):
            raise ValueError(f"required teacher is not enabled Gold-Train: {member_id}")
        resolved = (base / str(source.get("path", ""))).resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f"missing Gold-Train teacher: {resolved}")
        actual_sha = sha256_file(resolved)
        if actual_sha != source.get("sha256"):
            raise ValueError(
                f"SHA256 mismatch for {member_id}: {actual_sha} != {source.get('sha256')}"
            )
        member = dict(source)
        member["member_index"] = int(member_index)
        member["resolved_path"] = str(resolved)
        selected[member_id] = member
    missing = sorted(REQUIRED_TEACHER_IDS - set(selected))
    if missing:
        raise ValueError(f"registry is missing required Gold-Train teachers: {missing}")
    metadata = {
        "path": str(registry_path),
        "sha256": sha256_file(registry_path),
        "schema": REGISTRY_SCHEMA,
        "selected_gold_split": "train",
        "selected_teacher_ids": sorted(selected),
        "dev_blind_selected": False,
    }
    return metadata, selected


def teacher_id_for(option_id: int, seed: int) -> str:
    """Deterministic seed-balanced teacher assignment for fixed options 1/2."""

    if int(option_id) not in FIXED_OPTIONS:
        raise ValueError(f"option_id must be one of {FIXED_OPTIONS}")
    choices = OPTION_TEACHERS[int(option_id)]
    return choices[int(seed) % len(choices)]


def episode_group_id(seed: int, option_id: int) -> int:
    """Keep both seats together without mixing different option teachers."""

    if int(seed) < 0 or int(option_id) not in FIXED_OPTIONS:
        raise ValueError("episode group requires a non-negative seed and fixed option")
    return int(seed) * 3 + int(option_id)


def build_seed_schedule(
    seed_start: int, seeds: int, opponents: Sequence[str],
) -> list[SeedAssignment]:
    if seeds <= 0:
        raise ValueError("seeds must be positive")
    if seed_start < 0:
        raise ValueError("seed_start must be non-negative")
    if not opponents or any(not str(value) for value in opponents):
        raise ValueError("at least one non-empty opponent is required")
    return [
        SeedAssignment(
            seed=seed,
            opponent_id=str(opponents[(seed - int(seed_start)) % len(opponents)]),
        )
        for seed in range(int(seed_start), int(seed_start) + int(seeds))
    ]


def _teacher_assignment(member: Mapping[str, Any], seed: int) -> PoolAssignment:
    return PoolAssignment(
        seed=int(seed),
        layer="gold_train",
        layer_id=LAYER_IDS["gold_train"],
        member_id=str(member["id"]),
        member_index=int(member["member_index"]),
        member=member,
    )


def _apply_v6_derived_contract(
    row: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]:
    """Derive unit roles and make the first market STOP absorbing."""

    unit_tokens = np.asarray(row["unit_tokens"])
    unit_mask = np.asarray(row["unit_mask"])
    unit_roles = np.vectorize(unit_role, otypes=[np.int8])(unit_tokens)
    unit_roles[unit_mask == 0] = 0
    market_tokens = np.asarray(row["market_tokens"]).copy()
    market_quantities = np.asarray(row["market_quantities"]).copy()
    market_mask = np.asarray(row["market_mask"]).copy()
    market_roles = np.vectorize(market_role, otypes=[np.int8])(market_tokens)
    market_roles[market_mask == 0] = 0
    stop_token = int(space.MARKET_INDEX["STOP"])
    active_stops = np.flatnonzero(
        (market_mask != 0) & (market_tokens == stop_token)
    )
    if active_stops.size == 0:
        if not np.all(market_mask != 0):
            raise ValueError(
                "teacher market label has no active STOP and is not a full sequence"
            )
        return (
            unit_roles.astype(np.int8), market_tokens, market_quantities,
            market_roles.astype(np.int8), 0,
        )
    first_stop = int(active_stops[0])
    if np.any(market_mask[first_stop + 1:] != 0):
        raise ValueError("teacher market label contains active actions after STOP")
    added = int(np.count_nonzero(market_mask[first_stop + 1:] == 0))
    tail = slice(first_stop, len(market_tokens))
    market_tokens[tail] = stop_token
    market_quantities[tail] = 0
    market_mask[tail] = 1
    market_roles[tail] = 0
    row["market_tokens"] = market_tokens
    row["market_quantities"] = market_quantities
    row["market_mask"] = market_mask
    return (
        unit_roles.astype(np.int8), market_tokens, market_quantities,
        market_roles.astype(np.int8), added,
    )


def _candidate_summary(games: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not games:
        return {
            "games": 0,
            "wdl": {"wins": 0, "draws": 0, "losses": 0},
            "score_rate": 0.0,
            "mean_reward": 0.0,
            "mean_margin": 0.0,
            "catastrophe_games": 0,
            "catastrophe_rate": 0.0,
        }
    counts = Counter(str(game["result"]) for game in games)
    catastrophes = sum(bool(game["catastrophe"]) for game in games)
    scores = {"win": 1.0, "draw": 0.5, "loss": 0.0}
    return {
        "games": len(games),
        "wdl": {
            "wins": int(counts["win"]),
            "draws": int(counts["draw"]),
            "losses": int(counts["loss"]),
        },
        "score_rate": float(np.mean([scores[str(game["result"])] for game in games])),
        "mean_reward": float(np.mean([float(game["candidate_reward"]) for game in games])),
        "mean_margin": float(np.mean([float(game["margin"]) for game in games])),
        "catastrophe_games": int(catastrophes),
        "catastrophe_rate": catastrophes / len(games),
    }


def _rows_to_arrays(rows: list[dict[str, Any]]) -> dict[str, np.ndarray]:
    if not rows:
        raise RuntimeError("no candidate-state DAgger rows were collected")
    keys = list(rows[0])
    if any(set(row) != set(keys) for row in rows):
        raise RuntimeError("DAgger rows do not share one array schema")
    if set(keys) != set(V6_SOURCE_KEYS):
        raise RuntimeError(
            "V6 DAgger row schema mismatch: "
            f"found={sorted(keys)}, expected={sorted(V6_SOURCE_KEYS)}"
        )
    string_keys = {"teacher_id", "teacher_family", "teacher_sha256"}
    arrays: dict[str, np.ndarray] = {}
    for key in keys:
        values = [row[key] for row in rows]
        arrays[key] = _string_array([str(value) for value in values]) if key in string_keys else np.asarray(values)
    for key in ("global", "board", "units"):
        arrays[key] = arrays[key].astype(np.float16)
    if any(array.dtype == object for array in arrays.values()):
        raise TypeError("object arrays are forbidden in the V6 DAgger dataset")
    return arrays


def collect(args: argparse.Namespace) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    started = time.time()
    checkpoint = checkpoint_metadata(args.checkpoint)
    registry, teachers = load_required_gold_train_teachers(args.registry)
    schedule = build_seed_schedule(args.seed_start, args.seeds, list(args.opponent))

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
    teacher_game_counts: Counter[str] = Counter()
    teacher_row_counts: Counter[str] = Counter()
    option_game_counts: Counter[int] = Counter()
    status_pairs: Counter[str] = Counter()
    unknown_teacher_unit = 0
    unknown_teacher_market = 0
    canonical_unknown_teacher_unit = 0
    canonical_unknown_teacher_market = 0
    canonical_changed = 0
    absorbing_stop_slots_added = 0

    for assignment in schedule:
        seed = int(assignment.seed)
        # Mark immediately before disclosure.  A crash after this point must
        # never make the seed appear fresh again.
        ledger.mark_exposed(
            seed,
            split="train",
            campaign_id=str(args.campaign),
            opponent_id=assignment.opponent_id,
        )
        for option_id in FIXED_OPTIONS:
            teacher_id = teacher_id_for(option_id, seed)
            teacher_member = teachers[teacher_id]
            teacher_family = OPTION_FAMILIES[option_id]
            teacher_sha = str(teacher_member["sha256"])

            for seat in (0, 1):
                suffix = f"{seed}_{option_id}_{seat}_{teacher_id}"
                candidate = LatentRoleOptionPolicy(
                    args.checkpoint.resolve(),
                    option_id,
                    worker_cap=WORKER_CAP,
                    cash_reserve=CASH_RESERVE,
                    terminal_buy_cutoff=TERMINAL_CUTOFF,
                )
                teacher = build_opponent(
                    _teacher_assignment(teacher_member, seed),
                    f"v114_v6_dagger_teacher_{suffix}",
                )
                opponent = resolve_opponent(
                    assignment.opponent_id,
                    f"v114_v6_dagger_opponent_{suffix}",
                )
                env = make(
                    "kaggriculture", configuration={"seed": seed}, debug=False
                )
                env.reset(2)
                game_indices: list[int] = []

                while not env.done:
                    observations = agent_observations(env)
                    candidate_obs = observations[seat]
                    candidate_raw = call_opponent(
                        candidate, candidate_obs, env.configuration
                    )

                    # The teacher sees exactly the candidate-reached state.
                    # Its output is copied, canonicalised and encoded only as
                    # a label; it is deliberately absent from actions below.
                    teacher_raw = call_opponent(
                        teacher, copy.deepcopy(candidate_obs), env.configuration
                    )
                    teacher_canonical, diagnostics = canonical_action(
                        candidate_obs, teacher_raw
                    )
                    unknown_teacher_unit += int(diagnostics["raw_unit_unknown"])
                    unknown_teacher_market += int(diagnostics["raw_market_unknown"])
                    canonical_unknown_teacher_unit += int(
                        diagnostics["canonical_unit_unknown"]
                    )
                    canonical_unknown_teacher_market += int(
                        diagnostics["canonical_market_unknown"]
                    )
                    canonical_changed += int(diagnostics["changed"])

                    step = int(space.get(candidate_obs, "step", len(env.steps) - 1) or 0)
                    unit_expert = int(
                        space.functional_unit_expert_label(teacher_canonical, step)
                    )
                    market_expert = int(
                        space.functional_market_expert_label(teacher_canonical, step)
                    )
                    row, _ = labelled_row(
                        candidate_obs, teacher_canonical, 0, seed, seat
                    )
                    (
                        unit_roles, _, _, market_roles, stop_slots_added,
                    ) = _apply_v6_derived_contract(row)
                    absorbing_stop_slots_added += stop_slots_added
                    row.update({
                        "teacher_id": teacher_id,
                        "teacher_family": teacher_family,
                        "teacher_sha256": teacher_sha,
                        "option_id": np.int8(option_id),
                        "unit_expert": np.int16(unit_expert),
                        "market_expert": np.int16(market_expert),
                        "unit_roles": unit_roles,
                        "market_roles": market_roles,
                        "terminal_flag": np.int8(step >= TERMINAL_STEP),
                    })
                    row["episode"] = np.int64(episode_group_id(seed, option_id))
                    rows.append(row)
                    game_indices.append(len(rows) - 1)
                    teacher_row_counts[teacher_id] += 1

                    actions: list[Any] = [None, None]
                    actions[seat] = candidate_raw
                    actions[1 - seat] = call_opponent(
                        opponent, observations[1 - seat], env.configuration
                    )
                    env.step(actions)

                rewards = [float(state.reward or 0.0) for state in env.state]
                statuses = [str(state.status) for state in env.state]
                expected_rows = int(
                    space.get(env.configuration, "episodeSteps", 720)
                ) - 1
                if statuses != ["DONE", "DONE"]:
                    raise RuntimeError(
                        f"incomplete candidate trajectory seed={seed}, option={option_id}, "
                        f"seat={seat}: {statuses}"
                    )
                if len(game_indices) != expected_rows:
                    raise RuntimeError(
                        f"non-contiguous candidate trajectory seed={seed}, option={option_id}, "
                        f"seat={seat}: {len(game_indices)} != {expected_rows}"
                    )
                if not np.all(np.isfinite(rewards)):
                    raise RuntimeError(
                        f"non-finite terminal reward seed={seed}, option={option_id}, seat={seat}"
                    )

                margin = rewards[seat] - rewards[1 - seat]
                result = result_name(margin)
                catastrophe = rewards[seat] < CATASTROPHE_REWARD
                value = (
                    (1.0 if margin > 0 else (-1.0 if margin < 0 else 0.0))
                    + 0.05 * np.tanh(margin / 25000.0)
                )
                for row_index in game_indices:
                    rows[row_index]["value"] = np.float32(value)

                status_pairs["/".join(statuses)] += 1
                teacher_game_counts[teacher_id] += 1
                option_game_counts[option_id] += 1
                game = {
                    "seed": seed,
                    "fresh_seed": True,
                    "option_id": option_id,
                    "seat": seat,
                    "opponent_id": assignment.opponent_id,
                    "teacher_id": teacher_id,
                    "teacher_family": teacher_family,
                    "teacher_registry_family": str(
                        teacher_member.get("behavior_family", "")
                    ),
                    "teacher_sha256": teacher_sha,
                    "rows": len(game_indices),
                    "statuses": statuses,
                    "candidate_reward": rewards[seat],
                    "opponent_reward": rewards[1 - seat],
                    "margin": margin,
                    "result": result,
                    "catastrophe": catastrophe,
                }
                games.append(game)
                print(json.dumps(game, ensure_ascii=False), flush=True)

    arrays = _rows_to_arrays(rows)
    ledger_sha_after_exposure = ledger.sha256()
    by_option = {
        str(option_id): _candidate_summary(
            [game for game in games if int(game["option_id"]) == option_id]
        )
        for option_id in FIXED_OPTIONS
    }
    teacher_shas = {
        teacher_id: str(teachers[teacher_id]["sha256"])
        for teacher_id in sorted(REQUIRED_TEACHER_IDS)
    }
    report = {
        "schema": SCHEMA,
        "checkpoint": checkpoint,
        "registry": registry,
        "split": "train",
        "options": list(FIXED_OPTIONS),
        "option_teacher_contract": {
            "1": {
                "family": OPTION_FAMILIES[1],
                "teacher_ids": list(OPTION_TEACHERS[1]),
                "assignment": "fixed",
            },
            "2": {
                "family": OPTION_FAMILIES[2],
                "teacher_ids": list(OPTION_TEACHERS[2]),
                "assignment": "seed modulo 2; balanced to +/-1 over consecutive seed blocks",
            },
        },
        "teacher_sha256": teacher_shas,
        "candidate_safety": {
            "worker_cap": WORKER_CAP,
            "cash_reserve": CASH_RESERVE,
            "terminal_buy_cutoff": TERMINAL_CUTOFF,
        },
        "execution_contract": {
            "engine": "official kaggle_environments Kaggriculture",
            "state_distribution": "candidate reached states only",
            "environment_action_source": "frozen latent-role candidate plus scheduled opponent",
            "teacher_execution": "never; canonical supervision query only",
            "candidate_reloaded_each_game": True,
            "teacher_reloaded_each_game": True,
            "opponent_reloaded_each_game": True,
            "historical_agent_fallback": False,
            "dual_seat_same_seed_same_opponent": True,
            "same_teacher_within_option_seed_dual_seat": True,
            "kaggle_submission": False,
        },
        "isolation_contract": {
            "selected_gold_split": "train",
            "gold_dev_used": False,
            "gold_blind_used": False,
            "selection_is_exact_allowlist": sorted(REQUIRED_TEACHER_IDS),
        },
        "fresh_seed_contract": {
            "campaign": str(args.campaign),
            "ledger": str(args.ledger.resolve()),
            "ledger_sha256_after_reservation": ledger_sha_after_reservation,
            "ledger_sha256_after_exposure": ledger_sha_after_exposure,
            "reserved_seed_blocks": [item.seed for item in schedule],
            "all_rows_marked_fresh_at_reservation": True,
            "seats_per_seed": [0, 1],
            "episode_group_id": "seed * 3 + option_id; both seats share one group",
        },
        "seed_start": int(args.seed_start),
        "seed_blocks": len(schedule),
        "games": len(games),
        "rows": len(rows),
        "opponents": list(args.opponent),
        "teacher_game_counts": {
            key: int(value) for key, value in sorted(teacher_game_counts.items())
        },
        "teacher_row_counts": {
            key: int(value) for key, value in sorted(teacher_row_counts.items())
        },
        "option_game_counts": {
            str(key): int(value) for key, value in sorted(option_game_counts.items())
        },
        "status_pair_counts": {
            key: int(value) for key, value in sorted(status_pairs.items())
        },
        "done_done_games": int(status_pairs["DONE/DONE"]),
        "candidate_summary": {
            "overall": _candidate_summary(games),
            "by_option": by_option,
        },
        "metric_contract": {
            "win": "candidate reward > opponent reward",
            "draw": "candidate reward == opponent reward",
            "loss": "candidate reward < opponent reward",
            "catastrophe": f"candidate reward < {CATASTROPHE_REWARD:g}",
        },
        "teacher_canonicalization": {
            "raw_unit_unknown": int(unknown_teacher_unit),
            "raw_market_unknown": int(unknown_teacher_market),
            "canonical_unit_unknown": int(canonical_unknown_teacher_unit),
            "canonical_market_unknown": int(canonical_unknown_teacher_market),
            "modified_steps": int(canonical_changed),
            "absorbing_stop_slots_added": int(absorbing_stop_slots_added),
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
        "teacher_game_counts": report["teacher_game_counts"],
    }, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
