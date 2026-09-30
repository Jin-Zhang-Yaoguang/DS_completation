#!/usr/bin/env python3
"""Package the frozen V120 standalone candidate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tarfile


HERE = Path(__file__).resolve().parent
MAIN = HERE / "main.py"
ARCHIVE = HERE / "submission.tar.gz"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    with tarfile.open(ARCHIVE, "w:gz") as archive:
        archive.add(MAIN, arcname="main.py")
    with tarfile.open(ARCHIVE, "r:gz") as archive:
        members = archive.getnames()
        embedded = archive.extractfile("main.py").read()
    result = {
        "schema": "kaggriculture-v120-submission-manifest-v1",
        "members": members,
        "main_sha256": sha256(MAIN),
        "embedded_main_sha256": hashlib.sha256(embedded).hexdigest(),
        "archive_sha256": sha256(ARCHIVE),
        "main_bytes": MAIN.stat().st_size,
        "archive_bytes": ARCHIVE.stat().st_size,
        "exact_source_archive_match": embedded == MAIN.read_bytes(),
        "status": "PACKAGE_PASS",
    }
    (HERE / "submission_manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
