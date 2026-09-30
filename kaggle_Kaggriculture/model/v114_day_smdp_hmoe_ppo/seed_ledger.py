"""Atomic seed exposure ledger for V114 train/dev/blind isolation."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import threading
from typing import Any, Iterable, Mapping


SCHEMA = "kaggriculture-v114-seed-ledger-v1"
VALID_SPLITS = {"train", "dev", "blind"}
VALID_STATUSES = {"fresh", "exposed"}


class DuplicateSeedError(ValueError):
    """Raised when any seed is reused across train/dev/blind or campaigns."""


class SeedLedger:
    """Persistent global seed ledger.

    A seed is first reserved as ``fresh`` and can transition exactly once to
    ``exposed``.  It can never be reserved again under another split, campaign,
    opponent, or seat.  One record represents a dual-seat seed block.
    """

    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path).resolve() if path is not None else None
        self._lock = threading.RLock()
        self._data: dict[str, Any] = {
            "schema": SCHEMA,
            "records": {},
        }
        if self.path is not None and self.path.exists():
            self._data = json.loads(self.path.read_text(encoding="utf-8"))
        self._validate()

    def _validate(self) -> None:
        if self._data.get("schema") != SCHEMA:
            raise ValueError("unsupported seed ledger schema")
        records = self._data.get("records")
        if not isinstance(records, dict):
            raise ValueError("seed ledger records must be an object")
        seen: set[int] = set()
        for key, row in records.items():
            seed = int(row.get("seed", -1))
            if key != str(seed) or seed < 0 or seed in seen:
                raise ValueError(f"invalid or duplicate ledger seed: {key}")
            seen.add(seed)
            if row.get("split") not in VALID_SPLITS:
                raise ValueError(f"invalid ledger split for seed {seed}")
            if row.get("status") not in VALID_STATUSES:
                raise ValueError(f"invalid ledger status for seed {seed}")
            if row.get("seats") != [0, 1]:
                raise ValueError(f"seed {seed} must reserve both seats")
            for field in ("campaign_id", "opponent_id", "registry_sha256"):
                if not row.get(field):
                    raise ValueError(f"seed {seed} missing ledger field: {field}")

    def _save(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self._data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        temp = self.path.with_name(f".{self.path.name}.{os.getpid()}.tmp")
        temp.write_text(payload, encoding="utf-8")
        os.replace(temp, self.path)

    @staticmethod
    def _validate_new_record(
        seed: int,
        split: str,
        campaign_id: str,
        opponent_id: str,
        registry_sha256: str,
    ) -> None:
        if int(seed) < 0:
            raise ValueError("seed must be non-negative")
        if split not in VALID_SPLITS:
            raise ValueError(f"split must be one of {sorted(VALID_SPLITS)}")
        if not campaign_id or not opponent_id or not registry_sha256:
            raise ValueError("campaign_id, opponent_id and registry_sha256 are required")

    def is_fresh(self, seed: int) -> bool:
        """True only if a seed has never been reserved or exposed."""

        return str(int(seed)) not in self._data["records"]

    def assert_fresh(self, seeds: Iterable[int]) -> None:
        values = [int(seed) for seed in seeds]
        duplicates = sorted(seed for seed in set(values) if values.count(seed) > 1)
        used = sorted(seed for seed in set(values) if not self.is_fresh(seed))
        if duplicates or used:
            raise DuplicateSeedError(
                f"seed blocks are not fresh; duplicate_input={duplicates}, already_used={used}"
            )

    def reserve(
        self,
        seed: int,
        *,
        split: str,
        campaign_id: str,
        opponent_id: str,
        registry_sha256: str,
    ) -> dict[str, Any]:
        """Reserve one fresh dual-seat seed block without exposing it."""

        seed = int(seed)
        self._validate_new_record(seed, split, campaign_id, opponent_id, registry_sha256)
        with self._lock:
            if not self.is_fresh(seed):
                prior = self._data["records"][str(seed)]
                raise DuplicateSeedError(
                    f"seed {seed} already {prior['status']} in {prior['split']}:{prior['campaign_id']}"
                )
            row = {
                "seed": seed,
                "split": split,
                "status": "fresh",
                "campaign_id": campaign_id,
                "opponent_id": opponent_id,
                "registry_sha256": registry_sha256,
                "seats": [0, 1],
            }
            self._data["records"][str(seed)] = row
            self._save()
            return deepcopy(row)

    def reserve_schedule(
        self,
        schedule: Iterable[Any],
        *,
        split: str,
        campaign_id: str,
        registry_sha256: str,
    ) -> list[dict[str, Any]]:
        """Atomically reserve every seed assignment or reserve none."""

        rows = list(schedule)
        seeds = [int(row.seed if hasattr(row, "seed") else row["seed"]) for row in rows]
        with self._lock:
            self.assert_fresh(seeds)
            staged: list[dict[str, Any]] = []
            for assignment in rows:
                seed = int(assignment.seed if hasattr(assignment, "seed") else assignment["seed"])
                opponent_id = (
                    assignment.opponent_id
                    if hasattr(assignment, "opponent_id")
                    else assignment["opponent_id"]
                )
                self._validate_new_record(
                    seed, split, campaign_id, str(opponent_id), registry_sha256
                )
                staged.append({
                    "seed": seed,
                    "split": split,
                    "status": "fresh",
                    "campaign_id": campaign_id,
                    "opponent_id": str(opponent_id),
                    "registry_sha256": registry_sha256,
                    "seats": [0, 1],
                })
            for row in staged:
                self._data["records"][str(row["seed"])] = row
            self._save()
            return deepcopy(staged)

    def mark_exposed(
        self,
        seed: int,
        *,
        split: str | None = None,
        campaign_id: str | None = None,
        opponent_id: str | None = None,
    ) -> dict[str, Any]:
        """Commit actual use; all supplied identity fields must match reservation."""

        seed = int(seed)
        with self._lock:
            row = self._data["records"].get(str(seed))
            if row is None:
                raise ValueError(f"seed {seed} must be reserved before exposure")
            if row["status"] == "exposed":
                raise DuplicateSeedError(f"seed {seed} is already exposed")
            checks = {
                "split": split,
                "campaign_id": campaign_id,
                "opponent_id": opponent_id,
            }
            for field, expected in checks.items():
                if expected is not None and row[field] != expected:
                    raise ValueError(
                        f"seed {seed} {field} mismatch: {row[field]!r} != {expected!r}"
                    )
            row["status"] = "exposed"
            self._save()
            return deepcopy(row)

    def mark_schedule_exposed(self, schedule: Iterable[Any]) -> list[dict[str, Any]]:
        rows = list(schedule)
        seeds = [int(row.seed if hasattr(row, "seed") else row["seed"]) for row in rows]
        if len(seeds) != len(set(seeds)):
            raise DuplicateSeedError("schedule repeats a seed block")
        with self._lock:
            for seed in seeds:
                record = self._data["records"].get(str(seed))
                if record is None or record["status"] != "fresh":
                    raise DuplicateSeedError(f"seed {seed} is not reserved fresh")
            for seed in seeds:
                self._data["records"][str(seed)]["status"] = "exposed"
            self._save()
            return [deepcopy(self._data["records"][str(seed)]) for seed in seeds]

    def snapshot(self) -> dict[str, Any]:
        records = [
            deepcopy(self._data["records"][key])
            for key in sorted(self._data["records"], key=int)
        ]
        return {
            "schema": SCHEMA,
            "records": records,
            "indexes": {
                "fresh": [row["seed"] for row in records if row["status"] == "fresh"],
                "exposed": [row["seed"] for row in records if row["status"] == "exposed"],
                "dev": [row["seed"] for row in records if row["split"] == "dev"],
                "blind": [row["seed"] for row in records if row["split"] == "blind"],
            },
        }

    def sha256(self) -> str:
        canonical = json.dumps(
            self.snapshot(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

