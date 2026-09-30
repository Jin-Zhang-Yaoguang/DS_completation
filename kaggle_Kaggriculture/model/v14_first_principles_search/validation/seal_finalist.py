"""Derive and atomically seal the sole V14 confirmatory finalist."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from audit_dual_anchor import audit
from common import ANCHORS, HERE, file_sha256, load_json
from seal_candidates import CANDIDATE_SEAL, CANDIDATE_SLATE, CLEAN_REGISTRY, verify_candidate_seal
from verify_protocol import verify


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
        CLEAN_REGISTRY,
    )
    if load_json(paths["audit"]) != report:
        raise ValueError(f"stored screen audit differs from strict recomputation: {candidate}")
    a2 = report["by_anchor"][ANCHORS[1]]["overall"]
    r002 = report["by_anchor"][ANCHORS[0]]["overall"]
    return {
        "candidate": candidate,
        "passed_all_screen_gates": report["passed"],
        "run_fingerprint": report["run_fingerprint"],
        "panel_records_sha256": report["panel_records_sha256"],
        "files": {
            name: {"path": str(path.resolve()), "file_sha256": file_sha256(path)}
            for name, path in paths.items()
        },
        "ranking_metrics": {
            "a2_pure_win_rate": a2["pure_win_rate"],
            "r002_pure_win_rate": r002["pure_win_rate"],
            "a2_mean_margin": a2["mean_margin"],
            "a2_competition_score_rate_report_only": a2["competition_score_rate"],
        },
    }


def rank_records(
    records: list[dict[str, Any]], candidate_order: list[str]
) -> list[dict[str, Any]]:
    order = {candidate: index for index, candidate in enumerate(candidate_order)}
    eligible = [row for row in records if row["passed_all_screen_gates"] is True]
    return sorted(
        eligible,
        key=lambda row: (
            -float(row["ranking_metrics"]["a2_pure_win_rate"]),
            -float(row["ranking_metrics"]["r002_pure_win_rate"]),
            -float(row["ranking_metrics"]["a2_mean_margin"]),
            order[row["candidate"]],
        ),
    )


def derive_payload(screen_root: Path) -> dict[str, Any]:
    verify(require_candidates=True)
    verify_candidate_seal()
    if (HERE / "execution_state" / "confirmatory_consumed.json").exists():
        raise FileExistsError("confirmatory panel was already consumed")
    slate = load_json(CANDIDATE_SLATE)
    order = list(slate["candidate_order"])
    records = [recompute_screen_record(screen_root, candidate) for candidate in order]
    if [row["candidate"] for row in records] != order:
        raise ValueError("screen result order/closure differs from the sealed slate")
    if len({row["panel_records_sha256"] for row in records}) != 1:
        raise ValueError("screen candidates did not use one identical panel")
    ranked = rank_records(records, order)
    finalist = ranked[0]["candidate"] if ranked else None
    return {
        "schema": "kaggriculture-v14-finalist-seal-1",
        "status": "sealed_screen_winner" if finalist else "sealed_no_go_no_candidate_passed",
        "candidate_seal_file_sha256": file_sha256(CANDIDATE_SEAL),
        "candidate_slate_file_sha256": file_sha256(CANDIDATE_SLATE),
        "candidate_slate_core_sha256": slate["slate_core_sha256"],
        "clean_registry_file_sha256": file_sha256(CLEAN_REGISTRY),
        "screen_root": str(screen_root.resolve()),
        "candidate_order": order,
        "screen_records": records,
        "eligible_ranking": [row["candidate"] for row in ranked],
        "finalist": finalist,
        "maximum_confirmatory_finalists": 1,
        "selection_rule": slate["selection"]["ranking_order"],
        "hard_gate": "A2 pure win rate >= 0.65 and r002 pure win rate > 0.50",
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
    payload = load_json(path)
    if payload.get("schema") != "kaggriculture-v14-finalist-seal-1":
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
