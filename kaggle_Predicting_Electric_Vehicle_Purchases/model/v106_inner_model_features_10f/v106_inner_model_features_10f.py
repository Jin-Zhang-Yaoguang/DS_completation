"""v106：v101 残差 LightGBM + 内层模型预测特征（10 折，与 v101 同折、同起点、同参数）。

唯一变量：在 v101 的 117 列之上追加内层模型特征，配对参照为 v101 的残差 LGBM。
- 非目标特征（aux/，不含标签）：每个原始列由其余列预测的折外预测值/残差/类别概率；
- 目标特征（可选，V106_TARGET=1）：原始特征 LightGBM、去掉收入列的 LightGBM 的折外 logit，
  外层训练行用内层 5 折交叉拟合，外层验证/测试行用整个外层训练折拟合。
用法：python v106_inner_model_features_10f.py <fold>
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
V101 = HERE.parent / "v101_glm_margin_gbdt_10f" / "folds"
USE_TARGET = os.getenv("V106_TARGET", "0") == "1"
OUT = HERE / ("folds_target" if USE_TARGET else "folds")
OUT.mkdir(exist_ok=True)
SEED, FOLDS = 42, 10
N_THREADS = int(os.getenv("V106_THREADS", "2"))
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

# ---- 非目标内层模型特征
aux = {}
for f in sorted((HERE / "aux").glob("*.npz")):
    z = np.load(f)
    aux.update({k: z[k] for k in z.files})
aux = pd.DataFrame(aux)
assert len(aux) == ntr + len(test) and len(aux.columns) > 0
for X_, rows in ((X_tr, fit_rows), (X_va, valid_rows), (X_te, np.arange(ntr, ntr + len(test)))):
    X_[aux.columns] = aux.iloc[rows].to_numpy()

# ---- 目标内层模型特征
if USE_TARGET:
    raw = pd.concat([train.drop(columns=[ID, TARGET]), test.drop(columns=[ID])], ignore_index=True)
    for c in CAT_COLS:
        raw[c] = raw[c].astype("category")
    views = {"tg_raw": list(raw.columns), "tg_noinc": [c for c in raw.columns if c != "Annual_Income_USD"]}
    p = dict(n_estimators=250, learning_rate=0.1, num_leaves=31, min_child_samples=50, subsample=0.8, subsample_freq=1,
             colsample_bytree=0.8, n_jobs=N_THREADS, verbose=-1, random_state=SEED)
    test_rows = np.arange(ntr, ntr + len(test))
    for name, cols in views.items():
        f_fit = np.zeros(len(fit_rows))
        for ifit, iapp in StratifiedKFold(5, shuffle=True, random_state=SEED + 2).split(np.zeros(len(fit_rows)), y[fit_rows]):
            mdl = lgb.LGBMClassifier(**p).fit(raw.iloc[fit_rows[ifit]][cols], y[fit_rows[ifit]])
            f_fit[iapp] = mdl.predict(raw.iloc[fit_rows[iapp]][cols], raw_score=True)
        mdl = lgb.LGBMClassifier(**p).fit(raw.iloc[fit_rows][cols], y[fit_rows])
        X_tr[name] = f_fit
        X_va[name] = mdl.predict(raw.iloc[valid_rows][cols], raw_score=True)
        X_te[name] = mdl.predict(raw.iloc[test_rows][cols], raw_score=True)
        log(f"{name} 内层 AUC={roc_auc_score(y[fit_rows], f_fit):.5f} 验证 AUC={roc_auc_score(y[valid_rows], X_va[name]):.5f}")
    for X_, eta in ((X_tr, eta_fit), (X_va, eta_valid), (X_te, eta_test)):
        X_["tg_glm_minus_noinc"] = eta - X_["tg_noinc"]          # 线性模型相对「无收入模型」多出来的部分
log(f"特征 {X_tr.shape[1]} 列")

clf = lgb.LGBMClassifier(n_estimators=20000, learning_rate=0.02, max_depth=5, num_leaves=32, min_child_samples=10,
                         subsample=0.8, subsample_freq=1, colsample_bytree=0.3, reg_alpha=0.071, reg_lambda=2.0,
                         max_bin=1024, feature_pre_filter=False, random_state=SEED, n_jobs=N_THREADS, verbose=-1)
clf.fit(X_tr, y[fit_rows], init_score=eta_fit, eval_set=[(X_va, y[valid_rows])], eval_init_score=[eta_valid],
        eval_metric="auc", callbacks=[lgb.early_stopping(500, verbose=False)])
valid = clf.predict(X_va, raw_score=True) + eta_valid
test_pred = clf.predict(X_te, raw_score=True) + eta_test
ref = np.load(V101 / f"fold_{fold}.npz")["lgbm_valid"]
auc, auc_ref = roc_auc_score(y[valid_rows], valid), roc_auc_score(y[valid_rows], ref)
imp = pd.Series(clf.booster_.feature_importance("gain"), index=X_tr.columns)
new_share = imp[[c for c in X_tr.columns if c.startswith(("nt_", "tg_"))]].sum() / imp.sum()
log(f"残差 LGBM 树={clf.best_iteration_} AUC={auc:.6f} | v101 同折 {auc_ref:.6f} | 差 {auc - auc_ref:+.6f} | 新特征增益占比 {new_share:.3f}")
np.savez(OUT / f"fold_{fold}.npz", valid_rows=valid_rows, valid=valid, test=test_pred, best_iter=clf.best_iteration_)
