#!/usr/bin/env python3
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
REPLAY = PROJECT / "model_data/v17_rc1_online_2026-08-27/top5_leaderboard_replays/episode-100439801-replay.json"
TEMPLATE = HERE / "main_template.py"
ARCHIVE = HERE / "submission.tar.gz"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def target(observation, seat):
    farm = observation["farms"][seat]
    return {"positions": [farm["farmer"], *farm["hands"]]}


def payload():
    replay = json.loads(REPLAY.read_text())
    seat = replay["info"]["TeamNames"].index("lucaskna")
    return {
        "actions": [step[seat].get("action") or {} for step in replay["steps"][1:720]],
        "targets": [target(replay["steps"][step][seat]["observation"], seat) for step in range(719)],
    }


def render(data, mode):
    packed = base64.b85encode(zlib.compress(json.dumps(data, separators=(",", ":")).encode(), 9)).decode()
    text = TEMPLATE.read_text().replace("__PAYLOAD__", packed).replace("__MODE__", mode)
    compile(text, f"v106-{mode}", "exec")
    return text


def main():
    data = payload()
    for mode, name in (("full", "main.py"), ("ablation", "ablation_main.py")):
        (HERE / name).write_text(render(data, mode))
    with ARCHIVE.open("wb") as sink:
        with gzip.GzipFile(filename="", mode="wb", fileobj=sink, mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as archive:
                content = (HERE / "main.py").read_bytes()
                info = tarfile.TarInfo("main.py")
                info.size, info.mode, info.uid, info.gid, info.mtime = len(content), 0o644, 0, 0, 0
                info.uname = info.gname = ""
                archive.addfile(info, BytesIO(content))
    manifest = {
        "schema": "kaggriculture-v106-submission-v1",
        "model_id": "v106_conformal_support_option_moe",
        "strategy_parent": None,
        "strength_comparator": "v76_adjacent_safe_buy_lead",
        "archive_sha256": sha(ARCHIVE),
        "main_sha256": sha(HERE / "main.py"),
        "ablation_main_sha256": sha(HERE / "ablation_main.py"),
        "growth_expert_episode": 100439801,
        "growth_expert_replay_sha256": sha(REPLAY),
        "complete_historical_agent_bundled": False,
        "risk_checkpoint": 576,
        "risk_tree_rule": "public_money_gap<=-5129",
        "engine": "1.32.7",
        "remote_submission": "NOT_AUTHORIZED_NOT_SUBMITTED",
    }
    (HERE / "submission_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
