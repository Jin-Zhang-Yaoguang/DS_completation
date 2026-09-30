"""V33 clean：V120 核 + F/keiz 双带 + 对手条件路由 + 护栏/扰动/fill/择时，全显式命名单链。"""
import json, zlib, base64
from pathlib import Path
HERE = Path(__file__).resolve().parent
M = HERE.parent
V120 = (M / "v120_hierarchical_top5_distillation" / "main.py").read_text()
F = json.load(open(M / "v16_online_fidelity" / "tapes" / "fam_F_new.json"))["actions"]
K = json.load(open(M / "v16_online_fidelity" / "tapes" / "top_keiz_82acad.json"))["actions"]
fb = base64.b85encode(zlib.compress(json.dumps(F).encode())).decode()
kb = base64.b85encode(zlib.compress(json.dumps(K).encode())).decode()

LAYER = f'''

# ==================== V33 clean stack ====================
_F_TAPE = json.loads(zlib.decompress(base64.b85decode("{fb}")).decode())
_K_TAPE = json.loads(zlib.decompress(base64.b85decode("{kb}")).decode())
_LOW_ROUTE_ACTIONS = _F_TAPE
_HIGH_ROUTE_ACTIONS = _K_TAPE
_ACTIONS = _F_TAPE
_V33_ROUTE_AGENT = agent          # V120 总装链（含全部守卫）
''' + '''

def _v33_selected_route(obs):
    """t>=1 按对手开局扰动量分类：老代(>=40)→keiz 带碾压；否则 F 带。"""
    seat = obs.get("player", 0)
    st = _ROUTE_STATE[seat]
    t = int(obs.get("day", 0)) * 24 + int(obs.get("hour", 0))
    if t == 0:
        st["expert"] = None
    if st.get("expert") is None and t >= 1:
        inv_w = ((obs.get("market") or {}).get("inventory") or {}).get("WHEAT", 10000)
        opp_bought = (10000 - inv_w) - 43     # 我方 t0 = K 带完整扰动 43
        st["expert"] = "low" if 15 <= opp_bought <= 39 else "high"   # 新代20型→F；其余→K完整线
    return str(st.get("expert") or "high")


_V33_ORDER = {"BUY_ANIMAL": 0, "HIRE": 1, "BUY_SEED": 2, "BUY_PRODUCT": 3}
_V33_EXP = {}
_V33_MM = {}
_MMB = {"STRAWBERRY": 120, "MILK": 160, "WOOL": 200, "MELON": 250}


def _v33_count_animals(obs, seat):
    cows = sheep = 0
    farm = (obs.get("farms") or [])[seat]
    for row in farm.get("tiles") or []:
        for x in row or []:
            if isinstance(x, dict):
                a = x.get("animal")
                if isinstance(a, dict):
                    if a.get("kind") == "COW": cows += 1
                    elif a.get("kind") == "SHEEP": sheep += 1
                elif x.get("kind") == "COW": cows += 1
                elif x.get("kind") == "SHEEP": sheep += 1
    shed = (obs.get("private") or {}).get("shed") or {}
    cows += int(shed.get("COW", 0)); sheep += int(shed.get("SHEEP", 0))
    for i in (obs.get("private") or {}).get("inventories") or []:
        cows += int(i.get("COW", 0)); sheep += int(i.get("SHEEP", 0))
    return cows, sheep


def _v33_play_k(obs, _t):
    _a = _K_TAPE[_t] if _t < len(_K_TAPE) else {"farmer": ["PASS"], "hands": [], "market": []}
    act = {"farmer": list(_a.get("farmer") or ["PASS"]),
           "hands": [list(h) for h in (_a.get("hands") or [])],
           "market": [list(o) for o in (_a.get("market") or [])]}
    _exp = len((obs.get("farms") or [{}])[obs.get("player", 0)].get("hands") or [])
    while len(act["hands"]) < _exp: act["hands"].append(["PASS"])
    act["hands"] = act["hands"][:_exp]
    return act


def kaggriculture_agent_v33(obs, configuration=None):
    global _LOW_ROUTE_ACTIONS, _HIGH_ROUTE_ACTIONS, _ACTIONS
    _t = int(obs.get("day", 0)) * 24 + int(obs.get("hour", 0))
    route = _v33_selected_route(obs)
    if _t <= 1 or route == "high":
        act = _v33_play_k(obs, _t)     # 默认线：keiz 完整带（含 43 扰动开局）
    else:
        _LOW_ROUTE_ACTIONS = _F_TAPE; _HIGH_ROUTE_ACTIONS = _F_TAPE; _ACTIONS = _F_TAPE
        act = _V33_ROUTE_AGENT(obs, None)
    try:
        seat = obs.get("player", 0)
        day = int(obs.get("day", 0)); hour = int(obs.get("hour", 0)); t = day * 24 + hour
        market = [list(o) for o in (act.get("market") or []) if o]
        # 2) 护栏：开局两步重排 + 资产守卫
        exp = _V33_EXP.setdefault(seat, {"COW": 0, "SHEEP": 0, "bought": 0})
        if t == 0:
            exp.update({"COW": 0, "SHEEP": 0, "bought": 0})
        for o in market:
            if o and o[0] == "BUY_ANIMAL" and len(o) >= 3 and str(o[1]) in ("COW", "SHEEP"):
                exp[str(o[1])] += int(o[2])
        if t <= 1 and market:
            market.sort(key=lambda o: _V33_ORDER.get(str(o[0]), 9))
        if 1 <= day <= 2 and exp["bought"] < 4:
            cows, sheep = _v33_count_animals(obs, seat)
            money = (obs.get("farms") or [])[seat].get("money", 0)
            for kind, have in (("SHEEP", sheep), ("COW", cows)):
                if exp.get(kind, 0) - have > 0 and money >= 500 and len(market) < 10:
                    market.insert(0, ["BUY_ANIMAL", kind, 1]); exp["bought"] += 1
                    break
        # 4) 择时卖出 nudge（原假做市的显式等价：不拦 base，只在回升时追加）
        if 10 * 24 <= t <= 27 * 24:
            st = _V33_MM.setdefault(seat, {"pos": {}})
            prices = (obs.get("market") or {}).get("prices") or {}
            shed = (obs.get("private") or {}).get("shed") or {}
            selling = {o[1] for o in market if o and o[0] == "SELL" and len(o) > 1}
            money = float((obs.get("farms") or [])[seat].get("money", 0) or 0)
            room = 100 - sum(int(v) for v in shed.values())
            for it, base0 in _MMB.items():
                pr = prices.get(it, base0)
                pos = int(st["pos"].get(it, 0))
                if pos > 0 and pr >= 0.93 * base0 and int(shed.get(it, 0)) >= 1 and len(market) < 10:
                    q = min(pos, int(shed.get(it, 0)))
                    market.insert(0, ["SELL", it, q]); st["pos"][it] = pos - q
                    continue
                if pr <= 0.80 * base0 and it not in selling and pos < 24 and money > 3000 and room > 12:
                    lot = min(8, int((money * 0.25) // max(1, pr)), room - 10)
                    if lot >= 3: st["pos"][it] = pos + lot   # 仅状态触发器，不挂废单
            act["market"] = market[:10]
            return act
        act["market"] = market[:10]
    except Exception:
        pass
    return act
'''
(HERE / "main_clean.py").write_text(V120 + LAYER)
print("main_clean.py:", len(V120 + LAYER))
