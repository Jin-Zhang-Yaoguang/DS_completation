#!/usr/bin/env python3
"""Prove RC2 safety repairs preserved every retained target-gate outcome."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
RC1 = HERE / "frozen_gate_results_rc1.json"
RC2 = HERE / "frozen_gate_results_rc2.json"
OUTPUT = HERE / "target_rc1_rc2_parity.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path: Path) -> dict[tuple[int, int], tuple[object, ...]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        (int(row["episode_id"]), int(row["seat"])): (
            row["candidate_reward"], row["v76_reward"], row["margin"], row["steps"]
        )
        for row in data["rows"] if row["panel"] == "target_yarn_2_or_3"
    }


def main() -> int:
    left, right = rows(RC1), rows(RC2)
    shared = sorted(set(left) & set(right))
    exact = sum(left[key] == right[key] for key in shared)
    result = {
        "schema": "v118-target-rc1-rc2-parity-v1",
        "rc1_results_sha256": sha256(RC1),
        "rc2_results_sha256": sha256(RC2),
        "rc1_rows": len(left),
        "rc2_rows": len(right),
        "shared_rows": len(shared),
        "exact_reward_margin_step_rows": exact,
        "different_rows": len(shared) - exact,
        "gate": "PASS" if len(left) == len(right) == len(shared) == exact == 128 else "FAIL",
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["gate"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
