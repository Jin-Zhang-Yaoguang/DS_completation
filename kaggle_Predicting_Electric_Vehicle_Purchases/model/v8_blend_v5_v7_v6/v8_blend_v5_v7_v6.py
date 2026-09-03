# -*- coding: utf-8 -*-
"""
v8：v5（LightGBM TE bagging）+ v7（CatBoost 双表示 bagging）+ v6（MLP embedding + TE）三成员 percentile-rank 融合。

- 各成员 OOF / 测试预测在自身集合内做百分位秩变换；
- 权重交叉拟合：外层同 seed 5 折，每折在其余 4 折上用 Nelder-Mead 优化归一化权重，再应用到该折；
- 预注册门槛：相对最佳单成员，五折全部提升且整体 OOF 增益 >= 1e-4，否则不生成提交文件；
- 最终测试权重取五折所选权重的均值。
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import rankdata, spearmanr
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


SEED = 42
N_FOLDS = 5
TARGET = "Will_Buy_EV"
ID_COL = "id"
POS_LABEL = "Yes"
MIN_OOF_GAIN = 1e-4

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
OUT_DIR = Path(__file__).resolve().parent
MODEL_DIR = OUT_DIR.parent
MEMBERS = {"v5": "v5_lgbm_te_bag", "v7": "v7_catboost_bag", "v6": "v6_mlp_te"}


def pct_rank(x):
    return rankdata(x) / len(x)


def fit_weights(R, keys, y, idx):
    def neg(w):
        w = np.abs(w); w = w / w.sum()
        return -roc_auc_score(y[idx], sum(wi * R[k][idx] for wi, k in zip(w, keys)))
    r = minimize(neg, np.ones(len(keys)) / len(keys), method="Nelder-Mead",
                 options={"xatol": 1e-3, "fatol": 1e-7, "maxiter": 300})
    w = np.abs(r.x)
    return w / w.sum()


def main():
    train = pd.read_csv(DATA_DIR / "train.csv", usecols=[ID_COL, TARGET])
    test = pd.read_csv(DATA_DIR / "test.csv", usecols=[ID_COL])
    sample = pd.read_csv(DATA_DIR / "sample_submission.csv")
    y = (train[TARGET] == POS_LABEL).to_numpy(np.int8)
    keys = list(MEMBERS)

    oof = {k: np.load(MODEL_DIR / d / "oof_proba.npy") for k, d in MEMBERS.items()}
    tst = {k: np.load(MODEL_DIR / d / "test_proba.npy") for k, d in MEMBERS.items()}
    member_auc = {k: float(roc_auc_score(y, v)) for k, v in oof.items()}
    best_member = max(member_auc, key=member_auc.get)
    print("member OOF AUC:", {k: round(v, 6) for k, v in member_auc.items()})
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            print(f"spearman {keys[i]}-{keys[j]}: {spearmanr(oof[keys[i]], oof[keys[j]]).correlation:.4f}")

    R = {k: pct_rank(v) for k, v in oof.items()}
    Rt = {k: pct_rank(v) for k, v in tst.items()}
    blend_oof = np.zeros(len(y)); chosen = []; fold_rows = []
    for fold, (fit_idx, apply_idx) in enumerate(StratifiedKFold(N_FOLDS, shuffle=True, random_state=SEED).split(y, y), 1):
        w = fit_weights(R, keys, y, fit_idx); chosen.append(w)
        blend_oof[apply_idx] = sum(wi * R[k][apply_idx] for wi, k in zip(w, keys))
        b = float(roc_auc_score(y[apply_idx], blend_oof[apply_idx]))
        m = {k: float(roc_auc_score(y[apply_idx], oof[k][apply_idx])) for k in keys}
        fold_rows.append({"fold": fold, "w": dict(zip(keys, np.round(w, 4).tolist())), "blend": b, **m, "delta_vs_best_member": b - m[best_member]})
        print(f"fold={fold} w={dict(zip(keys, np.round(w, 3)))} blend={b:.6f} " + " ".join(f"{k}={v:.6f}" for k, v in m.items()) + f" delta_vs_{best_member}={b - m[best_member]:+.6f}")

    blend_auc = float(roc_auc_score(y, blend_oof)); gain = blend_auc - member_auc[best_member]
    folds_won = sum(r["delta_vs_best_member"] > 0 for r in fold_rows)
    final_w = np.mean(chosen, axis=0)
    print(f"cross-fitted blend OOF AUC={blend_auc:.6f} gain_vs_{best_member}={gain:+.6f} folds_won={folds_won}/{N_FOLDS} final_w={dict(zip(keys, np.round(final_w, 4)))}")
    test_blend = sum(wi * Rt[k] for wi, k in zip(final_w, keys))

    results = {"competition": "playground-series-s6e9", "model": "percentile-rank blend v5+v7+v6, cross-fitted Nelder-Mead weights",
               "members": MEMBERS, "member_oof_auc": member_auc, "best_member": best_member, "fold_results": fold_rows,
               "final_w": dict(zip(keys, final_w.tolist())), "oof_auc": blend_auc, "oof_delta_vs_best_member": gain,
               "folds_won_vs_best_member": int(folds_won), "min_oof_gain_threshold": MIN_OOF_GAIN,
               "passed_threshold": bool(folds_won == N_FOLDS and gain >= MIN_OOF_GAIN)}
    (OUT_DIR / "cv_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    np.save(OUT_DIR / "oof_proba.npy", blend_oof); np.save(OUT_DIR / "test_proba.npy", test_blend)
    if not results["passed_threshold"]:
        print("未通过预注册门槛，不生成提交文件。"); sys.exit(1)
    submission = sample.copy(); submission[TARGET] = test_blend
    if not submission[ID_COL].equals(test[ID_COL]) or not np.isfinite(test_blend).all() or ((test_blend < 0) | (test_blend > 1)).any():
        raise ValueError("提交格式异常")
    submission.to_csv(OUT_DIR / "submission.csv", index=False)
    print(f"submission={OUT_DIR / 'submission.csv'}")


if __name__ == "__main__":
    main()
