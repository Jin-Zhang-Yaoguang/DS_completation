"""V128 Majkel 硬编码复刻原型（计划 B）。

四层结构，照抄 Majkel1337 回放实测：
  L0 开局：t0/t1 市场单逐字硬编码（453 局零方差）。
  L1 战略日程：人手（0 点 8 单 + 1 点追加）、买地时点、按「当日已解锁商店数」线性表给出作物/动物/牧场/鸡舍目标。
  L2 调度器：同格清空 → 最近未认领任务 → 先纵后横；傍晚生存任务优先；格内次序 动物 FEED→COLLECT→HARVEST→CARE、作物 FERTILIZE→WATER→HARVEST。
  L3 市场层：先卖后买；奶/毛/莓 t%4==1 小批卖；蛋/萝卜/番茄/瓜 22 点整仓；肥料 d11 前全卖、之后留作施肥；小麦保留饲料余量。
所有可调量在 P 中，可用 PARAMS_OVERRIDE 注入（默认值 = 当前复刻行为）。
"""
import json
import os
from pathlib import Path

CROPS = {
    "WHEAT": {"seed": 10, "first": 2, "maxd": 4, "interval": 0, "maxy": 6, "ongoing": False},
    "CARROT": {"seed": 20, "first": 2, "maxd": 3, "interval": 0, "maxy": 4, "ongoing": False},
    "TOMATO": {"seed": 50, "first": 8, "maxd": 8, "interval": 1, "maxy": 4, "ongoing": True},
    "STRAWBERRY": {"seed": 100, "first": 10, "maxd": 10, "interval": 2, "maxy": 4, "ongoing": True},
    "MELON": {"seed": 80, "first": 10, "maxd": 12, "interval": 0, "maxy": 6, "ongoing": False},
}
ANIMALS = {"GOOSE": ("COOP", 300), "COW": ("PASTURE", 400), "SHEEP": ("PASTURE", 500)}
PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]
SHOPS = ["BAKERY", "BRUNCH_SPOT", "FARMERS_MARKET", "ICE_CREAM_SHOP", "PET_CAFE", "PIZZA_SHOP", "SMOOTHIE_SHOP", "YARN_STORE"]
MOVES = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}
ACCESS = [(4, 4), (5, 4), (4, 5), (5, 5)]
# 官方价格曲线（1.32.7 MARKET_PARAMS）：用于推算卖 k 件后的价格
MP = {"WHEAT": (25, 400, "sqrt", .80, "log", .20), "CARROT": (35, 450, "hinge", 1.0, "sqrt", .70), "TOMATO": (60, 200, "hinge", .40, "sqrt", .60),
      "STRAWBERRY": (120, 100, "sqrt", .70, "linear", 1.60), "MELON": (250, 300, "log", .20, "sq", 3.60), "EGG": (50, 332, "hinge", .40, "log", .20),
      "MILK": (160, 122, "sqrt", .60, "linear", 1.60), "WOOL": (200, 105, "log", .20, "sq", 3.20), "FERTILIZER": (100, 200, "linear", .40, "linear", .40)}


def _shape(f, x, T):
    x = max(0.0, x)
    if f == "linear": return x
    if f == "sq": return x * x
    if f == "sqrt": return x ** 0.5
    if f == "log": return __import__("math").log(1.0 + x)
    u = x / T
    return u + 8.0 * max(0.0, u - 1.0) ** 2


def mprice(item, inv):
    base, T, bf, bt, af, at = MP[item]
    if inv < 10000:
        price = base + bt * base / _shape(bf, T, T) * _shape(bf, 10000 - inv, T)
    else:
        price = base - at * base / _shape(af, T, T) * _shape(af, inv - 10000, T)
    return max(1, int(round(price)))
QUAD_OF = lambda x, y: ("N" if y < 5 else "S") + ("W" if x < 5 else "E")

P = {
    # L1 人手：0 点下 8 单（现金决定实际雇到几个），1 点追加
    "hire_h0": {1: 8, 2: 6, 3: 6, 4: 6, 5: 6},
    "hire_h0_default": 8,
    "hire_h1": {7: 1, 8: 1, 9: 2, 28: 2, 29: 2},
    "hire_h1_default_after10": 3,
    "hire_h2_day1": 1,
    # 买地
    "land1_step": 149, "land2_step": 217, "land_reserve_from": 12,
    # 作物
    "crop_quads": {"MELON": ["NW"], "STRAWBERRY": ["NW", "NE"], "WHEAT": ["SW", "NW", "NE"], "CARROT": ["SW", "NE", "NW"], "TOMATO": ["NW", "SW", "NE"]},
    "plant_last_day": {"WHEAT": 27, "CARROT": 27, "TOMATO": 20, "STRAWBERRY": 19, "MELON": 3},
    "seed_cap": {"WHEAT": 5, "MELON": 2, "STRAWBERRY": 2, "TOMATO": 2, "CARROT": 6},
    "target_scale": 1.0,
    # 施肥：起始日与各作物施肥龄窗
    "fert_start_day": 11,
    "fert_age": {"WHEAT": [1, 3], "CARROT": [1, 2], "STRAWBERRY": [7, 15], "TOMATO": [4, 10]},
    "fert_keep_carry": 6,
    # 结构区：离仓库最近的 R 格优先留给牧场/鸡舍
    "struct_reserve": 18,
    # 饲料
    "pickup_wheat": 3, "wheat_buffer": 2, "feed_last_day": 28,
    # 调度
    "survival_hour": 18, "drop_min": 6,
    # 市场
    "beat_phase": 1, "beat_items": ["MILK", "WOOL", "STRAWBERRY"], "beat_lot": 2,
    "bulk_items": ["EGG", "CARROT", "TOMATO", "MELON"], "bulk_hour": 22,
    "fert_sell_price": 45, "wheat_keep_per_animal": 2, "wheat_sell_phase": 2,
    "shed_guard": 85, "final_sell_step": 716,
    "opening_hardcode": True, "urgent_ratio": 0.35, "deliver_value": 1500,
    # 目标选择：距离 + 任务权重（越小越优先）；urgent 时非生存任务再加 urgent_penalty
    "op_penalty": {"WATER": 0, "FEED": 0, "PLACE": 0, "BUILD_PASTURE": 1, "BUILD_COOP": 1, "HARVEST": 1, "PLANT": 1,
                   "CARE": 1, "COLLECT_FERTILIZER": 1, "FERTILIZE": 0, "DIG": 3},
    "urgent_penalty": 8, "sticky": True, "sticky_bonus": 1.5,
    "fert_ages": {"WHEAT": [2], "CARROT": [2], "STRAWBERRY": [9, 11, 13, 15], "TOMATO": [7, 10]},
    "harvest_early": 1, "care_needs_fed": True, "plant_last_hour": 21, "struct_lookahead": 3,
    "harvest_wait": True, "pickup_by_need": True, "risk_bonus": 0,
    # 调度模式 v2（Majkel 逆向）：只在到达目标/同格连续时干活，途经不做；目标只挑主任务并持有到达；空手才领麦
    "dispatch": "v1", "target_model": True, "tm_plant_bias": 0.0, "tm_build_bias": 1.0, "tm_place_bias": 3.0, "pass_skip_ops": [], "pickup_mode": "target", "via_feed_gate": True,
    # 孤儿格修复：站在格上可无视远程认领；更近 claim_steal_margin 格可抢单；傍晚濒死作物加分
    "same_tile_override": True, "claim_steal_margin": 2, "sweep_hour": 18, "sweep_bonus": 4.0, "sweep_feed": False, "secondary_ops": ["CARE", "COLLECT_FERTILIZER"], "secondary_penalty": 3, "pickup_zero_only": True,
    # 市场 refill 模式（Majkel 逆向）：现金足时囤积奶/毛/莓，只在价格刚被消费抬升后卖回到上一步价位；现金紧时照旧成批卖
    "sell_mode": "beat", "beat_dump_hour": 21, "beat_frac": 0.3334, "beat_poor_money": 0, "beat_need_rise": False, "rich_money": 4300, "refill_frac_cap": 0.35, "refill_min": 1, "dump_step": 694, "refill_items": ["MILK", "WOOL", "STRAWBERRY"],
    "tm_animal_bias": 0.0, "atarget_add": {}, "atarget_add_from": 6, "sheep_share": None, "animal_buy_order": ["COW", "SHEEP", "GOOSE"],
    "same_tile_ops": ["FEED", "WATER", "COLLECT_FERTILIZER", "PLACE", "FERTILIZE", "HARVEST", "CARE", "DIG", "PLANT", "BUILD_PASTURE", "BUILD_COOP"],
}

# Majkel t2–t5 逐字动作（453 局中 t2–t4 100% 相同，t5 单位动作 100% 相同）
OPENING = {
    2: {"farmer": ["BUILD_PASTURE"], "hands": [["PICKUP", "SHEEP", 1], ["PICKUP", "SHEEP", 1], ["PICKUP", "COW", 1], ["PICKUP", "SHEEP", 1]], "market": [["SELL", "WHEAT", 1]]},
    3: {"farmer": ["PLACE", "COW", 1], "hands": [["NORTH"], ["NORTH"], ["NORTH"], ["WEST"]], "market": [["SELL", "WHEAT", 1], ["BUY_PRODUCT", "WHEAT", 1]]},
    4: {"farmer": ["PICKUP", "WHEAT", 3], "hands": [["WEST"], ["WEST"], ["NORTH"], ["BUILD_PASTURE"]], "market": [["SELL", "WHEAT", 1], ["BUY_PRODUCT", "WHEAT", 1]]},
    5: {"farmer": ["FEED"], "hands": [["BUILD_PASTURE"], ["WEST"], ["NORTH"], ["PLACE", "SHEEP", 1]], "market": [["BUY_PRODUCT", "WHEAT", 1]]},
}
try:
    P.update(PARAMS_OVERRIDE)  # noqa: F821  由打包/搜索注入
except NameError:
    pass
if os.environ.get("V128_PARAMS"):
    P.update(json.loads(os.environ["V128_PARAMS"]))

_TABLE_PATH = Path(__file__).resolve().parent / "v128_data" / "schedule_tables.json"
_TW_PATH = Path(__file__).resolve().parent / "v128_data" / "target_weights.json"
try:
    TW = TARGET_WEIGHTS  # noqa: F821  打包时内嵌
except NameError:
    TW = json.loads(_TW_PATH.read_text()) if _TW_PATH.exists() else None
try:
    SCHED = SCHEDULE_TABLES  # noqa: F821  打包时内嵌
except NameError:
    SCHED = json.loads(_TABLE_PATH.read_text())


# ---------------------------------------------------------------- 工具
def dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def access_dist(p):
    return min(dist(p, a) for a in ACCESS)


def step_toward(src, dst):
    """先纵后横（Majkel 换轴移动 91% 先纵）。"""
    if dst[1] != src[1]:
        return "SOUTH" if dst[1] > src[1] else "NORTH"
    if dst[0] != src[0]:
        return "EAST" if dst[0] > src[0] else "WEST"
    return "PASS"


def target(day, key, shops):
    row = SCHED["days"][str(min(day, 29))][key]
    v = row["base"] + sum(row["coef"][s] * shops.count(s) for s in SHOPS)
    return max(0, v)


def plant_age(tile, day):
    return day - tile["planted_day"]


def harvestable(tile, day):
    if tile.get("yield_units", 0) <= 0:
        return False
    if tile.get("kind") == "PLANT":
        return plant_age(tile, day) >= CROPS[tile["crop"]]["first"]
    return "animal" in tile


def dead_ongoing(tile, day):
    """持续作物已过最后一次产出且无存量：挖掉重种（Majkel 在草莓 16 龄、番茄 11 龄挖）。"""
    c = CROPS[tile["crop"]]
    if not c["ongoing"]:
        return False
    last_age = c["first"] + c["interval"] * (c["maxy"] - 1)
    return plant_age(tile, day) >= last_age and tile.get("yield_units", 0) == 0 and tile.get("watered_today") is not None


# ---------------------------------------------------------------- 状态
_S = {}


def _state(player):
    return _S.setdefault(player, {"first_wool_step": None})


# ---------------------------------------------------------------- 主决策
def decide(obs):
    me = obs["player"]
    step = obs.get("step", obs["day"] * 24 + obs["hour"])
    day, hour = obs["day"], obs["hour"]
    farm = obs["farms"][me]
    priv = obs["private"]
    shed = dict(priv["shed"])
    seeds = dict(priv["seeds"])
    invs = [dict(i) for i in priv["inventories"]]
    prices = obs["market"]["prices"]
    shops = list(obs["town"]["unlocked_shops"])
    tiles = farm["tiles"]
    money = farm["money"]
    st = _state(me)

    units = [tuple(farm["farmer"])] + [tuple(h) for h in farm["hands"]]
    while len(invs) < len(units):
        invs.append({})

    # L0 开局硬编码
    if step == 0:
        return {"farmer": ["PASS"], "hands": [], "market": [["BUY_ANIMAL", "COW", 1], ["BUY_PRODUCT", "WHEAT", 5]]}
    if step == 1:
        return {"farmer": ["PICKUP", "COW", 1], "hands": [],
                "market": [["SELL", "WHEAT", 1], ["HIRE"], ["HIRE"], ["HIRE"], ["HIRE"], ["BUY_ANIMAL", "COW", 1], ["BUY_ANIMAL", "SHEEP", 3]]}
    if 2 <= step <= 5 and len(farm["hands"]) == 4 and P["opening_hardcode"]:
        return OPENING[step]

    # ---- 棋盘盘点
    unlocked = set(farm["unlocked_quadrants"])
    counts = {k: 0 for k in list(CROPS) + list(ANIMALS) + ["PASTURE", "COOP"]}
    empty_struct = {"PASTURE": [], "COOP": []}
    empty_tiles, weeds = [], []
    unfed = unwatered = 0
    for y in range(10):
        for x in range(10):
            t = tiles[y][x]
            if t == "LOCKED":
                continue
            if t is None:
                if QUAD_OF(x, y) in unlocked:
                    empty_tiles.append((x, y))
                continue
            k = t.get("kind")
            if k == "PLANT":
                counts[t["crop"]] += 1
                if not t["watered_today"]:
                    unwatered += 1
            elif k in ("PASTURE", "COOP"):
                counts[k] += 1
                if "animal" in t:
                    counts[t["animal"]] += 1
                    if not t["fed_today"]:
                        unfed += 1
                else:
                    empty_struct[k].append((x, y))
            elif k == "WEED":
                weeds.append((x, y))
    carried = {k: sum(i.get(k, 0) for i in invs) for k in list(ANIMALS) + ["WHEAT", "FERTILIZER"]}
    for a in ANIMALS:
        counts[a] += shed.get(a, 0) + carried[a]
    n_animals = counts["COW"] + counts["SHEEP"] + counts["GOOSE"]

    # ---- L1 目标
    sc = P["target_scale"]
    ctarget = {c: round(target(day, c, shops) * sc) for c in CROPS}
    for c in CROPS:
        if day > P["plant_last_day"][c]:
            ctarget[c] = 0
    atarget = {a: max(0, round(target(day, a, shops) + (P["atarget_add"].get(a, 0) if day >= P["atarget_add_from"] else 0))) for a in ANIMALS}
    if P["sheep_share"] is not None and day >= P["atarget_add_from"]:
        tot = atarget["COW"] + atarget["SHEEP"]
        atarget["SHEEP"] = round(tot * P["sheep_share"]); atarget["COW"] = tot - atarget["SHEEP"]
    past_t = max(round(target(day, "kind:PASTURE", shops)), atarget["COW"] + atarget["SHEEP"])
    coop_t = max(round(target(day, "kind:COOP", shops)), atarget["GOOSE"])
    crop_def = {c: max(0, ctarget[c] - counts[c]) for c in CROPS}
    struct_def = {"PASTURE": max(0, past_t - counts["PASTURE"]), "COOP": max(0, coop_t - counts["COOP"])}

    # 结构区：未来 struct_lookahead 天的牧场/鸡舍缺口，预留离仓库最近的空格
    need_struct = 0
    for s, key, anis in (("PASTURE", "kind:PASTURE", ("COW", "SHEEP")), ("COOP", "kind:COOP", ("GOOSE",))):
        fut = max(max(round(target(dd, key, shops)), sum(round(target(dd, a, shops)) for a in anis))
                  for dd in range(day, min(29, day + P["struct_lookahead"]) + 1))
        need_struct += max(0, fut - counts[s])
    empty_sorted = sorted(empty_tiles, key=lambda p: (access_dist(p), p[1], p[0]))
    reserve = set(empty_sorted[:need_struct])

    # ---- L2 调度（任务制：任务 = (格, 动作)；单位选「距离 + 任务权重」最小的未认领任务，只在站到任务格上时执行）
    local = {}

    def tstate(p):
        if p in local:
            return local[p]
        t = tiles[p[1]][p[0]]
        return dict(t) if isinstance(t, dict) else t

    seeds_left = dict(seeds)
    plant_claims = {c: 0 for c in CROPS}
    build_claims = {"PASTURE": 0, "COOP": 0}
    shed_wheat = shed.get("WHEAT", 0)
    shed_animals = {a: shed.get(a, 0) for a in ANIMALS}
    claimed = set()
    wheat_total_need = unfed - carried["WHEAT"]
    remaining_labor = (23 - hour) * len(units)
    urgent = hour >= P["survival_hour"] or (unwatered + unfed) > remaining_labor * P["urgent_ratio"]
    fert_on = day >= P["fert_start_day"]
    free_struct = {s: len(empty_struct[s]) - sum(carried[a] for a in ANIMALS if ANIMALS[a][0] == s) for s in empty_struct}
    to_pick = {a: max(0, min(shed.get(a, 0), free_struct[ANIMALS[a][0]])) for a in ANIMALS}
    pickers = 0
    pen = P["op_penalty"]

    def fert_window(t):
        c = t["crop"]
        return plant_age(t, day) in P["fert_ages"].get(c, ()) and t["fertilized_until_day"] < day and (CROPS[c]["ongoing"] or not t["watered_today"])

    def harvest_ready(t):
        if t.get("yield_units", 0) <= 0:
            return False
        c = CROPS[t["crop"]]
        age = plant_age(t, day)
        if age < c["first"]:
            return False
        if c["ongoing"] or age > c["maxd"] or t["yield_units"] >= c["maxy"]:
            return True
        if not P["harvest_wait"]:
            return True
        return t["watered_today"] and age >= c["maxd"] - P["harvest_early"]

    def tile_ops(p, t, inv):
        """该格候选任务（格内次序），含随身物约束。"""
        out = []
        if isinstance(t, dict):
            k = t.get("kind")
            if "animal" in t:
                live = day <= P["feed_last_day"]
                if live and not t["fed_today"] and inv.get("WHEAT", 0) > 0:
                    out.append(["FEED"])
                if live and not t["cared_today"] and (t["fed_today"] or not P["care_needs_fed"]):
                    out.append(["CARE"])
                if t.get("fertilizer_available"):
                    out.append(["COLLECT_FERTILIZER"])
                if t.get("yield_units", 0) > 0:
                    out.append(["HARVEST"])
            elif k == "PLANT":
                if fert_on and inv.get("FERTILIZER", 0) > 0 and fert_window(t):
                    out.append(["FERTILIZE"])
                if not t["watered_today"]:
                    out.append(["WATER"])
                if harvest_ready(t):
                    out.append(["HARVEST"])
                elif dead_ongoing(t, day) and t["watered_today"]:
                    out.append(["DIG"])
            elif k == "WEED":
                out.append(["DIG"])
            elif k in ("PASTURE", "COOP") and "animal" not in t:
                for a, (s, _) in ANIMALS.items():
                    if s == k and inv.get(a, 0) > 0:
                        out.append(["PLACE", a, 1])
                        break
        elif t is None and QUAD_OF(*p) in unlocked:
            if p in reserve:
                for s in ("PASTURE", "COOP"):
                    if struct_def[s] - build_claims[s] > 0:
                        out.append(["BUILD_" + s])
                        break
            elif hour <= P["plant_last_hour"]:
                q = QUAD_OF(*p)
                for c in sorted(CROPS, key=lambda c: -crop_def[c]):
                    if crop_def[c] - plant_claims[c] > 0 and seeds_left.get(c, 0) > 0 and q in P["crop_quads"][c]:
                        out.append(["PLANT", c])
                        break
        return out

    def apply_local(p, inv, op):
        t = tstate(p)
        o = op[0]
        if o == "FEED":
            t["fed_today"] = True; inv["WHEAT"] -= 1
        elif o == "COLLECT_FERTILIZER":
            t["fertilizer_available"] = False; inv["FERTILIZER"] = inv.get("FERTILIZER", 0) + 1
        elif o == "HARVEST":
            if t.get("kind") == "PLANT" and not CROPS[t["crop"]]["ongoing"]:
                t = None
            else:
                t["yield_units"] = 0
        elif o == "CARE":
            t["cared_today"] = True
        elif o == "WATER":
            t["watered_today"] = True
        elif o == "FERTILIZE":
            t["fertilized_until_day"] = day + 2; inv["FERTILIZER"] -= 1
        elif o == "DIG":
            t = None
        elif o == "PLACE":
            inv[op[1]] -= 1
            t["animal"] = op[1]; t["fed_today"] = False; t["cared_today"] = False; t["fertilizer_available"] = False; t["yield_units"] = 0
        elif o.startswith("BUILD_"):
            t = {"kind": o[6:]}
            build_claims[o[6:]] += 1
        elif o == "PLANT":
            t = {"kind": "PLANT", "crop": op[1], "planted_day": day, "watered_today": False, "yield_units": 0, "fertilized_until_day": -1}
            seeds_left[op[1]] -= 1; plant_claims[op[1]] += 1
        local[p] = t

    TWI = dict(zip(TW["feats"], TW["w"])) if (TW and P["target_model"]) else None
    ACC4 = ACCESS

    def tm_score(p, q, t, ops, inv, i, lower_claims):
        """Majkel 目标选择线性打分（research/target_model.py 拟合，留出局第一名命中 57%）。"""
        x, y = q; dx, dy = x - p[0], y - p[1]; d = abs(dx) + abs(dy)
        o0 = ops[0][0]
        if o0 == "PLANT":
            return -1.377 * d + P["tm_plant_bias"]
        if o0.startswith("BUILD_"):
            return -1.377 * d + P["tm_build_bias"]
        if o0 == "PLACE":
            return -1.377 * d + P["tm_place_bias"]
        names = [op[0] for op in ops]
        f = {"d": d, "d1": d == 1, "d2": d == 2, "north": dy < 0, "south": dy > 0, "east": dx > 0, "west": dx < 0,
             "pure_v": dx == 0, "pure_h": dy == 0, "n_ops": len(names), "row": y / 9, "col": x / 9,
             "closer_units": sum(1 for j, u in enumerate(units) if j != i and abs(u[0] - x) + abs(u[1] - y) < d),
             "claimed_lower": q in lower_claims, "shed_d": min(abs(x - a[0]) + abs(y - a[1]) for a in ACC4), "late": hour >= 18}
        if isinstance(t, dict) and "animal" in t:
            f["k_animal"] = 1
            f["op_FEED"] = "FEED" in names; f["op_COLLECT"] = "COLLECT_FERTILIZER" in names
            f["op_HARVEST_ANIMAL"] = "HARVEST" in names; f["op_CARE"] = "CARE" in names
            f["risk"] = t.get("consecutive_unfed", 0) >= 1 and not t.get("fed_today")
            if P["sweep_feed"] and hour >= P["sweep_hour"] and f["risk"] and f["op_FEED"]:
                return sum(TWI[k] * float(v) for k, v in f.items() if k in TWI) + P["sweep_bonus"]
            if P["tm_animal_bias"]:
                return sum(TWI[k] * float(v) for k, v in f.items() if k in TWI) + P["tm_animal_bias"]
        elif isinstance(t, dict) and t.get("kind") == "PLANT":
            f["k_" + t["crop"]] = 1
            f["op_WATER"] = "WATER" in names; f["op_HARVEST_PLANT"] = "HARVEST" in names; f["op_FERT"] = "FERTILIZE" in names
            f["risk"] = (not t["watered_today"]) and t.get("consecutive_unwatered", 0) >= 1
            f["planted_today"] = t.get("planted_day") == day
            if hour >= P["sweep_hour"] and not t["watered_today"] and (f["risk"] or f["planted_today"]):
                f["planted_today"] = False
                return sum(TWI[k] * float(v) for k, v in f.items() if k in TWI) + P["sweep_bonus"]
        elif isinstance(t, dict) and t.get("kind") == "WEED":
            f["k_WEED"] = 1; f["op_DIG"] = "DIG" in names
        return sum(TWI[k] * float(v) for k, v in f.items() if k in TWI)

    actions = []
    positions = list(units)
    prev_target = st.get("targets", {}) if st.get("targets_day") == day else {}
    last_act = st.get("last", {}) if st.get("targets_day") == day else {}
    targets_now = {}
    v2 = P["dispatch"] == "v2"
    claimed_tiles = set()
    claim_dist = {}
    for i, p in enumerate(units):
        inv = invs[i]
        act = None
        # 1) 仓库旁：放置/领取
        if p in ACCESS:
            if inv.get("FERTILIZER", 0) > (0 if not fert_on else P["fert_keep_carry"]):
                act = ["PLACE", "FERTILIZER", inv["FERTILIZER"] - (0 if not fert_on else P["fert_keep_carry"])]
            else:
                prods = [(inv.get(k, 0) * prices[k], inv.get(k, 0), k) for k in PRODUCTS if k not in ("WHEAT", "FERTILIZER")]
                v, n, k = max(prods)
                if n >= P["drop_min"] or (n > 0 and v >= P["deliver_value"] / 3):
                    act = ["PLACE", k, n]; inv.pop(k, None)
            if act is None:
                for a in ("COW", "SHEEP", "GOOSE"):
                    if to_pick[a] > 0 and shed_animals[a] > 0 and not any(inv.get(x, 0) for x in ANIMALS):
                        act = ["PICKUP", a, 1]; shed_animals[a] -= 1; to_pick[a] -= 1; inv[a] = inv.get(a, 0) + 1
                        break
            if act is None and P["pickup_mode"] == "need" and (wheat_total_need > 0 if P["pickup_by_need"] else unfed > 0) and inv.get("WHEAT", 0) < (1 if (v2 and P["pickup_zero_only"]) else 2) and shed_wheat > 0 and day <= P["feed_last_day"] and hour >= 1:
                n = min(P["pickup_wheat"], shed_wheat)
                act = ["PICKUP", "WHEAT", n]; shed_wheat -= n; inv["WHEAT"] = inv.get("WHEAT", 0) + n; wheat_total_need -= n
        # 2) 同格处理：当前格首个任务属于 same_tile_ops 则直接做
        if act is None:
            here = tile_ops(p, tstate(p), inv)
            la = last_act.get(i)
            continuing = la is not None and tuple(la[0]) == p and la[1] not in MOVES and la[1] != "PASS"
            tgt = prev_target.get(i)
            allow_here = (not v2) or continuing or tgt is None or tuple(tgt) == p
            if v2 and here and not continuing and here[0][0] in P["secondary_ops"] and tgt is not None and tuple(tgt) != p:
                allow_here = False
            # 路过跳过：非同格连续、且本格不是目标时，这些动作不顺手做
            if here and not continuing and here[0][0] in P["pass_skip_ops"] and tgt is not None and tuple(tgt) != p:
                allow_here = False
            remote_ok = P["same_tile_override"] and claim_dist.get(p, 0) > 0
            if allow_here and here and here[0][0] in P["same_tile_ops"] and ((p, here[0][0]) not in claimed or remote_ok) and not (v2 and p in claimed_tiles and not remote_ok):
                act = here[0]
                apply_local(p, inv, act)
                claimed.add((p, act[0])); claimed_tiles.add(p)
                targets_now[i] = None if v2 else p
        # 3) 选任务
        if act is None:
            best = None
            keep = prev_target.get(i) if v2 else None
            if keep is not None and tuple(keep) != p and tuple(keep) not in claimed_tiles:
                kq = tuple(keep); kt = tstate(kq)
                kops = [op for op in (tile_ops(kq, kt, inv) if kt != "LOCKED" else []) if (kq, op[0]) not in claimed and op[0] not in P["secondary_ops"]]
                if kops:
                    best = ((1, -1, dist(p, kq)), kq, kops[0])
            for y in range(10) if best is None else ():
                for x in range(10):
                    q = (x, y)
                    if v2 and q in claimed_tiles:
                        continue
                    t = tstate(q)
                    if t == "LOCKED" or (t is None and QUAD_OF(x, y) not in unlocked):
                        continue
                    tops = tile_ops(q, t, inv)
                    if TWI is not None and tops and not any(o0[0] in ("PLACE",) or (o0[0].startswith("BUILD_") and sum(to_pick.values()) > 0) for o0 in tops[:1]):
                        steal = q in claim_dist and claim_dist[q] - dist(p, q) >= P["claim_steal_margin"]
                        ops_free = [op for op in tops if (q, op[0]) not in claimed or steal]
                        if not ops_free or dist(p, q) > 12:
                            continue
                        sc = tm_score(p, q, t, ops_free, inv, i, claimed_tiles)
                        key = (1, -sc, dist(p, q))
                        if best is None or key < best[0]:
                            best = (key, q, ops_free[0])
                        continue
                    for op in tops:
                        if (q, op[0]) in claimed:
                            continue
                        o = op[0]
                        pri = 0 if (o == "PLACE" or (o.startswith("BUILD_") and sum(to_pick.values()) > 0)) else 1
                        d0 = dist(p, q)
                        w = d0 + pen.get(o, 2)
                        if v2 and o in P["secondary_ops"]:
                            w += P["secondary_penalty"]
                        if urgent and o not in ("WATER", "FEED", "PLACE"):
                            w += P["urgent_penalty"]
                        if P["sticky"] and prev_target.get(i) == q:
                            w -= P["sticky_bonus"]
                        # 死亡风险：昨天漏浇/今天刚种（今晚不浇即变杂草）、昨天漏喂（今晚不喂即逃走）
                        if o == "WATER" and (t.get("consecutive_unwatered", 0) >= 1 or t.get("planted_day") == day):
                            w -= P["risk_bonus"]
                        elif o == "FEED" and t.get("consecutive_unfed", 0) >= 1:
                            w -= P["risk_bonus"]
                        key = (pri, w, d0)
                        if best is None or key < best[0]:
                            best = (key, q, op)
                        break  # 每格只取格内次序中第一个未认领任务
            acc = min(ACCESS, key=lambda a: dist(p, a))
            via_feed = None
            if P["pickup_mode"] == "target" and TWI is not None and inv.get("WHEAT", 0) == 0 and shed_wheat > 0 and day <= P["feed_last_day"] and hour >= 1 \
                    and (wheat_total_need > 0 or not P["via_feed_gate"]):
                for y in range(10):
                    for x in range(10):
                        q = (x, y); t = tstate(q)
                        if not (isinstance(t, dict) and "animal" in t and not t["fed_today"]) or (q, "FEED") in claimed or q in claimed_tiles:
                            continue
                        sc = tm_score(acc, q, t, [["FEED"]], {"WHEAT": 3}, i, claimed_tiles) - 1.377 * dist(p, acc)
                        if via_feed is None or sc > via_feed[0]:
                            via_feed = (sc, q)
                if via_feed is not None and (best is None or best[2] is None or (best[0][0] >= 1 and -best[0][1] < via_feed[0])):
                    if p in ACCESS:
                        n = min(P["pickup_wheat"], shed_wheat)
                        act = ["PICKUP", "WHEAT", n]; shed_wheat -= n; inv["WHEAT"] = n; wheat_total_need -= n
                        claimed.add((via_feed[1], "FEED")); claimed_tiles.add(via_feed[1])
                        targets_now[i] = via_feed[1]; best = None
                    else:
                        claimed.add((via_feed[1], "FEED")); claimed_tiles.add(via_feed[1])
                        best = ((1, 0, dist(p, acc)), acc, None); wheat_total_need -= P["pickup_wheat"]
            carry_value = sum(inv.get(k, 0) * prices[k] for k in PRODUCTS if k not in ("WHEAT", "FERTILIZER"))
            if p in ACCESS or act is not None:
                pass
            elif carry_value >= P["deliver_value"] and hour < P["bulk_hour"]:
                best = ((0, 0, dist(p, acc)), acc, None)
            elif not any(inv.get(a, 0) for a in ANIMALS) and sum(to_pick.values()) > pickers and (best is None or best[0][0] >= 1):
                best = ((0, 0, dist(p, acc)), acc, None); pickers += 1
            elif act is None and P["pickup_mode"] == "need" and unfed > 0 and inv.get("WHEAT", 0) == 0 and wheat_total_need > 0 and shed_wheat > 0 and day <= P["feed_last_day"] \
                    and (best is None or best[2] is None or best[2][0] != "FEED") and (best is None or dist(p, acc) <= best[0][2] + 2 or urgent):
                best = ((1, 0, dist(p, acc)), acc, None); wheat_total_need -= P["pickup_wheat"]
            if act is not None:
                pass
            elif best is not None and best[1] == p and best[2] is not None:
                act = best[2]
                apply_local(p, inv, act)
                claimed.add((p, act[0])); claimed_tiles.add(p)
                targets_now[i] = None if v2 else p
            elif best is not None and best[1] != p:
                q = best[1]
                targets_now[i] = q
                if best[2] is not None:
                    claimed.add((q, best[2][0])); claimed_tiles.add(q)
                    claim_dist[q] = min(claim_dist.get(q, 99), dist(p, q))
                    if best[2][0] == "PLANT":
                        plant_claims[best[2][1]] += 1; seeds_left[best[2][1]] -= 1
                    elif best[2][0].startswith("BUILD_"):
                        build_claims[best[2][0][6:]] += 1
                act = [step_toward(p, q)]
            else:
                act = ["PASS"]
                if P.get("debug"):
                    _S.setdefault("why", []).append((step, "no_task", None))
        if act[0] in MOVES:
            dx, dy = MOVES[act[0]]
            positions[i] = (p[0] + dx, p[1] + dy)
        actions.append(act)
        targets_now.setdefault(i, None)

    st["targets"] = {k: v for k, v in targets_now.items() if v is not None}; st["targets_day"] = day
    st["last"] = {i: (units[i], actions[i][0]) for i in range(len(units))}
    if P.get("debug"):
        _S.setdefault("tgt", {})[step] = {"targets": dict(targets_now), "claimed": sorted(claimed), "units": list(units), "acts": [list(x) for x in actions]}
    # PLANT 原子性：同作物本步种植请求不得超过持有种子
    plant_req = {}
    for a in actions:
        if a[0] == "PLANT":
            plant_req[a[1]] = plant_req.get(a[1], 0) + 1
    for i, a in enumerate(actions):
        if a[0] == "PLANT" and plant_req[a[1]] > seeds.get(a[1], 0):
            actions[i] = ["PASS"]

    # ---- L3 市场
    market = []
    est = money
    stock = dict(shed)
    for i, a in enumerate(actions):  # 本步单位动作入库部分（PLACE 到仓库）
        if a[0] == "PLACE" and units[i] in ACCESS and a[1] in PRODUCTS:
            stock[a[1]] = stock.get(a[1], 0) + a[2]

    def sell(item, n):
        nonlocal est
        n = min(n, stock.get(item, 0))
        if n > 0:
            market.append(["SELL", item, n]); stock[item] -= n; est += n * prices[item] * 0.95

    if step >= P["final_sell_step"]:
        for k in PRODUCTS:
            sell(k, stock.get(k, 0))
    else:
        if not fert_on or prices["FERTILIZER"] >= P["fert_sell_price"]:
            sell("FERTILIZER", stock.get("FERTILIZER", 0))
        keep = n_animals * P["wheat_keep_per_animal"]
        if step % 4 == P["wheat_sell_phase"] or hour == P["bulk_hour"]:
            sell("WHEAT", stock.get("WHEAT", 0) - keep)
        land_due = (len(farm["unlocked_quadrants"]) == 1 and step >= P["land1_step"] - 4) or (len(farm["unlocked_quadrants"]) == 2 and step >= P["land2_step"] - 4)
        inv_mk = obs["market"].get("inventory", {})
        prev = st.get("prev_prices") or {}
        for k in P["beat_items"]:
            if P["sell_mode"] == "refill" and k in P["refill_items"] and k in inv_mk and step < P["dump_step"] and money >= P["rich_money"] and not (land_due and money < 3000):
                pp = prev.get(k)
                if pp is not None and prices[k] > pp and stock.get(k, 0) > 0:
                    n = 0
                    while n < stock[k] and mprice(k, inv_mk[k] + n) >= pp:
                        n += 1
                    cap = max(P["refill_min"], int(stock[k] * P["refill_frac_cap"] + 0.999))
                    sell(k, max(P["refill_min"], min(n, cap)))
                continue
            if P["sell_mode"] == "refill" and k in P["refill_items"] and step >= P["dump_step"]:
                sell(k, stock.get(k, 0))
                continue
            if hour >= P["beat_dump_hour"] or (land_due and money < 3000) or (money < P["beat_poor_money"] and step % 4 == P["beat_phase"]):
                sell(k, stock.get(k, 0))
            elif step % 4 == P["beat_phase"] and (not P["beat_need_rise"] or prices[k] > (st.get("prev_prices") or {}).get(k, 0)):
                sell(k, max(P["beat_lot"], int(stock.get(k, 0) * P["beat_frac"])))
        if hour in (P["bulk_hour"], 0):
            for k in P["bulk_items"]:
                sell(k, stock.get(k, 0))
        if sum(v for k, v in stock.items()) > P["shed_guard"]:
            big = max(PRODUCTS, key=lambda k: stock.get(k, 0) * prices[k])
            sell(big, stock.get(big, 0) // 2)

    # 雇工
    if hour == 0 and day >= 1:
        market += [["HIRE"]] * P["hire_h0"].get(day, P["hire_h0_default"])
    elif hour == 1 and day >= 1:
        n = P["hire_h1"].get(day, P["hire_h1_default_after10"] if day >= 10 else 0)
        market += [["HIRE"]] * n
    elif hour == 2 and day == 1:
        market += [["HIRE"]] * P["hire_h2_day1"]

    # 买地
    nq = len(farm["unlocked_quadrants"])
    reserve_money = 0
    if nq == 1:
        if step >= P["land1_step"] and est >= 1000:
            market.append(["BUY_LAND"]); est -= 1000
        elif step >= P["land1_step"] - 20:
            reserve_money = 1000
    elif nq == 2:
        if step >= P["land2_step"] and est >= 2000:
            market.append(["BUY_LAND"]); est -= 2000
        elif step >= P["land2_step"] - 20:
            reserve_money = 2000

    # 买动物：有空结构且低于目标
    for a in P["animal_buy_order"]:
        s, cost = ANIMALS[a]
        free = len(empty_struct[s]) - sum(shed.get(x, 0) + carried[x] for x in ANIMALS if ANIMALS[x][0] == s)
        want = min(atarget[a] - counts[a], free)
        n = 0
        while n < want and est - cost >= reserve_money:
            n += 1; est -= cost
        if n > 0:
            market.append(["BUY_ANIMAL", a, n])

    # 饲料小麦
    if day <= P["feed_last_day"] and hour <= 14:
        need = unfed - carried["WHEAT"] - shed.get("WHEAT", 0) + P["wheat_buffer"]
        if need > 0:
            n = 0
            wp = prices["WHEAT"] + 1
            while n < min(need, 15) and est - wp >= 0:
                n += 1; est -= wp
            if n:
                market.append(["BUY_PRODUCT", "WHEAT", n])

    # 种子：按缺口与每步上限，保留买地现金
    for c in sorted(CROPS, key=lambda c: -crop_def[c]):
        want = min(P["seed_cap"][c], crop_def[c] - seeds.get(c, 0))
        n = 0
        while n < want and est - CROPS[c]["seed"] >= reserve_money:
            n += 1; est -= CROPS[c]["seed"]
        if n > 0:
            market.append(["BUY_SEED", c, n])

    st["prev_prices"] = dict(prices)
    return {"farmer": actions[0], "hands": actions[1:], "market": market[:10]}


def agent(obs, config=None):
    try:
        return decide(obs)
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}
