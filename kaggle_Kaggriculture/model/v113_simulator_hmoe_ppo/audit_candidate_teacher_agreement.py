"""Audit Stage35 candidate actions against Gold-Train teachers on-policy.

The timed sequence candidate controls the official Kaggriculture environment.
At every candidate state, one independently stateful representative from each
Gold-Train behavior family is queried, but its action is never executed.  The
teacher therefore follows the candidate observation sequence while preserving
its own recurrent/module state across the episode.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import tempfile
import time
from typing import Any, Mapping

from kaggle_environments import make
import numpy as np

import action_space as space
from audit_multiteacher_canonical_parity import select_family_representatives
from collect_multiteacher_sequence_bc import canonical_action, load_gold_train_teachers
from collect_rollouts import agent_observations, call_opponent, resolve_opponent
from opponent_pool import LAYER_IDS, PoolAssignment, build_opponent, sha256_file
from policy_sequence_action import TimedSequenceActionV113Policy


SCHEMA = "kaggriculture-v113-candidate-teacher-agreement-v1"
STAGES = (
    ("0-30", 0, 31),
    ("31-71", 31, 72),
    ("72-215", 72, 216),
    ("216-359", 216, 360),
    ("360-670", 360, 671),
    ("671-718", 671, 719),
)
COUNT_KEYS = (
    "unit_exact",
    "market_exact",
    "joint_exact",
    "functional_unit_label_agreement",
    "functional_market_label_agreement",
    "functional_joint_label_agreement",
)


def stage_name(step: int) -> str:
    for name, start, stop in STAGES:
        if start <= int(step) < stop:
            return name
    raise ValueError(f"step outside the official 0..718 action horizon: {step}")


def empty_metrics() -> dict[str, int]:
    return {"steps": 0, **{key: 0 for key in COUNT_KEYS}}


def update_metrics(target: dict[str, int], comparison: Mapping[str, bool]) -> None:
    target["steps"] += 1
    for key in COUNT_KEYS:
        target[key] += int(bool(comparison[key]))


def finalise_metrics(source: Mapping[str, int]) -> dict[str, Any]:
    steps = int(source["steps"])
    result: dict[str, Any] = {"steps": steps}
    for key in COUNT_KEYS:
        count = int(source[key])
        result[f"{key}_count"] = count
        result[f"{key}_rate"] = count / steps if steps else None
    return result


def encoded_action(obs: Mapping[str, Any], action: Mapping[str, Any]) -> dict[str, np.ndarray]:
    encoded = space.encode_action(obs, action)
    return {
        "unit_tokens": np.asarray(encoded["unit_tokens"], dtype=np.int16),
        "unit_quantities": np.asarray(encoded["unit_quantities"], dtype=np.int16),
        "unit_known": np.asarray(encoded["unit_known"], dtype=bool),
        "market_tokens": np.asarray(encoded["market_tokens"], dtype=np.int16),
        "market_quantities": np.asarray(encoded["market_quantities"], dtype=np.int16),
        "market_known": np.asarray(encoded["market_known"], dtype=bool),
    }


def compare_actions(
    obs: Mapping[str, Any], candidate_action: Mapping[str, Any],
    teacher_action: Mapping[str, Any], step: int,
) -> tuple[dict[str, bool], dict[str, Any]]:
    candidate_encoded = encoded_action(obs, candidate_action)
    teacher_encoded = encoded_action(obs, teacher_action)
    unit_exact = bool(
        np.array_equal(candidate_encoded["unit_tokens"], teacher_encoded["unit_tokens"])
        and np.array_equal(
            candidate_encoded["unit_quantities"], teacher_encoded["unit_quantities"]
        )
        and np.array_equal(candidate_encoded["unit_known"], teacher_encoded["unit_known"])
    )
    market_exact = bool(
        np.array_equal(candidate_encoded["market_tokens"], teacher_encoded["market_tokens"])
        and np.array_equal(
            candidate_encoded["market_quantities"], teacher_encoded["market_quantities"]
        )
        and np.array_equal(candidate_encoded["market_known"], teacher_encoded["market_known"])
    )
    candidate_unit_label = int(space.functional_unit_expert_label(candidate_action, step))
    teacher_unit_label = int(space.functional_unit_expert_label(teacher_action, step))
    candidate_market_label = int(space.functional_market_expert_label(candidate_action, step))
    teacher_market_label = int(space.functional_market_expert_label(teacher_action, step))
    comparison = {
        "unit_exact": unit_exact,
        "market_exact": market_exact,
        "joint_exact": unit_exact and market_exact,
        "functional_unit_label_agreement": candidate_unit_label == teacher_unit_label,
        "functional_market_label_agreement": candidate_market_label == teacher_market_label,
        "functional_joint_label_agreement": (
            candidate_unit_label == teacher_unit_label
            and candidate_market_label == teacher_market_label
        ),
    }
    detail = {
        "candidate_unit_label": candidate_unit_label,
        "teacher_unit_label": teacher_unit_label,
        "candidate_market_label": candidate_market_label,
        "teacher_market_label": teacher_market_label,
        "candidate_encoded": {
            key: value.astype(int).tolist() for key, value in candidate_encoded.items()
        },
        "teacher_encoded": {
            key: value.astype(int).tolist() for key, value in teacher_encoded.items()
        },
        "candidate_action": candidate_action,
        "teacher_canonical_action": teacher_action,
    }
    return comparison, detail


def teacher_assignment(member: Mapping[str, Any], seed: int) -> PoolAssignment:
    return PoolAssignment(
        seed=int(seed),
        layer="gold_train",
        layer_id=LAYER_IDS["gold_train"],
        member_id=str(member["id"]),
        member_index=int(member["member_index"]),
        member=member,
    )


def fresh_teachers(
    representatives: list[dict[str, Any]], seed: int, seat: int,
) -> dict[str, Any]:
    teachers: dict[str, Any] = {}
    for member in representatives:
        teacher_id = str(member["id"])
        name = f"v113_agreement_teacher_{seed}_{seat}_{teacher_id}"
        teachers[teacher_id] = build_opponent(
            teacher_assignment(member, seed), name,
        )
    return teachers


def game_metrics_template(representatives: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        str(member["id"]): {
            "behavior_family": str(member["behavior_family"]),
            "teacher_sha256": str(member["sha256"]),
            "overall": empty_metrics(),
            "stages": {name: empty_metrics() for name, _, _ in STAGES},
            "first_joint_divergence": None,
            "first_joint_divergence_by_stage": {
                name: None for name, _, _ in STAGES
            },
            "unknown_tokens": {
                "raw_unit": 0,
                "raw_market": 0,
                "canonical_unit": 0,
                "canonical_market": 0,
            },
        }
        for member in representatives
    }


def current_rewards_and_statuses(env: Any) -> tuple[list[float], list[str]]:
    rewards = [float(state.reward if state.reward is not None else 0.0) for state in env.state]
    statuses = [str(state.status) for state in env.state]
    return rewards, statuses


def audit_game(
    checkpoint: Path, registry_teachers: list[dict[str, Any]], opponent_name: str,
    seed: int, seat: int, router_period: int, max_steps: int | None,
) -> dict[str, Any]:
    suffix = f"{seed}_{seat}"
    # All stateful actors are reconstructed for every episode.  Teachers are
    # distinct objects and are never inserted into the official action list.
    candidate = TimedSequenceActionV113Policy(
        checkpoint, router_period=router_period,
    )
    teachers = fresh_teachers(registry_teachers, seed, seat)
    opponent = resolve_opponent(opponent_name, f"v113_agreement_opponent_{suffix}")
    env = make("kaggriculture", configuration={"seed": int(seed)}, debug=False)
    env.reset(2)
    episode_steps = int(space.get(env.configuration, "episodeSteps", 720)) - 1
    step_limit = episode_steps if max_steps is None else min(int(max_steps), episode_steps)
    teacher_metrics = game_metrics_template(registry_teachers)
    candidate_unknown = {
        "unit": 0,
        "market": 0,
        "canonical_unit": 0,
        "canonical_market": 0,
        "canonical_modified_steps": 0,
    }
    steps_executed = 0
    error: str | None = None

    try:
        while not env.done and steps_executed < step_limit:
            observations = agent_observations(env)
            candidate_obs = observations[seat]
            step = int(space.get(candidate_obs, "step", steps_executed) or 0)
            stage = stage_name(step)
            # Preserve a pristine copy for every shadow teacher.  A teacher is
            # queried once per candidate step so its own state advances along
            # this exact candidate observation sequence.
            teacher_obs = copy.deepcopy(candidate_obs)
            candidate_raw = call_opponent(candidate, candidate_obs, env.configuration)
            expected_hands = space.unit_count(teacher_obs) - 1
            candidate_action = space.normalise_action(candidate_raw or {}, expected_hands)
            _, candidate_diagnostics = canonical_action(teacher_obs, candidate_raw)
            candidate_unknown["unit"] += int(candidate_diagnostics["raw_unit_unknown"])
            candidate_unknown["market"] += int(candidate_diagnostics["raw_market_unknown"])
            candidate_unknown["canonical_unit"] += int(
                candidate_diagnostics["canonical_unit_unknown"]
            )
            candidate_unknown["canonical_market"] += int(
                candidate_diagnostics["canonical_market_unknown"]
            )
            candidate_unknown["canonical_modified_steps"] += int(
                candidate_diagnostics["changed"]
            )

            for member in registry_teachers:
                teacher_id = str(member["id"])
                teacher_raw = call_opponent(
                    teachers[teacher_id], copy.deepcopy(teacher_obs), env.configuration,
                )
                teacher_canonical, diagnostics = canonical_action(teacher_obs, teacher_raw)
                comparison, detail = compare_actions(
                    teacher_obs, candidate_action, teacher_canonical, step,
                )
                record = teacher_metrics[teacher_id]
                update_metrics(record["overall"], comparison)
                update_metrics(record["stages"][stage], comparison)
                record["unknown_tokens"]["raw_unit"] += int(
                    diagnostics["raw_unit_unknown"]
                )
                record["unknown_tokens"]["raw_market"] += int(
                    diagnostics["raw_market_unknown"]
                )
                record["unknown_tokens"]["canonical_unit"] += int(
                    diagnostics["canonical_unit_unknown"]
                )
                record["unknown_tokens"]["canonical_market"] += int(
                    diagnostics["canonical_market_unknown"]
                )
                if not comparison["joint_exact"] and record["first_joint_divergence"] is None:
                    record["first_joint_divergence"] = {
                        "step": step,
                        "stage": stage,
                        **comparison,
                        **detail,
                    }
                if (
                    not comparison["joint_exact"]
                    and record["first_joint_divergence_by_stage"][stage] is None
                ):
                    record["first_joint_divergence_by_stage"][stage] = {
                        "step": step,
                        "stage": stage,
                        **comparison,
                        **detail,
                    }

            actions: list[Any] = [None, None]
            # Execute the candidate request exactly as returned.  Teacher
            # canonical actions above are diagnostics only.
            actions[seat] = candidate_raw
            actions[1 - seat] = call_opponent(
                opponent, observations[1 - seat], env.configuration,
            )
            env.step(actions)
            steps_executed += 1
    except Exception as exc:  # Preserve partial diagnostics for a failed episode.
        error = f"{type(exc).__name__}: {exc}"

    rewards, statuses = current_rewards_and_statuses(env)
    margin = rewards[seat] - rewards[1 - seat]
    final_teacher_metrics = {
        teacher_id: {
            **{key: value for key, value in record.items() if key not in {"overall", "stages"}},
            "overall": finalise_metrics(record["overall"]),
            "stages": {
                name: {
                    **finalise_metrics(record["stages"][name]),
                    "first_joint_divergence": record[
                        "first_joint_divergence_by_stage"
                    ][name],
                }
                for name, _, _ in STAGES
            },
        }
        for teacher_id, record in teacher_metrics.items()
    }
    stop_reason = (
        "error" if error is not None else
        "done" if env.done else
        "max_steps" if steps_executed >= step_limit else
        "unknown"
    )
    return {
        "seed": int(seed),
        "candidate_seat": int(seat),
        "opponent": opponent_name,
        "router_period": int(router_period),
        "step_limit": int(step_limit),
        "steps_executed": int(steps_executed),
        "stop_reason": stop_reason,
        "done": bool(env.done),
        "candidate_reward": rewards[seat],
        "opponent_reward": rewards[1 - seat],
        "margin": margin,
        "candidate_status": statuses[seat],
        "opponent_status": statuses[1 - seat],
        "statuses": statuses,
        "error": error,
        "candidate_unknown_tokens": candidate_unknown,
        "candidate_unit_expert_usage": dict(candidate.unit_expert_usage),
        "candidate_market_expert_usage": dict(candidate.market_expert_usage),
        "teacher_agreement": final_teacher_metrics,
    }


def aggregate_teacher_metrics(
    representatives: list[dict[str, Any]], games: list[dict[str, Any]],
) -> dict[str, Any]:
    aggregate = game_metrics_template(representatives)
    first_by_game: dict[str, list[dict[str, Any]]] = {
        str(member["id"]): [] for member in representatives
    }
    first_by_stage: dict[str, dict[str, list[dict[str, Any]]]] = {
        str(member["id"]): {name: [] for name, _, _ in STAGES}
        for member in representatives
    }
    for game in games:
        for member in representatives:
            teacher_id = str(member["id"])
            source = game["teacher_agreement"][teacher_id]
            target = aggregate[teacher_id]
            for key in COUNT_KEYS:
                target["overall"][key] += int(source["overall"][f"{key}_count"])
            target["overall"]["steps"] += int(source["overall"]["steps"])
            for name, _, _ in STAGES:
                stage_source = source["stages"][name]
                target["stages"][name]["steps"] += int(stage_source["steps"])
                for key in COUNT_KEYS:
                    target["stages"][name][key] += int(stage_source[f"{key}_count"])
            for key, value in source["unknown_tokens"].items():
                target["unknown_tokens"][key] += int(value)
            if source["first_joint_divergence"] is not None:
                first_by_game[teacher_id].append({
                    "seed": game["seed"],
                    "candidate_seat": game["candidate_seat"],
                    **source["first_joint_divergence"],
                })
            for name, _, _ in STAGES:
                first = source["stages"][name]["first_joint_divergence"]
                if first is not None:
                    first_by_stage[teacher_id][name].append({
                        "seed": game["seed"],
                        "candidate_seat": game["candidate_seat"],
                        **first,
                    })

    result: dict[str, Any] = {}
    for member in representatives:
        teacher_id = str(member["id"])
        source = aggregate[teacher_id]
        first_rows = sorted(
            first_by_game[teacher_id],
            key=lambda row: (int(row["step"]), int(row["seed"]), int(row["candidate_seat"])),
        )
        stage_first_rows = {
            name: sorted(
                first_by_stage[teacher_id][name],
                key=lambda row: (
                    int(row["step"]), int(row["seed"]), int(row["candidate_seat"]),
                ),
            )
            for name, _, _ in STAGES
        }
        result[teacher_id] = {
            "behavior_family": str(member["behavior_family"]),
            "teacher_sha256": str(member["sha256"]),
            "overall": finalise_metrics(source["overall"]),
            "stages": {
                name: {
                    **finalise_metrics(source["stages"][name]),
                    "first_joint_divergence": (
                        stage_first_rows[name][0] if stage_first_rows[name] else None
                    ),
                }
                for name, _, _ in STAGES
            },
            "unknown_tokens": source["unknown_tokens"],
            "first_joint_divergence": first_rows[0] if first_rows else None,
            "first_joint_divergence_by_game": first_rows,
        }
    return result


def audit(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    registry, teachers = load_gold_train_teachers(args.registry)
    representatives, family_candidates = select_family_representatives(teachers)
    games: list[dict[str, Any]] = []
    for seed in range(int(args.seed_start), int(args.seed_start) + int(args.seeds)):
        for seat in (0, 1):
            game = audit_game(
                args.checkpoint, representatives, args.opponent,
                seed, seat, args.router_period, args.max_steps,
            )
            games.append(game)
            print(json.dumps({
                key: game[key] for key in (
                    "seed", "candidate_seat", "steps_executed", "stop_reason",
                    "candidate_reward", "opponent_reward", "margin", "statuses", "error",
                )
            }, ensure_ascii=False), flush=True)

    completed = [game for game in games if game["error"] is None]
    terminal = [game for game in completed if game["statuses"] == ["DONE", "DONE"]]
    return {
        "schema": SCHEMA,
        "checkpoint": {
            "path": str(args.checkpoint.resolve()),
            "sha256": sha256_file(args.checkpoint.resolve()),
            "policy_class": "TimedSequenceActionV113Policy",
        },
        "registry": registry,
        "teacher_selection": {
            "filter": "gold_split=train AND kind=agent",
            "unit": "behavior_family",
            "rule": "highest_sampling_weight_then_lexicographic_member_id",
            "family_candidates_in_selection_order": family_candidates,
            "selected": {
                str(member["behavior_family"]): {
                    "teacher_id": str(member["id"]),
                    "teacher_sha256": str(member["sha256"]),
                }
                for member in representatives
            },
        },
        "execution_contract": {
            "engine": "official kaggle_environments Kaggriculture",
            "candidate": "timed sequence policy executes its own action",
            "router_period": int(args.router_period),
            "dual_seat": True,
            "episode_isolation": "candidate, every teacher, and opponent reloaded per episode",
            "teacher_state": (
                "each independent teacher is queried once per candidate step and continuously "
                "updates on the candidate observation sequence"
            ),
            "teacher_execution": "query only; canonical action is never executed",
            "comparison": (
                "candidate returned request versus teacher canonical request; exact token and "
                "quantity equality under the shared action codec"
            ),
            "stages_inclusive": [
                {"name": name, "start": start, "end": stop - 1}
                for name, start, stop in STAGES
            ],
        },
        "opponent": args.opponent,
        "seed_start": int(args.seed_start),
        "seeds": int(args.seeds),
        "max_steps": args.max_steps,
        "games": len(games),
        "games_without_error": len(completed),
        "done_done": len(terminal),
        "mean_candidate_reward": (
            float(np.mean([game["candidate_reward"] for game in terminal]))
            if terminal else None
        ),
        "mean_margin": (
            float(np.mean([game["margin"] for game in terminal]))
            if terminal else None
        ),
        "teacher_summary": aggregate_teacher_metrics(representatives, games),
        "elapsed_seconds": time.time() - started,
        "rows": games,
    }


def atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", dir=path.parent, delete=False, encoding="utf-8",
    ) as sink:
        json.dump(payload, sink, ensure_ascii=False, indent=2, allow_nan=False)
        sink.write("\n")
        temporary = Path(sink.name)
    temporary.replace(path)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--checkpoint", type=Path, required=True)
    result.add_argument("--registry", type=Path, required=True)
    result.add_argument("--opponent", required=True)
    result.add_argument("--seed-start", type=int, required=True)
    result.add_argument("--seeds", type=int, required=True)
    result.add_argument("--output", type=Path, required=True)
    result.add_argument(
        "--router-period", type=int, default=1,
        help="Unit Router hold period; Stage35 functional labels require the default value 1.",
    )
    result.add_argument(
        "--max-steps", type=int,
        help="Optional per-game action cap for a quick smoke; omit for all 719 steps.",
    )
    return result


def main() -> None:
    argument_parser = parser()
    args = argument_parser.parse_args()
    if args.seeds < 1:
        argument_parser.error("--seeds must be positive")
    if args.router_period < 1:
        argument_parser.error("--router-period must be positive")
    if args.max_steps is not None and args.max_steps < 1:
        argument_parser.error("--max-steps must be positive")
    if not args.checkpoint.is_file():
        argument_parser.error(f"checkpoint does not exist: {args.checkpoint}")
    if not args.registry.is_file():
        argument_parser.error(f"registry does not exist: {args.registry}")
    report = audit(args)
    atomic_json(args.output, report)
    print(json.dumps({
        "output": str(args.output.resolve()),
        "games": report["games"],
        "games_without_error": report["games_without_error"],
        "done_done": report["done_done"],
        "mean_candidate_reward": report["mean_candidate_reward"],
        "mean_margin": report["mean_margin"],
        "elapsed_seconds": report["elapsed_seconds"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
