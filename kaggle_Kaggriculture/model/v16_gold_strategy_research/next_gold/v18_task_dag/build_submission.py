#!/usr/bin/env python3
"""Build the P0-B task-DAG candidate on the exact frozen V17 submission."""

from __future__ import annotations

import base64
import hashlib
import json
import tarfile
import zlib
from pathlib import Path


HERE = Path(__file__).resolve().parent
PARENT = HERE.parents[1] / "top_complete_portfolio" / "main.py"
PARENT_SHA = "b52e62545fb6bdc93f9e947f9a829e348dd6119ee9daf7d8eba7df9aec29a4b1"


def payload(value) -> str:
    raw = json.dumps(value, separators=(",", ":")).encode()
    return repr(base64.b85encode(zlib.compress(raw, 9)).decode())


def compact_dag() -> dict:
    source = json.loads((HERE / "task_dag.json").read_text())
    result = {}
    for route, body in source["routes"].items():
        result[route] = {
            step: [[n["actor"], n["position"], n["order"], n["deadline"], n["value"]] for n in nodes]
            for step, nodes in body["by_step"].items()
        }
    return result


APPENDIX = r'''

# --- V18 P0-B frozen task-DAG/local-repair overlay ---
_V18_PARENT = agent
_V18_DAG = json.loads(zlib.decompress(base64.b85decode(__DAG_PAYLOAD__)).decode())
_V18_MOVES = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}
_V18_ACCESS = {(4, 4), (5, 4), (4, 5), (5, 5)}
_V18_URGENT = {"DIG", "PLANT", "WATER", "FEED", "CARE", "PLACE"}
_V18_STATE = {
    0: {"last": -1, "route": "default", "prev_obs": None, "prev_action": None},
    1: {"last": -1, "route": "default", "prev_obs": None, "prev_action": None},
}

def _v18_step(obs):
    return int(_get(obs, "step", int(_get(obs, "day", 0) or 0) * 24 + int(_get(obs, "hour", 0) or 0)) or 0)

def _v18_positions(obs):
    farm = obs["farms"][_seat(obs)]
    return [tuple(map(int, farm["farmer"])), *[tuple(map(int, p)) for p in (farm.get("hands") or [])]]

def _v18_inventories(obs, n):
    values = [dict(v or {}) for v in (obs.get("private", {}).get("inventories", []) or [])]
    values.extend({} for _ in range(max(0, n - len(values))))
    return values[:n]

def _v18_tile(obs, pos):
    x, y = pos
    grid = obs["farms"][_seat(obs)]["tiles"]
    if not (0 <= y < len(grid) and 0 <= x < len(grid[y])):
        return "LOCKED"
    return grid[y][x]

def _v18_valid(obs, actor, order):
    if not order or order[0] == "PASS":
        return True
    positions = _v18_positions(obs)
    if actor >= len(positions):
        return False
    pos = positions[actor]
    tile = _v18_tile(obs, pos)
    inv = _v18_inventories(obs, len(positions))[actor]
    op = str(order[0])
    if op in _V18_MOVES:
        dx, dy = _V18_MOVES[op]
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
        return pos in _V18_ACCESS and len(order) > 2 and int(obs["private"]["shed"].get(order[1], 0) or 0) > 0
    if op == "DROP":
        return pos in _V18_ACCESS and sum(int(v or 0) for v in inv.values()) > 0
    if op == "PLACE":
        return len(order) > 1 and int(inv.get(order[1], 0) or 0) > 0
    return True

def _v18_toward(src, dst):
    if src[0] < dst[0]: return ["EAST"]
    if src[0] > dst[0]: return ["WEST"]
    if src[1] < dst[1]: return ["SOUTH"]
    if src[1] > dst[1]: return ["NORTH"]
    return ["PASS"]

def _v18_cap_pickups(obs, orders):
    remaining = {k: max(0, int(v or 0)) for k, v in obs["private"]["shed"].items()}
    result = []
    for raw in orders:
        order = list(raw or ["PASS"])
        if len(order) >= 3 and order[0] == "PICKUP":
            item = order[1]
            requested = max(0, int(order[2] or 0))
            executable = min(requested, remaining.get(item, 0))
            remaining[item] = max(0, remaining.get(item, 0) - executable)
            order = ["PASS"] if executable <= 0 else ["PICKUP", item, executable]
        result.append(order)
    return result

def _v18_transition_failed(before, action, after):
    old_pos, new_pos = _v18_positions(before), _v18_positions(after)
    old_inv = _v18_inventories(before, len(old_pos))
    new_inv = _v18_inventories(after, len(new_pos))
    same_day = int(before.get("day", 0) or 0) == int(after.get("day", 0) or 0)
    orders = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
    failed = []
    for actor, order in enumerate(orders):
        if actor >= len(old_pos) or not order or order[0] == "PASS": continue
        op, pos = str(order[0]), old_pos[actor]
        if op not in _V18_URGENT | {"HARVEST", "PICKUP", "BUILD_COOP", "BUILD_PASTURE"}: continue
        old_tile, new_tile = _v18_tile(before, pos), _v18_tile(after, pos)
        ok = True
        if op == "DIG": ok = new_tile != old_tile
        elif op == "PLANT": ok = isinstance(new_tile, dict) and new_tile.get("kind") == "PLANT" and new_tile.get("crop") == order[1]
        elif op == "WATER": ok = (not same_day) or (isinstance(new_tile, dict) and bool(new_tile.get("watered_today")))
        elif op == "HARVEST":
            oy = int(old_tile.get("yield_units", 0) or 0) if isinstance(old_tile, dict) else 0
            ny = int(new_tile.get("yield_units", 0) or 0) if isinstance(new_tile, dict) else 0
            ok = ny < oy or new_tile is None
        elif op in {"BUILD_COOP", "BUILD_PASTURE"}: ok = isinstance(new_tile, dict) and new_tile.get("kind") == op.replace("BUILD_", "")
        elif op == "FEED": ok = (not same_day) or (isinstance(new_tile, dict) and bool(new_tile.get("fed_today")))
        elif op == "CARE": ok = (not same_day) or (isinstance(new_tile, dict) and bool(new_tile.get("cared_today")))
        elif op == "PLACE":
            item = order[1]
            if item in {"COW", "SHEEP", "GOOSE"}:
                animal = new_tile.get("animal") if isinstance(new_tile, dict) else None
                kind = animal.get("kind") if isinstance(animal, dict) else animal
                ok = kind == item
            else: ok = actor < len(new_inv) and int(new_inv[actor].get(item, 0) or 0) < int(old_inv[actor].get(item, 0) or 0)
        elif op == "PICKUP":
            item = order[1]
            ok = (not same_day) or (actor < len(new_inv) and int(new_inv[actor].get(item, 0) or 0) > int(old_inv[actor].get(item, 0) or 0))
        if not ok:
            failed.append([actor, list(pos), list(order), int(before.get("day", 0) or 0) * 24 + 23, 200])
    return failed

def _v18_jobs(route, step, horizon=8):
    jobs = []
    table = _V18_DAG[route]
    for future in range(step, min(719, step + max(6, min(12, horizon)))):
        jobs.extend(table.get(str(future), []))
    return jobs

def _v18_first_order(obs, actor, job):
    _source_actor, target, order, _deadline, _value = job
    pos = _v18_positions(obs)[actor]
    target = tuple(target)
    op = order[0]
    inv = _v18_inventories(obs, len(_v18_positions(obs)))[actor]
    need = "WHEAT" if op == "FEED" else order[1] if op == "PLACE" and len(order) > 1 else None
    if need and int(inv.get(need, 0) or 0) <= 0:
        shed = int(obs["private"]["shed"].get(need, 0) or 0)
        if shed <= 0: return None
        if pos in _V18_ACCESS: return ["PICKUP", need, min(6, shed)]
        gate = min(_V18_ACCESS, key=lambda p: abs(pos[0] - p[0]) + abs(pos[1] - p[1]))
        return _v18_toward(pos, gate)
    return list(order) if pos == target else _v18_toward(pos, target)

def _v18_beam(obs, route, actors, missed):
    step, positions = _v18_step(obs), _v18_positions(obs)
    jobs = list(missed) + _v18_jobs(route, step, 8)
    choices = {}
    for actor in actors:
        rows = []
        for index, job in enumerate(jobs):
            order = _v18_first_order(obs, actor, job)
            if not order or not _v18_valid(obs, actor, order): continue
            target, deadline, value = tuple(job[1]), int(job[3]), float(job[4])
            dist = abs(positions[actor][0] - target[0]) + abs(positions[actor][1] - target[1])
            score = value - 4.0 * dist - 100.0 * max(0, step + dist + 1 - deadline)
            rows.append((score, index, order))
        choices[actor] = sorted(rows, reverse=True)[:6]
    beam = [(0.0, frozenset(), {})]
    for actor in actors:
        expanded = list(beam)
        for total, used, first in beam:
            for value, index, order in choices.get(actor, []):
                if index not in used: expanded.append((total + value, used | {index}, dict(first, **{str(actor): order})))
        beam = sorted(expanded, key=lambda row: row[0], reverse=True)[:32]
    return {int(k): v for k, v in beam[0][2].items()} if beam and beam[0][0] > 0 else {}

def _v18_needed(obs, job):
    _actor, target, order, _deadline, _value = job
    tile, op = _v18_tile(obs, tuple(target)), order[0]
    if op == "HARVEST": return isinstance(tile, dict) and int(tile.get("yield_units", 0) or 0) > 0
    if op == "FEED": return isinstance(tile, dict) and bool(tile.get("animal")) and not tile.get("fed_today")
    if op == "PLANT": return tile is None and int(obs["private"]["seeds"].get(order[1], 0) or 0) > 0
    if op == "PLACE" and order[1] in {"COW", "SHEEP", "GOOSE"}: return isinstance(tile, dict) and tile.get("kind") in {"PASTURE", "COOP"} and not tile.get("animal")
    return False

__version__ = "v18-p0b-task-dag-rc1"
del agent
def agent(obs, configuration=None):
    try:
        action = _V18_PARENT(obs, configuration)
        seat, step = _seat(obs), _v18_step(obs)
        state = _V18_STATE[seat]
        if step == 0 or step < int(state.get("last", -1)):
            state.update(last=step, route="default", prev_obs=None, prev_action=None)
        state["last"] = step
        if step >= 72:
            shops = list((_get(obs, "town", {}) or {}).get("unlocked_shops", []) or [])
            state["route"] = "yarn" if shops and str(shops[0]) == "YARN_STORE" else "default"
        missed = []
        if state.get("prev_obs") is not None and state.get("prev_action") is not None:
            missed = _v18_transition_failed(state["prev_obs"], state["prev_action"], obs)
        positions = _v18_positions(obs)
        orders = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
        orders.extend([["PASS"]] * max(0, len(positions) - len(orders)))
        orders = _v18_cap_pickups(obs, orders[:len(positions)])
        broken = sorted({int(j[0]) for j in missed if int(j[0]) < len(positions) and orders[int(j[0])][0] == "PASS"})
        for actor, order in _v18_beam(obs, state["route"], broken, missed).items():
            if _v18_valid(obs, actor, order): orders[actor] = order
        current = _V18_DAG[state["route"]].get(str(step), [])
        for job in current:
            if job[2][0] not in {"HARVEST", "FEED", "PLACE", "PLANT"} or not _v18_needed(obs, job): continue
            target = tuple(job[1])
            for actor, pos in enumerate(positions):
                if pos == target and orders[actor][0] == "PASS" and _v18_valid(obs, actor, job[2]):
                    orders[actor] = list(job[2]); break
        for job in _v18_jobs(state["route"], step, 8):
            op, deadline, target = job[2][0], int(job[3]), tuple(job[1])
            if op not in {"DIG", "WATER", "FEED", "CARE"} or deadline - step > 2: continue
            for actor, pos in enumerate(positions):
                if pos != target or orders[actor][0] != "PASS": continue
                if op == "DIG":
                    tile = _v18_tile(obs, pos)
                    if not (isinstance(tile, dict) and tile.get("kind") == "WEED"): continue
                if _v18_valid(obs, actor, job[2]): orders[actor] = list(job[2])
        action = copy.deepcopy(action)
        action["farmer"], action["hands"] = orders[0], orders[1:len(positions)]
        state["prev_obs"], state["prev_action"] = copy.deepcopy(obs), copy.deepcopy(action)
        return action
    except Exception:
        return _V18_PARENT(obs, configuration)
'''


def main() -> int:
    if hashlib.sha256(PARENT.read_bytes()).hexdigest() != PARENT_SHA:
        raise RuntimeError("exact V17 parent hash mismatch")
    appendix = APPENDIX.replace("__DAG_PAYLOAD__", payload(compact_dag()))
    target = HERE / "main.py"
    target.write_text(PARENT.read_text(encoding="utf-8") + appendix, encoding="utf-8")
    archive = HERE / "submission.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(target, arcname="main.py")
    manifest = {
        "candidate": "V18 P0-B task-DAG local repair RC1",
        "parent_main_sha256": PARENT_SHA,
        "main_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "archive_bytes": archive.stat().st_size,
        "single_file": True,
        "runtime_dependencies": "Python standard library only",
        "development_evidence": {"date_source": "2026-08-25", "seeds": [50000, 50007], "games": 112},
        "research_decision": "FAIL standalone gold gate; packaged only because user explicitly requested both P0 submissions",
        "remote_submitted": False,
    }
    (HERE / "submission_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
