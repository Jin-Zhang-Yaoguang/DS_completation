"""Fresh-seed paired evaluator for two one-day delayed production Routers."""

from __future__ import annotations

import json
from typing import Any

from evaluate_event_program_pair import (
    CHECKPOINT_ROLES,
    _error_side,
    _paired_row,
    build_parser,
    checkpoint_independent_episode_key,
    game_score,
    run_campaign,
)
from collect_event_program_ppo_rollouts import resolve_opponent
from policy_delayed_trainable_event_program import DelayedTrainableEventProgramPolicy
from policy_trainable_event_program import CATASTROPHE_REWARD


def _evaluate_delayed_one(
    checkpoint: str,
    *,
    seed: int,
    seat: int,
    opponent_id: str,
    rollout_seed: int,
    episode_key: str,
    deterministic: bool,
) -> dict[str, Any]:
    try:
        from kaggle_environments import make

        policy = DelayedTrainableEventProgramPolicy(
            checkpoint,
            rollout_seed=rollout_seed,
            episode_key=episode_key,
            deterministic=deterministic,
        )
        opponent = resolve_opponent(
            opponent_id, f"v114_delayed_pair_{seed}_{seat}"
        )
        agents: list[Any] = [None, None]
        agents[seat], agents[1 - seat] = policy, opponent
        env = make("kaggriculture", configuration={"seed": int(seed)}, debug=False)
        env.run(agents)
        rewards = [float(state.reward or 0.0) for state in env.state]
        statuses = [str(state.status) for state in env.state]
        reward, opponent_reward = rewards[seat], rewards[1 - seat]
        margin = reward - opponent_reward
        violations = int(policy.contract_violation_count)
        if policy.probe_action_steps != 24 or policy.manager_decision_count != 1:
            violations += 1
        return {
            "reward": reward,
            "opponent_reward": opponent_reward,
            "margin": margin,
            "score": game_score(margin),
            "catastrophe": reward < CATASTROPHE_REWARD,
            "action_steps": int(policy.action_steps),
            "decision_count": int(policy.manager_decision_count),
            "expected_decision_count": 1,
            "probe_action_steps": int(policy.probe_action_steps),
            "selected_route": policy.selected_route,
            "contract_violations": violations,
            "terminal_procurement": int(policy.terminal_procurement_count),
            "status": statuses[seat],
            "opponent_status": statuses[1 - seat],
            "statuses": statuses,
            "environment_states": len(env.steps),
            "error": None,
        }
    except Exception as exc:
        side = _error_side(f"{type(exc).__name__}: {exc}")
        side["expected_decision_count"] = 1
        side["probe_action_steps"] = 0
        side["selected_route"] = None
        return side


def evaluate_delayed_pair_seed(
    checkpoint_specs: tuple[dict[str, str], ...],
    seed: int,
    opponent_id: str,
    rollout_seed: int,
) -> list[dict[str, Any]]:
    specs = {str(item["role"]): dict(item) for item in checkpoint_specs}
    if set(specs) != set(CHECKPOINT_ROLES):
        raise ValueError("checkpoint_specs must contain incumbent and challenger")
    rows: list[dict[str, Any]] = []
    for seat in (0, 1):
        episode_key = checkpoint_independent_episode_key(seed, seat, opponent_id)
        sides = {
            role: _evaluate_delayed_one(
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


def main() -> None:
    args = build_parser().parse_args()
    report = run_campaign(args, worker_fn=evaluate_delayed_pair_seed)
    print(json.dumps({
        "status": report["status"],
        "summaries": report["summaries"],
        "paired": report["paired"],
        "validation_errors": report["validation_errors"],
    }, indent=2))


if __name__ == "__main__":
    main()
