#!/usr/bin/env python3
"""构建确定性的 V117 R2.1 模块化 Kaggle 归档。"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path

from schema import ENGINE_VERSION, VERSION


HERE = Path(__file__).resolve().parent
ARCHIVE = HERE / "submission.tar.gz"
MANIFEST = HERE / "submission_manifest.json"
RUNTIME_ROOT_FILES = ("main.py", "schema.py", "contracts.py", "state_ledger.py")
RUNTIME_DIRS = ("experts", "router", "executor", "market", "safety", "diagnostics")


def runtime_files() -> list[Path]:
    paths = [HERE / name for name in RUNTIME_ROOT_FILES]
    for folder in RUNTIME_DIRS:
        paths.extend(sorted(path for path in (HERE / folder).glob("*.py") if path.name != "__pycache__"))
    return sorted(paths, key=lambda path: str(path.relative_to(HERE)))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    files = runtime_files()
    with ARCHIVE.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as archive:
                for path in files:
                    payload = path.read_bytes()
                    name = str(path.relative_to(HERE))
                    info = tarfile.TarInfo(name)
                    info.size = len(payload)
                    info.mode = 0o644
                    info.mtime = 0
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    archive.addfile(info, io.BytesIO(payload))
    source_hashes = {str(path.relative_to(HERE)): sha256(path) for path in files}
    result = {
        "schema": "v117-r2.1-submission-manifest-v1",
        "version": VERSION, "strategy_parent": None,
        "engine": ENGINE_VERSION, "archive": ARCHIVE.name,
        "archive_members": list(source_hashes), "source_sha256": source_hashes,
        "archive_sha256": sha256(ARCHIVE),
        "evidence_status": "FULL_ARCHITECTURE_ENGINEERING_READY_SPECIALISTS_QUARANTINED_NOT_GOLD",
    }
    MANIFEST.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
