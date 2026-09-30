"""Collect reproducible Stage36 on-policy multi-teacher sequence DAgger data.

The timed sequence candidate controls the official Kaggriculture environment
with step-level routing.  One behavior-family-balanced Gold-Train teacher is
queried continuously on the candidate trajectory, but its action is only a
canonical supervision label and is never executed.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import copy
from pathlib import Path
import json
import time
from typing import Any, Mapping

from flax import serialization
from kaggle_environments import make
import numpy as np

import action_space as space
from audit_candidate_teacher_agreement import (
    STAGES,
    compare_actions,
    empty_metrics,
    finalise_metrics,
    stage_name,
    update_metrics,
)
from collect_dagger import labelled_row
from collect_multiteacher_sequence_bc import (
    _atomic_json,
    _atomic_npz,
    _string_array,
    build_teacher_schedule,
    canonical_action,
    load_gold_train_teachers,
)
from collect_rollouts import agent_observations, call_opponent, resolve_opponent
from opponent_pool import LAYER_IDS, PoolAssignment, build_opponent, sha256_file
from policy_sequence_action import TimedSequenceActionV113Policy


SCHEMA = "kaggriculture-v113-multiteacher-sequence-dagger-v1"
DATASET_NAME = "multiteacher_sequence_dagger.npz"
REPORT_NAME = "multiteacher_sequence_dagger_report.json"
EXPECTED_ARCHITECTURE = "timed-joint-autoregressive-action-hmoe-v1"
ROUTER_PERIOD = 1
COUNT_KEYS = (
    "unit_exact",
    "market_exact",
    "joint_exact",
    "functional_unit_label_agreement",
    "functional_market_label_agreement",
    "functional_joint_label_agreement",
)
DIAGNOSTIC_KEYS = (
    "raw_unit_unknown",
    "raw_market_unknown",
    "canonical_unit_unknown",
    "canonical_market_unknown",
    "changed",
)


def metric_block() -> dict[str, Any]:
    return {
        "overall": empty_metrics(),
        "stages": {name: empty_metrics() for name, _, _ in STAGES},
    }


def update_metric_block(
    target: dict[str, Any], stage: str, comparison: Mapping[str, bool],
) -> None:
    update_metrics(target["overall"], comparison)
    update_metrics(target["stages"][stage], comparison)


def finalise_metric_block(source: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "overall": finalise_metrics(source["overall"]),
        "stages": {
            name: finalise_metrics(source["stages"][name])
            for name, _, _ in STAGES
        },
    }


def add_diagnostics(target: Counter, diagnostics: Mapping[str, int]) -> None:
    for key in DIAGNOSTIC_KEYS:
        target[key] += int(diagnostics[key])


def finalise_diagnostics(source: Mapping[str, int]) -> dict[str, int]:
    raw_unit = int(source.get("raw_unit_unknown", 0))
    raw_market = int(source.get("raw_market_unknown", 0))
    canonical_unit = int(source.get("canonical_unit_unknown", 0))
    canonical_market = int(source.get("canonical_market_unknown", 0))
    return {
        "raw_unit": raw_unit,
        "raw_market": raw_market,
        "raw_total": raw_unit + raw_market,
        "canonical_unit": canonical_unit,
        "canonical_market": canonical_market,
        "canonical_total": canonical_unit + canonical_market,
        "canonical_modified_steps": int(source.get("changed", 0)),
    }


def checkpoint_metadata(checkpoint: Path) -> dict[str, Any]:
    checkpoint = checkpoint.resolve()
    if not checkpoint.is_file():
        raise FileNotFoundError(f"checkpoint does not exist: {checkpoint}")
    payload = serialization.msgpack_restore(checkpoint.read_bytes())
    if "params" not in payload:
        raise ValueError("checkpoint has no params payload")
    architecture = payload.get("architecture")
    if architecture != EXPECTED_ARCHITECTURE:
        raise ValueError(
            "Stage36 requires a timed sequence-action checkpoint: "
            f"{architecture!r} != {EXPECTED_ARCHITECTURE!r}"
        )
    return {
        "path": str(checkpoint),
        "sha256": sha256_file(checkpoint),
        "architecture": architecture,
        "model_id": payload.get("model_id"),
        "strategy_parent": payload.get("strategy_parent"),
        "policy_class": "TimedSequenceActionV113Policy",
        "router_period": ROUTER_PERIOD,
    }


def teacher_assignment(member: Mapping[str, Any], seed: int) -> PoolAssignment:
    return PoolAssignment(
        seed=int(seed),
        layer="gold_train",
        layer_id=LAYER_IDS["gold_train"],
        member_id=str(member["id"]),
        member_index=int(member["member_index"]),
        member=member,
    )


def result_name(margin: float) -> str:
    if margin > 0:
        return "win"
    if margin < 0:
        return "loss"
    return "draw"


def summarise_candidate(games: list[dict[str, Any]]) -> dict[str, Any]:
    wdl = Counter(str(game["result"]) for game in games)
    count = len(games)
    return {
        "games": count,
        "wdl": {
            "win": int(wdl["win"]),
            "draw": int(wdl["draw"]),
            "loss": int(wdl["loss"]),
        },
        "win_rate": wdl["win"] / count,
        "draw_rate": wdl["draw"] / count,
        "loss_rate": wdl["loss"] / count,
        "mean_reward": float(np.mean([game["candidate_reward"] for game in games])),
        "mean_opponent_reward": float(
            np.mean([game["opponent_reward"] for game in games])
        ),
        "mean_margin": float(np.mean([game["margin"] for game in games])),
    }


def collect(args: argparse.Namespace) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    started = time.time()
    checkpoint = checkpoint_metadata(args.checkpoint)
    registry, teachers = load_gold_train_teachers(args.registry)
    schedule = build_teacher_schedule(
        teachers,
        int(args.seed_start),
        int(args.seeds_per_family),
        list(args.opponent),
    )

    rows: list[dict[str, Any]] = []
    games: list[dict[str, Any]] = []
    family_rows: Counter = Counter()
    teacher_rows: Counter = Counter()
    family_games: Counter = Counter()
    teacher_games: Counter = Counter()
    opponent_games: Counter = Counter()
    status_pairs: Counter = Counter()
    global_agreement = metric_block()
    family_agreement: dict[str, dict[str, Any]] = defaultdict(metric_block)
    teacher_agreement: dict[str, dict[str, Any]] = defaultdict(metric_block)
    candidate_diagnostics: Counter = Counter()
    teacher_diagnostics: Counter = Counter()

    for assignment_index, assignment in enumerate(schedule):
        seed = int(assignment["seed"])
        teacher_member = assignment["teacher"]
        teacher_id = str(teacher_member["id"])
        teacher_family = str(assignment["family"])
        teacher_sha = str(teacher_member["sha256"])
        opponent_name = str(assignment["opponent"])

        for seat in (0, 1):
            suffix = f"{assignment_index}_{seed}_{seat}_{teacher_id}"
            # Candidate, teacher and opponent are all reconstructed for every
            # episode because every policy may carry module/recurrent state.
            candidate = TimedSequenceActionV113Policy(
                args.checkpoint.resolve(), router_period=ROUTER_PERIOD,
            )
            teacher = build_opponent(
                teacher_assignment(teacher_member, seed),
                f"v113_stage36_teacher_{suffix}",
            )
            opponent = resolve_opponent(
                opponent_name, f"v113_stage36_opponent_{suffix}",
            )
            env = make("kaggriculture", configuration={"seed": seed}, debug=False)
            env.reset(2)
            game_indices: list[int] = []
            game_agreement = metric_block()
            game_candidate_diagnostics: Counter = Counter()
            game_teacher_diagnostics: Counter = Counter()

            while not env.done:
                observations = agent_observations(env)
                obs = observations[seat]
                teacher_obs = copy.deepcopy(obs)
                step = int(space.get(obs, "step", len(env.steps) - 1) or 0)
                stage = stage_name(step)

                candidate_raw = call_opponent(candidate, obs, env.configuration)
                expected_hands = space.unit_count(teacher_obs) - 1
                candidate_action = space.normalise_action(
                    candidate_raw or {}, expected_hands,
                )
                _, candidate_diag = canonical_action(teacher_obs, candidate_raw)
                add_diagnostics(candidate_diagnostics, candidate_diag)
                add_diagnostics(game_candidate_diagnostics, candidate_diag)

                # This exact teacher instance advances once per candidate
                # state.  Its canonical action supervises the row but never
                # enters the official environment action list.
                teacher_raw = call_opponent(
                    teacher, copy.deepcopy(teacher_obs), env.configuration,
                )
                teacher_canonical, teacher_diag = canonical_action(
                    teacher_obs, teacher_raw,
                )
                add_diagnostics(teacher_diagnostics, teacher_diag)
                add_diagnostics(game_teacher_diagnostics, teacher_diag)
                comparison, _ = compare_actions(
                    teacher_obs, candidate_action, teacher_canonical, step,
                )
                update_metric_block(global_agreement, stage, comparison)
                update_metric_block(family_agreement[teacher_family], stage, comparison)
                update_metric_block(teacher_agreement[teacher_id], stage, comparison)
                update_metric_block(game_agreement, stage, comparison)

                unit_expert = int(
                    space.functional_unit_expert_label(teacher_canonical, step)
                )
                market_expert = int(
                    space.functional_market_expert_label(teacher_canonical, step)
                )
                if not 0 <= unit_expert < 6 or not 0 <= market_expert < 6:
                    raise ValueError(
                        "functional expert label out of range at "
                        f"seed={seed}, seat={seat}, step={step}"
                    )
                row, _ = labelled_row(
                    teacher_obs, teacher_canonical, 0, seed, seat,
                )
                row["teacher_id"] = teacher_id
                row["teacher_family"] = teacher_family
                row["teacher_sha256"] = teacher_sha
                row["unit_expert"] = np.int16(unit_expert)
                row["market_expert"] = np.int16(market_expert)
                rows.append(row)
                game_indices.append(len(rows) - 1)
                family_rows[teacher_family] += 1
                teacher_rows[teacher_id] += 1

                actions: list[Any] = [None, None]
                actions[seat] = candidate_raw
                actions[1 - seat] = call_opponent(
                    opponent, observations[1 - seat], env.configuration,
                )
                env.step(actions)

            rewards = [float(state.reward or 0.0) for state in env.state]
            statuses = [str(state.status) for state in env.state]
            expected_rows = int(space.get(env.configuration, "episodeSteps", 720)) - 1
            if statuses != ["DONE", "DONE"]:
                raise RuntimeError(
                    f"incomplete candidate trajectory seed={seed}, seat={seat}: {statuses}"
                )
            if len(game_indices) != expected_rows:
                raise RuntimeError(
                    f"non-contiguous candidate trajectory seed={seed}, seat={seat}: "
                    f"{len(game_indices)} != {expected_rows}"
                )
            if not np.all(np.isfinite(rewards)):
                raise RuntimeError(f"non-finite terminal reward seed={seed}, seat={seat}")

            margin = rewards[seat] - rewards[1 - seat]
            outcome = result_name(margin)
            value = (
                (1.0 if margin > 0 else (-1.0 if margin < 0 else 0.0))
                + 0.05 * np.tanh(margin / 25000.0)
            )
            for row_index in game_indices:
                rows[row_index]["value"] = np.float32(value)

            status_pairs["/".join(statuses)] += 1
            family_games[teacher_family] += 1
            teacher_games[teacher_id] += 1
            opponent_games[opponent_name] += 1
            game = {
                "seed": seed,
                "seat": seat,
                "teacher_id": teacher_id,
                "teacher_family": teacher_family,
                "teacher_sha256": teacher_sha,
                "opponent": opponent_name,
                "rows": len(game_indices),
                "statuses": statuses,
                "candidate_reward": rewards[seat],
                "opponent_reward": rewards[1 - seat],
                "margin": margin,
                "result": outcome,
                "agreement": finalise_metric_block(game_agreement),
                "unknown_tokens": {
                    "candidate": finalise_diagnostics(game_candidate_diagnostics),
                    "teacher": finalise_diagnostics(game_teacher_diagnostics),
                },
                "candidate_unit_expert_usage": dict(candidate.unit_expert_usage),
                "candidate_market_expert_usage": dict(candidate.market_expert_usage),
            }
            games.append(game)
            print(json.dumps({
                key: game[key] for key in (
                    "seed", "seat", "teacher_id", "teacher_family", "opponent",
                    "candidate_reward", "opponent_reward", "margin", "result", "statuses",
                )
            }, ensure_ascii=False), flush=True)

    if not rows or not games:
        raise RuntimeError("no Stage36 DAgger rows were collected")

    array_keys = [key for key in rows[0] if key not in {
        "teacher_id", "teacher_family", "teacher_sha256",
    }]
    arrays = {
        key: np.asarray([row[key] for row in rows])
        for key in array_keys
    }
    arrays["teacher_id"] = _string_array([str(row["teacher_id"]) for row in rows])
    arrays["teacher_family"] = _string_array(
        [str(row["teacher_family"]) for row in rows]
    )
    arrays["teacher_sha256"] = _string_array(
        [str(row["teacher_sha256"]) for row in rows]
    )
    for key in ("global", "board", "units"):
        arrays[key] = arrays[key].astype(np.float16)

    family_seed_groups = Counter(str(item["family"]) for item in schedule)
    teacher_seed_groups = Counter(str(item["teacher"]["id"]) for item in schedule)
    teacher_shas = {str(member["id"]): str(member["sha256"]) for member in teachers}
    done_done = int(status_pairs.get("DONE/DONE", 0))
    report = {
        "schema": SCHEMA,
        "checkpoint": checkpoint,
        "registry": registry,
        "teacher_selection": "gold_split=train AND kind=agent",
        "execution_contract": {
            "engine": "official kaggle_environments Kaggriculture",
            "candidate": "timed sequence checkpoint executes its own raw request",
            "router_period": ROUTER_PERIOD,
            "teacher_state": (
                "one assigned teacher instance is queried once per candidate step and "
                "advances continuously on the candidate observation sequence"
            ),
            "teacher_execution": "query only; canonical label is never executed",
            "episode_isolation": "candidate, teacher and opponent reloaded per episode",
            "dual_seat_same_seed_teacher_opponent": True,
            "label_action": "teacher normalise then encode/decode canonical",
        },
        "sampling_contract": {
            "unit": "behavior_family",
            "family_seed_groups": int(args.seeds_per_family),
            "within_family": "round_robin_equal_share",
            "opponent_rotation": "deterministic diagonal round robin",
        },
        "stage_contract": [
            {"name": name, "start": start, "stop_exclusive": stop}
            for name, start, stop in STAGES
        ],
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
        "opponent_game_counts": {
            name: int(count) for name, count in sorted(opponent_games.items())
        },
        "status_pair_counts": {
            name: int(count) for name, count in sorted(status_pairs.items())
        },
        "done_done_games": done_done,
        "done_done_rate": done_done / len(games),
        "candidate_summary": summarise_candidate(games),
        "agreement": {
            "overall": finalise_metric_block(global_agreement),
            "by_family": {
                family: finalise_metric_block(family_agreement[family])
                for family in sorted(family_seed_groups)
            },
            "by_teacher": {
                teacher_id: finalise_metric_block(teacher_agreement[teacher_id])
                for teacher_id in sorted(teacher_shas)
            },
        },
        "unknown_tokens": {
            "candidate": finalise_diagnostics(candidate_diagnostics),
            "teacher": finalise_diagnostics(teacher_diagnostics),
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
    result.add_argument(
        "--seeds-per-family", type=int, required=True,
        help=(
            "Seed-group quota per behavior family; the quota must be divisible "
            "by the number of members in every same-family group."
        ),
    )
    result.add_argument("--opponent", action="append", required=True)
    result.add_argument("--output-dir", type=Path, required=True)
    return result


def main() -> None:
    argument_parser = parser()
    args = argument_parser.parse_args()
    if args.seeds_per_family < 1:
        argument_parser.error("--seeds-per-family must be positive")
    if not args.registry.is_file():
        argument_parser.error(f"registry does not exist: {args.registry}")
    if not args.checkpoint.is_file():
        argument_parser.error(f"checkpoint does not exist: {args.checkpoint}")

    arrays, report = collect(args)
    dataset_path = args.output_dir / DATASET_NAME
    report_path = args.output_dir / REPORT_NAME
    _atomic_npz(dataset_path, arrays)
    report = dict(report)
    report["dataset"] = str(dataset_path.resolve())
    report["dataset_sha256"] = sha256_file(dataset_path.resolve())
    report["report"] = str(report_path.resolve())
    _atomic_json(report_path, report)
    print(json.dumps({
        "dataset": str(dataset_path.resolve()),
        "report": str(report_path.resolve()),
        "rows": report["rows"],
        "games": report["games"],
        "done_done_rate": report["done_done_rate"],
        "candidate_summary": report["candidate_summary"],
        "agreement": report["agreement"]["overall"],
        "unknown_tokens": report["unknown_tokens"],
    }, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
