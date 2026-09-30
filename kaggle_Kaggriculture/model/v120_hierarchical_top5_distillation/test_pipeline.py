#!/usr/bin/env python3
"""V120 数据与模型产物的轻量一致性测试。"""

from __future__ import annotations

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> int:
    manifest = json.loads((HERE / "dataset_manifest.json").read_text(encoding="utf-8"))
    report = json.loads((HERE / "pilot_training_report.json").read_text(encoding="utf-8"))
    model = json.loads((HERE / "pilot_model.json").read_text(encoding="utf-8"))
    shop = rows(HERE / "dataset/shop_refresh.jsonl")
    day = rows(HERE / "dataset/daily_movement.jsonl")
    global_rows = rows(HERE / "dataset/global_strategy.jsonl")
    assert len(shop) == manifest["rows"]["shop_refresh"] == 190
    assert len(day) == manifest["rows"]["daily_movement"] == 570
    assert len(global_rows) == manifest["rows"]["global_strategy"] == 570
    train = set(report["split"]["train_episode_ids"])
    dev = set(report["split"]["dev_episode_ids"])
    assert train.isdisjoint(dev)
    assert train | dev == set(manifest["episode_ids"])
    assert report["split"]["leakage"] is False
    assert report["gate"] == {
        "shop_macro_signal": True,
        "day_macro_signal": True,
        "global_beats_mean": True,
    }
    assert model["status"] == "NOT_DEPLOYABLE"
    assert manifest["alignment"] == "steps[t].observation -> steps[t+1].action"
    print(json.dumps({"status": "PASS", "episodes": manifest["episodes"], "teacher_trajectories": manifest["teacher_trajectories"], "model_status": model["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
