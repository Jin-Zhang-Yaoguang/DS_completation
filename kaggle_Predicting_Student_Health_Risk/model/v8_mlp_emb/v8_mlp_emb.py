# -*- coding: utf-8 -*-
"""
方案 v8：Entity Embedding MLP（PyTorch，MPS 加速）

设计目的：与 v6（TE-HGBC）做**跨家族融合**。同家族 GBDT 融合已被 v7 证伪
（两两分歧仅 0.5~1.1%，OOF 微增而 LB 回吐）。要突破 0.95057 天花板，
必须引入分歧率 5%+ 的异源成员——即用**完全不同的特征表示**训练神经网络。

与 v6 的解耦点：
- v6 用 TargetEncoder(cv=5) 把 13 列全部字符串化后逐值 TE，把「逐值经验条件率」
  直接递给 HGBC。特征表示 = 3×13 = 39 维标签率查表。
- v8 用 Entity Embedding 让 6 个类别列各自学 3~6 维向量；7 个数值列走
  标准化 + 缺失指示。不接触任何 target-encoded 表示。
- 早停口径：logloss（NN 校准好过树模型；调研教训：树模型上指标早停，NN 上 logloss 早停）

冻结 CV：seed=42, 5 折 StratifiedKFold（与本项目所有方案对齐，OOF 概率可直接相加融合）。
"""

import time
from pathlib import Path
from itertools import product as iprod

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.impute import SimpleImputer
from sklearn.metrics import balanced_accuracy_score, confusion_matrix
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset

SEED = 42
N_FOLDS = 5
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
OUT_DIR = Path(__file__).resolve().parent

CAT_COLS = ["diet_type", "stress_level", "sleep_quality",
            "physical_activity_level", "smoking_alcohol", "gender"]
NUM_COLS = ["sleep_duration", "heart_rate", "bmi", "calorie_expenditure",
            "step_count", "exercise_duration", "water_intake"]
RAW = NUM_COLS + CAT_COLS
TARGET = "health_condition"

DEVICE = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

BATCH_SIZE = 4096
EVAL_BATCH = 8192
MAX_EPOCHS = 100
PATIENCE = 8
LR = 1e-3
WD = 1e-4
DROPOUT = 0.3
HIDDEN = (384, 256, 128)


class EmbMLP(nn.Module):
    """
    每个类别列独立 embedding；数值和缺失指示走一层 BN 归一化后与 embedding 拼接，
    再进三层 MLP。类别列 embedding 维度 = min(6, ceil(sqrt(cardinality))+1)。
    """
    def __init__(self, cat_cardinalities, n_num, n_miss, hidden_dims, dropout, n_classes=3):
        super().__init__()
        self.embs = nn.ModuleList()
        emb_total = 0
        for card in cat_cardinalities:
            dim = min(6, int(np.ceil(np.sqrt(card))) + 1)
            self.embs.append(nn.Embedding(card, dim))
            emb_total += dim

        self.num_bn = nn.BatchNorm1d(n_num + n_miss)

        in_dim = emb_total + n_num + n_miss
        layers = []
        prev = in_dim
        for h in hidden_dims:
            layers += [nn.Linear(prev, h), nn.BatchNorm1d(h),
                       nn.ReLU(), nn.Dropout(dropout)]
            prev = h
        layers.append(nn.Linear(prev, n_classes))
        self.mlp = nn.Sequential(*layers)

    def forward(self, x_cat, x_num):
        emb = torch.cat([e(x_cat[:, i]) for i, e in enumerate(self.embs)], dim=1)
        num = self.num_bn(x_num)
        return self.mlp(torch.cat([emb, num], dim=1))


def build_cat_encoders(train, test):
    """把每个类别列（含 NaN）映射为 0..K-1 的整数，NaN 归入 K-1（专用 code）。"""
    encoders = {}
    for c in CAT_COLS:
        cats = pd.concat([train[c], test[c]], ignore_index=True)
        uniq = cats.dropna().astype(str).unique().tolist()
        code = {v: i for i, v in enumerate(sorted(uniq))}
        code["__NAN__"] = len(code)
        encoders[c] = code
    return encoders


def encode_cat(df, encoders):
    out = np.zeros((len(df), len(CAT_COLS)), dtype=np.int64)
    for j, c in enumerate(CAT_COLS):
        s = df[c].astype(str).where(df[c].notna(), "__NAN__")
        out[:, j] = s.map(encoders[c]).values.astype(np.int64)
    return out


def search_class_weights(proba, y):
    def _grid(g1, g2, best):
        for w1, w2 in iprod(g1, g2):
            s = balanced_accuracy_score(y, (proba * np.array([1.0, w1, w2])).argmax(1))
            if s > best[0]:
                best = (s, w1, w2)
        return best

    best = (balanced_accuracy_score(y, proba.argmax(1)), 1.0, 1.0)
    best = _grid(np.linspace(1, 12, 45), np.linspace(1, 12, 45), best)
    s, w1, w2 = _grid(np.linspace(max(0.5, best[1] - 0.3), best[1] + 0.3, 25),
                      np.linspace(max(0.5, best[2] - 0.3), best[2] + 0.3, 25), best)
    return s, np.array([1.0, w1, w2])


def train_fold(model, tr_loader, va_loader, class_weight, fold):
    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WD)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=MAX_EPOCHS)
    criterion = nn.CrossEntropyLoss(weight=torch.tensor(class_weight, device=DEVICE))

    best_val_loss = float("inf")
    best_state = None
    patience = 0

    for epoch in range(MAX_EPOCHS):
        model.train()
        for xc, xn, yb in tr_loader:
            xc, xn, yb = xc.to(DEVICE), xn.to(DEVICE), yb.to(DEVICE)
            optimizer.zero_grad()
            loss = criterion(model(xc, xn), yb)
            loss.backward()
            optimizer.step()
        scheduler.step()

        model.eval()
        val_loss_sum, val_n = 0.0, 0
        with torch.no_grad():
            for xc, xn, yb in va_loader:
                xc, xn, yb = xc.to(DEVICE), xn.to(DEVICE), yb.to(DEVICE)
                loss = criterion(model(xc, xn), yb)
                val_loss_sum += loss.item() * len(yb)
                val_n += len(yb)
        val_loss = val_loss_sum / val_n

        if val_loss < best_val_loss - 1e-5:
            best_val_loss = val_loss
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            patience = 0
        else:
            patience += 1
            if patience >= PATIENCE:
                break

    model.load_state_dict(best_state)
    model.to(DEVICE)
    return epoch + 1, best_val_loss


@torch.no_grad()
def predict_proba(model, loader):
    model.eval()
    outs = []
    for batch in loader:
        xc, xn = batch[0].to(DEVICE), batch[1].to(DEVICE)
        outs.append(torch.softmax(model(xc, xn), dim=1).cpu().numpy())
    return np.concatenate(outs, axis=0)


def main():
    t0 = time.time()
    torch.manual_seed(SEED)
    np.random.seed(SEED)

    train = pd.read_csv(DATA_DIR / "train.csv")
    test = pd.read_csv(DATA_DIR / "test.csv")
    sub = pd.read_csv(DATA_DIR / "sample_submission.csv")
    print(f"train {train.shape} | test {test.shape} | 设备 {DEVICE}", flush=True)

    classes = sorted(train[TARGET].unique())
    y = train[TARGET].map({c: i for i, c in enumerate(classes)}).values

    encoders = build_cat_encoders(train, test)
    cat_cards = [len(e) for e in encoders.values()]
    print(f"类别基数: {dict(zip(CAT_COLS, cat_cards))}", flush=True)

    Xc_all = encode_cat(train, encoders)
    Xc_test = encode_cat(test, encoders)

    miss_all = train[RAW].isnull().astype(np.float32).values
    miss_test = test[RAW].isnull().astype(np.float32).values

    oof = np.zeros((len(train), 3), dtype=np.float64)
    test_pred = np.zeros((len(test), 3), dtype=np.float64)

    skf = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    for fold, (tr, va) in enumerate(skf.split(train, y)):
        ts = time.time()

        imp = SimpleImputer(strategy="median")
        Xn_tr = imp.fit_transform(train[NUM_COLS].iloc[tr]).astype(np.float32)
        Xn_va = imp.transform(train[NUM_COLS].iloc[va]).astype(np.float32)
        Xn_te = imp.transform(test[NUM_COLS]).astype(np.float32)

        scaler = StandardScaler()
        Xn_tr = scaler.fit_transform(Xn_tr).astype(np.float32)
        Xn_va = scaler.transform(Xn_va).astype(np.float32)
        Xn_te = scaler.transform(Xn_te).astype(np.float32)

        Xn_tr_full = np.hstack([Xn_tr, miss_all[tr]]).astype(np.float32)
        Xn_va_full = np.hstack([Xn_va, miss_all[va]]).astype(np.float32)
        Xn_te_full = np.hstack([Xn_te, miss_test]).astype(np.float32)

        Xc_tr = Xc_all[tr]
        Xc_va = Xc_all[va]

        y_tr = y[tr]
        y_va = y[va]

        counts = np.bincount(y_tr, minlength=3)
        class_weight = (len(y_tr) / (3 * counts)).astype(np.float32)

        tr_ds = TensorDataset(torch.from_numpy(Xc_tr),
                              torch.from_numpy(Xn_tr_full),
                              torch.from_numpy(y_tr.astype(np.int64)))
        va_ds = TensorDataset(torch.from_numpy(Xc_va),
                              torch.from_numpy(Xn_va_full),
                              torch.from_numpy(y_va.astype(np.int64)))
        te_ds = TensorDataset(torch.from_numpy(Xc_test),
                              torch.from_numpy(Xn_te_full))

        tr_loader = DataLoader(tr_ds, batch_size=BATCH_SIZE, shuffle=True, drop_last=False)
        va_loader = DataLoader(va_ds, batch_size=EVAL_BATCH, shuffle=False)
        te_loader = DataLoader(te_ds, batch_size=EVAL_BATCH, shuffle=False)

        model = EmbMLP(cat_cards, n_num=len(NUM_COLS), n_miss=len(RAW),
                       hidden_dims=HIDDEN, dropout=DROPOUT, n_classes=3).to(DEVICE)

        n_epochs, best_vloss = train_fold(model, tr_loader, va_loader, class_weight, fold)

        oof[va] = predict_proba(model, va_loader)
        test_pred += predict_proba(model, te_loader) / N_FOLDS

        ba = balanced_accuracy_score(y_va, oof[va].argmax(1))
        print(f"fold {fold}: BA = {ba:.5f} | epochs={n_epochs} | val_ll={best_vloss:.4f} "
              f"| {time.time() - ts:.0f}s", flush=True)

    cv_raw = balanced_accuracy_score(y, oof.argmax(1))
    cv_weighted, w = search_class_weights(oof, y)
    print(f"\nargmax OOF: {cv_raw:.5f}")
    print(f"加权 OOF: {cv_weighted:.5f} (w={w.round(3)})")
    print("混淆矩阵（加权后，顺序 %s）:" % classes)
    print(confusion_matrix(y, (oof * w).argmax(1)))

    # 与 v6 的分歧率（诊断，看跨家族是否给出多样性）
    v6_oof = np.load(OUT_DIR.parent / "v6_te_hgbc/oof_proba.npy")
    v6_w = np.load(OUT_DIR.parent / "v6_te_hgbc/best_class_weights.npy")
    v6_pred = (v6_oof * v6_w).argmax(1)
    v8_pred = (oof * w).argmax(1)
    disagree = np.mean(v6_pred != v8_pred) * 100
    print(f"\n与 v6 加权预测分歧率: {disagree:.2f}% "
          f"(参照：v7 内 GBDT 家族 0.5~1.1%，需 ≥ 5% 才有融合价值)")

    sub[TARGET] = [classes[i] for i in (test_pred * w).argmax(1)]
    sub.to_csv(OUT_DIR / "submission.csv", index=False)
    print("\n提交预测分布:")
    print(sub[TARGET].value_counts(normalize=True).round(4))

    np.save(OUT_DIR / "oof_proba.npy", oof)
    np.save(OUT_DIR / "test_proba.npy", test_pred)
    np.save(OUT_DIR / "best_class_weights.npy", w)

    print(f"\n完成，耗时 {time.time() - t0:.0f}s")
    print(f"CV (加权 OOF balanced accuracy): {cv_weighted:.5f}")


if __name__ == "__main__":
    main()
