"""Register post-cutoff official daily Replays without opening Blind content."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import csv
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any


SCHEMA = "kaggriculture-v114-recent-official-replay-registry-v1"
HARD_MINIMUM_OFFICIAL_DATE = date(2026, 8, 25)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as sink:
        json.dump(payload, sink, ensure_ascii=False, indent=2, sort_keys=True)
        sink.write("\n")
        temporary = Path(sink.name)
    os.replace(temporary, path)


def inspect_nonblind_bytes(raw: bytes, expected_episode_id: int) -> dict[str, Any]:
    replay = json.loads(raw)
    info = replay.get("info", {}) or {}
    episode_id = int(info.get("EpisodeId", replay.get("id", expected_episode_id)))
    if episode_id != expected_episode_id:
        raise ValueError(f"episode id mismatch {episode_id} != {expected_episode_id}")
    steps = len(replay.get("steps", []) or [])
    statuses = list(replay.get("statuses", []) or [])
    if steps != 720 or statuses != ["DONE", "DONE"]:
        raise ValueError(f"incomplete replay: steps={steps}, statuses={statuses}")
    return {
        "steps": steps,
        "statuses": statuses,
        "team_names": list(info.get("TeamNames", []) or []),
        "seed": info.get("seed"),
    }


def inspect_path(item: tuple[str, str, Path, int]) -> tuple[str, dict[str, Any] | None, str | None]:
    """Read one Replay once; Blind is hashed but never decoded."""
    _, split, path, episode_id = item
    raw = path.read_bytes()
    replay_sha = hashlib.sha256(raw).hexdigest()
    if split == "blind":
        return replay_sha, None, None
    try:
        return replay_sha, inspect_nonblind_bytes(raw, episode_id), None
    except Exception as exc:
        return replay_sha, None, f"{type(exc).__name__}: {exc}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--sync-state", type=Path, required=True)
    parser.add_argument("--cutoff", default="2026-08-25")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=min(16, os.cpu_count() or 1))
    args = parser.parse_args()

    cutoff = date.fromisoformat(args.cutoff)
    if cutoff < HARD_MINIMUM_OFFICIAL_DATE:
        raise ValueError(
            f"official index cutoff {cutoff} violates hard minimum {HARD_MINIMUM_OFFICIAL_DATE}"
        )
    state = json.loads(args.sync_state.read_text(encoding="utf-8"))
    complete_dates = sorted(
        day for day, record in state.get("dates", {}).items()
        if date.fromisoformat(day) >= cutoff and record.get("status") == "complete"
    )
    if len(complete_dates) < 3:
        raise ValueError("at least three complete post-cutoff dates are required")
    blind_date, dev_date = complete_dates[-1], complete_dates[-2]
    split_by_date = {
        day: "blind" if day == blind_date else "dev" if day == dev_date else "train"
        for day in complete_dates
    }
    paths: list[tuple[str, str, Path, int]] = []
    for day in complete_dates:
        data_dir = args.root / f"date={day}" / "data"
        if not data_dir.is_dir():
            raise FileNotFoundError(data_dir)
        for path in sorted(data_dir.glob("*.json")):
            try:
                episode_id = int(path.stem)
            except ValueError:
                continue
            paths.append((day, split_by_date[day], path, episode_id))

    # A decoded Replay is memory-heavy; cap concurrent decodes even when hashing workers are higher.
    inspect_workers = min(max(1, args.workers), 4)
    with ProcessPoolExecutor(max_workers=inspect_workers) as pool:
        inspected = list(pool.map(inspect_path, paths))

    entries: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for (day, split, path, episode_id), (replay_sha, details, error) in zip(paths, inspected):
        row: dict[str, Any] = {
            "episode_id": episode_id,
            "game_date": day,
            "split": split,
            "source": "official_daily_index",
            "replay_path": str(path.resolve()),
            "replay_sha256": replay_sha,
            "dedup_key": f"{episode_id}:{replay_sha}",
            "blind_content_accessed": False,
        }
        if split != "blind":
            if error is None and details is not None:
                row.update(details)
                row["content_validated"] = True
            else:
                row["content_validated"] = False
                failures.append({
                    "episode_id": episode_id,
                    "game_date": day,
                    "path": str(path.resolve()),
                    "error": error or "unknown validation failure",
                })
        else:
            row["content_validated"] = None
        entries.append(row)

    unique: dict[tuple[int, str], dict[str, Any]] = {}
    duplicate_rows = 0
    episode_sha_conflicts: dict[int, set[str]] = {}
    for row in entries:
        key = (row["episode_id"], row["replay_sha256"])
        if key in unique:
            duplicate_rows += 1
            continue
        unique[key] = row
        episode_sha_conflicts.setdefault(row["episode_id"], set()).add(row["replay_sha256"])
    conflicts = {
        str(episode_id): sorted(values)
        for episode_id, values in episode_sha_conflicts.items() if len(values) > 1
    }

    selected = sorted(unique.values(), key=lambda row: (row["game_date"], row["episode_id"]))
    by_date = {
        day: {
            "split": split_by_date[day],
            "registered": sum(row["game_date"] == day for row in selected),
            "failures": sum(row["game_date"] == day for row in failures),
        }
        for day in complete_dates
    }
    report = {
        "schema": SCHEMA,
        "status": "QUALIFIED" if not failures and not conflicts else "FAIL_CLOSED",
        "cutoff_date_inclusive": args.cutoff,
        "hard_minimum_official_date_inclusive": HARD_MINIMUM_OFFICIAL_DATE.isoformat(),
        "date_split": {
            "train": complete_dates[:-2],
            "dev": [dev_date],
            "blind": [blind_date],
        },
        "blind_policy": "filenames and SHA only; Replay JSON content not opened",
        "io_policy": f"single-read SHA plus nonblind decode; max concurrent decodes={inspect_workers}",
        "source_sync_state": str(args.sync_state.resolve()),
        "source_sync_state_sha256": sha256_file(args.sync_state),
        "counts": {
            "source_files": len(paths),
            "unique_replays": len(selected),
            "duplicate_rows": duplicate_rows,
            "episode_sha_conflicts": len(conflicts),
            "failures": len(failures),
            "train": sum(row["split"] == "train" for row in selected),
            "dev": sum(row["split"] == "dev" for row in selected),
            "blind": sum(row["split"] == "blind" for row in selected),
        },
        "by_date": by_date,
        "episode_sha_conflicts": conflicts,
        "failures": failures,
        "entries": selected,
    }
    output = args.output_dir / "registry.json"
    atomic_json(output, report)
    csv_path = args.output_dir / "registry.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as sink:
        writer = csv.DictWriter(sink, fieldnames=(
            "episode_id", "game_date", "split", "source", "replay_sha256",
            "dedup_key", "replay_path", "content_validated", "blind_content_accessed",
        ))
        writer.writeheader()
        writer.writerows({key: row.get(key) for key in writer.fieldnames} for row in selected)
    print(json.dumps({
        "status": report["status"],
        "date_split": report["date_split"],
        "counts": report["counts"],
        "registry": str(output.resolve()),
        "registry_sha256": sha256_file(output),
        "csv_sha256": sha256_file(csv_path),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
