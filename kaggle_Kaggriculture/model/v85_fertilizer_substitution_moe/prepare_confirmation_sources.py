#!/usr/bin/env python3
"""Freeze V85's one-shot 256-source Confirmation set."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
BASE_PATH = HERE / "prepare_development_sources.py"
spec = importlib.util.spec_from_file_location("v85_source_preparer", BASE_PATH)
assert spec is not None and spec.loader is not None
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


CONFIRMATION_SALT = "kaggriculture-v85-fertilizer-substitution-confirm-v1"
CONFIRMATION_DATES = ("2026-08-12", "2026-08-13", "2026-08-14", "2026-08-15")


def main():
    base.SALT = CONFIRMATION_SALT
    base.DATES = CONFIRMATION_DATES
    base.QUOTA = 64
    base.MANIFEST = base.OUT / "confirmation_source_manifest.json"
    base.main()

    payload = json.loads(base.MANIFEST.read_text(encoding="utf-8"))
    payload["phase"] = "confirmation"
    payload["dates"] = list(CONFIRMATION_DATES)
    if len(payload.get("sources", [])) != 256:
        raise RuntimeError("Confirmation source count is not 256")
    base.MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # The shared deterministic selector labels rows as development internally;
    # relabel only this salt's newly appended records, leaving all prior ledger
    # entries byte-semantically unchanged.
    rows = []
    for line in base.LEDGER.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("salt") == CONFIRMATION_SALT:
            row["phase"] = "confirmation"
        rows.append(row)
    base.LEDGER.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    print(json.dumps({"status": "CONFIRMATION_FROZEN", "sources": 256,
                      "dates": list(CONFIRMATION_DATES)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
