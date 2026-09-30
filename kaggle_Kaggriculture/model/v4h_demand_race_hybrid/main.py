"""V4H v2：demand-race 市场层嫁接强生产底盘（DESIGN.md §8 + tape 内省）。

底盘：model/v1_adaptive_market（双路线 replay 派生，自带克隆局面 preempt）。
嫁接层只动 market 订单，不碰 farmer/hands。三个机制：

1. lookahead race-forward（本版新增，tape 内省）：
   - 直接读底盘模块的 _LOW/_HIGH_ROUTE_ACTIONS，得到未来 H 步的计划卖单；
   - V4 OpponentLedger 从对手公开 tiles + 市场反解预报对手供给到达时间；
   - 对手供给将先于底盘计划卖出到达时，把未来卖量提前到本回合（列表最前），
     并记入 debt——后续回合从底盘输出的同产品卖单中等量扣除（总量守恒，
     即 boatlee V16-RC5 / raykkretzschmar c45 验证过的 debt-tracked shift）。
   - 克隆局面（底盘 _clone_distance <= 6）让位给底盘自带 preempt，本层静默。
2. race-reorder：底盘本回合已计划卖、对手供给逼近的产品卖单前移（v1 保留）。
3. 终局保险：step >= 712 补挂漏掉的清仓单（v1 保留）。
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

RACE_ITEMS = ("MELON", "STRAWBERRY", "MILK", "WOOL")
LOOKAHEAD = 48          # 底盘计划扫描窗（step）
OPP_NEAR = 12           # 对手供给"迫近"窗
OPP_FAR = 36            # 对手供给"将至"窗
PULSE_MIN = 5.0         # 脉冲触发阈值（对手囤积/集中成熟量）
MAX_SHIFT = 10          # 单次前移量上限
RACE_START, RACE_STOP = 96, 690
WIN_FROM_DAY = 18       # LOCK 生效日
GAMBLE_FROM_DAY = 24    # GAMBLE 拦截开始日（窗口短，防爆仓）
WIN_MARGIN = 1500.0     # Δ 阈值
GAMBLE_RELEASE = 680    # GAMBLE 持仓强制放行步
GAMBLE_ITEMS = ("MELON", "STRAWBERRY", "MILK", "WOOL")
LOCK_PULL = 72          # LOCK 模式把未来多少步的计划卖单拉到现在
_H = {}


def _state():
    if "ledger" not in _H:
        _H["ledger"] = _v4.MarketLedger()
        _H["prev"] = []
        _H["debt"] = {}          # item -> 尚未从底盘未来卖单中扣除的已提前量
        _H["last_turn"] = -1
    return _H


def _opp_pulse(ledger, obs, item, window):
    """对手的脉冲供给：已囤积库存 + 一次性作物即将集中成熟。
    刻意排除动物/ongoing 的稳态流——稳态竞争已被底盘手调时序定价，
    对其抢跑等于在价格爬坡途中倾倒（v2 实测净负）。"""
    player = obs.get("player", 0)
    farms = obs.get("farms") or []
    opp = 1 - player
    pulse = ledger.opp_carry.get(item, 0.0)
    if opp < len(farms):
        day = obs["day"]
        horizon_day = (day * 24 + obs["hour"] + window) // 24
        for row in farms[opp].get("tiles") or []:
            for tt in row:
                if isinstance(tt, dict) and tt.get("kind") == "PLANT"                         and tt.get("crop") == item:
                    cd = _v4.CROPS[item]
                    if not cd["ongoing"]:
                        mature = tt["planted_day"] + cd["max_yield_day"]
                        if mature <= horizon_day:
                            pulse += max(tt.get("yield_units", 0),
                                         cd["max_yield"] * 0.7)
    return pulse


def _future_plan(step, item, horizon):
    """底盘未来 horizon 步内计划卖出 item 的 (首个卖出步, 总量)。"""
    high = getattr(_base, "_HIGH_ROUTE_ACTIONS", None)
    low = getattr(_base, "_LOW_ROUTE_ACTIONS", None) or getattr(_base, "_ACTIONS", None)
    if low is None:
        return None, 0
    if high is None:
        routes = [low]                        # 单路线底盘（V76 谱系）
    else:
        try:
            expert = _base._ROUTE_STATE[0].get("expert") or \
                _base._ROUTE_STATE[1].get("expert")
        except Exception:
            expert = None
        routes = [high if expert == "high" else low]
        if expert is None and step + horizon > 168:
            routes = [low, high]
    first, qty = None, 0
    for route in routes:
        f, q = None, 0
        for s in range(step + 1, min(step + horizon + 1, len(route))):
            for o in (route[s] or {}).get("market") or []:
                if isinstance(o, list) and len(o) >= 3 and o[0] == "SELL" and o[1] == item:
                    q += int(o[2])
                    if f is None:
                        f = s
        if f is not None and (first is None or f < first):
            first, qty = f, q
        elif first is None:
            qty = max(qty, q)
    return first, qty


def _delta(obs, ledger, shed, prices):
    """终局期望差 Δ = μ_me − μ_opp（双方 money 公开；对手 carry 由账本重建）。"""
    player = obs.get("player", 0)
    farms = obs.get("farms") or []
    if len(farms) < 2:
        return 0.0
    me, op = farms[player], farms[1 - player]
    liq = lambda items: sum(n * max(1, prices.get(it, 0)) * 0.85
                            for it, n in items.items() if it in _v4.PRODUCTS)
    mu_me = me["money"] + liq(shed) + _v4._farm_residual(me, obs["day"])
    mu_op = op["money"] + liq(ledger.opp_carry) + _v4._farm_residual(op, obs["day"])
    return mu_me - mu_op


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
        if turn <= st["last_turn"]:
            _H.clear()
            st = _state()
        st["last_turn"] = turn
        ledger = st["ledger"]
        ledger.update(obs, st["prev"])

        market = [list(o) for o in (act.get("market") or []) if isinstance(o, list)]
        shed = dict((obs.get("private") or {}).get("shed") or {})

        # 0) debt 扣减：底盘输出的卖单先偿还已提前的量（总量守恒）
        if st["debt"]:
            new_market = []
            for o in market:
                if o and o[0] == "SELL" and len(o) >= 3 and o[1] in st["debt"]:
                    d = st["debt"][o[1]]
                    take = min(d, int(o[2]))
                    if take > 0:
                        st["debt"][o[1]] -= take
                        o = [o[0], o[1], int(o[2]) - take]
                        if st["debt"][o[1]] <= 0:
                            del st["debt"][o[1]]
                    if int(o[2]) <= 0:
                        continue
                new_market.append(o)
            market = new_market
        planned_now = {o[1] for o in market if o and o[0] == "SELL" and len(o) > 1}

        # 判定克隆局面：让位给底盘自带 preempt
        try:
            is_clone = _base._clone_distance(obs) <= _base._PREEMPT_MAX_CLONE_DISTANCE
        except Exception:
            is_clone = False

        # 1) lookahead race-forward（tape 内省 + 债务记账）
        if not is_clone and RACE_START <= turn < RACE_STOP:
            for it in RACE_ITEMS:
                if len(market) >= 10:
                    break
                have = shed.get(it, 0) - st["debt"].get(it, 0)
                if have < 2 or it in planned_now:
                    continue
                pulse_near = _opp_pulse(ledger, obs, it, OPP_NEAR)
                pulse_far = _opp_pulse(ledger, obs, it, OPP_FAR)
                first_sell, fut_qty = _future_plan(turn, it, LOOKAHEAD)
                if fut_qty <= 0:
                    continue
                trigger = (pulse_near >= PULSE_MIN) or \
                    (pulse_far >= PULSE_MIN and (first_sell is None or first_sell - turn > OPP_FAR))
                if trigger:
                    q = min(have, fut_qty, MAX_SHIFT)
                    if q > 0:
                        market.insert(0, ["SELL", it, q])
                        st["debt"][it] = st["debt"].get(it, 0) + q
                        planned_now.add(it)

        # 2) race-reorder：既有卖单中危险产品前移
        if 24 <= turn < RACE_STOP and len(market) > 1:
            danger = [it for it in RACE_ITEMS if it in planned_now and
                      _opp_pulse(ledger, obs, it, 30) >= PULSE_MIN]
            if danger:
                front = [o for o in market if o[0] == "SELL" and len(o) > 1 and o[1] in danger]
                rest = [o for o in market if not (o[0] == "SELL" and len(o) > 1 and o[1] in danger)]
                market = front + rest

        # 2.5) WinLedger：终局 Δ 模式（GAMBLE 持仓赌方差 / LOCK 提前落袋）
        if obs["day"] >= WIN_FROM_DAY and turn < 712:
            prices = dict((obs.get("market") or {}).get("prices") or {})
            delta = _delta(obs, ledger, shed, prices)
            shed_used = sum(v for k2, v in shed.items())
            GAMBLE_ENABLED = False   # 已证伪：共享消耗性需求下持仓延迟是期望毁灭器
            if GAMBLE_ENABLED and delta < -WIN_MARGIN and obs["day"] >= GAMBLE_FROM_DAY \
                    and turn < GAMBLE_RELEASE and shed_used < 78:
                # 落后：短窗拦截 premium 卖单，集中到 GAMBLE_RELEASE 后抛（加方差）
                held = st.setdefault("gamble_held", {})
                kept = []
                for o in market:
                    if o and o[0] == "SELL" and len(o) >= 3 and o[1] in GAMBLE_ITEMS:
                        held[o[1]] = held.get(o[1], 0) + int(o[2])
                    else:
                        kept.append(o)
                market = kept
            elif st.get("gamble_held") and shed_used >= 78:
                # 仓压保护：放弃赌局，立即放行持仓
                for it in list(st["gamble_held"]):
                    if len(market) >= 10:
                        break
                    q = min(shed.get(it, 0), st["gamble_held"].pop(it))
                    if q > 0 and it not in planned_now:
                        market.insert(0, ["SELL", it, q])
                        planned_now.add(it)
            elif delta > WIN_MARGIN:
                # 领先：把未来 LOCK_PULL 步的计划卖单拉到现在（复用 debt 机制）
                for it in GAMBLE_ITEMS:
                    if len(market) >= 10:
                        break
                    have = shed.get(it, 0) - st["debt"].get(it, 0)
                    if have <= 0 or it in planned_now:
                        continue
                    _, fq = _future_plan(turn, it, LOCK_PULL)
                    q = min(have, fq)
                    if q > 0:
                        market.insert(0, ["SELL", it, q])
                        st["debt"][it] = st["debt"].get(it, 0) + q
                        planned_now.add(it)
            # 到达放行点：把 GAMBLE 攒下的持仓按当前价从高到低抛出
            if turn >= GAMBLE_RELEASE and st.get("gamble_held"):
                for it in sorted(st["gamble_held"],
                                 key=lambda x: -prices.get(x, 0)):
                    if len(market) >= 10:
                        break
                    have = min(shed.get(it, 0), st["gamble_held"].pop(it))
                    if have > 0 and it not in planned_now:
                        market.insert(0, ["SELL", it, have])
                        planned_now.add(it)

        # 3) 终局保险
        if turn >= 712:
            for it in _v4.PRODUCTS:
                if len(market) >= 10:
                    break
                if it not in planned_now and shed.get(it, 0) > 0:
                    market.append(["SELL", it, shed[it]])
                    planned_now.add(it)

        st["prev"] = market
        act["market"] = market[:10]
        return act
    except Exception:
        return act
