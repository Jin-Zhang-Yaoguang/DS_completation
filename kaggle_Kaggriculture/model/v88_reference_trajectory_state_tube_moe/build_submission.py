#!/usr/bin/env python3
"""Build standalone V88 full/ablation sources and deterministic archive."""

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
ROOT = MODEL.parents[1]
REPLAY = ROOT / "kaggle_Kaggriculture/model_data/v17_rc1_online_2026-08-27/top5_leaderboard_replays/episode-100485613-replay.json"
TEMPLATE = HERE / "main_template.py"
ARCHIVE = HERE / "submission.tar.gz"
TEAM = "lucaskna"
SUBMISSION_ID = 55803928


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def target(observation: dict, seat: int) -> dict:
    farm = observation["farms"][seat]
    private = observation["private"]
    return {
        "money": int(farm["money"]),
        "hands": len(farm["hands"]),
        "quadrants": len(farm["unlocked_quadrants"]),
        "positions": [farm["farmer"], *farm["hands"]],
        "seeds": {key: int(value) for key, value in private["seeds"].items()},
        "shed": {key: int(value) for key, value in private["shed"].items()},
    }


def load_reference() -> dict:
    replay = json.loads(REPLAY.read_text(encoding="utf-8"))
    seat = replay["info"]["TeamNames"].index(TEAM)
    actions = [pair[seat].get("action") or {} for pair in replay["steps"][1:720]]
    targets = [target(replay["steps"][step][seat]["observation"], seat) for step in range(719)]
    if len(actions) != 719 or len(targets) != 719:
        raise RuntimeError("reference length mismatch")
    return {"actions": actions, "targets": targets, "source_seat": seat}


def render(reference: dict, mode: str) -> str:
    packed = base64.b85encode(zlib.compress(
        json.dumps(reference, ensure_ascii=True, separators=(",", ":")).encode("utf-8"), 9
    )).decode("ascii")
    text = TEMPLATE.read_text(encoding="utf-8")
    text = text.replace("__REFERENCE_PAYLOAD__", packed).replace("__MODE__", mode)
    forbidden = ("importlib", "spec_from_file", "parent_agent", "_PARENT_AGENT", "load_parent", "v76.agent")
    hits = [token for token in forbidden if token in text]
    if hits:
        raise RuntimeError(f"complete-agent dependency tokens: {hits}")
    compile(text, f"v88-{mode}", "exec")
    return text


def write_archive(source: Path) -> None:
    with ARCHIVE.open("wb") as sink:
        with gzip.GzipFile(filename="", mode="wb", fileobj=sink, mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as archive:
                data = source.read_bytes()
                info = tarfile.TarInfo("main.py")
                info.size, info.mode, info.uid, info.gid, info.mtime = len(data), 0o644, 0, 0, 0
                info.uname = info.gname = ""
                archive.addfile(info, BytesIO(data))


def main() -> None:
    reference = load_reference()
    (HERE / "main.py").write_text(render(reference, "full"), encoding="utf-8")
    (HERE / "ablation_main.py").write_text(render(reference, "ablation"), encoding="utf-8")
    write_archive(HERE / "main.py")
    payload = {
        "schema": "kaggriculture-v88-submission-v1",
        "model_id": "v88_reference_trajectory_state_tube_moe",
        "strategy_parent": None,
        "strength_comparator": "v76_adjacent_safe_buy_lead",
        "archive": ARCHIVE.name,
        "archive_sha256": sha256(ARCHIVE),
        "main_sha256": sha256(HERE / "main.py"),
        "ablation_main_sha256": sha256(HERE / "ablation_main.py"),
        "reference": {
            "team": TEAM,
            "submission_id": SUBMISSION_ID,
            "episode_id": 100485613,
            "seat": reference["source_seat"],
            "replay_sha256": sha256(REPLAY),
        },
        "complete_historical_agent_bundled": False,
        "engine": "1.32.7",
        "remote_submission": "NOT_AUTHORIZED_NOT_SUBMITTED"
    }
    (HERE / "submission_manifest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

