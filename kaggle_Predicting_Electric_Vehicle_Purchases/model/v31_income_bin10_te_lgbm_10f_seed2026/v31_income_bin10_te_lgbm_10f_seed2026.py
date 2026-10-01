# -*- coding: utf-8 -*-
"""v31：v29 收入多分辨率特征，10 外层折，独立 LightGBM 随机种子 2026。"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


OUT_DIR = Path(__file__).resolve().parent
SOURCE = OUT_DIR.parent / "v29_income_bin10_te_lgbm" / "v29_income_bin10_te_lgbm.py"
MODEL_SEED = 2026


def main() -> None:
    spec = importlib.util.spec_from_file_location("v29_income_bin10_te_lgbm", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 v29：{SOURCE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    module.OUT_DIR = OUT_DIR
    module.base.N_FOLDS = 10
    for key in (
        "random_state",
        "bagging_seed",
        "feature_fraction_seed",
        "data_random_seed",
    ):
        module.base.LGB_PARAMS[key] = MODEL_SEED
    module.main()

    result_path = OUT_DIR / "cv_results.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["model"] = "10-fold income-bin10 multiscale TE LightGBM, model seed 2026"
    result["model_seed"] = MODEL_SEED
    result["hypothesis"] = (
        "combine 90-percent outer-fold coverage and income multiresolution TE with "
        "a model-randomness path independent from v14 seed 42"
    )
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
