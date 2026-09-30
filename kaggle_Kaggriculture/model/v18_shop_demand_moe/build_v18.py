#!/usr/bin/env python3
"""Build standalone V18 main.py and submission archive."""

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
    import shop_demand_policy as policy

    helpers = "\n".join(inspect.getsource(function) for function in (
        policy._PARENT._fail_closed_units,
        policy._PARENT._fib,
        policy._PARENT._cap_fixed_purchases,
        policy._shop_demand,
        policy._target_quantities,
        policy._update_demand_state,
        policy._apply_demand_overlay,
    ))
    route_payloads = ",\n".join(
        f'    {name!r}: json.loads(zlib.decompress(base64.b85decode({payload(actions)})).decode())'
        for name, actions in policy._ROUTES.items()
    )
    appendix = f'''\n\n# --- V18 public-shop demand eight-expert router ---
_V18_ROUTES = {{
{route_payloads}
}}
SHOP_PRODUCTS = {policy.SHOP_PRODUCTS!r}
ROUTE_REFERENCE_SHOPS = {policy.ROUTE_REFERENCE_SHOPS!r}
EXPERTS = {policy.EXPERTS!r}
DEMAND_TARGET_INITIALIZERS = {policy.DEMAND_TARGET_INITIALIZERS!r}
ROUTER_STEP = {policy.ROUTER_STEP}
UPDATE_STEPS = {policy.UPDATE_STEPS!r}
DEFER_CAP_PER_DEMAND = {policy.DEFER_CAP_PER_DEMAND}
DEFER_STOP_STEP = {policy.DEFER_STOP_STEP}
DEFER_EXCLUDED_ITEMS = {policy.DEFER_EXCLUDED_ITEMS!r}
_SEED_COST = {policy._PARENT._SEED_COST!r}
_ANIMAL_COST = {policy._PARENT._ANIMAL_COST!r}
_MOVES = {policy._PARENT._MOVES!r}
{helpers}
_V18_CORE = _CORE_AGENT
class _V18Proxy:
    _market_price = staticmethod(_market_price)
_V18_PROXY = _V18Proxy()
_V18_STATE = {{
    0: {{"last": -1, "expert": None, "route": "default", "update_stage": 0, "due_step": -1, "due": {{}}}},
    1: {{"last": -1, "expert": None, "route": "default", "update_stage": 0, "due_step": -1, "due": {{}}}},
}}
__version__ = "v18-shop-demand-moe-rc2"

del agent
def agent(obs, configuration=None):
    del configuration
    global _ACTIONS
    seat = _seat(obs)
    step = int(_get(obs, "step", int(_get(obs, "day", 0) or 0) * 24 + int(_get(obs, "hour", 0) or 0)) or 0)
    state = _V18_STATE[seat]
    if step == 0 or step < int(state.get("last", -1)):
        state.clear()
        state.update(last=step, expert=None, route="default", update_stage=0, due_step=-1, due={{}})
    state["last"] = step
    town = _get(obs, "town", {{}}) or {{}}
    shops = tuple(str(value) for value in (_get(town, "unlocked_shops", []) or []))
    if state.get("expert") is None and step >= ROUTER_STEP:
        expert = shops[0] if shops and shops[0] in EXPERTS else "SMOOTHIE_SHOP"
        state["expert"] = expert
        state["route"] = EXPERTS[expert]["route"]
    _update_demand_state(state, shops, step)
    _ACTIONS = _V18_ROUTES[str(state.get("route") or "default")]
    action = _V18_CORE(obs)
    action = _cap_fixed_purchases(obs, action, _V18_PROXY)
    action = _fail_closed_units(obs, action)
    return _apply_demand_overlay(obs, action, state, step)
'''
    target = HERE / "main.py"
    target.write_text(BASE.read_text(encoding="utf-8") + appendix, encoding="utf-8")
    archive = HERE / "submission.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(target, arcname="main.py")
    manifest = {
        "candidate": "V18 shop-demand eight-expert Router RC2",
        "status": "NOT_PROMOTED_PENDING_FROZEN_TEST",
        "parent": "V17 top complete portfolio RC1",
        "main_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "archive_bytes": archive.stat().st_size,
        "experts": list(policy.EXPERTS),
        "routes": {name: f"{team}::{episode}" for name, (team, episode) in policy.ROUTE_SOURCES.items()},
        "router_step": policy.ROUTER_STEP,
        "demand_update_steps": list(policy.UPDATE_STEPS),
        "defer_cap_per_demand": policy.DEFER_CAP_PER_DEMAND,
        "defer_excluded_items": list(policy.DEFER_EXCLUDED_ITEMS),
    }
    (HERE / "submission_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
