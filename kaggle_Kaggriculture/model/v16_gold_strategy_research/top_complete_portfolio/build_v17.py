#!/usr/bin/env python3
"""Build a single-file V17 candidate from the audited portfolio router."""

from __future__ import annotations

import base64
import hashlib
import inspect
import json
import tarfile
import zlib
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "kaggle_Kaggriculture" / "model" / "v1_adaptive_market" / "main.py"


def payload(value) -> str:
    raw = json.dumps(value, separators=(",", ":")).encode()
    return repr(base64.b85encode(zlib.compress(raw, 9)).decode())


def main() -> int:
    import sys
    sys.path.insert(0, str(HERE))
    import portfolio_policy as policy
    appendix = f'''\n\n# --- V17 complete-route public-shop portfolio ---
_PORT_DEFAULT = json.loads(zlib.decompress(base64.b85decode({payload(policy._DEFAULT_ACTIONS)})).decode())
_PORT_YARN = json.loads(zlib.decompress(base64.b85decode({payload(policy._YARN_ACTIONS)})).decode())
_SEED_COST = {policy._SEED_COST!r}
_ANIMAL_COST = {policy._ANIMAL_COST!r}
_MOVES = {policy._MOVES!r}
{inspect.getsource(policy._fail_closed_units)}
{inspect.getsource(policy._fib)}
{inspect.getsource(policy._cap_fixed_purchases)}
_PORT_STATE = {{0: {{"last": -1, "choice": None}}, 1: {{"last": -1, "choice": None}}}}
_PORT_CORE = _CORE_AGENT
__version__ = "v17-top-complete-portfolio-rc1"

del agent
def agent(obs, configuration=None):
    del configuration
    global _ACTIONS
    seat = _seat(obs)
    step = int(_get(obs, "step", int(_get(obs, "day", 0) or 0) * 24 + int(_get(obs, "hour", 0) or 0)) or 0)
    state = _PORT_STATE[seat]
    if step == 0 or step < int(state.get("last", -1)):
        state.update(last=step, choice=None)
    state["last"] = step
    if state.get("choice") is None and step >= 72:
        town = _get(obs, "town", {{}}) or {{}}
        shops = list(_get(town, "unlocked_shops", []) or [])
        state["choice"] = "yarn" if shops and str(shops[0]) == "YARN_STORE" else "default"
    _ACTIONS = _PORT_YARN if state.get("choice") == "yarn" else _PORT_DEFAULT
    action = _PORT_CORE(obs)
    action = _cap_fixed_purchases(obs, action, globals())
    return _fail_closed_units(obs, action)
'''
    # _cap_fixed_purchases expects an object with _market_price; globals() is a
    # dict, so use a tiny stable proxy in the generated file.
    appendix = appendix.replace("action = _cap_fixed_purchases(obs, action, globals())", "action = _cap_fixed_purchases(obs, action, _PORT_PROXY)")
    appendix = appendix.replace('_PORT_CORE = _CORE_AGENT', '_PORT_CORE = _CORE_AGENT\nclass _PortProxy:\n    _market_price = staticmethod(_market_price)\n_PORT_PROXY = _PortProxy()')
    target = HERE / "main.py"
    target.write_text(BASE.read_text(encoding="utf-8") + appendix, encoding="utf-8")
    archive = HERE / "submission.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(target, arcname="main.py")
    manifest = {
        "candidate": "V17 top complete portfolio RC1",
        "main_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "archive_bytes": archive.stat().st_size,
        "routes": ["tyz123456::99609968", "Kronki::99596430"],
        "decision": "first public shop at step72; YARN_STORE selects Kronki, otherwise tyz",
    }
    (HERE / "submission_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
