#!/usr/bin/env python3
"""Build standalone V86 full/ablation sources and deterministic archive."""

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


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
SOURCE = MODEL / "v27_lucaskna_shop_router/main.py"
TEMPLATE = HERE / "main_template.py"
ARCHIVE = HERE / "submission.tar.gz"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_blueprints():
    spec = importlib.util.spec_from_file_location("v86_blueprint_source", SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    plans = {
        "default": module._V19_ROUTES["default"],
        "yarn": module._V19_ROUTES["yarn"],
        "dairy": module._V21_LUCASKNA_ROUTE,
        "smoothie": module._V27_LUCAS_SMOOTHIE,
    }
    if set(plans) != {"default", "yarn", "dairy", "smoothie"}:
        raise RuntimeError("blueprint set mismatch")
    for name, rows in plans.items():
        if len(rows) != 719 or not all(isinstance(row, dict) for row in rows):
            raise RuntimeError(f"invalid blueprint {name}")
        for row in rows:
            if set(row) - {"farmer", "hands", "market"}:
                raise RuntimeError(f"non-action payload in {name}")
    return plans


def render(plans, mode):
    packed = base64.b85encode(zlib.compress(
        json.dumps(plans, ensure_ascii=True, separators=(",", ":")).encode("utf-8"), 9
    )).decode("ascii")
    text = TEMPLATE.read_text(encoding="utf-8")
    text = text.replace("__ROUTE_PAYLOAD__", packed).replace("__MODE__", mode)
    forbidden = ("importlib", "spec_from_file", "parent_agent", "_PARENT_AGENT", "load_parent")
    hits = [token for token in forbidden if token in text]
    if hits:
        raise RuntimeError(f"complete-agent dependency tokens: {hits}")
    compile(text, f"v86-{mode}", "exec")
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
    plans = load_blueprints()
    (HERE / "main.py").write_text(render(plans, "full"), encoding="utf-8")
    (HERE / "ablation_main.py").write_text(render(plans, "ablation"), encoding="utf-8")
    write_archive(HERE / "main.py")
    payload = {
        "schema": "kaggriculture-v86-submission-v1",
        "model_id": "v86_multiscale_demand_task_moe",
        "strategy_parent": None,
        "strength_comparator": "v76_adjacent_safe_buy_lead",
        "archive": ARCHIVE.name,
        "archive_sha256": sha256(ARCHIVE),
        "main_sha256": sha256(HERE / "main.py"),
        "ablation_main_sha256": sha256(HERE / "ablation_main.py"),
        "blueprint_source_path": str(SOURCE.relative_to(MODEL.parent)),
        "blueprint_source_sha256": sha256(SOURCE),
        "blueprint_payload_only": True,
        "complete_historical_agent_bundled": False,
        "engine": "1.32.7",
        "remote_submission": "NOT_AUTHORIZED_NOT_SUBMITTED",
    }
    (HERE / "submission_manifest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
