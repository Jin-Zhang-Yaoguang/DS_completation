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

    for unit, contract in sorted(list(contracts.items())):
        if unit in assigned:
            continue
        fitted = _fit(obs, unit, contract["target"], contract["stages"], available)
        if fitted is None or len(fitted["stages"]) != len(contract["stages"]):
            cancel(unit, "infeasible")
            continue
        other_urgent = any(g["target"] != contract["target"] and g["target"] not in occupied and (o := propose_contract(obs, unit, g, available)) and o["urgent"] for g in groups)
        if other_urgent and not fitted["urgent"]:
            cancel(unit, "urgent_preempted")
            continue
        if contract["target"] in occupied or not accept(unit, {**fitted, **contract}, existing=True):
            cancel(unit, "resource_unavailable")

    actors = [u for u in range(len(positions)) if u not in assigned]
    free_groups = [g for g in groups if g["target"] not in occupied]
    offers, weights = {}, []
    # 最后可行的保活窗口采用词典序优先，优先级尺度由当帧价值上界推导。
    urgent_bonus = 1 + sum(max(0, s["value"]) for g in free_groups for s in g["stages"])
    for u in actors:
        row = []
        for j, group in enumerate(free_groups):
            offer = propose_contract(obs, u, group, available)
            if offer:
                weight = sum(s["value"] for s in offer["stages"]) / max(1, offer["cost"])
                if positions[u] == group["target"]:
                    weight *= 1.15
                row.append(weight + (urgent_bonus if offer["urgent"] else 0))
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
    st["metrics"]["unit_commands"] += len(actions)
    st["metrics"]["pass"] += sum(a[0] == "PASS" for a in actions)
    return actions
