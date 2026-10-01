# -*- coding: utf-8 -*-
"""v19：以严格 leave-one-out TE 替换 v6 的内层五折 TE，消除训练/推理支持度错配。"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np


OUT_DIR = Path(__file__).resolve().parent
BASE_PATH = OUT_DIR.parent / "v6_multiscale_te_lgbm" / "v6_multiscale_te_lgbm.py"
SPEC = importlib.util.spec_from_file_location("v6_multiscale_te_lgbm_base", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"无法载入 {BASE_PATH}")
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)


def encode_key_loo(
    train_codes: np.ndarray,
    test_codes: np.ndarray,
    y: np.ndarray,
    fit_idx: np.ndarray,
    valid_idx: np.ndarray,
    inner_folds: list[tuple[np.ndarray, np.ndarray]],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """训练行只剔除自身标签；验证与测试仍只使用外层训练折标签。"""
    del inner_folds
    fit_codes = train_codes[fit_idx]
    valid_codes = train_codes[valid_idx]
    n_categories = int(max(train_codes.max(), test_codes.max())) + 1
    y_fit = y[fit_idx].astype(np.float64)
    prior = float(y_fit.mean())
    total_count = np.bincount(fit_codes, minlength=n_categories).astype(np.float64)
    total_sum = np.bincount(fit_codes, weights=y_fit, minlength=n_categories)

    fit_block = np.empty((len(fit_idx), len(base.SMOOTHS)), dtype=np.float32)
    valid_block = np.empty((len(valid_idx), len(base.SMOOTHS)), dtype=np.float32)
    test_block = np.empty((len(test_codes), len(base.SMOOTHS)), dtype=np.float32)
    for j, smooth in enumerate(base.SMOOTHS):
        fit_block[:, j] = (
            (total_sum[fit_codes] - y_fit + smooth * prior)
            / (total_count[fit_codes] - 1.0 + smooth)
        )
        mapping = (total_sum + smooth * prior) / (total_count + smooth)
        valid_block[:, j] = mapping[valid_codes]
        test_block[:, j] = mapping[test_codes]
    return fit_block, valid_block, test_block


def main() -> None:
    base.OUT_DIR = OUT_DIR
    base.N_FOLDS = 5
    base.encode_key = encode_key_loo
    base.main()
    result_path = OUT_DIR / "cv_results.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["model"] = "multiscale strict leave-one-out TE + digit/frequency fingerprints + shallow LightGBM"
    result["te_training_scheme"] = "leave-one-out within each outer training fold"
    result["te_support_match_note"] = "fit rows use all other outer-fit labels; validation/test use all outer-fit labels"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
