#!/usr/bin/env python3
"""
基于 OOF 探索得到的候选权重，生成少量“可复查”融合提交文件。

约定：
- 不再盲目全量融合，改为只做 2-3 个高优先级候选；
- 主要用于线下 OOF 验证和保守提交决策支持。
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "model"
OUT_DIR = Path(__file__).resolve().parent


def load_submission(path: Path) -> pd.Series:
    df = pd.read_csv(path)
    return df.sort_values("id")["addicted_label"].astype(float).to_numpy()


def blend_and_write(name: str, pred_list, weight_list, ids) -> None:
    pred = sum(w * p for w, p in zip(weight_list, pred_list))
    out = pd.DataFrame({"id": ids, "addicted_label": pred.clip(0.0, 1.0)})
    out.to_csv(OUT_DIR / name, index=False)
    print(f"[done] {name}")


def main() -> None:
    ids = pd.read_csv(MODEL_DIR / "v12_xgboost_rank_blend" / "submission.csv")["id"].to_numpy()
    subs = {
        "v13_xgb": load_submission(MODEL_DIR / "v13_fe_single_compare" / "submission_xgb.csv"),
        "v8": load_submission(MODEL_DIR / "v8_three_model_blend" / "submission.csv"),
        "v7": load_submission(MODEL_DIR / "v7_catboost_bagging" / "submission.csv"),
        "v3": load_submission(MODEL_DIR / "v3_dual_catboost" / "submission.csv"),
        "v12_prob": load_submission(MODEL_DIR / "v12_xgboost_rank_blend" / "submission.csv"),
        "v6": load_submission(MODEL_DIR / "v6_highres_lgbm" / "submission.csv"),
        "v12_rank": load_submission(MODEL_DIR / "v12_xgboost_rank_blend" / "submission_rank.csv"),
    }

    # 1) OOF 扫描里 pair best（v13_xgb + v8）
    blend_and_write(
        "submission_pair_v13xgb_13pct_v8_87pct.csv",
        [subs["v13_xgb"], subs["v8"]],
        [0.13, 0.87],
        ids,
    )

    # 2) v7 与 v8（偏向 v8）
    blend_and_write(
        "submission_pair_v7_3pct_v8_97pct.csv",
        [subs["v7"], subs["v8"]],
        [0.03, 0.97],
        ids,
    )

    # 3) ridge/逻辑回归线性近似候选（OOF 上 0.968635）
    blend_and_write(
        "submission_tri_v8_v3_v13xgb_0.8408_0.0670_0.0922.csv",
        [subs["v8"], subs["v3"], subs["v13_xgb"]],
        [0.8407889, 0.06700698, 0.09220412],
        ids,
    )

    # 4) 常规稳定参考：v12 rank 与 v8 混合（较小扰动）
    blend_and_write(
        "submission_pair_v12rank_20pct_v8_80pct.csv",
        [subs["v12_rank"], subs["v8"]],
        [0.20, 0.80],
        ids,
    )

    # 5) 单模型 baseline for 快速校验（v8）
    pd.DataFrame({"id": ids, "addicted_label": subs["v8"]}).to_csv(
        OUT_DIR / "submission_v8_ref_copy.csv", index=False
    )
    print("all candidates generated.")


if __name__ == "__main__":
    main()
