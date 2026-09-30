#!/usr/bin/env python3
"""Build the V28 broad-panel-rejected Smoothie process package."""

from __future__ import annotations

import hashlib
import json
import tarfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "v27_lucaskna_shop_router" / "main.py"
APPENDIX = '\n__version__ = "v28-smoothie-broad-panel-rejected-rc1"\n'


def main() -> int:
    target = HERE / "main.py"; target.write_text(BASE.read_text(encoding="utf-8") + APPENDIX, encoding="utf-8")
    archive = HERE / "submission.tar.gz"
    with tarfile.open(archive, "w:gz") as tar: tar.add(target, arcname="main.py")
    manifest = {
        "candidate": "V28 Smoothie broad-panel process RC1",
        "status": "LOCAL_PROCESS_VERSION_REJECTED_CI_TOUCHES_ZERO",
        "parent": "V27 lucaskna Smoothie expert",
        "main_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(), "archive_bytes": archive.stat().st_size,
        "broad_panel": {
            "models": 12, "seeds": [101000, 101127], "games_each": 3072,
            "impacted_cells": 471, "score_uplift_pp": 0.13020833333333331,
            "score_uplift_ci95_pp": [0.0, 0.3255208333333333],
            "target_shop_uplift_pp": 0.8492569002123143,
            "positive_zero_negative": [4, 3068, 0], "guardrail_pass": True, "primary_pass": False,
        },
    }
    (HERE / "submission_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
