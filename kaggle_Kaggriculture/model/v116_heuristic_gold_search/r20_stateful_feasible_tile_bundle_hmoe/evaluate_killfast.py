#!/usr/bin/env python3
"""Run the frozen single-seed kill-fast gate for R20."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
BASE_RUNNER = HERE.parent / "r16_value_backbone_cap11_hmoe" / "evaluate_killfast.py"
RESULT = HERE / "killfast_result.json"
DAILY = HERE / "daily_diagnostics.json"


def _load_base_runner():
    spec = importlib.util.spec_from_file_location("r20_shared_killfast_runner", BASE_RUNNER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    module.HERE = HERE
    module.MODEL = HERE / "main.py"
    return module


def _daily_assets(rows: list[dict], day: int) -> int:
    return int(next((row.get("assets", 0) for row in rows
                     if int(row.get("day", -1)) == int(day)), 0))


def main() -> None:
    runner = _load_base_runner()
    try:
        runner.main()
    except SystemExit:
        pass

    result = json.loads(RESULT.read_text(encoding="utf-8"))
    daily = json.loads(DAILY.read_text(encoding="utf-8"))
    moves = int(result.get("diagnostics", {}).get("audit", {}).get(
        "directional_moves", 0))
    action_counts = dict(result.get("action_counts", {}))
    care_and_fertilizer = int(action_counts.get("CARE", 0)) \
        + int(action_counts.get("COLLECT_FERTILIZER", 0))
    terminal = dict(result.get("terminal", {}))
    terminal_animals = {str(key): int(value) for key, value in
                        dict(terminal.get("animals", {})).items()}
    expert = str(result.get("diagnostics", {}).get("expert", ""))
    candidate = runner.load_candidate()
    goal = candidate.build_executor(params=None, mode=f"fixed_{expert}").goal(29)
    animal_targets = {str(key): int(value) for key, value in
                      dict(goal.get("animals", {})).items()}
    animal_target_realized = all(
        int(terminal_animals.get(kind, 0)) >= target
        for kind, target in animal_targets.items()
    )
    day9_assets = _daily_assets(daily, 9)
    day12_assets = _daily_assets(daily, 12)

    result["schema"] = "v116-r20-killfast-evidence-v1"
    result["trajectory"] = {
        "day9_assets": day9_assets,
        "day12_assets": day12_assets,
        "care_plus_collect_fertilizer": care_and_fertilizer,
        "expert": expert,
        "animal_targets": animal_targets,
        "terminal_animals": terminal_animals,
    }
    result["gates"].update({
        "directional_moves_le_3600": moves <= 3600,
        "day9_assets_ge_30": day9_assets >= 30,
        "day12_assets_ge_50": day12_assets >= 50,
        "terminal_weeds_zero": int(terminal.get("weeds", 0)) == 0,
        "final_transition_weed_checked": int(terminal.get("weeds", 0)) == 0,
        "expert_animal_targets_realized": animal_target_realized,
        "care_plus_collect_fertilizer_ge_430": care_and_fertilizer >= 430,
    })
    result["passed"] = all(bool(value) for value in result["gates"].values())
    result["decision"] = (
        "KILLFAST_PASS_READY_FOR_PARENT_REVIEW"
        if result["passed"] else "NOT_GOLD_KILLFAST_REJECT"
    )
    RESULT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "schema": result["schema"],
        "bank": result["bank"],
        "step144_assets": result["step144"]["assets"],
        "terminal_assets": terminal.get("assets", 0),
        "terminal_weeds": terminal.get("weeds", 0),
        "directional_moves": moves,
        "trajectory": result["trajectory"],
        "gates": result["gates"],
        "passed": result["passed"],
        "decision": result["decision"],
    }, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
