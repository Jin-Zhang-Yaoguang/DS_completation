"""Protocol constants and fail-closed helpers for the V15 evaluator."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Iterable


HERE = Path(__file__).resolve().parent
MODEL_ROOT = HERE.parents[1]
PROJECT_ROOT = MODEL_ROOT.parents[1]
V10_ROOT = MODEL_ROOT / "v10_replay_lolo_router"
SOURCE_MANIFEST = V10_ROOT / "evaluation_seed_manifest.jsonl"
SCORE_SCHEMA = HERE.parent / "cleanroom" / "score_only_feedback.schema.json"

DATES = ("2026-08-18", "2026-08-19", "2026-08-20")
ALLOWED_SPLITS = frozenset(("train", "validation"))
PANEL_SOURCES = 100
SEATS = (0, 1)
BOOTSTRAP_ROUNDS = 10_000

THRESHOLDS = {
    "primary_anchor_pure_win_rate_min": 0.65,
    "lineage_equal_pool_score_rate_min": 0.65,
    "lineage_equal_pool_score_ci95_low_min": 0.60,
    "paired_uplift_ci95_low_strict_min": 0.10,
}


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def normalise_split(value: Any) -> str:
    result = str(value or "").lower()
    return "validation" if result == "val" else result


def validate_attempt_id(value: str) -> str:
    if not re.fullmatch(r"attempt_[0-9]{3}", str(value)):
        raise ValueError("attempt id must match attempt_NNN")
    if value == "attempt_000":
        raise ValueError("attempt_000 is reserved for non-consuming dry-runs")
    return value


def unique_json_loads(text: str, *, source: str = "JSON") -> Any:
    def hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate key in {source}: {key}")
            result[key] = value
        return result

    return json.loads(text, object_pairs_hook=hook)


def atomic_create_json(path: Path, payload: Any) -> None:
    """Create an immutable state file; never overwrite existing evidence."""

    import os

    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        existing = unique_json_loads(path.read_text(encoding="utf-8"), source=str(path))
        if existing != payload:
            raise FileExistsError(f"immutable state differs: {path}")
        return
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())


def atomic_create_json_strict(path: Path, payload: Any) -> None:
    """Create one irreversible state record; any prior file is a hard failure."""

    import os

    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())


def hash_ints(values: Iterable[int]) -> str:
    return sha256_bytes(canonical(sorted({int(value) for value in values})))
