#!/usr/bin/env python3
"""Train current-state market-slot trees from a balanced sample of all Top20."""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import balanced_accuracy_score
from sklearn.tree import DecisionTreeClassifier

from contract_features import state_features


HERE = Path(__file__).resolve().parent
DATA = HERE / "dataset/daily_contract.jsonl"
OUTPUT = HERE / "market_slot_hmoe.json"
REPORT = HERE / "market_slot_training_report.json"


def _label(order) -> str:
    if not order: return "PASS"
    return json.dumps(list(order), ensure_ascii=False, separators=(",", ":"))


def _export(model: DecisionTreeClassifier, names: list[str]) -> dict:
    tree, classes = model.tree_, [str(value) for value in model.classes_]
    def node(index: int) -> dict:
        if tree.children_left[index] == tree.children_right[index]:
            counts = np.asarray(tree.value[index][0], dtype=float)
            best = int(np.argmax(counts))
            return {"leaf": classes[best], "confidence": float(counts[best] / max(1e-12, counts.sum()))}
        return {"feature": names[int(tree.feature[index])], "threshold": float(tree.threshold[index]),
                "left": node(int(tree.children_left[index])), "right": node(int(tree.children_right[index]))}
    return {"depth": int(tree.max_depth), "nodes": int(tree.node_count), "root": node(0)}


def main() -> int:
    trajectories = {}
    for line in DATA.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("source_panel") != "top20_cli_training_auxiliary": continue
        key = (int(row["episode_id"]), int(row["seat"]))
        trajectories[key] = {"teacher": str(row["teacher"]), "rank": int(row["leaderboard_rank"]), "split": str(row["split"])}
    grouped = defaultdict(lambda: defaultdict(list))
    for key, meta in trajectories.items(): grouped[meta["teacher"]][meta["split"]].append((key, meta))
    selected = []
    for teacher in sorted(grouped):
        selected.extend(sorted(grouped[teacher]["train"])[:6])
        selected.extend(sorted(grouped[teacher]["dev"])[:2])
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
            market = list(action.get("market") or [])
            labels = [_label(market[slot] if slot < len(market) else None) for slot in range(10)]
            records.append((features, labels, meta["split"], meta["rank"], meta["teacher"]))
            previous = obs
        if number % 20 == 0: print(json.dumps({"loaded_trajectories": number, "states": len(records)}), flush=True)
    names = sorted({key for features, *_ in records for key in features})
    x = np.asarray([[float(features.get(name, 0.0)) for name in names] for features, *_ in records], dtype=np.float32)
    train = np.asarray([split == "train" for _, _, split, _, _ in records]); dev = ~train
    weights = np.asarray([(1.0 + (21 - rank) / 20.0) * (3.0 if any(label != "PASS" for label in labels) else 1.0)
                          for _, labels, _, rank, _ in records], dtype=np.float32)
    models, slot_reports, dev_predictions = [], [], []
    for slot in range(10):
        y = np.asarray([labels[slot] for _, labels, *_ in records], dtype=object)
        model = DecisionTreeClassifier(max_depth=22, min_samples_leaf=3, random_state=1200 + slot, class_weight="balanced")
        model.fit(x[train], y[train], sample_weight=weights[train])
        pred = model.predict(x[dev]); dev_predictions.append(pred)
        nonpass = y[dev] != "PASS"
        slot_reports.append({"slot": slot, "classes": int(len(model.classes_)), "nodes": int(model.tree_.node_count),
                             "accuracy": float(np.mean(pred == y[dev])),
                             "balanced_accuracy": float(balanced_accuracy_score(y[dev], pred)),
                             "nonpass_recall": float(np.mean(pred[nonpass] == y[dev][nonpass])) if nonpass.any() else 1.0})
        models.append(_export(model, names)); print(json.dumps(slot_reports[-1]), flush=True)
    truth = np.asarray([labels for _, labels, split, *_ in records if split == "dev"], dtype=object)
    prediction = np.column_stack(dev_predictions)
    teachers = sorted(grouped)
    payload = {"schema": "kaggriculture-top20-current-state-market-slot-hmoe-v1",
               "runtime_contract": {"tape": False, "step_lookup": False, "future_features": False},
               "teachers": teachers, "teacher_count": len(teachers), "feature_names": names, "slots": models}
    report = {"selected_trajectories": len(selected), "train_trajectories": sum(meta["split"] == "train" for _, meta in selected),
              "dev_trajectories": sum(meta["split"] == "dev" for _, meta in selected), "teachers": teachers,
              "states": len(records), "dev_full_queue_exact": float(np.mean(np.all(prediction == truth, axis=1))), "slots": slot_reports}
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), **{k: report[k] for k in ("selected_trajectories", "states", "dev_full_queue_exact")}}, ensure_ascii=False))
    return 0


if __name__ == "__main__": raise SystemExit(main())
