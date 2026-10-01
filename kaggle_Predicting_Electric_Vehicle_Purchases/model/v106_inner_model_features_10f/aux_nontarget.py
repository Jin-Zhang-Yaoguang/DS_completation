"""v106 阶段 1：非目标内层模型特征（不使用购买标签）。

对 13 个原始列逐一用其余 12 列预测，在 train+test 合并数据上做 3 折折外预测。
数值列输出 预测值、残差；类别列输出 各类概率、实际类别的概率。
含义：这一行在生成器的列间关系里有多「反常」，以及焦虑等级等列背后的潜在连续分数。
用法：python aux_nontarget.py <列名>   # 产出 aux/<列名>.npz
"""
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.model_selection import KFold

HERE = Path(__file__).resolve().parent
DATA = HERE.parent.parent / "data"
OUT = HERE / "aux"
OUT.mkdir(exist_ok=True)
CAT_COLS = ["Gender", "City_Type", "Current_Car_Type", "Home_Charging_Possible", "Subsidy_Available", "Range_Anxiety_Level"]
NUM_COLS = ["Age", "Annual_Income_USD", "Daily_Commute_km", "Number_of_Cars_Owned", "Charging_Stations_Near_Home",
            "Charging_Stations_Near_Work", "Environmental_Concern_Level"]
col = sys.argv[1]

X = pd.concat([pd.read_csv(DATA / "train.csv")[NUM_COLS + CAT_COLS], pd.read_csv(DATA / "test.csv")[NUM_COLS + CAT_COLS]],
              ignore_index=True)
for c in CAT_COLS:
    X[c] = X[c].astype("category")
feats = [c for c in NUM_COLS + CAT_COLS if c != col]
params = dict(n_estimators=200, learning_rate=0.1, num_leaves=63, min_child_samples=50, subsample=0.8, subsample_freq=1,
              colsample_bytree=0.8, n_jobs=2, verbose=-1, random_state=42)
is_cat = col in CAT_COLS
codes = X[col].cat.codes.to_numpy() if is_cat else None
n_class = int(codes.max()) + 1 if is_cat else 0
pred = np.zeros((len(X), n_class if is_cat else 1))
for fit, app in KFold(3, shuffle=True, random_state=42).split(X):
    if is_cat:
        m = lgb.LGBMClassifier(**params).fit(X.iloc[fit][feats], codes[fit])
        pred[app] = m.predict_proba(X.iloc[app][feats])
    else:
        m = lgb.LGBMRegressor(**params).fit(X.iloc[fit][feats], X[col].to_numpy()[fit])
        pred[app, 0] = m.predict(X.iloc[app][feats])

out = {}
if is_cat:
    for j in range(1 if n_class == 2 else 0, n_class):
        out[f"nt_{col}_p{j}"] = pred[:, j]
    out[f"nt_{col}_p_actual"] = pred[np.arange(len(X)), codes]
else:
    out[f"nt_{col}_pred"] = pred[:, 0]
    out[f"nt_{col}_resid"] = X[col].to_numpy(np.float64) - pred[:, 0]
np.savez(OUT / f"{col}.npz", **{k: v.astype(np.float32) for k, v in out.items()})
print(col, {k: (float(v.mean()), float(v.std())) for k, v in out.items()}, flush=True)
