#!/usr/bin/env python3
"""Distil Top20 market actions into causal event and quantity rule trees."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import precision_recall_fscore_support
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

from contract_features import PRODUCTS, CROPS, ANIMALS, state_features


HERE = Path(__file__).resolve().parent
DATA = HERE / "dataset/daily_contract.jsonl"
OUTPUT = HERE / "structured_market_hmoe.json"
REPORT = HERE / "structured_market_training_report.json"
TARGETS = (
    "HIRE", "BUY_LAND",
    *(f"BUY_SEED:{item}" for item in CROPS),
    *(f"BUY_ANIMAL:{item}" for item in ANIMALS),
    *(f"BUY_PRODUCT:{item}" for item in PRODUCTS),
    *(f"SELL:{item}" for item in PRODUCTS),
)


def _targets(action: dict) -> dict[str, int]:
    result: Counter = Counter()
    for raw in action.get("market") or []:
        order = list(raw or [])
        if not order:
            continue
        op = str(order[0])
        key = op if op in {"HIRE", "BUY_LAND"} else f"{op}:{order[1]}" if len(order) >= 2 else op
        quantity = 1 if op in {"HIRE", "BUY_LAND"} else max(0, int(order[2] or 0)) if len(order) >= 3 else 0
        if key in TARGETS:
            result[key] += quantity
    return dict(result)


def _positions(action: dict) -> dict[str, int]:
    result = {}
    for index, raw in enumerate(action.get("market") or []):
        order = list(raw or [])
        if not order: continue
        op = str(order[0]); key = op if op in {"HIRE", "BUY_LAND"} else f"{op}:{order[1]}" if len(order) >= 2 else op
        if key in TARGETS and key not in result: result[key] = index
    return result


def _export_classifier(model: DecisionTreeClassifier, names: list[str]) -> dict:
    tree = model.tree_
    positive = int(np.flatnonzero(model.classes_ == 1)[0]) if 1 in model.classes_ else -1
    def node(index: int) -> dict:
        counts = np.asarray(tree.value[index][0], dtype=float)
        probability = float(counts[positive] / max(1e-12, counts.sum())) if positive >= 0 else 0.0
        if tree.children_left[index] == tree.children_right[index]:
            return {"probability": probability}
        return {"feature": names[int(tree.feature[index])], "threshold": float(tree.threshold[index]),
                "probability": probability, "left": node(int(tree.children_left[index])),
                "right": node(int(tree.children_right[index]))}
    return {"depth": int(tree.max_depth), "nodes": int(tree.node_count), "root": node(0)}


def _export_regressor(model: DecisionTreeRegressor, names: list[str]) -> dict:
    tree = model.tree_
    def node(index: int) -> dict:
        value = float(tree.value[index][0][0])
        if tree.children_left[index] == tree.children_right[index]:
            return {"value": value}
        return {"feature": names[int(tree.feature[index])], "threshold": float(tree.threshold[index]),
                "value": value, "left": node(int(tree.children_left[index])),
                "right": node(int(tree.children_right[index]))}
    return {"depth": int(tree.max_depth), "nodes": int(tree.node_count), "root": node(0)}


def _threshold(y: np.ndarray, p: np.ndarray, min_precision: float = 0.55) -> tuple[float, dict]:
    best = (0.0, 0.5, 0.0, 0.0)
    for threshold in np.arange(0.20, 0.951, 0.025):
        pred = p >= threshold
        precision, recall, f1, _ = precision_recall_fscore_support(y, pred, average="binary", zero_division=0)
        # Precision-biased selection limits destructive off-distribution buys.
        score = f1 if precision >= min_precision else f1 * precision / min_precision
        if score > best[0]:
            best = (float(score), float(threshold), float(precision), float(recall))
    return best[1], {"precision": best[2], "recall": best[3], "selection_score": best[0]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--teacher", default="")
    parser.add_argument("--output", default=str(OUTPUT))
    parser.add_argument("--report", default=str(REPORT))
    args = parser.parse_args()
    trajectories = {}
    for line in DATA.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("source_panel") != "top20_cli_training_auxiliary":
            continue
        key = (int(row["episode_id"]), int(row["seat"]))
        trajectories[key] = {"teacher": str(row["teacher"]), "rank": int(row["leaderboard_rank"]), "split": str(row["split"])}
    grouped = defaultdict(lambda: defaultdict(list))
    for key, meta in trajectories.items():
        grouped[meta["teacher"]][meta["split"]].append((key, meta))
    selected = []
    chosen_teachers = [args.teacher] if args.teacher else sorted(grouped)
    for teacher in chosen_teachers:
        selected.extend(sorted(grouped[teacher]["train"])[:12 if args.teacher else 6])
        selected.extend(sorted(grouped[teacher]["dev"])[:4 if args.teacher else 2])
    paths = {int(path.name.split("-")[1]): path for path in (HERE / "replay_data").rglob("episode-*-replay.json")}
    records = []
    for number, (key, meta) in enumerate(selected, 1):
        episode, seat = key
        replay = json.loads(paths[episode].read_bytes())
        previous = None
        for turn in range(719):
            obs = replay["steps"][turn][seat]["observation"]
            features = state_features(obs, previous)
            action = replay["steps"][turn + 1][seat].get("action") or {}
            records.append((features, _targets(action), _positions(action), meta["split"], meta["rank"], meta["teacher"]))
            previous = obs
        if number % 20 == 0:
            print(json.dumps({"loaded_trajectories": number, "states": len(records)}), flush=True)
    names = sorted({key for features, *_ in records for key in features})
    x = np.asarray([[float(features.get(name, 0.0)) for name in names] for features, *_ in records], dtype=np.float32)
    train = np.asarray([split == "train" for _, _, _, split, _, _ in records])
    dev = ~train
    rank_weight = np.asarray([1.0 + (21-rank)/20.0 for _, _, _, _, rank, _ in records], dtype=np.float32)
    models, reports = {}, {}
    for index, target in enumerate(TARGETS):
        quantity = np.asarray([values.get(target, 0) for _, values, *_ in records], dtype=np.float32)
        position = np.asarray([values.get(target, 9) for _, _, values, *_ in records], dtype=np.float32)
        y = (quantity > 0).astype(np.int8)
        positive_train = int(y[train].sum())
        if positive_train < 8:
            continue
        event = DecisionTreeClassifier(max_depth=20 if args.teacher else 12,
                                       min_samples_leaf=2 if args.teacher else 12,
                                       random_state=1210+index,
                                       class_weight=None if args.teacher else {0: 1.0, 1: 6.0})
        event.fit(x[train], y[train], sample_weight=rank_weight[train])
        classes = list(event.classes_)
        p = event.predict_proba(x[dev])[:, classes.index(1)] if 1 in classes else np.zeros(dev.sum())
        threshold, metrics = _threshold(y[dev], p, 0.95 if args.teacher else 0.55)
        positive = train & (quantity > 0)
        amount = DecisionTreeRegressor(max_depth=14 if args.teacher else 10,
                                       min_samples_leaf=2 if args.teacher else 8,
                                       random_state=2210+index)
        amount.fit(x[positive], quantity[positive], sample_weight=rank_weight[positive])
        position_model = DecisionTreeRegressor(max_depth=12 if args.teacher else 8,
                                               min_samples_leaf=2 if args.teacher else 4,
                                               random_state=3210+index)
        position_model.fit(x[positive], position[positive], sample_weight=rank_weight[positive])
        qpred = np.maximum(1, np.rint(amount.predict(x[dev][y[dev] > 0])))
        qtruth = quantity[dev][y[dev] > 0]
        metrics.update({"train_events": positive_train, "dev_events": int(y[dev].sum()),
                        "threshold": threshold,
                        "quantity_mae": float(np.mean(np.abs(qpred-qtruth))) if len(qtruth) else None,
                        "event_nodes": int(event.tree_.node_count), "quantity_nodes": int(amount.tree_.node_count),
                        "position_nodes": int(position_model.tree_.node_count)})
        models[target] = {"threshold": threshold, "event": _export_classifier(event, names),
                          "quantity": _export_regressor(amount, names),
                          "position": _export_regressor(position_model, names)}
        reports[target] = metrics
        print(json.dumps({"target": target, **metrics}), flush=True)
    payload = {"schema": "kaggriculture-top20-structured-market-hmoe-v1",
               "runtime_contract": {"tape": False, "step_lookup": False, "future_features": False},
               "teachers": chosen_teachers, "teacher_count": len(chosen_teachers), "feature_names": names, "models": models}
    report = {"selected_trajectories": len(selected), "states": len(records), "teachers": chosen_teachers, "targets": reports}
    output, report_path = Path(args.output).expanduser().resolve(), Path(args.report).expanduser().resolve()
    output.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "targets": len(models), "states": len(records)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
