# -*- coding: utf-8 -*-
"""v25：在 v6 的多尺度 TE 中只增加 smoothing=2 的低收缩视图。"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


OUT_DIR = Path(__file__).resolve().parent
BASE_PATH = OUT_DIR.parent / "v6_multiscale_te_lgbm" / "v6_multiscale_te_lgbm.py"
SPEC = importlib.util.spec_from_file_location("v6_multiscale_te_lgbm_base", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"无法载入 {BASE_PATH}")
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)


def main() -> None:
    base.OUT_DIR = OUT_DIR
    base.N_FOLDS = 5
    base.N_INNER = 5
    base.SMOOTHS = (2.0, 5.0, 15.0, 80.0)
    base.main()
    result_path = OUT_DIR / "cv_results.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["model"] = "v6 multiscale nested TE plus smoothing=2 view"
    result["hypothesis"] = "high-cardinality synthetic identity keys may benefit from a lower-shrinkage target-rate view"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
