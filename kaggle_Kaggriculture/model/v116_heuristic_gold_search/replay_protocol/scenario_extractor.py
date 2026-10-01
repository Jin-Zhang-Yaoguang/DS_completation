#!/usr/bin/env python3
"""Extract a fixed public-shop scenario through a streaming field whitelist."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .audit_registry import EXPECTED_CONFIG_SHA256, EXPECTED_MODULE, atomic_json_dump, canonical_sha256
    from .stream_whitelist import ReplayFormatError, read_replay_whitelist
except ImportError:  # direct-script execution
    from audit_registry import EXPECTED_CONFIG_SHA256, EXPECTED_MODULE, atomic_json_dump, canonical_sha256
    from stream_whitelist import ReplayFormatError, read_replay_whitelist


SCHEMA = "v116-fixed-public-shop-scenario-v1"
CAUSAL_CLASS = "protocol_fixed_realized_rng_coupled"
SHOPS: dict[str, tuple[str, ...]] = {
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
FORBIDDEN_OUTPUT_KEYS = {"action", "reward", "rewards", "farms", "private", "market", "agent", "agents"}


def _canonical_scenario_payload(
    module_version: str,
    configuration: dict[str, Any],
    seed: int,
    unlocks: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "module_version": module_version,
        "configuration": configuration,
        "actual_seed": seed,
        "realized_public_shops": unlocks,
        "causal_class": CAUSAL_CLASS,
    }


def _derive_unlocks(shops_by_step: tuple[tuple[str, ...], ...], turns_per_day: int) -> list[dict[str, Any]]:
    prior: tuple[str, ...] = tuple()
    unlocks: list[dict[str, Any]] = []
    for step, shops in enumerate(shops_by_step):
        if shops == prior:
            continue
        if len(shops) < len(prior) or shops[: len(prior)] != prior:
            raise ReplayFormatError(f"shop sequence is not monotone at replay step {step}")
        for ordinal, shop in enumerate(shops[len(prior) :], start=len(prior) + 1):
            if shop not in SHOPS:
                raise ReplayFormatError(f"unknown shop {shop!r} at replay step {step}")
            unlocks.append(
                {
                    "ordinal": ordinal,
                    "shop": shop,
                    "visible_from_step": step,
                    "day": step // turns_per_day,
                    "hour": step % turns_per_day,
                    "causal_class": CAUSAL_CLASS,
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
                products = SHOPS.get(shop)
                if products is None:
                    raise ReplayFormatError(f"unknown shop {shop!r}")
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
                raise AssertionError(f"forbidden output key {key!r} at {path}")
            _assert_output_whitelist(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_output_whitelist(child, f"{path}[{index}]")


def extract_scenario(replay_path: str | Path) -> dict[str, Any]:
    replay = read_replay_whitelist(replay_path, include_steps=True)
    if replay.module_version != EXPECTED_MODULE:
        raise ReplayFormatError(f"module version {replay.module_version!r} is not {EXPECTED_MODULE!r}")
    config_sha = canonical_sha256(replay.configuration)
    if config_sha != EXPECTED_CONFIG_SHA256:
        raise ReplayFormatError(f"configuration hash mismatch: {config_sha}")
    shops_by_step = replay.shops_by_step or tuple()
    turns_per_day = max(1, int(replay.configuration["turnsPerDay"]))
    unlocks = _derive_unlocks(shops_by_step, turns_per_day)
    demand = _derive_demand(shops_by_step, replay.configuration)
    payload = _canonical_scenario_payload(
        replay.module_version, replay.configuration, replay.seed, unlocks
    )
    scenario = {
        "schema": SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "episode_id": replay.episode_id,
        "replay_path": str(Path(replay_path).resolve()),
        "module_version": replay.module_version,
        "configuration": replay.configuration,
        "configuration_sha256": config_sha,
        "actual_seed": replay.seed,
        "causal_class": CAUSAL_CLASS,
        "online_feature_contract": "only shops visible in the current observation; never future unlocks",
        "step_count": len(shops_by_step),
        "realized_public_shops": unlocks,
        "derived_demand": demand,
        "scenario_sha256": canonical_sha256(payload),
        "forbidden_fields_materialized": False,
    }
    _assert_output_whitelist(scenario)
    return scenario


def _load_record(registry: dict[str, Any], source_class: str, episode_id: int) -> dict[str, Any]:
    matches = [
        row
        for row in registry.get("records", [])
        if row.get("source_class") == source_class and int(row.get("episode_id", -1)) == episode_id
    ]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one registry record, found {len(matches)}")
    record = matches[0]
    if not record.get("metadata_ready"):
        raise ValueError("registry record is not metadata-ready")
    return record


def _load_assignment(manifest: dict[str, Any], source_class: str, episode_id: int) -> dict[str, Any]:
    matches = [
        row
        for row in manifest.get("assignments", [])
        if row.get("source_class") == source_class and int(row.get("episode_id", -1)) == episode_id
    ]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one split assignment, found {len(matches)}")
    return matches[0]


def authorize_extraction(
    manifest: dict[str, Any], assignment: dict[str, Any], candidate_sha256: str | None
) -> None:
    if assignment.get("split") != "frozen":
        return
    lock = manifest.get("frozen_lock") or {}
    if lock.get("status") != "LOCKED":
        raise PermissionError("frozen content is locked; candidate hash has not been committed")
    expected = lock.get("candidate_sha256")
    if not candidate_sha256 or candidate_sha256 != expected:
        raise PermissionError("candidate hash does not match the frozen manifest lock")


def _verify_recomputed_hash(record: dict[str, Any]) -> None:
    if record.get("sha_state") != "recomputed" or not record.get("strict_ready"):
        raise PermissionError("frozen replay is not strict-ready; recomputed SHA256 is required")
    expected = record.get("replay_sha256")
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise PermissionError("strict-ready record has no valid replay SHA256")
    digest = hashlib.sha256()
    with Path(record["replay_path"]).open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    if digest.hexdigest() != expected:
        raise PermissionError("replay SHA256 changed after registry admission")


def extract_registered(
    registry_path: str | Path,
    manifest_path: str | Path,
    *,
    source_class: str,
    episode_id: int,
    candidate_sha256: str | None = None,
) -> dict[str, Any]:
    registry = json.loads(Path(registry_path).read_text(encoding="utf-8"))
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    record = _load_record(registry, source_class, episode_id)
    assignment = _load_assignment(manifest, source_class, episode_id)
    # This authorization check intentionally occurs before replay_path is opened.
    authorize_extraction(manifest, assignment, candidate_sha256)
    # Development and frozen Replay both require a recomputed file hash.  A
    # pending manifest claim cannot enforce episode_id + replay_sha256 dedup.
    _verify_recomputed_hash(record)
    scenario = extract_scenario(record["replay_path"])
    if scenario["episode_id"] != episode_id:
        raise ReplayFormatError("extracted episode id differs from registry")
    if scenario["actual_seed"] != record.get("actual_seed"):
        raise ReplayFormatError("extracted seed differs from registry")
    scenario["source_class"] = source_class
    scenario["split"] = assignment["split"]
    scenario["candidate_sha256"] = candidate_sha256 if assignment["split"] == "frozen" else None
    _assert_output_whitelist(scenario)
    return scenario


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument("--source", choices=("A_ACCOUNT_ONLINE", "B_OFFICIAL_DAILY"), required=True)
    parser.add_argument("--episode-id", type=int, required=True)
    parser.add_argument("--candidate-sha256")
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.candidate_sha256 and not re.fullmatch(r"[0-9a-f]{64}", args.candidate_sha256):
        raise SystemExit("--candidate-sha256 must be 64 lowercase hex characters")
    scenario = extract_registered(
        args.registry,
        args.split_manifest,
        source_class=args.source,
        episode_id=args.episode_id,
        candidate_sha256=args.candidate_sha256,
    )
    atomic_json_dump(scenario, args.output.resolve())
    print(json.dumps({"episode_id": args.episode_id, "scenario_sha256": scenario["scenario_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
