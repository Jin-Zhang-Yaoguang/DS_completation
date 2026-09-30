"""Read-only verifier for V14 panels, exposure ledger and optional candidate seal."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from common import (
    ALLOWED_SPLITS,
    CONFIRMATORY_QUOTAS,
    CONFIRMATORY_SALT,
    HERE,
    PROJECT_ROOT,
    SCREEN_QUOTAS,
    SCREEN_SALT,
    SOURCE_MANIFEST,
    canonical,
    file_sha256,
    load_json,
    load_sources,
    sha256_bytes,
)
from build_panels import (
    ASSET_SUMS,
    CONFIRMATORY_MANIFEST,
    CONFIRMATORY_PANEL,
    EXPOSURE_INVENTORY,
    PANEL_SEAL,
    SCREEN_MANIFEST,
    SCREEN_PANEL,
    build_exposure_inventory,
    panel_payload,
    select_panel,
    validate_panels,
)


def resolve_recorded_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def expected_jsonl(rows: list[dict[str, Any]]) -> bytes:
    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows
    ).encode("utf-8")


def _seal_core(seal: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "status",
        "test_access",
        "daily_replay_payloads_accessed",
        "candidate_archives_sealed",
        "environment_games_started",
        "source_manifest_file_sha256",
        "exposure_union_seed_count",
        "exposure_union_seeds_sha256",
        "screen_records_sha256",
        "confirmatory_records_sha256",
        "screen_confirmatory_disjoint",
        "screen_test_source_count",
        "confirmatory_test_source_count",
        "assets",
    )
    return {key: seal[key] for key in keys}


def verify(require_candidates: bool = False) -> dict[str, Any]:
    required = [
        EXPOSURE_INVENTORY,
        SCREEN_PANEL,
        SCREEN_MANIFEST,
        CONFIRMATORY_PANEL,
        CONFIRMATORY_MANIFEST,
        PANEL_SEAL,
        ASSET_SUMS,
        HERE / "evaluation_contract.json",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"frozen panel protocol is incomplete: {missing}")

    stored_inventory = load_json(EXPOSURE_INVENTORY)
    stored_screen = load_json(SCREEN_PANEL)
    stored_confirm = load_json(CONFIRMATORY_PANEL)
    sources = load_sources()
    current_inventory = build_exposure_inventory(sources)
    stored_seeds = [int(row["seed"]) for row in stored_inventory.get("records") or []]
    if (
        len(stored_seeds) != len(set(stored_seeds))
        or len(stored_seeds) != int(stored_inventory.get("union_seed_count", -1))
        or sha256_bytes(canonical(sorted(stored_seeds)))
        != stored_inventory.get("union_seeds_sha256")
    ):
        raise ValueError("frozen exposure inventory seed closure is inconsistent")
    stored_exposed = set(stored_seeds)
    available = [row for row in sources if row.seed not in stored_exposed]
    expected_screen_rows = select_panel(available, SCREEN_QUOTAS, SCREEN_SALT)
    expected_screen_seeds = {row.seed for row in expected_screen_rows}
    expected_confirm_rows = select_panel(
        [row for row in available if row.seed not in expected_screen_seeds],
        CONFIRMATORY_QUOTAS,
        CONFIRMATORY_SALT,
    )
    expected_screen = panel_payload(
        "screen36",
        expected_screen_rows,
        SCREEN_SALT,
        SCREEN_QUOTAS,
        stored_inventory["union_seeds_sha256"],
    )
    expected_confirm = panel_payload(
        "confirmatory100_single_use",
        expected_confirm_rows,
        CONFIRMATORY_SALT,
        CONFIRMATORY_QUOTAS,
        stored_inventory["union_seeds_sha256"],
    )
    if stored_screen != expected_screen:
        raise ValueError("screen panel differs from deterministic frozen-ledger selection")
    if stored_confirm != expected_confirm:
        raise ValueError("confirmatory panel differs from deterministic frozen-ledger selection")

    current_exposed = {int(row["seed"]) for row in current_inventory["records"]}
    selected = {
        int(row["seed"]) for row in [*stored_screen["records"], *stored_confirm["records"]]
    }
    newly_exposed_selected = sorted(selected & current_exposed)
    if newly_exposed_selected:
        raise ValueError(
            f"a currently discoverable development artifact exposes frozen panel sources: "
            f"{newly_exposed_selected[:5]}"
        )

    checks = validate_panels(stored_inventory, stored_screen, stored_confirm)
    official = {row.seed: row for row in sources}
    for label, panel in (("screen", stored_screen), ("confirmatory", stored_confirm)):
        for row in panel["records"]:
            seed = int(row["seed"])
            if seed not in official or row != official[seed].__dict__:
                raise ValueError(f"{label} source no longer equals official metadata: {seed}")
            if str(row["split"]) not in ALLOWED_SPLITS:
                raise ValueError(f"{label} contains a forbidden split: {row['split']}")

    if SCREEN_MANIFEST.read_bytes() != expected_jsonl(stored_screen["records"]):
        raise ValueError("screen JSONL manifest differs from panel records")
    if CONFIRMATORY_MANIFEST.read_bytes() != expected_jsonl(stored_confirm["records"]):
        raise ValueError("confirmatory JSONL manifest differs from panel records")

    seal = load_json(PANEL_SEAL)
    if seal.get("schema") != "kaggriculture-v14-panel-seal-1":
        raise ValueError("unexpected panel seal schema")
    if seal.get("seal_core_sha256") != sha256_bytes(canonical(_seal_core(seal))):
        raise ValueError("panel seal core hash mismatch")
    if seal.get("source_manifest_file_sha256") != file_sha256(SOURCE_MANIFEST):
        raise ValueError("panel seal source manifest hash mismatch")
    if seal.get("exposure_union_seeds_sha256") != stored_inventory["union_seeds_sha256"]:
        raise ValueError("panel seal exposure hash mismatch")
    if seal.get("screen_records_sha256") != stored_screen["records_sha256"]:
        raise ValueError("panel seal screen hash mismatch")
    if seal.get("confirmatory_records_sha256") != stored_confirm["records_sha256"]:
        raise ValueError("panel seal confirmatory hash mismatch")

    for asset in seal.get("assets") or []:
        path = resolve_recorded_path(str(asset["path"]))
        if not path.is_file():
            raise FileNotFoundError(f"panel-sealed asset missing: {path}")
        if path.stat().st_size != int(asset["size_bytes"]) or file_sha256(path) != asset["file_sha256"]:
            raise ValueError(f"panel-sealed asset changed: {path}")
    expected_sums = "".join(
        f"{file_sha256(resolve_recorded_path(str(asset['path'])))}  {asset['path']}\n"
        for asset in seal["assets"]
    ) + f"{file_sha256(PANEL_SEAL)}  {str(PANEL_SEAL.resolve().relative_to(PROJECT_ROOT.resolve()))}\n"
    if ASSET_SUMS.read_text(encoding="utf-8") != expected_sums:
        raise ValueError("protocol_assets.sha256 differs from current sealed assets")

    sealed_runtime = HERE / "sealed_runtime"
    if sealed_runtime.exists():
        from seal_candidates import verify_candidate_seal

        candidate_report = verify_candidate_seal()
    elif require_candidates:
        raise FileNotFoundError(
            "candidate archives are not sealed; run seal_candidates.py only after final package QA"
        )
    else:
        candidate_report = {
            "status": "UNSEALED_FAIL_CLOSED_FOR_RUNS",
            "candidate_order": [],
        }

    checks.update(
        {
            "frozen_inventory_seed_closure": True,
            "current_rescan_does_not_expose_selected_sources": True,
            "screen_manifest_exact": True,
            "confirmatory_manifest_exact": True,
            "panel_seal_core": True,
            "panel_sealed_assets_unchanged": True,
            "test_access_false": seal.get("test_access") is False,
            "test_outcomes_not_accessed": seal.get("daily_replay_payloads_accessed") is False,
        }
    )
    if not all(checks.values()):
        raise ValueError({name: ok for name, ok in checks.items() if not ok})
    return {
        "schema": "kaggriculture-v14-protocol-verification-1",
        "status": "PASS",
        "checks": checks,
        "source_manifest_file_sha256": file_sha256(SOURCE_MANIFEST),
        "exposure_union_seed_count": stored_inventory["union_seed_count"],
        "exposure_union_seeds_sha256": stored_inventory["union_seeds_sha256"],
        "current_rescan_union_seed_count": current_inventory["union_seed_count"],
        "current_rescan_union_seeds_sha256": current_inventory["union_seeds_sha256"],
        "current_rescan_evidence_sha256": current_inventory["incremental_evidence_sha256"],
        "frozen_evidence_drift_detected": (
            current_inventory["incremental_evidence_sha256"]
            != stored_inventory["incremental_evidence_sha256"]
        ),
        "screen_records_sha256": stored_screen["records_sha256"],
        "confirmatory_records_sha256": stored_confirm["records_sha256"],
        "screen_date_counts": stored_screen["date_counts"],
        "confirmatory_date_counts": stored_confirm["date_counts"],
        "screen_test_source_count": stored_screen["test_source_count"],
        "confirmatory_test_source_count": stored_confirm["test_source_count"],
        "panel_seal_file_sha256": file_sha256(PANEL_SEAL),
        "candidate_runtime": candidate_report,
        "games_started_by_verifier": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-candidates", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify(args.require_candidates), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
