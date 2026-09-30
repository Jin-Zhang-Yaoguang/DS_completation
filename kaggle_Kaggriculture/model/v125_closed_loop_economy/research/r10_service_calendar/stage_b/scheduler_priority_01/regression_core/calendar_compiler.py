"""R10 B future service compiler. Frozen R9 economic calendar lineage; no candidate imports.

Only adds service/state diagnostics at original calendar accumulation points.
The legacy goods/work/feed values are preserved. Future state is conditional on
legacy timely care and delivery, never an observation or execution receipt.
"""
from __future__ import annotations
from collections import Counter
from copy import deepcopy
import hashlib
import json
import math

PARENT_SOURCE_SHA256 = "e7f1fd549fc67ccec74015299af5366812abe43ec78c4142bb019429b6bb22e0"
CROPS = {"WHEAT": (10,2,4,0,6), "CARROT": (20,2,3,0,4),
         "TOMATO": (50,8,8,1,4), "STRAWBERRY": (100,10,10,2,4), "MELON": (80,10,12,0,6)}
ANIMALS = {"GOOSE": (300,"COOP",4,1,4,"EGG"), "COW": (400,"PASTURE",8,2,6,"MILK"),
           "SHEEP": (500,"PASTURE",6,3,6,"WOOL")}
ACCESS = ((4,4),(5,4),(4,5),(5,5))
FIELD_OPS = {"WATER", "FEED", "CARE", "HARVEST", "COLLECT_FERTILIZER"}

def canonical_sha(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()).hexdigest()

def dist(a,b):
    return abs(a[0]-b[0])+abs(a[1]-b[1])

def home(pos):
    return min(ACCESS,key=lambda q:(dist(pos,q),q))

def project_calendar_with_services(tile, day, hour=0, position=(4, 4), source=None):
    """每日照护、及时采收交付的模型日历；物量可用纯规则控制核对。"""
    goods, work, feed = {}, Counter(), Counter()
    raw_services = {}
    t = dict(tile)
    distance = dist(position, home(position))

    def product(d, item, qty):
        qty = int(qty)
        if qty <= 0 or d > 29:
            return
        if d == 29 and day == 29 and hour + distance + 2 > 22:
            return
        goods.setdefault(d, Counter())[item] += qty
        raw_services.setdefault(d, []).append({"op": "COLLECT_FERTILIZER" if item == "FERTILIZER" else "HARVEST", "requires": {}, "gives": {item: qty}})
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
                raw_services.setdefault(d, []).append({"op": "FEED", "requires": {"WHEAT": 1}, "gives": {}})
                work[d] += 1
                feed[d] += 1
            if d < 28 and not cared:
                raw_services.setdefault(d, []).append({"op": "CARE", "requires": {}, "gives": {}})
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
                raw_services.setdefault(d, []).append({"op": "WATER", "requires": {}, "gives": {}})
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
    legacy = {"goods": {d: dict(v) for d, v in goods.items()}, "work": dict(work), "feed": dict(feed)}
    return _enrich_calendar(tile, day, hour, position, source, legacy, raw_services)


def _asset_identity(tile, pos):
    x, y = pos
    if "animal" in tile:
        return "animal:%s:%d:%d,%d" % (tile["animal"], tile["placed_day"], x, y)
    return "plant:%s:%d:%d,%d" % (tile["crop"], tile["planted_day"], x, y)


def _normal_tile(tile):
    t = deepcopy(tile)
    if "animal" in t:
        a = t["animal"]
        if a not in ANIMALS:
            raise ValueError("unknown animal")
        t.setdefault("kind", ANIMALS[a][1])
        for key, value in (("yield_units", 0), ("consecutive_unfed", 0),
                           ("fed_today", False), ("cared_today", False),
                           ("fertilizer_available", False), ("pending_care_bonus", 0)):
            t.setdefault(key, value)
    else:
        c = t["crop"]
        if c not in CROPS:
            raise ValueError("unknown crop")
        t.setdefault("kind", "PLANT")
        for key, value in (("yield_units", 0), ("consecutive_unwatered", 0),
                           ("watered_today", False), ("fertilized_until_day", -1)):
            t.setdefault(key, value)
        # investment_quote's synthetic tile omits lifespan; this is the official
        # new-plant default, not a claim that activation has actually happened.
        t.setdefault("max_lifespan_step", -1 if CROPS[c][3] else (t["planted_day"] + CROPS[c][2] + 1) * 24)
    return t


def _apply_model_service(tile, service, day):
    """Conditional timely service, for future tile state only; no actor execution."""
    t = deepcopy(tile)
    op = service["op"]
    if not isinstance(t, dict):
        return t, "SERVICE_ON_ABSENT_MODEL_ASSET"
    if op == "WATER":
        if t.get("kind") != "PLANT" or t.get("watered_today"):
            return t, "WATER_MODEL_STATE_CONFLICT"
        t["watered_today"] = True
        c = CROPS[t["crop"]]
        age = day - t["planted_day"]
        if not c[3] and (c[2] + 1) // 2 <= age <= c[2]:
            t["yield_units"] = min(c[4], t["yield_units"] + (2 if t["fertilized_until_day"] >= day else 1))
    elif op in ("FEED", "CARE", "COLLECT_FERTILIZER"):
        if "animal" not in t:
            return t, "ANIMAL_MODEL_STATE_CONFLICT"
        flag = {"FEED": "fed_today", "CARE": "cared_today", "COLLECT_FERTILIZER": "fertilizer_available"}[op]
        if op == "COLLECT_FERTILIZER":
            if not t[flag]:
                return t, "FERTILIZER_MODEL_STATE_CONFLICT"
            t[flag] = False
        else:
            if t[flag]:
                return t, op + "_MODEL_STATE_CONFLICT"
            t[flag] = True
    elif op == "HARVEST":
        if t.get("kind") == "PLANT":
            item = t["crop"]
            if day - t["planted_day"] < CROPS[item][1]:
                return t, "IMMATURE_MODEL_HARVEST"
        elif "animal" in t:
            item = ANIMALS[t["animal"]][5]
        else:
            return t, "HARVEST_MODEL_STATE_CONFLICT"
        if service["gives"] != {item: int(t.get("yield_units", 0))} or t.get("yield_units", 0) <= 0:
            return t, "HARVEST_MODEL_QUANTITY_CONFLICT"
        t["yield_units"] = 0
        if t.get("kind") == "PLANT" and not CROPS[item][3]:
            t = None
    else:
        return t, "UNKNOWN_MODEL_SERVICE"
    return t, None


def _model_next_day(tile, day):
    """Official asset transitions under the explicitly timely service assumption.

    Random empty-cell weeds, shops, money and worker routes are not predicted.
    Daily services above were applied before any known same-day lifespan decay.
    """
    t = deepcopy(tile)
    if not isinstance(t, dict):
        return t
    if t.get("kind") == "PLANT":
        mls = t["max_lifespan_step"]
        if mls >= 0:
            for step in range(day * 24, day * 24 + 24):
                if step >= mls and (step - mls) % 2 == 0:
                    t["yield_units"] -= 1
                    if t["yield_units"] <= 0:
                        return {"kind": "WEED"}
        watered = t["watered_today"]
        t["consecutive_unwatered"] = 0 if watered else t["consecutive_unwatered"] + 1
        t["watered_today"] = False
        if t["consecutive_unwatered"] >= 2:
            return {"kind": "WEED"}
        c = CROPS[t["crop"]]
        if c[3]:
            since = day + 1 - t["planted_day"] - c[1]
            if since >= 0 and since % c[3] == 0:
                count = since // c[3] + 1
                if count <= c[4]:
                    bonus = watered and t["fertilized_until_day"] >= day
                    t["yield_units"] = min(c[4], t["yield_units"] + (2 if bonus else 1))
                    if count == c[4]:
                        t["max_lifespan_step"] = (day + 2) * 24
    elif "animal" in t:
        a = ANIMALS[t["animal"]]
        t["consecutive_unfed"] = 0 if t["fed_today"] else t["consecutive_unfed"] + 1
        if t["consecutive_unfed"] >= 2:
            return {"kind": a[1]}
        since = day + 1 - t["placed_day"] - a[2]
        if since >= 0 and since % a[3] == 0:
            bonus = t.get("pending_care_bonus", 0) if t["fed_today"] else 0
            t["yield_units"] = min(a[4], t["yield_units"] + 1 + bonus)
            t["pending_care_bonus"] = 0
        if t["cared_today"] and t["fed_today"]:
            t["pending_care_bonus"] = t.get("pending_care_bonus", 0) + 1
        t["fertilizer_available"] = True
        t["fed_today"] = False
        t["cared_today"] = False
    return t


def _enrich_calendar(tile, day, hour, position, source, legacy, raw_services):
    pos = list(position)
    aid = _asset_identity(tile, pos)
    t = _normal_tile(tile)
    states, services, unsupported = {}, {}, {}
    ordering = {"WATER": 0, "FEED": 1, "CARE": 2, "HARVEST": 3, "COLLECT_FERTILIZER": 4}
    condition = deepcopy(source) if source is not None else {"kind": "caller_supplied_tile", "actual_observation_proven": False}
    for d in range(day, 30):
        states[d] = deepcopy(t)
        field = []
        water_id = None
        for event in sorted(raw_services.get(d, []), key=lambda e: ordering[e["op"]]):
            op = event["op"]
            sid = aid + "/d%d/" % d + op
            release, deadline = (max(0, int(hour)) if d == day else 0), (22 if d == 29 else 23)
            if isinstance(t, dict) and t.get("kind") == "PLANT":
                mls = t.get("max_lifespan_step", -1)
                if mls >= 0:
                    deadline = min(deadline, mls - d * 24)
            if release > deadline:
                unsupported.setdefault(d, []).append("SERVICE_WINDOW_OR_LIFESPAN_UNSUPPORTED")
            deps = []
            if op == "HARVEST" and water_id and "crop" in tile and not CROPS[tile["crop"]][3]:
                deps.append(water_id)
            service = {"service_id": sid, "asset_id": aid, "pos": pos, "op": op, "item": None, "qty": 1,
                       "release": release, "deadline": deadline, "requires": deepcopy(event["requires"]),
                       "gives": deepcopy(event["gives"]), "dependencies": deps, "splittable": False}
            field.append(service)
            if op == "WATER":
                water_id = sid
        # The original accumulation points produce one event per operation/day.
        if len({s["service_id"] for s in field}) != len(field):
            unsupported.setdefault(d, []).append("DUPLICATE_FIELD_SERVICE")
        delivery = []
        for service in field:
            t, conflict = _apply_model_service(t, service, d)
            if conflict:
                unsupported.setdefault(d, []).append(conflict)
            for item, qty in service["gives"].items():
                delivery.append({"service_id": service["service_id"] + "/PLACE:" + item,
                                 "asset_id": aid, "pos": None, "op": "PLACE", "item": item, "qty": qty,
                                 "release": service["release"], "deadline": 22 if d == 29 else 23,
                                 "requires": {item: qty}, "gives": {},
                                 "dependencies": [service["service_id"]], "splittable": True})
        if field or delivery:
            services[d] = field + delivery
        if d < 29:
            t = _model_next_day(t, d)
    return {**legacy, "asset_id": aid, "pos": pos, "services": services, "state_by_day": states,
            "unsupported_by_day": unsupported,
            "conditional": [condition, {"kind": "legacy_timely_care_and_delivery",
              "detail": "Future tiles assume each original calendar service completes; not an execution receipt."}]}


def _integer_quantities(values, label):
    if not isinstance(values, dict):
        raise ValueError(label + " must be a dict")
    result = {}
    for item, qty in values.items():
        if not isinstance(item, str) or type(qty) is not int or qty < 0:
            raise ValueError(label + " has invalid quantity")
        if qty:
            result[item] = qty
    return result


def compile_day_problem(calendars, day, current_day, start_shed, reserved_shed,
                        planned_wheat_buy, legacy_work, legacy_hire_cost,
                        conditional=None, startup_fallback_days=None):
    """Compile a requested full future day. No guessing resources from scalar work.

    Completeness of the passed calendar list and funding inputs is a caller
    contract; coverage ids/conditional assumptions are exposed for independent QA.
    """
    if type(day) is not int or type(current_day) is not int or not 0 <= current_day <= day <= 29:
        raise ValueError("invalid day/current_day")
    reasons, tiles, services, goods, feed = [], [], [], Counter(), 0
    source_conditions = deepcopy(conditional or [])
    seen_assets, seen_positions, seen_services = set(), set(), set()
    if day == current_day:
        reasons.append("CURRENT_DAY_LEGACY")
    if day in (startup_fallback_days or []):
        reasons.append("UNSUPPORTED_STARTUP_FRONTIER")
    for cal in calendars:
        aid = cal["asset_id"]
        if aid in seen_assets:
            reasons.append("DUPLICATE_ASSET_CALENDAR")
            continue
        seen_assets.add(aid)
        if day not in cal["state_by_day"]:
            # Before conditional activation there are no lifecycle jobs; caller
            # must explicitly mark any startup day requiring the legacy gate.
            if cal["services"].get(day) or cal["goods"].get(day) or cal["feed"].get(day):
                reasons.append("MISSING_CONDITIONAL_ASSET_STATE")
            continue
        tile = deepcopy(cal["state_by_day"][day])
        jobs = deepcopy(cal["services"].get(day, []))
        reasons.extend(cal["unsupported_by_day"].get(day, []))
        active = isinstance(tile, dict) and (tile.get("kind") == "PLANT" or "animal" in tile)
        if active:
            p = tuple(cal["pos"])
            if p in seen_positions:
                reasons.append("DUPLICATE_ACTIVE_POSITION")
            seen_positions.add(p)
            tiles.append({"asset_id": aid, "pos": list(p), "tile": tile})
        elif jobs:
            reasons.append("SERVICE_ON_MISSING_ACTIVE_ASSET")
        for job in jobs:
            if job["service_id"] in seen_services:
                reasons.append("DUPLICATE_SERVICE")
            seen_services.add(job["service_id"])
            services.append(job)
        goods.update(cal["goods"].get(day, {}))
        feed += int(cal["feed"].get(day, 0))
        source_conditions.extend(deepcopy(cal["conditional"]))
    shed = _integer_quantities(start_shed, "start_shed")
    reserved = _integer_quantities(reserved_shed, "reserved_shed")
    buy = deepcopy(planned_wheat_buy)
    if not isinstance(buy, dict) or type(buy.get("qty")) is not int or buy["qty"] < 0:
        raise ValueError("planned_wheat_buy requires a nonnegative integer qty")
    if type(buy.get("estimated_cash")) not in (int, float) or not math.isfinite(buy["estimated_cash"]) or buy["estimated_cash"] < 0:
        raise ValueError("planned_wheat_buy requires finite nonnegative estimated_cash")
    if buy.get("order_hour") != 0 or buy.get("available_from_hour") != 1:
        reasons.append("UNSUPPORTED_WHEAT_BUY_TIMING")
    if buy["qty"] == 0 and buy["estimated_cash"] != 0:
        reasons.append("ZERO_BUY_NONZERO_ESTIMATED_CASH")
    if buy["qty"] and buy["estimated_cash"] <= 0:
        reasons.append("FREE_CONDITIONAL_WHEAT_BUY")
    if buy["qty"] > 16 or feed > 16:
        reasons.append("FEED_OR_BUY_ABOVE_STAGE_B_16_LIMIT")
    if sum(shed.values()) > 100:
        reasons.append("START_SHED_OVER_CAPACITY")
    if shed.get("WHEAT", 0) + buy["qty"] < feed:
        reasons.append("CONDITIONAL_WHEAT_SOURCE_SHORTFALL")
    if reserved.get("FERTILIZER", 0) > 12:
        reasons.append("FERTILIZER_RESERVE_ABOVE_LEGACY_CAP")
    derived_goods = Counter()
    derived_feed = 0
    for service in services:
        if service["op"] != "PLACE":
            derived_goods.update(service["gives"])
            derived_feed += service["requires"].get("WHEAT", 0)
    if derived_goods != goods or derived_feed != feed:
        reasons.append("CALENDAR_SERVICE_QUANTITY_MISMATCH")
    if type(legacy_work) is not int or legacy_work < 0:
        raise ValueError("legacy_work must be nonnegative integer")
    if type(legacy_hire_cost) not in (int, float) or not math.isfinite(legacy_hire_cost) or legacy_hire_cost < 0:
        raise ValueError("legacy_hire_cost must be finite and nonnegative")
    source_conditions.append({"kind": "conditional_bridge_from_legacy_day",
                              "detail": "Only this requested day is certified; prior days retain original R9 gate and timely-care assumptions."})
    return {"schema": "r10-future-day-problem-v1", "status": "UNSUPPORTED" if reasons else "SUPPORTED",
            "unsupported_reasons": sorted(set(reasons)), "day": day, "current_day": current_day,
            "end_hour": 22 if day == 29 else 23, "board_size": 10,
            "start_farm_tiles": sorted(tiles, key=lambda t: t["asset_id"]),
            "start_shed": shed, "reserved_shed": reserved, "planned_wheat_buy": buy,
            "services": sorted(services, key=lambda s: s["service_id"]),
            "expected_goods": dict(goods), "feed_units": feed,
            "legacy_work": legacy_work, "legacy_hire_cost": legacy_hire_cost,
            "conditional": source_conditions,
            "hire_protocol": {"max_hands": 12, "farmer_h0_pass": True, "h0_max_hires": 9, "h1_remaining_hires": True},
            "capacity": 100}
