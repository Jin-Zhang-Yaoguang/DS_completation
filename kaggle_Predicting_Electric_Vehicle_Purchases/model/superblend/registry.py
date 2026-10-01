"""Candidate discovery, artifact validation and immutable snapshot handling."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np


SNAPSHOT_SCHEMA_VERSION = 1
ALLOWED_ARTIFACT_TYPES = {"atomic_model", "historical_ensemble", "benchmark"}
ALLOWED_SOURCE_SCOPES = {"local", "audited_public"}


class RegistryError(ValueError):
    """Raised when registry evidence is incomplete or internally inconsistent."""


def canonical_json_bytes(value: Any) -> bytes:
    """Return a stable UTF-8 representation suitable for hashing."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_int_array(values: np.ndarray) -> str:
    array = np.ascontiguousarray(values, dtype=np.int64)
    return hashlib.sha256(array.tobytes(order="C")).hexdigest()


def write_json_exclusive(path: Path, payload: Any) -> None:
    """Write JSON exactly once; existing evidence is never overwritten."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")


def split_artifact_ref(reference: str) -> tuple[str, str | None]:
    base, separator, selector = reference.partition("::")
    if not base:
        raise RegistryError("artifact reference has an empty path")
    if separator and not selector:
        raise RegistryError(f"artifact reference has an empty selector: {reference!r}")
    return base, selector if separator else None


def resolve_repo_path(repo_root: Path, reference: str) -> tuple[Path, str | None]:
    """Resolve a repository-relative artifact reference without allowing escape."""

    base, selector = split_artifact_ref(reference)
    relative = Path(base)
    if relative.is_absolute():
        raise RegistryError(f"artifact paths must be repository-relative: {reference}")
    root = repo_root.resolve()
    resolved = (root / relative).resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise RegistryError(f"artifact path escapes repository: {reference}") from exc
    if not resolved.is_file():
        raise RegistryError(f"artifact is not a regular file: {reference}")
    return resolved, selector


def _load_tabular_column(path: Path, selector: str | None) -> np.ndarray:
    if selector is None:
        raise RegistryError(f"tabular prediction requires a ::column selector: {path}")
    try:
        import pandas as pd
    except ImportError as exc:  # pragma: no cover - project environment has pandas
        raise RegistryError("pandas is required for CSV/Parquet prediction sources") from exc
    suffix = path.suffix.lower()
    if suffix == ".csv":
        frame = pd.read_csv(path, usecols=[selector])
    elif suffix in {".parquet", ".pq"}:
        frame = pd.read_parquet(path, columns=[selector])
    else:  # pragma: no cover - guarded by caller
        raise RegistryError(f"unsupported tabular artifact: {path}")
    return frame[selector].to_numpy(copy=False)


def load_prediction_readonly(repo_root: Path, reference: str) -> np.ndarray:
    """Load one prediction vector without ever mutating its source artifact."""

    path, selector = resolve_repo_path(repo_root, reference)
    suffix = path.suffix.lower()
    if suffix == ".npy":
        if selector is not None:
            raise RegistryError(f".npy artifacts do not accept selectors: {reference}")
        values = np.load(path, mmap_mode="r", allow_pickle=False)
    elif suffix in {".csv", ".parquet", ".pq"}:
        values = _load_tabular_column(path, selector)
    else:
        raise RegistryError(f"unsupported prediction format: {reference}")
    array = np.asarray(values)
    if array.ndim != 1:
        raise RegistryError(f"prediction must be one-dimensional: {reference}")
    if not np.issubdtype(array.dtype, np.number):
        raise RegistryError(f"prediction must be numeric: {reference}")
    try:
        array.flags.writeable = False
    except ValueError:
        pass
    return array


def inspect_prediction(
    repo_root: Path,
    reference: str,
    expected_rows: int,
) -> dict[str, Any]:
    path, selector = resolve_repo_path(repo_root, reference)
    values = load_prediction_readonly(repo_root, reference)
    if len(values) != expected_rows:
        raise RegistryError(
            f"row count mismatch for {reference}: {len(values)} != {expected_rows}"
        )
    if not np.isfinite(values).all():
        raise RegistryError(f"prediction contains NaN or Inf: {reference}")
    minimum = float(values.min())
    maximum = float(values.max())
    if minimum < 0.0 or maximum > 1.0:
        raise RegistryError(
            f"prediction is outside [0, 1]: {reference} min={minimum} max={maximum}"
        )
    return {
        "path": reference,
        "file_sha256": sha256_file(path),
        "file_size_bytes": path.stat().st_size,
        "selector": selector,
        "n_rows": int(len(values)),
        "dtype": str(values.dtype),
        "min": minimum,
        "max": maximum,
    }


def _read_json(path: Path) -> Any:
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise RegistryError(f"cannot read valid JSON from {path}") from exc


def _result_oof_auc(results: Mapping[str, Any]) -> float | None:
    for key in ("oof_auc", "crossfit_oof_auc", "fixed_weight_oof_auc"):
        value = results.get(key)
        if isinstance(value, (int, float)) and np.isfinite(value):
            return float(value)
    return None


def audit_model_root(repo_root: Path, model_root: str = "model") -> dict[str, Any]:
    """Perform a metadata-only inventory; this does not create a candidate pool."""

    model_path, selector = resolve_repo_path(repo_root, f"{model_root}/experiments.md")
    if selector is not None:  # pragma: no cover - defensive
        raise RegistryError("model root sentinel unexpectedly has a selector")
    model_dir = model_path.parent
    rows: list[dict[str, Any]] = []
    for directory in sorted(path for path in model_dir.iterdir() if path.is_dir()):
        result_path = directory / "cv_results.json"
        oof_path = directory / "oof_proba.npy"
        test_path = directory / "test_proba.npy"
        if not (result_path.exists() or oof_path.exists() or test_path.exists()):
            continue
        present = {
            "cv_results": result_path.is_file(),
            "oof": oof_path.is_file(),
            "test": test_path.is_file(),
        }
        rows.append(
            {
                "id": directory.name,
                "experiment_dir": directory.relative_to(repo_root.resolve()).as_posix(),
                "artifacts_present": present,
                "paired_predictions": present["oof"] and present["test"],
                "eligible": False,
                "reason": "inventory_only_requires_explicit_candidate_config",
            }
        )
    return {
        "schema_version": 1,
        "model_root": model_root,
        "inventory_count": len(rows),
        "experiments": rows,
    }


def _normalise_candidate(
    repo_root: Path,
    raw: Mapping[str, Any],
    expected_oof_rows: int,
    expected_test_rows: int,
) -> dict[str, Any]:
    required = {
        "id",
        "experiment_dir",
        "artifact_type",
        "family",
        "feature_mechanism",
        "split_seed",
        "source_scope",
        "inclusion_reason",
        "row_order_evidence",
    }
    missing = sorted(required.difference(raw))
    if missing:
        raise RegistryError(f"candidate is missing required fields {missing}: {raw.get('id')}")
    candidate_id = str(raw["id"])
    if not candidate_id or "/" in candidate_id or "\\" in candidate_id:
        raise RegistryError(f"invalid candidate id: {candidate_id!r}")
    artifact_type = str(raw["artifact_type"])
    if artifact_type not in ALLOWED_ARTIFACT_TYPES:
        raise RegistryError(f"unsupported artifact_type for {candidate_id}: {artifact_type}")
    source_scope = str(raw["source_scope"])
    if source_scope not in ALLOWED_SOURCE_SCOPES:
        raise RegistryError(f"unsupported source_scope for {candidate_id}: {source_scope}")
    audited_public = bool(raw.get("audited_public", False))
    if source_scope == "audited_public" and not audited_public:
        raise RegistryError(f"public candidate is not explicitly audited: {candidate_id}")

    row_evidence = raw["row_order_evidence"]
    if not isinstance(row_evidence, Mapping):
        raise RegistryError(f"row_order_evidence must be an object: {candidate_id}")
    for side in ("oof", "test"):
        if not isinstance(row_evidence.get(side), str) or not row_evidence[side].strip():
            raise RegistryError(f"missing {side} row-order evidence: {candidate_id}")

    experiment_dir = str(raw["experiment_dir"])
    relative_dir = Path(experiment_dir)
    if relative_dir.is_absolute():
        raise RegistryError(f"experiment_dir must be relative: {candidate_id}")
    resolved_dir = (repo_root.resolve() / relative_dir).resolve(strict=True)
    try:
        resolved_dir.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise RegistryError(f"experiment_dir escapes repository: {candidate_id}") from exc
    if not resolved_dir.is_dir():
        raise RegistryError(f"experiment_dir is not a directory: {candidate_id}")

    oof_reference = str(raw.get("oof", f"{experiment_dir}/oof_proba.npy"))
    test_reference = str(raw.get("test", f"{experiment_dir}/test_proba.npy"))
    result_reference = str(raw.get("cv_results", f"{experiment_dir}/cv_results.json"))
    result_path, result_selector = resolve_repo_path(repo_root, result_reference)
    if result_selector is not None:
        raise RegistryError(f"cv_results cannot have a column selector: {candidate_id}")
    results = _read_json(result_path)
    if not isinstance(results, Mapping):
        raise RegistryError(f"cv_results must contain a JSON object: {candidate_id}")

    oof_auc = raw.get("oof_auc", _result_oof_auc(results))
    if not isinstance(oof_auc, (int, float)) or not np.isfinite(oof_auc):
        raise RegistryError(f"no finite OOF AUC is available: {candidate_id}")
    n_folds = raw.get("n_folds", results.get("n_folds"))
    if n_folds is not None and (not isinstance(n_folds, int) or n_folds < 2):
        raise RegistryError(f"invalid n_folds for {candidate_id}: {n_folds}")

    declared_parents = raw.get("declared_parents", [])
    if not isinstance(declared_parents, list) or not all(
        isinstance(parent, str) and parent for parent in declared_parents
    ):
        raise RegistryError(f"declared_parents must be a string list: {candidate_id}")

    return {
        "id": candidate_id,
        "experiment_dir": relative_dir.as_posix(),
        "artifact_type": artifact_type,
        "eligible_for_optimization": bool(
            raw.get("eligible_for_optimization", artifact_type == "atomic_model")
        ),
        "family": str(raw["family"]),
        "feature_mechanism": str(raw["feature_mechanism"]),
        "split_seed": int(raw["split_seed"]),
        "n_folds": n_folds,
        "status": "COMPLETE",
        "source_scope": source_scope,
        "audited_public": audited_public,
        "inclusion_reason": str(raw["inclusion_reason"]),
        "cycle_id": raw.get("cycle_id"),
        "cycle_index": raw.get("cycle_index"),
        "oof_auc": float(oof_auc),
        "row_order_evidence": dict(row_evidence),
        "declared_parents": sorted(set(declared_parents)),
        "cv_results": {
            "path": result_reference,
            "file_sha256": sha256_file(result_path),
            "file_size_bytes": result_path.stat().st_size,
        },
        "oof": inspect_prediction(repo_root, oof_reference, expected_oof_rows),
        "test": inspect_prediction(repo_root, test_reference, expected_test_rows),
    }


def build_candidate_snapshot(
    repo_root: Path,
    config: Mapping[str, Any],
    expected_oof_rows: int,
    expected_test_rows: int,
) -> dict[str, Any]:
    """Build an in-memory, fully hashed snapshot from an explicit allow-list."""

    if config.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
        raise RegistryError(
            f"candidate config schema_version must be {SNAPSHOT_SCHEMA_VERSION}"
        )
    cycle_id = config.get("cycle_id")
    if not isinstance(cycle_id, str) or not cycle_id:
        raise RegistryError("candidate config requires a non-empty cycle_id")
    raw_candidates = config.get("candidates")
    if not isinstance(raw_candidates, list) or not raw_candidates:
        raise RegistryError("candidate config requires a non-empty candidates list")
    candidates = [
        _normalise_candidate(repo_root, raw, expected_oof_rows, expected_test_rows)
        for raw in raw_candidates
    ]
    ids = [candidate["id"] for candidate in candidates]
    if len(set(ids)) != len(ids):
        raise RegistryError("candidate ids must be unique")
    candidates.sort(key=lambda item: item["id"])
    snapshot = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "cycle_id": cycle_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_config_sha256": sha256_json(config),
        "expected_oof_rows": int(expected_oof_rows),
        "expected_test_rows": int(expected_test_rows),
        "candidate_count": len(candidates),
        "candidates": candidates,
    }
    return {
        "snapshot": snapshot,
        "snapshot_sha256": sha256_json(snapshot),
    }


def freeze_candidate_snapshot(
    repo_root: Path,
    config_path: Path,
    output_path: Path,
    expected_oof_rows: int,
    expected_test_rows: int,
) -> dict[str, Any]:
    """Validate and write a candidate snapshot without overwrite semantics."""

    config = _read_json(config_path)
    if not isinstance(config, Mapping):
        raise RegistryError("candidate config must contain a JSON object")
    envelope = build_candidate_snapshot(
        repo_root=repo_root,
        config=config,
        expected_oof_rows=expected_oof_rows,
        expected_test_rows=expected_test_rows,
    )
    write_json_exclusive(output_path, envelope)
    return envelope


def _verify_hashed_file(repo_root: Path, record: Mapping[str, Any]) -> None:
    path, _ = resolve_repo_path(repo_root, str(record["path"]))
    actual = sha256_file(path)
    expected = record.get("file_sha256")
    if actual != expected:
        raise RegistryError(f"frozen source hash changed: {record['path']}")


def load_candidate_snapshot(
    repo_root: Path,
    snapshot_path: Path,
    *,
    verify_sources: bool = True,
) -> dict[str, Any]:
    """Load a frozen snapshot and reject snapshot or source mutation."""

    envelope = _read_json(snapshot_path)
    if not isinstance(envelope, Mapping) or not isinstance(envelope.get("snapshot"), Mapping):
        raise RegistryError("invalid candidate snapshot envelope")
    snapshot = dict(envelope["snapshot"])
    actual_hash = sha256_json(snapshot)
    if actual_hash != envelope.get("snapshot_sha256"):
        raise RegistryError("candidate snapshot content hash mismatch")
    if snapshot.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
        raise RegistryError("unsupported candidate snapshot schema")
    if verify_sources:
        for candidate in snapshot.get("candidates", []):
            _verify_hashed_file(repo_root, candidate["cv_results"])
            for side in ("oof", "test"):
                _verify_hashed_file(repo_root, candidate[side])
                expected_rows = snapshot[f"expected_{side}_rows"]
                inspected = inspect_prediction(repo_root, candidate[side]["path"], expected_rows)
                if inspected["selector"] != candidate[side].get("selector"):
                    raise RegistryError(f"selector changed for {candidate['id']} {side}")
    return snapshot


def sources_manifest(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Create the immutable source receipt used by a superblend run."""

    sources = {}
    for candidate in snapshot["candidates"]:
        sources[candidate["id"]] = {
            "cv_results": candidate["cv_results"],
            "oof": candidate["oof"],
            "test": candidate["test"],
        }
    payload = {
        "schema_version": 1,
        "candidate_snapshot_sha256": sha256_json(snapshot),
        "sources": sources,
    }
    return {"manifest": payload, "manifest_sha256": sha256_json(payload)}


def candidate_by_id(snapshot: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    candidates: Iterable[Mapping[str, Any]] = snapshot.get("candidates", [])
    return {str(candidate["id"]): candidate for candidate in candidates}

