"""v103：V85（Naji 配方，148 列）特征 + v101 线性模型 logit 作起点的残差 LightGBM（10 折）。

唯一变量：相对 v101 残差 LGBM 换成 V85 的特征视角；相对 V85 增加 init_score 起点。
折与起点沿用 v101（外层 10 折 seed42，训练行用内层交叉拟合 logit），须先跑完 v101 的 glm 阶段。
用法：python v103_v85_features_glm_margin_10f.py <fold>
"""
import importlib.util
import os
import sys
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import TargetEncoder

HERE = Path(__file__).resolve().parent
MARGINS = HERE.parent / "v101_glm_margin_gbdt_10f" / "folds"
# V85 的特征构建函数位于主线工作树（只读引用）
PROBE = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/strange-gates-ca18fe/"
             "kaggle_Predicting_Electric_Vehicle_Purchases/model/v68_naji_accelerated_probe/v68_naji_accelerated_probe.py")
OUT = HERE / "folds"
OUT.mkdir(exist_ok=True)
SEED, FOLDS = 42, 10
N_THREADS = int(os.getenv("V103_THREADS", "2"))
fold = int(sys.argv[1])
T0 = time.time()


def log(msg):
    print(f"[fold {fold} {time.time() - T0:6.0f}s] {msg}", flush=True)


spec = importlib.util.spec_from_file_location("naji_probe", PROBE)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
x, y_s, x_test, te_cols = probe.build_features(extra_income_bins=(10, 100))
y = y_s.to_numpy()
fit_rows, valid_rows = list(StratifiedKFold(FOLDS, shuffle=True, random_state=SEED).split(np.zeros(len(y)), y))[fold]
m = np.load(MARGINS / f"margin_{fold}.npz")
assert len(m["eta_fit"]) == len(fit_rows) and len(m["eta_valid"]) == len(valid_rows)

x_fit, x_valid, x_te = x.iloc[fit_rows].copy(), x.iloc[valid_rows].copy(), x_test.copy()
for tag, smooth in (("auto", "auto"), ("10", 10.0)):
    enc = TargetEncoder(shuffle=True, cv=5, smooth=smooth, random_state=SEED + fold + 1)
    e_fit = enc.fit_transform(x_fit[te_cols], y[fit_rows])
    for frame, e in ((x_fit, e_fit), (x_valid, enc.transform(x_valid[te_cols])), (x_te, enc.transform(x_te[te_cols]))):
        frame[[f"{c}_TE_{tag}" for c in te_cols]] = e.astype(np.float32)
x_fit, x_valid, x_te = (f.drop(columns=te_cols) for f in (x_fit, x_valid, x_te))
log(f"特征 {x_fit.shape[1]} 列")

clf = lgb.LGBMClassifier(n_estimators=12000, learning_rate=0.02, max_depth=5, num_leaves=32, min_child_samples=10,
                         subsample=0.8, subsample_freq=1, colsample_bytree=0.3, reg_alpha=0.071, reg_lambda=2.0,
                         max_bin=1024, feature_pre_filter=False, random_state=SEED + fold + 1, n_jobs=N_THREADS, verbose=-1)
clf.fit(x_fit, y[fit_rows], init_score=m["eta_fit"], eval_set=[(x_valid, y[valid_rows])], eval_init_score=[m["eta_valid"]],
        eval_metric="auc", callbacks=[lgb.early_stopping(350, verbose=False)])
valid = clf.predict(x_valid, raw_score=True) + m["eta_valid"]
test = clf.predict(x_te, raw_score=True) + m["eta_test"]
log(f"残差 LGBM(V85 特征) 树={clf.best_iteration_} AUC={roc_auc_score(y[valid_rows], valid):.6f}")
np.savez(OUT / f"fold_{fold}.npz", valid_rows=valid_rows, valid=valid, test=test, best_iter=clf.best_iteration_)
