#!/usr/bin/env python3
"""Fetch auditable Kaggriculture online evidence through the official API/CLI.

This script is deliberately resumable: completed replay/log files are validated
and skipped, while downloads are staged in per-episode temporary directories and
atomically moved into the evidence tree.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import threading
import zipfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from kaggle.api.kaggle_api_extended import KaggleApi


HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
TEAM_ID = 16731605
TEAM_NAME = "datatuu"
COMPETITION = "kaggriculture"
TARGETS = {
    "v14": 55722630,
    "a2": 55713355,
    "v13c": 55719781,
}
_PRINT_LOCK = threading.Lock()
_API_LOCAL = threading.local()


def iso_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def iso_taipei() -> str:
    return datetime.now(ZoneInfo("Asia/Taipei")).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def kaggle_api() -> KaggleApi:
    """Authenticate once per worker thread instead of once per episode."""
    api = getattr(_API_LOCAL, "api", None)
    if api is None:
        api = KaggleApi()
        api.authenticate()
        _API_LOCAL.api = api
    return api


def run_cli(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["kaggle", *args],
        cwd=cwd or HERE,
        text=True,
        capture_output=True,
        check=False,
    )


def enum_name(value: Any) -> str:
    text = str(value)
    return text.rsplit(".", 1)[-1]


def serialize_episode(row: Any) -> dict[str, Any]:
    agents = []
    for agent in row.agents or []:
        agents.append(
            {
                "submissionId": int(agent.submission_id),
                "index": int(agent.index or 0),
                "reward": None if agent.reward is None else float(agent.reward),
                "state": enum_name(agent.state),
                "teamName": str(agent.team_name),
                "teamId": int(agent.team_id),
            }
        )
    return {
        "id": int(row.id),
        "createTime": str(row.create_time),
        "endTime": str(row.end_time),
        "state": enum_name(row.state),
        "type": enum_name(row.type),
        "agents": sorted(agents, key=lambda item: item["index"]),
    }


def fetch_episodes() -> dict[str, list[dict[str, Any]]]:
    api = kaggle_api()
    all_rows: dict[str, list[dict[str, Any]]] = {}
    for version, submission_id in TARGETS.items():
        target = RAW / version
        target.mkdir(parents=True, exist_ok=True)
        rows = [serialize_episode(row) for row in api.competition_list_episodes(submission_id)]
        rows.sort(key=lambda item: (item.get("endTime") or "", item["id"]))
        write_json(target / "episodes_full.json", rows)
        # Retain the CLI's public-safe rendering as a second, independently callable source.
        result = run_cli(
            ["competitions", "episodes", str(submission_id), "--format", "json", "--quiet"]
        )
        (target / "episodes_cli.stdout").write_text(result.stdout, encoding="utf-8")
        (target / "episodes_cli.stderr").write_text(result.stderr, encoding="utf-8")
        write_json(
            target / "episodes_fetch_receipt.json",
            {
                "submission_id": submission_id,
                "fetched_at_utc": iso_utc(),
                "fetched_at_taipei": iso_taipei(),
                "official_sdk_count": len(rows),
                "cli_returncode": result.returncode,
                "source": "Kaggle official API competition_list_episodes and Kaggle CLI episodes",
                "sort": ["endTime", "id"],
                "episodes_full_sha256": sha256(target / "episodes_full.json"),
            },
        )
        all_rows[version] = rows
        with _PRINT_LOCK:
            print(
                json.dumps(
                    {
                        "phase": "episodes",
                        "version": version,
                        "submission_id": submission_id,
                        "count": len(rows),
                        "public": sum("PUBLIC" in row["type"] for row in rows),
                        "validation": sum("VALIDATION" in row["type"] for row in rows),
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
    return all_rows


def valid_replay(path: Path, episode_id: int) -> bool:
    if not path.exists() or path.stat().st_size < 1000:
        return False
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        # Replay ``id`` is an environment UUID; the Kaggle episode id lives in info.
        replay_episode_id = payload.get("info", {}).get("EpisodeId")
        return int(replay_episode_id) == episode_id
    except (OSError, ValueError, TypeError):
        return False


def download_replay(version: str, row: dict[str, Any]) -> dict[str, Any]:
    episode_id = row["id"]
    destination = RAW / version / "replays" / f"episode-{episode_id}-replay.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if valid_replay(destination, episode_id):
        return {
            "episode_id": episode_id,
            "kind": "replay",
            "status": "exists",
            "path": str(destination),
            "bytes": destination.stat().st_size,
            "sha256": sha256(destination),
        }
    if destination.exists():
        destination.rename(destination.with_suffix(destination.suffix + f".invalid-{int(datetime.now().timestamp())}"))
    temp_dir = Path(tempfile.mkdtemp(prefix=f"episode-{episode_id}-", dir=destination.parent))
    try:
        api = kaggle_api()
        api.competition_episode_replay(episode_id, str(temp_dir), quiet=True)
        produced = temp_dir / destination.name
        if not valid_replay(produced, episode_id):
            raise ValueError("downloaded replay failed JSON/id validation")
        os.replace(produced, destination)
        return {
            "episode_id": episode_id,
            "kind": "replay",
            "status": "downloaded",
            "path": str(destination),
            "bytes": destination.stat().st_size,
            "sha256": sha256(destination),
        }
    except Exception as exc:  # network/API failures are retained in the manifest
        return {
            "episode_id": episode_id,
            "kind": "replay",
            "status": "error",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def fetch_replays(all_rows: dict[str, list[dict[str, Any]]], workers: int) -> None:
    for version, rows in all_rows.items():
        public_rows = [row for row in rows if "PUBLIC" in row["type"] and "COMPLETED" in row["state"]]
        results: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(download_replay, version, row): row["id"] for row in public_rows}
            for number, future in enumerate(as_completed(futures), 1):
                item = future.result()
                results.append(item)
                with _PRINT_LOCK:
                    print(
                        json.dumps(
                            {
                                "phase": "replay",
                                "version": version,
                                "progress": f"{number}/{len(public_rows)}",
                                "episode_id": item["episode_id"],
                                "status": item["status"],
                            }
                        ),
                        flush=True,
                    )
        write_json(
            RAW / version / "replay_download_manifest.json",
            {
                "fetched_at_utc": iso_utc(),
                "fetched_at_taipei": iso_taipei(),
                "submission_id": TARGETS[version],
                "scope": "completed public episodes only",
                "results": sorted(results, key=lambda item: item["episode_id"]),
            },
        )


def valid_log(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        with path.open("r", encoding="utf-8") as handle:
            json.load(handle)
        return True
    except (OSError, ValueError):
        return False


def download_log(version: str, episode_id: int, agent_index: int) -> dict[str, Any]:
    destination = RAW / version / "agent_logs" / f"episode-{episode_id}-agent-{agent_index}-logs.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if valid_log(destination):
        return {
            "episode_id": episode_id,
            "agent_index": agent_index,
            "kind": "agent_log",
            "status": "exists",
            "path": str(destination),
            "bytes": destination.stat().st_size,
            "sha256": sha256(destination),
        }
    temp_dir = Path(tempfile.mkdtemp(prefix=f"episode-{episode_id}-agent-{agent_index}-", dir=destination.parent))
    try:
        api = kaggle_api()
        api.competition_episode_agent_logs(episode_id, agent_index, str(temp_dir), quiet=True)
        produced = list(temp_dir.glob("*.json"))
        if not produced:
            raise ValueError("agent log API returned no JSON file")
        source = max(produced, key=lambda path: path.stat().st_size)
        if not valid_log(source):
            raise ValueError("downloaded agent log is not valid JSON")
        os.replace(source, destination)
        return {
            "episode_id": episode_id,
            "agent_index": agent_index,
            "kind": "agent_log",
            "status": "downloaded",
            "path": str(destination),
            "bytes": destination.stat().st_size,
            "sha256": sha256(destination),
        }
    except Exception as exc:
        error = str(exc)
        return {
            "episode_id": episode_id,
            "agent_index": agent_index,
            "kind": "agent_log",
            "status": "forbidden" if "403" in error or "Forbidden" in error else "error",
            "error_type": type(exc).__name__,
            "error": error,
        }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def fetch_logs(all_rows: dict[str, list[dict[str, Any]]], workers: int) -> None:
    for version, rows in all_rows.items():
        public_rows = [row for row in rows if "PUBLIC" in row["type"] and "COMPLETED" in row["state"]]
        tasks = [(row["id"], agent["index"]) for row in public_rows for agent in row["agents"]]
        results: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(download_log, version, episode_id, index): (episode_id, index) for episode_id, index in tasks}
            for number, future in enumerate(as_completed(futures), 1):
                item = future.result()
                results.append(item)
                if number % 20 == 0 or number == len(tasks):
                    with _PRINT_LOCK:
                        print(
                            json.dumps(
                                {
                                    "phase": "logs",
                                    "version": version,
                                    "progress": f"{number}/{len(tasks)}",
                                    "status_counts": dict(Counter(row["status"] for row in results)),
                                }
                            ),
                            flush=True,
                        )
        write_json(
            RAW / version / "agent_log_download_manifest.json",
            {
                "fetched_at_utc": iso_utc(),
                "fetched_at_taipei": iso_taipei(),
                "submission_id": TARGETS[version],
                "scope": "both seats of every completed public episode; Kaggle authorization may restrict opponent logs",
                "results": sorted(results, key=lambda item: (item["episode_id"], item["agent_index"])),
            },
        )


def parse_cli_json(text: str) -> Any:
    begin = text.find("[")
    end = text.rfind("]")
    if begin < 0 or end < begin:
        raise ValueError("CLI output contains no JSON array")
    return json.loads(text[begin : end + 1])


def fetch_snapshot() -> dict[str, Any]:
    snapshot_dir = RAW / "snapshot"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    submissions_result = run_cli(
        ["competitions", "submissions", COMPETITION, "--format", "json", "--page-size", "200", "--quiet"]
    )
    team_result = run_cli(
        ["competitions", "team-submissions", str(TEAM_ID), "--format", "json", "--quiet"]
    )
    submissions = parse_cli_json(submissions_result.stdout)
    team_submissions = parse_cli_json(team_result.stdout)
    write_json(snapshot_dir / "our_submissions.json", submissions)
    write_json(snapshot_dir / "active_team_submissions.json", team_submissions)

    leaderboard_temp = Path(tempfile.mkdtemp(prefix="leaderboard-", dir=snapshot_dir))
    try:
        result = run_cli(
            ["competitions", "leaderboard", COMPETITION, "--download", "--path", str(leaderboard_temp), "--quiet"]
        )
        if result.returncode:
            raise RuntimeError((result.stderr or result.stdout).strip())
        archive = next(leaderboard_temp.glob("*.zip"))
        archive_destination = snapshot_dir / "kaggriculture_leaderboard.zip"
        os.replace(archive, archive_destination)
        with zipfile.ZipFile(archive_destination) as handle:
            member = handle.namelist()[0]
            csv_destination = snapshot_dir / "kaggriculture_public_leaderboard.csv"
            with handle.open(member) as source, csv_destination.open("wb") as target:
                shutil.copyfileobj(source, target)
    finally:
        shutil.rmtree(leaderboard_temp, ignore_errors=True)

    with (snapshot_dir / "kaggriculture_public_leaderboard.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        leaderboard = list(csv.DictReader(handle))
    our_row = next(row for row in leaderboard if int(row["TeamId"]) == TEAM_ID)
    by_id = {int(row["ref"]): row for row in submissions}
    snapshot = {
        "queried_at_utc": iso_utc(),
        "queried_at_taipei": iso_taipei(),
        "timezone": "Asia/Taipei",
        "sources": [
            "Kaggle CLI competitions submissions",
            "Kaggle CLI competitions team-submissions",
            "Kaggle CLI competitions leaderboard --download",
        ],
        "team": {
            "team_id": TEAM_ID,
            "team_name": TEAM_NAME,
            "rank": int(our_row["Rank"]),
            "rating": float(our_row["Score"]),
            "leaderboard_submission_count": int(our_row["SubmissionCount"]),
        },
        "active_latest_two": team_submissions,
        "targets": {
            version: {
                "submission_id": submission_id,
                "publicScore": float(by_id[submission_id]["publicScore"]),
                "status": by_id[submission_id]["status"],
                "description": by_id[submission_id]["description"],
                "date": by_id[submission_id]["date"],
                "is_active_latest_two": submission_id in {int(row["id"]) for row in team_submissions},
            }
            for version, submission_id in TARGETS.items()
        },
        "all_our_submissions": submissions,
        "hashes": {
            "leaderboard_zip": sha256(snapshot_dir / "kaggriculture_leaderboard.zip"),
            "leaderboard_csv": sha256(snapshot_dir / "kaggriculture_public_leaderboard.csv"),
            "our_submissions": sha256(snapshot_dir / "our_submissions.json"),
            "active_team_submissions": sha256(snapshot_dir / "active_team_submissions.json"),
        },
    }
    write_json(snapshot_dir / "current_snapshot.json", snapshot)
    return snapshot


def fetch_opponent_current_ratings(all_rows: dict[str, list[dict[str, Any]]], workers: int) -> dict[str, Any]:
    opponents: dict[int, dict[str, Any]] = {}
    for rows in all_rows.values():
        for row in rows:
            for agent in row["agents"]:
                if agent["teamId"] != TEAM_ID:
                    opponents[agent["teamId"]] = {
                        "team_id": agent["teamId"],
                        "team_name": agent["teamName"],
                    }

    def one(team_id: int) -> tuple[int, dict[str, Any]]:
        try:
            api = kaggle_api()
            submissions = []
            for row in api.competition_team_submissions(team_id):
                submissions.append(
                    {
                        "id": int(row.id),
                        "dateSubmitted": str(row.date_submitted),
                        "publicScore": None if row.public_score is None else float(row.public_score),
                    }
                )
            return team_id, {"status": "ok", "active_submissions": submissions}
        except Exception as exc:
            return team_id, {"status": "error", "error_type": type(exc).__name__, "error": str(exc)}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(one, team_id) for team_id in sorted(opponents)]
        for future in as_completed(futures):
            team_id, result = future.result()
            opponents[team_id].update(result)
    payload = {
        "queried_at_utc": iso_utc(),
        "queried_at_taipei": iso_taipei(),
        "semantic_note": "publicScore is current query-time submission rating, not the pre/post-game rating; Kaggle's episode API does not expose pre/post ratings",
        "teams": [opponents[key] for key in sorted(opponents)],
    }
    write_json(RAW / "snapshot" / "opponent_active_submissions.json", payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument(
        "--phase",
        choices=["all", "metadata", "replays", "logs", "snapshot", "opponents"],
        default="all",
    )
    args = parser.parse_args()
    workers = max(1, args.workers)
    started = {"started_at_utc": iso_utc(), "started_at_taipei": iso_taipei(), "phase": args.phase}
    write_json(HERE / "fetch_run.json", started)

    all_rows = fetch_episodes() if args.phase in {"all", "metadata", "replays", "logs", "opponents"} else {}
    if args.phase in {"all", "snapshot", "metadata"}:
        fetch_snapshot()
    if args.phase in {"all", "opponents", "metadata"}:
        fetch_opponent_current_ratings(all_rows, workers)
    if args.phase in {"all", "replays"}:
        fetch_replays(all_rows, workers)
    if args.phase in {"all", "logs"}:
        fetch_logs(all_rows, workers)

    started.update({"completed_at_utc": iso_utc(), "completed_at_taipei": iso_taipei(), "status": "complete"})
    write_json(HERE / "fetch_run.json", started)


if __name__ == "__main__":
    main()
