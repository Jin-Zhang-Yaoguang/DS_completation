#!/usr/bin/env python3
"""Build V89 from a frozen multi-episode day-option training library."""

from __future__ import annotations

import base64
from collections import Counter
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
MODEL_DATA = PROJECT / "model_data"
REPORT_ROWS = MODEL_DATA / "v17_rc1_online_2026-08-27/report/top5_replication_per_game.jsonl"
REPLAY_DIR = MODEL_DATA / "v17_rc1_online_2026-08-27/top5_leaderboard_replays"
TEMPLATE = HERE / "main_template.py"
ARCHIVE = HERE / "submission.tar.gz"
TEAM = "lucaskna"
SUBMISSION_ID = 55803928
REFERENCE_EPISODE = 100485613
ASSETS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "GOOSE", "COW", "SHEEP", "PASTURE", "COOP", "WEED")


def sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def replay_path(episode_id: int):
    direct = REPLAY_DIR / f"episode-{episode_id}-replay.json"
    if direct.exists():
        return direct
    matches = sorted(MODEL_DATA.glob(f"kaggriculture_episodes_index/date=*/data/{episode_id}.json"))
    if not matches:
        raise FileNotFoundError(episode_id)
    return matches[-1]


def tile_counts(farm):
    counts = {key: 0 for key in ASSETS}
    for row in farm["tiles"]:
        for tile in row:
            if not isinstance(tile, dict):
                continue
            value = str(tile.get("crop") or tile.get("animal") or tile.get("kind") or "").upper()
            if value in counts:
                counts[value] += 1
    return counts


def feature(observation, seat):
    farm = observation["farms"][seat]
    private = observation["private"]
    return {
        "shops": [str(value) for value in observation["town"]["unlocked_shops"]],
        "money": int(farm["money"]),
        "quadrants": len(farm["unlocked_quadrants"]),
        "farmer": [int(farm["farmer"][0]), int(farm["farmer"][1])],
        "tiles": tile_counts(farm),
        "seeds": {key: int(value) for key, value in private["seeds"].items()},
        "shed": {key: int(value) for key, value in private["shed"].items()},
    }


def load_library():
    rows = [json.loads(line) for line in REPORT_ROWS.read_text(encoding="utf-8").splitlines() if line.strip()]
    selected = sorted(
        (row for row in rows if int(row.get("submission_id") or 0) == SUBMISSION_ID and row.get("result") == "W"),
        key=lambda row: int(row["episode_id"]),
    )
    cases, provenance = [], []
    for row in selected:
        episode_id = int(row["episode_id"])
        path = replay_path(episode_id)
        replay = json.loads(path.read_text(encoding="utf-8"))
        seat = replay["info"]["TeamNames"].index(TEAM)
        actions = [pair[seat].get("action") or {} for pair in replay["steps"][1:720]]
        days = [feature(replay["steps"][day * 24][seat]["observation"], seat) for day in range(30)]
        if len(actions) != 719 or len(days) != 30:
            raise RuntimeError(f"bad case {episode_id}")
        cases.append({"episode_id": episode_id, "actions": actions, "days": days})
        provenance.append({
            "episode_id": episode_id,
            "seed": int(row["seed"]),
            "seat": seat,
            "first_shop": row["first_shop"],
            "reward": float(row["reward"]),
            "margin": float(row["margin"]),
            "replay_sha256": sha256(path),
        })
    if len(cases) != 50 or REFERENCE_EPISODE not in {case["episode_id"] for case in cases}:
        raise RuntimeError("training case inventory mismatch")
    return {"reference_episode_id": REFERENCE_EPISODE, "cases": cases}, provenance


def render(library, mode):
    packed = base64.b85encode(zlib.compress(
        json.dumps(library, ensure_ascii=True, separators=(",", ":")).encode("utf-8"), 9
    )).decode("ascii")
    text = TEMPLATE.read_text(encoding="utf-8")
    text = text.replace("__LIBRARY_PAYLOAD__", packed).replace("__MODE__", mode)
    forbidden = ("importlib", "spec_from_file", "parent_agent", "_PARENT_AGENT", "load_parent", "v76.agent")
    hits = [token for token in forbidden if token in text]
    if hits:
        raise RuntimeError(f"complete-agent dependency tokens: {hits}")
    compile(text, f"v89-{mode}", "exec")
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
    library, provenance = load_library()
    (HERE / "main.py").write_text(render(library, "full"), encoding="utf-8")
    (HERE / "ablation_main.py").write_text(render(library, "ablation"), encoding="utf-8")
    write_archive(HERE / "main.py")
    payload = {
        "schema": "kaggriculture-v89-submission-v1",
        "model_id": "v89_day_level_case_retrieval_moe",
        "strategy_parent": None,
        "strength_comparator": "v76_adjacent_safe_buy_lead",
        "archive": ARCHIVE.name,
        "archive_sha256": sha256(ARCHIVE),
        "main_sha256": sha256(HERE / "main.py"),
        "ablation_main_sha256": sha256(HERE / "ablation_main.py"),
        "training_submission_id": SUBMISSION_ID,
        "training_case_count": len(provenance),
        "training_episode_ids": [row["episode_id"] for row in provenance],
        "training_first_shop_counts": dict(sorted(Counter(row["first_shop"] for row in provenance).items())),
        "training_provenance_sha256": hashlib.sha256(json.dumps(provenance, sort_keys=True).encode()).hexdigest(),
        "reference_episode_id": REFERENCE_EPISODE,
        "complete_historical_agent_bundled": False,
        "engine": "1.32.7",
        "remote_submission": "NOT_AUTHORIZED_NOT_SUBMITTED",
    }
    (HERE / "training_provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (HERE / "submission_manifest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

