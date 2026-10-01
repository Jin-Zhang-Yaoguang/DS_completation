# -*- coding: utf-8 -*-
"""v29：在 v6 的精确收入与 100 美元分箱之间加入 10 美元分辨率的多尺度 TE。"""

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
    if cols != ["_income_bin10"]:
        return ORIGINAL_FACTORIZE_JOINT(train, test, cols)
    values = pd.concat(
        [train["Annual_Income_USD"], test["Annual_Income_USD"]],
        ignore_index=True,
    )
    keys = (values // 10).astype(np.int64)
    codes, _ = pd.factorize(keys, sort=True)
    return codes[: len(train)].astype(np.int32), codes[len(train) :].astype(np.int32)


def main() -> None:
    base.OUT_DIR = OUT_DIR
    base.factorize_joint = factorize_joint_extended
    base.TE_KEYS["income_bin10"] = ["_income_bin10"]
    base.main()

    result_path = OUT_DIR / "cv_results.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["model"] = "v6 plus multiscale income-bin10 target encoding"
    result["hypothesis"] = (
        "a 10-dollar neighborhood supplies a distinct middle-resolution estimate "
        "between exact-income identity and the existing 100-dollar neighborhood"
    )
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
