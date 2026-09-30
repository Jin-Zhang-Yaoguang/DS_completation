#!/usr/bin/env python3
"""Build deterministic V85 archive with the frozen V76 parent bundled."""

from __future__ import annotations

import gzip
import hashlib
from io import BytesIO
import json
from pathlib import Path
import tarfile


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
FILES = {"main.py": HERE / "main.py", "parent_v76.py": MODEL / "v76_adjacent_safe_buy_lead/main.py"}
ARCHIVE = HERE / "submission.tar.gz"
MANIFEST = HERE / "submission_manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def build():
    for source in FILES.values():
        text = source.read_text(encoding="utf-8")
        if "/Users/" in text or "kaggle_Kaggriculture.model" in text:
            raise RuntimeError(f"repository dependency leaked into {source.name}")
    with ARCHIVE.open("wb") as sink:
        with gzip.GzipFile(filename="", mode="wb", fileobj=sink, mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as archive:
                for arcname, source in FILES.items():
                    data = source.read_bytes()
                    info = tarfile.TarInfo(arcname)
                    info.size, info.mode, info.uid, info.gid, info.mtime = len(data), 0o644, 0, 0, 0
                    info.uname = info.gname = ""
                    archive.addfile(info, BytesIO(data))
    result = {
        "schema": "kaggriculture-v85-submission-v1",
        "model_id": "v85_fertilizer_substitution_moe",
        "parent_id": "v76_adjacent_safe_buy_lead",
        "strategy": "idle-unit fertilizer byproduct collection with frozen V76 fallback",
        "archive": ARCHIVE.name,
        "archive_size_bytes": ARCHIVE.stat().st_size,
        "archive_sha256": sha256(ARCHIVE),
        "main_sha256": sha256(HERE / "main.py"),
        "parent_main_sha256": sha256(FILES["parent_v76.py"]),
        "engine": "1.32.7",
        "deterministic_archive": True,
        "remote_submission": "NOT_AUTHORIZED_NOT_SUBMITTED",
    }
    MANIFEST.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
