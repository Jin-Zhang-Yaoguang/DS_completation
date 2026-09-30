#!/usr/bin/env python3
"""Lock the strict RC2 gate to candidate and V76 parent source hashes."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "main.py"
MANIFEST = HERE / "gate_panel_manifest_rc2.json"
PARENT = HERE.parent / "v76_adjacent_safe_buy_lead/main.py"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    current = sha256(SOURCE)
    parent = sha256(PARENT)
    prior = data.get("candidate_lock") or {}
    if prior.get("status") == "LOCKED" and prior.get("main_sha256") != current:
        raise SystemExit("manifest is already locked to a different candidate")
    data["candidate_lock"] = {
        "status": "LOCKED",
        "main_sha256": current,
        "parent_main_sha256": parent,
        "locked_at": datetime.now(timezone.utc).isoformat(),
    }
    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(data["candidate_lock"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
