"""Audit raw-teacher versus canonical-action transition parity.

For every behavior family represented by a registry-backed Gold-Train agent,
this script selects one deterministic representative and runs one fixed seed
from both seats against the built-in Starter agent.  Two isolated official
Kaggriculture environments are advanced in lockstep:

* the raw branch executes the teacher request unchanged;
* the canonical branch executes the same codec path used by
  ``collect_multiteacher_sequence_bc.py``.

The post-step official agent states are converted to canonical JSON and
SHA256-hashed.  Submitted action text is deliberately excluded from the state
hash: the audit asks whether two requests produce the same official transition,
not whether their serialized request objects are identical.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any, Mapping, Sequence

from kaggle_environments import make
import numpy as np

import action_space as space
from collect_multiteacher_sequence_bc import (
    canonical_action,
    load_gold_train_teachers,
)
from collect_rollouts import agent_observations, call_opponent, resolve_opponent
from opponent_pool import LAYER_IDS, PoolAssignment, build_opponent


SCHEMA = "kaggriculture-v113-multiteacher-canonical-parity-v1"
ANCHOR_OPPONENT = "builtin:starter"


def _jsonable(value: Any) -> Any:
    """Convert Kaggle Struct/numpy values to deterministic JSON primitives."""
    if isinstance(value, np.generic):
        return _jsonable(value.item())
    if isinstance(value, Mapping):
        return {
            str(key): _jsonable(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (set, frozenset)):
        converted = [_jsonable(item) for item in value]
        return sorted(converted, key=lambda item: _canonical_json(item))
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, float) and not np.isfinite(value):
        raise ValueError(f"official state contains non-finite float: {value!r}")
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    # Kaggle Struct is normally handled as a Mapping.  Fail closed for a new
    # engine object instead of hashing a repr that may contain memory addresses.
    raise TypeError(f"unsupported value in stable state hash: {type(value).__name__}")


def _canonical_json(value: Any) -> str:
    return json.dumps(
        _jsonable(value), ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    )


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def official_state_snapshot(env: Any) -> dict[str, Any]:
    """Return the full post-interpreter agent state, excluding submitted actions."""
    return {
        "done": bool(env.done),
        "agents": [
            {
                "observation": _jsonable(state.observation),
                "reward": _jsonable(state.reward),
                "status": str(state.status),
                "info": _jsonable(state.info),
            }
            for state in env.state
        ],
    }


def official_state_hash(env: Any) -> str:
    return _stable_hash(official_state_snapshot(env))


def select_family_representatives(
    teachers: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    """Select one stable representative per behavior family.

    Registry sampling weight is used as the primary preference.  Ties are
    broken by member id, making the selection independent of JSON ordering.
    """
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for teacher in teachers:
        by_family[str(teacher["behavior_family"])].append(teacher)

    selected: list[dict[str, Any]] = []
    candidates: dict[str, list[str]] = {}
    for family in sorted(by_family):
        members = sorted(
            by_family[family],
            key=lambda member: (-float(member.get("sampling_weight", 0.0)), str(member["id"])),
        )
        selected.append(members[0])
        candidates[family] = [str(member["id"]) for member in members]
    return selected, candidates


def _teacher_assignment(member: dict[str, Any], seed: int) -> PoolAssignment:
    return PoolAssignment(
        seed=int(seed),
        layer="gold_train",
        layer_id=LAYER_IDS["gold_train"],
        member_id=str(member["id"]),
        member_index=int(member["member_index"]),
        member=member,
    )


def _terminal_summary(env: Any, teacher_seat: int) -> dict[str, Any]:
    rewards = [float(state.reward if state.reward is not None else 0.0) for state in env.state]
    statuses = [str(state.status) for state in env.state]
    return {
        "done": bool(env.done),
        "state_hash": official_state_hash(env),
        "rewards": rewards,
        "statuses": statuses,
        "teacher_reward": rewards[teacher_seat],
        "opponent_reward": rewards[1 - teacher_seat],
        "teacher_status": statuses[teacher_seat],
        "opponent_status": statuses[1 - teacher_seat],
    }


def audit_game(
    member: dict[str, Any], seed: int, seat: int, max_steps: int | None,
) -> dict[str, Any]:
    family = str(member["behavior_family"])
    teacher_id = str(member["id"])
    suffix = f"{family}_{teacher_id}_{seed}_{seat}"
    assignment = _teacher_assignment(member, seed)

    # Separate module instances are required because every current Gold-Train
    # teacher carries module state.  The two branches must not share it.
    raw_teacher = build_opponent(assignment, f"v113_parity_raw_teacher_{suffix}")
    canonical_teacher = build_opponent(assignment, f"v113_parity_canonical_teacher_{suffix}")
    raw_opponent = resolve_opponent(ANCHOR_OPPONENT, f"v113_parity_raw_anchor_{suffix}")
    canonical_opponent = resolve_opponent(
        ANCHOR_OPPONENT, f"v113_parity_canonical_anchor_{suffix}",
    )

    raw_env = make("kaggriculture", configuration={"seed": int(seed)}, debug=False)
    canonical_env = make("kaggriculture", configuration={"seed": int(seed)}, debug=False)
    raw_env.reset(2)
    canonical_env.reset(2)

    episode_steps = int(space.get(raw_env.configuration, "episodeSteps", 720)) - 1
    step_limit = episode_steps if max_steps is None else min(int(max_steps), episode_steps)
    rows: list[dict[str, Any]] = []
    first_divergence: dict[str, Any] | None = None
    diagnostics_total: Counter[str] = Counter()

    while (
        len(rows) < step_limit
        and not raw_env.done
        and not canonical_env.done
    ):
        raw_observations = agent_observations(raw_env)
        canonical_observations = agent_observations(canonical_env)
        raw_obs = raw_observations[seat]
        canonical_obs = canonical_observations[seat]
        raw_step = int(space.get(raw_obs, "step", len(rows)) or 0)
        canonical_step = int(space.get(canonical_obs, "step", len(rows)) or 0)
        pre_raw_hash = official_state_hash(raw_env)
        pre_canonical_hash = official_state_hash(canonical_env)

        raw_teacher_action = call_opponent(raw_teacher, raw_obs, raw_env.configuration)
        canonical_teacher_raw_action = call_opponent(
            canonical_teacher, canonical_obs, canonical_env.configuration,
        )
        decoded_action, diagnostics = canonical_action(
            canonical_obs, canonical_teacher_raw_action,
        )
        diagnostics_total.update(diagnostics)

        expected_raw_hands = space.unit_count(raw_obs) - 1
        expected_canonical_hands = space.unit_count(canonical_obs) - 1
        normalised_raw_action = space.normalise_action(
            raw_teacher_action or {}, expected_raw_hands,
        )
        normalised_canonical_source = space.normalise_action(
            canonical_teacher_raw_action or {}, expected_canonical_hands,
        )

        raw_anchor_action = call_opponent(
            raw_opponent, raw_observations[1 - seat], raw_env.configuration,
        )
        canonical_anchor_action = call_opponent(
            canonical_opponent,
            canonical_observations[1 - seat],
            canonical_env.configuration,
        )
        raw_actions: list[Any] = [None, None]
        canonical_actions: list[Any] = [None, None]
        raw_actions[seat] = raw_teacher_action
        raw_actions[1 - seat] = raw_anchor_action
        canonical_actions[seat] = decoded_action
        canonical_actions[1 - seat] = canonical_anchor_action
        raw_env.step(raw_actions)
        canonical_env.step(canonical_actions)

        post_raw_hash = official_state_hash(raw_env)
        post_canonical_hash = official_state_hash(canonical_env)
        pre_equal = pre_raw_hash == pre_canonical_hash
        post_equal = post_raw_hash == post_canonical_hash
        source_actions_equal = normalised_raw_action == normalised_canonical_source
        anchor_actions_equal = _jsonable(raw_anchor_action) == _jsonable(canonical_anchor_action)
        row = {
            "index": len(rows),
            "raw_step": raw_step,
            "canonical_step": canonical_step,
            "pre_state_hash_equal": pre_equal,
            "post_state_hash_equal": post_equal,
            "raw_state_hash": post_raw_hash,
            "canonical_state_hash": post_canonical_hash,
            "teacher_source_actions_equal": source_actions_equal,
            "anchor_actions_equal": anchor_actions_equal,
            "canonical_action_modified": bool(diagnostics["changed"]),
            "raw_unknown_tokens": int(
                diagnostics["raw_unit_unknown"] + diagnostics["raw_market_unknown"]
            ),
            "canonical_unknown_tokens": int(
                diagnostics["canonical_unit_unknown"]
                + diagnostics["canonical_market_unknown"]
            ),
        }
        rows.append(row)

        if not post_equal and first_divergence is None:
            first_divergence = {
                "index": row["index"],
                "step": raw_step if raw_step == canonical_step else None,
                "raw_step": raw_step,
                "canonical_step": canonical_step,
                "pre_state_hash_equal": pre_equal,
                "raw_state_hash": post_raw_hash,
                "canonical_state_hash": post_canonical_hash,
                "teacher_source_actions_equal": source_actions_equal,
                "anchor_actions_equal": anchor_actions_equal,
                "raw_teacher_action": _jsonable(normalised_raw_action),
                "canonical_teacher_source_action": _jsonable(
                    normalised_canonical_source
                ),
                "canonical_decoded_action": _jsonable(decoded_action),
                "raw_anchor_action": _jsonable(raw_anchor_action),
                "canonical_anchor_action": _jsonable(canonical_anchor_action),
            }

    divergent_steps = sum(not row["post_state_hash_equal"] for row in rows)
    modified_steps = int(diagnostics_total["changed"])
    stop_reason = (
        "step_limit"
        if len(rows) >= step_limit and not (raw_env.done and canonical_env.done)
        else "both_done"
        if raw_env.done and canonical_env.done
        else "raw_done_first"
        if raw_env.done
        else "canonical_done_first"
        if canonical_env.done
        else "unknown"
    )
    return {
        "behavior_family": family,
        "teacher_id": teacher_id,
        "teacher_sha256": str(member["sha256"]),
        "seed": int(seed),
        "teacher_seat": int(seat),
        "opponent": ANCHOR_OPPONENT,
        "step_limit": step_limit,
        "steps_compared": len(rows),
        "stop_reason": stop_reason,
        "first_divergence_step": (
            None if first_divergence is None else first_divergence["step"]
        ),
        "first_divergence": first_divergence,
        "divergent_steps": divergent_steps,
        "divergence_rate": divergent_steps / len(rows) if rows else 0.0,
        "canonical_modified_steps": modified_steps,
        "action_modification_rate": modified_steps / len(rows) if rows else 0.0,
        "unknown_tokens": {
            "raw_unit": int(diagnostics_total["raw_unit_unknown"]),
            "raw_market": int(diagnostics_total["raw_market_unknown"]),
            "canonical_unit": int(diagnostics_total["canonical_unit_unknown"]),
            "canonical_market": int(diagnostics_total["canonical_market_unknown"]),
        },
        "raw_branch_final": _terminal_summary(raw_env, seat),
        "canonical_branch_final": _terminal_summary(canonical_env, seat),
        "step_rows": rows,
    }


def audit(args: argparse.Namespace) -> dict[str, Any]:
    registry, teachers = load_gold_train_teachers(args.registry)
    representatives, family_candidates = select_family_representatives(teachers)
    games: list[dict[str, Any]] = []
    for family_index, member in enumerate(representatives):
        seed = int(args.seed_start) + family_index
        for seat in (0, 1):
            games.append(audit_game(member, seed, seat, args.max_steps))

    total_steps = sum(int(game["steps_compared"]) for game in games)
    divergent_steps = sum(int(game["divergent_steps"]) for game in games)
    modified_steps = sum(int(game["canonical_modified_steps"]) for game in games)
    first_divergences = [
        {
            "behavior_family": game["behavior_family"],
            "teacher_id": game["teacher_id"],
            "seed": game["seed"],
            "teacher_seat": game["teacher_seat"],
            "step": game["first_divergence_step"],
        }
        for game in games
        if game["first_divergence"] is not None
    ]
    return {
        "schema": SCHEMA,
        "registry": registry,
        "teacher_selection": "gold_split=train AND kind=agent",
        "representative_contract": {
            "unit": "behavior_family",
            "selection": "highest_sampling_weight_then_lexicographic_member_id",
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
            "opponent": ANCHOR_OPPONENT,
            "one_seed_per_behavior_family": True,
            "dual_seat": True,
            "branch_isolation": "fresh teacher, opponent, and environment per branch",
            "raw_branch_action": "teacher request unchanged",
            "canonical_branch_action": "collect_multiteacher_sequence_bc.canonical_action",
            "state_hash": {
                "algorithm": "sha256",
                "serialization": "canonical JSON; sorted keys; compact separators",
                "included": "both official agent observations, rewards, statuses, info, env.done",
                "excluded": "submitted action field",
            },
        },
        "seed_start": int(args.seed_start),
        "max_steps": args.max_steps,
        "family_count": len(representatives),
        "paired_games": len(games),
        "branch_games": 2 * len(games),
        "summary": {
            "steps_compared": total_steps,
            "divergent_steps": divergent_steps,
            "divergence_rate": divergent_steps / total_steps if total_steps else 0.0,
            "canonical_modified_steps": modified_steps,
            "action_modification_rate": modified_steps / total_steps if total_steps else 0.0,
            "games_with_divergence": len(first_divergences),
            "all_state_hashes_equal": divergent_steps == 0,
            "first_divergences": first_divergences,
        },
        "games": games,
    }


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
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
    result.add_argument("--registry", type=Path, required=True)
    result.add_argument("--seed-start", type=int, required=True)
    result.add_argument("--output", type=Path, required=True)
    result.add_argument(
        "--max-steps", type=int,
        help="Optional per-game step cap for a quick smoke; omit for the full 719-step audit.",
    )
    return result


def main() -> None:
    argument_parser = parser()
    args = argument_parser.parse_args()
    if args.max_steps is not None and args.max_steps < 1:
        argument_parser.error("--max-steps must be positive")
    report = audit(args)
    _atomic_json(args.output, report)
    print(json.dumps({
        "output": str(args.output.resolve()),
        "family_count": report["family_count"],
        "paired_games": report["paired_games"],
        **report["summary"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
