"""V36 全天排程调度器：日初生成每工人 24h 任务序列（地理分簇+最近邻路径），执行期不重选。
需求对齐生产 + 速率匹配卖出继承自 V34/V35。"""
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
MENU = {"BAKERY": ("EGG", "WHEAT"), "PIZZA_SHOP": ("MILK", "TOMATO", "WHEAT"),
        "BRUNCH_SPOT": ("EGG", "WHEAT", "STRAWBERRY"), "YARN_STORE": ("WOOL",),
        "ICE_CREAM_SHOP": ("STRAWBERRY", "MILK", "WHEAT"), "PET_CAFE": ("CARROT",),
        "SMOOTHIE_SHOP": ("STRAWBERRY", "MILK"), "FARMERS_MARKET": ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY")}

P = {
    "hands": {0: 5, 1: 4, 2: 4, 3: 5, 4: 4, 5: 5, 6: 8, 7: 8, 8: 10, 9: 9, 10: 11, 11: 11},
    "hands_default": 12,
    "animals": {0: [["COW", 2], ["SHEEP", 2]], 2: [["COW", 1]], 3: [["COW", 1]], 6: [["COW", 2]], 7: [["COW", 2]],
                8: [["COW", 1], ["SHEEP", 2]], 9: [["COW", 1], ["SHEEP", 1]], 10: [["SHEEP", 2]], 11: [["SHEEP", 1]]},
    "land": {6: 1, 11: 1},
    "melon_n": 12, "straw_n": 33,
    "straw_from": 4, "straw_last": 16, "wheat_last": 27, "carrot_from": 25,
    "sheep_floor": 2, "cow_base": 3, "fert_keep": 15, "rate_mult": 1.5,
    "harvest_wheat_age": 4, "animal_hmin": 2,
}
_raw = os.environ.get("V36_PARAMS", "")
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


def agent(obs, configuration=None):
    try:
        return _agent(obs)
    except Exception:
        farms = obs.get("farms") or []
        me = obs.get("player", 0)
        n = len(farms[me].get("hands") or []) if farms and me < len(farms) else 0
        return {"farmer": ["PASS"], "hands": [["PASS"]] * n, "market": []}


def _tile_jobs(x, y, tt, day, hour, n_pet_s):
    """一块地今天剩余需要的动作序列（时刻无关，按依赖排序）。"""
    jobs = []
    if tt is None:
        return jobs
    if isinstance(tt, dict) and tt.get("kind") == "WEED":
        return [["DIG"]]
    if not (isinstance(tt, dict) and tt.get("kind") == "PLANT"):
        return jobs
    cd = CROPS[tt["crop"]]; age = day - int(tt.get("planted_day", day))
    yu = int(tt.get("yield_units", 0) or 0)
    watered = bool(tt.get("watered_today"))
    # 收获（含完账转产）
    if cd["ongoing"]:
        done_all = age >= cd["first"] + cd["interval"] * (cd["maxy"] - 1) + 1
        if yu >= 2 or (yu >= 1 and (done_all or day >= 28)):
            jobs.append(["HARVEST"])
            if done_all and day <= P["wheat_last"]:
                jobs += [["DIG"], ["PLANT", "CARROT" if day >= P["carrot_from"] or n_pet_s >= 2 else "WHEAT"], ["WATER"]]
                return jobs
    else:
        hw = P["harvest_wheat_age"] if tt["crop"] == "WHEAT" else cd["maxday"]
        if yu > 0 and (age >= hw or day >= 28) and not (tt["crop"] == "MELON" and age < cd["first"]):
            jobs.append(["HARVEST"])
            if day <= P["wheat_last"]:
                jobs += [["PLANT", "CARROT" if day >= P["carrot_from"] or n_pet_s >= 2 else "WHEAT"], ["WATER"]]
                return jobs
    # 浇水
    if not watered and (cd["ongoing"] or age <= cd["maxday"]) and day <= 28 and not any(j[0] == "WATER" for j in jobs):
        jobs.insert(0, ["WATER"])
    # 施肥（草莓无缝续肥）
    if (tt["crop"] == "STRAWBERRY" and age >= cd["first"] - 1 and day <= 26
            and int(tt.get("fertilized_until_day", -1)) < day + 1):
        jobs.insert(0, ["FERTILIZE"])
    return jobs


def _plan_day(obs, st, day, tiles, pasture_set, reuse_set, n_units, positions, n_pet_s):
    """日初排程：任务簇 -> 工人 -> 最近邻序列。返回 st['sched'][u] = [(x,y), ...] 意向清单。"""
    # 收集今日作业块（作物块 + 计划种植的空地）
    work_tiles = []
    for y in range(BS):
        for x in range(BS):
            tt = tiles[y][x]
            if tt == "LOCKED" or (x, y) in pasture_set: continue
            if tt is None or (isinstance(tt, dict) and tt.get("kind") in ("PLANT", "WEED")):
                work_tiles.append((x, y))
    ranch_tiles = sorted(pasture_set)
    # 动物工人数：按动物数配
    n_anim = sum(1 for (x, y) in ranch_tiles if isinstance(tiles[y][x], dict) and "animal" in tiles[y][x])
    n_ranch = min(n_units, max(1, -(-n_anim // 3))) if n_anim else 0
    field_units = [u for u in range(n_units)][n_ranch:]
    ranch_units = [u for u in range(n_units)][:n_ranch]
    sched = {}
    for u in ranch_units:
        sched[u] = {"kind": "ranch", "route": ranch_tiles}
    # 田间：按 x 坐标带状分区（连续条带 = 低移动巡回）
    if field_units:
        cols = sorted(work_tiles, key=lambda t: (t[0], t[1]))
        k = len(field_units); n = len(cols)
        for i, u in enumerate(field_units):
            band = cols[(i * n) // k:((i + 1) * n) // k]
            # 蛇形排序：x 主序、y 交替方向
            band.sort(key=lambda t: (t[0], t[1] if t[0] % 2 == 0 else -t[1]))
            sched[u] = {"kind": "field", "route": band, "i": 0}
    st["sched"] = sched
    st["sched_day"] = day


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
    st = _S.get(me)
    if st is None or turn <= st.get("last", -1):
        st = {"last": -1, "sched_day": -1, "pend_animals": [], "pend_land": 0, "day_done": -1, "units": {}}
        _S[me] = st
    st["last"] = turn
    LAST = 29

    def T(x, y): return tiles[y][x]

    town_shops = list((obs.get("town") or {}).get("unlocked_shops") or [])
    n_yarn_s = town_shops.count("YARN_STORE")
    n_dairy_s = sum(town_shops.count(x) for x in ("PIZZA_SHOP", "ICE_CREAM_SHOP", "SMOOTHIE_SHOP"))
    n_berry_s = sum(town_shops.count(x) for x in ("BRUNC_SPOT", "BRUNCH_SPOT", "ICE_CREAM_SHOP", "SMOOTHIE_SHOP", "FARMERS_MARKET"))
    n_pet_s = town_shops.count("PET_CAFE")

    # 蓝图
    all_tiles = [(x, y) for y in range(BS) for x in range(BS) if QUAD_OF(x, y) in unlocked]
    all_tiles.sort(key=lambda t: (abs(t[0] - 4.5) + abs(t[1] - 4.5), t[1], t[0]))
    n_anim_now = sum(1 for (x, y) in all_tiles if isinstance(T(x, y), dict) and "animal" in T(x, y))
    pasture_cap = max(n_anim_now + 1, 6 if day < 5 else 4 + n_anim_now)
    pasture_set = set()
    for t in all_tiles:
        x, y = t
        tt = T(x, y)
        if isinstance(tt, dict) and (("animal" in tt) or tt.get("kind") in ("PASTURE", "COOP")):
            pasture_set.add(t)
    for t in all_tiles:
        if len(pasture_set) >= pasture_cap: break
        if t not in pasture_set and abs(t[0] - 4.5) + abs(t[1] - 4.5) <= 3.0:
            pasture_set.add(t)
    rest = [t for t in all_tiles if t not in pasture_set]
    reuse_set = set(rest[:P["melon_n"] + P["straw_n"]])

    # 日初：对齐计划 + 排程
    if st["day_done"] != day:
        st["day_done"] = day
        want_sheep = P["sheep_floor"] if (day >= 8 and n_yarn_s == 0) else (min(8, 4 + 4 * n_yarn_s) if n_yarn_s else 8)
        want_cow = max(4, min(10, P["cow_base"] + 2 * n_dairy_s)) if day >= 6 else 10
        cur = {"SHEEP": int(shed.get("SHEEP", 0)), "COW": int(shed.get("COW", 0))}
        for (x, y) in pasture_set:
            tt = T(x, y)
            if isinstance(tt, dict) and tt.get("animal") in cur: cur[tt["animal"]] += 1
        for a, n in P["animals"].get(day, []):
            cap = want_sheep if a == "SHEEP" else want_cow
            pend_same = sum(nn for aa, nn in st["pend_animals"] if aa == a)
            n2 = max(0, min(n, cap - cur[a] - pend_same))
            if n2 > 0: st["pend_animals"].append([a, n2])
        if 6 <= day <= 14:
            for a in ("SHEEP", "COW"):
                cap = want_sheep if a == "SHEEP" else want_cow
                pend_same = sum(nn for aa, nn in st["pend_animals"] if aa == a)
                gap = cap - cur[a] - pend_same
                if gap > 0: st["pend_animals"].append([a, min(gap, 2)])
        st["pend_land"] += P["land"].get(day, 0)
        st["units"] = {}
        _plan_day(obs, st, day, tiles, pasture_set, reuse_set, n_units, positions, n_pet_s)
    if (st.get("sched_day") != day or len(st.get("sched", {})) != n_units
            or st.get("sched_anim") != n_anim_now):
        _plan_day(obs, st, day, tiles, pasture_set, reuse_set, n_units, positions, n_pet_s)
        st["sched_anim"] = n_anim_now

    # ---- 执行：每工人沿自己 route 巡回，做 _tile_jobs 给出的动作 ----
    acts = [["PASS"] for _ in range(n_units)]
    sched = st.get("sched", {})
    US = st["units"]
    n_straw = sum(1 for (x, y) in all_tiles if isinstance(T(x, y), dict) and T(x, y).get("kind") == "PLANT" and T(x, y).get("crop") == "STRAWBERRY")
    n_melon = sum(1 for (x, y) in all_tiles if isinstance(T(x, y), dict) and T(x, y).get("kind") == "PLANT" and T(x, y).get("crop") == "MELON")
    placed = set()
    for u in range(n_units):
        pos = positions[u]; inv = invs[u]
        s0 = US.setdefault(u, {"ops": [], "target": None})
        plan = sched.get(u)
        # 执行 ops
        if s0.get("ops") and s0.get("target") == pos:
            op = s0["ops"].pop(0)
            ok = True
            if op[0] == "FEED" and inv.get("WHEAT", 0) <= 0: ok = False
            if op[0] == "FERTILIZE" and inv.get("FERTILIZER", 0) <= 0: ok = False
            if op[0] == "PLANT" and seeds.get(op[1], 0) <= 0: ok = False
            if ok:
                acts[u] = list(op)
                if op[0] == "FEED": inv["WHEAT"] = inv.get("WHEAT", 0) - 1
                if op[0] == "FERTILIZE": inv["FERTILIZER"] = inv.get("FERTILIZER", 0) - 1
                if op[0] == "PLANT": seeds[op[1]] = seeds.get(op[1], 0) - 1
                if op[0] == "PICKUP" and len(op) >= 3: inv[op[1]] = inv.get(op[1], 0) + int(op[2])
                if op[0] == "PLACE" and len(op) >= 3: inv[op[1]] = max(0, inv.get(op[1], 0) - int(op[2]))
                continue
            s0["ops"] = []
        if s0.get("target") and s0.get("target") != pos and s0.get("ops"):
            acts[u] = _step_toward(pos, s0["target"]); continue
        s0["ops"] = []; s0["target"] = None
        # 物资领取
        if plan and plan["kind"] == "ranch":
            need_feed = sum(1 for (x, y) in plan["route"] if isinstance(T(x, y), dict) and "animal" in T(x, y) and not T(x, y).get("fed_today"))
            if need_feed > 0 and inv.get("WHEAT", 0) <= 0 and shed.get("WHEAT", 0) > 0 and day < LAST:
                k2 = min(int(shed.get("WHEAT", 0)), 8, need_feed); shed["WHEAT"] -= k2
                acc = _nacc(pos)
                s0["target"] = acc; s0["ops"] = [["PICKUP", "WHEAT", k2]]
                acts[u] = (s0["ops"].pop(0) if pos == acc else _step_toward(pos, acc))
                if pos == acc: inv["WHEAT"] = inv.get("WHEAT", 0) + k2
                continue
        if plan and plan["kind"] == "field" and inv.get("FERTILIZER", 0) <= 0 and shed.get("FERTILIZER", 0) > 2 and hour < 4:
            k2 = min(int(shed.get("FERTILIZER", 0)), 8); shed["FERTILIZER"] -= k2
            acc = _nacc(pos)
            s0["target"] = acc; s0["ops"] = [["PICKUP", "FERTILIZER", k2]]
            acts[u] = (s0["ops"].pop(0) if pos == acc else _step_toward(pos, acc))
            if pos == acc: inv["FERTILIZER"] = inv.get("FERTILIZER", 0) + k2
            continue
        # 放动物（显式状态机：任何空闲工人可接单；任务不被打断）
        carrying = s0.get("carry_animal")
        if carrying:
            tgt = s0.get("carry_to")
            if tgt is None or (isinstance(T(*tgt), dict) and "animal" in T(*tgt)):
                # 目标失效重选
                frees = [t for t in pasture_set if isinstance(T(*t), dict) and T(*t).get("kind") == "PASTURE" and "animal" not in T(*t) and t not in placed]
                builds = [t for t in pasture_set if T(*t) is None and t not in placed]
                tgt = min(frees or builds, key=lambda t: _dist(pos, t)) if (frees or builds) else None
                s0["carry_to"] = tgt
            if tgt is not None:
                placed.add(tgt)
                if pos != tgt:
                    acts[u] = _step_toward(pos, tgt); continue
                if T(*tgt) is None:
                    acts[u] = ["BUILD_PASTURE"]; continue
                acts[u] = ["PLACE", carrying]
                s0.pop("carry_animal", None); s0.pop("carry_to", None)
                continue
        pending_place = [a for a in ANIMALS for _ in range(int(shed.get(a, 0)))]
        if pending_place and not s0.get("ops") and not any(US.get(v2, {}).get("carry_animal") == pending_place[0] for v2 in range(n_units) if v2 != u):
            a0 = pending_place[0]; acc = _nacc(pos)
            if pos == acc:
                acts[u] = ["PICKUP", a0, 1]
                shed[a0] -= 1
                s0["carry_animal"] = a0; s0["carry_to"] = None
            else:
                acts[u] = _step_toward(pos, acc)
            continue
        # 入库（PLACE 定量，保留工作物资）
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
        # ---- 巡回：route 上找下一个有活的块 ----
        if not plan: continue
        route = plan["route"]
        if not route: continue
        start = plan.get("i", 0) % len(route)
        chosen = None
        for k2 in range(len(route)):
            t = route[(start + k2) % len(route)]
            x, y = t; tt = T(x, y)
            if plan["kind"] == "ranch":
                if isinstance(tt, dict) and "animal" in tt:
                    ops = []
                    if not tt.get("fed_today") and day < LAST and inv.get("WHEAT", 0) > 0: ops.append(["FEED"])
                    if not tt.get("cared_today") and day < LAST: ops.append(["CARE"])
                    if tt.get("fertilizer_available"): ops.append(["COLLECT_FERTILIZER"])
                    yu = int(tt.get("yield_units", 0))
                    if yu >= P["animal_hmin"] or (yu > 0 and day >= 27): ops.append(["HARVEST"])
                    if ops:
                        chosen = (t, ops, (start + k2) % len(route)); break
            else:
                if tt is None:
                    crop = None
                    if t in reuse_set:
                        if day <= 1 and n_melon < P["melon_n"]: crop = "MELON"
                        elif P["straw_from"] <= day <= P["straw_last"] and n_straw < int(P["straw_n"] * (0.6 if n_berry_s == 0 and day >= 6 else 1.0)):
                            if seeds.get("STRAWBERRY", 0) > 0 or money >= 400: crop = "STRAWBERRY"
                        elif day > P["straw_last"] and day <= P["wheat_last"]:
                            crop = "CARROT" if (day >= P["carrot_from"] or n_pet_s >= 2) else "WHEAT"
                    elif day <= P["wheat_last"] and day >= 1:
                        crop = "CARROT" if (day >= P["carrot_from"] or n_pet_s >= 2) and n_pet_s else "WHEAT"
                    if crop:
                        if crop == "MELON": n_melon += 1
                        if crop == "STRAWBERRY": n_straw += 1
                        chosen = (t, [["PLANT", crop], ["WATER"]], (start + k2) % len(route)); break
                else:
                    ops = _tile_jobs(x, y, tt, day, hour, n_pet_s)
                    if ops:
                        chosen = (t, ops, (start + k2) % len(route)); break
        if chosen:
            t, ops, idx = chosen
            plan["i"] = idx
            s0["target"] = t; s0["ops"] = [list(o) for o in ops]
            if pos == t:
                op = s0["ops"].pop(0)
                okk = True
                if op[0] == "PLANT" and seeds.get(op[1], 0) <= 0: okk = False
                if op[0] == "FERTILIZE" and inv.get("FERTILIZER", 0) <= 0:
                    s0["ops"] and s0["ops"].pop(0) if False else None
                    op = s0["ops"].pop(0) if s0["ops"] else ["PASS"]
                if okk:
                    acts[u] = list(op)
                    if op[0] == "PLANT": seeds[op[1]] = seeds.get(op[1], 0) - 1
                    if op[0] == "FERTILIZE": inv["FERTILIZER"] = inv.get("FERTILIZER", 0) - 1
                    if op[0] == "FEED": inv["WHEAT"] = inv.get("WHEAT", 0) - 1
            else:
                acts[u] = _step_toward(pos, t)

    market = _market(st, shed, seeds, money, day, hour, turn, prices, unlocked, farm, town_shops, n_units, tiles)
    return {"farmer": acts[0], "hands": acts[1:], "market": market[:10]}


def _market(st, shed, seeds, money, day, hour, turn, prices, unlocked, farm, town_shops, n_units, tiles):
    orders = []
    # 开局硬编码（CornHub 实战验证的现金流水线；无信息依赖的固定骨架）
    if turn == 0:
        st["pend_animals"] = [a for a in st["pend_animals"] if False]   # d0 批次由硬编码涵盖
        return [["BUY_PRODUCT", "WHEAT", 13]]
    if turn == 1:
        # 13 麦全留饲料（撑到 d2-3 小麦首收）；甜瓜分两批（d1 回血后补）
        return [["BUY_ANIMAL", "COW", 2], ["BUY_ANIMAL", "SHEEP", 2],
                ["HIRE"], ["HIRE"], ["HIRE"], ["HIRE"], ["HIRE"],
                ["BUY_SEED", "WHEAT", 7], ["BUY_SEED", "MELON", 6]]
    endgame = turn >= 24 * 28
    n_anim = sum(1 for row in tiles for x in row if isinstance(x, dict) and "animal" in x)
    n_anim += sum(int(shed.get(a, 0)) for a in ANIMALS)          # 仓库/搬运中
    n_anim += sum(n for _, n in st.get("pend_animals", []))       # 待购
    feed_keep = 0 if endgame else min(20, n_anim + 4)
    fert_keep = 0 if turn >= 24 * 27 else P["fert_keep"]
    sells = []
    for item in PRODUCTS:
        q = int(shed.get(item, 0))
        if item == "WHEAT": q -= feed_keep
        if item == "FERTILIZER": q -= fert_keep
        if q <= 0: continue
        pr = prices.get(item, BASE[item])
        if not endgame and item != "MELON":
            rate = 2
            for sh in town_shops:
                if item in MENU.get(sh, ()): rate += 2 if len(MENU[sh]) > 1 else 4
            q = min(q, int(rate * P["rate_mult"]))
        sells.append((q * pr, ["SELL", item, q]))
    sells.sort(key=lambda z: -z[0])
    orders += [o for _, o in sells[:6 if not endgame else 10]]
    cash = money + sum(v * 0.7 for v, _ in sells[:6])
    if turn >= 24 * 29 + 20: return orders
    wheat_have = int(shed.get("WHEAT", 0))
    n_pend_anim = sum(n for _, n in st["pend_animals"])
    need_mouths = n_anim + n_pend_anim
    if day <= 28 and wheat_have < need_mouths + 2 and prices.get("WHEAT", 25) <= 80:
        q = min(need_mouths + 4 - wheat_have, 20)
        if day == 0: q = max(q, 8)
        wp = prices.get("WHEAT", 25)
        q = min(q, int(max(0, cash - 100) // max(1, wp)))    # 永远保底 100 现金
        if q > 0:
            orders.insert(0, ["BUY_PRODUCT", "WHEAT", q]); cash -= q * wp
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
    n_extra = len(unlocked) - 1
    if st["pend_land"] > 0 and n_extra < 3:
        price = LAND_PRICES[n_extra]
        if cash >= price + 60 and len(orders) < 10:
            orders.append(["BUY_LAND"]); cash -= price; st["pend_land"] -= 1
    rest = []
    for a, n in st["pend_animals"]:
        if day == 0 and a == "SHEEP":
            rest.append([a, n]); continue        # 羊推迟到 d1+：给饲料/种子让出开局现金
        cost = ANIMALS[a]["cost"] * n
        if day <= 16 and cash >= cost + 300 and len(orders) < 10 and sum(shed.values()) + n < 95:
            orders.append(["BUY_ANIMAL", a, n]); cash -= cost
        elif day <= 16 and n > 1 and cash >= ANIMALS[a]["cost"] + 300 and len(orders) < 10:
            k3 = int((cash - 300) // ANIMALS[a]["cost"])
            if k3 > 0:
                orders.append(["BUY_ANIMAL", a, k3]); cash -= k3 * ANIMALS[a]["cost"]
                if n - k3 > 0: rest.append([a, n - k3])
        else: rest.append([a, n])
    st["pend_animals"] = rest if day <= 16 else []
    plant_need = {"STRAWBERRY": 4 if day >= P["straw_from"] - 1 and day <= P["straw_last"] else 0,
                  "MELON": P["melon_n"] if day <= 1 else 0,
                  "WHEAT": 8 if day <= P["wheat_last"] else 0,
                  "CARROT": 6 if (day >= P["carrot_from"] - 1) else 0}
    for crop in ("MELON", "STRAWBERRY", "WHEAT", "CARROT"):
        need = plant_need.get(crop, 0) - int(seeds.get(crop, 0))
        if need <= 0 or len(orders) >= 10: continue
        c0 = CROPS[crop]["seed"]
        n = min(need, int(max(0, cash - 10) // c0))
        if n > 0:
            orders.append(["BUY_SEED", crop, n]); cash -= n * c0
    return orders
