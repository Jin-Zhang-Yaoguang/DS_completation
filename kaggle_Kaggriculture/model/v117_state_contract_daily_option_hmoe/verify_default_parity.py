#!/usr/bin/env python3
"""Verify exact game-output parity between a frozen candidate and a new default."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


DEFAULT_FIELDS = (
    "candidate_reward",
    "v1_reward",
    "margin",
    "candidate_emitted_unit_actions",
    "candidate_emitted_market_orders",
    "candidate_emitted_market_units",
    "candidate_economy",
    "daily_totals",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load(path: Path, variant: str | None) -> dict[tuple[str, str, int], dict]:
    rows: dict[tuple[str, str, int], dict] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if variant is not None and row.get("variant") != variant:
                continue
            key = (row["source_class"], row["episode_id"], row["candidate_seat"])
            if key in rows:
                raise ValueError(f"duplicate game key: {key}")
            rows[key] = row
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen", type=Path, required=True)
    parser.add_argument("--experimental", type=Path, required=True)
    parser.add_argument("--variant")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    frozen = _load(args.frozen, None)
    experimental = _load(args.experimental, args.variant)
    shared = sorted(frozen.keys() & experimental.keys())
    mismatches = []
    for key in shared:
        for field in DEFAULT_FIELDS:
            if frozen[key].get(field) != experimental[key].get(field):
                mismatches.append({"game_key": list(key), "field": field})

    result = {
        "schema": "v117-r2.1-default-parity-v1",
        "frozen_games_sha256": _sha256(args.frozen),
        "experimental_games_sha256": _sha256(args.experimental),
        "experimental_variant": args.variant,
        "compared_games": len(shared),
        "frozen_game_count": len(frozen),
        "experimental_variant_game_count": len(experimental),
        "compared_fields": list(DEFAULT_FIELDS),
        "key_set_equal": set(frozen) == set(experimental),
        "mismatch_count": len(mismatches),
        "mismatches": mismatches[:100],
        "pass": bool(shared) and not mismatches,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
