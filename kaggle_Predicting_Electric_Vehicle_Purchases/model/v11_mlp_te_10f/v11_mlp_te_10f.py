# -*- coding: utf-8 -*-
"""
v11：v6 MLP 配方 × 外层 10 折（3 种子 bagging，MPS 训练）。

赛题：Predicting Electric Vehicle Purchases（Playground Series S6E9）
指标：ROC AUC

设计：
- 收入、通勤精确值以及所有低基数列做 embedding（收入/通勤词表来自 train+test，频次 <2 归入 UNK）；
- 7 个数值列标准化（收入取 log）作为数值输入；
- 与 v2/v5 相同的折内目标编码（收入精确值、收入//100、收入×补贴、收入×环保等级、通勤、年龄）
  经 logit 变换并按训练侧标准化后作为数值输入；训练侧内层 5 折 OOF，验证/测试侧全训练折统计；
- 3 层 MLP（512-256-128，SiLU，dropout），AdamW，验证 AUC 早停；
- 2 个模型种子在同一外层折划分下 bagging。消融（N3）单种子 OOF 0.945123，
  与 v2/v3 三成员融合交叉拟合 +0.000282（权重 0.21，5/5 折）。
"""

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


SEED = 42
N_FOLDS = 10
N_INNER = 5
TARGET = "Will_Buy_EV"
ID_COL = "id"
POS_LABEL = "Yes"
INCOME = "Annual_Income_USD"
TE_SMOOTH = 10.0
MODEL_SEEDS = [0, 1, 2]
EPOCHS = 30
BATCH = 4096
LR = 2e-3
WD = 1e-5
WIDTH = 512
DROP = 0.2
EMB_DROP = 0.2
PATIENCE = 4

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
OUT_DIR = Path(__file__).resolve().parent
BASE_RESULTS = OUT_DIR.parent / "v6_mlp_te" / "cv_results.json"

# (列, 最小频次, embedding 维度)
CAT_SPEC = [
    (INCOME, 2, 12), ("Daily_Commute_km", 2, 6), ("Age", 1, 4),
    ("Charging_Stations_Near_Home", 1, 4), ("Charging_Stations_Near_Work", 1, 4),
    ("Number_of_Cars_Owned", 1, 2), ("Environmental_Concern_Level", 1, 3),
    ("Subsidy_Available", 1, 2), ("Range_Anxiety_Level", 1, 2), ("Home_Charging_Possible", 1, 2),
    ("City_Type", 1, 2), ("Current_Car_Type", 1, 2), ("Gender", 1, 2),
]
NUM_COLS = [INCOME, "Daily_Commute_km", "Age", "Environmental_Concern_Level",
            "Charging_Stations_Near_Home", "Charging_Stations_Near_Work", "Number_of_Cars_Owned"]
TE_KEYS = {
    "te_inc": [INCOME],
    "te_inc_bin100": ["_inc_bin100"],
    "te_inc_subsidy": [INCOME, "Subsidy_Available"],
    "te_inc_env": [INCOME, "Environmental_Concern_Level"],
    "te_commute": ["Daily_Commute_km"],
    "te_age": ["Age"],
}


class Net(nn.Module):
    def __init__(self, vocab_dims, n_num):
        super().__init__()
        self.embs = nn.ModuleList([nn.Embedding(v, d) for v, d in vocab_dims])
        self.emb_drop = nn.Dropout(EMB_DROP)
        in_dim = sum(d for _, d in vocab_dims) + n_num
        self.mlp = nn.Sequential(
            nn.Linear(in_dim, WIDTH), nn.SiLU(), nn.Dropout(DROP),
            nn.Linear(WIDTH, WIDTH // 2), nn.SiLU(), nn.Dropout(DROP),
            nn.Linear(WIDTH // 2, WIDTH // 4), nn.SiLU(), nn.Dropout(DROP / 2),
            nn.Linear(WIDTH // 4, 1),
        )

    def forward(self, xc, xn):
        e = torch.cat([emb(xc[:, i]) for i, emb in enumerate(self.embs)], 1)
        return self.mlp(torch.cat([self.emb_drop(e), xn], 1)).squeeze(1)


def load_data():
    train = pd.read_csv(DATA_DIR / "train.csv")
    test = pd.read_csv(DATA_DIR / "test.csv")
    sample = pd.read_csv(DATA_DIR / "sample_submission.csv")
    if TARGET not in train or TARGET in test or not sample[ID_COL].equals(test[ID_COL]):
        raise ValueError("数据文件不符合预期")
    return train, test, sample


def key_series(df: pd.DataFrame, cols) -> pd.Series:
    parts = []
    for c in cols:
        if c == "_inc_bin100":
            parts.append((df[INCOME] // 100).astype(np.int64).astype(str))
        else:
            parts.append(df[c].astype(str))
    return pd.Series(["|".join(t) for t in zip(*parts)], index=df.index)


def smoothed_te(key_fit, y_fit, key_apply, prior):
    st = pd.DataFrame({"k": key_fit.to_numpy(), "y": y_fit}).groupby("k")["y"].agg(["sum", "count"])
    s = key_apply.map(st["sum"]).fillna(0.0).to_numpy()
    c = key_apply.map(st["count"]).fillna(0.0).to_numpy()
    return (s + prior * TE_SMOOTH) / (c + TE_SMOOTH)


def fold_target_encoding(key_tr, y_tr, key_va, key_te, seed):
    prior = float(y_tr.mean())
    key_tr = key_tr.reset_index(drop=True)
    enc = np.zeros(len(key_tr))
    for a, b in StratifiedKFold(N_INNER, shuffle=True, random_state=seed).split(key_tr, y_tr):
        enc[b] = smoothed_te(key_tr.iloc[a], y_tr[a], key_tr.iloc[b], prior)
    return enc, smoothed_te(key_tr, y_tr, key_va, prior), smoothed_te(key_tr, y_tr, key_te, prior)


def logit(p):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def predict(model, xc, xn):
    model.eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(xc), 65536):
            out.append(torch.sigmoid(model(xc[i:i + 65536], xn[i:i + 65536])).float().cpu().numpy())
    return np.concatenate(out)


def main():
    start = time.time()
    dev = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print("device", dev)
    train, test, sample = load_data()
    y = (train[TARGET] == POS_LABEL).to_numpy(np.float32)
    yi = y.astype(np.int8)

    xc_tr, xc_te, vocab = [], [], []
    for col, min_count, dim in CAT_SPEC:
        allv = pd.concat([train[col], test[col]]).astype(str)
        vc = allv.value_counts()
        mapping = {v: i + 1 for i, v in enumerate(vc[vc >= min_count].index)}
        xc_tr.append(train[col].astype(str).map(mapping).fillna(0).astype(np.int64).values)
        xc_te.append(test[col].astype(str).map(mapping).fillna(0).astype(np.int64).values)
        vocab.append((len(mapping) + 1, dim))
    xc_tr = np.stack(xc_tr, 1)
    xc_te = np.stack(xc_te, 1)
    xn_tr = train[NUM_COLS].astype(np.float32).values.copy()
    xn_te = test[NUM_COLS].astype(np.float32).values.copy()
    xn_tr[:, 0] = np.log(xn_tr[:, 0]); xn_te[:, 0] = np.log(xn_te[:, 0])
    mu, sd = xn_tr.mean(0), xn_tr.std(0) + 1e-6
    xn_tr = (xn_tr - mu) / sd; xn_te = (xn_te - mu) / sd

    keys_tr = {k: key_series(train, c) for k, c in TE_KEYS.items()}
    keys_te = {k: key_series(test, c) for k, c in TE_KEYS.items()}
    te_names = list(TE_KEYS)
    n_num = len(NUM_COLS) + len(te_names)

    XC = torch.tensor(xc_tr, device=dev); XCt = torch.tensor(xc_te, device=dev)
    XN_base = torch.tensor(xn_tr, device=dev); XNt_base = torch.tensor(xn_te, device=dev)
    Y = torch.tensor(y, device=dev)
    lossf = nn.BCEWithLogitsLoss()

    oof = np.zeros(len(train)); test_pred = np.zeros(len(test))
    fold_scores, best_epochs = [], []
    splitter = StratifiedKFold(N_FOLDS, shuffle=True, random_state=SEED)
    for fold, (ti, vi) in enumerate(splitter.split(xc_tr, yi), 1):
        # 折内 TE → logit → 训练侧标准化
        ftr = np.zeros((len(ti), len(te_names)), np.float32)
        fva = np.zeros((len(vi), len(te_names)), np.float32)
        fte = np.zeros((len(test), len(te_names)), np.float32)
        for j, k in enumerate(te_names):
            e1, e2, e3 = fold_target_encoding(keys_tr[k].iloc[ti], yi[ti], keys_tr[k].iloc[vi], keys_te[k], SEED + fold)
            l1, l2, l3 = logit(e1), logit(e2), logit(e3)
            m_, s_ = l1.mean(), l1.std() + 1e-6
            ftr[:, j] = (l1 - m_) / s_; fva[:, j] = (l2 - m_) / s_; fte[:, j] = (l3 - m_) / s_
        XN = torch.zeros((len(train), n_num), device=dev); XN[:, :len(NUM_COLS)] = XN_base
        XN[torch.tensor(ti, device=dev), len(NUM_COLS):] = torch.tensor(ftr, device=dev)
        XN[torch.tensor(vi, device=dev), len(NUM_COLS):] = torch.tensor(fva, device=dev)
        XNt = torch.cat([XNt_base, torch.tensor(fte, device=dev)], 1)

        fold_valid = np.zeros(len(vi)); fold_test = np.zeros(len(test)); fold_eps = []
        ti_t = torch.tensor(ti, device=dev)
        for mseed in MODEL_SEEDS:
            torch.manual_seed(SEED + fold + 1000 * mseed)
            model = Net(vocab, n_num).to(dev)
            opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WD)
            sched = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, mode="max", factor=0.5, patience=1)
            best, best_ep, bad, best_state, best_pv = -1.0, 0, 0, None, None
            for ep in range(1, EPOCHS + 1):
                model.train()
                perm = ti_t[torch.randperm(len(ti_t), device=dev)]
                for i in range(0, len(perm), BATCH):
                    idx = perm[i:i + BATCH]
                    opt.zero_grad(); loss = lossf(model(XC[idx], XN[idx]), Y[idx]); loss.backward(); opt.step()
                pv = predict(model, XC[vi], XN[vi]); auc = roc_auc_score(yi[vi], pv); sched.step(auc)
                if auc > best:
                    best, best_ep, bad = auc, ep, 0
                    best_state = {k_: v_.detach().clone() for k_, v_ in model.state_dict().items()}; best_pv = pv
                else:
                    bad += 1
                if bad >= PATIENCE:
                    break
            model.load_state_dict(best_state)
            fold_valid += best_pv / len(MODEL_SEEDS); fold_test += predict(model, XCt, XNt) / len(MODEL_SEEDS); fold_eps.append(best_ep)
            print(f"  fold={fold} mseed={mseed} auc={best:.6f} best_ep={best_ep} elapsed={time.time() - start:.0f}s", flush=True)
        oof[vi] = fold_valid; test_pred += fold_test / N_FOLDS
        fold_scores.append(float(roc_auc_score(yi[vi], fold_valid))); best_epochs.append(fold_eps)
        print(f"fold={fold} auc={fold_scores[-1]:.6f} elapsed={time.time() - start:.0f}s", flush=True)

    oof_auc = float(roc_auc_score(yi, oof))
    base = json.loads(BASE_RESULTS.read_text(encoding="utf-8"))
    deltas = np.full(len(fold_scores), np.nan)  # 10 折与 5 折基准逐折不可比
    print(f"OOF AUC={oof_auc:.6f}, delta_vs_v6={oof_auc - base['oof_auc']:+.6f} (逐折不可比)")

    submission = sample.copy(); submission[TARGET] = test_pred
    if not np.isfinite(test_pred).all() or ((test_pred < 0) | (test_pred > 1)).any():
        raise ValueError("提交概率非法")
    submission.to_csv(OUT_DIR / "submission.csv", index=False)
    np.save(OUT_DIR / "oof_proba.npy", oof); np.save(OUT_DIR / "test_proba.npy", test_pred)
    results = {
        "competition": "playground-series-s6e9", "model": "MLP + value embeddings + fold-wise TE inputs, 3-seed bagging, 10 outer folds",
        "seed": SEED, "n_folds": N_FOLDS, "model_seeds": MODEL_SEEDS, "te_keys": TE_KEYS, "cat_spec": CAT_SPEC, "num_cols": NUM_COLS,
        "hyper": {"epochs": EPOCHS, "batch": BATCH, "lr": LR, "wd": WD, "width": WIDTH, "drop": DROP, "emb_drop": EMB_DROP, "patience": PATIENCE},
        "fold_auc": fold_scores, "fold_auc_mean": float(np.mean(fold_scores)), "fold_auc_std": float(np.std(fold_scores)),
        "best_epochs": best_epochs, "oof_auc": oof_auc, "base": "v6_mlp_te", "base_oof_auc": base["oof_auc"],
        "oof_delta_vs_base": oof_auc - base["oof_auc"], "fold_delta_vs_base": None, "folds_won_vs_base": None,
        "prediction_mean": float(test_pred.mean()), "elapsed_seconds": time.time() - start, "torch_version": torch.__version__, "device": str(dev),
    }
    (OUT_DIR / "cv_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"submission={OUT_DIR / 'submission.csv'}  elapsed={time.time() - start:.0f}s")


if __name__ == "__main__":
    main()
