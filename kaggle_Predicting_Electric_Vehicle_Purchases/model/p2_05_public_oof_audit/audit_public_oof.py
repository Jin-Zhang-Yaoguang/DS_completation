# -*- coding: utf-8 -*-
"""P2-05：审计 v52 实际使用的公共 OOF，并核验 Smart 的 OOF 边界。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


OUT_DIR = Path(__file__).resolve().parent
MODEL_DIR = OUT_DIR.parent
DATA_DIR = OUT_DIR.parents[1] / "data"
PUBLIC_DIR = MODEL_DIR / "v7_cv_public_blend" / "public_inputs"
V61_DIR = MODEL_DIR / "v61_income_bin10_te_lgbm_40f_depth4_seed104395303"
SMART_DIR = MODEL_DIR / "v13_pb_v7_smart"
TARGET = "Will_Buy_EV"
FIVE_SPLIT_SEEDS = (42, 2026, 3407, 8119, 104729)

# 2026-09-03 从 Kaggle 当前 COMPLETE 内核下载后审计；哈希固定本次证据版本。
SOURCE_AUDIT = {
    "V1": {
        "kernel": "evgendvorkin/s6e9-single-xgb-oof-auc-0-94466",
        "notebook_sha256": "aa57f5cb758f656369bcf4787e23b2bb21fa79f0dd8d8597d92da6738921964e",
        "declared_outer_cv": "StratifiedKFold(10, shuffle=True, random_state=42)",
        "label_boundary": (
            "OOF 仅由外层验证折预测；train+test 只共同拟合无标签频率特征；"
            "外部原始数据只用于 EDA，未进入训练。"
        ),
        "downloaded_oof_file_sha256": "2498d792291a2bc683957b91cbd3a370358d1d5177bd0c76c4ce36469e932395",
        "downloaded_test_file_sha256": "ce56fb307f67ba7b8056a904230114d519cdb4a9e35befc35cca6d02b7385716",
        "collation_oof_exact_match": True,
        "collation_test_max_abs_diff": 0.0,
        "decision": "retain",
    },
    "V2": {
        "kernel": "tamerlanomralinov/s6e9-1st-blood",
        "notebook_sha256": "4dbb778de809837a477e64949ef5e8f2f374bce2f3052238fad7cdd7809f30d2",
        "declared_outer_cv": "StratifiedKFold(5, shuffle=True, random_state=42)",
        "label_boundary": (
            "八个基模型先产生共同五折 OOF；nested logit 的 scaler/系数仅在四折 OOF 上拟合，"
            "再预测未参与元模型拟合的第五折；target encoding 为 fold-inside-fold。"
        ),
        "downloaded_oof_file_sha256": "3679ae913bd52c703c8e270cf05943fb4357974fa0b809d34bd255fdc8afa6d0",
        "downloaded_test_file_sha256": "c9322f289fe598fcfcd897b4357ded57b8807be787ac078ba644d97e2da28b19",
        "collation_oof_exact_match": True,
        "collation_test_max_abs_diff": 6.776263578034403e-21,
        "decision": "retain",
    },
    "V3": {
        "kernel": "dylangunawan13331/ev-purchase-prediction-unified-pipeline",
        "notebook_sha256": "4eb00e045ee2a73bbf2951f6ed2d58995aa0a3d21cd4348d40979a30dcbb889f",
        "declared_outer_cv": "3 seeds [11, 202, 3407] x StratifiedKFold(5)",
        "label_boundary": (
            "每个外层训练折独立拟合 target encoder；训练折内部再次五折交叉编码；"
            "验证折与测试集只做 transform。"
        ),
        "downloaded_oof_file_sha256": "2a8dd2d82e9063a14bd6502370d0e9bc13a425ac2fc072589b0dc052dce383d7",
        "downloaded_test_file_sha256": "4154f00dd7c0e1666b68164703e021680544cd888abf4f908205ac3c73f2b252",
        "collation_oof_exact_match": True,
        "collation_test_max_abs_diff": 1.3552527156068805e-20,
        "decision": "retain",
    },
    "V4": {
        "kernel": "kirill0212/s6e9-lightgbm",
        "notebook_sha256": "365bf64ed8db622f1f865381971011012b811c685de1b49e91d3cfcc16e4ca42",
        "declared_outer_cv": "StratifiedKFold(5, shuffle=True, random_state=42)",
        "label_boundary": (
            "target encoder 只看外层训练折标签，训练折编码由内层五折生成；"
            "验证折与测试集只做 transform。"
        ),
        "downloaded_oof_file_sha256": "1f56228f4fd9874bb10bd238c73d536bd06271986b4ede23acd447ac85bbebde",
        "downloaded_test_file_sha256": "5d85442683e0129ae19de806b79242366505f08ecd3f9f52e07238d6da9e6d3b",
        "collation_oof_exact_match": True,
        "collation_test_max_abs_diff": 1.3552527156068805e-20,
        "decision": "retain",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pct_rank(values: np.ndarray) -> np.ndarray:
    return rankdata(np.asarray(values, dtype=np.float64), method="average") / len(values)


def fold_auc_rows(
    y: np.ndarray, values: np.ndarray, n_splits: int, seed: int
) -> list[float]:
    splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    return [
        float(roc_auc_score(y[valid_idx], values[valid_idx]))
        for _, valid_idx in splitter.split(values, y)
    ]


def single_feature_crossfit(y: np.ndarray, values: np.ndarray) -> dict[str, object]:
    feature = pct_rank(values).reshape(-1, 1)
    rows: list[dict[str, float | int]] = []
    for seed in FIVE_SPLIT_SEEDS:
        splitter = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
        for fold, (fit_idx, valid_idx) in enumerate(splitter.split(feature, y), 1):
            model = LogisticRegression(C=1.0, solver="lbfgs", max_iter=200)
            model.fit(feature[fit_idx], y[fit_idx])
            prediction = model.predict_proba(feature[valid_idx])[:, 1]
            rows.append(
                {
                    "seed": seed,
                    "fold": fold,
                    "coefficient": float(model.coef_[0, 0]),
                    "valid_auc": float(roc_auc_score(y[valid_idx], prediction)),
                }
            )
    auc = np.array([row["valid_auc"] for row in rows], dtype=np.float64)
    coefficient = np.array([row["coefficient"] for row in rows], dtype=np.float64)
    return {
        "fold_count": len(rows),
        "all_coefficients_positive": bool((coefficient > 0).all()),
        "coefficient_min": float(coefficient.min()),
        "coefficient_max": float(coefficient.max()),
        "valid_auc_mean": float(auc.mean()),
        "valid_auc_std": float(auc.std(ddof=1)),
        "rows": rows,
        "interpretation": (
            "仅检验五组切分下方向和行对齐是否稳定；单特征交叉拟合不能单独证明 OOF 无泄漏。"
        ),
    }


def main() -> None:
    train = pd.read_csv(DATA_DIR / "train.csv", usecols=[TARGET])
    y = train[TARGET].eq("Yes").to_numpy(np.int8)
    public_oof_path = PUBLIC_DIR / "OOF_Preds.parquet"
    public_test_path = PUBLIC_DIR / "Mdl_Preds.parquet"
    public_oof = pd.read_parquet(public_oof_path)
    public_test = pd.read_parquet(public_test_path)
    v61 = np.load(V61_DIR / "oof_proba.npy")
    if len(public_oof) != len(y) or len(v61) != len(y):
        raise ValueError("OOF 长度与训练集不一致")
    if len(public_test) != 286_571:
        raise ValueError("公共 test 预测长度异常")

    v61_fold_auc = np.array(fold_auc_rows(y, v61, 40, 42))
    members: dict[str, object] = {}
    for name in ("V1", "V2", "V3", "V4"):
        values = public_oof[name].to_numpy(np.float64)
        test_values = public_test[name].to_numpy(np.float64)
        if not np.isfinite(values).all() or not np.isfinite(test_values).all():
            raise ValueError(f"{name} 存在非有限预测")
        fold_auc = np.array(fold_auc_rows(y, values, 40, 42))
        delta = fold_auc - v61_fold_auc
        members[name] = {
            "source_audit": SOURCE_AUDIT[name],
            "oof_auc": float(roc_auc_score(y, values)),
            "oof_mean": float(values.mean()),
            "oof_std": float(values.std()),
            "test_mean": float(test_values.mean()),
            "test_std": float(test_values.std()),
            "oof_spearman_vs_v61": float(spearmanr(values, v61).statistic),
            "seed42_40fold_auc": {
                "mean": float(fold_auc.mean()),
                "variance": float(fold_auc.var(ddof=1)),
                "std": float(fold_auc.std(ddof=1)),
                "min": float(fold_auc.min()),
                "max": float(fold_auc.max()),
                "positive_delta_vs_v61_buckets": int((delta > 0).sum()),
                "mean_delta_vs_v61_buckets": float(delta.mean()),
                "rows": fold_auc.tolist(),
            },
            "five_split_single_feature_crossfit": single_feature_crossfit(y, values),
        }

    smart_source = SMART_DIR / "sources.json"
    smart_metadata = json.loads(smart_source.read_text(encoding="utf-8"))
    results = {
        "competition": "playground-series-s6e9",
        "experiment": "P2-05 public OOF honesty audit",
        "executed_at": "2026-09-03T20:30:38+08:00",
        "collation_kernel": "ravi20076/playgrounds6e9-public-datacollation-v1",
        "collation_notebook_sha256": "0bb48d0f624d84daca85a32036f6cbdf7caea86f534dc308d5efdbc1fd9db613",
        "input_hashes": {
            "OOF_Preds.parquet": sha256(public_oof_path),
            "Mdl_Preds.parquet": sha256(public_test_path),
            "v61_oof_proba.npy": sha256(V61_DIR / "oof_proba.npy"),
            "smart_sources.json": sha256(smart_source),
        },
        "v61_reference": {
            "oof_auc": float(roc_auc_score(y, v61)),
            "actual_training_split_seed": 104395303,
            "audit_bucket_split": "StratifiedKFold(40, shuffle=True, random_state=42)",
            "boundary": (
                "v61 实际训练划分不是 seed 42；这里仅在共同 seed42 行桶上比较既有 OOF，"
                "不能表述为同训练折配对实验。"
            ),
        },
        "members": members,
        "smart": {
            "decision": "exclude_from_oof_ensembles",
            "reason": "只有 Public 成绩与 test submission，没有 matching OOF artifact。",
            "source_validation_status": smart_metadata.get("validation_status"),
            "affects_v52_or_v72_predictions": False,
        },
        "decision": {
            "retain_public_oof": ["V1", "V2", "V3", "V4"],
            "exclude_public_oof": ["Smart"],
            "excluded_members_affecting_v72": [],
            "v72_recompute_required_now": False,
            "reason": (
                "V1-V4 的当前 Kaggle 源码均满足外层 OOF 标签边界，且聚合文件与当前内核"
                "下载产物逐元素一致（CSV 浮点往返误差不超过 1.36e-20）；Smart 从未进入 v52/v72。"
            ),
        },
        "pending": {
            "p2_01_c40": "等待 UTC 日配额重置后提交 v61；当前不能完成 OOF-LB 偏差比较。"
        },
    }
    (OUT_DIR / "audit_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(results["decision"], ensure_ascii=False, indent=2), flush=True)
    for name, row in members.items():
        bucket = row["seed42_40fold_auc"]
        print(
            f"{name}: OOF={row['oof_auc']:.9f} 40fold_std={bucket['std']:.9f} "
            f"delta_vs_v61={bucket['mean_delta_vs_v61_buckets']:+.9f}",
            flush=True,
        )
    print("P2-05 statistical/source audit complete; c40 comparison pending quota.", flush=True)


if __name__ == "__main__":
    main()
