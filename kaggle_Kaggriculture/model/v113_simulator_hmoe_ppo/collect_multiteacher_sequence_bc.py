"""Collect registry-backed, teacher-executed sequence BC trajectories.

Only ``gold_split=train`` agent members are eligible.  Seed-group quotas are
balanced across behavior families; members within a family share that quota.
Every seed is run from both seats against the same opponent, and every game
reloads the stateful teacher and opponent modules.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import tempfile
import time
from typing import Any, Mapping

from kaggle_environments import make
import numpy as np

import action_space as space
from collect_dagger import labelled_row
from collect_rollouts import agent_observations, call_opponent, resolve_opponent
from opponent_pool import LAYER_IDS, PoolAssignment, build_opponent, sha256_file


DATASET_NAME = "multiteacher_sequence_bc.npz"
REPORT_NAME = "multiteacher_sequence_bc_report.json"
STAGE_BOUNDS = (
    ("opening_0_71", 0, 72),
    ("router_72_215", 72, 216),
    ("production_216_359", 216, 360),
    ("market_360_670", 360, 671),
    ("terminal_671_718", 671, 719),
)


def stage_name(step: int) -> str:
    for name, start, stop in STAGE_BOUNDS:
        if start <= int(step) < stop:
            return name
    return "outside_expected_horizon"


def load_gold_train_teachers(registry_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Read and verify only train-split agent artifacts from the registry."""
    registry_path = registry_path.resolve()
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    if registry.get("schema") != "kaggriculture-v113-opponent-registry-v1":
        raise ValueError("unsupported opponent registry schema")
    base = (registry_path.parent / registry.get("path_base", ".")).resolve()
    selected: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for member_index, source in enumerate(registry.get("members", [])):
        if source.get("gold_split") != "train" or source.get("kind") != "agent":
            continue
        member = dict(source)
        member_id = str(member.get("id", ""))
        family = str(member.get("behavior_family", ""))
        if not member_id or member_id in seen_ids:
            raise ValueError(f"missing or duplicate Gold-Train teacher id: {member_id!r}")
        if not family:
            raise ValueError(f"Gold-Train teacher has no behavior_family: {member_id}")
        if not member.get("training_enabled") or member.get("training_layer") != "gold_train":
            raise ValueError(f"Gold-Train teacher is not enabled in gold_train: {member_id}")
        resolved = (base / str(member["path"])).resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f"missing Gold-Train teacher: {resolved}")
        actual_sha = sha256_file(resolved)
        if actual_sha != member.get("sha256"):
            raise ValueError(
                f"SHA256 mismatch for {member_id}: {actual_sha} != {member.get('sha256')}"
            )
        member["member_index"] = int(member_index)
        member["resolved_path"] = str(resolved)
        selected.append(member)
        seen_ids.add(member_id)
    if not selected:
        raise ValueError("registry contains no gold_split=train agent teachers")
    metadata = {
        "path": str(registry_path),
        "sha256": sha256_file(registry_path),
        "schema": registry["schema"],
    }
    return metadata, sorted(selected, key=lambda member: (member["behavior_family"], member["id"]))


def build_teacher_schedule(
    teachers: list[dict[str, Any]], seed_start: int, seeds_per_teacher: int,
    opponents: list[str],
) -> list[dict[str, Any]]:
    """Allocate an equal seed-group budget to each deduplicated family.

    ``seeds_per_teacher`` is the quota for one behavior-deduplicated teacher
    slot, i.e. one behavior family.  Multiple versions in the same family
    split that quota exactly; the quota must be divisible by the number of
    teachers in that family.
    """
    if seeds_per_teacher < 1:
        raise ValueError("seeds_per_teacher must be positive")
    if not opponents:
        raise ValueError("at least one opponent is required")
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for teacher in teachers:
        by_family[str(teacher["behavior_family"])].append(teacher)
    schedule: list[dict[str, Any]] = []
    next_seed = int(seed_start)
    for family in sorted(by_family):
        members = sorted(by_family[family], key=lambda member: member["id"])
        member_count = len(members)
        if seeds_per_teacher < member_count or seeds_per_teacher % member_count:
            raise ValueError(
                "--seeds-per-teacher is the per-family seed-group quota and must be "
                f"a positive multiple of {member_count} for family {family!r}"
            )
        for offset in range(seeds_per_teacher):
            member_offset = offset % member_count
            # This diagonal rotation avoids confounding one same-family member
            # with one opponent when both lists contain two entries.
            opponent_offset = (offset // member_count + member_offset) % len(opponents)
            schedule.append({
                "seed": next_seed,
                "teacher": members[member_offset],
                "family": family,
                "opponent": opponents[opponent_offset],
            })
            next_seed += 1
    return schedule


def canonical_action(obs: Mapping[str, Any], raw_action: Any) -> tuple[dict[str, Any], dict[str, int]]:
    expected_hands = space.unit_count(obs) - 1
    source = space.normalise_action(raw_action or {}, expected_hands)
    raw_encoded = space.encode_action(obs, source)
    canonical = space.decode_action(obs, raw_encoded)
    canonical_encoded = space.encode_action(obs, canonical)
    return canonical, {
        "raw_unit_unknown": int(np.sum(np.logical_not(
            np.asarray(raw_encoded["unit_known"], dtype=bool)
        ))),
        "raw_market_unknown": int(np.sum(np.logical_not(
            np.asarray(raw_encoded["market_known"], dtype=bool)
        ))),
        "canonical_unit_unknown": int(np.sum(np.logical_not(
            np.asarray(canonical_encoded["unit_known"], dtype=bool)
        ))),
        "canonical_market_unknown": int(np.sum(np.logical_not(
            np.asarray(canonical_encoded["market_known"], dtype=bool)
        ))),
        "changed": int(canonical != source),
    }


def _string_array(values: list[str]) -> np.ndarray:
    width = max(1, max((len(value) for value in values), default=1))
    return np.asarray(values, dtype=f"<U{width}")


def _atomic_npz(path: Path, arrays: dict[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".npz", dir=path.parent, delete=False) as sink:
        np.savez_compressed(sink, **arrays)
        temporary = Path(sink.name)
    temporary.replace(path)


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", dir=path.parent, delete=False, encoding="utf-8",
    ) as sink:
        json.dump(payload, sink, ensure_ascii=False, indent=2)
        sink.write("\n")
        temporary = Path(sink.name)
    temporary.replace(path)


def collect(args: argparse.Namespace) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    started = time.time()
    registry, teachers = load_gold_train_teachers(args.registry)
    schedule = build_teacher_schedule(
        teachers, args.seed_start, args.seeds_per_teacher, list(args.opponent),
    )
    rows: list[dict[str, Any]] = []
    games: list[dict[str, Any]] = []
    family_rows: Counter = Counter()
    teacher_rows: Counter = Counter()
    stage_rows: Counter = Counter()
    family_games: Counter = Counter()
    teacher_games: Counter = Counter()
    opponent_games: Counter = Counter()
    status_pairs: Counter = Counter()
    raw_to_canonical_changed = 0
    unknown_unit_tokens = 0
    unknown_market_tokens = 0
    canonical_unknown_unit_tokens = 0
    canonical_unknown_market_tokens = 0

    for assignment_index, assignment in enumerate(schedule):
        seed = int(assignment["seed"])
        teacher_member = assignment["teacher"]
        teacher_id = str(teacher_member["id"])
        teacher_family = str(assignment["family"])
        teacher_sha = str(teacher_member["sha256"])
        opponent_name = str(assignment["opponent"])
        pool_assignment = PoolAssignment(
            seed=seed,
            layer="gold_train",
            layer_id=LAYER_IDS["gold_train"],
            member_id=teacher_id,
            member_index=int(teacher_member["member_index"]),
            member=teacher_member,
        )
        for seat in (0, 1):
            suffix = f"{assignment_index}_{seed}_{seat}_{teacher_id}"
            # Both objects are reconstructed for every episode.  This is
            # required because all current gold teachers carry module state.
            teacher = build_opponent(pool_assignment, f"v113_multiteacher_{suffix}")
            opponent = resolve_opponent(
                opponent_name, f"v113_multiteacher_opponent_{suffix}",
            )
            env = make("kaggriculture", configuration={"seed": seed}, debug=False)
            env.reset(2)
            game_row_indices: list[int] = []
            game_changed = 0
            game_unknown_unit = 0
            game_unknown_market = 0
            while not env.done:
                observations = agent_observations(env)
                obs = observations[seat]
                raw_action = call_opponent(teacher, obs, env.configuration)
                canonical, diagnostics = canonical_action(obs, raw_action)
                step = int(space.get(obs, "step", len(env.steps) - 1) or 0)
                unit_expert = int(space.functional_unit_expert_label(canonical, step))
                market_expert = int(space.functional_market_expert_label(canonical, step))
                if not 0 <= unit_expert < 6 or not 0 <= market_expert < 6:
                    raise ValueError(
                        f"functional expert label out of range at seed={seed}, seat={seat}, step={step}"
                    )
                row, _ = labelled_row(obs, canonical, 0, seed, seat)
                row["teacher_id"] = teacher_id
                row["teacher_family"] = teacher_family
                row["teacher_sha256"] = teacher_sha
                row["unit_expert"] = np.int16(unit_expert)
                row["market_expert"] = np.int16(market_expert)
                rows.append(row)
                game_row_indices.append(len(rows) - 1)
                stage = stage_name(step)
                family_rows[teacher_family] += 1
                teacher_rows[teacher_id] += 1
                stage_rows[stage] += 1
                raw_to_canonical_changed += diagnostics["changed"]
                unknown_unit_tokens += diagnostics["raw_unit_unknown"]
                unknown_market_tokens += diagnostics["raw_market_unknown"]
                canonical_unknown_unit_tokens += diagnostics["canonical_unit_unknown"]
                canonical_unknown_market_tokens += diagnostics["canonical_market_unknown"]
                game_changed += diagnostics["changed"]
                game_unknown_unit += diagnostics["raw_unit_unknown"]
                game_unknown_market += diagnostics["raw_market_unknown"]

                actions = [None, None]
                # Execute the teacher's raw request, not the canonical label.
                # This keeps every recorded state on the teacher's own policy.
                actions[seat] = raw_action
                actions[1 - seat] = call_opponent(
                    opponent, observations[1 - seat], env.configuration,
                )
                env.step(actions)

            rewards = [float(state.reward or 0.0) for state in env.state]
            margin = rewards[seat] - rewards[1 - seat]
            value = (
                (1.0 if margin > 0 else (-1.0 if margin < 0 else 0.0))
                + 0.05 * np.tanh(margin / 25000.0)
            )
            for row_index in game_row_indices:
                rows[row_index]["value"] = np.float32(value)
            statuses = [str(state.status) for state in env.state]
            expected_rows = int(space.get(env.configuration, "episodeSteps", 720)) - 1
            if statuses != ["DONE", "DONE"]:
                raise RuntimeError(
                    f"incomplete teacher trajectory seed={seed}, seat={seat}: {statuses}"
                )
            if len(game_row_indices) != expected_rows:
                raise RuntimeError(
                    f"non-contiguous teacher trajectory seed={seed}, seat={seat}: "
                    f"{len(game_row_indices)} != {expected_rows}"
                )
            if not np.all(np.isfinite(rewards)):
                raise RuntimeError(f"non-finite terminal reward seed={seed}, seat={seat}")
            status_key = "/".join(statuses)
            status_pairs[status_key] += 1
            family_games[teacher_family] += 1
            teacher_games[teacher_id] += 1
            opponent_games[opponent_name] += 1
            games.append({
                "seed": seed,
                "seat": seat,
                "teacher_id": teacher_id,
                "teacher_family": teacher_family,
                "teacher_sha256": teacher_sha,
                "opponent": opponent_name,
                "teacher_reward": rewards[seat],
                "opponent_reward": rewards[1 - seat],
                "margin": margin,
                "statuses": statuses,
                "rows": len(game_row_indices),
                "raw_to_canonical_changed": game_changed,
                "unknown_unit_tokens": game_unknown_unit,
                "unknown_market_tokens": game_unknown_market,
            })

    if not rows:
        raise RuntimeError("no multi-teacher rows were collected")
    array_keys = [key for key in rows[0] if key not in {
        "teacher_id", "teacher_family", "teacher_sha256",
    }]
    arrays = {
        key: np.asarray([row[key] for row in rows])
        for key in array_keys
    }
    arrays["teacher_id"] = _string_array([str(row["teacher_id"]) for row in rows])
    arrays["teacher_family"] = _string_array([str(row["teacher_family"]) for row in rows])
    arrays["teacher_sha256"] = _string_array([str(row["teacher_sha256"]) for row in rows])
    for key in ("global", "board", "units"):
        arrays[key] = arrays[key].astype(np.float16)

    family_seed_groups = Counter(str(row["family"]) for row in schedule)
    teacher_seed_groups = Counter(str(row["teacher"]["id"]) for row in schedule)
    teacher_shas = {str(member["id"]): str(member["sha256"]) for member in teachers}
    done_done = int(status_pairs.get("DONE/DONE", 0))
    report = {
        "schema": "kaggriculture-v113-multiteacher-sequence-bc-v1",
        "registry": registry,
        "teacher_selection": "gold_split=train AND kind=agent",
        "sampling_contract": {
            "unit": "behavior_family",
            "family_seed_groups": int(args.seeds_per_teacher),
            "within_family": "round_robin_equal_share",
            "dual_seat_same_seed_and_opponent": True,
            "teacher_executed_closed_loop_only": True,
            "label_action": "normalise_then_encode_decode_canonical",
        },
        "seed_start": int(args.seed_start),
        "seed_groups": len(schedule),
        "games": len(games),
        "rows": len(rows),
        "opponents": list(args.opponent),
        "teacher_sha256": teacher_shas,
        "family_counts": {
            family: {
                "seed_groups": int(family_seed_groups[family]),
                "games": int(family_games[family]),
                "rows": int(family_rows[family]),
            }
            for family in sorted(family_seed_groups)
        },
        "teacher_counts": {
            teacher_id: {
                "seed_groups": int(teacher_seed_groups[teacher_id]),
                "games": int(teacher_games[teacher_id]),
                "rows": int(teacher_rows[teacher_id]),
            }
            for teacher_id in sorted(teacher_shas)
        },
        "stage_contract": [
            {"name": name, "start": start, "stop_exclusive": stop}
            for name, start, stop in STAGE_BOUNDS
        ],
        "stage_counts": {key: int(value) for key, value in sorted(stage_rows.items())},
        "opponent_game_counts": {
            key: int(value) for key, value in sorted(opponent_games.items())
        },
        "status_pair_counts": {
            key: int(value) for key, value in sorted(status_pairs.items())
        },
        "done_done_games": done_done,
        "done_done_rate": done_done / len(games),
        "raw_to_canonical_changed_steps": int(raw_to_canonical_changed),
        "raw_to_canonical_modification_rate": raw_to_canonical_changed / len(rows),
        "unknown_tokens": {
            "raw": {
                "unit": int(unknown_unit_tokens),
                "market": int(unknown_market_tokens),
                "total": int(unknown_unit_tokens + unknown_market_tokens),
            },
            "canonical": {
                "unit": int(canonical_unknown_unit_tokens),
                "market": int(canonical_unknown_market_tokens),
                "total": int(
                    canonical_unknown_unit_tokens + canonical_unknown_market_tokens
                ),
            },
        },
        "elapsed_seconds": time.time() - started,
        "game_rows": games,
    }
    return arrays, report


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--registry", type=Path, required=True)
    result.add_argument("--seed-start", type=int, required=True)
    result.add_argument(
        "--seeds-per-teacher", type=int, required=True,
        help=(
            "Seed-group quota per behavior-deduplicated teacher slot (behavior family); "
            "same-family versions split this quota evenly."
        ),
    )
    result.add_argument("--opponent", action="append", required=True)
    result.add_argument("--output-dir", type=Path, required=True)
    return result


def main() -> None:
    argument_parser = parser()
    args = argument_parser.parse_args()
    if args.seeds_per_teacher < 1:
        argument_parser.error("--seeds-per-teacher must be positive")
    arrays, report = collect(args)
    dataset_path = args.output_dir / DATASET_NAME
    report_path = args.output_dir / REPORT_NAME
    _atomic_npz(dataset_path, arrays)
    report = dict(report)
    report["dataset"] = str(dataset_path.resolve())
    report["report"] = str(report_path.resolve())
    _atomic_json(report_path, report)
    print(json.dumps({
        "dataset": str(dataset_path),
        "report": str(report_path),
        "rows": report["rows"],
        "games": report["games"],
        "done_done_rate": report["done_done_rate"],
        "raw_to_canonical_modification_rate": report["raw_to_canonical_modification_rate"],
        "unknown_tokens": report["unknown_tokens"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
