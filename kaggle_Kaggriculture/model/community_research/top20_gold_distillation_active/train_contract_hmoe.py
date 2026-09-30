#!/usr/bin/env python3
"""训练 Top20 三层合同 HMoE，并导出无 sklearn 依赖的规则树。"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import balanced_accuracy_score, mean_squared_error, silhouette_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import RobustScaler
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor


HERE = Path(__file__).resolve().parent
DATA = HERE / "dataset"
MODEL = HERE / "contract_hmoe_model.json"
REPORT = HERE / "training_report.json"
FORBIDDEN = {"episode_id", "replay_sha256", "teacher", "submission_id", "seat", "seed", "future_shop", "future_action"}
CORE_TARGETS = (
    "market_HIRE", "market_BUY_LAND", "market_BUY_SEED", "market_BUY_ANIMAL", "market_BUY_PRODUCT", "market_SELL",
    "unit_PLANT", "unit_WATER", "unit_FERTILIZE", "unit_DIG", "unit_HARVEST", "unit_BUILD_PASTURE",
    "unit_BUILD_COOP", "unit_PLACE", "unit_FEED", "unit_CARE", "unit_COLLECT_FERTILIZER", "unit_PICKUP", "unit_DROP",
    "moves", "productive", "mean_task_distance", "productive_per_move", "center_task_share",
    "center_livestock_share", "top_two_row_plant_share",
)
PROTOTYPE_TARGETS = CORE_TARGETS + tuple(
    [f"market_BUY_SEED_{item}" for item in ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")]
    + [f"plant_{item}" for item in ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")]
    + [f"market_BUY_ANIMAL_{item}" for item in ("GOOSE", "COW", "SHEEP")]
    + [f"market_BUY_PRODUCT_{item}" for item in ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")]
    + [f"sell_{item}" for item in ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")]
)


def read_jsonl(name: str) -> list[dict]:
    return [json.loads(line) for line in (DATA / name).read_text(encoding="utf-8").splitlines() if line]


def feature_names(rows: list[dict]) -> list[str]:
    names = sorted({key for row in rows for key in row["features"]})
    bad = FORBIDDEN.intersection(names)
    if bad:
        raise ValueError(f"非法运行时特征: {sorted(bad)}")
    return names


def x_matrix(rows: list[dict], names: list[str], parent: np.ndarray | None = None, clusters: int = 0) -> np.ndarray:
    x = np.asarray([[float(row["features"].get(name, 0.0)) for name in names] for row in rows], dtype=np.float64)
    if parent is not None:
        onehot = np.zeros((len(rows), clusters), dtype=np.float64)
        onehot[np.arange(len(rows)), parent.astype(int)] = 1.0
        x = np.column_stack((x, onehot))
    return x


def y_matrix(rows: list[dict], names: tuple[str, ...] | list[str]) -> np.ndarray:
    values = np.asarray([[float(row["target"].get(name, 0.0)) for name in names] for row in rows], dtype=np.float64)
    # 次数目标按 log 压缩；比例/距离维持原尺度，避免动作频次淹没布局合同。
    for index, name in enumerate(names):
        if name not in {"mean_task_distance", "productive_per_move", "center_task_share", "center_livestock_share", "top_two_row_plant_share"}:
            values[:, index] = np.sign(values[:, index]) * np.log1p(np.abs(values[:, index]))
    return values


def teacher_weights(rows: list[dict]) -> np.ndarray:
    counts = Counter(str(row["teacher"]) for row in rows)
    weights = []
    for row in rows:
        rank = max(1, int(row.get("leaderboard_rank", 20) or 20))
        rank_weight = 1.0 + (21 - min(rank, 20)) / 20.0
        weights.append(rank_weight / counts[str(row["teacher"])])
    result = np.asarray(weights, dtype=np.float64)
    return result / result.mean()


def fit_clusters(rows: list[dict], targets: tuple[str, ...], candidates: tuple[int, ...], seed: int) -> tuple[RobustScaler, KMeans, dict]:
    train = [row for row in rows if row["split"] == "train"]
    raw = y_matrix(train, targets)
    scaler = RobustScaler(quantile_range=(10, 90)).fit(raw)
    y = np.clip(scaler.transform(raw), -8.0, 8.0)
    trials = []
    sample = y if len(y) <= 2500 else y[np.random.default_rng(seed).choice(len(y), 2500, replace=False)]
    for clusters in candidates:
        km = KMeans(n_clusters=clusters, random_state=seed, n_init=20).fit(y, sample_weight=teacher_weights(train))
        labels = km.predict(sample)
        support = Counter(km.labels_)
        score = float(silhouette_score(sample, labels)) if len(set(labels)) > 1 else -1.0
        trials.append({"clusters": clusters, "silhouette": score, "minimum_support": min(support.values())})
    eligible = [trial for trial in trials if trial["minimum_support"] >= max(12, len(train) // 200)]
    chosen = max(eligible or trials, key=lambda item: (item["silhouette"], item["minimum_support"], -item["clusters"]))
    model = KMeans(n_clusters=int(chosen["clusters"]), random_state=seed, n_init=40).fit(y, sample_weight=teacher_weights(train))
    return scaler, model, {"selected": chosen, "candidates": trials}


def transformed_targets(rows: list[dict], targets: tuple[str, ...], scaler: RobustScaler) -> np.ndarray:
    return np.clip(scaler.transform(y_matrix(rows, targets)), -8.0, 8.0)


def labels_for(rows: list[dict], targets: tuple[str, ...], scaler: RobustScaler, kmeans: KMeans) -> np.ndarray:
    return kmeans.predict(transformed_targets(rows, targets, scaler)).astype(int)


def contract_loss(y: np.ndarray, prediction: np.ndarray, centers: np.ndarray) -> float:
    return float(np.mean(np.sum((y - centers[prediction]) ** 2, axis=1)))


def choose_tree(train_rows: list[dict], dev_rows: list[dict], x_train: np.ndarray, x_dev: np.ndarray,
                y_train: np.ndarray, y_dev: np.ndarray, transformed_dev: np.ndarray, centers: np.ndarray, seed: int) -> tuple[DecisionTreeClassifier, dict]:
    baseline = np.full(len(dev_rows), Counter(y_train).most_common(1)[0][0], dtype=int)
    baseline_loss = contract_loss(transformed_dev, baseline, centers)
    trials = []
    weights = teacher_weights(train_rows)
    for depth in (5, 7, 9, 11):
        for leaf in (8, 16, 32, 48):
            tree = DecisionTreeClassifier(max_depth=depth, min_samples_leaf=leaf, random_state=seed, class_weight="balanced")
            tree.fit(x_train, y_train, sample_weight=weights)
            pred = tree.predict(x_dev).astype(int)
            loss = contract_loss(transformed_dev, pred, centers)
            trials.append({
                "depth": depth, "leaf": leaf, "dev_contract_loss": loss,
                "improvement_vs_mode": 1.0 - loss / max(1e-9, baseline_loss),
                "dev_accuracy": float(np.mean(pred == y_dev)),
                "dev_balanced_accuracy": float(balanced_accuracy_score(y_dev, pred)),
            })
    best = min(trials, key=lambda item: (item["dev_contract_loss"], item["depth"], -item["leaf"]))
    model = DecisionTreeClassifier(max_depth=best["depth"], min_samples_leaf=best["leaf"], random_state=seed, class_weight="balanced")
    model.fit(x_train, y_train, sample_weight=weights)
    return model, {"selected": best, "mode_contract_loss": baseline_loss, "candidates": trials}


def oof_macro_prediction(rows: list[dict], x: np.ndarray, y: np.ndarray, depth: int, leaf: int, seed: int) -> np.ndarray:
    groups = np.asarray([int(row["episode_id"]) for row in rows])
    pred = np.empty(len(rows), dtype=int)
    for fold, (fit, valid) in enumerate(GroupKFold(n_splits=5).split(x, y, groups)):
        tree = DecisionTreeClassifier(max_depth=depth, min_samples_leaf=leaf, random_state=seed + fold, class_weight="balanced")
        tree.fit(x[fit], y[fit], sample_weight=teacher_weights([rows[i] for i in fit]))
        pred[valid] = tree.predict(x[valid]).astype(int)
    return pred


def macro_parent_map(rows: list[dict], labels: np.ndarray) -> dict[tuple[int, str, int, int], int]:
    return {(int(row["episode_id"]), str(row["teacher"]), int(row["seat"]), int(row["decision_day"])): int(label) for row, label in zip(rows, labels)}


def daily_parents(rows: list[dict], mapping: dict[tuple[int, str, int, int], int]) -> np.ndarray:
    return np.asarray([mapping[(int(row["episode_id"]), str(row["teacher"]), int(row["seat"]), int(row["cycle_day"]))] for row in rows], dtype=int)


def export_classifier(model: DecisionTreeClassifier, names: list[str]) -> dict:
    tree, classes = model.tree_, [int(v) for v in model.classes_]
    def node(index: int) -> dict:
        if tree.children_left[index] == tree.children_right[index]:
            counts = np.asarray(tree.value[index][0], dtype=float)
            probs = counts / max(1e-12, counts.sum())
            return {"leaf": classes[int(np.argmax(counts))], "probabilities": {str(classes[i]): float(v) for i, v in enumerate(probs)}}
        return {"feature": names[int(tree.feature[index])], "threshold": float(tree.threshold[index]),
                "left": node(int(tree.children_left[index])), "right": node(int(tree.children_right[index]))}
    return {"kind": "classification_tree", "classes": classes, "depth": int(tree.max_depth), "nodes": int(tree.node_count), "root": node(0)}


def export_regressor(model: DecisionTreeRegressor, names: list[str], targets: list[str]) -> dict:
    tree = model.tree_
    def node(index: int) -> dict:
        if tree.children_left[index] == tree.children_right[index]:
            values = np.asarray(tree.value[index]).reshape(-1)
            return {"value": {target: float(values[i]) for i, target in enumerate(targets)}}
        return {"feature": names[int(tree.feature[index])], "threshold": float(tree.threshold[index]),
                "left": node(int(tree.children_left[index])), "right": node(int(tree.children_right[index]))}
    return {"kind": "regression_tree", "targets": targets, "depth": int(tree.max_depth), "nodes": int(tree.node_count), "root": node(0)}


def raw_prototypes(rows: list[dict], labels: np.ndarray, count: int, targets: tuple[str, ...]) -> dict[str, dict[str, float]]:
    grouped: dict[int, list[dict]] = defaultdict(list)
    for row, label in zip(rows, labels):
        if row["split"] == "train":
            grouped[int(label)].append(row["target"])
    return {str(cluster): {target: float(np.median([r.get(target, 0.0) for r in grouped[cluster]])) for target in targets}
            for cluster in range(count)}


def choose_regressor(x_train: np.ndarray, y_train: np.ndarray, x_dev: np.ndarray, y_dev: np.ndarray,
                     weights: np.ndarray, seed: int) -> tuple[DecisionTreeRegressor, dict]:
    baseline = np.repeat(np.average(y_train, axis=0, weights=weights)[None, :], len(y_dev), axis=0)
    baseline_rmse = float(mean_squared_error(y_dev, baseline) ** 0.5)
    trials = []
    for depth in (4, 6, 8, 10):
        for leaf in (12, 24, 48):
            model = DecisionTreeRegressor(max_depth=depth, min_samples_leaf=leaf, random_state=seed)
            model.fit(x_train, y_train, sample_weight=weights)
            rmse = float(mean_squared_error(y_dev, model.predict(x_dev)) ** 0.5)
            trials.append({"depth": depth, "leaf": leaf, "dev_rmse": rmse, "improvement_vs_mean": 1.0 - rmse / max(1e-9, baseline_rmse)})
    best = min(trials, key=lambda item: (item["dev_rmse"], item["depth"], -item["leaf"]))
    model = DecisionTreeRegressor(max_depth=best["depth"], min_samples_leaf=best["leaf"], random_state=seed).fit(x_train, y_train, sample_weight=weights)
    return model, {"selected": best, "mean_baseline_rmse": baseline_rmse, "candidates": trials}


def main() -> int:
    macro, daily, global_rows = read_jsonl("macro_3day.jsonl"), read_jsonl("daily_contract.jsonl"), read_jsonl("global_market.jsonl")
    macro_train = [r for r in macro if r["split"] == "train"]
    macro_dev = [r for r in macro if r["split"] == "dev"]
    macro_names = feature_names(macro)
    macro_scaler, macro_km, macro_cluster_report = fit_clusters(macro, CORE_TARGETS, (6, 8, 10, 12), 122)
    macro_train_labels = labels_for(macro_train, CORE_TARGETS, macro_scaler, macro_km)
    macro_dev_labels = labels_for(macro_dev, CORE_TARGETS, macro_scaler, macro_km)
    x_macro_train, x_macro_dev = x_matrix(macro_train, macro_names), x_matrix(macro_dev, macro_names)
    macro_model, macro_tree_report = choose_tree(
        macro_train, macro_dev, x_macro_train, x_macro_dev, macro_train_labels, macro_dev_labels,
        transformed_targets(macro_dev, CORE_TARGETS, macro_scaler), macro_km.cluster_centers_, 122,
    )
    macro_oof = oof_macro_prediction(macro_train, x_macro_train, macro_train_labels,
                                     macro_tree_report["selected"]["depth"], macro_tree_report["selected"]["leaf"], 122)
    macro_train_map = macro_parent_map(macro_train, macro_oof)
    macro_dev_map = macro_parent_map(macro_dev, macro_model.predict(x_macro_dev).astype(int))

    daily_train, daily_dev = [r for r in daily if r["split"] == "train"], [r for r in daily if r["split"] == "dev"]
    daily_names = feature_names(daily)
    daily_scaler, daily_km, daily_cluster_report = fit_clusters(daily, CORE_TARGETS, (8, 12, 16, 20), 223)
    daily_train_labels = labels_for(daily_train, CORE_TARGETS, daily_scaler, daily_km)
    daily_dev_labels = labels_for(daily_dev, CORE_TARGETS, daily_scaler, daily_km)
    parent_train, parent_dev = daily_parents(daily_train, macro_train_map), daily_parents(daily_dev, macro_dev_map)
    macro_count = int(macro_km.n_clusters)
    x_daily_train = x_matrix(daily_train, daily_names, parent_train, macro_count)
    x_daily_dev = x_matrix(daily_dev, daily_names, parent_dev, macro_count)
    daily_full_names = daily_names + [f"macro_contract_{i}" for i in range(macro_count)]
    daily_model, daily_tree_report = choose_tree(
        daily_train, daily_dev, x_daily_train, x_daily_dev, daily_train_labels, daily_dev_labels,
        transformed_targets(daily_dev, CORE_TARGETS, daily_scaler), daily_km.cluster_centers_, 223,
    )

    # 全局 critic：比较给定状态执行某个三日合同后的资金差变化。
    critic_names = macro_names + [f"macro_contract_{i}" for i in range(macro_count)]
    critic_train_parent = macro_train_labels
    critic_dev_parent = macro_model.predict(x_macro_dev).astype(int)
    x_critic_train = x_matrix(macro_train, macro_names, critic_train_parent, macro_count)
    x_critic_dev = x_matrix(macro_dev, macro_names, critic_dev_parent, macro_count)
    y_critic_train = np.asarray([[float(r["target"].get("money_gap_delta", 0.0))] for r in macro_train])
    y_critic_dev = np.asarray([[float(r["target"].get("money_gap_delta", 0.0))] for r in macro_dev])
    critic_model, critic_report = choose_regressor(x_critic_train, y_critic_train, x_critic_dev, y_critic_dev, teacher_weights(macro_train), 324)

    # 日级全局专家预测卖出/对手/资金变化，由当前状态与暴露后的宏观合同共同决定。
    global_train, global_dev = [r for r in global_rows if r["split"] == "train"], [r for r in global_rows if r["split"] == "dev"]
    global_targets = sorted({key for row in global_rows for key in row["target"]})
    x_global_train = x_matrix(global_train, daily_names, parent_train, macro_count)
    x_global_dev = x_matrix(global_dev, daily_names, parent_dev, macro_count)
    y_global_train = y_matrix(global_train, global_targets)
    y_global_dev = y_matrix(global_dev, global_targets)
    global_model, global_report = choose_regressor(x_global_train, y_global_train, x_global_dev, y_global_dev, teacher_weights(global_train), 425)

    all_macro_labels = labels_for(macro, CORE_TARGETS, macro_scaler, macro_km)
    all_daily_labels = labels_for(daily, CORE_TARGETS, daily_scaler, daily_km)
    model = {
        "schema": "kaggriculture-v122-top20-contract-hmoe-v1", "status": "RESEARCH_ONLY_PENDING_CLOSED_LOOP",
        "runtime_contract": {"tape": False, "step_action_lookup": False, "future_action_features": False,
                             "primary_action_source": "independent_state_recovery_executor", "forbidden_fields": sorted(FORBIDDEN)},
        "teachers": {"scope": "current leaderboard Top20", "training_auxiliary_not_promotion_evidence": True,
                     "count": len({r["teacher"] for r in macro})},
        "macro_router": export_classifier(macro_model, macro_names),
        "daily_router": export_classifier(daily_model, daily_full_names),
        "global_value_critic": export_regressor(critic_model, critic_names, ["money_gap_delta"]),
        "global_daily_expert": export_regressor(global_model, daily_full_names, global_targets),
        "macro_contract_prototypes": raw_prototypes(macro, all_macro_labels, macro_count, PROTOTYPE_TARGETS),
        "daily_contract_prototypes": raw_prototypes(daily, all_daily_labels, int(daily_km.n_clusters), PROTOTYPE_TARGETS),
        "router_contract": {"macro_refresh_days": 3, "daily_refresh_days": 1, "critic_objective": "predicted_3day_money_gap_delta",
                            "daily_parent_signal": "OOF_macro_on_train_and_predicted_macro_on_dev"},
    }
    MODEL.write_text(json.dumps(model, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = {
        "schema": "kaggriculture-v122-top20-contract-training-report-v1",
        "data": {"episodes": len({r["episode_id"] for r in macro}), "teacher_trajectories": len(macro) // 10,
                 "teachers_train": len({r["teacher"] for r in macro_train}), "teachers_dev": len({r["teacher"] for r in macro_dev}),
                 "split": "episode_id isolated train/dev"},
        "macro_clusters": macro_cluster_report, "macro_router": macro_tree_report,
        "daily_clusters": daily_cluster_report, "daily_router": daily_tree_report,
        "global_value_critic": critic_report, "global_daily_expert": global_report,
        "expert_usage": {"macro_train": dict(Counter(map(int, macro_train_labels))), "macro_dev": dict(Counter(map(int, macro_dev_labels))),
                         "daily_train": dict(Counter(map(int, daily_train_labels))), "daily_dev": dict(Counter(map(int, daily_dev_labels)))},
        "offline_gate": {"uses_at_least_3_macro_experts": len(set(macro_model.predict(x_macro_dev))) >= 3,
                         "uses_at_least_3_daily_experts": len(set(daily_model.predict(x_daily_dev))) >= 3,
                         "critic_beats_mean": critic_report["selected"]["improvement_vs_mean"] > 0,
                         "closed_loop_required": True},
        "verdict": "OFFLINE_RESEARCH_SIGNAL_ONLY_NOT_PROMOTABLE",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
