# -*- coding: utf-8 -*-
"""v21：保持 v6 模型参数，仅提高有效特征密度，减少弱列对列采样的稀释。"""

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

FOCUSED_TE_KEYS = {
    key: cols
    for key, cols in base.TE_KEYS.items()
    if key
    in {
        "Annual_Income_USD",
        "Daily_Commute_km",
        "Age",
        "Environmental_Concern_Level",
        "Home_Charging_Possible",
        "Subsidy_Available",
        "Range_Anxiety_Level",
        "income_bin100",
        "income_subsidy",
        "income_env",
    }
}
ORIGINAL_BUILD_STATIC = base.build_static_features


def build_focused_static(train, test):
    x_train, x_test, keys_train, keys_test = ORIGINAL_BUILD_STATIC(train, test)
    keep = []
    for column in x_train.columns:
        if column in base.RAW_FEATURES:
            keep.append(column)
        elif column.startswith(("Annual_Income_USD_digit_", "Daily_Commute_km_digit_")):
            keep.append(column)
        elif column in {
            "freq_Annual_Income_USD",
            "freq_Daily_Commute_km",
            "freq_Environmental_Concern_Level",
            "freq_Home_Charging_Possible",
            "freq_Subsidy_Available",
            "freq_Range_Anxiety_Level",
        }:
            keep.append(column)
        elif column.startswith("freq_key_"):
            keep.append(column)
    return x_train[keep].copy(), x_test[keep].copy(), keys_train, keys_test


def main() -> None:
    base.OUT_DIR = OUT_DIR
    base.N_FOLDS = 5
    base.N_INNER = 5
    base.TE_KEYS = FOCUSED_TE_KEYS
    base.build_static_features = build_focused_static
    base.main()
    result_path = OUT_DIR / "cv_results.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["model"] = "focused multiscale nested TE + high-signal static fingerprints + shallow LightGBM"
    result["hypothesis"] = "remove weak fingerprints and TE keys that dilute 30 percent column sampling"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
