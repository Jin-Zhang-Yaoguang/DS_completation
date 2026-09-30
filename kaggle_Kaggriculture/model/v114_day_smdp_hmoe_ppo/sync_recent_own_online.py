"""Incrementally mirror post-cutoff own Kaggriculture episodes using Kaggle CLI only."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any


HERE = Path(__file__).resolve().parent
COMPETITION_ROOT = HERE.parent.parent
MODEL_ROOT = COMPETITION_ROOT / "model"
MODEL_DATA_ROOT = COMPETITION_ROOT / "model_data"
INDEX_ROOT = MODEL_DATA_ROOT / "kaggriculture_episodes_index"
KAGGLE = Path("/Users/a1-6/.local/bin/kaggle")
SCHEMA = "kaggriculture-v114-recent-own-online-registry-v1"


# 本映射只用于登记当时提交包的本地 SHA，不参与动作生成。重复提交显式指向同一冻结归档。
SUBMISSION_ARTIFACTS: dict[int, tuple[str, str | None]] = {
    55647343: ("v8_kawa_lead2_slot", "v8_kawa_lead2_slot/submission.tar.gz"),
    55649391: ("v9_anti_mirror", "v9_anti_mirror/submission.tar.gz"),
    55680692: ("v1_adaptive_market_resubmit", "v1_adaptive_market/submission.tar.gz"),
    55680696: ("v2_survival_guard_resubmit", "v2_survival_guard/submission.tar.gz"),
    55713093: ("v12_a2_invalid_package", None),
    55713101: ("v12_incumbent_error", None),
    55713355: ("v12a2_no_shop_gate", "v12a2_no_shop_gate/submission.tar.gz"),
    55713359: ("v12_incumbent_r002", "v12_incumbent_r002/submission.tar.gz"),
    55719781: ("v13c_a2_v8_no_wool_throttle", "v13c_a2_v8_no_wool_throttle/submission.tar.gz"),
    55722630: ("v14_queue_stateful_no_mirror", "v14_queue_best_response/submission.tar.gz"),
    55743118: ("v12a2_repeat_1", "v12a2_no_shop_gate/submission.tar.gz"),
    55743125: ("v12a2_repeat_2", "v12a2_no_shop_gate/submission.tar.gz"),
    55743133: ("v12a2_repeat_3", "v12a2_no_shop_gate/submission.tar.gz"),
    55797007: ("v16_s2_town_drain", "v16_s2_town_drain_challenger/submission.tar.gz"),
    55798152: ("v17_complete_route_router", None),
    55806427: ("p0a_market_mpc", None),
    55806437: ("p0b_task_dag_repair", None),
    55819961: ("v19_hierarchical_moe", "v19_hierarchical_moe/submission.tar.gz"),
    55821249: ("v20_demand_timing_moe", "v20_demand_timing_moe/submission.tar.gz"),
    55821671: ("v21_top_meta_moe", "v21_top_meta_moe/submission.tar.gz"),
    55843998: ("v19_hierarchical_moe_resubmit_20260828", "v19_hierarchical_moe/submission.tar.gz"),
    55844004: ("v20_demand_timing_moe_resubmit_20260828", "v20_demand_timing_moe/submission.tar.gz"),
    55847378: ("v29_selected_v21_champion_20260828", "v29_champion_selection/submission.tar.gz"),
    55855161: ("v32_clone_horizon_preempt", "v32_clone_horizon_preempt/submission.tar.gz"),
    55856751: ("v76_adjacent_safe_buy_lead", "v76_adjacent_safe_buy_lead/submission.tar.gz"),
    55858336: ("v20_demand_timing_moe_resubmit_20260829", "v20_demand_timing_moe/submission.tar.gz"),
    55861471: ("v37_preterminal_boundary_preempt", "v37_preterminal_boundary_preempt/submission.tar.gz"),
    55861473: ("v54_terminal_water_bypass", "v54_terminal_water_bypass/submission.tar.gz"),
    55866631: ("v37_preterminal_boundary_preempt_resubmit", "v37_preterminal_boundary_preempt/submission.tar.gz"),
    55878384: ("v_copy1_public_2900", "v_copy1/submission.tar.gz"),
    55879211: ("v29_selected_v21_champion_resubmit", "v29_champion_selection/submission.tar.gz"),
    55891047: ("v19_hierarchical_moe_resubmit_20260830", "v19_hierarchical_moe/submission.tar.gz"),
    55891069: ("v12a2_resubmit_20260830", "v12a2_no_shop_gate/submission.tar.gz"),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def parse_json_output(text: str) -> Any:
    start = min(position for position in (text.find("["), text.find("{")) if position >= 0)
    decoder = json.JSONDecoder()
    payload, _ = decoder.raw_decode(text[start:])
    return payload


def run_cli(args: list[str]) -> str:
    result = subprocess.run(
        [str(KAGGLE), *args], cwd=COMPETITION_ROOT, text=True, capture_output=True
    )
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout).strip())
    return result.stdout


def iso_date(value: str) -> date:
    return date.fromisoformat(value[:10])


def fallback_version(description: str, submission_id: int) -> str:
    label = re.sub(r"[^a-z0-9]+", "_", description.lower()).strip("_")[:64]
    return label or f"submission_{submission_id}"


def artifact_identity(submission_id: int, description: str) -> dict[str, Any]:
    version, relative = SUBMISSION_ARTIFACTS.get(
        submission_id, (fallback_version(description, submission_id), None)
    )
    if relative is None:
        return {
            "model_version": version,
            "agent_artifact_path": None,
            "agent_or_package_sha256": None,
            "agent_sha_status": "MISSING_LOCAL_EXACT_ARTIFACT_FAIL_CLOSED",
        }
    path = MODEL_ROOT / relative
    if not path.is_file():
        return {
            "model_version": version,
            "agent_artifact_path": str(path.resolve()),
            "agent_or_package_sha256": None,
            "agent_sha_status": "MAPPED_ARTIFACT_NOT_FOUND_FAIL_CLOSED",
        }
    return {
        "model_version": version,
        "agent_artifact_path": str(path.resolve()),
        "agent_or_package_sha256": sha256_file(path),
        "agent_sha_status": "LOCAL_SUBMISSION_ARTIFACT_HASHED",
    }


def existing_replays(output_root: Path) -> dict[int, Path]:
    result: dict[int, Path] = {}
    for path in COMPETITION_ROOT.rglob("episode-*-replay.json"):
        match = re.search(r"episode-(\d+)-replay\.json$", path.name)
        if match and output_root not in path.parents and path.exists():
            result.setdefault(int(match.group(1)), path)
    return result


def existing_logs(output_root: Path) -> dict[tuple[int, int], Path]:
    result: dict[tuple[int, int], Path] = {}
    for path in COMPETITION_ROOT.rglob("episode-*-agent-*"):
        match = re.search(r"episode-(\d+)-agent-(\d+)", path.name)
        if match and output_root not in path.parents and path.is_file():
            result.setdefault((int(match.group(1)), int(match.group(2))), path)
    return result


def allowed_index_replay(episode_id: int, minimum: date) -> Path | None:
    for path in sorted(INDEX_ROOT.glob(f"date=*/data/{episode_id}.json"), reverse=True):
        day = date.fromisoformat(path.parent.parent.name.removeprefix("date="))
        if day >= minimum:
            return path
    return None


def ensure_replay(
    episode_id: int,
    replay_dir: Path,
    replay_cache: dict[int, Path],
    official_index_minimum: date,
) -> dict[str, Any]:
    target = replay_dir / f"episode-{episode_id}-replay.json"
    if target.exists():
        return {"episode_id": episode_id, "status": "exists", "path": target}
    source = replay_cache.get(episode_id) or allowed_index_replay(episode_id, official_index_minimum)
    if source is not None:
        target.symlink_to(os.path.relpath(source, replay_dir))
        return {"episode_id": episode_id, "status": "linked_local", "path": target, "source": source}
    result = subprocess.run(
        [str(KAGGLE), "competitions", "replay", str(episode_id), "--path", str(replay_dir), "--quiet"],
        cwd=COMPETITION_ROOT, text=True, capture_output=True,
    )
    if result.returncode or not target.exists():
        return {
            "episode_id": episode_id,
            "status": "error",
            "error": (result.stderr or result.stdout).strip() or "Replay file not produced",
        }
    return {"episode_id": episode_id, "status": "downloaded", "path": target}


def replay_team_seats(path: Path) -> list[int]:
    # Replay 常见大小约 30MB，但 info/TeamNames 位于文件头部；禁止为 seat 登记解析整局。
    with path.open("rb") as source:
        prefix = source.read(64 * 1024)
    match = re.search(rb'"TeamNames"\s*:\s*(\[[^\]]*\])', prefix)
    if match is None:
        raise ValueError("TeamNames not found in first 64KiB")
    names = list(json.loads(match.group(1)))
    return [index for index, name in enumerate(names) if name == "datatuu"]


def ensure_log(
    episode_id: int,
    seat: int,
    log_dir: Path,
    log_cache: dict[tuple[int, int], Path],
) -> dict[str, Any]:
    target = log_dir / f"episode-{episode_id}-agent-{seat}.log"
    if target.exists():
        return {"episode_id": episode_id, "seat": seat, "status": "exists", "path": target}
    source = log_cache.get((episode_id, seat))
    if source is not None:
        target.symlink_to(os.path.relpath(source, log_dir))
        return {"episode_id": episode_id, "seat": seat, "status": "linked_local", "path": target, "source": source}
    temporary = log_dir / f".episode-{episode_id}-seat-{seat}"
    if temporary.exists():
        shutil.rmtree(temporary)
    temporary.mkdir(parents=True)
    try:
        result = subprocess.run(
            [str(KAGGLE), "competitions", "logs", str(episode_id), str(seat), "--path", str(temporary), "--quiet"],
            cwd=COMPETITION_ROOT, text=True, capture_output=True,
        )
        produced = [path for path in temporary.iterdir() if path.is_file()]
        if result.returncode or not produced:
            return {
                "episode_id": episode_id,
                "seat": seat,
                "status": "error",
                "error": (result.stderr or result.stdout).strip() or "Agent log not produced",
            }
        max(produced, key=lambda path: path.stat().st_mtime).replace(target)
        return {"episode_id": episode_id, "seat": seat, "status": "downloaded", "path": target}
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--minimum-game-date", default="2026-08-20")
    parser.add_argument("--official-index-minimum", default="2026-08-25")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--refresh-episode-lists", action="store_true")
    args = parser.parse_args()

    minimum_game_date = date.fromisoformat(args.minimum_game_date)
    official_index_minimum = date.fromisoformat(args.official_index_minimum)
    output_root = args.output_root.resolve()
    replay_dir = output_root / "replays"
    log_dir = output_root / "agent_logs"
    submission_dir = output_root / "submissions"
    replay_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    submission_dir.mkdir(parents=True, exist_ok=True)

    submissions = parse_json_output(run_cli([
        "competitions", "submissions", "kaggriculture", "--format", "json", "--page-size", "200"
    ]))
    selected_submissions = [
        row for row in submissions if iso_date(str(row["date"])) >= minimum_game_date
    ]
    memberships: dict[int, list[dict[str, Any]]] = {}
    submission_records = []
    failures: list[dict[str, Any]] = []
    for row in selected_submissions:
        submission_id = int(row["ref"])
        identity = artifact_identity(submission_id, str(row.get("description", "")))
        record = {
            "submission_id": submission_id,
            "submission_date": str(row["date"]),
            "description": str(row.get("description", "")),
            "submission_status": str(row.get("status", "")),
            "public_score": row.get("publicScore"),
            **identity,
        }
        episode_cache = submission_dir / f"{submission_id}-episodes.json"
        try:
            if episode_cache.exists() and not args.refresh_episode_lists:
                episodes = json.loads(episode_cache.read_text(encoding="utf-8"))
            else:
                episodes = parse_json_output(run_cli([
                    "competitions", "episodes", str(submission_id), "--format", "json"
                ]))
                atomic_json(episode_cache, episodes)
        except Exception as exc:
            episodes = []
            failures.append({
                "kind": "episode_list",
                "submission_id": submission_id,
                "error": f"{type(exc).__name__}: {exc}",
            })
        eligible = [
            episode for episode in episodes
            if "COMPLETED" in str(episode.get("state", ""))
            and iso_date(str(episode.get("createTime") or episode.get("endTime"))) >= minimum_game_date
        ]
        record["episodes_total"] = len(episodes)
        record["episodes_post_cutoff_completed"] = len(eligible)
        submission_records.append(record)
        for episode in eligible:
            episode_id = int(episode["id"])
            memberships.setdefault(episode_id, []).append({
                "submission_id": submission_id,
                "model_version": identity["model_version"],
                "game_date": str(episode.get("createTime") or episode.get("endTime"))[:10],
                "create_time": episode.get("createTime"),
                "end_time": episode.get("endTime"),
                "agent_or_package_sha256": identity["agent_or_package_sha256"],
                "agent_sha_status": identity["agent_sha_status"],
            })

    replay_cache = existing_replays(output_root)
    replay_results: dict[int, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {
            pool.submit(ensure_replay, episode_id, replay_dir, replay_cache, official_index_minimum): episode_id
            for episode_id in memberships
        }
        for future in as_completed(futures):
            result = future.result()
            replay_results[int(result["episode_id"])] = result

    episode_seats: dict[int, list[int]] = {}
    for episode_id, result in replay_results.items():
        path = result.get("path")
        if result["status"] == "error" or not isinstance(path, Path):
            failures.append({"kind": "replay", **{key: value for key, value in result.items() if key != "path"}})
            continue
        try:
            episode_seats[episode_id] = replay_team_seats(path)
        except Exception as exc:
            failures.append({
                "kind": "replay_parse", "episode_id": episode_id,
                "error": f"{type(exc).__name__}: {exc}",
            })

    log_cache = existing_logs(output_root)
    log_results: dict[tuple[int, int], dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {
            pool.submit(ensure_log, episode_id, seat, log_dir, log_cache): (episode_id, seat)
            for episode_id, seats in episode_seats.items() for seat in seats
        }
        for future in as_completed(futures):
            result = future.result()
            log_results[(int(result["episode_id"]), int(result["seat"]))] = result
            if result["status"] == "error":
                failures.append({"kind": "agent_log", **{key: value for key, value in result.items() if key != "path"}})

    entries = []
    ambiguous_self_matches = 0
    missing_agent_sha = 0
    missing_logs = 0
    for episode_id, rows in sorted(memberships.items()):
        replay_result = replay_results.get(episode_id, {})
        replay_path = replay_result.get("path")
        if not isinstance(replay_path, Path) or not replay_path.exists():
            continue
        replay_sha = sha256_file(replay_path)
        seats = episode_seats.get(episode_id, [])
        unambiguous = len(seats) == 1 and len(rows) == 1
        if not unambiguous:
            ambiguous_self_matches += 1
        for membership in rows:
            seat = seats[0] if unambiguous else None
            candidate_log_paths = [
                result.get("path") for (identity, _), result in log_results.items()
                if identity == episode_id and isinstance(result.get("path"), Path)
                and result.get("path").exists()
            ]
            log_sha_by_seat = {
                str(key[1]): sha256_file(result["path"])
                for key, result in log_results.items()
                if key[0] == episode_id and isinstance(result.get("path"), Path)
                and result["path"].exists()
            }
            selected_log_sha = log_sha_by_seat.get(str(seat)) if seat is not None else None
            if not membership["agent_or_package_sha256"]:
                missing_agent_sha += 1
            if seat is not None and selected_log_sha is None:
                missing_logs += 1
            evidence_eligible = bool(
                seat is not None
                and membership["agent_or_package_sha256"]
                and selected_log_sha
            )
            entries.append({
                **membership,
                "episode_id": episode_id,
                "seat": seat,
                "seat_candidates": seats,
                "seat_status": "UNAMBIGUOUS" if unambiguous else "AMBIGUOUS_SELF_MATCH_FAIL_CLOSED",
                "replay_path": str(replay_path.resolve()),
                "replay_sha256": replay_sha,
                "dedup_key": f"{episode_id}:{replay_sha}",
                "agent_log_sha256": selected_log_sha,
                "agent_log_sha256_by_seat": log_sha_by_seat,
                "agent_log_paths": [str(path.resolve()) for path in candidate_log_paths],
                "evidence_eligible": evidence_eligible,
                "exclusion_reason": None if evidence_eligible else "MISSING_UNAMBIGUOUS_SEAT_AGENT_SHA_OR_LOG_SHA",
            })

    report = {
        "schema": SCHEMA,
        "generated_at": utc_now(),
        "status": "QUALIFIED" if not failures and not ambiguous_self_matches and not missing_agent_sha and not missing_logs else "PARTIAL_FAIL_CLOSED",
        "minimum_game_date_inclusive": args.minimum_game_date,
        "official_index_minimum_partition_date_inclusive": args.official_index_minimum,
        "source": "KAGGLE_CLI_ONLY_WITH_LOCAL_INCREMENTAL_REUSE",
        "global_dedup_key": ["episode_id", "replay_sha256"],
        "counts": {
            "submissions_post_cutoff": len(selected_submissions),
            "submission_versions": len({row["model_version"] for row in submission_records}),
            "unique_episodes": len(memberships),
            "membership_rows": len(entries),
            "evidence_eligible_rows": sum(bool(row["evidence_eligible"]) for row in entries),
            "ambiguous_self_match_episodes": ambiguous_self_matches,
            "missing_agent_sha_rows": missing_agent_sha,
            "missing_log_sha_rows": missing_logs,
            "failures": len(failures),
        },
        "date_coverage": sorted({row["game_date"] for row in entries}),
        "version_coverage": sorted({row["model_version"] for row in entries}),
        "submissions": submission_records,
        "failures": failures,
        "entries": entries,
    }
    output = output_root / "registry.json"
    atomic_json(output, report)
    print(json.dumps({
        "status": report["status"],
        "counts": report["counts"],
        "date_coverage": report["date_coverage"],
        "registry": str(output),
        "registry_sha256": sha256_file(output),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
