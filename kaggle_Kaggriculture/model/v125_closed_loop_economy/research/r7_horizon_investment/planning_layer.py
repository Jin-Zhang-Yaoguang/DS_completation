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
    """每日报价为当天本方拟售项成交前；当前田间现货从次日进入留存供给。"""
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
                    calendars.append((seat, (x, y), project_calendar(tile, day, obs["hour"], (x, y))))
    prices, inventories = {}, {}
    for d in range(day, 30):
        if d > day:
            for p in PRODUCTS:
                supply[p] -= demand[p]
            for _, _, cal in calendars:
                for p, n in cal["goods"].get(d - 1, {}).items():
                    supply[p] += n
                supply["WHEAT"] -= cal["feed"].get(d - 1, 0)
        inventories[d] = dict(supply)
        prices[d] = {p: price(p, supply[p], obs["market"].get("params")) for p in PRODUCTS}
    return {"prices": prices, "inventories": inventories, "demand": demand, "calendars": calendars}


def apply_project_supply(obs, model, cal):
    # 日内项目先后成交未知，统一从次日报价体现当前项目的产品与买粮冲击。
    for d in range(obs["day"], 30):
        for future_day in range(d + 1, 30):
            for p, n in cal["goods"].get(d, {}).items():
                model["inventories"][future_day][p] += n
            model["inventories"][future_day]["WHEAT"] -= cal["feed"].get(d, 0)
            model["prices"][future_day] = {p: price(p, model["inventories"][future_day][p], obs["market"].get("params")) for p in PRODUCTS}


def labor_schedule(obs, workload, market_order_reserve=0):
    """当前工人已到场；新工次帧可动，未来雇工保留真实费用和每帧订单限制。"""
    f = obs["farms"][obs["player"]]
    existing = len(f["hands"])
    target, feasible = existing, True
    cash_by_day, capacity_by_day = {}, {}
    cap = int(PARAMS["max_hands"])
    for d in range(obs["day"], 30):
        need = max(0, workload.get(d, 0))
        slots = (23 if d == 29 else 24) - (obs["hour"] if d == obs["day"] else 0)
        base = existing if d == obs["day"] else 0
        workers = base
        # 一个市场最多十条命令；前十名h0雇，余下h1雇，次帧起有容量。
        capacity = (1 + base) * max(0, slots)
        can_hire = d != obs["day"] or obs["hour"] < 8
        first_frame_hires = max(0, 10 - market_order_reserve) if d == obs["day"] else 10
        limit = min(cap, existing + first_frame_hires) if d == obs["day"] and obs["hour"] == 7 else cap
        while capacity < need and workers < limit and can_hire:
            delay = 1 if workers - base < first_frame_hires else 2 + (workers - base - first_frame_hires) // 10
            capacity += max(0, slots - delay)
            workers += 1
        if capacity < need:
            feasible = False
        if d == obs["day"]:
            # 当日目标最多本帧可发的10单；次帧重算剩余需要。
            target = min(workers, existing + first_frame_hires)
            ordinal = int(f.get("hires_today", existing))
        else:
            ordinal = 0
        cash_by_day[d] = sum(FIB[min(ordinal + i, len(FIB) - 1)] for i in range(workers - base))
        capacity_by_day[d] = capacity
    return {"feasible": feasible, "hire_target_today": target, "cash_by_day": cash_by_day,
            "capacity_by_day": capacity_by_day, "total_cost": sum(cash_by_day.values())}


def investment_quote(obs, item, position, market_model, seed_credit=False, already_owned=False, committed=False):
    """成本分机会价值与现金；时钟按顺序启动，产出是假设照护及时的模型。"""
    day, hour = obs["day"], obs["hour"]
    f = obs["farms"][obs["player"]]
    x, y = position
    tile = f["tiles"][y][x]
    actors = [tuple(f["farmer"])] + [tuple(p) for p in f["hands"]]
    approach = min(dist(p, position) for p in actors)
    distance = dist(position, home(position))
    if item in ANIMALS and isinstance(tile, dict) and tile.get("kind") in ("COOP", "PASTURE") and tile.get("kind") != ANIMALS[item][1]:
        return None
    build = item in ANIMALS and not (isinstance(tile, dict) and tile.get("kind") == ANIMALS[item][1] and "animal" not in tile)
    setup_work = Counter()
    if item in ANIMALS:
        build_actions = approach + (1 if tile is not None else 0) + 1 if build else 0
        if build and not committed and hour + build_actions > 21:
            return None
        # 有现货且已携带者从其位置直接PLACE；否则到仓领取，不能借未来市场动作。
        carriers = [i for i, inv in enumerate(obs["private"]["inventories"]) if inv.get(item, 0)] if already_owned else []
        if carriers and not build:
            transport = min(dist(actors[i], position) + 1 for i in carriers)
            wait_buy = 0
        else:
            transport = (2 * distance + 2) if build else min(dist(p, home(position)) for p in actors) + distance + 2
            wait_buy = 0 if already_owned else 1
        start_step = obs["step"] + build_actions + wait_buy + transport - 1
        active_steps = build_actions + transport
        start_day = start_step // 24
        future = {"kind": ANIMALS[item][1], "animal": item, "placed_day": start_day, "yield_units": 0,
                  "fed_today": False, "cared_today": False, "fertilizer_available": False, "pending_care_bonus": 0}
        fixed = 0 if already_owned else ANIMALS[item][0]
    else:
        if isinstance(tile, dict) and tile.get("kind") != "WEED":
            return None
        clear = int(tile is not None)
        wait_buy = int(not seed_credit)
        # make_tasks h21停止接受新PLANT；购买缺种必须等下一帧，首水须赶在h21。
        if not committed and (day >= 28 or hour + wait_buy >= 21 or hour + wait_buy + approach + clear + 1 > 21):
            return None
        active_steps = approach + clear + 1  # 首水由生命周期日历另记，避免重复。
        start_step = obs["step"] + wait_buy + active_steps - 1
        start_day = start_step // 24
        future = {"kind": "PLANT", "crop": item, "planted_day": start_day, "yield_units": 0 if CROPS[item][3] else 1,
                  "watered_today": False, "consecutive_unwatered": 1, "fertilized_until_day": -1}
        fixed = 0 if seed_credit else CROPS[item][0]
    if start_step >= 718 or start_day > 29:
        return None
    cal = project_calendar(future, start_day, start_step % 24 + 1, position)
    # 启动行程逐日占用；采购等待只推进时钟，不虚构工人动作。
    for k in range(active_steps):
        action_day = min(29, (obs["step"] + k) // 24)
        setup_work[action_day] += 1
    for d, n in setup_work.items():
        cal["work"][d] = cal["work"].get(d, 0) + n
    gross = sum(sum(price(p, market_model["inventories"][d][p] + k, obs["market"].get("params")) for k in range(n))
                for d, goods in cal["goods"].items() for p, n in goods.items())
    feed_cost = sum(sum(price("WHEAT", market_model["inventories"][d]["WHEAT"] - k - 1, obs["market"].get("params")) for k in range(n))
                    for d, n in cal["feed"].items())
    primary = ANIMALS[item][5] if item in ANIMALS else item
    productive_days = [d for d, goods in cal["goods"].items() if goods.get(primary, 0)]
    if not productive_days and not committed:
        return None
    labor = sum(cal["work"].values())
    return {"item": item, "position": tuple(position), "build_first": build, "start_step_model": start_step,
            "first_product_day": min(productive_days) if productive_days else None, "calendar": cal,
            "fixed_cash": fixed, "setup_work": dict(setup_work), "gross_cash_model": gross,
            "feed_cost_model": feed_cost, "net_before_hiring_model": gross - fixed - feed_cost,
            "labor": labor, "score_before_hiring": (gross - fixed - feed_cost) / max(1, labor)}


def feed_ledger(obs, model, requirements, owned_wheat):
    """同一饲料物量：自有麦按可售价值占用，只有不足部分按逐单位买价占现金。"""
    left = max(0, int(owned_wheat))
    cash, opportunity, owned_used = 0., 0., 0
    buys = {}
    for d in sorted(requirements):
        n = max(0, int(requirements[d]))
        held = min(left, n)
        left -= held
        owned_used += held
        supply = model["inventories"][d]["WHEAT"]
        opportunity += sum(price("WHEAT", supply + k, obs["market"].get("params")) for k in range(held))
        bought = n - held
        cost = sum(price("WHEAT", supply - k - 1, obs["market"].get("params")) for k in range(bought))
        cash += cost
        opportunity += cost
        if bought:
            buys[d] = bought
    return {"cash": cash, "opportunity": opportunity, "owned_used": owned_used,
            "owned_remaining": left, "buys_by_day": buys, "units": sum(requirements.values())}


def economic_plan(obs, st):
    f, private, day = obs["farms"][obs["player"]], obs["private"], obs["day"]
    own = counts(f, private)
    model = dated_market_model(obs)
    st["forecasts"] = dict(model["prices"][day])
    st["crop_scores"] = {}
    owned = [(x, y) for y, row in enumerate(f["tiles"]) for x, t in enumerate(row) if t != "LOCKED"]
    ranked = sorted(owned, key=lambda p: (dist(p, home(p)), p[1], p[0]))
    free = [p for p in ranked if f["tiles"][p[1]][p[0]] is None or (isinstance(f["tiles"][p[1]][p[0]], dict) and f["tiles"][p[1]][p[0]].get("kind") == "WEED")]
    structures = [p for p in ranked if isinstance(f["tiles"][p[1]][p[0]], dict) and f["tiles"][p[1]][p[0]].get("kind") in ("PASTURE", "COOP") and "animal" not in f["tiles"][p[1]][p[0]]]
    workload, feed = Counter(), Counter()
    for seat, _, cal in model["calendars"]:
        if seat == obs["player"]:
            workload.update(cal["work"]); feed.update(cal["feed"])
    builds, reserved, plant_permits = {}, set(), {}
    committed_plant_sites = set()
    seeds = Counter(private["seeds"])
    committed_fixed, commitments = 0., []
    in_transit = {a: inventory_total(private, a) for a in ANIMALS}
    unassigned_transit = Counter(in_transit)
    transit_calendars = []
    previous_builds = st.get("latest_investment_plan", {}).get("build_permits", {})
    # 先占用正在执行的合同目标，不能给未落地的同格重新许可另一项目。
    for contract in st.get("contracts", {}).values():
        pos = tuple(contract["target"])
        if pos not in free:
            continue
        ops = [stage["op"] for stage in contract.get("stages", [])]
        plant = next((op[1] for op in ops if op[0] == "PLANT"), None)
        building = next((op[0][6:] for op in ops if op[0].startswith("BUILD_")), None)
        if not plant and not building:
            continue
        item = plant or previous_builds.get(pos, "GOOSE" if building == "COOP" else "COW")
        reserved.add(pos)
        existing_animal = bool(building and unassigned_transit[item] > 0)
        if existing_animal:
            unassigned_transit[item] -= 1
        q = investment_quote(obs, item, pos, model, seed_credit=bool(plant and seeds[item]), already_owned=existing_animal, committed=True)
        if q:
            workload.update(q["calendar"]["work"]); feed.update(q["calendar"]["feed"])
            committed_fixed += q["fixed_cash"]
            commitments.append(q)
            if existing_animal:
                transit_calendars.append(q)
            apply_project_supply(obs, model, q["calendar"])
        if plant:
            plant_permits[pos] = plant
            committed_plant_sites.add(pos)
            seeds[plant] = max(0, seeds[plant] - 1)
        else:
            builds[pos] = item
    used_structures = set()
    for animal in ANIMALS:
        for _ in range(unassigned_transit[animal]):
            site = next((p for p in structures if p not in used_structures and f["tiles"][p[1]][p[0]]["kind"] == ANIMALS[animal][1]), None)
            if site is None:
                site = next((p for p in free if p not in reserved), None)
                if site is not None:
                    builds[site] = animal
            if site is None:
                continue
            reserved.add(site); used_structures.add(site)
            q = investment_quote(obs, animal, site, model, already_owned=True, committed=True)
            if q:
                workload.update(q["calendar"]["work"]); feed.update(q["calendar"]["feed"])
                transit_calendars.append(q)
                apply_project_supply(obs, model, q["calendar"])
    # 现有R6补粮目标的周转缓冲也占现金；不会免费假设未来卖货支付照护。
    n_animals = sum(own[a] for a in ANIMALS)
    buffer_units = max(3, n_animals // 2) if n_animals and day < 29 else 0
    feed_cash_requirements = Counter(feed)
    feed_cash_requirements[day] += buffer_units
    base_feed = feed_ledger(obs, model, feed_cash_requirements, inventory_total(private, "WHEAT"))
    feed_order_needed = bool(n_animals and day < 29 and inventory_total(private, "WHEAT") < n_animals + max(3, n_animals // 2))
    material_order_keys = {("feed", "WHEAT")} if feed_order_needed else set()
    base_labor = labor_schedule(obs, workload, len(material_order_keys))
    base_reserved = committed_fixed + base_feed["cash"] + base_labor["total_cost"]
    cash = max(0., float(f["money"]) - base_reserved)
    base_summary = {"work": dict(workload), "feed": dict(feed), "in_transit": in_transit,
                    "transit_project_count": len(transit_calendars), "contract_count": len(commitments),
                    "feed_cash": base_feed["cash"], "feed_opportunity": base_feed["opportunity"],
                    "owned_feed_used": base_feed["owned_used"], "hire_cash": base_labor["total_cost"],
                    "committed_fixed_cash": committed_fixed, "reserved_cash": base_reserved}
    animal_orders, seed_orders, accepted, rejected = Counter(), Counter(), [], Counter()
    expert_items = {"balanced": ("WHEAT", "CARROT"), "dairy": ("COW",), "fiber": ("SHEEP",),
                    "horticulture": ("TOMATO", "STRAWBERRY", "MELON")}

    def budget_quote(item, pos):
        q = investment_quote(obs, item, pos, model, seeds.get(item, 0) > 0)
        if not q:
            return None, "startup_or_maturity"
        next_work = workload + Counter(q["calendar"]["work"])
        next_keys = set(material_order_keys)
        if q["fixed_cash"] and not q["build_first"]:
            next_keys.add(("animal" if item in ANIMALS else "seed", item))
        labor = labor_schedule(obs, next_work, len(next_keys))
        marginal_hires = max(0., labor["total_cost"] - base_labor["total_cost"])
        cash_feed = Counter(q["calendar"]["feed"])
        if item in ANIMALS and not n_animals:
            cash_feed[day] += 3  # 保留R6首次建立喂料周转缓冲所需现金。
        next_ledger = feed_ledger(obs, model, cash_feed, base_feed["owned_remaining"])
        marginal_feed_cash = next_ledger["cash"]
        # 经济成本仍包含自有麦的机会价值，不能因已有粮而把饲料记成免费。
        marginal_opportunity = next_ledger["opportunity"]
        net = q["gross_cash_model"] - q["fixed_cash"] - marginal_opportunity - marginal_hires
        cash_need = q["fixed_cash"] + marginal_feed_cash + marginal_hires
        q.update(net_cash_model=net, cash_reserved_model=cash_need, feed_cash_model=marginal_feed_cash,
                 feed_cost_model=marginal_opportunity, hire_cash_model=marginal_hires,
                 score=net / max(1, q["labor"]), feed_ledger=next_ledger, material_order_keys=next_keys)
        if not labor["feasible"]:
            return q, "labor"
        if net <= 0:
            return q, "nonpositive_net"
        if cash_need > cash:
            return q, "cash"
        return q, None

    offers, expert_scores = [], {e: -1e9 for e in expert_items}
    for pos in ranked:
        if pos in reserved or (pos not in free and pos not in structures):
            continue
        for expert, items in expert_items.items():
            for item in items:
                if item in ANIMALS and sum(in_transit.values()):
                    continue
                if item in CROPS and pos in structures:
                    continue
                q, reason = budget_quote(item, pos)
                if reason:
                    rejected[reason] += 1
                    continue
                q["expert"] = expert
                offers.append(q)
                expert_scores[expert] = max(expert_scores[expert], q["score"])
                if item in CROPS:
                    st["crop_scores"][item] = max(st["crop_scores"].get(item, -1e9), q["score"])
    chosen = PARAMS["router"]
    if chosen == "adaptive":
        chosen = max(expert_scores, key=expert_scores.get)
    if chosen not in expert_items:
        chosen = "balanced"
    st["expert"] = chosen
    st["metrics"]["expert_" + chosen] += 1
    st["crop_choice"] = max(st["crop_scores"], key=st["crop_scores"].get) if st["crop_scores"] else None
    animal_admitted = False
    for q0 in sorted((q for q in offers if q["expert"] == chosen), key=lambda q: (-q["score"], dist(q["position"], home(q["position"])), q["position"])):
        item, pos = q0["item"], q0["position"]
        if pos in reserved or pos in plant_permits or (item in ANIMALS and animal_admitted):
            continue
        q, reason = budget_quote(item, pos)
        if reason:
            rejected[reason] += 1
            continue
        q["expert"] = chosen
        cash -= q["cash_reserved_model"]
        workload.update(q["calendar"]["work"])
        feed_cash_requirements.update(q["calendar"]["feed"])
        material_order_keys = q["material_order_keys"]
        base_labor = labor_schedule(obs, workload, len(material_order_keys))
        base_feed["owned_used"] += q["feed_ledger"]["owned_used"]
        base_feed["owned_remaining"] = q["feed_ledger"]["owned_remaining"]
        base_feed["cash"] += q["feed_ledger"]["cash"]
        base_feed["opportunity"] += q["feed_ledger"]["opportunity"]
        accepted.append(q)
        if item in ANIMALS:
            reserved.add(pos); animal_admitted = True
            if q["build_first"]:
                builds[pos] = item
            else:
                animal_orders[item] += 1
        else:
            plant_permits[pos] = item
            if seeds[item] > 0:
                seeds[item] -= 1
            else:
                seed_orders[item] += 1
        apply_project_supply(obs, model, q["calendar"])
    occupied = sum(isinstance(t, dict) for row in f["tiles"] for t in row if t != "LOCKED")
    lands = len(f["unlocked_quadrants"])
    land_cost = (1000, 2000, 4000)[lands - 1] if 0 < lands < 3 else 0
    hire_orders = max(0, base_labor["hire_target_today"] - len(f["hands"])) if obs["hour"] < 8 else 0
    buy_land = bool(land_cost and 3 <= day < 19 and occupied >= lands * 25 - 8 and cash > land_cost + 600
                    and hire_orders + len(material_order_keys) < 10)
    if buy_land:
        cash -= land_cost
    st["metrics"]["investment_permit_quotes"] += len(accepted)
    st["metrics"]["investment_budget_rejected_quotes"] += sum(rejected.values())
    plan = {"counts": own, "animals": {a: own[a] + animal_orders[a] for a in ANIMALS},
            "melon_cap": 100, "strawberry_cap": 100, "crop_choice": st["crop_choice"], "demand": model["demand"],
            "build_permits": builds, "reserved_animal_sites": reserved, "plant_permits": plant_permits,
            "committed_plant_sites": committed_plant_sites,
            "animal_purchases": dict(animal_orders), "seed_purchases": dict(seed_orders), "buy_land": buy_land,
            "land_cash": land_cost if buy_land else 0, "material_order_slots": len(material_order_keys) + int(buy_land), "hire_target_today": base_labor["hire_target_today"],
            "planned_work": dict(workload), "labor_plan": base_labor, "existing_obligations": base_summary,
            "remaining_investment_cash_model": cash, "admitted_investments": accepted,
            "expert_quote_scores": expert_scores, "in_transit_existing": in_transit,
            "owned_wheat_reserved": base_feed["owned_used"], "rejected_types": dict(rejected)}
    st["latest_investment_plan"] = plan
    receipt = {"step": obs["step"], "expert": chosen, "actual_cash": f["money"],
               "actual_wheat": inventory_total(private, "WHEAT"), "existing": base_summary,
               "remaining_cash": cash, "land_cash": plan["land_cash"], "rejected_types": dict(rejected),
               "work": dict(workload), "capacity": base_labor["capacity_by_day"],
               "admitted": [{k: list(q[k]) if k == "position" else q[k] for k in
                             ("item", "position", "build_first", "cash_reserved_model", "feed_cash_model", "feed_cost_model", "hire_cash_model")} for q in accepted]}
    st.setdefault("investment_receipts", []).append(receipt)
    st["investment_receipts"] = st["investment_receipts"][-720:]
    return plan


def record_investment_intents(st, orders, actions):
    receipt = st["investment_receipts"][-1]
    receipt["market_intents"] = [list(o) for o in orders[:10]]
    receipt["unit_investment_intents"] = [
        {"unit": i, "action": list(a)} for i, a in enumerate(actions)
        if a and (a[0] in ("PLANT", "PLACE") or a[0].startswith("BUILD_"))]
