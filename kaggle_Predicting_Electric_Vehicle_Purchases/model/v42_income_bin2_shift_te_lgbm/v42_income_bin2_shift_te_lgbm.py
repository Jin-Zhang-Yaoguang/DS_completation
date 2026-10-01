# -*- coding: utf-8 -*-
"""v42：在 v29 上新增 2 美元宽、半格偏移的收入多尺度目标编码。"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd


OUT_DIR = Path(__file__).resolve().parent
SOURCE = OUT_DIR.parent / "v29_income_bin10_te_lgbm" / "v29_income_bin10_te_lgbm.py"
SPEC = importlib.util.spec_from_file_location("v29_income_bin10_te_lgbm", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"无法载入 {SOURCE}")
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)

ORIGINAL_FACTORIZE_JOINT = base.factorize_joint_extended


def factorize_joint_extended(
    train: pd.DataFrame, test: pd.DataFrame, cols: list[str]
) -> tuple[np.ndarray, np.ndarray]:
    if cols != ["_income_bin2_shift"]:
        return ORIGINAL_FACTORIZE_JOINT(train, test, cols)
    values = pd.concat(
        [train["Annual_Income_USD"], test["Annual_Income_USD"]],
        ignore_index=True,
    )
    keys = np.floor((values + 1.0) / 2.0).astype(np.int64)
    codes, _ = pd.factorize(keys, sort=True)
    return codes[: len(train)].astype(np.int32), codes[len(train) :].astype(np.int32)


def main() -> None:
    base.OUT_DIR = OUT_DIR
    # v29.main 会把其底层模块重新绑定到本模块的 factorize_joint_extended，
    # 因此必须替换 v29 模块级符号，而不能只提前修改底层模块。
    base.factorize_joint_extended = factorize_joint_extended
    base.base.TE_KEYS["income_bin10"] = ["_income_bin10"]
    base.base.TE_KEYS["income_bin2_shift"] = ["_income_bin2_shift"]
    base.main()

    result_path = OUT_DIR / "cv_results.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["model"] = "v29 plus shifted 2-dollar income-bin multiscale TE"
    result["hypothesis"] = (
        "adjacent integer income values share a generator-level random effect; "
        "strict 10-fold univariate TE favored floor((income+1)/2) over exact income "
        "and the existing 10-dollar bin"
    )
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
