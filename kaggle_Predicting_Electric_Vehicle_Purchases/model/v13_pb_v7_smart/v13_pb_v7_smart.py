# -*- coding: utf-8 -*-
"""
v13：PB 探测候选，等权秩融合本地 v7 与公开 Smart Ensemble。

公开 Smart Ensemble 没有配套 OOF，因此本方案不能声明本地验证增益；只用于用户明确
允许的 Public-LB probing。两个成员已各自取得 0.94620 / 0.94621 Public LB。
"""

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata


TARGET = "Will_Buy_EV"
ID_COL = "id"
WEIGHT_V7 = 0.5

OUT_DIR = Path(__file__).resolve().parent
MODEL_DIR = OUT_DIR.parent
DATA_DIR = OUT_DIR.parents[1] / "data"


def pct_rank(values: np.ndarray) -> np.ndarray:
    return rankdata(values) / len(values)


def main() -> None:
    test = pd.read_csv(DATA_DIR / "test.csv", usecols=[ID_COL])
    sample = pd.read_csv(DATA_DIR / "sample_submission.csv")
    v7 = pd.read_csv(MODEL_DIR / "v7_cv_public_blend" / "submission.csv")
    smart = pd.read_csv(OUT_DIR / "public_inputs" / "submission.csv")
    if not v7[ID_COL].equals(test[ID_COL]) or not smart[ID_COL].equals(test[ID_COL]):
        raise ValueError("成员提交的 id 与 test 不一致")

    pred = WEIGHT_V7 * pct_rank(v7[TARGET].to_numpy()) + (1 - WEIGHT_V7) * pct_rank(
        smart[TARGET].to_numpy()
    )
    submission = sample.copy()
    submission[TARGET] = pred
    if submission.shape != sample.shape or not submission[ID_COL].equals(test[ID_COL]):
        raise ValueError("提交格式异常")
    if not np.isfinite(pred).all() or ((pred < 0) | (pred > 1)).any():
        raise ValueError("提交概率非法")
    submission.to_csv(OUT_DIR / "submission.csv", index=False)
    np.save(OUT_DIR / "test_proba.npy", pred)
    print(f"rows={len(submission)}, weight_v7={WEIGHT_V7:.2f}")
    print(f"submission={OUT_DIR / 'submission.csv'}")


if __name__ == "__main__":
    main()
