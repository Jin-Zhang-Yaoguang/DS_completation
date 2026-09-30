"""V13 路线库：V120 守卫栈 + Tetsutani 8/30 公开的 5 条完整路线 tape（可强制指定路线）。

环境变量：
  V13_ROUTE   强制路线名（10C4S_3Q / 8C6S_3Q / 6C8S_3Q / 6C12S_4Q_FIRST_YARN / 6C12S_4Q_SECOND_YARN，
              前缀 LEGACY_ 取旧版；"v120" 表示不改动 V120 原路线）
  V13_V10RULES=1  叠加 V10 的两条规则（无毛线店晚期不买羊、乳品店<=1 不买牛）
"""
import os, re, json, zlib, base64

_HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v13_route_library"
_CORE_SRC = open(os.path.join(_HERE, "..", "v10_rule_distill", "v120_core.py")).read()
_TET_SRC = open(os.path.join(_HERE, "tetsutani_main.py")).read()

_NS = {"__name__": "v13_core"}
exec(compile(_CORE_SRC, "v120_core.py", "exec"), _NS)

_TAPES = {}
for _m in re.finditer(r"^(_(?:LEGACY_)?ACTIONS_\w+) = json\.loads\(zlib\.decompress\(base64\.b85decode\('([^']+)'\)\)", _TET_SRC, re.M):
    _TAPES[_m.group(1).replace("_ACTIONS_", "", 1).lstrip("_")] = json.loads(zlib.decompress(base64.b85decode(_m.group(2))).decode())

ROUTE = os.environ.get("V13_ROUTE", "v120")
if ROUTE != "v120":
    _tape = _TAPES[ROUTE]
    # V120 顶层每步把 _ACTIONS 设为 _V120_DISTILLED_ROUTE，覆盖它才生效
    _NS["_V120_DISTILLED_ROUTE"] = _tape
    _NS["_LOW_ROUTE_ACTIONS"] = _tape
    _NS["_HIGH_ROUTE_ACTIONS"] = _tape
    _NS["_ACTIONS"] = _tape

_ROUTE_AGENT = _NS["agent"]

_V10_R1_DAY = 10; _V10_R2_DAY = 9; _V10_R2_MAX = 1
_V10_DAIRY = ("PIZZA_SHOP", "ICE_CREAM_SHOP", "SMOOTHIE_SHOP")
_USE_V10 = os.environ.get("V13_V10RULES", "0") == "1"


def _v10_filter(obs, action):
    try:
        day = int(obs.get("day", 0) or 0)
        shops = list((obs.get("town") or {}).get("unlocked_shops") or [])
        n_dairy = sum(1 for s in shops if s in _V10_DAIRY)
        has_yarn = "YARN_STORE" in shops
        market = action.get("market") or []
        out = []
        for o in market:
            if o and o[0] == "BUY_ANIMAL" and len(o) > 1:
                if o[1] == "SHEEP" and day >= _V10_R1_DAY and not has_yarn:
                    continue
                if o[1] == "COW" and day >= _V10_R2_DAY and n_dairy <= _V10_R2_MAX:
                    continue
            out.append(o)
        action["market"] = out
    except Exception:
        pass
    return action


def agent(obs, configuration=None):
    act = _ROUTE_AGENT(obs, configuration)
    if _USE_V10:
        act = _v10_filter(obs, act)
    return act
