#!/usr/bin/env python3
"""Build the standalone V19 step-360 hierarchical MoE submission."""

from __future__ import annotations

import base64
import hashlib
import inspect
import json
import tarfile
import zlib
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
BASE = PROJECT / "model" / "v1_adaptive_market" / "main.py"


def payload(value) -> str:
    raw = json.dumps(value, separators=(",", ":")).encode()
    return repr(base64.b85encode(zlib.compress(raw, 9)).decode())


def main() -> int:
    import sys
    sys.path.insert(0, str(HERE))
    import hierarchical_policy as policy

    parent = policy.PARENT
    helpers = "\n".join(inspect.getsource(function) for function in (
        parent._fail_closed_units,
        parent._fib,
        parent._cap_fixed_purchases,
    ))
    route_payloads = ",\n".join(
        f'    {name!r}: json.loads(zlib.decompress(base64.b85decode({payload(actions)})).decode())'
        for name, actions in policy._ROUTES.items()
    )
    appendix = f'''\n\n# --- V19 hierarchical MoE: safe V17 prefix + step-360 route suffix ---
_V19_ROUTES = {{
{route_payloads}
}}
_SEED_COST = {parent._SEED_COST!r}
_ANIMAL_COST = {parent._ANIMAL_COST!r}
_MOVES = {parent._MOVES!r}
{helpers}
class _V19Proxy:
    _market_price = staticmethod(_market_price)
_V19_PROXY = _V19Proxy()
_V19_CORE = _CORE_AGENT
_V19_STATE = {{0: {{"last": -1, "route": None}}, 1: {{"last": -1, "route": None}}}}
_V19_ROUTER_STEP = 72
_V19_SUFFIX_STEP = 360
__version__ = "v19-hierarchical-moe-step360-rc1"

del agent
def agent(obs, configuration=None):
    del configuration
    global _ACTIONS
    seat = _seat(obs)
    step = int(_get(obs, "step", int(_get(obs, "day", 0) or 0) * 24 + int(_get(obs, "hour", 0) or 0)) or 0)
    state = _V19_STATE[seat]
    if step == 0 or step < int(state.get("last", -1)):
        state.clear()
        state.update(last=step, route=None)
    state["last"] = step
    if state.get("route") is None and step >= _V19_ROUTER_STEP:
        town = _get(obs, "town", {{}}) or {{}}
        shops = list(_get(town, "unlocked_shops", []) or [])
        state["route"] = "yarn" if shops and str(shops[0]) == "YARN_STORE" else "default"
    if state.get("route") == "default" and step >= _V19_SUFFIX_STEP:
        state["route"] = "bakery_brunch"
    _ACTIONS = _V19_ROUTES[str(state.get("route") or "default")]
    action = _V19_CORE(obs)
    action = _cap_fixed_purchases(obs, action, _V19_PROXY)
    return _fail_closed_units(obs, action)
'''
    target = HERE / "main.py"
    target.write_text(BASE.read_text(encoding="utf-8") + appendix, encoding="utf-8")
    archive = HERE / "submission.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(target, arcname="main.py")
    manifest = {
        "candidate": "V19 hierarchical MoE step-360 RC1",
        "status": "OFFLINE_QUALIFIED_PACKAGE_QA_PENDING",
        "parent": "V17 top complete portfolio RC1",
        "main_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "archive_bytes": archive.stat().st_size,
        "routes": {name: f"{team}::{episode}" for name, (team, episode) in policy.ROUTE_SOURCES.items()},
        "router_step": policy.ROUTER_STEP,
        "suffix_switch_step": 360,
        "routing": "YARN_STORE keeps yarn; all other shops use default through step359 and bakery_brunch from step360",
        "confirmation": {
            "games_each": 1792,
            "score_uplift_pp": 1.7857142857142856,
            "score_uplift_ci95_pp": [0.6138392857142857, 3.180803571428571],
            "positive_zero_negative": [32, 1760, 0],
        },
    }
    (HERE / "submission_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
