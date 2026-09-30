"""Fresh-source allocation with attempt-level and hidden single-use locks.

Only identity metadata from the official manifest is loaded.  Prior exposure is
reconstructed from metadata-only exposure inventories, panels, and seed
manifests; historical game outcomes are never opened here.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import fcntl
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable

from .protocol import (
    ALLOWED_SPLITS,
    DATES,
    HERE,
    MODEL_ROOT,
    PANEL_SOURCES,
    SOURCE_MANIFEST,
    atomic_create_json,
    canonical,
    file_sha256,
    hash_ints,
    normalise_split,
    validate_attempt_id,
)


STATE_ROOT = HERE / "state" / "private"
PANELS_ROOT = STATE_ROOT / "panels"
CAPACITY_AUDIT = HERE / "source_capacity_audit.json"

# One validation source per date preserves split coverage while allowing four
# fully fresh development+hidden attempts from the remaining official data.
STRATUM_QUOTAS = {
    ("2026-08-18", "train"): 33,
    ("2026-08-18", "validation"): 1,
    ("2026-08-19", "train"): 32,
    ("2026-08-19", "validation"): 1,
    ("2026-08-20", "train"): 32,
    ("2026-08-20", "validation"): 1,
}

EXPOSURE_NAME_RE = re.compile(r"(panel|seed_manifest|exposure_inventory)", re.I)
SEED_RE = re.compile(r"(?i)[\"']?seed[\"']?\s*[:=`\"']+\s*([0-9]{4,12})")


@dataclass(frozen=True)
class Source:
    date: str
    seed: int
    episode_id: str
    split: str
    source_path: str
    lineage_fold: str = ""


def load_official_sources() -> list[Source]:
    rows: list[Source] = []
    seen: dict[int, Source] = {}
    with SOURCE_MANIFEST.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            value = json.loads(line)
            split = normalise_split(value.get("split"))
            date = str(value.get("date") or value.get("source_date") or "")[:10]
            row = Source(
                date=date,
                seed=int(value["seed"]),
                episode_id=str(value.get("episode_id") or ""),
                split=split,
                source_path=str(value.get("source_path") or value.get("source_relpath") or ""),
                lineage_fold=str(value.get("lineage_fold") or ""),
            )
            previous = seen.setdefault(row.seed, row)
            if previous != row:
                raise ValueError(f"official seed is not globally unique: {row.seed}")
            rows.append(row)
    if not rows:
        raise ValueError("official source manifest is empty")
    return sorted(rows, key=lambda row: (row.date, row.split, row.seed, row.episode_id))


def _metadata_exposure_files() -> list[Path]:
    result: list[Path] = []
    for path in MODEL_ROOT.rglob("*"):
        if not path.is_file() or HERE.parent in path.parents:
            continue
        if path.name in {"evaluation_seed_manifest.json", "evaluation_seed_manifest.jsonl"}:
            continue
        if path.suffix.lower() not in {".json", ".jsonl"}:
            continue
        if not EXPOSURE_NAME_RE.search(path.name):
            continue
        if path.stat().st_size > 64 * 1024 * 1024:
            raise ValueError(f"oversized exposure metadata: {path}")
        result.append(path)
    return sorted(result)


def historical_exposure() -> tuple[set[int], list[dict[str, Any]]]:
    official = {row.seed for row in load_official_sources()}
    seeds: set[int] = set()
    evidence: list[dict[str, Any]] = []
    for path in _metadata_exposure_files():
        text = path.read_text(encoding="utf-8", errors="strict")
        matched = {int(value) for value in SEED_RE.findall(text)} & official
        if not matched:
            continue
        seeds.update(matched)
        evidence.append(
            {
                "path": str(path.resolve()),
                "file_sha256": file_sha256(path),
                "matched_seed_count": len(matched),
                "matched_seeds_sha256": hash_ints(matched),
            }
        )
    return seeds, evidence


def reserved_panels(state_root: Path = STATE_ROOT) -> list[dict[str, Any]]:
    root = state_root / "panels"
    if not root.exists():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(root.glob("attempt_*_*.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("schema") != "kaggriculture-v15-private-source-panel-1":
            raise ValueError(f"unknown panel state: {path}")
        rows.append(value)
    return rows


def reserved_seeds(state_root: Path = STATE_ROOT) -> set[int]:
    result: set[int] = set()
    for panel in reserved_panels(state_root):
        values = {int(row["seed"]) for row in panel["records"]}
        if result & values:
            raise ValueError("two V15 panels reuse a source seed")
        result.update(values)
    return result


def _rank(source: Source, attempt_id: str, stage: str) -> bytes:
    value = (
        f"kaggriculture-v15-fresh-panel-v1:{attempt_id}:{stage}:"
        f"{source.date}:{source.split}:{source.seed}:{source.episode_id}"
    )
    return hashlib.sha256(value.encode("utf-8")).digest()


def select_panel(
    attempt_id: str,
    stage: str,
    *,
    state_root: Path = STATE_ROOT,
    extra_excluded: Iterable[int] = (),
) -> dict[str, Any]:
    validate_attempt_id(attempt_id)
    if stage not in {"development", "hidden"}:
        raise ValueError("stage must be development or hidden")
    historical, evidence = historical_exposure()
    excluded = historical | reserved_seeds(state_root) | {int(value) for value in extra_excluded}
    sources = [
        row
        for row in load_official_sources()
        if row.date in DATES and row.split in ALLOWED_SPLITS and row.seed not in excluded
    ]
    selected: list[Source] = []
    for stratum, quota in STRATUM_QUOTAS.items():
        candidates = [row for row in sources if (row.date, row.split) == stratum]
        candidates.sort(key=lambda row: _rank(row, attempt_id, stage))
        if len(candidates) < quota:
            raise ValueError(f"insufficient fresh sources for {stratum}: {len(candidates)} < {quota}")
        selected.extend(candidates[:quota])
    if len(selected) != PANEL_SOURCES or len({row.seed for row in selected}) != PANEL_SOURCES:
        raise ValueError("fresh panel closure is not exactly 100 unique sources")
    if any(row.split not in ALLOWED_SPLITS or row.split == "test" for row in selected):
        raise PermissionError("test sources are permanently forbidden")
    selected.sort(key=lambda row: _rank(row, attempt_id, stage + ":shuffle"))
    records = [asdict(row) for row in selected]
    payload = {
        "schema": "kaggriculture-v15-private-source-panel-1",
        "attempt_id": attempt_id,
        "stage": stage,
        "status": "single_use_consumed_on_reservation",
        "records": records,
        "records_sha256": hashlib.sha256(canonical(records)).hexdigest(),
        "source_count": len(records),
        "environment_games_started": False,
        "test_source_count": 0,
        "historical_exposure_seed_count": len(historical),
        "historical_exposure_seeds_sha256": hash_ints(historical),
        "prior_v15_reserved_seed_count": len(reserved_seeds(state_root)),
        "metadata_evidence_files": len(evidence),
        "stratum_quotas": {f"{date}:{split}": quota for (date, split), quota in STRATUM_QUOTAS.items()},
    }
    return payload


def reserve_panel(attempt_id: str, stage: str, *, state_root: Path = STATE_ROOT) -> dict[str, Any]:
    """Reserve and consume a panel atomically, even if later execution fails."""

    validate_attempt_id(attempt_id)
    panels_root = state_root / "panels"
    panels_root.mkdir(parents=True, exist_ok=True)
    target = panels_root / f"{attempt_id}_{stage}.json"
    lock = state_root / "allocation.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        if target.is_file():
            existing = json.loads(target.read_text(encoding="utf-8"))
            if existing.get("attempt_id") != attempt_id or existing.get("stage") != stage:
                raise ValueError("existing panel reservation identity mismatch")
            return existing
        panel = select_panel(attempt_id, stage, state_root=state_root)
        atomic_create_json(target, panel)
        return panel


def capacity_audit(*, state_root: Path = STATE_ROOT) -> dict[str, Any]:
    official = load_official_sources()
    historical, evidence = historical_exposure()
    reserved = reserved_seeds(state_root)
    allowed = [row for row in official if row.date in DATES and row.split in ALLOWED_SPLITS]
    fresh = [row for row in allowed if row.seed not in historical and row.seed not in reserved]
    payload = {
        "schema": "kaggriculture-v15-source-capacity-audit-1",
        "source_manifest": str(SOURCE_MANIFEST.resolve()),
        "source_manifest_sha256": file_sha256(SOURCE_MANIFEST),
        "official_records": len(official),
        "allowed_train_validation_records": len(allowed),
        "historically_exposed_allowed_records": len({row.seed for row in allowed} & historical),
        "v15_reserved_records": len(reserved),
        "fresh_allowed_records": len(fresh),
        "metadata_evidence_files": len(evidence),
        "test_selected": False,
        "panel_sources": PANEL_SOURCES,
        "sources_per_full_attempt": PANEL_SOURCES * 2,
        "maximum_remaining_full_attempts": len(fresh) // (PANEL_SOURCES * 2),
        "games_started": False,
    }
    CAPACITY_AUDIT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload

