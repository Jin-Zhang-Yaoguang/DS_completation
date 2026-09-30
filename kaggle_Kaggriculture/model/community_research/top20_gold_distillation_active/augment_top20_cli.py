#!/usr/bin/env python3
"""用 Kaggle 官方 CLI/SDK 获取 Top20 当前提交的训练 Replay。"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess

from kaggle.api.kaggle_api_extended import KaggleApi
from kagglesdk.competitions.types.competition_api_service import ApiListTeamPublicSubmissionsRequest


HERE = Path(__file__).resolve().parent
RAW = HERE / "replay_data/top20_cli_raw"
SNAPSHOT = HERE / "top20_snapshot.json"
OUT = HERE / "replay_data/top20_cli_receipt.json"
KAGGLE = "/Users/a1-6/.local/bin/kaggle"
ENGINE = "1.32.7"


def run(command: list[str]) -> str:
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout).strip())
    return result.stdout or result.stderr


def json_prefix(text: str):
    starts = [value for value in (text.find("["), text.find("{")) if value >= 0]
    return json.JSONDecoder().raw_decode(text[min(starts):])[0]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def current_submission(team_id: int, score: float) -> dict:
    api = KaggleApi()
    api.authenticate()
    request = ApiListTeamPublicSubmissionsRequest()
    request.team_id = team_id
    with api.build_kaggle_client() as client:
        response = client.competitions.competition_api_client.list_team_public_submissions(request)
    rows = [row.to_dict() for row in list(response.submissions or [])]
    if not rows:
        raise ValueError(f"team_id={team_id} 没有公开提交")
    return min(rows, key=lambda row: (abs(float(row.get("publicScore") or -1) - score), -int(row["id"])))


def episodes(submission_id: int) -> list[dict]:
    rows = json_prefix(run([KAGGLE, "competitions", "episodes", str(submission_id), "--format", "json"]))
    return sorted(
        [row for row in rows if str(row.get("state")) == "EpisodeState.COMPLETED" and str(row.get("type")) == "EpisodeType.EPISODE_TYPE_PUBLIC"],
        key=lambda row: str(row["createTime"]),
    )


def existing(episode_id: int) -> Path | None:
    matches = sorted(RAW.glob(f"*{episode_id}*"))
    return matches[0] if matches else None


def download(episode_id: int) -> Path:
    RAW.mkdir(parents=True, exist_ok=True)
    path = existing(episode_id)
    if path:
        return path
    run([KAGGLE, "competitions", "replay", str(episode_id), "-p", str(RAW)])
    path = existing(episode_id)
    if not path:
        raise FileNotFoundError(episode_id)
    return path


def select(rows: list[dict], train_n: int, dev_n: int, blind_n: int) -> tuple[list[dict], list[dict]]:
    blind = rows[-blind_n:] if blind_n else []
    usable = rows[:-blind_n] if blind_n else rows
    dev = usable[-dev_n:] if dev_n else []
    train_pool = usable[:-dev_n] if dev_n else usable
    train = train_pool[-train_n:]
    return ([{**row, "split": "train"} for row in train] + [{**row, "split": "dev"} for row in dev], blind)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-per-team", type=int, default=12)
    parser.add_argument("--dev-per-team", type=int, default=4)
    parser.add_argument("--blind-per-team", type=int, default=4)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    leaders = json.loads(SNAPSHOT.read_text(encoding="utf-8"))["rows"]
    selected_rows, blind_rows, submissions = [], [], []
    for leader in leaders:
        submission = current_submission(int(leader["team_id"]), float(leader["score"]))
        submission_id = int(submission["id"])
        eps = episodes(submission_id)
        chosen, blind = select(eps, args.train_per_team, args.dev_per_team, args.blind_per_team)
        submissions.append({**leader, "submission_id": submission_id, "public_score": float(submission.get("publicScore") or 0), "public_episodes": len(eps)})
        selected_rows.extend([{**row, "teacher": leader["team"], "submission_id": submission_id, "team_id": leader["team_id"], "leaderboard_rank": leader["rank"], "leaderboard_score": leader["score"]} for row in chosen])
        blind_rows.extend([{"episode_id": int(row["id"]), "create_time": row["createTime"], "teacher": leader["team"], "submission_id": submission_id} for row in blind])
        print(json.dumps({"team": leader["team"], "submission_id": submission_id, "episodes": len(eps), "selected": len(chosen), "blind_reserved": len(blind)}, ensure_ascii=False), flush=True)

    unique_requests = {int(row["id"]): row for row in selected_rows}
    paths: dict[int, Path] = {}
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(download, episode_id): episode_id for episode_id in unique_requests}
        for future in as_completed(futures):
            episode_id = futures[future]
            paths[episode_id] = future.result()
            if len(paths) % 20 == 0:
                print(json.dumps({"downloaded": len(paths), "total": len(unique_requests)}, ensure_ascii=False), flush=True)

    rows = []
    for request in selected_rows:
        episode_id = int(request["id"])
        path = paths[episode_id]
        payload = json.loads(path.read_text(encoding="utf-8"))
        info = dict(payload.get("info") or {})
        teams = list(info.get("TeamNames") or [])
        if int(info.get("EpisodeId", -1)) != episode_id or len(payload.get("steps") or []) != 720:
            raise ValueError(f"Replay 结构错误: {episode_id}")
        if str(payload.get("module_version")) != ENGINE:
            raise ValueError(f"Replay 规则版本错误: {episode_id} {payload.get('module_version')}")
        if request["teacher"] not in teams:
            raise ValueError(f"教师身份错误: {episode_id} {request['teacher']} {teams}")
        actual_date = str(request["createTime"])[:10]
        if datetime.fromisoformat(actual_date).date() < datetime.fromisoformat("2026-08-20").date():
            raise ValueError(f"Replay 日期过旧: {episode_id} {actual_date}")
        rows.append({
            "episode_id": episode_id, "actual_date": actual_date, "create_time": request["createTime"],
            "split": request["split"], "source_panel": "top20_cli_training_auxiliary",
            "path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": sha256(path),
            "module_version": ENGINE, "seed": int(info.get("seed", -1)), "teams": teams,
            "teachers": [{"team": request["teacher"], "seat": teams.index(request["teacher"]), "submission_id": request["submission_id"], "team_id": request["team_id"], "leaderboard_rank": request["leaderboard_rank"], "leaderboard_score": request["leaderboard_score"]}],
        })
    # 同一教师/episode 只留一份；不同 Top20 同场时允许两条教师轨迹共享 Replay。
    unique = {}
    for row in rows:
        teacher = row["teachers"][0]["team"]
        unique[(row["episode_id"], row["sha256"], teacher)] = row
    rows = sorted(unique.values(), key=lambda row: (row["split"], row["actual_date"], row["episode_id"], row["teachers"][0]["team"]))
    report = {
        "schema": "kaggriculture-v122-top20-cli-training-receipt-v1", "engine": ENGINE,
        "role": "TRAINING_AUXILIARY_NOT_PROMOTION_EVIDENCE", "submissions": submissions,
        "blind_episode_metadata_only_not_downloaded": blind_rows, "rows": rows,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    coverage = {leader["team"]: {split: sum(row["teachers"][0]["team"] == leader["team"] and row["split"] == split for row in rows) for split in ("train", "dev")} for leader in leaders}
    summary = {"replays": len({(row["episode_id"], row["sha256"]) for row in rows}), "teacher_trajectories": len(rows), "train": sum(row["split"] == "train" for row in rows), "dev": sum(row["split"] == "dev" for row in rows), "top20_train_coverage": sum(value["train"] > 0 for value in coverage.values()), "top20_dev_coverage": sum(value["dev"] > 0 for value in coverage.values()), "coverage": coverage}
    (HERE / "replay_data/top20_cli_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
