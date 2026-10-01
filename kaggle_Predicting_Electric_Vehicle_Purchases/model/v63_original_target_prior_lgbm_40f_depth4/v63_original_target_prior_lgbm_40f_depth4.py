# -*- coding: utf-8 -*-
"""v63：在 v59 matched 40 折上加入原始数据逐特征目标先验。"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd


OUT_DIR = Path(__file__).resolve().parent
SOURCE = OUT_DIR.parent / "v29_income_bin10_te_lgbm" / "v29_income_bin10_te_lgbm.py"
ORIGINAL_DATA = OUT_DIR.parents[1] / "data" / "original_dataset" / "EV_Adoption_and_Range_Anxiety_Dataset.csv"
FULL_SEED = 49_979_687


def main() -> None:
    spec = importlib.util.spec_from_file_location("v29_income_bin10_te_lgbm", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 v29：{SOURCE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original_build = module.base.build_static_features

    def build_static_features(train, test):
        x_train, x_test, keys_train, keys_test = original_build(train, test)
        original = pd.read_csv(ORIGINAL_DATA)
        original_y = (original[module.base.TARGET] == module.base.POS_LABEL).astype(np.float64)
        prior = float(original_y.mean())
        for col in module.base.RAW_FEATURES:
            mapping = (
                pd.DataFrame({col: original[col], "_target": original_y})
                .groupby(col, dropna=False)["_target"]
                .mean()
            )
            name = f"original_target_mean_{col}"
            x_train[name] = train[col].map(mapping).fillna(prior).astype(np.float32)
            x_test[name] = test[col].map(mapping).fillna(prior).astype(np.float32)
        return x_train, x_test, keys_train, keys_test

    module.base.build_static_features = build_static_features
    module.OUT_DIR = OUT_DIR
    module.base.SEED = FULL_SEED
    module.base.N_FOLDS = 40
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
    result["model"] = "matched v59 40-fold depth-4 LightGBM plus original target priors"
    result["full_seed"] = FULL_SEED
    result["matched_baseline"] = "v59_income_bin10_te_lgbm_40f_depth4"
    result["hypothesis"] = (
        "the v62 probe won four of five matched folds; the strongest external-prior "
        "columns are monotonic re-expressions of environmental concern, subsidy, and "
        "range anxiety, increasing strong-signal availability under feature subsampling, "
        "while the original income-label prior supplies a small independent random effect"
    )
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
