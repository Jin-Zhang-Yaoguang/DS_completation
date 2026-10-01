# -*- coding: utf-8 -*-
"""v27：对内层 OOF 目标编码做重复折叠平均，降低任意一次切分带来的方差。

外层验证集和测试集仍只使用当前外层训练集的标签映射；只有外层训练行的
inner-OOF 编码在三个相互独立的五折切分上取平均，因此不改变泄漏边界。
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
from sklearn.model_selection import StratifiedKFold


OUT_DIR = Path(__file__).resolve().parent
BASE_PATH = OUT_DIR.parent / "v6_multiscale_te_lgbm" / "v6_multiscale_te_lgbm.py"
SPEC = importlib.util.spec_from_file_location("v6_multiscale_te_lgbm_base", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"无法载入 {BASE_PATH}")
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)

N_REPEATS = 3
ORIGINAL_ENCODE_KEY = base.encode_key


def encode_key_repeated(
    train_codes: np.ndarray,
    test_codes: np.ndarray,
    y: np.ndarray,
    fit_idx: np.ndarray,
    valid_idx: np.ndarray,
    inner_folds: list[tuple[np.ndarray, np.ndarray]],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    fit_block, valid_block, test_block = ORIGINAL_ENCODE_KEY(
        train_codes, test_codes, y, fit_idx, valid_idx, inner_folds
    )
    fit_sum = fit_block.astype(np.float64)

    # 第一组沿用 v6 的折叠，新增折叠仅由当前外层训练标签构造。
    # valid_idx[0] 让五个外层折拥有不同但完全可复现的随机种子。
    for repeat in range(1, N_REPEATS):
        splitter = StratifiedKFold(
            base.N_INNER,
            shuffle=True,
            random_state=base.SEED + repeat * 1000 + int(valid_idx[0]),
        )
        repeated_folds = list(
            splitter.split(np.zeros(len(fit_idx)), y[fit_idx])
        )
        repeated_fit, _, _ = ORIGINAL_ENCODE_KEY(
            train_codes,
            test_codes,
            y,
            fit_idx,
            valid_idx,
            repeated_folds,
        )
        fit_sum += repeated_fit

    return (fit_sum / N_REPEATS).astype(np.float32), valid_block, test_block


def main() -> None:
    base.OUT_DIR = OUT_DIR
    base.encode_key = encode_key_repeated
    base.main()

    result_path = OUT_DIR / "cv_results.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["model"] = "v6 multiscale nested TE with repeated inner-fold averaging"
    result["inner_te_repeats"] = N_REPEATS
    result["hypothesis"] = (
        "average leakage-safe inner-OOF encodings across independent partitions "
        "to reduce partition noise while preserving the outer validation boundary"
    )
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
