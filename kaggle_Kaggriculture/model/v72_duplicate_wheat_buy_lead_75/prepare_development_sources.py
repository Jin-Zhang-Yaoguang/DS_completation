#!/usr/bin/env python3
"""Deterministically freeze the V72 date/shop-stratified official source set."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import re


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
INDEX = PROJECT / "model_data/kaggriculture_episodes_index"
OUT = PROJECT / "model_data/loop_evaluations/v72_duplicate_wheat_buy_lead_75"
MANIFEST = OUT / "development_source_manifest.json"
LEDGER = PROJECT / "model_data/loop_evaluations/exposure_ledger.jsonl"
SALT = "kaggriculture-v72-dev-v1"
DATES = ["2026-08-18", "2026-08-19"]
DATE_QUOTAS = {date: 32 for date in DATES}
POOL_PER_DATE = 200
SEED_RE = re.compile(rb'"seed"\s*:\s*([0-9]+)')
SHOPS_RE = re.compile(rb'"unlocked_shops"\s*:\s*(\[[^\]]*\])')


def rank_key(*parts: object) -> str:
    return hashlib.sha256(":".join([SALT, *map(str, parts)]).encode()).hexdigest()


def inspect_replay(path: Path) -> tuple[int, list[str]]:
    payload = path.read_bytes()
    seeds = SEED_RE.findall(payload)
    if not seeds:
        raise ValueError(f"seed missing: {path}")
    sequences: list[list[str]] = []
    previous: list[str] | None = None
    for match in SHOPS_RE.finditer(payload):
        shops = json.loads(match.group(1))
        if shops and shops != previous:
            sequences.append([str(value) for value in shops])
            previous = shops
        if len(shops) >= 3:
            break
    if not sequences:
        raise ValueError(f"shop regime missing: {path}")
    return int(seeds[-1]), sequences[-1]


def existing_exposure() -> tuple[set[str], set[int]]:
    ids: set[str] = set()
    seeds: set[int] = set()
    if not LEDGER.exists():
        return ids, seeds
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        ids.add(str(row["episode_id"]))
        seeds.add(int(row["seed"]))
    return ids, seeds


def main() -> None:
    if MANIFEST.exists():
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
        if payload.get("salt") != SALT or len(payload.get("sources", [])) != 64:
            raise RuntimeError("existing V72 source manifest does not match frozen protocol")
        print(json.dumps({"status": "ALREADY_FROZEN", "sources": 64}, ensure_ascii=False))
        return
    exposed_ids, exposed_seeds = existing_exposure()
    inspected: list[dict[str, object]] = []
    for date in DATES:
        base = INDEX / f"date={date}/data"
        with (base / "manifest.csv").open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        rows.sort(key=lambda row: rank_key(date, row["episode_id"]))
        accepted = 0
        for row in rows:
            episode_id = str(row["episode_id"])
            if episode_id in exposed_ids:
                continue
            source = base / f"{episode_id}.json"
            if not source.is_file():
                continue
            seed, shops = inspect_replay(source)
            if seed in exposed_seeds:
                continue
            inspected.append({
                "date": date,
                "episode_id": episode_id,
                "seed": seed,
                "shops": shops,
                "first_shop": shops[0],
                "source_path": str(source.relative_to(PROJECT)),
                "source_size_bytes": source.stat().st_size,
                "rank": rank_key(date, episode_id),
            })
            accepted += 1
            if accepted >= POOL_PER_DATE:
                break
        if accepted < POOL_PER_DATE:
            raise RuntimeError(f"insufficient eligible sources for {date}: {accepted}")

    selected: list[dict[str, object]] = []
    selected_seeds: set[int] = set()
    for date in DATES:
        groups: dict[str, list[dict[str, object]]] = {}
        for row in inspected:
            if row["date"] == date:
                groups.setdefault(str(row["first_shop"]), []).append(row)
        for values in groups.values():
            values.sort(key=lambda row: str(row["rank"]))
        shop_order = sorted(groups, key=lambda shop: rank_key(date, shop))
        while sum(row["date"] == date for row in selected) < DATE_QUOTAS[date]:
            progressed = False
            for shop in shop_order:
                if sum(row["date"] == date for row in selected) >= DATE_QUOTAS[date]:
                    break
                while groups[shop] and int(groups[shop][0]["seed"]) in selected_seeds:
                    groups[shop].pop(0)
                if groups[shop]:
                    row = groups[shop].pop(0)
                    selected.append(row)
                    selected_seeds.add(int(row["seed"]))
                    progressed = True
            if not progressed:
                raise RuntimeError(f"cannot satisfy date/shop quota for {date}")

    OUT.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "kaggriculture-loop-source-manifest-v1",
        "model_id": "v72_duplicate_wheat_buy_lead_75",
        "phase": "development",
        "salt": SALT,
        "dates": DATES,
        "date_quotas": DATE_QUOTAS,
        "pool_per_date": POOL_PER_DATE,
        "source_count": len(selected),
        "source_ids_unique": len({row["episode_id"] for row in selected}) == len(selected),
        "seeds_unique": len(selected_seeds) == len(selected),
        "candidate_archive_sha256": "aaa1628aa9416e88e6f1bd8bc9812c373a12a172bd0e69c4f797e97fcbad6979",
        "sources": selected,
    }
    MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with LEDGER.open("a", encoding="utf-8") as stream:
        for row in selected:
            stream.write(json.dumps({
                "model_id": "v72_duplicate_wheat_buy_lead_75",
                "phase": "development",
                "episode_id": row["episode_id"],
                "seed": row["seed"],
                "date": row["date"],
                "first_shop": row["first_shop"],
                "salt": SALT,
            }, ensure_ascii=False) + "\n")
    print(json.dumps({
        "status": "FROZEN",
        "sources": len(selected),
        "by_date": {date: sum(row["date"] == date for row in selected) for date in DATES},
        "by_first_shop": {
            shop: sum(row["first_shop"] == shop for row in selected)
            for shop in sorted({str(row["first_shop"]) for row in selected})
        },
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
