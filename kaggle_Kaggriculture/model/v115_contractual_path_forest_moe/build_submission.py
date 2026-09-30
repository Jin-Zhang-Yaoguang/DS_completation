#!/usr/bin/env python3
"""Build deterministic standalone V115 sources and Kaggle archive."""

from __future__ import annotations

import base64
import gzip
import hashlib
import importlib.util
from io import BytesIO
import json
from pathlib import Path
import tarfile
import zlib

import numpy as np
from sklearn.tree import DecisionTreeClassifier


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
BLUEPRINT_SOURCE = MODEL / "v27_lucaskna_shop_router/main.py"
PREDICTIVE_CACHE = MODEL / "v97_opponent_market_impact_tempo_moe/predictive_probe_arrays.npz"
PREDICTIVE_REPORT = MODEL / "v97_opponent_market_impact_tempo_moe/predictive_probe_results.json"
TEMPLATE = HERE / "main_template.py"
ARCHIVE = HERE / "submission.tar.gz"
MODES = ("full", "ablation", "expert_default", "expert_yarn", "expert_dairy", "expert_smoothie")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_blueprints():
    spec = importlib.util.spec_from_file_location("v115_blueprint_source", BLUEPRINT_SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    plans = {
        "default": module._V19_ROUTES["default"],
        "yarn": module._V19_ROUTES["yarn"],
        "dairy": module._V21_LUCASKNA_ROUTE,
        "smoothie": module._V27_LUCAS_SMOOTHIE,
    }
    for name, rows in plans.items():
        if len(rows) != 719 or not all(isinstance(row, dict) for row in rows):
            raise RuntimeError(f"invalid complete blueprint: {name}")
        if any(set(row) - {"farmer", "hands", "market"} for row in rows):
            raise RuntimeError(f"non-action payload: {name}")
    return plans


def train_tree():
    arrays = np.load(PREDICTIVE_CACHE)
    model = DecisionTreeClassifier(
        max_depth=6,
        min_samples_leaf=100,
        class_weight="balanced",
        random_state=115,
    ).fit(arrays["x"], arrays["y"])
    tree = model.tree_
    return {
        "left": tree.children_left.tolist(),
        "right": tree.children_right.tolist(),
        "feature": tree.feature.tolist(),
        "threshold": tree.threshold.tolist(),
        "value": tree.value[:, 0, :].tolist(),
        "classes": [int(value) for value in model.classes_.tolist()],
    }


def render(payload, mode):
    packed = base64.b85encode(zlib.compress(
        json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8"), 9
    )).decode("ascii")
    text = TEMPLATE.read_text(encoding="utf-8").replace("__PAYLOAD__", packed).replace("__MODE__", mode)
    forbidden = ("spec_from_file", "parent_agent", "load_parent", "v76.agent", "_PARENT_AGENT")
    hits = [token for token in forbidden if token in text]
    if hits:
        raise RuntimeError(f"complete-agent dependency tokens: {hits}")
    compile(text, f"v115-{mode}", "exec")
    return text


def write_archive(source: Path):
    with ARCHIVE.open("wb") as sink:
        with gzip.GzipFile(filename="", mode="wb", fileobj=sink, mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as archive:
                data = source.read_bytes()
                info = tarfile.TarInfo("main.py")
                info.size, info.mode, info.uid, info.gid, info.mtime = len(data), 0o644, 0, 0, 0
                info.uname = info.gname = ""
                archive.addfile(info, BytesIO(data))


def main():
    payload = {"plans": load_blueprints(), "tree": train_tree()}
    paths = {}
    for mode in MODES:
        path = HERE / ("main.py" if mode == "full" else f"{mode}_main.py")
        path.write_text(render(payload, mode), encoding="utf-8")
        paths[mode] = path
    write_archive(paths["full"])
    manifest = {
        "schema": "kaggriculture-v115-submission-v1",
        "model_id": "v115_contractual_path_forest_moe",
        "strategy_parent": None,
        "strength_comparator": "v76_adjacent_safe_buy_lead",
        "archive": ARCHIVE.name,
        "archive_sha256": sha256(ARCHIVE),
        "main_sha256": sha256(paths["full"]),
        "mode_sha256": {mode: sha256(path) for mode, path in paths.items()},
        "blueprint_source_path": str(BLUEPRINT_SOURCE.relative_to(MODEL.parent)),
        "blueprint_source_sha256": sha256(BLUEPRINT_SOURCE),
        "predictive_cache_sha256": sha256(PREDICTIVE_CACHE),
        "predictive_report_sha256": sha256(PREDICTIVE_REPORT),
        "blueprint_payload_only": True,
        "complete_historical_agent_bundled": False,
        "engine": "1.32.7",
        "remote_submission": "NOT_AUTHORIZED_NOT_SUBMITTED",
    }
    (HERE / "submission_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

