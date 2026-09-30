"""Persistent task contracts and deterministic unit compiler for V12 G1."""

from __future__ import annotations

from dataclasses import dataclass
from collections import Counter
from pathlib import Path
import sys
from typing import Any, Callable, Mapping

from flax import serialization
import jax
import jax.numpy as jnp
import numpy as np


HERE = Path(__file__).resolve().parent
V113 = HERE.parent / "v113_simulator_hmoe_ppo"
if str(V113) not in sys.path:
    sys.path.insert(0, str(V113))

import action_space as space  # noqa: E402
import features  # noqa: E402
from build_unit_task_dataset import (  # noqa: E402
    ITEMS, QUANTITY_TIERS, ROLE_NAMES, TASK_OPERATIONS,
)
from model_unit_task_hmoe import UnitTaskHMoE  # noqa: E402
from enterprise_contracts_v12 import resolve_contract  # noqa: E402


@dataclass(frozen=True)
class UnitTask:
    role: str
    operation: str
    item: str
    quantity: int
    target_x: int
    target_y: int
    duration: int

    def __post_init__(self):
        if self.role not in ROLE_NAMES:
            raise ValueError("unknown task role")
        if self.operation not in TASK_OPERATIONS:
            raise ValueError("unknown task operation")
        if self.item not in ITEMS:
            raise ValueError("unknown task item")
        if not 0 <= self.target_x < 10 or not 0 <= self.target_y < 10:
            raise ValueError("task target outside board")
        if not 1 <= self.duration <= 24:
            raise ValueError("task duration must be in 1..24")


@dataclass
class ActiveTask:
    contract: UnitTask
    started_step: int
    blocked_turns: int = 0


def _positions(observation: Mapping[str, Any]) -> list[tuple[int, int]]:
    player = int(observation.get("player", 0) or 0)
    farm = list(observation.get("farms", []) or [])[player]
    raw = [farm.get("farmer", [0, 0]), *list(farm.get("hands", []) or [])]
    return [(int(position[0]), int(position[1])) for position in raw]


def _movement_candidates(origin: tuple[int, int], target: tuple[int, int]) -> list[str]:
    horizontal = "EAST" if origin[0] < target[0] else "WEST" if origin[0] > target[0] else None
    vertical = "SOUTH" if origin[1] < target[1] else "NORTH" if origin[1] > target[1] else None
    return [move for move in (horizontal, vertical) if move is not None]


def _task_order(task: UnitTask) -> list:
    if task.operation == "REST":
        return ["PASS"]
    if task.operation == "PLANT":
        return ["PLANT", task.item]
    if task.operation in {"PICKUP", "PLACE"}:
        return [task.operation, task.item, task.quantity]
    return [task.operation]


def _log_softmax(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    shifted = values - np.max(values)
    return shifted - np.log(np.exp(shifted).sum())


def _tile(observation: Mapping[str, Any], x: int, y: int) -> Any:
    player = int(observation.get("player", 0) or 0)
    farms = list(observation.get("farms", []) or [])
    if not 0 <= player < len(farms):
        return "LOCKED"
    tiles = list(farms[player].get("tiles", []) or [])
    return tiles[y][x] if 0 <= y < len(tiles) and 0 <= x < len(tiles[y]) else "LOCKED"


def _task_candidates(
    observation: Mapping[str, Any], unit_index: int,
    reserved_targets: set[tuple[int, int, str, str]] | None = None,
) -> list[tuple[str, str, int, int, int]]:
    """Enumerate state-feasible semantic tasks, not primitive movements."""
    origin = _positions(observation)[unit_index]
    private = observation.get("private", {}) or {}
    seeds = private.get("seeds", {}) or {}
    shed = private.get("shed", {}) or {}
    inventories = list(private.get("inventories", []) or [])
    inventory = inventories[unit_index] if unit_index < len(inventories) else {}
    day = int(observation.get("step", 0) or 0) // 24
    hour = int(observation.get("step", 0) or 0) % 24
    remaining_turns = 24 - hour
    reserved_targets = reserved_targets or set()
    candidates: list[tuple[str, str, int, int, int]] = [
        ("REST", "NONE", 0, origin[0], origin[1])
    ]
    for y in range(10):
        for x in range(10):
            if abs(x - origin[0]) + abs(y - origin[1]) >= 24:
                continue
            if abs(x - origin[0]) + abs(y - origin[1]) + 1 > remaining_turns:
                continue
            tile = _tile(observation, x, y)
            if tile == "LOCKED":
                continue
            if tile is None:
                for crop in space.CROPS:
                    if int(seeds.get(crop, 0) or 0) > 0:
                        candidates.append(("PLANT", crop, 0, x, y))
                candidates.append(("BUILD_COOP", "NONE", 0, x, y))
                candidates.append(("BUILD_PASTURE", "NONE", 0, x, y))
            # DIG is destructive.  It is a semantic option only for weeds;
            # legal-action masks alone cannot distinguish a weed from a crop.
            if isinstance(tile, Mapping) and tile.get("kind") == "WEED":
                candidates.append(("DIG", "NONE", 0, x, y))
            if isinstance(tile, Mapping) and tile.get("kind") == "PLANT":
                if not bool(tile.get("watered_today", False)):
                    candidates.append(("WATER", "NONE", 0, x, y))
                crop = str(tile.get("crop", ""))
                mature = day - int(tile.get("planted_day", day) or 0) >= space.CROP_FIRST_YIELD_DAY.get(crop, 10**9)
                if mature and int(tile.get("yield_units", 0) or 0) > 0:
                    candidates.append(("HARVEST", "NONE", 0, x, y))
                if int(inventory.get("FERTILIZER", 0) or 0) > 0:
                    candidates.append(("FERTILIZE", "NONE", 0, x, y))
            if isinstance(tile, Mapping) and tile.get("animal"):
                if int(tile.get("yield_units", 0) or 0) > 0:
                    candidates.append(("HARVEST", "NONE", 0, x, y))
                if not bool(tile.get("fed_today", False)) and int(inventory.get("WHEAT", 0) or 0) > 0:
                    candidates.append(("FEED", "NONE", 0, x, y))
                if not bool(tile.get("cared_today", False)):
                    candidates.append(("CARE", "NONE", 0, x, y))
                if bool(tile.get("fertilizer_available", False)):
                    candidates.append(("COLLECT_FERTILIZER", "NONE", 0, x, y))
            if (x, y) in space.SHED_ACCESS:
                if any(int(value or 0) > 0 for value in inventory.values()):
                    candidates.append(("DROP", "NONE", 0, x, y))
                for item in space.ITEMS:
                    available = int(shed.get(item, 0) or 0)
                    if available > 0:
                        candidates.append(("PICKUP", item, available, x, y))
                    carried = int(inventory.get(item, 0) or 0)
                    if carried > 0:
                        candidates.append(("PLACE", item, carried, x, y))
            if isinstance(tile, Mapping) and not tile.get("animal"):
                kind = str(tile.get("kind", ""))
                for animal in space.ANIMALS:
                    expected = "COOP" if animal == "GOOSE" else "PASTURE"
                    carried = int(inventory.get(animal, 0) or 0)
                    if kind == expected and carried > 0:
                        candidates.append(("PLACE", animal, min(1, carried), x, y))
    return [
        candidate for candidate in candidates
        if (
            (candidate[3], candidate[4], candidate[0], candidate[1]) not in reserved_targets
            and (candidate[3], candidate[4], "*", "*") not in reserved_targets
        )
        or candidate[0] == "REST"
    ]


class PersistentUnitTaskExecutor:
    """Hold each planned task until success, failure, or timeout."""

    def __init__(self, planner: Callable[[Any, int], UnitTask]):
        self.planner = planner
        self.tasks: dict[int, ActiveTask] = {}
        self.last_step = -1
        self.planner_calls = 0
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.timed_out_tasks = 0
        self.blocked_turns = 0
        self.planned_operations: Counter[str] = Counter()
        self.completed_operations: Counter[str] = Counter()
        self.failure_reasons: Counter[str] = Counter()
        self._turn_reservations: set[tuple[int, int, str, str]] = set()

    def reset(self) -> None:
        self.tasks.clear()
        self.last_step = -1
        self.planner_calls = 0
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.timed_out_tasks = 0
        self.blocked_turns = 0
        self.planned_operations.clear()
        self.completed_operations.clear()
        self.failure_reasons.clear()
        self._turn_reservations.clear()

    def _plan(self, observation, unit_index: int, step: int) -> ActiveTask:
        self.planner_calls += 1
        reservations = {
            (
                active.contract.target_x, active.contract.target_y,
                active.contract.operation, active.contract.item,
            )
            for index, active in self.tasks.items() if index != unit_index
        }
        reservations.update({
            (active.contract.target_x, active.contract.target_y, "*", "*")
            for index, active in self.tasks.items() if index != unit_index
        })
        reservations.update(self._turn_reservations)
        set_reservations = getattr(self.planner, "set_reserved_targets", None)
        if callable(set_reservations):
            set_reservations(reservations)
        task = self.planner(observation, unit_index)
        self._turn_reservations.add((task.target_x, task.target_y, "*", "*"))
        self.planned_operations[task.operation] += 1
        active = ActiveTask(task, step)
        self.tasks[unit_index] = active
        return active

    def _outcome(
        self,
        observation: Mapping[str, Any],
        unit_index: int,
        active: ActiveTask,
        status: str,
        step: int,
    ) -> None:
        callback = getattr(self.planner, "observe_outcome", None)
        if callable(callback):
            callback(
                observation=observation,
                unit_index=unit_index,
                task=active.contract,
                status=status,
                start_step=active.started_step,
                end_step=step,
            )

    def act(self, observation: Mapping[str, Any]) -> dict:
        step = int(observation.get("step", 0) or 0)
        if step < self.last_step or (step == 0 and self.last_step > 0):
            self.reset()
        positions = _positions(observation)
        self._turn_reservations = {
            (active.contract.target_x, active.contract.target_y, "*", "*")
            for active in self.tasks.values()
        }
        for index, active in list(self.tasks.items()):
            if index >= len(positions):
                self._outcome(observation, index, active, "unit_removed", step)
        self.tasks = {index: task for index, task in self.tasks.items() if index < len(positions)}
        orders: list[list] = []
        for unit_index, origin in enumerate(positions):
            active = self.tasks.get(unit_index)
            if active is not None and step - active.started_step >= active.contract.duration:
                self.timed_out_tasks += 1
                self.failure_reasons[f"timeout:{active.contract.operation}"] += 1
                self._outcome(observation, unit_index, active, "timeout", step)
                self.tasks.pop(unit_index, None)
                active = None
            if active is None:
                active = self._plan(observation, unit_index, step)
            task = active.contract
            legal = np.asarray(space.unit_legal_mask(observation, unit_index), dtype=bool)
            if origin != (task.target_x, task.target_y):
                order = ["PASS"]
                for move in _movement_candidates(origin, (task.target_x, task.target_y)):
                    token = int(space.UNIT_INDEX[move])
                    if legal[token]:
                        order = [move]
                        break
                if order[0] == "PASS":
                    active.blocked_turns += 1
                    self.blocked_turns += 1
                    if active.blocked_turns >= 2:
                        self.failed_tasks += 1
                        self.failure_reasons[f"blocked_path:{task.operation}"] += 1
                        self._outcome(observation, unit_index, active, "blocked_path", step)
                        self.tasks.pop(unit_index, None)
                else:
                    active.blocked_turns = 0
                orders.append(order)
                continue

            desired = _task_order(task)
            if desired[0] == "PASS":
                self.completed_tasks += 1
                self.completed_operations[task.operation] += 1
                self._outcome(observation, unit_index, active, "success", step)
                self.tasks.pop(unit_index, None)
                orders.append(desired)
                continue
            token, quantity_token, known = space.unit_token(desired)
            if not known or not legal[int(token)]:
                self.failed_tasks += 1
                reason = "unknown_action" if not known else "illegal_at_target"
                self.failure_reasons[f"{reason}:{task.operation}"] += 1
                self._outcome(observation, unit_index, active, reason, step)
                self.tasks.pop(unit_index, None)
                orders.append(["PASS"])
                continue
            order = space.decode_unit(observation, unit_index, int(token), int(quantity_token))
            if not order or order[0] == "PASS":
                self.failed_tasks += 1
                self.failure_reasons[f"decode_pass:{task.operation}"] += 1
                self._outcome(observation, unit_index, active, "decode_pass", step)
            else:
                self.completed_tasks += 1
                self.completed_operations[task.operation] += 1
                self._outcome(observation, unit_index, active, "success", step)
            self.tasks.pop(unit_index, None)
            orders.append(list(order or ["PASS"]))
        self.last_step = max(self.last_step, step)
        return {
            "farmer": orders[0] if orders else ["PASS"],
            "hands": orders[1:],
            "market": [],
        }

    def audit(self) -> dict:
        report = {
            "active_tasks": len(self.tasks),
            "planner_calls": self.planner_calls,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "timed_out_tasks": self.timed_out_tasks,
            "blocked_turns": self.blocked_turns,
            "market_actions": 0,
            "planned_operations": dict(sorted(self.planned_operations.items())),
            "completed_operations": dict(sorted(self.completed_operations.items())),
            "failure_reasons": dict(sorted(self.failure_reasons.items())),
        }
        planner_audit = getattr(self.planner, "audit", None)
        if callable(planner_audit):
            report["planner"] = planner_audit()
        return report


class UnitTaskBCPolicy:
    """Checkpoint-backed task planner; movement remains deterministic."""

    def __init__(self, checkpoint: Path, contract: str | None = None):
        payload = serialization.msgpack_restore(Path(checkpoint).read_bytes())
        if payload.get("strategy_parent") is not None:
            raise ValueError("V12 unit-task checkpoint must have strategy_parent=null")
        if payload.get("inherits_historical_checkpoint") is not False:
            raise ValueError("historical checkpoint inheritance is forbidden")
        if payload.get("historical_agent_online_action_source") is not False:
            raise ValueError("historical agent online actions are forbidden")
        if payload.get("architecture") != "v114-event-ledger-persistent-unit-task-hmoe-v1":
            raise ValueError("unexpected V12 unit-task architecture")
        self.params = payload["params"]
        self.model = UnitTaskHMoE()
        self.contract = resolve_contract(contract)
        self._apply = jax.jit(
            lambda params, g, b, u: self.model.apply({"params": params}, g, b, u)
        )
        self.decode_calls = 0
        self.candidate_counts: Counter[str] = Counter()
        self.reserved_targets: set[tuple[int, int, str, str]] = set()

    def set_reserved_targets(self, values: set[tuple[int, int, str, str]]) -> None:
        self.reserved_targets = set(values)

    def __call__(self, observation: Mapping[str, Any], unit_index: int) -> UnitTask:
        encoded = features.encode_observation(observation)
        output = jax.tree.map(
            lambda value: np.asarray(value[0]),
            self._apply(
                self.params,
                jnp.asarray(encoded["global"])[None],
                jnp.asarray(encoded["board"])[None],
                jnp.asarray(encoded["units"][unit_index])[None],
            ),
        )
        logp = {
            key: _log_softmax(value) if key == "role_logits" else np.stack([
                _log_softmax(row) for row in value
            ])
            for key, value in output.items() if key.endswith("logits")
        }
        origin = _positions(observation)[unit_index]
        best: tuple[float, UnitTask] | None = None
        candidates = _task_candidates(
            observation, unit_index, reserved_targets=self.reserved_targets
        )
        if self.contract is not None:
            candidates = [
                candidate for candidate in candidates
                if self.contract.allows_task(candidate[0], candidate[1])
            ]
        self.decode_calls += 1
        self.candidate_counts["total"] += len(candidates)
        for operation, item, feasible_quantity, x, y in candidates:
            role = role_for_operation(operation)
            operation_index = TASK_OPERATIONS.index(operation)
            item_index = ITEMS.index(item)
            distance = abs(x - origin[0]) + abs(y - origin[1])
            minimum_duration = min(24, distance + 1)
            maximum_duration = max(minimum_duration, 24 - int(observation.get("step", 0) or 0) % 24)
            duration = max(
                range(minimum_duration, min(24, maximum_duration) + 1),
                key=lambda value: float(logp["duration_logits"][role, value]),
            )
            quantity_index = 0
            if feasible_quantity > 0:
                valid_quantities = [
                    index for index, value in enumerate(QUANTITY_TIERS)
                    if 0 < value <= feasible_quantity
                ] or [1]
                quantity_index = max(
                    valid_quantities,
                    key=lambda index: float(logp["quantity_logits"][role, index]),
                )
            score_value = (
                float(logp["role_logits"][role])
                + float(logp["operation_logits"][role, operation_index])
                + float(logp["target_x_logits"][role, x])
                + float(logp["target_y_logits"][role, y])
                + float(logp["duration_logits"][role, duration])
            )
            if operation in {"PLANT", "PICKUP", "PLACE"}:
                score_value += float(logp["item_logits"][role, item_index])
            if operation in {"PICKUP", "PLACE"}:
                score_value += float(logp["quantity_logits"][role, quantity_index])
            task = UnitTask(
                ROLE_NAMES[role], operation, item,
                QUANTITY_TIERS[quantity_index], x, y, duration,
            )
            if best is None or score_value > best[0]:
                best = (score_value, task)
        if best is None:
            return UnitTask("RECOVERY_IDLE", "REST", "NONE", 0, origin[0], origin[1], 1)
        self.candidate_counts[f"selected:{best[1].operation}"] += 1
        return best[1]

    def audit(self) -> dict:
        return {
            "decode_calls": self.decode_calls,
            "enterprise_contract": self.contract.name if self.contract else None,
            "candidate_counts": dict(sorted(self.candidate_counts.items())),
        }


def role_for_operation(operation: str) -> int:
    if operation in {"PLANT", "WATER", "HARVEST", "FERTILIZE", "DIG"}:
        return 0
    if operation in {
        "BUILD_COOP", "BUILD_PASTURE", "FEED", "COLLECT_FERTILIZER", "CARE",
    }:
        return 1
    if operation in {"PICKUP", "PLACE", "DROP"}:
        return 2
    return 3
