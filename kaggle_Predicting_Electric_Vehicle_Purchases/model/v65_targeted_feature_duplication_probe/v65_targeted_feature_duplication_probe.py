# -*- coding: utf-8 -*-
"""v65：检验 v62 增益是否来自强变量在随机列采样中的定向复制。"""

from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold


SEED = 15_485_863
OUT_DIR = Path(__file__).resolve().parent
SOURCE = OUT_DIR.parent / "v29_income_bin10_te_lgbm" / "v29_income_bin10_te_lgbm.py"
BASELINE_RESULTS = OUT_DIR.parent / "v53_income_bin2_range_probe" / "probe_results.json"
ORIGINAL_DATA = (
    OUT_DIR.parents[1]
    / "data"
    / "original_dataset"
    / "EV_Adoption_and_Range_Anxiety_Dataset.csv"
)


def load_base():
    spec = importlib.util.spec_from_file_location("v29_income_bin10_te_lgbm", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 v29：{SOURCE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.base


def duplicated_block(
    name: str,
    x_train: pd.DataFrame,
    x_test: pd.DataFrame,
    original_top3_train: pd.DataFrame,
    original_top3_test: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if name.startswith("raw_top2_x"):
        copies = int(name.rsplit("x", 1)[1])
        source_train = x_train[["Subsidy_Available", "Environmental_Concern_Level"]]
        source_test = x_test[["Subsidy_Available", "Environmental_Concern_Level"]]
    elif name.startswith("original_top3_x"):
        copies = int(name.rsplit("x", 1)[1])
        source_train = original_top3_train
        source_test = original_top3_test
    else:
        raise ValueError(name)

    train_parts: list[pd.DataFrame] = []
    test_parts: list[pd.DataFrame] = []
    for copy in range(1, copies + 1):
        train_part = source_train.copy()
        test_part = source_test.copy()
        train_part.columns = [f"{name}_copy{copy}_{col}" for col in source_train]
        test_part.columns = train_part.columns
        train_parts.append(train_part)
        test_parts.append(test_part)
    return pd.concat(train_parts, axis=1), pd.concat(test_parts, axis=1)


def main() -> None:
    start = time.time()
    base = load_base()
    original_factorize = base.factorize_joint

    def factorize_joint(train, test, cols):
        if cols != ["_income_bin10"]:
            return original_factorize(train, test, cols)
        values = pd.concat(
            [train["Annual_Income_USD"], test["Annual_Income_USD"]], ignore_index=True
        )
        codes, _ = pd.factorize((values // 10).astype(np.int64), sort=True)
        return codes[: len(train)].astype(np.int32), codes[len(train) :].astype(np.int32)

    base.factorize_joint = factorize_joint
    base.TE_KEYS["income_bin10"] = ["_income_bin10"]
    train, test, _ = base.load_data()
    y = (train[base.TARGET] == base.POS_LABEL).to_numpy(np.int8)
    x_train, x_test, keys_train, keys_test = base.build_static_features(train, test)

    original = pd.read_csv(ORIGINAL_DATA)
    original_y = (original[base.TARGET] == base.POS_LABEL).astype(np.float64)
    original_rate = float(original_y.mean())
    top3 = [
        "Subsidy_Available",
        "Environmental_Concern_Level",
        "Range_Anxiety_Level",
    ]
    original_top3_train = pd.DataFrame(index=train.index)
    original_top3_test = pd.DataFrame(index=test.index)
    for col in top3:
        mapping = (
            pd.DataFrame({col: original[col], "_target": original_y})
            .groupby(col, dropna=False)["_target"]
            .mean()
        )
        feature = f"original_target_mean_{col}"
        original_top3_train[feature] = (
            train[col].map(mapping).fillna(original_rate).astype(np.float32)
        )
        original_top3_test[feature] = (
            test[col].map(mapping).fillna(original_rate).astype(np.float32)
        )

    config_names = [
        "raw_top2_x1",
        "raw_top2_x3",
        "raw_top2_x7",
        "original_top3_x1",
        "original_top3_x3",
    ]
    config_blocks = {
        name: duplicated_block(
            name, x_train, x_test, original_top3_train, original_top3_test
        )
        for name in config_names
    }
    te_names = [
        f"te_{key}_m{smooth:g}" for key in base.TE_KEYS for smooth in base.SMOOTHS
    ]
    baseline_json = json.loads(BASELINE_RESULTS.read_text(encoding="utf-8"))
    baseline_auc = {
        int(row["fold"]): float(row["auc"])
        for row in baseline_json["rows"]
        if row["config"] == "baseline"
    }
    params = dict(base.LGB_PARAMS)
    params.update(
        {
            "max_depth": 4,
            "num_leaves": 15,
            "random_state": SEED,
            "bagging_seed": SEED,
            "feature_fraction_seed": SEED,
            "data_random_seed": SEED,
        }
    )
    folds = list(StratifiedKFold(5, shuffle=True, random_state=SEED).split(train, y))
    rows: list[dict] = []

    for fold, (fit_idx, valid_idx) in enumerate(folds, 1):
        inner = list(
            StratifiedKFold(base.N_INNER, shuffle=True, random_state=SEED + fold).split(
                np.zeros(len(fit_idx)), y[fit_idx]
            )
        )
        fit_te: list[np.ndarray] = []
        valid_te: list[np.ndarray] = []
        for key in base.TE_KEYS:
            fit_block, valid_block, _ = base.encode_key(
                keys_train[key], keys_test[key], y, fit_idx, valid_idx, inner
            )
            fit_te.append(fit_block)
            valid_te.append(valid_block)
        base_fit = np.column_stack(
            [x_train.iloc[fit_idx].to_numpy(np.float32), *fit_te]
        )
        base_valid = np.column_stack(
            [x_train.iloc[valid_idx].to_numpy(np.float32), *valid_te]
        )

        for name in config_names:
            train_block, _ = config_blocks[name]
            feature_names = list(x_train.columns) + te_names + list(train_block.columns)
            x_fit = np.column_stack(
                [base_fit, train_block.iloc[fit_idx].to_numpy(np.float32)]
            )
            x_valid = np.column_stack(
                [base_valid, train_block.iloc[valid_idx].to_numpy(np.float32)]
            )
            model = lgb.LGBMClassifier(**params)
            model.fit(
                x_fit,
                y[fit_idx],
                eval_set=[(x_valid, y[valid_idx])],
                eval_metric="auc",
                feature_name=feature_names,
                callbacks=[
                    lgb.early_stopping(base.EARLY_STOPPING_ROUNDS, verbose=False),
                    lgb.log_evaluation(period=0),
                ],
            )
            iteration = int(model.best_iteration_ or params["n_estimators"])
            pred = model.predict_proba(x_valid, num_iteration=iteration)[:, 1]
            auc = float(roc_auc_score(y[valid_idx], pred))
            delta = auc - baseline_auc[fold]
            rows.append(
                {
                    "fold": fold,
                    "config": name,
                    "baseline_auc": baseline_auc[fold],
                    "auc": auc,
                    "delta": delta,
                    "best_iteration": iteration,
                }
            )
            print(
                f"fold={fold} config={name} auc={auc:.9f} delta={delta:+.9f} "
                f"iter={iteration} elapsed={time.time() - start:.1f}s",
                flush=True,
            )

    summary = {}
    for name in config_names:
        selected = [row for row in rows if row["config"] == name]
        deltas = [row["delta"] for row in selected]
        summary[name] = {
            "mean_auc": float(np.mean([row["auc"] for row in selected])),
            "mean_delta": float(np.mean(deltas)),
            "folds_won": int(sum(delta > 0 for delta in deltas)),
            "fold_deltas": deltas,
            "mean_best_iteration": float(
                np.mean([row["best_iteration"] for row in selected])
            ),
        }
    result = {
        "competition": "playground-series-s6e9",
        "model": "matched-fold targeted strong-feature duplication probe",
        "seed": SEED,
        "rows": rows,
        "summary": summary,
        "hypothesis": (
            "v62 gains are mainly caused by duplicating subsidy and environmental "
            "concern so they are selected more often under low feature_fraction"
        ),
        "elapsed_seconds": time.time() - start,
    }
    (OUT_DIR / "probe_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
