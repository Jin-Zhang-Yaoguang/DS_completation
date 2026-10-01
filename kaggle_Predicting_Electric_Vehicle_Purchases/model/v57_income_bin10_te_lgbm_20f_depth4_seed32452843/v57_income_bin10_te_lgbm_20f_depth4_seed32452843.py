# -*- coding: utf-8 -*-
"""v57：第二个独立全路径 seed 的 20 折 depth-4 income-bin10 LGBM。"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


OUT_DIR = Path(__file__).resolve().parent
SOURCE = OUT_DIR.parent / "v29_income_bin10_te_lgbm" / "v29_income_bin10_te_lgbm.py"
FULL_SEED = 32_452_843


def main() -> None:
    spec = importlib.util.spec_from_file_location("v29_income_bin10_te_lgbm", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 v29：{SOURCE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.OUT_DIR = OUT_DIR
    module.base.SEED = FULL_SEED
    module.base.N_FOLDS = 20
    module.base.LGB_PARAMS["max_depth"] = 4
    module.base.LGB_PARAMS["num_leaves"] = 15
    for key in (
        "random_state",
        "bagging_seed",
        "feature_fraction_seed",
        "data_random_seed",
    ):
        module.base.LGB_PARAMS[key] = FULL_SEED
    module.main()

    result_path = OUT_DIR / "cv_results.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["model"] = "20-fold income-bin10 TE depth-4 LightGBM, full seed 32452843"
    result["full_seed"] = FULL_SEED
    result["hypothesis"] = (
        "a second independent depth-4 path should reduce the variance of v51's "
        "validated structural diversity before it enters the final ensemble"
    )
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
