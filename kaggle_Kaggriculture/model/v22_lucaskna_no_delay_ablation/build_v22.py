#!/usr/bin/env python3
"""Build the standalone rejected V22 no-delay ablation package."""

from __future__ import annotations

import hashlib
import json
import tarfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "v21_top_meta_moe" / "main.py"


APPENDIX = r'''

# --- V22 ablation: keep V21 production Router, remove demand-delay sells ---
_V22_STATE = {0: {"last": -1, "route": None}, 1: {"last": -1, "route": None}}
__version__ = "v22-lucaskna-step216-no-delay-ablation-rc1"


del agent
def agent(obs, configuration=None):
    del configuration
    global _ACTIONS
    seat = _seat(obs)
    step = int(_get(obs, "step", int(_get(obs, "day", 0) or 0) * 24 + int(_get(obs, "hour", 0) or 0)) or 0)
    state = _V22_STATE[seat]
    if step == 0 or step < int(state.get("last", -1)):
        state.clear()
        state.update(last=step, route=None)
    state["last"] = step
    if state.get("route") is None and step >= _V21_ROUTER_STEP:
        town = _get(obs, "town", {}) or {}
        shops = list(_get(town, "unlocked_shops", []) or [])
        state["route"] = "yarn" if shops and str(shops[0]) == "YARN_STORE" else "default"
    route = str(state.get("route") or "default")
    _ACTIONS = _V21_LUCASKNA_ROUTE if route != "yarn" and step >= _V21_EXPERT_STEP else _V19_ROUTES[route]
    action = _V19_CORE(obs)
    action = _cap_fixed_purchases(obs, action, _V19_PROXY)
    return _fail_closed_units(obs, action)
'''


def main() -> int:
    HERE.mkdir(parents=True, exist_ok=True)
    target = HERE / "main.py"
    target.write_text(BASE.read_text(encoding="utf-8") + APPENDIX, encoding="utf-8")
    archive = HERE / "submission.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(target, arcname="main.py")
    manifest = {
        "candidate": "V22 lucaskna step-216 no-delay ablation RC1",
        "status": "LOCAL_PROCESS_VERSION_REJECTED",
        "parent": "V21 top-meta hierarchical MoE RC1",
        "change": "remove V20 demand_delay_25 while preserving production Router and safe executor",
        "main_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "archive_bytes": archive.stat().st_size,
        "development": {
            "models": 12,
            "seeds": [98400, 98431],
            "games_each": 768,
            "score_uplift_vs_v21_pp": -1.4322916666666665,
            "positive_zero_negative": [0, 751, 17],
            "mean_margin_delta": -45.510416666666664,
            "mean_own_delta": -16.567708333333332,
            "guardrail_pass": False,
        },
    }
    (HERE / "submission_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
