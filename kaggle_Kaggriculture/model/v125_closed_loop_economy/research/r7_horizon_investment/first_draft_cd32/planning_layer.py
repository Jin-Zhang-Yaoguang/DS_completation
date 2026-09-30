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
