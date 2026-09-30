#!/usr/bin/env python3
"""构造 V124 独立训练集、行为指纹与来源审计。"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any

from contract import aggregate_contract, behavior_fingerprint, state_features


HERE = Path(__file__).resolve().parent
KAGGRICULTURE = HERE.parents[1]
REPLAY_HOME = KAGGRICULTURE / "model" / "community_research" / "top20_gold_distillation_active" / "replay_data"
TRAIN_RECEIPT = REPLAY_HOME / "top20_cli_receipt.json"
RESERVED_RECEIPT = REPLAY_HOME / "receipt.json"
CUTOFF = date(2026, 8, 20)
ENGINE = "1.32.7"
TRAIN_PANEL = "top20_cli_training_auxiliary"
RESERVED_PANELS = {"own_online_primary", "official_daily_confirmation"}
FORBIDDEN_RUNTIME_FIELDS = {
    "episode_id", "replay_sha256", "teacher", "opponent", "submission_id",
    "seat", "seed", "actual_date", "future_action", "future_shop",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=HERE / "dataset")
    parser.add_argument("--limit-replays", type=int, default=0)
    parser.add_argument("--verify-reserved", action="store_true")
    return parser.parse_args()


def json_dump(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def resolve_path(raw_path: str) -> Path:
    path = Path(raw_path)
    candidates = (
        path,
        REPLAY_HOME / "top20_cli_raw" / path.name,
        REPLAY_HOME / "own_online_raw" / path.name,
        REPLAY_HOME / "official_daily_raw" / path.name,
    )
    found = next((candidate for candidate in candidates if candidate.exists()), None)
    if found is None:
        raise FileNotFoundError(path)
    return found


def validate_source(source: dict, expected_panels: set[str]) -> Path:
    if date.fromisoformat(str(source["actual_date"])) < CUTOFF:
        raise ValueError(f"Replay 日期早于门槛: {source['episode_id']}")
    if str(source.get("module_version")) != ENGINE:
        raise ValueError(f"Replay 规则版本不一致: {source['episode_id']}")
    if str(source.get("source_panel")) not in expected_panels:
        raise ValueError(f"Replay 面板越界: {source['episode_id']} {source.get('source_panel')}")
    return resolve_path(str(source["path"]))


def load_training_sources() -> tuple[list[dict], dict]:
    receipt = json.loads(TRAIN_RECEIPT.read_text(encoding="utf-8"))
    selected: dict[tuple[int, str, str, int], dict] = {}
    source_rows = receipt.get("rows", [])
    for source in source_rows:
        path = validate_source(source, {TRAIN_PANEL})
        for teacher in source.get("teachers", []):
            key = (
                int(source["episode_id"]), str(source["sha256"]),
                str(teacher["team"]), int(teacher["seat"]),
            )
            candidate = {**source, "path": str(path), "teacher": dict(teacher)}
            old = selected.get(key)
            if old is None or (old.get("split") == "train" and candidate.get("split") == "dev"):
                selected[key] = candidate
    return list(selected.values()), {
        "receipt_path": str(TRAIN_RECEIPT),
        "receipt_rows": len(source_rows),
        "deduped_teacher_trajectories": len(selected),
    }


def inspect_reserved_sources(verify_hash: bool) -> dict:
    receipt = json.loads(RESERVED_RECEIPT.read_text(encoding="utf-8"))
    rows = receipt.get("rows", [])
    panels: Counter = Counter()
    dates: Counter = Counter()
    missing: list[int] = []
    hash_failures: list[int] = []
    unique: dict[tuple[int, str], Path] = {}
    for source in rows:
        try:
            path = validate_source(source, RESERVED_PANELS)
        except FileNotFoundError:
            missing.append(int(source["episode_id"]))
            continue
        panels[str(source["source_panel"])] += 1
        dates[str(source["actual_date"])] += 1
        unique[(int(source["episode_id"]), str(source["sha256"]))] = path
    if verify_hash:
        for index, ((episode, expected_sha), path) in enumerate(sorted(unique.items()), 1):
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
                hash_failures.append(episode)
            if index % 20 == 0 or index == len(unique):
                print(f"reserved hash {index}/{len(unique)}", flush=True)
    return {
        "receipt_path": str(RESERVED_RECEIPT),
        "rows": len(rows),
        "unique_replays": len(unique),
        "source_panels": dict(sorted(panels.items())),
        "actual_dates": dict(sorted(dates.items())),
        "path_missing_episode_ids": missing,
        "hash_verified": bool(verify_hash),
        "hash_failure_episode_ids": hash_failures,
        "evidence_policy": "RESERVED_ONLY_NOT_USED_FOR_TRAINING_OR_MODEL_SELECTION",
    }


def observation_at(replay: dict, seat: int, turn: int) -> dict:
    return replay["steps"][min(turn, len(replay["steps"]) - 1)][seat].get("observation", {}) or {}


def opponent_name(source: dict, seat: int) -> str:
    teams = list(source.get("teams", []) or [])
    return str(teams[1 - seat]) if len(teams) == 2 else "UNKNOWN"


def daily_rows(replay: dict, source: dict) -> list[dict]:
    teacher = source["teacher"]
    seat = int(teacher["seat"])
    base = {
        "episode_id": int(source["episode_id"]),
        "replay_sha256": str(source["sha256"]),
        "actual_date": str(source["actual_date"]),
        "source_panel": str(source["source_panel"]),
        "evidence_role": "TRAINING_AUXILIARY_NOT_PROMOTION_EVIDENCE",
        "seed": int(source.get("seed", 0) or 0),
        "teacher": str(teacher["team"]),
        "opponent": opponent_name(source, seat),
        "submission_id": int(teacher.get("submission_id", 0) or 0),
        "leaderboard_rank": int(teacher.get("leaderboard_rank", 0) or 0),
        "seat": seat,
    }
    rows: list[dict] = []
    for day in range(30):
        start, stop = day * 24, min((day + 1) * 24, 719)
        obs = observation_at(replay, seat, start)
        previous = observation_at(replay, seat, max(0, start - 24)) if start else None
        rows.append({
            **base,
            "decision_day": day,
            "cycle_phase": day % 3,
            "features": state_features(obs, previous),
            "target": aggregate_contract(replay, seat, start, stop),
        })
    return rows


def trajectory_fingerprint(replay: dict, source: dict, seat: int, role: str) -> dict:
    teams = list(source.get("teams", []) or [])
    team = str(teams[seat]) if len(teams) == 2 else "UNKNOWN"
    return {
        "episode_id": int(source["episode_id"]),
        "replay_sha256": str(source["sha256"]),
        "actual_date": str(source["actual_date"]),
        "team": team,
        "seat": seat,
        "role": role,
        "fingerprint": behavior_fingerprint(replay, seat),
    }


def main() -> int:
    args = parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    sources, source_audit = load_training_sources()
    grouped: dict[tuple[int, str], list[dict]] = defaultdict(list)
    for source in sources:
        grouped[(int(source["episode_id"]), str(source["sha256"]))].append(source)
    grouped_items = sorted(grouped.items())
    if args.limit_replays:
        grouped_items = grouped_items[: args.limit_replays]

    rows: list[dict] = []
    fingerprints: list[dict] = []
    dates: Counter = Counter()
    teachers: Counter = Counter()
    path_by_episode: dict[int, str] = {}
    for index, ((episode, expected_sha), group) in enumerate(grouped_items, 1):
        path = Path(group[0]["path"])
        raw = path.read_bytes()
        actual_sha = hashlib.sha256(raw).hexdigest()
        if actual_sha != expected_sha:
            raise ValueError(f"Replay SHA 不匹配: {episode}")
        replay = json.loads(raw)
        if len(replay.get("steps", [])) != 720:
            raise ValueError(f"Replay 不完整: {episode}")
        path_by_episode[episode] = str(path)
        teacher_seats = {(str(item["teacher"]["team"]), int(item["teacher"]["seat"])) for item in group}
        for source in group:
            rows.extend(daily_rows(replay, source))
            teachers[str(source["teacher"]["team"])] += 1
            dates[str(source["actual_date"])] += 1
        teams = list(group[0].get("teams", []) or [])
        for seat in (0, 1):
            role = "teacher" if len(teams) == 2 and (str(teams[seat]), seat) in teacher_seats else "opponent"
            fingerprints.append(trajectory_fingerprint(replay, group[0], seat, role))
        if index % 10 == 0 or index == len(grouped_items):
            print(f"training replay {index}/{len(grouped_items)}", flush=True)

    feature_names = sorted({name for row in rows for name in row["features"]})
    target_names = sorted({name for row in rows for name in row["target"]})
    forbidden_found = sorted(FORBIDDEN_RUNTIME_FIELDS.intersection(feature_names))
    if forbidden_found:
        raise ValueError(f"运行时特征越界: {forbidden_found}")

    write_jsonl(output / "daily_contract.jsonl", rows)
    write_jsonl(output / "trajectory_fingerprints.jsonl", fingerprints)
    json_dump(output / "feature_contract.json", {
        "schema": "kaggriculture-v124-runtime-feature-contract-v1",
        "alignment": "steps[t].observation plus same-episode past observation -> unordered steps[t+1:t+24].actions contract target",
        "runtime_feature_names": feature_names,
        "runtime_feature_count": len(feature_names),
        "target_names": target_names,
        "target_count": len(target_names),
        "forbidden_runtime_fields": sorted(FORBIDDEN_RUNTIME_FIELDS),
        "forbidden_found": forbidden_found,
        "runtime_uses_future_actions": False,
        "fingerprints_enter_runtime": False,
    })

    reserved = inspect_reserved_sources(bool(args.verify_reserved))
    unique_dates = sorted(dates)
    manifest = {
        "schema": "kaggriculture-v124-protocol-first-dataset-v1",
        "status": "TRAINING_DATA_READY_NOT_PROMOTION_EVIDENCE",
        "admission": {
            "minimum_actual_date": str(CUTOFF),
            "engine": ENGINE,
            "training_panel": TRAIN_PANEL,
            "dedupe_training": "episode_id+replay_sha256+teacher+seat",
        },
        "training": {
            **source_audit,
            "processed_unique_replays": len(grouped_items),
            "processed_teacher_trajectories": len(rows) // 30,
            "daily_rows": len(rows),
            "fingerprint_rows": len(fingerprints),
            "teacher_count": len(teachers),
            "teacher_trajectory_counts": dict(sorted(teachers.items())),
            "actual_dates": dict(sorted(dates.items())),
            "source_paths_by_episode": {str(k): v for k, v in sorted(path_by_episode.items())},
        },
        "split_policy": {
            "legacy_receipt_split_ignored": True,
            "next_stage": "behavior-family clustering then purged nested CV",
            "purge_unit": "episode_id+replay_sha256",
            "teacher_axis": "leave-one-behavior-family-out",
            "opponent_axis": "inner leave-one-opponent-family-out with episode purge",
            "time_axis_status": "BLOCKED_SINGLE_COLLECTION_DATE" if len(unique_dates) < 2 else "AVAILABLE",
            "time_axis_dates": unique_dates,
            "time_blind_replacement": "future own-online primary plus separate official-daily confirmation; never pooled",
        },
        "reserved_online_panels": reserved,
        "leakage_checks": {
            "runtime_future_action_fields": 0,
            "runtime_identifier_fields": len(forbidden_found),
            "action_order_preserved_in_target": False,
            "raw_action_tape_exported": False,
            "formal_online_rows_used_for_training": 0,
        },
    }
    json_dump(output / "dataset_manifest.json", manifest)
    print(json.dumps({
        "output": str(output),
        "replays": len(grouped_items),
        "teacher_trajectories": len(rows) // 30,
        "daily_rows": len(rows),
        "teachers": len(teachers),
        "time_axis_status": manifest["split_policy"]["time_axis_status"],
        "reserved_hash_failures": len(reserved["hash_failure_episode_ids"]),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
