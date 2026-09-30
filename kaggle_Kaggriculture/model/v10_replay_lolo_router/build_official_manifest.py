#!/usr/bin/env python3
"""Build a compact, leakage-safe manifest from official Kaggriculture replays.

The raw replay corpus is intentionally processed one file at a time.  Only a
small record is retained after each JSON file, so peak memory is independent of
the 60 GiB corpus size.  ``orjson`` is used when installed; the standard
library JSON parser is the supported fallback.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import struct
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

try:  # Optional accelerator; the output is parser-independent.
    import orjson as _orjson
except ImportError:  # pragma: no cover - exercised in the current environment.
    _orjson = None


SCHEMA_VERSION = "kaggriculture-official-replay-manifest-v1"
ACTION_HASH_SCHEMA = "farmer-hands-canonical-json-length-prefixed-v1"
DEFAULT_DATES = ("2026-08-18", "2026-08-19", "2026-08-20")
DEFAULT_SPLIT_RATIOS = {"train": 0.80, "val": 0.10, "test": 0.10}
DEFAULT_SPLIT_SALT = "kaggriculture-official-20260818-20-v1"
DEFAULT_DATA_ROOT = (
    Path(__file__).resolve().parents[2]
    / "model_data"
    / "kaggriculture_episodes_index"
    / "daily"
)


def _loads(raw: bytes) -> Any:
    if _orjson is not None:
        return _orjson.loads(raw)
    return json.loads(raw)


def _canonical_bytes(value: Any) -> bytes:
    """Return stable bytes independent of the JSON parser in use."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def production_action_hash(
    steps: Sequence[Any], seat: int, limit: int | None = None
) -> tuple[str, int, int]:
    """Hash one seat's farmer+hands trajectory, deliberately excluding market.

    ``prefix72`` means replay indices 0 through 71 inclusive.  Missing seat or
    malformed action records are represented explicitly instead of silently
    becoming PASS, ensuring data defects cannot alias a valid trajectory.
    """

    digest = hashlib.sha256()
    digest.update(ACTION_HASH_SCHEMA.encode("ascii"))
    digest.update(b"\0")
    selected = steps if limit is None else steps[:limit]
    malformed = 0
    count = 0
    for step in selected:
        agents = step if isinstance(step, list) else []
        row = agents[seat] if seat < len(agents) and isinstance(agents[seat], dict) else {}
        action = row.get("action")
        if isinstance(action, dict):
            production = {
                "farmer": action.get("farmer"),
                "hands": action.get("hands"),
            }
        else:
            production = {"farmer": None, "hands": None}
            malformed += 1
        blob = _canonical_bytes(production)
        digest.update(struct.pack(">I", len(blob)))
        digest.update(blob)
        count += 1
    return digest.hexdigest(), count, malformed


def _value_missing(value: Any) -> bool:
    return value is None or value == "" or value == []


def _coerce_episode_id(info: Mapping[str, Any], path: Path) -> int | str | None:
    value = info.get("EpisodeId")
    if value is not None:
        return value
    try:
        return int(path.stem)
    except ValueError:
        return path.stem or None


def extract_record(path: Path, date: str, source_root: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    replay_sha256 = hashlib.sha256(raw).hexdigest()
    payload = _loads(raw)
    del raw
    if not isinstance(payload, dict):
        raise ValueError("top-level JSON value is not an object")

    info = payload.get("info") if isinstance(payload.get("info"), dict) else {}
    config = (
        payload.get("configuration")
        if isinstance(payload.get("configuration"), dict)
        else {}
    )
    steps = _safe_list(payload.get("steps"))
    episode_id = _coerce_episode_id(info, path)
    seed = info.get("seed")
    if seed is None:
        seed = config.get("seed")
    team_names = _safe_list(info.get("TeamNames"))
    if not team_names:
        agents = _safe_list(info.get("Agents"))
        team_names = [
            agent.get("Name") if isinstance(agent, dict) else None for agent in agents
        ]
    final_rewards = _safe_list(payload.get("rewards"))
    final_statuses = _safe_list(payload.get("statuses"))
    last_step = steps[-1] if steps and isinstance(steps[-1], list) else []
    terminal_rewards = [
        row.get("reward") if isinstance(row, dict) else None for row in last_step
    ]
    terminal_statuses = [
        row.get("status") if isinstance(row, dict) else None for row in last_step
    ]
    seat_count = max(
        2,
        len(team_names),
        len(final_rewards),
        len(final_statuses),
        len(last_step),
    )
    production: list[dict[str, Any]] = []
    for seat in range(seat_count):
        full_hash, full_count, full_malformed = production_action_hash(steps, seat)
        prefix_hash, prefix_count, prefix_malformed = production_action_hash(
            steps, seat, limit=72
        )
        production.append(
            {
                "seat": seat,
                "team_name": team_names[seat] if seat < len(team_names) else None,
                "action_count": full_count,
                "malformed_action_count": full_malformed,
                "production_action_sha256": full_hash,
                "production_lineage": f"prod-{full_hash[:16]}",
                "prefix72_action_count": prefix_count,
                "prefix72_malformed_action_count": prefix_malformed,
                "prefix72_sha256": prefix_hash,
                "prefix72_lineage": f"prefix72-{prefix_hash[:16]}",
            }
        )

    expected_steps = config.get("episodeSteps", 720)
    if not isinstance(expected_steps, int):
        expected_steps = 720
    missing_fields: list[str] = []
    required = {
        "episode_id": episode_id,
        "seed": seed,
        "team_names": team_names,
        "final_rewards": final_rewards,
        "final_statuses": final_statuses,
        "steps": steps,
    }
    for field, value in required.items():
        if _value_missing(value):
            missing_fields.append(field)
    if len(team_names) != 2:
        missing_fields.append("team_names_length_2")
    if len(final_rewards) != 2:
        missing_fields.append("final_rewards_length_2")
    if len(final_statuses) != 2:
        missing_fields.append("final_statuses_length_2")

    top_level_done = len(final_statuses) == 2 and all(
        status == "DONE" for status in final_statuses
    )
    terminal_done = len(terminal_statuses) == 2 and all(
        status == "DONE" for status in terminal_statuses
    )
    rewards_consistent = final_rewards == terminal_rewards
    statuses_consistent = final_statuses == terminal_statuses
    malformed_actions = sum(item["malformed_action_count"] for item in production)
    eligible = (
        not missing_fields
        and len(steps) == expected_steps
        and top_level_done
        and terminal_done
        and rewards_consistent
        and statuses_consistent
        and malformed_actions == 0
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "date": date,
        "source_date": date,
        "source_relpath": path.relative_to(source_root).as_posix(),
        "source_size_bytes": path.stat().st_size,
        "source_sha256": replay_sha256,
        "episode_id": episode_id,
        "episode_uuid": payload.get("id"),
        "seed": seed,
        "team_names": team_names,
        "final_rewards": final_rewards,
        "final_statuses": final_statuses,
        "terminal_rewards": terminal_rewards,
        "terminal_statuses": terminal_statuses,
        "steps_len": len(steps),
        "expected_steps": expected_steps,
        "module_version": payload.get("module_version"),
        "production": production,
        "production_lineages": [item["production_lineage"] for item in production],
        "production_action_sha256": [
            item["production_action_sha256"] for item in production
        ],
        "prefix72_sha256": [item["prefix72_sha256"] for item in production],
        "prefix72_lineages": [item["prefix72_lineage"] for item in production],
        "quality": {
            "missing_fields": sorted(set(missing_fields)),
            "top_level_done": top_level_done,
            "terminal_done": terminal_done,
            "rewards_consistent": rewards_consistent,
            "statuses_consistent": statuses_consistent,
            "malformed_production_actions": malformed_actions,
            "eligible_for_evaluation": eligible,
        },
    }


class UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))
        self.rank = [0] * size

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: int, right: int) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root == right_root:
            return
        if self.rank[left_root] < self.rank[right_root]:
            left_root, right_root = right_root, left_root
        self.parent[right_root] = left_root
        if self.rank[left_root] == self.rank[right_root]:
            self.rank[left_root] += 1


def form_identity_groups(records: Sequence[dict[str, Any]]) -> dict[str, list[int]]:
    """Union records sharing either episode id or seed."""

    uf = UnionFind(len(records))
    first_seen: dict[tuple[str, str], int] = {}
    for index, record in enumerate(records):
        identities: list[tuple[str, str]] = []
        if record.get("episode_id") is not None:
            identities.append(("episode", str(record["episode_id"])))
        if record.get("seed") is not None:
            identities.append(("seed", str(record["seed"])))
        for identity in identities:
            if identity in first_seen:
                uf.union(index, first_seen[identity])
            else:
                first_seen[identity] = index

    members_by_root: dict[int, list[int]] = defaultdict(list)
    for index in range(len(records)):
        members_by_root[uf.find(index)].append(index)

    result: dict[str, list[int]] = {}
    for members in members_by_root.values():
        tokens: list[str] = []
        for index in members:
            record = records[index]
            tokens.append(f"episode:{record.get('episode_id')}")
            tokens.append(f"seed:{record.get('seed')}")
        canonical = "|".join(sorted(set(tokens)))
        group_id = "identity-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]
        result[group_id] = sorted(members)
    return result


def _stable_score(salt: str, value: str) -> str:
    return hashlib.sha256(f"{salt}|{value}".encode("utf-8")).hexdigest()


def assign_splits(
    records: Sequence[dict[str, Any]],
    groups: Mapping[str, Sequence[int]],
    ratios: Mapping[str, float] = DEFAULT_SPLIT_RATIOS,
    salt: str = DEFAULT_SPLIT_SALT,
    min_test_unique_seeds: int = 100,
) -> dict[str, str]:
    """Assign whole groups using date + common-prefix-lineage stratification.

    This is a deterministic iterative multi-label split.  Every replay adds a
    date label; prefix72 lineage labels are added only when they occur at least
    ten times, because a singleton lineage cannot meaningfully be represented
    in three splits.  The identity group remains indivisible throughout.
    """

    if not math.isclose(sum(ratios.values()), 1.0, abs_tol=1e-9):
        raise ValueError("split ratios must sum to one")
    raw_group_labels: dict[str, Counter[str]] = {}
    raw_lineage_totals: Counter[str] = Counter()
    for group_id, members in groups.items():
        labels: Counter[str] = Counter()
        for index in members:
            record = records[index]
            date = str(record["date"])
            labels[f"date:{date}"] += 1
            for item in record["production"]:
                lineage_label = f"date-prefix72:{date}:{item['prefix72_lineage']}"
                labels[lineage_label] += 1
                raw_lineage_totals[lineage_label] += 1
        raw_group_labels[group_id] = labels

    group_labels: dict[str, Counter[str]] = {}
    label_totals: Counter[str] = Counter()
    for group_id, labels in raw_group_labels.items():
        filtered = Counter(
            {
                label: count
                for label, count in labels.items()
                if label.startswith("date:") or raw_lineage_totals[label] >= 10
            }
        )
        group_labels[group_id] = filtered
        label_totals.update(filtered)

    # Rarer common lineages are placed first; stable hashes break all ties.
    ordered_groups = sorted(
        groups,
        key=lambda group_id: (
            min(label_totals[label] for label in group_labels[group_id]),
            -len(groups[group_id]),
            _stable_score(salt, group_id),
        ),
    )
    split_order = ("train", "val", "test")
    total_records = sum(len(members) for members in groups.values())
    split_targets = {split: total_records * ratios[split] for split in split_order}
    label_targets = {
        label: {split: count * ratios[split] for split in split_order}
        for label, count in label_totals.items()
    }
    split_current: Counter[str] = Counter()
    label_current: dict[str, Counter[str]] = defaultdict(Counter)
    assignments: dict[str, str] = {}
    for group_id in ordered_groups:
        size = len(groups[group_id])
        labels = group_labels[group_id]
        scored: list[tuple[float, str, str]] = []
        for split in split_order:
            target = split_targets[split]
            before = split_current[split] - target
            overall_delta = ((before + size) ** 2 - before**2) / max(target, 1.0)
            label_delta = 0.0
            for label, count in labels.items():
                label_target = label_targets[label][split]
                label_before = label_current[label][split] - label_target
                label_delta += (
                    (label_before + count) ** 2 - label_before**2
                ) / max(label_target, 1.0)
            score = overall_delta + label_delta
            scored.append((score, _stable_score(salt + "|tie", f"{group_id}|{split}"), split))
        _, _, selected_split = min(scored)
        assignments[group_id] = selected_split
        split_current[selected_split] += size
        for label, count in labels.items():
            label_current[label][selected_split] += count

    def test_seed_set() -> set[Any]:
        return {
            records[index]["seed"]
            for group_id, members in groups.items()
            if assignments[group_id] == "test"
            for index in members
            if records[index]["quality"]["eligible_for_evaluation"]
            and records[index].get("seed") is not None
        }

    all_dates = {str(record["date"]) for record in records}
    test_dates = {
        str(records[index]["date"])
        for group_id, members in groups.items()
        if assignments[group_id] == "test"
        for index in members
        if records[index]["quality"]["eligible_for_evaluation"]
    }
    candidate_groups = sorted(
        (
            group_id
            for group_id in groups
            if assignments[group_id] != "test"
            and any(
                records[index]["quality"]["eligible_for_evaluation"]
                for index in groups[group_id]
            )
        ),
        key=lambda item: _stable_score(salt + "|rebalance", item),
    )
    for missing_date in sorted(all_dates - test_dates):
        candidate = next(
            (
                group_id
                for group_id in candidate_groups
                if any(str(records[index]["date"]) == missing_date for index in groups[group_id])
            ),
            None,
        )
        if candidate is not None:
            assignments[candidate] = "test"
            candidate_groups.remove(candidate)
    while len(test_seed_set()) < min_test_unique_seeds and candidate_groups:
        existing = test_seed_set()
        candidate = next(
            (
                group_id
                for group_id in candidate_groups
                if any(
                    records[index].get("seed") not in existing
                    and records[index].get("seed") is not None
                    for index in groups[group_id]
                    if records[index]["quality"]["eligible_for_evaluation"]
                )
            ),
            None,
        )
        if candidate is None:
            break
        assignments[candidate] = "test"
        candidate_groups.remove(candidate)
    return assignments


def _duplicates(values: Iterable[Any]) -> dict[str, int]:
    counts = Counter(str(value) for value in values if value is not None)
    return {key: count for key, count in sorted(counts.items()) if count > 1}


def verify_no_leakage(records: Sequence[dict[str, Any]]) -> dict[str, Any]:
    by_episode: dict[str, set[str]] = defaultdict(set)
    by_seed: dict[str, set[str]] = defaultdict(set)
    for record in records:
        if record.get("episode_id") is not None:
            by_episode[str(record["episode_id"])].add(record["split"])
        if record.get("seed") is not None:
            by_seed[str(record["seed"])].add(record["split"])
    episode_leaks = {key: sorted(value) for key, value in by_episode.items() if len(value) > 1}
    seed_leaks = {key: sorted(value) for key, value in by_seed.items() if len(value) > 1}
    return {
        "episode_id_leak_count": len(episode_leaks),
        "seed_leak_count": len(seed_leaks),
        "episode_id_leak_examples": dict(list(episode_leaks.items())[:20]),
        "seed_leak_examples": dict(list(seed_leaks.items())[:20]),
        "passed": not episode_leaks and not seed_leaks,
    }


def build_quality_report(
    records: Sequence[dict[str, Any]],
    parse_errors: Sequence[dict[str, str]],
    source_root: Path,
    dates: Sequence[str],
    discovered_by_date: Mapping[str, int],
    groups: Mapping[str, Sequence[int]],
    min_test_unique_seeds: int,
    elapsed_seconds: float,
) -> dict[str, Any]:
    episode_duplicates = _duplicates(record.get("episode_id") for record in records)
    uuid_duplicates = _duplicates(record.get("episode_uuid") for record in records)
    seed_duplicates = _duplicates(record.get("seed") for record in records)
    missing_counts = Counter(
        field
        for record in records
        for field in record["quality"]["missing_fields"]
    )
    complete_hashes = Counter(
        item["production_action_sha256"]
        for record in records
        for item in record["production"]
    )
    prefix_hashes = Counter(
        item["prefix72_sha256"] for record in records for item in record["production"]
    )
    steps_distribution = Counter(str(record["steps_len"]) for record in records)
    split_counts = Counter(record["split"] for record in records)
    eligible_split_counts = Counter(
        record["split"]
        for record in records
        if record["quality"]["eligible_for_evaluation"]
    )
    split_by_date: dict[str, dict[str, int]] = {}
    for date in dates:
        split_by_date[date] = dict(
            Counter(record["split"] for record in records if record["date"] == date)
        )
    unique_seeds_by_split = {
        split: len(
            {
                record["seed"]
                for record in records
                if record["split"] == split
                and record["quality"]["eligible_for_evaluation"]
                and record.get("seed") is not None
            }
        )
        for split in ("train", "val", "test")
    }
    test_dates = sorted(
        {
            record["date"]
            for record in records
            if record["split"] == "test"
            and record["quality"]["eligible_for_evaluation"]
        }
    )
    leakage = verify_no_leakage(records)
    top_full = [
        {"sha256": key, "seat_trajectories": count}
        for key, count in complete_hashes.most_common(20)
    ]
    top_prefix = [
        {"sha256": key, "seat_trajectories": count}
        for key, count in prefix_hashes.most_common(20)
    ]
    critical_missing = sum(missing_counts.values())
    eligible_count = sum(
        record["quality"]["eligible_for_evaluation"] for record in records
    )
    all_done = sum(
        record["quality"]["top_level_done"]
        and record["quality"]["terminal_done"]
        for record in records
    )
    data_quality_passed = (
        not parse_errors
        and not episode_duplicates
        and not uuid_duplicates
        and critical_missing == 0
        and eligible_count == len(records)
        and leakage["passed"]
        and unique_seeds_by_split["test"] >= min_test_unique_seeds
        and set(test_dates) == set(dates)
    )
    warnings: list[str] = []
    if seed_duplicates:
        warnings.append(
            "Repeated seeds are present; all corresponding episodes were kept in one split."
        )
    if _orjson is None:
        warnings.append("orjson is unavailable; the standard-library json fallback was used.")
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "root": str(source_root.resolve()),
            "dates": list(dates),
            "discovered_json_files": sum(discovered_by_date.values()),
            "discovered_by_date": dict(discovered_by_date),
            "parsed_files": len(records),
            "parser": "orjson" if _orjson is not None else "json",
            "elapsed_seconds": round(elapsed_seconds, 3),
        },
        "uniqueness": {
            "unique_episode_ids": len(
                {record.get("episode_id") for record in records if record.get("episode_id") is not None}
            ),
            "duplicate_episode_id_count": len(episode_duplicates),
            "duplicate_episode_ids": episode_duplicates,
            "unique_episode_uuids": len(
                {record.get("episode_uuid") for record in records if record.get("episode_uuid") is not None}
            ),
            "duplicate_episode_uuid_count": len(uuid_duplicates),
            "duplicate_episode_uuids": uuid_duplicates,
            "unique_seeds": len(
                {record.get("seed") for record in records if record.get("seed") is not None}
            ),
            "duplicate_seed_value_count": len(seed_duplicates),
            "duplicate_seed_episode_count": sum(seed_duplicates.values()),
            "duplicate_seed_values": seed_duplicates,
        },
        "missing": {
            "records_with_missing_fields": sum(
                bool(record["quality"]["missing_fields"]) for record in records
            ),
            "missing_field_occurrences": dict(sorted(missing_counts.items())),
            "parse_error_count": len(parse_errors),
            "parse_errors": list(parse_errors),
        },
        "completion": {
            "all_done_records": all_done,
            "not_all_done_records": len(records) - all_done,
            "eligible_for_evaluation": eligible_count,
            "ineligible_for_evaluation": len(records) - eligible_count,
            "steps_len_distribution": dict(sorted(steps_distribution.items(), key=lambda item: int(item[0]))),
            "reward_mismatch_records": sum(
                not record["quality"]["rewards_consistent"] for record in records
            ),
            "status_mismatch_records": sum(
                not record["quality"]["statuses_consistent"] for record in records
            ),
            "malformed_production_action_records": sum(
                record["quality"]["malformed_production_actions"] > 0
                for record in records
            ),
        },
        "production_lineages": {
            "hash_schema": ACTION_HASH_SCHEMA,
            "semantic_scope": (
                "observed replay-action provenance only; this is not the curated "
                "expert-family/LOLO root lineage"
            ),
            "prefix72_definition": "step indices 0..71 inclusive",
            "seat_trajectories": sum(len(record["production"]) for record in records),
            "unique_complete_hashes": len(complete_hashes),
            "unique_prefix72_hashes": len(prefix_hashes),
            "top_complete_hashes": top_full,
            "top_prefix72_hashes": top_prefix,
        },
        "split": {
            "policy": "deterministic iterative date+common-prefix72-lineage identity-group split",
            "lineage_stratum_min_seat_trajectories": 10,
            "ratios": DEFAULT_SPLIT_RATIOS,
            "identity_group_count": len(groups),
            "record_counts": dict(split_counts),
            "eligible_record_counts": dict(eligible_split_counts),
            "record_counts_by_date": split_by_date,
            "eligible_unique_seeds_by_split": unique_seeds_by_split,
            "test_dates": test_dates,
            "minimum_test_unique_seeds": min_test_unique_seeds,
            "leakage": leakage,
        },
        "warnings": warnings,
        "data_quality_passed": data_quality_passed,
    }


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def write_outputs(
    records: Sequence[dict[str, Any]],
    report: Mapping[str, Any],
    output_dir: Path,
    dates: Sequence[str],
    split_salt: str,
) -> None:
    manifest_path = output_dir / "official_replay_manifest.jsonl"
    manifest_text = "".join(
        json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
        for record in records
    )
    _atomic_write_text(manifest_path, manifest_text)
    _atomic_write_text(
        output_dir / "data_quality_report.json",
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )

    splits: dict[str, dict[str, Any]] = {}
    for split in ("train", "val", "test"):
        selected = [
            record
            for record in records
            if record["split"] == split
            and record["quality"]["eligible_for_evaluation"]
        ]
        splits[split] = {
            "episode_count": len(selected),
            "unique_seed_count": len({record["seed"] for record in selected}),
            "seeds": sorted({record["seed"] for record in selected}),
            "records": [
                {
                    "date": record["date"],
                    "source_date": record["source_date"],
                    "split": record["split"],
                    "episode_id": record["episode_id"],
                    "seed": record["seed"],
                    "source_relpath": record["source_relpath"],
                    "team_names": record["team_names"],
                    "final_rewards": record["final_rewards"],
                    "final_statuses": record["final_statuses"],
                    "identity_group": record["identity_group"],
                    "production_lineages": [
                        item["production_lineage"] for item in record["production"]
                    ],
                    "prefix72_lineages": [
                        item["prefix72_lineage"] for item in record["production"]
                    ],
                    "production_action_sha256": record["production_action_sha256"],
                    "prefix72_sha256": record["prefix72_sha256"],
                }
                for record in selected
            ],
        }
    seed_manifest = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": report["generated_at_utc"],
        "source_dates": list(dates),
        "split_salt": split_salt,
        "grouping_keys": ["episode_id", "seed"],
        "lineage_semantics": (
            "production hashes describe observed official-replay action provenance; "
            "they are not the curated expert-family/LOLO root lineage"
        ),
        "eligibility": (
            "two DONE seats, expected step count, consistent terminal reward/status, "
            "no missing required field or malformed production action"
        ),
        "splits": splits,
    }
    _atomic_write_text(
        output_dir / "evaluation_seed_manifest.json",
        json.dumps(seed_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    flat_evaluation_rows = [
        {
            "schema_version": SCHEMA_VERSION,
            "seed": record["seed"],
            "date": record["date"],
            "source_date": record["source_date"],
            "split": record["split"],
            "episode_id": record["episode_id"],
            "identity_group": record["identity_group"],
            "source_relpath": record["source_relpath"],
            "team_names": record["team_names"],
            "final_statuses": record["final_statuses"],
            "production_lineages": record["production_lineages"],
            "production_action_sha256": record["production_action_sha256"],
            "prefix72_lineages": record["prefix72_lineages"],
            "prefix72_sha256": record["prefix72_sha256"],
        }
        for record in records
        if record["quality"]["eligible_for_evaluation"]
    ]
    _atomic_write_text(
        output_dir / "evaluation_seed_manifest.jsonl",
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
            for row in flat_evaluation_rows
        ),
    )


@dataclass(frozen=True)
class BuildResult:
    records: list[dict[str, Any]]
    report: dict[str, Any]


def build_manifest(
    source_root: Path,
    output_dir: Path,
    dates: Sequence[str] = DEFAULT_DATES,
    min_test_unique_seeds: int = 100,
    split_salt: str = DEFAULT_SPLIT_SALT,
    expected_files: int | None = 2090,
    progress_every: int = 100,
    max_files: int | None = None,
) -> BuildResult:
    started = time.monotonic()
    paths: list[tuple[str, Path]] = []
    discovered_by_date: dict[str, int] = {}
    for date in dates:
        date_dir = source_root / date
        if not date_dir.is_dir():
            raise FileNotFoundError(f"missing source date directory: {date_dir}")
        date_paths = sorted(date_dir.glob("*.json"), key=lambda item: item.name)
        discovered_by_date[date] = len(date_paths)
        paths.extend((date, path) for path in date_paths)
    if max_files is not None:
        paths = paths[:max_files]
        # Reflect what is actually processed in smoke mode.
        discovered_by_date = dict(Counter(date for date, _ in paths))
    if expected_files is not None and len(paths) != expected_files:
        raise ValueError(f"expected {expected_files} JSON files, discovered {len(paths)}")

    records: list[dict[str, Any]] = []
    parse_errors: list[dict[str, str]] = []
    total = len(paths)
    for number, (date, path) in enumerate(paths, start=1):
        try:
            records.append(extract_record(path, date, source_root))
        except Exception as exc:  # Keep auditing instead of hiding the rest of the corpus.
            parse_errors.append(
                {
                    "date": date,
                    "source_relpath": path.relative_to(source_root).as_posix(),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
        if progress_every and (number % progress_every == 0 or number == total):
            elapsed = time.monotonic() - started
            rate = number / elapsed if elapsed else 0.0
            print(
                f"[{number:4d}/{total}] parsed={len(records)} errors={len(parse_errors)} "
                f"rate={rate:.2f} files/s",
                flush=True,
            )
    records.sort(key=lambda record: (record["date"], str(record["episode_id"])))
    groups = form_identity_groups(records)
    assignments = assign_splits(
        records,
        groups,
        ratios=DEFAULT_SPLIT_RATIOS,
        salt=split_salt,
        min_test_unique_seeds=min_test_unique_seeds,
    )
    for group_id, member_indices in groups.items():
        for index in member_indices:
            records[index]["identity_group"] = group_id
            records[index]["split"] = assignments[group_id]
    report = build_quality_report(
        records=records,
        parse_errors=parse_errors,
        source_root=source_root,
        dates=dates,
        discovered_by_date=discovered_by_date,
        groups=groups,
        min_test_unique_seeds=min_test_unique_seeds,
        elapsed_seconds=time.monotonic() - started,
    )
    write_outputs(records, report, output_dir, dates, split_salt)
    return BuildResult(records=records, report=report)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--dates", nargs="+", default=list(DEFAULT_DATES))
    parser.add_argument("--min-test-unique-seeds", type=int, default=100)
    parser.add_argument("--split-salt", default=DEFAULT_SPLIT_SALT)
    parser.add_argument("--expected-files", type=int, default=2090)
    parser.add_argument("--progress-every", type=int, default=100)
    parser.add_argument("--max-files", type=int)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="return non-zero when the generated data-quality gate fails",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    expected_files = args.expected_files
    if args.max_files is not None and expected_files == 2090:
        expected_files = args.max_files
    result = build_manifest(
        source_root=args.source_root,
        output_dir=args.output_dir,
        dates=args.dates,
        min_test_unique_seeds=args.min_test_unique_seeds,
        split_salt=args.split_salt,
        expected_files=expected_files,
        progress_every=args.progress_every,
        max_files=args.max_files,
    )
    report = result.report
    print(
        json.dumps(
            {
                "data_quality_passed": report["data_quality_passed"],
                "parsed_files": report["source"]["parsed_files"],
                "eligible": report["completion"]["eligible_for_evaluation"],
                "unique_seeds": report["uniqueness"]["unique_seeds"],
                "test_unique_seeds": report["split"]["eligible_unique_seeds_by_split"]["test"],
                "output_dir": str(args.output_dir.resolve()),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 2 if args.strict and not report["data_quality_passed"] else 0


if __name__ == "__main__":
    sys.exit(main())
