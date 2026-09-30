#!/usr/bin/env python3
"""Build the V29 selected-champion package from frozen V21 code."""

from __future__ import annotations

import hashlib, json, tarfile
from pathlib import Path


HERE=Path(__file__).resolve().parent; BASE=HERE.parent/"v21_top_meta_moe"/"main.py"
APPENDIX='\n__version__ = "v29-selected-v21-champion-rc1"\n'


def main():
    target=HERE/"main.py"; target.write_text(BASE.read_text(encoding="utf-8")+APPENDIX,encoding="utf-8")
    archive=HERE/"submission.tar.gz"
    with tarfile.open(archive,"w:gz") as tar: tar.add(target,arcname="main.py")
    manifest={
        "candidate":"V29 selected V21 champion RC1","status":"OFFLINE_GOLD_CANDIDATE_SELECTED_FOR_V30",
        "strategy":"V21 shop-demand hierarchical MoE", "main_sha256":hashlib.sha256(target.read_bytes()).hexdigest(),
        "archive_sha256":hashlib.sha256(archive.read_bytes()).hexdigest(),"archive_bytes":archive.stat().st_size,
        "champion_panel":{"models":12,"seeds":[103000,103063],"games_each":1536,
            "vs_v19":{"uplift_pp":14.0625,"ci95_pp":[11.71875,16.666666666666664],"positive_zero_negative":[271,1265,0]},
            "vs_v20":{"uplift_pp":9.5703125,"ci95_pp":[7.03125,12.37141927083331],"positive_zero_negative":[147,1389,0]},
            "v27_vs_v21":{"uplift_pp":0.0,"ci95_pp":[0.0,0.0],"positive_zero_negative":[0,1536,0]}},
    }
    (HERE/"submission_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(manifest,ensure_ascii=False,indent=2)); return 0


if __name__=="__main__": raise SystemExit(main())
