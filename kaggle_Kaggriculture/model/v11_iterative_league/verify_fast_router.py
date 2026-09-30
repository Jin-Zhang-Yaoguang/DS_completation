#!/usr/bin/env python3
"""Closed-loop equivalence gate for V10 ShadowRouter and V11 FastShadowRouter.

The frozen formal schedule is two Routers x four baselines x all 100 sealed
validation sources x both Router seats: 1,600 comparisons / 3,200 real games.
Results are append-only JSONL. Deterministic run/task fingerprints provide safe
resume while foreign or conflicting successful records are rejected. Test
sources are never accepted.
"""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import random
import sys
import time
from typing import Any, Mapping, Sequence

import numpy as np

try:
    from .fast_router import create_agent as create_fast_router
    from .league import HERE, _atomic_json, model_fingerprints
except ImportError:  # direct-file CLI compatibility
    from league import HERE, _atomic_json, model_fingerprints
    from fast_router import create_agent as create_fast_router

from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import (
    create_agent,
    load_registry,
    registry_fingerprint,
    resolve_path,
)
from kaggle_Kaggriculture.model.v10_replay_lolo_router.freeze_router_fit_sources import (
    validate_payload as validate_fit_exclusions,
)
from kaggle_Kaggriculture.model.v10_replay_lolo_router.report_frozen_test import (
    _validate_registry_seals,
)
from kaggle_Kaggriculture.model.v10_replay_lolo_router.router import (
    _copy_action,
    create_router,
)


SCHEMA = "kaggriculture-v11-fast-router-equivalence-task-3"
REPORT_SCHEMA = "kaggriculture-v11-fast-router-equivalence-report-3"
ROUTERS = ("rule_router", "learned_router")
OPPONENTS = ("baseline_v1", "baseline_v2", "baseline_v5", "baseline_v8")
FINAL_MODELS = (
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
FORMAL_SPLIT = "validation"
FORMAL_SOURCES = 100
FORMAL_COMPARISONS = len(ROUTERS) * len(OPPONENTS) * FORMAL_SOURCES * 2
EXPECTED_FINAL_REGISTRY_FINGERPRINT = (
    "74c47874dd6f439d5cb8943b94d264e8cba70fab8bfbf9e3139bdfb872ca9930"
)
EXPECTED_FINAL14_AUDIT_SHA256 = (
    "95f9a543a2f33c0793fb08c1f782c464bb226e2380a52685e45a28f7c87987c3"
)
EXACT_FIELDS = (
    "engine",
    "closed_loop",
    "trace_agent",
    "rng_seed",
    "statuses",
    "rewards",
    "action_sha256",
    "calls",
    "selected",
    "selection_reason",
    "selection_eligible",
    "prefix_complete",
    "prefix_match",
    "prefix_first_mismatch",
    "prefix_errors",
    "selected_fallbacks",
    "runtime_errors",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def implementation_fingerprint() -> str:
    """Bind evaluator, runtime and both Router implementations."""

    import kaggle_environments

    payload = {
        "python": list(sys.version_info[:2]),
        "numpy": np.__version__,
        "kaggle_environments": getattr(kaggle_environments, "__version__", "unknown"),
    }
    digest = hashlib.sha256(_canonical(payload))
    for path in (
        Path(__file__).resolve(),
        HERE / "fast_router.py",
        HERE.parent / "v10_replay_lolo_router" / "agent_factory.py",
        HERE.parent / "v10_replay_lolo_router" / "router.py",
    ):
        digest.update(str(path).encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _reset_rng(seed: int, seat: int) -> int:
    """Use the same deterministic RNG state at every fairness boundary."""

    value = (int(seed) * 104729 + int(seat) * 1009) % (2**32 - 1)
    random.seed(value)
    np.random.seed(value)
    return value


class Recorder:
    def __init__(self, agent: Any):
        self.agent = agent
        self.actions: list[dict[str, Any]] = []

    def __call__(self, obs: Any, configuration: Any = None):
        action = _copy_action(self.agent(obs, configuration))
        self.actions.append(action)
        return action


def _action_sha256(actions: Sequence[dict[str, Any]]) -> str:
    return hashlib.sha256(_canonical(actions)).hexdigest()


def _run(
    registry: Any,
    router_factory: Any,
    opponent_id: str,
    seed: int,
    router_seat: int,
) -> dict[str, Any]:
    """Run one game with three explicit, identical RNG reset boundaries."""

    from kaggle_environments import make

    rng_seed = _reset_rng(seed, router_seat)  # before agent construction
    router = router_factory()
    recorder = Recorder(router)
    opponent = create_agent(registry, opponent_id)
    agents = [recorder, opponent] if router_seat == 0 else [opponent, recorder]

    _reset_rng(seed, router_seat)  # before environment construction
    env = make("kaggriculture", configuration={"seed": int(seed)}, debug=False)
    _reset_rng(seed, router_seat)  # immediately before the actual run
    env.run(agents)
    diagnostics = dict(router.diagnostics())
    return {
        "engine": "kaggle_environments.make(kaggriculture)",
        "closed_loop": True,
        "trace_agent": False,
        "rng_seed": rng_seed,
        "statuses": [str(state.status) for state in env.state],
        "rewards": [float(state.reward or 0.0) for state in env.state],
        "action_sha256": _action_sha256(recorder.actions),
        "calls": len(recorder.actions),
        "selected": diagnostics.get("selected"),
        "selection_reason": diagnostics.get("selection_reason"),
        "selection_eligible": list(diagnostics.get("selection_eligible") or []),
        "prefix_complete": diagnostics.get("prefix_complete"),
        "prefix_match": diagnostics.get("prefix_match"),
        "prefix_first_mismatch": diagnostics.get("prefix_first_mismatch"),
        "prefix_errors": diagnostics.get("prefix_errors"),
        "selected_fallbacks": int(diagnostics.get("selected_fallbacks") or 0),
        "runtime_errors": list(diagnostics.get("runtime_errors") or []),
        "fast_shadow": diagnostics.get("fast_shadow") is True,
        "actions": recorder.actions,
    }


def _source_rows(
    fit_exclusions_path: Path, split: str
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    fit_exclusions_path = fit_exclusions_path.expanduser().resolve()
    payload = json.loads(fit_exclusions_path.read_text(encoding="utf-8"))
    source_grid = Path(str(payload.get("source_grid") or "")).expanduser().resolve()
    validate_fit_exclusions(payload, source_grid)
    split = "validation" if split == "val" else str(split)
    if split not in {"train", "validation"}:
        raise ValueError("Fast equivalence may use train/validation only")
    rows = [
        dict(item)
        for item in (payload.get("records") or [])
        if item.get("split") == split
    ]
    rows.sort(key=lambda item: (item["date"], int(item["seed"]), item["episode_id"]))
    if len(rows) != 100 or len({int(item["seed"]) for item in rows}) != 100:
        raise ValueError(f"expected exact 100-source {split} equivalence panel")
    if any(str(item.get("split")) == "test" for item in rows):
        raise ValueError("test source reached Fast equivalence panel")
    return rows, payload


def _validate_final14_audit(registry: Any) -> dict[str, Any]:
    """Bind equivalence to the independently audited, exact starting 14."""

    audit_path = registry.path.parent / "freeze_chain_final14_audit.json"
    if not audit_path.is_file():
        raise FileNotFoundError(f"final-14 freeze audit missing: {audit_path}")
    payload = json.loads(audit_path.read_text(encoding="utf-8"))
    evidence = (payload.get("evidence") or {}).get(
        "final_registry_exact_14_and_sealed"
    ) or {}
    current_fingerprint = registry_fingerprint(registry)
    if (
        _sha256(audit_path) != EXPECTED_FINAL14_AUDIT_SHA256
        or current_fingerprint != EXPECTED_FINAL_REGISTRY_FINGERPRINT
        or payload.get("schema") != "kaggriculture-v10-freeze-chain-audit-1"
        or payload.get("read_only") is not True
        or payload.get("environment_games_started") is not False
        or payload.get("final_test_results_opened") is not False
        or (payload.get("checks") or {}).get("final_registry_exact_14_and_sealed")
        is not True
        or evidence.get("schema") != "kaggriculture-v10-final-registry-1"
        or evidence.get("models") != list(FINAL_MODELS)
        or evidence.get("registry_and_code_sha256") != current_fingerprint
    ):
        raise ValueError("source final registry differs from the frozen final-14 audit")
    return {
        "path": str(audit_path.resolve()),
        "file_sha256": _sha256(audit_path),
        "schema": payload.get("schema"),
        "registry_and_code_sha256": current_fingerprint,
        "models": list(FINAL_MODELS),
    }


def _validate_inputs(
    registry_path: Path,
    training_report_path: Path,
    fit_exclusions_path: Path,
    split: str,
) -> tuple[Any, dict[str, Any], list[dict[str, Any]], dict[str, Any], Path]:
    registry_path = registry_path.expanduser().resolve()
    training_report_path = training_report_path.expanduser().resolve()
    fit_exclusions_path = fit_exclusions_path.expanduser().resolve()
    registry = load_registry(registry_path)
    if registry.raw.get("schema") != "kaggriculture-v10-final-registry-1":
        raise ValueError("formal equivalence requires the sealed V10 final registry")
    if tuple(registry.models) != FINAL_MODELS:
        raise ValueError("formal equivalence requires exact final rule+learned Routers")
    _validate_registry_seals(registry)
    _validate_final14_audit(registry)
    training = json.loads(training_report_path.read_text(encoding="utf-8"))
    if registry.raw.get("training_report_sha256") != _sha256(training_report_path):
        raise ValueError("final registry/training report SHA mismatch")
    if (
        training.get("test_used_for_fit") is not False
        or training.get("pre_selection_test_access") is not False
    ):
        raise ValueError("training report does not prove test isolation")
    if [str(item) for item in (training.get("classes") or [])] != list(OPPONENTS):
        raise ValueError("training classes differ from formal Router experts")
    weights_path = resolve_path(
        registry, str(registry.require("learned_router").get("weights") or "")
    )
    if (
        not weights_path.is_file()
        or _sha256(weights_path) != registry.raw.get("learned_weights_sha256")
        or _sha256(weights_path) != training.get("weights_sha256")
    ):
        raise ValueError("learned Router weights SHA mismatch")
    sources, exclusions = _source_rows(fit_exclusions_path, split)
    exclusion_seal = registry.raw.get("router_fit_source_exclusions") or {}
    if (
        exclusion_seal.get("file_sha256") != _sha256(fit_exclusions_path)
        or exclusion_seal.get("records_sha256") != exclusions.get("records_sha256")
        or exclusion_seal.get("records") != 200
    ):
        raise ValueError("final registry/Router-fit exclusion seal mismatch")
    for model_id in (*ROUTERS, *OPPONENTS):
        registry.require(model_id)
    for router_id in ROUTERS:
        spec = registry.require(router_id)
        if (
            spec.get("kind") != "router"
            or spec.get("router_kind") != router_id.split("_", 1)[0]
            or list(spec.get("experts") or []) != list(OPPONENTS)
        ):
            raise ValueError(f"unexpected logical Router spec: {router_id}")
    return registry, training, sources, exclusions, weights_path


def _run_fingerprint(
    registry: Any,
    training_report_path: Path,
    weights_path: Path,
    fit_exclusions_path: Path,
    exclusions: Mapping[str, Any],
    sources: Sequence[Mapping[str, Any]],
    split: str,
) -> tuple[str, dict[str, Any]]:
    serving = model_fingerprints(registry, (*ROUTERS, *OPPONENTS))
    provenance = {
        "equivalence_implementation_sha256": implementation_fingerprint(),
        "source_final_registry": str(registry.path),
        "source_final_registry_file_sha256": _sha256(registry.path),
        "source_final_registry_and_code_sha256": registry_fingerprint(registry),
        "serving_fingerprints": serving,
        "final14_freeze_audit": _validate_final14_audit(registry),
        "training_report": str(training_report_path.expanduser().resolve()),
        "training_report_sha256": _sha256(training_report_path.expanduser().resolve()),
        "learned_weights": str(weights_path),
        "learned_weights_sha256": _sha256(weights_path),
        "source_manifest_sha256": (
            registry.raw.get("source_manifest_seal") or {}
        ).get("file_sha256"),
        "fit_exclusions": str(fit_exclusions_path.expanduser().resolve()),
        "fit_exclusions_file_sha256": _sha256(
            fit_exclusions_path.expanduser().resolve()
        ),
        "fit_exclusions_records_sha256": exclusions.get("records_sha256"),
        "environment_split": split,
        "routers": list(ROUTERS),
        "opponents": list(OPPONENTS),
        "seats": [0, 1],
        "sources": [dict(item) for item in sources],
    }
    return _canonical_sha256({"schema": REPORT_SCHEMA, **provenance}), provenance


def _task_id(
    run_fingerprint: str,
    router_id: str,
    opponent_id: str,
    source: Mapping[str, Any],
    seat: int,
) -> str:
    return _canonical_sha256(
        {
            "run_fingerprint": run_fingerprint,
            "router_id": router_id,
            "opponent_id": opponent_id,
            "source": dict(source),
            "router_seat": int(seat),
        }
    )[:24]


def build_tasks(
    registry_path: Path,
    run_fingerprint: str,
    sources: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    tasks = []
    for router_id in ROUTERS:
        for opponent_id in OPPONENTS:
            for source in sources:
                for seat in (0, 1):
                    tasks.append(
                        {
                            "schema": SCHEMA,
                            "task_id": _task_id(
                                run_fingerprint, router_id, opponent_id, source, seat
                            ),
                            "run_fingerprint": run_fingerprint,
                            "registry": str(registry_path.expanduser().resolve()),
                            "router_id": router_id,
                            "opponent_id": opponent_id,
                            "source": dict(source),
                            "router_seat": seat,
                        }
                    )
    return tasks


def _healthy(result: Mapping[str, Any], *, fast: bool) -> bool:
    rewards = result.get("rewards")
    prefix_match = result.get("prefix_match") or {}
    prefix_errors = result.get("prefix_errors") or {}
    prefix_mismatches = result.get("prefix_first_mismatch") or {}
    eligible = [str(item) for item in (result.get("selection_eligible") or [])]
    selected = str(result.get("selected") or "")
    action_sha = str(result.get("action_sha256") or "")
    return bool(
        result.get("engine") == "kaggle_environments.make(kaggriculture)"
        and result.get("closed_loop") is True
        and result.get("trace_agent") is False
        and result.get("statuses") == ["DONE", "DONE"]
        and isinstance(rewards, list)
        and len(rewards) == 2
        and all(np.isfinite(float(value)) for value in rewards)
        and int(result.get("calls") or -1) == 719
        and len(action_sha) == 64
        and all(character in "0123456789abcdef" for character in action_sha)
        and result.get("prefix_complete") is True
        and set(prefix_match) == set(OPPONENTS)
        and set(prefix_errors) == set(OPPONENTS)
        and set(prefix_mismatches) == set(OPPONENTS)
        and all(value is True for value in prefix_match.values())
        and not any(prefix_errors.values())
        and not any(value is not None for value in prefix_mismatches.values())
        and selected in set(OPPONENTS)
        and selected in set(eligible)
        and not result.get("runtime_errors")
        and int(result.get("selected_fallbacks") or 0) == 0
        and bool(result.get("fast_shadow")) is bool(fast)
    )


def _one_comparison(task: Mapping[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    base = {
        key: task[key]
        for key in (
            "schema",
            "task_id",
            "run_fingerprint",
            "router_id",
            "opponent_id",
            "source",
            "router_seat",
        )
    }
    try:
        registry = load_registry(str(task["registry"]))
        router_id = str(task["router_id"])
        opponent_id = str(task["opponent_id"])
        seed = int((task.get("source") or {})["seed"])
        seat = int(task["router_seat"])
        spec = dict(registry.require(router_id))
        embedded = {
            str(model_id): dict(registry.require(str(model_id)))
            for model_id in (spec.get("experts") or [])
        }
        original = _run(
            registry,
            lambda: create_router(registry, spec),
            opponent_id,
            seed,
            seat,
        )
        fast = _run(
            registry,
            lambda: create_fast_router(spec, embedded, str(registry.path.parent)),
            opponent_id,
            seed,
            seat,
        )
        action_equal = original["actions"] == fast["actions"]
        original.pop("actions")
        fast.pop("actions")
        field_equal = {
            key: original.get(key) == fast.get(key) for key in EXACT_FIELDS
        }
        row = {
            **base,
            "error": None,
            "action_equal": action_equal,
            "field_equal": field_equal,
            "original": original,
            "fast": fast,
        }
        row["equivalent"] = bool(
            action_equal
            and all(field_equal.values())
            and _healthy(original, fast=False)
            and _healthy(fast, fast=True)
        )
    except Exception as exc:  # append-only failures remain retryable
        row = {
            **base,
            "error": f"{type(exc).__name__}:{exc}",
            "equivalent": False,
        }
    row["elapsed_seconds"] = time.perf_counter() - started
    semantic = {key: value for key, value in row.items() if key != "elapsed_seconds"}
    row["semantic_sha256"] = _canonical_sha256(semantic)
    return row


def _read_existing(
    path: Path,
    run_fingerprint: str,
    expected: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    successful: dict[str, dict[str, Any]] = {}
    stats = Counter()
    if not path.exists():
        return successful, dict(stats)
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            stats["physical_records"] += 1
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"malformed equivalence JSONL line {line_number}") from exc
            if row.get("run_fingerprint") != run_fingerprint:
                raise ValueError(f"foreign equivalence record at line {line_number}")
            if row.get("schema") != SCHEMA:
                raise ValueError(f"unexpected equivalence row schema at line {line_number}")
            claimed_semantic_sha = str(row.get("semantic_sha256") or "")
            semantic = {
                key: value
                for key, value in row.items()
                if key not in {"elapsed_seconds", "semantic_sha256"}
            }
            if claimed_semantic_sha != _canonical_sha256(semantic):
                raise ValueError(f"equivalence semantic hash mismatch at line {line_number}")
            task_id = str(row.get("task_id") or "")
            task = expected.get(task_id)
            if task is None:
                raise ValueError(f"unknown equivalence task_id at line {line_number}")
            for key in ("router_id", "opponent_id", "source", "router_seat"):
                if row.get(key) != task.get(key):
                    raise ValueError(
                        f"task semantic mismatch for {key} at line {line_number}"
                    )
            if row.get("error") is not None:
                stats["error_records"] += 1
                continue
            previous = successful.get(task_id)
            if previous is None:
                successful[task_id] = row
                continue
            if row.get("semantic_sha256") != previous.get("semantic_sha256"):
                stats["conflicting_success_records"] += 1
                raise ValueError(f"conflicting successful task_id: {task_id}")
            stats["duplicate_success_records"] += 1
    stats["successful_tasks"] = len(successful)
    return successful, dict(stats)


def _append(path: Path, row: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _validate_success(row: Mapping[str, Any]) -> None:
    if row.get("error") is not None:
        raise ValueError("successful equivalence row contains error")
    if row.get("equivalent") is not True or row.get("action_equal") is not True:
        raise ValueError(f"non-equivalent FastRouter task: {row.get('task_id')}")
    fields = row.get("field_equal") or {}
    original, fast = row.get("original") or {}, row.get("fast") or {}
    recomputed_fields = {
        key: original.get(key) == fast.get(key) for key in EXACT_FIELDS
    }
    if fields != recomputed_fields or not all(recomputed_fields.values()):
        raise ValueError(f"FastRouter exact-field mismatch: {row.get('task_id')}")
    if original.get("action_sha256") != fast.get("action_sha256"):
        raise ValueError(f"FastRouter action hash mismatch: {row.get('task_id')}")
    if not _healthy(original, fast=False) or not _healthy(fast, fast=True):
        raise ValueError(f"FastRouter health failure: {row.get('task_id')}")


def _build_report(
    *,
    output_path: Path,
    games_path: Path,
    formal: bool,
    run_fingerprint: str,
    provenance: Mapping[str, Any],
    tasks: Sequence[Mapping[str, Any]],
    successes: Mapping[str, Mapping[str, Any]],
    resume_stats: Mapping[str, int],
) -> dict[str, Any]:
    rows = [successes[task["task_id"]] for task in tasks if task["task_id"] in successes]
    for row in rows:
        _validate_success(row)
    coverage = Counter(
        (str(row["router_id"]), str(row["opponent_id"]), int(row["router_seat"]))
        for row in rows
    )
    expected_per_cell = len(provenance["sources"])
    exact_coverage = all(
        coverage[(router, opponent, seat)] == expected_per_cell
        for router in ROUTERS
        for opponent in OPPONENTS
        for seat in (0, 1)
    )
    selection_counts = {
        router_id: dict(
            Counter(
                str(row["fast"]["selected"])
                for row in rows
                if row["router_id"] == router_id
            )
        )
        for router_id in ROUTERS
    }
    missing = [task["task_id"] for task in tasks if task["task_id"] not in successes]
    formal_complete = bool(
        formal
        and len(tasks) == FORMAL_COMPARISONS
        and len(rows) == FORMAL_COMPARISONS
        and not missing
        and exact_coverage
    )
    report = {
        "schema": REPORT_SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "formal": bool(formal),
        "formal_complete": formal_complete,
        "test_sources_accessed": False,
        "run_fingerprint": run_fingerprint,
        **dict(provenance),
        "source_count": len(provenance["sources"]),
        "expected_comparisons": len(tasks),
        "successful_comparisons": len(rows),
        "missing_comparisons": len(missing),
        "missing_task_ids": missing,
        "coverage": {
            f"{router}__vs__{opponent}__seat{seat}": coverage[
                (router, opponent, seat)
            ]
            for router in ROUTERS
            for opponent in OPPONENTS
            for seat in (0, 1)
        },
        "exact_cell_coverage": exact_coverage,
        "all_equivalent": len(rows) == len(tasks),
        "selection_counts": selection_counts,
        "resume_audit": dict(resume_stats),
        "games_jsonl": str(games_path),
        "games_jsonl_file_sha256": _sha256(games_path) if games_path.is_file() else None,
    }
    _atomic_json(output_path, report)
    return report


def validate_formal_report(
    report_path: Path,
    source_registry_path: Path | None = None,
) -> dict[str, Any]:
    """Re-open and independently validate a complete formal equivalence run.

    This is the only evidence accepted by the Fast registry materializer and
    league formal preflight. It never launches an environment.
    """

    report_path = report_path.expanduser().resolve()
    if not report_path.is_file():
        raise FileNotFoundError(f"Fast equivalence report missing: {report_path}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("schema") != REPORT_SCHEMA:
        raise ValueError("unexpected formal FastRouter equivalence report schema")
    if (
        report.get("formal") is not True
        or report.get("formal_complete") is not True
        or report.get("all_equivalent") is not True
        or report.get("test_sources_accessed") is not False
        or report.get("environment_split") != FORMAL_SPLIT
    ):
        raise ValueError("FastRouter equivalence report is not a complete isolated formal run")
    if (
        report.get("routers") != list(ROUTERS)
        or report.get("opponents") != list(OPPONENTS)
        or report.get("seats") != [0, 1]
        or int(report.get("source_count") or -1) != FORMAL_SOURCES
        or int(report.get("expected_comparisons") or -1) != FORMAL_COMPARISONS
        or int(report.get("successful_comparisons") or -1) != FORMAL_COMPARISONS
        or int(report.get("missing_comparisons", -1)) != 0
        or report.get("missing_task_ids") != []
        or report.get("exact_cell_coverage") is not True
    ):
        raise ValueError("FastRouter formal schedule is not exact 2x4x100x2")
    sources = [dict(item) for item in (report.get("sources") or [])]
    if (
        len(sources) != FORMAL_SOURCES
        or len({int(item["seed"]) for item in sources}) != FORMAL_SOURCES
        or any(str(item.get("split")) != FORMAL_SPLIT for item in sources)
        or Counter(str(item.get("date")) for item in sources)
        != Counter({"2026-08-18": 34, "2026-08-19": 33, "2026-08-20": 33})
    ):
        raise ValueError("formal equivalence source panel is not the sealed validation panel")

    source_value = Path(str(report.get("source_final_registry") or "")).expanduser()
    if not source_value.is_absolute():
        raise ValueError("formal equivalence source registry path must be absolute")
    source_path = source_value.resolve()
    if source_registry_path is not None and source_path != source_registry_path.expanduser().resolve():
        raise ValueError("formal equivalence report belongs to a different source registry")
    training_path = Path(str(report.get("training_report") or "")).expanduser()
    exclusion_path = Path(str(report.get("fit_exclusions") or "")).expanduser()
    weights_value = Path(str(report.get("learned_weights") or "")).expanduser()
    games_value = Path(str(report.get("games_jsonl") or "")).expanduser()
    if not all(path.is_absolute() for path in (training_path, exclusion_path, weights_value, games_value)):
        raise ValueError("formal equivalence provenance paths must be absolute")
    training_path = training_path.resolve()
    exclusion_path = exclusion_path.resolve()
    weights_value = weights_value.resolve()
    games_path = games_value.resolve()

    registry, _training, sealed_sources, exclusions, weights_path = _validate_inputs(
        source_path, training_path, exclusion_path, FORMAL_SPLIT
    )
    if weights_value != weights_path.resolve():
        raise ValueError("formal equivalence report points to different learned weights")
    run_fingerprint, provenance = _run_fingerprint(
        registry,
        training_path,
        weights_path,
        exclusion_path,
        exclusions,
        sealed_sources,
        FORMAL_SPLIT,
    )
    for key, expected_value in provenance.items():
        if report.get(key) != expected_value:
            raise ValueError(f"formal equivalence provenance changed: {key}")
    if report.get("run_fingerprint") != run_fingerprint:
        raise ValueError("formal equivalence run fingerprint cannot be reproduced")
    if report.get("equivalence_implementation_sha256") != implementation_fingerprint():
        raise ValueError("Fast equivalence implementation changed after the run")
    if not games_path.is_file() or report.get("games_jsonl_file_sha256") != _sha256(games_path):
        raise ValueError("formal equivalence JSONL file/hash mismatch")

    tasks = build_tasks(registry.path, run_fingerprint, sealed_sources)
    expected = {str(task["task_id"]): task for task in tasks}
    successes, resume_stats = _read_existing(games_path, run_fingerprint, expected)
    if len(successes) != FORMAL_COMPARISONS:
        raise ValueError("formal equivalence JSONL lacks 1,600 successful comparisons")
    if int(resume_stats.get("duplicate_success_records", 0)) != 0:
        raise ValueError("formal equivalence JSONL contains duplicate successes")
    if int(resume_stats.get("conflicting_success_records", 0)) != 0:
        raise ValueError("formal equivalence JSONL contains conflicting successes")
    if report.get("resume_audit") != resume_stats:
        raise ValueError("formal equivalence report/JSONL resume audit mismatch")
    for task in tasks:
        _validate_success(successes[str(task["task_id"])])

    coverage = {
        f"{router}__vs__{opponent}__seat{seat}": sum(
            1
            for row in successes.values()
            if row["router_id"] == router
            and row["opponent_id"] == opponent
            and int(row["router_seat"]) == seat
        )
        for router in ROUTERS
        for opponent in OPPONENTS
        for seat in (0, 1)
    }
    if any(value != FORMAL_SOURCES for value in coverage.values()):
        raise ValueError("formal equivalence JSONL has incomplete router/opponent/seat cells")
    if report.get("coverage") != coverage:
        raise ValueError("formal equivalence report coverage differs from JSONL")
    selection_counts = {
        router_id: dict(
            Counter(
                str(row["fast"]["selected"])
                for row in successes.values()
                if row["router_id"] == router_id
            )
        )
        for router_id in ROUTERS
    }
    if report.get("selection_counts") != selection_counts:
        raise ValueError("formal equivalence selection summary differs from JSONL")

    return {
        "schema": REPORT_SCHEMA,
        "report": str(report_path),
        "report_file_sha256": _sha256(report_path),
        "games_jsonl": str(games_path),
        "games_jsonl_file_sha256": _sha256(games_path),
        "run_fingerprint": run_fingerprint,
        "equivalence_implementation_sha256": implementation_fingerprint(),
        "formal_complete": True,
        "all_equivalent": True,
        "test_sources_accessed": False,
        "environment_split": FORMAL_SPLIT,
        "routers": list(ROUTERS),
        "opponents": list(OPPONENTS),
        "seats": [0, 1],
        "source_count": FORMAL_SOURCES,
        "comparisons": FORMAL_COMPARISONS,
        "source_records_sha256": _canonical_sha256(sealed_sources),
        "source_final_registry": str(registry.path),
        "source_final_registry_file_sha256": _sha256(registry.path),
        "source_final_registry_and_code_sha256": registry_fingerprint(registry),
        "serving_fingerprints": model_fingerprints(
            registry, (*ROUTERS, *OPPONENTS)
        ),
        "final14_freeze_audit": _validate_final14_audit(registry),
        "training_report": str(training_path),
        "training_report_sha256": _sha256(training_path),
        "learned_weights": str(weights_path),
        "learned_weights_sha256": _sha256(weights_path),
        "source_manifest_sha256": report.get("source_manifest_sha256"),
        "fit_exclusions": str(exclusion_path),
        "fit_exclusions_file_sha256": _sha256(exclusion_path),
        "fit_exclusions_records_sha256": exclusions.get("records_sha256"),
        "exact_action_status_reward_selection_error_equivalence": True,
        "runtime_errors": 0,
        "selected_fallbacks": 0,
    }


def verify(
    registry_path: Path,
    training_report_path: Path,
    fit_exclusions_path: Path,
    output_path: Path,
    *,
    games_path: Path | None = None,
    split: str = FORMAL_SPLIT,
    limit: int | None = None,
    formal: bool = False,
    workers: int = 1,
) -> dict[str, Any]:
    registry, _training, sources, exclusions, weights_path = _validate_inputs(
        registry_path, training_report_path, fit_exclusions_path, split
    )
    if formal and limit is not None:
        raise ValueError("formal equivalence cannot use --limit")
    if formal and split != FORMAL_SPLIT:
        raise ValueError("formal equivalence is frozen to validation sources")
    if limit is not None:
        if int(limit) <= 0:
            raise ValueError("limit must be positive")
        sources = sources[: int(limit)]
    if formal and len(sources) != FORMAL_SOURCES:
        raise ValueError("formal equivalence requires all 100 validation sources")
    output_path = output_path.expanduser().resolve()
    games_path = (
        games_path.expanduser().resolve()
        if games_path is not None
        else output_path.with_suffix(".jsonl")
    )
    run_fingerprint, provenance = _run_fingerprint(
        registry,
        training_report_path,
        weights_path,
        fit_exclusions_path,
        exclusions,
        sources,
        split,
    )
    tasks = build_tasks(registry.path, run_fingerprint, sources)
    expected = {str(task["task_id"]): task for task in tasks}
    successes, _ = _read_existing(games_path, run_fingerprint, expected)
    pending = [task for task in tasks if task["task_id"] not in successes]

    workers = max(1, int(workers))
    if workers == 1:
        for task in pending:
            row = _one_comparison(task)
            _append(games_path, row)
    elif pending:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(_one_comparison, task) for task in pending]
            for future in as_completed(futures):
                _append(games_path, future.result())

    # Re-read the append-only artifact rather than trusting in-memory results.
    successes, final_stats = _read_existing(games_path, run_fingerprint, expected)
    return _build_report(
        output_path=output_path,
        games_path=games_path,
        formal=formal,
        run_fingerprint=run_fingerprint,
        provenance=provenance,
        tasks=tasks,
        successes=successes,
        resume_stats=final_stats,
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--training-report", type=Path, required=True)
    parser.add_argument("--fit-exclusions", type=Path, required=True)
    parser.add_argument("--split", choices=("train", "validation"), default=FORMAL_SPLIT)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--formal", action="store_true")
    parser.add_argument("--workers", type=int, default=max(1, min(8, os.cpu_count() or 1)))
    parser.add_argument("--games", type=Path)
    parser.add_argument(
        "--output", type=Path, default=HERE / "fast_router_equivalence_report.json"
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = verify(
        args.registry,
        args.training_report,
        args.fit_exclusions,
        args.output,
        games_path=args.games,
        split=args.split,
        limit=args.limit,
        formal=args.formal,
        workers=args.workers,
    )
    print(
        json.dumps(
            {
                "output": str(args.output.expanduser().resolve()),
                "games": report["games_jsonl"],
                "formal": report["formal"],
                "formal_complete": report["formal_complete"],
                "successful_comparisons": report["successful_comparisons"],
                "missing_comparisons": report["missing_comparisons"],
                "all_equivalent": report["all_equivalent"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["all_equivalent"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
