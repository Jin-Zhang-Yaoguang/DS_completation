#!/usr/bin/env python3
"""Bind the frozen kill-fast contract to the R23 candidate."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
SHARED = HERE.parent / "r22_observation_valid_frontier_hmoe" / "evaluate_killfast.py"
RESULT = HERE / "killfast_result.json"


def main() -> None:
    spec = importlib.util.spec_from_file_location("r23_shared_killfast_contract", SHARED)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    module.HERE = HERE
    module.RESULT = RESULT
    try:
        module.main()
    except SystemExit:
        pass
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    result["schema"] = "v116-r23-killfast-evidence-v1"
    RESULT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
