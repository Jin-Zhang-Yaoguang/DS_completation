"""V4H-tape：OceanMix 金牌 tape 生产骨架 × V4 账本卖出层。

底盘：排行榜第 2 名 OceanMix 的纯开环 tape（82 场跨 seed/对手/席位逐步一致，
来源 episode 102549659，hash be03c18c，提取过程见
model/v4_demand_race/distillation_feasibility.md）。

接管边界（最小侵入）：
- field 动作：保留 tape 原样，仅加 hands 对齐与 C92 式 weed 修复；
- 市场买入（HIRE/BUY_*）与 WHEAT、FERTILIZER 买卖：保留 tape 原样（饲料/施肥链不动）；
- 市场层：tape 原样原序。消融证明（见 README）自创的 race 跟跑 / 现金流阀 /
  价格挂起全部为负收益——tape 的手调时序与资金链是自洽的。仅保留两个增强：
  1. 一回合 premium 前移（boatlee V16-RC5 公开配方）：下一回合有 premium 卖单、
     本回合该品无商店需求 tick、shed 有货 → 提前一回合执行，从原单等量扣除；
  2. 终局兜底：714+ 清算 shed 内剩余 premium。
"""
from __future__ import annotations

import json
import math
import os

# --------------------------------------------------------------------------
# 引擎常量（1.32.7，与 kaggriculture.py 一致；用于价格预估与成本估算）
# --------------------------------------------------------------------------
MARKET_PARAMS = {
    "WHEAT": {"base": 25, "T": 400, "bf": "sqrt", "bt": 0.8, "af": "log", "at": 0.2},
    "CARROT": {"base": 35, "T": 450, "bf": "hinge", "bt": 1.0, "af": "sqrt", "at": 0.7},
    "TOMATO": {"base": 60, "T": 200, "bf": "hinge", "bt": 0.4, "af": "sqrt", "at": 0.6},
    "STRAWBERRY": {"base": 120, "T": 100, "bf": "sqrt", "bt": 0.7, "af": "linear", "at": 1.6},
    "MELON": {"base": 250, "T": 300, "bf": "log", "bt": 0.2, "af": "sq", "at": 3.6},
    "EGG": {"base": 50, "T": 332, "bf": "hinge", "bt": 0.4, "af": "log", "at": 0.2},
    "MILK": {"base": 160, "T": 122, "bf": "sqrt", "bt": 0.6, "af": "linear", "at": 1.6},
    "WOOL": {"base": 200, "T": 105, "bf": "log", "bt": 0.2, "af": "sq", "at": 3.2},
    "FERTILIZER": {"base": 100, "T": 200, "bf": "linear", "bt": 0.4, "af": "linear", "at": 0.4},
}
I0 = 10000
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
SEED_COST = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
ANIMAL_COST = {"GOOSE": 300, "COW": 400, "SHEEP": 500}
LAND_PRICES = [1000, 2000, 4000]
PRODUCTS = list(MARKET_PARAMS)

MANAGED = ("WOOL", "MILK", "STRAWBERRY", "MELON", "CARROT")   # 接管的卖出品
HANDLED_OPS = {"SELL"}                                        # 只接管 SELL 且限 MANAGED

# --------------------------------------------------------------------------
# 策略参数
# --------------------------------------------------------------------------
P = {
    "race_window": 36,        # 前移：只提前这个窗口内的计划量
    "race_opp_units": 3,      # 对手近 horizon 步净卖出 ≥ 此值触发 race
    "race_horizon": 6,        # 对手压力统计窗口（步）
    "defer_ratio": 0.55,      # price < base*ratio 时挂起计划单
    "release_ratio": 0.70,    # price ≥ base*ratio 时释放挂起
    "defer_max_steps": 48,    # 挂起超时强制释放
    "cash_lookahead": 8,      # 现金流阀：预估 tape 未来 N 步买入成本
    "cash_buffer": 50,        # 现金安全垫
    "shed_soft": 85,          # 仓容阀触发线（容量 100）
    "endgame_start": 700,     # 终局清算起点
    "endgame_hard": 714,      # 全量清算
    "batch_cap": 12,          # 单回合单品卖出上限（防自压）
}


def _shape(func, x, T=None):
    """与引擎 kaggriculture._shape 逐式一致（HINGE_GAIN=8.0）。"""
    x = max(0.0, float(x))
    if func == "linear":
        return x
    if func == "sq":
        return x * x
    if func == "sqrt":
        return math.sqrt(x)
    if func == "log":
        return math.log(1.0 + x)
    if func == "hinge":
        if not T or T <= 0:
            return x
        u = x / T
        return u + 8.0 * max(0.0, u - 1.0) ** 2
    return x


def price_of(item, inv):
    """复刻引擎 market_price（1.32.7）。"""
    p = MARKET_PARAMS[item]
    base, T = p["base"], p["T"]
    if inv < I0:
        amp = p["bt"] * base / _shape(p["bf"], T, T)
        price = base + amp * _shape(p["bf"], I0 - inv, T)
    else:
        amp = p["at"] * base / _shape(p["af"], T, T)
        price = base - amp * _shape(p["af"], inv - I0, T)
    return max(1, int(round(price)))


# --------------------------------------------------------------------------
# tape 加载与计划流预处理
# --------------------------------------------------------------------------
_TAPE = None
_PLAN = None          # [(step, item, qty), ...] 接管品的卖出计划
_KEEP_MARKET = None   # step -> [非接管的 tape 市场单]
_BUY_COST = None      # step -> 该步 tape 买入的估算成本（不含 BUY_PRODUCT 市价部分）
_BUY_PRODUCT = None   # step -> [(item, qty)] 需按市价估的买入


def _load_tape():
    global _TAPE, _PLAN, _KEEP_MARKET, _BUY_COST, _BUY_PRODUCT
    if _TAPE is not None:
        return
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "tape.json")) as fh:
        _TAPE = json.load(fh)
    _PLAN, _KEEP_MARKET, _BUY_COST, _BUY_PRODUCT = [], {}, {}, {}
    for t, act in enumerate(_TAPE):
        keep, cost, buyp = [], 0.0, []
        for m in (act.get("market") or []):
            op = m[0]
            if op == "SELL" and len(m) >= 3 and m[1] in MANAGED:
                _PLAN.append([t, m[1], int(m[2])])
                continue
            keep.append(m)
            if op == "BUY_SEED" and len(m) >= 3:
                cost += SEED_COST.get(m[1], 0) * int(m[2])
            elif op == "BUY_ANIMAL" and len(m) >= 3:
                cost += ANIMAL_COST.get(m[1], 0) * int(m[2])
            elif op == "BUY_LAND":
                cost += 2000.0            # 保守均值；精确值依赖已购块数
            elif op == "HIRE":
                cost += 15.0              # 日内多雇的均摊近似
            elif op == "BUY_PRODUCT" and len(m) >= 3:
                buyp.append((m[1], int(m[2])))
        if keep:
            _KEEP_MARKET[t] = keep
        if cost:
            _BUY_COST[t] = cost
        if buyp:
            _BUY_PRODUCT[t] = buyp


# --------------------------------------------------------------------------
# 运行时状态（按进程全局；同进程新一局用 turn 回退检测重置）
# --------------------------------------------------------------------------
_S = {}


def _fresh_state():
    return {
        "last_turn": -1,
        "plan_left": None,        # 计划流各条余量 [qty,...]
        "cursor": 0,              # 计划流游标（step 序）
        "deferred": [],           # [(item, qty, since_turn)]
        "prev_inv": None,         # 上回合市场库存
        "prev_shops": [],         # 上回合商店列表
        "my_last_sells": {},      # 上回合我方提交的卖量 {item: qty}
        "my_last_buys": {},       # 上回合我方提交的产品买量
        "opp_pressure": {},       # item -> 近期对手净卖出滑窗 [ (turn, units), ... ]
        "pending": {},            # 单位 idx -> 被 weed 顶掉待补的动作
        "shifted": {},            # 前移记账：item -> 已提前的量
    }


def _town_drain(step, shops):
    """step 执行后的城镇消耗（用于对手卖出反解）。"""
    d = {}
    if step % 4 == 0:
        for s in shops:
            mult = 2 if len(SHOPS.get(s, [])) == 1 else 1
            for it in SHOPS.get(s, []):
                d[it] = d.get(it, 0) + mult
    if step % 24 == 0:
        for it in TOWN_CENTER:
            d[it] = d.get(it, 0) + 1
    return d


def agent(obs, config=None):
    try:
        return _decide(obs)
    except Exception:
        farms = obs.get("farms") or []
        player = obs.get("player", 0)
        n = len(farms[player].get("hands") or []) if farms and player < len(farms) else 0
        return {"farmer": ["PASS"], "hands": [["PASS"]] * n, "market": []}


def _decide(obs):
    _load_tape()
    player = obs.get("player", 0)
    turn = int(obs.get("day", 0)) * 24 + int(obs.get("hour", 0))

    st = _S.get(player)
    if st is None or turn <= st["last_turn"]:
        st = _fresh_state()
        st["plan_left"] = [q for (_, _, q) in _PLAN]
        _S[player] = st
    st["last_turn"] = turn

    farm = obs["farms"][player]
    tiles = farm["tiles"]
    bs = len(tiles)
    private = obs.get("private") or {}
    shed = private.get("shed") or {}
    market = obs.get("market") or {}
    inv = market.get("inventory") or {}
    prices = market.get("prices") or {}
    money = float(farm.get("money") or 0)
    shops = list((obs.get("town") or {}).get("unlocked_shops") or [])

    # ---------------- 对手卖出反解 ----------------
    if st["prev_inv"] is not None:
        drain = _town_drain(turn - 1, st["prev_shops"])
        for it in PRODUCTS:
            di = inv.get(it, I0) - st["prev_inv"].get(it, I0)
            net_all = di + drain.get(it, 0)                     # 双方净卖出
            mine = st["my_last_sells"].get(it, 0) - st["my_last_buys"].get(it, 0)
            opp = net_all - mine
            if opp > 0:
                st["opp_pressure"].setdefault(it, []).append((turn, opp))
    st["prev_inv"] = dict(inv)
    st["prev_shops"] = shops

    def opp_recent(item):
        win = st["opp_pressure"].get(item, [])
        while win and win[0][0] < turn - P["race_horizon"]:
            win.pop(0)
        return sum(u for (_, u) in win)

    # ---------------- field 层：tape + 守卫 ----------------
    tape_act = _TAPE[turn] if turn < len(_TAPE) else {"farmer": ["PASS"], "hands": [], "market": []}
    farmer = list(tape_act.get("farmer") or ["PASS"])
    hands = [list(h) for h in (tape_act.get("hands") or [])]
    n_hands = len(farm.get("hands") or [])
    hands = (hands + [["PASS"]] * n_hands)[:n_hands]

    positions = [tuple(farm["farmer"])] + [tuple(pp) for pp in (farm.get("hands") or [])]
    unit_actions = [farmer] + hands

    BLOCKABLE = {"PLANT", "BUILD_PASTURE", "BUILD_COOP", "PLACE"}
    for idx, act in enumerate(unit_actions):
        if idx >= len(positions):
            break
        x, y = positions[idx]
        tile = tiles[y][x] if 0 <= y < bs and 0 <= x < bs else None
        is_weed = isinstance(tile, dict) and tile.get("kind") == "WEED"
        pend = st["pending"].get(idx)
        if pend and positions[idx] != pend[1]:
            st["pending"].pop(idx, None)            # 单位已离开目标格，放弃补执行
            pend = None
        if act and act[0] in BLOCKABLE and is_weed:
            st["pending"][idx] = (list(act), (x, y))    # C92：先 DIG，动作原格挂起
            unit_actions[idx] = ["DIG"]
        elif pend and act and act[0] == "PASS":
            unit_actions[idx] = pend[0]             # 仍在原格的 PASS 步补执行
            st["pending"].pop(idx, None)

    # ---------------- market 层：tape 原样 + 一回合前移 + 终局兜底 ----------------
    tape_market = [list(m) for m in (tape_act.get("market") or [])]

    # 上一回合前移的量，从本回合原单中扣除
    shifted = st.get("shifted") or {}
    if shifted:
        rebuilt = []
        for m in tape_market:
            if m[0] == "SELL" and len(m) >= 3 and m[1] in shifted and shifted[m[1]] > 0:
                take = min(int(m[2]), shifted[m[1]])
                shifted[m[1]] -= take
                q = int(m[2]) - take
                if q > 0:
                    rebuilt.append(["SELL", m[1], q])
            else:
                rebuilt.append(m)
        tape_market = rebuilt
    st["shifted"] = {k: v for k, v in shifted.items() if v > 0}

    lead_orders = []
    if turn + 1 < len(_TAPE) and turn < P["endgame_start"]:
        served_now = set()
        if turn % 4 == 0:
            for s in shops:
                served_now.update(SHOPS.get(s, []))
        nxt = _TAPE[turn + 1].get("market") or []
        for m in nxt:
            if m[0] == "SELL" and len(m) >= 3 and m[1] in MANAGED:
                item, qty = m[1], int(m[2])
                if item in served_now:
                    continue                      # 本回合有需求 tick，让原时序吃 tick 后的价
                have = shed.get(item, 0)
                take = min(qty, have)
                if take > 0:
                    lead_orders.append(["SELL", item, take])
                    st["shifted"][item] = st["shifted"].get(item, 0) + take

    endgame_orders = []
    if turn >= P["endgame_hard"]:
        planned = {m[1] for m in tape_market if m[0] == "SELL" and len(m) >= 2}
        for item in MANAGED:
            if item not in planned and shed.get(item, 0) > 0:
                endgame_orders.append(["SELL", item, shed[item]])

    orders = (lead_orders + endgame_orders + tape_market)[:10]

    st["my_last_sells"] = {}
    st["my_last_buys"] = {}
    for m in orders:
        if m[0] == "SELL" and len(m) >= 3:
            st["my_last_sells"][m[1]] = st["my_last_sells"].get(m[1], 0) + int(m[2])
        elif m[0] == "BUY_PRODUCT" and len(m) >= 3:
            st["my_last_buys"][m[1]] = st["my_last_buys"].get(m[1], 0) + int(m[2])

    return {"farmer": unit_actions[0], "hands": unit_actions[1:], "market": orders}
