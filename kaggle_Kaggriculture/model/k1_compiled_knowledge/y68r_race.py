"""y68r：y68f 底盘 + 逐步对手条件市场层（race 提前卖）原型。

研究目标（2026-09-13 用户指令）：在不低于 y68 家族强度的前提下，
用更短步骤（每回合）的自适应降低跨局路径重复度。

机制（对手条件触发，区别于启发式线已证伪的无条件节拍规则）：
  每回合用市场库存增量反解对手净卖出（扣除自己上回合卖单；低价区 $1 成交
  不入库存，只在价格>阈值时反解）。检测到对手正在抛售某高价品时，把 base
  带内未来 W 步计划卖出的同品提前到本步**追加**卖出——抢在对手供给压价前出货。

安全约束（全部来自实验册负知识）：
  - 只追加、不删改 base 的任何订单（压卖单→满仓销毁/贫困陷阱，已证伪）；
  - 本回合 base 有 BUY/HIRE/BUY_LAND 时完全不动（现金周转保护）；
  - 追加后总订单不超 MAX_ORDERS=10，超了放弃；
  - 追加量 ≤ shed 现货 且 ≤ base 未来 W 步计划卖量（不凭空加卖，总量守恒）。
"""
import importlib.util
import sys
from pathlib import Path

_PACKS = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/opponent_pool_v1/packs")

_spec = importlib.util.spec_from_file_location(f"y68f_base_{id(object())}", _PACKS / "y68f_main.py")
_base_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base_mod)
_BASE = _base_mod.agent
_CH = _base_mod._IMPL.chassis

# 参数集中于此并可被调参器注入（PARAMS_OVERRIDE），与 K1 框架的旋钮纪律对齐；
# 本文件是跨底盘研究原型（宿主 y68f 不属于 K1 框架），采纳后由收编线按其
# 层叠工艺正式并入；K1 框架内的同机制层见 main.py market_orders 的 race 段。
PARAMS = {
    "race_items": ("MILK", "WOOL", "STRAWBERRY", "MELON", "EGG"),
    "race_window": 4,    # 提前 base 未来 W 步内的计划卖单
    "race_trigger": 3,   # 衰减累计对手净卖出 >= 此值触发
    "race_decay": 0.6,   # 对手卖出信号逐步衰减
    "min_price": 30,     # 低价区不反解也不抢跑
}
PARAMS_OVERRIDE = None

def _p(k):
    if PARAMS_OVERRIDE and k in PARAMS_OVERRIDE:
        return PARAMS_OVERRIDE[k]
    return PARAMS[k]

RACE_ITEMS = PARAMS["race_items"]

_ST = {}


def _reset(player):
    _ST[player] = {"prev_inv": None, "my_prev_sells": {}, "opp_flow": {p: 0.0 for p in RACE_ITEMS}}


def agent(observation, configuration=None):
    act = _BASE(observation, configuration)
    try:
        player = int(observation.get("player", 0))
        turn = int(observation.get("step", 0) or 0)
        if turn <= 1 or player not in _ST:
            _reset(player)
        st = _ST[player]
        mkt = observation.get("market") or {}
        inv = dict(mkt.get("inventory") or {})
        prices = dict(mkt.get("prices") or {})

        # 1) 反解对手净卖出：Δ库存 - 我上回合卖量（仅高价区可靠）
        if st["prev_inv"] is not None:
            for it in RACE_ITEMS:
                if prices.get(it, 0) < _p("min_price"):
                    continue
                delta = inv.get(it, 0) - st["prev_inv"].get(it, 0)
                opp = delta - st["my_prev_sells"].get(it, 0)
                st["opp_flow"][it] = st["opp_flow"][it] * _p("race_decay") + max(0.0, opp)
        st["prev_inv"] = inv

        market = [list(o) for o in (act.get("market") or [])]
        my_sells = {}
        for o in market:
            if o and o[0] == "SELL" and len(o) >= 3:
                my_sells[o[1]] = my_sells.get(o[1], 0) + max(0, int(o[2] or 0))

        # 2) 条件触发：对手在抛 → 提前 base 未来计划卖单（追加式）
        has_buy = any(o and o[0] in ("BUY_SEED", "BUY_ANIMAL", "BUY_PRODUCT", "HIRE", "BUY_LAND")
                      for o in market)
        if not has_buy and turn < 700:
            pst = _CH.players.get(player) or {}
            route = pst.get("route", 0)
            shed = dict((observation.get("private") or {}).get("shed") or {})
            for it in RACE_ITEMS:
                if st["opp_flow"].get(it, 0.0) < _p("race_trigger"):
                    continue
                if prices.get(it, 0) < _p("min_price") or it in my_sells:
                    continue
                try:
                    # future_sells 返回后缀和：窗口内计划卖量 = 后缀(turn+1) - 后缀(turn+1+W)
                    planned = _CH.future_sells(route, it, turn + 1) - \
                        _CH.future_sells(route, it, min(719, turn + 1 + _p("race_window")))
                except Exception:
                    planned = 0
                q = min(planned, shed.get(it, 0))
                if q > 0 and len(market) < 10:
                    market.append(["SELL", it, q])
        act["market"] = market
        st["my_prev_sells"] = {}
        for o in market:
            if o and o[0] == "SELL" and len(o) >= 3:
                st["my_prev_sells"][o[1]] = st["my_prev_sells"].get(o[1], 0) + max(0, int(o[2] or 0))
    except Exception:
        pass
    return act


_ENTRY = agent
