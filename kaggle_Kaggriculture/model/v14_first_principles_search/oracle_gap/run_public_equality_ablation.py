"""Exposed-only ablation of the redundant exact-public-equality gate.

The candidate source is not edited.  In each isolated worker, the exact
equality predicate is replaced with True while the existing clone-distance
cap, stateful shadow, conformance checks, V8/V8 gate, strict SELL constraints,
and own-revenue guard remain unchanged.
"""

from __future__ import annotations

from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
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
STATEFUL_GAMES = BASE / "dev_runs/queue_solver_stateful_screen36/games.jsonl"
ORACLE_GAMES = BASE / "oracle/a2_parent_oracle_games.jsonl"
OUT = HERE / "public_equality_ablation.json"


def _outcome(margin: float) -> str:
    return "W" if margin > 0 else "T" if margin == 0 else "L"


def _always_true(_: Any) -> bool:
    return True


def _run_one(task: Mapping[str, Any]) -> dict[str, Any]:
    from kaggle_environments import make

    # Analysis-only monkeypatch, local to this worker process.
    queue._public_production_equal = _always_true
    source = dict(task["source"])
    seat = int(task["model_a_seat"])
    seed = int(source["seed"])
    random.seed(seed * 104729 + seat * 1009)
    np.random.seed((seed + seat * 65537) % (2**32 - 1))
    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    env.reset(2)
    candidate = queue.make_agent()
    opponent = a2.make_agent()
    step = 0
    while [str(state.status) for state in env.state] == ["ACTIVE", "ACTIVE"]:
        for state in env.state:
            state.observation.step = step
        action = queue._canonical_action(candidate(env.state[seat].observation, env.configuration))
        opponent_action = queue._canonical_action(opponent(env.state[1 - seat].observation, env.configuration))
        env.step([action, opponent_action] if seat == 0 else [opponent_action, action])
        step += 1
        if step > 1000:
            raise RuntimeError("environment exceeded 1000 steps")
    rewards = [float(state.reward or 0.0) for state in env.state]
    margin = rewards[seat] - rewards[1 - seat]
    diagnostics = candidate.diagnostics()
    return {
        "source": source,
        "candidate_seat": seat,
        "statuses": [str(state.status) for state in env.state],
        "rewards": rewards,
        "margin": margin,
        "outcome": _outcome(margin),
        "reordered_steps": int(diagnostics["reordered_steps"]),
        "predicted_advantage": float(diagnostics["predicted_advantage"]),
        "shadow_trusted": bool(diagnostics["shadow_trusted"]),
        "conformance_steps": int(diagnostics["conformance_steps"]),
        "shadow_faults": int(diagnostics["shadow_faults"]),
        "shadow_update_errors": int(diagnostics["shadow_update_errors"]),
        "skip_reasons": diagnostics["skip_reasons"],
        "own_branch": diagnostics["own_branch"],
        "opponent_branch": diagnostics["opponent_branch"],
    }


def main() -> None:
    source_rows = [
        json.loads(line)
        for line in STATEFUL_GAMES.read_text(encoding="utf-8").splitlines()
        if line
    ]
    oracle_rows = [
        json.loads(line)
        for line in ORACLE_GAMES.read_text(encoding="utf-8").splitlines()
        if line
    ]
    if len(source_rows) != 72 or len(oracle_rows) != 72:
        raise AssertionError("scope guard: expected the 72-game exposed V13 screen36 artifacts")
    with ProcessPoolExecutor(max_workers=12) as pool:
        futures = [pool.submit(_run_one, row) for row in source_rows]
        rows = [future.result() for future in as_completed(futures)]
    rows.sort(key=lambda row: (int(row["source"]["seed"]), int(row["candidate_seat"])))
    oracle = {
        (int(row["source"]["seed"]), int(row["candidate_seat"])): row
        for row in oracle_rows
    }
    transitions: Counter[str] = Counter()
    reward_exact = 0
    for row in rows:
        key = (int(row["source"]["seed"]), int(row["candidate_seat"]))
        target = oracle[key]
        transitions[f"{target['outcome']}->{row['outcome']}"] += 1
        reward_exact += row["rewards"] == [float(value) for value in target["rewards"]]
    outcomes = Counter(row["outcome"] for row in rows)
    payload = {
        "schema": "kaggriculture-v14-public-equality-ablation-1",
        "epistemic_status": "causal ablation on already-exposed V13 screen36 only; not validation",
        "change": "remove exact cross-farm public equality; retain clone_distance<=4 and every other gate",
        "scope": {
            "stateful_games": str(STATEFUL_GAMES.resolve()),
            "oracle_games": str(ORACLE_GAMES.resolve()),
            "v14_fresh_screen_read": False,
            "v14_confirm_read": False,
            "test_read": False,
            "candidate_source_edited": False,
        },
        "candidate_source": str(Path(queue.__file__).resolve()),
        "candidate_sha256": hashlib.sha256(Path(queue.__file__).read_bytes()).hexdigest(),
        "games": len(rows),
        "outcomes": dict(sorted(outcomes.items())),
        "pure_win_rate": outcomes["W"] / len(rows),
        "score_rate": (outcomes["W"] + 0.5 * outcomes["T"]) / len(rows),
        "oracle_to_ablation_transitions": dict(sorted(transitions.items())),
        "reward_vectors_exact_oracle": reward_exact,
        "reordered_steps": sum(row["reordered_steps"] for row in rows),
        "shadow_faults": sum(row["shadow_faults"] for row in rows),
        "shadow_update_errors": sum(row["shadow_update_errors"] for row in rows),
        "all_shadow_trusted": all(row["shadow_trusted"] for row in rows),
        "rows": rows,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in (
        "games", "outcomes", "pure_win_rate", "score_rate",
        "oracle_to_ablation_transitions", "reward_vectors_exact_oracle",
        "reordered_steps", "shadow_faults", "shadow_update_errors", "all_shadow_trusted",
    )}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
