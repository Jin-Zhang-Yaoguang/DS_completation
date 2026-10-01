#!/usr/bin/env python3
"""V11 迭代联赛编排器。

每轮从 2026-08-18..20 官方 train+validation 清单按日分层抽取
100 个全局唯一 seed。模型池中每个无序模型对在相同 seed 面板上交换席位，
因此每对恰好运行 200 场闭环对战。底层任务执行、DONE 判定、失败重试和
结果去重直接复用 V10 pairwise evaluator；本模块负责轮次状态、积分、矩阵、
候选准入和超过 16 个模型时的确定性淘汰。
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import random
import sys
from typing import Any, Iterable, Mapping, Sequence


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from kaggle_Kaggriculture.model.v10_replay_lolo_router import pairwise_evaluate as v10  # noqa: E402
from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import (  # noqa: E402
    Registry,
    create_agent as create_registry_agent,
    load_registry,
    registry_fingerprint,
    resolve_path,
)


STATE_SCHEMA = "kaggriculture-v11-league-state-1"
ROUND_SCHEMA = "kaggriculture-v11-league-round-1"
PANEL_SCHEMA = "kaggriculture-v11-round-panel-1"
LEAGUE_SUMMARY_SCHEMA = "kaggriculture-v11-league-summary-1"
EXCLUSION_SCHEMA = "kaggriculture-v11-router-fit-exclusion-1"
INITIAL_MODELS = (
    "baseline_v1",
    "baseline_v2",
    "baseline_v5",
    "baseline_v8",
    "v1_topdays",
    "v2_topdays",
    "v5_topdays",
    "v8_topdays",
    "v5_price_slot",
    "v8_lead1",
    "v8_no_preempt",
    "v8_conservative",
    "rule_router",
    "learned_router",
)
TARGET_BASELINES = ("baseline_v1", "baseline_v2", "baseline_v5", "baseline_v8")
DATES = v10.DEFAULT_DATES
FORMAL_MAX_ATTEMPTS = 3
AUTHORITATIVE_V10_FINAL14_SHA256 = (
    "74c47874dd6f439d5cb8943b94d264e8cba70fab8bfbf9e3139bdfb872ca9930"
)
IMMUTABLE_REGISTRY_FIELDS = (
    "sealed_before_test",
    "test_used_for_fit",
    "pre_selection_test_access",
    "fixed_registry_sha256",
    "training_report_sha256",
    "training_report_schema",
    "training_implementation_sha256",
    "learned_weights_sha256",
    "source_manifest_seal",
    "fit_protocol",
    "router_fit_source_exclusions",
    "test_protocol",
    "source_registry",
    "source_final_registry_sha256",
    "source_registry_schema",
    "source_registry_raw_sha256",
    "source_registry_and_code_sha256",
    "converted_routers",
    "equivalence_contract",
    "formal_fast_router_equivalence",
    "formal_fast_router_fresh_challenge",
    "materialized_serving_fingerprints",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical(payload: Any) -> bytes:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _implementation_seal() -> dict[str, str]:
    """Freeze the orchestration/admission code for every formal state change."""

    admission = HERE / "admission_verifier.py"
    return {
        "league_sha256": _sha256_file(Path(__file__).resolve()),
        "admission_verifier_sha256": (
            _sha256_file(admission) if admission.is_file() else "missing"
        ),
    }


def _validate_implementation_seal(state: Mapping[str, Any]) -> None:
    expected = dict(state.get("orchestration_implementation") or {})
    actual = _implementation_seal()
    if expected and expected != actual:
        raise ValueError(
            "V11 orchestration/admission implementation changed after league init; "
            "start an explicitly versioned experiment instead of silently resuming"
        )


def _registry_immutable_metadata(raw: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: deepcopy(raw[key])
        for key in IMMUTABLE_REGISTRY_FIELDS
        if key in raw
    }


def _registry_immutable_metadata_sha256(raw: Mapping[str, Any]) -> str:
    return _sha256_bytes(_canonical(_registry_immutable_metadata(raw)))


def _source_identity(value: Mapping[str, Any]) -> tuple[str, str, int, str]:
    split = str(value.get("split") or "").lower()
    split = "validation" if split == "val" else split
    return (
        str(value.get("date") or value.get("source_date") or "")[:10],
        str(value.get("episode_id") or value.get("episodeId") or ""),
        int(value.get("seed") or 0),
        split,
    )


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def _state_checksum(payload: Mapping[str, Any]) -> str:
    clean = {key: value for key, value in payload.items() if key != "state_sha256"}
    return _sha256_bytes(_canonical(clean))


def save_state(path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(dict(payload))
    result["updated_at"] = _utc_now()
    result["state_sha256"] = _state_checksum(result)
    _atomic_json(path, result)
    return result


def load_state(path: Path) -> dict[str, Any]:
    path = path.expanduser().resolve()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != STATE_SCHEMA:
        raise ValueError(f"unsupported pool state schema: {payload.get('schema')!r}")
    expected = str(payload.get("state_sha256") or "")
    if not expected or expected != _state_checksum(payload):
        raise ValueError("pool state checksum mismatch; refuse unaudited resume")
    return payload


def _source_candidate(registry: Registry, value: str) -> Path | None:
    candidates = [
        (registry.path.parent / value).resolve(),
        (registry.path.parent.parent / value).resolve(),
    ]
    return next((item for item in candidates if item.is_file()), None)


def model_fingerprint(
    registry: Registry, model_id: str, _stack: tuple[str, ...] = ()
) -> str:
    """Hash one immutable serving policy, including recursive Router experts."""

    model_id = str(model_id)
    if model_id in _stack:
        raise ValueError(f"recursive model dependency: {' -> '.join((*_stack, model_id))}")
    spec = deepcopy(registry.require(model_id))
    paths: set[Path] = set()
    normalised_spec = deepcopy(spec)
    for key in ("path", "module_path", "weights"):
        if spec.get(key):
            resolved = resolve_path(registry, str(spec[key]))
            paths.add(resolved)
            normalised_spec[key] = str(resolved)
    if spec.get("source"):
        source = _source_candidate(registry, str(spec["source"]))
        if source is not None:
            paths.add(source)
        else:
            source = resolve_path(registry, str(spec["source"]))
            paths.add(source)
        normalised_spec["source"] = str(source)
    resolved_code_paths = [
        resolve_path(registry, str(value)) for value in spec.get("code_paths") or []
    ]
    paths.update(resolved_code_paths)
    if "code_paths" in normalised_spec:
        normalised_spec["code_paths"] = sorted(str(item) for item in resolved_code_paths)
    factory_kwargs = spec.get("factory_kwargs") or {}
    parent_registry_value = factory_kwargs.get("parent_registry") if isinstance(factory_kwargs, Mapping) else None
    parent_id = factory_kwargs.get("parent_id") if isinstance(factory_kwargs, Mapping) else None
    parent_dependency: Path | None = None
    if parent_registry_value and parent_id:
        module_value = spec.get("path") or spec.get("module_path")
        module_path = resolve_path(registry, str(module_value)) if module_value else registry.path
        parent_dependency = Path(str(parent_registry_value)).expanduser()
        if not parent_dependency.is_absolute():
            # CandidateAgent resolves this value relative to its own module.
            parent_dependency = (module_path.parent / parent_dependency).resolve()
        normalised_spec.setdefault("factory_kwargs", {})["parent_registry"] = str(
            parent_dependency
        )
    digest = hashlib.sha256()
    # Raw registry-relative spellings are presentation details. The canonical
    # serving spec uses resolved dependencies so registry directory rebases do
    # not make an unchanged policy appear mutated.
    digest.update(_canonical(normalised_spec))
    for path in sorted(paths):
        digest.update(str(path).encode("utf-8"))
        digest.update(path.read_bytes() if path.is_file() else b"<missing>")
    if parent_dependency is not None and parent_id:
        if not parent_dependency.is_file():
            raise FileNotFoundError(f"candidate parent registry missing: {parent_dependency}")
        digest.update(str(parent_dependency).encode("utf-8"))
        digest.update(parent_dependency.read_bytes())
        parent_registry = load_registry(parent_dependency)
        digest.update(
            model_fingerprint(
                parent_registry, str(parent_id), (*_stack, model_id)
            ).encode("ascii")
        )
    for expert_id in spec.get("experts") or []:
        digest.update(str(expert_id).encode("utf-8"))
        digest.update(
            model_fingerprint(registry, str(expert_id), (*_stack, model_id)).encode("ascii")
        )
    return digest.hexdigest()


def model_fingerprints(registry: Registry, model_ids: Sequence[str]) -> dict[str, str]:
    return {str(item): model_fingerprint(registry, str(item)) for item in model_ids}


def _model_router_ancestry(
    registry: Registry,
    model_id: str,
    stack: tuple[tuple[str, str], ...] = (),
) -> dict[str, Any] | None:
    """Resolve whether a serving model is ultimately backed by a Router."""

    key = (str(registry.path), str(model_id))
    if key in stack:
        raise ValueError("recursive candidate Router ancestry")
    spec = registry.require(str(model_id))
    kind = str(spec.get("kind") or ("router" if spec.get("router_kind") else "python"))
    if spec.get("fast_shadow") is True:
        router_spec = (spec.get("factory_kwargs") or {}).get("router_spec") or {}
        experts = [str(item) for item in router_spec.get("experts") or []]
        return {
            "router_model_id": str(model_id),
            "experts": experts,
            "fast_shadow_required": True,
        }
    if kind == "router":
        return {
            "router_model_id": str(model_id),
            "experts": [str(item) for item in spec.get("experts") or []],
            "fast_shadow_required": False,
        }
    module_value = spec.get("path") or spec.get("module_path")
    if not module_value or resolve_path(registry, str(module_value)) != (
        HERE / "candidate_agent.py"
    ).resolve():
        return None
    kwargs = spec.get("factory_kwargs") or {}
    parent_id = str(kwargs.get("parent_id") or "")
    parent_registry_value = kwargs.get("parent_registry")
    if not parent_id or not parent_registry_value:
        return None
    parent_path = Path(str(parent_registry_value)).expanduser()
    if not parent_path.is_absolute():
        parent_path = ((HERE / "candidate_agent.py").parent / parent_path).resolve()
    else:
        parent_path = parent_path.resolve()
    parent_registry = load_registry(parent_path)
    return _model_router_ancestry(parent_registry, parent_id, (*stack, key))


def model_router_ancestries(
    registry: Registry, model_ids: Sequence[str]
) -> dict[str, dict[str, Any] | None]:
    return {
        str(model_id): _model_router_ancestry(registry, str(model_id))
        for model_id in model_ids
    }


def _validate_model_ids(model_ids: Sequence[str]) -> list[str]:
    result = [str(item) for item in model_ids]
    if not result or len(result) != len(set(result)):
        raise ValueError("model ids must be non-empty and unique")
    return result


def _validate_formal_fast_evidence(
    raw: Mapping[str, Any], source_registry: Registry
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Re-read both formal FastRouter gates; embedded summaries are not evidence."""

    equivalence = raw.get("formal_fast_router_equivalence") or {}
    report_value = Path(str(equivalence.get("report") or "")).expanduser()
    if not report_value.is_absolute():
        raise ValueError("formal FastRouter equivalence report path must be absolute")
    report_path = report_value.resolve()
    if (
        not report_path.is_file()
        or _sha256_file(report_path) != equivalence.get("report_file_sha256")
    ):
        raise ValueError("formal FastRouter equivalence report file/hash mismatch")
    # Import lazily: verify_fast_router imports league helpers for generation,
    # while formal init only needs its independent, read-only evidence parser.
    try:
        from .verify_fast_router import validate_formal_report
    except ImportError:  # direct-file CLI compatibility
        from verify_fast_router import validate_formal_report
    revalidated_equivalence = validate_formal_report(report_path, source_registry.path)
    if equivalence != revalidated_equivalence:
        raise ValueError(
            "embedded FastRouter equivalence seal differs from the re-read report/JSONL"
        )
    challenge = raw.get("formal_fast_router_fresh_challenge") or {}
    challenge_value = Path(str(challenge.get("report") or "")).expanduser()
    if not challenge_value.is_absolute():
        raise ValueError("formal FastRouter fresh challenge path must be absolute")
    challenge_path = challenge_value.resolve()
    if (
        not challenge_path.is_file()
        or _sha256_file(challenge_path) != challenge.get("report_file_sha256")
    ):
        raise ValueError("formal FastRouter fresh challenge file/hash mismatch")
    try:
        from .audit_fast_router_challenge import validate_challenge_report
    except ImportError:  # direct-file CLI compatibility
        from audit_fast_router_challenge import validate_challenge_report
    revalidated_challenge = validate_challenge_report(
        challenge_path,
        report_path,
        source_registry.path,
    )
    if challenge != revalidated_challenge:
        raise ValueError(
            "embedded FastRouter fresh challenge seal differs from re-read evidence"
        )
    return revalidated_equivalence, revalidated_challenge


def validate_formal_registry_and_sources(
    registry: Registry,
    manifest_path: Path,
    exclusion_path: Path,
    excluded_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Reject lookalike 14-model registries and swapped development sources."""

    raw = registry.raw
    if raw.get("schema") != "kaggriculture-v11-fast-router-registry-1":
        raise ValueError("formal registry must be a sealed V11 FastRouter materialization")
    if tuple(registry.models) != INITIAL_MODELS or len(registry.models) != 14:
        raise ValueError("formal registry must contain exactly the ordered V10 14-model pool")
    if list(raw.get("converted_routers") or []) != ["rule_router", "learned_router"]:
        raise ValueError("formal registry must convert exactly rule_router and learned_router")
    if raw.get("source_registry_schema") != "kaggriculture-v10-final-registry-1":
        raise ValueError("fast registry is not linked to the sealed V10 final registry")
    source_registry = Path(str(raw.get("source_registry") or "")).expanduser().resolve()
    if not source_registry.is_file() or _sha256_file(source_registry) != raw.get(
        "source_final_registry_sha256"
    ):
        raise ValueError("source V10 final registry file/hash mismatch")
    source = load_registry(source_registry)
    if source.raw.get("schema") != "kaggriculture-v10-final-registry-1":
        raise ValueError("linked source is not a V10 final registry")
    if tuple(source.models) != INITIAL_MODELS or len(source.models) != 14:
        raise ValueError("linked V10 final registry is not the exact ordered 14 pool")
    if _sha256_bytes(_canonical(source.raw)) != raw.get("source_registry_raw_sha256"):
        raise ValueError("source V10 registry raw provenance mismatch")
    source_runtime_sha = registry_fingerprint(source)
    if source_runtime_sha != AUTHORITATIVE_V10_FINAL14_SHA256:
        raise ValueError("linked V10 final14 registry/code differs from the authoritative freeze audit")
    if source_runtime_sha != raw.get("source_registry_and_code_sha256"):
        raise ValueError("source V10 registry serving provenance mismatch")
    for key in (
        "sealed_before_test",
        "test_used_for_fit",
        "pre_selection_test_access",
        "fixed_registry_sha256",
        "training_report_sha256",
        "training_report_schema",
        "training_implementation_sha256",
        "learned_weights_sha256",
        "source_manifest_seal",
        "fit_protocol",
        "router_fit_source_exclusions",
        "test_protocol",
    ):
        if raw.get(key) != source.raw.get(key):
            raise ValueError(f"fast registry changed frozen V10 provenance: {key}")
    for model_id in INITIAL_MODELS:
        fast_spec = registry.require(model_id)
        source_spec = source.require(model_id)
        if model_id in {"rule_router", "learned_router"}:
            expected_spec_sha = _sha256_bytes(_canonical(source_spec))
            if (
                fast_spec.get("fast_shadow") is not True
                or fast_spec.get("source_router_spec_sha256") != expected_spec_sha
            ):
                raise ValueError(f"FastRouter proxy does not bind source {model_id}")
        elif model_fingerprint(registry, model_id) != model_fingerprint(source, model_id):
            raise ValueError(f"non-Router model changed during Fast materialization: {model_id}")
    for key, expected in (
        ("sealed_before_test", True),
        ("test_used_for_fit", False),
        ("pre_selection_test_access", False),
    ):
        if raw.get(key) is not expected:
            raise ValueError(f"formal registry seal mismatch: {key}")
    for key in (
        "training_report_sha256",
        "learned_weights_sha256",
        "fixed_registry_sha256",
        "source_registry_raw_sha256",
        "source_registry_and_code_sha256",
    ):
        if len(str(raw.get(key) or "")) != 64:
            raise ValueError(f"formal registry missing frozen provenance: {key}")
    fit = raw.get("router_fit_source_exclusions") or {}
    exclusion_file_seal = _exclusion_file_seal(exclusion_path, excluded_rows)
    exclusion_rows_hash = exclusion_file_seal["records_sha256"]
    if (
        fit.get("league_must_exclude") is not True
        or int(fit.get("records", -1)) != 200
        or fit.get("file_sha256") != _sha256_file(exclusion_path)
        or fit.get("records_sha256") != exclusion_rows_hash
    ):
        raise ValueError("league exclusion metadata differs from the Router fit seal")
    manifest_records = v10.load_seed_manifest(manifest_path)
    split_counts = defaultdict(int)
    date_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for item in manifest_records:
        split = "validation" if str(item.split).lower() == "val" else str(item.split).lower()
        split_counts[split] += 1
        date_counts[split][item.date] += 1
    seal = raw.get("source_manifest_seal") or {}
    actual_manifest_summary = {
        "file_sha256": _sha256_file(manifest_path),
        "records": len(manifest_records),
        "unique_seeds": len({int(item.seed) for item in manifest_records}),
        "dates": sorted({item.date for item in manifest_records}),
        "split_counts": dict(sorted(split_counts.items())),
        "date_counts_by_split": {
            split: dict(sorted(values.items())) for split, values in sorted(date_counts.items())
        },
    }
    for key, value in actual_manifest_summary.items():
        if seal.get(key) != value:
            raise ValueError(f"official manifest differs from the V10 frozen seal: {key}")
    if (
        actual_manifest_summary["records"] != 2090
        or actual_manifest_summary["unique_seeds"] != 2090
        or actual_manifest_summary["dates"] != list(DATES)
        or actual_manifest_summary["split_counts"]
        != {"test": 210, "train": 1670, "validation": 210}
    ):
        raise ValueError("official manifest formal structure is not 2090/1880 development")
    revalidated_equivalence, revalidated_challenge = _validate_formal_fast_evidence(
        raw, source
    )
    current_materialized = model_fingerprints(registry, INITIAL_MODELS)
    if raw.get("materialized_serving_fingerprints") != current_materialized:
        raise ValueError("materialized FastRouter serving fingerprints changed")
    # Instantiate every entry now, before any official league work begins.
    # This catches same-name placeholder specs and missing learned weights while
    # keeping the sealed test completely untouched.
    for model_id in INITIAL_MODELS:
        create_registry_agent(registry, model_id)
    return {
        "manifest": actual_manifest_summary,
        "exclusion_records_sha256": exclusion_rows_hash,
        "source_final_registry_sha256": raw["source_final_registry_sha256"],
        "formal_fast_router_equivalence": deepcopy(revalidated_equivalence),
        "formal_fast_router_fresh_challenge": deepcopy(revalidated_challenge),
    }


def load_exclusion_metadata(path: Path) -> list[dict[str, Any]]:
    """Read date/seed provenance while refusing any grid outcome payload."""

    path = path.expanduser().resolve()
    forbidden_fragments = (
        "reward",
        "score",
        "margin",
        "feature",
        "action",
        "candidate",
        "opponent",
        "status",
        "diagnostic",
    )

    def reject_outcomes(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, item in value.items():
                lowered = str(key).lower()
                if any(fragment in lowered for fragment in forbidden_fragments):
                    raise ValueError(
                        f"exclusion metadata contains forbidden outcome field: {key}"
                    )
                reject_outcomes(item)
        elif isinstance(value, list):
            for item in value:
                reject_outcomes(item)

    payloads = []
    if path.suffix.lower() in {".jsonl", ".ndjson"}:
        with path.open("r", encoding="utf-8") as handle:
            payloads = [json.loads(line) for line in handle if line.strip()]
    else:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        payloads = loaded if isinstance(loaded, list) else [loaded]
    reject_outcomes(payloads)
    rows = []

    def collect(value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                collect(item)
            return
        if not isinstance(value, Mapping):
            return
        if value.get("seed") is not None and (
            value.get("date") or value.get("source_date")
        ):
            split = str(value.get("split") or "").lower()
            split = "validation" if split == "val" else split
            if split not in {"train", "validation"}:
                raise ValueError("excluded router-fit source must be train/validation")
            rows.append(
                {
                    "date": str(value.get("date") or value.get("source_date"))[:10],
                    "seed": int(value["seed"]),
                    "episode_id": str(value.get("episode_id") or value.get("episodeId") or ""),
                    "split": split,
                }
            )
            return
        for key in ("records", "sources", "excluded_sources", "rows", "items"):
            if key in value:
                collect(value[key])

    for payload in payloads:
        collect(payload)
    unique = {}
    for row in rows:
        previous = unique.get(row["seed"])
        if previous is not None and previous != row:
            raise ValueError(f"conflicting exclusion metadata for seed {row['seed']}")
        unique[row["seed"]] = row
    if not unique:
        raise ValueError("exclusion metadata has no sources")
    return sorted(unique.values(), key=lambda item: (item["date"], item["seed"]))


def _exclusion_file_seal(path: Path, rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    path = path.expanduser().resolve()
    declared = None
    schema = None
    metadata_only = True
    if path.suffix.lower() not in {".jsonl", ".ndjson"}:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, Mapping):
            schema = payload.get("schema")
            metadata_only = payload.get("metadata_only", True) is True
            raw_records = list(payload.get("records") or [])
            if raw_records:
                calculated = _sha256_bytes(_canonical(raw_records))
                declared = str(payload.get("records_sha256") or "")
                if declared and declared != calculated:
                    raise ValueError("exclusion file records_sha256 is invalid")
                declared = calculated
    return {
        "path": str(path),
        "file_sha256": _sha256_file(path),
        "schema": schema,
        "metadata_only": metadata_only,
        "records_sha256": declared or _sha256_bytes(_canonical(list(rows))),
        "count": len(rows),
    }


def initialise_state(
    registry_path: Path,
    manifest_path: Path,
    state_path: Path,
    model_ids: Sequence[str] = INITIAL_MODELS,
    *,
    root_seed: int = 20260822,
    pool_cap: int = 16,
    require_initial_14: bool = True,
    excluded_sources_path: Path | None = None,
) -> dict[str, Any]:
    registry_path = registry_path.expanduser().resolve()
    manifest_path = manifest_path.expanduser().resolve()
    state_path = state_path.expanduser().resolve()
    if state_path.exists():
        raise FileExistsError(f"pool state already exists: {state_path}")
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    model_ids = _validate_model_ids(model_ids)
    if require_initial_14 and tuple(model_ids) != INITIAL_MODELS:
        raise ValueError("formal V11 league must start with the pre-registered V10 14-model pool")
    registry = load_registry(registry_path)
    for model_id in model_ids:
        registry.require(model_id)
    if int(pool_cap) != 16 and require_initial_14:
        raise ValueError("formal V11 league pool cap must be 16")
    if require_initial_14 and excluded_sources_path is None:
        raise ValueError("formal V11 init requires metadata-only router-fit exclusions")
    excluded_rows = (
        load_exclusion_metadata(excluded_sources_path)
        if excluded_sources_path is not None
        else []
    )
    exclusion_seal = (
        _exclusion_file_seal(excluded_sources_path, excluded_rows)
        if excluded_sources_path is not None
        else {
            "path": None,
            "file_sha256": None,
            "schema": None,
            "metadata_only": True,
            "records_sha256": _sha256_bytes(_canonical([])),
            "count": 0,
        }
    )
    excluded_seeds = {int(item["seed"]) for item in excluded_rows}
    if require_initial_14 and len(excluded_seeds) != 200:
        raise ValueError(
            f"formal router-fit exclusion must contain exactly 200 unique seeds, got {len(excluded_seeds)}"
        )
    formal_provenance = (
        validate_formal_registry_and_sources(
            registry,
            manifest_path,
            excluded_sources_path.expanduser().resolve(),
            excluded_rows,
        )
        if require_initial_14 and excluded_sources_path is not None
        else None
    )
    manifest_records = v10.load_seed_manifest(manifest_path)
    development_records = [
        item
        for item in manifest_records
        if str(item.split).lower() in {"train", "validation", "val"}
    ]
    development_seeds = {int(item.seed) for item in development_records}
    if not excluded_seeds <= development_seeds:
        raise ValueError("router-fit exclusions are not a subset of the official development manifest")
    remaining_development = development_seeds - excluded_seeds
    if require_initial_14 and len(remaining_development) != 1680:
        raise ValueError(
            f"formal first-cycle pool must contain 1680 seeds after exclusion, got {len(remaining_development)}"
        )
    payload = {
        "schema": STATE_SCHEMA,
        "created_at": _utc_now(),
        "status": "ready",
        "root_seed": int(root_seed),
        "pool_cap": int(pool_cap),
        "target_baselines": list(TARGET_BASELINES),
        "initial_models": list(model_ids),
        "active_models": list(model_ids),
        "retired_models": [],
        "model_entries": {
            model_id: {
                "entered_after_round": 0,
                "evaluated_rounds": 0,
                "serving_sha256": model_fingerprint(registry, model_id),
                "proposal": None,
            }
            for model_id in model_ids
        },
        "registry": str(registry_path),
        "registry_and_code_sha256": registry_fingerprint(registry),
        "immutable_registry_metadata": _registry_immutable_metadata(registry.raw),
        "immutable_registry_metadata_sha256": _registry_immutable_metadata_sha256(
            registry.raw
        ),
        "orchestration_implementation": _implementation_seal(),
        "manifest": str(manifest_path),
        "manifest_sha256": _sha256_file(manifest_path),
        "router_fit_exclusion": {**exclusion_seal, "seeds": sorted(excluded_seeds)},
        "formal_provenance": formal_provenance,
        "development_pool_after_exclusion": len(remaining_development),
        "rounds_per_cycle": 16,
        "current_cycle": 1,
        "next_cycle_round": 1,
        "cycle_used_development_seeds": [],
        "panel_sha256_history": [],
        "seed_usage_counts": {},
        "used_development_seeds": [],
        "used_development_sources": [],
        "next_round": 1,
        "candidate_required": False,
        "pending_candidate": None,
        "activation_for_round": None,
        "history": [],
        "goal": {
            "required_pool_size": 16,
            "required_absent_models": list(TARGET_BASELINES),
            "achieved": False,
        },
    }
    return save_state(state_path, payload)


def round_salt(state: Mapping[str, Any], round_number: int) -> tuple[str, int]:
    material = {
        "schema": PANEL_SCHEMA,
        "root_seed": int(state["root_seed"]),
        "round": int(round_number),
        "cycle": int(state.get("current_cycle", 1)),
        "cycle_round": int(state.get("next_cycle_round", round_number)),
        "manifest_sha256": str(state["manifest_sha256"]),
        "router_fit_exclusion_sha256": str(
            (state.get("router_fit_exclusion") or {}).get("records_sha256") or ""
        ),
    }
    value = _sha256_bytes(_canonical(material))
    return value, int(value[:16], 16) % (2**31 - 1)


def select_round_panel(
    records: Sequence[v10.SeedRecord],
    count: int,
    round_number: int,
    salt_sha256: str,
    dates: Sequence[str] = DATES,
    exclude_seeds: set[int] | None = None,
    usage_counts: Mapping[int, int] | None = None,
) -> list[v10.SeedRecord]:
    """Select a deterministic date-balanced train+validation panel."""

    if int(count) <= 0:
        raise ValueError("panel count must be positive")
    dates = tuple(str(item) for item in dates)
    exclude_seeds = {int(item) for item in (exclude_seeds or set())}
    usage_counts = {int(key): int(value) for key, value in (usage_counts or {}).items()}
    allowed = {"train", "validation", "val"}
    by_date: dict[str, list[v10.SeedRecord]] = {
        date: [
            item
            for item in records
            if item.date == date
            and str(item.split).lower() in allowed
            and int(item.seed) not in exclude_seeds
        ]
        for date in dates
    }
    if any(not values for values in by_date.values()):
        missing = [date for date, values in by_date.items() if not values]
        raise ValueError(f"manifest has no train+validation records for {missing}")
    quotas = {date: int(count) // len(dates) for date in dates}
    extra_start = (int(round_number) - 1) % len(dates)
    for offset in range(int(count) % len(dates)):
        quotas[dates[(extra_start + offset) % len(dates)]] += 1
    used: set[int] = set()
    panel: list[v10.SeedRecord] = []
    for date in dates:
        values = list(by_date[date])
        date_seed = int(
            hashlib.sha256(f"{salt_sha256}:{date}".encode("utf-8")).hexdigest()[:16],
            16,
        )
        rng = random.Random(date_seed)
        tiers: dict[int, list[v10.SeedRecord]] = defaultdict(list)
        for item in values:
            tiers[usage_counts.get(int(item.seed), 0)].append(item)
        values = []
        for usage in sorted(tiers):
            tier = tiers[usage]
            rng.shuffle(tier)
            values.extend(tier)
        selected = []
        for item in values:
            if int(item.seed) in used:
                continue
            used.add(int(item.seed))
            selected.append(item)
            if len(selected) == quotas[date]:
                break
        if len(selected) != quotas[date]:
            raise ValueError(
                f"not enough globally unique train+validation seeds for {date}: "
                f"need {quotas[date]}, got {len(selected)}"
            )
        panel.extend(selected)
    final_seed = int(salt_sha256[-16:], 16)
    random.Random(final_seed).shuffle(panel)
    if len(panel) != count or len({int(item.seed) for item in panel}) != count:
        raise AssertionError("round panel is not exactly globally unique")
    return panel


def _round_dir(state_path: Path, round_number: int) -> Path:
    return state_path.parent / "runs" / f"round_{int(round_number):03d}"


def _candidate_design_panel(
    state: Mapping[str, Any], activated_model: str | None
) -> tuple[int | None, str | None, set[int]]:
    """Return the panel that designed a newly activated candidate."""

    if not activated_model:
        return None, None, set()
    entry = (state.get("model_entries") or {}).get(activated_model) or {}
    source_round = int(entry.get("entered_after_round", 0))
    history = next(
        (
            item
            for item in reversed(list(state.get("history") or []))
            if int(item.get("round", -1)) == source_round
        ),
        None,
    )
    if history is None:
        raise ValueError("activated candidate design round is missing from history")
    panel_path = Path(str(history["directory"])) / "panel.json"
    if not panel_path.is_file():
        raise ValueError("activated candidate design panel is missing")
    payload = json.loads(panel_path.read_text(encoding="utf-8"))
    records = list(payload.get("records") or [])
    if _sha256_bytes(_canonical(records)) != payload.get("records_sha256"):
        raise ValueError("activated candidate design panel checksum mismatch")
    expected_sha = str(history.get("panel_sha256") or "")
    if expected_sha and expected_sha != payload.get("records_sha256"):
        raise ValueError("candidate design panel differs from round history")
    return (
        source_round,
        str(payload.get("records_sha256") or ""),
        {int(item["seed"]) for item in records},
    )


def _panel_payload(
    panel: Sequence[v10.SeedRecord],
    round_number: int,
    salt: str,
    *,
    cycle: int = 1,
    cycle_round: int = 1,
    selection_salt: str | None = None,
    selection_nonce: int = 0,
    prior_usage: Mapping[int, int] | None = None,
) -> dict[str, Any]:
    rows = [asdict(item) for item in panel]
    prior_usage = {int(key): int(value) for key, value in (prior_usage or {}).items()}
    return {
        "schema": PANEL_SCHEMA,
        "round": int(round_number),
        "cycle": int(cycle),
        "cycle_round": int(cycle_round),
        "round_salt_sha256": salt,
        "selection_salt_sha256": selection_salt or salt,
        "selection_nonce": int(selection_nonce),
        "source_splits": ["train", "validation"],
        "dates": list(DATES),
        "count": len(rows),
        "date_counts": {
            date: sum(item["date"] == date for item in rows) for date in DATES
        },
        "all_seeds_unique": len({int(item["seed"]) for item in rows}) == len(rows),
        "reused_seed_count": sum(prior_usage.get(int(item["seed"]), 0) > 0 for item in rows),
        "max_prior_reuse_count": max(
            [prior_usage.get(int(item["seed"]), 0) for item in rows] or [0]
        ),
        "min_prior_reuse_count": min(
            [prior_usage.get(int(item["seed"]), 0) for item in rows] or [0]
        ),
        "source_prior_reuse_counts": {
            str(item["seed"]): prior_usage.get(int(item["seed"]), 0) for item in rows
        },
        "records": rows,
        "records_sha256": _sha256_bytes(_canonical(rows)),
    }


def _panel_from_payload(
    payload: Mapping[str, Any],
    round_number: int,
    salt: str,
    *,
    cycle: int = 1,
    cycle_round: int = 1,
) -> list[v10.SeedRecord]:
    if payload.get("schema") != PANEL_SCHEMA:
        raise ValueError("frozen panel schema mismatch")
    if int(payload.get("round", -1)) != int(round_number):
        raise ValueError("frozen panel round mismatch")
    if str(payload.get("round_salt_sha256")) != salt:
        raise ValueError("frozen panel salt mismatch")
    if int(payload.get("cycle", -1)) != int(cycle) or int(
        payload.get("cycle_round", -1)
    ) != int(cycle_round):
        raise ValueError("frozen panel cycle mismatch")
    raw = list(payload.get("records") or [])
    if _sha256_bytes(_canonical(raw)) != payload.get("records_sha256"):
        raise ValueError("frozen panel record checksum mismatch")
    panel = [v10.SeedRecord(**dict(item)) for item in raw]
    if len(panel) != 100 or len({int(item.seed) for item in panel}) != 100:
        raise ValueError("frozen panel must contain 100 unique seeds")
    if any(str(item.split) not in {"train", "validation", "val"} for item in panel):
        raise ValueError("frozen panel contains a non-development split")
    return panel


def _expected_pairs(model_ids: Sequence[str]) -> set[tuple[str, str]]:
    return {
        (str(model_ids[left]), str(model_ids[right]))
        for left in range(len(model_ids))
        for right in range(left + 1, len(model_ids))
    }


def _deduplicate_successes(
    rows: Iterable[Mapping[str, Any]], expected_task_ids: set[str], run_fingerprint: str
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    semantic_sha: dict[str, str] = {}
    observed_rows = 0
    foreign_rows = 0
    failed_attempt_rows = 0
    identical_success_duplicates = 0

    def semantic(row: Mapping[str, Any]) -> str:
        fields = {
            key: row.get(key)
            for key in (
                "schema",
                "task_id",
                "run_fingerprint",
                "pair_id",
                "model_a",
                "model_b",
                "model_a_seat",
                "source",
                "seat_models",
                "statuses",
                "rewards",
                "done",
                "reward_a",
                "reward_b",
                "margin_a",
                "score_a",
                "model_meta",
                "agent_diagnostics",
                "seat_diagnostics",
                "error",
            )
        }
        return _sha256_bytes(_canonical(fields))

    for raw in rows:
        observed_rows += 1
        row = dict(raw)
        task_id = str(row.get("task_id") or "")
        if task_id not in expected_task_ids or row.get("run_fingerprint") != run_fingerprint:
            foreign_rows += 1
            continue
        success = (
            row.get("error") is None
            and row.get("done") is True
            and row.get("score_a") is not None
        )
        if success:
            digest = semantic(row)
            if task_id in semantic_sha:
                if semantic_sha[task_id] != digest:
                    raise ValueError(
                        f"conflicting successful results for task_id={task_id}"
                    )
                identical_success_duplicates += 1
                continue
            result[task_id] = row
            semantic_sha[task_id] = digest
        else:
            failed_attempt_rows += 1
    return result, {
        "observed_rows": observed_rows,
        "foreign_rows": foreign_rows,
        "failed_attempt_rows": failed_attempt_rows,
        "identical_success_duplicates": identical_success_duplicates,
        "unique_successes": len(result),
        "conflicting_successes": 0,
    }


def _validate_success_semantics(
    row: Mapping[str, Any],
    model_ids: Sequence[str],
    panel: Sequence[v10.SeedRecord],
    run_fingerprint: str,
    router_ancestry: Mapping[str, Mapping[str, Any] | None] | None = None,
) -> None:
    """Recompute every score-bearing field before it can enter standings."""

    if row.get("schema") != v10.SCHEMA:
        raise ValueError("score-bearing row has the wrong evaluator schema")
    if row.get("closed_loop") is not True or row.get("trace_agent") is not False:
        raise ValueError("score-bearing row is not a direct closed-loop evaluation")
    if row.get("engine") != "kaggle_environments.make(kaggriculture)":
        raise ValueError("score-bearing row did not use the official Kaggriculture engine")

    a, b = str(row.get("model_a") or ""), str(row.get("model_b") or "")
    pair_id = str(row.get("pair_id") or "")
    if (a, b) not in _expected_pairs(model_ids) or pair_id != f"{a}__vs__{b}":
        raise ValueError("successful row has invalid model/pair semantics")
    seat = row.get("model_a_seat")
    if seat not in (0, 1):
        raise ValueError("successful row has invalid seat")
    source = row.get("source")
    if not isinstance(source, Mapping):
        raise ValueError("successful row has no source identity")
    source_key = (
        str(source.get("date") or ""),
        str(source.get("episode_id") or ""),
        int(source.get("seed") or 0),
    )
    panel_map = {
        (item.date, str(item.episode_id), int(item.seed)): item for item in panel
    }
    if source_key not in panel_map or dict(source) != asdict(panel_map[source_key]):
        raise ValueError("successful row source differs from the frozen panel task")
    expected_task = v10._task_id(
        run_fingerprint, pair_id, panel_map[source_key], int(seat)
    )
    if str(row.get("task_id") or "") != expected_task:
        raise ValueError("successful row task_id does not match pair/source/seat")
    if row.get("error") is not None or row.get("done") is not True:
        raise ValueError("score-bearing row is not a successful DONE result")
    if list(row.get("statuses") or []) != ["DONE", "DONE"]:
        raise ValueError("score-bearing row is not DONE/DONE")
    rewards = list(row.get("rewards") or [])
    if len(rewards) != 2:
        raise ValueError("score-bearing row has invalid rewards")
    try:
        rewards = [float(value) for value in rewards]
        reward_a = float(row.get("reward_a"))
        reward_b = float(row.get("reward_b"))
        margin_a = float(row.get("margin_a"))
        score_a = float(row.get("score_a"))
    except (TypeError, ValueError) as exc:
        raise ValueError("score-bearing row has non-numeric outcome") from exc
    if not all(math.isfinite(value) for value in [*rewards, reward_a, reward_b, margin_a, score_a]):
        raise ValueError("score-bearing row has non-finite outcome")
    expected_a, expected_b = rewards[int(seat)], rewards[1 - int(seat)]
    expected_margin = expected_a - expected_b
    expected_score = 1.0 if expected_margin > 0 else 0.5 if expected_margin == 0 else 0.0
    if (
        reward_a != expected_a
        or reward_b != expected_b
        or margin_a != expected_margin
        or score_a not in {0.0, 0.5, 1.0}
        or score_a != expected_score
    ):
        raise ValueError("score/reward/margin fields are internally inconsistent")
    expected_seat_models = [a, b] if int(seat) == 0 else [b, a]
    if list(row.get("seat_models") or []) != expected_seat_models:
        raise ValueError("seat_models differs from model_a_seat")
    seat_diagnostics = list(row.get("seat_diagnostics") or [])
    if len(seat_diagnostics) != 2:
        raise ValueError("successful row is missing seat diagnostics")
    def diagnostic_nodes(value: Any) -> Iterable[Mapping[str, Any]]:
        if not isinstance(value, Mapping):
            return
        yield value
        # ObservedAgent stores a Router under ``router``. Candidate wrappers
        # can add one or more nested ``underlying``/``parent`` layers.
        for key in (
            "router",
            "underlying",
            "parent",
            "parent_diagnostics",
            "child",
            "agent",
            "wrapped",
        ):
            nested = value.get(key)
            if isinstance(nested, Mapping):
                yield from diagnostic_nodes(nested)

    for model_id, diagnostic in zip(expected_seat_models, seat_diagnostics):
        nodes = list(diagnostic_nodes(diagnostic))
        for node in nodes:
            if node.get("diagnostic_error") or node.get("internal_error"):
                raise ValueError(f"model {model_id} has a diagnostics failure")
            if list(node.get("runtime_errors") or []):
                raise ValueError(f"model {model_id} has an internal runtime failure")
        routers = [
            node
            for node in nodes
            if node.get("kind") == "shadow_full_expert_router"
            or "prefix_complete" in node
            or "prefix_match" in node
        ]
        expected_ancestry = (
            (router_ancestry or {}).get(model_id)
            if router_ancestry is not None
            else (
                {"experts": [], "fast_shadow_required": True}
                if model_id in {"rule_router", "learned_router"}
                else None
            )
        )
        if expected_ancestry is not None and len(routers) != 1:
            raise ValueError(
                f"Router ancestry for {model_id} requires exactly one Router diagnostic"
            )
        if expected_ancestry is None and routers:
            raise ValueError(f"non-Router model {model_id} has unexpected Router diagnostics")
        if expected_ancestry is not None and expected_ancestry.get(
            "fast_shadow_required"
        ) is True and len(expected_ancestry.get("experts") or []) != 4:
            raise ValueError(f"FastRouter ancestry for {model_id} is not the sealed four-expert pool")
        for router in routers:
            expected_experts = [
                str(item) for item in expected_ancestry.get("experts") or []
            ] if expected_ancestry is not None else []
            prefix_match = router.get("prefix_match") or {}
            prefix_errors = router.get("prefix_errors") or {}
            prefix_mismatch = router.get("prefix_first_mismatch") or {}
            selection_eligible = [
                str(item) for item in (router.get("selection_eligible") or [])
            ]
            selected = str(router.get("selected") or "")
            bad_reason = str(router.get("selection_reason") or "").lower()
            if (
                (
                    expected_ancestry is not None
                    and expected_ancestry.get("fast_shadow_required") is True
                    and router.get("fast_shadow") is not True
                )
                or router.get("prefix_complete") is not True
                or not prefix_match
                or not all(value is True for value in prefix_match.values())
                or any(values for values in prefix_errors.values())
                or any(value is not None for value in prefix_mismatch.values())
                or not selection_eligible
                or int(router.get("selected_fallbacks", 0)) != 0
                or "fallback" in bad_reason
                or "incomplete" in bad_reason
            ):
                raise ValueError(f"Router {model_id} has an internal/prefix failure")
            if expected_experts and (
                set(prefix_match) != set(expected_experts)
                or set(prefix_errors) != set(expected_experts)
                or set(prefix_mismatch) != set(expected_experts)
                or not set(selection_eligible).issubset(set(expected_experts))
                or selected not in set(expected_experts)
                or selected not in set(selection_eligible)
            ):
                raise ValueError(f"Router {model_id} diagnostics do not cover its four experts")


def build_league_summary(
    rows: Sequence[Mapping[str, Any]],
    model_ids: Sequence[str],
    expected_task_ids: set[str],
    run_fingerprint: str,
    round_number: int,
    panel: Sequence[v10.SeedRecord],
    router_ancestry: Mapping[str, Mapping[str, Any] | None] | None = None,
) -> dict[str, Any]:
    """Build total-point standings and a directed W-D-L/points matrix."""

    model_ids = _validate_model_ids(model_ids)
    successes, retry_audit = _deduplicate_successes(
        rows, expected_task_ids, run_fingerprint
    )
    if int(retry_audit.get("foreign_rows", 0)) != 0:
        raise ValueError(
            "round JSONL contains foreign task/run rows; refuse mixed-resume scoring"
        )
    for row in successes.values():
        _validate_success_semantics(
            row, model_ids, panel, run_fingerprint, router_ancestry
        )
    stats: dict[str, dict[str, Any]] = {
        model_id: {
            "model_id": model_id,
            "points": 0.0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "games": 0,
            "margin_sum": 0.0,
        }
        for model_id in model_ids
    }
    matrix: dict[str, dict[str, dict[str, Any] | None]] = {
        model_id: {other: None for other in model_ids} for model_id in model_ids
    }
    for model_id in model_ids:
        matrix[model_id][model_id] = None
    pair_stats: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    for left, right in _expected_pairs(model_ids):
        pair_stats[(left, right)] = {
            left: {"wins": 0, "draws": 0, "losses": 0, "points": 0.0, "games": 0},
            right: {"wins": 0, "draws": 0, "losses": 0, "points": 0.0, "games": 0},
        }
    for row in successes.values():
        a, b = str(row["model_a"]), str(row["model_b"])
        if a not in stats or b not in stats or a == b:
            continue
        score_a = float(row["score_a"])
        score_b = 1.0 - score_a
        margin_a = float(row.get("margin_a") or 0.0)
        pair = (a, b) if (a, b) in pair_stats else (b, a)
        for model_id, opponent, score, margin in (
            (a, b, score_a, margin_a),
            (b, a, score_b, -margin_a),
        ):
            stats[model_id]["points"] += score
            stats[model_id]["games"] += 1
            stats[model_id]["margin_sum"] += margin
            side = pair_stats[pair][model_id]
            side["points"] += score
            side["games"] += 1
            outcome = "wins" if score == 1.0 else "draws" if score == 0.5 else "losses"
            stats[model_id][outcome] += 1
            side[outcome] += 1
    for pair, values in pair_stats.items():
        left, right = pair
        matrix[left][right] = dict(values[left])
        matrix[right][left] = dict(values[right])

    # Only exact total-point ties use the tied cohort's direct games as the
    # second tie-break. All models play the same schedule, so no normalization
    # is needed for the primary score.
    tied: dict[float, list[str]] = defaultdict(list)
    for model_id, value in stats.items():
        tied[round(float(value["points"]), 10)].append(model_id)
    for points, members in tied.items():
        del points
        member_set = set(members)
        for model_id in members:
            h2h = 0.0
            for other in member_set - {model_id}:
                cell = matrix[model_id][other]
                h2h += float(cell["points"]) if cell else 0.0
            stats[model_id]["head_to_head_points"] = h2h
    standings = []
    for value in stats.values():
        value["points"] = float(value["points"])
        value["mean_margin"] = (
            float(value["margin_sum"]) / value["games"] if value["games"] else 0.0
        )
        opponent_rates = []
        for other in model_ids:
            if other == value["model_id"]:
                continue
            cell = matrix[value["model_id"]][other]
            if cell and int(cell["games"]) > 0:
                opponent_rates.append(float(cell["points"]) / int(cell["games"]))
        value["worst_opponent_score_rate"] = min(opponent_rates) if opponent_rates else 0.0
        # A complete formal round has zero unresolved errors. This field is
        # retained in the pre-registered ordering, but an incomplete round is
        # hard-failed and can never reach elimination.
        value["error_count"] = 0
        value.pop("margin_sum")
        standings.append(value)
    standings.sort(
        key=lambda item: (
            -float(item["points"]),
            -float(item["head_to_head_points"]),
            -float(item["mean_margin"]),
            -float(item["worst_opponent_score_rate"]),
            int(item["error_count"]),
            str(item["model_id"]),
        )
    )
    for rank, value in enumerate(standings, 1):
        value["rank"] = rank

    required_games = len(model_ids) * (len(model_ids) - 1) // 2 * 200
    complete_pairs = 0
    pair_completeness = {}
    expected_panel_keys = {
        (str(item.date), str(item.episode_id), int(item.seed)) for item in panel
    }
    pair_panel_integrity = {}
    for (left, right), values in pair_stats.items():
        games = int(values[left]["games"])
        pair_rows = [
            row
            for row in successes.values()
            if str(row["model_a"]) == left and str(row["model_b"]) == right
        ]
        actual_slots = [
            (
                str(row["source"]["date"]),
                str(row["source"]["episode_id"]),
                int(row["source"]["seed"]),
                int(row["model_a_seat"]),
            )
            for row in pair_rows
        ]
        expected_slots = {
            (*source_key, seat)
            for source_key in expected_panel_keys
            for seat in (0, 1)
        }
        actual_source_set = {slot[:3] for slot in actual_slots}
        exact_panel = (
            set(actual_slots) == expected_slots
            and len(actual_slots) == len(set(actual_slots))
            and actual_source_set == expected_panel_keys
        )
        complete = games == 200 and exact_panel
        complete_pairs += int(complete)
        pair_completeness[f"{left}__vs__{right}"] = {
            "games": games,
            "complete": complete,
        }
        pair_panel_integrity[f"{left}__vs__{right}"] = {
            "unique_sources": len(actual_source_set),
            "unique_source_seats": len(set(actual_slots)),
            "duplicate_source_seats": len(actual_slots) - len(set(actual_slots)),
            "exact_shared_panel": exact_panel,
        }
    all_pairs_share_panel = all(
        value["exact_shared_panel"] for value in pair_panel_integrity.values()
    )
    return {
        "schema": LEAGUE_SUMMARY_SCHEMA,
        "created_at": _utc_now(),
        "round": int(round_number),
        "run_fingerprint": run_fingerprint,
        "scoring": {"win": 1.0, "draw": 0.5, "loss": 0.0},
        "model_ids": list(model_ids),
        "model_count": len(model_ids),
        "panel": {
            "count": len(panel),
            "unique_seeds": len({int(item.seed) for item in panel}),
            "date_counts": {
                date: sum(item.date == date for item in panel) for date in DATES
            },
            "splits": sorted({str(item.split) for item in panel}),
        },
        "scheduled_games": required_games,
        "valid_games": len(successes),
        "expected_pairs": len(pair_stats),
        "complete_pairs": complete_pairs,
        "complete": (
            len(successes) == required_games
            and complete_pairs == len(pair_stats)
            and all_pairs_share_panel
        ),
        "pair_completeness": pair_completeness,
        "panel_integrity": {
            "expected_unique_sources": len(expected_panel_keys),
            "expected_seats_per_source": [0, 1],
            "all_pairs_share_exact_panel": all_pairs_share_panel,
            "pairs": pair_panel_integrity,
        },
        "retry_audit": retry_audit,
        "standings": standings,
        "matrix": matrix,
        "tie_break": [
            "总积分降序",
            "同总积分模型之间的直接对战积分降序",
            "全局平均金币差降序",
            "最差单一对手得分率降序",
            "未解决错误数升序（正式完成轮必须为 0）",
            "model_id 字典序升序",
        ],
        "elimination_rule": "排名最后者淘汰；新候选仅在首次参赛前免于依据上一轮成绩淘汰，完成一轮后无永久保护。",
    }


def render_round_report(summary: Mapping[str, Any], pool_change: Mapping[str, Any] | None = None) -> str:
    number = int(summary["round"])
    lines = [
        f"# 第 {number} 轮迭代",
        "",
        "## 模型及得分（降序排列）",
        "",
        "| 排名 | 模型 | 得分 | 胜 | 平 | 负 | 对局 | 平均金币差 | 最差对手得分率 | 同分直接积分 |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["standings"]:
        lines.append(
            f"| {row['rank']} | `{row['model_id']}` | {float(row['points']):.1f} | "
            f"{row['wins']} | {row['draws']} | {row['losses']} | {row['games']} | "
            f"{float(row['mean_margin']):.2f} | {float(row['worst_opponent_score_rate']):.3f} | "
            f"{float(row['head_to_head_points']):.1f} |"
        )
    models = list(summary["model_ids"])
    lines.extend(
        [
            "",
            f"## {len(models)}×{len(models)} 对战矩阵",
            "",
            "单元格为“胜-平-负 / 得分”，行模型对列模型。",
            "",
            "| 行\\列 | " + " | ".join(f"`{item}`" for item in models) + " |",
            "| --- | " + " | ".join("---:" for _ in models) + " |",
        ]
    )
    matrix = summary["matrix"]
    for model_id in models:
        cells = []
        for other in models:
            cell = matrix[model_id][other]
            cells.append(
                "—"
                if cell is None
                else f"{cell['wins']}-{cell['draws']}-{cell['losses']} / {float(cell['points']):.1f}"
            )
        lines.append(f"| `{model_id}` | " + " | ".join(cells) + " |")
    lines.extend(
        [
            "",
            "## 轮次审计",
            "",
            f"- 模型数：{summary['model_count']}；无序模型对：{summary['expected_pairs']}。",
            f"- 评测：100 个官方 seed × 双席位；计划 {summary['scheduled_games']} 场，"
            f"有效 {summary['valid_games']} 场。",
            f"- 日期配额：{json.dumps(summary['panel']['date_counts'], ensure_ascii=False, sort_keys=True)}。",
            f"- 开发周期：cycle {summary['panel'].get('cycle', 1)} / 第 {summary['panel'].get('cycle_round', number)} 轮；"
            f"本 panel 复用 seed {summary['panel'].get('reused_seed_count', 0)} 个；"
            f"选前复用次数 min/max={summary['panel'].get('min_prior_reuse_count', 0)}/"
            f"{summary['panel'].get('max_prior_reuse_count', 0)}。",
            f"- 全开发池轮后复用次数 min/max="
            f"{(summary['panel'].get('global_reuse_balance_after_round') or {}).get('min', 0)}/"
            f"{(summary['panel'].get('global_reuse_balance_after_round') or {}).get('max', 0)}；"
            f"按日期：{json.dumps((summary['panel'].get('global_reuse_balance_after_round') or {}).get('by_date', {}), ensure_ascii=False, sort_keys=True)}。",
            f"- Router-fit 永久排除：{summary['panel'].get('router_fit_exclusion_count', 0)} 个 seed；"
            f"metadata SHA-256 `{summary['panel'].get('router_fit_exclusion_records_sha256')}`。",
            f"- 完整状态：`{str(bool(summary['complete'])).lower()}`。",
            "- 排名规则：" + "；".join(summary["tie_break"]) + "。",
        ]
    )
    if pool_change:
        lines.extend(["", "## 轮后模型池变更", ""])
        if pool_change.get("activated_model"):
            lines.append(f"- 本轮首次参赛：`{pool_change['activated_model']}`。")
        if pool_change.get("eliminated_model"):
            lines.append(
                f"- 淘汰：`{pool_change['eliminated_model']}`；依据本轮排名最后。"
            )
        else:
            lines.append("- 淘汰：无，模型池尚未超过 16。")
        lines.append(f"- 轮后模型数：{pool_change.get('pool_size_after')}。")
        if pool_change.get("pending_model"):
            lines.append(
                f"- 待下一轮激活：`{pool_change['pending_model']}`；本轮结果不用于评测或淘汰该候选。"
            )
    return "\n".join(lines) + "\n"


def _validate_current_registry(state: Mapping[str, Any], registry: Registry) -> None:
    _validate_implementation_seal(state)
    expected_registry = str(state.get("registry_and_code_sha256") or "")
    actual_registry = registry_fingerprint(registry)
    if not expected_registry or actual_registry != expected_registry:
        raise ValueError("registry/code fingerprint changed outside audited candidate admission")
    expected_metadata = dict(state.get("immutable_registry_metadata") or {})
    actual_metadata = _registry_immutable_metadata(registry.raw)
    expected_metadata_sha = str(
        state.get("immutable_registry_metadata_sha256") or ""
    )
    if (
        actual_metadata != expected_metadata
        or _sha256_bytes(_canonical(actual_metadata)) != expected_metadata_sha
    ):
        raise ValueError("candidate registry truncated or mutated frozen pre-test provenance")
    expected = dict(state.get("model_entries") or {})
    for model_id in state["active_models"]:
        registry.require(model_id)
        actual = model_fingerprint(registry, model_id)
        recorded = str((expected.get(model_id) or {}).get("serving_sha256") or "")
        if not recorded or actual != recorded:
            raise ValueError(f"serving fingerprint changed for active model {model_id}")


def _load_round_rows(path: Path) -> list[dict[str, Any]]:
    return v10._read_jsonl(path)  # intentional reuse of the audited V10 reader


def _append_attempt_batch(
    tasks: Sequence[Mapping[str, Any]], path: Path, workers: int
) -> None:
    """Run exactly one new V10 evaluator attempt for each supplied task."""

    if not tasks:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", buffering=1) as output:
        if int(workers) <= 1:
            for task in tasks:
                output.write(
                    json.dumps(
                        v10._one_game(task),
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                    + "\n"
                )
            return
        with ProcessPoolExecutor(
            max_workers=min(int(workers), len(tasks))
        ) as pool:
            futures = {pool.submit(v10._one_game, task): task for task in tasks}
            for future in as_completed(futures):
                output.write(
                    json.dumps(
                        future.result(),
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                    + "\n"
                )


def _attempt_state(
    rows: Sequence[Mapping[str, Any]],
    tasks: Sequence[Mapping[str, Any]],
    model_ids: Sequence[str],
    panel: Sequence[v10.SeedRecord],
    run_fingerprint: str,
    router_ancestry: Mapping[str, Mapping[str, Any] | None] | None = None,
) -> tuple[set[str], dict[str, int], dict[str, list[str]]]:
    """Classify strict successes and persistently count all task attempts."""

    expected = {str(task["task_id"]): dict(task) for task in tasks}
    counts = {task_id: 0 for task_id in expected}
    successes: set[str] = set()
    invalid_reasons: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        task_id = str(row.get("task_id") or "")
        if task_id not in expected or row.get("run_fingerprint") != run_fingerprint:
            continue
        counts[task_id] += 1
        if counts[task_id] > FORMAL_MAX_ATTEMPTS:
            raise ValueError(
                f"task {task_id} exceeds the cumulative three-attempt budget"
            )
        claimed_success = row.get("error") is None and row.get("done") is True
        if not claimed_success:
            continue
        try:
            _validate_success_semantics(
                row, model_ids, panel, run_fingerprint, router_ancestry
            )
        except ValueError as exc:
            invalid_reasons[task_id].append(str(exc))
        else:
            successes.add(task_id)
    return successes, counts, dict(invalid_reasons)


def _pending_retry_tasks(
    tasks: Sequence[Mapping[str, Any]],
    strict_successes: set[str],
    attempt_counts: Mapping[str, int],
) -> list[dict[str, Any]]:
    """Return tasks with persistent retry budget; safe across process resume."""

    task_by_id = {str(task["task_id"]): dict(task) for task in tasks}
    return [
        task_by_id[task_id]
        for task_id in sorted(task_by_id)
        if task_id not in strict_successes
        and int(attempt_counts.get(task_id, 0)) < FORMAL_MAX_ATTEMPTS
    ]


def build_failure_audit(
    rows: Sequence[Mapping[str, Any]],
    tasks: Sequence[Mapping[str, Any]],
    run_fingerprint: str,
    attempts: int,
    strict_success_task_ids: set[str] | None = None,
    invalid_success_reasons: Mapping[str, Sequence[str]] | None = None,
) -> dict[str, Any]:
    expected = {str(task["task_id"]): dict(task) for task in tasks}
    histories: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        task_id = str(row.get("task_id") or "")
        if task_id in expected and row.get("run_fingerprint") == run_fingerprint:
            histories[task_id].append(row)
    unresolved = []
    for task_id, task in expected.items():
        task_rows = histories.get(task_id, [])
        successful = (
            task_id in strict_success_task_ids
            if strict_success_task_ids is not None
            else any(
                row.get("error") is None and row.get("done") is True
                for row in task_rows
            )
        )
        if successful:
            continue
        last = task_rows[-1] if task_rows else {}
        unresolved.append(
            {
                "task_id": task_id,
                "pair_id": task["pair_id"],
                "model_a": task["model_a"],
                "model_b": task["model_b"],
                "model_a_seat": task["model_a_seat"],
                "source": task["source"],
                "observed_attempts": len(task_rows),
                "last_error": last.get("error") if last else "missing_result",
                "last_statuses": last.get("statuses", []),
                "last_done": last.get("done", False),
                "invalid_success_reasons": list(
                    (invalid_success_reasons or {}).get(task_id, [])
                ),
            }
        )
    return {
        "schema": "kaggriculture-v11-round-failure-audit-1",
        "created_at": _utc_now(),
        "run_fingerprint": run_fingerprint,
        "configured_attempts": int(attempts),
        "policy": "hard_fail_no_imputation_no_loss_assignment",
        "expected_tasks": len(expected),
        "successful_tasks": len(expected) - len(unresolved),
        "unresolved_tasks": len(unresolved),
        "unresolved": unresolved,
    }


def run_round(
    state_path: Path,
    *,
    workers: int = 1,
    max_attempts: int = 3,
    games_per_pair: int = 200,
) -> dict[str, Any]:
    state_path = state_path.expanduser().resolve()
    state = load_state(state_path)
    _validate_implementation_seal(state)
    if state.get("goal", {}).get("achieved"):
        raise ValueError("league goal already achieved")
    if state.get("candidate_required"):
        raise ValueError("previous round still requires exactly one admitted candidate")
    if int(games_per_pair) != 200:
        raise ValueError("formal V11 round requires exactly 200 games per unordered pair")
    if int(max_attempts) != FORMAL_MAX_ATTEMPTS:
        raise ValueError("formal V11 retry budget is fixed at three cumulative attempts per task")
    if int(state.get("next_cycle_round", 1)) > int(state.get("rounds_per_cycle", 16)):
        state["current_cycle"] = int(state.get("current_cycle", 1)) + 1
        state["next_cycle_round"] = 1
        state["cycle_used_development_seeds"] = []
        state = save_state(state_path, state)
    cycle = int(state.get("current_cycle", 1))
    cycle_round = int(state.get("next_cycle_round", 1))
    registry = load_registry(state["registry"])
    _validate_current_registry(state, registry)
    activated_model = None
    pending = state.get("pending_candidate")
    if pending:
        activated_model = str(pending["model_id"])
        if activated_model in state["active_models"]:
            raise ValueError("pending candidate is already active")
        registry.require(activated_model)
        actual = model_fingerprint(registry, activated_model)
        if actual != state["model_entries"][activated_model]["serving_sha256"]:
            raise ValueError("pending candidate serving fingerprint changed")
        state["active_models"].append(activated_model)
        state["pending_candidate"] = None
        state["activation_for_round"] = {
            "round": int(state["next_round"]),
            "model_id": activated_model,
        }
        state["status"] = "ready"
        state = save_state(state_path, state)
    elif state.get("activation_for_round") and int(
        state["activation_for_round"].get("round", -1)
    ) == int(state["next_round"]):
        activated_model = str(state["activation_for_round"]["model_id"])
    design_round, design_panel_sha, design_panel_seeds = _candidate_design_panel(
        state, activated_model
    )
    manifest = Path(state["manifest"])
    if _sha256_file(manifest) != state["manifest_sha256"]:
        raise ValueError("official manifest changed since league initialization")
    exclusion_state = state.get("router_fit_exclusion") or {}
    if exclusion_state.get("path"):
        exclusion_path = Path(str(exclusion_state["path"]))
        exclusion_rows = load_exclusion_metadata(exclusion_path)
        current_exclusion = _exclusion_file_seal(exclusion_path, exclusion_rows)
        for key in ("file_sha256", "records_sha256", "count"):
            if current_exclusion.get(key) != exclusion_state.get(key):
                raise ValueError(f"Router-fit exclusion changed since init: {key}")
    round_number = int(state["next_round"])
    model_ids = list(state["active_models"])
    router_ancestry = model_router_ancestries(registry, model_ids)
    round_dir = _round_dir(state_path, round_number)
    round_dir.mkdir(parents=True, exist_ok=True)
    meta_path = round_dir / "round_meta.json"
    panel_path = round_dir / "panel.json"
    games_path = round_dir / "games.jsonl"
    pairwise_path = round_dir / "pairwise_summary.json"
    summary_path = round_dir / "league_summary.json"
    report_path = round_dir / "report.md"
    failure_path = round_dir / "failure_audit.json"

    # Activation is persisted before expensive evaluation. On a later resume,
    # recover that audit fact from the frozen round metadata rather than
    # pretending no candidate entered this round.
    if meta_path.exists() and activated_model is None:
        activated_model = json.loads(meta_path.read_text(encoding="utf-8")).get(
            "activated_model"
        )

    salt_sha256, random_seed = round_salt(state, round_number)
    if panel_path.exists():
        panel_payload = json.loads(panel_path.read_text(encoding="utf-8"))
        panel = _panel_from_payload(
            panel_payload,
            round_number,
            salt_sha256,
            cycle=cycle,
            cycle_round=cycle_round,
        )
    else:
        if meta_path.exists():
            raise ValueError("round metadata exists but its frozen panel is missing")
        records = v10.load_seed_manifest(manifest)
        permanent_exclusions = {
            int(item)
            for item in (state.get("router_fit_exclusion") or {}).get("seeds", [])
        }
        cycle_exclusions = {
            int(item) for item in state.get("cycle_used_development_seeds", [])
        }
        prior_usage = {
            int(key): int(value)
            for key, value in (state.get("seed_usage_counts") or {}).items()
        }
        panel = []
        panel_payload = {}
        for nonce in range(100):
            selection_salt = (
                salt_sha256
                if nonce == 0
                else _sha256_bytes(f"{salt_sha256}:panel-nonce:{nonce}".encode("utf-8"))
            )
            candidate = select_round_panel(
                records,
                100,
                cycle_round,
                selection_salt,
                exclude_seeds=(
                    permanent_exclusions | cycle_exclusions | design_panel_seeds
                ),
                usage_counts=prior_usage,
            )
            candidate_payload = _panel_payload(
                candidate,
                round_number,
                salt_sha256,
                cycle=cycle,
                cycle_round=cycle_round,
                selection_salt=selection_salt,
                selection_nonce=nonce,
                prior_usage=prior_usage,
            )
            if candidate_payload["records_sha256"] not in set(
                state.get("panel_sha256_history", [])
            ):
                panel, panel_payload = candidate, candidate_payload
                break
        if not panel:
            raise RuntimeError("unable to construct a non-repeated panel after 100 deterministic salts")
        _atomic_json(panel_path, panel_payload)
    permanent_exclusions = {
        int(item) for item in (state.get("router_fit_exclusion") or {}).get("seeds", [])
    }
    current_seeds = {int(item.seed) for item in panel}
    if current_seeds & permanent_exclusions:
        raise ValueError("frozen panel overlaps Router-fit exclusions")
    if current_seeds & design_panel_seeds:
        raise ValueError(
            "candidate first-evaluation panel overlaps its immediately previous design panel"
        )
    prior_cycle_reserved = {
        int(item["seed"])
        for item in state.get("used_development_sources", [])
        if int(item.get("round", -1)) != round_number
        and int(item.get("cycle", 1)) == cycle
    }
    if current_seeds & prior_cycle_reserved:
        raise ValueError("frozen panel overlaps an earlier round in the same cycle")
    reserved = {int(item) for item in state.get("used_development_seeds", [])}
    reserved.update(current_seeds)
    state["used_development_seeds"] = sorted(reserved)
    cycle_reserved = {
        int(item) for item in state.get("cycle_used_development_seeds", [])
    }
    cycle_reserved.update(current_seeds)
    state["cycle_used_development_seeds"] = sorted(cycle_reserved)
    existing_sources = {
        (int(item["round"]), int(item["seed"]))
        for item in state.get("used_development_sources", [])
    }
    usage_counts = {
        int(key): int(value)
        for key, value in (state.get("seed_usage_counts") or {}).items()
    }
    for item in panel:
        key = (round_number, int(item.seed))
        if key not in existing_sources:
            prior_reuse = usage_counts.get(int(item.seed), 0)
            state["used_development_sources"].append(
                {
                    "round": round_number,
                    "cycle": cycle,
                    "cycle_round": cycle_round,
                    "date": item.date,
                    "seed": int(item.seed),
                    "episode_id": item.episode_id,
                    "split": item.split,
                    "prior_reuse_count": prior_reuse,
                }
            )
            usage_counts[int(item.seed)] = prior_reuse + 1
    state["seed_usage_counts"] = {
        str(key): value for key, value in sorted(usage_counts.items())
    }
    all_development = [
        item
        for item in v10.load_seed_manifest(manifest)
        if str(item.split).lower() in {"train", "validation", "val"}
        and int(item.seed) not in permanent_exclusions
    ]
    reuse_values = [usage_counts.get(int(item.seed), 0) for item in all_development]
    reuse_by_date = {}
    for date in DATES:
        values = [
            usage_counts.get(int(item.seed), 0)
            for item in all_development
            if item.date == date
        ]
        reuse_by_date[date] = {
            "min": min(values, default=0),
            "max": max(values, default=0),
        }
    state["seed_reuse_balance"] = {
        "eligible_sources": len(all_development),
        "min": min(reuse_values, default=0),
        "max": max(reuse_values, default=0),
        "by_date": reuse_by_date,
    }
    if panel_payload["records_sha256"] not in state.get("panel_sha256_history", []):
        state.setdefault("panel_sha256_history", []).append(
            panel_payload["records_sha256"]
        )
    state = save_state(state_path, state)
    run_fingerprint = v10.evaluation_fingerprint(
        registry, model_ids, panel, games_per_pair, False
    )
    tasks = v10.build_tasks(registry, model_ids, panel, run_fingerprint, False)
    current_meta = {
        "schema": ROUND_SCHEMA,
        "round": round_number,
        "cycle": cycle,
        "cycle_round": cycle_round,
        "status": "running",
        "model_ids": model_ids,
        "model_fingerprints": model_fingerprints(registry, model_ids),
        "router_ancestry": deepcopy(router_ancestry),
        "registry": str(registry.path),
        "registry_and_code_sha256": registry_fingerprint(registry),
        "evaluation_implementation_sha256": v10.implementation_fingerprint(),
        "orchestration_implementation": deepcopy(
            state.get("orchestration_implementation")
        ),
        "manifest": str(manifest),
        "manifest_sha256": state["manifest_sha256"],
        "round_salt_sha256": salt_sha256,
        "random_seed": random_seed,
        "panel_sha256": panel_payload["records_sha256"],
        "panel_reused_seed_count": panel_payload["reused_seed_count"],
        "router_fit_exclusion_records_sha256": (
            state.get("router_fit_exclusion") or {}
        ).get("records_sha256"),
        "router_fit_exclusion_count": (
            state.get("router_fit_exclusion") or {}
        ).get("count", 0),
        "games_per_pair": games_per_pair,
        "expected_pairs": len(model_ids) * (len(model_ids) - 1) // 2,
        "expected_tasks": len(tasks),
        "run_fingerprint": run_fingerprint,
        "activated_model": activated_model,
        "activated_candidate_source_round": design_round,
        "activated_candidate_design_panel_sha256": design_panel_sha,
        "activated_candidate_design_panel_overlap": len(
            current_seeds & design_panel_seeds
        ),
    }
    if meta_path.exists():
        previous = json.loads(meta_path.read_text(encoding="utf-8"))
        comparable = {key: value for key, value in previous.items() if key not in {"status", "completed_at"}}
        current_comparable = {
            key: value
            for key, value in current_meta.items()
            if key not in {"status", "completed_at"}
        }
        if comparable != current_comparable:
            raise ValueError("round metadata/fingerprint mismatch; refuse mixed resume")
    else:
        _atomic_json(meta_path, current_meta)

    state["status"] = "round_running"
    state["current_round"] = {
        "round": round_number,
        "cycle": cycle,
        "cycle_round": cycle_round,
        "directory": str(round_dir),
        "run_fingerprint": run_fingerprint,
    }
    save_state(state_path, state)

    expected_ids = {str(task["task_id"]) for task in tasks}
    rows: list[dict[str, Any]] = []
    pairwise: dict[str, Any] = {}
    attempt_audit_path = round_dir / "attempt_audit.json"
    while True:
        rows = _load_round_rows(games_path)
        strict_successes, attempt_counts, invalid_reasons = _attempt_state(
            rows, tasks, model_ids, panel, run_fingerprint, router_ancestry
        )
        pending = _pending_retry_tasks(tasks, strict_successes, attempt_counts)
        _atomic_json(
            attempt_audit_path,
            {
                "schema": "kaggriculture-v11-cumulative-attempt-audit-1",
                "created_at": _utc_now(),
                "run_fingerprint": run_fingerprint,
                "max_attempts_per_task": FORMAL_MAX_ATTEMPTS,
                "expected_tasks": len(expected_ids),
                "strict_successes": len(strict_successes),
                "pending_with_budget": len(pending),
                "exhausted_without_success": sum(
                    task_id not in strict_successes
                    and attempt_counts.get(task_id, 0) >= FORMAL_MAX_ATTEMPTS
                    for task_id in expected_ids
                ),
                "attempt_counts": dict(sorted(attempt_counts.items())),
                "invalid_success_reasons": invalid_reasons,
            },
        )
        if len(strict_successes) == len(expected_ids) or not pending:
            break
        # One append-only attempt per still-eligible task. Counts are recovered
        # from JSONL on every resume, so restarting cannot reset the budget.
        _append_attempt_batch(pending, games_path, int(workers))
    rows = _load_round_rows(games_path)
    strict_successes, attempt_counts, invalid_reasons = _attempt_state(
        rows, tasks, model_ids, panel, run_fingerprint, router_ancestry
    )
    strict_complete = len(strict_successes) == len(expected_ids)
    scoring_rows = []
    for row in rows:
        task_id = str(row.get("task_id") or "")
        if task_id not in expected_ids or row.get("run_fingerprint") != run_fingerprint:
            scoring_rows.append(row)
            continue
        if task_id in strict_successes:
            try:
                _validate_success_semantics(
                    row, model_ids, panel, run_fingerprint, router_ancestry
                )
            except ValueError:
                continue
            scoring_rows.append(row)
        elif row.get("done") is not True or row.get("error") is not None:
            scoring_rows.append(row)
    pairwise = v10.summarise(
        scoring_rows, model_ids, games_per_pair, expected_ids, run_fingerprint, False
    )
    pairwise["formal_gate_complete"] = bool(
        pairwise.get("formal_gate_complete") and strict_complete
    )
    pairwise["cumulative_retry_audit"] = {
        "path": str(attempt_audit_path),
        "file_sha256": _sha256_file(attempt_audit_path),
        "max_attempts_per_task": FORMAL_MAX_ATTEMPTS,
        "max_observed_attempts": max(attempt_counts.values(), default=0),
        "invalid_success_tasks": len(invalid_reasons),
    }
    pairwise["provenance"] = {
        "round": round_number,
        "cycle": cycle,
        "cycle_round": cycle_round,
        "round_salt_sha256": salt_sha256,
        "random_seed": random_seed,
        "registry": str(registry.path),
        "registry_and_code_sha256": registry_fingerprint(registry),
        "evaluation_implementation_sha256": v10.implementation_fingerprint(),
        "orchestration_implementation": deepcopy(
            state.get("orchestration_implementation")
        ),
        "router_ancestry": deepcopy(router_ancestry),
        "manifest": str(manifest),
        "manifest_sha256": state["manifest_sha256"],
        "panel": [asdict(item) for item in panel],
        "panel_sha256": panel_payload["records_sha256"],
        "panel_reused_seed_count": panel_payload["reused_seed_count"],
        "panel_max_prior_reuse_count": panel_payload["max_prior_reuse_count"],
        "panel_min_prior_reuse_count": panel_payload["min_prior_reuse_count"],
        "activated_candidate_source_round": design_round,
        "activated_candidate_design_panel_sha256": design_panel_sha,
        "activated_candidate_design_panel_overlap": len(
            current_seeds & design_panel_seeds
        ),
        "router_fit_exclusion": deepcopy(state.get("router_fit_exclusion")),
        "source_splits": ["train", "validation"],
        "games_jsonl": str(games_path),
    }
    _atomic_json(pairwise_path, pairwise)
    summary = build_league_summary(
        scoring_rows,
        model_ids,
        expected_ids,
        run_fingerprint,
        round_number,
        panel,
        router_ancestry,
    )
    summary["panel"].update(
        {
            "cycle": cycle,
            "cycle_round": cycle_round,
            "reused_seed_count": panel_payload["reused_seed_count"],
            "max_prior_reuse_count": panel_payload["max_prior_reuse_count"],
            "min_prior_reuse_count": panel_payload["min_prior_reuse_count"],
            "router_fit_exclusion_count": (
                state.get("router_fit_exclusion") or {}
            ).get("count", 0),
            "router_fit_exclusion_records_sha256": (
                state.get("router_fit_exclusion") or {}
            ).get("records_sha256"),
            "global_reuse_balance_after_round": deepcopy(
                state.get("seed_reuse_balance")
            ),
        }
    )
    summary["provenance"] = deepcopy(pairwise["provenance"])
    _atomic_json(summary_path, summary)
    _atomic_text(report_path, render_round_report(summary))
    if not pairwise["formal_gate_complete"] or not summary["complete"]:
        failure_audit = build_failure_audit(
            rows,
            tasks,
            run_fingerprint,
            FORMAL_MAX_ATTEMPTS,
            strict_success_task_ids=strict_successes,
            invalid_success_reasons=invalid_reasons,
        )
        _atomic_json(failure_path, failure_audit)
        state = load_state(state_path)
        state["status"] = "round_incomplete"
        state["current_round"]["valid_games"] = summary["valid_games"]
        state["current_round"]["failure_audit"] = str(failure_path)
        state["current_round"]["unresolved_tasks"] = failure_audit[
            "unresolved_tasks"
        ]
        save_state(state_path, state)
        return summary

    # If the newly activated model made the evaluated pool 17, it has now
    # competed on a fresh panel and is fully eligible for the same deterministic
    # elimination rule as every historical model. This prevents adaptive reuse
    # of the panel that created it.
    eliminated = None
    active_after = list(model_ids)
    if len(active_after) > int(state["pool_cap"]):
        eliminated = _lowest_model(summary, set(active_after))
        active_after.remove(eliminated)
    if len(active_after) > int(state["pool_cap"]):
        raise AssertionError("pool cap enforcement failed")
    achieved = (
        len(active_after) == int(state["goal"]["required_pool_size"])
        and not (set(state["goal"]["required_absent_models"]) & set(active_after))
    )
    pool_change = {
        "activated_model": activated_model,
        "eliminated_model": eliminated,
        "pool_size_after": len(active_after),
        "active_models_after": list(active_after),
        "goal_achieved": achieved,
    }
    _atomic_text(report_path, render_round_report(summary, pool_change))

    current_meta["status"] = "complete"
    current_meta["completed_at"] = _utc_now()
    _atomic_json(meta_path, current_meta)
    state = load_state(state_path)
    for model_id in model_ids:
        state["model_entries"][model_id]["evaluated_rounds"] = int(
            state["model_entries"][model_id].get("evaluated_rounds", 0)
        ) + 1
    state["active_models"] = active_after
    if eliminated:
        state["retired_models"].append(
            {
                "model_id": eliminated,
                "eliminated_after_round": round_number,
                "reason": "本轮总排名最后；按预注册 tie-break 决定同分顺序",
                "serving_sha256": state["model_entries"][eliminated]["serving_sha256"],
            }
        )
    state["history"].append(
        {
            "round": round_number,
            "cycle": cycle,
            "cycle_round": cycle_round,
            "status": "complete",
            "directory": str(round_dir),
            "model_ids": model_ids,
            "run_fingerprint": run_fingerprint,
            "panel_sha256": panel_payload["records_sha256"],
            "panel_reused_seed_count": panel_payload["reused_seed_count"],
            "round_salt_sha256": salt_sha256,
            "league_summary": str(summary_path),
            "report": str(report_path),
            "activated_model": activated_model,
            "candidate_added": None,
            "eliminated_model": eliminated,
            "active_models_after": list(active_after),
            "pool_change": pool_change,
        }
    )
    state["goal"]["achieved"] = achieved
    state["goal"]["achieved_after_round"] = round_number if achieved else None
    state["status"] = "goal_achieved" if achieved else "awaiting_candidate"
    state["candidate_required"] = not achieved
    state["current_round"] = None
    state["activation_for_round"] = None
    state["next_round"] = round_number + 1
    state["next_cycle_round"] = cycle_round + 1
    if achieved:
        baseline_presence = sorted(
            set(state["goal"]["required_absent_models"]) & set(active_after)
        )
        if baseline_presence:
            raise AssertionError("terminal evidence cannot seal while baselines remain")
        state["terminal_evidence"] = {
            "schema": "kaggriculture-v11-terminal-state-evidence-1",
            "achieved_after_round": round_number,
            "active_models": list(active_after),
            "active_model_count": len(active_after),
            "required_absent_models": list(
                state["goal"]["required_absent_models"]
            ),
            "required_absent_models_present": baseline_presence,
            "serving_fingerprints": {
                model_id: state["model_entries"][model_id]["serving_sha256"]
                for model_id in active_after
            },
            "source_pool_registry": str(registry.path),
            "source_pool_registry_file_sha256": _sha256_file(registry.path),
            "source_pool_registry_and_code_sha256": registry_fingerprint(registry),
            "terminal_round_summary": str(summary_path),
            "terminal_round_summary_file_sha256": _sha256_file(summary_path),
            "terminal_round_matrix_sha256": _sha256_bytes(
                _canonical(summary["matrix"])
            ),
            "orchestration_implementation": deepcopy(
                state.get("orchestration_implementation")
            ),
        }
    saved = save_state(state_path, state)
    if achieved:
        report = report_path.read_text(encoding="utf-8")
        report += (
            "\n## 终局冻结输入\n\n"
            f"- Pool state checksum：`{saved['state_sha256']}`。\n"
            f"- 终局 summary SHA-256：`{saved['terminal_evidence']['terminal_round_summary_file_sha256']}`。\n"
            f"- 终局 matrix SHA-256：`{saved['terminal_evidence']['terminal_round_matrix_sha256']}`。\n"
            f"- active 16：{json.dumps(active_after, ensure_ascii=False)}。\n"
            f"- 四个 baseline 均已退出：`true`。\n"
        )
        _atomic_text(report_path, report)
    return summary


def _proposal_registry_path(proposal: Mapping[str, Any], proposal_path: Path) -> Path | None:
    value = proposal.get("registry_path")
    if not value and isinstance(proposal.get("registry"), Mapping):
        value = proposal["registry"].get("path")
    if not value:
        return None
    path = Path(str(value)).expanduser()
    return path.resolve() if path.is_absolute() else (proposal_path.parent / path).resolve()


def _validate_proposal(
    proposal: Mapping[str, Any],
    candidate_id: str,
    *,
    source_round: int,
    first_evaluation_round: int,
) -> dict[str, Any]:
    required = {
        "model_id",
        "registry_entry",
        "parent_models",
        "hypothesis",
        "change_scope",
        "code_paths",
        "smoke_evidence",
    }
    missing = sorted(key for key in required if key not in proposal)
    if missing:
        raise ValueError(f"candidate proposal missing fields: {missing}")
    if str(proposal["model_id"]) != candidate_id:
        raise ValueError("proposal model_id differs from requested candidate")
    evidence = proposal.get("smoke_evidence")
    if not isinstance(evidence, Mapping) or evidence.get("done") is not True:
        raise ValueError("candidate needs smoke_evidence.done=true")
    if list(evidence.get("statuses") or []) != ["DONE", "DONE"]:
        raise ValueError("candidate smoke must end DONE/DONE")
    if int(evidence.get("steps", 0)) != 720:
        raise ValueError("candidate smoke must prove 720 steps")
    if int(proposal.get("source_round", -1)) != int(source_round):
        raise ValueError("proposal source_round differs from the completed design round")
    if int(proposal.get("first_evaluation_round", -1)) != int(first_evaluation_round):
        raise ValueError("candidate first evaluation must be the next fresh-panel round")
    if proposal.get("same_panel_performance_claim") is not False:
        raise ValueError("candidate may not claim performance on its design-round panel")
    if int(evidence.get("source_round", -1)) != int(source_round):
        raise ValueError("smoke source_round mismatch")
    if int(evidence.get("first_evaluation_round", -1)) != int(first_evaluation_round):
        raise ValueError("smoke first_evaluation_round mismatch")
    smoke_path_value = evidence.get("path")
    smoke_sha = str(evidence.get("sha256") or "")
    if not smoke_path_value or len(smoke_sha) != 64:
        raise ValueError("candidate smoke must bind an external report path and SHA-256")
    smoke_path = Path(str(smoke_path_value)).expanduser()
    if not smoke_path.is_absolute():
        raise ValueError("candidate smoke report path must be absolute")
    smoke_path = smoke_path.resolve()
    if not smoke_path.is_file() or _sha256_file(smoke_path) != smoke_sha:
        raise ValueError("candidate smoke report file/hash mismatch")
    smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
    embedded = {key: value for key, value in evidence.items() if key not in {"path", "sha256"}}
    if smoke != embedded:
        raise ValueError("proposal smoke evidence differs from its bound report")
    mutation = proposal.get("mutation") or {}
    registry_entry = proposal.get("registry_entry") or {}
    parents = [str(item) for item in proposal.get("parent_models") or []]
    entry_parents = [str(item) for item in registry_entry.get("parent_models") or []]
    factory_kwargs = registry_entry.get("factory_kwargs") or {}
    if len(parents) != 1 or entry_parents != parents or str(
        factory_kwargs.get("parent_id") or ""
    ) != parents[0]:
        raise ValueError("proposal/registry/factory direct parent bindings disagree")
    if (
        str(smoke.get("candidate_id") or "") != candidate_id
        or str(smoke.get("parent_id") or "") != parents[0]
        or str(smoke.get("mutation_name") or "") != str(mutation.get("name") or "")
        or dict(smoke.get("mutation_params") or {}) != dict(mutation.get("params") or {})
    ):
        raise ValueError("candidate smoke identity/mutation bindings disagree")
    sources = list(smoke.get("development_sources") or [])
    if len(sources) != 6 or len(
        {
            (str(item.get("date")), str(item.get("episode_id")), int(item.get("seed", 0)))
            for item in sources
        }
    ) != 6:
        raise ValueError("candidate smoke must bind six unique explicit sources")
    if _sha256_bytes(_canonical(sources)) != smoke.get("development_sources_sha256"):
        raise ValueError("candidate smoke development-source digest mismatch")
    gates = {
        "passed": evidence.get("passed") is True,
        "functionality_only": evidence.get("functionality_only") is True,
        "performance_evidence_false": evidence.get("performance_evidence") is False,
        "design_panel_smoke_only": evidence.get("source_panel_reused_only_for_smoke") is True,
        "six_unique_seeds": int(evidence.get("seeds", 0)) >= 6,
        "candidate_games": int(evidence.get("candidate_games", 0)) >= 12,
        "parent_control_games": int(evidence.get("parent_control_games", 0)) >= 12,
        "all_done": evidence.get("all_done") is True,
        "all_720_steps": evidence.get("all_720_steps") is True,
        "zero_stderr": evidence.get("zero_stderr") is True,
        "real_action_difference": evidence.get("real_action_difference") is True,
        "changed_games": int(evidence.get("changed_games", 0)) > 0,
        "changed_steps": int(evidence.get("action_difference_steps", 0)) > 0,
    }
    failed = [name for name, passed in gates.items() if not passed]
    if failed:
        raise ValueError(f"candidate smoke admission gates failed: {failed}")
    return smoke


def _normalise_registry_entry(entry: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(dict(entry))
    model_id = str(result.get("id") or "")
    result.setdefault("family", model_id)
    result.setdefault("lineage", result["family"])
    result.setdefault("tags", [result["tag"]] if result.get("tag") else [])
    return result


def _lowest_model(summary: Mapping[str, Any], eligible: set[str]) -> str:
    ordered = [
        str(row["model_id"])
        for row in summary["standings"]
        if str(row["model_id"]) in eligible
    ]
    if not ordered:
        raise ValueError("no evaluated model is eligible for deterministic elimination")
    return ordered[-1]


def _validate_candidate_parent(
    parent_id: str, state: Mapping[str, Any], summary: Mapping[str, Any]
) -> None:
    if parent_id not in {str(item) for item in state.get("active_models") or []}:
        raise ValueError("candidate direct parent is not active in the completed round")
    standings = list(summary.get("standings") or [])
    if not standings or str(standings[0].get("model_id") or "") != parent_id:
        raise ValueError("candidate direct parent must be the completed round leader")


def _validate_candidate_wrapper(
    registry: Registry,
    entry: Mapping[str, Any],
    candidate_id: str,
    parent_id: str,
    expected_parent_sha256: str,
) -> None:
    """Bind an admitted candidate to the audited residual wrapper and parent."""

    module_value = entry.get("path") or entry.get("module_path")
    if str(entry.get("kind") or "python") != "python" or not module_value:
        raise ValueError("candidate must be the audited Python residual wrapper")
    module_path = resolve_path(registry, str(module_value))
    expected_module = (HERE / "candidate_agent.py").resolve()
    if module_path != expected_module or str(entry.get("factory") or "") != "create_agent":
        raise ValueError("candidate path/factory is not the audited residual wrapper")
    actual_code_paths = {
        resolve_path(registry, str(value)) for value in entry.get("code_paths") or []
    }
    expected_code_paths = {
        (HERE / "candidate_agent.py").resolve(),
        (HERE / "mutation_catalog.py").resolve(),
    }
    if actual_code_paths != expected_code_paths:
        raise ValueError("candidate code_paths differ from the audited wrapper package")
    kwargs = entry.get("factory_kwargs") or {}
    if (
        str(kwargs.get("candidate_id") or "") != candidate_id
        or str(kwargs.get("parent_id") or "") != parent_id
    ):
        raise ValueError("candidate wrapper identity/direct-parent kwargs mismatch")
    parent_registry_value = kwargs.get("parent_registry")
    if not parent_registry_value:
        raise ValueError("candidate wrapper has no parent_registry")
    parent_registry_path = Path(str(parent_registry_value)).expanduser()
    if not parent_registry_path.is_absolute():
        parent_registry_path = (module_path.parent / parent_registry_path).resolve()
    else:
        parent_registry_path = parent_registry_path.resolve()
    if not parent_registry_path.is_file():
        raise ValueError("candidate runtime parent_registry is missing")
    parent_registry = load_registry(parent_registry_path)
    parent_registry.require(parent_id)
    actual_parent_sha = model_fingerprint(parent_registry, parent_id)
    if actual_parent_sha != str(expected_parent_sha256):
        raise ValueError("candidate runtime parent dependency is stale or substituted")


def add_candidate(
    state_path: Path,
    proposal_path: Path,
    *,
    registry_path: Path | None = None,
    admission_workers: int = 1,
) -> dict[str, Any]:
    """Admit exactly one smoke-tested strategy after a completed round."""

    state_path = state_path.expanduser().resolve()
    proposal_path = proposal_path.expanduser().resolve()
    state = load_state(state_path)
    _validate_implementation_seal(state)
    if not state.get("candidate_required") or state.get("status") != "awaiting_candidate":
        raise ValueError("no completed round is waiting for a candidate")
    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    candidate_id = str(proposal.get("model_id") or "")
    last = state["history"][-1]
    smoke = _validate_proposal(
        proposal,
        candidate_id,
        source_round=int(last["round"]),
        first_evaluation_round=int(state["next_round"]),
    )
    if candidate_id in state["active_models"] or candidate_id in {
        item["model_id"] for item in state["retired_models"]
    }:
        raise ValueError(f"candidate id is not a new immutable version: {candidate_id}")
    registry_path = (
        registry_path.expanduser().resolve()
        if registry_path is not None
        else _proposal_registry_path(proposal, proposal_path)
    )
    if registry_path is None:
        raise ValueError("provide --registry-next or proposal.registry_path")
    registry = load_registry(registry_path)
    registry.require(candidate_id)
    if _registry_immutable_metadata(registry.raw) != dict(
        state.get("immutable_registry_metadata") or {}
    ):
        raise ValueError("candidate registry does not preserve frozen pre-test provenance")
    if _registry_immutable_metadata_sha256(registry.raw) != str(
        state.get("immutable_registry_metadata_sha256") or ""
    ):
        raise ValueError("candidate registry immutable provenance hash mismatch")

    # Candidate admission may add registry entries but may not mutate any
    # active historical policy under the same id.
    for model_id in state["active_models"]:
        registry.require(model_id)
        actual = model_fingerprint(registry, model_id)
        recorded = state["model_entries"][model_id]["serving_sha256"]
        if actual != recorded:
            raise ValueError(f"candidate registry mutates active model {model_id}")
    registry_entry = deepcopy(registry.require(candidate_id))
    if _normalise_registry_entry(proposal["registry_entry"]) != registry_entry:
        raise ValueError("proposal.registry_entry differs from admitted registry entry")
    parent_id = str(proposal["parent_models"][0])
    summary_path = Path(last["league_summary"])
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if not summary.get("complete"):
        raise ValueError("cannot admit a candidate after an incomplete round")
    _validate_candidate_parent(parent_id, state, summary)
    design_panel_path = Path(str(last["directory"])) / "panel.json"
    if not design_panel_path.is_file():
        raise ValueError("candidate design round panel is missing")
    design_panel = json.loads(design_panel_path.read_text(encoding="utf-8"))
    design_records = list(design_panel.get("records") or [])
    if (
        _sha256_bytes(_canonical(design_records))
        != design_panel.get("records_sha256")
        or str(last.get("panel_sha256") or "")
        != str(design_panel.get("records_sha256") or "")
    ):
        raise ValueError("candidate design panel/history checksum mismatch")
    design_identities = {_source_identity(item) for item in design_records}
    if any(
        _source_identity(item) not in design_identities
        for item in smoke["development_sources"]
    ):
        raise ValueError("candidate smoke source is not an exact design-panel source")
    factory_kwargs = registry_entry.get("factory_kwargs") or {}
    mutation = proposal.get("mutation") or {}
    if (
        [str(item) for item in registry_entry.get("parent_models") or []]
        != [parent_id]
        or str(factory_kwargs.get("parent_id") or "") != parent_id
        or str(factory_kwargs.get("mutation_name") or "")
        != str(mutation.get("name") or "")
        or dict(factory_kwargs.get("mutation_params") or {})
        != dict(mutation.get("params") or {})
        or int(registry_entry.get("source_round", -1)) != int(last["round"])
        or int(registry_entry.get("first_evaluation_round", -1))
        != int(state["next_round"])
    ):
        raise ValueError("candidate registry entry does not match proposal lineage/mutation")
    _validate_candidate_wrapper(
        registry,
        registry_entry,
        candidate_id,
        parent_id,
        str(state["model_entries"][parent_id]["serving_sha256"]),
    )
    candidate_sha = model_fingerprint(registry, candidate_id)
    parent_sha = model_fingerprint(registry, parent_id)
    if candidate_sha == parent_sha:
        raise ValueError("candidate serving policy is a renamed clone of its direct parent")
    smoke_bindings = {
        "registry_path": str(smoke.get("admitted_registry") or "") == str(registry.path),
        "registry_file": smoke.get("admitted_registry_file_sha256")
        == _sha256_file(registry.path),
        "registry_and_code": smoke.get("admitted_registry_and_code_sha256")
        == registry_fingerprint(registry),
        "candidate_serving": smoke.get("candidate_serving_sha256") == candidate_sha,
        "parent_serving": smoke.get("parent_serving_sha256") == parent_sha,
    }
    if not all(smoke_bindings.values()):
        failed = sorted(key for key, passed in smoke_bindings.items() if not passed)
        raise ValueError(
            f"candidate smoke is not bound to the admitted registry/policies: {failed}"
        )

    # Do not trust optimizer-produced booleans: independently run 24 fresh
    # trajectories (candidate/control × six sources × both seats) here.
    try:
        from .admission_verifier import verify_candidate
    except ImportError:  # direct-script CLI
        from admission_verifier import verify_candidate
    independent = verify_candidate(
        registry.path,
        candidate_id,
        parent_id,
        list(smoke["development_sources"]),
        workers=max(1, int(admission_workers)),
    )
    if independent.get("passed") is not True:
        raise ValueError("independent candidate admission rerun failed")
    admission_path = Path(last["directory"]) / f"admission_{candidate_id}.json"
    independent.update(
        {
            "source_round": int(last["round"]),
            "first_evaluation_round": int(state["next_round"]),
            "proposal": str(proposal_path),
            "proposal_sha256": _sha256_file(proposal_path),
            "optimizer_smoke": str(
                (proposal.get("smoke_evidence") or {}).get("path") or ""
            ),
            "optimizer_smoke_sha256": str(
                (proposal.get("smoke_evidence") or {}).get("sha256") or ""
            ),
            "candidate_serving_sha256": candidate_sha,
            "parent_serving_sha256": parent_sha,
            "admission_verifier_sha256": _implementation_seal()[
                "admission_verifier_sha256"
            ],
        }
    )
    _atomic_json(admission_path, independent)

    state["model_entries"][candidate_id] = {
        "entered_after_round": int(last["round"]),
        "evaluated_rounds": 0,
        "serving_sha256": candidate_sha,
        "proposal": str(proposal_path),
        "proposal_sha256": _sha256_file(proposal_path),
        "independent_admission": str(admission_path),
        "independent_admission_sha256": _sha256_file(admission_path),
    }

    state["registry"] = str(registry.path)
    state["registry_and_code_sha256"] = registry_fingerprint(registry)
    state["candidate_required"] = False
    state["pending_candidate"] = {
        "model_id": candidate_id,
        "proposal": str(proposal_path),
        "proposal_sha256": _sha256_file(proposal_path),
        "admitted_after_round": int(last["round"]),
        "serving_sha256": state["model_entries"][candidate_id]["serving_sha256"],
        "source_round": int(last["round"]),
        "design_panel_sha256": str(last.get("panel_sha256") or ""),
        "independent_admission": str(admission_path),
        "independent_admission_sha256": _sha256_file(admission_path),
    }
    last["candidate_added"] = candidate_id
    last["candidate_proposal"] = str(proposal_path)
    state["status"] = "ready"
    pool_change = {
        "activated_model": last.get("activated_model"),
        "pending_model": candidate_id,
        "eliminated_model": last.get("eliminated_model"),
        "pool_size_after": len(state["active_models"]),
        "active_models_after": list(state["active_models"]),
        "goal_achieved": False,
    }
    last["pool_change"] = pool_change
    report_path = Path(last["report"])
    _atomic_text(report_path, render_round_report(summary, pool_change))
    return save_state(state_path, state)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="initialize the formal 14-model pool")
    init_parser.add_argument("--registry", type=Path, required=True)
    init_parser.add_argument("--manifest", type=Path, required=True)
    init_parser.add_argument("--state", type=Path, default=HERE / "pool_state.json")
    init_parser.add_argument("--root-seed", type=int, default=20260822)
    init_parser.add_argument("--pool-cap", type=int, default=16)
    init_parser.add_argument(
        "--excluded-sources",
        type=Path,
        help="metadata-only 200 Router-fit train/validation sources; required formally",
    )
    init_parser.add_argument("--models", nargs="+", default=list(INITIAL_MODELS))
    init_parser.add_argument("--development", action="store_true", help="allow a non-formal small initial registry in tests")

    run_parser = subparsers.add_parser("run-round", help="run or resume exactly one formal round")
    run_parser.add_argument("--state", type=Path, default=HERE / "pool_state.json")
    run_parser.add_argument("--workers", type=int, default=max(1, min(20, os.cpu_count() or 1)))
    run_parser.add_argument("--max-attempts", type=int, default=3)

    add_parser = subparsers.add_parser("add-candidate", help="admit the optimizer's one candidate")
    add_parser.add_argument("--state", type=Path, default=HERE / "pool_state.json")
    add_parser.add_argument("--proposal", type=Path, required=True)
    add_parser.add_argument("--registry-next", type=Path)
    add_parser.add_argument("--workers", type=int, default=max(1, min(12, os.cpu_count() or 1)))

    status_parser = subparsers.add_parser("status", help="print compact pool status")
    status_parser.add_argument("--state", type=Path, default=HERE / "pool_state.json")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "init":
        state = initialise_state(
            args.registry,
            args.manifest,
            args.state,
            args.models,
            root_seed=args.root_seed,
            pool_cap=args.pool_cap,
            require_initial_14=not args.development,
            excluded_sources_path=args.excluded_sources,
        )
    elif args.command == "run-round":
        summary = run_round(
            args.state, workers=args.workers, max_attempts=args.max_attempts
        )
        state = load_state(args.state)
        state["last_round_complete"] = bool(summary["complete"])
        state["last_round_valid_games"] = int(summary["valid_games"])
    elif args.command == "add-candidate":
        state = add_candidate(
            args.state,
            args.proposal,
            registry_path=args.registry_next,
            admission_workers=args.workers,
        )
    else:
        state = load_state(args.state)
    print(
        json.dumps(
            {
                "status": state["status"],
                "active_models": state["active_models"],
                "model_count": len(state["active_models"]),
                "next_round": state["next_round"],
                "cycle": state.get("current_cycle", 1),
                "next_cycle_round": state.get("next_cycle_round", 1),
                "candidate_required": state["candidate_required"],
                "pending_candidate": (state.get("pending_candidate") or {}).get("model_id"),
                "goal_achieved": state["goal"]["achieved"],
                "state_sha256": state["state_sha256"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
