"""Build the sealed, leakage-safe V12 ``frozen_v5`` formal protocol.

This script never runs a Kaggriculture game.  It reuses the already frozen
100-source formal panel byte-for-byte at the record level, proves that every
known development exposure remains disjoint, materialises both candidates from
their clean submission archives, and freezes the exact 23-pair protocol.
Existing frozen artifacts are immutable: a rerun may verify them, but it will
not silently replace different content.
"""

from __future__ import annotations

from collections import Counter
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import tarfile
from typing import Any, Iterable, Mapping


HERE = Path(__file__).resolve().parent
MODEL_ROOT = HERE.parent
V10 = MODEL_ROOT / "v10_replay_lolo_router"
V11 = MODEL_ROOT / "v11_iterative_league"

DEFAULT_MANIFEST = V10 / "evaluation_seed_manifest.jsonl"
DEFAULT_STATE = V11 / "pool_state.json"
DEFAULT_FIT_EXCLUSIONS = V10 / "router_fit_source_exclusions.json"
DEFAULT_ROUND_PANELS = tuple(
    V11 / "runs" / f"round_{number:03d}" / "panel.json" for number in (1, 2, 3)
)
DEFAULT_CANDIDATE_ENTRIES = (
    MODEL_ROOT / "v12_incumbent_r002" / "registry_entry.json",
    MODEL_ROOT / "v12a2_no_shop_gate" / "registry_entry.json",
)
DEFAULT_CONTEXT_ARTIFACTS = (
    MODEL_ROOT / "v12_incumbent_r002" / "development_evidence.json",
    MODEL_ROOT / "v12_incumbent_r002" / "README.md",
)
DEFAULT_TEXT_EXPOSURE_ARTIFACTS = (
    MODEL_ROOT / "v12a2_no_shop_gate" / "README.md",
)
DEFAULT_LOCKED_FORMAL_PANEL = HERE / "frozen_v4" / "formal_panel.json"

DATES = ("2026-08-18", "2026-08-19", "2026-08-20")
FORMAL_QUOTA = {DATES[0]: 34, DATES[1]: 33, DATES[2]: 33}
FORMAL_SALT = "kaggriculture-v12-formal-20260823-v1"
EXPECTED_FORMAL_RECORDS_SHA256 = (
    "02d8d87151a525bd3977889153192d73d7729cf25f9528d530115522a6be49d7"
)

COMMON_OPPONENTS = (
    "baseline_v1",
    "baseline_v5",
    "baseline_v8",
    "rule_router",
    "v5_topdays",
    "v8_topdays",
    "v8_conservative",
)
CANDIDATES = (
    "v12_incumbent_r002",
    "v12a2_no_shop_gate",
)
PARENTS = {
    "v12_incumbent_r002": "learned_router",
    "v12a2_no_shop_gate": "v12_incumbent_r002",
}
# The source A2 entry names the historical r002 id.  The formal parent is the
# independently packaged, policy-equivalent incumbent alias.  Both declarations
# are frozen and checked rather than silently rewriting candidate provenance.
SOURCE_DECLARED_PARENTS = {
    "v12_incumbent_r002": "learned_router",
    "v12a2_no_shop_gate": "r002_learned_router_topday_animal_throttle",
}
FORMAL_MODELS = (*COMMON_OPPONENTS, "learned_router", *CANDIDATES)


def _targeted_pairs() -> list[tuple[str, str]]:
    order = {model_id: index for index, model_id in enumerate(FORMAL_MODELS)}
    pairs: list[tuple[str, str]] = []

    def add(left: str, right: str) -> None:
        pair = (left, right) if order[left] < order[right] else (right, left)
        if pair not in pairs:
            pairs.append(pair)

    for candidate in CANDIDATES:
        parent = PARENTS[candidate]
        add(candidate, parent)
        for opponent in COMMON_OPPONENTS:
            add(candidate, opponent)
            add(parent, opponent)
    if len(pairs) != 23:
        raise AssertionError(f"targeted pair protocol is not 23 pairs: {len(pairs)}")
    return pairs


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> Any:
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _normalise_split(value: Any) -> str:
    split = str(value or "").lower()
    return "validation" if split == "val" else split


def _normalise_source(row: Mapping[str, Any]) -> dict[str, Any]:
    date = str(row.get("date") or row.get("source_date") or "")[:10]
    seed = int(row["seed"])
    episode_id = str(row.get("episode_id") or row.get("episodeId") or "")
    split = _normalise_split(row.get("split"))
    source_path = str(
        row.get("source_path")
        or row.get("source_relpath")
        or row.get("path")
        or ""
    )
    return {
        "date": date,
        "seed": seed,
        "episode_id": episode_id,
        "split": split,
        "source_path": source_path,
        "lineage_fold": str(row.get("lineage_fold") or row.get("fold") or ""),
    }


def _load_manifest(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            raw = json.loads(line)
            row = _normalise_source(raw)
            if row["date"] not in DATES:
                continue
            if row["split"] not in {"train", "validation"}:
                continue
            if list(raw.get("final_statuses") or []) != ["DONE", "DONE"]:
                raise ValueError(f"official manifest has non-DONE source at line {line_number}")
            rows.append(row)
    keys = [(row["date"], row["seed"]) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("official train/validation manifest is not unique at date x seed")
    return rows


def _panel_records(path: Path) -> list[dict[str, Any]]:
    payload = _read_json(path)
    records = payload.get("records") if isinstance(payload, Mapping) else None
    if not isinstance(records, list):
        raise ValueError(f"panel has no records array: {path}")
    return [_normalise_source(row) for row in records]


def _locked_formal_records(
    panel_path: Path, official_records: Iterable[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Load the original formal100; never select a replacement source."""

    payload = _read_json(panel_path)
    records = payload.get("records") if isinstance(payload, Mapping) else None
    if not isinstance(records, list):
        raise ValueError(f"locked formal panel has no records array: {panel_path}")
    normalised = [_normalise_source(row) for row in records]
    records_sha = _sha256_bytes(_canonical(normalised))
    if (
        payload.get("records_sha256") != EXPECTED_FORMAL_RECORDS_SHA256
        or records_sha != EXPECTED_FORMAL_RECORDS_SHA256
    ):
        raise ValueError(
            "locked formal panel record hash mismatch: "
            f"{records_sha} != {EXPECTED_FORMAL_RECORDS_SHA256}"
        )
    if len(normalised) != 100 or len({int(row["seed"]) for row in normalised}) != 100:
        raise ValueError("locked formal panel must contain 100 unique seeds")
    if Counter(row["date"] for row in normalised) != Counter(FORMAL_QUOTA):
        raise ValueError("locked formal panel date quotas drifted")
    if any(row["split"] not in {"train", "validation"} for row in normalised):
        raise ValueError("locked formal panel contains test/non-development source")

    official_by_key = {
        (str(row["date"]), int(row["seed"])): dict(row) for row in official_records
    }
    for row in normalised:
        key = (str(row["date"]), int(row["seed"]))
        if official_by_key.get(key) != row:
            raise ValueError(f"locked formal source no longer matches official manifest: {key}")
    return normalised


def _assert_formal_exposure_disjoint(
    records: Iterable[Mapping[str, Any]], excluded_seeds: Iterable[int]
) -> None:
    formal = {int(row["seed"]) for row in records}
    collisions = sorted(formal & {int(seed) for seed in excluded_seeds})
    if collisions:
        raise ValueError(
            "locked formal panel intersects newly declared development exposure; "
            f"refusing replacement selection, collisions={collisions}"
        )


def _smoke_seeds(path: Path) -> set[int]:
    payload = _read_json(path)
    seeds: set[int] = set()

    def visit(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if key == "seed" and isinstance(child, (int, float)):
                    seeds.add(int(child))
                elif key == "seeds" and isinstance(child, list):
                    seeds.update(
                        int(item) for item in child if isinstance(item, (int, float))
                    )
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(payload)
    if not seeds:
        raise ValueError(f"smoke report exposes no seeds: {path}")
    return seeds


def _markdown_seed_literals(path: Path) -> set[int]:
    seeds = {
        int(value)
        for value in re.findall(
            r"(?i)\bseed\s*[`'\"]?([0-9]{8,12})[`'\"]?",
            path.read_text(encoding="utf-8"),
        )
    }
    if not seeds:
        raise ValueError(f"markdown exposure declares no seed literal: {path}")
    return seeds


def _discover_exposure_reports() -> tuple[Path, ...]:
    """Return every structured seed-bearing artifact used to design/re-QA v5.

    The A2 README explicitly reports development results on both old screen
    panels, so those panels are first-class exposures.  Candidate-side JSON is
    discovered dynamically; a later seed-bearing JSON makes preflight fail
    until the protocol is rebuilt and re-sealed.
    """

    reports: list[Path] = []
    for directory in (
        MODEL_ROOT / "v12_incumbent_r002",
        MODEL_ROOT / "v12a2_no_shop_gate",
    ):
        for path in sorted(directory.glob("*.json")):
            try:
                _smoke_seeds(path)
            except (ValueError, KeyError, TypeError, json.JSONDecodeError):
                continue
            reports.append(path)
    for version in ("frozen_v3", "frozen_v4"):
        prior_screen = HERE / version / "screen_panel.json"
        if not prior_screen.is_file():
            raise FileNotFoundError(
                f"required prior screen exposure missing: {prior_screen}"
            )
        reports.append(prior_screen)
    if not reports:
        raise ValueError("no candidate exposure reports discovered")
    return tuple(dict.fromkeys(path.resolve() for path in reports))


def _stable_rank(salt: str, row: Mapping[str, Any]) -> str:
    identity = (
        f"{salt}:{row['date']}:{int(row['seed'])}:"
        f"{row['episode_id']}:{row['split']}"
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def _select_panel(
    records: Iterable[dict[str, Any]],
    quota: Mapping[str, int],
    excluded_seeds: set[int],
    salt: str,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    used = set(int(value) for value in excluded_seeds)
    rows = list(records)
    for date in DATES:
        candidates = sorted(
            (
                row
                for row in rows
                if row["date"] == date and int(row["seed"]) not in used
            ),
            key=lambda row: (_stable_rank(salt, row), int(row["seed"])),
        )
        chosen: list[dict[str, Any]] = []
        for row in candidates:
            seed = int(row["seed"])
            if seed in used:
                continue
            chosen.append(dict(row))
            used.add(seed)
            if len(chosen) == int(quota[date]):
                break
        if len(chosen) != int(quota[date]):
            raise ValueError(f"insufficient clean sources for {date}: {len(chosen)}")
        selected.extend(chosen)
    selected.sort(key=lambda row: (_stable_rank(f"{salt}:order", row), row["date"]))
    if len({int(row["seed"]) for row in selected}) != len(selected):
        raise ValueError("selected panel repeats an environment seed")
    return selected


def _rebase(value: str, origin: Path) -> str:
    path = Path(str(value)).expanduser()
    return str(path.resolve() if path.is_absolute() else (origin / path).resolve())


def _rebase_entry(entry: Mapping[str, Any], origin: Path) -> dict[str, Any]:
    result = copy.deepcopy(dict(entry))
    for key in ("path", "module_path", "weights"):
        if result.get(key):
            result[key] = _rebase(str(result[key]), origin)
    if result.get("code_paths"):
        result["code_paths"] = [
            _rebase(str(value), origin) for value in result["code_paths"]
        ]
    # ``source`` is path-like only when it resolves to a real file.  Some old
    # registries use the same key as a symbolic model reference.
    if result.get("source"):
        candidate = Path(_rebase(str(result["source"]), origin))
        if candidate.is_file():
            result["source"] = str(candidate)
    return result


def _combined_registry(
    state_path: Path, candidate_entry_paths: Iterable[Path]
) -> tuple[dict[str, Any], dict[str, Any]]:
    state = _read_json(state_path)
    registry_path = Path(str(state["registry"])).expanduser().resolve()
    source = _read_json(registry_path)
    if not isinstance(source, Mapping) or not isinstance(source.get("models"), list):
        raise ValueError("Round-3 registry must be an object with a models list")
    source_ids = [str(row.get("id")) for row in source["models"]]
    active_ids = [str(value) for value in state.get("active_models") or []]
    if source_ids != active_ids:
        raise ValueError("Round-3 state/registry model order mismatch")

    models = [_rebase_entry(row, registry_path.parent) for row in source["models"]]
    entry_provenance: list[dict[str, Any]] = []
    for entry_path in candidate_entry_paths:
        entry_path = entry_path.expanduser().resolve()
        entry_payload = _read_json(entry_path)
        if not isinstance(entry_payload, Mapping):
            raise ValueError(f"invalid candidate registry entry: {entry_path}")
        # Candidate teams used two equivalent presentation contracts: a raw
        # single model spec, or an envelope with exactly one ``models`` spec.
        # Accept both but never guess among multiple entries.
        if entry_payload.get("id"):
            entry = dict(entry_payload)
        else:
            wrapped = entry_payload.get("models")
            if not isinstance(wrapped, list) or len(wrapped) != 1:
                raise ValueError(f"invalid candidate registry entry: {entry_path}")
            entry = dict(wrapped[0])
        if not entry.get("id"):
            raise ValueError(f"candidate registry entry has no model id: {entry_path}")
        model_id = str(entry["id"])
        if model_id in {str(row["id"]) for row in models}:
            raise ValueError(f"duplicate model id in combined registry: {model_id}")
        rebased = _rebase_entry(entry, entry_path.parent)
        models.append(rebased)
        entry_provenance.append(
            {
                "model_id": model_id,
                "path": str(entry_path),
                "file_sha256": _sha256_file(entry_path),
                "entry_schema": entry_payload.get("schema"),
                "normalised_entry_sha256": _sha256_bytes(_canonical(rebased)),
            }
        )

    ids = [str(row["id"]) for row in models]
    if tuple(ids[-len(CANDIDATES) :]) != CANDIDATES:
        raise ValueError(f"candidate entry order/id mismatch: {ids[-len(CANDIDATES):]}")
    for candidate, parent in SOURCE_DECLARED_PARENTS.items():
        row = next(item for item in models if item["id"] == candidate)
        if list(row.get("parent_models") or []) != [parent]:
            raise ValueError(
                f"{candidate} source registry must declare exact "
                f"parent_models=[{parent!r}]"
            )
    missing = [model_id for model_id in FORMAL_MODELS if model_id not in ids]
    if missing:
        raise ValueError(f"formal validation models missing from registry: {missing}")

    combined = copy.deepcopy(dict(source))
    combined["schema"] = "kaggriculture-v12-local-validation-registry-1"
    combined["models"] = models
    combined["validation_overlay"] = {
        "purpose": "local train/validation evaluation only; never a Kaggle submission",
        "source_round3_state": str(state_path.resolve()),
        "source_round3_state_sha256": _sha256_file(state_path),
        "source_registry": str(registry_path),
        "source_registry_file_sha256": _sha256_file(registry_path),
        "source_registry_and_code_sha256": str(state["registry_and_code_sha256"]),
        "candidate_entries": entry_provenance,
        "test_sources_allowed": False,
    }
    return combined, {
        "source_registry": str(registry_path),
        "source_registry_file_sha256": _sha256_file(registry_path),
        "source_registry_and_code_sha256": str(state["registry_and_code_sha256"]),
        "candidate_entries": entry_provenance,
    }


def _panel_payload(
    kind: str,
    records: list[dict[str, Any]],
    quota: Mapping[str, int],
    salt: str,
    manifest_path: Path,
    exclusion_summary: Mapping[str, Any],
) -> dict[str, Any]:
    counts = Counter(row["date"] for row in records)
    split_counts = Counter(row["split"] for row in records)
    if counts != Counter({str(key): int(value) for key, value in quota.items()}):
        raise ValueError(f"{kind} panel date quota mismatch: {counts}")
    if any(row["split"] not in {"train", "validation"} for row in records):
        raise ValueError(f"{kind} panel contains test/non-development sources")
    return {
        "schema": "kaggriculture-v12-validation-panel-1",
        "kind": kind,
        "frozen": True,
        "metadata_only": True,
        "source_manifest": str(manifest_path.resolve()),
        "source_manifest_sha256": _sha256_file(manifest_path),
        "selection_salt": salt,
        "selection_salt_sha256": _sha256_bytes(salt.encode("utf-8")),
        "dates": list(DATES),
        "allowed_splits": ["train", "validation"],
        "test_source_count": 0,
        "count": len(records),
        "date_counts": dict(sorted(counts.items())),
        "split_counts": dict(sorted(split_counts.items())),
        "all_environment_seeds_unique": len({row["seed"] for row in records})
        == len(records),
        "exclusions": copy.deepcopy(dict(exclusion_summary)),
        "records_sha256": _sha256_bytes(_canonical(records)),
        "records": records,
    }


def _json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _jsonl_bytes(records: Iterable[Mapping[str, Any]]) -> bytes:
    return b"".join(_canonical(dict(row)) + b"\n" for row in records)


def _freeze_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError(f"refusing to replace different frozen artifact: {path}")
        return
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def _materialize_submission_closure(
    combined: dict[str, Any], output_dir: Path
) -> dict[str, Any]:
    definitions = {
        "v12_incumbent_r002": {
            "archive": MODEL_ROOT / "v12_incumbent_r002" / "submission.tar.gz",
            "manifest": MODEL_ROOT / "v12_incumbent_r002" / "submission_manifest.json",
        },
        "v12a2_no_shop_gate": {
            "archive": MODEL_ROOT / "v12a2_no_shop_gate" / "submission.tar.gz",
            "manifest": MODEL_ROOT / "v12a2_no_shop_gate" / "submission_manifest.json",
        },
    }
    report: dict[str, Any] = {
        "schema": "kaggriculture-v12-clean-submission-closure-1",
        "candidates": {},
    }
    for model_id, definition in definitions.items():
        archive = Path(definition["archive"]).resolve()
        manifest_path = Path(definition["manifest"]).resolve()
        manifest = _read_json(manifest_path)
        expected_archive_sha = str(
            manifest.get("archive_sha256") or manifest.get("sha256") or ""
        )
        actual_archive_sha = _sha256_file(archive)
        if not expected_archive_sha or actual_archive_sha != expected_archive_sha:
            raise ValueError(f"{model_id} submission archive/manifest mismatch")
        target = output_dir / "clean_submissions" / model_id
        members: list[dict[str, Any]] = []
        with tarfile.open(archive, "r:gz") as handle:
            for member in handle.getmembers():
                member_path = Path(member.name)
                if (
                    not member.isfile()
                    or member_path.is_absolute()
                    or ".." in member_path.parts
                ):
                    if member.isdir():
                        continue
                    raise ValueError(f"unsafe/non-file archive member: {member.name}")
                source = handle.extractfile(member)
                if source is None:
                    raise ValueError(f"cannot read archive member: {member.name}")
                content = source.read()
                destination = target / member_path
                _freeze_write(destination, content)
                members.append(
                    {
                        "path": str(destination.resolve()),
                        "relative_path": member.name,
                        "size_bytes": len(content),
                        "sha256": _sha256_bytes(content),
                    }
                )
        members.sort(key=lambda item: item["relative_path"])
        main_path = (target / "main.py").resolve()
        if not main_path.is_file():
            raise ValueError(f"{model_id} clean archive has no main.py")
        spec = next(row for row in combined["models"] if row["id"] == model_id)
        spec["path"] = str(main_path)
        spec["code_paths"] = [item["path"] for item in members]
        spec["validation_runtime"] = "clean_submission_archive"
        report["candidates"][model_id] = {
            "archive": str(archive),
            "archive_sha256": actual_archive_sha,
            "manifest": str(manifest_path),
            "manifest_sha256": _sha256_file(manifest_path),
            "clean_root": str(target.resolve()),
            "members": members,
            "members_sha256": _sha256_bytes(_canonical(members)),
        }
    return report


def build(args: argparse.Namespace) -> dict[str, Any]:
    manifest = args.manifest.expanduser().resolve()
    state = args.state.expanduser().resolve()
    fit_path = args.fit_exclusions.expanduser().resolve()
    round_panels = tuple(path.expanduser().resolve() for path in args.round_panels)
    smoke_reports = tuple(path.expanduser().resolve() for path in args.smoke_reports)
    candidate_entries = tuple(
        path.expanduser().resolve() for path in args.candidate_entries
    )
    context_artifacts = tuple(path.resolve() for path in DEFAULT_CONTEXT_ARTIFACTS)
    text_exposure_artifacts = tuple(
        path.resolve() for path in DEFAULT_TEXT_EXPOSURE_ARTIFACTS
    )
    locked_formal_panel = args.locked_formal_panel.expanduser().resolve()

    # Validate every prerequisite before writing anything.  In particular, a
    # missing V12B entry cannot produce a half-valid combined registry.
    required = (
        manifest,
        state,
        fit_path,
        *round_panels,
        *smoke_reports,
        *candidate_entries,
        *context_artifacts,
        *text_exposure_artifacts,
        locked_formal_panel,
    )
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"validation prerequisites missing: {missing}")

    output_dir = args.output_dir.expanduser().resolve()
    combined, registry_provenance = _combined_registry(state, candidate_entries)
    official = _load_manifest(manifest)
    fit_payload = _read_json(fit_path)
    fit_records = fit_payload.get("records") if isinstance(fit_payload, Mapping) else None
    if not isinstance(fit_records, list) or len(fit_records) != 200:
        raise ValueError("Router-fit exclusion artifact must contain exactly 200 records")
    exclusion_sets: dict[str, set[int]] = {
        "router_fit_200": {int(row["seed"]) for row in fit_records},
    }
    for number, path in enumerate(round_panels, 1):
        records = _panel_records(path)
        if len(records) != 100:
            raise ValueError(f"Round-{number} panel is not exactly 100 sources")
        exclusion_sets[f"round_{number:03d}"] = {
            int(row["seed"]) for row in records
        }
    exposure_artifact_rows: list[dict[str, Any]] = [
        {
            "path": str(fit_path),
            "file_sha256": _sha256_file(fit_path),
            "parser": "json_seed_keys_v1",
            "seed_bearing": True,
        },
        *[
            {
                "path": str(path),
                "file_sha256": _sha256_file(path),
                "parser": "json_seed_keys_v1",
                "seed_bearing": True,
            }
            for path in round_panels
        ],
    ]
    for path in smoke_reports:
        model_id = path.parent.name
        category = f"exposure_{model_id}_{path.stem}"
        if category in exclusion_sets:
            raise ValueError(f"duplicate exposure artifact category: {category}")
        exclusion_sets[category] = _smoke_seeds(path)
        exposure_artifact_rows.append(
            {
                "path": str(path),
                "file_sha256": _sha256_file(path),
                "parser": "json_seed_keys_v1",
                "seed_bearing": True,
            }
        )
    for path in text_exposure_artifacts:
        category = f"exposure_{path.parent.name}_{path.stem}_seed_literals"
        if category in exclusion_sets:
            raise ValueError(f"duplicate exposure artifact category: {category}")
        exclusion_sets[category] = _markdown_seed_literals(path)
        exposure_artifact_rows.append(
            {
                "path": str(path),
                "file_sha256": _sha256_file(path),
                "parser": "markdown_seed_literals_v1",
                "seed_bearing": True,
            }
        )

    for item in exposure_artifact_rows:
        path = Path(item["path"])
        values = (
            _smoke_seeds(path)
            if item["parser"] == "json_seed_keys_v1"
            else _markdown_seed_literals(path)
        )
        item["seed_count"] = len(values)
        item["seeds_sha256"] = _sha256_bytes(_canonical(sorted(values)))

    excluded_union = set().union(*exclusion_sets.values())
    exclusion_summary = {
        "policy": "exclude by environment seed across all source dates",
        "union_seed_count": len(excluded_union),
        "categories": {
            key: {
                "seed_count": len(values),
                "seeds_sha256": _sha256_bytes(_canonical(sorted(values))),
            }
            for key, values in sorted(exclusion_sets.items())
        },
        "artifacts": exposure_artifact_rows,
        "context_artifacts": [
            {
                "path": str(path),
                "file_sha256": _sha256_file(path),
                "seed_bearing": False,
            }
            for path in context_artifacts
        ],
    }

    formal_records = _locked_formal_records(locked_formal_panel, official)
    _assert_formal_exposure_disjoint(formal_records, excluded_union)

    # Do not write even a partial clean-package closure until every source
    # selection and the fixed formal-panel hash have passed.
    submission_closure = _materialize_submission_closure(combined, output_dir)

    formal_panel = _panel_payload(
        "formal",
        formal_records,
        FORMAL_QUOTA,
        FORMAL_SALT,
        manifest,
        exclusion_summary,
    )

    payloads: dict[str, bytes] = {
        "combined_registry.json": _json_bytes(combined),
        "submission_closure.json": _json_bytes(submission_closure),
        "formal_panel.json": _json_bytes(formal_panel),
        "formal_seed_manifest.jsonl": _jsonl_bytes(formal_records),
    }
    for name, content in payloads.items():
        _freeze_write(output_dir / name, content)

    # Import only after the registry file exists; this is a loadability check,
    # not a game or a result-producing evaluation.
    import sys

    project_root = MODEL_ROOT.parents[1]
    sys.path.insert(0, str(project_root))
    sys.path.insert(0, str(V10))
    try:
        from agent_factory import create_agent, load_registry, registry_fingerprint
        import pairwise_evaluate as v10_evaluator

        registry = load_registry(output_dir / "combined_registry.json")
        for model_id in FORMAL_MODELS:
            create_agent(registry, model_id)
        combined_runtime_sha = registry_fingerprint(registry)
        evaluator_implementation_sha = v10_evaluator.implementation_fingerprint()
    finally:
        sys.path.pop(0)
        sys.path.pop(0)

    config = {
        "schema": "kaggriculture-v12-local-validation-config-2",
        "invalidated": False,
        "purpose": "fixed-sequence formal requalification on the locked official train/validation panel",
        "test_access": False,
        "combined_registry": str(output_dir / "combined_registry.json"),
        "combined_registry_file_sha256": _sha256_file(
            output_dir / "combined_registry.json"
        ),
        "combined_registry_and_code_sha256": combined_runtime_sha,
        "registry_provenance": registry_provenance,
        "submission_closure": str(output_dir / "submission_closure.json"),
        "submission_closure_file_sha256": _sha256_file(
            output_dir / "submission_closure.json"
        ),
        "formal_models": list(FORMAL_MODELS),
        "strong_opponents": list(COMMON_OPPONENTS),
        "candidates": [
            {
                "id": candidate,
                "parent": PARENTS[candidate],
                "source_declared_parent": SOURCE_DECLARED_PARENTS[candidate],
            }
            for candidate in CANDIDATES
        ],
        "formal_panel": str(output_dir / "formal_panel.json"),
        "formal_panel_file_sha256": _sha256_file(output_dir / "formal_panel.json"),
        "formal_panel_records_sha256": formal_panel["records_sha256"],
        "formal_panel_expected_records_sha256": EXPECTED_FORMAL_RECORDS_SHA256,
        "formal_panel_lineage": {
            "source_panel": str(locked_formal_panel),
            "source_panel_file_sha256": _sha256_file(locked_formal_panel),
            "source_records_sha256": EXPECTED_FORMAL_RECORDS_SHA256,
            "replacement_selection_allowed": False,
        },
        "formal_seed_manifest": str(output_dir / "formal_seed_manifest.jsonl"),
        "formal_seed_manifest_file_sha256": _sha256_file(
            output_dir / "formal_seed_manifest.jsonl"
        ),
        "formal_protocol": {
            "games_per_pair": 200,
            "source_seeds": 100,
            "seat_assignments_per_source": 2,
            "dates": list(DATES),
            "split": "all",
            "random_seed": 20260823,
            "unordered_pairs": len(_targeted_pairs()),
            "targeted_pairs": [list(pair) for pair in _targeted_pairs()],
            "expected_games": len(_targeted_pairs()) * 200,
            "closed_loop": True,
            "common_panel": True,
            "allowed_splits": ["train", "validation"],
        },
        "formal_execution_gate": {
            "requires_explicit_cli_flag": "--execute-formal",
            "requires_independent_redteam_before_use": True,
            "old_screen_gate_dependency": False,
        },
        "quality_thresholds": {
            "direct_parent_score_point_min": 0.5,
            "direct_parent_score_ci95_low_min": 0.5,
            "common_opponent_uplift_point_min": 0.0,
            "common_opponent_uplift_ci95_low_min": 0.0,
            "worst_common_opponent_point_min": -0.02,
        },
        "fixed_sequence_gate": {
            "primary": "v12_incumbent_r002",
            "secondary": "v12a2_no_shop_gate",
            "policy": "primary must pass every pre-registered gate before secondary is confirmatorily interpreted",
        },
        "v10_evaluation_implementation_sha256": evaluator_implementation_sha,
        "implementation_seal": [
            {"path": str(path.resolve()), "file_sha256": _sha256_file(path)}
            for path in (
                HERE / "build_validation_assets.py",
                HERE / "protocol.py",
                HERE / "targeted_evaluate.py",
                HERE / "audit_results.py",
                HERE / "run_validation.sh",
            )
        ],
    }
    config_bytes = _json_bytes(config)
    _freeze_write(output_dir / "validation_config.json", config_bytes)

    sealed_names = [*payloads, "validation_config.json"]
    sha_lines = [
        f"{_sha256_file(output_dir / name)}  {name}\n" for name in sealed_names
    ]
    _freeze_write(
        output_dir / "validation_assets.sha256", "".join(sha_lines).encode("utf-8")
    )
    return {
        "output_dir": str(output_dir),
        "models": list(FORMAL_MODELS),
        "formal_sources": len(formal_records),
        "formal_date_counts": dict(Counter(row["date"] for row in formal_records)),
        "formal_split_counts": dict(Counter(row["split"] for row in formal_records)),
        "excluded_union_seeds": len(excluded_union),
        "formal_records_sha256": formal_panel["records_sha256"],
        "combined_registry_and_code_sha256": combined_runtime_sha,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument(
        "--fit-exclusions", type=Path, default=DEFAULT_FIT_EXCLUSIONS
    )
    parser.add_argument(
        "--round-panels", type=Path, nargs="+", default=list(DEFAULT_ROUND_PANELS)
    )
    parser.add_argument(
        "--candidate-entries",
        type=Path,
        nargs="+",
        default=list(DEFAULT_CANDIDATE_ENTRIES),
    )
    parser.add_argument(
        "--smoke-reports", type=Path, nargs="+", default=None
    )
    parser.add_argument(
        "--locked-formal-panel", type=Path, default=DEFAULT_LOCKED_FORMAL_PANEL
    )
    parser.add_argument("--output-dir", type=Path, default=HERE / "frozen_v5")
    args = parser.parse_args()
    if args.smoke_reports is None:
        args.smoke_reports = list(_discover_exposure_reports())
    print(json.dumps(build(args), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
