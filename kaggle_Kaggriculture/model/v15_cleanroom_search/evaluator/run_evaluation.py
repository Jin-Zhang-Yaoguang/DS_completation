"""Execute one V15 black-box development or single-use hidden evaluation.

Without ``--execute`` this command refuses to start games.  ``--dry-run`` is a
non-consuming task-closure preview and is the only mode used during protocol
construction.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping

from .inventory import (
    LINEAGE_SEAL,
    REGISTRY,
    SEALED_MODELS,
    archive_closure,
    extract_closure,
)
from .protocol import (
    HERE,
    PROJECT_ROOT,
    THRESHOLDS,
    atomic_create_json,
    atomic_create_json_strict,
    canonical,
    file_sha256,
    unique_json_loads,
    validate_attempt_id,
)
from .scorecard import audit_and_score, read_jsonl, validate_task_subset
from .source_control import STATE_ROOT, capacity_audit, reserve_panel, select_panel

for value in (str(PROJECT_ROOT), str(HERE)):
    if value not in sys.path:
        sys.path.insert(0, value)

from kaggle_Kaggriculture.model.v10_replay_lolo_router import pairwise_evaluate as v10  # noqa: E402
from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import (  # noqa: E402
    load_registry,
    registry_fingerprint,
)


SCHEMA = "kaggriculture-v15-blackbox-run-1"
CANDIDATE_ID = "candidate_policy"
PARENT_ID = "parent_policy"


def evaluator_implementation_fingerprint() -> str:
    """Bind the V15 decision layers plus the underlying closed-loop runner."""

    digest = hashlib.sha256()
    digest.update(v10.implementation_fingerprint().encode("ascii"))
    for path in (
        Path(__file__).resolve(),
        HERE / "scorecard.py",
        HERE / "source_control.py",
        HERE / "protocol.py",
        HERE / "inventory.py",
        HERE / "qa_candidate.py",
        HERE.parent / "firewall" / "firewall.py",
        HERE.parent / "firewall" / "generator_policy.json",
    ):
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _load(path: Path) -> dict[str, Any]:
    value = unique_json_loads(path.read_text(encoding="utf-8"), source=str(path))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def validate_firewall_seal(path: Path, attempt_id: str, archive: Path) -> dict[str, Any]:
    seal = _load(path)
    required = {
        "schema",
        "attempt_id",
        "passed",
        "candidate_sha256",
        "candidate_archive_sha256",
        "candidate_serving_sha256",
        "policy_sha256",
    }
    if not required <= set(seal):
        raise ValueError(f"candidate firewall seal lacks fields: {sorted(required - set(seal))}")
    if seal["schema"] != "kaggriculture-v15-cleanroom-candidate-seal-1":
        raise ValueError("unexpected candidate firewall seal schema")
    from kaggle_Kaggriculture.model.v15_cleanroom_search.firewall import firewall as cleanroom_firewall

    output_root = Path(str(seal.get("output_root") or "")).resolve()
    verified = cleanroom_firewall.verify_candidate_seal(output_root, path)
    if verified != seal:
        raise ValueError("firewall candidate verification changed the sealed payload")
    if seal["attempt_id"] != attempt_id or seal["passed"] is not True:
        raise PermissionError("candidate did not pass the exact clean-room firewall")
    if seal["candidate_archive_sha256"] != file_sha256(archive):
        raise ValueError("candidate archive differs from the firewall seal")
    closure = archive_closure(archive)
    main = next(row for row in closure["members"] if row["path"] == "main.py")
    if seal["candidate_serving_sha256"] != main["sha256"]:
        raise ValueError("candidate main.py differs from the firewall seal")
    if seal["policy_sha256"] != file_sha256(cleanroom_firewall.POLICY_PATH):
        raise ValueError("candidate was sealed under a different firewall policy")
    for key in ("candidate_sha256", "candidate_archive_sha256", "candidate_serving_sha256", "policy_sha256"):
        value = str(seal[key])
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            raise ValueError(f"malformed firewall digest: {key}")
    return {**seal, "archive_closure": closure}


def validate_candidate_qa(
    path: Path,
    *,
    archive_sha256: str,
    serving_sha256: str,
) -> dict[str, Any]:
    qa = _load(path)
    expected_keys = {
        "schema",
        "passed",
        "archive_sha256",
        "serving_sha256",
        "serving_fingerprint",
        "seeds_sha256",
        "games",
        "all_done",
        "all_calls_719",
        "all_states_720",
        "stderr_bytes",
        "stdout_bytes",
        "test_sources_accessed",
    }
    if set(qa) != expected_keys:
        raise ValueError("candidate QA fields differ from the private contract")
    if (
        qa["schema"] != "kaggriculture-v15-private-package-qa-1"
        or qa["passed"] is not True
        or qa["archive_sha256"] != archive_sha256
        or qa["serving_sha256"] != serving_sha256
        or qa["games"] != 6
        or qa["all_done"] is not True
        or qa["all_calls_719"] is not True
        or qa["all_states_720"] is not True
        or qa["stderr_bytes"] != 0
        or qa["test_sources_accessed"] is not False
    ):
        raise ValueError("candidate did not pass the exact private raw-loader QA")
    return qa


def _lineage_context(stage: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    seal = _load(LINEAGE_SEAL)
    if seal.get("schema") != "kaggriculture-v15-lineage-seal-1":
        raise ValueError("lineage seal is absent or invalid")
    claimed_sha = seal.get("seal_sha256")
    unsigned = {key: value for key, value in seal.items() if key != "seal_sha256"}
    if claimed_sha != hashlib.sha256(canonical(unsigned)).hexdigest():
        raise ValueError("lineage seal digest mismatch")
    rows = list(seal["models"])
    ids = [str(row.get("opaque_pool_id") or "") for row in rows]
    if len(rows) != 11 or len(set(ids)) != 11 or any(not value for value in ids):
        raise ValueError("lineage seal must contain 11 unique opaque models")
    if any(row.get("hidden_included") is not True for row in rows):
        raise ValueError("hidden must include every exact-serving-unique model")
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        lineage = str(row.get("behaviour_lineage") or "")
        groups.setdefault(lineage, []).append(row)
    if "" in groups or len(groups) != 7:
        raise ValueError("lineage seal must contain exactly 7 non-empty lineages")
    for lineage, members in groups.items():
        representatives = [row for row in members if row.get("development_representative") is True]
        if len(representatives) != 1:
            raise ValueError(f"lineage lacks exactly one development representative: {lineage}")
    summary = {str(row.get("behaviour_lineage") or ""): row for row in seal.get("lineages", [])}
    if set(summary) != set(groups):
        raise ValueError("lineage summary differs from model membership")
    for lineage, members in groups.items():
        expected_members = [str(row["opaque_pool_id"]) for row in members]
        representative = next(
            str(row["opaque_pool_id"])
            for row in members
            if row.get("development_representative") is True
        )
        row = summary[lineage]
        if (
            row.get("hidden_member_pool_ids") != expected_members
            or row.get("hidden_member_count") != len(expected_members)
            or row.get("development_representative_pool_id") != representative
        ):
            raise ValueError(f"lineage summary closure failed: {lineage}")
    registry_ids = {
        str(row.get("id") or "")
        for row in _load(REGISTRY).get("models", [])
    }
    if registry_ids != set(ids):
        raise ValueError("opaque registry differs from the lineage seal")
    parent = str(seal.get("parent_mapping", {}).get("opaque_pool_id") or "")
    anchors = seal.get("direct_anchor_mapping", {})
    if (
        parent not in registry_ids
        or anchors.get("primary") != parent
        or anchors.get("secondary") not in registry_ids
    ):
        raise ValueError("parent/direct-anchor mapping is not closed over the pool")
    selected = [
        row
        for row in rows
        if row.get("hidden_included") is True
        and (stage == "hidden" or row.get("development_representative") is True)
    ]
    expected_models = 11 if stage == "hidden" else 7
    expected_lineages = 7
    if (
        seal.get(f"{stage}_models") != expected_models
        or seal.get(f"{stage}_lineages") != expected_lineages
        or len(selected) != expected_models
        or len({row["behaviour_lineage"] for row in selected}) != expected_lineages
    ):
        raise ValueError(f"unexpected {stage} lineage closure")
    return seal, selected


def _candidate_runtime(archive: Path, closure: dict[str, Any]) -> Path:
    runtime = SEALED_MODELS / ("candidate_" + closure["serving_fingerprint"][:20])
    extract_closure(archive, closure, runtime)
    return runtime


def build_run_registry(
    attempt_dir: Path,
    candidate_archive: Path,
    candidate_closure: dict[str, Any],
    parent_pool_id: str,
) -> Path:
    payload = _load(REGISTRY)
    models = [dict(row) for row in payload["models"]]
    by_id = {str(row["id"]): row for row in models}
    if parent_pool_id not in by_id:
        raise ValueError("sealed parent is absent from the pool registry")
    candidate_runtime = _candidate_runtime(candidate_archive, candidate_closure)
    candidate = {
        "id": CANDIDATE_ID,
        "kind": "python",
        "path": str((candidate_runtime / "main.py").resolve()),
        "entrypoint": "agent",
        "family": "opaque_candidate",
        "lineage": "opaque_candidate",
        "code_paths": [str((candidate_runtime / row["path"]).resolve()) for row in candidate_closure["members"]],
        "tags": ["clean-room", "firewall-sealed"],
    }
    parent = {**by_id[parent_pool_id], "id": PARENT_ID, "family": "opaque_parent", "lineage": "opaque_parent"}
    run_registry = {
        "schema": "kaggriculture-v15-private-run-registry-1",
        "models": [*models, candidate, parent],
        "base_pool_registry_sha256": file_sha256(REGISTRY),
    }
    path = attempt_dir / "run_registry.private.json"
    atomic_create_json(path, run_registry)
    return path


def run_fingerprint(
    *,
    stage: str,
    attempt_id: str,
    candidate_closure: Mapping[str, Any],
    candidate_qa_file_sha256: str,
    firewall_seal: Mapping[str, Any],
    lineage_seal: Mapping[str, Any],
    selected_lineages: list[dict[str, Any]],
    panel: Mapping[str, Any],
    registry_path: Path,
) -> str:
    registry = load_registry(registry_path)
    payload = {
        "schema": SCHEMA,
        "stage": stage,
        "attempt_id": attempt_id,
        "candidate_archive_sha256": candidate_closure["archive_sha256"],
        "candidate_serving_fingerprint": candidate_closure["serving_fingerprint"],
        "candidate_qa_file_sha256": candidate_qa_file_sha256,
        "candidate_firewall_seal_sha256": hashlib.sha256(canonical(dict(firewall_seal))).hexdigest(),
        "parent_mapping": lineage_seal["parent_mapping"],
        "direct_anchor_mapping": lineage_seal["direct_anchor_mapping"],
        "selected_opaque_pool_ids": [row["opaque_pool_id"] for row in selected_lineages],
        "lineage_seal_sha256": lineage_seal["seal_sha256"],
        "panel_records_sha256": panel["records_sha256"],
        "panel_sources": panel["source_count"],
        "seats": [0, 1],
        "policies": [CANDIDATE_ID, PARENT_ID],
        "thresholds": THRESHOLDS,
        "registry_and_code_sha256": registry_fingerprint(registry),
        "evaluation_implementation_sha256": evaluator_implementation_fingerprint(),
    }
    return hashlib.sha256(canonical(payload)).hexdigest()


def build_tasks(
    *,
    fingerprint: str,
    registry_path: Path,
    pool_ids: list[str],
    panel: Mapping[str, Any],
) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for policy in (CANDIDATE_ID, PARENT_ID):
        for opponent in pool_ids:
            pair_id = f"{policy}__vs__{opponent}"
            for source in panel["records"]:
                for seat in (0, 1):
                    raw = (
                        f"{fingerprint}:{policy}:{opponent}:{source['date']}:"
                        f"{source['episode_id']}:{source['seed']}:policy-seat-{seat}"
                    )
                    tasks.append(
                        {
                            "task_id": hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24],
                            "run_fingerprint": fingerprint,
                            "pair_id": pair_id,
                            "model_a": policy,
                            "model_b": opponent,
                            "model_a_seat": seat,
                            "source": dict(source),
                            "registry": str(registry_path.resolve()),
                        }
                    )
    if len({task["task_id"] for task in tasks}) != len(tasks):
        raise ValueError("task ids are not unique")
    return tasks


def index_expected_tasks(tasks: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for task in tasks:
        task_id = task.get("task_id")
        if not isinstance(task_id, str) or not task_id or task_id in indexed:
            raise ValueError("generated tasks contain a missing or duplicate task id")
        indexed[task_id] = task
    return indexed


def validate_resume_file(
    path: Path,
    *,
    expected_tasks: Mapping[str, Mapping[str, Any]],
    pool_ids: set[str],
    panel_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError("--resume requires an existing raw-game JSONL")
    rows = read_jsonl(path)
    validate_task_subset(
        rows,
        expected_tasks=expected_tasks,
        policy_ids={CANDIDATE_ID, PARENT_ID},
        pool_ids=pool_ids,
        panel_records=panel_records,
    )
    return rows


def _attempt_state_dir(attempt_id: str, state_root: Path) -> Path:
    return state_root / "attempts" / attempt_id


def _bind_candidate_stage(
    *,
    attempt_id: str,
    stage: str,
    seal: Mapping[str, Any],
    candidate_closure: Mapping[str, Any],
    state_root: Path,
) -> Path:
    attempt = _attempt_state_dir(attempt_id, state_root)
    development = attempt / "development_candidate.json"
    target = attempt / f"{stage}_candidate.json"
    payload = {
        "schema": "kaggriculture-v15-attempt-candidate-binding-1",
        "attempt_id": attempt_id,
        "stage": stage,
        "candidate_archive_sha256": candidate_closure["archive_sha256"],
        "candidate_serving_fingerprint": candidate_closure["serving_fingerprint"],
        "candidate_main_sha256": seal["candidate_serving_sha256"],
        "candidate_qa_file_sha256": seal.get("candidate_qa_file_sha256"),
        "firewall_policy_sha256": seal["policy_sha256"],
    }
    if stage == "hidden":
        if target.exists():
            raise PermissionError("hidden evaluation was already consumed for this attempt")
        if not development.is_file():
            raise PermissionError("hidden cannot be read before a development candidate is sealed")
        dev = _load(development)
        for key in (
            "candidate_archive_sha256",
            "candidate_serving_fingerprint",
            "candidate_main_sha256",
            "candidate_qa_file_sha256",
            "firewall_policy_sha256",
        ):
            if dev.get(key) != payload.get(key):
                raise PermissionError("candidate was tuned or repackaged after development; hidden access denied")
        result = attempt / "development_result.private.json"
        if not result.is_file() or _load(result).get("feedback", {}).get("overall_passed") is not True:
            raise PermissionError("hidden is available only to an unchanged development-pass candidate")
        # This candidate-level O_EXCL marker closes the cross-attempt race: the
        # first hidden entrance consumes the serving bytes even if the process
        # dies before panel selection or before the first game.
        marker = (
            state_root
            / "hidden_serving"
            / f"{payload['candidate_serving_fingerprint']}.json"
        )
        try:
            atomic_create_json_strict(
                marker,
                {
                    "schema": "kaggriculture-v15-hidden-serving-consumption-1",
                    "attempt_id": attempt_id,
                    "candidate_serving_fingerprint": payload["candidate_serving_fingerprint"],
                    "status": "consumed_on_hidden_entry",
                },
            )
        except FileExistsError as exc:
            raise PermissionError("candidate has already consumed a hidden panel") from exc
    if stage == "hidden":
        atomic_create_json_strict(target, payload)
    else:
        atomic_create_json(target, payload)
    return target


def dry_run_payload(attempt_id: str = "attempt_001") -> dict[str, Any]:
    validate_attempt_id(attempt_id)
    capacity = capacity_audit()
    lineage_seal, development = _lineage_context("development")
    _, hidden = _lineage_context("hidden")
    dev_panel = select_panel(attempt_id, "development")
    hidden_panel = select_panel(
        attempt_id,
        "hidden",
        extra_excluded=[int(row["seed"]) for row in dev_panel["records"]],
    )
    if set(row["seed"] for row in dev_panel["records"]) & set(row["seed"] for row in hidden_panel["records"]):
        raise ValueError("dry-run preview reused a development source in hidden")
    payload = {
        "schema": "kaggriculture-v15-evaluator-dry-run-1",
        "attempt_id": attempt_id,
        "games_started": False,
        "panels_reserved": False,
        "test_sources_selected": 0,
        "parent_public_alias": lineage_seal["parent_mapping"]["public_alias"],
        "parent_mapping_private_catalog_key": lineage_seal["parent_mapping"]["catalog_key"],
        "development": {
            "source_clusters": 100,
            "models": len(development),
            "lineages_equal_weighted": len({row["behaviour_lineage"] for row in development}),
            "direct_anchor_games_each": 200,
            "candidate_games": 100 * len(development) * 2,
            "parent_games": 100 * len(development) * 2,
            "total_tasks": 100 * len(development) * 2 * 2,
            "panel_records_sha256": dev_panel["records_sha256"],
        },
        "hidden": {
            "single_use": True,
            "source_clusters": 100,
            "models": len(hidden),
            "lineages_equal_weighted": len({row["behaviour_lineage"] for row in hidden}),
            "direct_anchor_games_each": 200,
            "candidate_games": 100 * len(hidden) * 2,
            "parent_games": 100 * len(hidden) * 2,
            "total_tasks": 100 * len(hidden) * 2 * 2,
            "panel_records_sha256": hidden_panel["records_sha256"],
        },
        "statistics": {
            "pool_formula": "mean_source(mean_lineage(mean_model(mean_two_candidate_seats(score))))",
            "paired_uplift_formula": "same-source mean_lineage(mean_model(candidate score - P0 score))",
            "bootstrap": "100 source clusters, stratified by source date, 10000 resamples, q=0.025",
        },
        "thresholds": THRESHOLDS,
        "fresh_source_capacity": capacity["fresh_allowed_records"],
        "maximum_full_attempts": capacity["maximum_remaining_full_attempts"],
    }
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt-id", default="attempt_001")
    parser.add_argument("--stage", choices=("development", "hidden"), default="development")
    parser.add_argument("--candidate-archive", type=Path)
    parser.add_argument("--firewall-seal", type=Path)
    parser.add_argument("--candidate-qa", type=Path)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--feedback-output", type=Path)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        if args.execute:
            raise ValueError("--dry-run and --execute are mutually exclusive")
        payload = dry_run_payload(args.attempt_id)
        output = HERE / "dry_run_report.json"
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return
    if not args.execute:
        raise PermissionError("games are locked; pass --execute deliberately")
    validate_attempt_id(args.attempt_id)
    if (
        args.candidate_archive is None
        or args.firewall_seal is None
        or args.candidate_qa is None
        or args.output_root is None
    ):
        raise ValueError("formal execution requires candidate archive, firewall seal, private QA, and output root")
    archive = args.candidate_archive.resolve()
    if args.stage == "hidden" and args.resume:
        raise PermissionError("hidden reservation is single-use; interrupted hidden runs are not retryable")
    firewall = validate_firewall_seal(args.firewall_seal.resolve(), args.attempt_id, archive)
    closure = firewall.pop("archive_closure")
    qa_path = args.candidate_qa.resolve()
    validate_candidate_qa(
        qa_path,
        archive_sha256=closure["archive_sha256"],
        serving_sha256=firewall["candidate_serving_sha256"],
    )
    firewall["candidate_qa_file_sha256"] = file_sha256(qa_path)
    lineage_seal, selected = _lineage_context(args.stage)
    candidate_binding = _bind_candidate_stage(
        attempt_id=args.attempt_id,
        stage=args.stage,
        seal=firewall,
        candidate_closure=closure,
        state_root=STATE_ROOT,
    )
    panel = reserve_panel(args.attempt_id, args.stage)
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    registry_path = build_run_registry(
        output_root,
        archive,
        closure,
        str(lineage_seal["parent_mapping"]["opaque_pool_id"]),
    )
    fingerprint = run_fingerprint(
        stage=args.stage,
        attempt_id=args.attempt_id,
        candidate_closure=closure,
        candidate_qa_file_sha256=firewall["candidate_qa_file_sha256"],
        firewall_seal=firewall,
        lineage_seal=lineage_seal,
        selected_lineages=selected,
        panel=panel,
        registry_path=registry_path,
    )
    pool_ids = [str(row["opaque_pool_id"]) for row in selected]
    tasks = build_tasks(fingerprint=fingerprint, registry_path=registry_path, pool_ids=pool_ids, panel=panel)
    expected_by_id = index_expected_tasks(tasks)
    expected = 2800 if args.stage == "development" else 4400
    if len(tasks) != expected:
        raise ValueError(f"unexpected task closure: {len(tasks)} != {expected}")
    run_manifest = {
        "schema": SCHEMA,
        "attempt_id": args.attempt_id,
        "stage": args.stage,
        "run_fingerprint": fingerprint,
        "candidate_binding": str(candidate_binding.resolve()),
        "candidate_binding_sha256": file_sha256(candidate_binding),
        "candidate_archive_sha256": closure["archive_sha256"],
        "firewall_seal_sha256": file_sha256(args.firewall_seal.resolve()),
        "candidate_qa_file_sha256": firewall["candidate_qa_file_sha256"],
        "lineage_seal_sha256": lineage_seal["seal_sha256"],
        "panel_records_sha256": panel["records_sha256"],
        "registry_and_code_sha256": registry_fingerprint(load_registry(registry_path)),
        "evaluation_implementation_sha256": evaluator_implementation_fingerprint(),
        "expected_tasks": expected,
        "execute_flag": True,
    }
    manifest_path = output_root / "run_manifest.private.json"
    atomic_create_json(manifest_path, run_manifest)
    hidden_lock_dir: Path | None = None
    if args.stage == "hidden":
        from kaggle_Kaggriculture.model.v15_cleanroom_search.firewall import firewall as cleanroom_firewall

        hidden_lock_dir = output_root / "hidden_lock.private"
        cleanroom_firewall.reserve_hidden(
            hidden_lock_dir,
            STATE_ROOT / "panels" / f"{args.attempt_id}_hidden.json",
            args.firewall_seal.resolve(),
            Path(__file__).resolve(),
        )
    games = output_root / "games.private.jsonl"
    if games.exists() and not args.resume:
        raise FileExistsError("raw games already exist; exact --resume is required")
    if args.resume:
        validate_resume_file(
            games,
            expected_tasks=expected_by_id,
            pool_ids=set(pool_ids),
            panel_records=panel["records"],
        )
    v10.run_tasks(tasks, games, args.workers, args.resume)
    # Never trust the V10 convenience return value: reparse with duplicate-key
    # rejection and bind every final row to this exact sealed task matrix.
    rows = read_jsonl(games)
    mapping = {str(row["opaque_pool_id"]): str(row["behaviour_lineage"]) for row in selected}
    feedback, private = audit_and_score(
        rows,
        attempt_id=args.attempt_id,
        candidate_id=CANDIDATE_ID,
        parent_id=PARENT_ID,
        panel_records=panel["records"],
        pool_to_lineage=mapping,
        expected_tasks=expected_by_id,
        primary_anchor_id=str(lineage_seal["direct_anchor_mapping"]["primary"]),
        secondary_anchor_id=str(lineage_seal["direct_anchor_mapping"]["secondary"]),
        integrity_passed=True,
        bootstrap_label=fingerprint,
    )
    private.update(
        {
            "run_fingerprint": fingerprint,
            "raw_games_sha256": file_sha256(games),
            "lineage_seal_sha256": lineage_seal["seal_sha256"],
            "candidate_firewall_seal_sha256": file_sha256(args.firewall_seal.resolve()),
        }
    )
    private_path = output_root / "score_audit.private.json"
    atomic_create_json(private_path, private)
    reducer_private = {
        "schema": "kaggriculture-v15-private-evaluation-1",
        "attempt_id": args.attempt_id,
        "candidate_sha256": firewall["candidate_sha256"],
        "integrity_passed": feedback["integrity_passed"],
        "anchors": {
            "primary": {"games": 200, "pure_win_rate": feedback["primary_anchor_pure_win_rate"]},
            "secondary": {"games": 200, "pure_win_rate": feedback["secondary_anchor_pure_win_rate"]},
        },
        "pool": {
            "lineage_equal_score_rate": feedback["lineage_equal_pool_score_rate"],
            "source_cluster_ci95_low": feedback["lineage_equal_pool_score_ci95_low"],
        },
        "parent": {
            "paired_uplift_rate": feedback["paired_uplift_rate"],
            "paired_uplift_ci95_low": feedback["paired_uplift_ci95_low"],
        },
    }
    reducer_private_path = output_root / "feedback_reducer_input.private.json"
    atomic_create_json(reducer_private_path, reducer_private)
    result_state = _attempt_state_dir(args.attempt_id, STATE_ROOT) / f"{args.stage}_result.private.json"
    atomic_create_json(result_state, private)
    if args.stage == "hidden":
        feedback_path = output_root / "score_only_internal.private.json"
        if args.feedback_output is not None:
            raise PermissionError("hidden feedback is evaluator-private and cannot be exported")
        atomic_create_json(feedback_path, feedback)
        assert hidden_lock_dir is not None
        from kaggle_Kaggriculture.model.v15_cleanroom_search.firewall import firewall as cleanroom_firewall

        cleanroom_firewall.complete_hidden(hidden_lock_dir, reducer_private_path)
    else:
        if args.feedback_output is None:
            raise ValueError("development requires an explicit generator feedback output")
        feedback_path = args.feedback_output.resolve()
        from kaggle_Kaggriculture.model.v15_cleanroom_search.firewall import firewall as cleanroom_firewall

        reduced = cleanroom_firewall.reduce_feedback(reducer_private_path, feedback_path)
        if reduced != feedback:
            raise ValueError("firewall feedback reducer disagrees with evaluator scorecard")
    print(json.dumps({"passed": feedback["overall_passed"], "private_audit": str(private_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
