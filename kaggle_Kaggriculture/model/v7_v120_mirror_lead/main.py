"""V7：精确 V120（执行链原样）+ 一回合 premium 前移覆盖层。

镜像对局在 lockstep 结算下是平局；先一回合卖出的一方拿更高单价。
覆盖层：在回合 t，若原始 tape 的 t+1 有 premium 卖单、本回合无该品需求 tick、shed 有货，
则本回合前插同量 SELL，并在后续 V120 输出中扣除等量（总量守恒）。
参数（环境变量）：V7_LEAD_K（提前回合数，默认 1）、V7_MODE（no_tick|always）、V7_ITEMS。
"""
import importlib.util, os

HERE = os.path.dirname(os.path.abspath(__file__))
V120_PATH = os.path.join(HERE, "..", "v120_hierarchical_top5_distillation", "main.py")

SHOPS = {
    "BAKERY": ["EGG", "WHEAT"], "PIZZA_SHOP": ["MILK", "TOMATO", "WHEAT"],
    "BRUNCH_SPOT": ["EGG", "WHEAT", "STRAWBERRY"], "YARN_STORE": ["WOOL"],
    "ICE_CREAM_SHOP": ["STRAWBERRY", "MILK", "WHEAT"], "PET_CAFE": ["CARROT"],
    "SMOOTHIE_SHOP": ["STRAWBERRY", "MILK"], "FARMERS_MARKET": ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY"],
}
LEAD_K = int(os.environ.get("V7_LEAD_K", "1"))
MODE = os.environ.get("V7_MODE", "no_tick")
ITEMS = tuple(os.environ.get("V7_ITEMS", "WOOL,MILK,STRAWBERRY,MELON,CARROT").split(","))
UNTIL = int(os.environ.get("V7_UNTIL", "700"))


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_v120 = _load_module("v7_v120_core", V120_PATH)
_TAPE = _v120._V120_DISTILLED_ROUTE
_S = {}


def agent(obs, configuration=None):
    try:
        base = _v120.agent(obs, configuration)     # 精确 V120
    except Exception:
        farms = obs.get("farms") or []
        player = obs.get("player", 0)
        n = len(farms[player].get("hands") or []) if farms and player < len(farms) else 0
        return {"farmer": ["PASS"], "hands": [["PASS"]] * n, "market": []}
    try:
        player = obs.get("player", 0)
        turn = int(obs.get("day", 0)) * 24 + int(obs.get("hour", 0))
        st = _S.get(player)
        if st is None or turn <= st["last"]:
            st = {"last": -1, "shifted": {}}
            _S[player] = st
        st["last"] = turn
        market = [list(m) for m in (base.get("market") or [])]
        shed = (obs.get("private") or {}).get("shed") or {}
        shops = list((obs.get("town") or {}).get("unlocked_shops") or [])

        # 不做扣除记账：V120 执行器自身按 shed 实际库存截断卖单，再扣一次会双重扣减
        DEBT = os.environ.get("V7_DEBT", "0") == "1"
        if DEBT and st["shifted"]:
            rebuilt = []
            for m in market:
                if m[0] == "SELL" and len(m) >= 3 and st["shifted"].get(m[1], 0) > 0:
                    take = min(int(m[2]), st["shifted"][m[1]])
                    st["shifted"][m[1]] -= take
                    if int(m[2]) - take > 0:
                        rebuilt.append(["SELL", m[1], int(m[2]) - take])
                else:
                    rebuilt.append(m)
            market = rebuilt
            st["shifted"] = {k: v for k, v in st["shifted"].items() if v > 0}

        lead = []
        if turn < UNTIL and LEAD_K > 0:
            served = set()
            if turn % 4 == 0:
                for s in shops:
                    served.update(SHOPS.get(s, []))
            for item in ITEMS:
                if MODE == "no_tick" and item in served:
                    continue
                avail = shed.get(item, 0) - sum(int(m[2]) for m in market if m[0] == "SELL" and len(m) >= 3 and m[1] == item)
                if avail <= 0:
                    continue
                for dt in range(1, LEAD_K + 1):
                    if turn + dt >= len(_TAPE) or avail <= 0:
                        break
                    for m in (_TAPE[turn + dt].get("market") or []):
                        if m[0] == "SELL" and len(m) >= 3 and m[1] == item:
                            take = min(int(m[2]), avail)
                            if take > 0:
                                lead.append(["SELL", item, take])
                                st["shifted"][item] = st["shifted"].get(item, 0) + take
                                avail -= take
        base["market"] = (lead + market)[:10]
        return base
    except Exception:
        return base
