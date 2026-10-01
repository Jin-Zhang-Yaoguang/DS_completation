"""Build and validate ensemble-to-atomic-model lineage graphs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .registry import RegistryError, sha256_json, split_artifact_ref, write_json_exclusive


def _normalised_ref(reference: str) -> str:
    path, selector = split_artifact_ref(reference)
    return f"{Path(path).as_posix()}::{selector}" if selector else Path(path).as_posix()


def _source_references(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if key in {"oof", "test"} and isinstance(nested, str):
                yield nested
            else:
                yield from _source_references(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _source_references(nested)


def _read_sources(path: Path) -> Mapping[str, Any]:
    try:
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise RegistryError(f"cannot read lineage source file: {path}") from exc
    if not isinstance(payload, Mapping):
        raise RegistryError(f"sources.json must contain an object: {path}")
    return payload


def _assert_acyclic(parents: Mapping[str, list[str]]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise RegistryError(f"lineage cycle detected at {node}")
        if node in visited:
            return
        visiting.add(node)
        for parent in parents.get(node, []):
            if parent in parents:
                visit(parent)
        visiting.remove(node)
        visited.add(node)

    for node in parents:
        visit(node)


def build_lineage(repo_root: Path, snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve parents from explicit declarations and historical sources.json files."""

    candidates = snapshot.get("candidates", [])
    candidate_ids = {str(candidate["id"]) for candidate in candidates}
    artifact_owner: dict[str, str] = {}
    for candidate in candidates:
        for side in ("oof", "test"):
            artifact_owner[_normalised_ref(candidate[side]["path"])] = candidate["id"]

    parents: dict[str, list[str]] = {}
    unresolved: dict[str, list[str]] = {}
    evidence: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        candidate_id = str(candidate["id"])
        found = set(candidate.get("declared_parents", []))
        unknown_declared = found.difference(candidate_ids)
        if unknown_declared:
            raise RegistryError(
                f"declared parents are outside the frozen snapshot for {candidate_id}: "
                f"{sorted(unknown_declared)}"
            )
        source_path = repo_root / candidate["experiment_dir"] / "sources.json"
        unresolved_refs: set[str] = set()
        referenced: list[str] = []
        if source_path.is_file():
            source_payload = _read_sources(source_path)
            for raw_reference in _source_references(source_payload):
                reference = _normalised_ref(raw_reference)
                referenced.append(reference)
                owner = artifact_owner.get(reference)
                if owner and owner != candidate_id:
                    found.add(owner)
                elif owner is None:
                    unresolved_refs.add(reference)
        if candidate_id in found:
            raise RegistryError(f"candidate declares itself as a lineage parent: {candidate_id}")
        parents[candidate_id] = sorted(found)
        unresolved[candidate_id] = sorted(unresolved_refs)
        evidence[candidate_id] = {
            "sources_json": (
                source_path.relative_to(repo_root).as_posix() if source_path.is_file() else None
            ),
            "referenced_prediction_sources": sorted(set(referenced)),
        }

    _assert_acyclic(parents)
    payload = {
        "schema_version": 1,
        "candidate_snapshot_sha256": sha256_json(snapshot),
        "parents": parents,
        "unresolved_prediction_sources": unresolved,
        "evidence": evidence,
    }
    return {"lineage": payload, "lineage_sha256": sha256_json(payload)}


def freeze_lineage(path: Path, lineage_envelope: Mapping[str, Any]) -> None:
    write_json_exclusive(path, lineage_envelope)


def ancestors(node: str, parents: Mapping[str, list[str]]) -> set[str]:
    found: set[str] = set()
    pending = list(parents.get(node, []))
    while pending:
        parent = pending.pop()
        if parent in found:
            continue
        found.add(parent)
        pending.extend(parents.get(parent, []))
    return found


def assert_no_lineage_overlap(
    selected_ids: Iterable[str], parents: Mapping[str, list[str]]
) -> None:
    selected = set(selected_ids)
    conflicts = {
        node: sorted(ancestors(node, parents).intersection(selected))
        for node in selected
        if ancestors(node, parents).intersection(selected)
    }
    if conflicts:
        raise RegistryError(f"selected pool contains parent/child lineage overlap: {conflicts}")

