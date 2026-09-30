#!/usr/bin/env python3
"""Build a source-traceable inventory over fetched Kaggriculture online data."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
TEAM_ID = 16731605
TARGETS = {"v14": 55722630, "a2": 55713355, "v13c": 55719781}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def now_taipei() -> str:
    return datetime.now(ZoneInfo("Asia/Taipei")).isoformat()


def mean(values: list[float]) -> float | None:
    return statistics.fmean(values) if values else None


def replay_summary(path: Path, expected_episode_id: int) -> dict[str, Any]:
    try:
        payload = load_json(path)
        episode_id = int(payload.get("info", {}).get("EpisodeId"))
        statuses = list(payload.get("statuses") or [])
        rewards = [float(value) for value in payload.get("rewards") or []]
        return {
            "valid": episode_id == expected_episode_id,
            "episode_id": episode_id,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "steps": len(payload.get("steps") or []),
            "statuses": statuses,
            "rewards": rewards,
            "team_names": list(payload.get("info", {}).get("TeamNames") or []),
            "seed": payload.get("info", {}).get("seed"),
            "module_version": payload.get("module_version"),
            "schema_version": payload.get("schema_version"),
        }
    except Exception as exc:
        return {
            "valid": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "bytes": path.stat().st_size if path.exists() else None,
        }


def log_summary(path: Path) -> dict[str, Any]:
    try:
        payload = load_json(path)
        records = [record for turn in payload for record in (turn if isinstance(turn, list) else [turn])]
        stderr_nonempty = [record.get("stderr", "") for record in records if record.get("stderr")]
        stdout_nonempty = [record.get("stdout", "") for record in records if record.get("stdout")]
        durations = [float(record["duration"]) for record in records if record.get("duration") is not None]
        return {
            "valid": True,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "turns": len(payload),
            "records": len(records),
            "stderr_nonempty_records": len(stderr_nonempty),
            "stdout_nonempty_records": len(stdout_nonempty),
            "duration_max": max(durations) if durations else None,
            "duration_mean": mean(durations),
        }
    except Exception as exc:
        return {"valid": False, "error_type": type(exc).__name__, "error": str(exc)}


def load_leaderboard() -> tuple[dict[int, dict[str, Any]], dict[str, Any]]:
    snapshot = load_json(RAW / "snapshot" / "current_snapshot.json")
    rows: dict[int, dict[str, Any]] = {}
    path = RAW / "snapshot" / "kaggriculture_public_leaderboard.csv"
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            rows[int(row["TeamId"])] = {
                "rank": int(row["Rank"]),
                "rating": float(row["Score"]),
                "team_name": row["TeamName"],
                "last_submission_date": row["LastSubmissionDate"],
            }
    return rows, snapshot


def manifest_map(path: Path, index_fields: tuple[str, ...]) -> dict[tuple[Any, ...], dict[str, Any]]:
    if not path.exists():
        return {}
    payload = load_json(path)
    return {tuple(row[field] for field in index_fields): row for row in payload.get("results", [])}


def build_version(
    version: str,
    submission_id: int,
    leaderboard: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    root = RAW / version
    episodes = load_json(root / "episodes_full.json")
    replay_manifest = manifest_map(root / "replay_download_manifest.json", ("episode_id",))
    log_manifest = manifest_map(root / "agent_log_download_manifest.json", ("episode_id", "agent_index"))
    ids = [int(row["id"]) for row in episodes]
    duplicate_ids = sorted(key for key, count in Counter(ids).items() if count > 1)
    public_rows = [row for row in episodes if "PUBLIC" in row["type"]]
    validation_rows = [row for row in episodes if "VALIDATION" in row["type"]]
    completed_public = [row for row in public_rows if "COMPLETED" in row["state"]]

    details: list[dict[str, Any]] = []
    outcomes: Counter[str] = Counter()
    margins: list[float] = []
    seat_outcomes: dict[int, Counter[str]] = {0: Counter(), 1: Counter()}
    replay_valid = 0
    replay_done = 0
    replay_error = 0
    reward_mismatches = 0
    log_valid_by_role = Counter()
    log_nonempty_stderr_by_role = Counter()
    opponents = Counter()

    for row in completed_public:
        mine = next(agent for agent in row["agents"] if int(agent["submissionId"]) == submission_id)
        opponent = next(agent for agent in row["agents"] if int(agent["submissionId"]) != submission_id)
        margin = float(mine["reward"]) - float(opponent["reward"])
        outcome = "win" if margin > 0 else "loss" if margin < 0 else "tie"
        outcomes[outcome] += 1
        margins.append(margin)
        seat = int(mine["index"])
        seat_outcomes[seat][outcome] += 1
        opponents[(int(opponent["teamId"]), int(opponent["submissionId"]), opponent["teamName"])] += 1

        replay_path = root / "replays" / f"episode-{row['id']}-replay.json"
        replay = replay_summary(replay_path, int(row["id"])) if replay_path.exists() else {"valid": False, "missing": True}
        if replay.get("valid"):
            replay_valid += 1
            statuses = replay.get("statuses") or []
            replay_done += int(statuses == ["DONE", "DONE"])
            replay_error += int(any(status != "DONE" for status in statuses))
            api_rewards = [float(agent["reward"]) for agent in sorted(row["agents"], key=lambda value: value["index"])]
            reward_mismatches += int(replay.get("rewards") != api_rewards)

        logs: list[dict[str, Any]] = []
        for agent in row["agents"]:
            index = int(agent["index"])
            role = "ours" if int(agent["teamId"]) == TEAM_ID else "opponent"
            path = root / "agent_logs" / f"episode-{row['id']}-agent-{index}-logs.json"
            summary = log_summary(path) if path.exists() else {"valid": False, "missing": True}
            if summary.get("valid"):
                log_valid_by_role[role] += 1
                log_nonempty_stderr_by_role[role] += int(summary.get("stderr_nonempty_records", 0) > 0)
            summary.update(
                {
                    "agent_index": index,
                    "role": role,
                    "path": str(path) if path.exists() else None,
                    "download_manifest": log_manifest.get((int(row["id"]), index)),
                }
            )
            logs.append(summary)

        opponent_leaderboard = leaderboard.get(int(opponent["teamId"]))
        details.append(
            {
                "episode_id": int(row["id"]),
                "create_time": row["createTime"],
                "end_time": row["endTime"],
                "type": row["type"],
                "state": row["state"],
                "candidate": mine,
                "opponent": opponent,
                "candidate_seat": seat,
                "candidate_reward": float(mine["reward"]),
                "opponent_reward": float(opponent["reward"]),
                "margin": margin,
                "outcome": outcome,
                "opponent_current_leaderboard": opponent_leaderboard,
                "rating_availability": {
                    "pre_game": "not_exposed_by_episode/replay API",
                    "post_game": "not_exposed_by_episode/replay API",
                    "query_time_team_rating": "available" if opponent_leaderboard else "not_on_current_leaderboard",
                },
                "replay_path": str(replay_path) if replay_path.exists() else None,
                "replay": replay,
                "replay_download_manifest": replay_manifest.get((int(row["id"]),)),
                "agent_logs": logs,
            }
        )

    count = len(completed_public)
    return {
        "version": version,
        "submission_id": submission_id,
        "sources": {
            "episodes_full": str(root / "episodes_full.json"),
            "episodes_full_sha256": sha256(root / "episodes_full.json"),
            "episode_receipt": str(root / "episodes_fetch_receipt.json"),
            "replay_manifest": str(root / "replay_download_manifest.json") if (root / "replay_download_manifest.json").exists() else None,
            "agent_log_manifest": str(root / "agent_log_download_manifest.json") if (root / "agent_log_download_manifest.json").exists() else None,
        },
        "episode_counts": {
            "all": len(episodes),
            "public": len(public_rows),
            "validation": len(validation_rows),
            "completed_public": count,
            "state_counts": dict(Counter(row["state"] for row in episodes)),
            "type_counts": dict(Counter(row["type"] for row in episodes)),
            "duplicate_episode_ids": duplicate_ids,
        },
        "time_window": {
            "first_end_time": min((row["endTime"] for row in episodes), default=None),
            "last_end_time": max((row["endTime"] for row in episodes), default=None),
        },
        "public_outcomes": {
            "wins": outcomes["win"],
            "ties": outcomes["tie"],
            "losses": outcomes["loss"],
            "pure_win_rate": outcomes["win"] / count if count else None,
            "score_rate_w_plus_half_tie": (outcomes["win"] + 0.5 * outcomes["tie"]) / count if count else None,
            "mean_margin": mean(margins),
            "median_margin": statistics.median(margins) if margins else None,
            "margin_min": min(margins) if margins else None,
            "margin_max": max(margins) if margins else None,
            "by_candidate_seat": {str(seat): dict(counter) for seat, counter in seat_outcomes.items()},
        },
        "coverage_and_quality": {
            "expected_public_replays": count,
            "valid_public_replays": replay_valid,
            "missing_or_invalid_public_replays": count - replay_valid,
            "replays_done_done": replay_done,
            "replays_with_non_done_status": replay_error,
            "api_vs_replay_reward_mismatches": reward_mismatches,
            "valid_our_agent_logs": log_valid_by_role["ours"],
            "valid_opponent_agent_logs": log_valid_by_role["opponent"],
            "our_logs_with_nonempty_stderr": log_nonempty_stderr_by_role["ours"],
            "opponent_logs_with_nonempty_stderr": log_nonempty_stderr_by_role["opponent"],
        },
        "opponents": [
            {
                "team_id": key[0],
                "submission_id": key[1],
                "team_name": key[2],
                "games": games,
                "current_leaderboard": leaderboard.get(key[0]),
            }
            for key, games in opponents.most_common()
        ],
        "episodes": sorted(details, key=lambda item: (item["end_time"], item["episode_id"])),
    }


def markdown(payload: dict[str, Any]) -> str:
    snapshot = payload["current_snapshot"]
    lines = [
        "# V14 / A2 / V13C 线上数据清单",
        "",
        f"- 生成时间（Asia/Taipei）：`{payload['generated_at_taipei']}`",
        f"- 排名查询时间（Asia/Taipei）：`{snapshot['queried_at_taipei']}`",
        f"- 当前团队：rank **{snapshot['team']['rank']}**，rating **{snapshot['team']['rating']}**",
        f"- 当前 active latest-two：`{', '.join(str(row['id']) for row in snapshot['active_latest_two'])}`",
        "- pre/post-game Rating：Kaggle episode/replay API 未提供；逐局只记录查询时 leaderboard team rating，并明确标注其不是赛时 Rating。",
        "",
        "| 版本 | Submission | Public score | Active | Public episodes | W/T/L | 纯胜率 | Replay | 自方 logs | 对手 logs |",
        "|---|---:|---:|:---:|---:|---:|---:|---:|---:|---:|",
    ]
    for version in ("v14", "a2", "v13c"):
        row = payload["versions"][version]
        target = snapshot["targets"][version]
        outcomes = row["public_outcomes"]
        quality = row["coverage_and_quality"]
        lines.append(
            f"| {version} | {row['submission_id']} | {target['publicScore']:.1f} | "
            f"{'是' if target['is_active_latest_two'] else '否'} | {row['episode_counts']['public']} | "
            f"{outcomes['wins']}/{outcomes['ties']}/{outcomes['losses']} | {outcomes['pure_win_rate']:.2%} | "
            f"{quality['valid_public_replays']}/{quality['expected_public_replays']} | "
            f"{quality['valid_our_agent_logs']}/{quality['expected_public_replays']} | "
            f"{quality['valid_opponent_agent_logs']}/{quality['expected_public_replays']} |"
        )
    lines.extend(
        [
            "",
            "## 口径与缺失",
            "",
            "- Episode 总表保留 validation/public，胜负统计只使用 completed public。",
            "- 胜负由双方 reward 比较，margin = candidate reward - opponent reward；平局不算纯胜。",
            "- Replay 要求 EpisodeId 一致，并交叉核对双方 rewards 与 `[DONE, DONE]`。",
            "- 两个 seat 的 logs 都尝试下载；Kaggle 通常只授权本队 seat，对手日志的 403 会保留在 manifest，不能当作运行错误。",
            "- 逐局原始字段和覆盖状态位于 `data_inventory.json -> versions.<version>.episodes`。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    leaderboard, snapshot = load_leaderboard()
    versions = {
        version: build_version(version, submission_id, leaderboard)
        for version, submission_id in TARGETS.items()
    }
    all_episode_ids = [
        row["episode_id"]
        for version in versions.values()
        for row in version["episodes"]
    ]
    cross_duplicates = sorted(key for key, count in Counter(all_episode_ids).items() if count > 1)
    payload = {
        "schema": "kaggriculture-v14-online-data-inventory-v1",
        "generated_at_taipei": now_taipei(),
        "source_policy": "Kaggle CLI/API only; no browser",
        "current_snapshot": snapshot,
        "cross_version_duplicate_public_episode_ids": cross_duplicates,
        "versions": versions,
    }
    destination = HERE / "data_inventory.json"
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (HERE / "data_inventory.md").write_text(markdown(payload), encoding="utf-8")
    print(json.dumps({"inventory": str(destination), "sha256": sha256(destination)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
