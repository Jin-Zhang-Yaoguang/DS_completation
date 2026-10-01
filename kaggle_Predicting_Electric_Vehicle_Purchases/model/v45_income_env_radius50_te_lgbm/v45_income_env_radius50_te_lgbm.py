# -*- coding: utf-8 -*-
"""v45：在 v29 上新增同环保等级内收入 ±50 美元的中心邻域 TE。"""

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
ORIGINAL_ENCODE_KEY = base.base.encode_key
RADIUS = 50
SPECIAL_N_INCOME: int | None = None
SPECIAL_N_GROUPS: int | None = None


def factorize_joint_extended(
    train: pd.DataFrame, test: pd.DataFrame, cols: list[str]
) -> tuple[np.ndarray, np.ndarray]:
    global SPECIAL_N_INCOME, SPECIAL_N_GROUPS
    if cols != ["_income_env_radius50"]:
        return ORIGINAL_FACTORIZE_JOINT(train, test, cols)

    combined = pd.concat(
        [
            train[["Annual_Income_USD", "Environmental_Concern_Level"]],
            test[["Annual_Income_USD", "Environmental_Concern_Level"]],
        ],
        ignore_index=True,
    )
    income = combined["Annual_Income_USD"].round().astype(np.int64)
    income_code = (income - income.min()).to_numpy(np.int64)
    env_code, env_levels = pd.factorize(
        combined["Environmental_Concern_Level"], sort=True
    )
    SPECIAL_N_INCOME = int(income_code.max()) + 1
    SPECIAL_N_GROUPS = len(env_levels)
    codes = env_code.astype(np.int64) * SPECIAL_N_INCOME + income_code
    return codes[: len(train)].astype(np.int32), codes[len(train) :].astype(np.int32)


def rolling_neighbor_sum(values: np.ndarray) -> np.ndarray:
    cumulative = np.pad(np.cumsum(values, axis=1), ((0, 0), (1, 0)))
    positions = np.arange(values.shape[1])
    left = np.maximum(0, positions - RADIUS)
    right = np.minimum(values.shape[1], positions + RADIUS + 1)
    return cumulative[:, right] - cumulative[:, left]


def encode_key_extended(
    train_codes: np.ndarray,
    test_codes: np.ndarray,
    y: np.ndarray,
    fit_idx: np.ndarray,
    valid_idx: np.ndarray,
    inner_folds: list[tuple[np.ndarray, np.ndarray]],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if (
        SPECIAL_N_INCOME is None
        or SPECIAL_N_GROUPS is None
        or int(train_codes.max()) < SPECIAL_N_INCOME
    ):
        return ORIGINAL_ENCODE_KEY(
            train_codes, test_codes, y, fit_idx, valid_idx, inner_folds
        )

    fit_codes = train_codes[fit_idx]
    y_fit = y[fit_idx].astype(np.float64)
    n_categories = SPECIAL_N_GROUPS * SPECIAL_N_INCOME
    total_count = np.bincount(fit_codes, minlength=n_categories).astype(np.float64)
    total_sum = np.bincount(
        fit_codes, weights=y_fit, minlength=n_categories
    ).astype(np.float64)
    total_count = total_count.reshape(SPECIAL_N_GROUPS, SPECIAL_N_INCOME)
    total_sum = total_sum.reshape(SPECIAL_N_GROUPS, SPECIAL_N_INCOME)
    prior = float(y_fit.mean())
    smooths = base.base.SMOOTHS

    fit_block = np.empty((len(fit_idx), len(smooths)), dtype=np.float32)
    for _, hold in inner_folds:
        hold_codes = fit_codes[hold]
        hold_count = np.bincount(hold_codes, minlength=n_categories).reshape(
            SPECIAL_N_GROUPS, SPECIAL_N_INCOME
        )
        hold_sum = np.bincount(
            hold_codes, weights=y_fit[hold], minlength=n_categories
        ).reshape(SPECIAL_N_GROUPS, SPECIAL_N_INCOME)
        count = rolling_neighbor_sum(total_count - hold_count)
        target_sum = rolling_neighbor_sum(total_sum - hold_sum)
        flat_count = count.ravel()
        flat_sum = target_sum.ravel()
        for column, smooth in enumerate(smooths):
            mapping = (flat_sum + smooth * prior) / (flat_count + smooth)
            fit_block[hold, column] = mapping[hold_codes]

    count = rolling_neighbor_sum(total_count).ravel()
    target_sum = rolling_neighbor_sum(total_sum).ravel()
    valid_codes = train_codes[valid_idx]
    valid_block = np.empty((len(valid_idx), len(smooths)), dtype=np.float32)
    test_block = np.empty((len(test_codes), len(smooths)), dtype=np.float32)
    for column, smooth in enumerate(smooths):
        mapping = (target_sum + smooth * prior) / (count + smooth)
        valid_block[:, column] = mapping[valid_codes]
        test_block[:, column] = mapping[test_codes]
    return fit_block, valid_block, test_block


def main() -> None:
    base.OUT_DIR = OUT_DIR
    base.factorize_joint_extended = factorize_joint_extended
    base.base.encode_key = encode_key_extended
    base.base.SMOOTHS = (2.0, 5.0, 15.0, 80.0)
    base.base.TE_KEYS["income_bin10"] = ["_income_bin10"]
    base.base.TE_KEYS["income_env_radius50"] = ["_income_env_radius50"]
    base.main()

    result_path = OUT_DIR / "cv_results.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["model"] = "v29 plus centered income +/-50 within environment TE"
    result["income_environment_radius"] = RADIUS
    result["hypothesis"] = (
        "the generator shares target propensity among nearby income values within "
        "the same environmental-concern level; centered neighborhoods avoid the "
        "boundary loss of fixed bins"
    )
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
