#!/usr/bin/env python3
"""Build V91 from a frozen reference task stream and actor-state targets."""

from __future__ import annotations

import base64
import gzip
import hashlib
from io import BytesIO
import json
from pathlib import Path
import tarfile
import zlib


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
PROJECT = MODEL.parent
REPLAY = PROJECT / "model_data/v17_rc1_online_2026-08-27/top5_leaderboard_replays/episode-100485613-replay.json"
TEMPLATE = HERE / "main_template.py"
ARCHIVE = HERE / "submission.tar.gz"
TEAM = "lucaskna"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_reference():
    replay = json.loads(REPLAY.read_text(encoding="utf-8"))
    seat = replay["info"]["TeamNames"].index(TEAM)
    actions = [pair[seat].get("action") or {} for pair in replay["steps"][1:720]]
    targets = []
    for step in range(719):
        observation = replay["steps"][step][seat]["observation"]
        farm = observation["farms"][seat]
        targets.append({
            "positions": [farm["farmer"], *farm["hands"]],
            "inventories": observation["private"]["inventories"],
        })
    return {"actions": actions, "targets": targets, "source_seat": seat}


def render(reference, mode):
    packed = base64.b85encode(zlib.compress(json.dumps(reference, separators=(",", ":")).encode(), 9)).decode("ascii")
    text = TEMPLATE.read_text(encoding="utf-8").replace("__REFERENCE_PAYLOAD__", packed).replace("__MODE__", mode)
    forbidden = ("importlib", "spec_from_file", "parent_agent", "_PARENT_AGENT", "load_parent", "v76.agent")
    hits = [token for token in forbidden if token in text]
    if hits:
        raise RuntimeError(hits)
    compile(text, f"v91-{mode}", "exec")
    return text


def write_archive(source):
    with ARCHIVE.open("wb") as sink:
        with gzip.GzipFile(filename="", mode="wb", fileobj=sink, mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as archive:
                data = source.read_bytes()
                info = tarfile.TarInfo("main.py")
                info.size, info.mode, info.uid, info.gid, info.mtime = len(data), 0o644, 0, 0, 0
                info.uname = info.gname = ""
                archive.addfile(info, BytesIO(data))


def main():
    reference = load_reference()
    (HERE / "main.py").write_text(render(reference, "full"), encoding="utf-8")
    (HERE / "ablation_main.py").write_text(render(reference, "ablation"), encoding="utf-8")
    write_archive(HERE / "main.py")
    manifest = {
        "schema": "kaggriculture-v91-submission-v1",
        "model_id": "v91_permutation_invariant_labor_moe",
        "strategy_parent": None,
        "strength_comparator": "v76_adjacent_safe_buy_lead",
        "archive_sha256": sha256(ARCHIVE),
        "main_sha256": sha256(HERE / "main.py"),
        "ablation_main_sha256": sha256(HERE / "ablation_main.py"),
        "reference_episode_id": 100485613,
        "reference_replay_sha256": sha256(REPLAY),
        "complete_historical_agent_bundled": False,
        "engine": "1.32.7",
        "remote_submission": "NOT_AUTHORIZED_NOT_SUBMITTED",
    }
    (HERE / "submission_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

