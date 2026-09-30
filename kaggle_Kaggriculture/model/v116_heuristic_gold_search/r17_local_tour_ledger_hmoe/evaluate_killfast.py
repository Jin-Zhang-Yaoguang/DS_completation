#!/usr/bin/env python3
"""Run the frozen single-seed kill-fast gate for R17.

The mechanics runner is shared with R16 only to keep the observation and
semantic-invalid checks identical.  This wrapper binds it to the R17 source
tree and adds R17's preregistered movement gate.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
BASE_RUNNER = HERE.parent / "r16_value_backbone_cap11_hmoe" / "evaluate_killfast.py"
RESULT = HERE / "killfast_result.json"


def _load_base_runner():
    spec = importlib.util.spec_from_file_location("r17_shared_killfast_runner", BASE_RUNNER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    module.HERE = HERE
    module.MODEL = HERE / "main.py"
    return module


def main() -> None:
    runner = _load_base_runner()
    try:
        runner.main()
    except SystemExit:
        pass

    result = json.loads(RESULT.read_text(encoding="utf-8"))
    moves = int(result.get("diagnostics", {}).get("audit", {}).get(
        "directional_moves", 0))
    result["schema"] = "v116-r17-killfast-evidence-v1"
    result["gates"]["directional_moves_le_3600"] = moves <= 3600
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
        "terminal_assets": result["terminal"]["assets"],
        "directional_moves": moves,
        "gates": result["gates"],
        "passed": result["passed"],
        "decision": result["decision"],
    }, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
