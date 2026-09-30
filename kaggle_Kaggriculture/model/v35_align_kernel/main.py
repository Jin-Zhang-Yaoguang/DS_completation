"""V23 计划先行调度器：静态蓝图 + 每日待办队列 + 班表执行（设计见 ../v22_global_scheduler/REWRITE_DESIGN.md）。"""
import os, json

BS = 10
ACCESS = [(4, 4), (5, 4), (4, 5), (5, 5)]
QUAD_OF = lambda x, y: ("N" if y < 5 else "S") + ("W" if x < 5 else "E")
CROPS = {
    "WHEAT": dict(seed=10, first=2, maxday=4, interval=0, maxy=6, ongoing=False),
    "CARROT": dict(seed=20, first=2, maxday=3, interval=0, maxy=4, ongoing=False),
    "STRAWBERRY": dict(seed=100, first=10, maxday=10, interval=2, maxy=4, ongoing=True),
    "MELON": dict(seed=80, first=10, maxday=12, interval=0, maxy=6, ongoing=False),
    "TOMATO": dict(seed=50, first=8, maxday=8, interval=1, maxy=4, ongoing=True),
}
ANIMALS = {"COW": dict(cost=400, product="MILK"), "SHEEP": dict(cost=500, product="WOOL"), "GOOSE": dict(cost=300, product="EGG")}
PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]
BASE = {"WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120, "MELON": 250, "EGG": 50, "MILK": 160, "WOOL": 200, "FERTILIZER": 100}
LAND_PRICES = [1000, 2000, 4000]
FIB = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987]

P = {
    "hands": {0: 5, 1: 4, 2: 4, 3: 5, 4: 4, 5: 5, 6: 8, 7: 8, 8: 10, 9: 9, 10: 11, 11: 11},
    "hands_default": 11,
    "animals": {0: [["COW", 2], ["SHEEP", 2]], 2: [["COW", 1]], 3: [["COW", 1]], 6: [["COW", 2]], 7: [["COW", 2]],
                8: [["COW", 1], ["SHEEP", 2]], 9: [["COW", 1], ["SHEEP", 1]], 10: [["SHEEP", 2]], 11: [["SHEEP", 1]]},
    "land": {6: 1, 11: 1},
    "melon_n": 12, "straw_n": 33, "reuse_n": 33,
    "straw_last_plant": 14, "wheat_last_plant": 27, "carrot_from": 25,
    "fert_keep": 18, "sell_batch": 12, "burst": 15,
    "harvest_wheat_age": 4, "animal_harvest_min": 2,
    "straw_from": 4, "straw_cash_floor": 250, "hv_crops": ["STRAWBERRY", "MELON"],
}
_raw = os.environ.get("V23_PARAMS", "")
if _raw:
    P.update(json.loads(open(_raw).read() if os.path.exists(_raw) else _raw))
for k in ("hands", "animals", "land"):
    P[k] = {int(a): b for a, b in P[k].items()}

_S = {}


def _dist(a, b): return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _step_toward(src, dst):
    dx, dy = dst[0] - src[0], dst[1] - src[1]
    if abs(dx) >= abs(dy) and dx: return ["EAST"] if dx > 0 else ["WEST"]
    if dy: return ["SOUTH"] if dy > 0 else ["NORTH"]
    if dx: return ["EAST"] if dx > 0 else ["WEST"]
    return ["PASS"]


def _nacc(pos): return min(ACCESS, key=lambda a: _dist(pos, a))


def _blueprint(unlocked):
    """静态蓝图：牧场 18 中心 / 复用带 33（甜瓜->草莓->快作物）/ 其余小麦带。"""
    tiles = [(x, y) for y in range(BS) for x in range(BS) if QUAD_OF(x, y) in unlocked]
    tiles.sort(key=lambda t: (abs(t[0] - 4.5) + abs(t[1] - 4.5), t[1], t[0]))
    past = [t for t in tiles if abs(t[0] - 4.5) + abs(t[1] - 4.5) <= 3.0][:18]
    rest = [t for t in tiles if t not in set(past)]
    reuse = rest[:P["reuse_n"]]
    wheat = rest[P["reuse_n"]:]
    rs = reuse[P["melon_n"]:]
    return {"pasture": past, "reuse": reuse, "wheat": wheat,
            "reuse_melon": reuse[:P["melon_n"]], "reuse_straw": rs,
            "straw_early": rs[:len(rs) // 2], "straw_late": rs[len(rs) // 2:]}


def _state(seat, turn):
    st = _S.get(seat)
    if st is None or turn <= st.get("last", -1):
        st = {"last": -1, "units": {}, "day_done": -1, "pend_animals": [], "pend_land": 0, "planned": {}, "bp_key": None}
        _S[seat] = st
    st["last"] = turn
    return st


def agent(obs, configuration=None):
    try:
        return _agent(obs)
    except Exception:
        farms = obs.get("farms") or []
        me = obs.get("player", 0)
        n = len(farms[me].get("hands") or []) if farms and me < len(farms) else 0
        return {"farmer": ["PASS"], "hands": [["PASS"]] * n, "market": []}


def _agent(obs):
    me = obs.get("player", 0)
    day = int(obs.get("day", 0)); hour = int(obs.get("hour", 0)); turn = day * 24 + hour
    farm = obs["farms"][me]; tiles = farm["tiles"]
    priv = obs["private"]; shed = dict(priv["shed"]); seeds = dict(priv["seeds"])
    invs = [dict(i) for i in priv["inventories"]]
    money = float(farm["money"]); prices = obs["market"]["prices"]
    unlocked = list(farm.get("unlocked_quadrants") or ["NW"])
    positions = [tuple(farm["farmer"])] + [tuple(h) for h in farm["hands"]]
    n_units = len(positions)
    st = _state(me, turn)
    LAST = 29

    def T(x, y): return tiles[y][x]

    bp_key = tuple(sorted(unlocked))
    if st["bp_key"] != bp_key:
        st["bp"] = _blueprint(unlocked); st["bp_key"] = bp_key
    bp = st["bp"]
    pasture_set = set(bp["pasture"])

    # ---- 日初计划注入（需求对齐：配额 = f(已解锁商店)）----
    town_shops = list((obs.get("town") or {}).get("unlocked_shops") or [])
    n_yarn_s = town_shops.count("YARN_STORE")
    n_dairy_s = sum(town_shops.count(x) for x in ("PIZZA_SHOP", "ICE_CREAM_SHOP", "SMOOTHIE_SHOP"))
    n_berry_s = sum(town_shops.count(x) for x in ("BRUNCH_SPOT", "ICE_CREAM_SHOP", "SMOOTHIE_SHOP", "FARMERS_MARKET"))
    n_pet_s = town_shops.count("PET_CAFE")
    st["_shops"] = town_shops
    if st["day_done"] != day:
        st["day_done"] = day
        want_sheep = int(P.get("sheep_floor", 2)) if (day >= 8 and n_yarn_s == 0) else min(8, 4 + 4 * n_yarn_s) if n_yarn_s > 0 else 8
        want_cow = max(4, min(10, int(P.get("cow_base", 3)) + 2 * n_dairy_s)) if day >= 6 else 10
        cur_sheep = int(shed.get("SHEEP", 0)); cur_cow = int(shed.get("COW", 0))
        for row in tiles:
            for x in row:
                if isinstance(x, dict) and x.get("animal") == "SHEEP": cur_sheep += 1
                elif isinstance(x, dict) and x.get("animal") == "COW": cur_cow += 1
        for a, n in P["animals"].get(day, []):
            cap = want_sheep if a == "SHEEP" else want_cow
            have = cur_sheep if a == "SHEEP" else cur_cow
            pend_same = sum(nn for aa, nn in st["pend_animals"] if aa == a)
            n2 = max(0, min(n, cap - have - pend_same))
            if n2 > 0: st["pend_animals"].append([a, n2])
        # 补差自愈：配额随商店揭示上调时，把早砍误伤的批次追回（晚买总比不买强）
        if 6 <= day <= 14:
            for a, cap, have in (("SHEEP", want_sheep, cur_sheep), ("COW", want_cow, cur_cow)):
                pend_same = sum(nn for aa, nn in st["pend_animals"] if aa == a)
                gap = cap - have - pend_same
                if gap > 0: st["pend_animals"].append([a, min(gap, 2)])
        st["pend_land"] += P["land"].get(day, 0)
        # 作物配额对齐
        P["straw_n"] = int(33 * (float(P.get("straw_scale_zero", 0.6)) if n_berry_s == 0 else (1.0 if n_berry_s >= 2 else 0.85)))
        P["carrot_from"] = 6 if n_pet_s >= 2 else 25
        st["units"] = {}

    # ---- 扫描场面 ----
    animal_tiles, struct_empty, weed, empty, plants = [], [], [], [], []
    for y in range(BS):
        for x in range(BS):
            tt = T(x, y)
            if tt is None:
                if (x, y) in set(bp["reuse"]) | set(bp["wheat"]) | pasture_set: empty.append((x, y))
            elif tt == "LOCKED": continue
            elif isinstance(tt, dict):
                if "animal" in tt: animal_tiles.append((x, y))
                elif tt.get("kind") == "PLANT": plants.append((x, y))
                elif tt.get("kind") == "WEED": weed.append((x, y))
                elif tt.get("kind") in ("PASTURE", "COOP"): struct_empty.append((x, y))

    # ---- 待办队列生成（每小时重算，幂等）----
    todo = []   # (priority, (x,y), ops)
    for (x, y) in animal_tiles:
        tt = T(x, y); ops = []
        if not tt.get("fed_today") and day < LAST: ops.append(["FEED"])
        if not tt.get("cared_today") and day < LAST: ops.append(["CARE"])
        if tt.get("fertilizer_available"): ops.append(["COLLECT_FERTILIZER"])
        yu = int(tt.get("yield_units", 0))
        if yu >= P["animal_harvest_min"] or (yu > 0 and day >= 27): ops.append(["HARVEST"])
        if ops: todo.append((0, (x, y), ops))
    for (x, y) in plants:
        tt = T(x, y); cd = CROPS[tt["crop"]]; age = day - int(tt.get("planted_day", day)); ops = []
        yu = int(tt.get("yield_units", 0)); unw = int(tt.get("consecutive_unwatered", 0))
        watered = bool(tt.get("watered_today"))
        # 收获判定
        if cd["ongoing"]:
            done_all = age >= cd["first"] + cd["interval"] * (cd["maxy"] - 1) + 1
            if yu >= 2 or (yu >= 1 and (hour >= 18 or done_all or day >= LAST - 1)):
                ops.append(["HARVEST"])
                if done_all and day <= P["wheat_last_plant"]:
                    ops += [["DIG"], ["PLANT", "CARROT" if day >= P["carrot_from"] else "WHEAT"], ["WATER"]]
        else:
            hw = P["harvest_wheat_age"] if tt["crop"] == "WHEAT" else cd["maxday"]
            yu_after = yu + (1 if (not watered and (cd["maxday"] + 1) // 2 <= age <= cd["maxday"]) else 0)
            if yu > 0 and (yu_after >= cd["maxy"] or age >= hw or day >= LAST) and not (tt["crop"] == "MELON" and age < cd["first"]):
                ops.append(["HARVEST"])
                if day <= P["wheat_last_plant"]:
                    ops += [["PLANT", "CARROT" if day >= P["carrot_from"] else "WHEAT"], ["WATER"]]
        # 浇水判定（收获链里已带 WATER 的不重复）
        if not watered and not any(o[0] == "WATER" for o in ops):
            if cd["ongoing"] or age <= cd["maxday"]:
                if day <= LAST: ops.insert(0, ["WATER"])
        # 施肥（草莓，无缝续肥）
        if (tt["crop"] == "STRAWBERRY" and age >= cd["first"] - 1 and day <= LAST - 2
                and int(tt.get("fertilized_until_day", -1)) < day + 1):
            ops.insert(0, ["FERTILIZE"])
        if ops:
            hv = tt["crop"] in tuple(P.get("hv_crops", ["STRAWBERRY", "MELON"]))
            pr = 1 if (unw >= 1 or yu >= 2 or "FERTILIZE" in [o[0] for o in ops]
                       or (hv and any(o[0] == "WATER" for o in ops))) else 2

            todo.append((pr, (x, y), ops))
    # 种植桶：蓝图缺口
    n_straw = sum(1 for (x, y) in plants if T(x, y)["crop"] == "STRAWBERRY")
    n_melon = sum(1 for (x, y) in plants if T(x, y)["crop"] == "MELON")
    for (x, y) in weed:
        todo.append((2, (x, y), [["DIG"]] + ([["PLANT", "WHEAT"], ["WATER"]] if day <= P["wheat_last_plant"] and (x, y) not in pasture_set else [])))
    for (x, y) in empty:
        if (x, y) in pasture_set: continue
        crop = None
        if (x, y) in set(bp["reuse"]):
            in_melon = (x, y) in set(bp.get("reuse_melon", []))
            if in_melon and day == 0 and n_melon < P["melon_n"]:
                crop = "MELON"; n_melon += 1
            elif P["straw_from"] <= day <= P["straw_last_plant"] and n_straw < P["straw_n"]:
                # 草莓专区（含 d10 后腾出的甜瓜地）：只等草莓，不给麦占位
                if seeds.get("STRAWBERRY", 0) > 0 or money >= P["straw_cash_floor"]:
                    crop = "STRAWBERRY"; n_straw += 1
            elif day > P["straw_last_plant"] and day <= P["wheat_last_plant"]:
                crop = "CARROT" if day >= P["carrot_from"] else "WHEAT"
        elif day <= P["wheat_last_plant"]:
            crop = "CARROT" if day >= P["carrot_from"] else "WHEAT"
        if crop: todo.append((1 if crop != "WHEAT" else 2, (x, y), [["PLANT", crop], ["WATER"]]))

    # ---- 执行：工人从待办取最近项（优先级 0 > 1 > 2）----
    US = st["units"]
    acts = [["PASS"] for _ in range(n_units)]
    claimed = set()
    for u in range(n_units):
        s0 = US.get(u)
        if s0 and s0.get("target") and s0.get("ops"): claimed.add(s0["target"])
    # 需要物资的领取（日初 h0-1：饲料/肥/种子按待办估算）
    need_feed_carry = sum(1 for _, tt0, ops in todo if any(o[0] == "FEED" for o in ops))
    need_fert_carry = sum(1 for _, tt0, ops in todo if any(o[0] == "FERTILIZE" for o in ops))
    for u in range(n_units):
        pos = positions[u]; inv = invs[u]
        s0 = US.setdefault(u, {"target": None, "ops": []})
        # 执行中
        if s0.get("ops") and s0.get("target") == pos:
            op = s0["ops"].pop(0)
            if op[0] == "FEED" and inv.get("WHEAT", 0) <= 0: op = None
            elif op[0] == "FERTILIZE" and inv.get("FERTILIZER", 0) <= 0: op = None
            elif op[0] == "PLANT" and seeds.get(op[1], 0) <= 0: op = None
            if op:
                acts[u] = list(op)
                if op[0] == "FEED": inv["WHEAT"] = inv.get("WHEAT", 0) - 1
                if op[0] == "FERTILIZE": inv["FERTILIZER"] = inv.get("FERTILIZER", 0) - 1
                if op[0] == "PLANT": seeds[op[1]] = seeds.get(op[1], 0) - 1
                if op[0] == "PICKUP" and len(op) >= 3: inv[op[1]] = inv.get(op[1], 0) + int(op[2])
                if op[0] == "PLACE" and len(op) >= 3: inv[op[1]] = max(0, inv.get(op[1], 0) - int(op[2]))
                continue
        if s0.get("target") and s0.get("target") != pos and s0.get("ops"):
            acts[u] = _step_toward(pos, s0["target"]); continue
        s0["ops"] = []; s0["target"] = None
        # 领取物资：喂养手无麦 / 施肥待办多而身上无肥
        if need_feed_carry > 0 and inv.get("WHEAT", 0) <= 0 and shed.get("WHEAT", 0) > 0:
            k = min(shed.get("WHEAT", 0), 8, need_feed_carry); shed["WHEAT"] -= k
            s0["target"] = _nacc(pos); s0["ops"] = [["PICKUP", "WHEAT", k]]
            acts[u] = (_step_toward(pos, s0["target"]) if pos != s0["target"] else (s0["ops"].pop(0), inv.__setitem__("WHEAT", inv.get("WHEAT", 0) + k))[0])
            if isinstance(acts[u], tuple): acts[u] = list(acts[u])
            need_feed_carry -= k; continue
        if need_fert_carry >= 1 and inv.get("FERTILIZER", 0) <= 0 and shed.get("FERTILIZER", 0) > 0:
            k = min(shed.get("FERTILIZER", 0), 8, need_fert_carry); shed["FERTILIZER"] -= k
            s0["target"] = _nacc(pos); s0["ops"] = [["PICKUP", "FERTILIZER", k]]
            if pos == s0["target"]:
                acts[u] = s0["ops"].pop(0); inv["FERTILIZER"] = inv.get("FERTILIZER", 0) + k
            else: acts[u] = _step_toward(pos, s0["target"])
            need_fert_carry -= k; continue
        # 放动物
        pending_place = [a for a in ANIMALS for _ in range(int(shed.get(a, 0)))]
        if pending_place:
            tgt = None; build_first = False
            frees = [t2 for t2 in struct_empty if t2 not in claimed]
            if frees:
                tgt = min(frees, key=lambda t2: _dist(pos, t2))
            else:
                pe = [t2 for t2 in pasture_set if T(*t2) is None and t2 not in claimed]
                if pe:
                    tgt = min(pe, key=lambda t2: _dist(pos, t2)); build_first = True
            if tgt is not None:
                a0 = pending_place[0]; acc = _nacc(pos)
                shed[a0] -= 1; claimed.add(tgt)
                if tgt in struct_empty: struct_empty.remove(tgt)
                chain = ([["BUILD_PASTURE"]] if build_first else []) + [["PLACE", a0]]
                if pos == acc:
                    acts[u] = ["PICKUP", a0, 1]; inv[a0] = inv.get(a0, 0) + 1
                    s0["target"] = tgt; s0["ops"] = chain
                else:
                    s0["target"] = acc; s0["ops"] = [["PICKUP", a0, 1]]; s0["then"] = ("place", tgt, a0, build_first)
                    acts[u] = _step_toward(pos, acc)
                continue
        if s0.get("then") and inv.get(s0["then"][2], 0) > 0:
            _, tgt, a0, bf = s0.pop("then"); s0["target"] = tgt
            s0["ops"] = ([["BUILD_PASTURE"]] if bf else []) + [["PLACE", a0]]
            acts[u] = s0["ops"].pop(0) if pos == tgt else _step_toward(pos, tgt); continue
        # 入库（PLACE 定量，保留随身工作物资）
        carry_val = sum(v * BASE.get(k2, 0) for k2, v in inv.items() if k2 in PRODUCTS and k2 not in ("WHEAT", "FERTILIZER"))
        npd = sum(v for k2, v in inv.items() if k2 in PRODUCTS and k2 not in ("WHEAT", "FERTILIZER"))
        if npd > 0 and (carry_val >= 500 or npd >= 8 or hour >= 21 or day >= LAST):
            acc = _nacc(pos)
            dep = [["PLACE", k2, int(v)] for k2, v in inv.items() if k2 in PRODUCTS and int(v) > 0 and k2 not in ("WHEAT", "FERTILIZER")]
            if day >= LAST or hour >= 22:
                dep = [["PLACE", k2, int(v)] for k2, v in inv.items() if k2 in PRODUCTS and int(v) > 0]
            if dep:
                s0["target"] = acc; s0["ops"] = dep
                if pos == acc:
                    op = s0["ops"].pop(0); acts[u] = list(op); inv[op[1]] = max(0, inv.get(op[1], 0) - int(op[2]))
                else: acts[u] = _step_toward(pos, acc)
                continue
        # 从待办取最近项
        best = None
        for pr, tt0, ops in sorted(todo, key=lambda z: (z[0],)):
            if tt0 in claimed: continue
            if any(o[0] == "FEED" for o in ops) and inv.get("WHEAT", 0) <= 0:
                ops = [o for o in ops if o[0] != "FEED"]
                if not ops: continue
            if any(o[0] == "FERTILIZE" for o in ops) and inv.get("FERTILIZER", 0) <= 0:
                ops = [o for o in ops if o[0] != "FERTILIZE"]
                if not ops: continue
            d0 = _dist(pos, tt0)
            score = (pr, d0)
            if best is None or score < best[0]: best = (score, tt0, ops)
        if best:
            _, tgt, ops = best
            s0["target"] = tgt; s0["ops"] = [list(o) for o in ops]; claimed.add(tgt)
            if pos == tgt:
                op = s0["ops"].pop(0)
                if op[0] == "FEED": inv["WHEAT"] = inv.get("WHEAT", 0) - 1
                if op[0] == "FERTILIZE": inv["FERTILIZER"] = inv.get("FERTILIZER", 0) - 1
                if op[0] == "PLANT":
                    if seeds.get(op[1], 0) <= 0: op = ["PASS"]
                    else: seeds[op[1]] = seeds.get(op[1], 0) - 1
                acts[u] = list(op)
            else:
                acts[u] = _step_toward(pos, tgt)

    market = _market(st, shed, seeds, money, day, hour, turn, prices, unlocked, farm, todo, plants, n_units)
    return {"farmer": acts[0], "hands": acts[1:], "market": market[:10]}


def _market(st, shed, seeds, money, day, hour, turn, prices, unlocked, farm, todo, plants, n_units):
    orders = []
    endgame = turn >= 24 * 28
    # 卖出：分相模板（洪峰全量 / 日常滴灌 / 终局清仓）
    feed_keep = 0 if endgame else min(24, sum(1 for _, _, ops in todo if any(o[0] == "FEED" for o in ops)) + 4)
    fert_keep = 0 if turn >= 24 * 27 else P["fert_keep"]
    sells = []
    for item in PRODUCTS:
        q = int(shed.get(item, 0))
        if item == "WHEAT": q -= feed_keep
        if item == "FERTILIZER": q -= fert_keep
        if q <= 0: continue
        if not endgame and item != "MELON" and q < P["burst"]:
            menu = {"BAKERY": ("EGG", "WHEAT"), "PIZZA_SHOP": ("MILK", "TOMATO", "WHEAT"),
                    "BRUNCH_SPOT": ("EGG", "WHEAT", "STRAWBERRY"), "YARN_STORE": ("WOOL",),
                    "ICE_CREAM_SHOP": ("STRAWBERRY", "MILK", "WHEAT"), "PET_CAFE": ("CARROT",),
                    "SMOOTHIE_SHOP": ("STRAWBERRY", "MILK"), "FARMERS_MARKET": ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY")}
            rate = 2
            for sh in (st.get("_shops") or []):
                if item in menu.get(sh, ()): rate += 2 if len(menu[sh]) > 1 else 4
            q = min(q, int(rate * float(P.get("rate_mult", 1.5))))
        sells.append((q * prices.get(item, BASE[item]), ["SELL", item, q]))
    sells.sort(key=lambda z: -z[0])
    orders += [o for _, o in sells[:6 if not endgame else 10]]
    cash = money + sum(v * 0.7 for v, _ in sells[:6])
    if turn >= 24 * 29 + 20: return orders
    # 饲料：不囤，按今日需求买
    n_anim = sum(1 for _, tt0, ops in todo if any(o[0] in ("FEED", "CARE") for o in ops))
    wheat_have = int(shed.get("WHEAT", 0))
    if day <= 28 and wheat_have < n_anim + 2 and prices.get("WHEAT", 25) <= 80:
        q = min(n_anim + 4 - wheat_have, 20)
        if q > 0 and cash >= q * prices.get("WHEAT", 25):
            orders.insert(0, ["BUY_PRODUCT", "WHEAT", q]); cash -= q * prices.get("WHEAT", 25)
    # 雇工
    want = P["hands"].get(day, P["hands_default"])
    if day == 29: want = min(want, 8)
    hired = int(farm.get("hires_today", 0) or 0)
    if hour <= 2 and hired < want:
        k = 0; cost = 0
        for i in range(want - hired):
            c = FIB[hired + i]
            if cost + c > cash - 3 or len(orders) + k >= 10: break
            cost += c; k += 1
        orders += [["HIRE"]] * k; cash -= cost
    # 土地
    n_extra = len(unlocked) - 1
    if st["pend_land"] > 0 and n_extra < 3:
        price = LAND_PRICES[n_extra]
        if cash >= price + 60 and len(orders) < 10:
            orders.append(["BUY_LAND"]); cash -= price; st["pend_land"] -= 1
    # 种子（按种植待办买：草莓优先）
    plant_need = {}
    for _, _, ops in todo:
        for o in ops:
            if o[0] == "PLANT": plant_need[o[1]] = plant_need.get(o[1], 0) + 1
    for crop in ("MELON", "STRAWBERRY", "WHEAT", "CARROT"):
        need = plant_need.get(crop, 0) - int(seeds.get(crop, 0))
        if need <= 0 or len(orders) >= 10: continue
        c0 = CROPS[crop]["seed"]
        n = min(need, int(max(0, cash - 10) // c0))
        if n > 0:
            orders.append(["BUY_SEED", crop, n]); cash -= n * c0
    # 动物
    rest = []
    for a, n in st["pend_animals"]:
        cost = ANIMALS[a]["cost"] * n
        if day <= 16 and cash >= cost + 240 and len(orders) < 10 and sum(shed.values()) + n < 95:
            orders.append(["BUY_ANIMAL", a, n]); cash -= cost
        else: rest.append([a, n])
    st["pend_animals"] = rest if day <= 16 else []
    return orders
