"""v115：v113 去掉线性起点（不设 init_score），作为独立于起点族的视角；其余与 v113 相同，复用 v113 的 donor 缓存。原 v113 说明：v112 配方唯一改动为外层 10 → 20 折（起点与参照改用 v105，donor 特征按 20 折重新缓存）。原说明：v101 残差 LGBM 的 117 列 + heuljax donor 基底 173 列（+GAM margin）合并，起点为 v101 线性 logit。

唯一变量：相对 v101 残差 LGBM 追加 donor 特征；相对 v107 换成同时看到两套特征的 LightGBM。
donor 特征取自 v111_glm_donor_basis_10f/donor_cache（训练行为 donor 内层 5 折交叉拟合）。
用法：python v112_merged_basis_lgbm_glm_margin_10f.py <fold>
"""
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
DATA = HERE.parent.parent / "data"
V101 = HERE.parent / "v105_glm_margin_gbdt_20f" / "folds"   # 20 折起点与参照
OUT = HERE / "folds"
OUT.mkdir(exist_ok=True)
SEED, FOLDS = 42, 20
N_THREADS = int(os.getenv("V112_THREADS", "2"))
TARGET, ID = "Will_Buy_EV", "id"
CAT_COLS = ["Gender", "City_Type", "Current_Car_Type", "Home_Charging_Possible", "Subsidy_Available", "Range_Anxiety_Level"]
fold = int(sys.argv[1])
T0 = time.time()


def log(msg):
    print(f"[fold {fold} {time.time() - T0:6.0f}s] {msg}", flush=True)


train = pd.read_csv(DATA / "train.csv")
test = pd.read_csv(DATA / "test.csv")
orig = pd.read_csv(DATA / "original_dataset" / "EV_Adoption_and_Range_Anxiety_Dataset.csv").drop(columns=["Buyer_ID"]).dropna()
y = (train[TARGET] == "Yes").astype(np.int8).to_numpy()
orig["_y"] = (orig[TARGET] == "Yes").astype(float)
ntr = len(train)
fit_rows, valid_rows = list(StratifiedKFold(FOLDS, shuffle=True, random_state=SEED).split(np.zeros(ntr), y))[fold]
m = np.load(V101 / f"margin_{fold}.npz")
eta_fit, eta_valid, eta_test = m["eta_fit"], m["eta_valid"], m["eta_test"]


def build_features(train, test, orig):          # 与 v101 的 B 部分完全一致
    n_train = len(train)
    df = pd.concat([train, test], ignore_index=True).drop(columns=["Number_of_Cars_Owned"])
    inc, com = df["Annual_Income_USD"], df["Daily_Commute_km"]
    df["inc_exact"] = inc.astype(int).astype(str)
    df["com_exact"] = com.round(1).astype(str)
    df["age_key"] = df["Age"].astype(str)
    df["env_key"] = df["Environmental_Concern_Level"].astype(int).astype(str)
    df["csh_key"] = df["Charging_Stations_Near_Home"].astype(str)
    df["csw_key"] = df["Charging_Stations_Near_Work"].astype(str)
    key_cols = CAT_COLS + ["inc_exact", "com_exact", "age_key", "env_key", "csh_key", "csw_key"]
    for c in ["Annual_Income_USD", "Daily_Commute_km"]:
        for k in range(-1, 6):
            d = (df[c] // (10 ** k) % 10).astype(int)
            if d.nunique() > 1:
                df[f"{c[:3]}_d{k}"] = d.astype(str)
                key_cols.append(f"{c[:3]}_d{k}")
    df["inc_100"] = (inc // 100).astype(int).astype(str)
    df["inc_1000"] = (inc // 1000).astype(int).astype(str)
    df["com_int"] = com.astype(int).astype(str)
    key_cols += ["inc_100", "inc_1000", "com_int"]
    fe = pd.DataFrame({f"{c}_fe": df[c].map(df[c].value_counts(normalize=True)).astype("float32") for c in key_cols})
    df = pd.concat([df, fe], axis=1)
    orig_mean = orig["_y"].mean()
    for c in ["Annual_Income_USD", "Daily_Commute_km", "Age", "Environmental_Concern_Level",
              "Charging_Stations_Near_Home", "Charging_Stations_Near_Work"] + CAT_COLS:
        df[f"{c}_orig_mean"] = df[c].map(orig.groupby(c)["_y"].mean()).fillna(orig_mean).astype("float32")
    df["is_30k_spike"] = (inc == 30000).astype("int8")
    df["is_millionaire_cliff"] = (inc >= 170537).astype("int8")
    df["is_dead_zone"] = inc.between(38000, 42000).astype("int8")
    return df.iloc[:n_train].copy(), df.iloc[n_train:].copy(), key_cols


def target_encode(X_tr, y_tr, X_others, key_cols):
    outs = [X_tr.copy()] + [Xo.copy() for Xo in X_others]
    for s in ("auto", 10.0, 100.0):
        te = TargetEncoder(cv=5, smooth=s, random_state=SEED)
        enc = [te.fit_transform(X_tr[key_cols], y_tr)] + [te.transform(Xo[key_cols]) for Xo in X_others]
        tag = "auto" if s == "auto" else str(int(s))
        for Xo, e in zip(outs, enc):
            Xo[[f"{c}_te{tag}" for c in key_cols]] = e.astype("float32")
    return [Xo.drop(columns=key_cols) for Xo in outs]


tr_f, te_f, key_cols = build_features(train.drop(columns=[TARGET]), test, orig)
features = [c for c in te_f.columns if c != ID]
X_tr, X_va, X_te = target_encode(tr_f[features].iloc[fit_rows], y[fit_rows],
                                 [tr_f[features].iloc[valid_rows], te_f[features]], key_cols)

# ---- donor 基底特征
dc = np.load(HERE.parent / "v113_merged_basis_lgbm_glm_margin_20f" / "donor_cache" / f"fold_{fold}.npz")
dnames = [f"dn_{c}" for c in dc["names"]] + ["dn_GAM_MARGIN"]
for X_, x, g in ((X_tr, dc["train_x"], dc["gam_tr"]), (X_va, dc["valid_x"], dc["gam_va"]), (X_te, dc["test_x"], dc["gam_te"])):
    assert len(x) == len(X_)
    X_[dnames] = np.column_stack([x, g]).astype(np.float32)
log(f"特征 {X_tr.shape[1]} 列")

clf = lgb.LGBMClassifier(n_estimators=20000, learning_rate=0.02, max_depth=5, num_leaves=32, min_child_samples=10,
                         subsample=0.8, subsample_freq=1, colsample_bytree=0.3, reg_alpha=0.071, reg_lambda=2.0,
                         max_bin=1024, feature_pre_filter=False, random_state=SEED, n_jobs=N_THREADS, verbose=-1)
clf.fit(X_tr, y[fit_rows], eval_set=[(X_va, y[valid_rows])],
        eval_metric="auc", callbacks=[lgb.early_stopping(500, verbose=False)])
valid = clf.predict(X_va, raw_score=True)
test_pred = clf.predict(X_te, raw_score=True)
ref = np.load(V101 / f"fold_{fold}.npz")["lgbm_valid"]
auc, auc_ref = roc_auc_score(y[valid_rows], valid), roc_auc_score(y[valid_rows], ref)
imp = pd.Series(clf.booster_.feature_importance("gain"), index=X_tr.columns)
new_share = imp[[c for c in X_tr.columns if c.startswith("dn_")]].sum() / imp.sum()
log(f"残差 LGBM 树={clf.best_iteration_} AUC={auc:.6f} | v105 同折 {auc_ref:.6f} | 差 {auc - auc_ref:+.6f} | 新特征增益占比 {new_share:.3f}")
np.savez(OUT / f"fold_{fold}.npz", valid_rows=valid_rows, valid=valid, test=test_pred, best_iter=clf.best_iteration_)
