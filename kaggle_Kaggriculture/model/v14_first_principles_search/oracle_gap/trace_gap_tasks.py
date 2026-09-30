"""Trace the six exposed A2 losses that the strict oracle turned into wins.

Scope guard: this script reads only the already-exposed V13 screen36 artifacts.
It does not read V14 screen/confirm/test assets and it never mutates the
candidate.  The candidate's parent and opponent shadow are wrapped only to
observe their inputs and outputs while preserving their behavior.
"""

from __future__ import annotations

import copy
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import random
import sys
from typing import Any, Mapping

import numpy as np


HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[3]
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

from kaggle_Kaggriculture.model.v12a2_no_shop_gate import main as a2  # noqa: E402
from kaggle_Kaggriculture.model.v14_first_principles_search import (  # noqa: E402
    prototype_queue_solver as queue,
)


BASE = HERE.parent
BASELINE_GAMES = BASE / "oracle/a2_parent_baseline_games.jsonl"
ORACLE_GAMES = BASE / "oracle/a2_parent_oracle_games.jsonl"
STATEFUL_GAMES = BASE / "dev_runs/queue_solver_stateful_screen36/games.jsonl"
OUT = HERE / "gap_task_trace.json"


def _rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _key(row: Mapping[str, Any], seat_key: str) -> tuple[int, int]:
    return int(row["source"]["seed"]), int(row[seat_key])


def _result(row: Mapping[str, Any]) -> str:
    score = float(row["score_a"])
    return "W" if score == 1.0 else "T" if score == 0.5 else "L"


def _outcome(margin: float) -> str:
    return "W" if margin > 0 else "T" if margin == 0 else "L"


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class Spy:
    """Transparent observer for an agent; no action or state is changed."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.last_obs: Any = None
        self.last_action: dict[str, list[Any]] | None = None

    def __call__(self, obs: Any, configuration: Any = None) -> Any:
        self.last_obs = copy.deepcopy(obs)
        self.last_action = queue._canonical_action(self.inner(obs, configuration))
        return copy.deepcopy(self.last_action)

    def _selected_branch(self) -> str | None:
        method = getattr(self.inner, "_selected_branch", None)
        selected = method() if callable(method) else None
        return str(selected) if selected else None

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)


def _gate_reason(
    *,
    step: int,
    candidate: queue.QueueBestResponseAgent,
    obs: Any,
    parent_action: Mapping[str, Any],
    predicted_action: Mapping[str, Any],
    predicted_obs: Any,
) -> str:
    if not queue._configuration_supported(_CONFIGURATION):
        return "unsupported_shadow_runtime"
    if step < candidate.start_step:
        return "before_start"
    if not candidate.shadow_trusted or candidate.conformance_steps < candidate.minimum_conformance_steps:
        return "insufficient_shadow_conformance"
    if candidate.own_branch != "baseline_v8" or candidate.opponent_branch != "baseline_v8":
        return "not_v8_v8"
    if not queue._public_production_equal(obs) or queue._clone_distance(obs) > candidate.max_clone_distance:
        return "public_production_not_mirror"
    if queue._has_same_turn_shed_transfer(parent_action) or queue._has_same_turn_shed_transfer(predicted_action):
        return "same_turn_shed_transfer"
    predicted_best, _, _ = queue._best_sell_permutation(
        obs, parent_action, predicted_action, predicted_obs
    )
    if predicted_best == queue._canonical_action(parent_action):
        return "no_positive_queue_best_response"
    return "candidate_should_reorder"


_CONFIGURATION: Any = None


def _run_one(source: Mapping[str, Any], seat: int, expected: Mapping[str, Any]) -> dict[str, Any]:
    global _CONFIGURATION
    from kaggle_environments import make

    seed = int(source["seed"])
    random.seed(seed * 104729 + seat * 1009)
    np.random.seed((seed + seat * 65537) % (2**32 - 1))
    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    env.reset(2)
    _CONFIGURATION = env.configuration

    candidate = queue.make_agent()
    candidate.parent = Spy(candidate.parent)
    candidate.opponent_shadow = Spy(candidate.opponent_shadow)
    opponent = a2.make_agent()
    opportunities: list[dict[str, Any]] = []
    step = 0
    while [str(state.status) for state in env.state] == ["ACTIVE", "ACTIVE"]:
        for state in env.state:
            state.observation.step = step
        obs = env.state[seat].observation
        opponent_obs = env.state[1 - seat].observation
        result = queue._canonical_action(candidate(obs, env.configuration))
        parent_action = copy.deepcopy(candidate.parent.last_action)
        predicted_action = copy.deepcopy(candidate.opponent_shadow.last_action)
        predicted_obs = copy.deepcopy(candidate.opponent_shadow.last_obs)
        actual_action = queue._canonical_action(opponent(opponent_obs, env.configuration))

        perfect, perfect_advantage, _ = queue._best_sell_permutation(
            obs, parent_action, actual_action, opponent_obs
        )
        if perfect != parent_action:
            base_own, base_opponent = queue._simulate_sell_queues(
                parent_action["market"], actual_action["market"], queue._inventory(obs),
                queue._shed(obs), queue._shed(opponent_obs),
            )
            best_own, best_opponent = queue._simulate_sell_queues(
                perfect["market"], actual_action["market"], queue._inventory(obs),
                queue._shed(obs), queue._shed(opponent_obs),
            )
            reason = _gate_reason(
                step=step,
                candidate=candidate,
                obs=obs,
                parent_action=parent_action,
                predicted_action=predicted_action,
                predicted_obs=predicted_obs,
            )
            opportunities.append(
                {
                    "step": step,
                    "day": int(obs.get("day", 0) or 0),
                    "hour": int(obs.get("hour", 0) or 0),
                    "candidate_applied": result != parent_action,
                    "candidate_matches_perfect": result == perfect,
                    "gate_reason": reason,
                    "perfect_advantage": float(perfect_advantage),
                    "public_production_equal": queue._public_production_equal(obs),
                    "clone_distance": queue._clone_distance(obs),
                    "own_branch": candidate.own_branch,
                    "opponent_branch": candidate.opponent_branch,
                    "shadow_trusted": candidate.shadow_trusted,
                    "conformance_steps": candidate.conformance_steps,
                    "predicted_action_exact": predicted_action == actual_action,
                    "predicted_private_exact": _canonical(predicted_obs.get("private", {}))
                    == _canonical(opponent_obs.get("private", {})),
                    "parent_all_sell": queue._all_sell(parent_action),
                    "opponent_all_sell": queue._all_sell(actual_action),
                    "parent_has_transfer": queue._has_same_turn_shed_transfer(parent_action),
                    "opponent_has_transfer": queue._has_same_turn_shed_transfer(actual_action),
                    "own_revenue_non_decrease": best_own + 1e-9 >= base_own,
                    "own_revenue_gain": float(best_own - base_own),
                    "relative_revenue_gain": float(
                        (best_own - best_opponent) - (base_own - base_opponent)
                    ),
                    "parent_queue": parent_action["market"],
                    "actual_opponent_queue": actual_action["market"],
                    "perfect_queue": perfect["market"],
                }
            )
        actions = [result, actual_action] if seat == 0 else [actual_action, result]
        env.step(actions)
        step += 1
        if step > 1000:
            raise RuntimeError("environment exceeded 1000 steps")

    rewards = [float(state.reward or 0.0) for state in env.state]
    margin = rewards[seat] - rewards[1 - seat]
    expected_rewards = [float(value) for value in expected["rewards"]]
    if rewards != expected_rewards:
        raise AssertionError(
            f"replay drift for {(seed, seat)}: expected {expected_rewards}, got {rewards}"
        )
    missed = [row for row in opportunities if not row["candidate_matches_perfect"]]
    return {
        "source": dict(source),
        "candidate_seat": seat,
        "rewards": rewards,
        "margin": margin,
        "outcome": _outcome(margin),
        "perfect_opportunity_steps": len(opportunities),
        "applied_perfect_steps": sum(row["candidate_matches_perfect"] for row in opportunities),
        "missed_perfect_steps": len(missed),
        "first_perfect_opportunity": opportunities[0] if opportunities else None,
        "first_missed_perfect_opportunity": missed[0] if missed else None,
        "missed_gate_counts": {
            key: sum(row["gate_reason"] == key for row in missed)
            for key in sorted({row["gate_reason"] for row in missed})
        },
        "opportunities": opportunities,
        "candidate_diagnostics": candidate.diagnostics(),
    }


def _run_one_star(args: tuple[Mapping[str, Any], int, Mapping[str, Any]]) -> dict[str, Any]:
    return _run_one(*args)


def main() -> None:
    HERE.mkdir(parents=True, exist_ok=True)
    baseline = {_key(row, "candidate_seat"): row for row in _rows(BASELINE_GAMES)}
    oracle = {_key(row, "candidate_seat"): row for row in _rows(ORACLE_GAMES)}
    stateful = {_key(row, "model_a_seat"): row for row in _rows(STATEFUL_GAMES)}
    keys = sorted(
        key for key in baseline
        if baseline[key]["outcome"] == "L" and oracle[key]["outcome"] == "W"
    )
    if len(keys) != 6:
        raise AssertionError(f"expected six baseline L->oracle W tasks, found {len(keys)}")
    args = [(stateful[key]["source"], key[1], stateful[key]) for key in keys]
    with ProcessPoolExecutor(max_workers=len(args)) as pool:
        traces = list(pool.map(_run_one_star, args))
    traces.sort(key=lambda row: (int(row["source"]["seed"]), int(row["candidate_seat"])))
    payload = {
        "schema": "kaggriculture-v14-oracle-gap-trace-1",
        "epistemic_status": "diagnostic replay on already-exposed V13 screen36 only",
        "scope": {
            "baseline_games": str(BASELINE_GAMES.resolve()),
            "oracle_games": str(ORACLE_GAMES.resolve()),
            "stateful_games": str(STATEFUL_GAMES.resolve()),
            "v14_fresh_screen_read": False,
            "v14_confirm_read": False,
            "test_read": False,
            "candidate_mutated": False,
        },
        "candidate_source": str(Path(queue.__file__).resolve()),
        "candidate_sha256": hashlib.sha256(Path(queue.__file__).read_bytes()).hexdigest(),
        "tasks": traces,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(OUT.resolve()),
        "tasks": len(traces),
        "outcomes": [row["outcome"] for row in traces],
        "first_missed_gates": [
            row["first_missed_perfect_opportunity"]["gate_reason"]
            if row["first_missed_perfect_opportunity"] else None
            for row in traces
        ],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
