"""只读复算既有 V100 OOF 的 AUC 和错序来源，不训练或调整模型。"""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

PROJECT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).with_name("error_accounting.json")
PREDICTION = PROJECT / "model/v100_v90_ctboost_nested_cv_blend/oof_proba.npy"
EXPECTED_SHA = "8ad4a6a026eb579036911aa7010a39cbfa7ceefb4976b39d95bc60a87cb41fda"

def main():
    digest = hashlib.sha256(PREDICTION.read_bytes()).hexdigest()
    if digest != EXPECTED_SHA:
        raise ValueError("冻结 OOF 文件哈希不符")
    frame = pd.read_csv(PROJECT / "data/train.csv")
    target = frame.Will_Buy_EV.eq("Yes").to_numpy()
    prediction = np.load(PREDICTION, allow_pickle=False)
    assert len(frame) == len(prediction) == 668665
    assert np.array_equal(frame.id.to_numpy(), np.arange(len(frame)))
    assert np.isfinite(prediction).all()
    assert ((prediction >= 0) & (prediction <= 1)).all()
    positive = np.sort(prediction[target])
    negative = np.sort(prediction[~target])
    errors = np.empty(len(frame), dtype=np.float64)
    # 每个正例被负例超过的比例；每个负例超过正例的比例；并列各计半。
    errors[target] = 1 - (
        np.searchsorted(negative, prediction[target], side="left")
        + np.searchsorted(negative, prediction[target], side="right")
    ) / (2 * len(negative))
    errors[~target] = (
        np.searchsorted(positive, prediction[~target], side="left")
        + np.searchsorted(positive, prediction[~target], side="right")
    ) / (2 * len(positive))
    auc = float(1 - errors[target].mean())
    recorded = json.loads(PREDICTION.with_name("cv_results.json").read_text())["oof_auc"]
    assert abs(auc - recorded) < 1e-12
    assert abs(errors[target].mean() - errors[~target].mean()) < 1e-12
    result = {
        "scope": "既有开发 OOF 的只读误差审计；不代表独立确认或新增模型",
        "n_rows": len(frame),
        "n_positive": int(target.sum()),
        "n_negative": int((~target).sum()),
        "auc_recomputed": auc,
        "auc_recorded": recorded,
        "oof_sha256": digest,
        "slices": {},
    }
    counts = frame.Annual_Income_USD.map(frame.Annual_Income_USD.value_counts())
    frame["income_frequency_bucket"] = pd.cut(
        counts, [0, 5, 20, 100, np.inf], labels=["1-5", "6-20", "21-100", "101+"]
    )
    subgroup = (
        frame.Environmental_Concern_Level.ge(4)
        & frame.Subsidy_Available.eq("Yes")
        & frame.Range_Anxiety_Level.eq("Low")
    ).to_numpy()
    frame["main_signal_group"] = np.where(subgroup, "env4or5_subsidyYes_anxietyLow", "other")
    for column in [
        "Environmental_Concern_Level", "Subsidy_Available", "Range_Anxiety_Level",
        "income_frequency_bucket", "main_signal_group"
    ]:
        rows = []
        for key, indices in frame.groupby(column, observed=True).groups.items():
            indices = np.asarray(indices)
            pos_indices = indices[target[indices]]
            neg_indices = indices[~target[indices]]
            rows.append({
                "group": str(key),
                "n_rows": int(len(indices)),
                "row_pct": 100 * len(indices) / len(frame),
                "n_positive": int(len(pos_indices)),
                "n_negative": int(len(neg_indices)),
                "positive_error_share_pct": float(100 * errors[pos_indices].sum() / errors[target].sum()),
                "negative_error_share_pct": float(100 * errors[neg_indices].sum() / errors[~target].sum()),
            })
        result["slices"][column] = rows
    pos_sub = np.sort(prediction[subgroup & target])
    neg_sub = np.sort(prediction[subgroup & ~target])
    wrong = len(neg_sub) - (
        np.searchsorted(neg_sub, pos_sub, side="left")
        + np.searchsorted(neg_sub, pos_sub, side="right")
    ) / 2
    total_pairs = len(positive) * len(negative)
    pair_mass = len(pos_sub) * len(neg_sub) / total_pairs
    result["main_signal_within"] = {
        "pair_mass": pair_mass,
        "auc": float(1 - wrong.mean() / len(neg_sub)),
        "error_share_pct": float(100 * wrong.sum() / (total_pairs * (1 - auc))),
        "conditional_auc_gain_for_global_0_0001_if_cross_pairs_unchanged": 0.0001 / pair_mass,
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "output": str(OUTPUT),
        "auc": auc,
        "subgroup_auc": result["main_signal_within"]["auc"],
        "subgroup_error_share_pct": result["main_signal_within"]["error_share_pct"],
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()

