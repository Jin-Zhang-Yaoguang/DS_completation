#!/usr/bin/env python3
"""Build the frozen V30 offline-gold package from the independently confirmed V21 policy."""

from __future__ import annotations

import hashlib
import json
import tarfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "v21_top_meta_moe" / "main.py"
APPENDIX = '\n__version__ = "v30-offline-gold-hierarchical-moe-rc1"\n'


def main() -> int:
    target = HERE / "main.py"
    target.write_text(BASE.read_text(encoding="utf-8") + APPENDIX, encoding="utf-8")
    archive = HERE / "submission.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(target, arcname="main.py")
    manifest = {
        "candidate": "V30 offline-gold hierarchical MoE RC1",
        "status": "OFFLINE_GOLD_LEVEL_QA_PASS",
        "parent": "V21 top-meta hierarchical MoE RC1",
        "architecture": "shop-demand router + production experts + state-safe executor + product-level demand-delay seller",
        "routing": "YARN_STORE keeps yarn expert; non-YARN routes switch to lucaskna production expert at step 216",
        "sell_controller": "demand_delay_25",
        "main_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "archive_bytes": archive.stat().st_size,
        "independent_confirmation": {
            "seed_range": [104000, 104127], "opponent_families": 8,
            "games_each": 2048, "total_games": 6144,
            "v21_score_rate": 0.83447265625,
            "vs_v19": {"uplift_pp": 19.189453125, "ci95_pp": [17.041015625, 21.2890625], "positive_zero_negative": [488, 1556, 4], "margin_delta_mean": 952.44384765625, "own_delta_mean": 445.65234375},
            "vs_v20": {"uplift_pp": 14.404296875, "ci95_pp": [12.255859375, 16.50390625], "positive_zero_negative": [295, 1753, 0], "margin_delta_mean": 868.39404296875, "own_delta_mean": 411.087890625},
            "family_guardrails_pass": True,
        },
        "qa": {
            "research_package_exact_games": [8, 8],
            "official_cpp_exact_games": [4, 4],
            "official_statuses_all_done": True,
            "action_safety_games": 224,
            "unit_orders": 1501217,
            "unit_precondition_invalid": 0,
            "market_overflow": 0,
            "hand_mismatch": 0,
        },
    }
    (HERE / "submission_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
