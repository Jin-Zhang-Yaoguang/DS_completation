"""未来整日服务证书的独立重演检查；不导入调度器、编译器、候选或引擎。

动作规则依据冻结官方 kaggriculture.py（bc8a54879ef0…）。现金与未来
日初状态是外部条件；本检查只证明给定条件下的动作、物量与交付。
"""
from collections import Counter
import copy
import hashlib
import json
import math

PRODUCTS = {"WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
            "EGG", "MILK", "WOOL", "FERTILIZER"}
CROPS = {"WHEAT": (2, 4, 0, 6), "CARROT": (2, 3, 0, 4),
         "TOMATO": (8, 8, 1, 4), "STRAWBERRY": (10, 10, 2, 4),
         "MELON": (10, 12, 0, 6)}
ANIMALS = {"GOOSE": ("COOP", "EGG", 4), "COW": ("PASTURE", "MILK", 6),
           "SHEEP": ("PASTURE", "WOOL", 6)}
ACCESS = ((4, 4), (5, 4), (4, 5), (5, 5))
MOVES = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}
FIELDS = {"WATER", "FEED", "CARE", "HARVEST", "COLLECT_FERTILIZER"}


class Invalid(Exception):
    def __init__(self, code, detail):
        self.code, self.detail = code, detail


def _need(ok, code, detail):
    if not ok:
        raise Invalid(code, detail)


def _int(value, lo=0, hi=None):
    return type(value) is int and value >= lo and (hi is None or value <= hi)


def _cash(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def _pos(value):
    return isinstance(value, list) and len(value) == 2 and all(_int(x, 0, 9) for x in value)


def _stock(value, label, allowed=None):
    _need(isinstance(value, dict), "STOCK_TYPE", label)
    _need(all(isinstance(k, str) and _int(v) and (allowed is None or k in allowed)
              for k, v in value.items()), "STOCK_DOMAIN", label)
    return Counter({k: v for k, v in value.items() if v})


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _plain(stock):
    return dict(sorted((k, v) for k, v in stock.items() if v))


def _fib(n):
    a = b = 1
    for _ in range(n):
        a, b = b, a + b
    return a


def _identity(tile, pos):
    if "animal" in tile:
        return f"animal:{tile['animal']}:{tile['placed_day']}:{pos[0]},{pos[1]}"
    return f"plant:{tile['crop']}:{tile['planted_day']}:{pos[0]},{pos[1]}"


def _validate_problem(p):
    _need(isinstance(p, dict) and p.get("schema") == "r10-future-day-problem-v1", "PROBLEM_SCHEMA", "schema")
    _need(p.get("status") == "SUPPORTED" and p.get("unsupported_reasons") == [], "UNSUPPORTED", "不接受fallback问题")
    day, current = p.get("day"), p.get("current_day")
    _need(_int(current, 0, 28) and _int(day, current + 1, 29), "DAY", "只接受未来完整日")
    end = 22 if day == 29 else 23
    _need(p.get("end_hour") == end and type(p.get("end_hour")) is int, "DAY_END", "day29止于h22")
    _need(type(p.get("board_size")) is int and p["board_size"] == 10 and
          type(p.get("capacity")) is int and p["capacity"] == 100, "BOARD_CAPACITY", "固定10格棋盘与100仓容")
    protocol = {"max_hands": 12, "farmer_h0_pass": True, "h0_max_hires": 9, "h1_remaining_hires": True}
    _need(p.get("hire_protocol") == protocol and
          type(p["hire_protocol"].get("max_hands")) is int and
          type(p["hire_protocol"].get("h0_max_hires")) is int and
          type(p["hire_protocol"].get("farmer_h0_pass")) is bool and
          type(p["hire_protocol"].get("h1_remaining_hires")) is bool, "HIRE_PROTOCOL", "固定协议")
    _need(isinstance(p.get("conditional"), list), "CONDITIONAL", "必须明示未来条件")
    _need(_cash(p.get("legacy_work")) and _cash(p.get("legacy_hire_cost")), "LEGACY_DOMAIN", "旧成本域")
    shed = _stock(p.get("start_shed"), "start_shed", PRODUCTS | set(ANIMALS))
    reserve = _stock(p.get("reserved_shed"), "reserved_shed", PRODUCTS | set(ANIMALS))
    _need(sum(shed.values()) <= 100 and reserve.get("FERTILIZER", 0) <= 12, "START_CAPACITY", "日初仓容或肥料预约")
    buy = p.get("planned_wheat_buy")
    _need(isinstance(buy, dict) and _int(buy.get("qty"), 0, 16) and
          _cash(buy.get("estimated_cash")) and type(buy.get("order_hour")) is int and
          buy["order_hour"] == 0 and type(buy.get("available_from_hour")) is int and
          buy["available_from_hour"] == 1, "BUY_PROTOCOL", "仅h0一笔≤16麦，h1可用")
    _need(buy["qty"] != 0 or buy["estimated_cash"] == 0, "BUY_CASH", "零采购不能计采购现金")
    _need(_int(p.get("feed_units"), 0, 16), "FEED_LIMIT", "当日feed必须≤16")
    goods = _stock(p.get("expected_goods"), "expected_goods", PRODUCTS)
    assets, board = {}, {}
    _need(isinstance(p.get("start_farm_tiles"), list), "ASSETS", "资产列表")
    for row in p["start_farm_tiles"]:
        _need(isinstance(row, dict) and _pos(row.get("pos")), "ASSET_POS", "资产坐标")
        pos, tile, aid = tuple(row["pos"]), row.get("tile"), row.get("asset_id")
        _need(isinstance(aid, str) and isinstance(tile, dict), "ASSET_STATE", "未知/null/LOCKED不能作为活动资产")
        _need(aid not in assets and pos not in board, "DUPLICATE_ASSET", aid)
        _need(_int(tile.get("yield_units")), "TILE_YIELD", aid)
        if "animal" in tile:
            a = tile["animal"]
            _need(a in ANIMALS and tile.get("kind") == ANIMALS[a][0], "ANIMAL", aid)
            _need(_int(tile.get("placed_day"), 0, day) and _int(tile.get("pending_care_bonus")) and
                  _int(tile.get("consecutive_unfed")) and tile["yield_units"] <= ANIMALS[a][2], "ANIMAL_STATE", aid)
            _need(all(type(tile.get(k)) is bool for k in ("fed_today", "cared_today", "fertilizer_available")), "ANIMAL_FLAGS", aid)
        else:
            c = tile.get("crop")
            _need(tile.get("kind") == "PLANT" and c in CROPS, "PLANT", aid)
            _need(_int(tile.get("planted_day"), 0, day) and _int(tile.get("consecutive_unwatered")) and
                  _int(tile.get("fertilized_until_day"), -1) and _int(tile.get("max_lifespan_step"), -1) and
                  type(tile.get("watered_today")) is bool and tile["yield_units"] <= CROPS[c][3], "PLANT_STATE", aid)
            mls = tile["max_lifespan_step"]
            _need(mls < 0 or mls >= day * 24, "EXPIRED_ASSET", aid)
        _need(aid == _identity(tile, pos), "ASSET_IDENTITY", aid)
        assets[aid] = {"pos": pos, "tile": copy.deepcopy(tile)}
        board[pos] = aid
    services, field_keys = {}, set()
    source_goods, delivery_goods, feed_count = Counter(), Counter(), 0
    _need(isinstance(p.get("services"), list), "SERVICES", "服务列表")
    for s in p["services"]:
        _need(isinstance(s, dict), "SERVICE_TYPE", "服务对象")
        sid, aid, op = s.get("service_id"), s.get("asset_id"), s.get("op")
        _need(isinstance(sid, str) and sid and sid not in services, "DUPLICATE_SERVICE", str(sid))
        _need(isinstance(aid, str) and aid in assets, "SERVICE_ASSET", sid)
        _need(_int(s.get("release"), 0, end) and _int(s.get("deadline"), s["release"], end), "SERVICE_WINDOW", sid)
        req, gives = _stock(s.get("requires"), sid + "/requires", PRODUCTS), _stock(s.get("gives"), sid + "/gives", PRODUCTS)
        deps = s.get("dependencies")
        _need(isinstance(deps, list) and all(isinstance(x, str) for x in deps) and len(deps) == len(set(deps)), "DEPENDENCIES", sid)
        if op == "PLACE":
            item = s.get("item")
            _need(s.get("pos") is None and item in PRODUCTS and _int(s.get("qty"), 1) and
                  s.get("splittable") is True and req == Counter({item: s["qty"]}) and not gives and deps, "DELIVERY_SCHEMA", sid)
            delivery_goods[item] += s["qty"]
        else:
            _need(op in FIELDS and _pos(s.get("pos")) and tuple(s["pos"]) == assets[aid]["pos"] and
                  s.get("item") is None and type(s.get("qty")) is int and s["qty"] == 1 and
                  s.get("splittable") is False, "FIELD_SCHEMA", sid)
            key = (aid, op)
            _need(key not in field_keys, "DUPLICATE_FIELD_OPERATION", sid)
            field_keys.add(key)
            tile = assets[aid]["tile"]
            _need(req == (Counter({"WHEAT": 1}) if op == "FEED" else Counter()), "FIELD_REQUIREMENT", sid)
            if op in ("WATER", "FEED", "CARE"):
                _need(not gives, "FIELD_GIVES", sid)
            elif op == "COLLECT_FERTILIZER":
                _need(gives == Counter({"FERTILIZER": 1}), "FIELD_GIVES", sid)
            elif op == "HARVEST":
                product = ANIMALS[tile["animal"]][1] if "animal" in tile else tile["crop"]
                _need(set(gives) == {product} and gives[product] > 0, "FIELD_GIVES", sid)
            if op == "WATER":
                _need(tile.get("kind") == "PLANT" and not tile["watered_today"], "WATER_ELIGIBILITY", sid)
            if op in ("FEED", "CARE", "COLLECT_FERTILIZER"):
                _need("animal" in tile, "ANIMAL_SERVICE", sid)
                flag = {"FEED": "fed_today", "CARE": "cared_today", "COLLECT_FERTILIZER": "fertilizer_available"}[op]
                _need(tile[flag] == (op == "COLLECT_FERTILIZER"), "ANIMAL_SERVICE_FLAG", sid)
            if tile.get("kind") == "PLANT" and tile["max_lifespan_step"] >= 0:
                _need(s["deadline"] <= tile["max_lifespan_step"] - day * 24, "LIFESPAN_DEADLINE", sid)
            source_goods.update(gives)
            feed_count += op == "FEED"
        services[sid] = copy.deepcopy(s)
        services[sid]["requires"] = dict(req)
        services[sid]["gives"] = dict(gives)
    _need(source_goods == goods == delivery_goods, "GOODS_COVERAGE", "预期产出、田间来源和交付数量必须一致")
    _need(feed_count == p["feed_units"], "FEED_COVERAGE", "feed计数与服务一致")
    for sid, s in services.items():
        _need(all(x in services and x != sid for x in s["dependencies"]), "UNKNOWN_DEPENDENCY", sid)
        if s["op"] == "PLACE":
            _need(all(services[x]["op"] in ("HARVEST", "COLLECT_FERTILIZER") and
                      services[x]["gives"].get(s["item"], 0) > 0 for x in s["dependencies"]), "DELIVERY_SOURCE", sid)
    visited, visiting = set(), set()
    def visit(sid):
        _need(sid not in visiting, "DEPENDENCY_CYCLE", sid)
        if sid in visited:
            return
        visiting.add(sid)
        for dep in services[sid]["dependencies"]:
            visit(dep)
        visiting.remove(sid); visited.add(sid)
    for sid in services:
        visit(sid)
    return day, end, shed, reserve, assets, board, services


def _run(p, c):
    day, end, shed, reserve, assets, board, services = _validate_problem(p)
    _need(isinstance(c, dict) and c.get("schema") == "r10-future-day-certificate-v1", "CERTIFICATE_SCHEMA", "schema")
    _need(c.get("status") == "FEASIBLE", "NO_CERTIFICATE", "未找到证书不等于通过")
    _need(c.get("problem_sha256") == canonical_hash(p), "PROBLEM_HASH", "问题摘要不符")
    n = c.get("n_hands")
    _need(_int(n, 0, 12), "HAND_COUNT", "0..12整数")
    _need(c.get("reason") is None and _cash(c.get("hire_cost")), "CERTIFICATE_METADATA", "成功证书元数据")
    _need(isinstance(c.get("actions"), list) and isinstance(c.get("markets"), list), "SCHEDULE_TYPE", "动作和市场列表")
    actions, keys = {}, []
    for row in c["actions"]:
        _need(isinstance(row, dict) and _int(row.get("hour"), 0, end) and _int(row.get("unit"), 0, n), "ACTION_SLOT", "非法时槽或unit")
        key = row["hour"], row["unit"]
        _need(key not in actions, "DUPLICATE_SLOT", str(key))
        _need(isinstance(row.get("action"), list) and row["action"] and isinstance(row["action"][0], str) and
              isinstance(row.get("service_allocations"), list), "ACTION_SCHEMA", str(key))
        actions[key] = row; keys.append(key)
    _need(keys == sorted(keys), "ACTION_ORDER", "须按hour/unit排序")
    markets = {}
    for row in c["markets"]:
        _need(isinstance(row, dict) and _int(row.get("hour"), 0, end) and row["hour"] not in markets and
              isinstance(row.get("orders"), list) and len(row["orders"]) <= 10, "MARKET_SLOT", "市场记录或10订单槽")
        markets[row["hour"]] = row["orders"]
    _need([r["hour"] for r in c["markets"]] == list(range(end + 1)), "MARKET_COVERAGE", "每小时精确一条市场记录")
    positions = {0: (4, 4)}
    inventories, lots = {0: Counter()}, {0: Counter()}
    completed, done_qty, visited_slots = set(), Counter(), set()
    receipts, market_events, hires = [], [], []
    action_counts, sold, purchased, delivered, consumed = Counter(), Counter(), Counter(), Counter(), Counter()
    hire_cost, total_buy = 0, 0

    def take(unit, item, qty):
        _need(inventories[unit][item] >= qty, "MATERIAL_SHORTFALL", f"unit{unit} {item} need{qty}")
        tagged = sum(v for (source, product), v in lots[unit].items() if product == item)
        untagged = inventories[unit][item] - tagged
        left = max(0, qty - untagged)
        for key in sorted(lots[unit]):
            if key[1] == item and left:
                q = min(lots[unit][key], left); lots[unit][key] -= q; left -= q
        inventories[unit][item] -= qty

    for hour in range(end + 1):
        # 市场产生的新工只在下个hour出现在positions里；本hour先走全部旧unit。
        for unit in sorted(positions):
            key = hour, unit
            _need(key in actions, "MISSING_SLOT", str(key))
            visited_slots.add(key)
            row = actions[key]; action = row["action"]; op = action[0]
            alloc = row["service_allocations"]
            _need(all(isinstance(a, dict) and isinstance(a.get("service_id"), str) and
                      a["service_id"] in services and _int(a.get("qty"), 1) for a in alloc), "ALLOCATION_SCHEMA", str(key))
            _need(len({a["service_id"] for a in alloc}) == len(alloc), "DUPLICATE_ALLOCATION", str(key))
            _need(hour != 0 or unit != 0 or action == ["PASS"], "FARMER_H0", "农夫h0必须PASS")
            pos = positions[unit]
            if op in MOVES or op == "PASS":
                _need(len(action) == 1 and not alloc, "NON_SERVICE_ALLOCATION", str(key))
                if op in MOVES:
                    dx, dy = MOVES[op]; dest = pos[0] + dx, pos[1] + dy
                    _need(all(0 <= v < 10 for v in dest), "MOVE_BOUNDS", str(key))
                    positions[unit] = dest
            elif op == "PICKUP":
                _need(len(action) == 3 and action[1] in PRODUCTS and _int(action[2], 1) and not alloc,
                      "PICKUP_SCHEMA", str(key))
                item, qty = action[1:]
                _need(pos in ACCESS, "PICKUP_LOCATION", str(key))
                _need(item != "WHEAT" or qty <= 4, "R9_PICKUP_LIMIT", str(key))
                _need(shed[item] >= qty, "PICKUP_PARTIAL", str(key))
                shed[item] -= qty; inventories[unit][item] += qty
            elif op == "PLACE":
                _need(len(action) == 3 and action[1] in PRODUCTS and _int(action[2], 1) and pos in ACCESS, "PLACE_SCHEMA", str(key))
                item, requested = action[1:]
                actual = min(requested, inventories[unit][item], 100 - sum(shed.values()))
                _need(actual > 0 and sum(a["qty"] for a in alloc) == actual, "PLACE_ACTUAL_QUANTITY", str(key))
                # 分配量核销执行者真实采收来源，不能拿日初同品或别人的货代替。
                for a in alloc:
                    sid, qty = a["service_id"], a["qty"]; s = services[sid]
                    _need(s["op"] == "PLACE" and s["item"] == item and s["release"] <= hour <= s["deadline"], "PLACE_SERVICE", sid)
                    _need(all(d in completed for d in s["dependencies"]), "DEPENDENCY_NOT_DONE", sid)
                    _need(done_qty[sid] + qty <= s["qty"], "OVER_DELIVERY", sid)
                    remaining = qty
                    for source in sorted(s["dependencies"]):
                        lotkey = source, item
                        q = min(lots[unit][lotkey], remaining); lots[unit][lotkey] -= q; remaining -= q
                    _need(remaining == 0, "DELIVERY_PROVENANCE", sid)
                    done_qty[sid] += qty
                    if done_qty[sid] == s["qty"]:
                        completed.add(sid)
                inventories[unit][item] -= actual; shed[item] += actual; delivered[item] += actual
            elif op in FIELDS:
                _need(len(action) == 1 and len(alloc) == 1 and alloc[0]["qty"] == 1, "FIELD_ALLOCATION", str(key))
                sid = alloc[0]["service_id"]; s = services[sid]
                _need(s["op"] == op and sid not in completed and tuple(s["pos"]) == pos, "FIELD_TARGET_OR_REPEAT", sid)
                _need(s["release"] <= hour <= s["deadline"], "FIELD_DEADLINE", sid)
                _need(all(d in completed for d in s["dependencies"]), "DEPENDENCY_NOT_DONE", sid)
                aid = board.get(pos); tile = assets[aid]["tile"] if aid else None
                _need(aid == s["asset_id"] and isinstance(tile, dict), "FIELD_ASSET_GONE", sid)
                gives = Counter()
                if op == "WATER":
                    _need(tile.get("kind") == "PLANT" and not tile["watered_today"], "WATER_NO_EFFECT", sid)
                    tile["watered_today"] = True
                    first, last, interval, cap = CROPS[tile["crop"]]
                    age = day - tile["planted_day"]
                    if not interval and (last + 1) // 2 <= age <= last:
                        tile["yield_units"] = min(cap, tile["yield_units"] + (2 if tile["fertilized_until_day"] >= day else 1))
                elif op == "FEED":
                    _need("animal" in tile and not tile["fed_today"], "FEED_NO_EFFECT", sid)
                    take(unit, "WHEAT", 1); consumed["WHEAT"] += 1; tile["fed_today"] = True
                elif op == "CARE":
                    _need("animal" in tile and not tile["cared_today"], "CARE_NO_EFFECT", sid)
                    tile["cared_today"] = True
                elif op == "COLLECT_FERTILIZER":
                    _need("animal" in tile and tile["fertilizer_available"], "COLLECT_NO_EFFECT", sid)
                    tile["fertilizer_available"] = False; gives["FERTILIZER"] = 1
                elif op == "HARVEST":
                    _need(tile.get("yield_units", 0) > 0, "HARVEST_EMPTY", sid)
                    if tile.get("kind") == "PLANT":
                        first, last, interval, cap = CROPS[tile["crop"]]
                        _need(day - tile["planted_day"] >= first, "HARVEST_IMMATURE", sid)
                        gives[tile["crop"]] = tile["yield_units"]; tile["yield_units"] = 0
                        if not interval:
                            assets[aid]["tile"] = None
                    else:
                        _need("animal" in tile, "HARVEST_NOT_PRODUCTIVE", sid)
                        gives[ANIMALS[tile["animal"]][1]] = tile["yield_units"]; tile["yield_units"] = 0
                _need(gives == Counter(s["gives"]), "ACTUAL_GIVES_MISMATCH", sid)
                for item, qty in gives.items():
                    inventories[unit][item] += qty; lots[unit][(sid, item)] += qty
                completed.add(sid); done_qty[sid] = 1
            else:
                raise Invalid("UNSUPPORTED_ACTION", str(action))
            action_counts[op] += 1
            receipts.append({"hour": hour, "unit": unit, "action": copy.deepcopy(action),
                             "allocations": copy.deepcopy(alloc)})
        hour_hires, hour_buy = 0, 0
        for order in markets[hour]:
            _need(isinstance(order, list) and order and isinstance(order[0], str), "ORDER_SCHEMA", str(hour))
            op = order[0]
            if op == "HIRE":
                _need(len(order) == 1 and hour in (0, 1) and len(positions) - 1 < n, "HIRE_WINDOW", str(hour))
                _need(hour != 0 or hour_hires < 9, "H0_HIRE_LIMIT", str(hour))
                occ = Counter(positions.values())
                spawn = min(ACCESS, key=lambda xy: (occ[xy], ACCESS.index(xy)))
                index = len(positions); cost = _fib(index - 1)
                positions[index] = spawn; inventories[index] = Counter(); lots[index] = Counter()
                hire_cost += cost; hour_hires += 1
                hires.append({"unit": index, "order_hour": hour, "available_from_hour": hour + 1,
                              "spawn": list(spawn), "cost": cost})
            elif op == "BUY_PRODUCT":
                _need(len(order) == 3 and order[1] == "WHEAT" and _int(order[2], 1, 16) and hour == 0 and hour_buy == 0,
                      "BUY_ORDER", str(order))
                qty = order[2]
                _need(qty == p["planned_wheat_buy"]["qty"] and sum(shed.values()) + qty <= 100, "BUY_QUANTITY_CAPACITY", str(order))
                shed["WHEAT"] += qty; purchased["WHEAT"] += qty; total_buy += qty; hour_buy += 1
            elif op == "SELL":
                _need(len(order) == 3 and order[1] in PRODUCTS and _int(order[2], 1), "SELL_ORDER", str(order))
                item, requested = order[1:]
                actual = min(shed[item], requested)
                minimum = min(shed[item], reserve[item])
                _need(actual > 0 and shed[item] - actual >= minimum, "RESERVED_SELL", str(order))
                shed[item] -= actual; sold[item] += actual
            else:
                raise Invalid("UNSUPPORTED_ORDER", str(order))
            market_events.append({"hour": hour, "order": copy.deepcopy(order)})
        _need(hour_hires == (min(n, 9) if hour == 0 else max(0, n - 9) if hour == 1 else 0), "HIRE_PLAN", str(hour))
        _need(sum(shed.values()) <= 100, "WAREHOUSE_OVERFLOW", str(hour))
        # 官方在当帧单位与市场动作之后衰减；mls当帧仍可采收。
        absolute = day * 24 + hour
        for asset in assets.values():
            tile = asset["tile"]
            if isinstance(tile, dict) and tile.get("kind") == "PLANT":
                mls = tile["max_lifespan_step"]
                if mls >= 0 and absolute >= mls and (absolute - mls) % 2 == 0:
                    tile["yield_units"] -= 1
                    if tile["yield_units"] <= 0:
                        asset["tile"] = {"kind": "WEED"}
    _need(visited_slots == set(actions), "PREBIRTH_OR_EXTRA_SLOT", "含出生前或额外unit时槽")
    _need(total_buy == p["planned_wheat_buy"]["qty"], "BUY_COVERAGE", "原计划采购必须精确落实")
    _need(len(positions) == n + 1 and c["hire_cost"] == hire_cost, "HIRE_COST", "实际FIB费用不符")
    _need(completed == set(services), "MISSING_SERVICE", str(sorted(set(services) - completed)))
    reported = c.get("scheduled_service_ids")
    _need(isinstance(reported, list) and all(isinstance(x, str) for x in reported) and
          len(reported) == len(set(reported)) and set(reported) == completed, "FORGED_COMPLETION", "scheduled字段不符真实动作")
    terminal = c.get("terminal_positions")
    _need(isinstance(terminal, dict) and all(_pos(v) for v in terminal.values()) and
          terminal == {str(u): list(pos) for u, pos in positions.items()}, "TERMINAL_POSITION", "终点不符动作")
    if "terminal_shed" in c:
        reported_shed = _stock(c["terminal_shed"], "terminal_shed", PRODUCTS | set(ANIMALS))
        _need(_plain(reported_shed) == _plain(shed), "TERMINAL_SHED", "证书仓存不符重演")
    if "terminal_inventories" in c:
        reported_invs = c["terminal_inventories"]
        _need(isinstance(reported_invs, list) and len(reported_invs) == n + 1,
              "TERMINAL_INVENTORIES", "证书背包列表长度")
        _need(all(_plain(_stock(inv, f"terminal_inventory/{u}", PRODUCTS)) == _plain(inventories[u])
                  for u, inv in enumerate(reported_invs)), "TERMINAL_INVENTORIES", "证书背包不符重演")
    if "remaining_service_quantities" in c:
        _need(c["remaining_service_quantities"] == {} and isinstance(c["remaining_service_quantities"], dict),
              "TERMINAL_REMAINING", "成功证书不应有剩余服务")
    harvested = Counter()
    for s in services.values():
        if s["op"] in FIELDS:
            harvested.update(s["gives"])
    lhs = Counter(p["start_shed"]) + purchased + harvested
    rhs = shed + sold + consumed
    for inv in inventories.values():
        rhs.update(inv)
    _need(lhs == rhs, "RESOURCE_IDENTITY", "库存+买入+采收=终存+卖出+消耗")
    eod_shed, overflow = Counter(shed), Counter()
    if day != 29:
        for unit in sorted(inventories):
            for item, qty in inventories[unit].items():
                put = min(qty, max(0, 100 - sum(eod_shed.values())))
                eod_shed[item] += put; overflow[item] += qty - put
    return {"cash_feasibility": "CONDITIONAL_EXTERNAL_FUNDING_CHECK",
            "future_state_status": "CONDITIONAL_NOT_ACTUAL_OBSERVATION",
            "coverage_scope": "SUPPLIED_PORTFOLIO_AND_SERVICES_ONLY",
            "day": day, "hours": end + 1, "unit_actions": len(actions), "action_counts": dict(action_counts),
            "completed_service_count": len(completed), "completed_service_ids": sorted(completed),
            "delivered_goods": _plain(delivered), "harvested_goods": _plain(harvested),
            "purchased_goods": _plain(purchased), "sold_goods": _plain(sold), "consumed_goods": _plain(consumed),
            "hire_cost": hire_cost, "hires": hires, "resource_identity": True,
            "terminal_positions": terminal, "terminal_shed": _plain(shed),
            "terminal_inventories": {str(u): _plain(inv) for u, inv in inventories.items()},
            "conditional_eod_shed": _plain(eod_shed) if day != 29 else None,
            "conditional_eod_overflow": _plain(overflow),
            "service_receipts": receipts, "market_events": market_events,
            "sales_cash": None, "planned_wheat_cash_condition": p["planned_wheat_buy"]["estimated_cash"]}


def check_day(problem, certificate):
    """失败返回首个明确反例；不修改传入对象、不推断调度失败等于无解。"""
    try:
        stats = _run(copy.deepcopy(problem), copy.deepcopy(certificate))
        return {"valid": True, "errors": [], "stats": stats}
    except Invalid as exc:
        return {"valid": False, "errors": [{"code": exc.code, "detail": exc.detail}], "stats": {}}
    except (KeyError, TypeError, ValueError, OverflowError, RecursionError) as exc:
        return {"valid": False, "errors": [{"code": "MALFORMED_INPUT", "detail": str(exc)}], "stats": {}}
