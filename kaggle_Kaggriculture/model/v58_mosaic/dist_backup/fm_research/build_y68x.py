"""构建 y68x = y68v + 按对手开局类型选路线(FM 组合)。
用法: python build_y68x.py decision.json out_name
decision.json: {"组合A|组合B": {"heavy": rid|null, "b15": rid|null, "nowash": rid|null, "mid": rid|null}}
null = 沿用 y68v 原路由。类别由第 1 步观测到的对手现金判定(y68v 买30开局下实测):
  heavy  <2700(V38原版 2582 / 13+13 2602)
  mid    2700~2950(qq 型 2873 等)
  b15    2950~2995(V41/V42/V43 2977)
  nowash >=2995(B10 3000 / 不洗单)
"""
import sys, json, inspect
from pathlib import Path
S = Path(__file__).resolve().parent
dec = json.load(open(sys.argv[1])); out = sys.argv[2]
table = {}
for combo, m in dec.items():
    a, b = combo.split("|")
    table[(a, b)] = {k: v for k, v in m.items() if v is not None}
tail = f'''

# ==================== y68x 层:FM 组合按对手开局类型选路线 ====================
# 第 1 步观测的对手现金暴露其开局买卖量(与 seed 无关);V41 与 V43 在第 6 天前不可分,归为同类。
_Y68X_TABLE = {table!r}
_Y68X_OPP = {{}}

def _y68x_class(money):
    if money < 2700: return "heavy"
    if money < 2950: return "mid"
    if money < 2995: return "b15"
    return "nowash"

_y68x_prev_router = _IMPL.chassis.router

def _y68x_router(observation, step, state):
    try:
        player = int(_get(observation, "player", 0))
        if step == 0:
            _Y68X_OPP.pop(player, None)
        if step == 1 or (step >= 1 and player not in _Y68X_OPP):
            farms = _get(observation, "farms", []) or []
            if len(farms) >= 2:
                _Y68X_OPP[player] = _y68x_class(float(_get(farms[1 - player], "money", 3000) or 3000))
        if step >= 144 and not state.get("day6"):
            shops = tuple((_get(_get(observation, "town", {{}}), "unlocked_shops", []) or [])[:2])
            rid = (_Y68X_TABLE.get(shops) or {{}}).get(_Y68X_OPP.get(player))
            if rid is not None and rid in _IMPL.chassis.routes:
                state["route"] = rid
                state["day6"] = True
                return rid
    except Exception:
        pass
    return _y68x_prev_router(observation, step, state)

_IMPL.chassis.router = _y68x_router
_Y68X_ENTRY = _Y68U_ENTRY
'''
src = (S / "y68v_main.py").read_text() + tail
(S / f"{out}_main.py").write_text(src)
ns = {}; exec(src, ns)
last = [k for k, v in ns.items() if callable(v) and not inspect.isclass(v) and not k.startswith("__")][-1]
assert last == "_Y68X_ENTRY", last
print(f"{out}: 尾 callable {last};覆盖组合 {len(table)} 个;路线均存在 {all(r in ns['_IMPL'].chassis.routes for m in table.values() for r in m.values())}")
