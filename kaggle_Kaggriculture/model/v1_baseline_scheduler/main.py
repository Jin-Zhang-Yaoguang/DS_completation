"""Kaggriculture V1 baseline: deterministic livestock-core task scheduler.

设计取自公开社区调研（见 competition_description/public_solutions_survey.md）的共识事实，
但不复刻任何一份 replay 动作带：整局行为完全由当前 observation 现算。

核心结构
--------
1. 静态地块角色规划（ANIMAL / WHEAT / MELON / STRAWBERRY），按到 shed 的距离从近到远分配，
   把每天都要服务的畜牧地块压在 shed 旁边，把只需偶尔照料的作物推到外圈。
2. 每回合生成任务列表 → 贪心分配给农民与临时工 → 单位在任务完成前不换目标（抑制"来回走"）。
3. 市场层：SELL 永远排在 BUY 之前（引擎按 list index 逐单位结算）；肥料即收即卖；
   premium 走价格地板 + 小批量；终局全量清算。

引擎细节（已对 kaggle-environments 1.32.7 源码核对）
- 一回合内 field 动作先于 market 结算：同回合 DROP 的货可以同回合卖出。
- 最后一个会被执行的动作是 step 718（index 719 不执行）。
- 不读 obs["step"]（seat 1 的序列化观测里缺该字段），一律用 day * turnsPerDay + hour。
- FEED 消耗执行动作那个单位自己身上的 WHEAT，不是 shed 里的。
- 新种作物 consecutive_unwatered 初始为 1，当天不浇当晚变杂草；动物连续两天不喂永久逃走。
- shed 容量 100（不含种子），日终溢出被丢弃；买入的 wheat / 动物也占容量。
"""

# --------------------------------------------------------------------------
# 引擎常量（内联，保证提交包自包含）
# --------------------------------------------------------------------------
CROPS = {
    "WHEAT": {"seed": 10, "first_yield_day": 2, "max_yield_day": 4, "interval": 0, "max_yield": 6, "ongoing": False},
    "CARROT": {"seed": 20, "first_yield_day": 2, "max_yield_day": 3, "interval": 0, "max_yield": 4, "ongoing": False},
    "TOMATO": {"seed": 50, "first_yield_day": 8, "max_yield_day": 8, "interval": 1, "max_yield": 4, "ongoing": True},
    "STRAWBERRY": {"seed": 100, "first_yield_day": 10, "max_yield_day": 10, "interval": 2, "max_yield": 4, "ongoing": True},
    "MELON": {"seed": 80, "first_yield_day": 10, "max_yield_day": 12, "interval": 0, "max_yield": 6, "ongoing": False},
}
ANIMALS = {
    "GOOSE": {"cost": 300, "structure": "COOP", "first_yield_day": 4, "interval": 1, "max_held": 4, "product": "EGG"},
    "COW": {"cost": 400, "structure": "PASTURE", "first_yield_day": 8, "interval": 2, "max_held": 6, "product": "MILK"},
    "SHEEP": {"cost": 500, "structure": "PASTURE", "first_yield_day": 6, "interval": 3, "max_held": 6, "product": "WOOL"},
}
LAND_PRICES = [1000, 2000, 4000]
LAND_ORDER = ["NE", "SW", "SE"]
PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]
SHED_CAPACITY = 100
MAX_ORDERS = 10

# --------------------------------------------------------------------------
# 策略参数（本版全部为常量，后续版本可作为搜索维度）
# --------------------------------------------------------------------------
POLICY = {
    "herd": [("SHEEP", 4), ("COW", 6)],      # 目标畜群，按购买优先级排列
    "n_animal_tiles": 10,
    "n_wheat_tiles": 4,
    "n_melon_tiles": 18,
    "n_straw_tiles": 0,      # V1 的动作预算养不起草莓的每日浇水，见 README「已知缺口」
    "last_animal_day": 20,                    # 之后买动物来不及回本
    "hands_schedule": [(0, 5), (2, 8), (5, 10)],           # (起始日, 当日雇佣数)
    "cash_reserve": 400,                      # 任何非饲料支出后必须留下的现金
    "buy_land_days": {"NE": 3, "SW": 10},     # 最早买地日
    "feed_stock_days": 2,                     # shed 里保持几天的饲料
    "wheat_buy_price_cap": 70,                # 饲料买入价上限
    "carry_wheat": 6,                         # 每个"喂养工"一次带多少小麦
    "sell_floor": {"MELON": 90, "STRAWBERRY": 70, "MILK": 90, "WOOL": 110,
                   "EGG": 40, "WHEAT": 27, "CARROT": 30, "TOMATO": 40},
    "sell_batch": {"MELON": 6, "STRAWBERRY": 8, "MILK": 6, "WOOL": 5,
                   "EGG": 6, "WHEAT": 8, "CARROT": 8, "TOMATO": 8},
    "terminal_turn": 690,                     # 从这一步起只做清算
    "last_turn": 718,                         # 最后一个会被执行的 step
}

_STATE = {}


# --------------------------------------------------------------------------
# 基础工具
# --------------------------------------------------------------------------
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


def _plan_roles(bs):
    """把 NW -> NE -> SW 三个象限的地块按到 shed 的距离排序，依次分配角色。"""
    order = []
    for quad in ("NW", "NE", "SW"):
        tiles = [(x, y) for y in range(bs) for x in range(bs) if _quadrant(x, y, bs) == quad]
        tiles.sort(key=lambda t: (_shed_dist(t, bs), t[1], t[0]))
        order.extend(tiles)
    roles, i = {}, 0
    for role, n in (("ANIMAL", POLICY["n_animal_tiles"]),
                    ("WHEAT", POLICY["n_wheat_tiles"]),
                    ("MELON", POLICY["n_melon_tiles"]),
                    ("STRAWBERRY", POLICY["n_straw_tiles"])):
        for _ in range(n):
            if i < len(order):
                roles[order[i]] = role
                i += 1
    return roles


def _state_for(player, bs):
    st = _STATE.get(player)
    if st is None:
        st = {"roles": _plan_roles(bs), "day": -1, "assign": {}, "last_turn": -1}
        _STATE[player] = st
    return st


# --------------------------------------------------------------------------
# 农事判定
# --------------------------------------------------------------------------
def _needs_water(tile, day):
    return isinstance(tile, dict) and tile.get("kind") == "PLANT" and not tile.get("watered_today")


def _crop_ready(tile, day):
    if not (isinstance(tile, dict) and tile.get("kind") == "PLANT"):
        return False
    cd = CROPS[tile["crop"]]
    age = day - tile["planted_day"]
    if tile.get("yield_units", 0) <= 0 or age < cd["first_yield_day"]:
        return False
    if cd["ongoing"]:
        return True
    # 一次性作物：等长满再收（水浇满时 max_yield_day 的一半左右到顶）
    return age >= cd["max_yield_day"] or tile["yield_units"] >= cd["max_yield"]


def _plantable(crop, day, turns_per_day, total_days):
    """还来得及成熟 + 收获 + 运回 + 卖出吗？"""
    cd = CROPS[crop]
    need = cd["max_yield_day"] if not cd["ongoing"] else cd["first_yield_day"]
    return day + need + 1 <= total_days - 1


# --------------------------------------------------------------------------
# 主体
# --------------------------------------------------------------------------
def _decide(obs, config):
    farms = obs.get("farms") or []
    player = obs.get("player", 0)
    if not farms or player >= len(farms):
        return {"farmer": ["PASS"], "hands": [], "market": []}

    farm = farms[player]
    private = obs.get("private") or {}
    tiles = farm["tiles"]
    bs = len(tiles)
    turns_per_day = int((config or {}).get("turnsPerDay", 24) or 24)
    total_days = max(1, int((config or {}).get("episodeSteps", 720) or 720) // turns_per_day)
    day = int(obs.get("day", 0))
    hour = int(obs.get("hour", 0))
    turn = day * turns_per_day + hour          # 不读 obs["step"]

    st = _state_for(player, bs)
    if turn <= st["last_turn"]:                # 同一进程跑新的一局
        _STATE[player] = st = {"roles": _plan_roles(bs), "day": -1, "assign": {}, "last_turn": -1}
    st["last_turn"] = turn
    if st["day"] != day:                       # 每天早上单位重置，清空任务绑定
        st["day"] = day
        st["assign"] = {}

    roles = st["roles"]
    shed = dict(private.get("shed") or {})
    seeds = dict(private.get("seeds") or {})
    invs = [dict(i or {}) for i in (private.get("inventories") or [{}])]
    prices = dict((obs.get("market") or {}).get("prices") or {})
    money = farm["money"]
    n_units = 1 + len(farm.get("hands") or [])
    while len(invs) < n_units:
        invs.append({})

    positions = [tuple(farm["farmer"])] + [tuple(p) for p in (farm.get("hands") or [])]
    shed_set = set(_shed_tiles(bs))
    terminal = turn >= POLICY["terminal_turn"]

    # ---------------- 场上盘点 ----------------
    animals, plants, weeds, empty = [], [], [], []
    free_struct = []
    for y in range(bs):
        for x in range(bs):
            t = tiles[y][x]
            if t == "LOCKED":
                continue
            if t is None:
                empty.append((x, y))
            elif isinstance(t, dict):
                k = t.get("kind")
                if "animal" in t:
                    animals.append(((x, y), t))
                elif k == "PLANT":
                    plants.append(((x, y), t))
                elif k == "WEED":
                    weeds.append((x, y))
                elif k in ("COOP", "PASTURE"):
                    free_struct.append(((x, y), k))

    # ---------------- 任务生成 ----------------
    # (priority, need_wheat, need_item, pos, op)
    tasks = []
    if not terminal:
        for pos, t in animals:                                   # 0 濒死动物
            if not t.get("fed_today") and t.get("consecutive_unfed", 0) >= 1:
                tasks.append((0, True, None, pos, ["FEED"]))
        for pos, t in plants:                                    # 1 今晚会枯死的作物
            if _needs_water(t, day) and t.get("consecutive_unwatered", 0) >= 1:
                tasks.append((1, False, None, pos, ["WATER"]))
        for pos, t in animals:                                   # 2 常规喂食
            if not t.get("fed_today"):
                tasks.append((2, True, None, pos, ["FEED"]))
        for pos, t in plants:                                    # 3 常规浇水
            if _needs_water(t, day) and t.get("consecutive_unwatered", 0) < 1:
                tasks.append((3, False, None, pos, ["WATER"]))
        for animal in ("SHEEP", "COW"):                          # 4 放置在手的动物
            n_have = shed.get(animal, 0) + sum(inv.get(animal, 0) for inv in invs)
            if n_have <= 0:
                continue
            slots = [p for p, k in free_struct if k == ANIMALS[animal]["structure"]]
            for p in slots[:n_have]:
                tasks.append((4, False, animal, p, ["PLACE", animal]))
        for pos, t in animals:                                   # 5 快满仓的产出
            cap = ANIMALS[t["animal"]]["max_held"]
            if t.get("yield_units", 0) >= max(1, cap - 1):
                tasks.append((5, False, None, pos, ["HARVEST"]))
        for pos, t in animals:                                   # 6 CARE（把日产从 1 提到 2）
            if not t.get("cared_today"):
                tasks.append((6, False, None, pos, ["CARE"]))
        for p in empty:                                          # 7 建畜栏
            if roles.get(p) == "ANIMAL":
                tasks.append((7, False, None, p, ["BUILD_PASTURE"]))
        for p in empty:                                          # 7 播种（本位作物来不及就退回小麦）
            role = roles.get(p)
            if role not in ("WHEAT", "MELON", "STRAWBERRY"):
                continue
            if not _plantable(role, day, turns_per_day, total_days):
                role = "WHEAT"
            if seeds.get(role, 0) > 0 and _plantable(role, day, turns_per_day, total_days):
                tasks.append((7, False, None, p, ["PLANT", role]))
        for pos, t in animals:                                   # 8 捡肥料（每动作收益仅次于甜瓜）
            if t.get("fertilizer_available"):
                tasks.append((8, False, None, pos, ["COLLECT_FERTILIZER"]))
        for pos, t in plants:                                    # 9 收作物
            if _crop_ready(t, day):
                tasks.append((9, False, None, pos, ["HARVEST"]))
        for pos, t in animals:                                   # 10 收零散产出
            if t.get("yield_units", 0) > 0:
                tasks.append((10, False, None, pos, ["HARVEST"]))
        for p in weeds:                                          # 11 清掉计划地块上的杂草
            if p in roles:
                tasks.append((11, False, None, p, ["DIG"]))

    tasks.sort(key=lambda z: z[0])

    # ---------------- 分配 ----------------
    claimed = set(v[0] for v in st["assign"].values() if v)
    actions = [["PASS"] for _ in range(n_units)]
    used_units = set()

    def carried_wheat(i):
        return invs[i].get("WHEAT", 0)

    def carried_value(i):
        return sum(n * max(1, prices.get(it, 0)) for it, n in invs[i].items() if it in PRODUCTS)

    # 终局：全员回 shed 卸货
    if terminal:
        for i in range(n_units):
            pos = positions[i]
            if invs[i]:
                if pos in shed_set:
                    actions[i] = ["DROP"]
                else:
                    target = min(shed_set, key=lambda s: _dist(pos, s))
                    actions[i] = _step_toward(pos, target) or ["PASS"]
            elif turn < POLICY["last_turn"] - 2:
                # 还有时间就继续把成熟产物收回来
                cand = [(p, t) for p, t in animals if t.get("yield_units", 0) > 0] + \
                       [(p, t) for p, t in plants if _crop_ready(t, day)]
                cand = [c for c in cand if c[0] not in claimed]
                if cand:
                    p = min(cand, key=lambda c: _dist(positions[i], c[0]))[0]
                    claimed.add(p)
                    if positions[i] == p:
                        actions[i] = ["HARVEST"]
                    else:
                        actions[i] = _step_toward(positions[i], p) or ["PASS"]
        st["assign"] = {}
    else:
        # 1) 先执行已绑定的任务
        for i in range(n_units):
            a = st["assign"].get(i)
            if not a:
                continue
            pos, op, need_w = a[0], a[1], a[2]
            tile = tiles[pos[1]][pos[0]] if 0 <= pos[0] < bs and 0 <= pos[1] < bs else None
            still = _task_still_valid(tile, op, day)
            if not still or (need_w and carried_wheat(i) <= 0):
                st["assign"].pop(i, None)
                claimed.discard(pos)
                continue
            if positions[i] == pos:
                actions[i] = op
                used_units.add(i)
                st["assign"].pop(i, None)
                claimed.discard(pos)
            else:
                actions[i] = _step_toward(positions[i], pos) or ["PASS"]
                used_units.add(i)

        # 2) 空闲单位：卸货 / 取小麦 / 取动物 / 领新任务
        need_wheat_tasks = any(t[1] for t in tasks)
        pending_animals = sum(shed.get(a, 0) for a in ANIMALS)
        free_slots = len(free_struct)
        for i in range(n_units):
            if i in used_units:
                continue
            pos = positions[i]
            # 满载或身上有价值物 -> 回 shed（携带待放置动物时除外）
            holds_animal_now = any(invs[i].get(a, 0) > 0 for a in ANIMALS)
            if not holds_animal_now and (carried_value(i) >= 600 or sum(invs[i].values()) >= 12):
                if pos in shed_set:
                    actions[i] = ["DROP"]
                    invs[i] = {}
                else:
                    actions[i] = _step_toward(pos, min(shed_set, key=lambda s: _dist(pos, s))) or ["PASS"]
                used_units.add(i)
                continue
            # 在 shed 边上：先卸产物，再补给（绝不把待放置的动物丢回仓库）
            if pos in shed_set:
                holds_animal = any(invs[i].get(a, 0) > 0 for a in ANIMALS)
                spare_products = [it for it in invs[i]
                                  if it in PRODUCTS and not (it == "WHEAT" and need_wheat_tasks)]
                if spare_products and not holds_animal:
                    actions[i] = ["DROP"]
                    invs[i] = {}
                    used_units.add(i)
                    continue
                if not holds_animal and pending_animals > 0 and free_slots > 0:
                    for a in ("SHEEP", "COW", "GOOSE"):
                        if shed.get(a, 0) > 0:
                            take = min(shed[a], free_slots)
                            actions[i] = ["PICKUP", a, take]
                            invs[i][a] = invs[i].get(a, 0) + take
                            shed[a] -= take
                            pending_animals = sum(shed.get(z, 0) for z in ANIMALS)
                            used_units.add(i)
                            break
                    if i in used_units:
                        continue
                if need_wheat_tasks and carried_wheat(i) < 2 and shed.get("WHEAT", 0) > 0:
                    take = min(POLICY["carry_wheat"], shed["WHEAT"])
                    actions[i] = ["PICKUP", "WHEAT", take]
                    shed["WHEAT"] -= take
                    invs[i]["WHEAT"] = invs[i].get("WHEAT", 0) + take
                    used_units.add(i)
                    continue
            # 领任务
            best = None
            for t in tasks:
                pri, need_w, need_item, tpos, op = t
                if tpos in claimed:
                    continue
                if need_w and carried_wheat(i) <= 0:
                    continue
                if need_item and invs[i].get(need_item, 0) <= 0:
                    continue
                d = _dist(pos, tpos)
                score = pri * 4 + d
                if best is None or score < best[0]:
                    best = (score, t)
            if best is None:
                # 没活干就往 shed 靠，方便下一轮补给
                if pos not in shed_set:
                    actions[i] = _step_toward(pos, min(shed_set, key=lambda s: _dist(pos, s))) or ["PASS"]
                continue
            _, (pri, need_w, need_item, tpos, op) = best
            claimed.add(tpos)
            if pos == tpos:
                actions[i] = op
                if op[0] == "FEED":
                    invs[i]["WHEAT"] = max(0, invs[i].get("WHEAT", 0) - 1)
                if op[0] == "PLACE":
                    invs[i][op[1]] = max(0, invs[i].get(op[1], 0) - 1)
                if op[0] == "PLANT":
                    seeds[op[1]] = max(0, seeds.get(op[1], 0) - 1)
            else:
                st["assign"][i] = (tpos, op, need_w)
                actions[i] = _step_toward(pos, tpos) or ["PASS"]
            used_units.add(i)

    # ---------------- 市场层 ----------------
    shed0 = dict(private.get("shed") or {})
    inv0 = [dict(i or {}) for i in (private.get("inventories") or [{}])]
    market = _market_orders(obs, farm, shed0, inv0, seeds, prices, money, day, hour, turn,
                            turns_per_day, total_days, animals, free_struct, roles, terminal)

    return {"farmer": actions[0], "hands": actions[1:], "market": market[:MAX_ORDERS]}


def _task_still_valid(tile, op, day):
    o = op[0]
    if o == "BUILD_PASTURE":
        return tile is None
    if o == "PLANT":
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
    if o == "HARVEST":
        return tile.get("yield_units", 0) > 0
    return False


def _market_orders(obs, farm, shed, invs, seeds, prices, money, day, hour, turn,
                   turns_per_day, total_days, animals, free_struct, roles, terminal):
    sells, buys = [], []
    shed_used = sum(v for k, v in shed.items())
    n_animals = len(animals)

    # ---- 卖 ----
    if terminal:
        for item in PRODUCTS:
            if shed.get(item, 0) > 0:
                sells.append(["SELL", item, shed[item]])
        return sells[:MAX_ORDERS]

    if shed.get("FERTILIZER", 0) > 0:            # 肥料只会贬值，收到就卖
        sells.append(["SELL", "FERTILIZER", shed["FERTILIZER"]])

    feed_need = max(0, n_animals * POLICY["feed_stock_days"])
    for item in ("MELON", "STRAWBERRY", "MILK", "WOOL", "EGG", "CARROT", "TOMATO"):
        have = shed.get(item, 0)
        if have <= 0:
            continue
        floor = POLICY["sell_floor"].get(item, 0)
        if prices.get(item, 0) < floor and shed_used < SHED_CAPACITY - 20:
            continue                              # 价太低且仓里还有地方 -> 等
        sells.append(["SELL", item, min(have, POLICY["sell_batch"].get(item, 6))])
    wheat_extra = shed.get("WHEAT", 0) - feed_need
    if wheat_extra > 0 and prices.get("WHEAT", 0) >= POLICY["sell_floor"]["WHEAT"]:
        sells.append(["SELL", "WHEAT", min(wheat_extra, POLICY["sell_batch"]["WHEAT"])])

    # ---- 买 ----
    reserve = POLICY["cash_reserve"] + 25 * feed_need
    # 雇工（占订单槽，只在每天第 0 回合做）
    if hour == 0 and not terminal:
        want = 0
        for d0, k in POLICY["hands_schedule"]:
            if day >= d0:
                want = k
        already = int(farm.get("hires_today", 0) or 0)
        for _ in range(max(0, want - already)):
            buys.append(["HIRE"])
    # 买地
    n_extra = len(farm.get("unlocked_quadrants") or ["NW"]) - 1
    if 0 <= n_extra < len(LAND_PRICES):
        quad = LAND_ORDER[n_extra]
        earliest = POLICY["buy_land_days"].get(quad)
        if earliest is not None and day >= earliest and money >= LAND_PRICES[n_extra] + reserve + 600:
            buys.append(["BUY_LAND"])
    # 买动物：只在还有空畜栏、还来得及回本、且现金够时买，一回合最多一头
    n_pending = sum(shed.get(a, 0) for a in ANIMALS) + \
        sum(inv.get(a, 0) for inv in invs for a in ANIMALS)
    n_slots_planned = sum(1 for p in roles if roles[p] == "ANIMAL")
    if (day <= POLICY["last_animal_day"] and shed_used < SHED_CAPACITY - 5
            and n_pending < max(0, len(free_struct))
            and n_animals + n_pending < n_slots_planned):
        placed = {}
        for _, t in animals:
            placed[t["animal"]] = placed.get(t["animal"], 0) + 1
        for animal, target in POLICY["herd"]:
            have = placed.get(animal, 0) + shed.get(animal, 0) + \
                sum(inv.get(animal, 0) for inv in invs)
            cost = ANIMALS[animal]["cost"]
            if have < target and money >= cost + reserve:
                buys.append(["BUY_ANIMAL", animal, 1])
                money -= cost
                break
    # 买种
    for crop, want in (("MELON", 4), ("WHEAT", 4), ("STRAWBERRY", 2)):
        if not _plantable(crop, day, turns_per_day, total_days):
            continue
        if seeds.get(crop, 0) < want and money >= CROPS[crop]["seed"] * 2 + reserve:
            n = want - seeds.get(crop, 0)
            buys.append(["BUY_SEED", crop, n])
            money -= CROPS[crop]["seed"] * n
    # 买饲料
    if n_animals > 0 and shed.get("WHEAT", 0) < feed_need and shed_used < SHED_CAPACITY - 10:
        p = prices.get("WHEAT", 25)
        if p <= POLICY["wheat_buy_price_cap"]:
            n = min(feed_need - shed.get("WHEAT", 0),
                    SHED_CAPACITY - 10 - shed_used,
                    max(0, int((money - POLICY["cash_reserve"]) // max(1, p))))
            if n > 0:
                buys.append(["BUY_PRODUCT", "WHEAT", n])

    return (sells + buys)[:MAX_ORDERS]           # SELL 必须排在 BUY 之前


def agent(obs, config=None):
    try:
        return _decide(obs, config)
    except Exception:
        farms = obs.get("farms") or []
        player = obs.get("player", 0)
        n = 0
        if farms and player < len(farms):
            n = len(farms[player].get("hands") or [])
        return {"farmer": ["PASS"], "hands": [["PASS"]] * n, "market": []}
