"""V31：把 V25 假做市的意外机制显式化——高价品择时卖出（低价拦截延后，回升放行全卖）。
同时移除非法买单（BUY_PRODUCT 仅 WHEAT/FERTILIZER 合法）。基于 V26-a30 重构 MM 段。"""
from pathlib import Path
HERE = Path(__file__).resolve().parent
src = (HERE.parent / "v26_f_base" / "variant_a30.py").read_text()
# 定位并替换整个 V25 MM 段（从标记行到文件尾的 kaggriculture_agent_v25）
mark = "# ==================== V25 market maker (appended) ===================="
head = src[:src.index(mark)]
NEW = mark + '''
# V31 重写：显式择时卖出（原假做市的非法买单已移除）
_MM_BASE = {"STRAWBERRY": 120, "MILK": 160, "WOOL": 200, "MELON": 250}
_MM_STATE = {}
import os as _os
try:
    _MM_CFG = __import__("json").loads(_os.environ.get("MM_PARAMS", "{}"))
except Exception:
    _MM_CFG = {}
_MM_HOLD_FRAC = float(_MM_CFG.get("hold", 0.80))    # 价格低于基准 80%：拦截该品卖单延后
_MM_GO_FRAC = float(_MM_CFG.get("go", 0.93))        # 回升到 93%：放行并全量卖出
_MM_MAX_HOLD = int(_MM_CFG.get("max_hold", 24))     # 最多延后 24 步（逃生阀）


def _mm_layer(obs, act, seat):
    day = int(obs.get("day", 0)); hour = int(obs.get("hour", 0)); t = day * 24 + hour
    st = _MM_STATE.setdefault(seat, {"hold": {}, "last": -1})
    if t <= st["last"]: st.clear(); st.update({"hold": {}, "last": -1})
    st["last"] = t
    if not (8 * 24 <= t <= 27 * 24 + 12):
        return act
    prices = (obs.get("market") or {}).get("prices") or {}
    shed = (obs.get("private") or {}).get("shed") or {}
    shed_total = sum(int(v) for v in shed.values())
    mk = [list(o) for o in (act.get("market") or []) if o]
    out = []
    for o in mk:
        if o[0] == "SELL" and len(o) >= 3 and o[1] in _MM_BASE and shed_total < 80:
            it = o[1]; pr = prices.get(it, _MM_BASE[it])
            held = st["hold"].get(it, 0)
            if pr < _MM_HOLD_FRAC * _MM_BASE[it] and held < _MM_MAX_HOLD:
                st["hold"][it] = held + 1
                continue          # 低价：拦截延后
        out.append(o)
    # 回升放行：hold 中的品价格达标 -> 全量卖出
    for it in list(st["hold"]):
        pr = prices.get(it, _MM_BASE[it])
        have = int(shed.get(it, 0))
        if have <= 0:
            st["hold"].pop(it); continue
        if (pr >= _MM_GO_FRAC * _MM_BASE[it] or st["hold"][it] >= _MM_MAX_HOLD or shed_total >= 80) and len(out) < 10:
            if not any(o[0] == "SELL" and len(o) > 1 and o[1] == it for o in out):
                out.insert(0, ["SELL", it, have])
            st["hold"].pop(it)
    act["market"] = out[:10]
    return act


_V25_PREV = kaggriculture_agent_v24


def kaggriculture_agent_v25(obs, configuration=None):
    act = _V25_PREV(obs, configuration)
    try:
        act = _mm_layer(obs, act, obs.get("player", 0))
    except Exception:
        pass
    return act
'''
(HERE / "main.py").write_text(head + NEW)
print("main.py:", len(head + NEW))
