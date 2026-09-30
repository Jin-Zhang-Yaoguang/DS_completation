#!/usr/bin/env python3
"""Build the rejected V24 Crop-YARN branch package."""

from __future__ import annotations

import base64
import hashlib
import json
import sys
import tarfile
import zlib
from pathlib import Path


HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "v21_top_meta_moe" / "main.py"
sys.path.insert(0, str(HERE.parent / "v21_top_meta_moe"))
from top_route_panel import route_actions


def payload(value) -> str:
    return repr(base64.b85encode(zlib.compress(json.dumps(value, separators=(",", ":")).encode(), 9)).decode())


def main() -> int:
    crop_yarn = route_actions("crop_yarn")
    appendix = f'''

# --- V24 rejected branch: Crop Dusta YARN expert at step 216 ---
_V24_CROP_YARN = json.loads(zlib.decompress(base64.b85decode({payload(crop_yarn)})).decode())
_V24_STATE = {{0: {{"last": -1, "first_shop": None}}, 1: {{"last": -1, "first_shop": None}}}}
__version__ = "v24-crop-yarn-step216-rejected-rc1"


del agent
def agent(obs, configuration=None):
    del configuration
    global _ACTIONS
    seat = _seat(obs)
    step = int(_get(obs, "step", int(_get(obs, "day", 0) or 0) * 24 + int(_get(obs, "hour", 0) or 0)) or 0)
    state = _V24_STATE[seat]
    if step == 0 or step < int(state.get("last", -1)):
        state.clear()
        state.update(last=step, first_shop=None)
    state["last"] = step
    shops = list(_get(_get(obs, "town", {{}}) or {{}}, "unlocked_shops", []) or [])
    if state.get("first_shop") is None and step >= 72 and shops:
        state["first_shop"] = str(shops[0])
    first = str(state.get("first_shop") or "")
    if step >= 216 and first == "YARN_STORE":
        _ACTIONS = _V24_CROP_YARN
    elif step >= 216 and first != "YARN_STORE":
        _ACTIONS = _V21_LUCASKNA_ROUTE
    else:
        _ACTIONS = _V19_ROUTES["yarn" if first == "YARN_STORE" else "default"]
    action = _V19_CORE(obs)
    action = _v20_delay_sales(obs, action, step)
    action = _cap_fixed_purchases(obs, action, _V19_PROXY)
    return _fail_closed_units(obs, action)
'''
    target = HERE / "main.py"
    target.write_text(BASE.read_text(encoding="utf-8") + appendix, encoding="utf-8")
    archive = HERE / "submission.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(target, arcname="main.py")
    manifest = {
        "candidate": "V24 Crop-YARN targeted expert rejected RC1",
        "status": "LOCAL_PROCESS_VERSION_REJECTED_STATE_INCOMPATIBLE",
        "parent": "V21 top-meta hierarchical MoE",
        "main_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "archive_bytes": archive.stat().st_size,
        "development": {
            "models": 5, "seeds": [98800, 98831], "cells": 320,
            "impacted_cells": 28, "score_uplift_pp": -6.875,
            "target_shop_uplift_pp": -78.57142857142857,
            "positive_zero_negative": [0, 298, 22], "guardrail_pass": False,
        },
    }
    (HERE / "submission_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
