"""Merge a V114 V6 base dataset with candidate-state DAgger datasets.

The base input must already implement the V6 latent-role/absorbing-STOP
contract.  Candidate-state DAgger inputs may use either the original Stage36
schema or that schema plus the four V6-derived arrays.  Every DAgger teacher
must match a teacher id, behavior family and checkpoint SHA256 recorded in the
base dataset.  No checkpoint or parent strategy is inherited by this data-only
composition.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import tempfile
from typing import Any, Iterable

import numpy as np

from build_latent_role_dataset import (
    MARKET_ROLE_NAMES,
    OPTION_IDS,
    STOP_ROLE,
    TERMINAL_STEP,
    UNIT_ROLE_NAMES,
    market_role,
    unit_role,
)
import action_space as space


CORE_KEYS = frozenset({
    "global", "board", "units", "unit_mask", "unit_tokens",
    "unit_quantities", "market_tokens", "market_quantities", "market_mask",
    "expert", "value", "split", "episode", "step", "seat", "unit_expert",
    "market_expert", "teacher_id", "teacher_family", "teacher_sha256",
})
DERIVED_KEYS = frozenset({"option_id", "unit_roles", "market_roles", "terminal_flag"})
BASE_KEYS = CORE_KEYS | DERIVED_KEYS
OUTPUT_PROVENANCE_KEYS = frozenset({"source_kind", "source_id", "source_episode"})
STRING_KEYS = frozenset({"teacher_id", "teacher_family", "teacher_sha256"})
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_npz(path: Path, arrays: dict[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", suffix=".npz", dir=path.parent, delete=False) as sink:
        np.savez_compressed(sink, **arrays)
        temporary = Path(sink.name)
    temporary.replace(path)


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as sink:
        json.dump(payload, sink, ensure_ascii=False, indent=2)
        sink.write("\n")
        temporary = Path(sink.name)
    temporary.replace(path)


def _load_exact(path: Path, allowed_schemas: tuple[frozenset[str], ...], label: str) -> dict[str, np.ndarray]:
    if not path.is_file():
        raise FileNotFoundError(f"{label} dataset does not exist: {path}")
    with np.load(path, allow_pickle=False) as archive:
        keys = frozenset(archive.files)
        if keys not in allowed_schemas:
            expected = [sorted(schema) for schema in allowed_schemas]
            raise ValueError(
                f"{label} array schema mismatch: found={sorted(keys)}, expected_one_of={expected}"
            )
        return {key: archive[key] for key in archive.files}


def _validate_rows(arrays: dict[str, np.ndarray], label: str) -> int:
    rows = len(arrays["episode"])
    if rows == 0:
        raise ValueError(f"{label} dataset is empty")
    for key, array in arrays.items():
        if array.ndim == 0 or len(array) != rows:
            raise ValueError(f"{label} array {key!r} is not row-aligned")
    for key in ("episode", "step", "seat", "split", "teacher_id", "teacher_family", "teacher_sha256"):
        if arrays[key].ndim != 1:
            raise ValueError(f"{label} array {key!r} must be one-dimensional")
    if arrays["episode"].dtype.kind not in "iu":
        raise ValueError(f"{label} episode must use an integer dtype")
    for key in STRING_KEYS:
        if arrays[key].dtype.kind not in "US":
            raise ValueError(f"{label} array {key!r} must use a fixed-width string dtype")
    if arrays["unit_tokens"].ndim != 2:
        raise ValueError(f"{label} unit_tokens must be rank-2")
    for key in ("unit_mask", "unit_quantities"):
        if arrays[key].shape != arrays["unit_tokens"].shape:
            raise ValueError(f"{label} {key} shape must match unit_tokens")
    if arrays["market_tokens"].ndim != 2:
        raise ValueError(f"{label} market_tokens must be rank-2")
    for key in ("market_mask", "market_quantities"):
        if arrays[key].shape != arrays["market_tokens"].shape:
            raise ValueError(f"{label} {key} shape must match market_tokens")
    return rows


def _validate_compatible_schema(
    base: dict[str, np.ndarray], candidate: dict[str, np.ndarray], label: str,
) -> None:
    for key in sorted(CORE_KEYS):
        base_array = base[key]
        candidate_array = candidate[key]
        if base_array.shape[1:] != candidate_array.shape[1:]:
            raise ValueError(
                f"{label} trailing shape mismatch for {key}: "
                f"{candidate_array.shape[1:]} != {base_array.shape[1:]}"
            )
        if key in STRING_KEYS or key == "episode":
            continue
        if candidate_array.dtype != base_array.dtype:
            raise ValueError(
                f"{label} dtype mismatch for {key}: {candidate_array.dtype} != {base_array.dtype}"
            )


def _expected_option_ids(families: np.ndarray, label: str) -> np.ndarray:
    family_values = np.asarray(families).astype(str)
    unknown = sorted(set(family_values.tolist()) - set(OPTION_IDS))
    if unknown:
        raise ValueError(f"{label} contains unknown teacher families: {unknown}")
    return np.fromiter(
        (OPTION_IDS[family] for family in family_values),
        dtype=np.int8,
        count=len(family_values),
    )


def _teacher_contract(
    arrays: dict[str, np.ndarray], label: str,
) -> dict[str, tuple[str, str]]:
    ids = np.asarray(arrays["teacher_id"]).astype(str)
    families = np.asarray(arrays["teacher_family"]).astype(str)
    shas = np.asarray(arrays["teacher_sha256"]).astype(str)
    contract: dict[str, tuple[str, str]] = {}
    for teacher_id, family, digest in zip(ids, families, shas, strict=True):
        if not teacher_id:
            raise ValueError(f"{label} contains an empty teacher_id")
        if not SHA256_PATTERN.fullmatch(digest):
            raise ValueError(f"{label} teacher {teacher_id!r} has an invalid SHA256: {digest!r}")
        identity = (family, digest)
        previous = contract.setdefault(teacher_id, identity)
        if previous != identity:
            raise ValueError(
                f"{label} teacher {teacher_id!r} maps to multiple family/SHA identities"
            )
    return contract


def _validate_episode_groups(arrays: dict[str, np.ndarray], label: str) -> None:
    episode = np.asarray(arrays["episode"])
    for local_episode in np.unique(episode):
        mask = episode == local_episode
        for key in ("teacher_id", "teacher_family", "teacher_sha256", "option_id", "split"):
            if len(np.unique(arrays[key][mask])) != 1:
                raise ValueError(
                    f"{label} episode {local_episode!r} spans multiple {key} values; "
                    "grouped folds would leak"
                )


def _derive_unit_roles(arrays: dict[str, np.ndarray]) -> np.ndarray:
    roles = np.vectorize(unit_role, otypes=[np.int8])(arrays["unit_tokens"])
    roles[np.asarray(arrays["unit_mask"]) == 0] = 0
    return roles.astype(np.int8)


def _apply_absorbing_stop(
    arrays: dict[str, np.ndarray], label: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]:
    tokens = np.asarray(arrays["market_tokens"]).copy()
    quantities = np.asarray(arrays["market_quantities"]).copy()
    mask = np.asarray(arrays["market_mask"]).copy()
    roles = np.vectorize(market_role, otypes=[np.int8])(tokens)
    roles[mask == 0] = STOP_ROLE
    stop_token = int(space.MARKET_INDEX["STOP"])
    added = 0
    for row in range(len(tokens)):
        active_stops = np.flatnonzero((mask[row] != 0) & (tokens[row] == stop_token))
        if active_stops.size == 0:
            if not np.all(mask[row] != 0):
                raise ValueError(
                    f"{label} market row {row} has no active STOP and is not a full sequence"
                )
            continue
        first_stop = int(active_stops[0])
        active_tail = mask[row, first_stop + 1:] != 0
        if np.any(
            active_tail
            & (
                (tokens[row, first_stop + 1:] != stop_token)
                | (quantities[row, first_stop + 1:] != 0)
            )
        ):
            raise ValueError(
                f"{label} market row {row} has a non-STOP action or non-zero quantity "
                "after its first STOP"
            )
        added += int(np.count_nonzero(mask[row, first_stop + 1:] == 0))
        tail = slice(first_stop, tokens.shape[1])
        tokens[row, tail] = stop_token
        quantities[row, tail] = 0
        mask[row, tail] = 1
        roles[row, tail] = STOP_ROLE
    return tokens, quantities, mask, roles.astype(np.int8), added


def _normalise_source(
    arrays: dict[str, np.ndarray], label: str, *, require_derived: bool,
) -> tuple[dict[str, np.ndarray], int]:
    _validate_rows(arrays, label)
    expected_options = _expected_option_ids(arrays["teacher_family"], label)
    if "option_id" in arrays:
        existing = np.asarray(arrays["option_id"])
        if existing.ndim != 1 or not np.array_equal(existing.astype(np.int8), expected_options):
            raise ValueError(f"{label} option_id conflicts with teacher_family")
    elif require_derived:
        raise ValueError(f"{label} is missing option_id")

    derived_unit_roles = _derive_unit_roles(arrays)
    if "unit_roles" in arrays:
        unit_roles = np.asarray(arrays["unit_roles"])
        if unit_roles.shape != arrays["unit_tokens"].shape:
            raise ValueError(f"{label} unit_roles shape must match unit_tokens")
        if np.any((unit_roles < 0) | (unit_roles >= len(UNIT_ROLE_NAMES))):
            raise ValueError(f"{label} unit_roles contains an unknown label")
        unit_roles = unit_roles.astype(np.int8, copy=True)
    elif require_derived:
        raise ValueError(f"{label} is missing unit_roles")
    else:
        unit_roles = derived_unit_roles

    market_tokens, market_quantities, market_mask, market_roles, added = _apply_absorbing_stop(
        arrays, label,
    )
    if require_derived:
        if not np.array_equal(arrays["market_tokens"], market_tokens):
            raise ValueError(f"{label} violates the absorbing STOP token contract")
        if not np.array_equal(arrays["market_quantities"], market_quantities):
            raise ValueError(f"{label} violates the absorbing STOP quantity contract")
        if not np.array_equal(arrays["market_mask"], market_mask):
            raise ValueError(f"{label} violates the absorbing STOP mask contract")
        if np.asarray(arrays["market_roles"]).shape != market_roles.shape or not np.array_equal(
            np.asarray(arrays["market_roles"]).astype(np.int8), market_roles
        ):
            raise ValueError(f"{label} market_roles conflicts with market actions")

    terminal = (np.asarray(arrays["step"]) >= TERMINAL_STEP).astype(np.int8)
    if require_derived and not np.array_equal(
        np.asarray(arrays["terminal_flag"]).astype(np.int8), terminal,
    ):
        raise ValueError(f"{label} terminal_flag conflicts with step >= {TERMINAL_STEP}")

    normalised = {key: np.asarray(arrays[key]).copy() for key in CORE_KEYS}
    normalised["option_id"] = expected_options
    normalised["unit_roles"] = unit_roles
    normalised["market_tokens"] = market_tokens
    normalised["market_quantities"] = market_quantities
    normalised["market_mask"] = market_mask
    normalised["market_roles"] = market_roles
    normalised["terminal_flag"] = terminal
    _teacher_contract(normalised, label)
    _validate_episode_groups(normalised, label)
    return normalised, added


def _counts(arrays: dict[str, np.ndarray]) -> dict[str, Any]:
    families = np.asarray(arrays["teacher_family"]).astype(str)
    options = np.asarray(arrays["option_id"]).astype(int)
    terminal = np.asarray(arrays["terminal_flag"]).astype(bool)
    return {
        "rows": int(len(families)),
        "episodes": int(len(np.unique(arrays["episode"]))),
        "by_option": {str(option): int(np.count_nonzero(options == option)) for option in sorted(OPTION_IDS.values())},
        "by_family": {family: int(np.count_nonzero(families == family)) for family in OPTION_IDS},
        "terminal": {
            "rows": int(np.count_nonzero(terminal)),
            "non_terminal_rows": int(np.count_nonzero(~terminal)),
        },
    }


def _first_seen_unique(values: np.ndarray) -> list[int]:
    return list(dict.fromkeys(int(value) for value in np.asarray(values).tolist()))


def merge_latent_dagger_dataset(
    base: Path,
    daggers: Iterable[Path],
    output: Path,
    manifest: Path | None = None,
) -> dict[str, Any]:
    base = base.resolve()
    dagger_paths = [path.resolve() for path in daggers]
    output = output.resolve()
    manifest = (manifest or output.with_suffix(".manifest.json")).resolve()
    if not dagger_paths:
        raise ValueError("at least one candidate-state DAgger dataset is required")
    inputs = [base, *dagger_paths]
    if len(set(inputs)) != len(inputs):
        raise ValueError("base and DAgger inputs must be unique files")
    if output.suffix != ".npz":
        raise ValueError("output must use the .npz suffix")
    if output in inputs or manifest in {*inputs, output}:
        raise ValueError("output and manifest must differ from every input and each other")

    base_raw = _load_exact(base, (BASE_KEYS,), "base")
    base_arrays, base_added = _normalise_source(base_raw, "base", require_derived=True)
    if base_added != 0:
        raise ValueError("base is not already an absorbing-STOP latent-role dataset")
    base_contract = _teacher_contract(base_arrays, "base")

    sources = [base_arrays]
    source_reports: list[dict[str, Any]] = [{
        "source_id": 0,
        "kind": "base",
        "path": str(base),
        "sha256": sha256_file(base),
        "absorbing_stop_slots_added": 0,
        **_counts(base_arrays),
    }]
    for index, path in enumerate(dagger_paths, start=1):
        raw = _load_exact(path, (CORE_KEYS, BASE_KEYS), f"dagger[{index - 1}]")
        _validate_compatible_schema(base_arrays, raw, f"dagger[{index - 1}]")
        normalised, added = _normalise_source(
            raw, f"dagger[{index - 1}]", require_derived=frozenset(raw) == BASE_KEYS,
        )
        candidate_contract = _teacher_contract(normalised, f"dagger[{index - 1}]")
        for teacher_id, identity in candidate_contract.items():
            if teacher_id not in base_contract:
                raise ValueError(
                    f"dagger[{index - 1}] teacher {teacher_id!r} is absent from the base teacher contract"
                )
            if base_contract[teacher_id] != identity:
                raise ValueError(
                    f"dagger[{index - 1}] teacher {teacher_id!r} family/SHA does not match base"
                )
        sources.append(normalised)
        source_reports.append({
            "source_id": index,
            "kind": "dagger",
            "path": str(path),
            "sha256": sha256_file(path),
            "absorbing_stop_slots_added": int(added),
            **_counts(normalised),
        })

    output_arrays: dict[str, list[np.ndarray]] = {key: [] for key in BASE_KEYS}
    source_kind_parts: list[np.ndarray] = []
    source_id_parts: list[np.ndarray] = []
    source_episode_parts: list[np.ndarray] = []
    episode_parts: list[np.ndarray] = []
    next_episode = 0
    episode_ranges: list[dict[str, int]] = []
    for source_id, arrays in enumerate(sources):
        rows = len(arrays["episode"])
        for key in BASE_KEYS:
            output_arrays[key].append(arrays[key])
        original_episode = np.asarray(arrays["episode"], dtype=np.int64)
        mapping = {
            local: next_episode + offset
            for offset, local in enumerate(_first_seen_unique(original_episode))
        }
        reindexed = np.fromiter(
            (mapping[int(local)] for local in original_episode),
            dtype=np.int64,
            count=rows,
        )
        if reindexed.max(initial=0) > np.iinfo(np.int32).max:
            raise OverflowError("globally reindexed episode id exceeds int32")
        episode_count = len(mapping)
        episode_ranges.append({
            "source_id": source_id,
            "start_inclusive": next_episode,
            "stop_exclusive": next_episode + episode_count,
            "episodes": episode_count,
        })
        next_episode += episode_count
        episode_parts.append(reindexed.astype(np.int32))
        source_episode_parts.append(original_episode)
        source_id_parts.append(np.full(rows, source_id, dtype=np.int16))
        source_kind_parts.append(np.full(rows, "base" if source_id == 0 else "dagger", dtype="<U6"))

    merged = {
        key: np.concatenate(parts, axis=0)
        for key, parts in output_arrays.items()
    }
    merged["episode"] = np.concatenate(episode_parts)
    merged["source_episode"] = np.concatenate(source_episode_parts)
    merged["source_id"] = np.concatenate(source_id_parts)
    merged["source_kind"] = np.concatenate(source_kind_parts)
    if len(np.unique(merged["episode"])) != next_episode:
        raise AssertionError("global episode reindexing is not unique")
    _atomic_npz(output, merged)

    merged_counts = _counts(merged)
    base_rows = int(len(base_arrays["episode"]))
    dagger_rows = int(sum(len(source["episode"]) for source in sources[1:]))
    teacher_manifest = {
        teacher_id: {"family": family, "sha256": digest}
        for teacher_id, (family, digest) in sorted(base_contract.items())
    }
    report: dict[str, Any] = {
        "schema": "kaggriculture-v114-v6-latent-role-base-dagger-merge-v1",
        "model_id": "v114_day_smdp_hmoe_ppo_v6",
        "strategy_parent": None,
        "inherits_v113_checkpoint": False,
        "source_checkpoint": None,
        "checkpoint_inheritance": "NONE_DATASET_COMPOSITION_ONLY",
        "online_historical_agent_fallback": False,
        "inputs": source_reports,
        "output": {
            "path": str(output),
            "sha256": sha256_file(output),
            "compression": "np.savez_compressed",
        },
        "rows": {
            "base": base_rows,
            "dagger": dagger_rows,
            "total": base_rows + dagger_rows,
        },
        "counts": merged_counts,
        "episode_grouping": {
            "contract": "global id is unique by (source_id, original episode); one original episode cannot cross folds",
            "global_unique_episodes": next_episode,
            "contiguous_zero_based": bool(np.array_equal(np.unique(merged["episode"]), np.arange(next_episode))),
            "source_ranges": episode_ranges,
            "original_episode_preserved_as": "source_episode",
        },
        "option_contract": dict(OPTION_IDS),
        "role_contract": {
            "unit": {str(index): name for index, name in enumerate(UNIT_ROLE_NAMES)},
            "market": {str(index): name for index, name in enumerate(MARKET_ROLE_NAMES)},
            "terminal_step_gte": TERMINAL_STEP,
            "absorbing_market_stop": True,
        },
        "teacher_contract": teacher_manifest,
        "source_exposure": {
            "label_teacher_scope": "base-known teachers only",
            "base_rows": base_rows,
            "candidate_state_dagger_rows": dagger_rows,
            "gold_train_rows": base_rows + dagger_rows,
            "gold_dev": {"accessed": False, "rows": 0},
            "gold_blind": {"accessed": False, "rows": 0},
        },
        "arrays": {
            key: {"shape": list(array.shape), "dtype": str(array.dtype)}
            for key, array in sorted(merged.items())
        },
        "qualification_status": "DATASET_ONLY_NOT_QUALIFIED_NOT_GOLD",
    }
    _atomic_json(manifest, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--dagger", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, help="Defaults to <output stem>.manifest.json")
    args = parser.parse_args()
    report = merge_latent_dagger_dataset(args.base, args.dagger, args.output, args.manifest)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
