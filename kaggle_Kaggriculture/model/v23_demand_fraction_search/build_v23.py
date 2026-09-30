#!/usr/bin/env python3
"""Build the standalone V23 37.5% demand-delay process package."""

from __future__ import annotations

import hashlib
import json
import tarfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "v21_top_meta_moe" / "main.py"
APPENDIX = r'''

# --- V23 process ablation: 37.5% instead of 25% demand-delay fraction ---
_V20_DELAY_FRACTION = 0.375
__version__ = "v23-demand-delay-37-5-ablation-rc1"
'''


def main() -> int:
    target = HERE / "main.py"
    target.write_text(BASE.read_text(encoding="utf-8") + APPENDIX, encoding="utf-8")
    archive = HERE / "submission.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(target, arcname="main.py")
    manifest = {
        "candidate": "V23 demand-delay 37.5% process RC1",
        "status": "LOCAL_PROCESS_VERSION_NO_WIN_UPLIFT",
        "parent": "V21 demand-delay 25%",
        "main_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "archive_bytes": archive.stat().st_size,
        "development": {
            "models": 12, "seeds": [98600, 98615], "games_each": 384,
            "score_uplift_pp": 0.0, "positive_zero_negative": [0, 384, 0],
            "mean_bank_delta": 6.619791666671517,
            "mean_margin_delta": 2.994791666666515,
        },
    }
    (HERE / "submission_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
