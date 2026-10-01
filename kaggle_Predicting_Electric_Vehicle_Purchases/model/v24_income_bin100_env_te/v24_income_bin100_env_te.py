# -*- coding: utf-8 -*-
"""v24：在 v6 上只增加收入百元箱×环保等级的多尺度嵌套目标编码。"""

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
    base.TE_KEYS = dict(base.TE_KEYS)
    base.TE_KEYS["income_bin100_env"] = ["_income_bin100", "Environmental_Concern_Level"]
    base.main()
    result_path = OUT_DIR / "cv_results.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["model"] = "v6 plus multiscale nested income-bin100 x environment target encoding"
    result["hypothesis"] = "smooth the strongest exact income-environment lookup across neighboring income values"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
