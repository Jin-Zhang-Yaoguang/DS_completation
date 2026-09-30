"""Execute one frozen V13 candidate against r002 and A2 on a sealed panel."""

from __future__ import annotations

from dataclasses import asdict
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
from typing import Any


HERE = Path(__file__).resolve().parent
MODEL_ROOT = HERE.parents[1]
PROJECT_ROOT = MODEL_ROOT.parents[1]
V10 = MODEL_ROOT / "v10_replay_lolo_router"
for value in (str(PROJECT_ROOT), str(V10), str(HERE)):
    if value not in sys.path:
        sys.path.insert(0, value)

from kaggle_Kaggriculture.model.v10_replay_lolo_router import pairwise_evaluate as v10  # noqa: E402
from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import (  # noqa: E402
    load_registry,
    registry_fingerprint,
)
from freeze_protocol import canonical, file_sha256, verify  # noqa: E402


SCHEMA = "kaggriculture-v13-dual-anchor-run-1"


def load_panel(phase: str) -> tuple[Path, dict[str, Any], list[v10.SeedRecord]]:
    path = HERE / ("screen_panel.json" if phase == "screen" else "confirmatory_panel.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = [
        v10.SeedRecord(
            date=str(row["date"]),
            seed=int(row["seed"]),
            episode_id=str(row["episode_id"]),
            split=str(row["split"]),
            source_path=str(row.get("source_path") or ""),
            lineage_fold=str(row.get("lineage_fold") or ""),
        )
        for row in payload["records"]
    ]
    if payload.get("test_source_count") != 0:
        raise ValueError("sealed panel contains test sources")
    return path, payload, records


def run_fingerprint(
    phase: str,
    candidate: str,
    anchors: list[str],
    registry: Any,
    panel_path: Path,
    panel: dict[str, Any],
    records: list[v10.SeedRecord],
) -> str:
    payload = {
        "schema": SCHEMA,
        "phase": phase,
        "candidate": candidate,
        "targeted_pairs": [[candidate, anchor] for anchor in anchors],
        "seat_assignments_per_source": 2,
        "panel_file_sha256": file_sha256(panel_path),
        "panel_records_sha256": panel["records_sha256"],
        "panel_records": [asdict(row) for row in records],
        "evaluation_contract_file_sha256": file_sha256(HERE / "evaluation_contract.json"),
        "candidate_slate_file_sha256": file_sha256(HERE / "candidate_slate.json"),
        "candidate_slate_core_sha256": json.loads(
            (HERE / "candidate_slate.json").read_text(encoding="utf-8")
        )["slate_core_sha256"],
        "protocol_seal_file_sha256": file_sha256(HERE / "protocol_seal.json"),
        "registry_and_serving_code_sha256": registry_fingerprint(registry),
        "v10_evaluation_implementation_sha256": v10.implementation_fingerprint(),
        "v10_row_schema": v10.SCHEMA,
    }
    return hashlib.sha256(canonical(payload)).hexdigest()


def task_id(
    fingerprint: str, candidate: str, anchor: str, source: v10.SeedRecord, seat: int
) -> str:
    value = (
        f"{fingerprint}:{candidate}:{anchor}:{source.date}:{source.episode_id}:"
        f"{source.seed}:candidate-seat-{seat}"
    )
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def build_tasks(
    registry: Any,
    candidate: str,
    anchors: list[str],
    records: list[v10.SeedRecord],
    fingerprint: str,
) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for anchor in anchors:
        pair_id = f"{candidate}__vs__{anchor}"
        for source in records:
            for candidate_seat in (0, 1):
                tasks.append(
                    {
                        "task_id": task_id(
                            fingerprint, candidate, anchor, source, candidate_seat
                        ),
                        "run_fingerprint": fingerprint,
                        "pair_id": pair_id,
                        "model_a": candidate,
                        "model_b": anchor,
                        "model_a_seat": candidate_seat,
                        "source": asdict(source),
                        "registry": str(registry.path),
                    }
                )
    return tasks


def finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def validate_row_against_task(row: dict[str, Any], task: dict[str, Any]) -> None:
    line = row.get("_physical_line", "?")
    exact_fields = (
        "task_id",
        "run_fingerprint",
        "pair_id",
        "model_a",
        "model_b",
        "model_a_seat",
        "source",
    )
    for field in exact_fields:
        if row.get(field) != task.get(field):
            raise ValueError(f"row/task {field} mismatch at line {line}")
    if not isinstance(row.get("model_a_seat"), int) or isinstance(
        row.get("model_a_seat"), bool
    ):
        raise ValueError(f"model_a_seat must be an integer at line {line}")
    if row.get("schema") != v10.SCHEMA:
        raise ValueError(f"unexpected row schema at line {line}")
    if row.get("engine") != "kaggle_environments.make(kaggriculture)":
        raise ValueError(f"unexpected engine at line {line}")
    if row.get("closed_loop") is not True or row.get("trace_agent") is not False:
        raise ValueError(f"row is not a closed-loop non-trace game at line {line}")
    if row.get("done") is not True or row.get("statuses") != ["DONE", "DONE"]:
        raise ValueError(f"row is not DONE/DONE at line {line}")
    if row.get("error") is not None:
        raise ValueError(f"row has error at line {line}: {row.get('error')}")
    seat = int(task["model_a_seat"])
    expected_seat_models = (
        [task["model_a"], task["model_b"]]
        if seat == 0
        else [task["model_b"], task["model_a"]]
    )
    if row.get("seat_models") != expected_seat_models:
        raise ValueError(f"seat_models mismatch at line {line}")
    rewards = row.get("rewards")
    if (
        not isinstance(rewards, list)
        or len(rewards) != 2
        or not all(finite_number(value) for value in rewards)
    ):
        raise ValueError(f"invalid rewards at line {line}")
    reward_a = rewards[seat]
    reward_b = rewards[1 - seat]
    margin_a = reward_a - reward_b
    score_a = 1.0 if margin_a > 0 else 0.5 if margin_a == 0 else 0.0
    for field, expected in (
        ("reward_a", reward_a),
        ("reward_b", reward_b),
        ("margin_a", margin_a),
        ("score_a", score_a),
    ):
        value = row.get(field)
        if not finite_number(value) or value != expected:
            raise ValueError(f"derived {field} mismatch at line {line}: {value!r} != {expected!r}")


def load_slate() -> dict[str, Any]:
    slate = json.loads((HERE / "candidate_slate.json").read_text(encoding="utf-8"))
    if slate.get("status") != "sealed_before_any_screen_game":
        raise ValueError("candidate slate is not valid")
    return slate


def clean_registry_or_fail(path: Path, registry: Any, seal: dict[str, Any]) -> None:
    expected = (HERE / "clean_screen_registry.json").resolve()
    if path.resolve() != expected:
        raise ValueError(f"only sealed clean-package registry is allowed: {expected}")
    current_code = registry_fingerprint(registry)
    bound = seal["candidate_slate"]
    if (
        file_sha256(path) != bound["clean_registry_file_sha256"]
        or current_code != bound["clean_registry_and_code_sha256"]
    ):
        raise ValueError("clean registry or reachable serving code changed")


def consume_lock(
    phase: str,
    candidate: str,
    fingerprint: str,
    jsonl: Path,
    run_manifest: Path,
    registry: Any,
    resume: bool,
    state_root: Path | None = None,
) -> Path:
    state = state_root.resolve() if state_root is not None else HERE / "execution_state"
    lock_path = (
        state / "screen" / f"{candidate}.json"
        if phase == "screen"
        else state / "confirmatory_consumed.json"
    )
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "kaggriculture-v13-panel-consume-lock-1",
        "phase": phase,
        "candidate": candidate,
        "run_fingerprint": fingerprint,
        "jsonl": str(jsonl.resolve()),
        "run_manifest": str(run_manifest.resolve()),
        "run_manifest_file_sha256": file_sha256(run_manifest),
        "registry_and_code_sha256": registry_fingerprint(registry),
        "panel_file_sha256": file_sha256(
            HERE / ("screen_panel.json" if phase == "screen" else "confirmatory_panel.json")
        ),
        "candidate_slate_file_sha256": file_sha256(HERE / "candidate_slate.json"),
    }
    encoded = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    try:
        descriptor = os.open(lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        existing = json.loads(lock_path.read_text(encoding="utf-8"))
        if resume is not True or existing != payload:
            raise FileExistsError(
                f"panel already consumed; only exact fingerprint/path --resume is allowed: {lock_path}"
            )
        return lock_path
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    return lock_path


def validate_resume(
    path: Path, fingerprint: str, expected_tasks: dict[str, dict[str, Any]]
) -> None:
    if not path.is_file():
        return
    seen: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            task = str(row.get("task_id") or "")
            if row.get("run_fingerprint") != fingerprint or task not in expected_tasks or task in seen:
                raise ValueError(
                    f"resume input is not a clean subset of this exact run at line {line_number}"
                )
            row["_physical_line"] = line_number
            validate_row_against_task(row, expected_tasks[task])
            seen.add(task)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("screen", "confirmatory"), required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--jsonl", type=Path, required=True)
    parser.add_argument("--audit-output", type=Path, required=True)
    parser.add_argument("--run-manifest", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute-confirmatory", action="store_true")
    parser.add_argument("--finalist-seal", type=Path, default=HERE / "finalist_seal.json")
    parser.add_argument("--r002", default="v12_incumbent_r002")
    parser.add_argument("--a2", default="v12a2_no_shop_gate")
    args = parser.parse_args()

    if args.phase == "confirmatory" and args.execute_confirmatory is not True:
        raise PermissionError(
            "confirmatory panel is single-use; pass --execute-confirmatory only after the finalist is sealed"
        )
    protocol_verification = verify()
    seal = json.loads((HERE / "protocol_seal.json").read_text(encoding="utf-8"))
    slate = load_slate()
    panel_path, panel, records = load_panel(args.phase)
    anchors = [args.r002, args.a2]
    if args.candidate in anchors or len(set(anchors)) != 2:
        raise ValueError("candidate and anchors must be three distinct model IDs")
    if args.candidate not in slate["candidate_order"]:
        raise ValueError(f"candidate is not in sealed slate: {args.candidate}")
    if anchors != [str(row["id"]) for row in slate["anchors"]]:
        raise ValueError("anchor IDs/order differ from sealed slate")
    registry = load_registry(args.registry.resolve())
    clean_registry_or_fail(args.registry.resolve(), registry, seal)
    for model_id in [args.candidate, *anchors]:
        registry.require(model_id)
    fingerprint = run_fingerprint(
        args.phase,
        args.candidate,
        anchors,
        registry,
        panel_path,
        panel,
        records,
    )
    tasks = build_tasks(registry, args.candidate, anchors, records, fingerprint)
    expected = len(records) * len(anchors) * 2
    if len(tasks) != expected or expected not in {144, 400}:
        raise ValueError(f"unexpected targeted task closure: {len(tasks)} != {expected}")
    expected_ids = {str(task["task_id"]) for task in tasks}
    if len(expected_ids) != len(tasks):
        raise ValueError("task IDs are not unique")
    expected_tasks = {str(task["task_id"]): task for task in tasks}
    if args.resume:
        validate_resume(args.jsonl.resolve(), fingerprint, expected_tasks)
    elif args.jsonl.exists():
        raise FileExistsError("refusing to overwrite an existing games JSONL without a new path")
    manifest = {
        "schema": SCHEMA,
        "phase": args.phase,
        "candidate": args.candidate,
        "anchors": anchors,
        "run_fingerprint": fingerprint,
        "registry": str(registry.path),
        "registry_file_sha256": file_sha256(registry.path),
        "registry_and_serving_code_sha256": registry_fingerprint(registry),
        "v10_evaluation_implementation_sha256": v10.implementation_fingerprint(),
        "evaluation_contract_file_sha256": file_sha256(HERE / "evaluation_contract.json"),
        "candidate_slate_file_sha256": file_sha256(HERE / "candidate_slate.json"),
        "candidate_slate_core_sha256": slate["slate_core_sha256"],
        "protocol_seal_file_sha256": file_sha256(HERE / "protocol_seal.json"),
        "panel": str(panel_path),
        "panel_file_sha256": file_sha256(panel_path),
        "panel_records_sha256": panel["records_sha256"],
        "sources": len(records),
        "targeted_pairs": [[args.candidate, anchor] for anchor in anchors],
        "expected_games": expected,
        "protocol_verification": protocol_verification,
        "confirmatory_execution_flag": bool(args.execute_confirmatory),
        "dry_run": bool(args.dry_run),
    }
    args.run_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.run_manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if args.dry_run:
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "run_manifest": str(args.run_manifest),
                    "run_fingerprint": fingerprint,
                    "expected_games": expected,
                    "games_started": False,
                },
                ensure_ascii=False,
            )
        )
        return
    if args.phase == "confirmatory":
        from seal_finalist import validate_finalist_seal

        finalist = validate_finalist_seal(args.finalist_seal.resolve())
        if finalist["finalist"] != args.candidate:
            raise ValueError("confirmatory candidate differs from sealed screen winner")
    consume_lock(
        args.phase,
        args.candidate,
        fingerprint,
        args.jsonl.resolve(),
        args.run_manifest.resolve(),
        registry,
        args.resume,
    )
    v10.run_tasks(tasks, args.jsonl.resolve(), args.workers, args.resume)
    from audit_dual_anchor import audit

    report = audit(
        args.phase,
        args.candidate,
        args.jsonl.resolve(),
        args.run_manifest.resolve(),
        args.registry.resolve(),
        args.r002,
        args.a2,
    )
    if report["run_fingerprint"] != fingerprint:
        raise ValueError("audit run fingerprint differs from sealed task fingerprint")
    args.audit_output.parent.mkdir(parents=True, exist_ok=True)
    args.audit_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"run_manifest": str(args.run_manifest), "audit": str(args.audit_output), "passed": report["passed"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
