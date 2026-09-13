"""K1 compiled-knowledge agent（知识编译型四层启发式）。

架构（对应设计文档 README.md）：
  S0 knowledge.json  日程表/卖出规则/现金参数——全部策略数据，代码不含魔数
  S1 t0 初始化       载入知识包，按（未来的）商店分支选表
  S2 战略日程        人手/买地/建栏/动物/作物面积/施肥预算，零方差查表
  S3 反应式调度      任务生成 → 优先级桶 + 最近邻指派 + 先纵后横寻路
  S4 市场层          节拍卖出（t%4 相位）+ 卖肥阈值 + 采购日程 + 现金守卫
  S5 守护层          烂窗抢收 / 濒死喂养 / 终局清仓

执行器骨架源自 v4_demand_race（本仓库原创），战略层整体替换为
Majkel1337 逆向日程表（v71_majkel_reverse）。引擎契约同 v4：
  - field 先于 market 结算；市场订单逐单位 lockstep；step 718 最后动作。
  - 日终随身物品自动入 shed（容量 100，超出丢弃）。
  - 已实证教训：同回合有买单/雇工/买地或现金低于阈值时，禁止推迟/削减卖单
    （V38 贫困陷阱：卖单被压 → 种子买不到 → 产线崩）。
"""
import json
import math
from pathlib import Path

# ------------------------------------------------------------------
# 引擎常量（1.32.7 复刻，与 v4_demand_race 同源）
# ------------------------------------------------------------------
CROPS = {
    "WHEAT":      {"seed": 10,  "first_yield_day": 2,  "max_yield_day": 4,  "interval": 0, "max_yield": 6, "ongoing": False},
    "CARROT":     {"seed": 20,  "first_yield_day": 2,  "max_yield_day": 3,  "interval": 0, "max_yield": 4, "ongoing": False},
    "TOMATO":     {"seed": 50,  "first_yield_day": 8,  "max_yield_day": 8,  "interval": 1, "max_yield": 4, "ongoing": True},
    "STRAWBERRY": {"seed": 100, "first_yield_day": 10, "max_yield_day": 10, "interval": 2, "max_yield": 4, "ongoing": True},
    "MELON":      {"seed": 80,  "first_yield_day": 10, "max_yield_day": 12, "interval": 0, "max_yield": 6, "ongoing": False},
}
ANIMALS = {
    "GOOSE": {"cost": 300, "structure": "COOP",    "product": "EGG"},
    "COW":   {"cost": 400, "structure": "PASTURE", "product": "MILK"},
    "SHEEP": {"cost": 500, "structure": "PASTURE", "product": "WOOL"},
}
PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]
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
LAND_ORDER = ["NE", "SW", "SE"]
LAND_PRICES = [1000, 2000, 4000]
SHED_CAP = 100
MAX_ORDERS = 10
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

_KNOWLEDGE_EMBED = None  # build_submission 时内嵌 JSON 字符串
KN_OVERRIDE = None       # 调参器注入：{key: value}，浅覆盖 knowledge 顶层键


def _load_knowledge():
    if _KNOWLEDGE_EMBED:
        kn = json.loads(_KNOWLEDGE_EMBED)
    else:
        p = Path(__file__).resolve().parent / "knowledge.json"
        kn = json.loads(p.read_text())
    if KN_OVERRIDE:
        for k2, v in KN_OVERRIDE.items():
            kn[k2] = v
    kn.setdefault("tuning", {})
    return kn


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
    return max(1, int(round(price)))


# ------------------------------------------------------------------
# 几何
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
    """先纵后横（Majkel 指纹：两轴移动 94% 先纵后横）。"""
    if src[1] > dst[1]:
        return ["NORTH"]
    if src[1] < dst[1]:
        return ["SOUTH"]
    if src[0] > dst[0]:
        return ["WEST"]
    if src[0] < dst[0]:
        return ["EAST"]
    return None


# ------------------------------------------------------------------
# S2 战略日程（零方差查表）
# ------------------------------------------------------------------
class Schedule:
    def __init__(self, kn):
        self.kn = kn
        self.tu = kn.get("tuning", {})

    def hands_target(self, day):
        tbl = self.kn["hands_by_day"]
        return tbl[min(day, len(tbl) - 1)]

    def crop_targets(self, day, shops):
        out = {}
        scales = self.tu.get("crop_scale", {})
        for crop, tbl in self.kn["crop_area_by_day"].items():
            out[crop] = int(round(tbl[min(day, len(tbl) - 1)] * scales.get(crop, 1.0)))
        for shop, ov in self.kn["crop_area_shop_overrides"].items():
            if shop in shops:
                for crop, steps in ov.items():
                    for d0, n in steps:
                        if day >= d0:
                            out[crop] = max(out.get(crop, 0), n)
        return out

    def pasture_target(self, turn, shops):
        st = self.kn["structures"]
        if turn < st["pasture_early"]["turn_from"]:
            return 0
        if turn < st["pasture_main"]["turn_from"]:
            return st["pasture_early"]["count"]
        n = st["pasture_main"]["count_default"]
        for shop, cnt in st["pasture_main"]["count_by_shop"].items():
            if shop in shops:
                n = cnt
                break
        return n

    def coop_target(self, turn):
        st = self.kn["structures"]
        return st["coop"]["count_default"] if turn >= st["coop"]["turn_from"] else 0

    def animal_wanted(self, day):
        """累计到当天为止日程表要求买入的动物总数。"""
        s = self.tu.get("animal_scale", 1.0)
        want = {"COW": 0, "SHEEP": 0, "GOOSE": 0}
        for row in self.kn["animal_buys"]:
            if day >= row["day"]:
                for a, n in row["buys"].items():
                    want[a] += n
        return {a: int(round(n * s)) for a, n in want.items()}

    def fert_budget(self, day):
        tbl = self.kn["fertilize"]["daily_budget"]
        return int(round(tbl[min(day, len(tbl) - 1)] * self.tu.get("fert_scale", 1.0)))


# ------------------------------------------------------------------
# 角色规划：面积目标 → 地块角色（动物最近，服务频率定距离）
# ------------------------------------------------------------------
ROLE_ORDER = ["ANIMAL", "STRAWBERRY", "TOMATO", "CARROT", "WHEAT", "MELON"]


def plan_roles(tiles, bs, targets, n_pasture, n_coop):
    """每天重排：已占用格锁定角色；空格按需求序从近到远补。"""
    order = []
    for y in range(bs):
        for x in range(bs):
            if tiles[y][x] != "LOCKED" and (x, y) not in _shed_tiles(bs):
                order.append((x, y))
    order.sort(key=lambda t: (_shed_dist(t, bs), t[1], t[0]))

    roles = {}
    remaining = dict(targets)
    remaining["ANIMAL"] = n_pasture + n_coop
    # 1) 已占用格锁定
    for (x, y) in order:
        t = tiles[y][x]
        if not isinstance(t, dict):
            continue
        if "animal" in t or t.get("kind") in ("PASTURE", "COOP"):
            roles[(x, y)] = "ANIMAL"
            remaining["ANIMAL"] = max(0, remaining["ANIMAL"] - 1)
        elif t.get("kind") == "PLANT":
            c = t.get("crop")
            roles[(x, y)] = c
            remaining[c] = max(0, remaining.get(c, 0) - 1)
    # 2) 空格（含杂草格）按需求序补
    for (x, y) in order:
        if (x, y) in roles:
            continue
        t = tiles[y][x]
        if isinstance(t, dict) and t.get("kind") not in ("WEED",):
            continue
        for role in ROLE_ORDER:
            if remaining.get(role, 0) > 0:
                roles[(x, y)] = role
                remaining[role] -= 1
                break
    return roles


# ------------------------------------------------------------------
# S3 任务生成
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


def build_tasks(st, kn, sched, tiles, bs, seeds, shed, day, turn, shops):
    roles = st["roles"]
    tu = kn.get("tuning", {})
    hour = turn % 24
    tasks = []
    animals, plants, weeds, empty, free_struct = [], [], [], [], []
    n_pasture = n_coop = 0
    for y in range(bs):
        for x in range(bs):
            t = tiles[y][x]
            if t == "LOCKED" or (x, y) in _shed_tiles(bs):
                continue
            if t is None:
                empty.append((x, y))
            elif isinstance(t, dict):
                if "animal" in t:
                    animals.append(((x, y), t))
                    n_pasture += 1 if ANIMALS[t["animal"]]["structure"] == "PASTURE" else 0
                    n_coop += 1 if ANIMALS[t["animal"]]["structure"] == "COOP" else 0
                elif t.get("kind") == "PLANT":
                    plants.append(((x, y), t))
                elif t.get("kind") == "WEED":
                    weeds.append((x, y))
                elif t.get("kind") in ("PASTURE", "COOP"):
                    free_struct.append(((x, y), t.get("kind")))
                    n_pasture += 1 if t["kind"] == "PASTURE" else 0
                    n_coop += 1 if t["kind"] == "COOP" else 0
    st["free_struct"] = free_struct
    st["n_animals"] = len(animals)
    st["n_starving"] = sum(1 for _, t in animals
                           if not t.get("fed_today") and t.get("consecutive_unfed", 0) >= 1)
    planted = {}
    for _, t in plants:
        planted[t["crop"]] = planted.get(t["crop"], 0) + 1
    st["planted"] = planted
    stop_feed = day >= kn["feed"]["stop_feed_day"]

    # P0 生存线：濒死喂养 / 濒枯浇水
    if not stop_feed:
        for pos, t in animals:
            if not t.get("fed_today") and t.get("consecutive_unfed", 0) >= 1:
                tasks.append((0, "WHEAT", pos, ["FEED"]))
    for pos, t in plants:
        if not t.get("watered_today") and t.get("consecutive_unwatered", 0) >= 1:
            tasks.append((0.5, None, pos, ["WATER"]))
    # P1 烂窗抢收（一次性作物）
    for pos, t in plants:
        cd = CROPS[t["crop"]]
        if not cd["ongoing"] and t.get("yield_units", 0) > 0:
            rot = (t["planted_day"] + cd["max_yield_day"] + 1) * 24
            if turn >= rot - 26:
                tasks.append((1, None, pos, ["HARVEST"]))
    # P2 常规喂养 / 成熟一次性作物收获 / P3 浇水
    if not stop_feed:
        feed_ddl = tu.get("feed_deadline_hour", 18)
        for pos, t in animals:
            if not t.get("fed_today"):
                tasks.append((2 if turn % 24 < feed_ddl else 1.6, "WHEAT", pos, ["FEED"]))
    for pos, t in plants:
        cd = CROPS[t["crop"]]
        if not cd["ongoing"] and t.get("yield_units", 0) > 0:
            age = day - t["planted_day"]
            if age >= cd["max_yield_day"] or t["yield_units"] >= cd["max_yield"]:
                tasks.append((2.2, None, pos, ["HARVEST"]))
    water_ddl = tu.get("water_deadline_hour", 16)
    for pos, t in plants:
        if not t.get("watered_today"):
            # 白天就近浇；傍晚起未浇的升入生存桶清尾（当天不浇即枯/杂草化）
            tasks.append((3 if hour < water_ddl else 1.5, None, pos, ["WATER"]))
    # P4 放置动物（仅 14 点前，保证当天喂得上；引擎：连续两天未喂即逃走）
    if turn % 24 <= 14:
        for a in ("SHEEP", "COW", "GOOSE"):
            n_have = shed.get(a, 0) + sum(inv.get(a, 0) for inv in st["invs"])
            if n_have <= 0:
                continue
            slots = [p for p, k in free_struct if k == ANIMALS[a]["structure"]]
            for p in slots[:n_have]:
                tasks.append((4, a, p, ["PLACE", a]))
    # P5 产出收获（收获=变现+恢复产出，先于照料）：动物与 ongoing 作物
    ymin = tu.get("harvest_yield_min", 2)
    for pos, t in animals:
        if t.get("yield_units", 0) >= ymin:
            tasks.append((5, None, pos, ["HARVEST"]))
    for pos, t in plants:
        cd = CROPS[t["crop"]]
        if cd["ongoing"] and t.get("yield_units", 0) >= ymin and day - t["planted_day"] >= cd["first_yield_day"]:
            tasks.append((5, None, pos, ["HARVEST"]))
    # P6 照料
    for pos, t in animals:
        if not t.get("cared_today"):
            tasks.append((6, None, pos, ["CARE"]))
    # P4 建栏（日程目标数 - 现有数；在存量服务(浇水)之后）
    want_pasture = sched.pasture_target(turn, shops)
    want_coop = sched.coop_target(turn)
    n_p, n_c = n_pasture, n_coop
    for p in empty:
        if roles.get(p) != "ANIMAL":
            continue
        if n_p < want_pasture:
            tasks.append((4, None, p, ["BUILD_PASTURE"]))
            n_p += 1
        elif n_c < want_coop:
            tasks.append((4, None, p, ["BUILD_COOP"]))
            n_c += 1
    # P4.3 播种（面积缺口 + 截止保护 + 日限速；下午种、傍晚浇同天闭环）
    if turn <= kn["endgame"]["last_plant_turn"]:
        targets = st["crop_targets"]
        deficit = {c: targets.get(c, 0) - planted.get(c, 0) for c in CROPS}
        until = kn.get("plant_until_day", {})
        plant_quota = tu.get("plant_per_day_cap", kn.get("plant_per_day_cap", 6)) - st.get("planted_today", 0)
        for p in empty:
            if plant_quota <= 0:
                break
            role = roles.get(p)
            if role not in CROPS:
                continue
            crop = role
            if crop in until and day > until[crop]:
                crop = "WHEAT"
            cd = CROPS[crop]
            need = cd["first_yield_day"] if cd["ongoing"] else cd["max_yield_day"]
            if day + need + 1 > 29:
                crop = "WHEAT"
                if day + CROPS["WHEAT"]["max_yield_day"] + 1 > 29 or deficit.get("WHEAT", 0) <= 0:
                    continue
            if deficit.get(crop, 0) > 0 and seeds.get(crop, 0) > 0:
                tasks.append((4.3, None, p, ["PLANT", crop]))
                deficit[crop] -= 1
                plant_quota -= 1
                seeds = dict(seeds)
                seeds[crop] -= 1
    # P3.5 施肥（日预算，优先级表）
    fb = kn["fertilize"]
    if day >= fb["start_day"] and turn <= fb["last_fert_turn"]:
        budget = sched.fert_budget(day) - st.get("fert_done_today", 0)
        if budget > 0:
            cand = []
            for pos, t in plants:
                cd = CROPS[t["crop"]]
                if t.get("fertilized_until_day", -1) >= day + 1:
                    continue
                age = day - t["planted_day"]
                if cd["ongoing"] and age >= cd["first_yield_day"] - 3:
                    cand.append((fb["crop_priority"].index(t["crop"]) if t["crop"] in fb["crop_priority"] else 9, pos))
                elif not cd["ongoing"] and t["crop"] in fb["crop_priority"] and age <= 1:
                    cand.append((fb["crop_priority"].index(t["crop"]), pos))
            cand.sort()
            for _, pos in cand[:budget]:
                tasks.append((4.5, "FERTILIZER", pos, ["FERTILIZE"]))
    # P9 收肥 / P10 收 ongoing 产出与动物产出 / P11 清杂草
    for pos, t in animals:
        if t.get("fertilizer_available"):
            tasks.append((9, None, pos, ["COLLECT_FERTILIZER"]))
    for pos, t in plants:
        cd = CROPS[t["crop"]]
        if cd["ongoing"] and t.get("yield_units", 0) > 0 and day - t["planted_day"] >= cd["first_yield_day"]:
            tasks.append((10, None, pos, ["HARVEST"]))
    for pos, t in animals:
        if t.get("yield_units", 0) > 0:
            tasks.append((10.5, None, pos, ["HARVEST"]))
    for p in weeds:
        tasks.append((11, None, p, ["DIG"]))
    return tasks


# ------------------------------------------------------------------
# S3 指派（v4 框架：绑定保持 + 供应链 + 优先级桶内最近邻）
# ------------------------------------------------------------------
def _apply_local(invs, i, op):
    if op[0] == "FEED":
        invs[i]["WHEAT"] = max(0, invs[i].get("WHEAT", 0) - 1)
    elif op[0] == "FERTILIZE":
        invs[i]["FERTILIZER"] = max(0, invs[i].get("FERTILIZER", 0) - 1)
    elif op[0] == "PLACE" and len(op) > 1 and op[1] in ANIMALS:
        invs[i][op[1]] = max(0, invs[i].get(op[1], 0) - 1)


def assign(st, tasks, positions, invs, tiles, bs, shed, kn):
    n = len(positions)
    actions = [["PASS"] for _ in range(n)]
    used, claimed = set(), set()
    shed_set = set(_shed_tiles(bs))

    def carried(i, item):
        return invs[i].get(item, 0)

    # 0) 既有绑定继续
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
            _apply_local(invs, i, op)
            if op[0] == "FERTILIZE":
                st["fert_done_today"] = st.get("fert_done_today", 0) + 1
            elif op[0] == "PLANT":
                st["planted_today"] = st.get("planted_today", 0) + 1
        else:
            actions[i] = _step_toward(positions[i], pos_t) or ["PASS"]
            used.add(i)
            claimed.add((pos_t, op[0]))

    # 0.5) 喂养供应链：有 FEED 任务但无人持麦 → 派最近单位取麦
    n_feed = sum(1 for t in tasks if t[3][0] == "FEED")
    wheat_carried = sum(carried(i, "WHEAT") for i in range(n) if i not in used)
    feeder_mode = kn.get("tuning", {}).get("feeder_mode", 1)
    feeder_hungry = (wheat_carried < n_feed) if feeder_mode else \
        (sum(1 for i in range(n) if carried(i, "WHEAT") > 0 and i not in used) * 5 < n_feed)
    if n_feed > 0 and feeder_hungry and shed.get("WHEAT", 0) > 0:
        best = min(((_shed_dist(positions[i], bs), i) for i in range(n) if i not in used), default=None)
        if best:
            i = best[1]
            if positions[i] in shed_set:
                take = min(n_feed + 2, shed["WHEAT"])
                actions[i] = ["PICKUP", "WHEAT", take]
                shed["WHEAT"] -= take
                invs[i]["WHEAT"] = invs[i].get("WHEAT", 0) + take
            else:
                actions[i] = _step_toward(positions[i], min(shed_set, key=lambda s: _dist(positions[i], s))) or ["PASS"]
            used.add(i)

    # 0.6) 动物放置供应链
    shed_animals = [a for a in ANIMALS if shed.get(a, 0) > 0]
    if shed_animals and st.get("free_struct"):
        holding = sum(1 for i in range(n) if any(invs[i].get(a, 0) > 0 for a in ANIMALS))
        if holding == 0:
            best = min(((_shed_dist(positions[i], bs), i) for i in range(n) if i not in used), default=None)
            if best:
                i = best[1]
                if positions[i] in shed_set:
                    a = shed_animals[0]
                    take = min(shed[a], 4)
                    actions[i] = ["PICKUP", a, take]
                    shed[a] -= take
                    invs[i][a] = invs[i].get(a, 0) + take
                else:
                    actions[i] = _step_toward(positions[i], min(shed_set, key=lambda s: _dist(positions[i], s))) or ["PASS"]
                used.add(i)

    # 0.7) 肥料供应链：有 FERTILIZE 任务但无人持肥
    n_fert = sum(1 for t in tasks if t[3][0] == "FERTILIZE")
    fert_holders = sum(1 for i in range(n) if carried(i, "FERTILIZER") > 0 and i not in used)
    if n_fert > 0 and fert_holders == 0 and shed.get("FERTILIZER", 0) > 0:
        best = min(((_shed_dist(positions[i], bs), i) for i in range(n) if i not in used), default=None)
        if best:
            i = best[1]
            if positions[i] in shed_set:
                take = min(n_fert, shed["FERTILIZER"], 10)
                actions[i] = ["PICKUP", "FERTILIZER", take]
                shed["FERTILIZER"] -= take
                invs[i]["FERTILIZER"] = invs[i].get("FERTILIZER", 0) + take
            else:
                actions[i] = _step_toward(positions[i], min(shed_set, key=lambda s: _dist(positions[i], s))) or ["PASS"]
            used.add(i)

    # 1) 优先级桶：P0-P2 生存/资本任务严格分层；P3+ 并入大桶按(距离,优先级)——
    #    脚下任务(dist=0)总是先做，同块浇水/收获/施肥自然串联，压移动开销。
    buckets = {}
    for tk in tasks:
        b = int(tk[0]) if tk[0] < 3 else 3
        buckets.setdefault(b, []).append(tk)
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
                _apply_local(invs, i, op)
                if op[0] == "FERTILIZE":
                    st["fert_done_today"] = st.get("fert_done_today", 0) + 1
            else:
                st["assign"][i] = (pos_t, op, need)
                actions[i] = _step_toward(positions[i], pos_t) or ["PASS"]

    # 2) 空闲单位：预备补给或原地待命
    need_wheat = any(t[1] == "WHEAT" for t in tasks)
    need_fert = any(t[1] == "FERTILIZER" for t in tasks)
    for i in range(n):
        if i in used:
            continue
        pos = positions[i]
        if pos in shed_set:
            if need_wheat and carried(i, "WHEAT") < 2 and shed.get("WHEAT", 0) > 0:
                take = min(6, shed["WHEAT"])
                actions[i] = ["PICKUP", "WHEAT", take]
                shed["WHEAT"] -= take
                invs[i]["WHEAT"] = invs[i].get("WHEAT", 0) + take
                used.add(i)
            elif need_fert and carried(i, "FERTILIZER") < 1 and shed.get("FERTILIZER", 0) > 0:
                take = min(3, shed["FERTILIZER"])
                actions[i] = ["PICKUP", "FERTILIZER", take]
                shed["FERTILIZER"] -= take
                invs[i]["FERTILIZER"] = invs[i].get("FERTILIZER", 0) + take
                used.add(i)
        elif need_wheat or need_fert:
            actions[i] = _step_toward(pos, min(shed_set, key=lambda s: _dist(pos, s))) or ["PASS"]
            used.add(i)
    return actions


# ------------------------------------------------------------------
# S4 市场层：节拍卖出 + 采购日程 + 现金守卫
# ------------------------------------------------------------------
def _batch_size(item, inv, cap, slip_tol):
    p0 = market_price(item, inv)
    lo = max(1, int(p0 * (1 - slip_tol)))
    q = 0
    while q < cap and market_price(item, inv + q) >= lo:
        q += 1
    return max(1, q)


def market_orders(st, kn, sched, obs, farm, shed, seeds, prices, day, hour, turn, shops):
    sr = kn["sell_rules"]
    money = farm["money"]
    inv_mkt = dict((obs.get("market") or {}).get("inventory") or {})
    sells, buys = [], []

    # ---- 终局清仓 ----
    if turn >= kn["endgame"]["terminal_from_turn"]:
        order = sorted((it for it in PRODUCTS if shed.get(it, 0) > 0),
                       key=lambda it: -prices.get(it, 0))
        for it in order:
            sells.append(["SELL", it, shed[it]])
        return sells[:MAX_ORDERS]

    feed_need = 0 if day >= kn["feed"]["stop_feed_day"] else \
        st.get("n_animals", 0) * kn["feed"]["buffer_days"]

    # ---- 卖出（节拍表驱动）----
    for it, rule in sr["phase_sell"].items():
        have = shed.get(it, 0)
        if have > 0 and turn % 4 == rule["phase"]:
            q = min(have, rule["lot_max"])
            sells.append(["SELL", it, q])
    for it, rule in sr["eod_sell"].items():
        have = shed.get(it, 0)
        if have > 0 and hour >= rule["hour"]:
            sells.append(["SELL", it, have])
    # 小麦：余粮（扣饲料预留）在相位或日末卖
    wr = sr["wheat"]
    wheat_extra = shed.get("WHEAT", 0) - feed_need
    if wheat_extra > 2 and (turn % 4 == wr["phase"] or hour >= wr["eod_hour"]):
        sells.append(["SELL", "WHEAT", min(wheat_extra, wr["lot_max"])])
    # 瓜：即收即卖，slip 控批
    mr = sr["melon"]
    have_melon = shed.get("MELON", 0)
    if have_melon > 0:
        q = min(have_melon, _batch_size("MELON", inv_mkt.get("MELON", 10000), mr["lot_max"], mr["slip_tol"]))
        sells.append(["SELL", "MELON", q])
    # 肥料：保留日预算，超出部分高价卖
    fert_keep = sched.fert_budget(day) + sched.fert_budget(day + 1) if day >= kn["fertilize"]["start_day"] - 2 else 6
    fert_extra = shed.get("FERTILIZER", 0) - fert_keep
    if fert_extra > 0 and prices.get("FERTILIZER", 0) >= sr["fertilizer_sell_price"]:
        sells.append(["SELL", "FERTILIZER", fert_extra])

    # 仓压保护：仓库将满时强制加卖最高价持仓
    shed_used = sum(shed.values())
    if shed_used > SHED_CAP - 12:
        sold = {o[1] for o in sells}
        for it in sorted(PRODUCTS, key=lambda x: -prices.get(x, 0)):
            if it not in sold and shed.get(it, 0) > 3 and it != "WHEAT":
                sells.append(["SELL", it, shed[it] // 2])
                break

    # ---- 买入（现金守卫：floor 之上才花非生存钱）----
    floor = kn.get("tuning", {}).get("cash_floor", kn["cash"]["floor"])

    # 雇工：h0/h1 雇到日程目标
    if hour in kn["hire_hours"] and turn <= kn["last_hire_turn"]:
        want = sched.hands_target(day)
        hired = int(farm.get("hires_today", 0) or 0)
        cur = len(farm.get("hands") or [])
        for _ in range(max(0, want - max(hired, cur))):
            buys.append(["HIRE"])

    # 买地：精确时点
    quads = farm.get("unlocked_quadrants") or ["NW"]
    n_extra = len(quads) - 1
    if 0 <= n_extra < len(LAND_ORDER):
        quad = LAND_ORDER[n_extra]
        t_buy = kn["land_buy_turns"].get(quad)
        if t_buy is not None and turn >= t_buy and money >= LAND_PRICES[n_extra] + floor:
            buys.append(["BUY_LAND"])
            money -= LAND_PRICES[n_extra]

    # 动物：日程累计目标 - 已有（复利资产，优先于种子）
    animal_gap_cost = 0
    if turn <= kn["last_animal_turn"]:
        want = sched.animal_wanted(day)
        have = dict(st.get("placed_counts", {}))
        for a in ANIMALS:
            have[a] = have.get(a, 0) + shed.get(a, 0) + sum(inv.get(a, 0) for inv in st["invs"])
        for a in ("COW", "SHEEP", "GOOSE"):
            gap = want.get(a, 0) - have.get(a, 0)
            n_buy = 0
            while gap > 0 and money >= ANIMALS[a]["cost"] + floor and n_buy < 3:
                buys.append(["BUY_ANIMAL", a, 1])
                money -= ANIMALS[a]["cost"]
                gap -= 1
                n_buy += 1
            animal_gap_cost += gap * ANIMALS[a]["cost"]
        # 为未买齐的动物批次预留预算，防止种子把钱吃光
        animal_gap_cost = min(animal_gap_cost, 1200)

    # 种子：面积缺口，轮询小批购买（防单一作物挤占现金）
    targets = st["crop_targets"]
    planted = st.get("planted", {})
    seed_floor = floor + animal_gap_cost
    seed_gap = {}
    for crop in CROPS:
        cd = CROPS[crop]
        need_day = cd["first_yield_day"] if cd["ongoing"] else cd["max_yield_day"]
        if day + need_day + 1 > 29:
            continue
        g = targets.get(crop, 0) - planted.get(crop, 0) - seeds.get(crop, 0)
        if g > 0:
            seed_gap[crop] = g
    seed_orders = {}
    rounds = 0
    while seed_gap and rounds < 6:
        rounds += 1
        for crop in ("WHEAT", "MELON", "STRAWBERRY", "TOMATO", "CARROT"):
            g = seed_gap.get(crop, 0)
            if g <= 0:
                continue
            cd = CROPS[crop]
            n = min(g, 3, max(0, int((money - seed_floor) // cd["seed"])))
            if n > 0:
                seed_orders[crop] = seed_orders.get(crop, 0) + n
                seed_gap[crop] = g - n
                money -= cd["seed"] * n
            else:
                seed_gap.pop(crop, None)
    for crop, n in seed_orders.items():
        buys.append(["BUY_SEED", crop, n])

    # 饲料：缓冲补货 + 大批日
    fd = kn["feed"]
    if day < fd["stop_feed_day"] and st.get("n_animals", 0) > 0:
        wheat_have = shed.get("WHEAT", 0) + sum(inv.get("WHEAT", 0) for inv in st["invs"])
        target = st["n_animals"] * (fd["bulk_target_per_animal"] if day in fd["bulk_days"] else fd["buffer_days"])
        p_wheat = prices.get("WHEAT", 25)
        starving = st.get("n_starving", 0) > 0
        cap_price = 10 ** 9 if starving else fd["wheat_buy_price_cap"]
        if wheat_have < max(target, fd["low_water_mark"]) and p_wheat <= cap_price:
            room = SHED_CAP - 8 - sum(shed.values())
            n = min(target - wheat_have, max(0, room),
                    max(0, int((money - (100 if starving else floor)) // max(1, p_wheat))))
            if n > 0:
                buys.insert(0, ["BUY_PRODUCT", "WHEAT", n])
                money -= p_wheat * n

    # 教训：有买单时绝不推迟/削减卖单——本函数卖单先生成、不回收，天然满足。
    return (sells + buys)[:MAX_ORDERS]


# ------------------------------------------------------------------
# 主入口（S1 状态机）
# ------------------------------------------------------------------
_STATE = {}


def _get_state(player, turn):
    st = _STATE.get(player)
    if st is None or turn <= st.get("last_turn", -1):
        st = {"kn": _load_knowledge(), "assign": {}, "day": -1, "last_turn": -1,
              "roles": {}, "invs": [{}], "crop_targets": {}}
        st["sched"] = Schedule(st["kn"])
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

    st = _get_state(player, turn)
    st["last_turn"] = turn
    kn, sched = st["kn"], st["sched"]
    shops = list((obs.get("town") or {}).get("unlocked_shops") or [])

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

    # 每天 h0：重算面积目标与角色（土地解锁/商店变化都会被吸收）
    if st["day"] != day:
        st["day"] = day
        st["assign"] = {}
        st["fert_done_today"] = 0
        st["planted_today"] = 0
    st["crop_targets"] = sched.crop_targets(day, shops)
    st["roles"] = plan_roles(tiles, bs, st["crop_targets"],
                             sched.pasture_target(turn, shops), sched.coop_target(turn))

    st["placed_counts"] = {}
    for row in tiles:
        for t in row:
            if isinstance(t, dict) and "animal" in t:
                st["placed_counts"][t["animal"]] = st["placed_counts"].get(t["animal"], 0) + 1

    tasks = build_tasks(st, kn, sched, tiles, bs, seeds, shed, day, turn, shops)
    market = market_orders(st, kn, sched, obs, farm, shed, seeds, prices, day, hour, turn, shops)

    if turn >= kn["endgame"]["terminal_from_turn"]:
        # 终局：回仓卸货 + 近处抢收
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
            elif turn < 714:
                cand = [(p, op) for (pri, need, p, op) in tasks if op[0] == "HARVEST" and p not in claimed]
                if cand:
                    p, op = min(cand, key=lambda c: _dist(pos, c[0]))
                    claimed.add(p)
                    actions[i] = op if pos == p else (_step_toward(pos, p) or ["PASS"])
        st["assign"] = {}
    else:
        actions = assign(st, tasks, positions, invs, tiles, bs, shed, kn)

    return {"farmer": actions[0], "hands": actions[1:n_units], "market": market}


def agent(obs, config=None):
    try:
        return _decide(obs, config)
    except Exception:
        farms = obs.get("farms") or []
        player = obs.get("player", 0)
        n = len(farms[player].get("hands") or []) if farms and player < len(farms) else 0
        return {"farmer": ["PASS"], "hands": [["PASS"]] * n, "market": []}


_ENTRY = agent
