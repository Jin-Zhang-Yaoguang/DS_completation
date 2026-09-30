"""V4H：demand-race 市场层嫁接到强生产底盘（DESIGN.md §8 预案）。

底盘：model/v1_adaptive_market（Tetsutani 公开双路线，本地最强执行体之一）。
嫁接层（只动 market 列表，不碰 farmer/hands）：
  1. race-forward：V4 对手账本判定某产品的对手供给将在 lookahead 步内到达，
     而底盘本回合未卖该产品且 shed 有存货 → 前插一笔 SELL 抢先成交。
     底盘后续自己的同产品卖单若因 shed 清空而失败 = 引擎静默 no-op，方向安全。
  2. 终局保险：step >= 712 时补挂底盘漏掉的清仓单。
  账本与参数完全复用 v4_demand_race/main.py（MarketLedger / POLICY）。
"""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE_PATH = HERE.parent / "v1_adaptive_market" / "main.py"
V4_PATH = HERE.parent / "v4_demand_race" / "main.py"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_base = _load("v4h_base", str(BASE_PATH))
_v4 = _load("v4h_lib", str(V4_PATH))

RACE_LOOKAHEAD = 30
RACE_MIN_STOCK = 3
RACE_ITEMS = ("MELON", "STRAWBERRY", "MILK", "WOOL")
_H = {}


def _state():
    if "ledger" not in _H:
        _H["ledger"] = _v4.MarketLedger()
        _H["prev"] = []
        _H["last_turn"] = -1
    return _H


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
        day, hour = int(obs.get("day", 0)), int(obs.get("hour", 0))
        turn = day * 24 + hour
        if turn <= st["last_turn"]:              # 新的一局
            _H.clear()
            st = _state()
        st["last_turn"] = turn
        ledger = st["ledger"]
        ledger.update(obs, st["prev"])

        market = [list(o) for o in (act.get("market") or []) if isinstance(o, list)]
        shed = dict((obs.get("private") or {}).get("shed") or {})
        planned_sell = {o[1] for o in market if o and o[0] == "SELL" and len(o) > 1}

        # 1) race-reorder：底盘已计划卖、且对手供给逼近的产品，其卖单前移
        #    （不增删任何订单，只改同回合内的成交次序；卖出计划保持底盘原样）
        if 24 <= turn < 690 and len(market) > 1:
            danger = []
            for it in RACE_ITEMS:
                if it in planned_sell and                         ledger.opp_supply_eta(obs, it, RACE_LOOKAHEAD) >= 3:
                    danger.append(it)
            if danger:
                front = [o for o in market if o[0] == "SELL" and len(o) > 1 and o[1] in danger]
                rest = [o for o in market if not (o[0] == "SELL" and len(o) > 1 and o[1] in danger)]
                market = front + rest

        # 2) 终局保险
        if turn >= 712:
            for it in _v4.PRODUCTS:
                if len(market) >= 10:
                    break
                if it not in planned_sell and shed.get(it, 0) > 0:
                    market.append(["SELL", it, shed[it]])
                    planned_sell.add(it)

        st["prev"] = market
        act["market"] = market[:10]
        return act
    except Exception:
        return act


