"""Shared sealed primitives for the V12 ``frozen_v5`` formal protocol."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import re
import sys
import tarfile
from typing import Any, Iterable, Mapping, Sequence


HERE = Path(__file__).resolve().parent
MODEL_ROOT = HERE.parent
PROJECT_ROOT = MODEL_ROOT.parents[1]
V10 = MODEL_ROOT / "v10_replay_lolo_router"

for value in (str(PROJECT_ROOT), str(V10)):
    if value not in sys.path:
        sys.path.insert(0, value)

from agent_factory import load_registry, registry_fingerprint  # noqa: E402
import pairwise_evaluate as v10  # noqa: E402
from kaggle_Kaggriculture.model.v11_iterative_league.league import (  # noqa: E402
    model_fingerprint,
)


TARGET_SCHEMA = "kaggriculture-v12-targeted-pairwise-2"
EXPECTED_FORMAL_RECORDS_SHA256 = (
    "02d8d87151a525bd3977889153192d73d7729cf25f9528d530115522a6be49d7"
)
EXPECTED_ASSET_NAMES = {
    "combined_registry.json",
    "submission_closure.json",
    "formal_panel.json",
    "formal_seed_manifest.jsonl",
    "validation_config.json",
}


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_config(path: Path) -> dict[str, Any]:
    payload = json.loads(path.expanduser().resolve().read_text(encoding="utf-8"))
    if payload.get("schema") != "kaggriculture-v12-local-validation-config-2":
        raise ValueError("unexpected V12 validation config schema")
    if payload.get("invalidated") is not False:
        raise ValueError("V12 validation config is invalidated")
    return payload


def target_pairs(config: Mapping[str, Any]) -> list[tuple[str, str]]:
    models = [str(value) for value in config["formal_models"]]
    order = {model_id: index for index, model_id in enumerate(models)}
    raw = (config.get("formal_protocol") or {}).get("targeted_pairs") or []
    pairs: list[tuple[str, str]] = []
    for item in raw:
        if not isinstance(item, list) or len(item) != 2:
            raise ValueError(f"invalid targeted pair: {item!r}")
        left, right = str(item[0]), str(item[1])
        if left == right or left not in order or right not in order:
            raise ValueError(f"invalid targeted pair models: {item!r}")
        pair = (left, right) if order[left] < order[right] else (right, left)
        pairs.append(pair)
    if len(pairs) != len(set(pairs)) or len(pairs) != 23:
        raise ValueError(f"formal protocol must contain exactly 23 unique pairs: {len(pairs)}")
    return pairs


def evaluator_panel(config: Mapping[str, Any]):
    protocol = dict(config["formal_protocol"])
    records = v10.load_seed_manifest(Path(config["formal_seed_manifest"]))
    panel = v10.stratified_seed_panel(
        records,
        int(protocol["source_seeds"]),
        list(protocol["dates"]),
        str(protocol["split"]),
        int(protocol["random_seed"]),
    )
    return panel


def run_fingerprint(
    config: Mapping[str, Any], registry: Any, panel: Sequence[Any]
) -> str:
    payload = {
        "schema": TARGET_SCHEMA,
        "v10_row_schema": v10.SCHEMA,
        "evaluation_implementation_sha256": v10.implementation_fingerprint(),
        "registry_and_code_sha256": registry_fingerprint(registry),
        "models": [str(value) for value in config["formal_models"]],
        "targeted_pairs": [list(pair) for pair in target_pairs(config)],
        "games_per_pair": int(config["formal_protocol"]["games_per_pair"]),
        "seed_panel": [asdict(item) for item in panel],
        # Bind every field that changes the confirmatory interpretation, not
        # only the environment tasks.  This prevents a completed row set from
        # being re-labelled under looser thresholds or a reversed sequence.
        "candidates": list(config["candidates"]),
        "strong_opponents": [str(value) for value in config["strong_opponents"]],
        "quality_thresholds": dict(config["quality_thresholds"]),
        "fixed_sequence_gate": dict(config["fixed_sequence_gate"]),
        "formal_panel_records_sha256": str(
            config["formal_panel_records_sha256"]
        ),
    }
    return hashlib.sha256(canonical(payload)).hexdigest()


def task_id(
    fingerprint: str, pair_id: str, source: Mapping[str, Any], model_a_seat: int
) -> str:
    text = (
        f"{fingerprint}:{pair_id}:{source['date']}:{source['episode_id']}:"
        f"{int(source['seed'])}:a-seat-{int(model_a_seat)}"
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]


def expected_tasks(
    config: Mapping[str, Any], registry: Any | None = None
) -> tuple[str, list[dict[str, Any]], list[Any]]:
    if registry is None:
        registry = load_registry(config["combined_registry"])
    panel = evaluator_panel(config)
    fingerprint = run_fingerprint(config, registry, panel)
    tasks: list[dict[str, Any]] = []
    for model_a, model_b in target_pairs(config):
        pair_id = f"{model_a}__vs__{model_b}"
        for item in panel:
            source = asdict(item)
            for seat in (0, 1):
                tasks.append(
                    {
                        "task_id": task_id(fingerprint, pair_id, source, seat),
                        "run_fingerprint": fingerprint,
                        "pair_id": pair_id,
                        "model_a": model_a,
                        "model_b": model_b,
                        "model_a_seat": seat,
                        "source": source,
                        "registry": str(Path(config["combined_registry"]).resolve()),
                    }
                )
    expected = int(config["formal_protocol"]["expected_games"])
    if len(tasks) != expected or expected != 4600:
        raise ValueError(f"unexpected targeted task count: {len(tasks)} != {expected}")
    return fingerprint, tasks, panel


def _all_numeric_seeds(value: Any) -> set[int]:
    seeds: set[int] = set()

    def visit(item: Any) -> None:
        if isinstance(item, Mapping):
            for key, child in item.items():
                if key == "seed" and isinstance(child, (int, float)):
                    seeds.add(int(child))
                elif key == "seeds" and isinstance(child, list):
                    seeds.update(
                        int(entry)
                        for entry in child
                        if isinstance(entry, (int, float))
                    )
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    return seeds


def _asset_manifest_checks(config_path: Path) -> dict[str, bool]:
    base = config_path.parent
    manifest = base / "validation_assets.sha256"
    checks: dict[str, bool] = {"asset_sha_manifest_exists": manifest.is_file()}
    if not manifest.is_file():
        return checks
    listed: set[str] = set()
    listed_rows: list[str] = []
    digests_well_formed = True
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, name = line.split(None, 1)
        name = name.strip()
        listed_rows.append(name)
        digests_well_formed = digests_well_formed and bool(
            re.fullmatch(r"[0-9a-f]{64}", digest)
        )
        listed.add(name)
        path = base / name
        checks[f"asset:{name}"] = path.is_file() and file_sha256(path) == digest
    checks["asset_manifest_binds_config"] = "validation_config.json" in listed
    checks["asset_manifest_exact_v5_set"] = listed == EXPECTED_ASSET_NAMES
    checks["asset_manifest_unique_well_formed_rows"] = (
        digests_well_formed
        and len(listed_rows) == len(set(listed_rows)) == len(EXPECTED_ASSET_NAMES)
    )
    return checks


def _parse_exposure_artifact(item: Mapping[str, Any]) -> set[int]:
    path = Path(str(item["path"])).resolve()
    parser = str(item.get("parser") or "")
    if parser == "json_seed_keys_v1":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return _all_numeric_seeds(payload)
    if parser == "markdown_seed_literals_v1":
        return {
            int(value)
            for value in re.findall(
                r"(?i)\bseed\s*[`'\"]?([0-9]{8,12})[`'\"]?",
                path.read_text(encoding="utf-8"),
            )
        }
    raise ValueError(f"unknown exposure parser: {parser!r}")


def _archive_closure_checks(item: Mapping[str, Any]) -> dict[str, bool]:
    """Re-open a candidate archive and independently rebuild its member seal."""

    archive = Path(str(item["archive"])).resolve()
    manifest_path = Path(str(item["manifest"])).resolve()
    prefix = f"archive_rebuild:{archive.parent.name}"
    checks: dict[str, bool] = {
        f"{prefix}:files_exist": archive.is_file() and manifest_path.is_file()
    }
    if not all((archive.is_file(), manifest_path.is_file())):
        return checks

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_archive_sha = str(
        manifest.get("archive_sha256") or manifest.get("sha256") or ""
    )
    checks[f"{prefix}:manifest_archive_sha"] = (
        bool(expected_archive_sha)
        and expected_archive_sha == item.get("archive_sha256")
        and file_sha256(archive) == expected_archive_sha
    )
    manifest_size = manifest.get("archive_size_bytes", manifest.get("size_bytes"))
    checks[f"{prefix}:manifest_archive_size"] = (
        manifest_size is not None and archive.stat().st_size == int(manifest_size)
    )

    rebuilt: list[dict[str, Any]] = []
    names: list[str] = []
    safe = True
    with tarfile.open(archive, "r:gz") as handle:
        for member in handle.getmembers():
            member_path = Path(member.name)
            if member.isdir():
                continue
            if (
                not member.isfile()
                or member_path.is_absolute()
                or ".." in member_path.parts
            ):
                safe = False
                continue
            source = handle.extractfile(member)
            if source is None:
                safe = False
                continue
            content = source.read()
            names.append(member.name)
            rebuilt.append(
                {
                    "relative_path": member.name,
                    "size_bytes": len(content),
                    "sha256": hashlib.sha256(content).hexdigest(),
                }
            )
    rebuilt.sort(key=lambda row: str(row["relative_path"]))
    checks[f"{prefix}:safe_unique_regular_members"] = safe and len(names) == len(
        set(names)
    )
    closure_rows = sorted(
        [
            {
                "relative_path": str(row["relative_path"]),
                "size_bytes": int(row["size_bytes"]),
                "sha256": str(row["sha256"]),
            }
            for row in item.get("members") or []
        ],
        key=lambda row: row["relative_path"],
    )
    checks[f"{prefix}:closure_member_exact_match"] = rebuilt == closure_rows
    manifest_rows = sorted(
        [
            {
                "relative_path": str(row.get("path") or row.get("relative_path")),
                "size_bytes": int(row["size_bytes"]),
                "sha256": str(row["sha256"]),
            }
            for row in manifest.get("files") or []
        ],
        key=lambda row: row["relative_path"],
    )
    checks[f"{prefix}:manifest_member_exact_match"] = rebuilt == manifest_rows
    return checks


def preflight(config_path: Path) -> dict[str, Any]:
    config_path = config_path.expanduser().resolve()
    config = read_config(config_path)
    checks = _asset_manifest_checks(config_path)

    candidate_items = list(config.get("candidates") or [])
    candidate_ids = [str(item.get("id")) for item in candidate_items]
    checks["exact_v5_candidate_sequence"] = candidate_ids == [
        "v12_incumbent_r002",
        "v12a2_no_shop_gate",
    ] and [str(item.get("parent")) for item in candidate_items] == [
        "learned_router",
        "v12_incumbent_r002",
    ]
    checks["exact_v5_common_opponents"] = list(config.get("strong_opponents") or []) == [
        "baseline_v1",
        "baseline_v5",
        "baseline_v8",
        "rule_router",
        "v5_topdays",
        "v8_topdays",
        "v8_conservative",
    ]
    checks["exact_v5_formal_model_order"] = list(config.get("formal_models") or []) == [
        "baseline_v1",
        "baseline_v5",
        "baseline_v8",
        "rule_router",
        "v5_topdays",
        "v8_topdays",
        "v8_conservative",
        "learned_router",
        "v12_incumbent_r002",
        "v12a2_no_shop_gate",
    ]
    execution_gate = dict(config.get("formal_execution_gate") or {})
    checks["formal_requires_explicit_execution_flag"] = (
        execution_gate.get("requires_explicit_cli_flag") == "--execute-formal"
        and execution_gate.get("requires_independent_redteam_before_use") is True
        and execution_gate.get("old_screen_gate_dependency") is False
    )
    checks["exact_v5_quality_thresholds"] = dict(
        config.get("quality_thresholds") or {}
    ) == {
        "direct_parent_score_point_min": 0.5,
        "direct_parent_score_ci95_low_min": 0.5,
        "common_opponent_uplift_point_min": 0.0,
        "common_opponent_uplift_ci95_low_min": 0.0,
        "worst_common_opponent_point_min": -0.02,
    }
    sequence = dict(config.get("fixed_sequence_gate") or {})
    checks["exact_v5_fixed_sequence"] = (
        sequence.get("primary") == "v12_incumbent_r002"
        and sequence.get("secondary") == "v12a2_no_shop_gate"
        and sequence.get("policy")
        == "primary must pass every pre-registered gate before secondary is confirmatorily interpreted"
    )
    formal_protocol = dict(config.get("formal_protocol") or {})
    checks["exact_v5_formal_execution_contract"] = (
        formal_protocol.get("dates")
        == ["2026-08-18", "2026-08-19", "2026-08-20"]
        and formal_protocol.get("split") == "all"
        and formal_protocol.get("allowed_splits") == ["train", "validation"]
        and int(formal_protocol.get("random_seed", -1)) == 20260823
        and int(formal_protocol.get("source_seeds", -1)) == 100
        and int(formal_protocol.get("seat_assignments_per_source", -1)) == 2
        and formal_protocol.get("closed_loop") is True
        and formal_protocol.get("common_panel") is True
    )

    registry_path = Path(config["combined_registry"]).resolve()
    registry = load_registry(registry_path)
    checks["combined_registry_file"] = (
        file_sha256(registry_path) == config["combined_registry_file_sha256"]
    )
    checks["combined_registry_runtime"] = (
        registry_fingerprint(registry)
        == config["combined_registry_and_code_sha256"]
    )

    provenance = dict(config["registry_provenance"])
    source_path = Path(provenance["source_registry"]).resolve()
    source_registry = load_registry(source_path)
    checks["external_parent_registry_file"] = (
        file_sha256(source_path) == provenance["source_registry_file_sha256"]
    )
    checks["external_parent_registry_runtime"] = (
        registry_fingerprint(source_registry)
        == provenance["source_registry_and_code_sha256"]
    )
    for entry in provenance["candidate_entries"]:
        entry_path = Path(entry["path"]).resolve()
        checks[f"candidate_entry:{entry['model_id']}"] = (
            entry_path.is_file()
            and file_sha256(entry_path) == entry["file_sha256"]
        )
        if entry_path.is_file():
            entry_payload = json.loads(entry_path.read_text(encoding="utf-8"))
            entry_spec = (
                entry_payload
                if entry_payload.get("id")
                else (entry_payload.get("models") or [{}])[0]
            )
            configured = next(
                (
                    item
                    for item in candidate_items
                    if str(item.get("id")) == str(entry["model_id"])
                ),
                {},
            )
            checks[f"candidate_source_parent:{entry['model_id']}"] = list(
                entry_spec.get("parent_models") or []
            ) == [str(configured.get("source_declared_parent"))]

    closure_path = Path(config["submission_closure"]).resolve()
    checks["submission_closure_file"] = (
        closure_path.is_file()
        and file_sha256(closure_path) == config["submission_closure_file_sha256"]
    )
    closure = json.loads(closure_path.read_text(encoding="utf-8"))
    checks["submission_closure_exact_candidates"] = set(
        (closure.get("candidates") or {}).keys()
    ) == set(candidate_ids)
    for model_id, item in closure["candidates"].items():
        archive = Path(item["archive"]).resolve()
        manifest = Path(item["manifest"]).resolve()
        checks[f"clean_archive:{model_id}"] = (
            archive.is_file() and file_sha256(archive) == item["archive_sha256"]
        )
        checks[f"clean_archive_manifest:{model_id}"] = (
            manifest.is_file() and file_sha256(manifest) == item["manifest_sha256"]
        )
        member_rows = list(item["members"])
        checks[f"clean_archive_members:{model_id}"] = all(
            Path(member["path"]).is_file()
            and file_sha256(Path(member["path"])) == member["sha256"]
            for member in member_rows
        ) and hashlib.sha256(canonical(member_rows)).hexdigest() == item[
            "members_sha256"
        ]
        spec = registry.require(model_id)
        checks[f"clean_archive_registry_binding:{model_id}"] = (
            Path(spec["path"]).resolve()
            == (Path(item["clean_root"]) / "main.py").resolve()
            and set(Path(value).resolve() for value in spec.get("code_paths") or [])
            == {Path(member["path"]).resolve() for member in member_rows}
            and spec.get("validation_runtime") == "clean_submission_archive"
        )
        checks.update(_archive_closure_checks(item))

    source_r002_sha = model_fingerprint(
        source_registry, "r002_learned_router_topday_animal_throttle"
    )
    incumbent_provenance = next(
        item
        for item in provenance["candidate_entries"]
        if str(item["model_id"]) == "v12_incumbent_r002"
    )
    incumbent_entry = json.loads(
        Path(incumbent_provenance["path"]).read_text(encoding="utf-8")
    )
    incumbent_manifest_path = Path(
        closure["candidates"]["v12_incumbent_r002"]["manifest"]
    ).resolve()
    incumbent_manifest = json.loads(
        incumbent_manifest_path.read_text(encoding="utf-8")
    )
    checks["incumbent_source_r002_serving_fingerprint"] = (
        source_r002_sha == "38afb12bd5fbc987adf752acb437abe9330bd385233c22782b35353f77be2d74"
        and incumbent_entry.get("source_serving_sha256") == source_r002_sha
        and (incumbent_manifest.get("source_provenance") or {}).get(
            "source_serving_sha256"
        )
        == source_r002_sha
    )

    for item in config["implementation_seal"]:
        path = Path(item["path"]).resolve()
        checks[f"implementation:{path.name}"] = (
            path.is_file() and file_sha256(path) == item["file_sha256"]
        )
    checks["v10_evaluator_implementation"] = (
        v10.implementation_fingerprint()
        == config["v10_evaluation_implementation_sha256"]
    )

    formal_panel_path = Path(config["formal_panel"]).resolve()
    formal_manifest_path = Path(config["formal_seed_manifest"]).resolve()
    formal_panel = json.loads(formal_panel_path.read_text(encoding="utf-8"))
    checks["formal_panel_file"] = (
        file_sha256(formal_panel_path) == config["formal_panel_file_sha256"]
    )
    checks["formal_seed_manifest_file"] = (
        formal_manifest_path.is_file()
        and file_sha256(formal_manifest_path)
        == config["formal_seed_manifest_file_sha256"]
    )
    formal_seeds = {int(row["seed"]) for row in formal_panel["records"]}
    checks["formal_panel_records_hash_locked"] = (
        formal_panel.get("records_sha256")
        == config.get("formal_panel_records_sha256")
        == config.get("formal_panel_expected_records_sha256")
        == EXPECTED_FORMAL_RECORDS_SHA256
        and hashlib.sha256(canonical(formal_panel["records"])).hexdigest()
        == EXPECTED_FORMAL_RECORDS_SHA256
    )
    checks["formal_exact_100_unique"] = (
        len(formal_panel["records"]) == len(formal_seeds) == 100
    )
    checks["formal_exact_date_strata"] = {
        str(date): sum(str(row["date"]) == str(date) for row in formal_panel["records"])
        for date in ("2026-08-18", "2026-08-19", "2026-08-20")
    } == {"2026-08-18": 34, "2026-08-19": 33, "2026-08-20": 33}
    checks["formal_zero_test"] = all(
        str(row["split"]) in {"train", "validation"}
        for row in formal_panel["records"]
    )
    lineage = dict(config.get("formal_panel_lineage") or {})
    lineage_path = Path(str(lineage.get("source_panel") or "")).resolve()
    checks["formal_locked_lineage_file"] = (
        lineage_path.is_file()
        and file_sha256(lineage_path) == lineage.get("source_panel_file_sha256")
    )
    if lineage_path.is_file():
        lineage_payload = json.loads(lineage_path.read_text(encoding="utf-8"))
        checks["formal_locked_lineage_records"] = (
            lineage.get("source_records_sha256") == EXPECTED_FORMAL_RECORDS_SHA256
            and lineage_payload.get("records_sha256")
            == EXPECTED_FORMAL_RECORDS_SHA256
            and lineage.get("replacement_selection_allowed") is False
        )

    exposure_artifacts: set[Path] = set()
    exclusion_union: set[int] = set()
    candidate_dirs = {
        Path(item["path"]).resolve().parent
        for item in provenance["candidate_entries"]
    }
    for item in formal_panel["exclusions"]["artifacts"]:
        path = Path(item["path"]).resolve()
        artifact_key = f"exclusion_artifact:{path.parent.name}:{path.name}"
        checks[artifact_key] = path.is_file() and file_sha256(path) == item["file_sha256"]
        if path.is_file():
            artifact_seeds = _parse_exposure_artifact(item)
            checks[f"{artifact_key}:seed_binding"] = (
                item.get("seed_bearing") is True
                and len(artifact_seeds) == int(item.get("seed_count", -1))
                and hashlib.sha256(canonical(sorted(artifact_seeds))).hexdigest()
                == item.get("seeds_sha256")
            )
            exclusion_union.update(artifact_seeds)
            if path.name in {"package_qa_report.json", "package_qa_v2_report.json"}:
                qa_payload = json.loads(path.read_text(encoding="utf-8"))
                qa_checks = dict(qa_payload.get("checks") or {})
                checks[f"candidate_package_qa_pass:{path.parent.name}"] = (
                    qa_payload.get("verdict") == "PASS"
                    and bool(qa_checks)
                    and all(value is True for value in qa_checks.values())
                    and str(qa_payload.get("candidate")) in candidate_ids
                )
        if path.parent in candidate_dirs:
            exposure_artifacts.add(path)
    for item in formal_panel["exclusions"].get("context_artifacts", []):
        path = Path(item["path"]).resolve()
        checks[
            f"context_artifact:{path.name}:{file_sha256(path)[:8] if path.is_file() else 'missing'}"
        ] = (
            item.get("seed_bearing") is False
            and path.is_file()
            and file_sha256(path) == item["file_sha256"]
        )
        if path.is_file() and path.suffix == ".json":
            checks[f"context_has_no_direct_seed:{path.name}"] = not _all_numeric_seeds(
                json.loads(path.read_text(encoding="utf-8"))
            )
        if path.is_file() and path.suffix.lower() == ".md":
            checks[f"context_has_no_seed_literal:{path.name}"] = not re.findall(
                r"(?i)\bseed\s*[`'\"]?([0-9]{8,12})[`'\"]?",
                path.read_text(encoding="utf-8"),
            )
    checks["formal_exclusion_disjoint"] = not (formal_seeds & exclusion_union)

    # Fail if another result-bearing JSON appeared after freeze without being
    # added to the exposure inventory.  Markdown seed literals are also
    # tracked because A2's development diagnosis is recorded in its README.
    current_exposure_artifacts: set[Path] = set()
    for directory in candidate_dirs:
        for path in directory.glob("*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if _all_numeric_seeds(payload):
                current_exposure_artifacts.add(path.resolve())
        for path in directory.glob("*.md"):
            if re.findall(
                r"(?i)\bseed\s*[`'\"]?([0-9]{8,12})[`'\"]?",
                path.read_text(encoding="utf-8"),
            ):
                current_exposure_artifacts.add(path.resolve())
    checks["candidate_exposure_inventory_complete"] = (
        current_exposure_artifacts == exposure_artifacts
    )

    raw_manifest_rows: list[dict[str, Any]] = []
    with formal_manifest_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError("formal seed manifest contains a non-object row")
                raw_manifest_rows.append(row)
    checks["formal_manifest_exact_raw_rows"] = (
        len(raw_manifest_rows) == 100
        and len({canonical(row) for row in raw_manifest_rows}) == 100
        and [canonical(row) for row in raw_manifest_rows]
        == [canonical(row) for row in formal_panel["records"]]
    )
    frozen_manifest_rows = [
        asdict(item) for item in v10.load_seed_manifest(formal_manifest_path)
    ]
    checks["formal_panel_manifest_full_record_match"] = {
        canonical(row) for row in frozen_manifest_rows
    } == {canonical(row) for row in formal_panel["records"]}
    evaluator_sources = {asdict(item)["seed"] for item in evaluator_panel(config)}
    checks["formal_evaluator_reuses_frozen_source_set"] = (
        evaluator_sources == formal_seeds
    )
    pairs = target_pairs(config)
    expected_pair_sets: set[frozenset[str]] = set()
    for item in candidate_items:
        candidate = str(item["id"])
        parent = str(item["parent"])
        expected_pair_sets.add(frozenset((candidate, parent)))
        for opponent in config["strong_opponents"]:
            expected_pair_sets.add(frozenset((candidate, str(opponent))))
            expected_pair_sets.add(frozenset((parent, str(opponent))))
    checks["exact_required_pair_set"] = (
        len(expected_pair_sets) == 23
        and {frozenset(pair) for pair in pairs} == expected_pair_sets
    )
    checks["exact_23_pairs_4600_games"] = (
        len(pairs) == 23
        and int(config["formal_protocol"]["expected_games"]) == 4600
        and int(config["formal_protocol"]["games_per_pair"]) == 200
    )
    passed = all(checks.values())
    report = {
        "schema": "kaggriculture-v12-preflight-1",
        "config": str(config_path),
        "checks": checks,
        "passed": passed,
        "combined_registry_and_code_sha256": registry_fingerprint(registry),
        "external_parent_registry_and_code_sha256": registry_fingerprint(
            source_registry
        ),
        "candidate_exposure_files": sorted(str(path) for path in exposure_artifacts),
    }
    if not passed:
        failures = [key for key, value in checks.items() if not value]
        raise ValueError(f"V12 preflight failed: {failures}")
    return report
