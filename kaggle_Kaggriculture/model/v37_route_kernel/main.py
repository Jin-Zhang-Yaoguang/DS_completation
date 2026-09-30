"""V15 闭环调度器 v2：每步由观测现算动作（原创，不回放任何 tape）。

- 布局：动物压在棚接入格与其邻环；作物由近到远。
- 任务捆绑：一次到访完成 浇水→收获→补种→浇水 / 喂→照料→收肥→收产品，减少走动。
- 喂养前校验单位随身小麦；饲料按已有动物两天量采购。
- 市场：10 槽预算；SELL 前置；购买计划为跨小时/跨天待办。
"""
import os, json

BS = 10
ACCESS = [(4, 4), (5, 4), (4, 5), (5, 5)]
QUAD_OF = lambda x, y: ("N" if y < 5 else "S") + ("W" if x < 5 else "E")
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
LAND_PRICES = [1000, 2000, 4000]
FIB = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987]

DEFAULT_PLAN = {
    # 雇工数按 V120 路线（fib 累计费用：9 人 88 / 10 人 143 / 11 人 232 / 12 人 376）
    "hands": {0: 5, 1: 4, 2: 4, 3: 5, 4: 4, 5: 5, 6: 8, 7: 8, 8: 10, 9: 9, 10: 11, 11: 11, 12: 9, 13: 10, 14: 10, 15: 11},
    "hands_default": 12,
    # 动物：V120 路线 10 牛 8 羊
    "animals": {0: [["COW", 2], ["SHEEP", 2]], 2: [["COW", 1]], 3: [["COW", 1]], 6: [["COW", 2]], 7: [["COW", 2]],
                8: [["COW", 1], ["SHEEP", 2]], 9: [["COW", 1], ["SHEEP", 1]], 10: [["SHEEP", 2]], 11: [["SHEEP", 1]]},
    "animal_last_day": 16,
    "land": {6: 1, 11: 1},
    "land_day1": 6, "land_day2": 11,
    "melon_tiles": 12,
    "straw": {5: 4, 6: 8, 7: 4, 8: 4, 9: 4, 11: 9},
    "wheat_tiles": 7, "wheat_tiles_mid": 14, "wheat_tiles_late": 30,
    "animal_cash_reserve": 240,
    "feed_days": 3, "wheat_buy_cap": 80,
    "fert_reserve": 30, "fertilize_crops": ["STRAWBERRY"],
    "harvest_wheat_age": 4,
    "deposit_min": 10,
    "pasture_radius": 3.0, "pasture_reserve": 18, "animals_per_ranch": 3,
    "ranch_bias": 6.0, "v_fert_coef": 1.2, "v_water_ongoing": 0.5,
    "last_plant_day": {"WHEAT": 27, "CARROT": 26, "STRAWBERRY": 16, "MELON": 15, "TOMATO": 18},
}
_raw = os.environ.get("V15_PARAMS", "")
PLAN = json.loads(json.dumps(DEFAULT_PLAN))
if _raw:
    _ov = json.load(open(_raw)) if os.path.exists(_raw) else json.loads(_raw)
    for k, v in _ov.items():
        if isinstance(v, dict) and isinstance(PLAN.get(k), dict):
            d = dict(PLAN[k]); d.update({(int(kk) if str(kk).lstrip("-").isdigit() else kk): vv for kk, vv in v.items()}); PLAN[k] = d
        else:
            PLAN[k] = v
# json 往返把 int 键变成 str，统一回 int
for k in ("hands", "animals", "land", "straw"):
    PLAN[k] = {(int(kk) if str(kk).lstrip("-").isdigit() else kk): vv for kk, vv in PLAN[k].items()}
PLAN["land"] = {int(PLAN.get("land_day1", 6)): 1, int(PLAN.get("land_day2", 11)): 1}

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


def _nearest_access(pos):
    return min(ACCESS, key=lambda a: _dist(pos, a))


def _layout(unlocked):
    tiles = [(x, y) for y in range(BS) for x in range(BS) if QUAD_OF(x, y) in unlocked]
    key = lambda t: (abs(t[0] - 4.5) + abs(t[1] - 4.5), t[1], t[0])
    tiles.sort(key=key)
    return tiles


def _state(seat, turn):
    st = _S.get(seat)
    if st is None or turn <= st["last"]:
        st = {"last": -1, "day_plan": {}, "pending": None, "units": {}, "roles": None}
        _S[seat] = st
    st["last"] = turn
    return st


_TAPE_UNTIL = PLAN.get("tape_until_day")
_TAPE_AGENT = None
if _TAPE_UNTIL is not None:
    _here = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
        "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v15_closed_loop"
    _src = open(os.path.join(_here, "..", "v10_rule_distill", "dist", "main.py")).read()
    _ns = {"__name__": "v15_tape_base"}
    exec(compile(_src, "v10_dist_main.py", "exec"), _ns)
    _TAPE_AGENT = _ns["agent"]


def agent(obs, configuration=None):
    try:
        if _TAPE_AGENT is not None:
            d = int(obs.get("day", 0) or 0)
            if d < int(_TAPE_UNTIL):
                return _TAPE_AGENT(obs, configuration)
        return _agent(obs)
    except Exception:
        farms = obs.get("farms") or []
        p = int(obs.get("player", 0) or 0)
        n = len(farms[p].get("hands") or []) if farms and p < len(farms) else 0
        return {"farmer": ["PASS"], "hands": [["PASS"]] * n, "market": []}


def _snake_key(t):
    return (t[1], t[0] if t[1] % 2 == 0 else -t[0])


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
    prices = dict((obs.get("market") or {}).get("prices") or {})
    st = _state(seat, turn)
    LAST = 29
    ENDGAME = turn >= 24 * 29 + 16

    def T(x, y): return tiles[y][x]
    animal_tiles, plant_tiles, weed_tiles, empty_tiles, struct_empty = [], [], [], [], []
    for y in range(BS):
        for x in range(BS):
            tt = tiles[y][x]
            if tt == "LOCKED": continue
            if tt is None: empty_tiles.append((x, y))
            elif isinstance(tt, dict):
                if "animal" in tt: animal_tiles.append((x, y))
                elif tt.get("kind") == "PLANT": plant_tiles.append((x, y))
                elif tt.get("kind") == "WEED": weed_tiles.append((x, y))
                elif tt.get("kind") in ("PASTURE", "COOP"): struct_empty.append((x, y))
    n_animals = len(animal_tiles)
    shed_animals = [(a, int(shed.get(a, 0))) for a in ANIMALS if int(shed.get(a, 0)) > 0]
    carried = sum(int(i.get(a, 0)) for i in invs for a in ANIMALS)
    order = _layout(unlocked)
    empty_set = set(empty_tiles)

    # 牧场环
    pasture_set = set(animal_tiles) | set(struct_empty)
    _reserve = int(PLAN.get("_dyn_pasture", PLAN.get("pasture_reserve", 18)))
    for (x, y) in order:
        if abs(x - 4.5) + abs(y - 4.5) <= PLAN.get("pasture_radius", 3.0) and len(pasture_set) < _reserve:
            pasture_set.add((x, y))
    want_past = max(0, sum(n for _, n in shed_animals) + carried - len(struct_empty))
    build_tiles = []
    for tt in order:
        if want_past <= 0: break
        if tt in pasture_set and tt in empty_set:
            build_tiles.append(tt); want_past -= 1
    build_set = set(build_tiles)

    # 种子预算与作物配额
    seed_budget = {c: int(seeds.get(c, 0)) for c in CROPS}
    lp = PLAN["last_plant_day"]
    crop_count = {c: 0 for c in CROPS}
    for (x, y) in plant_tiles: crop_count[T(x, y)["crop"]] += 1
    straw_cap = int(sum(int(v) for d, v in PLAN["straw"].items() if int(d) <= day) * float(PLAN.get("_straw_scale", 1.0)))
    caps = {"MELON": PLAN["melon_tiles"], "STRAWBERRY": straw_cap, "TOMATO": PLAN.get("tomato_cap", 0), "CARROT": PLAN.get("carrot_cap", 0), "WHEAT": 10 ** 6}
    plant_reserved = {c: 0 for c in CROPS}   # 本步已下达的 PLANT 数（原子校验）

    # 蓝图分区：内环 = 距牧场质心最近的 premium_zone 块（甜瓜/草莓专区，时序复用），其余 = 小麦区
    _pz = int(PLAN.get("premium_zone", 60))
    _nonpast = [tt for tt in order if tt not in pasture_set]
    inner_zone = set(_nonpast[:_pz])   # order 已按离中心距离排序

    def pick_crop(commit=True, at=None):
        for c in ("MELON", "STRAWBERRY", "TOMATO", "CARROT", "WHEAT"):
            if not (seed_budget.get(c, 0) > 0 and day <= lp[c] and crop_count[c] < caps[c]):
                continue
            if at is not None and c in ("MELON", "STRAWBERRY", "TOMATO") and at not in inner_zone:
                continue   # 高价值作物只种内环，保持功能分区不混插
            if commit:
                seed_budget[c] -= 1; crop_count[c] += 1
            return c
        return None

    # ---------- 需求对齐：按已解锁商店动态调整生产计划 ----------
    town_shops = list((obs.get("town") or {}).get("unlocked_shops") or [])
    n_yarn_s = town_shops.count("YARN_STORE")
    n_dairy_s = sum(town_shops.count(x) for x in ("PIZZA_SHOP", "ICE_CREAM_SHOP", "SMOOTHIE_SHOP"))
    n_berry_s = sum(town_shops.count(x) for x in ("BRUNCH_SPOT", "ICE_CREAM_SHOP", "SMOOTHIE_SHOP", "FARMERS_MARKET"))
    n_pet_s = town_shops.count("PET_CAFE")
    st["_shops2"] = town_shops
    if PLAN.get("demand_align", True) and day >= 5:
        want_sheep = int(PLAN.get("sheep_floor", 2)) if n_yarn_s == 0 else min(8, 4 + 4 * n_yarn_s)
        want_cow = max(4, min(10, int(PLAN.get("cow_base", 3)) + 2 * n_dairy_s))
        pend = st.get("pending")
        if pend:
            cur_sheep = sum(1 for (x, y) in animal_tiles if T(x, y).get("animal") == "SHEEP") + int(shed.get("SHEEP", 0))
            cur_cow = sum(1 for (x, y) in animal_tiles if T(x, y).get("animal") == "COW") + int(shed.get("COW", 0))
            new_animals = []
            for a, n in pend.get("animals", []):
                cap = want_sheep if a == "SHEEP" else want_cow
                have = cur_sheep if a == "SHEEP" else cur_cow
                n2 = max(0, min(n, cap - have))
                if n2 > 0:
                    new_animals.append([a, n2])
                    if a == "SHEEP": cur_sheep += n2
                    else: cur_cow += n2
            pend["animals"] = new_animals
        PLAN["_dyn_pasture"] = max(len(animal_tiles) + 1, want_sheep + want_cow + 1)
        PLAN["_straw_scale"] = float(PLAN.get("straw_scale_zero", 0.5)) if n_berry_s == 0 else (1.0 if n_berry_s >= 2 else float(PLAN.get("straw_scale_one", 0.75)))
        PLAN["carrot_cap"] = 8 * n_pet_s if day >= 6 else 0

    # ---------- 每块地"需要做什么" ----------
    def animal_ops(x, y):
        tt = T(x, y); ops = []
        if not (isinstance(tt, dict) and "animal" in tt): return ops
        if not tt.get("fed_today") and day < LAST: ops.append(["FEED"])
        if not tt.get("cared_today") and day < LAST: ops.append(["CARE"])
        if tt.get("fertilizer_available"): ops.append(["COLLECT_FERTILIZER"])
        yu = int(tt.get("yield_units", 0) or 0); held = ANIMALS[tt["animal"]]["held"]
        if yu > 0 and (yu >= PLAN.get("animal_harvest_min", 2) or yu >= held - 1 or day >= 27): ops.append(["HARVEST"])
        return ops

    def plant_ops(x, y, unit_has_fert):
        tt = T(x, y)
        if tt is None:
            if ENDGAME or (x, y) in pasture_set: return []
            c = pick_crop(commit=False, at=(x, y))
            return [["PLANT", c], ["WATER"]] if c else []
        if not isinstance(tt, dict): return []
        if tt.get("kind") == "WEED":
            if ENDGAME: return []
            if (x, y) in pasture_set: return [["DIG"]]
            c = pick_crop(commit=False, at=(x, y))
            return [["DIG"], ["PLANT", c], ["WATER"]] if c else [["DIG"]]
        if tt.get("kind") != "PLANT": return []
        cd = CROPS[tt["crop"]]; age = day - int(tt.get("planted_day", day)); ops = []
        yu = int(tt.get("yield_units", 0) or 0)
        need_water = (not tt.get("watered_today")) and (cd["ongoing"] or age <= cd["maxday"]) and day <= LAST
        if cd["ongoing"]:
            hi = prices.get(tt["crop"], BASE[tt["crop"]]) >= PLAN.get("eager_price_frac", 0.6) * BASE[tt["crop"]]
            last_prod = int(tt.get("max_lifespan_step", -1) or -1) > 0   # 已完成最后一次产出，随后腐烂
            ripe = yu >= 2 or (yu >= 1 and (hi or last_prod or hour >= 18 or day >= LAST - 1))
        else:
            yu_after = yu + (1 if (need_water and (cd["maxday"] + 1) // 2 <= age <= cd["maxday"]) else 0)
            hw = int(PLAN.get("harvest_wheat_age", 4)) if tt["crop"] == "WHEAT" else cd["maxday"]
            ripe = yu > 0 and (yu_after >= cd["maxy"] or age >= hw or day >= LAST or (age >= cd["maxday"] - 1 and hour >= 21))
            if tt["crop"] == "MELON" and age < cd["first"]: ripe = False
            meh = PLAN.get("melon_early_hour")
            if tt["crop"] == "MELON" and meh is not None and age == cd["first"] - 1 and hour >= int(meh) and yu >= 4: ripe = True
        if need_water: ops.append(["WATER"])
        if (cd["ongoing"] and age >= cd["first"] - 1 and int(tt.get("fertilized_until_day", -1)) < day + 1 and day <= LAST - 2
                and tt["crop"] in PLAN.get("fertilize_crops", ["STRAWBERRY"]) and unit_has_fert):
            ops.append(["FERTILIZE"])
        if (tt["crop"] == "MELON" and (cd["maxday"] + 1) // 2 <= age <= cd["maxday"] and int(tt.get("fertilized_until_day", -1)) < day
                and "MELON" in PLAN.get("fertilize_crops", []) and unit_has_fert):
            ops.append(["FERTILIZE"])
        if ripe:
            ops.append(["HARVEST"])
            if not cd["ongoing"] and day <= lp["WHEAT"] and not ENDGAME:
                c = pick_crop(commit=False, at=(x, y))
                if c: ops += [["PLANT", c], ["WATER"]]
            elif cd["ongoing"] and not ENDGAME and day <= lp["WHEAT"]:
                # ongoing 完账（最后一次产出）后立即转小麦，不等腐烂成杂草
                done_all = age >= cd["first"] + cd["interval"] * (cd["maxy"] - 1) + 1
                if done_all:
                    ops += [["DIG"], ["PLANT", "WHEAT"], ["WATER"]]
        return ops

    def _vp(item):
        return max(prices.get(item, BASE.get(item, 30)), float(PLAN.get("v_base_floor", 0.8)) * BASE.get(item, 30))

    def task_value(tt, u):
        """(x,y) 块上任务链的边际价值（金币）。0 = 无任务。"""
        if tt in animal_tiles:
            x2 = T(*tt)
            v = 0.0
            if not x2.get("fed_today"): v += float(PLAN.get("v_feed", 55.0))
            if not x2.get("cared_today"): v += float(PLAN.get("v_care", 30.0)) + float(PLAN.get("v_care_bonus", 8.0)) * int(x2.get("pending_care_bonus", 0))
            if x2.get("fertilizer_available"): v += _vp("FERTILIZER") * float(PLAN.get("v_fert_coef", 0.9))
            if int(x2.get("yield_units", 0)) > 0:
                v += int(x2["yield_units"]) * _vp(ANIMALS[x2["animal"]]["product"])
            return v
        if tt in build_set: return 120.0
        x2 = T(*tt)
        if x2 is None or (isinstance(x2, dict) and x2.get("kind") == "WEED"):
            if ENDGAME or tt in pasture_set: return 15.0 if isinstance(x2, dict) else 0.0
            c = pick_crop(commit=False, at=tt)
            if not c: return 12.0 if isinstance(x2, dict) else 0.0
            v0 = _vp(c) * float(PLAN.get("v_plant_coef", 2.2))
            # 种植波次：空地堆积（象限解锁）时临时倍增，突击种完即回落
            if len(empty_tiles) >= int(PLAN.get("wave_threshold", 999)):
                v0 *= float(PLAN.get("wave_boost", 4.0))
            return v0
        if not isinstance(x2, dict) or x2.get("kind") != "PLANT": return 0.0
        cd2 = CROPS[x2["crop"]]; age2 = day - int(x2.get("planted_day", day))
        pr2 = _vp(x2["crop"])
        v = 0.0
        yu2 = int(x2.get("yield_units", 0) or 0)
        unw = int(x2.get("consecutive_unwatered", 0))
        watered = bool(x2.get("watered_today"))
        if not watered:
            if unw >= 1:      # 濒死：挽救剩余期望产出
                if cd2["ongoing"]:
                    left = max(0, cd2["maxy"] - max(0, (age2 - cd2["first"]) // max(1, cd2["interval"]) + 1))
                    v += yu2 * pr2 + left * pr2 * 1.4
                else:
                    v += max(1, yu2) * pr2 + pr2 * 2
            if not cd2["ongoing"] and (cd2["maxday"] + 1) // 2 <= age2 <= cd2["maxday"]:
                bonus = 2 if int(x2.get("fertilized_until_day", -1)) >= day else 1
                v += bonus * pr2 * 0.9      # 今日浇水 = 未来收获 +bonus
            elif cd2["ongoing"]:
                v += pr2 * float(PLAN.get("v_water_ongoing", 0.75))
        if yu2 > 0 and (yu2 >= 2 or not cd2["ongoing"]):
            v += yu2 * pr2                  # 可收获
        if (cd2["ongoing"] and x2["crop"] in PLAN.get("fertilize_crops", ["STRAWBERRY"])
                and age2 >= cd2["first"] - 1 and int(x2.get("fertilized_until_day", -1)) < day + 1
                and day <= LAST - 2):
            v += 2 * pr2 - _vp("FERTILIZER") * 0.6   # 施肥期权
        return v

    # ---------- 角色与分区（每天一次；手数变化时重算） ----------
    roles = st.get("roles")
    n_anim_all = n_animals + sum(n for _, n in shed_animals) + carried
    if roles is None or roles.get("day") != day or roles.get("n") != n_units:
        n_ranch = min(n_units, max(1, -(-n_anim_all // PLAN.get("animals_per_ranch", 4)))) if n_anim_all > 0 else 0
        if n_units <= 2: n_ranch = min(n_ranch, 1)
        by_near = sorted(range(n_units), key=lambda u: (_dist(positions[u], _nearest_access(positions[u])), u))
        ranch_units = by_near[:n_ranch]
        field_units = [u for u in range(n_units) if u not in ranch_units]
        ring = sorted(list(pasture_set), key=_snake_key)
        groups = {}
        if ranch_units:
            k = len(ranch_units); n = len(ring)
            for i, u in enumerate(ranch_units):
                groups[u] = ring[(i * n) // k:((i + 1) * n) // k]
        crop_all = sorted([tt for tt in order if tt not in pasture_set], key=_snake_key)
        if field_units:
            k = len(field_units); n = len(crop_all)
            for i, u in enumerate(field_units):
                groups[u] = crop_all[(i * n) // k:((i + 1) * n) // k]
        new_day = (st.get("roles") is None) or (st["roles"].get("day") != day)
        roles = {"day": day, "n": n_units, "ranch": set(ranch_units), "groups": groups}
        st["roles"] = roles
        if new_day: st["units"] = {}
    ranch = roles["ranch"]; groups = roles["groups"]
    US = st["units"]   # u -> {"target": (x,y) or None, "ops": [...], "phase": ...}

    unit_actions = [["PASS"] for _ in range(n_units)]
    unfed_total = sum(1 for (x, y) in animal_tiles if not T(x, y).get("fed_today"))
    # 待放置的动物：分给牧场手（棚内动物数）
    place_queue = []
    for a, n in shed_animals:
        place_queue += [a] * n
    free_structs = sorted(list(struct_empty), key=lambda tt: _dist(tt, ACCESS[0]))
    for tt in build_tiles: free_structs.append(tt)   # 需先建

    def unit_value(inv):
        return sum(v * BASE.get(k, 0) for k, v in inv.items() if k in PRODUCTS and k not in ("WHEAT", "FERTILIZER"))

    def unit_nprod(inv):
        return sum(v for k, v in inv.items() if k in PRODUCTS and k not in ("WHEAT", "FERTILIZER"))

    claimed_tiles = set()
    for u in range(n_units):
        s = US.get(u)
        if s and s.get("target") and s.get("ops"): claimed_tiles.add(s["target"])
    # 濒死块 -> 指派最近的一个工人（其余工人不参与救火，保生产）
    rescue_of = {}
    if PLAN.get("rescue_top", False):
        for (rx, ry) in plant_tiles:
            x3 = T(rx, ry)
            if (isinstance(x3, dict) and int(x3.get("consecutive_unwatered", 0)) >= 1
                    and not x3.get("watered_today")):
                u_near = min(range(n_units), key=lambda uu: _dist(positions[uu], (rx, ry)))
                rescue_of[u_near] = (rx, ry)

    def needs_work(tt, u):
        if tt in claimed_tiles: return False
        if tt in animal_tiles: return bool(animal_ops(*tt))
        if tt in build_set: return True
        return bool(plant_ops(tt[0], tt[1], int(invs[u].get("FERTILIZER", 0)) > 0))

    for u in range(n_units):
        pos = positions[u]; inv = invs[u]
        s = US.setdefault(u, {"target": None, "ops": [], "did_pickup": 0})
        # 1) 若有进行中的 op 队列且在目标上：执行
        if s.get("ops") and s.get("target") == pos:
            op = s["ops"].pop(0)
            # 校验：FEED 无麦 / FERTILIZE 无肥 / PLANT 无种子 → 跳过
            if op[0] == "FEED" and int(inv.get("WHEAT", 0)) <= 0: op = None
            elif op[0] == "FERTILIZE" and int(inv.get("FERTILIZER", 0)) <= 0: op = None
            elif op[0] == "PLANT":
                c = op[1]
                if seed_budget.get(c, 0) - plant_reserved[c] <= 0: op = None
                else: plant_reserved[c] += 1
            if op is None:
                if s["ops"]:
                    op = s["ops"].pop(0)
                    if op[0] == "WATER" and not (isinstance(T(*pos), dict) and T(*pos).get("kind") == "PLANT"): op = None
            if op is not None:
                unit_actions[u] = list(op)
                if op[0] == "FEED": inv["WHEAT"] = int(inv.get("WHEAT", 0)) - 1
                if op[0] == "FERTILIZE": inv["FERTILIZER"] = int(inv.get("FERTILIZER", 0)) - 1
                if op[0] == "DROP": inv.clear()
                if op[0] == "PLACE" and len(op) >= 3: inv[op[1]] = max(0, int(inv.get(op[1], 0)) - int(op[2]))
                if op[0] == "PICKUP" and op[1] in ("WHEAT", "FERTILIZER"): inv[op[1]] = int(inv.get(op[1], 0)) + int(op[2])
                continue
        # 2) 在途：继续走（顺路作业：脚下块恰有待办则顺手做一步，零移动成本）
        if s.get("target") and s.get("target") != pos and s.get("ops"):
            if PLAN.get("enroute_work", False) and pos not in claimed_tiles and pos not in animal_tiles:
                tt0 = T(*pos) if 0 <= pos[0] < BS and 0 <= pos[1] < BS else None
                if isinstance(tt0, dict) and tt0.get("kind") == "PLANT" and not tt0.get("watered_today"):
                    cd0 = CROPS[tt0["crop"]]; age0 = day - int(tt0.get("planted_day", day))
                    if (cd0["ongoing"] or age0 <= cd0["maxday"]) and day <= LAST:
                        unit_actions[u] = ["WATER"]; claimed_tiles.add(pos); continue
            unit_actions[u] = _step_toward(pos, s["target"]); continue
        # 2b) 到访批处理：当前块做完后就近接续（dist<=2 的待办块），消灭全局重选的布朗运动
        _bc = s.get("batch_count", 0)
        if s.get("target") != pos: s["batch_count"] = 0
        _batch_on = PLAN.get("visit_batch", False) or (PLAN.get("batch_evening", True) and hour >= int(PLAN.get("batch_from_hour", 18)))
        if (_batch_on and u not in ranch and not s.get("ops") and s.get("target") == pos
                and _bc < int(PLAN.get("batch_limit", 4))):
            near = [tt for tt in order if tt not in claimed_tiles and _dist(pos, tt) <= int(PLAN.get("batch_radius", 2))
                    and tt not in animal_tiles and needs_work(tt, u)]
            if near:
                tgt2 = min(near, key=lambda tt: _dist(pos, tt))
                ops2 = plant_ops(tgt2[0], tgt2[1], int(inv.get("FERTILIZER", 0)) > 0)
                if ops2:
                    s["batch_count"] = _bc + 1
                    s["target"] = tgt2; s["ops"] = ops2; claimed_tiles.add(tgt2)
                    if pos == tgt2:
                        op = ops2[0]; s["ops"] = ops2[1:]
                        if op[0] == "PLANT":
                            if seed_budget.get(op[1], 0) - plant_reserved[op[1]] < 0: op = ["PASS"]
                            else: plant_reserved[op[1]] += 1; pick_crop(commit=True)
                        if op[0] == "FERTILIZE": inv["FERTILIZER"] = int(inv.get("FERTILIZER", 0)) - 1
                        unit_actions[u] = list(op)
                    else:
                        unit_actions[u] = _step_toward(pos, tgt2)
                    continue
        # 3) 选下一个目标
        s["ops"] = []; s["target"] = None
        grp = groups.get(u, [])
        is_ranch = u in ranch
        # 3a) 牧场手：先取麦（有未喂动物且身上无麦）
        if is_ranch and unfed_total > 0 and int(inv.get("WHEAT", 0)) <= 0 and int(shed.get("WHEAT", 0)) > 0 and day < LAST:
            k = min(int(shed.get("WHEAT", 0)), max(1, sum(1 for tt in grp if tt in animal_tiles and not T(*tt).get("fed_today"))), 8)
            acc = _nearest_access(pos)
            s["target"] = acc; s["ops"] = [["PICKUP", "WHEAT", k]]
            shed["WHEAT"] = int(shed.get("WHEAT", 0)) - k
            if pos == acc:
                unit_actions[u] = s["ops"].pop(0); inv["WHEAT"] = int(inv.get("WHEAT", 0)) + k
            else:
                unit_actions[u] = _step_toward(pos, acc)
            continue
        # 3b) 田间手：日初取肥（有需要施肥的草莓且身上无肥）
        if (not is_ranch) and int(inv.get("FERTILIZER", 0)) <= 0 and int(shed.get("FERTILIZER", 0)) > 0 and s.get("did_pickup", 0) < 4:
            need_f = sum(1 for tt in grp if tt in plant_tiles and CROPS[T(*tt)["crop"]]["ongoing"] and T(*tt)["crop"] in PLAN.get("fertilize_crops", ["STRAWBERRY"])
                         and int(T(*tt).get("fertilized_until_day", -1)) < day and day - int(T(*tt).get("planted_day", day)) >= CROPS[T(*tt)["crop"]]["first"] - 2)
            if (need_f >= 2 and (not s.get("ops"))) or (need_f > 0 and _dist(pos, _nearest_access(pos)) <= 2):
                k = min(int(shed.get("FERTILIZER", 0)), need_f, 8); acc = _nearest_access(pos)
                s["did_pickup"] = s.get("did_pickup", 0) + 1; s["target"] = acc; s["ops"] = [["PICKUP", "FERTILIZER", k]]
                shed["FERTILIZER"] = int(shed.get("FERTILIZER", 0)) - k
                if pos == acc:
                    unit_actions[u] = s["ops"].pop(0); inv["FERTILIZER"] = int(inv.get("FERTILIZER", 0)) + k
                else:
                    unit_actions[u] = _step_toward(pos, acc)
                continue
        # 3c) 放动物（牧场手，棚内有动物且有空结构）
        if place_queue and free_structs and (is_ranch or not grp or not any(needs_work(tt, u) for tt in grp)) and (pos in ACCESS or _dist(pos, _nearest_access(pos)) <= 2):
            a = place_queue.pop(0); tgt = free_structs.pop(0); acc = _nearest_access(pos)
            s["target"] = acc; s["ops"] = [["PICKUP", a, 1]]; s["place_to"] = tgt; s["place_a"] = a
            if pos == acc:
                unit_actions[u] = s["ops"].pop(0); s["target"] = tgt
                s["ops"] = ([["BUILD_PASTURE"]] if tgt in build_set else []) + [["PLACE", a]]
                inv[a] = int(inv.get(a, 0)) + 1
            else:
                unit_actions[u] = _step_toward(pos, acc)
            claimed_tiles.add(tgt); continue
        if s.get("place_to") and int(inv.get(s.get("place_a", ""), 0)) > 0:
            tgt = s["place_to"]; s["target"] = tgt
            s["ops"] = ([["BUILD_PASTURE"]] if tgt in build_set else []) + [["PLACE", s["place_a"]]]
            s.pop("place_to", None)
            if pos == tgt: unit_actions[u] = s["ops"].pop(0)
            else: unit_actions[u] = _step_toward(pos, tgt)
            claimed_tiles.add(tgt); continue
        # 3d) 入库判断
        val = unit_value(inv); npd = unit_nprod(inv)
        acc = _nearest_access(pos); dd = _dist(pos, acc)
        want_dep = npd > 0 and (val >= PLAN.get("deposit_value", 600) or npd >= PLAN.get("deposit_min", 10) or hour >= 21 or ENDGAME or (dd <= 1 and val >= 150) or (is_ranch and dd <= 2 and val >= 250))
        # 3e-pre) V37：田间手走预排带状巡回（route 上找下一个有活的块）
        if not is_ranch:
            rt = st.setdefault("routes", {})
            if rt.get("day") != day or u not in rt:
                fu = [uu for uu in range(n_units) if uu not in ranch]
                cols = sorted([tt for tt in order if tt not in pasture_set], key=lambda t: (t[0], t[1]))
                nb = len(cols); kb = max(1, len(fu))
                for i2, uu in enumerate(fu):
                    band = cols[(i2 * nb) // kb:((i2 + 1) * nb) // kb]
                    band.sort(key=lambda t: (t[0], t[1] if t[0] % 2 == 0 else -t[1]))
                    rt[uu] = {"band": band, "i": 0}
                rt["day"] = day
            band = (rt.get(u) or {}).get("band") or []
            if band:
                start = rt[u].get("i", 0) % len(band)
                found = None
                for k3 in range(len(band)):
                    tt = band[(start + k3) % len(band)]
                    if tt in claimed_tiles: continue
                    if not needs_work(tt, u): continue
                    found = (tt, (start + k3) % len(band)); break
                if found:
                    tt, idx = found
                    rt[u]["i"] = idx
                    ops = plant_ops(tt[0], tt[1], int(inv.get("FERTILIZER", 0)) > 0)
                    if ops:
                        s["target"] = tt; s["ops"] = ops; claimed_tiles.add(tt)
                        for o in ops:
                            if o[0] == "PLANT": pick_crop(commit=True)
                        if pos == tt:
                            op = s["ops"].pop(0)
                            if op[0] == "PLANT":
                                if seed_budget.get(op[1], 0) - plant_reserved[op[1]] < 0: op = ["PASS"]
                                else: plant_reserved[op[1]] += 1
                            if op[0] == "FERTILIZE": inv["FERTILIZER"] = int(inv.get("FERTILIZER", 0)) - 1
                            unit_actions[u] = list(op)
                        else:
                            unit_actions[u] = _step_toward(pos, tt)
                        continue
        # 3e) V22：全场候选，按 value/(1+dist) 全局贪心（牧场手保留动物优先权重）
        # V22.1 微分区固定巡回：田间工人优先做自己环内（groups[u]）有活的块，
        # 沿环推进不折返；环内无活才进入全局候选（保留跨区支援能力）
        if PLAN.get("patrol", False) and (not is_ranch) and grp:
            ring = grp
            start = st.setdefault("patrol_idx", {}).get(u, 0) % len(ring)
            for k2 in range(len(ring)):
                tt = ring[(start + k2) % len(ring)]
                if tt in claimed_tiles: continue
                if tt in animal_tiles or tt in build_set: continue
                if not needs_work(tt, u): continue
                if task_value(tt, u) <= 0: continue
                st["patrol_idx"][u] = (start + k2) % len(ring)
                s["target"] = tt; s["ops"] = plant_ops(tt[0], tt[1], int(inv.get("FERTILIZER", 0)) > 0)
                break
            if s.get("ops"):
                if int(inv.get("WHEAT", 0)) <= 0: s["ops"] = [o for o in s["ops"] if o[0] != "FEED"]
                if s["ops"]:
                    for o in s["ops"]:
                        if o[0] == "PLANT": pick_crop(commit=True)
                    claimed_tiles.add(s["target"])
                    if pos == s["target"]:
                        op = s["ops"].pop(0)
                        if op[0] == "FERTILIZE": inv["FERTILIZER"] = int(inv.get("FERTILIZER", 0)) - 1
                        unit_actions[u] = list(op)
                    else:
                        unit_actions[u] = _step_toward(pos, s["target"])
                    continue
                s["target"] = None
        pool = []
        raw_vals = {}
        def _dying(tt):
            x3 = T(*tt)
            return (isinstance(x3, dict) and x3.get("kind") == "PLANT"
                    and int(x3.get("consecutive_unwatered", 0)) >= 1 and not x3.get("watered_today"))
        for tt in order:
            if tt in claimed_tiles and rescue_of.get(u) != tt: continue
            if tt in animal_tiles:
                if not (int(inv.get("WHEAT", 0)) > 0 or not any(o[0] == "FEED" for o in animal_ops(*tt))): continue
                if not animal_ops(*tt): continue
            elif tt in build_set:
                pass
            elif not needs_work(tt, u):
                continue
            v = task_value(tt, u)
            if v <= 0: continue
            if is_ranch and tt in animal_tiles: v *= PLAN.get("ranch_bias", 1.6)
            if (not is_ranch) and tt not in animal_tiles and tt in grp: v *= PLAN.get("home_bias", 1.15)
            raw_vals[tt] = v
        cr = int(PLAN.get("cluster_radius", 0)); cdisc = float(PLAN.get("cluster_disc", 0.8))
        for tt, v in raw_vals.items():
            if cr > 0:
                # 区域价值密度：目的地 + 邻域未认领任务的折扣和，摊薄路程成本
                neigh = [v2 for tt2, v2 in raw_vals.items() if tt2 != tt and _dist(tt, tt2) <= cr]
                v_cl = v + cdisc * sum(neigh)
                score = v_cl / (1.0 + _dist(pos, tt) + len(neigh))
            else:
                score = v / (1.0 + _dist(pos, tt)) ** float(PLAN.get("dist_pow", 1.0))
            if rescue_of.get(u) == tt:
                score = 1e6 - _dist(pos, tt) * 1e3   # 被指派的救火任务置顶
            pool.append((score, tt))
        pool.sort(reverse=True)
        cand = [tt for _, tt in pool[:int(PLAN.get("pool_width", 6))]]
        # 保底任务：候选耗尽时落到最近可种空地（不与高价值任务竞争，防闲置防杂草）
        if not cand and not want_dep and not ENDGAME and day <= lp["WHEAT"]:
            fallback = [tt for tt in empty_tiles if tt not in claimed_tiles and tt not in pasture_set]
            if fallback and pick_crop(commit=False, at=fallback[0]):
                cand = [min(fallback, key=lambda tt: _dist(pos, tt))]
        if want_dep and (not cand or dd <= 1 or val >= PLAN.get("deposit_value", 600) or hour >= 21):
            keep_all = ("FERTILIZER",) if hour < 21 and not ENDGAME else ()
            keep_wheat = 4 if (hour < 21 and not ENDGAME and u in ranch) else 0
            dep_ops = []
            for k2, v2 in inv.items():
                if k2 not in PRODUCTS or int(v2) <= 0 or k2 in keep_all: continue
                n2 = int(v2) - (keep_wheat if k2 == "WHEAT" else 0)
                if n2 > 0: dep_ops.append(["PLACE", k2, n2])
            if dep_ops:
                s["target"] = acc; s["ops"] = dep_ops
                if pos == acc:
                    op0 = s["ops"].pop(0); unit_actions[u] = list(op0)
                    inv[op0[1]] = int(inv.get(op0[1], 0)) - int(op0[2])
                else: unit_actions[u] = _step_toward(pos, acc)
                continue
        if not cand:
            continue
        tgt = cand[0]
        if tgt in animal_tiles: ops = animal_ops(*tgt)
        elif tgt in build_set: ops = [["BUILD_PASTURE"]]
        else: ops = plant_ops(tgt[0], tgt[1], int(inv.get("FERTILIZER", 0)) > 0)
        # 若含 FEED 但无麦：去掉 FEED
        if int(inv.get("WHEAT", 0)) <= 0: ops = [o for o in ops if o[0] != "FEED"]
        if not ops: continue
        # 提交种子预算
        for o in ops:
            if o[0] == "PLANT": pick_crop(commit=True)
        s["target"] = tgt; s["ops"] = ops; claimed_tiles.add(tgt)
        if pos == tgt:
            op = s["ops"].pop(0)
            if op[0] == "PLANT":
                if seed_budget.get(op[1], 0) - plant_reserved[op[1]] < 0: op = ["PASS"]
                else: plant_reserved[op[1]] += 1
            unit_actions[u] = list(op)
            if op[0] == "FEED": inv["WHEAT"] = int(inv.get("WHEAT", 0)) - 1
            if op[0] == "FERTILIZE": inv["FERTILIZER"] = int(inv.get("FERTILIZER", 0)) - 1
        else:
            unit_actions[u] = _step_toward(pos, tgt)

    market = _market(farm, shed, seeds, invs, money, day, hour, turn, n_animals, shed_animals, carried, plant_tiles, empty_tiles, prices, st, unlocked)
    return {"farmer": unit_actions[0], "hands": unit_actions[1:], "market": market[:10]}


def _market(farm, shed, seeds, invs, money, day, hour, turn, n_animals, shed_animals, carried, plant_tiles, empty_tiles, prices, st, unlocked):
    orders = []
    n_anim_now = n_animals + sum(n for _, n in shed_animals) + carried
    n_anim_soon = n_anim_now + sum(int(n) for _, n in PLAN["animals"].get(day, []))
    pend = st.get("pending")
    if pend is None:
        pend = st["pending"] = {"animals": [], "straw": 0, "land": 0, "melon": PLAN["melon_tiles"] if day == 0 else 0}
        if day > 0:
            for d0 in range(0, day): st["day_plan"][("plan_added", d0)] = True
    dk = ("plan_added", day)
    if not st["day_plan"].get(dk):
        st["day_plan"][dk] = True
        for a, n in PLAN["animals"].get(day, []): pend["animals"].append([a, int(n)])
        pend["straw"] += int(PLAN["straw"].get(day, 0))
        pend["land"] += int(PLAN["land"].get(day, 0))
    fd = 1 if day < PLAN.get("feed_days_from", 8) else PLAN["feed_days"]
    feed_reserve = n_anim_now * fd + (2 if day < 8 else 4) if turn < 24 * 29 else 0
    has_straw = any(farm["tiles"][y][x].get("crop") == "STRAWBERRY" for (x, y) in plant_tiles)
    fert_reserve = PLAN["fert_reserve"] if (turn < 24 * 27 and has_straw and day >= 6) else 0
    sells = []
    shed_total = sum(int(v) for v in shed.values())
    endgame_sell = turn >= 24 * 28
    for item in PRODUCTS:
        q = int(shed.get(item, 0))
        if item == "WHEAT": q -= feed_reserve
        if item == "FERTILIZER": q -= fert_reserve
        if q <= 0: continue
        pr = prices.get(item, BASE[item])
        # 速率匹配：每步卖出 ≈ 城镇吸收速率（供给≤需求则价格不砸穿）；甜瓜洪峰保留全量
        if not endgame_sell and shed_total < 80 and item != "MELON":
            menu = {"BAKERY": ("EGG", "WHEAT"), "PIZZA_SHOP": ("MILK", "TOMATO", "WHEAT"),
                    "BRUNCH_SPOT": ("EGG", "WHEAT", "STRAWBERRY"), "YARN_STORE": ("WOOL",),
                    "ICE_CREAM_SHOP": ("STRAWBERRY", "MILK", "WHEAT"), "PET_CAFE": ("CARROT",),
                    "SMOOTHIE_SHOP": ("STRAWBERRY", "MILK"), "FARMERS_MARKET": ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY")}
            rate = 2
            for sh in (st.get("_shops2") or []):
                if item in menu.get(sh, ()): rate += 2 if len(menu[sh]) > 1 else 4
            q = min(q, int(rate * float(PLAN.get("rate_mult", 1.5))))
        sells.append((q * pr, ["SELL", item, q]))
    sells.sort(key=lambda s: -s[0])
    max_sell = 10 if turn >= 24 * 29 + 16 else 6
    orders += [o for _, o in sells[:max_sell]]
    cash = money + sum(v * 0.7 for v, _ in sells[:max_sell])
    if turn >= 24 * 29 + 20:
        return orders
    # 饲料
    wheat_have = int(shed.get("WHEAT", 0)) + sum(int(i.get("WHEAT", 0)) for i in invs)
    need_feed = n_anim_soon * fd + 2
    wp = prices.get("WHEAT", 25)
    if n_anim_soon and day <= 27 and wheat_have < n_anim_soon + 1 and wp <= PLAN["wheat_buy_cap"] and len(orders) < 10:
        q = min(need_feed - wheat_have, 24)
        if day < 8: q = max(1, min(q, n_anim_soon + 2 - wheat_have))
        if day == 0: q = max(q, 8)
        if cash >= q * wp:
            orders.insert(0, ["BUY_PRODUCT", "WHEAT", q]); cash -= q * wp
        elif cash >= wp:
            q = int(cash // wp); orders.insert(0, ["BUY_PRODUCT", "WHEAT", q]); cash -= q * wp
    # 雇工
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
    # 土地
    n_extra = len(unlocked) - 1
    if pend["land"] > 0 and n_extra < 3 and len(orders) < 10:
        price = LAND_PRICES[n_extra]
        if cash >= price + 60:
            orders.append(["BUY_LAND"]); cash -= price; pend["land"] -= 1
    # 草莓种子（优先于动物：草莓满肥效一块产 8 个 x ~120，ROI 高于晚批牛）
    lp0 = PLAN["last_plant_day"]
    if pend["straw"] > 0 and day <= lp0["STRAWBERRY"] and len(orders) < 10:
        n = pend["straw"]; c = 100 * n
        if cash >= c + 10:
            orders.append(["BUY_SEED", "STRAWBERRY", n]); cash -= c; pend["straw"] = 0
        elif cash >= 110:
            n = int((cash - 10) // 100)
            if n > 0:
                orders.append(["BUY_SEED", "STRAWBERRY", n]); cash -= n * 100; pend["straw"] -= n
    # 动物
    if day <= PLAN["animal_last_day"]:
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
    # 种子
    lp = PLAN["last_plant_day"]
    if pend["melon"] > 0 and day <= lp["MELON"] and len(orders) < 10:
        n = pend["melon"]; c = 80 * n
        if cash >= c + 10:
            orders.append(["BUY_SEED", "MELON", n]); cash -= c; pend["melon"] = 0
        elif cash >= 170:
            n = int((cash - 10) // 80); orders.append(["BUY_SEED", "MELON", n]); cash -= n * 80; pend["melon"] -= n
    if pend["straw"] > 0 and day <= lp["STRAWBERRY"] and len(orders) < 10:
        n = pend["straw"]; c = 100 * n
        if cash >= c + 10:
            orders.append(["BUY_SEED", "STRAWBERRY", n]); cash -= c; pend["straw"] = 0
        elif cash >= 110:
            n = int((cash - 10) // 100); orders.append(["BUY_SEED", "STRAWBERRY", n]); cash -= n * 100; pend["straw"] -= n
    if day <= lp["WHEAT"] and len(orders) < 10:
        target_wheat = PLAN["wheat_tiles"] if day < 6 else (PLAN["wheat_tiles_mid"] if day < 11 else PLAN["wheat_tiles_late"])
        have_wheat_plants = sum(1 for (x, y) in plant_tiles if farm["tiles"][y][x].get("crop") == "WHEAT")
        n_empty = len(empty_tiles)
        buf = 0 if day < 3 else 6
        want = max(0, min(target_wheat - have_wheat_plants + buf, n_empty + buf) - int(seeds.get("WHEAT", 0)))
        if want >= (1 if day < 3 else 3) and day <= 27:
            c = 10 * want
            if cash >= c + 5:
                orders.append(["BUY_SEED", "WHEAT", want]); cash -= c
            elif cash >= 35:
                n = int((cash - 5) // 10); orders.append(["BUY_SEED", "WHEAT", n]); cash -= n * 10
    return orders
