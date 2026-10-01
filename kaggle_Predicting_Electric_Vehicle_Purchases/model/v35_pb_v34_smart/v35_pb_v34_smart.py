# -*- coding: utf-8 -*-
"""v35：PB 探测，用本地最强 v34 替换 v13 中的 v7，与公开 Smart 等权秩融合。"""

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr


TARGET = "Will_Buy_EV"
ID_COL = "id"
WEIGHT_V34 = 0.5

OUT_DIR = Path(__file__).resolve().parent
MODEL_DIR = OUT_DIR.parent
DATA_DIR = OUT_DIR.parents[1] / "data"


def pct_rank(values: np.ndarray) -> np.ndarray:
    return rankdata(values) / len(values)


def main() -> None:
    test = pd.read_csv(DATA_DIR / "test.csv", usecols=[ID_COL])
    sample = pd.read_csv(DATA_DIR / "sample_submission.csv")
    v34 = pd.read_csv(MODEL_DIR / "v34_blend_bin10_bag_v28" / "submission.csv")
    smart = pd.read_csv(
        MODEL_DIR / "v13_pb_v7_smart" / "public_inputs" / "submission.csv"
    )
    if not v34[ID_COL].equals(test[ID_COL]) or not smart[ID_COL].equals(test[ID_COL]):
        raise ValueError("成员提交的 id 与 test 不一致")

    v34_pred = v34[TARGET].to_numpy(np.float64)
    smart_pred = smart[TARGET].to_numpy(np.float64)
    pred = WEIGHT_V34 * pct_rank(v34_pred) + (1.0 - WEIGHT_V34) * pct_rank(smart_pred)
    submission = sample.copy()
    submission[TARGET] = pred
    if submission.shape != sample.shape or not submission[ID_COL].equals(test[ID_COL]):
        raise ValueError("提交格式异常")
    if not np.isfinite(pred).all() or ((pred < 0) | (pred > 1)).any():
        raise ValueError("提交概率非法")
    submission.to_csv(OUT_DIR / "submission.csv", index=False)
    np.save(OUT_DIR / "test_proba.npy", pred)
    print(f"weight_v34={WEIGHT_V34:.2f}")
    print(f"v34_smart_spearman={spearmanr(v34_pred, smart_pred).statistic:.9f}")
    print(f"submission={OUT_DIR / 'submission.csv'}")


if __name__ == "__main__":
    main()
