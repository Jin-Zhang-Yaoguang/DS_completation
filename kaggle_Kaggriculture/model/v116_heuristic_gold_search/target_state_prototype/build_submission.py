#!/usr/bin/env python3
"""Build the standalone V116 target-state heuristic agent.

Only observable states are extracted from the public replay.  The replay's
``action`` fields are deliberately never read and cannot enter the package.
"""

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
MODEL = HERE.parents[1]
ROOT = MODEL.parents[1]
REPLAY = ROOT / "kaggle_Kaggriculture/model_data/v17_rc1_online_2026-08-27/top5_leaderboard_replays/episode-100485613-replay.json"
TEMPLATE = HERE / "main_template.py"
MAIN = HERE / "main.py"
ARCHIVE = HERE / "submission.tar.gz"
TEAM = "lucaskna"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def daily_target(observations: list[dict], seat: int, day: int) -> dict:
    """Reduce one day to aggregate assets, topology and capacity only."""
    farms = [observation["farms"][seat] for observation in observations]
    final_farm = farms[-1]
    final_private = observations[-1]["private"]
    topology = {"PLANT": 0, "PASTURE": 0, "COOP": 0, "WEED": 0}
    crops = {name: 0 for name in ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")}
    animals = {name: 0 for name in ("GOOSE", "COW", "SHEEP")}
    yield_capacity = {name: 0 for name in (*crops, "EGG", "MILK", "WOOL", "FERTILIZER")}
    for row in final_farm["tiles"]:
        for tile in row:
            if not isinstance(tile, dict):
                continue
            kind = str(tile.get("kind", ""))
            if kind in topology:
                topology[kind] += 1
            crop = tile.get("crop")
            animal = tile.get("animal")
            if crop in crops:
                crops[crop] += 1
                yield_capacity[crop] += int(tile.get("yield_units", 0) or 0)
            if animal in animals:
                animals[animal] += 1
                product = {"GOOSE": "EGG", "COW": "MILK", "SHEEP": "WOOL"}[animal]
                yield_capacity[product] += int(tile.get("yield_units", 0) or 0)
                yield_capacity["FERTILIZER"] += int(bool(tile.get("fertilizer_available")))
    return {
        "day": day,
        "max_hands": max(len(farm["hands"]) for farm in farms),
        "quadrants": len(final_farm["unlocked_quadrants"]),
        "topology": topology,
        "crops": crops,
        "animals": animals,
        "seeds": {key: int(value) for key, value in final_private["seeds"].items()},
        "shed": {key: int(value) for key, value in final_private["shed"].items()},
        "yield_capacity": yield_capacity,
    }


def load_targets() -> dict:
    replay = json.loads(REPLAY.read_text(encoding="utf-8"))
    seat = replay["info"]["TeamNames"].index(TEAM)
    # Intentionally access observations only.  There is no action extraction.
    targets = []
    for day in range(30):
        observations = [
            replay["steps"][step][seat]["observation"]
            for step in range(day * 24, min(719, (day + 1) * 24))
        ]
        targets.append(daily_target(observations, seat, day))
    if len(targets) > 31:
        raise RuntimeError("daily aggregate protocol permits at most 31 targets")
    return {"targets": targets, "source_seat": seat}


def render(reference: dict) -> str:
    packed = base64.b85encode(zlib.compress(
        json.dumps(reference, ensure_ascii=True, separators=(",", ":")).encode("utf-8"), 9
    )).decode("ascii")
    text = TEMPLATE.read_text(encoding="utf-8").replace("__TARGET_STATE_PAYLOAD__", packed)
    forbidden = (
        "_ACTIONS", "reference_actions", "copy_action", "importlib", "spec_from_file",
        "parent_agent", "load_parent", "v76.agent",
    )
    hits = [token for token in forbidden if token in text]
    if hits:
        raise RuntimeError(f"forbidden embedded-agent/action tokens: {hits}")
    compile(text, "v116-target-state-prototype", "exec")
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
    reference = load_targets()
    MAIN.write_text(render(reference), encoding="utf-8")
    write_archive(MAIN)
    manifest = {
        "schema": "kaggriculture-v116-target-state-heuristic-v1",
        "model_id": "v116_target_state_heuristic_moe_prototype",
        "strategy_parent": None,
        "strength_comparator": "v76_adjacent_safe_buy_lead",
        "teacher_representation": "daily_aggregate_assets_topology_capacity_only",
        "embedded_replay_actions": False,
        "target_count": len(reference["targets"]),
        "production_experts": ["balanced", "wool", "dairy", "orchard"],
        "replay": {
            "episode_id": 100485613,
            "team": TEAM,
            "seat": reference["source_seat"],
            "sha256": sha256(REPLAY),
        },
        "main_sha256": sha256(MAIN),
        "archive_sha256": sha256(ARCHIVE),
        "remote_submission": "NOT_AUTHORIZED_NOT_SUBMITTED",
    }
    (HERE / "submission_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
