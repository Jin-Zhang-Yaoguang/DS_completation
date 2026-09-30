"""Build and clean-room validate the self-contained V12A2 archive."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import tarfile
from tempfile import TemporaryDirectory

from kaggle_Kaggriculture.model.v12a_terminal_branch_guard import (
    build_submission as parent_build,
)


HERE = Path(__file__).resolve().parent
PARENT = HERE.parent / "v12a_terminal_branch_guard"
ARCHIVE = HERE / "submission.tar.gz"
MANIFEST = HERE / "submission_manifest.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def build() -> dict[str, object]:
    with TemporaryDirectory(prefix="kaggriculture_v12a2_build_") as directory:
        stage = Path(directory) / "stage"
        stage.mkdir()
        shutil.copy2(HERE / "main.py", stage / "main.py")
        shutil.copy2(PARENT / "main.py", stage / "base_agent.py")
        parent_build._copy_runtime(stage)
        parent_build._copy_experts(stage)
        parent_build._write_policy(stage)
        members = sorted(path for path in stage.rglob("*") if path.is_file())
        with tarfile.open(ARCHIVE, "w:gz") as archive:
            for path in members:
                archive.add(path, arcname=path.relative_to(stage))
        extract = Path(directory) / "extract"
        extract.mkdir()
        with tarfile.open(ARCHIVE, "r:gz") as archive:
            archive.extractall(extract, filter="data")
        module = parent_build._load_clean_main(extract / "main.py")
        clean_match = parent_build._clean_match(module)
        file_records = [
            {
                "path": str(path.relative_to(extract)),
                "size_bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
            for path in sorted(extract.rglob("*"))
            if path.is_file() and "__pycache__" not in path.parts
        ]
    result: dict[str, object] = {
        "schema": "kaggriculture-v12a2-submission-1",
        "model_id": "v12a2_no_wool_throttle",
        "parent_id": "v12a_terminal_branch_guard",
        "removed_component": "WOOL top-day throttle",
        "archive": ARCHIVE.name,
        "archive_size_bytes": ARCHIVE.stat().st_size,
        "archive_sha256": _sha256(ARCHIVE),
        "files": file_records,
        "clean_match": clean_match,
    }
    MANIFEST.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    build()
