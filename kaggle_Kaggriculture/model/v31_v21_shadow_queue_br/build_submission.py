"""Build the deterministic, self-contained V31 Kaggle archive."""

from __future__ import annotations

import gzip
import hashlib
from io import BytesIO
import json
from pathlib import Path
import tarfile
from tempfile import TemporaryDirectory


HERE = Path(__file__).resolve().parent
ARCHIVE = HERE / "submission.tar.gz"
MANIFEST = HERE / "submission_manifest.json"
MEMBERS = (
    "main.py",
    "queue_core.py",
    "v21_adapter.py",
    "v21_parent.py",
    "official_kaggriculture.py",
    "kaggriculture.json",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def build() -> dict[str, object]:
    records = []
    for name in MEMBERS:
        path = HERE / name
        if not path.is_file():
            raise FileNotFoundError(path)
        text = path.read_text(encoding="utf-8")
        if "/Users/" in text or "kaggle_Kaggriculture.model" in text:
            raise RuntimeError(f"repository dependency leaked into {name}")
        records.append({"path": name, "size_bytes": path.stat().st_size, "sha256": sha256(path)})

    with ARCHIVE.open("wb") as sink:
        with gzip.GzipFile(filename="", mode="wb", fileobj=sink, mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as archive:
                for record in records:
                    path = HERE / str(record["path"])
                    data = path.read_bytes()
                    info = tarfile.TarInfo(str(record["path"]))
                    info.size = len(data)
                    info.mode = 0o644
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    info.mtime = 0
                    archive.addfile(info, BytesIO(data))

    with TemporaryDirectory(prefix="v31_extract_") as directory:
        root = Path(directory)
        with tarfile.open(ARCHIVE, "r:gz") as archive:
            archive.extractall(root, filter="data")
        extracted = [
            {"path": name, "size_bytes": (root / name).stat().st_size, "sha256": sha256(root / name)}
            for name in MEMBERS
        ]
    if extracted != records:
        raise RuntimeError("archive extraction differs from source manifest")

    result = {
        "schema": "kaggriculture-v31-submission-1",
        "model_id": "v31_v21_shadow_queue_br",
        "parent_id": "v21_top_meta_moe",
        "archive": ARCHIVE.name,
        "archive_size_bytes": ARCHIVE.stat().st_size,
        "archive_sha256": sha256(ARCHIVE),
        "deterministic_archive": True,
        "files": records,
    }
    MANIFEST.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
