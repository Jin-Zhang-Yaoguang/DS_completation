#!/usr/bin/env python3
"""训练 V121 闭环动作层：专家条件 actor 树 + 专家条件市场树。"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import accuracy_score, balanced_accuracy_score, mean_squared_error
from sklearn.model_selection import GroupKFold
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

from behavior_features import actor_features, global_features, market_names, market_vector, normalize_unit, positions


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "v120_hierarchical_top5_distillation"
RECEIPT = SOURCE / "replay_data/download_receipt.json"
MODEL_OUT = HERE / "behavior_hmoe.joblib"
REPORT_OUT = HERE / "behavior_training_report.json"
EXPERTS = ("CAPACITY", "CROP", "LIVESTOCK", "LIQUIDATE")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def daily_expert_map() -> dict[tuple[int, str, int, int], str]:
    rows = read_jsonl(HERE / "dataset/daily_contract.jsonl")
    return {
        (int(row["episode_id"]), str(row["teacher"]), int(row["seat"]), int(row["decision_day"])): str(row["expert"])
        for row in rows
    }


def source_rows() -> list[dict]:
    return json.loads(RECEIPT.read_text(encoding="utf-8"))["rows"]


def total_actor_rows(sources: list[dict]) -> int:
    total = 0
    for source in sources:
        replay = json.loads(Path(source["path"]).read_text(encoding="utf-8"))
        for teacher in source["teachers"]:
            seat = int(teacher["seat"])
            for step in range(719):
                farm = replay["steps"][step][seat]["observation"]["farms"][seat]
                total += len(positions(farm))
    return total


def gentle_weights(labels: np.ndarray) -> np.ndarray:
    counts = Counter(str(value) for value in labels)
    n, k = len(labels), len(counts)
    return np.asarray([min(8.0, math.sqrt(n / max(1, k * counts[str(value)]))) for value in labels], dtype=np.float64)


def unit_oof(x: np.ndarray, y: np.ndarray, groups: np.ndarray) -> dict:
    prediction = np.empty(len(y), dtype=object)
    splits = min(3, len(set(int(value) for value in groups)))
    if splits < 2:
        return {"rows": len(y), "accuracy": None, "balanced_accuracy": None, "groups": splits}
    for train, valid in GroupKFold(n_splits=splits).split(x, y, groups):
        model = DecisionTreeClassifier(max_depth=22, min_samples_leaf=3, random_state=121)
        model.fit(x[train], y[train], sample_weight=gentle_weights(y[train]))
        prediction[valid] = model.predict(x[valid])
    return {
        "rows": int(len(y)),
        "classes": int(len(set(str(value) for value in y))),
        "accuracy": float(accuracy_score(y, prediction)),
        "balanced_accuracy": float(balanced_accuracy_score(y, prediction)),
        "groups": int(splits),
    }


def market_oof(x: np.ndarray, y: np.ndarray, groups: np.ndarray) -> dict:
    prediction = np.zeros_like(y)
    splits = min(3, len(set(int(value) for value in groups)))
    if splits < 2:
        return {"rows": len(y), "rmse": None, "nonzero_f1": None, "groups": splits}
    for train, valid in GroupKFold(n_splits=splits).split(x, y, groups):
        model = DecisionTreeRegressor(max_depth=16, min_samples_leaf=3, random_state=121)
        model.fit(x[train], y[train])
        prediction[valid] = np.maximum(0.0, model.predict(x[valid]))
    truth_on, pred_on = y > 0.5, prediction >= 0.5
    tp = int(np.logical_and(truth_on, pred_on).sum())
    fp = int(np.logical_and(~truth_on, pred_on).sum())
    fn = int(np.logical_and(truth_on, ~pred_on).sum())
    precision = tp / max(1, tp + fp)
    recall = tp / max(1, tp + fn)
    f1 = 2 * precision * recall / max(1e-12, precision + recall)
    return {
        "rows": int(len(y)), "targets": int(y.shape[1]),
        "rmse": float(mean_squared_error(y, prediction) ** 0.5),
        "nonzero_precision": precision, "nonzero_recall": recall, "nonzero_f1": f1,
        "groups": int(splits),
    }


def main() -> int:
    sources = source_rows()
    mapping = daily_expert_map()
    # 固定特征 schema；所有字段只来自当前 observation。
    first = json.loads(Path(sources[0]["path"]).read_text(encoding="utf-8"))
    first_teacher = sources[0]["teachers"][0]
    first_obs = first["steps"][0][int(first_teacher["seat"])]["observation"]
    # 逐 actor 路线只允许依赖己方生产状态；对手和即时市场字段会把教师路径
    # 绑定到原比赛，换对手后产生严重分布漂移。
    actor_names = sorted(
        name for name in actor_features(first_obs, 0)
        if not name.startswith(("rival_", "market_", "price_")) and name != "money_gap"
    )
    global_names = sorted(global_features(first_obs))
    teacher_market_names = [
        name for name in global_names
        if not name.startswith(("rival_", "market_", "price_")) and name != "money_gap"
    ]
    teacher_market_columns = [global_names.index(name) for name in teacher_market_names]
    market_targets = market_names()
    actor_total = total_actor_rows(sources)
    turn_total = 719 * sum(len(source["teachers"]) for source in sources)
    actor_x = np.empty((actor_total, len(actor_names)), dtype=np.float32)
    actor_y = np.empty(actor_total, dtype=object)
    actor_q = np.empty(actor_total, dtype=np.int16)
    actor_group = np.empty(actor_total, dtype=np.int64)
    actor_expert = np.empty(actor_total, dtype=object)
    actor_teacher = np.empty(actor_total, dtype=object)
    market_x = np.empty((turn_total, len(global_names)), dtype=np.float32)
    market_y = np.empty((turn_total, len(market_targets)), dtype=np.float32)
    market_group = np.empty(turn_total, dtype=np.int64)
    market_expert = np.empty(turn_total, dtype=object)
    market_teacher = np.empty(turn_total, dtype=object)
    market_basket = np.empty(turn_total, dtype=object)
    ai = mi = 0
    for source in sources:
        episode = int(source["episode_id"])
        replay = json.loads(Path(source["path"]).read_text(encoding="utf-8"))
        for teacher in source["teachers"]:
            seat, team = int(teacher["seat"]), str(teacher["team"])
            for step in range(719):
                obs = replay["steps"][step][seat]["observation"]
                action = replay["steps"][step + 1][seat].get("action") or {"farmer": ["PASS"], "hands": [], "market": []}
                expert = mapping[(episode, team, seat, step // 24)]
                farm = obs["farms"][seat]
                actor_count = len(positions(farm))
                units = [action.get("farmer", ["PASS"]), *list(action.get("hands") or [])]
                if len(units) < actor_count:
                    units.extend([["PASS"]] * (actor_count - len(units)))
                for actor in range(actor_count):
                    feature = actor_features(obs, actor)
                    label, quantity = normalize_unit(units[actor])
                    actor_x[ai] = [float(feature.get(name, 0.0)) for name in actor_names]
                    actor_y[ai], actor_q[ai] = label, quantity
                    actor_group[ai], actor_expert[ai], actor_teacher[ai] = episode, expert, team
                    ai += 1
                feature = global_features(obs)
                market_x[mi] = [float(feature.get(name, 0.0)) for name in global_names]
                market_y[mi] = market_vector(action, market_targets)
                market_group[mi], market_expert[mi], market_teacher[mi] = episode, expert, team
                market_basket[mi] = json.dumps(action.get("market", []) or [], separators=(",", ":"), ensure_ascii=True)
                mi += 1
    if ai != actor_total or mi != turn_total:
        raise AssertionError((ai, actor_total, mi, turn_total))

    unit_models = {}
    market_models = {}
    quantity_medians: dict[str, dict[str, int]] = {}
    report = {"schema": "kaggriculture-v121-behavior-hmoe-training-v1", "data": {"actor_rows": actor_total, "turn_rows": turn_total, "episodes": len({int(value) for value in actor_group}), "actor_features": len(actor_names), "market_features": len(global_names)}, "experts": {}}
    for expert in EXPERTS:
        actor_mask = actor_expert == expert
        market_mask = market_expert == expert
        ux, uy, ug = actor_x[actor_mask], actor_y[actor_mask], actor_group[actor_mask]
        mx, my, mg = market_x[market_mask], market_y[market_mask], market_group[market_mask]
        unit_report = unit_oof(ux, uy, ug)
        market_report = market_oof(mx, my, mg)
        unit_model = DecisionTreeClassifier(max_depth=22, min_samples_leaf=3, random_state=121)
        unit_model.fit(ux, uy, sample_weight=gentle_weights(uy))
        market_model = DecisionTreeRegressor(max_depth=16, min_samples_leaf=3, random_state=121)
        market_model.fit(mx, my)
        unit_models[expert] = unit_model
        market_models[expert] = market_model
        quantity_medians[expert] = {
            label: max(1, int(np.median(actor_q[actor_mask][uy == label])))
            for label in sorted(set(str(value) for value in uy))
        }
        report["experts"][expert] = {"unit": unit_report, "market": market_report, "unit_tree": {"depth": int(unit_model.tree_.max_depth), "nodes": int(unit_model.tree_.node_count)}, "market_tree": {"depth": int(market_model.tree_.max_depth), "nodes": int(market_model.tree_.node_count)}}
        print(json.dumps({"expert": expert, **report["experts"][expert]}, ensure_ascii=False), flush=True)
    teacher_unit_models = {}
    teacher_market_models = {}
    teacher_quantity_medians: dict[str, dict[str, int]] = {}
    report["teachers"] = {}
    for teacher in sorted(set(str(value) for value in actor_teacher)):
        actor_mask = actor_teacher == teacher
        market_mask = market_teacher == teacher
        ux, uy, ug = actor_x[actor_mask], actor_y[actor_mask], actor_group[actor_mask]
        mx = market_x[market_mask][:, teacher_market_columns]
        my, mg = market_basket[market_mask], market_group[market_mask]
        unit_report = unit_oof(ux, uy, ug)
        basket_report = unit_oof(mx, my, mg)
        unit_model = DecisionTreeClassifier(max_depth=26, min_samples_leaf=2, random_state=121)
        unit_model.fit(ux, uy, sample_weight=gentle_weights(uy))
        basket_model = DecisionTreeClassifier(max_depth=22, min_samples_leaf=2, random_state=121)
        basket_model.fit(mx, my, sample_weight=gentle_weights(my))
        teacher_unit_models[teacher] = unit_model
        teacher_market_models[teacher] = basket_model
        teacher_quantity_medians[teacher] = {
            label: max(1, int(np.median(actor_q[actor_mask][uy == label])))
            for label in sorted(set(str(value) for value in uy))
        }
        report["teachers"][teacher] = {
            "actor": unit_report, "basket": basket_report,
            "actor_tree": {"depth": int(unit_model.tree_.max_depth), "nodes": int(unit_model.tree_.node_count)},
            "basket_tree": {"depth": int(basket_model.tree_.max_depth), "nodes": int(basket_model.tree_.node_count)},
        }
        print(json.dumps({"teacher": teacher, **report["teachers"][teacher]}, ensure_ascii=False), flush=True)
    bundle = {
        "schema": "kaggriculture-v121-behavior-hmoe-bundle-v1",
        "status": "RESEARCH_ONLY",
        "runtime_contract": {"tape": False, "step_action_lookup": False, "teacher_identity": False, "primary_action_source": "state_conditioned_expert_trees"},
        "actor_features": actor_names,
        "global_features": global_names,
        "market_targets": market_targets,
        "unit_models": unit_models,
        "market_models": market_models,
        "quantity_medians": quantity_medians,
        "teacher_unit_models": teacher_unit_models,
        "teacher_market_models": teacher_market_models,
        "teacher_quantity_medians": teacher_quantity_medians,
        "teacher_market_features": teacher_market_names,
    }
    joblib.dump(bundle, MODEL_OUT, compress=3)
    report["verdict"] = "BEHAVIOR_TREES_TRAINED_CLOSED_LOOP_REQUIRED"
    REPORT_OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"model": str(MODEL_OUT), "bytes": MODEL_OUT.stat().st_size, "verdict": report["verdict"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
