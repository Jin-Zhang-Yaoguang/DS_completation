"""构建 v50 main.py:fam_F 前缀(0..71)+ t=72 两级路由(市场指纹优先,shop 表兜底)+ v41 武器层。
尾部候选:F(fam_F 本尊,镜像收割)/ rb(rb7925)/ c0(cand_0)。
市场指纹(t<=32 累积,均为公开观测):
  dw0=t0→t1 WHEAT 库存变化, dw1=t1→t2, d28=t28→t29..t32 窗口最小跳变
  规则(先特异后一般):
    -30<=dw0<=-24 且 12<=dw1<=20  -> "F"   (对手 13/8 同款 => 镜像,LEAD 收割)
    dw0<=-31                      -> "rb"  (pert_1/Andrey/keiz 大扰动族)
    |dw0+14|<=3 且 d28<=-2        -> "F"   (OceanMix 特征: t28 对手卖麦)
    否则 -> shop 表
"""
import sys, json, zlib, base64
from pathlib import Path

HERE = Path(__file__).resolve().parent
TAPES = HERE.parent / "v16_online_fidelity" / "tapes"
V41 = HERE.parent / "v46_fert_fill" / "main.py"

F = json.load(open(TAPES / "fam_F_new.json"))["actions"]
R = json.load(open(TAPES / "rb_7925cb146f.json"))["actions"]
C0 = json.load(open(TAPES / "cand_0_ec979a.json"))["actions"]
FE = json.load(open(TAPES / "rb_fed85a15a6.json"))["actions"]
B8 = json.load(open(TAPES / "rb_837669b4a0.json"))["actions"]
A8 = json.load(open(TAPES / "rb_84a8a63442.json"))["actions"]
CUT = 72
tapes = {"F": F, "rb": F[:CUT] + R[CUT:], "c0": F[:CUT] + C0[CUT:],
         "fe": F[:CUT] + FE[CUT:], "b8": F[:CUT] + B8[CUT:], "a8": F[:CUT] + A8[CUT:]}

SHOP_TABLE = {"BAKERY": "rb", "BRUNCH_SPOT": "c0", "FARMERS_MARKET": "c0",
              "ICE_CREAM_SHOP": "c0", "PET_CAFE": "rb", "PIZZA_SHOP": "rb",
              "SMOOTHIE_SHOP": "c0", "YARN_STORE": "rb"}


def pack(actions):
    raw = json.dumps(actions, separators=(",", ":")).encode()
    return base64.b85encode(zlib.compress(raw, 9)).decode()


packed = ",\n    ".join(f'"{k}": json.loads(zlib.decompress(base64.b85decode("{pack(v)}")).decode())'
                        for k, v in tapes.items())

head = f'''"""v52 five-tail router + V46 fert fill: fam_F prefix + t=72 two-level latch (market fp > shop table) + v41 weapon layers."""
import json, zlib, base64

_TAPES = {{
    {packed},
}}
_SHOP_TABLE = {json.dumps(SHOP_TABLE)}
_DEFAULT = "rb"
_SEL = {{}}
_MKT = {{}}
_ACTIONS = _TAPES[_DEFAULT]
_LOW_ROUTE_ACTIONS = _ACTIONS
_HIGH_ROUTE_ACTIONS = _ACTIONS
_selected_route = "v53e_table_a8"


def _mkt_route(m):
    dw0 = m.get(1, 0) - m.get(0, 0) if 0 in m and 1 in m else None
    dw1 = m.get(2, 0) - m.get(1, 0) if 1 in m and 2 in m else None
    if dw0 is None or dw1 is None:
        return None
    if -30 <= dw0 <= -24 and 12 <= dw1 <= 20:
        return "a8"
    if dw0 <= -31:
        return "rb"
    d28 = m[29] - m[28] if 28 in m and 29 in m else 0
    if abs(dw0 + 14) <= 3 and abs(dw1 - 3) <= 3 and d28 <= -2:
        return "F"
    dw2 = m.get(3, 0) - m.get(2, 0) if 2 in m and 3 in m else 0
    if abs(dw0 + 14) <= 3 and dw2 >= 2:
        return "fe"
    return None


def agent(obs, configuration=None):
    global _ACTIONS
    day = int(obs.get("day", 0) or 0)
    hour = int(obs.get("hour", 0) or 0)
    t = day * 24 + hour
    seat = obs.get("player", 0)
    if t == 0:
        _SEL.pop(seat, None)
        _MKT[seat] = {{}}
    try:
        if t <= 33 and seat in _MKT:
            _MKT[seat][t] = int(((obs.get("market") or {{}}).get("inventory") or {{}}).get("WHEAT", 0))
    except Exception:
        pass
    if seat not in _SEL and t >= 72:
        sel = None
        try:
            sel = _mkt_route(_MKT.get(seat) or {{}})
        except Exception:
            sel = None
        if sel is None:
            try:
                shops = (obs.get("town") or {{}}).get("unlocked_shops") or []
                first = shops[0] if shops else None
                if isinstance(first, dict):
                    first = first.get("name")
                sel = _SHOP_TABLE.get(str(first), _DEFAULT) if first else _DEFAULT
            except Exception:
                sel = _DEFAULT
        _SEL[seat] = sel
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
out = HERE / "dist_v53e"
out.mkdir(exist_ok=True)
(out / "main.py").write_text(head + "\n\n" + tail)
compile((out / "main.py").read_text(), "main.py", "exec")
print(f"built dist_v53e/main.py size={len((out/'main.py').read_text())}")
