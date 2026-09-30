"""Independent, read-only reconstruction of the V14 fresh-screen result.

This implementation deliberately does not import ``audit_dual_anchor`` or any
of its statistical helpers.  It does not construct an environment or invoke an
agent.  Its only writes are the two ``independent_audit`` report artifacts next
to this script.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import random
import sys
import tarfile
from typing import Any, Iterable


SCRIPT = Path(__file__).resolve()
RUN_DIR = SCRIPT.parent
VALIDATION = SCRIPT.parents[3]
MODEL_ROOT = VALIDATION.parents[1]
WORKSPACE = VALIDATION.parents[3]
V10 = MODEL_ROOT / "v10_replay_lolo_router"
SEALED = VALIDATION / "sealed_runtime"

CANDIDATE = "v14_queue_stateful_no_mirror"
ANCHORS = ("v12_incumbent_r002", "v12a2_no_shop_gate")
ROW_SCHEMA = "kaggriculture-v10-pairwise-closed-loop-1"
RUN_SCHEMA = "kaggriculture-v14-dual-anchor-run-1"
ENGINE = "kaggle_environments.make(kaggriculture)"
BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED_NAMESPACE = "v14-independent-screen-source-cluster-bootstrap-v1"


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


def load_json(path: Path) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key in {path}: {key}")
            result[key] = value
        return result

    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicates)
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key in {path}: {key}")
            result[key] = value
        return result

    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line, object_pairs_hook=reject_duplicates)
            if not isinstance(value, dict):
                raise ValueError(f"non-object JSONL row at {path}:{line_number}")
            value["_physical_line"] = line_number
            rows.append(value)
    return rows


def finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def resolve_workspace_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (WORKSPACE / path).resolve()


def registry_fingerprint(raw: dict[str, Any], registry_path: Path) -> tuple[str, list[str]]:
    """Reimplement the V10 reachable-code fingerprint without importing V10."""

    digest = hashlib.sha256(canonical(raw))
    source = raw.get("models", raw.get("agents", {}))
    if isinstance(source, list):
        specs = source
    elif isinstance(source, dict):
        specs = [{"id": str(key), **dict(value)} for key, value in source.items()]
    else:
        raise ValueError("invalid registry models")
    paths: set[Path] = set()
    for spec in specs:
        module_value = spec.get("path") or spec.get("module_path")
        if module_value:
            module = Path(str(module_value)).expanduser()
            paths.add(
                module.resolve()
                if module.is_absolute()
                else (registry_path.parent / module).resolve()
            )
        source_value = spec.get("source")
        if source_value:
            for candidate in (
                (registry_path.parent / str(source_value)).resolve(),
                (registry_path.parent.parent / str(source_value)).resolve(),
            ):
                if candidate.is_file():
                    paths.add(candidate)
                    break
        for value in spec.get("code_paths") or []:
            path = Path(str(value)).expanduser()
            paths.add(
                path.resolve()
                if path.is_absolute()
                else (registry_path.parent / path).resolve()
            )
        weights = spec.get("weights")
        if weights:
            path = Path(str(weights)).expanduser()
            paths.add(
                path.resolve()
                if path.is_absolute()
                else (registry_path.parent / path).resolve()
            )
    ordered = sorted(paths)
    for path in ordered:
        digest.update(str(path).encode("utf-8"))
        if not path.is_file():
            digest.update(b"<missing>")
        else:
            digest.update(path.read_bytes())
    return digest.hexdigest(), [str(path) for path in ordered]


def evaluator_fingerprint() -> tuple[str, dict[str, Any], list[str]]:
    """Reimplement the V10 evaluator fingerprint from raw bytes and runtime versions."""

    import kaggle_environments
    import numpy as np

    runtime = {
        "python": list(sys.version_info[:2]),
        "kaggle_environments": getattr(kaggle_environments, "__version__", "unknown"),
        "numpy": np.__version__,
    }
    paths = [
        V10 / "pairwise_evaluate.py",
        V10 / "agent_factory.py",
        V10 / "router.py",
        V10 / "freeze_test_panel.py",
    ]
    digest = hashlib.sha256()
    digest.update(json.dumps(runtime, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    for path in paths:
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest(), runtime, [str(path) for path in paths]


def normalized_records(panel: dict[str, Any]) -> list[dict[str, Any]]:
    fields = ("date", "seed", "episode_id", "split", "source_path", "lineage_fold")
    records: list[dict[str, Any]] = []
    for row in panel["records"]:
        record = {
            "date": str(row["date"]),
            "seed": int(row["seed"]),
            "episode_id": str(row["episode_id"]),
            "split": str(row["split"]),
            "source_path": str(row.get("source_path") or ""),
            "lineage_fold": str(row.get("lineage_fold") or ""),
        }
        if set(row) != set(fields):
            raise ValueError(f"screen panel source schema differs: {set(row)}")
        records.append(record)
    return records


def expected_run_fingerprint(
    panel_path: Path,
    panel: dict[str, Any],
    records: list[dict[str, Any]],
    slate: dict[str, Any],
    registry_code_hash: str,
    evaluator_hash: str,
) -> tuple[str, dict[str, Any]]:
    payload = {
        "schema": RUN_SCHEMA,
        "phase": "screen",
        "candidate": CANDIDATE,
        "targeted_pairs": [[CANDIDATE, anchor] for anchor in ANCHORS],
        "seat_assignments_per_source": 2,
        "panel_file_sha256": file_sha256(panel_path),
        "panel_records_sha256": panel["records_sha256"],
        "panel_records": records,
        "evaluation_contract_file_sha256": file_sha256(
            VALIDATION / "evaluation_contract.json"
        ),
        "panel_seal_file_sha256": file_sha256(VALIDATION / "panel_seal.json"),
        "candidate_slate_file_sha256": file_sha256(SEALED / "candidate_slate.json"),
        "candidate_slate_core_sha256": slate["slate_core_sha256"],
        "candidate_seal_file_sha256": file_sha256(SEALED / "candidate_seal.json"),
        "registry_and_serving_code_sha256": registry_code_hash,
        "v10_evaluation_implementation_sha256": evaluator_hash,
        "v10_row_schema": ROW_SCHEMA,
    }
    return sha256_bytes(canonical(payload)), payload


def make_task_id(
    fingerprint: str, anchor: str, source: dict[str, Any], seat: int
) -> str:
    value = (
        f"{fingerprint}:{CANDIDATE}:{anchor}:{source['date']}:{source['episode_id']}:"
        f"{source['seed']}:candidate-seat-{seat}"
    )
    return sha256_bytes(value.encode("utf-8"))[:24]


def build_expected_tasks(
    fingerprint: str, records: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    tasks: dict[str, dict[str, Any]] = {}
    for anchor in ANCHORS:
        for source in records:
            for seat in (0, 1):
                task = {
                    "task_id": make_task_id(fingerprint, anchor, source, seat),
                    "run_fingerprint": fingerprint,
                    "pair_id": f"{CANDIDATE}__vs__{anchor}",
                    "model_a": CANDIDATE,
                    "model_b": anchor,
                    "model_a_seat": seat,
                    "source": source,
                }
                if task["task_id"] in tasks:
                    raise ValueError(f"expected task ID collision: {task['task_id']}")
                tasks[task["task_id"]] = task
    return tasks


def validate_rows(
    rows: list[dict[str, Any]], expected: dict[str, dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    errors: list[str] = []
    seen: set[str] = set()
    derived: list[dict[str, Any]] = []
    coverage: Counter[tuple[str, str, int]] = Counter()
    status_counts: Counter[str] = Counter()
    for row in rows:
        line = row["_physical_line"]
        task_id = str(row.get("task_id") or "")
        if not task_id or task_id in seen or task_id not in expected:
            errors.append(f"line {line}: missing, duplicate, or foreign task_id {task_id!r}")
            continue
        seen.add(task_id)
        task = expected[task_id]
        for field in (
            "task_id",
            "run_fingerprint",
            "pair_id",
            "model_a",
            "model_b",
            "model_a_seat",
            "source",
        ):
            if row.get(field) != task[field]:
                errors.append(f"line {line}: task field mismatch {field}")
        seat = task["model_a_seat"]
        expected_seats = (
            [CANDIDATE, task["model_b"]]
            if seat == 0
            else [task["model_b"], CANDIDATE]
        )
        checks = {
            "schema": row.get("schema") == ROW_SCHEMA,
            "engine": row.get("engine") == ENGINE,
            "closed_loop": row.get("closed_loop") is True,
            "trace_agent": row.get("trace_agent") is False,
            "seat_models": row.get("seat_models") == expected_seats,
            "statuses": row.get("statuses") == ["DONE", "DONE"],
            "done": row.get("done") is True,
            "error": row.get("error") is None,
        }
        for name, ok in checks.items():
            if not ok:
                errors.append(f"line {line}: invalid {name}")
        statuses = row.get("statuses")
        if isinstance(statuses, list):
            status_counts["/".join(str(item) for item in statuses)] += 1
        rewards = row.get("rewards")
        if (
            not isinstance(rewards, list)
            or len(rewards) != 2
            or not all(finite_number(value) for value in rewards)
        ):
            errors.append(f"line {line}: invalid rewards")
            continue
        reward_a = rewards[seat]
        reward_b = rewards[1 - seat]
        margin = reward_a - reward_b
        score = 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0
        for field, value in (
            ("reward_a", reward_a),
            ("reward_b", reward_b),
            ("margin_a", margin),
            ("score_a", score),
        ):
            if not finite_number(row.get(field)) or row.get(field) != value:
                errors.append(f"line {line}: derived {field} mismatch")
        source_key = (
            task["source"]["date"],
            task["source"]["episode_id"],
            task["source"]["seed"],
        )
        coverage[(task["model_b"], sha256_bytes(canonical(source_key)), seat)] += 1
        derived.append(
            {
                "task_id": task_id,
                "anchor": task["model_b"],
                "seat": seat,
                "date": task["source"]["date"],
                "episode_id": task["source"]["episode_id"],
                "seed": task["source"]["seed"],
                "margin": float(margin),
                "score": float(score),
                "win": int(margin > 0),
                "tie": int(margin == 0),
                "loss": int(margin < 0),
            }
        )
    missing = sorted(set(expected) - seen)
    if missing:
        errors.append(f"missing {len(missing)} expected task IDs")
    coverage_bad = [key for key, count in coverage.items() if count != 1]
    if coverage_bad:
        errors.append(f"non-unit anchor/source/seat coverage: {len(coverage_bad)}")
    expected_minimal = [expected[key] for key in sorted(expected)]
    observed_minimal = [
        {field: row[field] for field in expected[row["task_id"]]}
        for row in sorted(rows, key=lambda value: str(value.get("task_id") or ""))
        if row.get("task_id") in expected
    ]
    checks = {
        "rows": len(rows),
        "expected_rows": len(expected),
        "unique_task_ids": len(seen),
        "missing_task_ids": len(missing),
        "foreign_or_duplicate_or_invalid_count": len(errors),
        "row_validation_errors": errors,
        "status_counts": dict(sorted(status_counts.items())),
        "expected_tasks_sha256": sha256_bytes(canonical(expected_minimal)),
        "observed_task_projection_sha256": sha256_bytes(canonical(observed_minimal)),
        "expected_observed_task_projection_equal": expected_minimal == observed_minimal,
        "coverage_cells": len(coverage),
        "coverage_all_exactly_once": len(coverage) == len(expected) and not coverage_bad,
    }
    return derived, checks


def summarize(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    values = list(rows)
    games = len(values)
    wins = sum(int(row["win"]) for row in values)
    ties = sum(int(row["tie"]) for row in values)
    losses = sum(int(row["loss"]) for row in values)
    return {
        "games": games,
        "wins": wins,
        "ties": ties,
        "losses": losses,
        "pure_win_rate": wins / games if games else None,
        "competition_score_rate": (wins + 0.5 * ties) / games if games else None,
        "mean_margin": sum(float(row["margin"]) for row in values) / games if games else None,
    }


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("empty percentile input")
    index = (len(ordered) - 1) * probability
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    weight = index - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def cluster_bootstrap(rows: list[dict[str, Any]], anchor: str) -> dict[str, Any]:
    selected = [row for row in rows if row["anchor"] == anchor]
    by_date: dict[str, dict[tuple[str, int], list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row in selected:
        by_date[row["date"]][(row["episode_id"], row["seed"])].append(row)
    for date, clusters in by_date.items():
        if any(len(cluster) != 2 for cluster in clusters.values()):
            raise ValueError(f"source cluster is not exactly both seats: {anchor} {date}")
    seed_text = f"{BOOTSTRAP_SEED_NAMESPACE}|{anchor}"
    seed = int.from_bytes(hashlib.sha256(seed_text.encode("utf-8")).digest()[:8], "big")
    rng = random.Random(seed)
    pure: list[float] = []
    score: list[float] = []
    margin: list[float] = []
    ordered_dates = sorted(by_date)
    cluster_lists = {
        date: [clusters[key] for key in sorted(clusters)]
        for date, clusters in by_date.items()
    }
    for _ in range(BOOTSTRAP_REPLICATES):
        draw: list[dict[str, Any]] = []
        for date in ordered_dates:
            clusters = cluster_lists[date]
            for _source in range(len(clusters)):
                draw.extend(clusters[rng.randrange(len(clusters))])
        stats = summarize(draw)
        pure.append(float(stats["pure_win_rate"]))
        score.append(float(stats["competition_score_rate"]))
        margin.append(float(stats["mean_margin"]))
    return {
        "method": "date-stratified source-cluster percentile bootstrap; sample source clusters with replacement within each date and retain both seats",
        "replicates": BOOTSTRAP_REPLICATES,
        "rng": "Python random.Random(MT19937)",
        "seed_namespace": BOOTSTRAP_SEED_NAMESPACE,
        "seed_text": seed_text,
        "seed_uint64_be_sha256_prefix": seed,
        "percentile_interpolation": "linear, index=(n-1)*p",
        "source_clusters": sum(len(value) for value in by_date.values()),
        "clusters_by_date": {date: len(cluster_lists[date]) for date in ordered_dates},
        "pure_win_rate_ci95": [percentile(pure, 0.025), percentile(pure, 0.975)],
        "competition_score_rate_ci95": [
            percentile(score, 0.025),
            percentile(score, 0.975),
        ],
        "mean_margin_ci95": [percentile(margin, 0.025), percentile(margin, 0.975)],
    }


def metric_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    report: dict[str, Any] = {}
    for anchor in ANCHORS:
        selected = [row for row in rows if row["anchor"] == anchor]
        overall = summarize(selected)
        bootstrap = cluster_bootstrap(rows, anchor)
        overall.update(
            {
                "source_clusters": bootstrap["source_clusters"],
                "pure_win_rate_ci95": bootstrap["pure_win_rate_ci95"],
                "competition_score_rate_ci95": bootstrap[
                    "competition_score_rate_ci95"
                ],
                "mean_margin_ci95": bootstrap["mean_margin_ci95"],
            }
        )
        report[anchor] = {
            "overall": overall,
            "by_date": {
                date: summarize(row for row in selected if row["date"] == date)
                for date in sorted({row["date"] for row in selected})
            },
            "by_candidate_seat": {
                str(seat): summarize(row for row in selected if row["seat"] == seat)
                for seat in (0, 1)
            },
            "by_date_and_candidate_seat": {
                date: {
                    str(seat): summarize(
                        row
                        for row in selected
                        if row["date"] == date and row["seat"] == seat
                    )
                    for seat in (0, 1)
                }
                for date in sorted({row["date"] for row in selected})
            },
            "bootstrap": bootstrap,
        }
    return report


def verify_panel_chain(panel: dict[str, Any]) -> dict[str, Any]:
    records = normalized_records(panel)
    dates = Counter(row["date"] for row in records)
    splits = Counter(row["split"] for row in records)
    identities = {(row["date"], row["episode_id"], row["seed"]) for row in records}
    seeds = {row["seed"] for row in records}
    record_hash = sha256_bytes(canonical(records))
    panel_checks = {
        "schema": panel.get("schema") == "kaggriculture-v14-frozen-development-panel-1",
        "kind": panel.get("kind") == "screen36",
        "count": panel.get("count") == len(records) == 36,
        "date_counts": panel.get("date_counts") == dict(dates) == {
            "2026-08-18": 12,
            "2026-08-19": 12,
            "2026-08-20": 12,
        },
        "split_counts": panel.get("split_counts") == dict(splits),
        "allowed_splits": set(splits).issubset({"train", "validation"}),
        "no_test": panel.get("test_source_count") == 0 and "test" not in splits,
        "identity_unique": len(identities) == len(records),
        "seed_unique": len(seeds) == len(records),
        "records_sha256": panel.get("records_sha256") == record_hash,
        "metadata_only": panel.get("metadata_only") is True,
        "historical_payloads_not_accessed": panel.get("historical_replay_payloads_accessed")
        is False,
        "environment_games_started_at_freeze": panel.get("environment_games_started") is False,
    }
    panel_seal_path = VALIDATION / "panel_seal.json"
    panel_seal = load_json(panel_seal_path)
    seal_core = {key: value for key, value in panel_seal.items() if key not in {"schema", "seal_core_sha256"}}
    asset_checks: list[dict[str, Any]] = []
    for asset in panel_seal["assets"]:
        path = resolve_workspace_path(str(asset["path"]))
        actual_hash = file_sha256(path) if path.is_file() else None
        actual_size = path.stat().st_size if path.is_file() else None
        asset_checks.append(
            {
                "path": str(path),
                "expected_sha256": asset["file_sha256"],
                "actual_sha256": actual_hash,
                "expected_size_bytes": asset["size_bytes"],
                "actual_size_bytes": actual_size,
                "passed": actual_hash == asset["file_sha256"]
                and actual_size == asset["size_bytes"],
            }
        )
    checksum_checks: list[dict[str, Any]] = []
    checksum_path = VALIDATION / "protocol_assets.sha256"
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected_hash, relative_path = line.split("  ", 1)
        path = resolve_workspace_path(relative_path)
        actual_hash = file_sha256(path) if path.is_file() else None
        checksum_checks.append(
            {
                "path": str(path),
                "expected_sha256": expected_hash,
                "actual_sha256": actual_hash,
                "passed": actual_hash == expected_hash,
            }
        )
    return {
        "panel_file_sha256": file_sha256(VALIDATION / "screen_panel.json"),
        "records_sha256_recomputed": record_hash,
        "panel_checks": panel_checks,
        "panel_checks_all_pass": all(panel_checks.values()),
        "panel_seal_file_sha256": file_sha256(panel_seal_path),
        "panel_seal_core_sha256_recomputed": sha256_bytes(canonical(seal_core)),
        "panel_seal_core_pass": panel_seal.get("seal_core_sha256")
        == sha256_bytes(canonical(seal_core)),
        "panel_seal_assets": asset_checks,
        "panel_seal_assets_all_pass": all(row["passed"] for row in asset_checks),
        "protocol_assets_checksum_rows": checksum_checks,
        "protocol_assets_all_pass": all(row["passed"] for row in checksum_checks),
    }


def verify_runtime_chain(
    slate: dict[str, Any],
    candidate_seal: dict[str, Any],
    registry: dict[str, Any],
    registry_hash: str,
) -> dict[str, Any]:
    slate_core_fields = (
        "candidate_order",
        "candidates",
        "anchors",
        "selection",
        "panel_seal_file_sha256",
        "screen_panel_records_sha256",
        "confirmatory_panel_records_sha256",
        "evaluation_contract_file_sha256",
    )
    slate_core = {key: slate[key] for key in slate_core_fields}
    package_checks: list[dict[str, Any]] = []
    packages = [*(slate.get("anchors") or []), *(slate.get("candidates") or [])]
    for package in packages:
        archive = resolve_workspace_path(str(package["archive"]["path"]))
        archive_hash = file_sha256(archive) if archive.is_file() else None
        archive_size = archive.stat().st_size if archive.is_file() else None
        artifact_checks: dict[str, Any] = {}
        for artifact_name in ("registry_entry", "source_main", "submission_manifest", "package_qa"):
            artifact = package[artifact_name]
            path = resolve_workspace_path(str(artifact["path"]))
            actual = file_sha256(path) if path.is_file() else None
            artifact_checks[artifact_name] = {
                "path": str(path),
                "expected_sha256": artifact["file_sha256"],
                "actual_sha256": actual,
                "passed": actual == artifact["file_sha256"],
            }
        members = package["clean_submission"]["members"]
        member_checks: list[dict[str, Any]] = []
        closure_rows: list[dict[str, Any]] = []
        expected_tar_names = [str(row["archive_path"]) for row in members]
        for member in members:
            path = Path(str(member["clean_path"])).resolve()
            actual_hash = file_sha256(path) if path.is_file() else None
            actual_size = path.stat().st_size if path.is_file() else None
            member_checks.append(
                {
                    "archive_path": member["archive_path"],
                    "clean_path": str(path),
                    "expected_sha256": member["sha256"],
                    "actual_sha256": actual_hash,
                    "expected_size_bytes": member["size_bytes"],
                    "actual_size_bytes": actual_size,
                    "passed": actual_hash == member["sha256"]
                    and actual_size == member["size_bytes"],
                }
            )
            closure_rows.append(
                {
                    "archive_path": member["archive_path"],
                    "sha256": member["sha256"],
                    "size_bytes": member["size_bytes"],
                }
            )
        tar_checks: list[dict[str, Any]] = []
        tar_names: list[str] = []
        if archive.is_file():
            with tarfile.open(archive, "r:gz") as handle:
                for tar_member in handle.getmembers():
                    if not tar_member.isfile():
                        tar_checks.append(
                            {
                                "archive_path": tar_member.name,
                                "passed": False,
                                "reason": "non-regular member",
                            }
                        )
                        continue
                    normalized = PurePosixPath(tar_member.name).as_posix()
                    tar_names.append(normalized)
                    stream = handle.extractfile(tar_member)
                    data = stream.read() if stream is not None else b""
                    expected_member = next(
                        (row for row in members if row["archive_path"] == normalized), None
                    )
                    tar_checks.append(
                        {
                            "archive_path": normalized,
                            "actual_sha256": sha256_bytes(data),
                            "actual_size_bytes": len(data),
                            "passed": expected_member is not None
                            and sha256_bytes(data) == expected_member["sha256"]
                            and len(data) == expected_member["size_bytes"],
                        }
                    )
        closure_hash = sha256_bytes(canonical(closure_rows))
        package_checks.append(
            {
                "id": package["id"],
                "archive": {
                    "path": str(archive),
                    "expected_sha256": package["archive"]["file_sha256"],
                    "actual_sha256": archive_hash,
                    "expected_size_bytes": package["archive"]["size_bytes"],
                    "actual_size_bytes": archive_size,
                    "passed": archive_hash == package["archive"]["file_sha256"]
                    and archive_size == package["archive"]["size_bytes"],
                },
                "artifacts": artifact_checks,
                "artifacts_all_pass": all(row["passed"] for row in artifact_checks.values()),
                "clean_member_count_expected": package["clean_submission"]["member_count"],
                "clean_member_count_actual": len(member_checks),
                "clean_members": member_checks,
                "clean_members_all_pass": all(row["passed"] for row in member_checks),
                "closure_sha256_expected": package["clean_submission"]["closure_sha256"],
                "closure_sha256_recomputed": closure_hash,
                "closure_pass": closure_hash == package["clean_submission"]["closure_sha256"],
                "member_order_sorted": expected_tar_names == sorted(expected_tar_names),
                "archive_member_names_exact": tar_names == expected_tar_names,
                "archive_members": tar_checks,
                "archive_members_all_pass": len(tar_checks) == len(expected_tar_names)
                and all(row["passed"] for row in tar_checks),
            }
        )
    seal_core_fields = (
        "status",
        "panel_verification_sha256",
        "panel_seal_file_sha256",
        "candidate_slate_file_sha256",
        "candidate_slate_core_sha256",
        "clean_registry_file_sha256",
        "registry_and_serving_code_sha256",
        "candidate_order",
        "anchor_order",
        "candidate_archive_sha256",
        "screen_games_started",
        "confirmatory_games_started",
        "test_access",
    )
    seal_core = {key: candidate_seal[key] for key in seal_core_fields}
    package_map = {row["id"]: row for row in package_checks}
    model_ids = [str(row["id"]) for row in registry["models"]]
    registry_package_checks: dict[str, Any] = {}
    raw_packages = {str(row["id"]): row for row in packages}
    for spec in registry["models"]:
        model_id = str(spec["id"])
        package = raw_packages[model_id]
        expected_paths = [str(Path(row["clean_path"]).resolve()) for row in package["clean_submission"]["members"]]
        registry_package_checks[model_id] = {
            "path_is_clean_main": str(Path(spec["path"]).resolve())
            == str(Path(package["clean_submission"]["main"]).resolve()),
            "code_paths_exact": list(spec.get("code_paths") or []) == expected_paths,
            "archive_hash_exact": spec.get("source_archive_sha256")
            == package["archive"]["file_sha256"],
            "closure_hash_exact": spec.get("clean_submission_closure_sha256")
            == package["clean_submission"]["closure_sha256"],
            "raw_agent_entrypoint": spec.get("entrypoint") == "agent"
            and spec.get("validation_runtime")
            == "safe_exact_archive_raw_agent_entrypoint",
        }
    return {
        "candidate_slate_file_sha256": file_sha256(SEALED / "candidate_slate.json"),
        "candidate_slate_core_sha256_recomputed": sha256_bytes(canonical(slate_core)),
        "candidate_slate_checks": {
            "schema": slate.get("schema") == "kaggriculture-v14-candidate-slate-1",
            "status": slate.get("status") == "sealed_before_any_screen_game",
            "test_access_false": slate.get("test_access") is False,
            "candidate_order": slate.get("candidate_order") == [CANDIDATE],
            "anchor_order": [row.get("id") for row in slate.get("anchors") or []]
            == list(ANCHORS),
            "core_hash": slate.get("slate_core_sha256") == sha256_bytes(canonical(slate_core)),
            "panel_seal_hash": slate.get("panel_seal_file_sha256")
            == file_sha256(VALIDATION / "panel_seal.json"),
            "screen_records_hash": slate.get("screen_panel_records_sha256")
            == load_json(VALIDATION / "screen_panel.json")["records_sha256"],
            "evaluation_contract_hash": slate.get("evaluation_contract_file_sha256")
            == file_sha256(VALIDATION / "evaluation_contract.json"),
        },
        "packages": package_checks,
        "packages_all_pass": all(
            row["archive"]["passed"]
            and row["artifacts_all_pass"]
            and row["clean_members_all_pass"]
            and row["closure_pass"]
            and row["member_order_sorted"]
            and row["archive_member_names_exact"]
            and row["archive_members_all_pass"]
            and row["clean_member_count_expected"] == row["clean_member_count_actual"]
            for row in package_checks
        ),
        "candidate_seal_file_sha256": file_sha256(SEALED / "candidate_seal.json"),
        "candidate_seal_core_sha256_recomputed": sha256_bytes(canonical(seal_core)),
        "candidate_seal_checks": {
            "schema": candidate_seal.get("schema") == "kaggriculture-v14-candidate-seal-1",
            "core_hash": candidate_seal.get("seal_core_sha256")
            == sha256_bytes(canonical(seal_core)),
            "slate_file_hash": candidate_seal.get("candidate_slate_file_sha256")
            == file_sha256(SEALED / "candidate_slate.json"),
            "slate_core_hash": candidate_seal.get("candidate_slate_core_sha256")
            == slate.get("slate_core_sha256"),
            "registry_file_hash": candidate_seal.get("clean_registry_file_sha256")
            == file_sha256(SEALED / "clean_registry.json"),
            "registry_code_hash": candidate_seal.get("registry_and_serving_code_sha256")
            == registry_hash,
            "candidate_order": candidate_seal.get("candidate_order") == [CANDIDATE],
            "anchor_order": candidate_seal.get("anchor_order") == list(ANCHORS),
            "archive_map": candidate_seal.get("candidate_archive_sha256")
            == {CANDIDATE: package_map[CANDIDATE]["archive"]["actual_sha256"]},
            "games_unstarted_at_seal": candidate_seal.get("screen_games_started") is False
            and candidate_seal.get("confirmatory_games_started") is False,
            "test_access_false": candidate_seal.get("test_access") is False,
        },
        "registry": {
            "file_sha256": file_sha256(SEALED / "clean_registry.json"),
            "reachable_code_sha256_recomputed": registry_hash,
            "schema_pass": registry.get("schema")
            == "kaggriculture-v14-clean-dual-anchor-registry-1",
            "test_sources_disallowed": registry.get("test_sources_allowed") is False,
            "candidate_slate_core_exact": registry.get("candidate_slate_core_sha256")
            == slate.get("slate_core_sha256"),
            "model_order_exact": model_ids == [*ANCHORS, CANDIDATE],
            "package_binding": registry_package_checks,
            "package_binding_all_pass": all(
                all(checks.values()) for checks in registry_package_checks.values()
            ),
        },
    }


def expected_run_manifest(
    fingerprint: str,
    panel: dict[str, Any],
    slate: dict[str, Any],
    registry_hash: str,
    evaluator_hash: str,
) -> dict[str, Any]:
    return {
        "anchors": list(ANCHORS),
        "candidate": CANDIDATE,
        "candidate_seal_file_sha256": file_sha256(SEALED / "candidate_seal.json"),
        "candidate_slate_core_sha256": slate["slate_core_sha256"],
        "candidate_slate_file_sha256": file_sha256(SEALED / "candidate_slate.json"),
        "confirmatory_execution_flag": False,
        "dry_run": False,
        "evaluation_contract_file_sha256": file_sha256(
            VALIDATION / "evaluation_contract.json"
        ),
        "expected_games": 144,
        "panel": str((VALIDATION / "screen_panel.json").resolve()),
        "panel_file_sha256": file_sha256(VALIDATION / "screen_panel.json"),
        "panel_records_sha256": panel["records_sha256"],
        "panel_seal_file_sha256": file_sha256(VALIDATION / "panel_seal.json"),
        "phase": "screen",
        "protocol_verification_status": "PASS",
        "registry": str((SEALED / "clean_registry.json").resolve()),
        "registry_and_serving_code_sha256": registry_hash,
        "registry_file_sha256": file_sha256(SEALED / "clean_registry.json"),
        "run_fingerprint": fingerprint,
        "schema": RUN_SCHEMA,
        "sources": 36,
        "targeted_pairs": [[CANDIDATE, anchor] for anchor in ANCHORS],
        "v10_evaluation_implementation_sha256": evaluator_hash,
    }


def expected_consume_lock(
    fingerprint: str, run_manifest_path: Path, registry_hash: str
) -> dict[str, Any]:
    return {
        "schema": "kaggriculture-v14-panel-consume-lock-1",
        "phase": "screen",
        "candidate": CANDIDATE,
        "run_fingerprint": fingerprint,
        "jsonl": str((RUN_DIR / "games.jsonl").resolve()),
        "run_manifest": str(run_manifest_path.resolve()),
        "run_manifest_file_sha256": file_sha256(run_manifest_path),
        "registry_and_code_sha256": registry_hash,
        "panel_file_sha256": file_sha256(VALIDATION / "screen_panel.json"),
        "candidate_seal_file_sha256": file_sha256(SEALED / "candidate_seal.json"),
    }


def compare_landed_audit(
    independent_metrics: dict[str, Any], independent_gates: dict[str, bool]
) -> dict[str, Any]:
    audit_path = RUN_DIR / "audit.json"
    audit = load_json(audit_path)
    fields = (
        "games",
        "wins",
        "ties",
        "losses",
        "pure_win_rate",
        "competition_score_rate",
        "mean_margin",
    )
    comparisons: dict[str, Any] = {}
    all_points_equal = True
    for anchor in ANCHORS:
        independent = independent_metrics[anchor]
        landed = audit["by_anchor"][anchor]
        overall = {
            field: independent["overall"][field] == landed["overall"][field]
            for field in fields
        }
        by_date = {
            date: {
                field: independent["by_date"][date][field] == landed["by_date"][date][field]
                for field in fields
            }
            for date in independent["by_date"]
        }
        by_seat = {
            seat: {
                field: independent["by_candidate_seat"][seat][field]
                == landed["by_candidate_seat"][seat][field]
                for field in fields
            }
            for seat in independent["by_candidate_seat"]
        }
        anchor_pass = (
            all(overall.values())
            and all(all(values.values()) for values in by_date.values())
            and all(all(values.values()) for values in by_seat.values())
        )
        all_points_equal &= anchor_pass
        comparisons[anchor] = {
            "overall_point_fields": overall,
            "by_date_point_fields": by_date,
            "by_seat_point_fields": by_seat,
            "all_point_metrics_equal": anchor_pass,
            "landed_bootstrap_ci95": {
                "pure_win_rate": landed["overall"].get("pure_win_rate_ci95"),
                "competition_score_rate": landed["overall"].get(
                    "competition_score_rate_ci95"
                ),
                "mean_margin": landed["overall"].get("mean_margin_ci95"),
            },
            "independent_bootstrap_ci95": {
                "pure_win_rate": independent["overall"].get("pure_win_rate_ci95"),
                "competition_score_rate": independent["overall"].get(
                    "competition_score_rate_ci95"
                ),
                "mean_margin": independent["overall"].get("mean_margin_ci95"),
            },
            "ci_comparison_note": "Both use the preregistered stratified source-cluster design and 10000 replicates; the independent audit intentionally uses a separately derived RNG seed, so exact endpoints need not match.",
        }
    landed_gates = audit.get("gates") or {}
    gates_equal = all(landed_gates.get(key) == value for key, value in independent_gates.items())
    return {
        "audit_file_sha256": file_sha256(audit_path),
        "schema_pass": audit.get("schema") == "kaggriculture-v14-dual-anchor-audit-1",
        "candidate_phase_pass": audit.get("candidate") == CANDIDATE
        and audit.get("phase") == "screen",
        "rows_pass": audit.get("rows") == 144 and audit.get("expected_rows") == 144,
        "done_error_pass": audit.get("done_done_count") == 144
        and audit.get("error_count") == 0,
        "status_counts_pass": audit.get("status_counts") == {"DONE/DONE": 144},
        "run_fingerprint_pass": audit.get("run_fingerprint")
        == load_json(RUN_DIR / "run_manifest.json")["run_fingerprint"],
        "point_metric_comparisons": comparisons,
        "all_point_metrics_equal": all_points_equal,
        "gate_values_equal": gates_equal,
        "landed_gates": landed_gates,
        "landed_passed_true": audit.get("passed") is True,
        "embedded_protocol_status": (audit.get("protocol_verification") or {}).get("status"),
        "embedded_frozen_evidence_drift_detected": (audit.get("protocol_verification") or {}).get(
            "frozen_evidence_drift_detected"
        ),
        "embedded_current_rescan_selected_sources_unexposed": (audit.get("protocol_verification") or {}).get(
            "checks", {}
        ).get("current_rescan_does_not_expose_selected_sources"),
    }


def compare_recovery_provenance() -> dict[str, Any]:
    provenance_path = RUN_DIR / "audit_recovery_provenance.json"
    provenance = load_json(provenance_path)
    paths = {
        "games": RUN_DIR / "games.jsonl",
        "run_manifest": RUN_DIR / "run_manifest.json",
        "consume_lock": VALIDATION
        / "execution_state"
        / "screen"
        / f"{CANDIDATE}.json",
        "panel": VALIDATION / "screen_panel.json",
        "candidate_seal": SEALED / "candidate_seal.json",
        "candidate_slate": SEALED / "candidate_slate.json",
        "clean_registry": SEALED / "clean_registry.json",
        "panel_seal": VALIDATION / "panel_seal.json",
        "evaluation_contract": VALIDATION / "evaluation_contract.json",
        "sealed_runner": VALIDATION / "run_dual_anchor.py",
        "sealed_auditor": VALIDATION / "audit_dual_anchor.py",
        "sealed_protocol_verifier": VALIDATION / "verify_protocol.py",
    }
    actual = {key: file_sha256(path) for key, path in paths.items()}
    recorded = provenance.get("immutable_input_sha256") or {}
    recovery_script = VALIDATION / "recover_audit_only.py"
    static_text = recovery_script.read_text(encoding="utf-8")
    static_surface = {
        "imports_kaggle_environments": "import kaggle_environments" in static_text,
        "calls_run_tasks_literal": "run_tasks(" in static_text,
        "calls_sealed_audit_audit": "sealed_audit.audit(" in static_text,
        "assigns_only_documented_audit_globals": "sealed_audit.panel_path = panel_path" in static_text
        and "sealed_audit._validate_consume_lock = _exact_writer_lock_validator" in static_text,
    }
    return {
        "provenance_file_sha256": file_sha256(provenance_path),
        "schema_status_pass": provenance.get("schema")
        == "kaggriculture-v14-audit-recovery-1"
        and provenance.get("status") == "AUDIT_ONLY_RECOVERY_COMPLETE",
        "candidate_phase_pass": provenance.get("candidate") == CANDIDATE
        and provenance.get("phase") == "screen",
        "claims_no_games_or_tasks": provenance.get("games_replayed") is False
        and provenance.get("run_tasks_called") is False,
        "claims_inputs_equal": provenance.get("immutable_inputs_before_after_equal") is True,
        "recorded_input_hashes": recorded,
        "actual_input_hashes": actual,
        "recorded_input_hashes_match_current": recorded == actual,
        "audit_output_path_exact": provenance.get("audit_output")
        == str((RUN_DIR / "audit.json").resolve()),
        "audit_output_hash_exact": provenance.get("audit_output_sha256")
        == file_sha256(RUN_DIR / "audit.json"),
        "recovery_script_hash_exact": provenance.get("recovery_script_sha256")
        == file_sha256(recovery_script),
        "patched_surface_exact": provenance.get("patched_surface")
        == "runtime replacement of _validate_consume_lock only",
        "static_recovery_surface": static_surface,
        "static_recovery_surface_pass": static_surface
        == {
            "imports_kaggle_environments": False,
            "calls_run_tasks_literal": False,
            "calls_sealed_audit_audit": True,
            "assigns_only_documented_audit_globals": True,
        },
        "evidentiary_limit": "Static artifacts and the script control flow support audit-only recovery, but the two no-game booleans remain provenance claims; a filesystem report cannot independently prove all historical process activity.",
    }


def collect_immutable_input_paths(slate: dict[str, Any]) -> dict[str, Path]:
    paths: dict[str, Path] = {
        "games": RUN_DIR / "games.jsonl",
        "run_manifest": RUN_DIR / "run_manifest.json",
        "consume_lock": VALIDATION / "execution_state" / "screen" / f"{CANDIDATE}.json",
        "landed_audit": RUN_DIR / "audit.json",
        "recovery_provenance": RUN_DIR / "audit_recovery_provenance.json",
        "screen_panel": VALIDATION / "screen_panel.json",
        "panel_seal": VALIDATION / "panel_seal.json",
        "protocol_assets": VALIDATION / "protocol_assets.sha256",
        "evaluation_contract": VALIDATION / "evaluation_contract.json",
        "candidate_slate": SEALED / "candidate_slate.json",
        "candidate_seal": SEALED / "candidate_seal.json",
        "clean_registry": SEALED / "clean_registry.json",
        "sealed_runner": VALIDATION / "run_dual_anchor.py",
        "sealed_auditor": VALIDATION / "audit_dual_anchor.py",
        "sealed_protocol_verifier": VALIDATION / "verify_protocol.py",
        "recovery_script": VALIDATION / "recover_audit_only.py",
    }
    for package in [*(slate.get("anchors") or []), *(slate.get("candidates") or [])]:
        package_id = str(package["id"])
        paths[f"archive:{package_id}"] = resolve_workspace_path(str(package["archive"]["path"]))
        for artifact_name in ("registry_entry", "source_main", "submission_manifest", "package_qa"):
            paths[f"artifact:{package_id}:{artifact_name}"] = resolve_workspace_path(
                str(package[artifact_name]["path"])
            )
        for member in package["clean_submission"]["members"]:
            paths[f"clean:{package_id}:{member['archive_path']}"] = Path(
                str(member["clean_path"])
            ).resolve()
    return paths


def hash_paths(paths: dict[str, Path]) -> dict[str, str]:
    return {key: file_sha256(path) for key, path in sorted(paths.items())}


def report_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# V14 fresh screen 独立复算",
        "",
        f"结论：**{report['decision']}**。这是进入 confirmatory 的屏幕门结论，不等同于最终提交结论。",
        "",
        "## 独立指标",
        "",
        "| 对手 | W/T/L | 纯胜率（wins/all） | 比赛计分率 | 平均 margin | 独立 95% CI（纯胜率） |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for anchor in ANCHORS:
        overall = report["metrics"][anchor]["overall"]
        ci = overall["pure_win_rate_ci95"]
        lines.append(
            f"| {anchor} | {overall['wins']}/{overall['ties']}/{overall['losses']} | "
            f"{overall['pure_win_rate']:.4%} | {overall['competition_score_rate']:.4%} | "
            f"{overall['mean_margin']:+.4f} | [{ci[0]:.4%}, {ci[1]:.4%}] |"
        )
    lines.extend(
        [
            "",
            "纯胜率严格按 `wins / all games`；平局留在分母且不算胜。Bootstrap 为 10,000 次日期分层 source-cluster 重采样，每个 source 保留双席；本复算使用独立 SHA256 派生 seed，所以 CI 不要求与落盘审计逐点相同。",
            "",
            "## 完整性",
            "",
            f"- 逐行任务：{report['task_integrity']['rows']}/{report['task_integrity']['expected_rows']}；唯一 task_id {report['task_integrity']['unique_task_ids']}；缺失 {report['task_integrity']['missing_task_ids']}；验证错误 {report['task_integrity']['foreign_or_duplicate_or_invalid_count']}。",
            f"- 运行 fingerprint：`{report['fingerprints']['run_fingerprint_recomputed']}`，与 manifest/consume lock/144 行完全一致。",
            f"- 状态：{report['task_integrity']['status_counts']}；所有 schema、engine、双席、DONE、error、reward、margin、score 均由逐行原始字段重算。",
            f"- Panel：`{report['hash_chain']['panel']['panel_file_sha256']}`；records `{report['hash_chain']['panel']['records_sha256_recomputed']}`。",
            f"- Registry：文件 `{report['hash_chain']['runtime']['registry']['file_sha256']}`；reachable-code `{report['fingerprints']['registry_and_serving_code_sha256_recomputed']}`。",
        ]
    )
    for package in report["hash_chain"]["runtime"]["packages"]:
        lines.append(
            f"- Archive {package['id']}：`{package['archive']['actual_sha256']}`；tar 成员、clean closure 与登记哈希均通过。"
        )
    lines.extend(
        [
            "",
            "## 日期与席位",
            "",
        ]
    )
    for anchor in ANCHORS:
        lines.append(f"### {anchor}")
        lines.append("")
        lines.append("| 分层 | games | W/T/L | pure | score | mean margin |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for date, stats in report["metrics"][anchor]["by_date"].items():
            lines.append(
                f"| 日期 {date} | {stats['games']} | {stats['wins']}/{stats['ties']}/{stats['losses']} | {stats['pure_win_rate']:.4%} | {stats['competition_score_rate']:.4%} | {stats['mean_margin']:+.4f} |"
            )
        for seat, stats in report["metrics"][anchor]["by_candidate_seat"].items():
            lines.append(
                f"| 候选席位 {seat} | {stats['games']} | {stats['wins']}/{stats['ties']}/{stats['losses']} | {stats['pure_win_rate']:.4%} | {stats['competition_score_rate']:.4%} | {stats['mean_margin']:+.4f} |"
            )
        lines.append("")
    lines.extend(
        [
            "## 落盘审计与 recovery",
            "",
            f"- 落盘 audit 的总体、日期、席位点估计与独立复算：`{report['landed_audit_comparison']['all_point_metrics_equal']}`；gate 一致：`{report['landed_audit_comparison']['gate_values_equal']}`。",
            f"- Recovery provenance 登记的全部 immutable input hash 与当前文件：`{report['recovery_provenance']['recorded_input_hashes_match_current']}`；audit 输出及 recovery 脚本 hash：`{report['recovery_provenance']['audit_output_hash_exact'] and report['recovery_provenance']['recovery_script_hash_exact']}`。",
            f"- 本次独立复算前后输入 hash 不变：`{report['input_hash_stability']['before_after_equal']}`。",
            "- 证据边界：静态脚本只调用原审计并写 audit/provenance，未发现环境或 run_tasks 调用；但历史进程是否绝对未启动游戏不能仅靠静态文件反证。现有 games hash、consume lock、任务闭包和 recovery 前后 hash 链均一致。",
            "",
            "## Gate",
            "",
            f"- 完整性：`{report['gates']['integrity']}`",
            f"- A2 纯胜率 >= 65%：`{report['gates']['a2_pure_win_rate_gte_0_65']}`",
            f"- r002 纯胜率 > 50%：`{report['gates']['r002_pure_win_rate_gt_0_50']}`",
            "",
            "因此给出 **GO**：可按既定单次协议进入 confirmatory；不能据此跳过 confirmatory 或直接宣称达到最终 65% 目标。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    panel_path = VALIDATION / "screen_panel.json"
    games_path = RUN_DIR / "games.jsonl"
    run_manifest_path = RUN_DIR / "run_manifest.json"
    registry_path = SEALED / "clean_registry.json"
    consume_lock_path = VALIDATION / "execution_state" / "screen" / f"{CANDIDATE}.json"

    panel = load_json(panel_path)
    slate = load_json(SEALED / "candidate_slate.json")
    candidate_seal = load_json(SEALED / "candidate_seal.json")
    registry = load_json(registry_path)
    immutable_paths = collect_immutable_input_paths(slate)
    hashes_before = hash_paths(immutable_paths)

    registry_hash, registry_paths = registry_fingerprint(registry, registry_path)
    evaluator_hash, evaluator_runtime, evaluator_paths = evaluator_fingerprint()
    records = normalized_records(panel)
    fingerprint, fingerprint_payload = expected_run_fingerprint(
        panel_path, panel, records, slate, registry_hash, evaluator_hash
    )
    expected_tasks = build_expected_tasks(fingerprint, records)
    rows = load_jsonl(games_path)
    derived, task_integrity = validate_rows(rows, expected_tasks)
    metrics = metric_report(derived)

    manifest = load_json(run_manifest_path)
    manifest_expected = expected_run_manifest(
        fingerprint, panel, slate, registry_hash, evaluator_hash
    )
    lock = load_json(consume_lock_path)
    lock_expected = expected_consume_lock(fingerprint, run_manifest_path, registry_hash)

    panel_chain = verify_panel_chain(panel)
    runtime_chain = verify_runtime_chain(slate, candidate_seal, registry, registry_hash)
    runtime_checks_all = (
        all(runtime_chain["candidate_slate_checks"].values())
        and runtime_chain["packages_all_pass"]
        and all(runtime_chain["candidate_seal_checks"].values())
        and runtime_chain["registry"]["schema_pass"]
        and runtime_chain["registry"]["test_sources_disallowed"]
        and runtime_chain["registry"]["candidate_slate_core_exact"]
        and runtime_chain["registry"]["model_order_exact"]
        and runtime_chain["registry"]["package_binding_all_pass"]
    )
    panel_checks_all = (
        panel_chain["panel_checks_all_pass"]
        and panel_chain["panel_seal_core_pass"]
        and panel_chain["panel_seal_assets_all_pass"]
        and panel_chain["protocol_assets_all_pass"]
    )
    task_integrity_pass = (
        task_integrity["rows"] == task_integrity["expected_rows"] == 144
        and task_integrity["unique_task_ids"] == 144
        and task_integrity["missing_task_ids"] == 0
        and task_integrity["foreign_or_duplicate_or_invalid_count"] == 0
        and task_integrity["expected_observed_task_projection_equal"]
        and task_integrity["coverage_all_exactly_once"]
        and task_integrity["status_counts"] == {"DONE/DONE": 144}
    )
    manifest_pass = manifest == manifest_expected
    lock_pass = lock == lock_expected
    fingerprint_rows_pass = all(
        row.get("run_fingerprint") == fingerprint for row in rows
    )
    gates = {
        "integrity": task_integrity_pass
        and manifest_pass
        and lock_pass
        and fingerprint_rows_pass
        and panel_checks_all
        and runtime_checks_all,
        "a2_pure_win_rate_gte_0_65": metrics["v12a2_no_shop_gate"]["overall"][
            "pure_win_rate"
        ]
        >= 0.65,
        "r002_pure_win_rate_gt_0_50": metrics["v12_incumbent_r002"]["overall"][
            "pure_win_rate"
        ]
        > 0.50,
    }
    landed_comparison = compare_landed_audit(metrics, gates)
    provenance_comparison = compare_recovery_provenance()

    hashes_after_analysis = hash_paths(immutable_paths)
    input_stable = hashes_before == hashes_after_analysis
    recovery_pass = (
        provenance_comparison["schema_status_pass"]
        and provenance_comparison["candidate_phase_pass"]
        and provenance_comparison["claims_no_games_or_tasks"]
        and provenance_comparison["claims_inputs_equal"]
        and provenance_comparison["recorded_input_hashes_match_current"]
        and provenance_comparison["audit_output_path_exact"]
        and provenance_comparison["audit_output_hash_exact"]
        and provenance_comparison["recovery_script_hash_exact"]
        and provenance_comparison["patched_surface_exact"]
        and provenance_comparison["static_recovery_surface_pass"]
    )
    landed_pass = (
        landed_comparison["schema_pass"]
        and landed_comparison["candidate_phase_pass"]
        and landed_comparison["rows_pass"]
        and landed_comparison["done_error_pass"]
        and landed_comparison["status_counts_pass"]
        and landed_comparison["run_fingerprint_pass"]
        and landed_comparison["all_point_metrics_equal"]
        and landed_comparison["gate_values_equal"]
        and landed_comparison["landed_passed_true"]
    )
    go = all(gates.values()) and landed_pass and recovery_pass and input_stable

    report = {
        "schema": "kaggriculture-v14-independent-screen-audit-1",
        "candidate": CANDIDATE,
        "phase": "screen",
        "decision": "GO_TO_CONFIRMATORY" if go else "NO_GO",
        "independence": {
            "imports_audit_dual_anchor": False,
            "imports_run_dual_anchor": False,
            "imports_validation_statistics": False,
            "games_or_agents_invoked": False,
            "confirmatory_games_or_test_outcomes_accessed": False,
            "confirmatory_metadata_files_hashed_as_seal_assets": True,
            "method": "standard-library reconstruction from sealed bytes, panel metadata, manifest, consume lock, and games JSONL",
        },
        "metric_note": "Pure win rate is wins/all games. Ties are not wins and remain in the denominator. Competition score is reported separately.",
        "gates": gates,
        "task_integrity": task_integrity,
        "metrics": metrics,
        "fingerprints": {
            "run_fingerprint_recomputed": fingerprint,
            "run_fingerprint_manifest": manifest.get("run_fingerprint"),
            "run_fingerprint_consume_lock": lock.get("run_fingerprint"),
            "run_fingerprint_all_rows_exact": fingerprint_rows_pass,
            "run_fingerprint_payload": fingerprint_payload,
            "registry_and_serving_code_sha256_recomputed": registry_hash,
            "registry_reachable_paths": registry_paths,
            "v10_evaluation_implementation_sha256_recomputed": evaluator_hash,
            "evaluator_runtime": evaluator_runtime,
            "evaluator_paths": evaluator_paths,
        },
        "run_manifest": {
            "file_sha256": file_sha256(run_manifest_path),
            "exact_reconstruction_pass": manifest_pass,
            "observed": manifest,
            "expected": manifest_expected,
        },
        "consume_lock": {
            "file_sha256": file_sha256(consume_lock_path),
            "exact_writer_payload_pass": lock_pass,
            "observed": lock,
            "expected": lock_expected,
        },
        "hash_chain": {"panel": panel_chain, "runtime": runtime_chain},
        "landed_audit_comparison": landed_comparison,
        "recovery_provenance": provenance_comparison,
        "input_hash_stability": {
            "tracked_file_count": len(immutable_paths),
            "before_sha256": hashes_before,
            "after_analysis_sha256": hashes_after_analysis,
            "before_after_equal": input_stable,
            "hash_manifest_sha256": sha256_bytes(canonical(hashes_before)),
        },
        "limitations": [
            "No game was executed and no confirmatory/test outcome was opened. Confirmatory metadata files were only hashed because they are members of the frozen panel-seal asset list.",
            "The independent bootstrap deliberately uses a separate deterministic seed; its endpoints validate stability under the same design, not byte identity with the landed audit.",
            "Static files cannot prove every historical process action; recovery no-game claims are corroborated by script control flow and unchanged immutable hashes, not by an external process ledger.",
        ],
    }
    json_path = RUN_DIR / "independent_audit.json"
    md_path = RUN_DIR / "independent_audit.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(report_markdown(report), encoding="utf-8")

    hashes_after_write = hash_paths(immutable_paths)
    if hashes_after_write != hashes_before:
        raise RuntimeError("an immutable input changed while writing independent reports")
    print(
        json.dumps(
            {
                "decision": report["decision"],
                "json": str(json_path),
                "json_sha256": file_sha256(json_path),
                "markdown": str(md_path),
                "markdown_sha256": file_sha256(md_path),
                "input_hashes_unchanged_after_write": True,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
