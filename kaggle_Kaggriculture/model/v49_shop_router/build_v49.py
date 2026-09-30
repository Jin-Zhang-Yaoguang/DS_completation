"""构建 v49 main.py:fam_F 公共前缀(0..71)+ t>=72 按首店闩锁选带 + v41 武器层原样。
用法: python build_v49.py [aggressive|conservative]
"""
import sys, json, zlib, base64
from pathlib import Path

HERE = Path(__file__).resolve().parent
TAPES = HERE.parent / "v16_online_fidelity" / "tapes"
V41 = HERE.parent / "v41_famF_glass" / "main.py"

mode = sys.argv[1] if len(sys.argv) > 1 else "aggressive"

F = json.load(open(TAPES / "fam_F_new.json"))["actions"]
R = json.load(open(TAPES / "rb_7925cb146f.json"))["actions"]
C0 = json.load(open(TAPES / "cand_0_ec979a.json"))["actions"]
CUT = 72
tape_rb = F[:CUT] + R[CUT:]
tape_c0 = F[:CUT] + C0[CUT:]

ROUTES = {
    "aggressive": {"BAKERY": "rb", "BRUNCH_SPOT": "c0", "FARMERS_MARKET": "c0",
                   "ICE_CREAM_SHOP": "c0", "PET_CAFE": "rb", "PIZZA_SHOP": "c0",
                   "SMOOTHIE_SHOP": "rb", "YARN_STORE": "rb"},
    "conservative": {"BAKERY": "rb", "BRUNCH_SPOT": "c0", "FARMERS_MARKET": "rb",
                     "ICE_CREAM_SHOP": "c0", "PET_CAFE": "rb", "PIZZA_SHOP": "rb",
                     "SMOOTHIE_SHOP": "rb", "YARN_STORE": "rb"},
}
table = ROUTES[mode]


def pack(actions):
    raw = json.dumps(actions, separators=(",", ":")).encode()
    return base64.b85encode(zlib.compress(raw, 9)).decode()


head = f'''"""v49 shop router ({mode}): fam_F prefix(0..71) + t=72 first-shop latch (rb7925 | cand_0) + v41 weapon layers."""
import json, zlib, base64

_TAPES = {{
    "rb": json.loads(zlib.decompress(base64.b85decode("{pack(tape_rb)}")).decode()),
    "c0": json.loads(zlib.decompress(base64.b85decode("{pack(tape_c0)}")).decode()),
}}
_ROUTE_TABLE = {json.dumps(table)}
_DEFAULT = "rb"
_SEL = {{}}
_ACTIONS = _TAPES[_DEFAULT]
_LOW_ROUTE_ACTIONS = _ACTIONS
_HIGH_ROUTE_ACTIONS = _ACTIONS
_selected_route = "v49_shop_router_{mode}"


def agent(obs, configuration=None):
    global _ACTIONS
    day = int(obs.get("day", 0) or 0)
    hour = int(obs.get("hour", 0) or 0)
    t = day * 24 + hour
    seat = obs.get("player", 0)
    if t == 0:
        _SEL.pop(seat, None)
    if seat not in _SEL and t >= 72:
        try:
            shops = (obs.get("town") or {{}}).get("unlocked_shops") or []
            first = shops[0] if shops else None
            if isinstance(first, dict):
                first = first.get("name")
            _SEL[seat] = _ROUTE_TABLE.get(str(first), _DEFAULT) if first else _DEFAULT
        except Exception:
            _SEL[seat] = _DEFAULT
    _ACTIONS = _TAPES[_SEL.get(seat, _DEFAULT)]
    a = _ACTIONS[t] if 0 <= t < len(_ACTIONS) else None
    if not isinstance(a, dict):
        return {{"farmer": ["PASS"], "hands": [], "market": []}}
    return {{
        "farmer": list(a.get("farmer") or ["PASS"]),
        "hands": [list(h) for h in (a.get("hands") or [])],
        "market": [list(o) for o in (a.get("market") or [])],
    }}
'''

v41 = V41.read_text()
marker = "# ==================== V17 market guard (appended) ===================="
tail = v41[v41.index(marker):]
out = HERE / "dist"
out.mkdir(exist_ok=True)
(out / "main.py").write_text(head + "\n\n" + tail)
compile((out / "main.py").read_text(), "main.py", "exec")
print(f"built dist/main.py mode={mode} size={len((out/'main.py').read_text())} bytes")
