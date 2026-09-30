"""Shared primitives for the V14 validation protocol.

Only metadata from the official manifest is loaded here.  No historical replay
payload and no test outcome is opened by the panel builder or verifier.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable


HERE = Path(__file__).resolve().parent
MODEL_ROOT = HERE.parents[1]
PROJECT_ROOT = MODEL_ROOT.parents[1]
V10_ROOT = MODEL_ROOT / "v10_replay_lolo_router"
SOURCE_MANIFEST = V10_ROOT / "evaluation_seed_manifest.jsonl"
V13_PROTOCOL = MODEL_ROOT / "v13_dual_anchor_search" / "protocol"
V13_EXPOSURE_INVENTORY = V13_PROTOCOL / "exposure_inventory.json"

DATES = ("2026-08-18", "2026-08-19", "2026-08-20")
ALLOWED_SPLITS = {"train", "validation"}
ANCHORS = ("v12_incumbent_r002", "v12a2_no_shop_gate")

SCREEN_QUOTAS = {
    ("2026-08-18", "train"): 10,
    ("2026-08-18", "validation"): 2,
    ("2026-08-19", "train"): 10,
    ("2026-08-19", "validation"): 2,
    ("2026-08-20", "train"): 10,
    ("2026-08-20", "validation"): 2,
}
CONFIRMATORY_QUOTAS = {
    ("2026-08-18", "train"): 30,
    ("2026-08-18", "validation"): 4,
    ("2026-08-19", "train"): 29,
    ("2026-08-19", "validation"): 4,
    ("2026-08-20", "train"): 29,
    ("2026-08-20", "validation"): 4,
}

SCREEN_SALT = "kaggriculture-v14-dual-anchor-screen-20260824-v1"
CONFIRMATORY_SALT = "kaggriculture-v14-dual-anchor-confirmatory-20260824-v1"


@dataclass(frozen=True)
class Source:
    date: str
    seed: int
    episode_id: str
    split: str
    source_path: str
    lineage_fold: str = ""


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


def relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def normalise_split(value: Any) -> str:
    split = str(value or "").lower()
    return "validation" if split == "val" else split


def load_json(path: Path) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for key, value in pairs:
            if key in payload:
                raise ValueError(f"duplicate JSON key in {path}: {key}")
            payload[key] = value
        return payload

    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicates)
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def load_sources() -> list[Source]:
    """Load only the source identity fields needed to seed a closed-loop game."""

    rows: list[Source] = []
    with SOURCE_MANIFEST.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            payload = json.loads(line)
            date = str(payload.get("date") or payload.get("source_date") or "")[:10]
            split = normalise_split(payload.get("split"))
            if date not in DATES or split not in ALLOWED_SPLITS:
                continue
            rows.append(
                Source(
                    date=date,
                    seed=int(payload["seed"]),
                    episode_id=str(payload.get("episode_id") or ""),
                    split=split,
                    source_path=str(
                        payload.get("source_path") or payload.get("source_relpath") or ""
                    ),
                    lineage_fold=str(payload.get("lineage_fold") or ""),
                )
            )
    if not rows:
        raise ValueError("official train/validation metadata is empty")
    by_seed: dict[int, Source] = {}
    for row in rows:
        previous = by_seed.setdefault(row.seed, row)
        if previous != row:
            raise ValueError(f"official environment seed is not unique: {row.seed}")
    return sorted(rows, key=lambda row: (row.date, row.split, row.seed, row.episode_id))


def source_dict(row: Source) -> dict[str, Any]:
    return asdict(row)


def finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )

