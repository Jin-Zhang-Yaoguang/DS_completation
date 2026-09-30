#!/usr/bin/env python3
"""Compress a champion replay into daily actor option queues, not move actions."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1] / "v120_hierarchical_top5_distillation/replay_data/raw/episode-104547425-replay.json"
OUTPUT = HERE / "role_option_contract_diagnostic.json"
MOVE = {"NORTH", "SOUTH", "EAST", "WEST"}


def actor_positions(replay: dict, turn: int, seat: int) -> list[tuple[int, int]]:
    farm = replay["steps"][turn][seat]["observation"]["farms"][seat]
    raw = [farm.get("farmer") or [4, 4], *(farm.get("hands") or [])]
    return [tuple(map(int, value)) for value in raw]


def compressed_path(replay: dict, seat: int, actor: int, start: int, stop: int) -> list[list[int]]:
    points = []
    for turn in range(max(0, start), stop + 1):
        positions = actor_positions(replay, turn, seat)
        if actor < len(positions) and (not points or points[-1] != positions[actor]):
            points.append(positions[actor])
    if len(points) <= 1:
        return [list(points[-1])] if points else []
    corners = []
    previous_direction = None
    for index in range(1, len(points)):
        direction = (points[index][0] - points[index - 1][0], points[index][1] - points[index - 1][1])
        if previous_direction is not None and direction != previous_direction:
            corners.append(points[index - 1])
        previous_direction = direction
    corners.append(points[-1])
    return [list(point) for point in corners]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=str(SOURCE))
    parser.add_argument("--output", default=str(OUTPUT))
    parser.add_argument("--seat", type=int, default=0)
    parser.add_argument("--teacher", default="OceanMix")
    args = parser.parse_args()
    source = Path(args.source).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    raw_bytes = source.read_bytes()
    replay = json.loads(raw_bytes)
    seat = 1 if args.seat == 1 else 0
    days = {str(day): {"actors": {}, "market_diagnostic": {}} for day in range(30)}
    option_count = 0
    market_count = 0
    previous_task_turn: dict[tuple[int, int], int] = {}
    for turn in range(719):
        day, hour = divmod(turn, 24)
        obs = replay["steps"][turn][seat]["observation"]
        farm = obs["farms"][seat]
        positions = [farm.get("farmer") or [4, 4], *(farm.get("hands") or [])]
        action = replay["steps"][turn + 1][seat].get("action") or {}
        units = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
        for actor, raw in enumerate(units):
            order = list(raw or ["PASS"])
            if not order or order[0] in MOVE or order[0] == "PASS" or actor >= len(positions):
                continue
            x, y = map(int, positions[actor])
            path_start = previous_task_turn.get((day, actor), day * 24) + (1 if (day, actor) in previous_task_turn else 0)
            path = compressed_path(replay, seat, actor, path_start, turn)
            days[str(day)]["actors"].setdefault(str(actor), []).append(
                {"hour": hour, "target": [x, y], "path": path, "order": order}
            )
            previous_task_turn[(day, actor)] = turn
            option_count += 1
        market = [list(value) for value in (action.get("market") or []) if value and value[0] != "PASS"]
        if market:
            # This channel is retained only to measure how much fidelity the
            # option executor loses. It is forbidden from a promotable model.
            days[str(day)]["market_diagnostic"][str(hour)] = market
            market_count += len(market)
    for day in range(30):
        bucket = days[str(day)]
        totals: dict[tuple[str, str], dict] = {}
        sequence = 0
        for hour, orders in sorted(bucket["market_diagnostic"].items(), key=lambda item: int(item[0])):
            for order in orders:
                op = str(order[0]); item = str(order[1]) if len(order) >= 2 else ""
                key = (op, item)
                quantity = max(0, int(order[2] or 0)) if len(order) >= 3 else 1
                row = totals.setdefault(key, {"op": op, "item": item, "quantity": 0, "orders": 0, "first_hour": int(hour), "first_index": sequence, "max_batch": 0})
                row["orders"] += 1
                row["quantity"] += quantity
                row["max_batch"] = max(row["max_batch"], quantity)
                sequence += 1
        bucket["market_day_budget"] = sorted(totals.values(), key=lambda row: row["first_index"])
        phases = {}
        for phase in range(6):
            phase_totals: dict[tuple[str, str], dict] = {}
            sequence = 0
            for hour, orders in sorted(bucket["market_diagnostic"].items(), key=lambda item: int(item[0])):
                if int(hour) // 4 != phase:
                    continue
                for order in orders:
                    op = str(order[0]); item = str(order[1]) if len(order) >= 2 else ""; key = (op, item)
                    quantity = max(0, int(order[2] or 0)) if len(order) >= 3 else 1
                    row = phase_totals.setdefault(key, {"op": op, "item": item, "quantity": 0, "orders": 0, "phase": phase, "first_index": sequence, "max_batch": 0})
                    row["orders"] += 1; row["quantity"] += quantity; row["max_batch"] = max(row["max_batch"], quantity); sequence += 1
            phases[str(phase)] = sorted(phase_totals.values(), key=lambda row: row["first_index"])
        bucket["market_phase_budgets"] = phases
        windows = {}
        for width in (1, 2, 3, 4, 6):
            groups = {}
            for window in range((24 + width - 1) // width):
                window_totals: dict[tuple[str, str], dict] = {}
                sequence = 0
                for hour, orders in sorted(bucket["market_diagnostic"].items(), key=lambda item: int(item[0])):
                    if int(hour) // width != window: continue
                    for order in orders:
                        op = str(order[0]); item = str(order[1]) if len(order) >= 2 else ""; key = (op, item)
                        quantity = max(0, int(order[2] or 0)) if len(order) >= 3 else 1
                        row = window_totals.setdefault(key, {"op": op, "item": item, "quantity": 0, "orders": 0, "phase": window, "first_index": sequence, "max_batch": 0})
                        row["orders"] += 1; row["quantity"] += quantity; row["max_batch"] = max(row["max_batch"], quantity); sequence += 1
                groups[str(window)] = sorted(window_totals.values(), key=lambda row: row["first_index"])
            windows[str(width)] = groups
        bucket["market_window_budgets"] = windows
    payload = {
        "schema": "kaggriculture-role-option-contract-diagnostic-v1",
        "source": {
            "episode_id": int(source.name.split("-")[1]),
            "replay_sha256": hashlib.sha256(raw_bytes).hexdigest(),
            "teacher": args.teacher,
            "seat": seat,
        },
        "runtime_contract": {
            "unit_move_actions_stored": False,
            "unit_action_source": "state_recovered_path_to_daily_semantic_options",
            "market_diagnostic_only": True,
            "promotable": False,
        },
        "option_count": option_count,
        "market_order_count": market_count,
        "days": days,
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "option_count": option_count, "market_order_count": market_count}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
