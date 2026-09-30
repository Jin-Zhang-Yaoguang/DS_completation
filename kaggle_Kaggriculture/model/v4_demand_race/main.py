"""Kaggriculture V4 demand-race agent.

设计文档：同目录 DESIGN.md。架构：
  PlanRoles（静态地块角色 + 预留栏）
  + MarketLedger（需求坑账本 + 对手账本：卖出反解、收获推断、供给预报）
  + WinLedger（终局 Δ 模式：LOCK / NORMAL / GAMBLE）
  + Router（day 3/6/9 商店信号 → 组合调整）
  + Executor（任务全局指派；日终自动入库，不做无谓运货）
  + Market（坑内分批卖出 + race 抢跑 + 终局清算）

引擎契约（1.32.7，逐条在源码核对）：
  - 一回合内 field 先于 market 结算；市场订单按 index 逐单位 lockstep。
  - step 718 是最后一个被执行的动作；不读 obs["step"]，用 day*24+hour。
  - 日终自动把所有随身物品放入 shed（容量 100，超出丢弃）。
  - 一次性作物到 (planted_day+max_yield_day+1)*24 后每 2 步烂 1 yield。
  - ongoing 作物产出日"浇水+施肥期内"为 +2；及时收获不撞 cap。
  - SELL 成交价为 $1 时不增加市场库存（对手反解在低价区不可靠）。
"""
import math

# ------------------------------------------------------------------
# 引擎常量（1.32.7 复刻，保证提交包自包含）
# ------------------------------------------------------------------
CROPS = {
    "WHEAT":      {"seed": 10,  "first_yield_day": 2,  "max_yield_day": 4,  "interval": 0, "max_yield": 6, "ongoing": False},
    "CARROT":     {"seed": 20,  "first_yield_day": 2,  "max_yield_day": 3,  "interval": 0, "max_yield": 4, "ongoing": False},
    "TOMATO":     {"seed": 50,  "first_yield_day": 8,  "max_yield_day": 8,  "interval": 1, "max_yield": 4, "ongoing": True},
    "STRAWBERRY": {"seed": 100, "first_yield_day": 10, "max_yield_day": 10, "interval": 2, "max_yield": 4, "ongoing": True},
    "MELON":      {"seed": 80,  "first_yield_day": 10, "max_yield_day": 12, "interval": 0, "max_yield": 6, "ongoing": False},
}
ANIMALS = {
    "GOOSE": {"cost": 300, "structure": "COOP",    "first_yield_day": 4, "interval": 1, "max_held": 4, "product": "EGG"},
    "COW":   {"cost": 400, "structure": "PASTURE", "first_yield_day": 8, "interval": 2, "max_held": 6, "product": "MILK"},
    "SHEEP": {"cost": 500, "structure": "PASTURE", "first_yield_day": 6, "interval": 3, "max_held": 6, "product": "WOOL"},
}
PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]
SHOPS = {
    "BAKERY":         ["EGG", "WHEAT"],
    "PIZZA_SHOP":     ["MILK", "TOMATO", "WHEAT"],
    "BRUNCH_SPOT":    ["EGG", "WHEAT", "STRAWBERRY"],
    "YARN_STORE":     ["WOOL"],
    "ICE_CREAM_SHOP": ["STRAWBERRY", "MILK", "WHEAT"],
    "PET_CAFE":       ["CARROT"],
    "SMOOTHIE_SHOP":  ["STRAWBERRY", "MILK"],
    "FARMERS_MARKET": ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY"],
}
TOWN_CENTER = [p for p in PRODUCTS if p != "FERTILIZER"]
MARKET_PARAMS = {
    "WHEAT":      {"base": 25,  "I0": 10000, "T": 400, "below_func": "sqrt",  "below_target": 0.8, "above_func": "log",    "above_target": 0.2},
    "CARROT":     {"base": 35,  "I0": 10000, "T": 450, "below_func": "hinge", "below_target": 1.0, "above_func": "sqrt",   "above_target": 0.7},
    "TOMATO":     {"base": 60,  "I0": 10000, "T": 200, "below_func": "hinge", "below_target": 0.4, "above_func": "sqrt",   "above_target": 0.6},
    "STRAWBERRY": {"base": 120, "I0": 10000, "T": 100, "below_func": "sqrt",  "below_target": 0.7, "above_func": "linear", "above_target": 1.6},
    "MELON":      {"base": 250, "I0": 10000, "T": 300, "below_func": "log",   "below_target": 0.2, "above_func": "sq",     "above_target": 3.6},
    "EGG":        {"base": 50,  "I0": 10000, "T": 332, "below_func": "hinge", "below_target": 0.4, "above_func": "log",    "above_target": 0.2},
    "MILK":       {"base": 160, "I0": 10000, "T": 122, "below_func": "sqrt",  "below_target": 0.6, "above_func": "linear", "above_target": 1.6},
    "WOOL":       {"base": 200, "I0": 10000, "T": 105, "below_func": "log",   "below_target": 0.2, "above_func": "sq",     "above_target": 3.2},
    "FERTILIZER": {"base": 100, "I0": 10000, "T": 200, "below_func": "linear","below_target": 0.4, "above_func": "linear", "above_target": 0.4},
}
HINGE_GAIN = 8.0
PRICE_FLOOR = 1
LAND_ORDER = ["NE", "SW", "SE"]
LAND_PRICES = [1000, 2000, 4000]
SHED_CAP = 100
MAX_ORDERS = 10
MAX_SHOPS = 8


def _shape(func, x, T=None):
    x = max(0.0, x)
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
        return u + HINGE_GAIN * max(0.0, u - 1.0) ** 2
    return x


def market_price(item, inventory):
    p = MARKET_PARAMS[item]
    base, I0, T = p["base"], p["I0"], p["T"]
    if inventory < I0:
        amp = p["below_target"] * base / _shape(p["below_func"], T, T)
        price = base + amp * _shape(p["below_func"], I0 - inventory, T)
    else:
        amp = p["above_target"] * base / _shape(p["above_func"], T, T)
        price = base - amp * _shape(p["above_func"], inventory - I0, T)
    return max(PRICE_FLOOR, int(round(price)))


def sell_revenue(item, inventory, q):
    """卖 q 单位的精确收入（逐单位；$1 成交不增库存）。"""
    total, inv = 0, inventory
    for _ in range(q):
        pr = market_price(item, inv)
        total += pr
        if pr > 1:
            inv += 1
    return total


# ------------------------------------------------------------------
# 策略参数（CEM 搜索的对象；机制开关用于消融）
# ------------------------------------------------------------------
POLICY = {
    # --- 组合（基础先验，Router 会动态调整） ---
    "herd": [('SHEEP', 4), ('COW', 10)],   # 终期目标（Router 再调）
    "herd_early": [('SHEEP', 2), ('COW', 3)],  # 阶段 A（melon IPO 前）
    "ipo_day": 7,                 # melon 首收日：资本阶段切换点
    "n_animal_tiles": 8,
    "n_reserve_pens": 2,
    "n_wheat_tiles": 5,
    "n_melon_tiles": 14,           # 阶段 A 主力资产（NW）
    "n_straw_tiles": 6,           # 阶段 B 主产线（NE/SW，肥料引擎）
    "n_melon2_tiles": 4,           # 第二波 melon
    "last_animal_day": 14,
    "hands_schedule": [(0, 3), (2, 9), (10, 9)],
    "cash_reserve": 400,
    "buy_land_days": {'NE': 7, 'SW': 13},
    "feed_stock_days": 2,
    "wheat_buy_price_cap": 60,
    "wheat_hoard_until_day": 13,   # 此前逢低囤饲料
    "carry_wheat": 6,
    # --- 市场层 ---
    "slip_tol": 0.0815,              # 单批自压容忍（批末价 >= 批首价*(1-tol)）
    "batch_cap": 10,               # 单批上限
    "premium_wait_margin": 1.084,   # 坑内等价的目标（>= base*margin 才主动卖）
    "race_lookahead": 30,          # 对手供给预报窗口（step）
    "glut_floor_frac": 0.3301,       # 坑外卖出下限（base 比例）
    "fert_reserve_per_straw": 1.2, # 每株活跃草莓预留肥料
    # --- Router ---
    "router_days": (3, 6, 9),
    "sheep_per_yarn": 2,
    "cow_per_dairy2": 2,
    "straw_shops_needed": 2,       # 几家草莓商店确认后草莓满负荷
    "yarn_deadline_day": 9,        # 此日仍无 yarn 则放弃加羊
    # --- WinLedger ---
    "sell_late_day": 22,           # 此日起 glut 也无条件出清
    "forced_flush": 1,             # 仓压时强制大批量（0/1）
    "win_mode_from_day": 20,
    "win_margin": 5000.0,
    "gamble_hold_until_day": 27,
    # --- 终局 ---
    "terminal_turn": 694,
    "last_turn": 718,
    # --- 机制开关（消融用） ---
    "assign_pri_w": 6.0,           # 指派代价 = pri*pri_w + dist*dist_w
    "assign_dist_w": 1.1232,
    "use_opp_ledger": True,
    "use_race": True,
    "use_router": True,
    "use_win_modes": True,
    "use_fertilize": True,
}

_STATE = {}


# ------------------------------------------------------------------
# 几何与角色规划
# ------------------------------------------------------------------
def _shed_tiles(bs):
    h = bs // 2
    return [(h - 1, h - 1), (h, h - 1), (h - 1, h), (h, h)]


def _quadrant(x, y, bs):
    h = bs // 2
    return ("N" if y < h else "S") + ("W" if x < h else "E")


def _dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _shed_dist(p, bs):
    return min(_dist(p, s) for s in _shed_tiles(bs))


def _step_toward(src, dst):
    if src[0] > dst[0]:
        return ["WEST"]
    if src[0] < dst[0]:
        return ["EAST"]
    if src[1] > dst[1]:
        return ["NORTH"]
    if src[1] < dst[1]:
        return ["SOUTH"]
    return None


def _plan_roles(bs, pol):
    """NW→NE→SW 按到 shed 距离分配角色。每天都要服务的资产压在 shed 旁。"""
    order = []
    for quad in ("NW", "NE", "SW"):
        tiles = [(x, y) for y in range(bs) for x in range(bs) if _quadrant(x, y, bs) == quad]
        tiles.sort(key=lambda t: (_shed_dist(t, bs), t[1], t[0]))
        order.extend(tiles)
    roles, i = {}, 0
    spec = [("ANIMAL", pol["n_animal_tiles"]),
            ("WHEAT", pol["n_wheat_tiles"]),
            ("MELON", pol["n_melon_tiles"]),
            ("STRAWBERRY", pol["n_straw_tiles"]),
            ("MELON", pol.get("n_melon2_tiles", 0))]
    for role, n in spec:
        for _ in range(n):
            if i < len(order):
                roles[order[i]] = role
                i += 1
    return roles


# ------------------------------------------------------------------
# MarketLedger：需求坑 + 对手重建
# ------------------------------------------------------------------
class MarketLedger:
    def __init__(self):
        self.prev_inv = None          # 上回合市场库存
        self.prev_my_net = {}         # 上回合我方提交的净卖出（sell-买入）
        self.prev_opp_tiles = None    # 上回合对手 tiles 快照（收获推断）
        self.opp_sold = {p: 0.0 for p in PRODUCTS}
        self.opp_carry = {p: 0.0 for p in PRODUCTS}
        self.my_sold = {p: 0 for p in PRODUCTS}

    # ---- 城镇 drain ----
    @staticmethod
    def drain_at(step, shops):
        d = {p: 0 for p in PRODUCTS}
        if step % 4 == 0:
            for s in shops:
                menu = SHOPS.get(s, [])
                mult = 2 if len(menu) == 1 else 1
                for it in menu:
                    d[it] += mult
        if step % 24 == 0:
            for it in TOWN_CENTER:
                d[it] += 1
        return d

    @staticmethod
    def remaining_drain(turn, shops, item):
        """剩余赛季该产品的城镇需求（已解锁确定部分 + 未来解锁期望部分）。"""
        last = 719
        # 已解锁商店：每 4 步一 tick
        ticks = max(0, (last - turn) // 4 + 1)
        det = 0
        for s in shops:
            menu = SHOPS.get(s, [])
            if item in menu:
                det += (2 if len(menu) == 1 else 1) * ticks
        # 城镇中心
        if item != "FERTILIZER":
            det += max(0, (last - turn) // 24 + 1)
        # 未来商店（day 2,5,8..23 末解锁；期望菜单）
        exp = 0.0
        n_future = max(0, MAX_SHOPS - len(shops))
        if n_future:
            per_shop = sum((2 if len(m) == 1 else 1) for m in SHOPS.values() if item in m) / len(SHOPS)
            day = turn // 24
            k = len(shops)
            for j in range(n_future):
                unlock_day = 3 * (k + j + 1) - 1        # 第 m 家在 day 3m-1 末解锁
                if unlock_day >= 30:
                    break
                remain_steps = max(0, last - (unlock_day + 1) * 24)
                exp += per_shop * (remain_steps // 4 + 1)
        return det + exp

    # ---- 每回合更新 ----
    def update(self, obs, my_prev_orders):
        inv = dict((obs.get("market") or {}).get("inventory") or {})
        player = obs.get("player", 0)
        opp = 1 - player
        farms = obs.get("farms") or []
        shops = list((obs.get("town") or {}).get("unlocked_shops") or [])
        turn = obs["day"] * 24 + obs["hour"]

        if self.prev_inv is not None and POLICY["use_opp_ledger"]:
            drain = self.drain_at(turn - 1, self.prev_shops)
            for it in PRODUCTS:
                if it not in inv or it not in self.prev_inv:
                    continue
                delta = inv[it] - self.prev_inv[it]
                # delta = 双方净卖入 - drain  →  对手净卖 = delta + drain - 我方净卖
                opp_net = delta + drain[it] - self.prev_my_net.get(it, 0)
                if opp_net > 0.01:
                    self.opp_sold[it] += opp_net
                    self.opp_carry[it] = max(0.0, self.opp_carry[it] - opp_net)

        # 对手收获推断（tiles 公开）
        if opp < len(farms):
            tiles = farms[opp].get("tiles")
            if self.prev_opp_tiles is not None and tiles is not None and POLICY["use_opp_ledger"]:
                bs = len(tiles)
                for y in range(bs):
                    for x in range(bs):
                        old = self.prev_opp_tiles[y][x]
                        new = tiles[y][x] if y < len(tiles) else None
                        if not isinstance(old, dict):
                            continue
                        oy = old.get("yield_units", 0) or 0
                        ny = new.get("yield_units", 0) if isinstance(new, dict) else 0
                        if oy > ny:
                            if "animal" in old:
                                self.opp_carry[ANIMALS[old["animal"]]["product"]] += oy - ny
                            elif old.get("kind") == "PLANT":
                                self.opp_carry[old["crop"]] += oy - ny
            self.prev_opp_tiles = [list(row) for row in tiles] if tiles is not None else None

        self.prev_inv = inv
        self.prev_shops = shops
        # 记录本回合我方净卖（供下回合反解）
        net = {p: 0 for p in PRODUCTS}
        for o in my_prev_orders or []:
            if not isinstance(o, list) or len(o) < 3:
                continue
            if o[0] == "SELL" and o[1] in PRODUCTS:
                net[o[1]] += int(o[2])
            elif o[0] == "BUY_PRODUCT" and o[1] in PRODUCTS:
                net[o[1]] -= int(o[2])
        self.prev_my_net = net

    # ---- 对手供给预报 ----
    def opp_supply_eta(self, obs, item, window):
        """对手在未来 window 步内预计新增的该产品供给（碰撞预警）。"""
        player = obs.get("player", 0)
        farms = obs.get("farms") or []
        opp = 1 - player
        if opp >= len(farms) or not POLICY["use_opp_ledger"]:
            return 0.0
        tiles = farms[opp].get("tiles") or []
        day = obs["day"]
        horizon_day = (obs["day"] * 24 + obs["hour"] + window) // 24
        supply = self.opp_carry.get(item, 0.0)
        for row in tiles:
            for t in row:
                if not isinstance(t, dict):
                    continue
                if t.get("kind") == "PLANT" and t.get("crop") == item:
                    cd = CROPS[item]
                    mature = t["planted_day"] + cd["max_yield_day"]
                    if mature <= horizon_day:
                        supply += max(t.get("yield_units", 0), cd["max_yield"] * 0.7)
                elif "animal" in t and ANIMALS[t["animal"]]["product"] == item:
                    a = ANIMALS[t["animal"]]
                    days = max(0, horizon_day - day)
                    supply += t.get("yield_units", 0) + days / max(1, a["interval"])
        return supply


# ------------------------------------------------------------------
# WinLedger：终局模式
# ------------------------------------------------------------------
def _est_liquidation(items, prices):
    """按当前价打折估算一批货的可实现价值。"""
    return sum(n * max(1, prices.get(it, 0)) * 0.85 for it, n in items.items() if it in PRODUCTS)


def win_mode(obs, ledger, shed, prices):
    if not POLICY["use_win_modes"] or obs["day"] < POLICY["win_mode_from_day"]:
        return "NORMAL"
    player = obs.get("player", 0)
    farms = obs.get("farms") or []
    if len(farms) < 2:
        return "NORMAL"
    me, op = farms[player], farms[1 - player]
    mu_me = me["money"] + _est_liquidation(shed, prices) + _farm_residual(me, obs["day"])
    mu_op = op["money"] + _est_liquidation(ledger.opp_carry, prices) + _farm_residual(op, obs["day"])
    delta = mu_me - mu_op
    if delta > POLICY["win_margin"]:
        return "LOCK"
    if delta < -POLICY["win_margin"]:
        return "GAMBLE"
    return "NORMAL"


def _farm_residual(farm, day):
    """在场资产的剩余产出估值（粗粒度，只用于 Δ 判断）。"""
    days_left = max(0, 29 - day)
    val = 0.0
    for row in farm.get("tiles") or []:
        for t in row:
            if not isinstance(t, dict):
                continue
            if "animal" in t:
                a = ANIMALS[t["animal"]]
                per_day = MARKET_PARAMS[a["product"]]["base"] / max(1, a["interval"]) + 60
                val += per_day * days_left * 0.5
            elif t.get("kind") == "PLANT":
                val += t.get("yield_units", 0) * MARKET_PARAMS[t["crop"]]["base"] * 0.6
    return val


# ------------------------------------------------------------------
# Router：商店信号 → 组合调整
# ------------------------------------------------------------------
def route_update(st, obs):
    """在决策日调整 herd 目标与草莓激活状态；只动目标，不动几何。"""
    if not POLICY["use_router"]:
        st["straw_active"] = True
        return
    day = obs["day"]
    shops = list((obs.get("town") or {}).get("unlocked_shops") or [])
    yarn = shops.count("YARN_STORE")
    dairy = sum(1 for s in shops if "MILK" in SHOPS.get(s, []))
    straw = sum(1 for s in shops if "STRAWBERRY" in SHOPS.get(s, []))

    base_sheep = POLICY["herd"][0][1]
    base_cow = POLICY["herd"][1][1]
    tgt = {"SHEEP": base_sheep, "COW": base_cow}
    if yarn > 0:
        tgt["SHEEP"] = min(8, base_sheep + yarn * POLICY["sheep_per_yarn"])
    elif day >= POLICY["yarn_deadline_day"]:
        tgt["SHEEP"] = min(base_sheep, st.get("placed_sheep", 0) or base_sheep)
        tgt["COW"] = base_cow + 1
    if dairy >= 2:
        tgt["COW"] = max(tgt["COW"], base_cow + POLICY["cow_per_dairy2"])
    st["herd_target"] = [("SHEEP", tgt["SHEEP"]), ("COW", tgt["COW"])]
    # 草莓：默认激活（4/8 商店收它）；day9 后仍零草莓店才停止新种
    st["straw_active"] = not (day >= 9 and straw == 0)


# ------------------------------------------------------------------
# Executor：任务生成 + 全局指派
# ------------------------------------------------------------------
def _task_still_valid(tile, op):
    o = op[0]
    if o in ("BUILD_PASTURE", "BUILD_COOP", "PLANT"):
        return tile is None
    if o == "DIG":
        return isinstance(tile, dict) and tile.get("kind") == "WEED"
    if o == "PLACE":
        return isinstance(tile, dict) and tile.get("kind") in ("PASTURE", "COOP") and "animal" not in tile
    if not isinstance(tile, dict):
        return False
    if o == "WATER":
        return tile.get("kind") == "PLANT" and not tile.get("watered_today")
    if o == "FEED":
        return "animal" in tile and not tile.get("fed_today")
    if o == "CARE":
        return "animal" in tile and not tile.get("cared_today")
    if o == "COLLECT_FERTILIZER":
        return "animal" in tile and tile.get("fertilizer_available")
    if o == "FERTILIZE":
        return tile.get("kind") == "PLANT"
    if o == "HARVEST":
        return tile.get("yield_units", 0) > 0
    return False


def build_tasks(st, obs, farm, tiles, bs, seeds, shed, day, turn):
    """任务表：(priority, need_item, pos, op)。priority 小者先。"""
    roles = st["roles"]
    tasks = []
    animals, plants, weeds, empty, free_struct = [], [], [], [], []
    for y in range(bs):
        for x in range(bs):
            t = tiles[y][x]
            if t == "LOCKED":
                continue
            if t is None:
                empty.append((x, y))
            elif isinstance(t, dict):
                if "animal" in t:
                    animals.append(((x, y), t))
                elif t.get("kind") == "PLANT":
                    plants.append(((x, y), t))
                elif t.get("kind") == "WEED":
                    weeds.append((x, y))
                elif t.get("kind") in ("PASTURE", "COOP"):
                    free_struct.append(((x, y), t.get("kind")))
    st["placed_sheep"] = sum(1 for _, t in animals if t.get("animal") == "SHEEP")
    ebr = {}
    for p in empty:
        r = roles.get(p)
        if r in ("WHEAT", "MELON", "STRAWBERRY"):
            if r == "STRAWBERRY" and not st.get("straw_active"):
                r = "WHEAT"
            ebr[r] = ebr.get(r, 0) + 1
    st["empty_by_role"] = ebr
    st["n_starving"] = sum(1 for _, t in animals
                           if not t.get("fed_today") and t.get("consecutive_unfed", 0) >= 1)
    st["free_struct"] = free_struct
    st["n_animals"] = len(animals)

    # P0 生存线
    for pos, t in animals:
        if not t.get("fed_today") and t.get("consecutive_unfed", 0) >= 1:
            tasks.append((0, "WHEAT", pos, ["FEED"]))
    for pos, t in plants:
        if not t.get("watered_today") and t.get("consecutive_unwatered", 0) >= 1:
            tasks.append((0.5, None, pos, ["WATER"]))
    # P1 收获截止（一次性作物烂窗）
    for pos, t in plants:
        cd = CROPS[t["crop"]]
        if not cd["ongoing"] and t.get("yield_units", 0) > 0:
            rot_step = (t["planted_day"] + cd["max_yield_day"] + 1) * 24
            if turn >= rot_step - 26:
                tasks.append((1, None, pos, ["HARVEST"]))
    # P2 常规喂食 / P2.2 成熟一次性作物立即收（资本事件） / P3 常规浇水
    for pos, t in animals:
        if not t.get("fed_today"):
            tasks.append((2, "WHEAT", pos, ["FEED"]))
    for pos, t in plants:
        cd = CROPS[t["crop"]]
        if not cd["ongoing"] and t.get("yield_units", 0) > 0:
            age = day - t["planted_day"]
            if age >= cd["max_yield_day"] or t["yield_units"] >= cd["max_yield"]:
                tasks.append((2.2, None, pos, ["HARVEST"]))
    for pos, t in plants:
        if not t.get("watered_today"):
            tasks.append((3, None, pos, ["WATER"]))
    # P4 放置动物
    for animal in ("SHEEP", "COW", "GOOSE"):
        n_have = shed.get(animal, 0) + sum(inv.get(animal, 0) for inv in st["invs"])
        if n_have <= 0:
            continue
        slots = [p for p, k in free_struct if k == ANIMALS[animal]["structure"]]
        for p in slots[:n_have]:
            tasks.append((4, animal, p, ["PLACE", animal]))
    # P5 动物满仓收获 / P6 CARE
    for pos, t in animals:
        if t.get("yield_units", 0) >= ANIMALS[t["animal"]]["max_held"] - 1:
            tasks.append((5, None, pos, ["HARVEST"]))
    for pos, t in animals:
        if not t.get("cared_today"):
            tasks.append((6, None, pos, ["CARE"]))
    # P7 建栏 + 播种
    n_pens = sum(1 for p, k in free_struct if k == "PASTURE") + \
        sum(1 for _, t in animals if ANIMALS[t["animal"]]["structure"] == "PASTURE")
    for p in empty:
        if roles.get(p) == "ANIMAL" and n_pens < POLICY["n_animal_tiles"]:
            tasks.append((7, None, p, ["BUILD_PASTURE"]))
            n_pens += 1
    total_days = 30
    for p in empty:
        role = roles.get(p)
        if role in ("WHEAT", "MELON", "STRAWBERRY"):
            crop = role
            if crop == "STRAWBERRY" and not st.get("straw_active"):
                crop = "WHEAT"
            cd = CROPS[crop]
            need = cd["first_yield_day"] if cd["ongoing"] else cd["max_yield_day"]
            if day + need + 1 > total_days - 1:
                crop = "WHEAT"
                if day + CROPS["WHEAT"]["max_yield_day"] + 1 > total_days - 1:
                    continue
            if seeds.get(crop, 0) > 0:
                tasks.append((7.5, None, p, ["PLANT", crop]))
    # P8 施肥（ongoing 作物产出翻倍引擎）
    if POLICY["use_fertilize"]:
        for pos, t in plants:
            cd = CROPS[t["crop"]]
            if cd["ongoing"] and t.get("fertilized_until_day", -1) < day + 1:
                age = day - t["planted_day"]
                if age >= cd["first_yield_day"] - 3:
                    tasks.append((8, "FERTILIZER", pos, ["FERTILIZE"]))
    # P9 收肥料 / P10 收成熟作物与动物产出 / P11 清杂草
    for pos, t in animals:
        if t.get("fertilizer_available"):
            tasks.append((9, None, pos, ["COLLECT_FERTILIZER"]))
    for pos, t in plants:
        cd = CROPS[t["crop"]]
        age = day - t["planted_day"]
        if cd["ongoing"] and t.get("yield_units", 0) > 0 and age >= cd["first_yield_day"]:
            tasks.append((10, None, pos, ["HARVEST"]))
    for pos, t in animals:
        if t.get("yield_units", 0) > 0:
            tasks.append((10.5, None, pos, ["HARVEST"]))
    for p in weeds:
        if p in roles:
            tasks.append((11, None, p, ["DIG"]))
    return tasks


def assign(st, obs, tasks, positions, invs, tiles, bs, shed, need_sell_items, turn):
    """全局指派：任务×单位按 (pri*W + dist) 排序逐对绑定；保持既有绑定。"""
    n = len(positions)
    actions = [["PASS"] for _ in range(n)]
    used = set()
    claimed = set()
    shed_set = set(_shed_tiles(bs))

    def carried(i, item):
        return invs[i].get(item, 0)

    # 0) 已绑定任务继续执行
    for i in list(st["assign"].keys()):
        if i >= n:
            st["assign"].pop(i)
            continue
        pos_t, op, need = st["assign"][i]
        tile = tiles[pos_t[1]][pos_t[0]]
        if not _task_still_valid(tile, op) or (need and carried(i, need) <= 0):
            st["assign"].pop(i)
            continue
        if positions[i] == pos_t:
            actions[i] = op
            used.add(i)
            claimed.add((pos_t, op[0]))
            st["assign"].pop(i)
            _apply_local(invs, seeds_ref=st, i=i, op=op)
        else:
            actions[i] = _step_toward(positions[i], pos_t) or ["PASS"]
            used.add(i)
            claimed.add((pos_t, op[0]))

    # 0.5) 喂食供应链：有 FEED 任务但没有任何单位持麦 → 强制派最近单位去取麦
    n_feed_tasks = sum(1 for t in tasks if t[3][0] == "FEED")
    holders = sum(1 for i in range(n) if carried(i, "WHEAT") > 0 and i not in used)
    if n_feed_tasks > 0 and holders * 5 < n_feed_tasks and shed.get("WHEAT", 0) > 0:
        best = None
        for i in range(n):
            if i in used:
                continue
            d = _shed_dist(positions[i], bs)
            if best is None or d < best[0]:
                best = (d, i)
        if best:
            i = best[1]
            if positions[i] in shed_set:
                take = min(max(POLICY["carry_wheat"], n_feed_tasks), shed["WHEAT"])
                actions[i] = ["PICKUP", "WHEAT", take]
                shed["WHEAT"] -= take
                invs[i]["WHEAT"] = invs[i].get("WHEAT", 0) + take
            else:
                tgt = min(shed_set, key=lambda s: _dist(positions[i], s))
                actions[i] = _step_toward(positions[i], tgt) or ["PASS"]
            used.add(i)

    # 0.6) 动物放置供应链：shed 有动物 + 有空栏 + 无单位持动物 → 强制派人取
    shed_animals = [a for a in ANIMALS if shed.get(a, 0) > 0]
    if shed_animals and st.get("free_struct"):
        holding = sum(1 for i in range(n)
                      if any(invs[i].get(a, 0) > 0 for a in ANIMALS))
        if holding == 0:
            best = None
            for i in range(n):
                if i in used:
                    continue
                d = _shed_dist(positions[i], bs)
                if best is None or d < best[0]:
                    best = (d, i)
            if best:
                i = best[1]
                if positions[i] in shed_set:
                    a = shed_animals[0]
                    take = min(shed[a], 4)
                    actions[i] = ["PICKUP", a, take]
                    shed[a] -= take
                    invs[i][a] = invs[i].get(a, 0) + take
                else:
                    tgt = min(shed_set, key=lambda s: _dist(positions[i], s))
                    actions[i] = _step_toward(positions[i], tgt) or ["PASS"]
                used.add(i)

    # 1) 紧急入库：市场层要卖但 shed 没货、有单位大量携带 → 派去 DROP
    for it in need_sell_items:
        best = None
        for i in range(n):
            if i in used:
                continue
            if carried(i, it) >= 3:
                d = _shed_dist(positions[i], bs)
                if best is None or d < best[0]:
                    best = (d, i)
        if best:
            i = best[1]
            if positions[i] in shed_set:
                actions[i] = ["DROP"]
                invs[i] = {}
            else:
                tgt = min(shed_set, key=lambda s: _dist(positions[i], s))
                actions[i] = _step_toward(positions[i], tgt) or ["PASS"]
            used.add(i)

    # 2) 严格分层指派：优先级桶从高到低，桶内按距离贪心
    #    高优任务（喂食/救急浇水/资本收获）绝不被低优任务抢走单位。
    buckets = {}
    for tk in tasks:
        buckets.setdefault(int(tk[0]), []).append(tk)
    for b in sorted(buckets):
        cands = []
        for tk in buckets[b]:
            pri, need, pos_t, op = tk
            if (pos_t, op[0]) in claimed:
                continue
            for i in range(n):
                if i in used:
                    continue
                if need and carried(i, need) <= 0:
                    continue
                cands.append((_dist(positions[i], pos_t), pri, i, tk))
        cands.sort(key=lambda z: (z[0], z[1]))
        for _, pri, i, tk in cands:
            if i in used:
                continue
            _, need, pos_t, op = tk
            if (pos_t, op[0]) in claimed:
                continue
            claimed.add((pos_t, op[0]))
            used.add(i)
            if positions[i] == pos_t:
                actions[i] = op
                _apply_local(invs, seeds_ref=st, i=i, op=op)
            else:
                st["assign"][i] = (pos_t, op, need)
                actions[i] = _step_toward(positions[i], pos_t) or ["PASS"]

    # 3) 剩余空闲单位：需要补给（小麦/肥料/动物）就去 shed，否则待命不动
    need_wheat = any(t[1] == "WHEAT" for t in tasks)
    need_fert = any(t[1] == "FERTILIZER" for t in tasks)
    pend_animal = [a for a in ANIMALS if shed.get(a, 0) > 0]
    for i in range(n):
        if i in used:
            continue
        pos = positions[i]
        if pos in shed_set:
            if pend_animal and st.get("free_struct"):
                a = pend_animal[0]
                take = min(shed.get(a, 0), 4)
                if take > 0:
                    actions[i] = ["PICKUP", a, take]
                    invs[i][a] = invs[i].get(a, 0) + take
                    shed[a] -= take
                    used.add(i)
                    continue
            if need_wheat and carried(i, "WHEAT") < 2 and shed.get("WHEAT", 0) > 0:
                take = min(POLICY["carry_wheat"], shed["WHEAT"])
                actions[i] = ["PICKUP", "WHEAT", take]
                shed["WHEAT"] -= take
                invs[i]["WHEAT"] = invs[i].get("WHEAT", 0) + take
                used.add(i)
                continue
            if need_fert and carried(i, "FERTILIZER") < 1 and shed.get("FERTILIZER", 0) > 0:
                take = min(3, shed["FERTILIZER"])
                actions[i] = ["PICKUP", "FERTILIZER", take]
                shed["FERTILIZER"] -= take
                invs[i]["FERTILIZER"] = invs[i].get("FERTILIZER", 0) + take
                used.add(i)
                continue
        elif (need_wheat or need_fert or pend_animal):
            tgt = min(shed_set, key=lambda s: _dist(pos, s))
            actions[i] = _step_toward(pos, tgt) or ["PASS"]
            used.add(i)
    return actions


def _apply_local(invs, seeds_ref, i, op):
    """本地记账：让同回合后续决策看到扣减。"""
    if op[0] == "FEED":
        invs[i]["WHEAT"] = max(0, invs[i].get("WHEAT", 0) - 1)
    elif op[0] == "FERTILIZE":
        invs[i]["FERTILIZER"] = max(0, invs[i].get("FERTILIZER", 0) - 1)
    elif op[0] == "PLACE" and len(op) > 1 and op[1] in ANIMALS:
        invs[i][op[1]] = max(0, invs[i].get(op[1], 0) - 1)


# ------------------------------------------------------------------
# Market：坑内分批 + race + 终局
# ------------------------------------------------------------------
def _batch_size(item, inv, cap):
    """最大 q 使批末价 >= 批首价*(1-slip_tol)。"""
    p0 = market_price(item, inv)
    lo = max(1, int(p0 * (1 - POLICY["slip_tol"])))
    q = 0
    while q < cap and market_price(item, inv + q) >= lo:
        q += 1
    return max(1, q)


def market_orders(st, obs, ledger, farm, shed, seeds, prices, mode, terminal, turn):
    day, hour = obs["day"], obs["hour"]
    money = farm["money"]
    inv_mkt = dict((obs.get("market") or {}).get("inventory") or {})
    shops = list((obs.get("town") or {}).get("unlocked_shops") or [])
    sells, buys = [], []
    shed_used = sum(shed.values())
    need_sell_items = []

    if terminal:
        order = sorted((it for it in PRODUCTS if shed.get(it, 0) > 0),
                       key=lambda it: -prices.get(it, 0))
        for it in order:
            sells.append(["SELL", it, shed[it]])
        return sells[:MAX_ORDERS], []

    # ---- 肥料：预留给草莓后即收即卖 ----
    n_straw = st.get("n_active_straw", 0)
    fert_keep = int(n_straw * POLICY["fert_reserve_per_straw"]) if POLICY["use_fertilize"] else 0
    fert_extra = shed.get("FERTILIZER", 0) - fert_keep
    if fert_extra > 0:
        sells.append(["SELL", "FERTILIZER", fert_extra])

    # ---- 主产品卖出 ----
    feed_need = st.get("n_animals", 0) * POLICY["feed_stock_days"]
    for it in ("MELON", "STRAWBERRY", "MILK", "WOOL", "EGG", "TOMATO", "CARROT"):
        have = shed.get(it, 0)
        carried = sum(inv.get(it, 0) for inv in st["invs"])
        if have + carried <= 0:
            continue
        inv_i = inv_mkt.get(it, MARKET_PARAMS[it]["I0"])
        price = prices.get(it, 0)
        base = MARKET_PARAMS[it]["base"]
        in_hole = inv_i < MARKET_PARAMS[it]["I0"]
        urgent = False
        if in_hole:
            hole = ledger.remaining_drain(turn, shops, it)
            supply_soon = ledger.opp_supply_eta(obs, it, POLICY["race_lookahead"]) \
                if POLICY["use_race"] else 0.0
            my_stock = have + carried
            # 等待的边际收益：未来 ~5 天城镇继续吃出的价差
            wait_depth = int(min(hole, 120))
            wait_gain = market_price(it, int(inv_i) - wait_depth) - price
            if supply_soon >= 3 and my_stock > 0:
                urgent = True                     # race：对手供给逼近，先手出货
            elif hole < (my_stock + ledger.opp_carry.get(it, 0)) * 1.2:
                urgent = True                     # 坑不够分，先到先得
            elif wait_gain <= price * 0.04:
                urgent = True                     # 等也涨不了多少（melon 类小坑/平坑）
            elif price >= base * POLICY["premium_wait_margin"]:
                urgent = True                     # 价格已到目标
        else:
            urgent = price >= base * POLICY["glut_floor_frac"] or \
                shed_used > SHED_CAP - 15 or day >= POLICY["sell_late_day"]
        if mode == "GAMBLE" and it in ("MELON", "STRAWBERRY", "MILK", "WOOL") \
                and day < POLICY["gamble_hold_until_day"]:
            urgent = False                        # 落后：集中晚卖赌方差
        if mode == "LOCK":
            urgent = have > 0                     # 领先：见货即出，锁定确定性
        if urgent:
            if have > 0:
                cap = POLICY["batch_cap"] * (2 if (day >= POLICY["sell_late_day"]
                                                    or shed_used > SHED_CAP - 15) else 1)
                q = _batch_size(it, inv_i, cap)
                if POLICY["forced_flush"] and shed_used > SHED_CAP - 10:
                    q = max(q, cap)
                q = min(have, q)
                sells.append(["SELL", it, q])
            elif carried >= 3:
                need_sell_items.append(it)        # 让执行器派人紧急入库
    # 余粮小麦
    wheat_extra = shed.get("WHEAT", 0) - feed_need
    if wheat_extra > 3 and day >= POLICY["wheat_hoard_until_day"] and \
            prices.get("WHEAT", 0) >= MARKET_PARAMS["WHEAT"]["base"]:
        sells.append(["SELL", "WHEAT", min(wheat_extra, POLICY["batch_cap"])])

    # ---- 买入 ----
    reserve = POLICY["cash_reserve"] + 25 * feed_need
    if hour == 0:
        want = 0
        for d0, k in POLICY["hands_schedule"]:
            if day >= d0:
                want = k
        if mode == "LOCK" and day >= 27:
            want = min(want, 6)
        for _ in range(max(0, want - int(farm.get("hires_today", 0) or 0))):
            buys.append(["HIRE"])
    n_extra = len(farm.get("unlocked_quadrants") or ["NW"]) - 1
    if 0 <= n_extra < len(LAND_PRICES) and mode != "LOCK":
        quad = LAND_ORDER[n_extra]
        earliest = POLICY["buy_land_days"].get(quad)
        if earliest is not None and day >= earliest and \
                money >= LAND_PRICES[n_extra] + reserve + 600:
            buys.append(["BUY_LAND"])
    def _buy_seeds(money):
        empty_by_role = st.get("empty_by_role", {})
        for crop in ("MELON", "WHEAT", "STRAWBERRY"):
            if crop == "STRAWBERRY" and not st.get("straw_active"):
                continue
            cd = CROPS[crop]
            need_day = cd["first_yield_day"] if cd["ongoing"] else cd["max_yield_day"]
            if day + need_day + 1 > 29:
                continue
            demand = min(8, empty_by_role.get(crop, 0)) - seeds.get(crop, 0)
            if demand > 0:
                afford = max(0, int((money - 200) // CROPS[crop]["seed"]))
                n = min(demand, afford)
                if n > 0:
                    buys.append(["BUY_SEED", crop, n])
                    money -= CROPS[crop]["seed"] * n
        return money

    if day < POLICY["ipo_day"]:
        money = _buy_seeds(money)      # 阶段 A：种子先行（melon 铺量）

    # 动物（herd_target 由 Router 维护）
    if day <= POLICY["last_animal_day"] and shed_used < SHED_CAP - 5 and mode != "LOCK":
        placed = st.get("placed_counts", {})
        pending = {a: shed.get(a, 0) + sum(inv.get(a, 0) for inv in st["invs"]) for a in ANIMALS}
        free_pens = sum(1 for _, k in st.get("free_struct", []) if k == "PASTURE")
        if sum(pending.values()) < free_pens:
            bought = 0
            phase_herd = st["herd_target"] if day >= POLICY["ipo_day"] else POLICY["herd_early"]
            for animal, target in phase_herd:
                while bought < (2 if (day <= 2 or day >= POLICY["ipo_day"]) else 1):
                    have = placed.get(animal, 0) + pending.get(animal, 0)
                    cost = ANIMALS[animal]["cost"]
                    if have < target and money >= cost + reserve:
                        buys.append(["BUY_ANIMAL", animal, 1])
                        pending[animal] = pending.get(animal, 0) + 1
                        money -= cost
                        bought += 1
                    else:
                        break
                if bought >= (2 if day <= 2 else 1):
                    break

    if day >= POLICY["ipo_day"]:
        money = _buy_seeds(money)      # 阶段 B：动物优先后再补种子

    # 饲料：逢低囤 + 缺口补；动物濒饿时忽略价格上限、只留基础现金
    wheat_have = shed.get("WHEAT", 0) + sum(inv.get("WHEAT", 0) for inv in st["invs"])
    p_wheat = prices.get("WHEAT", 25)
    starving = st.get("n_starving", 0) > 0
    if st.get("n_animals", 0) > 0 or day < POLICY["wheat_hoard_until_day"]:
        cap_price = 10 ** 9 if starving else POLICY["wheat_buy_price_cap"]
        budget_floor = 100 if starving else POLICY["cash_reserve"]
        room = SHED_CAP - 10 - shed_used
        if wheat_have < feed_need and p_wheat <= cap_price and room > 0:
            n = min(feed_need - wheat_have, room,
                    max(0, int((money - budget_floor) // max(1, p_wheat))))
            if n > 0:
                buys.insert(0, ["BUY_PRODUCT", "WHEAT", n]) if not sells else \
                    buys.insert(0, ["BUY_PRODUCT", "WHEAT", n])

    return (sells + buys)[:MAX_ORDERS], need_sell_items


# ------------------------------------------------------------------
# 主入口
# ------------------------------------------------------------------
def _get_state(player, bs, turn):
    st = _STATE.get(player)
    if st is None or turn <= st.get("last_turn", -1):
        st = {
            "roles": _plan_roles(bs, POLICY),
            "assign": {}, "day": -1, "last_turn": -1,
            "ledger": MarketLedger(),
            "herd_target": list(POLICY["herd"]),
            "straw_active": True,
            "prev_orders": [],
        }
        _STATE[player] = st
    return st


def _decide(obs, config):
    farms = obs.get("farms") or []
    player = obs.get("player", 0)
    if not farms or player >= len(farms):
        return {"farmer": ["PASS"], "hands": [], "market": []}
    farm = farms[player]
    tiles = farm["tiles"]
    bs = len(tiles)
    day, hour = int(obs.get("day", 0)), int(obs.get("hour", 0))
    turn = day * 24 + hour

    st = _get_state(player, bs, turn)
    st["last_turn"] = turn
    if st["day"] != day:
        st["day"] = day
        st["assign"] = {}
        if day in POLICY["router_days"] and hour == 0 or st["day"] == -1:
            pass
    if hour == 0 and (day in POLICY["router_days"] or day == 0):
        route_update(st, obs)

    private = obs.get("private") or {}
    shed = dict(private.get("shed") or {})
    seeds = dict(private.get("seeds") or {})
    invs = [dict(i or {}) for i in (private.get("inventories") or [{}])]
    n_units = 1 + len(farm.get("hands") or [])
    while len(invs) < n_units:
        invs.append({})
    st["invs"] = invs
    prices = dict((obs.get("market") or {}).get("prices") or {})
    positions = [tuple(farm["farmer"])] + [tuple(p) for p in (farm.get("hands") or [])]

    ledger = st["ledger"]
    ledger.update(obs, st.get("prev_orders"))

    terminal = turn >= POLICY["terminal_turn"]
    mode = win_mode(obs, ledger, shed, prices)

    tasks = build_tasks(st, obs, farm, tiles, bs, seeds, shed, day, turn)
    st["placed_counts"] = {}
    for row in tiles:
        for t in row:
            if isinstance(t, dict) and "animal" in t:
                st["placed_counts"][t["animal"]] = st["placed_counts"].get(t["animal"], 0) + 1
    st["n_active_straw"] = sum(
        1 for row in tiles for t in row
        if isinstance(t, dict) and t.get("kind") == "PLANT" and t.get("crop") == "STRAWBERRY")

    market, need_sell = market_orders(st, obs, ledger, farm, shed, seeds, prices,
                                      mode, terminal, turn)

    if terminal:
        # 终局：全员回仓卸货 + 继续收获近处成熟物
        actions = [["PASS"] for _ in range(n_units)]
        shed_set = set(_shed_tiles(bs))
        claimed = set()
        for i in range(n_units):
            pos = positions[i]
            if invs[i] and any(it in PRODUCTS for it in invs[i]):
                if pos in shed_set:
                    actions[i] = ["DROP"]
                else:
                    actions[i] = _step_toward(pos, min(shed_set, key=lambda s: _dist(pos, s))) or ["PASS"]
            elif turn < POLICY["last_turn"] - 4:
                cand = [(pri, need, p, op) for (pri, need, p, op) in tasks
                        if op[0] == "HARVEST" and p not in claimed]
                if cand:
                    _, _, p, op = min(cand, key=lambda c: _dist(pos, c[2]))
                    claimed.add(p)
                    actions[i] = op if pos == p else (_step_toward(pos, p) or ["PASS"])
        st["assign"] = {}
    else:
        actions = assign(st, obs, tasks, positions, invs, tiles, bs, shed, need_sell, turn)

    st["prev_orders"] = market
    return {"farmer": actions[0], "hands": actions[1:n_units], "market": market}


def agent(obs, config=None):
    try:
        return _decide(obs, config)
    except Exception:
        farms = obs.get("farms") or []
        player = obs.get("player", 0)
        n = len(farms[player].get("hands") or []) if farms and player < len(farms) else 0
        return {"farmer": ["PASS"], "hands": [["PASS"]] * n, "market": []}
