#!/usr/bin/env python3
"""V117 Replay 准入、预分组、冻结锁和外生场景抽取协议。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .stream_whitelist import ReplayFormatError, read_replay_whitelist
except ImportError:
    from stream_whitelist import ReplayFormatError, read_replay_whitelist


CUTOFF = "2026-08-20"
EXPECTED_MODULE = "1.32.7"
SOURCES = ("ACCOUNT_ONLINE", "OFFICIAL_DAILY")
SCHEMA_RECORD = "v117-replay-admission-record-v2"
SCHEMA_MANIFEST = "v117-replay-date-split-manifest-v2"
SCHEMA_SCENARIO = "v117-replay-exogenous-scenario-v1"

EXPECTED_CONFIGURATION: dict[str, Any] = {
    "actTimeout": 1,
    "boardSize": 10,
    "episodeSteps": 720,
    "farmHandCostMult": 1,
    "marketParams": {},
    "maxMarketOrdersPerTurn": 10,
    "runTimeout": 1200,
    "seed": None,
    "shedCapacity": 100,
    "startingMoney": 3000,
    "townCenterSellInterval": 24,
    "townShopSellInterval": 4,
    "townShopUnlockInterval": 3,
    "turnsPerDay": 24,
    "weedSpawnChance": 0.005,
}

SHOP_PRODUCTS: dict[str, tuple[str, ...]] = {
    "BAKERY": ("EGG", "WHEAT"),
    "PIZZA_SHOP": ("MILK", "TOMATO", "WHEAT"),
    "BRUNCH_SPOT": ("EGG", "WHEAT", "STRAWBERRY"),
    "YARN_STORE": ("WOOL",),
    "ICE_CREAM_SHOP": ("STRAWBERRY", "MILK", "WHEAT"),
    "PET_CAFE": ("CARROT",),
    "SMOOTHIE_SHOP": ("STRAWBERRY", "MILK"),
    "FARMERS_MARKET": ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY"),
}
TOWN_CENTER_PRODUCTS = (
    "WHEAT",
    "CARROT",
    "TOMATO",
    "STRAWBERRY",
    "MELON",
    "EGG",
    "MILK",
    "WOOL",
)
FORBIDDEN_OUTPUT_KEYS = {
    "action",
    "actions",
    "reward",
    "rewards",
    "farms",
    "private",
    "market",
    "statuses",
    "agent",
    "agents",
}


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


EXPECTED_CONFIGURATION_SHA256 = canonical_sha256(EXPECTED_CONFIGURATION)


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json_dump(value: Any, output: str | Path) -> None:
    destination = Path(output).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=destination.name + ".", suffix=".tmp", dir=destination.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _assert_date(value: str) -> None:
    if not re.fullmatch(r"20\d\d-\d\d-\d\d", value):
        raise ValueError("observed_date 必须是 YYYY-MM-DD")
    datetime.strptime(value, "%Y-%m-%d")


def audit_replay(
    replay_path: str | Path,
    *,
    source_class: str,
    observed_date: str,
    date_basis: str,
    episode_type: str,
    submission_id: int | None = None,
    model_version: str | None = None,
    seat: int | None = None,
    agent_or_package_sha256: str | None = None,
    agent_log_sha256: str | None = None,
) -> dict[str, Any]:
    """只读元数据并重新计算文件哈希；不打开 steps 值。"""
    if source_class not in SOURCES:
        raise ValueError(f"未知数据来源：{source_class}")
    _assert_date(observed_date)
    path = Path(replay_path).resolve()
    failures: list[str] = []
    if observed_date < CUTOFF:
        failures.append("before_cutoff")

    metadata = read_replay_whitelist(path, include_steps=False)
    configuration_sha256 = canonical_sha256(metadata.configuration)
    if metadata.module_version != EXPECTED_MODULE:
        failures.append("module_version_mismatch")
    if configuration_sha256 != EXPECTED_CONFIGURATION_SHA256:
        failures.append("configuration_mismatch")
    if not metadata.stopped_before_steps:
        failures.append("steps_boundary_not_seen")

    if source_class == "ACCOUNT_ONLINE":
        if submission_id is None or int(submission_id) <= 0:
            failures.append("missing_submission_id")
        if not model_version:
            failures.append("missing_model_version")
        if seat not in {0, 1}:
            failures.append("missing_or_invalid_seat")
        if not agent_or_package_sha256 or not re.fullmatch(r"[0-9a-f]{64}", agent_or_package_sha256):
            failures.append("missing_or_invalid_agent_or_package_sha256")
        if agent_log_sha256 is not None and not re.fullmatch(r"[0-9a-f]{64}", agent_log_sha256):
            failures.append("invalid_agent_log_sha256")
    elif date_basis != "test_fixture":
        expected_fragment = f"model_data/kaggriculture_episodes_index/date={observed_date}/data/"
        if expected_fragment not in str(path):
            failures.append("official_source_path_mismatch")

    replay_sha256 = file_sha256(path)
    is_public_match = (
        episode_type in {"PUBLIC", "EpisodeType.EPISODE_TYPE_PUBLIC", "OFFICIAL_DAILY_PUBLIC"}
    )
    return {
        "schema": SCHEMA_RECORD,
        "source_class": source_class,
        "source_confidence_rank": 1 if source_class == "ACCOUNT_ONLINE" else 2,
        "observed_date": observed_date,
        "date_basis": date_basis,
        "episode_type": episode_type,
        "episode_id": metadata.episode_id,
        "actual_seed": metadata.seed,
        "module_version": metadata.module_version,
        "configuration": metadata.configuration,
        "configuration_sha256": configuration_sha256,
        "replay_path": str(path),
        "replay_sha256": replay_sha256,
        "metadata_stopped_before_steps": metadata.stopped_before_steps,
        "strict_ready": not failures,
        "panel_ready": not failures and is_public_match,
        "panel_exclusion": None if is_public_match else "not_public_match",
        "failures": failures,
        "record_id": f"{source_class}:{metadata.episode_id}:{replay_sha256}",
        "account_lineage": {
            "submission_id": int(submission_id) if submission_id is not None else None,
            "model_version": model_version,
            "seat": int(seat) if seat in {0, 1} else None,
            "agent_or_package_sha256": agent_or_package_sha256,
            "agent_log_sha256": agent_log_sha256,
            "agent_log_required_when_available": True,
        } if source_class == "ACCOUNT_ONLINE" else None,
    }


def _rank(salt: str, source: str, episode_id: int, replay_sha256: str) -> str:
    raw = f"{salt}\0{source}\0{episode_id}\0{replay_sha256}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _deduplicate(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """按 episode_id + replay_sha256 去重，跨来源相同时保留账号来源。"""
    conflicts: list[dict[str, Any]] = []
    by_episode: defaultdict[int, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_episode[int(record["episode_id"])].append(record)

    selected: list[dict[str, Any]] = []
    for episode_id, rows in sorted(by_episode.items()):
        hashes = {str(row["replay_sha256"]) for row in rows}
        if len(hashes) != 1:
            conflicts.append(
                {
                    "kind": "same_episode_different_replay_sha256",
                    "episode_id": episode_id,
                    "record_ids": sorted(str(row["record_id"]) for row in rows),
                }
            )
            continue
        rows.sort(key=lambda row: (int(row["source_confidence_rank"]), str(row["record_id"])))
        selected.append(rows[0])
    return selected, conflicts


def preregister(
    records: list[dict[str, Any]],
    *,
    salt: str,
    train_per_source: int,
    dev_per_source: int,
    frozen_per_source: int,
) -> dict[str, Any]:
    """严格按日期预注册 Train/Development/Blind，不打开任何 Replay steps。"""
    if min(train_per_source, dev_per_source, frozen_per_source) <= 0:
        raise ValueError("train/dev/blind 每个来源的数量都必须大于零")
    eligible = [record for record in records if record.get("panel_ready")]
    eligible, conflicts = _deduplicate(eligible)
    if conflicts:
        raise ValueError(f"episode/replay 哈希冲突：{conflicts}")

    by_seed: defaultdict[int, list[dict[str, Any]]] = defaultdict(list)
    for record in eligible:
        by_seed[int(record["actual_seed"])].append(record)
    seed_collisions = {seed for seed, rows in by_seed.items() if len(rows) > 1}
    exclusions = [
        {
            "kind": "seed_collision",
            "actual_seed": seed,
            "record_ids": sorted(str(row["record_id"]) for row in by_seed[seed]),
        }
        for seed in sorted(seed_collisions)
    ]
    eligible = [record for record in eligible if int(record["actual_seed"]) not in seed_collisions]

    assignments: list[dict[str, Any]] = []
    date_split: dict[str, Any] = {}
    selected_record_ids: set[str] = set()
    for source in SOURCES:
        source_records = [record for record in eligible if record["source_class"] == source]
        dates = sorted({str(record["observed_date"]) for record in source_records})
        if len(dates) < 3:
            raise ValueError(f"{source} 只有 {len(dates)} 个日期；日期隔离需要至少 Train/Dev/Blind 三天")
        train_dates = dates[:-2]
        development_date = dates[-2]
        blind_date = dates[-1]
        pools = {
            "train": [record for record in source_records if record["observed_date"] in train_dates],
            "development": [record for record in source_records if record["observed_date"] == development_date],
            "blind_confirmation": [record for record in source_records if record["observed_date"] == blind_date],
        }
        requested = {
            "train": train_per_source,
            "development": dev_per_source,
            "blind_confirmation": frozen_per_source,
        }
        for split, pool in pools.items():
            pool.sort(key=lambda record: _rank(
                salt, source, int(record["episode_id"]), str(record["replay_sha256"]),
            ))
            if len(pool) < requested[split]:
                raise ValueError(
                    f"{source}:{split} 在日期隔离后只有 {len(pool)} 条，需要 {requested[split]} 条"
                )
        date_split[source] = {
            "train_dates": train_dates,
            "development_dates": [development_date],
            "blind_dates": [blind_date],
            "latest_date_reserved_for_blind": True,
        }
        selected: list[tuple[str, dict[str, Any]]] = []
        for split in ("train", "development", "blind_confirmation"):
            selected.extend((split, record) for record in pools[split][:requested[split]])
        for split, record in selected:
            selected_record_ids.add(str(record["record_id"]))
            assignments.append(
                {
                    "record_id": record["record_id"],
                    "source_class": source,
                    "episode_id": int(record["episode_id"]),
                    "actual_seed": int(record["actual_seed"]),
                    "observed_date": record["observed_date"],
                    "replay_path": record["replay_path"],
                    "replay_sha256": record["replay_sha256"],
                    "configuration_sha256": record["configuration_sha256"],
                    "account_lineage": record.get("account_lineage"),
                    "split": split,
                    "rank_sha256": _rank(
                        salt,
                        source,
                        int(record["episode_id"]),
                        str(record["replay_sha256"]),
                    ),
                    "scenario_sha256": None,
                }
            )

    exclusions.extend({
        "kind": "eligible_not_selected_after_date_split",
        "record_id": str(record["record_id"]),
        "source_class": str(record["source_class"]),
        "observed_date": str(record["observed_date"]),
    } for record in eligible if str(record["record_id"]) not in selected_record_ids)
    counts = Counter((row["source_class"], row["split"]) for row in assignments)
    return {
        "schema": SCHEMA_MANIFEST,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "cutoff": CUTOFF,
        "expected_module_version": EXPECTED_MODULE,
        "expected_configuration_sha256": EXPECTED_CONFIGURATION_SHA256,
        "selection": {
            "algorithm": "date split first; then sha256(salt\\0source\\0episode_id\\0replay_sha256), ascending",
            "salt": salt,
            "outcomes_used": False,
            "steps_opened": False,
        },
        "date_split": date_split,
        "isolation": {
            "keys": ["episode_id", "actual_seed", "scenario_sha256"],
            "scenario_collision_policy": "抽取后发现重复则 fail-closed",
        },
        "source_reporting": {
            "mix_results": False,
            "primary": "ACCOUNT_ONLINE",
            "confirmation": "OFFICIAL_DAILY",
            "report_order": ["ACCOUNT_ONLINE", "OFFICIAL_DAILY"],
            "account_failure_blocks_promotion": True,
            "official_volume_cannot_override_account": True,
        },
        "gold_gate": {
            "status": "UNCHANGED_R4_TO_R7",
            "source_specific_threshold": None,
            "both_sources_and_gate": False,
        },
        "frozen_lock": {"status": "UNLOCKED", "candidate_sha256": None, "locked_at": None},
        "counts": {
            f"{source}:{split}": counts[(source, split)]
            for source in SOURCES
            for split in ("train", "development", "blind_confirmation")
        },
        "exclusions": exclusions,
        "assignments": assignments,
    }


def lock_candidate(manifest: dict[str, Any], candidate_sha256: str) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{64}", candidate_sha256):
        raise ValueError("candidate_sha256 必须是 64 位小写十六进制")
    prior = manifest.get("frozen_lock") or {}
    if prior.get("status") == "LOCKED" and prior.get("candidate_sha256") != candidate_sha256:
        raise ValueError("manifest 已锁定到另一个候选")
    result = json.loads(json.dumps(manifest))
    result["frozen_lock"] = {
        "status": "LOCKED",
        "candidate_sha256": candidate_sha256,
        "locked_at": datetime.now(timezone.utc).isoformat(),
    }
    return result


def _derive_unlocks(
    shops_by_step: tuple[tuple[str, ...], ...], turns_per_day: int
) -> list[dict[str, Any]]:
    prior: tuple[str, ...] = tuple()
    unlocks: list[dict[str, Any]] = []
    for step, shops in enumerate(shops_by_step):
        if shops == prior:
            continue
        if len(shops) < len(prior) or shops[: len(prior)] != prior:
            raise ReplayFormatError(f"商店轨迹在 step={step} 非单调")
        for ordinal, shop in enumerate(shops[len(prior) :], start=len(prior) + 1):
            if shop not in SHOP_PRODUCTS:
                raise ReplayFormatError(f"未知商店：{shop}")
            unlocks.append(
                {
                    "ordinal": ordinal,
                    "shop": shop,
                    "visible_from_step": step,
                    "day": step // turns_per_day,
                    "hour": step % turns_per_day,
                }
            )
        prior = shops
    return unlocks


def _derive_demand(
    shops_by_step: tuple[tuple[str, ...], ...], configuration: dict[str, Any]
) -> list[dict[str, Any]]:
    shop_interval = max(1, int(configuration["townShopSellInterval"]))
    center_interval = max(1, int(configuration["townCenterSellInterval"]))
    events: list[dict[str, Any]] = []
    for step, shops in enumerate(shops_by_step):
        shop_demand: Counter[str] = Counter()
        center_demand: Counter[str] = Counter()
        if step % shop_interval == 0:
            for shop in shops:
                products = SHOP_PRODUCTS.get(shop)
                if products is None:
                    raise ReplayFormatError(f"未知商店：{shop}")
                multiplier = 2 if len(products) == 1 else 1
                for product in products:
                    shop_demand[product] += multiplier
        if step % center_interval == 0:
            center_demand.update(TOWN_CENTER_PRODUCTS)
        if shop_demand or center_demand:
            total = shop_demand + center_demand
            events.append(
                {
                    "step": step,
                    "phase": "post_market",
                    "shop_quantities": dict(sorted(shop_demand.items())),
                    "town_center_quantities": dict(sorted(center_demand.items())),
                    "total_quantities": dict(sorted(total.items())),
                }
            )
    return events


def _assert_output_whitelist(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in FORBIDDEN_OUTPUT_KEYS:
                raise AssertionError(f"输出含禁用字段 {key!r}，位置 {path}")
            _assert_output_whitelist(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_output_whitelist(child, f"{path}[{index}]")


def extract_registered(
    manifest: dict[str, Any],
    *,
    source_class: str,
    episode_id: int,
    candidate_sha256: str | None = None,
) -> dict[str, Any]:
    matches = [
        row
        for row in manifest.get("assignments", [])
        if row.get("source_class") == source_class and int(row.get("episode_id", -1)) == episode_id
    ]
    if len(matches) != 1:
        raise ValueError(f"预注册记录数量不是 1：{len(matches)}")
    assignment = matches[0]
    if assignment["split"] == "blind_confirmation":
        lock = manifest.get("frozen_lock") or {}
        if lock.get("status") != "LOCKED":
            raise PermissionError("Blind 尚未锁定候选，禁止打开")
        if not candidate_sha256 or candidate_sha256 != lock.get("candidate_sha256"):
            raise PermissionError("候选哈希与冻结锁不一致")

    replay_path = Path(assignment["replay_path"])
    if file_sha256(replay_path) != assignment["replay_sha256"]:
        raise PermissionError("Replay 文件哈希发生变化")
    replay = read_replay_whitelist(replay_path, include_steps=True)
    configuration_sha256 = canonical_sha256(replay.configuration)
    if replay.episode_id != episode_id or replay.seed != int(assignment["actual_seed"]):
        raise ReplayFormatError("Replay 身份与 manifest 不一致")
    if replay.module_version != EXPECTED_MODULE:
        raise ReplayFormatError("module_version 不一致")
    if configuration_sha256 != EXPECTED_CONFIGURATION_SHA256:
        raise ReplayFormatError("完整 configuration 不一致")
    shops_by_step = replay.shops_by_step or tuple()
    turns_per_day = max(1, int(replay.configuration["turnsPerDay"]))
    unlocks = _derive_unlocks(shops_by_step, turns_per_day)
    demand = _derive_demand(shops_by_step, replay.configuration)
    hash_payload = {
        "module_version": replay.module_version,
        "configuration_sha256": configuration_sha256,
        "actual_seed": replay.seed,
        "realized_public_shops": unlocks,
        "derived_town_demand": demand,
    }
    scenario = {
        "schema": SCHEMA_SCENARIO,
        "source_class": source_class,
        "split": assignment["split"],
        "account_lineage": assignment.get("account_lineage"),
        "episode_id": replay.episode_id,
        "observed_date": assignment["observed_date"],
        "replay_sha256": assignment["replay_sha256"],
        "module_version": replay.module_version,
        "configuration": replay.configuration,
        "configuration_sha256": configuration_sha256,
        "actual_seed": replay.seed,
        "step_count": len(shops_by_step),
        "realized_public_shops": unlocks,
        "derived_town_demand": demand,
        "scenario_sha256": canonical_sha256(hash_payload),
        "historical_player_fields_materialized": False,
        "online_information_rule": "运行时只能看当前 observation，不能读取未来商店",
        "candidate_sha256": candidate_sha256
        if assignment["split"] == "blind_confirmation"
        else None,
    }
    _assert_output_whitelist(scenario)
    return scenario


def validate_scenario_isolation(scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    for key in ("episode_id", "actual_seed", "scenario_sha256"):
        values = [scenario[key] for scenario in scenarios]
        if len(values) != len(set(values)):
            raise ValueError(f"场景隔离失败：{key} 重复")
    return {"pass": True, "scenario_count": len(scenarios), "collision_count": 0}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    audit = sub.add_parser("audit-one")
    audit.add_argument("--replay", type=Path, required=True)
    audit.add_argument("--source", choices=SOURCES, required=True)
    audit.add_argument("--observed-date", required=True)
    audit.add_argument("--date-basis", required=True)
    audit.add_argument("--episode-type", required=True)
    audit.add_argument("--submission-id", type=int)
    audit.add_argument("--model-version")
    audit.add_argument("--seat", type=int, choices=(0, 1))
    audit.add_argument("--agent-or-package-sha256")
    audit.add_argument("--agent-log-sha256")
    audit.add_argument("--output", type=Path, required=True)

    split = sub.add_parser("preregister")
    split.add_argument("--record", type=Path, action="append", required=True)
    split.add_argument("--salt", default="v117-replay-panels-v1")
    split.add_argument("--train-per-source", type=int, default=64)
    split.add_argument("--dev-per-source", type=int, default=64)
    split.add_argument("--frozen-per-source", type=int, default=128)
    split.add_argument("--output", type=Path, required=True)

    lock = sub.add_parser("lock-candidate")
    lock.add_argument("--manifest", type=Path, required=True)
    lock.add_argument("--candidate-sha256", required=True)
    lock.add_argument("--output", type=Path, required=True)

    extract = sub.add_parser("extract")
    extract.add_argument("--manifest", type=Path, required=True)
    extract.add_argument("--source", choices=SOURCES, required=True)
    extract.add_argument("--episode-id", type=int, required=True)
    extract.add_argument("--candidate-sha256")
    extract.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "audit-one":
        result = audit_replay(
            args.replay,
            source_class=args.source,
            observed_date=args.observed_date,
            date_basis=args.date_basis,
            episode_type=args.episode_type,
            submission_id=args.submission_id,
            model_version=args.model_version,
            seat=args.seat,
            agent_or_package_sha256=args.agent_or_package_sha256,
            agent_log_sha256=args.agent_log_sha256,
        )
    elif args.command == "preregister":
        records = [_load_json(path) for path in args.record]
        result = preregister(
            records,
            salt=args.salt,
            train_per_source=args.train_per_source,
            dev_per_source=args.dev_per_source,
            frozen_per_source=args.frozen_per_source,
        )
    elif args.command == "lock-candidate":
        result = lock_candidate(_load_json(args.manifest), args.candidate_sha256)
    else:
        result = extract_registered(
            _load_json(args.manifest),
            source_class=args.source,
            episode_id=args.episode_id,
            candidate_sha256=args.candidate_sha256,
        )
    atomic_json_dump(result, args.output)
    print(json.dumps({"schema": result.get("schema"), "output": str(args.output.resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
