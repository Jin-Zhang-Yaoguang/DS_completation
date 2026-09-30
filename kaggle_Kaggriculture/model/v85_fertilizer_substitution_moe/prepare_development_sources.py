#!/usr/bin/env python3
"""Freeze V85's single-use, date/shop-stratified Development sources."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import re


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
INDEX = PROJECT / "model_data/kaggriculture_episodes_index"
OUT = PROJECT / "model_data/loop_evaluations/v85_fertilizer_substitution_moe"
MANIFEST = OUT / "development_source_manifest.json"
LEDGER = PROJECT / "model_data/loop_evaluations/exposure_ledger.jsonl"
SALT = "kaggriculture-v85-fertilizer-substitution-dev-v1"
DATES = ("2026-08-26", "2026-08-27")
QUOTA = 32
ARCHIVE_SHA = "c2e822ec1d56f76f2edb857b2877041a38257f876cbe14de7d2c4cbd153fe51f"
SEED_RE = re.compile(rb'"seed"\s*:\s*([0-9]+)')
SHOPS_RE = re.compile(rb'"unlocked_shops"\s*:\s*(\[[^\]]*\])')


def rank_key(*parts):
    return hashlib.sha256(":".join([SALT, *map(str, parts)]).encode()).hexdigest()


def inspect_replay(path: Path):
    payload = b""
    with path.open("rb") as stream:
        while len(payload) < 8 * 1024 * 1024:
            block = stream.read(1024 * 1024)
            if not block:
                break
            payload += block
            matches = SHOPS_RE.findall(payload)
            if any(len(json.loads(match)) >= 3 for match in matches):
                break
    seeds = SEED_RE.findall(payload)
    if not seeds:
        raise ValueError(f"seed missing: {path}")
    shops = []
    for match in SHOPS_RE.findall(payload):
        current = [str(value) for value in json.loads(match)]
        if current:
            shops = current
        if len(shops) >= 3:
            break
    if not shops:
        raise ValueError(f"shop regime missing: {path}")
    return int(seeds[-1]), shops


def existing_exposure():
    ids, seeds = set(), set()
    if LEDGER.exists():
        for line in LEDGER.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                ids.add(str(row["episode_id"]))
                seeds.add(int(row["seed"]))
    return ids, seeds


def main():
    if MANIFEST.exists():
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
        if payload.get("salt") != SALT or payload.get("candidate_archive_sha256") != ARCHIVE_SHA:
            raise RuntimeError("existing V85 manifest conflicts with frozen protocol")
        print(json.dumps({"status": "ALREADY_FROZEN", "sources": len(payload["sources"])}, ensure_ascii=False))
        return
    exposed_ids, exposed_seeds = existing_exposure()
    candidates = []
    for date in DATES:
        base = INDEX / f"date={date}/data"
        with (base / "manifest.csv").open(newline="", encoding="utf-8") as stream:
            rows = sorted(csv.DictReader(stream), key=lambda r: rank_key(date, r["episode_id"]))
        for row in rows:
            episode_id = str(row["episode_id"])
            path = base / f"{episode_id}.json"
            if episode_id in exposed_ids or not path.is_file():
                continue
            seed, shops = inspect_replay(path)
            if seed in exposed_seeds:
                continue
            candidates.append({"date": date, "episode_id": episode_id, "seed": seed,
                               "shops": shops, "first_shop": shops[0],
                               "source_path": str(path.relative_to(PROJECT)),
                               "source_size_bytes": path.stat().st_size,
                               "rank": rank_key(date, episode_id)})
    selected, selected_seeds = [], set()
    for date in DATES:
        groups = {}
        for row in candidates:
            if row["date"] == date:
                groups.setdefault(row["first_shop"], []).append(row)
        for values in groups.values():
            values.sort(key=lambda row: row["rank"])
        while sum(row["date"] == date for row in selected) < QUOTA:
            progressed = False
            for shop in sorted(groups, key=lambda value: rank_key(date, value)):
                while groups[shop] and groups[shop][0]["seed"] in selected_seeds:
                    groups[shop].pop(0)
                if groups[shop] and sum(row["date"] == date for row in selected) < QUOTA:
                    row = groups[shop].pop(0)
                    selected.append(row)
                    selected_seeds.add(row["seed"])
                    progressed = True
            if not progressed:
                raise RuntimeError(f"insufficient unexposed sources for {date}")
    OUT.mkdir(parents=True, exist_ok=True)
    payload = {"schema": "kaggriculture-loop-source-manifest-v1",
               "model_id": "v85_fertilizer_substitution_moe", "phase": "development",
               "salt": SALT, "dates": list(DATES), "date_quota": QUOTA,
               "source_count": len(selected), "source_ids_unique": len({r["episode_id"] for r in selected}) == len(selected),
               "seeds_unique": len(selected_seeds) == len(selected),
               "candidate_archive_sha256": ARCHIVE_SHA, "sources": selected}
    MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with LEDGER.open("a", encoding="utf-8") as stream:
        for row in selected:
            stream.write(json.dumps({"model_id": "v85_fertilizer_substitution_moe", "phase": "development",
                                     "episode_id": row["episode_id"], "seed": row["seed"], "date": row["date"],
                                     "first_shop": row["first_shop"], "salt": SALT}, ensure_ascii=False) + "\n")
    print(json.dumps({"status": "FROZEN", "sources": len(selected),
                      "by_date": {date: sum(r["date"] == date for r in selected) for date in DATES},
                      "by_first_shop": {shop: sum(r["first_shop"] == shop for r in selected)
                                        for shop in sorted({r["first_shop"] for r in selected})}},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
