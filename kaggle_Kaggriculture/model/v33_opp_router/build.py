"""V33 对手条件路由：t1 按对手开局扰动量分类，切换克制带。
LOW=F 带（对新代/无扰动），HIGH=keiz 带（碾老代扰动 53 型）。基于 V32 清洁版重构。"""
import json, zlib, base64
from pathlib import Path
HERE = Path(__file__).resolve().parent
M = HERE.parent
src = (M / "v32_clean_mm" / "main.py").read_text()
K = json.load(open(M / "v16_online_fidelity" / "tapes" / "top_keiz_82acad.json"))["actions"]
kblob = base64.b85encode(zlib.compress(json.dumps(K).encode())).decode()

# 1) HIGH 表换成 keiz 带（在 V26 的 tape_swap 段之后追加覆盖）
anchor = "_ACTIONS = _F_ACTIONS"
assert anchor in src
inject = anchor + f'''
_KEIZ_ACTIONS = json.loads(zlib.decompress(base64.b85decode("{kblob}")).decode())
_HIGH_ROUTE_ACTIONS = _KEIZ_ACTIONS   # HIGH = 对轰特化（碾老代扰动）
'''
src = src.replace(anchor, inject, 1)

# 2) route 判据重写：yarn@168 -> 对手扰动分类@t1
old = '''def _selected_route(obs):
    seat = _seat(obs)
    step = _route_step(obs)
    state = _ROUTE_STATE[seat]
    if step == 0 or step < int(state.get("last_step", -1)):
        state = {"last_step": step, "shops": (), "expert": None}
        _ROUTE_STATE[seat] = state
    state["last_step"] = step
    if step <= _ROUTE_DECISION_STEP:
        state["shops"] = _route_shops(obs)
    if state.get("expert") is None and step >= _ROUTE_DECISION_STEP:
        shops = tuple(state.get("shops") or ())
        dominated = (
            len(shops) >= 2
            and shops[0] == "ICE_CREAM_SHOP"
            and shops[1] == "YARN_STORE"
        )
        state["expert"] = (
            "high" if "YARN_STORE" in shops and not dominated else "low"
        )
    return str(state.get("expert") or "low")'''
new = '''def _selected_route(obs):
    seat = _seat(obs)
    step = _route_step(obs)
    state = _ROUTE_STATE[seat]
    if step == 0 or step < int(state.get("last_step", -1)):
        state = {"last_step": step, "shops": (), "expert": None}
        _ROUTE_STATE[seat] = state
    state["last_step"] = step
    t_dh = int(_get(obs, "day", 0) or 0) * 24 + int(_get(obs, "hour", 0) or 0)
    if state.get("expert") is None and t_dh >= 1:
        # t1: 对手开局扰动分类（市场小麦库存缺口 - 我方 t0 买入 53/30）
        inv_w = ((obs.get("market") or {}).get("inventory") or {}).get("WHEAT", 10000)
        my_t0 = 30 + 13    # GUARD 扰动 30 + F 带自买 13
        opp_bought = (10000 - inv_w) - my_t0
        state["expert"] = "high" if opp_bought >= 40 else "low"
    return str(state.get("expert") or "low")'''
assert old in src, "route anchor"
src = src.replace(old, new)
(HERE / "main.py").write_text(src)
print("main.py:", len(src))
