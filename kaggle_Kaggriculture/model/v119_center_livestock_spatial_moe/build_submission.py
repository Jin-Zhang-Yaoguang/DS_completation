"""Build the deterministic V119 archive after the spatial contract passes."""

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
SPATIAL_RESULTS = HERE / "spatial_contract_results.json"
SOURCE_REPLAY = HERE / "evidence/episode-103982514-replay.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict[str, object]:
    spatial = json.loads(SPATIAL_RESULTS.read_text(encoding="utf-8"))
    if spatial.get("gate") != "PASS" or not all(spatial.get("gates", {}).values()):
        raise RuntimeError("V119 spatial contract did not pass")
    if spatial.get("source", {}).get("replay_sha256") != sha256(SOURCE_REPLAY):
        raise RuntimeError("source replay changed after spatial evaluation")

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
        "schema": "kaggriculture-v119-submission-v1",
        "model_id": "v119_center_livestock_spatial_moe",
        "parent_id": "v118_v76_yarn_reveal_liquidity_moe",
        "archive": ARCHIVE.name,
        "archive_size_bytes": ARCHIVE.stat().st_size,
        "archive_sha256": sha256(ARCHIVE),
        "main_sha256": sha256(SOURCE),
        "source_replay_sha256": sha256(SOURCE_REPLAY),
        "spatial_results_sha256": sha256(SPATIAL_RESULTS),
        "production_action_source_sha256": "8b227c3e81eb298a8fb57aef03a014806cbea8ca56a23daa623059a3b5e60908",
        "spatial_contract": "PASS",
        "deterministic_archive": True,
        "remote_submission_at_build_time": "NOT_SUBMITTED",
        "submission_result_record": "submission_record.json",
    }
    MANIFEST.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
