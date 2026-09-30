#!/usr/bin/env python3
"""Compile a replay task graph into standalone V92 full/ablation submissions."""

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
PROJECT = HERE.parents[1]
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


def load_graph():
    replay = json.loads(REPLAY.read_text(encoding="utf-8"))
    seat = replay["info"]["TeamNames"].index(TEAM)
    frames = []
    for step in range(719):
        action = replay["steps"][step + 1][seat].get("action") or {}
        observation = replay["steps"][step][seat]["observation"]
        farm = observation["farms"][seat]
        frames.append({
            "farmer": action.get("farmer") or ["PASS"],
            "hands": action.get("hands") or [],
            "market": action.get("market") or [],
            "positions": [farm["farmer"], *farm["hands"]],
        })
    return {"frames": frames, "source_seat": seat}


def render(graph, mode):
    packed = base64.b85encode(zlib.compress(json.dumps(graph, separators=(",", ":")).encode(), 9)).decode("ascii")
    text = TEMPLATE.read_text(encoding="utf-8").replace("__GRAPH_PAYLOAD__", packed).replace("__MODE__", mode)
    forbidden = ("importlib", "spec_from_file", "parent_agent", "_PARENT_AGENT", "load_parent", "v76.agent")
    hits = [token for token in forbidden if token in text]
    if hits:
        raise RuntimeError(hits)
    compile(text, f"v92-{mode}", "exec")
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
    graph = load_graph()
    (HERE / "main.py").write_text(render(graph, "full"), encoding="utf-8")
    (HERE / "ablation_main.py").write_text(render(graph, "ablation"), encoding="utf-8")
    write_archive(HERE / "main.py")
    manifest = {
        "schema": "kaggriculture-v92-submission-v1",
        "model_id": "v92_event_option_resource_petri_moe",
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
