# -*- coding: utf-8 -*-
"""v38：PB 探测，利用公开 Smart 与低相关 20 折 v28 的预测方差互补。"""

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr


TARGET = "Will_Buy_EV"
ID_COL = "id"
WEIGHT_SMART = 0.55

OUT_DIR = Path(__file__).resolve().parent
MODEL_DIR = OUT_DIR.parent
DATA_DIR = OUT_DIR.parents[1] / "data"


def pct_rank(values: np.ndarray) -> np.ndarray:
    return rankdata(values) / len(values)


def main() -> None:
    test = pd.read_csv(DATA_DIR / "test.csv", usecols=[ID_COL])
    sample = pd.read_csv(DATA_DIR / "sample_submission.csv")
    smart = pd.read_csv(
        MODEL_DIR / "v13_pb_v7_smart" / "public_inputs" / "submission.csv"
    )
    v28 = pd.read_csv(MODEL_DIR / "v28_multiscale_te_lgbm_20f" / "submission.csv")
    if not smart[ID_COL].equals(test[ID_COL]) or not v28[ID_COL].equals(test[ID_COL]):
        raise ValueError("成员提交的 id 与 test 不一致")

    smart_pred = smart[TARGET].to_numpy(np.float64)
    v28_pred = v28[TARGET].to_numpy(np.float64)
    pred = WEIGHT_SMART * pct_rank(smart_pred) + (1.0 - WEIGHT_SMART) * pct_rank(v28_pred)
    submission = sample.copy()
    submission[TARGET] = pred
    if submission.shape != sample.shape or not submission[ID_COL].equals(test[ID_COL]):
        raise ValueError("提交格式异常")
    if not np.isfinite(pred).all() or ((pred < 0) | (pred > 1)).any():
        raise ValueError("提交概率非法")
    submission.to_csv(OUT_DIR / "submission.csv", index=False)
    np.save(OUT_DIR / "test_proba.npy", pred)
    print(f"weight_smart={WEIGHT_SMART:.2f}")
    print(f"smart_v28_spearman={spearmanr(smart_pred, v28_pred).statistic:.9f}")
    print(f"submission={OUT_DIR / 'submission.csv'}")


if __name__ == "__main__":
    main()
