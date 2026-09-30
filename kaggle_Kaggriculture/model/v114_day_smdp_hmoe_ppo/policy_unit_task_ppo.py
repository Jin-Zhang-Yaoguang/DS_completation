"""On-policy candidate-level SMDP policy for V12 persistent unit tasks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any, Mapping

from flax import serialization
import jax
import jax.numpy as jnp
import numpy as np

HERE = Path(__file__).resolve().parent
V113 = HERE.parent / "v113_simulator_hmoe_ppo"
if str(V113) not in sys.path:
    sys.path.insert(0, str(V113))

import features  # noqa: E402
from build_unit_task_dataset import ITEMS, QUANTITY_TIERS, ROLE_NAMES
from model_unit_task_hmoe import UnitTaskHMoE
from persistent_unit_tasks import (
    UnitTask,
    _log_softmax,
    _positions,
    _task_candidates,
    role_for_operation,
)
from unit_task_ppo_math import candidate_arrays, categorical_stats, score_candidates


REWARD_BY_OPERATION = {
    "REST": -0.05,
    "PLANT": 0.40,
    "WATER": 0.20,
    "HARVEST": 1.50,
    "FERTILIZE": 0.35,
    "DIG": 0.10,
    "BUILD_COOP": 0.30,
    "BUILD_PASTURE": 0.30,
    "FEED": 0.25,
    "COLLECT_FERTILIZER": 0.70,
    "CARE": 0.20,
    "PICKUP": 0.15,
    "PLACE": 0.25,
    "DROP": 0.25,
}


@dataclass(frozen=True)
class TaskCandidate:
    role_index: int
    operation: str
    item: str
    quantity_index: int
    target_x: int
    target_y: int
    duration: int

    def task(self) -> UnitTask:
        return UnitTask(
            ROLE_NAMES[self.role_index], self.operation, self.item,
            QUANTITY_TIERS[self.quantity_index], self.target_x, self.target_y,
            self.duration,
        )


def construct_candidates(
    observation: Mapping[str, Any],
    unit_index: int,
    output: Mapping[str, np.ndarray],
    reserved_targets: set[tuple[int, int, str, str]] | None = None,
) -> list[TaskCandidate]:
    logp = {
        key: _log_softmax(value) if key == "role_logits" else np.stack([
            _log_softmax(row) for row in value
        ])
        for key, value in output.items() if key.endswith("logits")
    }
    origin = _positions(observation)[unit_index]
    candidates: list[TaskCandidate] = []
    for operation, item, feasible_quantity, x, y in _task_candidates(
        observation, unit_index, reserved_targets=reserved_targets
    ):
        role = role_for_operation(operation)
        distance = abs(x - origin[0]) + abs(y - origin[1])
        minimum_duration = min(24, distance + 1)
        maximum_duration = max(
            minimum_duration, 24 - int(observation.get("step", 0) or 0) % 24
        )
        duration = max(
            range(minimum_duration, min(24, maximum_duration) + 1),
            key=lambda value: float(logp["duration_logits"][role, value]),
        )
        quantity_index = 0
        if feasible_quantity > 0:
            valid = [
                index for index, value in enumerate(QUANTITY_TIERS)
                if 0 < value <= feasible_quantity
            ] or [1]
            quantity_index = max(
                valid,
                key=lambda index: float(logp["quantity_logits"][role, index]),
            )
        candidates.append(TaskCandidate(
            role, operation, item, quantity_index, x, y, duration
        ))
    return candidates


class UnitTaskPPOPolicy:
    """Sample only at task boundaries and retain exact behavior-policy evidence."""

    def __init__(
        self,
        checkpoint: Path,
        *,
        rollout_seed: int,
        deterministic: bool = False,
        collect: bool = True,
    ) -> None:
        payload = serialization.msgpack_restore(Path(checkpoint).read_bytes())
        if payload.get("strategy_parent") is not None:
            raise ValueError("unit task PPO must remain an independent strategy lineage")
        if payload.get("inherits_historical_checkpoint") is not False:
            raise ValueError("historical checkpoint inheritance is forbidden")
        if payload.get("historical_agent_online_action_source") is not False:
            raise ValueError("historical online actions are forbidden")
        self.params = payload["params"]
        self.model = UnitTaskHMoE()
        self._apply = jax.jit(
            lambda params, g, b, u: self.model.apply({"params": params}, g, b, u)
        )
        self.rng = np.random.default_rng(int(rollout_seed))
        self.deterministic = bool(deterministic)
        self.collect = bool(collect)
        self.pending: dict[int, dict[str, Any]] = {}
        self.transitions: list[dict[str, Any]] = []
        self.decision_count = 0
        self.outcome_counts: dict[str, int] = {}
        self.reserved_targets: set[tuple[int, int, str, str]] = set()

    def set_reserved_targets(self, values: set[tuple[int, int, str, str]]) -> None:
        self.reserved_targets = set(values)

    def __call__(self, observation: Mapping[str, Any], unit_index: int) -> UnitTask:
        encoded = features.encode_observation(observation)
        jax_output = self._apply(
            self.params,
            jnp.asarray(encoded["global"])[None],
            jnp.asarray(encoded["board"])[None],
            jnp.asarray(encoded["units"][unit_index])[None],
        )
        output = jax.tree.map(lambda value: np.asarray(value[0]), jax_output)
        candidates = construct_candidates(
            observation, unit_index, output, reserved_targets=self.reserved_targets
        )
        arrays = candidate_arrays(candidates)
        batched = {key: jnp.asarray(value[None]) for key, value in arrays.items()}
        logits = np.asarray(score_candidates(jax_output, batched)[0], dtype=np.float64)
        legal = arrays["mask"]
        masked = np.where(legal, logits, -np.inf)
        if self.deterministic:
            action = int(np.argmax(masked))
        else:
            stable = masked - np.max(masked[legal])
            probability = np.where(legal, np.exp(stable), 0.0)
            probability /= probability.sum()
            action = int(self.rng.choice(len(probability), p=probability))
        old_logp, entropy = categorical_stats(
            jnp.asarray(logits[None], dtype=jnp.float32),
            jnp.asarray([action]),
            jnp.asarray(legal[None]),
        )
        task = candidates[action].task()
        self.decision_count += 1
        if self.collect:
            if unit_index in self.pending:
                raise RuntimeError("unit received a new task before previous outcome")
            self.pending[unit_index] = {
                "global": np.asarray(encoded["global"], np.float16),
                "board": np.asarray(encoded["board"], np.float16),
                "unit": np.asarray(encoded["units"][unit_index], np.float16),
                "candidates": arrays,
                "action": action,
                "old_logp": float(np.asarray(old_logp[0])),
                "old_entropy": float(np.asarray(entropy[0])),
                "value": float(np.asarray(output["value"])),
                "unit_index": int(unit_index),
                "operation": task.operation,
                "start_step": int(observation.get("step", 0) or 0),
            }
        return task

    def observe_outcome(
        self,
        *,
        observation: Mapping[str, Any],
        unit_index: int,
        task: UnitTask,
        status: str,
        start_step: int,
        end_step: int,
    ) -> None:
        self.outcome_counts[status] = self.outcome_counts.get(status, 0) + 1
        if not self.collect:
            return
        record = self.pending.pop(unit_index, None)
        if record is None:
            raise RuntimeError("task outcome has no matching behavior-policy record")
        success = status == "success"
        reward = REWARD_BY_OPERATION[task.operation] if success else -1.0
        duration = max(1, int(end_step) - int(start_step) + 1)
        record.update({
            "end_step": int(end_step),
            "duration_turns": duration,
            "status": status,
            "reward": float(reward - 0.002 * max(0, duration - 1)),
            "terminal": status == "unit_removed",
        })
        self.transitions.append(record)

    def finalize_episode(self, terminal_reward: float) -> list[dict[str, Any]]:
        for unit_index, record in list(self.pending.items()):
            record.update({
                "end_step": 719,
                "duration_turns": max(1, 720 - int(record["start_step"])),
                "status": "episode_terminal",
                "reward": -0.25,
                "terminal": True,
            })
            self.transitions.append(record)
            self.pending.pop(unit_index, None)
        for record in self.transitions:
            record["episode_terminal_reward"] = float(terminal_reward)
        return self.transitions

    def audit(self) -> dict:
        return {
            "decisions": self.decision_count,
            "closed_transitions": len(self.transitions),
            "pending": len(self.pending),
            "outcomes": dict(sorted(self.outcome_counts.items())),
            "selection": "argmax" if self.deterministic else "masked_candidate_sample",
        }
