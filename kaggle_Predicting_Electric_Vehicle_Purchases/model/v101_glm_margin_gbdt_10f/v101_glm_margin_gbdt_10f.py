"""v101：生成器感知岭逻辑回归 + 以其 logit 为起点的残差 GBDT（10 折）。

出处（公开 notebook，移植）：
- A 部分线性模型：heuljax「KPS6E09 Generator-Aware Ridge Logistic Regression」
- 十进制链 / 原始集均值 / 内层 logit / B 部分残差 GBDT：goodpjw2008「LR-Margin GBDT + OOF Stack」

用法：python v101_glm_margin_gbdt_10f.py <fold> glm    # 线性模型，产出 folds/margin_<k>.npz
      python v101_glm_margin_gbdt_10f.py <fold> gbdt   # 残差 GBDT，产出 folds/fold_<k>.npz
      两阶段必须分进程：macOS 上 torch 与 lightgbm 的 OpenMP 同进程会死锁。
口径：外层 10 折 seed42；带标签特征对外层训练行做内层 5 折交叉拟合；
      GBDT 早停使用外层验证折（开发口径，与公开方案一致）。
"""
import gc
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import TargetEncoder
from tokenizers import Tokenizer

HERE = Path(__file__).resolve().parent
DATA = HERE.parent.parent / "data"
OUT = HERE / "folds"
OUT.mkdir(exist_ok=True)

SEED, FOLDS, INNER_FOLDS = 42, 10, 5
N_THREADS = int(os.getenv("V101_THREADS", "2"))
DEBUG_ROWS = int(os.getenv("DEBUG_ROWS", "0"))
TARGET, ID = "Will_Buy_EV", "id"
L2, LBFGS_ITERS = 30.0, 200
CAT_COLS = ["Gender", "City_Type", "Current_Car_Type", "Home_Charging_Possible", "Subsidy_Available", "Range_Anxiety_Level"]
COLS = ["Age", "Annual_Income_USD", "Daily_Commute_km", "Number_of_Cars_Owned", "Charging_Stations_Near_Home",
        "Charging_Stations_Near_Work", "Environmental_Concern_Level"] + CAT_COLS

fold = int(sys.argv[1])
STAGE = sys.argv[2]
TAG = "_debug" if DEBUG_ROWS else ""
MARGIN_PATH = OUT / f"margin_{fold}{TAG}.npz"
T0 = time.time()


def log(msg):
    print(f"[fold {fold} {time.time() - T0:6.0f}s] {msg}", flush=True)


# ---------------------------------------------------------------- 数据
train = pd.read_csv(DATA / "train.csv")
test = pd.read_csv(DATA / "test.csv")
orig = pd.read_csv(DATA / "original_dataset" / "EV_Adoption_and_Range_Anxiety_Dataset.csv").drop(columns=["Buyer_ID"]).dropna()
if DEBUG_ROWS:
    train = train.sample(DEBUG_ROWS, random_state=0).reset_index(drop=True)
    test = test.sample(DEBUG_ROWS // 3, random_state=0).reset_index(drop=True)
y = (train[TARGET] == "Yes").astype(np.int8).to_numpy()
orig["_y"] = (orig[TARGET] == "Yes").astype(float)
ntr, nte = len(train), len(test)
SPLITS = list(StratifiedKFold(FOLDS, shuffle=True, random_state=SEED).split(np.zeros(ntr), y))
X = pd.concat([train[COLS], test[COLS]], ignore_index=True)
N = len(X)

if STAGE == "glm":
    import torch
    torch.set_num_threads(N_THREADS)
    # ---------------------------------------------------------------- A：线性模型特征基底
    TOK = Tokenizer.from_file(str(HERE / "gpt2_tokenizer.json"))
    inc_str = X.Annual_Income_USD.astype(np.int64).astype(str).to_numpy()
    u_inc, inv_inc = np.unique(inc_str, return_inverse=True)
    tok_ids = [TOK.encode(" " + s).ids for s in u_inc]


    def fz(values):
        return pd.factorize(values, sort=False)[0].astype(np.int64)


    def qbin(values, q):
        ranks = pd.Series(values).rank(method="first")
        return fz(pd.qcut(ranks, q, labels=False, duplicates="drop").to_numpy())


    K = {}
    K["L1"] = fz(np.array([t[0] for t in tok_ids], dtype=np.int64)[inv_inc])
    K["L2"] = fz(np.array([t[0] * 60000 + (t[1] if len(t) > 1 else -1) for t in tok_ids], dtype=np.int64)[inv_inc])
    K["IV"] = fz(inc_str)
    K["LAST"] = fz(np.array([len(t) * 60000 + t[-1] for t in tok_ids], dtype=np.int64)[inv_inc])
    cm = X.Daily_Commute_km.to_numpy(np.float64)
    K["CV"] = fz(cm)
    K["CI"] = fz(np.floor(cm))
    for c in COLS:
        if c not in ("Annual_Income_USD", "Daily_Commute_km"):
            K[c] = fz(X[c].to_numpy())
    K["AGEDEC"] = fz((X.Age // 10).to_numpy())
    K["CMTBIN"] = qbin(cm, 10)
    K["SHB"] = fz(np.minimum(X.Charging_Stations_Near_Home, 6).to_numpy())
    K["SWB"] = fz(np.minimum(X.Charging_Stations_Near_Work, 6).to_numpy())
    K["INCQ"] = qbin(X.Annual_Income_USD.to_numpy(), 5)
    K["INC20"] = qbin(X.Annual_Income_USD.to_numpy(), 20)
    K["INC_MOD100"] = fz((X.Annual_Income_USD.astype(np.int64) % 100).to_numpy())
    K["INC_DIV1000"] = fz((X.Annual_Income_USD.astype(np.int64) // 1000).to_numpy())
    K["CELL"] = fz(((K["Subsidy_Available"] * 5 + K["Environmental_Concern_Level"]) * 3 + K["Range_Anxiety_Level"]) * 2 + K["Home_Charging_Possible"])


    def cross(a, b):
        return fz(K[a] * (int(K[b].max()) + 1) + K[b])


    FLAT = {}
    for lv in ["L1", "L2", "LAST", "IV", "CV", "CI", "INC_MOD100", "INC_DIV1000", "Age"]:
        for a in (5, 50):
            FLAT[f"r_{lv}_a{a}"] = (K[lv], a)
    for lv in ["L1", "L2", "LAST"]:
        for c in ["City_Type", "Home_Charging_Possible", "Subsidy_Available", "Environmental_Concern_Level", "Range_Anxiety_Level",
                  "Gender", "Current_Car_Type", "Number_of_Cars_Owned", "AGEDEC", "CMTBIN", "SHB", "SWB"]:
            FLAT[f"tokx_{lv}_{c}"] = (cross(lv, c), 20)
    for c in ["City_Type", "Home_Charging_Possible", "Subsidy_Available", "Range_Anxiety_Level", "Environmental_Concern_Level", "INCQ"]:
        FLAT[f"cmtx_CI_{c}"] = (cross("CI", c), 20)
    for c in ["Home_Charging_Possible", "City_Type", "Range_Anxiety_Level"]:
        FLAT[f"cmtx_CV_{c}"] = (cross("CV", c), 20)
    for name, key, alpha in [("cell", K["CELL"], 5), ("cell_x_L1", cross("CELL", "L1"), 20),
                             ("cell_x_CI", cross("CELL", "CI"), 20), ("cell_x_INCQ", cross("CELL", "INCQ"), 20)]:
        FLAT[name] = (key, alpha)
    CATS = ["Environmental_Concern_Level", "Subsidy_Available", "Range_Anxiety_Level", "Home_Charging_Possible", "City_Type",
            "Current_Car_Type", "Number_of_Cars_Owned", "Gender", "AGEDEC", "SHB", "SWB"]
    for c in CATS:
        for suffix, other in [("INC20", "INC20"), ("CMT10", "CMTBIN")]:
            FLAT[f"xc_{c}_{suffix}"] = (cross(c, other), 20)
    for i, c1 in enumerate(CATS):
        for c2 in CATS[i + 1:]:
            FLAT[f"xp_{c1}_{c2}"] = (cross(c1, c2), 20)
    K["CELLI"] = cross("CELL", "INC20")
    for name, key in [("x3_CELL_INC20", K["CELLI"]), ("x3_CELL_CMT10", cross("CELL", "CMTBIN"))]:
        FLAT[name] = (key, 20)
    for c in ["City_Type", "Current_Car_Type", "Number_of_Cars_Owned", "AGEDEC"]:
        FLAT[f"x4_CELLI_{c}"] = (cross("CELLI", c), 20)

    CHAINS = {f"chain_S{S}": ([K["L1"], K["L2"], K["IV"]], S) for S in (5, 20, 80)}
    CHAINS.update({f"chainC_S{S}": ([K["CI"], K["CV"]], S) for S in (5, 20)})
    # 十进制链 income//1000 -> //100 -> 精确值
    inc_i = X.Annual_Income_USD.astype(np.int64).to_numpy()
    K["F1000"], K["F100"] = fz(inc_i // 1000), fz(inc_i // 100)
    for lv in ["F1000", "F100"]:
        for a in (5, 50):
            FLAT[f"r_{lv}_a{a}"] = (K[lv], a)
    for S in (5, 20, 80):
        CHAINS[f"chainF_S{S}"] = ([K["F1000"], K["F100"], K["IV"]], S)
    for c in ["City_Type", "Subsidy_Available", "Environmental_Concern_Level", "Range_Anxiety_Level"]:
        FLAT[f"tokx_F1000_{c}"] = (cross("F1000", c), 20)
    N_LABEL = len(FLAT) + sum(len(ks) for ks, _ in CHAINS.values())

    # 无标签特征
    LF = []
    for nm in ["IV", "L2", "L1", "CV", "LAST"]:
        LF.append(np.log1p(np.bincount(K[nm])[K[nm]]))
    inc_f = X.Annual_Income_USD.to_numpy(np.float64)
    env = X.Environmental_Concern_Level.to_numpy(np.float64)
    subs = (X.Subsidy_Available == "Yes").to_numpy()
    anx_formula = X.Range_Anxiety_Level.map({"Low": 0, "Medium": 1, "High": 3}).to_numpy(np.float64)
    LF.append(1.2 * inc_f / 1e5 + 0.6 * env + 2 * subs - anx_formula)
    for c in COLS[:7]:
        v = X[c].to_numpy(np.float64)
        LF.append(v)
        for q in (0.1, 0.3, 0.5, 0.7, 0.9):
            LF.append(np.maximum(v - np.quantile(v, q), 0.0))
    OH = pd.get_dummies(X[CAT_COLS + ["Environmental_Concern_Level", "Number_of_Cars_Owned"]].astype(str), dtype=np.float32)
    LF = np.column_stack(LF + [OH.to_numpy()]).astype(np.float32)

    MIXV = {"env": env, "sub": subs.astype(float),
            "anx": X.Range_Anxiety_Level.map({"Low": 0, "Medium": 1, "High": 2}).to_numpy(np.float64),
            "home": (X.Home_Charging_Possible == "Yes").to_numpy(float),
            "urban": (X.City_Type == "Urban").to_numpy(float), "rural": (X.City_Type == "Rural").to_numpy(float),
            "suv": (X.Current_Car_Type == "SUV").to_numpy(float), "truck": (X.Current_Car_Type == "Truck").to_numpy(float),
            "sedan": (X.Current_Car_Type == "Sedan").to_numpy(float), "male": (X.Gender == "Male").to_numpy(float),
            "cars": X.Number_of_Cars_Owned.to_numpy(float), "age": X.Age.to_numpy(float),
            "sth": X.Charging_Stations_Near_Home.to_numpy(float), "stw": X.Charging_Stations_Near_Work.to_numpy(float),
            "cmt": cm, "inc": inc_f / 1e4}
    ivcv = fz(np.char.add(np.char.add(inc_str.astype(str), "_"), X.Daily_Commute_km.astype(str).to_numpy()))
    MIX = []
    for kn, key in {"IV": K["IV"], "L2": K["L2"], "L1": K["L1"], "CV": K["CV"], "IVCV": ivcv}.items():
        counts = np.bincount(key).astype(np.float64)
        n = counts[key]
        MIX.append(np.log(np.maximum(n, 1.0)))
        for vn, v in MIXV.items():
            if (kn in ("IV", "L2", "L1") and vn == "inc") or (kn == "CV" and vn == "cmt") or (kn == "IVCV" and vn in ("inc", "cmt")):
                continue
            gm = float(v.mean())
            sums = np.bincount(key, weights=v, minlength=len(counts))[key]
            MIX.append((sums - v + 5 * gm) / (n - 1 + 5) - gm)
    LF = np.concatenate([LF, np.column_stack(MIX).astype(np.float32)], axis=1)
    om = orig["_y"].mean()
    for c in ["Annual_Income_USD", "Daily_Commute_km", "Age", "Environmental_Concern_Level"] + CAT_COLS:
        v = X[c].map(orig.groupby(c)["_y"].mean()).fillna(om).to_numpy(np.float32)
        LF = np.concatenate([LF, v[:, None]], axis=1)
    v = X["Annual_Income_USD"].isin(set(orig["Annual_Income_USD"])).to_numpy(np.float32)
    LF = np.concatenate([LF, v[:, None]], axis=1)
    P = N_LABEL + LF.shape[1]
    log(f"GLM 基底 {P} 列（带标签 {N_LABEL}，无标签 {LF.shape[1]}）")


    def _stats(key, fit):
        size = int(key.max()) + 1
        return np.bincount(key[fit], weights=y[fit], minlength=size), np.bincount(key[fit], minlength=size)


    def _logit_rate(rate):
        rate = np.clip(rate, 1e-6, 1 - 1e-6)
        return np.log(rate / (1 - rate)).astype(np.float32)


    def encode(fit, app, out, rows):
        prior = float(y[fit].mean())
        j = 0
        for key, alpha in FLAT.values():
            s, c = _stats(key, fit)
            ka = key[app]
            out[rows, j] = _logit_rate((s[ka] + alpha * prior) / (c[ka] + alpha))
            j += 1
        for keys, strength in CHAINS.values():
            post = np.full(len(app), prior, np.float64)
            for key in keys:
                s, c = _stats(key, fit)
                ka = key[app]
                post = (s[ka] + strength * post) / (c[ka] + strength)
                out[rows, j] = _logit_rate(post)
                j += 1


    def fit_glm(Z, yy):
        w = torch.zeros(Z.shape[1], dtype=torch.float64, requires_grad=True)
        b = torch.zeros(1, dtype=torch.float64, requires_grad=True)
        opt = torch.optim.LBFGS([w, b], lr=1.0, max_iter=LBFGS_ITERS, history_size=20, tolerance_grad=1e-9,
                                tolerance_change=1e-12, line_search_fn="strong_wolfe")

        def closure():
            opt.zero_grad()
            loss = torch.nn.functional.binary_cross_entropy_with_logits(Z @ w + b, yy, reduction="sum") + 0.5 * L2 * (w * w).sum()
            loss.backward()
            return loss

        opt.step(closure)
        return w.detach(), b.detach()


    def standardize(M, mu, sd):
        return torch.from_numpy((M - mu) / sd).to(torch.float64)


    fit_rows, valid_rows = SPLITS[fold]
    test_rows = np.arange(ntr, N)
    Mfit = np.empty((len(fit_rows), P), np.float32)
    Mvalid = np.empty((len(valid_rows), P), np.float32)
    Mtest = np.empty((nte, P), np.float32)
    encode(fit_rows, valid_rows, Mvalid, slice(None))
    encode(fit_rows, test_rows, Mtest, slice(None))
    position = np.full(ntr, -1, np.int64)
    position[fit_rows] = np.arange(len(fit_rows))
    for ifit, iapp in StratifiedKFold(INNER_FOLDS, shuffle=True, random_state=SEED).split(np.zeros(len(fit_rows)), y[fit_rows]):
        encode(fit_rows[ifit], fit_rows[iapp], Mfit, position[fit_rows[iapp]])
    Mfit[:, N_LABEL:] = LF[fit_rows]
    Mvalid[:, N_LABEL:] = LF[valid_rows]
    Mtest[:, N_LABEL:] = LF[ntr:]
    assert np.isfinite(Mfit).all() and np.isfinite(Mvalid).all() and np.isfinite(Mtest).all()

    mu = Mfit.mean(axis=0, dtype=np.float64)
    sd = Mfit.std(axis=0, dtype=np.float64) + 1e-6
    w, b = fit_glm(standardize(Mfit, mu, sd), torch.from_numpy(y[fit_rows].astype(np.float64)))
    eta_valid = (standardize(Mvalid, mu, sd) @ w + b).numpy()
    eta_test = (standardize(Mtest, mu, sd) @ w + b).numpy()
    glm_auc = roc_auc_score(y[valid_rows], eta_valid)
    log(f"GLM 验证 AUC={glm_auc:.6f}")

    # 训练行的内层交叉拟合 logit：供残差 GBDT 作起点，不含自身标签
    eta_fit = np.zeros(len(fit_rows))
    for ifit, iapp in StratifiedKFold(INNER_FOLDS, shuffle=True, random_state=SEED + 1).split(np.zeros(len(fit_rows)), y[fit_rows]):
        mu_i = Mfit[ifit].mean(axis=0, dtype=np.float64)
        sd_i = Mfit[ifit].std(axis=0, dtype=np.float64) + 1e-6
        wi, bi = fit_glm(standardize(Mfit[ifit], mu_i, sd_i), torch.from_numpy(y[fit_rows][ifit].astype(np.float64)))
        eta_fit[iapp] = (standardize(Mfit[iapp], mu_i, sd_i) @ wi + bi).numpy()
    log(f"GLM 内层 logit AUC={roc_auc_score(y[fit_rows], eta_fit):.6f}")
    np.savez(MARGIN_PATH, eta_fit=eta_fit, eta_valid=eta_valid, eta_test=eta_test)
    log("margin 已保存")


    sys.exit(0)

# ---------------------------------------------------------------- B：残差 GBDT
def build_features(train, test, orig):
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


TE_SMOOTHS = ("auto", 10.0, 100.0)


def target_encode(X_tr, y_tr, X_others, key_cols):
    outs = [X_tr.copy()] + [Xo.copy() for Xo in X_others]
    for s in TE_SMOOTHS:
        te = TargetEncoder(cv=5, smooth=s, random_state=SEED)
        enc = [te.fit_transform(X_tr[key_cols], y_tr)] + [te.transform(Xo[key_cols]) for Xo in X_others]
        tag = "auto" if s == "auto" else str(int(s))
        for Xo, e in zip(outs, enc):
            Xo[[f"{c}_te{tag}" for c in key_cols]] = e.astype("float32")
    return [Xo.drop(columns=key_cols) for Xo in outs]


fit_rows, valid_rows = SPLITS[fold]
_m = np.load(MARGIN_PATH)
eta_fit, eta_valid, eta_test = _m["eta_fit"], _m["eta_valid"], _m["eta_test"]
tr_f, te_f, key_cols = build_features(train.drop(columns=[TARGET]), test, orig)
features = [c for c in te_f.columns if c != ID]
X_tr, X_va, X_te = target_encode(tr_f[features].iloc[fit_rows], y[fit_rows],
                                 [tr_f[features].iloc[valid_rows], te_f[features]], key_cols)
log(f"GBDT 特征 {X_tr.shape[1]} 列")
y_tr, y_va = y[fit_rows], y[valid_rows]
res = {}

import lightgbm as lgb
clf = lgb.LGBMClassifier(n_estimators=20000, learning_rate=0.02, max_depth=5, num_leaves=32, min_child_samples=10,
                         subsample=0.8, subsample_freq=1, colsample_bytree=0.3, reg_alpha=0.071, reg_lambda=2.0,
                         max_bin=1024, feature_pre_filter=False, random_state=SEED, n_jobs=N_THREADS, verbose=-1)
clf.fit(X_tr, y_tr, init_score=eta_fit, eval_set=[(X_va, y_va)], eval_init_score=[eta_valid], eval_metric="auc",
        callbacks=[lgb.early_stopping(500, verbose=False)])
res["lgbm_valid"] = clf.predict(X_va, raw_score=True) + eta_valid
res["lgbm_test"] = clf.predict(X_te, raw_score=True) + eta_test
res["lgbm_iter"] = clf.best_iteration_
log(f"残差 LGBM 树={clf.best_iteration_} AUC={roc_auc_score(y_va, res['lgbm_valid']):.6f}")

from xgboost import XGBClassifier
clf = XGBClassifier(n_estimators=20000, learning_rate=0.02, max_depth=4, min_child_weight=5, subsample=0.9, colsample_bytree=0.6,
                    reg_lambda=5.0, max_bin=1024, tree_method="hist", eval_metric="auc", early_stopping_rounds=500,
                    random_state=SEED, n_jobs=N_THREADS, verbosity=0)
clf.fit(X_tr, y_tr, base_margin=eta_fit, eval_set=[(X_va, y_va)], base_margin_eval_set=[eta_valid], verbose=False)
res["xgb_valid"] = clf.predict(X_va, output_margin=True, base_margin=eta_valid)
res["xgb_test"] = clf.predict(X_te, output_margin=True, base_margin=eta_test)
res["xgb_iter"] = clf.best_iteration
log(f"残差 XGB 树={clf.best_iteration} AUC={roc_auc_score(y_va, res['xgb_valid']):.6f}")

if not DEBUG_ROWS:
    np.savez(OUT / f"fold_{fold}.npz", valid_rows=valid_rows, glm_valid=eta_valid, glm_test=eta_test, **res)
    log("已保存")
