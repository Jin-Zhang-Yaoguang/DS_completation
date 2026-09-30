"""V4H2：v1am 底盘 + race-reorder + 终局保险 + V20 式 tick-defer。

在 V4H（v4h_demand_race_hybrid）之上新增一个机制——移植自本仓库 V20
（v20_demand_timing_moe，17,408 场确认 +6.53pp）的需求时点控制：

引擎一回合的结算顺序是「市场订单 → 城镇/商店消耗」。因此在需求 tick 回合
（step%4==0 的商店 tick、step%24==0 的城镇中心 tick）把受需求商品的 25%
卖量延后一回合，可以吃到 tick 消耗抬价后的更高单价。
安全条件（照 V20）：非终局、shed 无溢出压力、延后量下一回合可并入。
生产、购买、卖出总量均不变，只动执行时间。
"""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE_PATH = HERE.parent / "v1_adaptive_market" / "main.py"
V4_PATH = HERE.parent / "v4_demand_race" / "main.py"

SHOPS = {
    "BAKERY": ["EGG", "WHEAT"],
    "PIZZA_SHOP": ["MILK", "TOMATO", "WHEAT"],
    "BRUNCH_SPOT": ["EGG", "WHEAT", "STRAWBERRY"],
    "YARN_STORE": ["WOOL"],
    "ICE_CREAM_SHOP": ["STRAWBERRY", "MILK", "WHEAT"],
    "PET_CAFE": ["CARROT"],
    "SMOOTHIE_SHOP": ["STRAWBERRY", "MILK"],
    "FARMERS_MARKET": ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY"],
}
TOWN_CENTER = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL"]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_base = _load("v4h2_base", str(BASE_PATH))
_v4 = _load("v4h2_lib", str(V4_PATH))

RACE_LOOKAHEAD = 30
RACE_ITEMS = ("MELON", "STRAWBERRY", "MILK", "WOOL")
DEFER_FRAC = 0.25          # V20 的比例
DEFER_ITEMS = ("MELON", "STRAWBERRY", "MILK", "WOOL", "EGG", "CARROT", "TOMATO")
_H = {}


def _state():
    if "ledger" not in _H:
        _H["ledger"] = _v4.MarketLedger()
        _H["prev"] = []
        _H["last_turn"] = -1
        _H["defer"] = {}       # item -> qty，待并入下一回合
    return _H


def _demanded_now(turn, shops):
    """本回合结算后会被城镇消耗的商品集合。"""
    d = set()
    if turn % 4 == 0:
        for s in shops:
            d.update(SHOPS.get(s, []))
    if turn % 24 == 0:
        d.update(TOWN_CENTER)
    return d


def agent(obs, config=None):
    try:
        act = _base.agent(obs)
    except Exception:
        farms = obs.get("farms") or []
        player = obs.get("player", 0)
        n = len(farms[player].get("hands") or []) if farms and player < len(farms) else 0
        return {"farmer": ["PASS"], "hands": [["PASS"]] * n, "market": []}
    try:
        st = _state()
        turn = int(obs.get("day", 0)) * 24 + int(obs.get("hour", 0))
        if turn <= st["last_turn"]:
            _H.clear()
            st = _state()
        st["last_turn"] = turn
        ledger = st["ledger"]
        ledger.update(obs, st["prev"])

        market = [list(o) for o in (act.get("market") or []) if isinstance(o, list)]
        shed = dict((obs.get("private") or {}).get("shed") or {})
        shops = list((obs.get("town") or {}).get("unlocked_shops") or [])

        # 0) 并入上一回合延后的量（该品已有卖单则加量，否则前插；槽满则继续顺延）
        if st["defer"]:
            leftover = {}
            for it, q in st["defer"].items():
                merged = False
                for o in market:
                    if o[0] == "SELL" and len(o) >= 3 and o[1] == it:
                        o[2] = int(o[2]) + q
                        merged = True
                        break
                if not merged:
                    if len(market) < 10:
                        market.insert(0, ["SELL", it, q])
                    else:
                        leftover[it] = q
            st["defer"] = leftover

        planned_sell = {o[1] for o in market if o and o[0] == "SELL" and len(o) > 1}

        # 1) race-reorder（继承 V4H：只重排不增删）
        if 24 <= turn < 690 and len(market) > 1:
            danger = [it for it in RACE_ITEMS
                      if it in planned_sell
                      and ledger.opp_supply_eta(obs, it, RACE_LOOKAHEAD) >= 3]
            if danger:
                front = [o for o in market if o[0] == "SELL" and len(o) > 1 and o[1] in danger]
                rest = [o for o in market if not (o[0] == "SELL" and len(o) > 1 and o[1] in danger)]
                market = front + rest

        # 2) V20 式 tick-defer：需求 tick 回合，把受需求商品 25% 卖量延后一回合
        if turn < 690 and sum(shed.values()) < 85:
            demanded = _demanded_now(turn, shops)
            for o in market:
                if o[0] != "SELL" or len(o) < 3:
                    continue
                it, q = o[1], int(o[2])
                if it not in DEFER_ITEMS or it not in demanded or q < 2:
                    continue
                move = max(1, int(q * DEFER_FRAC))
                if move >= q:
                    move = q - 1
                if move <= 0:
                    continue
                o[2] = q - move
                st["defer"][it] = st["defer"].get(it, 0) + move

        # 3) 终局保险（继承 V4H）
        if turn >= 712:
            for it, q in list(st["defer"].items()):
                merged = False
                for o in market:
                    if o[0] == "SELL" and len(o) >= 3 and o[1] == it:
                        o[2] = int(o[2]) + q
                        merged = True
                if not merged and len(market) < 10:
                    market.insert(0, ["SELL", it, q])
                st["defer"].pop(it, None)
            planned = {o[1] for o in market if o and o[0] == "SELL" and len(o) > 1}
            for it in _v4.PRODUCTS:
                if it not in planned and shed.get(it, 0) > 0 and len(market) < 10:
                    market.append(["SELL", it, shed[it]])

        act["market"] = market[:10]
        st["prev"] = [list(o) for o in act["market"]]
        return act
    except Exception:
        return act
