# -*- coding: utf-8 -*-
"""v40：在 v6 的精确通勤值之外新增 1km 分箱的多尺度目标编码。"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd


OUT_DIR = Path(__file__).resolve().parent
BASE_PATH = OUT_DIR.parent / "v6_multiscale_te_lgbm" / "v6_multiscale_te_lgbm.py"
SPEC = importlib.util.spec_from_file_location("v6_multiscale_te_lgbm_base", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"无法载入 {BASE_PATH}")
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)

ORIGINAL_FACTORIZE_JOINT = base.factorize_joint


def factorize_joint_extended(
    train: pd.DataFrame, test: pd.DataFrame, cols: list[str]
) -> tuple[np.ndarray, np.ndarray]:
    if cols != ["_commute_bin1"]:
        return ORIGINAL_FACTORIZE_JOINT(train, test, cols)
    values = pd.concat(
        [train["Daily_Commute_km"], test["Daily_Commute_km"]], ignore_index=True
    )
    keys = np.floor(values).astype(np.int64)
    codes, _ = pd.factorize(keys, sort=True)
    return codes[: len(train)].astype(np.int32), codes[len(train) :].astype(np.int32)


def main() -> None:
    base.OUT_DIR = OUT_DIR
    base.factorize_joint = factorize_joint_extended
    base.TE_KEYS["commute_bin1"] = ["_commute_bin1"]
    base.main()

    result_path = OUT_DIR / "cv_results.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["model"] = "v6 plus multiscale 1km commute-bin target encoding"
    result["hypothesis"] = (
        "pool neighboring exact commute values at a 1km resolution to expose a "
        "nonlinear local target rate not represented by exact-value TE alone"
    )
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
