#!/usr/bin/env python3
"""V17-preserving 6--12 step task-DAG beam repair overlay."""

from __future__ import annotations

import copy
import sys
import time
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import task_dag  # noqa: E402


MOVES = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}
URGENT = {"DIG", "PLANT", "WATER", "FEED", "CARE", "PLACE"}
SAFE_OPPORTUNISTIC = {"DIG", "WATER", "FEED", "CARE"}
ACCESS = {(4, 4), (5, 4), (4, 5), (5, 5)}
_STREAMS = {name: task_dag.route_stream(name)[0] for name in task_dag.ROUTES}
_DAGS = {name: task_dag.extract(name) for name in task_dag.ROUTES}


def _step(obs: dict[str, Any]) -> int:
    return int(obs.get("step", int(obs.get("day", 0) or 0) * 24 + int(obs.get("hour", 0) or 0)) or 0)


def _seat(obs: dict[str, Any]) -> int:
    return 1 if int(obs.get("player", 0) or 0) == 1 else 0


def _positions(obs: dict[str, Any]) -> list[tuple[int, int]]:
    farm = obs["farms"][_seat(obs)]
    return [tuple(map(int, farm["farmer"])), *[tuple(map(int, p)) for p in farm.get("hands", [])]]


def _inventories(obs: dict[str, Any], n: int) -> list[dict[str, int]]:
    values = [dict(v or {}) for v in obs.get("private", {}).get("inventories", [])]
    values.extend({} for _ in range(max(0, n - len(values))))
    return values[:n]


def _tile(obs: dict[str, Any], pos: tuple[int, int]) -> Any:
    x, y = pos
    grid = obs["farms"][_seat(obs)]["tiles"]
    if not (0 <= y < len(grid) and 0 <= x < len(grid[y])):
        return "LOCKED"
    return grid[y][x]


def _valid(obs: dict[str, Any], actor: int, order: list[Any]) -> bool:
    if not order or order[0] == "PASS":
        return True
    positions = _positions(obs)
    if actor >= len(positions):
        return False
    pos = positions[actor]
    tile = _tile(obs, pos)
    inv = _inventories(obs, len(positions))[actor]
    op = str(order[0])
    if op in MOVES:
        dx, dy = MOVES[op]
        grid = obs["farms"][_seat(obs)]["tiles"]
        return 0 <= pos[0] + dx < len(grid) and 0 <= pos[1] + dy < len(grid)
    if op == "DIG":
        return tile not in (None, "LOCKED") and not (isinstance(tile, dict) and tile.get("animal"))
    if op == "PLANT":
        return tile is None and len(order) > 1 and int(obs["private"]["seeds"].get(order[1], 0) or 0) > 0
    if op == "WATER":
        return isinstance(tile, dict) and tile.get("kind") == "PLANT" and not tile.get("watered_today")
    if op == "HARVEST":
        return isinstance(tile, dict) and int(tile.get("yield_units", 0) or 0) > 0
    if op == "FERTILIZE":
        return isinstance(tile, dict) and tile.get("kind") == "PLANT" and int(inv.get("FERTILIZER", 0) or 0) > 0
    if op in {"BUILD_COOP", "BUILD_PASTURE"}:
        return tile is None
    if op == "FEED":
        return isinstance(tile, dict) and bool(tile.get("animal")) and not tile.get("fed_today") and int(inv.get("WHEAT", 0) or 0) > 0
    if op == "CARE":
        return isinstance(tile, dict) and bool(tile.get("animal")) and not tile.get("cared_today")
    if op == "COLLECT_FERTILIZER":
        return isinstance(tile, dict) and bool(tile.get("fertilizer_available"))
    if op == "PICKUP":
        return pos in ACCESS and len(order) > 2 and int(obs["private"]["shed"].get(order[1], 0) or 0) > 0
    if op == "DROP":
        return pos in ACCESS and sum(int(v or 0) for v in inv.values()) > 0
    if op == "PLACE":
        return len(order) > 1 and int(inv.get(order[1], 0) or 0) > 0
    return True


def _toward(src: tuple[int, int], dst: tuple[int, int]) -> list[str]:
    if src[0] < dst[0]:
        return ["EAST"]
    if src[0] > dst[0]:
        return ["WEST"]
    if src[1] < dst[1]:
        return ["SOUTH"]
    if src[1] > dst[1]:
        return ["NORTH"]
    return ["PASS"]


def _cap_atomic_pickups(obs: dict[str, Any], orders: list[list[Any]]) -> tuple[list[list[Any]], int]:
    """Make concurrent shed withdrawals resource-complete.

    Frozen V17 validates each PICKUP independently. If several workers request
    the same stock in one atomic step, late orders can still be rejected. Keep
    engine order and cap the aggregate; this changes only otherwise rejected
    quantities and therefore has an exact local certificate.
    """
    remaining = {k: max(0, int(v or 0)) for k, v in obs["private"]["shed"].items()}
    result, edits = [], 0
    for raw in orders:
        order = list(raw or ["PASS"])
        if len(order) >= 3 and order[0] == "PICKUP":
            item = order[1]
            requested = max(0, int(order[2] or 0))
            executable = min(requested, remaining.get(item, 0))
            remaining[item] = max(0, remaining.get(item, 0) - executable)
            if executable <= 0:
                order = ["PASS"]
                edits += 1
            elif executable != requested:
                order[2] = executable
                edits += 1
        result.append(order)
    return result, edits


class RepairPlanner:
    """Small abstract beam. It runs only after a concrete deviation trigger."""

    def __init__(self, route: str, horizon: int = 8, width: int = 32):
        self.route = route
        self.horizon = min(12, max(6, int(horizon)))
        self.width = max(8, int(width))
        self.dag = _DAGS[route]

    def jobs(self, step: int) -> list[dict[str, Any]]:
        hi = step + self.horizon
        return [n for n in self.dag["nodes"] if n["actor"] != "market" and step <= int(n["step"]) < hi and n.get("position")]

    def _first_order(self, obs: dict[str, Any], actor: int, job: dict[str, Any]) -> list[Any] | None:
        pos = _positions(obs)[actor]
        target = tuple(job["position"])
        order = list(job["order"])
        op = order[0]
        inv = _inventories(obs, len(_positions(obs)))[actor]
        need = "WHEAT" if op == "FEED" else order[1] if op == "PLACE" and len(order) > 1 else None
        if need and int(inv.get(need, 0) or 0) <= 0:
            shed = int(obs["private"]["shed"].get(need, 0) or 0)
            if shed <= 0:
                return None
            if pos in ACCESS:
                return ["PICKUP", need, min(6, shed)]
            gate = min(ACCESS, key=lambda p: abs(pos[0] - p[0]) + abs(pos[1] - p[1]))
            return _toward(pos, gate)
        return order if pos == target else _toward(pos, target)

    def plan(self, obs: dict[str, Any], actors: list[int],
             extra_jobs: list[dict[str, Any]] | None = None) -> tuple[dict[int, list[Any]], float]:
        """Enumerate task assignments, then retain a width-limited beam.

        State is (assigned-mask, score, first-orders).  Completion value,
        deadline slack and travel are the abstract rollout objective.  This is
        intentionally a repair oracle, not an alternative season planner.
        """
        step = _step(obs)
        positions = _positions(obs)
        jobs = list(extra_jobs or []) + self.jobs(step)
        candidates: dict[int, list[tuple[float, int, list[Any]]]] = {}
        for actor in actors:
            rows = []
            for j, job in enumerate(jobs):
                order = self._first_order(obs, actor, job)
                if not order or not _valid(obs, actor, order):
                    continue
                target = tuple(job["position"])
                dist = abs(positions[actor][0] - target[0]) + abs(positions[actor][1] - target[1])
                finish = step + dist + 1
                lateness = max(0, finish - int(job["deadline"]))
                wait = max(0, int(job["step"]) - finish)
                score = float(job["value"]) - 4.0 * dist - 100.0 * lateness - 0.25 * wait
                rows.append((score, j, order))
            candidates[actor] = sorted(rows, reverse=True)[:6]

        beam: list[tuple[float, frozenset[int], dict[int, list[Any]]]] = [(0.0, frozenset(), {})]
        for actor in actors:
            expanded = list(beam)
            for total, used, first in beam:
                for value, j, order in candidates.get(actor, []):
                    if j in used:
                        continue
                    expanded.append((total + value, used | {j}, {**first, actor: order}))
            beam = sorted(expanded, key=lambda x: x[0], reverse=True)[: self.width]
        best = beam[0]
        return best[2], best[0]


def _transition_success(before: dict[str, Any], action: dict[str, Any],
                        after: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Audit actual engine transitions, not merely pre-action legality."""
    old_pos, new_pos = _positions(before), _positions(after)
    orders = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
    old_inv = _inventories(before, len(old_pos))
    new_inv = _inventories(after, len(new_pos))
    same_day = int(before.get("day", 0) or 0) == int(after.get("day", 0) or 0)
    failed: list[dict[str, Any]] = []
    metrics = {"attempted": 0, "completed": 0, "harvest_units": 0,
               "deadline_attempted": 0, "deadline_completed": 0}
    for actor, order in enumerate(orders):
        if actor >= len(old_pos) or not order or order[0] == "PASS":
            continue
        op, pos = str(order[0]), old_pos[actor]
        if op not in URGENT | {"HARVEST", "PICKUP", "DROP", "BUILD_COOP", "BUILD_PASTURE"} | set(MOVES):
            continue
        metrics["attempted"] += 1
        if op in URGENT:
            metrics["deadline_attempted"] += 1
        old_tile = _tile(before, pos)
        new_tile = _tile(after, pos)
        ok = True
        if op in MOVES:
            dx, dy = MOVES[op]
            ok = actor < len(new_pos) and new_pos[actor] == (pos[0] + dx, pos[1] + dy)
        elif op == "DIG":
            ok = new_tile != old_tile
        elif op == "PLANT":
            ok = isinstance(new_tile, dict) and new_tile.get("kind") == "PLANT" and new_tile.get("crop") == order[1]
        elif op == "WATER":
            ok = (not same_day) or (isinstance(new_tile, dict) and bool(new_tile.get("watered_today")))
        elif op == "HARVEST":
            old_yield = int(old_tile.get("yield_units", 0) or 0) if isinstance(old_tile, dict) else 0
            new_yield = int(new_tile.get("yield_units", 0) or 0) if isinstance(new_tile, dict) else 0
            ok = new_yield < old_yield or new_tile is None
            if ok:
                metrics["harvest_units"] += old_yield
        elif op in {"BUILD_COOP", "BUILD_PASTURE"}:
            ok = isinstance(new_tile, dict) and new_tile.get("kind") == op.removeprefix("BUILD_")
        elif op == "FEED":
            ok = (not same_day) or (isinstance(new_tile, dict) and bool(new_tile.get("fed_today")))
        elif op == "CARE":
            ok = (not same_day) or (isinstance(new_tile, dict) and bool(new_tile.get("cared_today")))
        elif op == "PLACE":
            item = order[1]
            if item in {"COW", "SHEEP", "GOOSE"}:
                animal = new_tile.get("animal") if isinstance(new_tile, dict) else None
                kind = animal.get("kind") if isinstance(animal, dict) else animal
                ok = kind == item
            else:
                # PLACE on a shed-access structure is a selective deposit.
                ok = actor < len(new_inv) and int(new_inv[actor].get(item, 0) or 0) < int(old_inv[actor].get(item, 0) or 0)
        elif op == "PICKUP":
            item = order[1]
            ok = (not same_day) or (actor < len(new_inv) and int(new_inv[actor].get(item, 0) or 0) > int(old_inv[actor].get(item, 0) or 0))
        elif op == "DROP":
            ok = actor >= len(new_inv) or sum(int(v or 0) for v in new_inv[actor].values()) < sum(int(v or 0) for v in old_inv[actor].values())
        if ok:
            metrics["completed"] += 1
            if op in URGENT:
                metrics["deadline_completed"] += 1
        elif op not in MOVES:
            failed.append({
                "id": f"missed:s{_step(before)}:u{actor}:{op}",
                "route": "runtime", "step": _step(after), "day": int(before.get("day", 0) or 0),
                "hour": int(after.get("hour", 0) or 0), "actor": actor,
                "position": list(pos), "order": list(order), "release": _step(after),
                "deadline": int(before.get("day", 0) or 0) * 24 + 23,
                "value": 200 if op in URGENT else 100,
            })
    return failed, metrics


def make_agent(mode: str = "candidate", horizon: int = 8):
    if mode not in {"candidate", "parent"}:
        raise ValueError(mode)
    # A fresh isolated import is essential: the frozen submission keeps route
    # and repair state in module globals. Never import the mutable research
    # helper ``portfolio_policy.py`` as the parent.
    frozen = task_dag.load_frozen_parent()
    parent = frozen.agent
    streams = _STREAMS
    planners = {name: RepairPlanner(name, horizon=horizon) for name in task_dag.ROUTES}
    local = {
        0: {"last": -1, "route": "default", "prev_obs": None, "prev_action": None},
        1: {"last": -1, "route": "default", "prev_obs": None, "prev_action": None},
    }
    stats = {
        "calls": 0, "parent_exact_calls": 0, "modified_calls": 0,
        "modified_units": 0, "deviation_repairs": 0,
        "opportunistic_repairs": 0, "planner_calls": 0,
        "planner_ns": 0, "predicted_parent_invalid": 0,
        "predicted_candidate_invalid": 0, "harvest_units": 0,
        "deadline_actions": 0, "total_ns": 0,
        "actual_attempted_actions": 0, "actual_completed_actions": 0,
        "actual_execution_failures": 0,
        "actual_deadline_attempted": 0, "actual_deadline_completed": 0,
        "atomic_pickup_caps": 0,
        "lifecycle_repairs": 0, "modified_ops": {},
    }

    def policy(obs: dict[str, Any], configuration=None):
        del configuration
        started = time.perf_counter_ns()
        seat, step = _seat(obs), _step(obs)
        state = local[seat]
        if step == 0 or step < state["last"]:
            state.update(last=step, route="default", prev_obs=None, prev_action=None)
        state["last"] = step
        if step >= 72:
            shops = list((obs.get("town") or {}).get("unlocked_shops") or [])
            state["route"] = "yarn" if shops and shops[0] == "YARN_STORE" else "default"
        route = state["route"]
        action = parent(obs)
        stats["calls"] += 1
        missed: list[dict[str, Any]] = []
        if state["prev_obs"] is not None and state["prev_action"] is not None:
            missed, audit = _transition_success(state["prev_obs"], state["prev_action"], obs)
            stats["actual_attempted_actions"] += audit["attempted"]
            stats["actual_completed_actions"] += audit["completed"]
            stats["actual_execution_failures"] += len(missed)
            stats["harvest_units"] += audit["harvest_units"]
            stats["actual_deadline_attempted"] += audit["deadline_attempted"]
            stats["actual_deadline_completed"] += audit["deadline_completed"]
        if mode == "parent":
            stats["parent_exact_calls"] += 1
            stats["total_ns"] += time.perf_counter_ns() - started
            state["prev_obs"], state["prev_action"] = copy.deepcopy(obs), copy.deepcopy(action)
            return action

        positions = _positions(obs)
        out_orders = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
        out_orders.extend([["PASS"]] * max(0, len(positions) - len(out_orders)))
        changed = False

        out_orders, pickup_edits = _cap_atomic_pickups(obs, out_orders[:len(positions)])
        if pickup_edits:
            changed = True
            stats["modified_units"] += pickup_edits
            stats["atomic_pickup_caps"] += pickup_edits
            stats["modified_ops"]["PICKUP_CAP"] = stats["modified_ops"].get("PICKUP_CAP", 0) + pickup_edits

        # Trigger 1: the preceding non-PASS service was actually rejected by
        # the engine and the affected worker is now idle. A replay PASS alone
        # is never treated as evidence of deviation.
        broken = sorted({int(j["actor"]) for j in missed
                         if int(j["actor"]) < len(positions)
                         and out_orders[int(j["actor"])][0] == "PASS"})
        if broken:
            t0 = time.perf_counter_ns()
            replacements, certificate = planners[route].plan(obs, broken, missed)
            stats["planner_ns"] += time.perf_counter_ns() - t0
            stats["planner_calls"] += 1
            if certificate > 0:
                for actor, order in replacements.items():
                    if order != out_orders[actor] and _valid(obs, actor, order):
                        out_orders[actor] = order
                        changed = True
                        stats["modified_units"] += 1
                        stats["deviation_repairs"] += 1
                        op = str(order[0])
                        stats["modified_ops"][op] = stats["modified_ops"].get(op, 0) + 1

        # Single economic revision: recover only an exact current-step
        # lifecycle service whose target visibly still needs work, using an
        # idle worker already on that tile. No route movement is displaced.
        current_jobs = [j for j in planners[route].jobs(step)
                        if int(j["step"]) == step and j["order"][0] in {"HARVEST", "FEED", "PLACE", "PLANT"}]
        for job in current_jobs:
            target = tuple(job["position"])
            op = str(job["order"][0])
            tile = _tile(obs, target)
            needed = (
                (op == "HARVEST" and isinstance(tile, dict) and int(tile.get("yield_units", 0) or 0) > 0)
                or (op == "FEED" and isinstance(tile, dict) and bool(tile.get("animal")) and not tile.get("fed_today"))
                or (op == "PLANT" and tile is None and int(obs["private"]["seeds"].get(job["order"][1], 0) or 0) > 0)
                or (op == "PLACE" and job["order"][1] in {"COW", "SHEEP", "GOOSE"}
                    and isinstance(tile, dict) and tile.get("kind") in {"PASTURE", "COOP"} and not tile.get("animal"))
            )
            if not needed:
                continue
            for actor, pos in enumerate(positions):
                order = list(job["order"])
                if pos == target and out_orders[actor][0] == "PASS" and _valid(obs, actor, order):
                    out_orders[actor] = order
                    changed = True
                    stats["modified_units"] += 1
                    stats["lifecycle_repairs"] += 1
                    stats["modified_ops"][op] = stats["modified_ops"].get(op, 0) + 1
                    break

        # Trigger 2: strictly local certificate. Only a late daily obligation
        # visible in current state may replace PASS; no travel is displaced.
        jobs = planners[route].jobs(step)
        for actor in range(len(positions)):
            if out_orders[actor][0] != "PASS":
                continue
            here = []
            current_tile = _tile(obs, positions[actor])
            for job in jobs:
                if tuple(job["position"]) != positions[actor] or int(job["deadline"]) - step > 2:
                    continue
                op = job["order"][0]
                if op == "DIG":
                    # A route DIG on an ordinary plant is not an emergency.
                    if not (isinstance(current_tile, dict) and current_tile.get("kind") == "WEED"):
                        continue
                elif op not in {"WATER", "FEED", "CARE"}:
                    continue
                here.append(job)
            for job in sorted(here, key=lambda j: (-int(j["value"]), int(j["deadline"]))):
                order = list(job["order"])
                if _valid(obs, actor, order):
                    out_orders[actor] = order
                    changed = True
                    stats["modified_units"] += 1
                    stats["opportunistic_repairs"] += 1
                    op = str(order[0])
                    stats["modified_ops"][op] = stats["modified_ops"].get(op, 0) + 1
                    break

        for actor, order in enumerate(out_orders[:len(positions)]):
            if not _valid(obs, actor, order):
                stats["predicted_candidate_invalid"] += 1
            if order and order[0] in URGENT:
                stats["deadline_actions"] += 1
        if changed:
            action = copy.deepcopy(action)
            action["farmer"] = out_orders[0]
            action["hands"] = out_orders[1:len(positions)]
            stats["modified_calls"] += 1
        else:
            stats["parent_exact_calls"] += 1
        stats["total_ns"] += time.perf_counter_ns() - started
        state["prev_obs"], state["prev_action"] = copy.deepcopy(obs), copy.deepcopy(action)
        return action

    policy.stats = stats
    policy.__name__ = f"v18_task_dag_{mode}"
    return policy


agent = make_agent("candidate")
