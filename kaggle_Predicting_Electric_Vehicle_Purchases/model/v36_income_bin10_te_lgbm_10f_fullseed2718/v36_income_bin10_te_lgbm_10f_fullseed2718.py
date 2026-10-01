# -*- coding: utf-8 -*-
"""v36：10 折收入-bin10 配方，同时更换外层、内层和 LightGBM 随机路径。"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


OUT_DIR = Path(__file__).resolve().parent
SOURCE = OUT_DIR.parent / "v29_income_bin10_te_lgbm" / "v29_income_bin10_te_lgbm.py"
FULL_SEED = 2718


def main() -> None:
    spec = importlib.util.spec_from_file_location("v29_income_bin10_te_lgbm", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 v29：{SOURCE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.OUT_DIR = OUT_DIR
    module.base.SEED = FULL_SEED
    module.base.N_FOLDS = 10
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
    result["model"] = "10-fold income-bin10 multiscale TE LightGBM, full seed 2718"
    result["full_seed"] = FULL_SEED
    result["hypothesis"] = (
        "vary outer folds and inner target-encoding partitions in addition to model "
        "subsampling so test-fold averaging removes another source of covariance"
    )
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
