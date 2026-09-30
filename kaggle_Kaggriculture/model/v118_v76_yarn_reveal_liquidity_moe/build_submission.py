"""Build the frozen, gate-passed V118 deterministic Kaggle archive."""

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
GATE_RESULTS = HERE / "frozen_gate_results_rc2.json"
GATE_MANIFEST = HERE / "gate_panel_manifest_rc2.json"
PARENT = HERE.parent / "v76_adjacent_safe_buy_lead/main.py"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def build() -> dict[str, object]:
    gate = json.loads(GATE_RESULTS.read_text(encoding="utf-8"))
    gate_manifest = json.loads(GATE_MANIFEST.read_text(encoding="utf-8"))
    source_sha = sha256(SOURCE)
    parent_sha = sha256(PARENT)
    lock = gate_manifest.get("candidate_lock") or {}
    if gate.get("pass") is not True:
        raise RuntimeError("strict frozen gate did not pass")
    if gate.get("gate_metric") != "pure_win_rate; ties are not wins":
        raise RuntimeError("frozen gate metric is not the strict pure-win metric")
    if gate.get("candidate_main_sha256") != source_sha or lock.get("main_sha256") != source_sha:
        raise RuntimeError("candidate changed after frozen gate")
    if gate.get("parent_main_sha256") != parent_sha or lock.get("parent_main_sha256") != parent_sha:
        raise RuntimeError("V76 parent changed after frozen gate")
    required = {
        "target_yarn_2_or_3": 0.80,
        "random": 0.55,
    }
    for panel, threshold in required.items():
        result = gate.get("panels", {}).get(panel, {})
        if result.get("pass") is not True or float(result.get("pure_win_rate", -1)) < threshold:
            raise RuntimeError(f"strict frozen panel failed: {panel}")
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
        "schema": "kaggriculture-v118-submission-1",
        "model_id": "v118_v76_yarn_reveal_liquidity_moe",
        "parent_id": "v76_adjacent_safe_buy_lead",
        "archive": ARCHIVE.name,
        "archive_size_bytes": ARCHIVE.stat().st_size,
        "archive_sha256": sha256(ARCHIVE),
        "main_sha256": source_sha,
        "parent_main_sha256": parent_sha,
        "gate_results_sha256": sha256(GATE_RESULTS),
        "gate_manifest_sha256": sha256(GATE_MANIFEST),
        "strict_gate": {
            panel: {
                "pure_win_rate": gate["panels"][panel]["pure_win_rate"],
                "wins_ties_losses": gate["panels"][panel]["wins_ties_losses"],
            }
            for panel in required
        },
        "deterministic_archive": True,
    }
    MANIFEST.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
