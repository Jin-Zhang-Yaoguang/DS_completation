#!/usr/bin/env python3
"""从本地已有 Replay 构建 R2.1 Train/Dev/Blind 双来源面板；不联网、不读取对局 steps。"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
PROJECT = MODEL.parents[2]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from protocol import CUTOFF, SOURCES, atomic_json_dump, audit_replay, preregister  # noqa: E402


DEFAULT_ACCOUNT_REGISTRY = (
    PROJECT / "kaggle_Kaggriculture/model_data/v114_day_smdp_hmoe_ppo/own_online_cli/registry.json"
)
DEFAULT_OFFICIAL_ROOT = PROJECT / "kaggle_Kaggriculture/model_data/kaggriculture_episodes_index"
DEFAULT_OUTPUT = MODEL / "replay_data/panels/r2_1_v1"


def _rank(token: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}\0{token}".encode("utf-8")).hexdigest()


def _select(rows: Iterable[Any], count: int, salt: str, token: Any) -> list[Any]:
    values = list(rows)
    values.sort(key=lambda row: _rank(str(token(row)), salt))
    return values[: min(len(values), max(0, count))]


def _episode_types(submission_root: Path) -> dict[tuple[int, int], str]:
    result: dict[tuple[int, int], str] = {}
    for path in sorted(submission_root.glob("*-episodes.json")):
        try:
            submission_id = int(path.name.split("-", 1)[0])
            rows = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, json.JSONDecodeError):
            continue
        for row in rows if isinstance(rows, list) else []:
            try:
                result[(submission_id, int(row["id"]))] = str(row.get("type") or "UNKNOWN")
            except (KeyError, TypeError, ValueError):
                continue
    return result


def _account_candidates(registry: dict[str, Any], *, train: int, dev: int, blind: int,
                        multiplier: int) -> list[dict[str, Any]]:
    rows = [dict(row) for row in registry.get("entries", []) if row.get("evidence_eligible")]
    by_date: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if str(row.get("game_date", "")) >= CUTOFF:
            by_date[str(row["game_date"])].append(row)
    dates = sorted(by_date)
    if len(dates) < 3:
        raise ValueError("账号本地 registry 不足三个合格日期")
    selected = []
    selected.extend(_select(by_date[dates[-1]], blind * multiplier, "account-blind",
                            lambda row: row["dedup_key"]))
    selected.extend(_select(by_date[dates[-2]], dev * multiplier, "account-dev",
                            lambda row: row["dedup_key"]))
    older = [row for day in dates[:-2] for row in by_date[day]]
    selected.extend(_select(older, train * multiplier, "account-train",
                            lambda row: row["dedup_key"]))
    return selected


def _official_candidates(root: Path, *, train: int, dev: int, blind: int,
                         multiplier: int) -> list[tuple[str, Path]]:
    by_date: dict[str, list[Path]] = {}
    for partition in sorted(root.glob("date=*")):
        observed_date = partition.name.removeprefix("date=")
        if observed_date < CUTOFF:
            continue
        files = sorted((partition / "data").glob("*.json"))
        if files:
            by_date[observed_date] = files
    dates = sorted(by_date)
    if len(dates) < 3:
        raise ValueError("官方本地 index 不足三个合格日期")
    selected: list[tuple[str, Path]] = []
    selected.extend((dates[-1], path) for path in _select(
        by_date[dates[-1]], blind * multiplier, "official-blind", lambda path: path.stem,
    ))
    selected.extend((dates[-2], path) for path in _select(
        by_date[dates[-2]], dev * multiplier, "official-dev", lambda path: path.stem,
    ))
    older = [(day, path) for day in dates[:-2] for path in by_date[day]]
    older = _select(older, train * multiplier, "official-train",
                    lambda row: f"{row[0]}:{row[1].stem}")
    selected.extend(older)
    return selected


def _source_manifest(manifest: dict[str, Any], source: str) -> dict[str, Any]:
    assignments = [row for row in manifest["assignments"] if row["source_class"] == source]
    return {
        "schema": "v117-r2.1-source-panel-manifest-v1",
        "source_class": source,
        "source_role": "PRIMARY" if source == "ACCOUNT_ONLINE" else "INDEPENDENT_CONFIRMATION",
        "date_split": manifest["date_split"][source],
        "counts": {split: sum(row["split"] == split for row in assignments)
                   for split in ("train", "development", "blind_confirmation")},
        "frozen_lock": manifest["frozen_lock"],
        "assignments": assignments,
        "mixed_with_other_source": False,
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    account_registry = json.loads(args.account_registry.read_text(encoding="utf-8"))
    episode_types = _episode_types(args.account_registry.parent / "submissions")
    audited: list[dict[str, Any]] = []
    audit_errors: list[dict[str, Any]] = []

    for row in _account_candidates(
        account_registry, train=args.train_per_source, dev=args.dev_per_source,
        blind=args.blind_per_source, multiplier=args.candidate_multiplier,
    ):
        try:
            submission_id = int(row["submission_id"])
            episode_id = int(row["episode_id"])
            record = audit_replay(
                row["replay_path"], source_class="ACCOUNT_ONLINE",
                observed_date=str(row["game_date"]),
                date_basis="cached_kaggle_cli_episode_create_time",
                episode_type=episode_types.get((submission_id, episode_id), "UNKNOWN"),
                submission_id=submission_id, model_version=str(row["model_version"]),
                seat=int(row["seat"]),
                agent_or_package_sha256=str(row["agent_or_package_sha256"]),
                agent_log_sha256=str(row["agent_log_sha256"]) if row.get("agent_log_sha256") else None,
            )
            if record["replay_sha256"] != row.get("replay_sha256"):
                record["failures"].append("registry_replay_sha256_mismatch")
                record["strict_ready"] = False
                record["panel_ready"] = False
            audited.append(record)
        except Exception as exc:
            audit_errors.append({
                "source_class": "ACCOUNT_ONLINE", "episode_id": row.get("episode_id"),
                "error": f"{type(exc).__name__}: {exc}",
            })

    for observed_date, path in _official_candidates(
        args.official_root, train=args.train_per_source, dev=args.dev_per_source,
        blind=args.blind_per_source, multiplier=args.candidate_multiplier,
    ):
        try:
            audited.append(audit_replay(
                path, source_class="OFFICIAL_DAILY", observed_date=observed_date,
                date_basis="official_partition_create_time", episode_type="OFFICIAL_DAILY_PUBLIC",
            ))
        except Exception as exc:
            audit_errors.append({
                "source_class": "OFFICIAL_DAILY", "replay_path": str(path),
                "error": f"{type(exc).__name__}: {exc}",
            })

    manifest = preregister(
        audited, salt=args.salt, train_per_source=args.train_per_source,
        dev_per_source=args.dev_per_source, frozen_per_source=args.blind_per_source,
    )
    manifest["candidate_preselection"] = {
        "outcomes_used": False,
        "steps_opened": False,
        "algorithm": "date bucket then sha256 fixed salt",
        "candidate_multiplier": args.candidate_multiplier,
    }
    counts = Counter((row["source_class"], bool(row.get("panel_ready"))) for row in audited)
    registry = {
        "schema": "v117-r2.1-replay-registry-v1",
        "cutoff": CUTOFF,
        "no_network_access": True,
        "steps_opened": False,
        "global_dedup_key": ["episode_id", "replay_sha256"],
        "counts": {
            f"{source}:{'ready' if ready else 'excluded'}": counts[(source, ready)]
            for source in SOURCES for ready in (True, False)
        },
        "audit_errors": audit_errors,
        "records": audited,
    }
    exposure = {
        "schema": "v117-r2.1-exposure-ledger-v1",
        "blind_content_accessed": False,
        "records": [{
            "record_id": row["record_id"], "source_class": row["source_class"],
            "episode_id": row["episode_id"], "actual_seed": row["actual_seed"],
            "scenario_sha256": row["scenario_sha256"], "split": row["split"],
            "exposure_state": "METADATA_ONLY", "steps_opened": False,
        } for row in manifest["assignments"]],
    }
    decision = {
        "schema": "v117-r2.1-data-admission-decision-v1",
        "decision": "PASS_METADATA_PREREGISTRATION_CONTENT_NOT_OPENED",
        "cutoff": CUTOFF,
        "account_primary": True,
        "official_confirmation_separate": True,
        "account_failure_blocks_promotion": True,
        "blind_locked": manifest["frozen_lock"]["status"] != "LOCKED",
        "strength_evaluation_run": False,
        "r2_1_20_50_claim_authorized": False,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    atomic_json_dump(registry, args.output_dir / "replay_registry.json")
    atomic_json_dump(manifest, args.output_dir / "replay_panel_manifest.json")
    atomic_json_dump(_source_manifest(manifest, "ACCOUNT_ONLINE"),
                     args.output_dir / "account_scenario_manifest.json")
    atomic_json_dump(_source_manifest(manifest, "OFFICIAL_DAILY"),
                     args.output_dir / "official_scenario_manifest.json")
    atomic_json_dump(exposure, args.output_dir / "exposure_ledger.json")
    atomic_json_dump(decision, args.output_dir / "data_admission_decision.json")
    return {
        "schema": "v117-r2.1-panel-build-receipt-v1",
        "output_dir": str(args.output_dir.resolve()),
        "counts": manifest["counts"],
        "date_split": manifest["date_split"],
        "audit_errors": len(audit_errors),
        "blind_content_accessed": False,
        "strength_evaluation_run": False,
        "pass": True,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account-registry", type=Path, default=DEFAULT_ACCOUNT_REGISTRY)
    parser.add_argument("--official-root", type=Path, default=DEFAULT_OFFICIAL_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--train-per-source", type=int, default=64)
    parser.add_argument("--dev-per-source", type=int, default=32)
    parser.add_argument("--blind-per-source", type=int, default=64)
    parser.add_argument("--candidate-multiplier", type=int, default=4)
    parser.add_argument("--salt", default="v117-r2.1-replay-panels-date-split-v1")
    return parser.parse_args()


if __name__ == "__main__":
    result = build(parse_args())
    print(json.dumps(result, ensure_ascii=False, indent=2))
