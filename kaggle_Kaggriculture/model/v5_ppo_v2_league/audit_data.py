"""G0 audit for PPO v2 sources, group splits, lineage and effective families.

The audit is intentionally conservative: missing public champion replays and
legacy shards without explicit lineage are reported rather than silently
treated as independent training examples.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import platform
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
MODEL_DIR = HERE.parent
FIXTURES = MODEL_DIR / "v2_survival_guard" / "fixtures"
CHAMPION_REPLAYS = HERE / "data" / "replays" / "champion"
IMPLEMENTED_FAMILY_IDS = {"v1", "v2", "v3", "v4", "starter", "production_low", "production_high", "market_buy", "market_delay", "market_priority", "exploit_wheat", "exploit_cleanup"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def group_bucket(group_id: str) -> int:
    return int.from_bytes(hashlib.sha256(group_id.encode("utf-8")).digest()[:8], "big") % 100


def split_for(group_id: str) -> str:
    bucket = group_bucket(group_id)
    return "train" if bucket < 80 else "validation" if bucket < 90 else "test"


def audit_bc_shards(data_dir: Path):
    rows = []
    exact = Counter()
    split_counts = Counter()
    family_counts = Counter()
    shard_files = sorted(data_dir.glob("bc-*.npz"))
    for shard in shard_files:
        data = np.load(shard, allow_pickle=False)
        required = {"features", "actions", "seeds", "seats", "opponents"}
        missing = sorted(required.difference(data.files))
        if missing:
            raise ValueError(f"{shard}: missing {missing}")
        explicit_lineage = {"sources", "strategy_families", "episode_ids"}.issubset(data.files)
        for i, (seed, seat, opponent) in enumerate(zip(data["seeds"], data["seats"], data["opponents"])):
            family = str(data["strategy_families"][i] if explicit_lineage else opponent)
            # Group by source/family/episode/seed.  Seed is shared across seats,
            # so the two seats cannot leak across partitions.
            if explicit_lineage:
                group_id = f"{str(data['sources'][i])}|{family}|{str(data['episode_ids'][i])}|seed-{int(seed)}"
            else:
                group_id = f"legacy_v3_generated|{family}|episode-{int(seed)}|seed-{int(seed)}"
            split = split_for(group_id)
            action_hash = hashlib.sha256(np.asarray(data["actions"][i]).tobytes()).hexdigest()
            exact[action_hash] += 1
            split_counts[split] += 1
            family_counts[(family, split)] += 1
            rows.append({"shard": shard.name, "row": i, "seed": int(seed), "seat": int(seat), "family": family, "group_id": group_id, "split": split, "action_hash": action_hash})
    groups = defaultdict(set)
    for row in rows:
        groups[row["group_id"]].add(row["split"])
    leakage = {group: sorted(splits) for group, splits in groups.items() if len(splits) > 1}
    return {
        "shards": [{"file": p.name, "episodes": int(np.load(p, allow_pickle=False)["seeds"].shape[0]), "sha256": sha256(p)} for p in shard_files],
        "episodes": len(rows),
        "groups": len(groups),
        "split_counts": dict(split_counts),
        "family_counts": {f"{family}|{split}": count for (family, split), count in sorted(family_counts.items())},
        "exact_action_sequence_hashes": len(exact),
        "duplicate_action_rows": int(sum(count - 1 for count in exact.values() if count > 1)),
        "group_leakage_count": len(leakage),
        "group_leakage_examples": dict(list(leakage.items())[:10]),
        "legacy_warning": None if any({"sources", "strategy_families", "episode_ids"}.issubset(np.load(p, allow_pickle=False).files) for p in shard_files) else "legacy V3 shards lack source/lineage fields; group IDs are conservatively derived from family and seed; regenerate for PPO v2 before final test",
    }


def audit_replays():
    rows = []
    paths = [(path, "available_public_fixture") for path in sorted(FIXTURES.glob("*.json.gz"))]
    paths.extend((path, "available_rank1_public_replay") for path in sorted(CHAMPION_REPLAYS.glob("*.json")))
    for path, source_status in paths:
        try:
            if path.suffix == ".gz":
                source_handle = gzip.open(path, "rt", encoding="utf-8")
            else:
                source_handle = path.open("rt", encoding="utf-8")
            with source_handle as source:
                payload = json.load(source)
            length = len(payload) if isinstance(payload, list) else (len(payload.get("steps", [])) if isinstance(payload, dict) else None)
            info = payload.get("info", {}) if isinstance(payload, dict) else {}
            rows.append({"file": path.name, "episode_id": path.name.split("episode-")[1].split("-")[0], "records": length, "teams": info.get("TeamNames", []), "seed": info.get("seed"), "records_have_public_actions": bool(isinstance(payload, dict) and payload.get("steps")), "sha256": sha256(path), "status": source_status})
        except Exception as exc:  # pragma: no cover - audit should report bad fixtures
            rows.append({"file": path.name, "sha256": sha256(path), "status": "unreadable", "error": repr(exc)})
    return rows


def run(output: Path, bc_dir: Path):
    opponent_manifest = json.loads((HERE / "opponent_manifest.json").read_text(encoding="utf-8"))
    available = [row for row in opponent_manifest["opponents"] if row["status"] == "available" and row["id"] in IMPLEMENTED_FAMILY_IDS]
    available_families = sorted({row["family"] for row in available})
    bc = audit_bc_shards(bc_dir) if bc_dir.is_dir() else {"episodes": 0, "groups": 0, "split_counts": {}, "family_counts": {}, "shards": []}
    report = {
        "schema": "kaggriculture-ppo-v2-g0-audit-1",
        "runtime": {"python": platform.python_version(), "platform": platform.platform(), "numpy": np.__version__},
        "primary_baseline": "v1",
        "safety_comparator": "v2",
        "opponent_pool": {"target": 28, "allowed": [24, 32], "manifest_entries": len(opponent_manifest["opponents"]), "executable_available_families": len(available_families), "families": available_families, "minimum_effective_families": 12, "implemented_family_ids": sorted(IMPLEMENTED_FAMILY_IDS), "missing_external": [row["id"] for row in opponent_manifest["opponents"] if row["status"] == "missing_external"], "planned_not_counted": [row["id"] for row in opponent_manifest["opponents"] if row["status"] == "planned"], "data_only_not_counted": [row["id"] for row in opponent_manifest["opponents"] if row["status"] == "available" and row["id"] not in IMPLEMENTED_FAMILY_IDS]},
        "bc_legacy": bc,
        "public_replays": audit_replays(),
        "split_contract": {"group_key": "source|strategy_family|episode_id|seed", "train": "hash bucket 0-79", "validation": "hash bucket 80-89", "test": "hash bucket 90-99", "same_seed_dual_seat_locked": True, "near_duplicate_policy": "trajectory/action signature clustering required before final PPO"},
        "gates": {"primary_baseline_declared": True, "group_leakage_zero": bc.get("group_leakage_count", 0) == 0, "minimum_families_for_full_ppo": len(available_families) >= 12, "champion_top10_replays_present": not any(row["status"] == "missing_external" for row in opponent_manifest["opponents"]), "legacy_data_regeneration_required": bc.get("legacy_warning") is not None},
    }
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    replay_daily = HERE / "data" / "replay_daily.npz"
    sources = {"legacy_v3_bc": str(bc_dir), "public_replay_fixtures": str(FIXTURES), "champion_rank1_replays": str(CHAMPION_REPLAYS), "champion_top10": "partial: rank1 downloaded; ranks2-10 missing"}
    if replay_daily.is_file():
        sources["champion_daily_dataset"] = {"path": str(replay_daily), "sha256": sha256(replay_daily)}
    (HERE / "data_manifest.json").write_text(json.dumps({"schema": "kaggriculture-ppo-v2-data-1", "audit_report": output.name, "sources": sources, "report_sha256": sha256(output)}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (HERE / "opponent_manifest.json").write_text(json.dumps(opponent_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bc-dir", type=Path, default=MODEL_DIR / "v3_bc_ppo_hybrid" / "data" / "bc")
    parser.add_argument("--output", type=Path, default=HERE / "g0_audit_report.json")
    args = parser.parse_args()
    print(json.dumps(run(args.output, args.bc_dir), ensure_ascii=False, indent=2))
