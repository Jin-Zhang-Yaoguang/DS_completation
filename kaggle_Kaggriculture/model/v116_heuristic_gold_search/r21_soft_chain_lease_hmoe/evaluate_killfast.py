#!/usr/bin/env python3
"""Bind the frozen R20 kill-fast contract to the R21 candidate."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
SHARED = HERE.parent / "r20_stateful_feasible_tile_bundle_hmoe" / "evaluate_killfast.py"
RESULT = HERE / "killfast_result.json"


def main() -> None:
    spec = importlib.util.spec_from_file_location("r21_shared_killfast_contract", SHARED)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    module.HERE = HERE
    module.RESULT = RESULT
    module.DAILY = HERE / "daily_diagnostics.json"
    try:
        module.main()
    except SystemExit:
        pass
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    result["schema"] = "v116-r21-killfast-evidence-v1"
    RESULT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
