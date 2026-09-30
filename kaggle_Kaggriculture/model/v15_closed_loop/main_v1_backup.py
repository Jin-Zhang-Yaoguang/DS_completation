"""V15 闭环调度器：每步由观测现算动作的可重排执行器（原创，不回放任何 tape）。

设计要点（来自对 V120 路线与引擎源码的解剖）：
- 布局：动物压在棚接入格及其一环/二环（喂养/照料/收肥/收产品/入库零距离），作物按离棚距离由近到远。
- 每步：盘点 → 任务表（带优先级） → 单位粘性贪心分配 → 移动/执行；产品由日终自动入库，
  但为了当天能卖，高价值品收获后就近入库。
- 市场：SELL 排在 BUY 前；饲料小麦按需 BUY_PRODUCT；动物/土地/种子按日计划与现金闸门购买。
- 宏观计划（每天买什么、雇几人）作为参数表，可被 V15_PARAMS 覆盖，用于后续搜索。
"""
import os, json

BS = 10
ACCESS = [(4, 4), (5, 4), (4, 5), (5, 5)]  # NW, NE, SW, SE 顺序
QUAD_OF = lambda x, y: ("N" if y < 5 else "S") + ("W" if x < 5 else "E")
MOVES = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}
CROPS = {
    "WHEAT": dict(seed=10, first=2, maxday=4, interval=0, maxy=6, ongoing=False),
    "CARROT": dict(seed=20, first=2, maxday=3, interval=0, maxy=4, ongoing=False),
    "TOMATO": dict(seed=50, first=8, maxday=8, interval=1, maxy=4, ongoing=True),
    "STRAWBERRY": dict(seed=100, first=10, maxday=10, interval=2, maxy=4, ongoing=True),
    "MELON": dict(seed=80, first=10, maxday=12, interval=0, maxy=6, ongoing=False),
}
ANIMALS = {"GOOSE": dict(cost=300, struct="COOP", first=4, interval=1, held=4, product="EGG"),
           "COW": dict(cost=400, struct="PASTURE", first=8, interval=2, held=6, product="MILK"),
           "SHEEP": dict(cost=500, struct="PASTURE", first=6, interval=3, held=6, product="WOOL")}
PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]
BASE = {"WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120, "MELON": 250, "EGG": 50, "MILK": 160, "WOOL": 200, "FERTILIZER": 100}
LAND_ORDER = ["NE", "SW", "SE"]; LAND_PRICES = [1000, 2000, 4000]
FIB = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987]

# ---------------- 宏观计划（默认对齐 V120 路线，可覆盖） ----------------
DEFAULT_PLAN = {
    "hands": {0: 5, 1: 4, 2: 4, 3: 5, 4: 5, 5: 4, 6: 8, 7: 11, 8: 12, 9: 12, 10: 12},   # 其余天默认 12
    "hands_default": 12,
    "animals": {0: [["COW", 2], ["SHEEP", 2]], 3: [["COW", 1]], 5: [["COW", 1]], 7: [["COW", 2], ["SHEEP", 1]],
                8: [["SHEEP", 1]], 9: [["COW", 2]], 11: [["COW", 2]]},
    "land": {6: 1, 11: 1},                       # 当天购买地块数
    "melon_tiles": 12, "melon_day": 0,
    "straw": {5: 4, 6: 8, 7: 4, 8: 4, 11: 13},   # 每天新增草莓地块数
    "wheat_tiles": 7,                            # 早期小麦轮作地块数
    "wheat_tiles_mid": 14,                       # 第 6 天后
    "wheat_tiles_late": 40,                      # 第 11 天后
    "animal_cash_reserve": 60,
    "feed_reserve_days": 2, "wheat_buy_cap": 70,
    "fert_reserve": 6, "fertilize_crops": ["STRAWBERRY"],
    "sell_asap": True,
    "harvest_wheat_age": 4,
    "last_plant_day": {"WHEAT": 25, "CARROT": 26, "STRAWBERRY": 16, "MELON": 15, "TOMATO": 18},
}
_raw = os.environ.get("V15_PARAMS", "")
PLAN = dict(DEFAULT_PLAN)
if _raw:
    _ov = json.load(open(_raw)) if os.path.exists(_raw) else json.loads(_raw)
    for k, v in _ov.items():
        if isinstance(v, dict) and isinstance(PLAN.get(k), dict):
            d = dict(PLAN[k]); d.update({(int(kk) if str(kk).lstrip("-").isdigit() else kk): vv for kk, vv in v.items()}); PLAN[k] = d
        else:
            PLAN[k] = v

_S = {}


def _dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _step_toward(src, dst):
    dx, dy = dst[0] - src[0], dst[1] - src[1]
    if abs(dx) >= abs(dy) and dx != 0:
        return ["EAST"] if dx > 0 else ["WEST"]
    if dy != 0:
        return ["SOUTH"] if dy > 0 else ["NORTH"]
    if dx != 0:
        return ["EAST"] if dx > 0 else ["WEST"]
    return ["PASS"]


def _nearest_access(pos, unlocked):
    cands = [a for a in ACCESS]  # 站在 LOCKED 接入格上也允许入库/取货
    return min(cands, key=lambda a: _dist(pos, a))


def _layout(unlocked):
    """按离棚中心距离排序的可用地块；返回 (pasture_order, crop_order)。"""
    tiles = [(x, y) for y in range(BS) for x in range(BS) if QUAD_OF(x, y) in unlocked]
    center = (4.5, 4.5)
    key = lambda t: (abs(t[0] - center[0]) + abs(t[1] - center[1]), t[1], t[0])
    tiles.sort(key=key)
    return tiles


def _state(seat, turn):
    st = _S.get(seat)
    if st is None or turn <= st["last"]:
        st = {"last": -1, "task": {}, "feed_carry": {}, "hired_step": -1, "planted_day": {}, "straw_tiles": set(), "melon_tiles": set(),
              "pasture_plan": [], "crop_plan": [], "bought_animals": 0, "land_bought": 0, "day_plan": {}}
        _S[seat] = st
    st["last"] = turn
    return st


class Task:
    __slots__ = ("kind", "target", "ops", "prio", "key")

    def __init__(self, kind, target, ops, prio, key=None):
        self.kind, self.target, self.ops, self.prio = kind, tuple(target), list(ops), prio
        self.key = key or (kind, self.target)


def agent(obs, configuration=None):
    try:
        return _agent(obs)
    except Exception:
        farms = obs.get("farms") or []
        p = int(obs.get("player", 0) or 0)
        n = len(farms[p].get("hands") or []) if farms and p < len(farms) else 0
        return {"farmer": ["PASS"], "hands": [["PASS"]] * n, "market": []}


def _agent(obs):
    seat = int(obs.get("player", 0) or 0)
    day = int(obs.get("day", 0) or 0); hour = int(obs.get("hour", 0) or 0); turn = day * 24 + hour
    farm = obs["farms"][seat]; private = obs.get("private") or {}
    tiles = farm["tiles"]; money = float(farm.get("money") or 0)
    unlocked = list(farm.get("unlocked_quadrants") or ["NW"])
    shed = dict(private.get("shed") or {}); seeds = dict(private.get("seeds") or {})
    invs = [dict(i or {}) for i in (private.get("inventories") or [{}])]
    positions = [tuple(farm["farmer"])] + [tuple(h) for h in (farm.get("hands") or [])]
    n_units = len(positions)
    while len(invs) < n_units: invs.append({})
    market_prices = dict((obs.get("market") or {}).get("prices") or {})
    shops = list((obs.get("town") or {}).get("unlocked_shops") or [])
    st = _state(seat, turn)
    last_day = 29
    ENDGAME = turn >= 24 * 29 + 18

    # ---------- 盘点 ----------
    def T(x, y): return tiles[y][x]
    animal_tiles, plant_tiles, weed_tiles, empty_tiles, struct_empty = [], [], [], [], []
    for y in range(BS):
        for x in range(BS):
            t = tiles[y][x]
            if t == "LOCKED": continue
            if t is None: empty_tiles.append((x, y))
            elif isinstance(t, dict):
                if "animal" in t: animal_tiles.append((x, y))
                elif t.get("kind") == "PLANT": plant_tiles.append((x, y))
                elif t.get("kind") == "WEED": weed_tiles.append((x, y))
                elif t.get("kind") in ("PASTURE", "COOP"): struct_empty.append((x, y))
    n_animals = len(animal_tiles)

    # ---------- 布局计划（每步重算，便宜） ----------
    order = _layout(unlocked)
    n_past_target = n_animals + len(struct_empty) + sum(int(shed.get(a, 0)) for a in ANIMALS)
    # 计划中的牧场地块：已有结构/动物 + 离棚最近的空位补足到 目标数
    pasture_set = set(animal_tiles) | set(struct_empty)
    carried = sum(int(i.get(a, 0)) for i in invs for a in ANIMALS)
    want_past = max(0, sum(int(shed.get(a, 0)) for a in ANIMALS) + carried - len(struct_empty))
    for t in order:
        if want_past <= 0: break
        if t in empty_tiles and t not in pasture_set:
            pasture_set.add(t); want_past -= 1
    build_tiles = [t for t in pasture_set if t in empty_tiles]

    # ---------- 任务表 ----------
    tasks = []
    unfed = [(x, y) for (x, y) in animal_tiles if not T(x, y).get("fed_today")]
    for (x, y) in animal_tiles:
        t = T(x, y); ops = []
        if not t.get("fed_today"): ops.append(["FEED"])
        if not t.get("cared_today") and not ENDGAME: ops.append(["CARE"])
        if t.get("fertilizer_available"): ops.append(["COLLECT_FERTILIZER"])
        yu = int(t.get("yield_units", 0) or 0); held = ANIMALS[t["animal"]]["held"]
        if yu > 0 and (yu >= held - 1 or day >= last_day or hour >= 12 or yu >= 2): ops.append(["HARVEST"])
        if ops:
            prio = 0 if (not t.get("fed_today") and int(t.get("consecutive_unfed", 0) or 0) >= 1) else (3 if not t.get("fed_today") else 6)
            tasks.append(Task("animal", (x, y), ops, prio))
    for (x, y) in plant_tiles:
        t = T(x, y); cd = CROPS[t["crop"]]; age = day - int(t.get("planted_day", day)); ops = []
        yu = int(t.get("yield_units", 0) or 0)
        if not t.get("watered_today") and day < last_day + 1:
            if cd["ongoing"] or age <= cd["maxday"]:
                ops.append(["WATER"])
        harvest = False
        if cd["ongoing"]:
            harvest = yu >= 2 or (yu >= 1 and (day >= last_day or hour >= 18))
        else:
            harvest = (yu > 0 and (age >= cd["maxday"] or day >= last_day)) or (yu > 0 and age >= cd["maxday"] - 1 and hour >= 20)
        # 非持续作物：当天先浇再收（浇水立即加产）
        if harvest and (not t.get("watered_today")) and (not cd["ongoing"]) and age <= cd["maxday"] and ["WATER"] not in ops:
            ops.insert(0, ["WATER"])
        if harvest: ops.append(["HARVEST"])
        if ops:
            urgent = (not t.get("watered_today")) and int(t.get("consecutive_unwatered", 0) or 0) >= 1
            prio = 1 if urgent else (4 if ["WATER"] in ops else 5)
            if ENDGAME and harvest: prio = 2
            tasks.append(Task("plant", (x, y), ops, prio))
    # 建牧场 / 放动物
    for t in build_tiles:
        tasks.append(Task("build", t, [["BUILD_PASTURE"]], 2))
    shed_animals = [(a, int(shed.get(a, 0))) for a in ANIMALS if int(shed.get(a, 0)) > 0]
    # 种植
    plant_wish = _plant_wishes(day, hour, empty_tiles, pasture_set, order, seeds, st)
    for (x, y), crop in plant_wish:
        tasks.append(Task("plant_new", (x, y), [["PLANT", crop], ["WATER"]], 5 if day < 12 else 6))
    # 除草（占计划地块的杂草）
    for (x, y) in weed_tiles:
        tasks.append(Task("dig", (x, y), [["DIG"]], 7))

    # ---------- 分配与执行 ----------
    unit_actions = [["PASS"] for _ in range(n_units)]
    # 放动物：作为普通高优先级任务（先去棚取，再走到空结构放置）
    free_structs = list(struct_empty)
    for a, n in shed_animals:
        for _ in range(n):
            if not free_structs: break
            tgt = free_structs.pop(0)
            tasks.append(Task("place", ACCESS[0], [["PICKUP", a, 1], ("GOTO", tgt), ["PLACE", a]], 2, key=("place", tgt)))
    task_by_key = {t.key: t for t in tasks}
    # 粘性：已开始（ops 含 GOTO 前缀或 kind 为 place/deposit）的任务不重置 ops；否则若任务仍存在则刷新 ops
    for u in list(st["task"].keys()):
        if u >= n_units: st["task"].pop(u, None)
    claimed = set()
    for u in range(n_units):
        cur = st["task"].get(u)
        if cur is None: continue
        started = cur.kind in ("place", "deposit") or any(isinstance(op, tuple) for op in cur.ops)
        fresh = task_by_key.get(cur.key)
        if started:
            if cur.kind == "place" and fresh is None and not any(isinstance(op, tuple) for op in cur.ops):
                pass  # 已取到动物，正在走向目标：保留
            claimed.add(cur.key); continue
        if fresh is None or not fresh.ops:
            st["task"].pop(u, None); continue
        cur.ops = list(fresh.ops); cur.prio = fresh.prio; claimed.add(cur.key)
    tasks.sort(key=lambda t: t.prio)
    for tk in tasks:
        if tk.key in claimed: continue
        # 候选：空闲单位；若任务 prio<=2，可抢占 prio 更低（数值更大且 >=4）且未开始的任务
        best = None; bestd = None
        for u in range(n_units):
            cur = st["task"].get(u)
            if cur is not None:
                if tk.prio > 2 or cur.prio <= tk.prio + 1: continue
                if cur.kind in ("place", "deposit") or any(isinstance(op, tuple) for op in cur.ops): continue
            d = _dist(positions[u], tk.target)
            if cur is not None: d += 2  # 抢占轻微惩罚
            if bestd is None or d < bestd: best, bestd = u, d
        if best is None: continue
        u = best; pos = positions[u]
        if st["task"].get(u) is not None:
            claimed.discard(st["task"][u].key)
        t = Task(tk.kind, tk.target, tk.ops, tk.prio, key=tk.key)
        needs_feed = any((not isinstance(op, tuple)) and op[0] == "FEED" for op in t.ops)
        if needs_feed and int(invs[u].get("WHEAT", 0)) <= 0:
            if int(shed.get("WHEAT", 0)) <= 0:
                t.ops = [op for op in t.ops if isinstance(op, tuple) or op[0] != "FEED"]
                if not t.ops: continue
            else:
                acc = _nearest_access(pos, unlocked)
                k = min(int(shed.get("WHEAT", 0)), max(1, len(unfed) // max(1, min(n_units, 4)) + 1), 8)
                t.ops = [["PICKUP", "WHEAT", k], ("GOTO", t.target)] + t.ops
                t.target = acc
                shed["WHEAT"] = int(shed.get("WHEAT", 0)) - k
        st["task"][u] = t; claimed.add(t.key)
    # 空闲单位：入库
    for u in range(n_units):
        if u in st["task"]: continue
        inv = invs[u]; prods = sum(v for k, v in inv.items() if k in PRODUCTS and k != "WHEAT")
        if prods > 0 and (hour >= 20 or prods >= 4 or ENDGAME or positions[u] in ACCESS):
            acc = _nearest_access(positions[u], unlocked)
            st["task"][u] = Task("deposit", acc, [["DROP"]], 8, key=("deposit", u))
    # 执行
    for u in range(n_units):
        t = st["task"].get(u)
        if t is None: continue
        pos = positions[u]
        if pos != t.target:
            unit_actions[u] = _step_toward(pos, t.target); continue
        while t.ops and isinstance(t.ops[0], tuple):
            t.target = tuple(t.ops.pop(0)[1])
        if pos != t.target:
            unit_actions[u] = _step_toward(pos, t.target); continue
        if not t.ops:
            st["task"].pop(u, None); continue
        op = t.ops.pop(0)
        unit_actions[u] = list(op)
        if op[0] == "FEED": invs[u]["WHEAT"] = int(invs[u].get("WHEAT", 0)) - 1
        if not t.ops:
            st["task"].pop(u, None)
            if op[0] == "HARVEST" and pos in ACCESS:
                st["task"][u] = Task("deposit", pos, [["DROP"]], 8, key=("deposit", u))

    # ---------- 市场 ----------
    market = _market(obs, farm, shed, seeds, invs, money, day, hour, turn, n_units, n_animals, plant_tiles, empty_tiles, shops, market_prices, st, unlocked, struct_empty, shed_animals)
    return {"farmer": unit_actions[0], "hands": unit_actions[1:], "market": market[:10]}


def _pick_free(positions, st, n_units, access, prefer_near=None):
    best = None; bd = None
    for u in range(n_units):
        if u in st["task"]: continue
        d = _dist(positions[u], prefer_near) if prefer_near else 0
        if bd is None or d < bd: best, bd = u, d
    return best


def _plant_wishes(day, hour, empty_tiles, pasture_set, order, seeds, st):
    """决定本步希望种植的 (tile, crop)。种子不足时受限于现有种子（引擎原子校验）。"""
    wishes = []
    avail = {c: int(seeds.get(c, 0)) for c in CROPS}
    cand = [t for t in order if t in empty_tiles and t not in pasture_set]
    # 近棚地块留给草莓/甜瓜（高频服务），远处小麦
    lp = PLAN["last_plant_day"]
    # 甜瓜：day 0 一次性
    if avail["MELON"] > 0 and day <= lp["MELON"]:
        for t in cand[:]:
            if avail["MELON"] <= 0: break
            wishes.append((t, "MELON")); avail["MELON"] -= 1; cand.remove(t)
    if avail["STRAWBERRY"] > 0 and day <= lp["STRAWBERRY"]:
        for t in cand[:]:
            if avail["STRAWBERRY"] <= 0: break
            wishes.append((t, "STRAWBERRY")); avail["STRAWBERRY"] -= 1; cand.remove(t)
    if avail["TOMATO"] > 0 and day <= lp["TOMATO"]:
        for t in cand[:]:
            if avail["TOMATO"] <= 0: break
            wishes.append((t, "TOMATO")); avail["TOMATO"] -= 1; cand.remove(t)
    if avail["CARROT"] > 0 and day <= lp["CARROT"]:
        for t in cand[:]:
            if avail["CARROT"] <= 0: break
            wishes.append((t, "CARROT")); avail["CARROT"] -= 1; cand.remove(t)
    if avail["WHEAT"] > 0 and day <= lp["WHEAT"]:
        for t in cand[:]:
            if avail["WHEAT"] <= 0: break
            wishes.append((t, "WHEAT")); avail["WHEAT"] -= 1; cand.remove(t)
    return wishes


def _market(obs, farm, shed, seeds, invs, money, day, hour, turn, n_units, n_animals, plant_tiles, empty_tiles, shops, prices, st, unlocked, struct_empty, shed_animals):
    """订单构造：10 槽预算。顺序：饲料小麦 → SELL（按价值取前几）→ HIRE → 土地 → 动物 → 种子。
    购买计划作为待办（pending）跨小时/跨天累积，现金够了就买。"""
    orders = []
    n_anim_all = n_animals + sum(n for _, n in shed_animals) + sum(int(i.get(a, 0)) for i in invs for a in ANIMALS)
    pend = st.setdefault("pending", {"animals": [], "straw": 0, "land": 0, "melon": 0, "init": False})
    if not pend["init"]:
        pend["init"] = True; pend["melon"] = PLAN["melon_tiles"]
    # 每天 0 时把当天计划加入待办
    dk = ("plan_added", day)
    if not st["day_plan"].get(dk):
        st["day_plan"][dk] = True
        for a, n in PLAN["animals"].get(day, []): pend["animals"].append([a, int(n)])
        pend["straw"] += int(PLAN["straw"].get(day, 0))
        pend["land"] += int(PLAN["land"].get(day, 0))
    n_anim_all += sum(n for _, n in pend["animals"])
    feed_reserve = n_anim_all * PLAN["feed_reserve_days"] + 4 if turn < 24 * 29 else 0
    has_straw = any(farm["tiles"][y][x].get("crop") == "STRAWBERRY" for (x, y) in plant_tiles)
    fert_reserve = PLAN["fert_reserve"] if (turn < 24 * 28 and has_straw and day >= 10) else 0
    # 1) SELL（按估值排序，最多 6 槽；小麦/肥料留保留量）
    sells = []
    for item in PRODUCTS:
        q = int(shed.get(item, 0))
        if item == "WHEAT": q -= feed_reserve
        if item == "FERTILIZER": q -= fert_reserve
        if q > 0: sells.append((q * prices.get(item, BASE[item]), ["SELL", item, q]))
    sells.sort(key=lambda s: -s[0])
    max_sell = 10 if turn >= 24 * 29 + 18 else 6
    orders += [o for _, o in sells[:max_sell]]
    cash = money + sum(v * 0.7 for v, _ in sells[:max_sell])
    if turn >= 24 * 29 + 20:
        return orders
    # 2) 饲料小麦（先于雇工）
    wheat_have = int(shed.get("WHEAT", 0)) + sum(int(i.get("WHEAT", 0)) for i in invs)
    need_feed = n_anim_all * PLAN["feed_reserve_days"]
    if n_anim_all and wheat_have < need_feed and prices.get("WHEAT", 25) <= PLAN["wheat_buy_cap"] and len(orders) < 10:
        q = need_feed - wheat_have
        c = q * prices.get("WHEAT", 25)
        if cash >= c:
            orders.insert(0, ["BUY_PRODUCT", "WHEAT", q]); cash -= c
        elif cash >= 2 * prices.get("WHEAT", 25):
            q = int(cash // prices.get("WHEAT", 25)); orders.insert(0, ["BUY_PRODUCT", "WHEAT", q]); cash -= q * prices.get("WHEAT", 25)
    # 3) HIRE（0–2 时；受槽位限制分小时下单）
    want_hands = PLAN["hands"].get(day, PLAN["hands_default"])
    if day == 29: want_hands = min(want_hands, 8)
    hired = int(farm.get("hires_today", 0) or 0)
    if hour <= 2 and hired < want_hands:
        n = want_hands - hired; cost = 0; k = 0
        for i in range(n):
            c = FIB[hired + i]
            if cost + c > cash - 3 or len(orders) + k >= 10: break
            cost += c; k += 1
        orders += [["HIRE"]] * k; cash -= cost
    # 4) 土地
    n_extra = len(unlocked) - 1
    if pend["land"] > 0 and n_extra < 3 and len(orders) < 10:
        price = LAND_PRICES[n_extra]
        if cash >= price + 60:
            orders.append(["BUY_LAND"]); cash -= price; pend["land"] -= 1
    # 5) 动物（逐条，现金够就买；第 16 天后放弃）
    if day <= 16:
        rest = []
        for a, n in pend["animals"]:
            cost = ANIMALS[a]["cost"] * n
            if cash >= cost + PLAN["animal_cash_reserve"] and len(orders) < 10 and sum(shed.values()) + n < 95:
                orders.append(["BUY_ANIMAL", a, n]); cash -= cost
            else:
                rest.append([a, n])
        pend["animals"] = rest
    else:
        pend["animals"] = []
    # 6) 种子：甜瓜（一次性）、草莓（待办）、小麦（按目标地块数）
    lp = PLAN["last_plant_day"]
    if pend["melon"] > 0 and day <= lp["MELON"] and len(orders) < 10:
        n = pend["melon"]; c = CROPS["MELON"]["seed"] * n
        if cash >= c + 10:
            orders.append(["BUY_SEED", "MELON", n]); cash -= c; pend["melon"] = 0
        elif cash >= CROPS["MELON"]["seed"] * 2 + 10:
            n = int((cash - 10) // CROPS["MELON"]["seed"]); orders.append(["BUY_SEED", "MELON", n]); cash -= n * 80; pend["melon"] -= n
    if pend["straw"] > 0 and day <= lp["STRAWBERRY"] and len(orders) < 10:
        n = pend["straw"]; c = CROPS["STRAWBERRY"]["seed"] * n
        if cash >= c + 10:
            orders.append(["BUY_SEED", "STRAWBERRY", n]); cash -= c; pend["straw"] = 0
        elif cash >= 110:
            n = int((cash - 10) // 100); orders.append(["BUY_SEED", "STRAWBERRY", n]); cash -= n * 100; pend["straw"] -= n
    if day <= lp["WHEAT"] and len(orders) < 10:
        target_wheat = PLAN["wheat_tiles"] if day < 6 else (PLAN["wheat_tiles_mid"] if day < 11 else PLAN["wheat_tiles_late"])
        have_wheat_plants = sum(1 for (x, y) in plant_tiles if farm["tiles"][y][x].get("crop") == "WHEAT")
        n_empty = len(empty_tiles)
        want = max(0, min(target_wheat - have_wheat_plants, n_empty) - int(seeds.get("WHEAT", 0)))
        if want > 0:
            c = CROPS["WHEAT"]["seed"] * want
            if cash >= c + 5:
                orders.append(["BUY_SEED", "WHEAT", want]); cash -= c
            elif cash >= 15:
                n = int((cash - 5) // 10); orders.append(["BUY_SEED", "WHEAT", n]); cash -= n * 10
    return orders
