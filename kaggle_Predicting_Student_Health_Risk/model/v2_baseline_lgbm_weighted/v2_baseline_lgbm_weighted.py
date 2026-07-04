# -*- coding: utf-8 -*-
"""
方案 v2：v1_baseline_lgbm + 类别决策权重后处理（不重训）
直接复用 v1_baseline_lgbm 留档的 OOF/测试概率：
- 在 OOF 概率上网格搜索每类乘性权重（固定 at-risk = 1），最大化 Balanced Accuracy；
- 将最优权重应用到测试概率，argmax 生成提交。
实验结果：OOF 0.93503（argmax）→ 0.94877（加权，w_fit≈6.975, w_unhealthy≈6.025）。
目的：用一次提交验证「OOF 后处理增益能否兑现到线上」。
"""

from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score

BASE_DIR = Path(__file__).resolve().parent
BASELINE_DIR = BASE_DIR.parent / "v1_baseline_lgbm"
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
TARGET = "health_condition"


def main():
    # 复用 baseline 留档概率
    oof = np.load(BASELINE_DIR / "oof_proba.npy")
    test_pred = np.load(BASELINE_DIR / "test_proba.npy")

    train = pd.read_csv(DATA_DIR / "train.csv")
    sub = pd.read_csv(DATA_DIR / "sample_submission.csv")
    classes = sorted(train[TARGET].unique())
    y = train[TARGET].map({c: i for i, c in enumerate(classes)}).values

    # 权重搜索：粗网格 → 细网格
    def _search(g1, g2, best):
        for w1, w2 in product(g1, g2):
            s = balanced_accuracy_score(y, (oof * np.array([1.0, w1, w2])).argmax(1))
            if s > best[0]:
                best = (s, w1, w2)
        return best

    best = (balanced_accuracy_score(y, oof.argmax(1)), 1.0, 1.0)
    print(f"argmax OOF: {best[0]:.5f}")
    best = _search(np.linspace(1, 12, 45), np.linspace(1, 12, 45), best)
    s, w1, w2 = _search(np.linspace(max(0.5, best[1] - 0.3), best[1] + 0.3, 25),
                        np.linspace(max(0.5, best[2] - 0.3), best[2] + 0.3, 25), best)
    w = np.array([1.0, w1, w2])
    print(f"加权 OOF: {s:.5f} (w_fit={w1:.3f}, w_unhealthy={w2:.3f})")

    # 应用到测试集
    sub[TARGET] = [classes[i] for i in (test_pred * w).argmax(1)]
    sub.to_csv(BASE_DIR / "submission.csv", index=False)
    np.save(BASE_DIR / "best_class_weights.npy", w)
    print("提交预测分布:")
    print(sub[TARGET].value_counts(normalize=True).round(4))
    print(f"CV (加权 OOF balanced accuracy): {s:.5f}")


if __name__ == "__main__":
    main()
