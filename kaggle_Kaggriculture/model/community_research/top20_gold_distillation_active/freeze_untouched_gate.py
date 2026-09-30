#!/usr/bin/env python3
"""Create the one-shot untouched seed panel and lock the candidate hashes."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re


HERE = Path(__file__).resolve().parent
MODEL = HERE.parents[1]
SEED_FILE = HERE / "v123_frozen_untouched_seeds.json"
MANIFEST_FILE = HERE / "v123_candidate_freeze_manifest.json"
SALT = "kaggriculture-v123-vs-v120-untouched-gate-2026-09-02-v1"
COUNT = 32
DEV_SEEDS = {
    122003, 122021, 122041, 122063, 122087, 122111, 122137, 122167,
    122189, 122219, 122251, 122279, 122309, 122333, 122363, 122393,
    122417, 122449, 122477, 122501, 122537, 122557, 122579, 122611,
    122633, 122663, 122689, 122719, 122743, 122773, 122801, 122827,
}
CANDIDATE_FILES = (
    HERE / "whyme_phase_release_candidate.py",
    HERE / "whyme_phase_core.py",
    HERE / "whyme_role_phase_contract.json",
)
OPPONENT_FILES = (MODEL / "v120_hierarchical_top5_distillation" / "main.py",)
EVALUATOR_FILES = (HERE / "evaluate_vs_v120.py",)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def previously_observed_seeds() -> set[int]:
    """Read only seed keys, never rewards/outcomes, from pre-freeze reports."""
    observed: set[int] = set()
    pattern = re.compile(r'"seed"\s*:\s*(\d+)')
    for path in HERE.glob("*.json"):
        if path in {SEED_FILE, MANIFEST_FILE}:
            continue
        for match in pattern.finditer(path.read_text(encoding="utf-8", errors="ignore")):
            observed.add(int(match.group(1)))
    return observed


def derive_seeds(excluded: set[int]) -> list[int]:
    seeds: list[int] = []
    index = 0
    while len(seeds) < COUNT:
        digest = hashlib.sha256(f"{SALT}:{index}".encode()).digest()
        seed = int.from_bytes(digest[:8], "big") % 2_000_000_000 + 1
        index += 1
        if seed in excluded or seed in seeds:
            continue
        seeds.append(seed)
    return seeds


def main() -> int:
    if SEED_FILE.exists() or MANIFEST_FILE.exists():
        raise SystemExit("freeze artifacts already exist; refusing to regenerate the untouched panel")
    observed = previously_observed_seeds()
    seeds = derive_seeds(observed | DEV_SEEDS)
    now = datetime.now(timezone.utc).isoformat()
    seed_payload = {
        "schema": "kaggriculture-v123-untouched-seed-panel-v1",
        "created_at_utc": now,
        "derivation": "sha256(salt:index) mapped to [1, 2000000000]",
        "salt": SALT,
        "count": len(seeds),
        "excluded_previously_observed_seed_count": len(observed),
        "excluded_development_seeds": sorted(DEV_SEEDS),
        "seeds": seeds,
        "outcomes_unseen_at_creation": True,
    }
    manifest = {
        "schema": "kaggriculture-v123-candidate-freeze-v1",
        "frozen_at_utc": now,
        "candidate_frozen_before_evaluation": True,
        "gate": {
            "opponent": "V120",
            "dual_seat": True,
            "games": 2 * len(seeds),
            "required_win_rate": ">0.70",
            "one_shot": True,
        },
        "candidate_files": {str(path.relative_to(HERE)): sha256(path) for path in CANDIDATE_FILES},
        "opponent_files": {str(path.relative_to(MODEL)): sha256(path) for path in OPPONENT_FILES},
        "evaluator_files": {str(path.relative_to(HERE)): sha256(path) for path in EVALUATOR_FILES},
        "seed_file": SEED_FILE.name,
        "seed_file_sha256": None,
    }
    SEED_FILE.write_text(json.dumps(seed_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest["seed_file_sha256"] = sha256(SEED_FILE)
    MANIFEST_FILE.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"seed_file": str(SEED_FILE), "manifest": str(MANIFEST_FILE), "seeds": seeds}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
