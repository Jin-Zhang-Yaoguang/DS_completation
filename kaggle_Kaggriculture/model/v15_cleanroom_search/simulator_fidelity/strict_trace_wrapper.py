#!/usr/bin/env python3
"""Fail-closed structural validator for kaggriculture-cppsim trace files.

The upstream C++ validator indexes ``truth[t]`` for every declared turn and
then indexes ``truth[-1]`` for the final state, but does not first prove that
the TRUTH block has exactly ``turns + 1`` rows.  This wrapper must pass before
the C++ semantic validator is allowed to run.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


EXPECTED_CONFIG_VALUES = 11
EXPECTED_MARKET_INVENTORY_FIELDS = 9


def _integers(tokens: list[str], context: str) -> list[int]:
    try:
        return [int(token) for token in tokens]
    except ValueError as exc:
        raise ValueError(f"{context}: expected integer tokens") from exc


def validate_trace(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path.resolve()),
        "pass": False,
        "seed": None,
        "declared_turns": None,
        "action_rows": 0,
        "truth_marker_count": 0,
        "truth_state_count": 0,
        "expected_truth_state_count": None,
        "inventory_fields_per_truth_state": EXPECTED_MARKET_INVENTORY_FIELDS,
        "error": None,
    }
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        if not lines:
            raise ValueError("empty trace")

        header = lines[0].split()
        if len(header) != 2:
            raise ValueError("header must contain exactly seed and turn count")
        seed, turns = _integers(header, "header")
        if turns < 0:
            raise ValueError("declared turn count is negative")
        result["seed"] = seed
        result["declared_turns"] = turns
        result["expected_truth_state_count"] = turns + 1

        index = 1
        if index < len(lines) and lines[index].split()[:1] == ["CONFIG"]:
            config = lines[index].split()
            if len(config) != EXPECTED_CONFIG_VALUES + 1:
                raise ValueError(
                    "CONFIG must contain exactly "
                    f"{EXPECTED_CONFIG_VALUES} values, found {len(config) - 1}"
                )
            try:
                [float(token) for token in config[1:]]
            except ValueError as exc:
                raise ValueError("CONFIG contains a non-numeric value") from exc
            index += 1

        expected_action_rows = turns * 2
        for action_row in range(expected_action_rows):
            if index >= len(lines):
                raise ValueError(
                    f"trace ended after {action_row}/{expected_action_rows} action rows"
                )
            tokens = lines[index].split()
            if tokens == ["TRUTH"]:
                raise ValueError(
                    f"TRUTH marker appeared after {action_row}/{expected_action_rows} action rows"
                )
            values = _integers(tokens, f"action row {action_row}")
            if len(values) < 2:
                raise ValueError(f"action row {action_row}: missing unit/order counts")
            units, orders = values[0], values[1]
            if units < 0 or orders < 0:
                raise ValueError(f"action row {action_row}: negative unit/order count")
            expected_tokens = 2 + 3 * (units + orders)
            if len(values) != expected_tokens:
                raise ValueError(
                    f"action row {action_row}: {len(values)} tokens, "
                    f"expected {expected_tokens}"
                )
            result["action_rows"] += 1
            index += 1

        result["truth_marker_count"] = sum(line.strip() == "TRUTH" for line in lines)
        if index >= len(lines) or lines[index].strip() != "TRUTH":
            raise ValueError("TRUTH marker missing at the exact post-action boundary")
        if result["truth_marker_count"] != 1:
            raise ValueError(
                f"expected exactly one TRUTH marker, found {result['truth_marker_count']}"
            )
        index += 1

        truth_rows = lines[index:]
        result["truth_state_count"] = len(truth_rows)
        if len(truth_rows) != turns + 1:
            raise ValueError(
                f"truth_state_count={len(truth_rows)} but declared_turns+1={turns + 1}"
            )

        expected_truth_tokens = 2 + EXPECTED_MARKET_INVENTORY_FIELDS
        for state_index, line in enumerate(truth_rows):
            tokens = line.split()
            if len(tokens) != expected_truth_tokens:
                raise ValueError(
                    f"truth state {state_index}: {len(tokens)} tokens, "
                    f"expected {expected_truth_tokens}"
                )
            try:
                money = [float(tokens[0]), float(tokens[1])]
            except ValueError as exc:
                raise ValueError(
                    f"truth state {state_index}: invalid money value"
                ) from exc
            if not all(math.isfinite(value) for value in money):
                raise ValueError(f"truth state {state_index}: non-finite money value")
            _integers(tokens[2:], f"truth state {state_index} inventory")

        result["pass"] = True
    except (OSError, ValueError) as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("traces", type=Path, nargs="+")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results = [validate_trace(path) for path in args.traces]
    payload = {
        "schema": "kaggriculture-cppsim-strict-trace-wrapper-v1",
        "pass": bool(results) and all(result["pass"] for result in results),
        "trace_count": len(results),
        "results": results,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
