#!/usr/bin/env python3
"""Freeze a V118-unseen ACCOUNT_ONLINE gold-registration panel."""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
V118 = HERE.parent
MODEL = V118.parent
PROJECT = MODEL.parent
MODEL_DATA = PROJECT / "model_data"
BASE_DIR = MODEL_DATA / "round_robin/gold18_replay_admitted_128x2_20260830"
BASE_SCRIPT = BASE_DIR / "prepare_replay_panels.py"
OFFICIAL_PANEL = BASE_DIR / "official_panel.json"
EXPOSURE_LEDGER = MODEL_DATA / "loop_evaluations/exposure_ledger.jsonl"
OUTPUT = HERE / "account_panel.json"
AUDIT = HERE / "admission_audit.json"
SALT = "v118-gold-registration-account-unseen-20260831-v1"
EXPECTED_CONFIGURATION = "1a9006518ccbe403a70e107bb041cc2489e38da637ae0e3872500010963c46f3"
SHOPS = (
    "BAKERY", "BRUNCH_SPOT", "FARMERS_MARKET", "ICE_CREAM_SHOP",
    "PET_CAFE", "PIZZA_SHOP", "SMOOTHIE_SHOP", "YARN_STORE",
)
PER_SHOP = 16


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rank(candidate: dict[str, Any]) -> str:
    return hashlib.sha256(
        f"{SALT}\0{candidate['episode_id']}\0{candidate['submission_id']}".encode()
    ).hexdigest()


def load_base():
    spec = importlib.util.spec_from_file_location("gold18_panel_builder", BASE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import gold18 panel builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def exposure_keys() -> tuple[set[str], set[int], set[str], int]:
    ids: set[str] = set()
    seeds: set[int] = set()
    scenarios: set[str] = set()
    count = 0
    if EXPOSURE_LEDGER.is_file():
        for line in EXPOSURE_LEDGER.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            count += 1
            if row.get("episode_id") is not None:
                ids.add(str(row["episode_id"]))
            if row.get("seed") is not None:
                seeds.add(int(row["seed"]))
            if row.get("scenario_sha256"):
                scenarios.add(str(row["scenario_sha256"]))
    return ids, seeds, scenarios, count


def v118_exposure_keys() -> tuple[set[str], set[int], set[str]]:
    ids: set[str] = set()
    seeds: set[int] = set()
    scenarios: set[str] = set()
    for name in ("gate_panel_manifest_rc1.json", "gate_panel_manifest_rc2.json"):
        data = json.loads((V118 / name).read_text(encoding="utf-8"))
        for row in data["assignments"]:
            ids.add(str(row["episode_id"]))
            seeds.add(int(row["actual_seed"]))
            scenarios.add(str(row["scenario_sha256"]))
    return ids, seeds, scenarios


def main() -> int:
    if OUTPUT.exists() or AUDIT.exists():
        raise SystemExit("gold-registration account panel already exists; refusing refreeze")
    base = load_base()
    candidates = sorted(base.account_candidates(), key=rank)
    ledger_ids, ledger_seeds, ledger_scenarios, ledger_count = exposure_keys()
    v118_ids, v118_seeds, v118_scenarios = v118_exposure_keys()
    official = json.loads(OFFICIAL_PANEL.read_text(encoding="utf-8"))
    official_rows = official["final_test"]
    official_ids = {str(row["episode_id"]) for row in official_rows}
    official_seeds = {int(row["seed"]) for row in official_rows}
    official_scenarios = {str(row["scenario_sha256"]) for row in official_rows}

    forbidden_ids = ledger_ids | v118_ids | official_ids
    forbidden_seeds = ledger_seeds | v118_seeds | official_seeds
    forbidden_scenarios = ledger_scenarios | v118_scenarios | official_scenarios
    selected: dict[str, list[dict[str, Any]]] = defaultdict(list)
    rejects: Counter[str] = Counter()
    inspected = 0
    seen_pairs: set[tuple[str, str]] = set()

    for candidate in candidates:
        if all(len(selected[shop]) >= PER_SHOP for shop in SHOPS):
            break
        try:
            row = base.inspect_replay(candidate)
        except Exception as exc:
            rejects[f"parse:{type(exc).__name__}"] += 1
            inspected += 1
            continue
        inspected += 1
        pair = (str(row["episode_id"]), str(row["replay_sha256"]))
        if pair in seen_pairs:
            rejects["duplicate_episode_plus_replay_sha256"] += 1
            continue
        seen_pairs.add(pair)
        if row["date"] < "2026-08-20":
            rejects["before_cutoff"] += 1
            continue
        if row["module_version"] != "1.32.7":
            rejects["module_version_mismatch"] += 1
            continue
        if row["configuration_sha256"] != EXPECTED_CONFIGURATION:
            rejects["configuration_mismatch"] += 1
            continue
        if row["statuses"] != ["DONE", "DONE"]:
            rejects["not_done_done"] += 1
            continue
        if str(row["episode_id"]) in forbidden_ids:
            rejects["episode_exposed_or_cross_panel"] += 1
            continue
        if int(row["seed"]) in forbidden_seeds:
            rejects["seed_exposed_or_cross_panel"] += 1
            continue
        if str(row["scenario_sha256"]) in forbidden_scenarios:
            rejects["scenario_exposed_or_cross_panel"] += 1
            continue
        shop = str(row["first_shop"])
        if len(selected[shop]) >= PER_SHOP:
            rejects["shop_quota_full"] += 1
            continue
        selected[shop].append({**row, "role": "final_test", "selection_rank": rank(candidate)})
        forbidden_ids.add(str(row["episode_id"]))
        forbidden_seeds.add(int(row["seed"]))
        forbidden_scenarios.add(str(row["scenario_sha256"]))

    missing = {shop: PER_SHOP - len(selected[shop]) for shop in SHOPS if len(selected[shop]) < PER_SHOP}
    if missing:
        raise RuntimeError(f"cannot fill balanced unseen account panel: {missing}; inspected={inspected}")
    rows = sorted([row for shop in SHOPS for row in selected[shop]], key=lambda row: row["selection_rank"])
    checks = {
        "count_128": len(rows) == 128,
        "balanced_16_per_first_shop": Counter(row["first_shop"] for row in rows) == Counter({shop: 16 for shop in SHOPS}),
        "episode_ids_unique": len({row["episode_id"] for row in rows}) == 128,
        "seeds_unique": len({row["seed"] for row in rows}) == 128,
        "scenarios_unique": len({row["scenario_sha256"] for row in rows}) == 128,
        "v118_development_and_gate_overlap_zero": not ({row["episode_id"] for row in rows} & v118_ids),
        "official_episode_overlap_zero": not ({row["episode_id"] for row in rows} & official_ids),
        "official_seed_overlap_zero": not ({row["seed"] for row in rows} & official_seeds),
        "official_scenario_overlap_zero": not ({row["scenario_sha256"] for row in rows} & official_scenarios),
        "all_after_cutoff": all(row["date"] >= "2026-08-20" for row in rows),
        "module_exact": all(row["module_version"] == "1.32.7" for row in rows),
        "configuration_exact": all(row["configuration_sha256"] == EXPECTED_CONFIGURATION for row in rows),
        "historical_actions_results_market_excluded": all(
            not row["historical_actions_included"]
            and not row["historical_rewards_included"]
            and not row["historical_market_inventory_included"]
            for row in rows
        ),
    }
    if not all(checks.values()):
        raise RuntimeError(f"account panel checks failed: {checks}")
    panel = {
        "schema": "kaggriculture-v118-gold-registration-account-panel-v1",
        "panel": "account_online",
        "role": "final_test",
        "cutoff_inclusive": "2026-08-20",
        "module_version": "1.32.7",
        "configuration_sha256": EXPECTED_CONFIGURATION,
        "selection_salt": SALT,
        "candidate_rows_available": len(candidates),
        "candidate_rows_inspected": inspected,
        "final_test": rows,
        "checks": checks,
    }
    OUTPUT.write_text(json.dumps(panel, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    before_hash = sha256(EXPOSURE_LEDGER)
    with EXPOSURE_LEDGER.open("a", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps({
                "model_id": "v118_gold_registration_20260831",
                "phase": "account_online_final_test",
                "episode_id": row["episode_id"],
                "seed": row["seed"],
                "date": row["date"],
                "first_shop": row["first_shop"],
                "scenario_sha256": row["scenario_sha256"],
                "salt": SALT,
            }, ensure_ascii=False) + "\n")
    audit = {
        "schema": "kaggriculture-v118-gold-registration-admission-audit-v1",
        "account_panel_sha256": sha256(OUTPUT),
        "official_panel_path": str(OFFICIAL_PANEL.relative_to(PROJECT)),
        "official_panel_sha256": sha256(OFFICIAL_PANEL),
        "ledger_rows_before": ledger_count,
        "ledger_sha256_before": before_hash,
        "ledger_rows_appended": 128,
        "ledger_sha256_after": sha256(EXPOSURE_LEDGER),
        "v118_exposed_episode_count": len(v118_ids),
        "candidate_rows_available": len(candidates),
        "candidate_rows_inspected": inspected,
        "rejects": dict(sorted(rejects.items())),
        "checks": checks,
        "status": "PASS",
    }
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "PASS", "selected": len(rows), "inspected": inspected,
        "first_shops": Counter(row["first_shop"] for row in rows),
        "rejects": audit["rejects"], "checks": checks,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
