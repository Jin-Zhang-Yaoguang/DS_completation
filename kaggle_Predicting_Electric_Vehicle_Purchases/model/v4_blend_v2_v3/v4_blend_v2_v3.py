# -*- coding: utf-8 -*-
"""
v4：v2（LightGBM + 收入伪影特征）与 v3（CatBoost 双表示）的 percentile-rank 融合。

赛题：Predicting Electric Vehicle Purchases（Playground Series S6E9）
指标：ROC AUC

- 融合对象为两模型的 OOF / 测试预测，各自在自身集合内做百分位秩变换；
- 权重用交叉拟合选择：外层同 seed 5 折，每折在其余 4 折上网格搜索 w_v2，
  再应用到该折，得到无偏的融合 OOF；
- 预注册门槛：相对 v2，五折全部提升且整体 OOF 增益 >= 1e-4，否则不生成提交文件；
- 最终测试权重取五折所选权重的均值。
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


SEED = 42
N_FOLDS = 5
TARGET = "Will_Buy_EV"
ID_COL = "id"
POS_LABEL = "Yes"
MIN_OOF_GAIN = 1e-4
GRID = np.round(np.arange(0.0, 1.0001, 0.01), 2)

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
OUT_DIR = Path(__file__).resolve().parent
MODEL_DIR = OUT_DIR.parent
MEMBERS = {"v2": "v2_income_artifact_lgbm", "v3": "v3_dual_catboost"}


def pct_rank(x: np.ndarray) -> np.ndarray:
    return rankdata(x) / len(x)


def main() -> None:
    train = pd.read_csv(DATA_DIR / "train.csv", usecols=[ID_COL, TARGET])
    test = pd.read_csv(DATA_DIR / "test.csv", usecols=[ID_COL])
    sample = pd.read_csv(DATA_DIR / "sample_submission.csv")
    y = (train[TARGET] == POS_LABEL).to_numpy(dtype=np.int8)

    oof = {k: np.load(MODEL_DIR / d / "oof_proba.npy") for k, d in MEMBERS.items()}
    tst = {k: np.load(MODEL_DIR / d / "test_proba.npy") for k, d in MEMBERS.items()}
    member_auc = {k: float(roc_auc_score(y, v)) for k, v in oof.items()}
    print("member OOF AUC:", {k: round(v, 6) for k, v in member_auc.items()})

    r_oof = {k: pct_rank(v) for k, v in oof.items()}
    r_tst = {k: pct_rank(v) for k, v in tst.items()}

    splitter = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    blend_oof = np.zeros(len(y), dtype=np.float64)
    chosen_w: list[float] = []
    fold_rows: list[dict] = []
    for fold, (fit_idx, apply_idx) in enumerate(splitter.split(r_oof["v2"], y), start=1):
        scores = [
            roc_auc_score(y[fit_idx], w * r_oof["v2"][fit_idx] + (1 - w) * r_oof["v3"][fit_idx])
            for w in GRID
        ]
        w = float(GRID[int(np.argmax(scores))])
        chosen_w.append(w)
        blend_oof[apply_idx] = w * r_oof["v2"][apply_idx] + (1 - w) * r_oof["v3"][apply_idx]
        b = float(roc_auc_score(y[apply_idx], blend_oof[apply_idx]))
        v2 = float(roc_auc_score(y[apply_idx], oof["v2"][apply_idx]))
        v3 = float(roc_auc_score(y[apply_idx], oof["v3"][apply_idx]))
        fold_rows.append({"fold": fold, "w_v2": w, "blend": b, "v2": v2, "v3": v3, "delta_vs_v2": b - v2})
        print(f"fold={fold} w_v2={w:.2f} blend={b:.6f} v2={v2:.6f} v3={v3:.6f} delta_vs_v2={b - v2:+.6f}")

    blend_auc = float(roc_auc_score(y, blend_oof))
    gain = blend_auc - member_auc["v2"]
    folds_won = sum(r["delta_vs_v2"] > 0 for r in fold_rows)
    print(f"cross-fitted blend OOF AUC={blend_auc:.6f} gain_vs_v2={gain:+.6f} folds_won={folds_won}/{N_FOLDS}")

    final_w = float(np.mean(chosen_w))
    test_blend = final_w * r_tst["v2"] + (1 - final_w) * r_tst["v3"]
    print(f"final w_v2={final_w:.3f} (mean of {chosen_w})")

    results = {
        "competition": "playground-series-s6e9",
        "model": "percentile-rank blend of v2 + v3, cross-fitted weight",
        "members": MEMBERS,
        "member_oof_auc": member_auc,
        "fold_results": fold_rows,
        "chosen_w_v2": chosen_w,
        "final_w_v2": final_w,
        "oof_auc": blend_auc,
        "base": "v2_income_artifact_lgbm",
        "base_oof_auc": member_auc["v2"],
        "oof_delta_vs_base": gain,
        "folds_won_vs_base": int(folds_won),
        "min_oof_gain_threshold": MIN_OOF_GAIN,
        "passed_threshold": bool(folds_won == N_FOLDS and gain >= MIN_OOF_GAIN),
    }
    (OUT_DIR / "cv_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    np.save(OUT_DIR / "oof_proba.npy", blend_oof)
    np.save(OUT_DIR / "test_proba.npy", test_blend)

    if not results["passed_threshold"]:
        print("未通过预注册门槛，不生成提交文件。")
        sys.exit(1)

    submission = sample.copy()
    submission[TARGET] = test_blend
    if not submission[ID_COL].equals(test[ID_COL]) or submission.shape != sample.shape:
        raise ValueError("提交格式异常")
    if not np.isfinite(test_blend).all() or ((test_blend < 0) | (test_blend > 1)).any():
        raise ValueError("融合分数超出 [0, 1]")
    submission.to_csv(OUT_DIR / "submission.csv", index=False)
    print(f"submission={OUT_DIR / 'submission.csv'}")


if __name__ == "__main__":
    main()
