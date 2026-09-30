#!/usr/bin/env python3
"""固化当前 Top20，并构建不读取 Blind 内容的合规 Replay 清单。"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
INDEX = ROOT / "kaggle_Kaggriculture/model_data/kaggriculture_episodes_index"
RAW = HERE / "replay_data/own_online_raw"
KAGGLE = "/Users/a1-6/.local/bin/kaggle"
COMPETITION = "kaggriculture"
OWN_SUBMISSION = 55943570
ENGINE = "1.32.7"
TRAIN_DATES = tuple(f"2026-08-{day:02d}" for day in range(20, 29))
DEV_DATES = ("2026-08-29", "2026-08-30")
OFFICIAL_BLIND_DATES = ("2026-08-31",)


def run(command: list[str]) -> str:
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout).strip())
    return result.stdout or result.stderr


def json_prefix(text: str) -> Any:
    starts = [index for index in (text.find("["), text.find("{")) if index >= 0]
    if not starts:
        raise ValueError(f"CLI 输出不含 JSON: {text[:200]}")
    return json.JSONDecoder().raw_decode(text[min(starts):])[0]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def replay_header(path: Path) -> dict | None:
    prefix = path.open("rb").read(65536).decode("utf-8", "ignore")
    episode = re.search(r'"EpisodeId"\s*:\s*(\d+)', prefix)
    teams = re.search(r'"TeamNames"\s*:\s*(\[[^\]]*\])', prefix)
    version = re.search(r'"module_version"\s*:\s*"([^"]+)"', prefix)
    if not episode or not teams:
        return None
    return {
        "episode_id": int(episode.group(1)),
        "teams": list(json.loads(teams.group(1))),
        "module_version": version.group(1) if version else None,
        "path": str(path.resolve()),
    }


def leaderboard() -> list[dict]:
    payload = json_prefix(run([KAGGLE, "competitions", "leaderboard", COMPETITION, "--show", "--format", "json"]))
    return [
        {"rank": rank, "team_id": int(row["teamId"]), "team": str(row["teamName"]),
         "score": float(row["score"]), "submission_date": str(row["submissionDate"])}
        for rank, row in enumerate(payload[:20], 1)
    ]


def own_episode_metadata() -> list[dict]:
    payload = json_prefix(run([KAGGLE, "competitions", "episodes", str(OWN_SUBMISSION), "--format", "json"]))
    rows = [row for row in payload if str(row.get("state")) == "EpisodeState.COMPLETED" and str(row.get("type")) == "EpisodeType.EPISODE_TYPE_PUBLIC"]
    return sorted(rows, key=lambda row: str(row["createTime"]))


def existing_replay(episode_id: int) -> Path | None:
    matches = sorted(RAW.glob(f"*{episode_id}*"))
    return matches[0] if matches else None


def download_replay(episode_id: int) -> Path:
    RAW.mkdir(parents=True, exist_ok=True)
    current = existing_replay(episode_id)
    if current:
        return current
    run([KAGGLE, "competitions", "replay", str(episode_id), "-p", str(RAW)])
    current = existing_replay(episode_id)
    if not current:
        raise FileNotFoundError(f"Replay {episode_id} 下载后不存在")
    return current


def official_candidates(top_names: set[str], dates: tuple[str, ...], split: str, per_team: int) -> list[dict]:
    by_team: dict[str, list[dict]] = {team: [] for team in top_names}
    for day in dates:
        for path in (INDEX / f"date={day}" / "data").glob("*.json"):
            header = replay_header(path)
            if header is None:
                continue
            for team in top_names.intersection(header["teams"]):
                by_team[team].append({**header, "actual_date": day, "split": split, "source_panel": "official_daily_confirmation"})
    selected: dict[int, dict] = {}
    for team, rows in by_team.items():
        for row in sorted(rows, key=lambda value: value["episode_id"], reverse=True)[:per_team]:
            selected.setdefault(row["episode_id"], row)
    return list(selected.values())


def validate_full(row: dict, top: dict[str, dict]) -> dict:
    path = Path(row["path"])
    payload = json.loads(path.read_text(encoding="utf-8"))
    info = dict(payload.get("info") or {})
    if int(info.get("EpisodeId", -1)) != int(row["episode_id"]) or len(payload.get("steps") or []) != 720:
        raise ValueError(f"Replay 结构错误: {path}")
    version = str(payload.get("module_version"))
    if version != ENGINE:
        raise ValueError(f"规则版本错误: {path} {version}")
    teams = list(info.get("TeamNames") or [])
    teachers = [
        {"team": team, "seat": seat, "leaderboard_rank": top[team]["rank"], "leaderboard_score": top[team]["score"], "team_id": top[team]["team_id"]}
        for seat, team in enumerate(teams) if team in top
    ]
    return {
        **row, "path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": sha256(path),
        "module_version": version, "seed": int(info.get("seed", -1)), "teams": teams,
        "teachers": teachers,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--official-train-per-team", type=int, default=12)
    parser.add_argument("--official-dev-per-team", type=int, default=4)
    args = parser.parse_args()
    leaders = leaderboard()
    top = {row["team"]: row for row in leaders}
    snapshot = {
        "schema": "kaggriculture-v122-top20-snapshot-v1", "fetched_at": datetime.now(timezone.utc).isoformat(),
        "competition": COMPETITION, "rows": leaders,
    }
    (HERE / "top20_snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    metadata = own_episode_metadata()
    n = len(metadata)
    blind_n = max(1, n // 5)
    dev_n = max(1, (n - blind_n) // 4)
    usable, blind = metadata[:-blind_n], metadata[-blind_n:]
    own_split = {}
    for index, row in enumerate(usable):
        own_split[int(row["id"])] = "train" if index < len(usable) - dev_n else "dev"
    print(json.dumps({"own_public": n, "own_train": sum(v == "train" for v in own_split.values()), "own_dev": sum(v == "dev" for v in own_split.values()), "own_blind_reserved_not_downloaded": len(blind)}, ensure_ascii=False), flush=True)
    downloaded: dict[int, Path] = {}
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(download_replay, int(row["id"])): int(row["id"]) for row in usable}
        for future in as_completed(futures):
            episode_id = futures[future]
            downloaded[episode_id] = future.result()
            if len(downloaded) % 16 == 0:
                print(json.dumps({"downloaded": len(downloaded), "total": len(usable)}, ensure_ascii=False), flush=True)
    own_rows = []
    meta_by_id = {int(row["id"]): row for row in usable}
    for episode_id, path in downloaded.items():
        header = replay_header(path)
        if header is None:
            continue
        own_rows.append({
            **header, "path": str(path.resolve()), "actual_date": str(meta_by_id[episode_id]["createTime"])[:10],
            "create_time": str(meta_by_id[episode_id]["createTime"]), "split": own_split[episode_id],
            "source_panel": "own_online_primary", "own_submission_id": OWN_SUBMISSION,
        })

    candidates = own_rows
    candidates += official_candidates(set(top), TRAIN_DATES, "train", args.official_train_per_team)
    candidates += official_candidates(set(top), DEV_DATES, "dev", args.official_dev_per_team)
    unique: dict[tuple[int, str], dict] = {}
    rows = []
    for candidate in candidates:
        validated = validate_full(candidate, top)
        if not validated["teachers"]:
            continue
        key = (validated["episode_id"], validated["sha256"])
        if key in unique:
            continue
        unique[key] = validated
        rows.append(validated)
    rows.sort(key=lambda row: (row["split"], row["actual_date"], row["episode_id"]))
    receipt = {
        "schema": "kaggriculture-v122-top20-replay-receipt-v1", "engine": ENGINE,
        "top20_snapshot": str((HERE / "top20_snapshot.json").resolve()),
        "official_blind_dates_reserved_not_read": list(OFFICIAL_BLIND_DATES),
        "own_blind_episode_metadata": [{"episode_id": int(row["id"]), "create_time": row["createTime"]} for row in blind],
        "dedup_key": "episode_id+replay_sha256", "rows": rows,
    }
    (HERE / "replay_data").mkdir(parents=True, exist_ok=True)
    (HERE / "replay_data/receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    coverage = {team: {split: sum(any(t["team"] == team for t in row["teachers"]) and row["split"] == split for row in rows) for split in ("train", "dev")} for team in top}
    summary = {"episodes": len(rows), "train": sum(row["split"] == "train" for row in rows), "dev": sum(row["split"] == "dev" for row in rows), "teacher_trajectories": sum(len(row["teachers"]) for row in rows), "top20_with_train": sum(value["train"] > 0 for value in coverage.values()), "top20_with_dev": sum(value["dev"] > 0 for value in coverage.values()), "coverage": coverage}
    (HERE / "replay_data/summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
