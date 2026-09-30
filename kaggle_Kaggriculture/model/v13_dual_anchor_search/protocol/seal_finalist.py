"""Derive the single V13 confirmatory finalist from all sealed screen results."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from audit_dual_anchor import audit
from freeze_protocol import HERE, canonical, file_sha256, verify
from run_dual_anchor import load_slate


def screen_paths(root: Path, candidate: str) -> dict[str, Path]:
    base = root.resolve() / candidate
    return {
        "games": base / "games.jsonl",
        "run_manifest": base / "run_manifest.json",
        "audit": base / "audit.json",
    }


def recompute_screen_record(root: Path, candidate: str) -> dict[str, Any]:
    paths = screen_paths(root, candidate)
    for path in paths.values():
        if not path.is_file():
            raise FileNotFoundError(path)
    report = audit(
        "screen",
        candidate,
        paths["games"],
        paths["run_manifest"],
        HERE / "clean_screen_registry.json",
        "v12_incumbent_r002",
        "v12a2_no_shop_gate",
    )
    stored = json.loads(paths["audit"].read_text(encoding="utf-8"))
    if stored != report:
        raise ValueError(f"stored screen audit differs from strict recomputation: {candidate}")
    lock_path = HERE / "execution_state" / "screen" / f"{candidate}.json"
    if not lock_path.is_file():
        raise FileNotFoundError(f"screen consume lock missing: {lock_path}")
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if (
        lock.get("phase") != "screen"
        or lock.get("candidate") != candidate
        or lock.get("run_fingerprint") != report["run_fingerprint"]
        or Path(lock.get("jsonl", "")).resolve() != paths["games"].resolve()
        or Path(lock.get("run_manifest", "")).resolve() != paths["run_manifest"].resolve()
        or lock.get("run_manifest_file_sha256") != file_sha256(paths["run_manifest"])
    ):
        raise ValueError(f"screen consume lock differs from result closure: {candidate}")
    a2 = report["by_anchor"]["v12a2_no_shop_gate"]["overall"]
    r002 = report["by_anchor"]["v12_incumbent_r002"]["overall"]
    return {
        "candidate": candidate,
        "passed_all_screen_gates": report["passed"],
        "run_fingerprint": report["run_fingerprint"],
        "panel_records_sha256": report["panel_records_sha256"],
        "files": {
            name: {"path": str(path.resolve()), "file_sha256": file_sha256(path)}
            for name, path in paths.items()
        },
        "consume_lock": {
            "path": str(lock_path.resolve()),
            "file_sha256": file_sha256(lock_path),
        },
        "ranking_metrics": {
            "a2_competition_score_rate": a2["competition_score_rate"],
            "r002_competition_score_rate": r002["competition_score_rate"],
            "a2_mean_margin": a2["mean_margin"],
        },
    }


def rank_records(records: list[dict[str, Any]], candidate_order: list[str]) -> list[dict[str, Any]]:
    order = {candidate: index for index, candidate in enumerate(candidate_order)}
    eligible = [row for row in records if row["passed_all_screen_gates"] is True]
    return sorted(
        eligible,
        key=lambda row: (
            -float(row["ranking_metrics"]["a2_competition_score_rate"]),
            -float(row["ranking_metrics"]["r002_competition_score_rate"]),
            -float(row["ranking_metrics"]["a2_mean_margin"]),
            order[row["candidate"]],
        ),
    )


def derive_payload(screen_root: Path) -> dict[str, Any]:
    verify()
    slate = load_slate()
    order = list(slate["candidate_order"])
    records = [recompute_screen_record(screen_root, candidate) for candidate in order]
    if len(records) != len(order) or [row["candidate"] for row in records] != order:
        raise ValueError("screen candidate closure differs from slate")
    if len({row["panel_records_sha256"] for row in records}) != 1:
        raise ValueError("screen candidates did not use the identical panel")
    ranked = rank_records(records, order)
    finalist = ranked[0]["candidate"] if ranked else None
    return {
        "schema": "kaggriculture-v13-finalist-seal-1",
        "status": "sealed_screen_winner" if finalist else "sealed_no_go_no_screen_candidate_passed",
        "protocol_seal_file_sha256": file_sha256(HERE / "protocol_seal.json"),
        "candidate_slate_file_sha256": file_sha256(HERE / "candidate_slate.json"),
        "candidate_slate_core_sha256": slate["slate_core_sha256"],
        "clean_registry_file_sha256": file_sha256(HERE / "clean_screen_registry.json"),
        "screen_root": str(screen_root.resolve()),
        "candidate_order": order,
        "screen_records": records,
        "eligible_ranking": [row["candidate"] for row in ranked],
        "finalist": finalist,
        "maximum_confirmatory_finalists": 1,
        "selection_rule": slate["selection"]["ranking_order"],
        "confirmatory_games_started": False,
    }


def write_exclusive(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def validate_finalist_seal(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "kaggriculture-v13-finalist-seal-1":
        raise ValueError("unexpected finalist seal schema")
    current = derive_payload(Path(payload["screen_root"]))
    if current != payload:
        raise ValueError("finalist seal differs from strict screen recomputation")
    if payload.get("status") != "sealed_screen_winner" or payload.get("finalist") is None:
        raise ValueError("no screen candidate qualified for confirmatory")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screen-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=HERE / "finalist_seal.json")
    args = parser.parse_args()
    payload = derive_payload(args.screen_root.resolve())
    write_exclusive(args.output.resolve(), payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
