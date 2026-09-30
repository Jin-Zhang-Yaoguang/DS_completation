"""V125-R4 执行合约原型：同 R3 经营谱系，动作收据推进短期合约。"""
from __future__ import annotations

import math
from collections import Counter


CANDIDATE_ID = "V125-R7-PROTOTYPE"
PARAMS = {"router": "adaptive", "task_cost": "full", "care_weight": 1.0,
          "max_hands": 12, "forecast_days": 6, "early_animals": 4}
CROPS = {
    "WHEAT": (10, 2, 4, 0, 6), "CARROT": (20, 2, 3, 0, 4),
    "TOMATO": (50, 8, 8, 1, 4), "STRAWBERRY": (100, 10, 10, 2, 4),
    "MELON": (80, 10, 12, 0, 6),
}
ANIMALS = {"GOOSE": (300, "COOP", 4, 1, 4, "EGG"),
           "COW": (400, "PASTURE", 8, 2, 6, "MILK"),
           "SHEEP": (500, "PASTURE", 6, 3, 6, "WOOL")}
PRODUCTS = tuple(CROPS) + ("EGG", "MILK", "WOOL", "FERTILIZER")
MARKET = {
    "WHEAT": (25, 400, "sqrt", .8, "log", .2),
    "CARROT": (35, 450, "hinge", 1., "sqrt", .7),
    "TOMATO": (60, 200, "hinge", .4, "sqrt", .6),
    "STRAWBERRY": (120, 100, "sqrt", .7, "linear", 1.6),
    "MELON": (250, 300, "log", .2, "sq", 3.6),
    "EGG": (50, 332, "hinge", .4, "log", .2),
    "MILK": (160, 122, "sqrt", .6, "linear", 1.6),
    "WOOL": (200, 105, "log", .2, "sq", 3.2),
    "FERTILIZER": (100, 200, "linear", .4, "linear", .4),
}
SHOPS = {"BAKERY": ("EGG", "WHEAT"), "PIZZA_SHOP": ("MILK", "TOMATO", "WHEAT"),
         "BRUNCH_SPOT": ("EGG", "WHEAT", "STRAWBERRY"), "YARN_STORE": ("WOOL",),
         "ICE_CREAM_SHOP": ("STRAWBERRY", "MILK", "WHEAT"), "PET_CAFE": ("CARROT",),
         "SMOOTHIE_SHOP": ("STRAWBERRY", "MILK"),
         "FARMERS_MARKET": ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY")}
ACCESS = ((4, 4), (5, 4), (4, 5), (5, 5))
FIB = (1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610)
_STATES = {}


def dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def home(p):
    return min(ACCESS, key=lambda q: (dist(p, q), q))


def move(p, q):
    dx, dy = q[0] - p[0], q[1] - p[1]
    if abs(dx) >= abs(dy) and dx:
        return ["EAST" if dx > 0 else "WEST"]
    if dy:
        return ["SOUTH" if dy > 0 else "NORTH"]
    return ["PASS"]


def curve(shape, x, scale):
    if shape == "sqrt":
        return math.sqrt(x)
    if shape == "log":
        return math.log1p(x)
    if shape == "log10":
        return math.log10(1 + x)
    if shape == "sq":
        return x * x
    if shape == "hinge":
        z = x / scale
        return z + 8 * max(0, z - 1) ** 2
    return x


def price(item, supply, overrides=None):
    b, t, low, la, high, ha = MARKET[item]
    p = (overrides or {}).get(item, {})
    b, t = p.get("base", b), p.get("T", t)
    center = p.get("I0", 10000)
    delta = supply - center
    shape = p.get("below_func", low) if delta < 0 else p.get("above_func", high)
    amp = p.get("below_target", la) if delta < 0 else p.get("above_target", ha)
    adjustment = amp * b * curve(shape, abs(delta), t) / max(1e-9, curve(shape, t, t))
    return max(1, int(round(b + (adjustment if delta < 0 else -adjustment))))


def counts(farm, private=None):
    c = Counter()
    for row in farm["tiles"]:
        for tile in row:
            if isinstance(tile, dict):
                if "animal" in tile:
                    c[tile["animal"]] += 1
                elif tile.get("kind") == "PLANT":
                    c[tile["crop"]] += 1
    if private is not None:
        for a in ANIMALS:
            c[a] += private["shed"].get(a, 0)
            c[a] += sum(i.get(a, 0) for i in private.get("inventories", []))
    return c


def inventory_total(private, item):
    return private.get("shed", {}).get(item, 0) + sum(i.get(item, 0) for i in private.get("inventories", []))


def summary(obs):
    f = obs["farms"][obs["player"]]
    return {"day": obs["day"], "hour": obs["hour"], "money": f["money"],
            "land": len(f["unlocked_quadrants"]), "hands": len(f["hands"]),
            "assets": dict(counts(f, obs["private"])),
            "seeds": dict(obs["private"]["seeds"])}


def new_state(obs):
    return {"last_step": -1, "last_day": -1, "previous": None, "issued": [],
            "procurement": [], "tasks": {}, "metrics": Counter(),
            "daily": [], "expert": "balanced", "forecasts": {}, "crop_choice": "WHEAT"}


def confirm_orders(st, obs):
    prev = st["previous"]
    if prev is None:
        return
    now = summary(obs)
    # 单位动作先于市场，因此种子消费必须加回；动物总量跨仓库/随身/地块守恒。
    plant_used = Counter(a[1] for a in st.get("unit_actions", []) if a and a[0] == "PLANT")
    for order in st["issued"]:
        op = order[0]
        if op == "BUY_LAND":
            requested, got = 1, now["land"] - prev["land"]
        elif op == "HIRE" and now["day"] == prev["day"]:
            continue  # 雇工按整批核对，避免逐订单重复计数。
        elif op == "BUY_ANIMAL":
            requested = order[2]
            got = now["assets"].get(order[1], 0) - prev["assets"].get(order[1], 0)
        elif op == "BUY_SEED":
            requested = order[2]
            got = now["seeds"].get(order[1], 0) - prev["seeds"].get(order[1], 0) + plant_used[order[1]]
        else:
            continue
        got = max(0, min(requested, got))
        st["metrics"]["purchase_requested"] += requested
        st["metrics"]["purchase_confirmed"] += got
        if got != requested:
            st["procurement"].append({"step": st["last_step"], "order": order,
                                      "confirmed": got, "missing": requested - got})
    hires = sum(o[0] == "HIRE" for o in st["issued"])
    if hires and now["day"] == prev["day"]:
        st["metrics"]["hire_requested"] += hires
        st["metrics"]["hire_confirmed"] += max(0, now["hands"] - prev["hands"])
    # 目标永远由当前实际总资产计算。未成交订单没有可以错误递减的待办计数。
    st["previous"] = now


"""R7 最小逐日投资层；由构建脚本并入单文件，不调用其他完整策略。"""


def project_calendar(tile, day, hour=0, position=(4, 4)):
    """每日照护、及时采收交付的模型日历；物量可用纯规则控制核对。"""
    goods, work, feed = {}, Counter(), Counter()
    t = dict(tile)
    distance = dist(position, home(position))

    def product(d, item, qty):
        qty = int(qty)
        if qty <= 0 or d > 29:
            return
        if d == 29 and day == 29 and hour + distance + 2 > 22:
            return
        goods.setdefault(d, Counter())[item] += qty
        work[d] += 2 + distance  # 采收/收肥，返仓与放下；销售为市场动作。

    if "animal" in t:
        a = t["animal"]
        spec = ANIMALS[a]
        product(day, spec[5], t.get("yield_units", 0))
        if t.get("fertilizer_available"):
            product(day, "FERTILIZER", 1)
        pending = int(t.get("pending_care_bonus", 0))
        for d in range(day, 29):
            fed = bool(t.get("fed_today")) if d == day else False
            cared = bool(t.get("cared_today")) if d == day else False
            if not fed:
                work[d] += 1
                feed[d] += 1
            if d < 28 and not cared:
                work[d] += 1
                cared = True
            next_day = d + 1
            age = next_day - t["placed_day"] - spec[2]
            if age >= 0 and age % spec[3] == 0:
                product(next_day, spec[5], min(spec[4], 1 + pending))
                pending = 0
            if cared:
                pending += 1
            product(next_day, "FERTILIZER", 1)
    else:
        c = t["crop"]
        _, first, last, interval, cap = CROPS[c]
        stock = int(t.get("yield_units", 0))
        dry = int(t.get("consecutive_unwatered", 0))
        for d in range(day, 30):
            age = d - t["planted_day"]
            if age < 0:
                continue
            fertilized = t.get("fertilized_until_day", -1) >= d
            watered = bool(t.get("watered_today")) if d == day else False
            if interval:
                final_age = first + interval * (cap - 1)
                next_produces = age + 1 >= first and (age + 1 - first) % interval == 0 and age + 1 <= final_age
                need = not watered and d < 29 and age < final_age and (dry >= 1 or next_produces or age == 0)
            else:
                growth = (last + 1) // 2 <= age <= last
                need = not watered and age <= last and (dry >= 1 or growth or age == 0)
            if need:
                work[d] += 1
                watered = True
                if not interval and growth:
                    stock = min(cap, stock + (2 if fertilized else 1))
            if stock and age >= first and (interval or stock >= cap or age >= last or d == 29):
                product(d, c, stock)
                stock = 0
                if not interval:
                    break
            if d == 29:
                break
            dry = 0 if watered else dry + 1
            if dry >= 2:
                break
            if interval and next_produces:
                stock = min(cap, stock + (2 if watered and fertilized else 1))
            if interval and age >= final_age and not stock:
                break
    for d in list(work):
        if work[d]:
            work[d] += max(1, distance)  # 当日进入地块的一段保守交通预算。
    return {"goods": {d: dict(v) for d, v in goods.items()}, "work": dict(work), "feed": dict(feed)}


def dated_market_model(obs):
    """固定已知商店需求；仅在田资产进入供给，未落地动物不冒充成熟。"""
    day = obs["day"]
    supply = {p: float(obs["market"]["inventory"].get(p, 10000)) for p in PRODUCTS}
    demand = {p: 0. if p == "FERTILIZER" else 1. for p in PRODUCTS}
    for shop in obs["town"].get("unlocked_shops", []):
        products = SHOPS.get(shop, ())
        for p in products:
            demand[p] += 12 if len(products) == 1 else 6
    calendars = []
    for seat, farm in enumerate(obs["farms"]):
        for y, row in enumerate(farm["tiles"]):
            for x, tile in enumerate(row):
                if isinstance(tile, dict) and ("animal" in tile or tile.get("kind") == "PLANT"):
                    cal = project_calendar(tile, day, obs["hour"], (x, y))
                    calendars.append((seat, (x, y), cal))
    prices, inventories = {}, {}
    for d in range(day, 30):
        if d > day:
            for p in PRODUCTS:
                supply[p] -= demand[p]
            for _, _, cal in calendars:
                for p, n in cal["goods"].get(d, {}).items():
                    supply[p] += n
                supply["WHEAT"] -= cal["feed"].get(d - 1, 0)
        inventories[d] = dict(supply)
        prices[d] = {p: price(p, supply[p], obs["market"].get("params")) for p in PRODUCTS}
    return {"prices": prices, "inventories": inventories, "demand": demand, "calendars": calendars}


def labor_schedule(obs, workload):
    """当前工人已到场；可负担增员的费用由投资账另计，新工次帧可动。"""
    f = obs["farms"][obs["player"]]
    existing = len(f["hands"])
    target = existing
    cash_by_day = {}
    feasible = True
    cap = int(PARAMS["max_hands"])
    for d in range(obs["day"], 30):
        need = max(0, workload.get(d, 0))
        if d == obs["day"]:
            slots = (23 if d == 29 else 24) - obs["hour"]
            have = (1 + existing) * max(0, slots)
            extra = 0
            if need > have:
                if obs["hour"] >= 8 or slots <= 1:
                    feasible = False
                else:
                    extra = int(math.ceil((need - have) / (slots - 1)))
            target = existing + extra
            if target > cap:
                feasible = False
            cash_by_day[d] = sum(FIB[min(int(f.get("hires_today", existing)) + i, len(FIB) - 1)] for i in range(extra))
        else:
            slots = 23 if d == 29 else 24
            # 每天起始只有农夫；雇工当日h0付款、h1起能行动。
            hands = max(0, int(math.ceil(max(0, need - slots) / max(1, slots - 1))))
            if hands > cap:
                feasible = False
            cash_by_day[d] = sum(FIB[min(i, len(FIB) - 1)] for i in range(hands))
    return {"feasible": feasible, "hire_target_today": min(cap, target), "cash_by_day": cash_by_day,
            "total_cost": sum(cash_by_day.values())}


def investment_quote(obs, item, position, market_model, seed_credit=False):
    day, hour = obs["day"], obs["hour"]
    f = obs["farms"][obs["player"]]
    x, y = position
    tile = f["tiles"][y][x]
    actors = [tuple(f["farmer"])] + [tuple(p) for p in f["hands"]]
    approach = min(dist(p, position) for p in actors)
    distance = dist(position, home(position))
    build = item in ANIMALS and not (isinstance(tile, dict) and tile.get("kind") == ANIMALS[item][1] and "animal" not in tile)
    if item in ANIMALS:
        setup = (approach + (1 if tile is not None else 0) + 1) if build else 0
        # 建成后下一帧才能买；采购后的下一帧才能领，领后运到目标再放置。
        start_step = obs["step"] + setup + 2 + 2 * distance
        start_day = start_step // 24
        future = {"kind": ANIMALS[item][1], "animal": item, "placed_day": start_day, "yield_units": 0,
                  "fed_today": False, "cared_today": False, "fertilizer_available": False, "pending_care_bonus": 0}
        fixed = ANIMALS[item][0]
    else:
        if isinstance(tile, dict) and tile.get("kind") not in ("WEED",):
            return None
        setup = approach + (1 if tile is not None else 0) + 2
        start_step = obs["step"] + (0 if seed_credit else 1) + setup - 2
        start_day = start_step // 24
        future = {"kind": "PLANT", "crop": item, "planted_day": start_day, "yield_units": 0 if CROPS[item][3] else 1,
                  "watered_today": False, "consecutive_unwatered": 1, "fertilized_until_day": -1}
        fixed = 0 if seed_credit else CROPS[item][0]
    if start_day > 28 or start_step > 718:
        return None
    cal = project_calendar(future, start_day, start_step % 24, position)
    cal["work"][day] = cal["work"].get(day, 0) + setup
    gross = 0.
    for d, products in cal["goods"].items():
        for p, n in products.items():
            inventory = market_model["inventories"][d][p]
            gross += sum(price(p, inventory + k, obs["market"].get("params")) for k in range(n))
    feed_cost = sum(n * market_model["prices"][d]["WHEAT"] for d, n in cal["feed"].items())
    labor = sum(cal["work"].values())
    primary = ANIMALS[item][5] if item in ANIMALS else item
    productive_days = [d for d, products in cal["goods"].items() if products.get(primary, 0)]
    # 不能以肥料副产物掩盖主营产品到终局仍无法成熟的动物投资。
    if not productive_days:
        return None
    return {"item": item, "position": tuple(position), "build_first": build, "start_step_model": start_step,
            "first_product_day": min(productive_days), "calendar": cal, "fixed_cash": fixed,
            "gross_cash_model": gross, "feed_cost_model": feed_cost, "net_before_hiring_model": gross - fixed - feed_cost,
            "labor": labor, "score_before_hiring": (gross - fixed - feed_cost) / max(1, labor)}


def economic_plan(obs, st):
    f, private, day = obs["farms"][obs["player"]], obs["private"], obs["day"]
    own = counts(f, private)
    model = dated_market_model(obs)
    st["forecasts"] = {p: model["prices"][day][p] for p in PRODUCTS}
    st["crop_scores"] = {}
    owned = [(x, y) for y, row in enumerate(f["tiles"]) for x, t in enumerate(row) if t != "LOCKED"]
    ranked = sorted(owned, key=lambda p: (dist(p, home(p)), p[1], p[0]))
    free = [p for p in ranked if f["tiles"][p[1]][p[0]] is None or (isinstance(f["tiles"][p[1]][p[0]], dict) and f["tiles"][p[1]][p[0]].get("kind") == "WEED")]
    structures = [p for p in ranked if isinstance(f["tiles"][p[1]][p[0]], dict) and f["tiles"][p[1]][p[0]].get("kind") in ("PASTURE", "COOP") and "animal" not in f["tiles"][p[1]][p[0]]]
    workload, feed = Counter(), Counter()
    for seat, _, cal in model["calendars"]:
        if seat == obs["player"]:
            workload.update(cal["work"])
            feed.update(cal["feed"])
    builds, reserved, plant_permits = {}, set(), {}
    in_transit = {a: inventory_total(private, a) for a in ANIMALS}
    used_structures = set()
    for animal in ANIMALS:
        for _ in range(in_transit[animal]):
            site = next((p for p in structures if p not in used_structures and f["tiles"][p[1]][p[0]]["kind"] == ANIMALS[animal][1]), None)
            if site is None:
                site = next((p for p in free if p not in reserved), None)
                if site is not None:
                    builds[site] = animal
            if site is not None:
                reserved.add(site); used_structures.add(site)
                workload[day] += 2 + 2 * dist(site, home(site)) + (2 if site in builds else 0)
    base_labor = labor_schedule(obs, workload)
    feed_buffer = max(0, sum(feed.get(d, 0) for d in (day, day + 1)) - inventory_total(private, "WHEAT")) * model["prices"][day]["WHEAT"]
    cash = max(0., float(f["money"]) - feed_buffer - base_labor["total_cost"])
    seeds = Counter(private["seeds"])
    animal_orders, seed_orders, accepted = Counter(), Counter(), []
    # 四条独立提议路径：快作物、牛、羊、长周期园艺，共用报价单位和账本。
    expert_items = {"balanced": ("WHEAT", "CARROT"), "dairy": ("COW",), "fiber": ("SHEEP",),
                    "horticulture": ("TOMATO", "STRAWBERRY", "MELON")}
    possible_sites = [p for p in ranked if p in free or p in structures]
    offers = []
    for pos in possible_sites:
        if pos in reserved:
            continue
        for expert, items in expert_items.items():
            for item in items:
                if item in ANIMALS and sum(in_transit.values()):
                    continue
                if item in CROPS and (pos in structures or obs["hour"] >= 21):
                    continue
                q = investment_quote(obs, item, pos, model, seeds.get(item, 0) > 0)
                if q:
                    q["expert"] = expert
                    offers.append(q)
                    if item in CROPS:
                        st["crop_scores"][item] = max(st["crop_scores"].get(item, -1e9), q["score_before_hiring"])
    expert_scores = {e: max((q["score_before_hiring"] for q in offers if q["expert"] == e), default=-1e9) for e in expert_items}
    chosen = PARAMS["router"]
    if chosen == "adaptive":
        chosen = max(expert_scores, key=expert_scores.get)
    if chosen not in expert_items:
        chosen = "balanced"
    st["expert"] = chosen
    st["metrics"]["expert_" + chosen] += 1
    st["crop_choice"] = max(st["crop_scores"], key=st["crop_scores"].get) if st["crop_scores"] else None
    animal_admitted = False
    for q0 in sorted((q for q in offers if q["expert"] == chosen), key=lambda q: (-q["score_before_hiring"], dist(q["position"], home(q["position"])), q["position"])):
        item, pos = q0["item"], q0["position"]
        if pos in reserved or pos in plant_permits or (item in ANIMALS and animal_admitted):
            continue
        q = investment_quote(obs, item, pos, model, seeds.get(item, 0) > 0)
        next_work = workload + Counter(q["calendar"]["work"])
        labor = labor_schedule(obs, next_work)
        marginal_hires = max(0., labor["total_cost"] - base_labor["total_cost"])
        net = q["net_before_hiring_model"] - marginal_hires
        cash_need = q["fixed_cash"] + q["feed_cost_model"] + marginal_hires
        if not labor["feasible"] or net <= 0 or cash_need > cash:
            st["metrics"]["investment_budget_rejected"] += 1
            continue
        cash -= cash_need
        workload, base_labor = next_work, labor
        q["net_cash_model"] = net
        q["cash_reserved_model"] = cash_need
        accepted.append(q)
        if item in ANIMALS:
            reserved.add(pos); animal_admitted = True
            if q["build_first"]:
                builds[pos] = item
            else:
                animal_orders[item] += 1
        else:
            plant_permits[pos] = item
            if seeds.get(item, 0) > 0:
                seeds[item] -= 1
            else:
                seed_orders[item] += 1
        # 后面的报价承受已准入项目的预计新增供给，避免每块地重复享受首份稀缺价。
        for d, goods in q["calendar"]["goods"].items():
            for future_day in range(d, 30):
                for p, n in goods.items():
                    model["inventories"][future_day][p] += n
                    model["prices"][future_day][p] = price(p, model["inventories"][future_day][p], obs["market"].get("params"))
    st["metrics"]["investment_admitted"] += len(accepted)
    st["metrics"]["investment_build_only"] += sum(q["build_first"] for q in accepted)
    plan = {"counts": own, "animals": {a: own[a] + animal_orders[a] for a in ANIMALS},
            "melon_cap": 100, "strawberry_cap": 100, "crop_choice": st["crop_choice"], "demand": model["demand"],
            "build_permits": builds, "reserved_animal_sites": reserved, "plant_permits": plant_permits,
            "animal_purchases": dict(animal_orders), "seed_purchases": dict(seed_orders),
            "hire_target_today": base_labor["hire_target_today"], "planned_work": dict(workload),
            "labor_plan": base_labor, "remaining_investment_cash_model": cash, "admitted_investments": accepted,
            "expert_quote_scores": expert_scores, "in_transit_existing": in_transit}
    st["latest_investment_plan"] = plan
    return plan



def matching(weights):
    """矩形最大权匹配；虚拟列表示本步不分派，避免逐工人抢走局部最优。"""
    n = len(weights)
    if not n:
        return {}
    width = len(weights[0])
    m = width + n
    u, v, p, way = [0.] * (n + 1), [0.] * (m + 1), [0] * (m + 1), [0] * (m + 1)
    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minimum, used = [float("inf")] * (m + 1), [False] * (m + 1)
        while True:
            used[j0] = True
            i0, delta, j1 = p[j0], float("inf"), 0
            for j in range(1, m + 1):
                if used[j]:
                    continue
                w = weights[i0 - 1][j - 1] if j <= width else 0.
                current = -w - u[i0] - v[j]
                if current < minimum[j]:
                    minimum[j], way[j] = current, j0
                if minimum[j] < delta:
                    delta, j1 = minimum[j], j
            for j in range(m + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minimum[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break
    return {p[j] - 1: j - 1 for j in range(1, width + 1)
            if p[j] and weights[p[j] - 1][j - 1] > 0}


def make_tasks(obs, st, plan):
    farm = obs["farms"][obs["player"]]
    private, day, hour = obs["private"], obs["day"], obs["hour"]
    values = st["forecasts"]
    tasks = []
    owned = [(x, y) for y, row in enumerate(farm["tiles"]) for x, t in enumerate(row) if t != "LOCKED"]
    ranked = sorted(owned, key=lambda p: (dist(p, home(p)), p[1], p[0]))
    animal_total = sum(plan["counts"][a] for a in ANIMALS)
    reserve = set(plan["reserved_animal_sites"])
    in_transit = Counter({a: inventory_total(private, a) for a in ANIMALS})
    empty_structure = Counter()
    for x, y in owned:
        t = farm["tiles"][y][x]
        if isinstance(t, dict) and t.get("kind") in ("PASTURE", "COOP") and "animal" not in t:
            empty_structure[t["kind"]] += 1

    def add(pos, kind, ops, value, deadline=23, requirement=None):
        if ops and value > 0:
            tasks.append({"pos": pos, "kind": kind, "ops": ops, "value": value,
                          "deadline": deadline, "requirement": requirement or {}})

    for x, y in owned:
        tile, pos = farm["tiles"][y][x], (x, y)
        if isinstance(tile, dict) and "animal" in tile:
            a = tile["animal"]
            spec = ANIMALS[a]
            feed = not tile["fed_today"] and day < 29
            care = not tile["cared_today"] and day < 28
            fertil = tile["fertilizer_available"]
            ready = tile.get("yield_units", 0)
            ops, value = [], 0.
            if feed:
                ops.append(["FEED"])
                survival = 450 if tile.get("consecutive_unfed", 0) else 0
                value += survival + max(40, values[spec[5]] * .65) + values["FERTILIZER"]
            if care:
                ops.append(["CARE"])
                value += values[spec[5]] * PARAMS["care_weight"]
            if fertil:
                ops.append(["COLLECT_FERTILIZER"])
                value += max(15, values["FERTILIZER"])
            if ready:
                ops.append(["HARVEST"])
                value += ready * values[spec[5]]
            add(pos, "animal", ops, value, requirement={"WHEAT": 1} if feed else {})
            continue
        if isinstance(tile, dict) and tile.get("kind") in ("PASTURE", "COOP"):
            for a in ("COW", "SHEEP", "GOOSE"):
                if in_transit[a] and ANIMALS[a][1] == tile["kind"]:
                    in_transit[a] -= 1
                    add(pos, "place_animal", [["PLACE", a]], 650., requirement={a: 1})
                    break
            continue
        if isinstance(tile, dict) and tile.get("kind") == "PLANT":
            c = tile["crop"]
            seed, first, maxday, interval, limit = CROPS[c]
            age = day - tile["planted_day"]
            water, yield_now = not tile["watered_today"], tile.get("yield_units", 0)
            danger = tile.get("consecutive_unwatered", 0) >= 1 or age == 0
            fertilized = tile.get("fertilized_until_day", -1) >= day
            mature = age >= first
            ops, value, req = [], 0., {}
            if interval:
                next_production = day + 1 >= tile["planted_day"] + first and (day + 1 - tile["planted_day"] - first) % interval == 0
                within_life = age < first + interval * (limit - 1)
                need_water = water and (danger or next_production) and within_life
                need_fert = next_production and within_life and not fertilized and values[c] > values["FERTILIZER"] * .55 and day < 29
                if need_fert and inventory_total(private, "FERTILIZER") > 0:
                    ops.append(["FERTILIZE"])
                    req["FERTILIZER"] = 1
                    value += values[c]
                if need_water:
                    ops.append(["WATER"])
                    value += values[c] * (2. if danger else .8)
                if yield_now and mature:
                    ops.append(["HARVEST"])
                    value += values[c] * yield_now
                if not ops and age >= first + interval * (limit - 1) + 1 and not yield_now:
                    add(pos, "clear", [["DIG"]], 35 if day < 27 else 0)
            else:
                growth = (maxday + 1) // 2 <= age <= maxday
                need_water = water and (danger or growth) and age <= maxday
                # 一次性作物肥料只在有两次以上有效浇水收益时使用。
                use_fert = c == "MELON" and growth and age <= maxday - 1 and not fertilized and values[c] > values["FERTILIZER"] and inventory_total(private, "FERTILIZER") > 0
                if use_fert:
                    ops.append(["FERTILIZE"])
                    req["FERTILIZER"] = 1
                    value += values[c] * 1.3
                if need_water:
                    ops.append(["WATER"])
                    value += values[c] * (2.5 if danger else 1.)
                after_water = yield_now + ((2 if fertilized or use_fert else 1) if need_water and growth else 0)
                harvest = yield_now > 0 and mature and (age >= maxday or after_water >= limit or day == 29)
                if harvest:
                    ops.append(["HARVEST"])
                    value += values[c] * after_water
            deadline = 21 if danger else 22 if tile.get("max_lifespan_step", -1) == day * 24 + 24 else 23
            if day == 29:
                deadline = max(0, 20 - dist(pos, home(pos)))
                if not yield_now:
                    continue
            add(pos, "crop", ops, value, deadline, req)
            continue
        if pos in plan["build_permits"]:
            a = plan["build_permits"][pos]
            ops = [["DIG"]] if tile is not None else []
            ops.append(["BUILD_" + ANIMALS[a][1]])
            add(pos, "build", ops, 550., 20)
            continue
        if pos in reserve or day >= 28 or hour >= 21:
            continue
        choice = plan["plant_permits"].get(pos)
        if choice and private["seeds"].get(choice, 0) > 0:
            ops = [["DIG"]] if tile is not None else []
            ops += [["PLANT", choice], ["WATER"]]
            value = max(15, st["crop_scores"].get(choice, 0)) * 4
            add(pos, "plant", ops, value, 21)
    return tasks



def _identity(tile):
    if not isinstance(tile, dict):
        return (tile,)
    return tuple(tile.get(k) for k in ("kind", "crop", "planted_day", "animal", "placed_day"))


def _stage_value(op, tile, task, st):
    name = op[0]
    values = st["forecasts"]
    if isinstance(tile, dict) and tile.get("animal"):
        product = ANIMALS[tile["animal"]][5]
        if name == "FEED":
            return (450 if tile.get("consecutive_unfed", 0) else 0) + max(40, values[product] * .65) + values["FERTILIZER"]
        if name == "CARE":
            return values[product] * PARAMS["care_weight"]
    else:
        product = tile.get("crop") if isinstance(tile, dict) else None
    if name == "HARVEST":
        return max(1, tile.get("yield_units", 0)) * values[product]
    if name == "COLLECT_FERTILIZER":
        return max(15, values["FERTILIZER"])
    if name == "FERTILIZE":
        return values[product] * (1.3 if product == "MELON" else 1)
    if name == "WATER" and product:
        danger = tile.get("consecutive_unwatered", 0) >= 1 or tile.get("planted_day") == st["contract_day"]
        return values[product] * ((2 if CROPS[product][3] else 2.5) if danger else (.8 if CROPS[product][3] else 1))
    return task["value"] / max(1, len(task["ops"]))


def compile_contracts(obs, st, tasks):
    """市场沿用原始任务；仅在执行器内部将每个目标编译为有类型的阶段。"""
    day = obs["day"]
    farm = obs["farms"][obs["player"]]
    st["contract_day"] = day
    groups = []
    for task in tasks:
        pos = tuple(task["pos"])
        tile = farm["tiles"][pos[1]][pos[0]]
        stages = []
        for op in task["ops"]:
            name = op[0]
            requirement = {"WHEAT": 1} if name == "FEED" else {"FERTILIZER": 1} if name == "FERTILIZE" else {op[1]: 1} if name == "PLACE" and op[1] in ANIMALS else {}
            necessary = name in ("WATER", "FEED")
            primitive = name in ("WATER", "FEED", "CARE", "FERTILIZE", "HARVEST", "COLLECT_FERTILIZER")
            deadline = day * 24 + (23 if primitive and day < 29 else task["deadline"])
            if name == "HARVEST" and isinstance(tile, dict) and tile.get("max_lifespan_step", -1) >= 0:
                # 规则先执行单位动作再衰减，恰好寿命边界当帧仍可完整收获。
                deadline = min(deadline, max(obs["step"], tile["max_lifespan_step"]))
            stages.append({"op": list(op), "requirement": requirement,
                           "deadline": deadline, "necessary": necessary,
                           "value": _stage_value(op, tile, task, st)})
        groups.append({"target": pos, "kind": task["kind"], "fingerprint": _identity(tile),
                       "stages": stages, "source_value": task["value"]})
    return groups


def _route(obs, unit, target, stage, available):
    f, private = obs["farms"][obs["player"]], obs["private"]
    positions = [tuple(f["farmer"])] + [tuple(p) for p in f["hands"]]
    if unit >= len(positions):
        return None
    pos, inv = positions[unit], private["inventories"][unit]
    missing = next((p for p, n in stage["requirement"].items() if inv.get(p, 0) < n), None)
    if missing:
        n = stage["requirement"][missing] - inv.get(missing, 0)
        if available.get(missing, 0) < n:
            return None
        depot = min(ACCESS, key=lambda p: (dist(pos, p) + dist(p, target), p))
        action = ["PICKUP", missing, n] if pos == depot else move(pos, depot)
        return {"action": action, "cost": dist(pos, depot) + 1 + dist(depot, target) + 1,
                "reservation": {missing: n}, "phase": "resupplying"}
    return {"action": list(stage["op"]) if pos == target else move(pos, target),
            "cost": dist(pos, target) + 1, "reservation": {},
            "phase": "ready" if pos == target else "travelling"}


def _fit(obs, unit, target, stages, available):
    if not stages:
        return None
    route = _route(obs, unit, target, stages[0], available)
    if route is None:
        return None
    step = obs["step"]
    inventory = dict(obs["private"]["inventories"][unit])
    seed_inventory = dict(obs["private"]["seeds"])
    for p, n in route["reservation"].items():
        inventory[p] = inventory.get(p, 0) + n
    elapsed, accepted = route["cost"], []
    for stage in stages:
        if accepted:
            elapsed += 1
        if step + elapsed - 1 > stage["deadline"]:
            break
        if any(inventory.get(p, 0) < n for p, n in stage["requirement"].items()):
            break
        if stage["op"][0] == "PLANT":
            crop = stage["op"][1]
            if seed_inventory.get(crop, 0) < 1:
                break
            seed_inventory[crop] -= 1
        if obs["day"] == 29 and obs["hour"] + elapsed + dist(target, home(target)) + 2 > 22:
            break
        accepted.append(stage)
        for p, n in stage["requirement"].items():
            inventory[p] -= n
    if not accepted:
        return None
    necessary = [(i, s) for i, s in enumerate(accepted) if s["necessary"]]
    slack = min((s["deadline"] - (step + route["cost"] + i - 1) for i, s in necessary), default=None)
    return {"stages": accepted, "route": route, "cost": route["cost"] + len(accepted) - 1,
            "urgent": slack is not None and slack <= 0, "slack": slack}


def propose_contract(obs, unit, group, available):
    stages = group["stages"]
    by_op = {s["op"][0]: s for s in stages}
    kind, target = group["kind"], group["target"]
    if kind == "crop":
        water, fert, harvest = by_op.get("WATER"), by_op.get("FERTILIZE"), by_op.get("HARVEST")
        if water:
            ordered = [water] + ([harvest] if harvest else [])
            # 肥料已在此工人手中且肥+水都可完成，保留真正的增产前缀。
            if fert and obs["private"]["inventories"][unit].get("FERTILIZER", 0):
                enriched = _fit(obs, unit, target, [fert, water], available)
                if enriched and len(enriched["stages"]) == 2:
                    ordered = [fert] + ordered
        elif harvest:
            tile = obs["farms"][obs["player"]]["tiles"][target[1]][target[0]]
            # 一次性作物采收会销毁对象，不能承诺其后的施肥阶段。
            ordered = [harvest] + ([fert] if fert and CROPS[tile["crop"]][3] else [])
        else:
            ordered = stages
    elif kind == "animal":
        feed, care = by_op.get("FEED"), by_op.get("CARE")
        harvest, collect = by_op.get("HARVEST"), by_op.get("COLLECT_FERTILIZER")
        feed_possible = feed and _fit(obs, unit, target, [feed], available)
        ordered = ([feed] if feed_possible else []) + ([harvest] if harvest else [])
        # 护理不再挡已有产物，未喂且本合约无法喂时不花护理动作。
        if care and (feed_possible or not feed):
            ordered.append(care)
        if collect:
            ordered.append(collect)
    else:
        ordered = stages
    fitted = _fit(obs, unit, target, ordered, available)
    if not fitted:
        return None
    if kind in ("build", "plant") and len(fitted["stages"]) != len(ordered):
        return None  # 新投资必须留足建成/首次浇水时间，不能只做准备动作。
    # 有增产前缀时不可只接受施肥而截掉必要 WATER。
    if fitted["stages"][0]["op"][0] == "FERTILIZE" and "WATER" in by_op and not any(s["op"][0] == "WATER" for s in fitted["stages"]):
        fitted = _fit(obs, unit, target, [by_op["WATER"]], available)
        if not fitted:
            return None
    return {**fitted, "target": target, "kind": kind, "fingerprint": group["fingerprint"]}


def _receipt_observation(obs, unit, target):
    f = obs["farms"][obs["player"]]
    positions = [tuple(f["farmer"])] + [tuple(p) for p in f["hands"]]
    t = f["tiles"][target[1]][target[0]]
    return {"step": obs["step"], "day": obs["day"],
            "position": positions[unit] if unit < len(positions) else None,
            "inventory": dict(obs["private"]["inventories"][unit]) if unit < len(positions) else {},
            "tile": dict(t) if isinstance(t, dict) else t}


def _receipt_result(receipt, now):
    before, action = receipt["before"], receipt["action"]
    if now["step"] != before["step"] + 1:
        return "unknown"
    bt, nt, op = before["tile"], now["tile"], action[0]
    same = _identity(bt) == _identity(nt)
    cross_day = now["day"] != before["day"]
    if op in ("WATER", "FEED"):
        if not same or not isinstance(nt, dict):
            return "failed"
        flag, counter = ("watered_today", "consecutive_unwatered") if op == "WATER" else ("fed_today", "consecutive_unfed")
        eligible = not bt.get(flag) and (op != "FEED" or before["inventory"].get("WHEAT", 0) >= 1)
        return "confirmed" if eligible and (nt.get(counter) == 0 if cross_day else nt.get(flag)) else "failed"
    if cross_day:
        return "unknown"
    inv, oldinv = now["inventory"], before["inventory"]
    if op in ("NORTH", "SOUTH", "EAST", "WEST"):
        dx, dy = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}[op]
        pos = before["position"]
        success = now["position"] == (pos[0] + dx, pos[1] + dy)
    elif op == "PICKUP":
        success = inv.get(action[1], 0) - oldinv.get(action[1], 0) >= action[2]
    elif op == "CARE":
        success = same and isinstance(nt, dict) and nt.get("cared_today") and not bt.get("cared_today")
    elif op == "FERTILIZE":
        success = same and isinstance(nt, dict) and nt.get("fertilized_until_day", -1) >= before["day"] + 2 and oldinv.get("FERTILIZER", 0) - inv.get("FERTILIZER", 0) == 1
    elif op == "HARVEST":
        product = bt.get("crop") or ANIMALS[bt["animal"]][5]
        success = bt.get("yield_units", 0) > 0 and inv.get(product, 0) - oldinv.get(product, 0) == bt["yield_units"]
    elif op == "COLLECT_FERTILIZER":
        success = same and isinstance(nt, dict) and bt.get("fertilizer_available") and not nt.get("fertilizer_available") and inv.get("FERTILIZER", 0) - oldinv.get("FERTILIZER", 0) == 1
    elif op == "DIG":
        success = bt is not None and nt is None
    elif op.startswith("BUILD_"):
        success = bt is None and isinstance(nt, dict) and nt.get("kind") == op[6:]
    elif op == "PLANT":
        success = bt is None and isinstance(nt, dict) and nt.get("crop") == action[1] and nt.get("planted_day") == before["day"]
    elif op == "PLACE" and action[1] in ANIMALS:
        success = isinstance(nt, dict) and nt.get("animal") == action[1] and oldinv.get(action[1], 0) - inv.get(action[1], 0) == 1
    else:
        return "unknown"
    return "confirmed" if success else "failed"


def confirm_execution(st, obs):
    contracts = st.setdefault("contracts", {})
    events = st.setdefault("contract_events", [])
    for unit, contract in list(contracts.items()):
        receipt = contract.get("receipt")
        now = _receipt_observation(obs, unit, contract["target"])
        if receipt:
            outcome = _receipt_result(receipt, now)
            op = receipt["action"][0]
            st["metrics"]["receipt_" + outcome] += 1
            events.append({"step": obs["step"], "unit": unit, "target": contract["target"], "action": receipt["action"], "outcome": outcome})
            if outcome != "confirmed":
                del contracts[unit]
                continue
            if op not in ("NORTH", "SOUTH", "EAST", "WEST", "PICKUP"):
                if receipt["action"] == contract["stages"][0]["op"]:
                    contract["stages"].pop(0)
                    st["metrics"]["confirmed_" + op] += 1
                if op == "HARVEST" and isinstance(receipt["before"]["tile"], dict) and receipt["before"]["tile"].get("kind") == "PLANT" and not CROPS[receipt["before"]["tile"]["crop"]][3]:
                    st["metrics"]["terminal_harvest_stages_pruned"] += len(contract["stages"])
                    contract["stages"] = []
                contract["fingerprint"] = _identity(now["tile"])
            contract["receipt"] = None
            contract["phase"] = "ready"
        if not contract["stages"]:
            st["metrics"]["contract_completed"] += 1
            del contracts[unit]
        elif now["day"] != contract["day"] or now["position"] is None or obs["step"] > contract["expires"]:
            st["metrics"]["contract_expired"] += 1
            del contracts[unit]
        elif _identity(now["tile"]) != contract["fingerprint"]:
            st["metrics"]["contract_target_changed"] += 1
            del contracts[unit]
    # 日志有界；计数器保留全局累计。它不是经验回放或策略查表。
    if len(events) > 4096:
        del events[:-4096]


def shared_task_urgency(obs, units, groups, available):
    """目标共用最快可行工人的必要阶段余量；路远不会获得额外紧迫奖励。"""
    result = {}
    for group in groups:
        slacks = []
        for unit in units:
            offer = propose_contract(obs, unit, group, available)
            if offer and offer["slack"] is not None:
                slacks.append(offer["slack"])
        result[group["target"]] = bool(slacks) and max(slacks) <= 0
    return result


def allocate(obs, st, plan, tasks):
    farm, private = obs["farms"][obs["player"]], obs["private"]
    positions = [tuple(farm["farmer"])] + [tuple(p) for p in farm["hands"]]
    actions = [["PASS"] for _ in positions]
    available = dict(private["shed"])
    capacity = 100 - sum(available.values())
    seeds = dict(private["seeds"])
    groups = compile_contracts(obs, st, tasks)
    contracts = st.setdefault("contracts", {})
    occupied, assigned = set(), set()
    day, hour = obs["day"], obs["hour"]
    animal_count = sum(plan["counts"][a] for a in ANIMALS)

    def cancel(unit, why):
        if unit in contracts:
            del contracts[unit]
            st["metrics"]["contract_" + why] += 1

    def accept(unit, offer, existing=False):
        nonlocal capacity
        route = _route(obs, unit, offer["target"], offer["stages"][0], available)
        if route is None:
            return False
        action = route["action"]
        seed_demand = Counter(s["op"][1] for s in offer["stages"] if s["op"][0] == "PLANT")
        for crop, n in seed_demand.items():
            if seeds.get(crop, 0) < n:
                return False
        for crop, n in seed_demand.items():
            seeds[crop] -= n
        # 路上承诺同样预留，不让后来的合同反复抢最后一份材料。
        for p, n in route["reservation"].items():
            available[p] -= n
        # 保守沿用 R3：不把尚未按工人编号执行的 PICKUP 当作已释放仓容。
        if not existing:
            contract = {"owner": unit, "target": offer["target"], "kind": offer["kind"],
                        "fingerprint": offer["fingerprint"], "stages": [dict(s) for s in offer["stages"]],
                        "day": day, "accepted_step": obs["step"], "expires": obs["step"] + offer["cost"]}
            contracts[unit] = contract
            st["metrics"]["contract_accepted"] += 1
        else:
            contract = contracts[unit]
        contract["phase"] = "awaiting_receipt"
        contract["route_phase"] = route["phase"]
        contract["receipt"] = {"action": list(action), "before": _receipt_observation(obs, unit, offer["target"])}
        actions[unit] = action
        assigned.add(unit)
        occupied.add(offer["target"])
        st["metrics"]["dispatched_" + action[0]] += 1
        return True

    # 原终局单品返仓逻辑保留；此轮不加入 DROP。
    for unit, pos in enumerate(positions):
        inv = private["inventories"][unit]
        final_return = day == 29 and (hour + dist(pos, home(pos)) >= 19 or hour >= 20)
        if final_return and any(inv.get(p, 0) for p in PRODUCTS):
            cancel(unit, "terminal_return")
            if pos not in ACCESS:
                actions[unit] = move(pos, home(pos))
            elif capacity > 0:
                item = max((p for p in PRODUCTS if inv.get(p, 0)), key=lambda p: inv[p] * st["forecasts"][p])
                n = min(inv[item], capacity)
                actions[unit] = ["PLACE", item, n]
                capacity -= n
            assigned.add(unit)

    # 在编号循环之前登记全部可执行 owner，不能让高编号的承诺暂时隐身。
    potential_units = [u for u in range(len(positions)) if u not in assigned]
    urgency = shared_task_urgency(obs, potential_units, groups, available)
    covered = set()
    for unit, contract in contracts.items():
        if unit in assigned:
            continue
        fit = _fit(obs, unit, contract["target"], contract["stages"], available)
        if fit and len(fit["stages"]) == len(contract["stages"]) and not (urgency.get(contract["target"], False) and fit["slack"] is None):
            covered.add(contract["target"])
    for unit, contract in sorted(list(contracts.items())):
        if unit in assigned:
            continue
        fitted = _fit(obs, unit, contract["target"], contract["stages"], available)
        if fitted is None or len(fitted["stages"]) != len(contract["stages"]):
            cancel(unit, "infeasible")
            continue
        if urgency.get(contract["target"], False) and fitted["slack"] is None:
            cancel(unit, "urgent_goal_not_covered")
            continue
        other_urgent = any(g["target"] != contract["target"] and g["target"] not in covered
                           and urgency.get(g["target"], False)
                           and (o := propose_contract(obs, unit, g, available)) and o["slack"] is not None for g in groups)
        if other_urgent and not urgency.get(contract["target"], False):
            cancel(unit, "urgent_preempted")
            continue
        if contract["target"] in occupied or not accept(unit, {**fitted, **contract}, existing=True):
            cancel(unit, "resource_unavailable")

    actors = [u for u in range(len(positions)) if u not in assigned]
    free_groups = [g for g in groups if g["target"] not in occupied]
    offers, weights = {}, []
    # owner 分配完成后，以剩余可派遣工人重新核对每个待分配目标的共享紧迫性。
    urgency = shared_task_urgency(obs, actors, free_groups, available)
    # 最后可行的保活窗口采用词典序优先，优先级尺度由当帧价值上界推导。
    urgent_bonus = 1 + 1.15 * sum(max(0, s["value"]) for g in free_groups for s in g["stages"])
    for u in actors:
        row = []
        for j, group in enumerate(free_groups):
            offer = propose_contract(obs, u, group, available)
            if offer:
                weight = sum(s["value"] for s in offer["stages"]) / max(1, offer["cost"])
                if positions[u] == group["target"]:
                    weight *= 1.15
                row.append(weight + (urgent_bonus if urgency.get(group["target"], False) and offer["slack"] is not None else 0))
                offers[u, j] = offer
            else:
                row.append(-1e6)
        weights.append(row)
    for i, j in matching(weights).items() if free_groups else []:
        u = actors[i]
        # 匹配后的资源额度可能已被先前合同使用，重新求可行前缀。
        offer = propose_contract(obs, u, free_groups[j], available)
        if offer and offer["target"] not in occupied:
            accept(u, offer)

    # 无合约的空闲工人才执行原普通产品返仓；不再为无目标的材料盲目领货。
    for u, pos in enumerate(positions):
        if u in assigned:
            continue
        inv = private["inventories"][u]
        cargo = {p: n for p, n in inv.items() if p in PRODUCTS and n > 0 and
                 (p not in ("WHEAT", "FERTILIZER") or n > (4 if p == "WHEAT" and animal_count else 2))}
        carry_value = sum(n * st["forecasts"].get(p, 0) for p, n in cargo.items())
        if pos in ACCESS and cargo and capacity > 0:
            item = max(cargo, key=lambda p: cargo[p] * st["forecasts"].get(p, 0))
            keep = 4 if item == "WHEAT" and animal_count and day < 29 else 2 if item == "FERTILIZER" and day < 28 else 0
            n = min(inv[item] - keep, capacity)
            if n > 0:
                actions[u] = ["PLACE", item, n]
                capacity -= n
        elif carry_value > 1800 and dist(pos, home(pos)) <= 3 and hour < 19:
            actions[u] = move(pos, home(pos))
    # 全部已接受合同预留必要材料后，才扩充真实取粮；不借其他合同的预约。
    if day < 29:
        for u, action in enumerate(actions):
            if action[0] != "PICKUP" or action[1] != "WHEAT":
                continue
            extra = min(max(0, 4 - action[2]), max(0, available.get("WHEAT", 0)))
            if extra:
                action[2] += extra
                available["WHEAT"] -= extra
                if u in contracts and contracts[u].get("receipt"):
                    contracts[u]["receipt"]["action"] = list(action)
                st["metrics"]["batch_feed_extra_requested"] += extra
    st["metrics"]["unit_commands"] += len(actions)
    st["metrics"]["pass"] += sum(a[0] == "PASS" for a in actions)
    return actions


def market_orders(obs, st, plan, tasks, actions):
    farm, private = obs["farms"][obs["player"]], obs["private"]
    shed = dict(private["shed"])
    # 逐单位动作后的可售库存与仓容可确定，不借用尚未成交的现金。
    for u, action in enumerate(actions):
        inv = private["inventories"][u]
        if action[0] == "PICKUP":
            shed[action[1]] = max(0, shed.get(action[1], 0) - action[2])
        elif action[0] == "PLACE" and action[1] in PRODUCTS:
            shed[action[1]] = shed.get(action[1], 0) + min(action[2], inv.get(action[1], 0))
    cash = float(farm["money"])
    day, hour = obs["day"], obs["hour"]
    own = plan["counts"]
    n_animals = sum(own[a] for a in ANIMALS)
    orders = []
    feed_remaining = sum(isinstance(t, dict) and "animal" in t and not t["fed_today"]
                         for row in farm["tiles"] for t in row)
    wheat_reserve = max(0, feed_remaining + n_animals // 2 - sum(i.get("WHEAT", 0) for i in private["inventories"])) if day < 29 else 0
    fertil_reserve = min(12, sum(t["requirement"].get("FERTILIZER", 0) for t in tasks) + 2) if day < 28 else 0
    for p in sorted(PRODUCTS, key=lambda p: shed.get(p, 0) * obs["market"]["prices"].get(p, 0), reverse=True):
        keep = wheat_reserve if p == "WHEAT" else fertil_reserve if p == "FERTILIZER" else 0
        n = max(0, shed.get(p, 0) - keep)
        if n:
            orders.append(["SELL", p, n])
            shed[p] -= n
    if day == 29 and hour >= 18:
        return orders[:10]

    def fixed_order(order, cost):
        nonlocal cash
        if cost <= cash and len(orders) < 10:
            orders.append(order)
            cash -= cost
            return True
        return False

    # 计划只计次帧起的新工容量；本帧市场落实同一雇工目标。
    desired_hands = int(plan["hire_target_today"])
    if hour < 8:
        for hire in range(len(farm["hands"]), desired_hands):
            ordinal = int(farm.get("hires_today", len(farm["hands"]))) + hire - len(farm["hands"])
            if not fixed_order(["HIRE"], FIB[min(ordinal, len(FIB) - 1)]):
                break
    # 饲料按逐单位递增报价和10%的可见价格余量保守预算。
    wheat_have = inventory_total(private, "WHEAT")
    feed_target = n_animals + max(3, n_animals // 2)
    if day < 29 and n_animals and wheat_have < feed_target:
        n = min(16, feed_target - wheat_have)
        supply = obs["market"]["inventory"]["WHEAT"]
        estimate = sum(price("WHEAT", supply - k - 1, obs["market"].get("params")) for k in range(n))
        if estimate * 1.10 <= cash and sum(shed.values()) + n <= 100:
            fixed_order(["BUY_PRODUCT", "WHEAT", n], estimate * 1.10)
            shed["WHEAT"] = shed.get("WHEAT", 0) + n
    # 准入许可已经共享扣账；建筑真实存在、且没有旧在途时才可能出现动物订单。
    for animal, quantity in plan["animal_purchases"].items():
        n = min(100, max(0, int(quantity)))
        if n and day < 29 and sum(shed.values()) + n <= 100:
            if fixed_order(["BUY_ANIMAL", animal, n], ANIMALS[animal][0] * n):
                shed[animal] = shed.get(animal, 0) + n
    for crop, quantity in plan["seed_purchases"].items():
        n = min(100, max(0, int(quantity)))
        if n:
            fixed_order(["BUY_SEED", crop, n], CROPS[crop][0] * n)
    # 当前原型只在已拥有地块分配预算，不发出未经投资报价的新土地购买。
    return orders[:10]



def diagnostics():
    return {str(seat): {"metrics": dict(st["metrics"]), "daily": st["daily"],
                        "purchase_misses": st["procurement"],
                        "active_contracts": st.get("contracts", {}),
                        "contract_events": st.get("contract_events", [])}
            for seat, st in _STATES.items()}


def agent(observation, configuration=None):
    # 异常直接交给评测器记录；不把实现错误静默掩盖成全员PASS。
    seat, step = int(observation["player"]), int(observation["step"])
    st = _STATES.get(seat)
    if st is None or step <= st["last_step"]:
        st = new_state(observation)
        _STATES[seat] = st
    confirm_execution(st, observation)
    confirm_orders(st, observation)
    plan = economic_plan(observation, st)
    tasks = make_tasks(observation, st, plan)
    actions = allocate(observation, st, plan, tasks)
    orders = market_orders(observation, st, plan, tasks, actions)
    if observation["day"] != st["last_day"]:
        st["daily"].append({**summary(observation), "expert": st["expert"],
                            "crop_choice": st["crop_choice"], "tasks": len(tasks),
                            "metrics": dict(st["metrics"])})
    st.update(last_step=step, last_day=observation["day"], previous=summary(observation),
              issued=orders, unit_actions=actions)
    return {"farmer": actions[0], "hands": actions[1:], "market": orders}
