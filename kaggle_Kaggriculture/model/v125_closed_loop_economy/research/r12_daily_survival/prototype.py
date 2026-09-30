"""V125：由可见状态生成经营目标、任务和动作，所有完成以观测确认。"""
from __future__ import annotations

import math
from collections import Counter


CANDIDATE_ID = "V125-R12-PROTOTYPE"
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


def economic_plan(obs, st):
    day = obs["day"]
    f = obs["farms"][obs["player"]]
    own, other = counts(f, obs["private"]), counts(obs["farms"][1 - obs["player"]])
    demand = {p: 1. for p in PRODUCTS}
    demand["FERTILIZER"] = 0.
    for shop in obs["town"].get("unlocked_shops", []):
        products = SHOPS.get(shop, ())
        for p in products:
            demand[p] += 12 if len(products) == 1 else 6
    production = Counter()
    for c in CROPS:
        first, interval = CROPS[c][1], CROPS[c][3]
        rate = 2 / interval if interval else (4.5 / (CROPS[c][2] + 1))
        production[c] = (own[c] + other[c]) * rate
    for a, spec in ANIMALS.items():
        production[spec[5]] += (own[a] + other[a]) * (1 + spec[3]) / spec[3]
        production["FERTILIZER"] += own[a] + other[a]
    production["WHEAT"] -= sum(own[a] + other[a] for a in ANIMALS)
    forecasts = {}
    for p in PRODUCTS:
        horizon = min(PARAMS["forecast_days"], max(0, 29 - day))
        supply = obs["market"]["inventory"].get(p, 10000)
        projected = supply + horizon * (production[p] - demand[p])
        today = obs["market"]["prices"].get(p, MARKET[p][0])
        future = price(p, projected, obs["market"].get("params"))
        forecasts[p] = max(.2 * MARKET[p][0], .45 * today + .55 * future)
    profiles = {"balanced": {"COW": 8, "SHEEP": 6, "GOOSE": 0},
                "dairy": {"COW": 14, "SHEEP": 3, "GOOSE": 0},
                "fiber": {"COW": 5, "SHEEP": 13, "GOOSE": 0},
                "horticulture": {"COW": 4, "SHEEP": 3, "GOOSE": 0}}
    scores = {"balanced": (forecasts["MILK"] * 1.1 + forecasts["WOOL"]) / 2,
              "dairy": forecasts["MILK"] * 1.15,
              "fiber": forecasts["WOOL"],
              "horticulture": max(forecasts["CARROT"] * 2., forecasts["STRAWBERRY"])}
    chosen = PARAMS["router"]
    if chosen == "adaptive":
        chosen = "balanced" if day < 3 else max(scores, key=scores.get)
    cap = profiles.get(chosen, profiles["balanced"])
    st["metrics"]["expert_" + chosen] += 1
    target_animals = {}
    progress = min(1., .25 + day / 16)
    for a in ANIMALS:
        target = int(round(cap[a] * progress))
        if day == 0:
            target = 2 if a in ("COW", "SHEEP") else 0
        if 29 - day < ANIMALS[a][2] + 5:
            target = own[a]
        target_animals[a] = max(own[a], target)
    # 草莓/甜瓜以有限目标控制一次投资；快速作物按净回款率补空地。
    melon_cap = 7 if day < 3 else 10 if day < 14 else 0
    strawberry_cap = 0 if day < 4 else min(24, 2 * (day - 3) + 4)
    if forecasts["STRAWBERRY"] < 45:
        strawberry_cap = min(strawberry_cap, 8)
    if day > 18:
        strawberry_cap = 0
    # 选择所需资源而非按种子名称固定优先级。未成熟的资产仍计算占用。
    crop_scores = {}
    for c, spec in CROPS.items():
        seed, first, maxday, interval, maxyield = spec
        if day + first > 28:
            continue
        operations = (maxday + 4) if not interval else (first / 2 + 9)
        yield_total = 4 if c == "WHEAT" else 3 if c == "CARROT" else 6 if c == "MELON" else 7
        crop_scores[c] = (forecasts[c] * yield_total - seed) / operations
        if c == "MELON" and (own[c] >= melon_cap or day > 15):
            crop_scores[c] = -1
        if c == "STRAWBERRY" and own[c] >= strawberry_cap:
            crop_scores[c] = -1
        if c == "TOMATO" and own[c] >= 12:
            crop_scores[c] = -1
    choice = max(crop_scores, key=crop_scores.get) if crop_scores else None
    st.update(expert=chosen, forecasts=forecasts, crop_choice=choice, crop_scores=crop_scores)
    return {"animals": target_animals, "melon_cap": melon_cap, "strawberry_cap": strawberry_cap,
            "crop_choice": choice, "demand": demand, "counts": own}


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
    reserve = set(ranked[:max(4, animal_total)])
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
        if pos in reserve and sum(in_transit.values()) > sum(empty_structure.values()):
            a = next((a for a in ("COW", "SHEEP", "GOOSE") if in_transit[a] > 0), None)
            if a:
                ops = [["DIG"]] if tile is not None else []
                ops += [["BUILD_" + ANIMALS[a][1]]]
                empty_structure[ANIMALS[a][1]] += 1
                add(pos, "build", ops, 550., 20)
                continue
        if pos in reserve or day >= 28 or hour >= 21:
            continue
        choice = st["crop_choice"]
        if choice and private["seeds"].get(choice, 0) > 0:
            ops = [["DIG"]] if tile is not None else []
            ops += [["PLANT", choice], ["WATER"]]
            value = max(15, st["crop_scores"].get(choice, 0)) * 4
            add(pos, "plant", ops, value, 21)
        elif isinstance(tile, dict) and tile.get("kind") == "WEED" and day < 27:
            add(pos, "clear", [["DIG"]], 15., 22)
    return tasks


def allocate(obs, st, plan, tasks):
    farm, private = obs["farms"][obs["player"]], obs["private"]
    positions = [tuple(farm["farmer"])] + [tuple(p) for p in farm["hands"]]
    invs = private["inventories"]
    actions = [["PASS"] for _ in positions]
    available = dict(private["shed"])
    capacity = 100 - sum(available.values())
    actors, weights, edges = [], [], {}
    day, hour = obs["day"], obs["hour"]
    animal_count = sum(plan["counts"][a] for a in ANIMALS)
    for u, pos in enumerate(positions):
        inv = invs[u] if u < len(invs) else {}
        cargo = {p: n for p, n in inv.items() if p in PRODUCTS and n > 0 and
                 (p not in ("WHEAT", "FERTILIZER") or n > (4 if p == "WHEAT" and animal_count else 2))}
        carry_value = sum(n * st["forecasts"].get(p, 0) for p, n in cargo.items())
        final_return = day == 29 and (hour + dist(pos, home(pos)) >= 19 or hour >= 20)
        if final_return and any(inv.get(p, 0) for p in PRODUCTS):
            if pos not in ACCESS:
                actions[u] = move(pos, home(pos))
            elif capacity > 0:
                item = max((p for p in PRODUCTS if inv.get(p, 0)), key=lambda p: inv[p] * st["forecasts"][p])
                n = min(inv[item], capacity)
                actions[u] = ["PLACE", item, n]
                capacity -= n
            continue
        if pos in ACCESS and cargo and capacity > 0:
            item = max(cargo, key=lambda p: cargo[p] * st["forecasts"].get(p, 0))
            keep = 4 if item == "WHEAT" and animal_count and day < 29 else 2 if item == "FERTILIZER" and day < 28 else 0
            n = min(inv[item] - keep, capacity)
            if n > 0:
                actions[u] = ["PLACE", item, n]
                capacity -= n
                continue
        if day < 29 and pos in ACCESS:
            # 动物由最近的工人逐只领取，仓库余额在同帧内原子预留。
            a = next((a for a in ANIMALS if available.get(a, 0) and not any(inv.get(k, 0) for k in ANIMALS)), None)
            if a:
                actions[u] = ["PICKUP", a, 1]
                available[a] -= 1
                continue
            if inv.get("WHEAT", 0) == 0 and animal_count > 0 and available.get("WHEAT", 0) > 0 and u < max(2, math.ceil(animal_count / 3)):
                n = min(4, available["WHEAT"])
                actions[u] = ["PICKUP", "WHEAT", n]
                available["WHEAT"] -= n
                continue
            if inv.get("FERTILIZER", 0) == 0 and available.get("FERTILIZER", 0) > 0 and any(t["requirement"].get("FERTILIZER") for t in tasks):
                n = min(2, available["FERTILIZER"])
                actions[u] = ["PICKUP", "FERTILIZER", n]
                available["FERTILIZER"] -= n
                continue
        if carry_value > 1800 and dist(pos, home(pos)) <= 3 and hour < 19:
            actions[u] = move(pos, home(pos))
            continue
        row = []
        for j, task in enumerate(tasks):
            required = task["requirement"]
            missing = next((p for p, n in required.items() if inv.get(p, 0) < n), None)
            target, extra = task["pos"], 0
            if missing:
                if available.get(missing, 0) < 1:
                    row.append(-1e6)
                    continue
                depot = min(ACCESS, key=lambda h: dist(pos, h) + dist(h, target))
                travel = dist(pos, depot) + dist(depot, target)
                extra = 1
                action = ["PICKUP", missing, min(4 if missing == "WHEAT" else 1, available[missing])] if pos == depot else move(pos, depot)
            else:
                travel = dist(pos, target)
                action = task["ops"][0] if pos == target else move(pos, target)
            duration = travel + extra + len(task["ops"])
            if hour + duration > task["deadline"] + 1:
                row.append(-1e6)
                continue
            if day == 29 and hour + duration + dist(target, home(target)) + 2 > 22:
                row.append(-1e6)
                continue
            # 自动日终入仓使普通日无需每条链返仓；终局必须计实际运回成本。
            return_cost = dist(target, home(target)) + 1 if day == 29 else 0
            denom = 1 + travel if PARAMS["task_cost"] == "distance" else max(1, duration + return_cost)
            weight = task["value"] / denom
            if pos == target:
                weight *= 1.15
            row.append(weight)
            edges[u, j] = action
        actors.append(u)
        weights.append(row)
    assignment = matching(weights) if tasks else {}
    seed_remaining = dict(private["seeds"])
    for i, j in assignment.items():
        u = actors[i]
        action = edges[u, j]
        if action[0] == "PLANT":
            c = action[1]
            if seed_remaining.get(c, 0) < 1:
                continue
            seed_remaining[c] -= 1
        if action[0] == "PICKUP":
            p = action[1]
            n = min(action[2], available.get(p, 0))
            if n <= 0:
                continue
            action = ["PICKUP", p, n]
            available[p] -= n
        actions[u] = action
        st["metrics"]["task_" + tasks[j]["kind"]] += 1
    actions, survival_receipt = r12_select(obs, actions, st, r12_check)
    st.setdefault("survival_receipts", []).append(survival_receipt)
    st["metrics"][survival_receipt["status"]] += 1
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

    # 每日已雇人数从真实状态读取；廉价劳力先于扩张。
    pending_tasks = len(tasks)
    desired_hands = min(PARAMS["max_hands"], max(4, math.ceil((pending_tasks * 2.4 + n_animals * 4) / 20)))
    if day <= 2:
        desired_hands = max(5, desired_hands)
    if day == 29:
        desired_hands = min(PARAMS["max_hands"], max(5, math.ceil(pending_tasks / 3)))
    if hour < 8:
        for hire in range(len(farm["hands"]), desired_hands):
            if not fixed_order(["HIRE"], FIB[min(hire, len(FIB) - 1)]):
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
    # 只按当前资产缺口采购，一次买一只，下一帧由总资产重新确认。
    if day < 21 and hour <= 18:
        for a in sorted(ANIMALS, key=lambda a: -st["forecasts"][ANIMALS[a][5]]):
            if own[a] < plan["animals"][a] and sum(shed.values()) < 90 and cash > ANIMALS[a][0] + 180:
                if fixed_order(["BUY_ANIMAL", a, 1], ANIMALS[a][0]):
                    shed[a] = shed.get(a, 0) + 1
    choice = st["crop_choice"]
    if choice and day < 28 and hour < 20:
        available_seeds = private["seeds"].get(choice, 0)
        target = min(6, max(2, sum(t["kind"] in ("plant", "clear") for t in tasks)))
        if choice == "MELON":
            target = min(target, max(0, plan["melon_cap"] - own[choice]))
        if choice == "STRAWBERRY":
            target = min(target, max(0, plan["strawberry_cap"] - own[choice]))
        n = min(max(0, target - available_seeds), max(0, int((cash - 100) / CROPS[choice][0])))
        if n:
            fixed_order(["BUY_SEED", choice, n], n * CROPS[choice][0])
    occupied = sum(isinstance(t, dict) for row in farm["tiles"] for t in row if t != "LOCKED")
    lands = len(farm["unlocked_quadrants"])
    if lands < 3 and 3 <= day < 19 and occupied >= lands * 25 - 8 and cash > (1000, 2000, 4000)[lands - 1] + 600:
        fixed_order(["BUY_LAND"], (1000, 2000, 4000)[lands - 1])
    return orders[:10]


def agent(observation, configuration=None):
    # 异常直接交给评测器记录；不把实现错误静默掩盖成全员PASS。
    seat, step = int(observation["player"]), int(observation["step"])
    st = _STATES.get(seat)
    if st is None or step <= st["last_step"]:
        st = new_state(observation)
        _STATES[seat] = st
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


def diagnostics():
    return {str(seat): {"metrics": dict(st["metrics"]), "daily": st["daily"],
                        "purchase_misses": st["procurement"], "survival_receipts": st.get("survival_receipts", [])}
            for seat, st in _STATES.items()}


from copy import deepcopy

R12_MOVES = {'NORTH': (0, -1), 'SOUTH': (0, 1), 'WEST': (-1, 0), 'EAST': (1, 0)}
R12_CROPS = {'WHEAT': (2, 4, False), 'CARROT': (2, 3, False),
             'TOMATO': (8, 8, True), 'STRAWBERRY': (10, 10, True), 'MELON': (10, 12, False)}


def r12_problem(obs):
    farm = obs['farms'][obs['player']]
    targets = []
    end = obs['day'] * 24 + 23
    for y, row in enumerate(farm['tiles']):
        for x, tile in enumerate(row):
            if not isinstance(tile, dict) or tile.get('kind') != 'PLANT':
                continue
            if tile['watered_today'] or tile['consecutive_unwatered'] < 1:
                continue
            life = tile['max_lifespan_step']
            deadline = min(end, life) if life >= 0 else end
            targets.append({'pos': [x, y], 'crop': tile['crop'], 'planted_day': tile['planted_day'],
                            'deadline': deadline})
    return {'step': obs['step'], 'end': end, 'board': len(farm['tiles']),
            'positions': deepcopy([farm['farmer']] + farm['hands']), 'targets': targets}


def r12_project(obs, actions):
    """仅投影单位动作后、市场与衰败前的坐标和危险植物；原子播种按官方规则。"""
    projected = deepcopy(obs)
    farm = projected['farms'][projected['player']]
    positions = [farm['farmer']] + farm['hands']
    seeds = projected['private']['seeds']
    day = projected['day']
    demand = {}
    for action in actions:
        if action and action[0] == 'PLANT' and len(action) >= 2:
            demand[action[1]] = demand.get(action[1], 0) + 1
    blocked = {c for c, n in demand.items() if n > seeds.get(c, 0)}
    for uid, action in enumerate(actions[:len(positions)]):
        if not action:
            continue
        op = action[0]
        x, y = positions[uid]
        if op in R12_MOVES:
            dx, dy = R12_MOVES[op]
            if 0 <= x + dx < len(farm['tiles']) and 0 <= y + dy < len(farm['tiles']):
                positions[uid][:] = [x + dx, y + dy]
            continue
        tile = farm['tiles'][y][x]
        if tile == 'LOCKED':
            continue
        if op == 'DIG':
            if not isinstance(tile, dict) or 'animal' not in tile:
                farm['tiles'][y][x] = None
        elif op == 'PLANT' and len(action) >= 2 and tile is None:
            crop = action[1]
            if crop in R12_CROPS and crop not in blocked and seeds.get(crop, 0) > 0:
                seeds[crop] -= 1
                _, maxday, ongoing = R12_CROPS[crop]
                farm['tiles'][y][x] = {'kind': 'PLANT', 'crop': crop, 'planted_day': day,
                    'watered_today': False, 'consecutive_unwatered': 1, 'yield_units': 0,
                    'max_lifespan_step': -1 if ongoing else (day + maxday + 1) * 24,
                    'fertilized_until_day': -1}
        elif op.startswith('BUILD_') and tile is None and op in ('BUILD_COOP', 'BUILD_PASTURE'):
            farm['tiles'][y][x] = {'kind': op[6:]}
        elif isinstance(tile, dict) and tile.get('kind') == 'PLANT':
            first, maxday, ongoing = R12_CROPS[tile['crop']]
            if op == 'WATER' and not tile['watered_today']:
                tile['watered_today'] = True
                if not ongoing and (maxday + 1) // 2 <= day - tile['planted_day'] <= maxday:
                    # 只需判断产物是否为正；实际产量不是本投影的承诺。
                    tile['yield_units'] = max(1, tile.get('yield_units', 0))
            elif op == 'HARVEST' and tile.get('yield_units', 0) > 0 and day - tile['planted_day'] >= first:
                tile['yield_units'] = 0
                if not ongoing:
                    farm['tiles'][y][x] = None
    projected['step'] += 1
    projected['hour'] += 1
    return r12_problem(projected)


def r12_schedule(problem):
    """最早截止、最早完工的确定性插入；失败只表示未找到证书。"""
    states = [{'pos': list(p), 'clock': problem['step'], 'route': []} for p in problem['positions']]
    pending = deepcopy(problem['targets'])
    while pending:
        choices = []
        for index, target in enumerate(pending):
            for uid, state in enumerate(states):
                length = abs(state['pos'][0] - target['pos'][0]) + abs(state['pos'][1] - target['pos'][1])
                at = state['clock'] + length
                if at <= min(problem['end'], target['deadline']):
                    choices.append((target['deadline'], at, length, target['pos'][1], target['pos'][0], uid, index))
        if not choices:
            return None
        *_, uid, index = min(choices)
        target = pending.pop(index)
        state = states[uid]
        while state['pos'] != target['pos']:
            dx = target['pos'][0] - state['pos'][0]
            dy = target['pos'][1] - state['pos'][1]
            op = 'EAST' if dx > 0 else 'WEST' if dx < 0 else 'SOUTH' if dy > 0 else 'NORTH'
            x, y = R12_MOVES[op]
            state['pos'][0] += x
            state['pos'][1] += y
            state['route'].append([op])
            state['clock'] += 1
        state['route'].append(['WATER'])
        state['clock'] += 1
    return {'problem': deepcopy(problem), 'routes': [s['route'] for s in states]}


def r12_select(obs, proposed, st, checker):
    """原动作若保留完整余量则执行；否则执行当日证书首步，失败显式记录。"""
    receipt = {'step': obs['step'], 'status': None, 'overrides': 0}
    if obs['day'] == 29:
        receipt['status'] = 'TERMINAL_R0_UNCHANGED'
        return proposed, receipt
    current = r12_problem(obs)
    after = r12_project(obs, proposed)
    receipt['danger_count'] = len(current['targets'])
    receipt['projected_danger_count'] = len(after['targets'])
    future = r12_schedule(after)
    if future is not None and checker(after, future)['valid']:
        st['r12_certificate'] = future
        receipt['status'] = 'ECONOMIC_ACTION_PRESERVES_WATER_CERTIFICATE'
        return proposed, receipt
    certificate = r12_schedule(current)
    if certificate is None or not checker(current, certificate)['valid']:
        saved = st.get('r12_certificate')
        certificate = saved if saved is not None and checker(current, saved)['valid'] else None
    if certificate is None:
        st.pop('r12_certificate', None)
        receipt['status'] = 'NO_COMPLETE_WATER_CERTIFICATE_R0_ACTION_RETAINED'
        return proposed, receipt
    selected = [list(route[0]) if route else ['PASS'] for route in certificate['routes']]
    receipt['overrides'] = sum(a != b for a, b in zip(proposed, selected))
    receipt['status'] = 'EXECUTE_CHECKED_WATER_CERTIFICATE_PREFIX'
    projected = r12_project(obs, selected)
    tail = {'problem': projected, 'routes': [route[1:] for route in certificate['routes']]}
    if checker(projected, tail)['valid']:
        st['r12_certificate'] = tail
    else:
        st.pop('r12_certificate', None)
        receipt['tail_check_failed'] = True
    return selected, receipt


from copy import deepcopy


def r12_check(problem, certificate):
    try:
        assert isinstance(certificate, dict) and certificate.get('problem') == problem, 'PROBLEM_IDENTITY'
        board, start, end = problem['board'], problem['step'], problem['end']
        assert type(board) is int and board == 10, 'BOARD'
        assert type(start) is int and type(end) is int and 0 <= start <= end + 1 <= 719, 'CLOCK'
        targets = {}
        for t in problem['targets']:
            pos = tuple(t['pos'])
            assert len(pos) == 2 and all(type(v) is int and 0 <= v < board for v in pos), 'TARGET_POSITION'
            assert pos not in targets, 'DUPLICATE_TARGET'
            assert type(t['deadline']) is int, 'DEADLINE_TYPE'
            targets[pos] = t
        positions = deepcopy(problem['positions'])
        routes = certificate['routes']
        assert len(routes) == len(positions) and positions, 'ACTOR_COVERAGE'
        visited = set()
        for uid, route in enumerate(routes):
            x, y = positions[uid]
            assert type(x) is int and type(y) is int and 0 <= x < board and 0 <= y < board, 'ACTOR_POSITION'
            for offset, action in enumerate(route):
                step = start + offset
                assert step <= end, 'OVERTIME'
                assert isinstance(action, list) and len(action) == 1, 'ACTION_SHAPE'
                op = action[0]
                if op == 'NORTH': y -= 1
                elif op == 'SOUTH': y += 1
                elif op == 'WEST': x -= 1
                elif op == 'EAST': x += 1
                elif op == 'WATER':
                    pos = (x, y)
                    assert pos in targets and pos not in visited, 'UNKNOWN_OR_DUPLICATE_WATER'
                    assert step <= targets[pos]['deadline'], 'LIFESPAN_DEADLINE'
                    visited.add(pos)
                else: raise AssertionError('UNSUPPORTED_ACTION')
                assert 0 <= x < board and 0 <= y < board, 'MOVE_OUT_OF_BOARD'
        assert visited == set(targets), 'MISSING_SERVICE'
        return {'valid': True, 'services': len(visited), 'error': None}
    except (AssertionError, KeyError, TypeError, ValueError, IndexError) as exc:
        return {'valid': False, 'services': 0, 'error': str(exc)}
