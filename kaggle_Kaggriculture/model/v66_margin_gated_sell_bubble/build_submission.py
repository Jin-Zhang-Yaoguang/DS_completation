"""Build a deterministic self-contained V66 Kaggle archive."""

from __future__ import annotations

import gzip
import hashlib
from io import BytesIO
import json
from pathlib import Path
import tarfile


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "main.py"
ARCHIVE = HERE / "submission.tar.gz"
MANIFEST = HERE / "submission_manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def build() -> dict[str, object]:
    text = SOURCE.read_text(encoding="utf-8")
    if "/Users/" in text or "kaggle_Kaggriculture.model" in text:
        raise RuntimeError("repository dependency leaked into serving source")
    data = SOURCE.read_bytes()
    with ARCHIVE.open("wb") as sink:
        with gzip.GzipFile(filename="", mode="wb", fileobj=sink, mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as archive:
                info = tarfile.TarInfo("main.py")
                info.size = len(data)
                info.mode = 0o644
                info.uid = info.gid = 0
                info.uname = info.gname = ""
                info.mtime = 0
                archive.addfile(info, BytesIO(data))
    result = {
        "schema": "kaggriculture-v66-submission-1",
        "model_id": "v66_margin_gated_sell_bubble",
        "parent_id": "v54_terminal_water_bypass",
        "archive": ARCHIVE.name,
        "archive_size_bytes": ARCHIVE.stat().st_size,
        "archive_sha256": sha256(ARCHIVE),
        "main_sha256": sha256(SOURCE),
        "deterministic_archive": True,
    }
    MANIFEST.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
