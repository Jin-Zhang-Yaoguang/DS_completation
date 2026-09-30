#!/usr/bin/env python3
"""通过 Kaggle CLI 下载并校验 V120 小样本 Public Replay。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess


HERE = Path(__file__).resolve().parent
SOURCES = HERE / "pilot_sources.json"
RAW = HERE / "replay_data/raw"
RECEIPT = HERE / "replay_data/download_receipt.json"
KAGGLE = "/Users/a1-6/.local/bin/kaggle"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def validate(path: Path, episode: dict) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    episode_id = int(episode["episode_id"])
    if int(payload.get("info", {}).get("EpisodeId", -1)) != episode_id:
        raise ValueError(f"EpisodeId 不匹配: {path}")
    if len(payload.get("steps", [])) != 720:
        raise ValueError(f"不是 720 状态 Replay: {path}")
    teams = list(payload.get("info", {}).get("TeamNames", []))
    for teacher in episode["teachers"]:
        seat = int(teacher["seat"])
        if seat >= len(teams) or str(teams[seat]) != str(teacher["team"]):
            raise ValueError(f"teacher/seat 不匹配: {episode_id} {teacher} vs {teams}")
    return {
        "episode_id": episode_id,
        "path": str(path.resolve()),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "module_version": str(payload.get("module_version")),
        "seed": int(payload.get("info", {}).get("seed", -1)),
        "teams": teams,
        "teachers": episode["teachers"],
        "actual_date": episode["actual_date"],
    }


def resolve_existing(episode: dict) -> Path | None:
    if episode.get("local_path"):
        path = (HERE / episode["local_path"]).resolve()
        return path if path.is_file() else None
    episode_id = int(episode["episode_id"])
    candidates = sorted(RAW.glob(f"*{episode_id}*"))
    return candidates[0] if candidates else None


def main() -> int:
    config = json.loads(SOURCES.read_text(encoding="utf-8"))
    RAW.mkdir(parents=True, exist_ok=True)
    rows = []
    for episode in config["episodes"]:
        episode_id = int(episode["episode_id"])
        path = resolve_existing(episode)
        if path is None:
            result = subprocess.run(
                [KAGGLE, "competitions", "replay", str(episode_id), "-p", str(RAW)],
                text=True,
                capture_output=True,
                check=False,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Replay {episode_id} 下载失败: {result.stderr.strip()}")
            path = resolve_existing(episode)
            if path is None:
                raise FileNotFoundError(f"下载后未找到 Replay {episode_id}: {result.stdout}")
        row = validate(path, episode)
        rows.append(row)
        print(json.dumps({"episode_id": episode_id, "sha256": row["sha256"], "bytes": row["bytes"]}), flush=True)
    unique = {(row["episode_id"], row["sha256"]) for row in rows}
    receipt = {
        "schema": "kaggriculture-v120-replay-download-receipt-v1",
        "source": "Kaggle CLI public replay",
        "episodes": len(rows),
        "unique_episode_sha_pairs": len(unique),
        "teacher_trajectories": sum(len(row["teachers"]) for row in rows),
        "rows": rows,
    }
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in receipt.items() if key != "rows"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
