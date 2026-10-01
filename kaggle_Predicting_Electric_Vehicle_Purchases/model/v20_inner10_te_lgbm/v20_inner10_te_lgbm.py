# -*- coding: utf-8 -*-
"""v20：v6 配方仅将目标编码内层折数由 5 提高到 10，缩小支持度错配。"""

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
    base.N_INNER = 10
    base.main()
    result_path = OUT_DIR / "cv_results.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["model"] = "v6 multiscale nested TE with 10 inner folds + shallow LightGBM"
    result["hypothesis"] = "10 inner folds reduce fit-vs-validation TE support mismatch while preserving blockwise label isolation"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
