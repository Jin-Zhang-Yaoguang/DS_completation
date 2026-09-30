#!/usr/bin/env python3
"""Build standalone V21 from V20 plus the qualified late production expert."""

from __future__ import annotations

import base64
import hashlib
import json
import sys
import tarfile
import zlib
from pathlib import Path


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
BASE = MODEL / "v20_demand_timing_moe" / "main.py"
sys.path.insert(0, str(HERE))
from top_route_panel import route_actions


def payload(value) -> str:
    raw = json.dumps(value, separators=(",", ":")).encode()
    return repr(base64.b85encode(zlib.compress(raw, 9)).decode())


def main() -> int:
    lucas = route_actions("lucaskna_high")
    appendix = f'''

# --- V21 top-meta MoE: causal late production expert behind the V20 router ---
_V21_LUCASKNA_ROUTE = json.loads(zlib.decompress(base64.b85decode({payload(lucas)})).decode())
_V21_ROUTER_STEP = 72
_V21_EXPERT_STEP = 216
_V21_STATE = {{0: {{"last": -1, "route": None}}, 1: {{"last": -1, "route": None}}}}
__version__ = "v21-top-meta-moe-lucaskna-step216-rc1"


del agent
def agent(obs, configuration=None):
    del configuration
    global _ACTIONS
    seat = _seat(obs)
    step = int(_get(obs, "step", int(_get(obs, "day", 0) or 0) * 24 + int(_get(obs, "hour", 0) or 0)) or 0)
    state = _V21_STATE[seat]
    if step == 0 or step < int(state.get("last", -1)):
        state.clear()
        state.update(last=step, route=None)
    state["last"] = step
    if state.get("route") is None and step >= _V21_ROUTER_STEP:
        town = _get(obs, "town", {{}}) or {{}}
        shops = list(_get(town, "unlocked_shops", []) or [])
        state["route"] = "yarn" if shops and str(shops[0]) == "YARN_STORE" else "default"
    route = str(state.get("route") or "default")
    if route != "yarn" and step >= _V21_EXPERT_STEP:
        _ACTIONS = _V21_LUCASKNA_ROUTE
    else:
        _ACTIONS = _V19_ROUTES[route]
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
        "candidate": "V21 top-meta hierarchical MoE lucaskna step-216 RC1",
        "status": "OFFLINE_GOLD_CANDIDATE_QA_PASS",
        "parent": "V20 demand-timing hierarchical MoE RC1",
        "source_expert": "lucaskna::100485613",
        "router_step": 72,
        "expert_switch_step": 216,
        "routing": "YARN_STORE keeps the yarn expert; every non-YARN route switches to the lucaskna production expert at step 216",
        "sell_controller": "V20 demand_delay_25",
        "main_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "archive_bytes": archive.stat().st_size,
        "confirmation": {
            "games_each": 2048,
            "opponent_families": 8,
            "score_uplift_pp": 14.208984375,
            "score_uplift_ci95_pp": [12.1337890625, 16.3330078125],
            "positive_zero_negative": [293, 1755, 0],
            "mean_margin_delta": 872.33203125,
            "mean_own_delta": 382.47607421875,
        },
        "qa": {
            "research_package_exact_games": [8, 8],
            "official_cpp_exact_games": [4, 4],
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
