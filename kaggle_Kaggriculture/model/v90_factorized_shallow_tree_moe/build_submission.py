#!/usr/bin/env python3
"""Train, export, and package V90's factorized shallow-tree MoE."""

from __future__ import annotations

import base64
from collections import Counter
import gzip
import hashlib
from io import BytesIO
import json
from pathlib import Path
import tarfile
import zlib

import numpy as np
from sklearn.metrics import accuracy_score
from sklearn.model_selection import GroupKFold
from sklearn.tree import DecisionTreeClassifier


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
PROJECT = MODEL.parent
MODEL_DATA = PROJECT / "model_data"
REPORT = MODEL_DATA / "v17_rc1_online_2026-08-27/report/top5_replication_per_game.jsonl"
REPLAY_DIR = MODEL_DATA / "v17_rc1_online_2026-08-27/top5_leaderboard_replays"
TEMPLATE = HERE / "main_template.py"
ARCHIVE = HERE / "submission.tar.gz"
TEAM = "lucaskna"
SUBMISSION_ID = 55803928
ITEMS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
SEEDS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")
SHOPS = ("BAKERY", "BRUNCH_SPOT", "FARMERS_MARKET", "ICE_CREAM_SHOP", "PET_CAFE", "PIZZA_SHOP", "SMOOTHIE_SHOP", "YARN_STORE")
ASSETS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "GOOSE", "COW", "SHEEP", "PASTURE", "COOP", "WEED")
TILE_TYPES = ("EMPTY", "LOCKED", "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "GOOSE", "COW", "SHEEP", "PASTURE", "COOP", "WEED", "OTHER")
TREE_ARGS = {"max_depth": 18, "max_leaf_nodes": 4096, "min_samples_leaf": 3, "random_state": 9001}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def replay_path(episode_id):
    path = REPLAY_DIR / f"episode-{episode_id}-replay.json"
    if path.exists():
        return path
    matches = sorted(MODEL_DATA.glob(f"kaggriculture_episodes_index/date=*/data/{episode_id}.json"))
    if not matches:
        raise FileNotFoundError(episode_id)
    return matches[-1]


def tile_type(tile):
    if tile is None:
        return "EMPTY"
    if tile == "LOCKED":
        return "LOCKED"
    if isinstance(tile, dict):
        value = str(tile.get("crop") or tile.get("animal") or tile.get("kind") or "OTHER").upper()
        return value if value in TILE_TYPES else "OTHER"
    return "OTHER"


def features(observation, seat, actor, slot=-1):
    step = int(observation.get("step", int(observation.get("day", 0)) * 24 + int(observation.get("hour", 0))))
    farm = observation["farms"][seat]
    private = observation["private"]
    positions = [farm["farmer"], *farm["hands"]]
    inventories = list(private["inventories"])
    shops = [str(value) for value in observation["town"]["unlocked_shops"]]
    shop_counts = {key: shops.count(key) for key in SHOPS}
    assets = {key: 0 for key in ASSETS}
    for row in farm["tiles"]:
        for tile in row:
            value = tile_type(tile)
            if value in assets:
                assets[value] += 1
    if 0 <= actor < len(positions):
        position = positions[actor]
        tile = farm["tiles"][position[1]][position[0]]
        inventory = inventories[actor]
    else:
        position, tile, inventory = (-1, -1), "LOCKED", {}
    tile_name = tile_type(tile)
    values = [step, step // 24, step % 24, len(farm["hands"]), len(farm["unlocked_quadrants"]), float(farm["money"]) / 100.0,
              actor, slot, position[0], position[1]]
    values.extend(1.0 if tile_name == key else 0.0 for key in TILE_TYPES)
    values.extend([
        float(tile.get("yield_units", 0) or 0) if isinstance(tile, dict) else 0.0,
        float(bool(tile.get("watered_today"))) if isinstance(tile, dict) else 0.0,
        float(bool(tile.get("fed_today"))) if isinstance(tile, dict) else 0.0,
        float(bool(tile.get("cared_today"))) if isinstance(tile, dict) else 0.0,
        float(bool(tile.get("fertilizer_available"))) if isinstance(tile, dict) else 0.0,
    ])
    values.extend(float(inventory.get(key, 0) or 0) for key in ITEMS)
    values.extend(float(shop_counts[key]) for key in SHOPS)
    values.extend(float(private["seeds"].get(key, 0) or 0) for key in SEEDS)
    values.extend(float(private["shed"].get(key, 0) or 0) for key in ITEMS)
    values.extend(float(assets[key]) for key in ASSETS)
    return values


def load_rows():
    report_rows = [json.loads(line) for line in REPORT.read_text(encoding="utf-8").splitlines() if line.strip()]
    selected = sorted(
        (row for row in report_rows if int(row.get("submission_id") or 0) == SUBMISSION_ID and row.get("result") == "W"),
        key=lambda row: int(row["episode_id"]),
    )
    unit_x, unit_y, unit_g, unit_r = [], [], [], []
    market_x, market_y, market_g, market_r = [], [], [], []
    provenance = []
    for row in selected:
        episode_id = int(row["episode_id"])
        path = replay_path(episode_id)
        replay = json.loads(path.read_text(encoding="utf-8"))
        seat = replay["info"]["TeamNames"].index(TEAM)
        regime = str(row["first_shop"])
        provenance.append({"episode_id": episode_id, "seed": int(row["seed"]), "seat": seat, "first_shop": regime, "replay_sha256": sha256(path)})
        for step in range(719):
            observation = replay["steps"][step][seat]["observation"]
            action = replay["steps"][step + 1][seat].get("action") or {}
            orders = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
            for actor, order in enumerate(orders):
                unit_x.append(features(observation, seat, actor))
                unit_y.append(json.dumps(order, separators=(",", ":")))
                unit_g.append(episode_id)
                unit_r.append(regime)
            market = action.get("market") or []
            for slot in range(10):
                market_x.append(features(observation, seat, -1, slot))
                market_y.append(json.dumps(market[slot] if slot < len(market) else [], separators=(",", ":")))
                market_g.append(episode_id)
                market_r.append(regime)
    if len(provenance) != 50:
        raise RuntimeError("training episode count mismatch")
    return (
        np.asarray(unit_x, dtype=np.float32), np.asarray(unit_y), np.asarray(unit_g), np.asarray(unit_r),
        np.asarray(market_x, dtype=np.float32), np.asarray(market_y), np.asarray(market_g), np.asarray(market_r),
        provenance,
    )


def fit_tree(x, y):
    model = DecisionTreeClassifier(**TREE_ARGS)
    model.fit(x, y)
    return model


def export_tree(model):
    tree = model.tree_
    output = np.argmax(tree.value[:, 0, :], axis=1)
    return {
        "labels": [str(value) for value in model.classes_],
        "left": tree.children_left.astype(int).tolist(),
        "right": tree.children_right.astype(int).tolist(),
        "feature": tree.feature.astype(int).tolist(),
        "threshold": np.round(tree.threshold, 6).tolist(),
        "output": output.astype(int).tolist(),
        "depth": int(tree.max_depth),
        "nodes": int(tree.node_count),
    }


def oof_accuracy(x, y, groups, label):
    predictions = np.empty(len(y), dtype=object)
    splitter = GroupKFold(n_splits=5)
    fold_rows = []
    for fold, (train, valid) in enumerate(splitter.split(x, y, groups), 1):
        model = fit_tree(x[train], y[train])
        predictions[valid] = model.predict(x[valid])
        fold_rows.append({"fold": fold, "groups": len(set(groups[valid])), "accuracy": float(accuracy_score(y[valid], predictions[valid]))})
    result = {"label": label, "accuracy": float(accuracy_score(y, predictions)), "folds": fold_rows}
    if label == "market_slot":
        nonempty = y != "[]"
        result["nonempty_accuracy"] = float(accuracy_score(y[nonempty], predictions[nonempty]))
        result["nonempty_samples"] = int(nonempty.sum())
    return result


def render(payload, mode):
    packed = base64.b85encode(zlib.compress(json.dumps(payload, separators=(",", ":")).encode(), 9)).decode("ascii")
    text = TEMPLATE.read_text(encoding="utf-8").replace("__MODEL_PAYLOAD__", packed).replace("__MODE__", mode)
    forbidden = ("importlib", "spec_from_file", "parent_agent", "_PARENT_AGENT", "load_parent", "v76.agent")
    hits = [token for token in forbidden if token in text]
    if hits:
        raise RuntimeError(f"complete-agent dependency tokens: {hits}")
    compile(text, f"v90-{mode}", "exec")
    return text


def write_archive(source):
    with ARCHIVE.open("wb") as sink:
        with gzip.GzipFile(filename="", mode="wb", fileobj=sink, mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as archive:
                data = source.read_bytes()
                info = tarfile.TarInfo("main.py")
                info.size, info.mode, info.uid, info.gid, info.mtime = len(data), 0o644, 0, 0, 0
                info.uname = info.gname = ""
                archive.addfile(info, BytesIO(data))


def main():
    ux, uy, ug, ur, mx, my, mg, mr, provenance = load_rows()
    oof = {"unit": oof_accuracy(ux, uy, ug, "unit"), "market": oof_accuracy(mx, my, mg, "market_slot")}
    trees = {"GLOBAL": {"unit": export_tree(fit_tree(ux, uy)), "market": export_tree(fit_tree(mx, my))}}
    for regime in SHOPS:
        ui = np.flatnonzero(ur == regime)
        mi = np.flatnonzero(mr == regime)
        trees[regime] = {"unit": export_tree(fit_tree(ux[ui], uy[ui])), "market": export_tree(fit_tree(mx[mi], my[mi]))}
    payload = {"schema": "v90-factorized-shallow-tree-payload-v1", "trees": trees}
    (HERE / "main.py").write_text(render(payload, "full"), encoding="utf-8")
    (HERE / "ablation_main.py").write_text(render(payload, "ablation"), encoding="utf-8")
    write_archive(HERE / "main.py")
    report = {
        "schema": "kaggriculture-v90-training-v1",
        "episode_count": len(provenance),
        "unit_samples": len(uy),
        "unit_classes": len(set(uy)),
        "market_slot_samples": len(my),
        "market_slot_classes": len(set(my)),
        "oof": oof,
        "tree_nodes": {key: {kind: value["nodes"] for kind, value in pair.items()} for key, pair in trees.items()},
        "training_provenance_sha256": hashlib.sha256(json.dumps(provenance, sort_keys=True).encode()).hexdigest(),
    }
    (HERE / "training_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "schema": "kaggriculture-v90-submission-v1",
        "model_id": "v90_factorized_shallow_tree_moe",
        "strategy_parent": None,
        "strength_comparator": "v76_adjacent_safe_buy_lead",
        "archive_sha256": sha256(ARCHIVE),
        "main_sha256": sha256(HERE / "main.py"),
        "ablation_main_sha256": sha256(HERE / "ablation_main.py"),
        "training_episode_count": len(provenance),
        "training_report_sha256": sha256(HERE / "training_report.json"),
        "complete_historical_agent_bundled": False,
        "engine": "1.32.7",
        "remote_submission": "NOT_AUTHORIZED_NOT_SUBMITTED",
    }
    (HERE / "submission_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": manifest, "training": report}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
