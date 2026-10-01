"""V125-R10 原型：仅以完整条件路线解除原未来劳动拒绝；R9资金、评分与执行同谱系保留。尚未冻结。"""
from __future__ import annotations
import math
from collections import Counter
CANDIDATE_ID = 'V125-R10-PROTOTYPE'
PARAMS = {'cash_funding': 'cash_prefix', 'router': 'adaptive', 'investment_selection': 'terminal_net', 'task_cost': 'full', 'care_weight': 1.0, 'max_hands': 12, 'forecast_days': 6, 'early_animals': 4, 'r10_route_mode': 'future_failure_certificate'}
CROPS = {'WHEAT': (10, 2, 4, 0, 6), 'CARROT': (20, 2, 3, 0, 4), 'TOMATO': (50, 8, 8, 1, 4), 'STRAWBERRY': (100, 10, 10, 2, 4), 'MELON': (80, 10, 12, 0, 6)}
ANIMALS = {'GOOSE': (300, 'COOP', 4, 1, 4, 'EGG'), 'COW': (400, 'PASTURE', 8, 2, 6, 'MILK'), 'SHEEP': (500, 'PASTURE', 6, 3, 6, 'WOOL')}
PRODUCTS = tuple(CROPS) + ('EGG', 'MILK', 'WOOL', 'FERTILIZER')
MARKET = {'WHEAT': (25, 400, 'sqrt', 0.8, 'log', 0.2), 'CARROT': (35, 450, 'hinge', 1.0, 'sqrt', 0.7), 'TOMATO': (60, 200, 'hinge', 0.4, 'sqrt', 0.6), 'STRAWBERRY': (120, 100, 'sqrt', 0.7, 'linear', 1.6), 'MELON': (250, 300, 'log', 0.2, 'sq', 3.6), 'EGG': (50, 332, 'hinge', 0.4, 'log', 0.2), 'MILK': (160, 122, 'sqrt', 0.6, 'linear', 1.6), 'WOOL': (200, 105, 'log', 0.2, 'sq', 3.2), 'FERTILIZER': (100, 200, 'linear', 0.4, 'linear', 0.4)}
SHOPS = {'BAKERY': ('EGG', 'WHEAT'), 'PIZZA_SHOP': ('MILK', 'TOMATO', 'WHEAT'), 'BRUNCH_SPOT': ('EGG', 'WHEAT', 'STRAWBERRY'), 'YARN_STORE': ('WOOL',), 'ICE_CREAM_SHOP': ('STRAWBERRY', 'MILK', 'WHEAT'), 'PET_CAFE': ('CARROT',), 'SMOOTHIE_SHOP': ('STRAWBERRY', 'MILK'), 'FARMERS_MARKET': ('WHEAT', 'CARROT', 'TOMATO', 'STRAWBERRY')}
ACCESS = ((4, 4), (5, 4), (4, 5), (5, 5))
FIB = (1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610)
_STATES = {}
'R10 B future service compiler. Frozen R9 economic calendar lineage; no candidate imports.\n\nOnly adds service/state diagnostics at original calendar accumulation points.\nThe legacy goods/work/feed values are preserved. Future state is conditional on\nlegacy timely care and delivery, never an observation or execution receipt.\n'
from collections import Counter as _r10_calendar_compiler_Counter
from copy import deepcopy as _r10_calendar_compiler_deepcopy
import hashlib as _r10_calendar_compiler_hashlib
import json as _r10_calendar_compiler_json
import math as _r10_calendar_compiler_math
_r10_calendar_compiler_PARENT_SOURCE_SHA256 = 'e7f1fd549fc67ccec74015299af5366812abe43ec78c4142bb019429b6bb22e0'
_r10_calendar_compiler_CROPS = {'WHEAT': (10, 2, 4, 0, 6), 'CARROT': (20, 2, 3, 0, 4), 'TOMATO': (50, 8, 8, 1, 4), 'STRAWBERRY': (100, 10, 10, 2, 4), 'MELON': (80, 10, 12, 0, 6)}
_r10_calendar_compiler_ANIMALS = {'GOOSE': (300, 'COOP', 4, 1, 4, 'EGG'), 'COW': (400, 'PASTURE', 8, 2, 6, 'MILK'), 'SHEEP': (500, 'PASTURE', 6, 3, 6, 'WOOL')}
_r10_calendar_compiler_ACCESS = ((4, 4), (5, 4), (4, 5), (5, 5))
_r10_calendar_compiler_FIELD_OPS = {'WATER', 'FEED', 'CARE', 'HARVEST', 'COLLECT_FERTILIZER'}

def _r10_calendar_compiler_canonical_sha(value):
    return _r10_calendar_compiler_hashlib.sha256(_r10_calendar_compiler_json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()

def _r10_calendar_compiler_dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def _r10_calendar_compiler_home(pos):
    return min(_r10_calendar_compiler_ACCESS, key=lambda q: (_r10_calendar_compiler_dist(pos, q), q))

def _r10_calendar_compiler_project_calendar_with_services(tile, day, hour=0, position=(4, 4), source=None):
    """每日照护、及时采收交付的模型日历；物量可用纯规则控制核对。"""
    goods, work, feed = ({}, _r10_calendar_compiler_Counter(), _r10_calendar_compiler_Counter())
    raw_services = {}
    t = dict(tile)
    distance = _r10_calendar_compiler_dist(position, _r10_calendar_compiler_home(position))

    def product(d, item, qty):
        qty = int(qty)
        if qty <= 0 or d > 29:
            return
        if d == 29 and day == 29 and (hour + distance + 2 > 22):
            return
        goods.setdefault(d, _r10_calendar_compiler_Counter())[item] += qty
        raw_services.setdefault(d, []).append({'op': 'COLLECT_FERTILIZER' if item == 'FERTILIZER' else 'HARVEST', 'requires': {}, 'gives': {item: qty}})
        work[d] += 2 + distance
    if 'animal' in t:
        a = t['animal']
        spec = _r10_calendar_compiler_ANIMALS[a]
        product(day, spec[5], t.get('yield_units', 0))
        if t.get('fertilizer_available'):
            product(day, 'FERTILIZER', 1)
        pending = int(t.get('pending_care_bonus', 0))
        for d in range(day, 29):
            fed = bool(t.get('fed_today')) if d == day else False
            cared = bool(t.get('cared_today')) if d == day else False
            if not fed:
                raw_services.setdefault(d, []).append({'op': 'FEED', 'requires': {'WHEAT': 1}, 'gives': {}})
                work[d] += 1
                feed[d] += 1
            if d < 28 and (not cared):
                raw_services.setdefault(d, []).append({'op': 'CARE', 'requires': {}, 'gives': {}})
                work[d] += 1
                cared = True
            next_day = d + 1
            age = next_day - t['placed_day'] - spec[2]
            if age >= 0 and age % spec[3] == 0:
                product(next_day, spec[5], min(spec[4], 1 + pending))
                pending = 0
            if cared:
                pending += 1
            product(next_day, 'FERTILIZER', 1)
    else:
        c = t['crop']
        _, first, last, interval, cap = _r10_calendar_compiler_CROPS[c]
        stock = int(t.get('yield_units', 0))
        dry = int(t.get('consecutive_unwatered', 0))
        for d in range(day, 30):
            age = d - t['planted_day']
            if age < 0:
                continue
            fertilized = t.get('fertilized_until_day', -1) >= d
            watered = bool(t.get('watered_today')) if d == day else False
            if interval:
                final_age = first + interval * (cap - 1)
                next_produces = age + 1 >= first and (age + 1 - first) % interval == 0 and (age + 1 <= final_age)
                need = not watered and d < 29 and (age < final_age) and (dry >= 1 or next_produces or age == 0)
            else:
                growth = (last + 1) // 2 <= age <= last
                need = not watered and age <= last and (dry >= 1 or growth or age == 0)
            if need:
                raw_services.setdefault(d, []).append({'op': 'WATER', 'requires': {}, 'gives': {}})
                work[d] += 1
                watered = True
                if not interval and growth:
                    stock = min(cap, stock + (2 if fertilized else 1))
            if stock and age >= first and (interval or stock >= cap or age >= last or (d == 29)):
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
            if interval and age >= final_age and (not stock):
                break
    for d in list(work):
        if work[d]:
            work[d] += max(1, distance)
    legacy = {'goods': {d: dict(v) for d, v in goods.items()}, 'work': dict(work), 'feed': dict(feed)}
    return _r10_calendar_compiler__enrich_calendar(tile, day, hour, position, source, legacy, raw_services)

def _r10_calendar_compiler__asset_identity(tile, pos):
    x, y = pos
    if 'animal' in tile:
        return 'animal:%s:%d:%d,%d' % (tile['animal'], tile['placed_day'], x, y)
    return 'plant:%s:%d:%d,%d' % (tile['crop'], tile['planted_day'], x, y)

def _r10_calendar_compiler__normal_tile(tile):
    t = _r10_calendar_compiler_deepcopy(tile)
    if 'animal' in t:
        a = t['animal']
        if a not in _r10_calendar_compiler_ANIMALS:
            raise ValueError('unknown animal')
        t.setdefault('kind', _r10_calendar_compiler_ANIMALS[a][1])
        for key, value in (('yield_units', 0), ('consecutive_unfed', 0), ('fed_today', False), ('cared_today', False), ('fertilizer_available', False), ('pending_care_bonus', 0)):
            t.setdefault(key, value)
    else:
        c = t['crop']
        if c not in _r10_calendar_compiler_CROPS:
            raise ValueError('unknown crop')
        t.setdefault('kind', 'PLANT')
        for key, value in (('yield_units', 0), ('consecutive_unwatered', 0), ('watered_today', False), ('fertilized_until_day', -1)):
            t.setdefault(key, value)
        t.setdefault('max_lifespan_step', -1 if _r10_calendar_compiler_CROPS[c][3] else (t['planted_day'] + _r10_calendar_compiler_CROPS[c][2] + 1) * 24)
    return t

def _r10_calendar_compiler__apply_model_service(tile, service, day):
    """Conditional timely service, for future tile state only; no actor execution."""
    t = _r10_calendar_compiler_deepcopy(tile)
    op = service['op']
    if not isinstance(t, dict):
        return (t, 'SERVICE_ON_ABSENT_MODEL_ASSET')
    if op == 'WATER':
        if t.get('kind') != 'PLANT' or t.get('watered_today'):
            return (t, 'WATER_MODEL_STATE_CONFLICT')
        t['watered_today'] = True
        c = _r10_calendar_compiler_CROPS[t['crop']]
        age = day - t['planted_day']
        if not c[3] and (c[2] + 1) // 2 <= age <= c[2]:
            t['yield_units'] = min(c[4], t['yield_units'] + (2 if t['fertilized_until_day'] >= day else 1))
    elif op in ('FEED', 'CARE', 'COLLECT_FERTILIZER'):
        if 'animal' not in t:
            return (t, 'ANIMAL_MODEL_STATE_CONFLICT')
        flag = {'FEED': 'fed_today', 'CARE': 'cared_today', 'COLLECT_FERTILIZER': 'fertilizer_available'}[op]
        if op == 'COLLECT_FERTILIZER':
            if not t[flag]:
                return (t, 'FERTILIZER_MODEL_STATE_CONFLICT')
            t[flag] = False
        else:
            if t[flag]:
                return (t, op + '_MODEL_STATE_CONFLICT')
            t[flag] = True
    elif op == 'HARVEST':
        if t.get('kind') == 'PLANT':
            item = t['crop']
            if day - t['planted_day'] < _r10_calendar_compiler_CROPS[item][1]:
                return (t, 'IMMATURE_MODEL_HARVEST')
        elif 'animal' in t:
            item = _r10_calendar_compiler_ANIMALS[t['animal']][5]
        else:
            return (t, 'HARVEST_MODEL_STATE_CONFLICT')
        if service['gives'] != {item: int(t.get('yield_units', 0))} or t.get('yield_units', 0) <= 0:
            return (t, 'HARVEST_MODEL_QUANTITY_CONFLICT')
        t['yield_units'] = 0
        if t.get('kind') == 'PLANT' and (not _r10_calendar_compiler_CROPS[item][3]):
            t = None
    else:
        return (t, 'UNKNOWN_MODEL_SERVICE')
    return (t, None)

def _r10_calendar_compiler__model_next_day(tile, day):
    """Official asset transitions under the explicitly timely service assumption.

    Random empty-cell weeds, shops, money and worker routes are not predicted.
    Daily services above were applied before any known same-day lifespan decay.
    """
    t = _r10_calendar_compiler_deepcopy(tile)
    if not isinstance(t, dict):
        return t
    if t.get('kind') == 'PLANT':
        mls = t['max_lifespan_step']
        if mls >= 0:
            for step in range(day * 24, day * 24 + 24):
                if step >= mls and (step - mls) % 2 == 0:
                    t['yield_units'] -= 1
                    if t['yield_units'] <= 0:
                        return {'kind': 'WEED'}
        watered = t['watered_today']
        t['consecutive_unwatered'] = 0 if watered else t['consecutive_unwatered'] + 1
        t['watered_today'] = False
        if t['consecutive_unwatered'] >= 2:
            return {'kind': 'WEED'}
        c = _r10_calendar_compiler_CROPS[t['crop']]
        if c[3]:
            since = day + 1 - t['planted_day'] - c[1]
            if since >= 0 and since % c[3] == 0:
                count = since // c[3] + 1
                if count <= c[4]:
                    bonus = watered and t['fertilized_until_day'] >= day
                    t['yield_units'] = min(c[4], t['yield_units'] + (2 if bonus else 1))
                    if count == c[4]:
                        t['max_lifespan_step'] = (day + 2) * 24
    elif 'animal' in t:
        a = _r10_calendar_compiler_ANIMALS[t['animal']]
        t['consecutive_unfed'] = 0 if t['fed_today'] else t['consecutive_unfed'] + 1
        if t['consecutive_unfed'] >= 2:
            return {'kind': a[1]}
        since = day + 1 - t['placed_day'] - a[2]
        if since >= 0 and since % a[3] == 0:
            bonus = t.get('pending_care_bonus', 0) if t['fed_today'] else 0
            t['yield_units'] = min(a[4], t['yield_units'] + 1 + bonus)
            t['pending_care_bonus'] = 0
        if t['cared_today'] and t['fed_today']:
            t['pending_care_bonus'] = t.get('pending_care_bonus', 0) + 1
        t['fertilizer_available'] = True
        t['fed_today'] = False
        t['cared_today'] = False
    return t

def _r10_calendar_compiler__enrich_calendar(tile, day, hour, position, source, legacy, raw_services):
    pos = list(position)
    aid = _r10_calendar_compiler__asset_identity(tile, pos)
    t = _r10_calendar_compiler__normal_tile(tile)
    states, services, unsupported = ({}, {}, {})
    ordering = {'WATER': 0, 'FEED': 1, 'CARE': 2, 'HARVEST': 3, 'COLLECT_FERTILIZER': 4}
    condition = _r10_calendar_compiler_deepcopy(source) if source is not None else {'kind': 'caller_supplied_tile', 'actual_observation_proven': False}
    for d in range(day, 30):
        states[d] = _r10_calendar_compiler_deepcopy(t)
        field = []
        water_id = None
        for event in sorted(raw_services.get(d, []), key=lambda e: ordering[e['op']]):
            op = event['op']
            sid = aid + '/d%d/' % d + op
            release, deadline = (max(0, int(hour)) if d == day else 0, 22 if d == 29 else 23)
            if isinstance(t, dict) and t.get('kind') == 'PLANT':
                mls = t.get('max_lifespan_step', -1)
                if mls >= 0:
                    deadline = min(deadline, mls - d * 24)
            if release > deadline:
                unsupported.setdefault(d, []).append('SERVICE_WINDOW_OR_LIFESPAN_UNSUPPORTED')
            deps = []
            if op == 'HARVEST' and water_id and ('crop' in tile) and (not _r10_calendar_compiler_CROPS[tile['crop']][3]):
                deps.append(water_id)
            service = {'service_id': sid, 'asset_id': aid, 'pos': pos, 'op': op, 'item': None, 'qty': 1, 'release': release, 'deadline': deadline, 'requires': _r10_calendar_compiler_deepcopy(event['requires']), 'gives': _r10_calendar_compiler_deepcopy(event['gives']), 'dependencies': deps, 'splittable': False}
            field.append(service)
            if op == 'WATER':
                water_id = sid
        if len({s['service_id'] for s in field}) != len(field):
            unsupported.setdefault(d, []).append('DUPLICATE_FIELD_SERVICE')
        delivery = []
        for service in field:
            t, conflict = _r10_calendar_compiler__apply_model_service(t, service, d)
            if conflict:
                unsupported.setdefault(d, []).append(conflict)
            for item, qty in service['gives'].items():
                delivery.append({'service_id': service['service_id'] + '/PLACE:' + item, 'asset_id': aid, 'pos': None, 'op': 'PLACE', 'item': item, 'qty': qty, 'release': service['release'], 'deadline': 22 if d == 29 else 23, 'requires': {item: qty}, 'gives': {}, 'dependencies': [service['service_id']], 'splittable': True})
        if field or delivery:
            services[d] = field + delivery
        if d < 29:
            t = _r10_calendar_compiler__model_next_day(t, d)
    return {**legacy, 'asset_id': aid, 'pos': pos, 'services': services, 'state_by_day': states, 'unsupported_by_day': unsupported, 'conditional': [condition, {'kind': 'legacy_timely_care_and_delivery', 'detail': 'Future tiles assume each original calendar service completes; not an execution receipt.'}]}

def _r10_calendar_compiler__integer_quantities(values, label):
    if not isinstance(values, dict):
        raise ValueError(label + ' must be a dict')
    result = {}
    for item, qty in values.items():
        if not isinstance(item, str) or type(qty) is not int or qty < 0:
            raise ValueError(label + ' has invalid quantity')
        if qty:
            result[item] = qty
    return result

def _r10_calendar_compiler_compile_day_problem(calendars, day, current_day, start_shed, reserved_shed, planned_wheat_buy, legacy_work, legacy_hire_cost, conditional=None, startup_fallback_days=None):
    """Compile a requested full future day. No guessing resources from scalar work.

    Completeness of the passed calendar list and funding inputs is a caller
    contract; coverage ids/conditional assumptions are exposed for independent QA.
    """
    if type(day) is not int or type(current_day) is not int or (not 0 <= current_day <= day <= 29):
        raise ValueError('invalid day/current_day')
    reasons, tiles, services, goods, feed = ([], [], [], _r10_calendar_compiler_Counter(), 0)
    source_conditions = _r10_calendar_compiler_deepcopy(conditional or [])
    seen_assets, seen_positions, seen_services = (set(), set(), set())
    if day == current_day:
        reasons.append('CURRENT_DAY_LEGACY')
    if day in (startup_fallback_days or []):
        reasons.append('UNSUPPORTED_STARTUP_FRONTIER')
    for cal in calendars:
        aid = cal['asset_id']
        if aid in seen_assets:
            reasons.append('DUPLICATE_ASSET_CALENDAR')
            continue
        seen_assets.add(aid)
        if day not in cal['state_by_day']:
            if cal['services'].get(day) or cal['goods'].get(day) or cal['feed'].get(day):
                reasons.append('MISSING_CONDITIONAL_ASSET_STATE')
            continue
        tile = _r10_calendar_compiler_deepcopy(cal['state_by_day'][day])
        jobs = _r10_calendar_compiler_deepcopy(cal['services'].get(day, []))
        reasons.extend(cal['unsupported_by_day'].get(day, []))
        active = isinstance(tile, dict) and (tile.get('kind') == 'PLANT' or 'animal' in tile)
        if active:
            p = tuple(cal['pos'])
            if p in seen_positions:
                reasons.append('DUPLICATE_ACTIVE_POSITION')
            seen_positions.add(p)
            tiles.append({'asset_id': aid, 'pos': list(p), 'tile': tile})
        elif jobs:
            reasons.append('SERVICE_ON_MISSING_ACTIVE_ASSET')
        for job in jobs:
            if job['service_id'] in seen_services:
                reasons.append('DUPLICATE_SERVICE')
            seen_services.add(job['service_id'])
            services.append(job)
        goods.update(cal['goods'].get(day, {}))
        feed += int(cal['feed'].get(day, 0))
        source_conditions.extend(_r10_calendar_compiler_deepcopy(cal['conditional']))
    shed = _r10_calendar_compiler__integer_quantities(start_shed, 'start_shed')
    reserved = _r10_calendar_compiler__integer_quantities(reserved_shed, 'reserved_shed')
    buy = _r10_calendar_compiler_deepcopy(planned_wheat_buy)
    if not isinstance(buy, dict) or type(buy.get('qty')) is not int or buy['qty'] < 0:
        raise ValueError('planned_wheat_buy requires a nonnegative integer qty')
    if type(buy.get('estimated_cash')) not in (int, float) or not _r10_calendar_compiler_math.isfinite(buy['estimated_cash']) or buy['estimated_cash'] < 0:
        raise ValueError('planned_wheat_buy requires finite nonnegative estimated_cash')
    if buy.get('order_hour') != 0 or buy.get('available_from_hour') != 1:
        reasons.append('UNSUPPORTED_WHEAT_BUY_TIMING')
    if buy['qty'] == 0 and buy['estimated_cash'] != 0:
        reasons.append('ZERO_BUY_NONZERO_ESTIMATED_CASH')
    if buy['qty'] and buy['estimated_cash'] <= 0:
        reasons.append('FREE_CONDITIONAL_WHEAT_BUY')
    if buy['qty'] > 16 or feed > 16:
        reasons.append('FEED_OR_BUY_ABOVE_STAGE_B_16_LIMIT')
    if sum(shed.values()) > 100:
        reasons.append('START_SHED_OVER_CAPACITY')
    if shed.get('WHEAT', 0) + buy['qty'] < feed:
        reasons.append('CONDITIONAL_WHEAT_SOURCE_SHORTFALL')
    if reserved.get('FERTILIZER', 0) > 12:
        reasons.append('FERTILIZER_RESERVE_ABOVE_LEGACY_CAP')
    derived_goods = _r10_calendar_compiler_Counter()
    derived_feed = 0
    for service in services:
        if service['op'] != 'PLACE':
            derived_goods.update(service['gives'])
            derived_feed += service['requires'].get('WHEAT', 0)
    if derived_goods != goods or derived_feed != feed:
        reasons.append('CALENDAR_SERVICE_QUANTITY_MISMATCH')
    if type(legacy_work) is not int or legacy_work < 0:
        raise ValueError('legacy_work must be nonnegative integer')
    if type(legacy_hire_cost) not in (int, float) or not _r10_calendar_compiler_math.isfinite(legacy_hire_cost) or legacy_hire_cost < 0:
        raise ValueError('legacy_hire_cost must be finite and nonnegative')
    source_conditions.append({'kind': 'conditional_bridge_from_legacy_day', 'detail': 'Only this requested day is certified; prior days retain original R9 gate and timely-care assumptions.'})
    return {'schema': 'r10-future-day-problem-v1', 'status': 'UNSUPPORTED' if reasons else 'SUPPORTED', 'unsupported_reasons': sorted(set(reasons)), 'day': day, 'current_day': current_day, 'end_hour': 22 if day == 29 else 23, 'board_size': 10, 'start_farm_tiles': sorted(tiles, key=lambda t: t['asset_id']), 'start_shed': shed, 'reserved_shed': reserved, 'planned_wheat_buy': buy, 'services': sorted(services, key=lambda s: s['service_id']), 'expected_goods': dict(goods), 'feed_units': feed, 'legacy_work': legacy_work, 'legacy_hire_cost': legacy_hire_cost, 'conditional': source_conditions, 'hire_protocol': {'max_hands': 12, 'farmer_h0_pass': True, 'h0_max_hires': 9, 'h1_remaining_hires': True}, 'capacity': 100}
'未来日完整服务的确定性构造器。结果须经独立checker，非最优性证明。'
import hashlib as _r10_scheduler_hashlib
import json as _r10_scheduler_json
from collections import Counter as _r10_scheduler_Counter, defaultdict as _r10_scheduler_defaultdict
_r10_scheduler_ACCESS = ((4, 4), (5, 4), (4, 5), (5, 5))
_r10_scheduler_PRODUCTS = ('WHEAT', 'CARROT', 'TOMATO', 'STRAWBERRY', 'MELON', 'EGG', 'MILK', 'WOOL', 'FERTILIZER')
_r10_scheduler_PRIORITY = {'WATER': 0, 'FEED': 0, 'HARVEST': 1, 'CARE': 2, 'COLLECT_FERTILIZER': 3}

def _r10_scheduler_distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def _r10_scheduler_nearest_home(pos):
    return min(_r10_scheduler_ACCESS, key=lambda q: (_r10_scheduler_distance(pos, q), q))

def _r10_scheduler_direction(pos, target):
    if pos[0] != target[0]:
        return ['EAST' if target[0] > pos[0] else 'WEST']
    if pos[1] != target[1]:
        return ['SOUTH' if target[1] > pos[1] else 'NORTH']
    return ['PASS']

def _r10_scheduler_canonical_sha(problem):
    raw = _r10_scheduler_json.dumps(problem, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
    return _r10_scheduler_hashlib.sha256(raw.encode()).hexdigest()

def _r10_scheduler_hire_cost(count):
    a, b, result = (1, 1, 0)
    for _ in range(count):
        result += a
        a, b = (b, a + b)
    return result

def _r10_scheduler_schedule_day(problem, n_hands):
    """逐小时构造所有工人、作业、物料和入仓动作；失败保留已构造前缀。"""
    result = {'schema': 'r10-future-day-certificate-v1', 'status': 'NO_CERTIFICATE', 'problem_sha256': _r10_scheduler_canonical_sha(problem), 'n_hands': n_hands, 'actions': [], 'markets': [], 'scheduled_service_ids': [], 'hire_cost': 0, 'terminal_positions': {}, 'reason': None}

    def reject(reason):
        result['reason'] = reason
        return result
    if problem.get('status') != 'SUPPORTED':
        return reject('UNSUPPORTED_PROBLEM')
    if isinstance(n_hands, bool) or not isinstance(n_hands, int) or (not 0 <= n_hands <= 12):
        return reject('INVALID_HAND_COUNT')
    if problem.get('schema') != 'r10-future-day-problem-v1':
        return reject('INVALID_SCHEMA')
    end = problem['end_hour']
    if end != (22 if problem['day'] == 29 else 23):
        return reject('INVALID_END_HOUR')
    services = problem['services']
    by_id = {s['service_id']: s for s in services}
    if len(by_id) != len(services):
        return reject('DUPLICATE_SERVICE_ID')
    if any((s['op'] not in (*_r10_scheduler_PRIORITY, 'PLACE') for s in services)):
        return reject('UNSUPPORTED_SERVICE_OPERATION')
    if any((dep not in by_id for s in services for dep in s['dependencies'])):
        return reject('UNKNOWN_DEPENDENCY')
    if problem['feed_units'] > 16 or problem['planned_wheat_buy']['qty'] > 16:
        return reject('FEED_SCOPE_EXCEEDED')
    field = [s for s in services if s['op'] != 'PLACE']
    deliveries = [s for s in services if s['op'] == 'PLACE']
    groups = _r10_scheduler_defaultdict(list)
    for s in field:
        groups[s['asset_id']].append(s)
    for group in groups.values():
        if len({tuple(s['pos']) for s in group}) != 1:
            return reject('ASSET_POSITION_CONFLICT')
        group.sort(key=lambda s: (s['deadline'], _r10_scheduler_PRIORITY[s['op']], s['service_id']))
    outputs = _r10_scheduler_defaultdict(list)
    source_remaining = {(s['service_id'], item): qty for s in field for item, qty in s['gives'].items()}
    for d in sorted(deliveries, key=lambda s: s['service_id']):
        left = d['qty']
        for dep in sorted(d['dependencies']):
            key = (dep, d['item'])
            take = min(left, source_remaining.get(key, 0))
            if take:
                outputs[dep].append((d['service_id'], d['item'], take))
                source_remaining[key] -= take
                left -= take
        if left:
            return reject('DELIVERY_WITHOUT_FIELD_SOURCE')
    if any(source_remaining.values()):
        return reject('FIELD_OUTPUT_WITHOUT_DELIVERY')
    workers = [{'pos': (4, 4), 'inv': _r10_scheduler_Counter(), 'lots': _r10_scheduler_Counter(), 'target': None}]
    shed = _r10_scheduler_Counter(problem['start_shed'])
    reserved = _r10_scheduler_Counter(problem['reserved_shed'])
    progress = _r10_scheduler_Counter()
    done = set()
    assigned = {}
    total_hired = 0

    def remaining(group_id):
        return [s for s in groups[group_id] if s['service_id'] not in done]

    def ready(s, hour):
        return s['release'] <= hour <= s['deadline'] and all((dep in done for dep in s['dependencies']))

    def wheat_free(w):
        committed = sum((q for sid, q in w['lots'].items() if by_id[sid]['item'] == 'WHEAT'))
        return w['inv'].get('WHEAT', 0) - committed

    def pending_items(w):
        return {by_id[sid]['item'] for sid, q in w['lots'].items() if q > 0}

    def projected_group_cost(w, group):
        pos = tuple(group[0]['pos'])
        steps = _r10_scheduler_distance(w['pos'], pos)
        needed = sum((s['requires'].get('WHEAT', 0) for s in group))
        if needed > wheat_free(w):
            depot = min(_r10_scheduler_ACCESS, key=lambda q: (_r10_scheduler_distance(w['pos'], q) + _r10_scheduler_distance(q, pos), q))
            steps = _r10_scheduler_distance(w['pos'], depot) + 1 + _r10_scheduler_distance(depot, pos)
        output_items = pending_items(w) | {item for s in group for item, qty in s['gives'].items() if qty}
        tail = _r10_scheduler_distance(pos, _r10_scheduler_nearest_home(pos)) + len(output_items) if output_items else 0
        return steps + len(group) + tail

    def free_assignment(w, unit, hour):
        pool = []
        for gid in sorted(groups):
            if gid in assigned:
                continue
            rem = remaining(gid)
            if not rem:
                continue
            cost = projected_group_cost(w, rem)
            deadline = min((s['deadline'] for s in rem))
            if hour + cost - 1 > end:
                continue
            if not any((ready(s, hour) or s['release'] > hour for s in rem)):
                continue
            pool.append(((deadline, cost, _r10_scheduler_distance(w['pos'], rem[0]['pos']), gid), gid))
        if pool:
            gid = min(pool)[1]
            assigned[gid] = unit
            w['target'] = gid

    def move_worker(w, action):
        x, y = w['pos']
        delta = {'EAST': (1, 0), 'WEST': (-1, 0), 'SOUTH': (0, 1), 'NORTH': (0, -1)}[action[0]]
        w['pos'] = (x + delta[0], y + delta[1])

    def delivery_action(w, hour):
        eligible = []
        for sid, qty in w['lots'].items():
            if qty and ready(by_id[sid], hour):
                eligible.append(sid)
        if not eligible:
            return (['PASS'], [])
        if w['pos'] not in _r10_scheduler_ACCESS:
            action = _r10_scheduler_direction(w['pos'], _r10_scheduler_nearest_home(w['pos']))
            move_worker(w, action)
            return (action, [])
        room = problem['capacity'] - sum(shed.values())
        if room <= 0:
            return (['PASS'], [])
        item = min({by_id[sid]['item'] for sid in eligible}, key=lambda p: (min((by_id[sid]['deadline'] for sid in eligible if by_id[sid]['item'] == p)), p))
        allocations, total = ([], 0)
        for sid in sorted(eligible):
            if by_id[sid]['item'] != item:
                continue
            take = min(room - total, w['lots'][sid])
            if take:
                allocations.append({'service_id': sid, 'qty': take})
                total += take
            if total == room:
                break
        if not total:
            return (['PASS'], [])
        w['inv'][item] -= total
        shed[item] += total
        for alloc in allocations:
            sid, qty = (alloc['service_id'], alloc['qty'])
            w['lots'][sid] -= qty
            progress[sid] += qty
            if progress[sid] == by_id[sid]['qty']:
                done.add(sid)
        return (['PLACE', item, total], allocations)
    for hour in range(end + 1):
        for unit, w in enumerate(workers):
            action, allocations = (['PASS'], [])
            if not (hour == 0 and unit == 0):
                gid = w['target']
                if gid and (not remaining(gid)):
                    w['target'] = None
                    assigned.pop(gid, None)
                if w['target'] is None:
                    free_assignment(w, unit, hour)
                gid = w['target']
                if gid:
                    rem = remaining(gid)
                    available = [s for s in rem if ready(s, hour)]
                    if available:
                        s = min(available, key=lambda q: (q['deadline'], _r10_scheduler_PRIORITY[q['op']], q['service_id']))
                        target = tuple(s['pos'])
                        need = s['requires'].get('WHEAT', 0)
                        if need > wheat_free(w):
                            depot = min(_r10_scheduler_ACCESS, key=lambda q: (_r10_scheduler_distance(w['pos'], q) + _r10_scheduler_distance(q, target), q))
                            if w['pos'] != depot:
                                action = _r10_scheduler_direction(w['pos'], depot)
                                move_worker(w, action)
                            elif shed.get('WHEAT', 0) >= need - wheat_free(w):
                                qty = need - wheat_free(w)
                                action = ['PICKUP', 'WHEAT', qty]
                                shed['WHEAT'] -= qty
                                w['inv']['WHEAT'] += qty
                        elif w['pos'] != target:
                            action = _r10_scheduler_direction(w['pos'], target)
                            move_worker(w, action)
                        elif all((w['inv'].get(item, 0) >= qty for item, qty in s['requires'].items())):
                            action = [s['op']]
                            allocations = [{'service_id': s['service_id'], 'qty': 1}]
                            for item, qty in s['requires'].items():
                                w['inv'][item] -= qty
                            for item, qty in s['gives'].items():
                                w['inv'][item] += qty
                            for sid, _, qty in outputs[s['service_id']]:
                                w['lots'][sid] += qty
                            progress[s['service_id']] = 1
                            done.add(s['service_id'])
                else:
                    action, allocations = delivery_action(w, hour)
            result['actions'].append({'hour': hour, 'unit': unit, 'action': action, 'service_allocations': allocations})
        orders = []
        hires = min(n_hands, 9) if hour == 0 else n_hands - total_hired if hour == 1 else 0
        for _ in range(hires):
            occupancy = _r10_scheduler_Counter((w['pos'] for w in workers))
            spawn = min(_r10_scheduler_ACCESS, key=lambda p: (occupancy[p], _r10_scheduler_ACCESS.index(p)))
            workers.append({'pos': spawn, 'inv': _r10_scheduler_Counter(), 'lots': _r10_scheduler_Counter(), 'target': None})
            total_hired += 1
            orders.append(['HIRE'])
        if hour == 0 and problem['planned_wheat_buy']['qty']:
            qty = problem['planned_wheat_buy']['qty']
            if sum(shed.values()) + qty > problem['capacity']:
                return reject('PLANNED_BUY_EXCEEDS_SHED')
            orders.append(['BUY_PRODUCT', 'WHEAT', qty])
            shed['WHEAT'] += qty
        for item in _r10_scheduler_PRODUCTS:
            qty = max(0, shed.get(item, 0) - reserved.get(item, 0))
            if item == 'WHEAT':
                needed = sum((s['requires'].get('WHEAT', 0) for s in field if s['service_id'] not in done))
                available_carried = sum((max(0, wheat_free(w)) for w in workers))
                qty = min(qty, max(0, shed.get(item, 0) - max(0, needed - available_carried)))
            if qty and len(orders) < 10:
                orders.append(['SELL', item, qty])
                shed[item] -= qty
        result['markets'].append({'hour': hour, 'orders': orders})
    result['scheduled_service_ids'] = sorted(done)
    result['hire_cost'] = _r10_scheduler_hire_cost(total_hired)
    result['terminal_positions'] = {str(i): list(w['pos']) for i, w in enumerate(workers)}
    result['terminal_shed'] = dict(shed)
    result['terminal_inventories'] = [dict(w['inv']) for w in workers]
    result['remaining_service_quantities'] = {s['service_id']: s['qty'] - progress[s['service_id']] for s in services if s['service_id'] not in done}
    if result['remaining_service_quantities']:
        return reject('UNSCHEDULED_SERVICES')
    result['status'] = 'FEASIBLE'
    return result
'未来整日服务证书的独立重演检查；不导入调度器、编译器、候选或引擎。\n\n动作规则依据冻结官方 kaggriculture.py（bc8a54879ef0…）。现金与未来\n日初状态是外部条件；本检查只证明给定条件下的动作、物量与交付。\n'
from collections import Counter as _r10_checker_Counter
import copy as _r10_checker_copy
import hashlib as _r10_checker_hashlib
import json as _r10_checker_json
import math as _r10_checker_math
_r10_checker_PRODUCTS = {'WHEAT', 'CARROT', 'TOMATO', 'STRAWBERRY', 'MELON', 'EGG', 'MILK', 'WOOL', 'FERTILIZER'}
_r10_checker_CROPS = {'WHEAT': (2, 4, 0, 6), 'CARROT': (2, 3, 0, 4), 'TOMATO': (8, 8, 1, 4), 'STRAWBERRY': (10, 10, 2, 4), 'MELON': (10, 12, 0, 6)}
_r10_checker_ANIMALS = {'GOOSE': ('COOP', 'EGG', 4), 'COW': ('PASTURE', 'MILK', 6), 'SHEEP': ('PASTURE', 'WOOL', 6)}
_r10_checker_ACCESS = ((4, 4), (5, 4), (4, 5), (5, 5))
_r10_checker_MOVES = {'NORTH': (0, -1), 'SOUTH': (0, 1), 'EAST': (1, 0), 'WEST': (-1, 0)}
_r10_checker_FIELDS = {'WATER', 'FEED', 'CARE', 'HARVEST', 'COLLECT_FERTILIZER'}

class _r10_checker_Invalid(Exception):

    def __init__(self, code, detail):
        self.code, self.detail = (code, detail)

def _r10_checker__need(ok, code, detail):
    if not ok:
        raise _r10_checker_Invalid(code, detail)

def _r10_checker__int(value, lo=0, hi=None):
    return type(value) is int and value >= lo and (hi is None or value <= hi)

def _r10_checker__cash(value):
    return type(value) in (int, float) and _r10_checker_math.isfinite(value) and (value >= 0)

def _r10_checker__pos(value):
    return isinstance(value, list) and len(value) == 2 and all((_r10_checker__int(x, 0, 9) for x in value))

def _r10_checker__stock(value, label, allowed=None):
    _r10_checker__need(isinstance(value, dict), 'STOCK_TYPE', label)
    _r10_checker__need(all((isinstance(k, str) and _r10_checker__int(v) and (allowed is None or k in allowed) for k, v in value.items())), 'STOCK_DOMAIN', label)
    return _r10_checker_Counter({k: v for k, v in value.items() if v})

def _r10_checker_canonical_hash(value):
    return _r10_checker_hashlib.sha256(_r10_checker_json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()

def _r10_checker__plain(stock):
    return dict(sorted(((k, v) for k, v in stock.items() if v)))

def _r10_checker__fib(n):
    a = b = 1
    for _ in range(n):
        a, b = (b, a + b)
    return a

def _r10_checker__identity(tile, pos):
    if 'animal' in tile:
        return f"animal:{tile['animal']}:{tile['placed_day']}:{pos[0]},{pos[1]}"
    return f"plant:{tile['crop']}:{tile['planted_day']}:{pos[0]},{pos[1]}"

def _r10_checker__validate_problem(p):
    _r10_checker__need(isinstance(p, dict) and p.get('schema') == 'r10-future-day-problem-v1', 'PROBLEM_SCHEMA', 'schema')
    _r10_checker__need(p.get('status') == 'SUPPORTED' and p.get('unsupported_reasons') == [], 'UNSUPPORTED', '不接受fallback问题')
    day, current = (p.get('day'), p.get('current_day'))
    _r10_checker__need(_r10_checker__int(current, 0, 28) and _r10_checker__int(day, current + 1, 29), 'DAY', '只接受未来完整日')
    end = 22 if day == 29 else 23
    _r10_checker__need(p.get('end_hour') == end and type(p.get('end_hour')) is int, 'DAY_END', 'day29止于h22')
    _r10_checker__need(type(p.get('board_size')) is int and p['board_size'] == 10 and (type(p.get('capacity')) is int) and (p['capacity'] == 100), 'BOARD_CAPACITY', '固定10格棋盘与100仓容')
    protocol = {'max_hands': 12, 'farmer_h0_pass': True, 'h0_max_hires': 9, 'h1_remaining_hires': True}
    _r10_checker__need(p.get('hire_protocol') == protocol and type(p['hire_protocol'].get('max_hands')) is int and (type(p['hire_protocol'].get('h0_max_hires')) is int) and (type(p['hire_protocol'].get('farmer_h0_pass')) is bool) and (type(p['hire_protocol'].get('h1_remaining_hires')) is bool), 'HIRE_PROTOCOL', '固定协议')
    _r10_checker__need(isinstance(p.get('conditional'), list), 'CONDITIONAL', '必须明示未来条件')
    _r10_checker__need(_r10_checker__cash(p.get('legacy_work')) and _r10_checker__cash(p.get('legacy_hire_cost')), 'LEGACY_DOMAIN', '旧成本域')
    shed = _r10_checker__stock(p.get('start_shed'), 'start_shed', _r10_checker_PRODUCTS | set(_r10_checker_ANIMALS))
    reserve = _r10_checker__stock(p.get('reserved_shed'), 'reserved_shed', _r10_checker_PRODUCTS | set(_r10_checker_ANIMALS))
    _r10_checker__need(sum(shed.values()) <= 100 and reserve.get('FERTILIZER', 0) <= 12, 'START_CAPACITY', '日初仓容或肥料预约')
    buy = p.get('planned_wheat_buy')
    _r10_checker__need(isinstance(buy, dict) and _r10_checker__int(buy.get('qty'), 0, 16) and _r10_checker__cash(buy.get('estimated_cash')) and (type(buy.get('order_hour')) is int) and (buy['order_hour'] == 0) and (type(buy.get('available_from_hour')) is int) and (buy['available_from_hour'] == 1), 'BUY_PROTOCOL', '仅h0一笔≤16麦，h1可用')
    _r10_checker__need(buy['qty'] != 0 or buy['estimated_cash'] == 0, 'BUY_CASH', '零采购不能计采购现金')
    _r10_checker__need(buy['qty'] == 0 or buy['estimated_cash'] > 0, 'BUY_CASH', '正采购量必须带正现金条件')
    _r10_checker__need(_r10_checker__int(p.get('feed_units'), 0, 16), 'FEED_LIMIT', '当日feed必须≤16')
    goods = _r10_checker__stock(p.get('expected_goods'), 'expected_goods', _r10_checker_PRODUCTS)
    assets, board = ({}, {})
    _r10_checker__need(isinstance(p.get('start_farm_tiles'), list), 'ASSETS', '资产列表')
    for row in p['start_farm_tiles']:
        _r10_checker__need(isinstance(row, dict) and _r10_checker__pos(row.get('pos')), 'ASSET_POS', '资产坐标')
        pos, tile, aid = (tuple(row['pos']), row.get('tile'), row.get('asset_id'))
        _r10_checker__need(isinstance(aid, str) and isinstance(tile, dict), 'ASSET_STATE', '未知/null/LOCKED不能作为活动资产')
        _r10_checker__need(aid not in assets and pos not in board, 'DUPLICATE_ASSET', aid)
        _r10_checker__need(_r10_checker__int(tile.get('yield_units')), 'TILE_YIELD', aid)
        if 'animal' in tile:
            a = tile['animal']
            _r10_checker__need(a in _r10_checker_ANIMALS and tile.get('kind') == _r10_checker_ANIMALS[a][0], 'ANIMAL', aid)
            _r10_checker__need(_r10_checker__int(tile.get('placed_day'), 0, day) and _r10_checker__int(tile.get('pending_care_bonus')) and _r10_checker__int(tile.get('consecutive_unfed')) and (tile['yield_units'] <= _r10_checker_ANIMALS[a][2]), 'ANIMAL_STATE', aid)
            _r10_checker__need(all((type(tile.get(k)) is bool for k in ('fed_today', 'cared_today', 'fertilizer_available'))), 'ANIMAL_FLAGS', aid)
        else:
            c = tile.get('crop')
            _r10_checker__need(tile.get('kind') == 'PLANT' and c in _r10_checker_CROPS, 'PLANT', aid)
            _r10_checker__need(_r10_checker__int(tile.get('planted_day'), 0, day) and _r10_checker__int(tile.get('consecutive_unwatered')) and _r10_checker__int(tile.get('fertilized_until_day'), -1) and _r10_checker__int(tile.get('max_lifespan_step'), -1) and (type(tile.get('watered_today')) is bool) and (tile['yield_units'] <= _r10_checker_CROPS[c][3]), 'PLANT_STATE', aid)
            mls = tile['max_lifespan_step']
            _r10_checker__need(mls < 0 or mls >= day * 24, 'EXPIRED_ASSET', aid)
        _r10_checker__need(aid == _r10_checker__identity(tile, pos), 'ASSET_IDENTITY', aid)
        assets[aid] = {'pos': pos, 'tile': _r10_checker_copy.deepcopy(tile)}
        board[pos] = aid
    services, field_keys = ({}, set())
    source_goods, delivery_goods, feed_count = (_r10_checker_Counter(), _r10_checker_Counter(), 0)
    _r10_checker__need(isinstance(p.get('services'), list), 'SERVICES', '服务列表')
    for s in p['services']:
        _r10_checker__need(isinstance(s, dict), 'SERVICE_TYPE', '服务对象')
        sid, aid, op = (s.get('service_id'), s.get('asset_id'), s.get('op'))
        _r10_checker__need(isinstance(sid, str) and sid and (sid not in services), 'DUPLICATE_SERVICE', str(sid))
        _r10_checker__need(isinstance(aid, str) and aid in assets, 'SERVICE_ASSET', sid)
        _r10_checker__need(_r10_checker__int(s.get('release'), 0, end) and _r10_checker__int(s.get('deadline'), s['release'], end), 'SERVICE_WINDOW', sid)
        req, gives = (_r10_checker__stock(s.get('requires'), sid + '/requires', _r10_checker_PRODUCTS), _r10_checker__stock(s.get('gives'), sid + '/gives', _r10_checker_PRODUCTS))
        deps = s.get('dependencies')
        _r10_checker__need(isinstance(deps, list) and all((isinstance(x, str) for x in deps)) and (len(deps) == len(set(deps))), 'DEPENDENCIES', sid)
        if op == 'PLACE':
            item = s.get('item')
            _r10_checker__need(s.get('pos') is None and item in _r10_checker_PRODUCTS and _r10_checker__int(s.get('qty'), 1) and (s.get('splittable') is True) and (req == _r10_checker_Counter({item: s['qty']})) and (not gives) and deps, 'DELIVERY_SCHEMA', sid)
            delivery_goods[item] += s['qty']
        else:
            _r10_checker__need(op in _r10_checker_FIELDS and _r10_checker__pos(s.get('pos')) and (tuple(s['pos']) == assets[aid]['pos']) and (s.get('item') is None) and (type(s.get('qty')) is int) and (s['qty'] == 1) and (s.get('splittable') is False), 'FIELD_SCHEMA', sid)
            key = (aid, op)
            _r10_checker__need(key not in field_keys, 'DUPLICATE_FIELD_OPERATION', sid)
            field_keys.add(key)
            tile = assets[aid]['tile']
            _r10_checker__need(req == (_r10_checker_Counter({'WHEAT': 1}) if op == 'FEED' else _r10_checker_Counter()), 'FIELD_REQUIREMENT', sid)
            if op in ('WATER', 'FEED', 'CARE'):
                _r10_checker__need(not gives, 'FIELD_GIVES', sid)
            elif op == 'COLLECT_FERTILIZER':
                _r10_checker__need(gives == _r10_checker_Counter({'FERTILIZER': 1}), 'FIELD_GIVES', sid)
            elif op == 'HARVEST':
                product = _r10_checker_ANIMALS[tile['animal']][1] if 'animal' in tile else tile['crop']
                _r10_checker__need(set(gives) == {product} and gives[product] > 0, 'FIELD_GIVES', sid)
            if op == 'WATER':
                _r10_checker__need(tile.get('kind') == 'PLANT' and (not tile['watered_today']), 'WATER_ELIGIBILITY', sid)
            if op in ('FEED', 'CARE', 'COLLECT_FERTILIZER'):
                _r10_checker__need('animal' in tile, 'ANIMAL_SERVICE', sid)
                flag = {'FEED': 'fed_today', 'CARE': 'cared_today', 'COLLECT_FERTILIZER': 'fertilizer_available'}[op]
                _r10_checker__need(tile[flag] == (op == 'COLLECT_FERTILIZER'), 'ANIMAL_SERVICE_FLAG', sid)
            if tile.get('kind') == 'PLANT' and tile['max_lifespan_step'] >= 0:
                _r10_checker__need(s['deadline'] <= tile['max_lifespan_step'] - day * 24, 'LIFESPAN_DEADLINE', sid)
            source_goods.update(gives)
            feed_count += op == 'FEED'
        services[sid] = _r10_checker_copy.deepcopy(s)
        services[sid]['requires'] = dict(req)
        services[sid]['gives'] = dict(gives)
    _r10_checker__need(source_goods == goods == delivery_goods, 'GOODS_COVERAGE', '预期产出、田间来源和交付数量必须一致')
    _r10_checker__need(feed_count == p['feed_units'], 'FEED_COVERAGE', 'feed计数与服务一致')
    for sid, s in services.items():
        _r10_checker__need(all((x in services and x != sid for x in s['dependencies'])), 'UNKNOWN_DEPENDENCY', sid)
        if s['op'] == 'PLACE':
            _r10_checker__need(all((services[x]['op'] in ('HARVEST', 'COLLECT_FERTILIZER') and services[x]['gives'].get(s['item'], 0) > 0 for x in s['dependencies'])), 'DELIVERY_SOURCE', sid)
    visited, visiting = (set(), set())

    def visit(sid):
        _r10_checker__need(sid not in visiting, 'DEPENDENCY_CYCLE', sid)
        if sid in visited:
            return
        visiting.add(sid)
        for dep in services[sid]['dependencies']:
            visit(dep)
        visiting.remove(sid)
        visited.add(sid)
    for sid in services:
        visit(sid)
    return (day, end, shed, reserve, assets, board, services)

def _r10_checker__run(p, c):
    day, end, shed, reserve, assets, board, services = _r10_checker__validate_problem(p)
    _r10_checker__need(isinstance(c, dict) and c.get('schema') == 'r10-future-day-certificate-v1', 'CERTIFICATE_SCHEMA', 'schema')
    _r10_checker__need(c.get('status') == 'FEASIBLE', 'NO_CERTIFICATE', '未找到证书不等于通过')
    _r10_checker__need(c.get('problem_sha256') == _r10_checker_canonical_hash(p), 'PROBLEM_HASH', '问题摘要不符')
    n = c.get('n_hands')
    _r10_checker__need(_r10_checker__int(n, 0, 12), 'HAND_COUNT', '0..12整数')
    _r10_checker__need(c.get('reason') is None and _r10_checker__cash(c.get('hire_cost')), 'CERTIFICATE_METADATA', '成功证书元数据')
    _r10_checker__need(isinstance(c.get('actions'), list) and isinstance(c.get('markets'), list), 'SCHEDULE_TYPE', '动作和市场列表')
    actions, keys = ({}, [])
    for row in c['actions']:
        _r10_checker__need(isinstance(row, dict) and _r10_checker__int(row.get('hour'), 0, end) and _r10_checker__int(row.get('unit'), 0, n), 'ACTION_SLOT', '非法时槽或unit')
        key = (row['hour'], row['unit'])
        _r10_checker__need(key not in actions, 'DUPLICATE_SLOT', str(key))
        _r10_checker__need(isinstance(row.get('action'), list) and row['action'] and isinstance(row['action'][0], str) and isinstance(row.get('service_allocations'), list), 'ACTION_SCHEMA', str(key))
        actions[key] = row
        keys.append(key)
    _r10_checker__need(keys == sorted(keys), 'ACTION_ORDER', '须按hour/unit排序')
    markets = {}
    for row in c['markets']:
        _r10_checker__need(isinstance(row, dict) and _r10_checker__int(row.get('hour'), 0, end) and (row['hour'] not in markets) and isinstance(row.get('orders'), list) and (len(row['orders']) <= 10), 'MARKET_SLOT', '市场记录或10订单槽')
        markets[row['hour']] = row['orders']
    _r10_checker__need([r['hour'] for r in c['markets']] == list(range(end + 1)), 'MARKET_COVERAGE', '每小时精确一条市场记录')
    positions = {0: (4, 4)}
    inventories, lots = ({0: _r10_checker_Counter()}, {0: _r10_checker_Counter()})
    completed, done_qty, visited_slots = (set(), _r10_checker_Counter(), set())
    receipts, market_events, hires = ([], [], [])
    action_counts, sold, purchased, delivered, consumed = (_r10_checker_Counter(), _r10_checker_Counter(), _r10_checker_Counter(), _r10_checker_Counter(), _r10_checker_Counter())
    hire_cost, total_buy = (0, 0)

    def take(unit, item, qty):
        _r10_checker__need(inventories[unit][item] >= qty, 'MATERIAL_SHORTFALL', f'unit{unit} {item} need{qty}')
        tagged = sum((v for (source, product), v in lots[unit].items() if product == item))
        untagged = inventories[unit][item] - tagged
        left = max(0, qty - untagged)
        for key in sorted(lots[unit]):
            if key[1] == item and left:
                q = min(lots[unit][key], left)
                lots[unit][key] -= q
                left -= q
        inventories[unit][item] -= qty
    for hour in range(end + 1):
        for unit in sorted(positions):
            key = (hour, unit)
            _r10_checker__need(key in actions, 'MISSING_SLOT', str(key))
            visited_slots.add(key)
            row = actions[key]
            action = row['action']
            op = action[0]
            alloc = row['service_allocations']
            _r10_checker__need(all((isinstance(a, dict) and isinstance(a.get('service_id'), str) and (a['service_id'] in services) and _r10_checker__int(a.get('qty'), 1) for a in alloc)), 'ALLOCATION_SCHEMA', str(key))
            _r10_checker__need(len({a['service_id'] for a in alloc}) == len(alloc), 'DUPLICATE_ALLOCATION', str(key))
            _r10_checker__need(hour != 0 or unit != 0 or action == ['PASS'], 'FARMER_H0', '农夫h0必须PASS')
            pos = positions[unit]
            if op in _r10_checker_MOVES or op == 'PASS':
                _r10_checker__need(len(action) == 1 and (not alloc), 'NON_SERVICE_ALLOCATION', str(key))
                if op in _r10_checker_MOVES:
                    dx, dy = _r10_checker_MOVES[op]
                    dest = (pos[0] + dx, pos[1] + dy)
                    _r10_checker__need(all((0 <= v < 10 for v in dest)), 'MOVE_BOUNDS', str(key))
                    positions[unit] = dest
            elif op == 'PICKUP':
                _r10_checker__need(len(action) == 3 and action[1] in _r10_checker_PRODUCTS and _r10_checker__int(action[2], 1) and (not alloc), 'PICKUP_SCHEMA', str(key))
                item, qty = action[1:]
                _r10_checker__need(pos in _r10_checker_ACCESS, 'PICKUP_LOCATION', str(key))
                _r10_checker__need(item != 'WHEAT' or qty <= 4, 'R9_PICKUP_LIMIT', str(key))
                _r10_checker__need(shed[item] >= qty, 'PICKUP_PARTIAL', str(key))
                shed[item] -= qty
                inventories[unit][item] += qty
            elif op == 'PLACE':
                _r10_checker__need(len(action) == 3 and action[1] in _r10_checker_PRODUCTS and _r10_checker__int(action[2], 1) and (pos in _r10_checker_ACCESS), 'PLACE_SCHEMA', str(key))
                item, requested = action[1:]
                actual = min(requested, inventories[unit][item], 100 - sum(shed.values()))
                _r10_checker__need(actual > 0 and sum((a['qty'] for a in alloc)) == actual, 'PLACE_ACTUAL_QUANTITY', str(key))
                for a in alloc:
                    sid, qty = (a['service_id'], a['qty'])
                    s = services[sid]
                    _r10_checker__need(s['op'] == 'PLACE' and s['item'] == item and (s['release'] <= hour <= s['deadline']), 'PLACE_SERVICE', sid)
                    _r10_checker__need(all((d in completed for d in s['dependencies'])), 'DEPENDENCY_NOT_DONE', sid)
                    _r10_checker__need(done_qty[sid] + qty <= s['qty'], 'OVER_DELIVERY', sid)
                    remaining = qty
                    for source in sorted(s['dependencies']):
                        lotkey = (source, item)
                        q = min(lots[unit][lotkey], remaining)
                        lots[unit][lotkey] -= q
                        remaining -= q
                    _r10_checker__need(remaining == 0, 'DELIVERY_PROVENANCE', sid)
                    done_qty[sid] += qty
                    if done_qty[sid] == s['qty']:
                        completed.add(sid)
                inventories[unit][item] -= actual
                shed[item] += actual
                delivered[item] += actual
            elif op in _r10_checker_FIELDS:
                _r10_checker__need(len(action) == 1 and len(alloc) == 1 and (alloc[0]['qty'] == 1), 'FIELD_ALLOCATION', str(key))
                sid = alloc[0]['service_id']
                s = services[sid]
                _r10_checker__need(s['op'] == op and sid not in completed and (tuple(s['pos']) == pos), 'FIELD_TARGET_OR_REPEAT', sid)
                _r10_checker__need(s['release'] <= hour <= s['deadline'], 'FIELD_DEADLINE', sid)
                _r10_checker__need(all((d in completed for d in s['dependencies'])), 'DEPENDENCY_NOT_DONE', sid)
                aid = board.get(pos)
                tile = assets[aid]['tile'] if aid else None
                _r10_checker__need(aid == s['asset_id'] and isinstance(tile, dict), 'FIELD_ASSET_GONE', sid)
                gives = _r10_checker_Counter()
                if op == 'WATER':
                    _r10_checker__need(tile.get('kind') == 'PLANT' and (not tile['watered_today']), 'WATER_NO_EFFECT', sid)
                    tile['watered_today'] = True
                    first, last, interval, cap = _r10_checker_CROPS[tile['crop']]
                    age = day - tile['planted_day']
                    if not interval and (last + 1) // 2 <= age <= last:
                        tile['yield_units'] = min(cap, tile['yield_units'] + (2 if tile['fertilized_until_day'] >= day else 1))
                elif op == 'FEED':
                    _r10_checker__need('animal' in tile and (not tile['fed_today']), 'FEED_NO_EFFECT', sid)
                    take(unit, 'WHEAT', 1)
                    consumed['WHEAT'] += 1
                    tile['fed_today'] = True
                elif op == 'CARE':
                    _r10_checker__need('animal' in tile and (not tile['cared_today']), 'CARE_NO_EFFECT', sid)
                    tile['cared_today'] = True
                elif op == 'COLLECT_FERTILIZER':
                    _r10_checker__need('animal' in tile and tile['fertilizer_available'], 'COLLECT_NO_EFFECT', sid)
                    tile['fertilizer_available'] = False
                    gives['FERTILIZER'] = 1
                elif op == 'HARVEST':
                    _r10_checker__need(tile.get('yield_units', 0) > 0, 'HARVEST_EMPTY', sid)
                    if tile.get('kind') == 'PLANT':
                        first, last, interval, cap = _r10_checker_CROPS[tile['crop']]
                        _r10_checker__need(day - tile['planted_day'] >= first, 'HARVEST_IMMATURE', sid)
                        gives[tile['crop']] = tile['yield_units']
                        tile['yield_units'] = 0
                        if not interval:
                            assets[aid]['tile'] = None
                    else:
                        _r10_checker__need('animal' in tile, 'HARVEST_NOT_PRODUCTIVE', sid)
                        gives[_r10_checker_ANIMALS[tile['animal']][1]] = tile['yield_units']
                        tile['yield_units'] = 0
                _r10_checker__need(gives == _r10_checker_Counter(s['gives']), 'ACTUAL_GIVES_MISMATCH', sid)
                for item, qty in gives.items():
                    inventories[unit][item] += qty
                    lots[unit][sid, item] += qty
                completed.add(sid)
                done_qty[sid] = 1
            else:
                raise _r10_checker_Invalid('UNSUPPORTED_ACTION', str(action))
            action_counts[op] += 1
            receipts.append({'hour': hour, 'unit': unit, 'action': _r10_checker_copy.deepcopy(action), 'allocations': _r10_checker_copy.deepcopy(alloc)})
        hour_hires, hour_buy = (0, 0)
        for order in markets[hour]:
            _r10_checker__need(isinstance(order, list) and order and isinstance(order[0], str), 'ORDER_SCHEMA', str(hour))
            op = order[0]
            if op == 'HIRE':
                _r10_checker__need(len(order) == 1 and hour in (0, 1) and (len(positions) - 1 < n), 'HIRE_WINDOW', str(hour))
                _r10_checker__need(hour != 0 or hour_hires < 9, 'H0_HIRE_LIMIT', str(hour))
                occ = _r10_checker_Counter(positions.values())
                spawn = min(_r10_checker_ACCESS, key=lambda xy: (occ[xy], _r10_checker_ACCESS.index(xy)))
                index = len(positions)
                cost = _r10_checker__fib(index - 1)
                positions[index] = spawn
                inventories[index] = _r10_checker_Counter()
                lots[index] = _r10_checker_Counter()
                hire_cost += cost
                hour_hires += 1
                hires.append({'unit': index, 'order_hour': hour, 'available_from_hour': hour + 1, 'spawn': list(spawn), 'cost': cost})
            elif op == 'BUY_PRODUCT':
                _r10_checker__need(len(order) == 3 and order[1] == 'WHEAT' and _r10_checker__int(order[2], 1, 16) and (hour == 0) and (hour_buy == 0), 'BUY_ORDER', str(order))
                qty = order[2]
                _r10_checker__need(qty == p['planned_wheat_buy']['qty'] and sum(shed.values()) + qty <= 100, 'BUY_QUANTITY_CAPACITY', str(order))
                shed['WHEAT'] += qty
                purchased['WHEAT'] += qty
                total_buy += qty
                hour_buy += 1
            elif op == 'SELL':
                _r10_checker__need(len(order) == 3 and order[1] in _r10_checker_PRODUCTS and _r10_checker__int(order[2], 1), 'SELL_ORDER', str(order))
                item, requested = order[1:]
                actual = min(shed[item], requested)
                minimum = min(shed[item], reserve[item])
                _r10_checker__need(actual > 0 and shed[item] - actual >= minimum, 'RESERVED_SELL', str(order))
                shed[item] -= actual
                sold[item] += actual
            else:
                raise _r10_checker_Invalid('UNSUPPORTED_ORDER', str(order))
            market_events.append({'hour': hour, 'order': _r10_checker_copy.deepcopy(order)})
        _r10_checker__need(hour_hires == (min(n, 9) if hour == 0 else max(0, n - 9) if hour == 1 else 0), 'HIRE_PLAN', str(hour))
        _r10_checker__need(sum(shed.values()) <= 100, 'WAREHOUSE_OVERFLOW', str(hour))
        absolute = day * 24 + hour
        for asset in assets.values():
            tile = asset['tile']
            if isinstance(tile, dict) and tile.get('kind') == 'PLANT':
                mls = tile['max_lifespan_step']
                if mls >= 0 and absolute >= mls and ((absolute - mls) % 2 == 0):
                    tile['yield_units'] -= 1
                    if tile['yield_units'] <= 0:
                        asset['tile'] = {'kind': 'WEED'}
    _r10_checker__need(visited_slots == set(actions), 'PREBIRTH_OR_EXTRA_SLOT', '含出生前或额外unit时槽')
    _r10_checker__need(total_buy == p['planned_wheat_buy']['qty'], 'BUY_COVERAGE', '原计划采购必须精确落实')
    _r10_checker__need(len(positions) == n + 1 and c['hire_cost'] == hire_cost, 'HIRE_COST', '实际FIB费用不符')
    _r10_checker__need(completed == set(services), 'MISSING_SERVICE', str(sorted(set(services) - completed)))
    reported = c.get('scheduled_service_ids')
    _r10_checker__need(isinstance(reported, list) and all((isinstance(x, str) for x in reported)) and (len(reported) == len(set(reported))) and (set(reported) == completed), 'FORGED_COMPLETION', 'scheduled字段不符真实动作')
    terminal = c.get('terminal_positions')
    _r10_checker__need(isinstance(terminal, dict) and all((_r10_checker__pos(v) for v in terminal.values())) and (terminal == {str(u): list(pos) for u, pos in positions.items()}), 'TERMINAL_POSITION', '终点不符动作')
    if 'terminal_shed' in c:
        reported_shed = _r10_checker__stock(c['terminal_shed'], 'terminal_shed', _r10_checker_PRODUCTS | set(_r10_checker_ANIMALS))
        _r10_checker__need(_r10_checker__plain(reported_shed) == _r10_checker__plain(shed), 'TERMINAL_SHED', '证书仓存不符重演')
    if 'terminal_inventories' in c:
        reported_invs = c['terminal_inventories']
        _r10_checker__need(isinstance(reported_invs, list) and len(reported_invs) == n + 1, 'TERMINAL_INVENTORIES', '证书背包列表长度')
        _r10_checker__need(all((_r10_checker__plain(_r10_checker__stock(inv, f'terminal_inventory/{u}', _r10_checker_PRODUCTS)) == _r10_checker__plain(inventories[u]) for u, inv in enumerate(reported_invs))), 'TERMINAL_INVENTORIES', '证书背包不符重演')
    if 'remaining_service_quantities' in c:
        _r10_checker__need(c['remaining_service_quantities'] == {} and isinstance(c['remaining_service_quantities'], dict), 'TERMINAL_REMAINING', '成功证书不应有剩余服务')
    harvested = _r10_checker_Counter()
    for s in services.values():
        if s['op'] in _r10_checker_FIELDS:
            harvested.update(s['gives'])
    lhs = _r10_checker_Counter(p['start_shed']) + purchased + harvested
    rhs = shed + sold + consumed
    for inv in inventories.values():
        rhs.update(inv)
    _r10_checker__need(lhs == rhs, 'RESOURCE_IDENTITY', '库存+买入+采收=终存+卖出+消耗')
    eod_shed, overflow = (_r10_checker_Counter(shed), _r10_checker_Counter())
    if day != 29:
        for unit in sorted(inventories):
            for item, qty in inventories[unit].items():
                put = min(qty, max(0, 100 - sum(eod_shed.values())))
                eod_shed[item] += put
                overflow[item] += qty - put
    return {'cash_feasibility': 'CONDITIONAL_EXTERNAL_FUNDING_CHECK', 'future_state_status': 'CONDITIONAL_NOT_ACTUAL_OBSERVATION', 'coverage_scope': 'SUPPLIED_PORTFOLIO_AND_SERVICES_ONLY', 'day': day, 'hours': end + 1, 'unit_actions': len(actions), 'action_counts': dict(action_counts), 'completed_service_count': len(completed), 'completed_service_ids': sorted(completed), 'delivered_goods': _r10_checker__plain(delivered), 'harvested_goods': _r10_checker__plain(harvested), 'purchased_goods': _r10_checker__plain(purchased), 'sold_goods': _r10_checker__plain(sold), 'consumed_goods': _r10_checker__plain(consumed), 'hire_cost': hire_cost, 'hires': hires, 'resource_identity': True, 'terminal_positions': terminal, 'terminal_shed': _r10_checker__plain(shed), 'terminal_inventories': {str(u): _r10_checker__plain(inv) for u, inv in inventories.items()}, 'conditional_eod_shed': _r10_checker__plain(eod_shed) if day != 29 else None, 'conditional_eod_overflow': _r10_checker__plain(overflow), 'service_receipts': receipts, 'market_events': market_events, 'sales_cash': None, 'planned_wheat_cash_condition': p['planned_wheat_buy']['estimated_cash']}

def _r10_checker_check_day(problem, certificate):
    """失败返回首个明确反例；不修改传入对象、不推断调度失败等于无解。"""
    try:
        stats = _r10_checker__run(_r10_checker_copy.deepcopy(problem), _r10_checker_copy.deepcopy(certificate))
        return {'valid': True, 'errors': [], 'stats': stats}
    except _r10_checker_Invalid as exc:
        return {'valid': False, 'errors': [{'code': exc.code, 'detail': exc.detail}], 'stats': {}}
    except (KeyError, TypeError, ValueError, OverflowError, RecursionError) as exc:
        return {'valid': False, 'errors': [{'code': 'MALFORMED_INPUT', 'detail': str(exc)}], 'stats': {}}
'R10 B 独立未来日劳动准入；不导入或调用候选，不改变原资金与评分。'
from collections import Counter as _r10_route_admission_Counter
from copy import deepcopy as _r10_route_admission_deepcopy
import math as _r10_route_admission_math
_r10_route_admission_PRODUCTS = {'WHEAT', 'CARROT', 'TOMATO', 'STRAWBERRY', 'MELON', 'EGG', 'MILK', 'WOOL', 'FERTILIZER'}
_r10_route_admission_ANIMALS = {'COW', 'SHEEP', 'GOOSE'}
_r10_route_admission_IMPLEMENTATION_ID = 'r10-route-admission-v1'

class _r10_route_admission_BindingError(ValueError):
    pass

def _r10_route_admission__need(test, reason):
    if not test:
        raise _r10_route_admission_BindingError(reason)

def _r10_route_admission__qty(value, name):
    _r10_route_admission__need(type(value) is int and value >= 0, name + ':INVALID_QUANTITY')
    return value

def _r10_route_admission__day_map(data, name, start, *, numeric=False):
    _r10_route_admission__need(isinstance(data, dict), name + ':MISSING_MAP')
    _r10_route_admission__need(set(data) == set(range(start, 30)), name + ':DAY_COVERAGE')
    for value in data.values():
        if numeric:
            _r10_route_admission__need(type(value) in (int, float) and _r10_route_admission_math.isfinite(value) and (value >= 0), name + ':INVALID_NUMBER')
        else:
            _r10_route_admission__qty(value, name)
    return data

def _r10_route_admission__normal_sparse(data):
    """只规范零项，不改变值；没有缺日填充粮账的功能。"""
    return {d: {p: n for p, n in value.items() if n} if isinstance(value, dict) else value for d, value in data.items() if value}

def _r10_route_admission_aggregate_calendars(calendars):
    """从原字段聚合；服务字段另核，不由 work 反推。"""
    work, feed, goods = (_r10_route_admission_Counter(), _r10_route_admission_Counter(), {})
    seen = set()
    for cal in calendars:
        aid = cal['asset_id']
        _r10_route_admission__need(aid not in seen, 'DUPLICATE_ASSET_CALENDAR')
        seen.add(aid)
        for key in ('work', 'feed', 'goods'):
            _r10_route_admission__need(isinstance(cal[key], dict), 'MISSING_LEGACY_CALENDAR')
            for d, value in cal[key].items():
                _r10_route_admission__need(type(d) is int and 0 <= d <= 29, 'INVALID_CALENDAR_DAY')
                if key == 'goods':
                    _r10_route_admission__need(isinstance(value, dict), 'INVALID_CALENDAR_GOODS')
                    for item, quantity in value.items():
                        _r10_route_admission__need(item in _r10_route_admission_PRODUCTS, 'UNKNOWN_CALENDAR_PRODUCT')
                        _r10_route_admission__qty(quantity, 'calendar.goods')
                    goods.setdefault(d, _r10_route_admission_Counter()).update(value)
                else:
                    _r10_route_admission__qty(value, 'calendar.' + key)
        work.update(cal['work'])
        feed.update(cal['feed'])
    return {'goods': _r10_route_admission__normal_sparse({d: dict(v) for d, v in goods.items()}), 'work': _r10_route_admission__normal_sparse(dict(work)), 'feed': _r10_route_admission__normal_sparse(dict(feed))}

def _r10_route_admission_inventory_totals(observed_private):
    total = _r10_route_admission_Counter()
    _r10_route_admission__need(isinstance(observed_private.get('shed'), dict), 'MISSING_OBSERVED_SHED')
    _r10_route_admission__need(isinstance(observed_private.get('inventories'), list), 'MISSING_OBSERVED_INVENTORIES')
    for source in [observed_private['shed'], *observed_private['inventories']]:
        _r10_route_admission__need(isinstance(source, dict), 'INVALID_OBSERVED_INVENTORY')
        for item, qty in source.items():
            _r10_route_admission__need(item in _r10_route_admission_PRODUCTS | _r10_route_admission_ANIMALS, 'UNKNOWN_OBSERVED_INVENTORY_ITEM')
            total[item] += _r10_route_admission__qty(qty, 'observed_inventory')
    return dict(total)

def _r10_route_admission_validate_portfolio(portfolio, today, observed_private):
    """核原字段、来源集合及全期粮账。失败不改任何输入。"""
    cals = portfolio['calendars']
    _r10_route_admission__need(isinstance(cals, list), 'CALENDARS_NOT_LIST')
    coverage = portfolio['coverage_asset_ids']
    _r10_route_admission__need(isinstance(coverage, list) and len(coverage) == len(set(coverage)), 'INVALID_COVERAGE_IDS')
    _r10_route_admission__need(set(coverage) == {c['asset_id'] for c in cals}, 'COVERAGE_ASSET_MISMATCH')
    aggregate = _r10_route_admission_aggregate_calendars(cals)
    _r10_route_admission__need(set(portfolio['legacy_aggregate']) == {'goods', 'work', 'feed'}, 'LEGACY_AGGREGATE_KEYS')
    for key in ('goods', 'work', 'feed'):
        _r10_route_admission__need(aggregate[key] == _r10_route_admission__normal_sparse(portfolio['legacy_aggregate'][key]), 'LEGACY_AGGREGATE_' + key.upper())
    _r10_route_admission__need(aggregate['work'] == _r10_route_admission__normal_sparse(portfolio['workload']), 'WORKLOAD_COVERAGE')
    labor = portfolio['labor']
    capacity = _r10_route_admission__day_map(labor['capacity_by_day'], 'capacity', today)
    cash = _r10_route_admission__day_map(labor['cash_by_day'], 'hire_cash', today, numeric=True)
    _r10_route_admission__need(type(labor['feasible']) is bool, 'INVALID_LEGACY_FEASIBLE')
    old_feasible = all((portfolio['workload'].get(d, 0) <= capacity[d] for d in range(today, 30)))
    _r10_route_admission__need(old_feasible == labor['feasible'], 'LEGACY_FEASIBILITY_MISMATCH')
    _r10_route_admission__need(abs(labor['total_cost'] - sum(cash.values())) < 1e-09, 'LEGACY_HIRE_TOTAL_MISMATCH')
    req = _r10_route_admission__day_map(portfolio['funding_requirements'], 'requirements', today)
    funding = portfolio['funding_feed']
    buys = _r10_route_admission__day_map(funding['buys_by_day'], 'funding_buys', today)
    stocks = _r10_route_admission__day_map(funding['stock_by_day'], 'funding_stock', today)
    costs = _r10_route_admission__day_map(funding['cash_by_day'], 'funding_cash', today, numeric=True)
    _r10_route_admission__need(abs(funding['total_cash'] - sum(costs.values())) < 1e-09, 'FUNDING_CASH_TOTAL_MISMATCH')
    held = _r10_route_admission_inventory_totals(observed_private).get('WHEAT', 0)
    buffer = req[today] - aggregate['feed'].get(today, 0)
    _r10_route_admission__need(buffer >= 0, 'NEGATIVE_BUFFER_DEBIT')
    for d in range(today, 30):
        if d > today:
            _r10_route_admission__need(req[d] == aggregate['feed'].get(d, 0), 'FUTURE_REQUIREMENTS_NOT_COMPLETE_FEED:d%d' % d)
        _r10_route_admission__need(held + buys[d] - req[d] == stocks[d], 'FUNDING_STOCK_IDENTITY:d%d' % d)
        _r10_route_admission__need(buys[d] == 0 and costs[d] == 0 or (buys[d] > 0 and costs[d] > 0), 'FUNDING_BUY_CASH_IDENTITY:d%d' % d)
        held = stocks[d]
    _r10_route_admission__need(isinstance(portfolio['startup_fallback_days'], list) and all((type(d) is int and today <= d <= 29 for d in portfolio['startup_fallback_days'])), 'INVALID_STARTUP_DAYS')
    pending = portfolio.get('pending_animal_units', {})
    _r10_route_admission__need(isinstance(pending, dict), 'INVALID_PENDING_ANIMALS')
    for item, qty in pending.items():
        _r10_route_admission__need(item in _r10_route_admission_ANIMALS, 'INVALID_PENDING_ANIMAL_TYPE')
        _r10_route_admission__qty(qty, 'pending_animal_units')
    _r10_route_admission__need(type(portfolio['conditional_prior_product_sales']) is bool, 'MISSING_PRIOR_SALES_CONDITION')
    return {'aggregate': aggregate, 'buffer_debit': buffer, 'legacy_sha256': _r10_calendar_compiler_canonical_sha({key: portfolio[key] for key in ('legacy_aggregate', 'workload', 'labor', 'funding_requirements', 'funding_feed')})}

def _r10_route_admission_bind_day_materials(portfolio, today, day, observed_private, validated=None):
    """粮账不变；额外 buffer/carry 只占物理库存、不得获得第二份资金信用。"""
    _r10_route_admission__need(today < day <= 29, 'MATERIAL_BINDING_FUTURE_ONLY')
    checked = validated or _r10_route_admission_validate_portfolio(portfolio, today, observed_private)
    for cal in portfolio['calendars']:
        for earlier, reasons in cal['unsupported_by_day'].items():
            if earlier < day and reasons:
                raise _r10_route_admission_BindingError('KNOWN_IMPOSSIBLE_CALENDAR_HISTORY:%s:d%d:%s' % (cal['asset_id'], earlier, ','.join(reasons)))
    aggregate = checked['aggregate']
    funding = portfolio['funding_feed']
    buffer = checked['buffer_debit']
    actual = _r10_route_admission_inventory_totals(observed_private)
    prior = _r10_route_admission_Counter()
    for d, goods in aggregate['goods'].items():
        if today <= d < day:
            prior.update(goods)
    sales = portfolio['conditional_prior_product_sales']
    shed, reserve = ({}, {})
    wheat_extra = 0 if sales else prior['WHEAT']
    shed['WHEAT'] = funding['stock_by_day'][day - 1] + buffer + wheat_extra
    reserve['WHEAT'] = funding['stock_by_day'][day] + buffer + wheat_extra
    for item in _r10_route_admission_ANIMALS:
        qty = actual.get(item, 0) + portfolio.get('pending_animal_units', {}).get(item, 0)
        if qty:
            shed[item] = reserve[item] = qty
    for item in _r10_route_admission_PRODUCTS - {'WHEAT'}:
        quantity = actual.get(item, 0) + prior[item]
        if sales:
            quantity = min(12, quantity) if item == 'FERTILIZER' else 0
        if quantity:
            shed[item] = reserve[item] = quantity
    conditions = [{'kind': 'original_funding_feed_identity', 'day': day, 'paid_start_stock': funding['stock_by_day'][day - 1], 'original_buy_qty': funding['buys_by_day'][day], 'complete_feed_units': aggregate['feed'].get(day, 0), 'paid_ending_stock': funding['stock_by_day'][day], 'buffer_debit': buffer, 'source_current_requirements': portfolio['funding_requirements'][today], 'source_complete_current_feed': aggregate['feed'].get(today, 0), 'additional_cash_credit': 0}, {'kind': 'conservative_physical_carry', 'actual_private_sha256': _r10_calendar_compiler_canonical_sha(observed_private), 'observed_total_inventory': actual, 'prior_conditional_products': dict(prior), 'pending_animal_units': _r10_route_admission_deepcopy(portfolio.get('pending_animal_units', {})), 'animal_carry_is_capacity_upper_bound_not_extra_productive_asset': True, 'wheat_self_production_excluded_from_funding_sources': True}, {'kind': 'conditional_prior_delivery_and_sale' if sales else 'prior_products_all_carried', 'through_day': day - 1, 'fertilizer_keep_cap': 12 if sales else None, 'sales_cash_added_by_route_module': 0}, {'kind': 'caller_complete_portfolio', 'asset_ids': sorted(portfolio['coverage_asset_ids']), 'actual_and_commitment_enumeration_is_external': True}]
    buy = {'qty': funding['buys_by_day'][day], 'estimated_cash': funding['cash_by_day'][day], 'order_hour': 0, 'available_from_hour': 1}
    return {'start_shed': {p: q for p, q in shed.items() if q}, 'reserved_shed': {p: q for p, q in reserve.items() if q}, 'planned_wheat_buy': buy, 'conditional': conditions, 'minimum_terminal_wheat': reserve['WHEAT'], 'buffer_debit': buffer}

class _r10_route_admission_PlanRouteCache:
    """一次 economic_plan 独占；没有持久/跨帧缓存入口。"""

    def __init__(self, plan_token, current_day, observed_private):
        _r10_route_admission__need(isinstance(plan_token, str) and bool(plan_token), 'EMPTY_PLAN_TOKEN')
        self.plan_token = plan_token
        self.context_sha256 = _r10_calendar_compiler_canonical_sha({'token': plan_token, 'day': current_day, 'private': observed_private})
        self.entries = {}

def _r10_route_admission_route_admission(baseline, trial, *, current_day, observed_private, plan_token, cache=None, schedule=None, check=None, implementation_ids=None):
    """只返回劳动结论；原现金前缀仍须另过，失败不提交任何缓存或经营状态。"""
    result = {'schema': 'r10-route-admission-result-v1', 'status': 'REJECTED', 'labor_feasible_after_routes': False, 'route_feasibility_by_day': {}, 'failed_day': None, 'reason': None, 'day_evidence': [], 'scheduler_calls': 0, 'checker_calls': 0, 'cache_hits': 0, 'cash_feasibility': 'UNCHANGED_EXTERNAL_R9_PREFIX_REQUIRED', 'candidate_calls': 0, 'official_calls': 0}
    try:
        _r10_route_admission__need(type(current_day) is int and 0 <= current_day <= 29, 'INVALID_CURRENT_DAY')
        if schedule is None:
            schedule = _r10_scheduler_schedule_day
        if check is None:
            check = _r10_checker_check_day
        _r10_route_admission__need(isinstance(implementation_ids, dict) and implementation_ids.get('scheduler') and implementation_ids.get('checker') and implementation_ids.get('compiler'), 'MISSING_IMPLEMENTATION_IDENTITIES')
        context = _r10_calendar_compiler_canonical_sha({'token': plan_token, 'day': current_day, 'private': observed_private})
        if cache is not None:
            _r10_route_admission__need(isinstance(cache, _r10_route_admission_PlanRouteCache) and cache.plan_token == plan_token and (cache.context_sha256 == context), 'CACHE_CONTEXT_MISMATCH')
        old = _r10_route_admission_validate_portfolio(baseline, current_day, observed_private)
        new = _r10_route_admission_validate_portfolio(trial, current_day, observed_private)
        old_by_id = {c['asset_id']: c for c in baseline['calendars']}
        new_by_id = {c['asset_id']: c for c in trial['calendars']}
        _r10_route_admission__need(set(old_by_id) <= set(new_by_id), 'TRIAL_REMOVED_BASELINE_ASSET')
        for aid, cal in old_by_id.items():
            _r10_route_admission__need(cal == new_by_id[aid], 'TRIAL_CHANGED_BASELINE_CALENDAR')
        result['baseline_legacy_sha256'] = old['legacy_sha256']
        result['trial_legacy_sha256'] = new['legacy_sha256']
        result['legacy_fields_unchanged'] = _r10_route_admission_deepcopy({key: trial[key] for key in ('legacy_aggregate', 'workload', 'labor', 'funding_requirements', 'funding_feed')})
        failures = [d for d in range(current_day, 30) if trial['workload'].get(d, 0) > trial['labor']['capacity_by_day'][d]]
        if current_day in failures:
            result.update(failed_day=current_day, reason='CURRENT_DAY_FAILURE_UNCHANGED')
            return result
        if not failures:
            result.update(status='LEGACY_FEASIBLE_UNCHANGED', labor_feasible_after_routes=True)
            return result
        staged, evidence, admitted = ({}, [], {})
        for day in failures:
            result['failed_day'] = day
            _r10_route_admission__need(trial['labor']['cash_by_day'][day] == 376, 'LEGACY_FAILED_DAY_NOT_12_HAND_COST_376')
            slots = 23 if day == 29 else 24
            _r10_route_admission__need(trial['labor']['capacity_by_day'][day] == slots + 10 * (slots - 1) + 2 * (slots - 2), 'LEGACY_FAILED_DAY_NOT_MAX_HAND_CAPACITY')
            materials = _r10_route_admission_bind_day_materials(trial, current_day, day, observed_private, new)
            problem = _r10_calendar_compiler_compile_day_problem(trial['calendars'], day, current_day, materials['start_shed'], materials['reserved_shed'], materials['planned_wheat_buy'], trial['workload'].get(day, 0), trial['labor']['cash_by_day'][day], conditional=materials['conditional'], startup_fallback_days=trial['startup_fallback_days'])
            _r10_route_admission__need(problem['status'] == 'SUPPORTED', 'UNSUPPORTED:' + ','.join(problem['unsupported_reasons']))
            key = _r10_calendar_compiler_canonical_sha({'problem': problem, 'implementations': implementation_ids, 'admission': _r10_route_admission_IMPLEMENTATION_ID, 'n_hands': 12})
            cached = cache.entries.get(key) if cache is not None else None
            if cached is None:
                result['scheduler_calls'] += 1
                certificate = schedule(_r10_route_admission_deepcopy(problem), 12)
                _r10_route_admission__need(certificate.get('status') == 'FEASIBLE', 'NO_CERTIFICATE:' + str(certificate.get('reason')))
                result['checker_calls'] += 1
                verification = check(_r10_route_admission_deepcopy(problem), _r10_route_admission_deepcopy(certificate))
                _r10_route_admission__need(verification.get('valid') is True, 'CHECKER_REJECTED:' + str(verification.get('errors')))
                _r10_route_admission__need(certificate['n_hands'] == 12 and certificate['hire_cost'] == 376 and (verification['stats']['hire_cost'] == 376), 'CERTIFICATE_CHANGED_HIRE_COST')
                _r10_route_admission__need(verification['stats']['terminal_shed'].get('WHEAT', 0) >= materials['minimum_terminal_wheat'], 'ENDING_WHEAT_RESERVED_SOURCE_SHORTFALL')
                _r10_route_admission__need(not any(verification['stats'].get('conditional_eod_overflow', {}).values()), 'CONDITIONAL_EOD_OVERFLOW')
                cached = {'problem': problem, 'certificate': certificate, 'verification': verification}
                staged[key] = _r10_route_admission_deepcopy(cached)
            else:
                result['cache_hits'] += 1
            evidence.append({'day': day, 'problem_sha256': _r10_calendar_compiler_canonical_sha(problem), 'cache_key': key, 'old_need': trial['workload'].get(day, 0), 'old_capacity': trial['labor']['capacity_by_day'][day], 'old_hire_cash': 376, 'buffer_debit': materials['buffer_debit'], 'start_shed': problem['start_shed'], 'reserved_shed': problem['reserved_shed'], 'buy': problem['planned_wheat_buy'], 'conditional_result': _r10_route_admission_deepcopy(cached['verification']['stats'])})
            admitted[day] = True
        if cache is not None:
            cache.entries.update(staged)
        result.update(status='CONDITIONAL_ROUTE_LABOR_FEASIBLE', labor_feasible_after_routes=True, route_feasibility_by_day=admitted, day_evidence=evidence, failed_day=None, reason=None)
        return result
    except (_r10_route_admission_BindingError, KeyError, TypeError, ValueError, OverflowError) as exc:
        result['reason'] = str(exc)
        return result
'R10 经济接入静态辅助函数；仅供构建，不直接作为推理包。'
import copy as _r10_integration_copy

def _r10_integration_new_context(obs, model):
    token = 'step%d-seat%d' % (obs['step'], obs['player'])
    return {'obs': obs, 'model': model, 'token': token, 'sources': [], 'compiled': {}, 'actual': None, 'cache': _r10_route_admission_PlanRouteCache(token, obs['day'], obs['private']), 'counts': {}, 'reasons': {}, 'first_events': [], 'last_accepted_proof': None}

def _r10_integration_increment(ctx, key, value=1):
    ctx['counts'][key] = ctx['counts'].get(key, 0) + value

def _r10_integration_register_quote(ctx, q):
    ctx['sources'].append(q)
    ctx['last_accepted_proof'] = q.get('_r10_approval')

def _r10_integration_legacy_equal(original, compiled):
    return all((original[k] == compiled[k] for k in ('goods', 'work', 'feed')))

def _r10_integration_actual_calendars(ctx):
    if ctx['actual'] is not None:
        return ctx['actual']
    obs = ctx['obs']
    expected = {(x, y): tile for y, row in enumerate(obs['farms'][obs['player']]['tiles']) for x, tile in enumerate(row) if isinstance(tile, dict) and (tile.get('kind') == 'PLANT' or 'animal' in tile)}
    old = {}
    for seat, pos, calendar in ctx['model']['calendars']:
        if seat != obs['player']:
            continue
        pos = tuple(pos)
        _r10_route_admission__need(pos not in old, 'DUPLICATE_OBSERVED_MODEL_POSITION')
        old[pos] = calendar
    _r10_route_admission__need(set(expected) == set(old), 'OBSERVED_MODEL_ASSET_COVERAGE')
    rows = []
    for pos, tile in sorted(expected.items()):
        calendar = _r10_calendar_compiler_project_calendar_with_services(tile, obs['day'], obs['hour'], pos, {'kind': 'actual_observed_field_asset', 'observation_step': obs['step'], 'position': list(pos)})
        _r10_integration_increment(ctx, 'actual_calendar_compilations')
        _r10_route_admission__need(_r10_integration_legacy_equal(old[pos], calendar), 'OBSERVED_LEGACY_CALENDAR_MISMATCH')
        rows.append((calendar, old[pos], None))
    ctx['actual'] = rows
    return rows

def _r10_integration_quote_calendar(ctx, q):
    material = {key: q[key] for key in ('item', 'position', 'start_step_model', 'setup_work', 'calendar', 'fixed_cash')}
    key = _r10_calendar_compiler_canonical_sha(material)
    if key in ctx['compiled']:
        _r10_integration_increment(ctx, 'quote_calendar_cache_hits')
        return ctx['compiled'][key]
    item, start = (q['item'], q['start_step_model'])
    _r10_route_admission__need(type(start) is int and ctx['obs']['step'] <= start < 718, 'INVALID_QUOTE_START_STEP')
    day, hour = (start // 24, start % 24 + 1)
    if item in ANIMALS:
        future = {'kind': ANIMALS[item][1], 'animal': item, 'placed_day': day, 'yield_units': 0, 'fed_today': False, 'cared_today': False, 'fertilizer_available': False, 'pending_care_bonus': 0}
    else:
        _r10_route_admission__need(item in CROPS, 'UNKNOWN_QUOTE_ITEM')
        future = {'kind': 'PLANT', 'crop': item, 'planted_day': day, 'yield_units': 0 if CROPS[item][3] else 1, 'watered_today': False, 'consecutive_unwatered': 1, 'fertilized_until_day': -1}
    cal = _r10_calendar_compiler_project_calendar_with_services(future, day, hour, q['position'], {'kind': 'conditional_quote_asset', 'model_start_step': start, 'item': item, 'fixed_cash_model': q['fixed_cash'], 'actual_observation_proven': False})
    for d, n in q['setup_work'].items():
        _r10_route_admission__need(type(d) is int and ctx['obs']['day'] <= d <= 29 and (type(n) is int) and (n >= 0), 'INVALID_QUOTE_SETUP_WORK')
        cal['work'][d] = cal['work'].get(d, 0) + n
    _r10_route_admission__need(_r10_integration_legacy_equal(q['calendar'], cal), 'QUOTE_LEGACY_CALENDAR_MISMATCH')
    _r10_integration_increment(ctx, 'quote_calendar_compilations')
    ctx['compiled'][key] = cal
    return cal

def _r10_integration_rows(ctx, trial_q=None):
    rows = list(_r10_integration_actual_calendars(ctx))
    sources = list(ctx['sources']) + ([trial_q] if trial_q is not None else [])
    for q in sources:
        rows.append((_r10_integration_quote_calendar(ctx, q), q['calendar'], q))
    owned = {a: inventory_total(ctx['obs']['private'], a) for a in ANIMALS}
    assigned = {a: 0 for a in ANIMALS}
    for _, _, q in rows:
        if q is not None and q['item'] in ANIMALS and (q['fixed_cash'] == 0):
            assigned[q['item']] += 1
    _r10_route_admission__need(owned == assigned, 'UNASSIGNED_IN_TRANSIT_WITHOUT_CALENDAR')
    return rows

def _r10_integration_portfolio(ctx, rows, workload, labor, requirements, book):
    today = ctx['obs']['day']
    work, feed, goods = ({}, {}, {})
    startup = set()
    pending = {}
    for _, old, q in rows:
        for key, target in (('work', work), ('feed', feed)):
            for day, qty in old[key].items():
                target[day] = target.get(day, 0) + qty
        for day, products in old['goods'].items():
            row = goods.setdefault(day, {})
            for item, qty in products.items():
                row[item] = row.get(item, 0) + qty
        if q is not None:
            startup.update((day for day, qty in q['setup_work'].items() if qty))
            startup.add(q['start_step_model'] // 24)
            if q['item'] in ANIMALS and q['fixed_cash'] > 0:
                pending[q['item']] = pending.get(q['item'], 0) + 1
    funding = {'buys_by_day': dict(book['feed_buys_by_day']), 'stock_by_day': dict(book['feed_ending_stock_by_day']), 'cash_by_day': dict(book['feed_cash_by_day']), 'total_cash': sum(book['feed_cash_by_day'].values())}
    return {'calendars': [c for c, _, _ in rows], 'coverage_asset_ids': [c['asset_id'] for c, _, _ in rows], 'legacy_aggregate': {'goods': goods, 'work': work, 'feed': feed}, 'workload': dict(workload), 'labor': _r10_integration_copy.deepcopy(labor), 'funding_requirements': {d: requirements.get(d, 0) for d in range(today, 30)}, 'funding_feed': funding, 'startup_fallback_days': sorted(startup), 'pending_animal_units': pending, 'conditional_prior_product_sales': True}

def _r10_integration_compact_result(result):
    witnesses = []
    for day in result.get('day_evidence', []):
        stats = day['conditional_result']
        witnesses.append({key: day[key] for key in ('day', 'problem_sha256', 'old_need', 'old_capacity', 'old_hire_cash', 'buffer_debit', 'start_shed', 'reserved_shed', 'buy')})
        witnesses[-1].update(service_count=stats['completed_service_count'], delivered_goods=stats['delivered_goods'], purchased_goods=stats['purchased_goods'], terminal_shed=stats['terminal_shed'])
    return {'status': result['status'], 'labor_feasible_after_routes': result['labor_feasible_after_routes'], 'route_feasibility_by_day': dict(result.get('route_feasibility_by_day', {})), 'reason': result.get('reason'), 'failed_day': result.get('failed_day'), 'trial_legacy_sha256': result.get('trial_legacy_sha256'), 'witnesses': witnesses, 'conditional_not_actual_execution': True}

def _r10_integration_try_route(ctx, q, workload, base_labor, next_work, labor, funding_requirements, funding_book, trial_requirements, trial_book):
    _r10_integration_increment(ctx, 'route_attempts')
    before_sources = len(ctx['sources'])
    try:
        base_rows = _r10_integration_rows(ctx)
        trial_rows = _r10_integration_rows(ctx, q)
        baseline = _r10_integration_portfolio(ctx, base_rows, workload, base_labor, funding_requirements, funding_book)
        trial = _r10_integration_portfolio(ctx, trial_rows, next_work, labor, trial_requirements, trial_book)
        result = _r10_route_admission_route_admission(baseline, trial, current_day=ctx['obs']['day'], observed_private=ctx['obs']['private'], plan_token=ctx['token'], cache=ctx['cache'], implementation_ids=_r10_integration_IMPLEMENTATION_IDS)
    except (_r10_route_admission_BindingError, KeyError, TypeError, ValueError) as exc:
        result = {'status': 'BINDING_REJECTED', 'labor_feasible_after_routes': False, 'reason': str(exc), 'failed_day': None, 'scheduler_calls': 0, 'checker_calls': 0, 'cache_hits': 0}
    _r10_route_admission__need(len(ctx['sources']) == before_sources, 'TRIAL_CHANGED_BASELINE_SOURCES')
    for key in ('scheduler_calls', 'checker_calls', 'cache_hits'):
        _r10_integration_increment(ctx, key, result.get(key, 0))
    _r10_integration_increment(ctx, 'route_successful_quotes' if result['labor_feasible_after_routes'] else 'route_failed_quotes')
    compact = _r10_integration_compact_result(result)
    q['_r10_approval'] = compact
    reason = (result.get('reason') or result['status']).split(':', 1)[0]
    ctx['reasons'][reason] = ctx['reasons'].get(reason, 0) + 1
    if len(ctx['first_events']) < 16:
        ctx['first_events'].append({'item': q['item'], 'position': list(q['position']), 'status': result['status'], 'failed_day': result.get('failed_day'), 'reason': result.get('reason'), 'route_days': sorted(result.get('route_feasibility_by_day', {}))})
    return result['labor_feasible_after_routes']

def _r10_integration_finish(ctx, plan, receipt):
    proof = ctx['last_accepted_proof']
    route_days = dict(proof['route_feasibility_by_day']) if proof else {}
    today = ctx['obs']['day']
    failures = [d for d in range(today, 30) if plan['planned_work'].get(d, 0) > plan['labor_plan']['capacity_by_day'][d]]
    effective = not failures or all((d > today and route_days.get(d) for d in failures))
    plan['r10_route_feasibility_by_day'] = route_days
    plan['r10_effective_labor_feasible'] = bool(effective)
    receipt['r10_future_route'] = {'mode': 'future_failure_certificate', 'counts': dict(ctx['counts']), 'reason_counts': dict(ctx['reasons']), 'first_events': list(ctx['first_events']), 'event_detail_limit': 16, 'events_are_quote_attempts_not_actual_permits': True, 'final_legacy_failed_days': failures, 'final_effective_labor_feasible': bool(effective), 'last_accepted_proof': proof, 'source_quote_count': len(ctx['sources']), 'compiled_quote_cache_entries': len(ctx['compiled']), 'route_cache_entries': len(ctx['cache'].entries), 'cash_and_three_scores_unchanged': True, 'prior_product_sales_are_conditional': True}
_r10_integration_IMPLEMENTATION_IDS = {'scheduler': '495cdc1c961216f9bcbd07df7fa797fda006406c57810e580a92a7eded64467d', 'checker': '2bf5c12c400effed3246f35abab18ac2c0132a17b7aba2139548e0d0ad64dee3', 'compiler': 'c908e47fed9236d9c74359e27758a0af237ece2a9da6993aed5e72c69764b402'}

def dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def home(p):
    return min(ACCESS, key=lambda q: (dist(p, q), q))

def move(p, q):
    dx, dy = (q[0] - p[0], q[1] - p[1])
    if abs(dx) >= abs(dy) and dx:
        return ['EAST' if dx > 0 else 'WEST']
    if dy:
        return ['SOUTH' if dy > 0 else 'NORTH']
    return ['PASS']

def curve(shape, x, scale):
    if shape == 'sqrt':
        return math.sqrt(x)
    if shape == 'log':
        return math.log1p(x)
    if shape == 'log10':
        return math.log10(1 + x)
    if shape == 'sq':
        return x * x
    if shape == 'hinge':
        z = x / scale
        return z + 8 * max(0, z - 1) ** 2
    return x

def price(item, supply, overrides=None):
    b, t, low, la, high, ha = MARKET[item]
    p = (overrides or {}).get(item, {})
    b, t = (p.get('base', b), p.get('T', t))
    center = p.get('I0', 10000)
    delta = supply - center
    shape = p.get('below_func', low) if delta < 0 else p.get('above_func', high)
    amp = p.get('below_target', la) if delta < 0 else p.get('above_target', ha)
    adjustment = amp * b * curve(shape, abs(delta), t) / max(1e-09, curve(shape, t, t))
    return max(1, int(round(b + (adjustment if delta < 0 else -adjustment))))

def counts(farm, private=None):
    c = Counter()
    for row in farm['tiles']:
        for tile in row:
            if isinstance(tile, dict):
                if 'animal' in tile:
                    c[tile['animal']] += 1
                elif tile.get('kind') == 'PLANT':
                    c[tile['crop']] += 1
    if private is not None:
        for a in ANIMALS:
            c[a] += private['shed'].get(a, 0)
            c[a] += sum((i.get(a, 0) for i in private.get('inventories', [])))
    return c

def inventory_total(private, item):
    return private.get('shed', {}).get(item, 0) + sum((i.get(item, 0) for i in private.get('inventories', [])))

def summary(obs):
    f = obs['farms'][obs['player']]
    return {'day': obs['day'], 'hour': obs['hour'], 'money': f['money'], 'land': len(f['unlocked_quadrants']), 'hands': len(f['hands']), 'assets': dict(counts(f, obs['private'])), 'seeds': dict(obs['private']['seeds'])}

def new_state(obs):
    return {'last_step': -1, 'last_day': -1, 'previous': None, 'issued': [], 'procurement': [], 'tasks': {}, 'metrics': Counter(), 'daily': [], 'expert': 'balanced', 'forecasts': {}, 'crop_choice': 'WHEAT'}

def confirm_orders(st, obs):
    prev = st['previous']
    if prev is None:
        return
    now = summary(obs)
    plant_used = Counter((a[1] for a in st.get('unit_actions', []) if a and a[0] == 'PLANT'))
    for order in st['issued']:
        op = order[0]
        if op == 'BUY_LAND':
            requested, got = (1, now['land'] - prev['land'])
        elif op == 'HIRE' and now['day'] == prev['day']:
            continue
        elif op == 'BUY_ANIMAL':
            requested = order[2]
            got = now['assets'].get(order[1], 0) - prev['assets'].get(order[1], 0)
        elif op == 'BUY_SEED':
            requested = order[2]
            got = now['seeds'].get(order[1], 0) - prev['seeds'].get(order[1], 0) + plant_used[order[1]]
        else:
            continue
        got = max(0, min(requested, got))
        st['metrics']['purchase_requested'] += requested
        st['metrics']['purchase_confirmed'] += got
        if got != requested:
            st['procurement'].append({'step': st['last_step'], 'order': order, 'confirmed': got, 'missing': requested - got})
    hires = sum((o[0] == 'HIRE' for o in st['issued']))
    if hires and now['day'] == prev['day']:
        st['metrics']['hire_requested'] += hires
        st['metrics']['hire_confirmed'] += max(0, now['hands'] - prev['hands'])
    st['previous'] = now
'R7 最小逐日投资层；由构建脚本并入单文件，不调用其他完整策略。'

def project_calendar(tile, day, hour=0, position=(4, 4)):
    """每日照护、及时采收交付的模型日历；物量可用纯规则控制核对。"""
    goods, work, feed = ({}, Counter(), Counter())
    t = dict(tile)
    distance = dist(position, home(position))

    def product(d, item, qty):
        qty = int(qty)
        if qty <= 0 or d > 29:
            return
        if d == 29 and day == 29 and (hour + distance + 2 > 22):
            return
        goods.setdefault(d, Counter())[item] += qty
        work[d] += 2 + distance
    if 'animal' in t:
        a = t['animal']
        spec = ANIMALS[a]
        product(day, spec[5], t.get('yield_units', 0))
        if t.get('fertilizer_available'):
            product(day, 'FERTILIZER', 1)
        pending = int(t.get('pending_care_bonus', 0))
        for d in range(day, 29):
            fed = bool(t.get('fed_today')) if d == day else False
            cared = bool(t.get('cared_today')) if d == day else False
            if not fed:
                work[d] += 1
                feed[d] += 1
            if d < 28 and (not cared):
                work[d] += 1
                cared = True
            next_day = d + 1
            age = next_day - t['placed_day'] - spec[2]
            if age >= 0 and age % spec[3] == 0:
                product(next_day, spec[5], min(spec[4], 1 + pending))
                pending = 0
            if cared:
                pending += 1
            product(next_day, 'FERTILIZER', 1)
    else:
        c = t['crop']
        _, first, last, interval, cap = CROPS[c]
        stock = int(t.get('yield_units', 0))
        dry = int(t.get('consecutive_unwatered', 0))
        for d in range(day, 30):
            age = d - t['planted_day']
            if age < 0:
                continue
            fertilized = t.get('fertilized_until_day', -1) >= d
            watered = bool(t.get('watered_today')) if d == day else False
            if interval:
                final_age = first + interval * (cap - 1)
                next_produces = age + 1 >= first and (age + 1 - first) % interval == 0 and (age + 1 <= final_age)
                need = not watered and d < 29 and (age < final_age) and (dry >= 1 or next_produces or age == 0)
            else:
                growth = (last + 1) // 2 <= age <= last
                need = not watered and age <= last and (dry >= 1 or growth or age == 0)
            if need:
                work[d] += 1
                watered = True
                if not interval and growth:
                    stock = min(cap, stock + (2 if fertilized else 1))
            if stock and age >= first and (interval or stock >= cap or age >= last or (d == 29)):
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
            if interval and age >= final_age and (not stock):
                break
    for d in list(work):
        if work[d]:
            work[d] += max(1, distance)
    return {'goods': {d: dict(v) for d, v in goods.items()}, 'work': dict(work), 'feed': dict(feed)}

def dated_market_model(obs):
    """每日报价为当天本方拟售项成交前；当前田间现货从次日进入留存供给。"""
    day = obs['day']
    supply = {p: float(obs['market']['inventory'].get(p, 10000)) for p in PRODUCTS}
    demand = {p: 0.0 if p == 'FERTILIZER' else 1.0 for p in PRODUCTS}
    for shop in obs['town'].get('unlocked_shops', []):
        products = SHOPS.get(shop, ())
        for p in products:
            demand[p] += 12 if len(products) == 1 else 6
    calendars = []
    for seat, farm in enumerate(obs['farms']):
        for y, row in enumerate(farm['tiles']):
            for x, tile in enumerate(row):
                if isinstance(tile, dict) and ('animal' in tile or tile.get('kind') == 'PLANT'):
                    calendars.append((seat, (x, y), project_calendar(tile, day, obs['hour'], (x, y))))
    prices, inventories = ({}, {})
    for d in range(day, 30):
        if d > day:
            for p in PRODUCTS:
                supply[p] -= demand[p]
            for _, _, cal in calendars:
                for p, n in cal['goods'].get(d - 1, {}).items():
                    supply[p] += n
                supply['WHEAT'] -= cal['feed'].get(d - 1, 0)
        inventories[d] = dict(supply)
        prices[d] = {p: price(p, supply[p], obs['market'].get('params')) for p in PRODUCTS}
    return {'prices': prices, 'inventories': inventories, 'demand': demand, 'calendars': calendars}

def apply_project_supply(obs, model, cal):
    for d in range(obs['day'], 30):
        for future_day in range(d + 1, 30):
            for p, n in cal['goods'].get(d, {}).items():
                model['inventories'][future_day][p] += n
            model['inventories'][future_day]['WHEAT'] -= cal['feed'].get(d, 0)
            model['prices'][future_day] = {p: price(p, model['inventories'][future_day][p], obs['market'].get('params')) for p in PRODUCTS}

def labor_schedule(obs, workload, market_order_reserve=0):
    """当前工人已到场；新工次帧可动，未来雇工保留真实费用和每帧订单限制。"""
    f = obs['farms'][obs['player']]
    existing = len(f['hands'])
    target, feasible = (existing, True)
    cash_by_day, capacity_by_day = ({}, {})
    cap = int(PARAMS['max_hands'])
    for d in range(obs['day'], 30):
        need = max(0, workload.get(d, 0))
        slots = (23 if d == 29 else 24) - (obs['hour'] if d == obs['day'] else 0)
        base = existing if d == obs['day'] else 0
        workers = base
        capacity = (1 + base) * max(0, slots)
        can_hire = d != obs['day'] or obs['hour'] < 8
        first_frame_hires = max(0, 10 - market_order_reserve) if d == obs['day'] else 10
        limit = min(cap, existing + first_frame_hires) if d == obs['day'] and obs['hour'] == 7 else cap
        while capacity < need and workers < limit and can_hire:
            delay = 1 if workers - base < first_frame_hires else 2 + (workers - base - first_frame_hires) // 10
            capacity += max(0, slots - delay)
            workers += 1
        if capacity < need:
            feasible = False
        if d == obs['day']:
            target = min(workers, existing + first_frame_hires)
            ordinal = int(f.get('hires_today', existing))
        else:
            ordinal = 0
        cash_by_day[d] = sum((FIB[min(ordinal + i, len(FIB) - 1)] for i in range(workers - base)))
        capacity_by_day[d] = capacity
    return {'feasible': feasible, 'hire_target_today': target, 'cash_by_day': cash_by_day, 'capacity_by_day': capacity_by_day, 'total_cost': sum(cash_by_day.values())}

def investment_quote(obs, item, position, market_model, seed_credit=False, already_owned=False, committed=False):
    """成本分机会价值与现金；时钟按顺序启动，产出是假设照护及时的模型。"""
    day, hour = (obs['day'], obs['hour'])
    f = obs['farms'][obs['player']]
    x, y = position
    tile = f['tiles'][y][x]
    actors = [tuple(f['farmer'])] + [tuple(p) for p in f['hands']]
    approach = min((dist(p, position) for p in actors))
    distance = dist(position, home(position))
    if item in ANIMALS and isinstance(tile, dict) and (tile.get('kind') in ('COOP', 'PASTURE')) and (tile.get('kind') != ANIMALS[item][1]):
        return None
    build = item in ANIMALS and (not (isinstance(tile, dict) and tile.get('kind') == ANIMALS[item][1] and ('animal' not in tile)))
    setup_work = Counter()
    if item in ANIMALS:
        build_actions = approach + (1 if tile is not None else 0) + 1 if build else 0
        if build and (not committed) and (hour + build_actions > 21):
            return None
        carriers = [i for i, inv in enumerate(obs['private']['inventories']) if inv.get(item, 0)] if already_owned else []
        if carriers and (not build):
            transport = min((dist(actors[i], position) + 1 for i in carriers))
            wait_buy = 0
        else:
            transport = 2 * distance + 2 if build else min((dist(p, home(position)) for p in actors)) + distance + 2
            wait_buy = 0 if already_owned else 1
        start_step = obs['step'] + build_actions + wait_buy + transport - 1
        active_steps = build_actions + transport
        start_day = start_step // 24
        future = {'kind': ANIMALS[item][1], 'animal': item, 'placed_day': start_day, 'yield_units': 0, 'fed_today': False, 'cared_today': False, 'fertilizer_available': False, 'pending_care_bonus': 0}
        fixed = 0 if already_owned else ANIMALS[item][0]
    else:
        if isinstance(tile, dict) and tile.get('kind') != 'WEED':
            return None
        clear = int(tile is not None)
        wait_buy = int(not seed_credit)
        if not committed and (day >= 28 or hour + wait_buy >= 21 or hour + wait_buy + approach + clear + 1 > 21):
            return None
        active_steps = approach + clear + 1
        start_step = obs['step'] + wait_buy + active_steps - 1
        start_day = start_step // 24
        future = {'kind': 'PLANT', 'crop': item, 'planted_day': start_day, 'yield_units': 0 if CROPS[item][3] else 1, 'watered_today': False, 'consecutive_unwatered': 1, 'fertilized_until_day': -1}
        fixed = 0 if seed_credit else CROPS[item][0]
    if start_step >= 718 or start_day > 29:
        return None
    cal = project_calendar(future, start_day, start_step % 24 + 1, position)
    for k in range(active_steps):
        action_day = min(29, (obs['step'] + k) // 24)
        setup_work[action_day] += 1
    for d, n in setup_work.items():
        cal['work'][d] = cal['work'].get(d, 0) + n
    gross = sum((sum((price(p, market_model['inventories'][d][p] + k, obs['market'].get('params')) for k in range(n))) for d, goods in cal['goods'].items() for p, n in goods.items()))
    feed_cost = sum((sum((price('WHEAT', market_model['inventories'][d]['WHEAT'] - k - 1, obs['market'].get('params')) for k in range(n))) for d, n in cal['feed'].items()))
    primary = ANIMALS[item][5] if item in ANIMALS else item
    productive_days = [d for d, goods in cal['goods'].items() if goods.get(primary, 0)]
    if not productive_days and (not committed):
        return None
    labor = sum(cal['work'].values())
    return {'item': item, 'position': tuple(position), 'build_first': build, 'start_step_model': start_step, 'first_product_day': min(productive_days) if productive_days else None, 'calendar': cal, 'fixed_cash': fixed, 'setup_work': dict(setup_work), 'gross_cash_model': gross, 'feed_cost_model': feed_cost, 'net_before_hiring_model': gross - fixed - feed_cost, 'labor': labor, 'score_before_hiring': (gross - fixed - feed_cost) / max(1, labor)}

def feed_ledger(obs, model, requirements, owned_wheat):
    """同一饲料物量：自有麦按可售价值占用，只有不足部分按逐单位买价占现金。"""
    left = max(0, int(owned_wheat))
    cash, opportunity, owned_used = (0.0, 0.0, 0)
    buys = {}
    for d in sorted(requirements):
        n = max(0, int(requirements[d]))
        held = min(left, n)
        left -= held
        owned_used += held
        supply = model['inventories'][d]['WHEAT']
        opportunity += sum((price('WHEAT', supply + k, obs['market'].get('params')) for k in range(held)))
        bought = n - held
        cost = sum((price('WHEAT', supply - k - 1, obs['market'].get('params')) for k in range(bought)))
        cash += cost
        opportunity += cost
        if bought:
            buys[d] = bought
    return {'cash': cash, 'opportunity': opportunity, 'owned_used': owned_used, 'owned_remaining': left, 'buys_by_day': buys, 'units': sum(requirements.values())}

def economic_plan_full_reserve(obs, st):
    selection_mode = PARAMS.get('investment_selection', 'terminal_net')
    if selection_mode not in ('terminal_net', 'labor_ratio'):
        raise ValueError('unknown investment selection objective')
    f, private, day = (obs['farms'][obs['player']], obs['private'], obs['day'])
    own = counts(f, private)
    model = dated_market_model(obs)
    st['forecasts'] = dict(model['prices'][day])
    st['crop_scores'] = {}
    owned = [(x, y) for y, row in enumerate(f['tiles']) for x, t in enumerate(row) if t != 'LOCKED']
    ranked = sorted(owned, key=lambda p: (dist(p, home(p)), p[1], p[0]))
    free = [p for p in ranked if f['tiles'][p[1]][p[0]] is None or (isinstance(f['tiles'][p[1]][p[0]], dict) and f['tiles'][p[1]][p[0]].get('kind') == 'WEED')]
    structures = [p for p in ranked if isinstance(f['tiles'][p[1]][p[0]], dict) and f['tiles'][p[1]][p[0]].get('kind') in ('PASTURE', 'COOP') and ('animal' not in f['tiles'][p[1]][p[0]])]
    workload, feed = (Counter(), Counter())
    for seat, _, cal in model['calendars']:
        if seat == obs['player']:
            workload.update(cal['work'])
            feed.update(cal['feed'])
    builds, reserved, plant_permits = ({}, set(), {})
    committed_plant_sites = set()
    seeds = Counter(private['seeds'])
    committed_fixed, commitments = (0.0, [])
    in_transit = {a: inventory_total(private, a) for a in ANIMALS}
    unassigned_transit = Counter(in_transit)
    transit_calendars = []
    previous_builds = st.get('latest_investment_plan', {}).get('build_permits', {})
    for contract in st.get('contracts', {}).values():
        pos = tuple(contract['target'])
        if pos not in free:
            continue
        ops = [stage['op'] for stage in contract.get('stages', [])]
        plant = next((op[1] for op in ops if op[0] == 'PLANT'), None)
        building = next((op[0][6:] for op in ops if op[0].startswith('BUILD_')), None)
        if not plant and (not building):
            continue
        item = plant or previous_builds.get(pos, 'GOOSE' if building == 'COOP' else 'COW')
        reserved.add(pos)
        existing_animal = bool(building and unassigned_transit[item] > 0)
        if existing_animal:
            unassigned_transit[item] -= 1
        q = investment_quote(obs, item, pos, model, seed_credit=bool(plant and seeds[item]), already_owned=existing_animal, committed=True)
        if q:
            workload.update(q['calendar']['work'])
            feed.update(q['calendar']['feed'])
            committed_fixed += q['fixed_cash']
            commitments.append(q)
            if existing_animal:
                transit_calendars.append(q)
            apply_project_supply(obs, model, q['calendar'])
        if plant:
            plant_permits[pos] = plant
            committed_plant_sites.add(pos)
            seeds[plant] = max(0, seeds[plant] - 1)
        else:
            builds[pos] = item
    used_structures = set()
    for animal in ANIMALS:
        for _ in range(unassigned_transit[animal]):
            site = next((p for p in structures if p not in used_structures and f['tiles'][p[1]][p[0]]['kind'] == ANIMALS[animal][1]), None)
            if site is None:
                site = next((p for p in free if p not in reserved), None)
                if site is not None:
                    builds[site] = animal
            if site is None:
                continue
            reserved.add(site)
            used_structures.add(site)
            q = investment_quote(obs, animal, site, model, already_owned=True, committed=True)
            if q:
                workload.update(q['calendar']['work'])
                feed.update(q['calendar']['feed'])
                transit_calendars.append(q)
                apply_project_supply(obs, model, q['calendar'])
    n_animals = sum((own[a] for a in ANIMALS))
    buffer_units = max(3, n_animals // 2) if n_animals and day < 29 else 0
    feed_cash_requirements = Counter(feed)
    feed_cash_requirements[day] += buffer_units
    base_feed = feed_ledger(obs, model, feed_cash_requirements, inventory_total(private, 'WHEAT'))
    feed_order_needed = bool(n_animals and day < 29 and (inventory_total(private, 'WHEAT') < n_animals + max(3, n_animals // 2)))
    material_order_keys = {('feed', 'WHEAT')} if feed_order_needed else set()
    base_labor = labor_schedule(obs, workload, len(material_order_keys))
    base_reserved = committed_fixed + base_feed['cash'] + base_labor['total_cost']
    cash = max(0.0, float(f['money']) - base_reserved)
    base_summary = {'work': dict(workload), 'feed': dict(feed), 'in_transit': in_transit, 'transit_project_count': len(transit_calendars), 'contract_count': len(commitments), 'feed_cash': base_feed['cash'], 'feed_opportunity': base_feed['opportunity'], 'owned_feed_used': base_feed['owned_used'], 'hire_cash': base_labor['total_cost'], 'committed_fixed_cash': committed_fixed, 'reserved_cash': base_reserved}
    animal_orders, seed_orders, accepted, rejected = (Counter(), Counter(), [], Counter())
    expert_items = {'balanced': ('WHEAT', 'CARROT'), 'dairy': ('COW',), 'fiber': ('SHEEP',), 'horticulture': ('TOMATO', 'STRAWBERRY', 'MELON')}

    def budget_quote(item, pos):
        q = investment_quote(obs, item, pos, model, seeds.get(item, 0) > 0)
        if not q:
            return (None, 'startup_or_maturity')
        next_work = workload + Counter(q['calendar']['work'])
        next_keys = set(material_order_keys)
        if q['fixed_cash'] and (not q['build_first']):
            next_keys.add(('animal' if item in ANIMALS else 'seed', item))
        labor = labor_schedule(obs, next_work, len(next_keys))
        marginal_hires = max(0.0, labor['total_cost'] - base_labor['total_cost'])
        cash_feed = Counter(q['calendar']['feed'])
        if item in ANIMALS and (not n_animals):
            cash_feed[day] += 3
        next_ledger = feed_ledger(obs, model, cash_feed, base_feed['owned_remaining'])
        marginal_feed_cash = next_ledger['cash']
        marginal_opportunity = next_ledger['opportunity']
        net = q['gross_cash_model'] - q['fixed_cash'] - marginal_opportunity - marginal_hires
        cash_need = q['fixed_cash'] + marginal_feed_cash + marginal_hires
        q.update(net_cash_model=net, cash_reserved_model=cash_need, feed_cash_model=marginal_feed_cash, feed_cost_model=marginal_opportunity, hire_cash_model=marginal_hires, score=net / max(1, q['labor']), selection_score=net if selection_mode == 'terminal_net' else net / max(1, q['labor']), feed_ledger=next_ledger, material_order_keys=next_keys)
        if not labor['feasible']:
            return (q, 'labor')
        if net <= 0:
            return (q, 'nonpositive_net')
        if cash_need > cash:
            return (q, 'cash')
        return (q, None)
    offers, expert_scores = ([], {e: -1000000000.0 for e in expert_items})
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
                q['expert'] = expert
                offers.append(q)
                expert_scores[expert] = max(expert_scores[expert], q['selection_score'])
                if item in CROPS:
                    st['crop_scores'][item] = max(st['crop_scores'].get(item, -1000000000.0), q['score'])
    chosen = PARAMS['router']
    if chosen == 'adaptive':
        chosen = max(expert_scores, key=expert_scores.get)
    if chosen not in expert_items:
        chosen = 'balanced'
    st['expert'] = chosen
    st['metrics']['expert_' + chosen] += 1
    st['crop_choice'] = max(st['crop_scores'], key=st['crop_scores'].get) if st['crop_scores'] else None
    animal_admitted = False
    for q0 in sorted((q for q in offers if q['expert'] == chosen), key=lambda q: (-q['selection_score'], dist(q['position'], home(q['position'])), q['position'])):
        item, pos = (q0['item'], q0['position'])
        if pos in reserved or pos in plant_permits or (item in ANIMALS and animal_admitted):
            continue
        q, reason = budget_quote(item, pos)
        if reason:
            rejected[reason] += 1
            continue
        q['expert'] = chosen
        cash -= q['cash_reserved_model']
        workload.update(q['calendar']['work'])
        feed_cash_requirements.update(q['calendar']['feed'])
        material_order_keys = q['material_order_keys']
        base_labor = labor_schedule(obs, workload, len(material_order_keys))
        base_feed['owned_used'] += q['feed_ledger']['owned_used']
        base_feed['owned_remaining'] = q['feed_ledger']['owned_remaining']
        base_feed['cash'] += q['feed_ledger']['cash']
        base_feed['opportunity'] += q['feed_ledger']['opportunity']
        accepted.append(q)
        if item in ANIMALS:
            reserved.add(pos)
            animal_admitted = True
            if q['build_first']:
                builds[pos] = item
            else:
                animal_orders[item] += 1
        else:
            plant_permits[pos] = item
            if seeds[item] > 0:
                seeds[item] -= 1
            else:
                seed_orders[item] += 1
        apply_project_supply(obs, model, q['calendar'])
    occupied = sum((isinstance(t, dict) for row in f['tiles'] for t in row if t != 'LOCKED'))
    lands = len(f['unlocked_quadrants'])
    land_cost = (1000, 2000, 4000)[lands - 1] if 0 < lands < 3 else 0
    hire_orders = max(0, base_labor['hire_target_today'] - len(f['hands'])) if obs['hour'] < 8 else 0
    buy_land = bool(land_cost and 3 <= day < 19 and (occupied >= lands * 25 - 8) and (cash > land_cost + 600) and (hire_orders + len(material_order_keys) < 10))
    if buy_land:
        cash -= land_cost
    st['metrics']['investment_permit_quotes'] += len(accepted)
    st['metrics']['investment_budget_rejected_quotes'] += sum(rejected.values())
    plan = {'counts': own, 'animals': {a: own[a] + animal_orders[a] for a in ANIMALS}, 'melon_cap': 100, 'strawberry_cap': 100, 'crop_choice': st['crop_choice'], 'demand': model['demand'], 'build_permits': builds, 'reserved_animal_sites': reserved, 'plant_permits': plant_permits, 'committed_plant_sites': committed_plant_sites, 'animal_purchases': dict(animal_orders), 'seed_purchases': dict(seed_orders), 'buy_land': buy_land, 'land_cash': land_cost if buy_land else 0, 'material_order_slots': len(material_order_keys) + int(buy_land), 'hire_target_today': base_labor['hire_target_today'], 'planned_work': dict(workload), 'labor_plan': base_labor, 'existing_obligations': base_summary, 'remaining_investment_cash_model': cash, 'admitted_investments': accepted, 'expert_quote_scores': expert_scores, 'in_transit_existing': in_transit, 'owned_wheat_reserved': base_feed['owned_used'], 'rejected_types': dict(rejected)}
    st['latest_investment_plan'] = plan
    receipt = {'step': obs['step'], 'expert': chosen, 'selection_objective': selection_mode, 'selected_expert_score': expert_scores[chosen] if expert_scores[chosen] > -1000000000.0 else None, 'expert_selection_scores': {e: v if v > -1000000000.0 else None for e, v in expert_scores.items()}, 'actual_cash': f['money'], 'actual_wheat': inventory_total(private, 'WHEAT'), 'existing': base_summary, 'remaining_cash': cash, 'land_cash': plan['land_cash'], 'rejected_types': dict(rejected), 'work': dict(workload), 'capacity': base_labor['capacity_by_day'], 'admitted': [{k: list(q[k]) if k == 'position' else q[k] for k in ('item', 'position', 'build_first', 'cash_reserved_model', 'feed_cash_model', 'feed_cost_model', 'hire_cash_model', 'net_cash_model', 'score', 'selection_score')} for q in accepted]}
    st.setdefault('investment_receipts', []).append(receipt)
    st['investment_receipts'] = st['investment_receipts'][-720:]
    return plan

def _r10_integration_legacy_economic_plan_prefix(obs, st):
    selection_mode = PARAMS.get('investment_selection', 'terminal_net')
    if selection_mode not in ('terminal_net', 'labor_ratio'):
        raise ValueError('unknown investment selection objective')
    f, private, day = (obs['farms'][obs['player']], obs['private'], obs['day'])
    own = counts(f, private)
    model = dated_market_model(obs)
    credit_batches, credit_sources = credit_batches_from_field(obs, model)
    st['forecasts'] = dict(model['prices'][day])
    st['crop_scores'] = {}
    owned = [(x, y) for y, row in enumerate(f['tiles']) for x, t in enumerate(row) if t != 'LOCKED']
    ranked = sorted(owned, key=lambda p: (dist(p, home(p)), p[1], p[0]))
    free = [p for p in ranked if f['tiles'][p[1]][p[0]] is None or (isinstance(f['tiles'][p[1]][p[0]], dict) and f['tiles'][p[1]][p[0]].get('kind') == 'WEED')]
    structures = [p for p in ranked if isinstance(f['tiles'][p[1]][p[0]], dict) and f['tiles'][p[1]][p[0]].get('kind') in ('PASTURE', 'COOP') and ('animal' not in f['tiles'][p[1]][p[0]])]
    workload, feed = (Counter(), Counter())
    for seat, _, cal in model['calendars']:
        if seat == obs['player']:
            workload.update(cal['work'])
            feed.update(cal['feed'])
    builds, reserved, plant_permits = ({}, set(), {})
    committed_plant_sites = set()
    seeds = Counter(private['seeds'])
    committed_fixed, commitments = (0.0, [])
    in_transit = {a: inventory_total(private, a) for a in ANIMALS}
    unassigned_transit = Counter(in_transit)
    transit_calendars = []
    previous_builds = st.get('latest_investment_plan', {}).get('build_permits', {})
    for contract in st.get('contracts', {}).values():
        pos = tuple(contract['target'])
        if pos not in free:
            continue
        ops = [stage['op'] for stage in contract.get('stages', [])]
        plant = next((op[1] for op in ops if op[0] == 'PLANT'), None)
        building = next((op[0][6:] for op in ops if op[0].startswith('BUILD_')), None)
        if not plant and (not building):
            continue
        item = plant or previous_builds.get(pos, 'GOOSE' if building == 'COOP' else 'COW')
        reserved.add(pos)
        existing_animal = bool(building and unassigned_transit[item] > 0)
        if existing_animal:
            unassigned_transit[item] -= 1
        q = investment_quote(obs, item, pos, model, seed_credit=bool(plant and seeds[item]), already_owned=existing_animal, committed=True)
        if q:
            workload.update(q['calendar']['work'])
            feed.update(q['calendar']['feed'])
            committed_fixed += q['fixed_cash']
            commitments.append(q)
            if existing_animal:
                transit_calendars.append(q)
            apply_project_supply(obs, model, q['calendar'])
        if plant:
            plant_permits[pos] = plant
            committed_plant_sites.add(pos)
            seeds[plant] = max(0, seeds[plant] - 1)
        else:
            builds[pos] = item
    used_structures = set()
    for animal in ANIMALS:
        for _ in range(unassigned_transit[animal]):
            site = next((p for p in structures if p not in used_structures and f['tiles'][p[1]][p[0]]['kind'] == ANIMALS[animal][1]), None)
            if site is None:
                site = next((p for p in free if p not in reserved), None)
                if site is not None:
                    builds[site] = animal
            if site is None:
                continue
            reserved.add(site)
            used_structures.add(site)
            q = investment_quote(obs, animal, site, model, already_owned=True, committed=True)
            if q:
                workload.update(q['calendar']['work'])
                feed.update(q['calendar']['feed'])
                transit_calendars.append(q)
                apply_project_supply(obs, model, q['calendar'])
    n_animals = sum((own[a] for a in ANIMALS))
    buffer_units = max(3, n_animals // 2) if n_animals and day < 29 else 0
    feed_cash_requirements = Counter(feed)
    feed_cash_requirements[day] += buffer_units
    base_feed = feed_ledger(obs, model, feed_cash_requirements, inventory_total(private, 'WHEAT'))
    feed_order_needed = bool(n_animals and day < 29 and (inventory_total(private, 'WHEAT') < n_animals + max(3, n_animals // 2)))
    material_order_keys = {('feed', 'WHEAT')} if feed_order_needed else set()
    base_labor = labor_schedule(obs, workload, len(material_order_keys))
    base_reserved = committed_fixed + base_feed['cash'] + base_labor['total_cost']
    cash = max(0.0, float(f['money']) - base_reserved)
    base_summary = {'work': dict(workload), 'feed': dict(feed), 'in_transit': in_transit, 'transit_project_count': len(transit_calendars), 'contract_count': len(commitments), 'feed_cash': base_feed['cash'], 'feed_opportunity': base_feed['opportunity'], 'owned_feed_used': base_feed['owned_used'], 'hire_cash': base_labor['total_cost'], 'committed_fixed_cash': committed_fixed, 'reserved_cash': base_reserved}
    credit_ceiling = price_credit_batches(obs, model, credit_batches)
    funding_requirements = Counter(feed_cash_requirements)
    funding_fixed = committed_fixed
    funding_book = funding_cash_book(obs, model, funding_requirements, base_labor, funding_fixed, credit_batches, credit_ceiling)
    initial_funding_book = funding_book
    cash = funding_book['additional_current_spend']
    animal_orders, seed_orders, accepted, rejected = (Counter(), Counter(), [], Counter())
    expert_items = {'balanced': ('WHEAT', 'CARROT'), 'dairy': ('COW',), 'fiber': ('SHEEP',), 'horticulture': ('TOMATO', 'STRAWBERRY', 'MELON')}

    def budget_quote(item, pos):
        q = investment_quote(obs, item, pos, model, seeds.get(item, 0) > 0)
        if not q:
            return (None, 'startup_or_maturity')
        next_work = workload + Counter(q['calendar']['work'])
        next_keys = set(material_order_keys)
        if q['fixed_cash'] and (not q['build_first']):
            next_keys.add(('animal' if item in ANIMALS else 'seed', item))
        labor = labor_schedule(obs, next_work, len(next_keys))
        marginal_hires = max(0.0, labor['total_cost'] - base_labor['total_cost'])
        cash_feed = Counter(q['calendar']['feed'])
        if item in ANIMALS and (not n_animals):
            cash_feed[day] += 3
        next_ledger = feed_ledger(obs, model, cash_feed, base_feed['owned_remaining'])
        marginal_feed_cash = next_ledger['cash']
        marginal_opportunity = next_ledger['opportunity']
        net = q['gross_cash_model'] - q['fixed_cash'] - marginal_opportunity - marginal_hires
        cash_need = q['fixed_cash'] + marginal_feed_cash + marginal_hires
        q.update(net_cash_model=net, cash_reserved_model=cash_need, feed_cash_model=marginal_feed_cash, feed_cost_model=marginal_opportunity, hire_cash_model=marginal_hires, score=net / max(1, q['labor']), selection_score=net if selection_mode == 'terminal_net' else net / max(1, q['labor']), feed_ledger=next_ledger, material_order_keys=next_keys)
        if not labor['feasible']:
            return (q, 'labor')
        if net <= 0:
            return (q, 'nonpositive_net')
        trial_model = funding_trial_model(obs, model, q['calendar'])
        trial_requirements = funding_requirements + cash_feed
        trial = funding_cash_book(obs, trial_model, trial_requirements, labor, funding_fixed + q['fixed_cash'], credit_batches, credit_ceiling)
        admission = prefix_admission(funding_book, trial, cash_need)
        q.update(funding_trial=trial, funding_requirements=trial_requirements, funding_admission=admission, original_full_horizon_new_cash=cash_need)
        if admission is None:
            return (q, 'cash_prefix')
        return (q, None)
    offers, expert_scores = ([], {e: -1000000000.0 for e in expert_items})
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
                q['expert'] = expert
                offers.append(q)
                expert_scores[expert] = max(expert_scores[expert], q['selection_score'])
                if item in CROPS:
                    st['crop_scores'][item] = max(st['crop_scores'].get(item, -1000000000.0), q['score'])
    chosen = PARAMS['router']
    if chosen == 'adaptive':
        chosen = max(expert_scores, key=expert_scores.get)
    if chosen not in expert_items:
        chosen = 'balanced'
    st['expert'] = chosen
    st['metrics']['expert_' + chosen] += 1
    st['crop_choice'] = max(st['crop_scores'], key=st['crop_scores'].get) if st['crop_scores'] else None
    animal_admitted = False
    for q0 in sorted((q for q in offers if q['expert'] == chosen), key=lambda q: (-q['selection_score'], dist(q['position'], home(q['position'])), q['position'])):
        item, pos = (q0['item'], q0['position'])
        if pos in reserved or pos in plant_permits or (item in ANIMALS and animal_admitted):
            continue
        q, reason = budget_quote(item, pos)
        if reason:
            rejected[reason] += 1
            continue
        q['expert'] = chosen
        funding_book = q['funding_trial']
        funding_requirements = q['funding_requirements']
        funding_fixed += q['fixed_cash']
        cash = funding_book['additional_current_spend']
        workload.update(q['calendar']['work'])
        feed_cash_requirements.update(q['calendar']['feed'])
        material_order_keys = q['material_order_keys']
        base_labor = labor_schedule(obs, workload, len(material_order_keys))
        base_feed['owned_used'] += q['feed_ledger']['owned_used']
        base_feed['owned_remaining'] = q['feed_ledger']['owned_remaining']
        base_feed['cash'] += q['feed_ledger']['cash']
        base_feed['opportunity'] += q['feed_ledger']['opportunity']
        accepted.append(q)
        if item in ANIMALS:
            reserved.add(pos)
            animal_admitted = True
            if q['build_first']:
                builds[pos] = item
            else:
                animal_orders[item] += 1
        else:
            plant_permits[pos] = item
            if seeds[item] > 0:
                seeds[item] -= 1
            else:
                seed_orders[item] += 1
        apply_project_supply(obs, model, q['calendar'])
    occupied = sum((isinstance(t, dict) for row in f['tiles'] for t in row if t != 'LOCKED'))
    lands = len(f['unlocked_quadrants'])
    land_cost = (1000, 2000, 4000)[lands - 1] if 0 < lands < 3 else 0
    hire_orders = max(0, base_labor['hire_target_today'] - len(f['hands'])) if obs['hour'] < 8 else 0
    buy_land = bool(land_cost and 3 <= day < 19 and (occupied >= lands * 25 - 8) and (cash > land_cost + 600) and (hire_orders + len(material_order_keys) < 10))
    if buy_land:
        land_trial = funding_cash_book(obs, model, funding_requirements, base_labor, funding_fixed + land_cost, credit_batches, credit_ceiling)
        buy_land = land_trial['feasible']
        if buy_land:
            funding_book = land_trial
            funding_fixed += land_cost
            cash = funding_book['additional_current_spend']
    st['metrics']['investment_permit_quotes'] += len(accepted)
    st['metrics']['investment_budget_rejected_quotes'] += sum(rejected.values())
    plan = {'counts': own, 'animals': {a: own[a] + animal_orders[a] for a in ANIMALS}, 'melon_cap': 100, 'strawberry_cap': 100, 'crop_choice': st['crop_choice'], 'demand': model['demand'], 'build_permits': builds, 'reserved_animal_sites': reserved, 'plant_permits': plant_permits, 'committed_plant_sites': committed_plant_sites, 'animal_purchases': dict(animal_orders), 'seed_purchases': dict(seed_orders), 'buy_land': buy_land, 'land_cash': land_cost if buy_land else 0, 'material_order_slots': len(material_order_keys) + int(buy_land), 'hire_target_today': base_labor['hire_target_today'], 'planned_work': dict(workload), 'labor_plan': base_labor, 'existing_obligations': base_summary, 'remaining_investment_cash_model': cash, 'admitted_investments': accepted, 'expert_quote_scores': expert_scores, 'in_transit_existing': in_transit, 'owned_wheat_reserved': base_feed['owned_used'], 'rejected_types': dict(rejected)}
    plan.update(cash_funding_model='cash_prefix', funding_book=funding_book, initial_funding_book=initial_funding_book, credit_source_positions=credit_sources)
    st['latest_investment_plan'] = plan
    receipt = {'step': obs['step'], 'expert': chosen, 'selection_objective': selection_mode, 'selected_expert_score': expert_scores[chosen] if expert_scores[chosen] > -1000000000.0 else None, 'expert_selection_scores': {e: v if v > -1000000000.0 else None for e, v in expert_scores.items()}, 'actual_cash': f['money'], 'actual_wheat': inventory_total(private, 'WHEAT'), 'existing': base_summary, 'remaining_cash': cash, 'land_cash': plan['land_cash'], 'rejected_types': dict(rejected), 'work': dict(workload), 'capacity': base_labor['capacity_by_day'], 'admitted': [{k: list(q[k]) if k == 'position' else q[k] for k in ('item', 'position', 'build_first', 'cash_reserved_model', 'feed_cash_model', 'feed_cost_model', 'hire_cash_model', 'net_cash_model', 'score', 'selection_score')} for q in accepted]}
    receipt.update(cash_funding_model='cash_prefix', funding_book=funding_book, initial_funding_book=initial_funding_book, credit_source_positions=credit_sources, funding_admissions=[{'item': q['item'], 'position': list(q['position']), 'status': q['funding_admission'], 'original_full_horizon_new_cash': q['original_full_horizon_new_cash'], 'trial_minimum': q['funding_trial']['minimum']} for q in accepted])
    st.setdefault('investment_receipts', []).append(receipt)
    st['investment_receipts'] = st['investment_receipts'][-720:]
    return plan

def economic_plan_prefix(obs, st):
    _r10_mode = PARAMS.get('r10_route_mode', 'future_failure_certificate')
    if _r10_mode == 'legacy':
        return _r10_integration_legacy_economic_plan_prefix(obs, st)
    if _r10_mode != 'future_failure_certificate':
        raise ValueError('unknown r10 route mode')
    selection_mode = PARAMS.get('investment_selection', 'terminal_net')
    if selection_mode not in ('terminal_net', 'labor_ratio'):
        raise ValueError('unknown investment selection objective')
    f, private, day = (obs['farms'][obs['player']], obs['private'], obs['day'])
    own = counts(f, private)
    model = dated_market_model(obs)
    _r10_context = _r10_integration_new_context(obs, model)
    credit_batches, credit_sources = credit_batches_from_field(obs, model)
    st['forecasts'] = dict(model['prices'][day])
    st['crop_scores'] = {}
    owned = [(x, y) for y, row in enumerate(f['tiles']) for x, t in enumerate(row) if t != 'LOCKED']
    ranked = sorted(owned, key=lambda p: (dist(p, home(p)), p[1], p[0]))
    free = [p for p in ranked if f['tiles'][p[1]][p[0]] is None or (isinstance(f['tiles'][p[1]][p[0]], dict) and f['tiles'][p[1]][p[0]].get('kind') == 'WEED')]
    structures = [p for p in ranked if isinstance(f['tiles'][p[1]][p[0]], dict) and f['tiles'][p[1]][p[0]].get('kind') in ('PASTURE', 'COOP') and ('animal' not in f['tiles'][p[1]][p[0]])]
    workload, feed = (Counter(), Counter())
    for seat, _, cal in model['calendars']:
        if seat == obs['player']:
            workload.update(cal['work'])
            feed.update(cal['feed'])
    builds, reserved, plant_permits = ({}, set(), {})
    committed_plant_sites = set()
    seeds = Counter(private['seeds'])
    committed_fixed, commitments = (0.0, [])
    in_transit = {a: inventory_total(private, a) for a in ANIMALS}
    unassigned_transit = Counter(in_transit)
    transit_calendars = []
    previous_builds = st.get('latest_investment_plan', {}).get('build_permits', {})
    for contract in st.get('contracts', {}).values():
        pos = tuple(contract['target'])
        if pos not in free:
            continue
        ops = [stage['op'] for stage in contract.get('stages', [])]
        plant = next((op[1] for op in ops if op[0] == 'PLANT'), None)
        building = next((op[0][6:] for op in ops if op[0].startswith('BUILD_')), None)
        if not plant and (not building):
            continue
        item = plant or previous_builds.get(pos, 'GOOSE' if building == 'COOP' else 'COW')
        reserved.add(pos)
        existing_animal = bool(building and unassigned_transit[item] > 0)
        if existing_animal:
            unassigned_transit[item] -= 1
        q = investment_quote(obs, item, pos, model, seed_credit=bool(plant and seeds[item]), already_owned=existing_animal, committed=True)
        if q:
            workload.update(q['calendar']['work'])
            _r10_integration_register_quote(_r10_context, q)
            feed.update(q['calendar']['feed'])
            committed_fixed += q['fixed_cash']
            commitments.append(q)
            if existing_animal:
                transit_calendars.append(q)
            apply_project_supply(obs, model, q['calendar'])
        if plant:
            plant_permits[pos] = plant
            committed_plant_sites.add(pos)
            seeds[plant] = max(0, seeds[plant] - 1)
        else:
            builds[pos] = item
    used_structures = set()
    for animal in ANIMALS:
        for _ in range(unassigned_transit[animal]):
            site = next((p for p in structures if p not in used_structures and f['tiles'][p[1]][p[0]]['kind'] == ANIMALS[animal][1]), None)
            if site is None:
                site = next((p for p in free if p not in reserved), None)
                if site is not None:
                    builds[site] = animal
            if site is None:
                continue
            reserved.add(site)
            used_structures.add(site)
            q = investment_quote(obs, animal, site, model, already_owned=True, committed=True)
            if q:
                workload.update(q['calendar']['work'])
                _r10_integration_register_quote(_r10_context, q)
                feed.update(q['calendar']['feed'])
                transit_calendars.append(q)
                apply_project_supply(obs, model, q['calendar'])
    n_animals = sum((own[a] for a in ANIMALS))
    buffer_units = max(3, n_animals // 2) if n_animals and day < 29 else 0
    feed_cash_requirements = Counter(feed)
    feed_cash_requirements[day] += buffer_units
    base_feed = feed_ledger(obs, model, feed_cash_requirements, inventory_total(private, 'WHEAT'))
    feed_order_needed = bool(n_animals and day < 29 and (inventory_total(private, 'WHEAT') < n_animals + max(3, n_animals // 2)))
    material_order_keys = {('feed', 'WHEAT')} if feed_order_needed else set()
    base_labor = labor_schedule(obs, workload, len(material_order_keys))
    base_reserved = committed_fixed + base_feed['cash'] + base_labor['total_cost']
    cash = max(0.0, float(f['money']) - base_reserved)
    base_summary = {'work': dict(workload), 'feed': dict(feed), 'in_transit': in_transit, 'transit_project_count': len(transit_calendars), 'contract_count': len(commitments), 'feed_cash': base_feed['cash'], 'feed_opportunity': base_feed['opportunity'], 'owned_feed_used': base_feed['owned_used'], 'hire_cash': base_labor['total_cost'], 'committed_fixed_cash': committed_fixed, 'reserved_cash': base_reserved}
    credit_ceiling = price_credit_batches(obs, model, credit_batches)
    funding_requirements = Counter(feed_cash_requirements)
    funding_fixed = committed_fixed
    funding_book = funding_cash_book(obs, model, funding_requirements, base_labor, funding_fixed, credit_batches, credit_ceiling)
    initial_funding_book = funding_book
    cash = funding_book['additional_current_spend']
    animal_orders, seed_orders, accepted, rejected = (Counter(), Counter(), [], Counter())
    expert_items = {'balanced': ('WHEAT', 'CARROT'), 'dairy': ('COW',), 'fiber': ('SHEEP',), 'horticulture': ('TOMATO', 'STRAWBERRY', 'MELON')}

    def budget_quote(item, pos):
        q = investment_quote(obs, item, pos, model, seeds.get(item, 0) > 0)
        if not q:
            return (None, 'startup_or_maturity')
        _r10_trial_book = None
        next_work = workload + Counter(q['calendar']['work'])
        next_keys = set(material_order_keys)
        if q['fixed_cash'] and (not q['build_first']):
            next_keys.add(('animal' if item in ANIMALS else 'seed', item))
        labor = labor_schedule(obs, next_work, len(next_keys))
        marginal_hires = max(0.0, labor['total_cost'] - base_labor['total_cost'])
        cash_feed = Counter(q['calendar']['feed'])
        if item in ANIMALS and (not n_animals):
            cash_feed[day] += 3
        next_ledger = feed_ledger(obs, model, cash_feed, base_feed['owned_remaining'])
        marginal_feed_cash = next_ledger['cash']
        marginal_opportunity = next_ledger['opportunity']
        net = q['gross_cash_model'] - q['fixed_cash'] - marginal_opportunity - marginal_hires
        cash_need = q['fixed_cash'] + marginal_feed_cash + marginal_hires
        q.update(net_cash_model=net, cash_reserved_model=cash_need, feed_cash_model=marginal_feed_cash, feed_cost_model=marginal_opportunity, hire_cash_model=marginal_hires, score=net / max(1, q['labor']), selection_score=net if selection_mode == 'terminal_net' else net / max(1, q['labor']), feed_ledger=next_ledger, material_order_keys=next_keys)
        if not labor['feasible']:
            if next_work.get(day, 0) > labor['capacity_by_day'][day] or net <= 0:
                return (q, 'labor')
            trial_model = funding_trial_model(obs, model, q['calendar'])
            trial_requirements = funding_requirements + cash_feed
            _r10_trial_book = funding_cash_book(obs, trial_model, trial_requirements, labor, funding_fixed + q['fixed_cash'], credit_batches, credit_ceiling)
            if not _r10_integration_try_route(_r10_context, q, workload, base_labor, next_work, labor, funding_requirements, funding_book, trial_requirements, _r10_trial_book):
                return (q, 'labor')
        if net <= 0:
            return (q, 'nonpositive_net')
        if _r10_trial_book is None:
            trial_model = funding_trial_model(obs, model, q['calendar'])
            trial_requirements = funding_requirements + cash_feed
            trial = funding_cash_book(obs, trial_model, trial_requirements, labor, funding_fixed + q['fixed_cash'], credit_batches, credit_ceiling)
        else:
            trial = _r10_trial_book
        admission = prefix_admission(funding_book, trial, cash_need)
        q.update(funding_trial=trial, funding_requirements=trial_requirements, funding_admission=admission, original_full_horizon_new_cash=cash_need)
        if admission is None:
            return (q, 'cash_prefix')
        return (q, None)
    offers, expert_scores = ([], {e: -1000000000.0 for e in expert_items})
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
                q['expert'] = expert
                offers.append(q)
                expert_scores[expert] = max(expert_scores[expert], q['selection_score'])
                if item in CROPS:
                    st['crop_scores'][item] = max(st['crop_scores'].get(item, -1000000000.0), q['score'])
    chosen = PARAMS['router']
    if chosen == 'adaptive':
        chosen = max(expert_scores, key=expert_scores.get)
    if chosen not in expert_items:
        chosen = 'balanced'
    st['expert'] = chosen
    st['metrics']['expert_' + chosen] += 1
    st['crop_choice'] = max(st['crop_scores'], key=st['crop_scores'].get) if st['crop_scores'] else None
    animal_admitted = False
    for q0 in sorted((q for q in offers if q['expert'] == chosen), key=lambda q: (-q['selection_score'], dist(q['position'], home(q['position'])), q['position'])):
        item, pos = (q0['item'], q0['position'])
        if pos in reserved or pos in plant_permits or (item in ANIMALS and animal_admitted):
            continue
        q, reason = budget_quote(item, pos)
        if reason:
            rejected[reason] += 1
            continue
        q['expert'] = chosen
        funding_book = q['funding_trial']
        funding_requirements = q['funding_requirements']
        funding_fixed += q['fixed_cash']
        cash = funding_book['additional_current_spend']
        workload.update(q['calendar']['work'])
        _r10_integration_register_quote(_r10_context, q)
        feed_cash_requirements.update(q['calendar']['feed'])
        material_order_keys = q['material_order_keys']
        base_labor = labor_schedule(obs, workload, len(material_order_keys))
        base_feed['owned_used'] += q['feed_ledger']['owned_used']
        base_feed['owned_remaining'] = q['feed_ledger']['owned_remaining']
        base_feed['cash'] += q['feed_ledger']['cash']
        base_feed['opportunity'] += q['feed_ledger']['opportunity']
        accepted.append(q)
        if item in ANIMALS:
            reserved.add(pos)
            animal_admitted = True
            if q['build_first']:
                builds[pos] = item
            else:
                animal_orders[item] += 1
        else:
            plant_permits[pos] = item
            if seeds[item] > 0:
                seeds[item] -= 1
            else:
                seed_orders[item] += 1
        apply_project_supply(obs, model, q['calendar'])
    occupied = sum((isinstance(t, dict) for row in f['tiles'] for t in row if t != 'LOCKED'))
    lands = len(f['unlocked_quadrants'])
    land_cost = (1000, 2000, 4000)[lands - 1] if 0 < lands < 3 else 0
    hire_orders = max(0, base_labor['hire_target_today'] - len(f['hands'])) if obs['hour'] < 8 else 0
    buy_land = bool(land_cost and 3 <= day < 19 and (occupied >= lands * 25 - 8) and (cash > land_cost + 600) and (hire_orders + len(material_order_keys) < 10))
    if buy_land:
        land_trial = funding_cash_book(obs, model, funding_requirements, base_labor, funding_fixed + land_cost, credit_batches, credit_ceiling)
        buy_land = land_trial['feasible']
        if buy_land:
            funding_book = land_trial
            funding_fixed += land_cost
            cash = funding_book['additional_current_spend']
    st['metrics']['investment_permit_quotes'] += len(accepted)
    st['metrics']['investment_budget_rejected_quotes'] += sum(rejected.values())
    plan = {'counts': own, 'animals': {a: own[a] + animal_orders[a] for a in ANIMALS}, 'melon_cap': 100, 'strawberry_cap': 100, 'crop_choice': st['crop_choice'], 'demand': model['demand'], 'build_permits': builds, 'reserved_animal_sites': reserved, 'plant_permits': plant_permits, 'committed_plant_sites': committed_plant_sites, 'animal_purchases': dict(animal_orders), 'seed_purchases': dict(seed_orders), 'buy_land': buy_land, 'land_cash': land_cost if buy_land else 0, 'material_order_slots': len(material_order_keys) + int(buy_land), 'hire_target_today': base_labor['hire_target_today'], 'planned_work': dict(workload), 'labor_plan': base_labor, 'existing_obligations': base_summary, 'remaining_investment_cash_model': cash, 'admitted_investments': accepted, 'expert_quote_scores': expert_scores, 'in_transit_existing': in_transit, 'owned_wheat_reserved': base_feed['owned_used'], 'rejected_types': dict(rejected)}
    plan.update(cash_funding_model='cash_prefix', funding_book=funding_book, initial_funding_book=initial_funding_book, credit_source_positions=credit_sources)
    st['latest_investment_plan'] = plan
    receipt = {'step': obs['step'], 'expert': chosen, 'selection_objective': selection_mode, 'selected_expert_score': expert_scores[chosen] if expert_scores[chosen] > -1000000000.0 else None, 'expert_selection_scores': {e: v if v > -1000000000.0 else None for e, v in expert_scores.items()}, 'actual_cash': f['money'], 'actual_wheat': inventory_total(private, 'WHEAT'), 'existing': base_summary, 'remaining_cash': cash, 'land_cash': plan['land_cash'], 'rejected_types': dict(rejected), 'work': dict(workload), 'capacity': base_labor['capacity_by_day'], 'admitted': [{k: list(q[k]) if k == 'position' else q[k] for k in ('item', 'position', 'build_first', 'cash_reserved_model', 'feed_cash_model', 'feed_cost_model', 'hire_cash_model', 'net_cash_model', 'score', 'selection_score')} for q in accepted]}
    receipt.update(cash_funding_model='cash_prefix', funding_book=funding_book, initial_funding_book=initial_funding_book, credit_source_positions=credit_sources, funding_admissions=[{'item': q['item'], 'position': list(q['position']), 'status': q['funding_admission'], 'original_full_horizon_new_cash': q['original_full_horizon_new_cash'], 'trial_minimum': q['funding_trial']['minimum']} for q in accepted])
    st.setdefault('investment_receipts', []).append(receipt)
    st['investment_receipts'] = st['investment_receipts'][-720:]
    _r10_integration_finish(_r10_context, plan, receipt)
    return plan

def clone_funding_model(model):
    return {**model, 'prices': {d: dict(v) for d, v in model['prices'].items()}, 'inventories': {d: dict(v) for d, v in model['inventories'].items()}}

def funding_trial_model(obs, model, cal):
    """与父apply_project_supply最终状态相同；每未来日只按累计冲击重价一次。"""
    trial = clone_funding_model(model)
    delta = Counter()
    for future_day in range(obs['day'] + 1, 30):
        delta.update(cal['goods'].get(future_day - 1, {}))
        delta['WHEAT'] -= cal['feed'].get(future_day - 1, 0)
        for product, quantity in delta.items():
            trial['inventories'][future_day][product] += quantity
        trial['prices'][future_day] = {p: price(p, trial['inventories'][future_day][p], obs['market'].get('params')) for p in PRODUCTS}
    return trial

def credit_batches_from_field(obs, model):
    """资格只取当前实际己方田块；不从后续新增项目/在途日历取得收入。"""
    batches = {}
    sources = []
    for seat, position, cal in model['calendars']:
        if seat != obs['player']:
            continue
        sources.append(list(position))
        for harvest_day, goods in cal['goods'].items():
            credit_day = int(harvest_day) + 1
            if credit_day <= obs['day'] or credit_day > 29:
                continue
            for product, quantity in goods.items():
                if product not in ('WHEAT', 'FERTILIZER') and quantity > 0:
                    key = (credit_day, product)
                    batches[key] = batches.get(key, 0) + quantity
    return (batches, sources)

def price_credit_batches(obs, model, batches, ceiling=None):
    """信用日库存已含前日供给；单一post-batch价乘批量，不再重复加量。"""
    amounts = {}
    for (d, product), quantity in batches.items():
        amount = quantity * price(product, model['inventories'][d][product], obs['market'].get('params'))
        if ceiling is not None:
            amount = min(amount, ceiling[d, product])
        amounts[d, product] = float(amount)
    return amounts

def current_feed_order_estimate(obs):
    """仅复述原市场的补麦数量和10%现金余量；不发动作，不借SELL。"""
    own = counts(obs['farms'][obs['player']], obs['private'])
    n_animals = sum((own[a] for a in ANIMALS))
    have = inventory_total(obs['private'], 'WHEAT')
    target = n_animals + max(3, n_animals // 2)
    quantity = min(16, max(0, target - have)) if n_animals and obs['day'] < 29 else 0
    supply = obs['market']['inventory']['WHEAT']
    nominal = sum((price('WHEAT', supply - k - 1, obs['market'].get('params')) for k in range(quantity)))
    return {'quantity': quantity, 'nominal_cash': nominal, 'cash_limit': nominal * 1.1}

def funding_feed_schedule(obs, model, requirements):
    """共享现金粮账：原补货若提前买入，余粮带到后日，避免同一粮重复购买。"""
    held = inventory_total(obs['private'], 'WHEAT')
    current_order = current_feed_order_estimate(obs)
    amounts, buys, ending_stock = ({}, {}, {})
    for d in range(obs['day'], 30):
        required = max(0, int(requirements.get(d, 0)))
        quantity = max(0, required - held)
        if d == obs['day']:
            quantity = max(quantity, current_order['quantity'])
        supply = model['inventories'][d]['WHEAT']
        nominal = sum((price('WHEAT', supply - k - 1, obs['market'].get('params')) for k in range(quantity)))
        cost = max(nominal, current_order['cash_limit']) if d == obs['day'] else nominal
        amounts[d] = float(cost)
        buys[d] = quantity
        held += quantity - required
        ending_stock[d] = held
    return {'cash_by_day': amounts, 'buys_by_day': buys, 'stock_by_day': ending_stock, 'total_cash': sum(amounts.values()), 'current_market_feed': current_order}

def cash_prefix_scan(cash, current_day, expenses, credits):
    """各日费用先付、再授信；原始负前缀保留，当前日信用强制为零。"""
    before, after = ({}, {})
    balance = float(cash)
    first_negative = None
    for d in range(current_day, 30):
        balance -= float(expenses.get(d, 0.0))
        before[d] = balance
        if balance < -1e-09 and first_negative is None:
            first_negative = d
        balance += float(credits.get(d, 0.0)) if d > current_day else 0.0
        after[d] = balance
    minimum = min(before.values(), default=float(cash))
    return {'before_credit': before, 'after_credit': after, 'minimum': minimum, 'first_negative_day': first_negative, 'feasible': first_negative is None, 'additional_current_spend': max(0.0, minimum)}

def funding_cash_book(obs, model, requirements, labor, fixed_cash, batches, ceiling):
    """资金估计独立于原R8净值账；仅对已经观察到的现金做每个时间前缀检查。"""
    feed_cash = funding_feed_schedule(obs, model, requirements)
    credit_amounts = price_credit_batches(obs, model, batches, ceiling)
    credits = Counter()
    for (d, _), amount in credit_amounts.items():
        credits[d] += amount
    expenses = {d: feed_cash['cash_by_day'][d] + labor['cash_by_day'].get(d, 0.0) for d in range(obs['day'], 30)}
    expenses[obs['day']] += fixed_cash
    scan = cash_prefix_scan(obs['farms'][obs['player']]['money'], obs['day'], expenses, credits)
    return {**scan, 'expenses_by_day': expenses, 'credits_by_day': dict(credits), 'feed_cash_by_day': feed_cash['cash_by_day'], 'feed_buys_by_day': feed_cash['buys_by_day'], 'feed_ending_stock_by_day': feed_cash['stock_by_day'], 'hire_cash_by_day': dict(labor['cash_by_day']), 'fixed_cash_today': fixed_cash, 'full_horizon_cash_outflow': sum(expenses.values()), 'current_market_feed': feed_cash['current_market_feed'], 'credit_batches': [{'credit_day': d, 'product': p, 'quantity': batches[d, p], 'cash_model': amount} for (d, p), amount in sorted(credit_amounts.items())]}

def prefix_admission(baseline, trial, original_new_cash):
    if trial['feasible']:
        return 'PREFIX_FEASIBLE'
    if not baseline['feasible'] and original_new_cash == 0 and all((trial['before_credit'][d] + 1e-09 >= v for d, v in baseline['before_credit'].items())) and all((trial['after_credit'][d] + 1e-09 >= v for d, v in baseline['after_credit'].items())):
        return 'EXISTING_SHORTFALL_ZERO_NEW_CASH_REUSE'
    return None

def economic_plan(obs, st):
    mode = PARAMS.get('cash_funding', 'cash_prefix')
    if mode == 'full_reserve':
        return economic_plan_full_reserve(obs, st)
    if mode == 'cash_prefix':
        return economic_plan_prefix(obs, st)
    raise ValueError('unknown cash funding model')

def record_investment_intents(st, orders, actions):
    receipt = st['investment_receipts'][-1]
    receipt['market_intents'] = [list(o) for o in orders[:10]]
    receipt['unit_investment_intents'] = [{'unit': i, 'action': list(a)} for i, a in enumerate(actions) if a and (a[0] in ('PLANT', 'PLACE') or a[0].startswith('BUILD_'))]

def matching(weights):
    """矩形最大权匹配；虚拟列表示本步不分派，避免逐工人抢走局部最优。"""
    n = len(weights)
    if not n:
        return {}
    width = len(weights[0])
    m = width + n
    u, v, p, way = ([0.0] * (n + 1), [0.0] * (m + 1), [0] * (m + 1), [0] * (m + 1))
    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minimum, used = ([float('inf')] * (m + 1), [False] * (m + 1))
        while True:
            used[j0] = True
            i0, delta, j1 = (p[j0], float('inf'), 0)
            for j in range(1, m + 1):
                if used[j]:
                    continue
                w = weights[i0 - 1][j - 1] if j <= width else 0.0
                current = -w - u[i0] - v[j]
                if current < minimum[j]:
                    minimum[j], way[j] = (current, j0)
                if minimum[j] < delta:
                    delta, j1 = (minimum[j], j)
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
    return {p[j] - 1: j - 1 for j in range(1, width + 1) if p[j] and weights[p[j] - 1][j - 1] > 0}

def make_tasks(obs, st, plan):
    farm = obs['farms'][obs['player']]
    private, day, hour = (obs['private'], obs['day'], obs['hour'])
    values = st['forecasts']
    tasks = []
    owned = [(x, y) for y, row in enumerate(farm['tiles']) for x, t in enumerate(row) if t != 'LOCKED']
    ranked = sorted(owned, key=lambda p: (dist(p, home(p)), p[1], p[0]))
    animal_total = sum((plan['counts'][a] for a in ANIMALS))
    reserve = set(plan['reserved_animal_sites'])
    in_transit = Counter({a: inventory_total(private, a) for a in ANIMALS})
    empty_structure = Counter()
    for x, y in owned:
        t = farm['tiles'][y][x]
        if isinstance(t, dict) and t.get('kind') in ('PASTURE', 'COOP') and ('animal' not in t):
            empty_structure[t['kind']] += 1

    def add(pos, kind, ops, value, deadline=23, requirement=None):
        if ops and value > 0:
            tasks.append({'pos': pos, 'kind': kind, 'ops': ops, 'value': value, 'deadline': deadline, 'requirement': requirement or {}})
    for x, y in owned:
        tile, pos = (farm['tiles'][y][x], (x, y))
        if isinstance(tile, dict) and 'animal' in tile:
            a = tile['animal']
            spec = ANIMALS[a]
            feed = not tile['fed_today'] and day < 29
            care = not tile['cared_today'] and day < 28
            fertil = tile['fertilizer_available']
            ready = tile.get('yield_units', 0)
            ops, value = ([], 0.0)
            if feed:
                ops.append(['FEED'])
                survival = 450 if tile.get('consecutive_unfed', 0) else 0
                value += survival + max(40, values[spec[5]] * 0.65) + values['FERTILIZER']
            if care:
                ops.append(['CARE'])
                value += values[spec[5]] * PARAMS['care_weight']
            if fertil:
                ops.append(['COLLECT_FERTILIZER'])
                value += max(15, values['FERTILIZER'])
            if ready:
                ops.append(['HARVEST'])
                value += ready * values[spec[5]]
            add(pos, 'animal', ops, value, requirement={'WHEAT': 1} if feed else {})
            continue
        if isinstance(tile, dict) and tile.get('kind') in ('PASTURE', 'COOP'):
            for a in ('COW', 'SHEEP', 'GOOSE'):
                if in_transit[a] and ANIMALS[a][1] == tile['kind']:
                    in_transit[a] -= 1
                    add(pos, 'place_animal', [['PLACE', a]], 650.0, requirement={a: 1})
                    break
            continue
        if isinstance(tile, dict) and tile.get('kind') == 'PLANT':
            c = tile['crop']
            seed, first, maxday, interval, limit = CROPS[c]
            age = day - tile['planted_day']
            water, yield_now = (not tile['watered_today'], tile.get('yield_units', 0))
            danger = tile.get('consecutive_unwatered', 0) >= 1 or age == 0
            fertilized = tile.get('fertilized_until_day', -1) >= day
            mature = age >= first
            ops, value, req = ([], 0.0, {})
            if interval:
                next_production = day + 1 >= tile['planted_day'] + first and (day + 1 - tile['planted_day'] - first) % interval == 0
                within_life = age < first + interval * (limit - 1)
                need_water = water and (danger or next_production) and within_life
                need_fert = next_production and within_life and (not fertilized) and (values[c] > values['FERTILIZER'] * 0.55) and (day < 29)
                if need_fert and inventory_total(private, 'FERTILIZER') > 0:
                    ops.append(['FERTILIZE'])
                    req['FERTILIZER'] = 1
                    value += values[c]
                if need_water:
                    ops.append(['WATER'])
                    value += values[c] * (2.0 if danger else 0.8)
                if yield_now and mature:
                    ops.append(['HARVEST'])
                    value += values[c] * yield_now
                if not ops and age >= first + interval * (limit - 1) + 1 and (not yield_now):
                    add(pos, 'clear', [['DIG']], 35 if day < 27 else 0)
            else:
                growth = (maxday + 1) // 2 <= age <= maxday
                need_water = water and (danger or growth) and (age <= maxday)
                use_fert = c == 'MELON' and growth and (age <= maxday - 1) and (not fertilized) and (values[c] > values['FERTILIZER']) and (inventory_total(private, 'FERTILIZER') > 0)
                if use_fert:
                    ops.append(['FERTILIZE'])
                    req['FERTILIZER'] = 1
                    value += values[c] * 1.3
                if need_water:
                    ops.append(['WATER'])
                    value += values[c] * (2.5 if danger else 1.0)
                after_water = yield_now + ((2 if fertilized or use_fert else 1) if need_water and growth else 0)
                harvest = yield_now > 0 and mature and (age >= maxday or after_water >= limit or day == 29)
                if harvest:
                    ops.append(['HARVEST'])
                    value += values[c] * after_water
            deadline = 21 if danger else 22 if tile.get('max_lifespan_step', -1) == day * 24 + 24 else 23
            if day == 29:
                deadline = max(0, 20 - dist(pos, home(pos)))
                if not yield_now:
                    continue
            add(pos, 'crop', ops, value, deadline, req)
            continue
        if pos in plan['build_permits']:
            a = plan['build_permits'][pos]
            ops = [['DIG']] if tile is not None else []
            ops.append(['BUILD_' + ANIMALS[a][1]])
            add(pos, 'build', ops, 550.0, 20)
            continue
        if pos not in plan['committed_plant_sites'] and (pos in reserve or day >= 28 or hour >= 21):
            continue
        choice = plan['plant_permits'].get(pos)
        if choice and private['seeds'].get(choice, 0) > 0:
            ops = [['DIG']] if tile is not None else []
            ops += [['PLANT', choice], ['WATER']]
            value = max(15, st['crop_scores'].get(choice, 0)) * 4
            add(pos, 'plant', ops, value, 21)
    return tasks

def _identity(tile):
    if not isinstance(tile, dict):
        return (tile,)
    return tuple((tile.get(k) for k in ('kind', 'crop', 'planted_day', 'animal', 'placed_day')))

def _stage_value(op, tile, task, st):
    name = op[0]
    values = st['forecasts']
    if isinstance(tile, dict) and tile.get('animal'):
        product = ANIMALS[tile['animal']][5]
        if name == 'FEED':
            return (450 if tile.get('consecutive_unfed', 0) else 0) + max(40, values[product] * 0.65) + values['FERTILIZER']
        if name == 'CARE':
            return values[product] * PARAMS['care_weight']
    else:
        product = tile.get('crop') if isinstance(tile, dict) else None
    if name == 'HARVEST':
        return max(1, tile.get('yield_units', 0)) * values[product]
    if name == 'COLLECT_FERTILIZER':
        return max(15, values['FERTILIZER'])
    if name == 'FERTILIZE':
        return values[product] * (1.3 if product == 'MELON' else 1)
    if name == 'WATER' and product:
        danger = tile.get('consecutive_unwatered', 0) >= 1 or tile.get('planted_day') == st['contract_day']
        return values[product] * ((2 if CROPS[product][3] else 2.5) if danger else 0.8 if CROPS[product][3] else 1)
    return task['value'] / max(1, len(task['ops']))

def compile_contracts(obs, st, tasks):
    """市场沿用原始任务；仅在执行器内部将每个目标编译为有类型的阶段。"""
    day = obs['day']
    farm = obs['farms'][obs['player']]
    st['contract_day'] = day
    groups = []
    for task in tasks:
        pos = tuple(task['pos'])
        tile = farm['tiles'][pos[1]][pos[0]]
        stages = []
        for op in task['ops']:
            name = op[0]
            requirement = {'WHEAT': 1} if name == 'FEED' else {'FERTILIZER': 1} if name == 'FERTILIZE' else {op[1]: 1} if name == 'PLACE' and op[1] in ANIMALS else {}
            necessary = name in ('WATER', 'FEED')
            primitive = name in ('WATER', 'FEED', 'CARE', 'FERTILIZE', 'HARVEST', 'COLLECT_FERTILIZER')
            deadline = day * 24 + (23 if primitive and day < 29 else task['deadline'])
            if name == 'HARVEST' and isinstance(tile, dict) and (tile.get('max_lifespan_step', -1) >= 0):
                deadline = min(deadline, max(obs['step'], tile['max_lifespan_step']))
            stages.append({'op': list(op), 'requirement': requirement, 'deadline': deadline, 'necessary': necessary, 'value': _stage_value(op, tile, task, st)})
        groups.append({'target': pos, 'kind': task['kind'], 'fingerprint': _identity(tile), 'stages': stages, 'source_value': task['value']})
    return groups

def _route(obs, unit, target, stage, available):
    f, private = (obs['farms'][obs['player']], obs['private'])
    positions = [tuple(f['farmer'])] + [tuple(p) for p in f['hands']]
    if unit >= len(positions):
        return None
    pos, inv = (positions[unit], private['inventories'][unit])
    missing = next((p for p, n in stage['requirement'].items() if inv.get(p, 0) < n), None)
    if missing:
        n = stage['requirement'][missing] - inv.get(missing, 0)
        if available.get(missing, 0) < n:
            return None
        depot = min(ACCESS, key=lambda p: (dist(pos, p) + dist(p, target), p))
        action = ['PICKUP', missing, n] if pos == depot else move(pos, depot)
        return {'action': action, 'cost': dist(pos, depot) + 1 + dist(depot, target) + 1, 'reservation': {missing: n}, 'phase': 'resupplying'}
    return {'action': list(stage['op']) if pos == target else move(pos, target), 'cost': dist(pos, target) + 1, 'reservation': {}, 'phase': 'ready' if pos == target else 'travelling'}

def _fit(obs, unit, target, stages, available):
    if not stages:
        return None
    route = _route(obs, unit, target, stages[0], available)
    if route is None:
        return None
    step = obs['step']
    inventory = dict(obs['private']['inventories'][unit])
    seed_inventory = dict(obs['private']['seeds'])
    for p, n in route['reservation'].items():
        inventory[p] = inventory.get(p, 0) + n
    elapsed, accepted = (route['cost'], [])
    for stage in stages:
        if accepted:
            elapsed += 1
        if step + elapsed - 1 > stage['deadline']:
            break
        if any((inventory.get(p, 0) < n for p, n in stage['requirement'].items())):
            break
        if stage['op'][0] == 'PLANT':
            crop = stage['op'][1]
            if seed_inventory.get(crop, 0) < 1:
                break
            seed_inventory[crop] -= 1
        if obs['day'] == 29 and obs['hour'] + elapsed + dist(target, home(target)) + 2 > 22:
            break
        accepted.append(stage)
        for p, n in stage['requirement'].items():
            inventory[p] -= n
    if not accepted:
        return None
    necessary = [(i, s) for i, s in enumerate(accepted) if s['necessary']]
    slack = min((s['deadline'] - (step + route['cost'] + i - 1) for i, s in necessary), default=None)
    return {'stages': accepted, 'route': route, 'cost': route['cost'] + len(accepted) - 1, 'urgent': slack is not None and slack <= 0, 'slack': slack}

def propose_contract(obs, unit, group, available):
    stages = group['stages']
    by_op = {s['op'][0]: s for s in stages}
    kind, target = (group['kind'], group['target'])
    if kind == 'crop':
        water, fert, harvest = (by_op.get('WATER'), by_op.get('FERTILIZE'), by_op.get('HARVEST'))
        if water:
            ordered = [water] + ([harvest] if harvest else [])
            if fert and obs['private']['inventories'][unit].get('FERTILIZER', 0):
                enriched = _fit(obs, unit, target, [fert, water], available)
                if enriched and len(enriched['stages']) == 2:
                    ordered = [fert] + ordered
        elif harvest:
            tile = obs['farms'][obs['player']]['tiles'][target[1]][target[0]]
            ordered = [harvest] + ([fert] if fert and CROPS[tile['crop']][3] else [])
        else:
            ordered = stages
    elif kind == 'animal':
        feed, care = (by_op.get('FEED'), by_op.get('CARE'))
        harvest, collect = (by_op.get('HARVEST'), by_op.get('COLLECT_FERTILIZER'))
        feed_possible = feed and _fit(obs, unit, target, [feed], available)
        ordered = ([feed] if feed_possible else []) + ([harvest] if harvest else [])
        if care and (feed_possible or not feed):
            ordered.append(care)
        if collect:
            ordered.append(collect)
    else:
        ordered = stages
    fitted = _fit(obs, unit, target, ordered, available)
    if not fitted:
        return None
    if kind in ('build', 'plant') and len(fitted['stages']) != len(ordered):
        return None
    if fitted['stages'][0]['op'][0] == 'FERTILIZE' and 'WATER' in by_op and (not any((s['op'][0] == 'WATER' for s in fitted['stages']))):
        fitted = _fit(obs, unit, target, [by_op['WATER']], available)
        if not fitted:
            return None
    return {**fitted, 'target': target, 'kind': kind, 'fingerprint': group['fingerprint']}

def _receipt_observation(obs, unit, target):
    f = obs['farms'][obs['player']]
    positions = [tuple(f['farmer'])] + [tuple(p) for p in f['hands']]
    t = f['tiles'][target[1]][target[0]]
    return {'step': obs['step'], 'day': obs['day'], 'position': positions[unit] if unit < len(positions) else None, 'inventory': dict(obs['private']['inventories'][unit]) if unit < len(positions) else {}, 'tile': dict(t) if isinstance(t, dict) else t}

def _receipt_result(receipt, now):
    before, action = (receipt['before'], receipt['action'])
    if now['step'] != before['step'] + 1:
        return 'unknown'
    bt, nt, op = (before['tile'], now['tile'], action[0])
    same = _identity(bt) == _identity(nt)
    cross_day = now['day'] != before['day']
    if op in ('WATER', 'FEED'):
        if not same or not isinstance(nt, dict):
            return 'failed'
        flag, counter = ('watered_today', 'consecutive_unwatered') if op == 'WATER' else ('fed_today', 'consecutive_unfed')
        eligible = not bt.get(flag) and (op != 'FEED' or before['inventory'].get('WHEAT', 0) >= 1)
        return 'confirmed' if eligible and (nt.get(counter) == 0 if cross_day else nt.get(flag)) else 'failed'
    if cross_day:
        return 'unknown'
    inv, oldinv = (now['inventory'], before['inventory'])
    if op in ('NORTH', 'SOUTH', 'EAST', 'WEST'):
        dx, dy = {'NORTH': (0, -1), 'SOUTH': (0, 1), 'EAST': (1, 0), 'WEST': (-1, 0)}[op]
        pos = before['position']
        success = now['position'] == (pos[0] + dx, pos[1] + dy)
    elif op == 'PICKUP':
        success = inv.get(action[1], 0) - oldinv.get(action[1], 0) >= action[2]
    elif op == 'CARE':
        success = same and isinstance(nt, dict) and nt.get('cared_today') and (not bt.get('cared_today'))
    elif op == 'FERTILIZE':
        success = same and isinstance(nt, dict) and (nt.get('fertilized_until_day', -1) >= before['day'] + 2) and (oldinv.get('FERTILIZER', 0) - inv.get('FERTILIZER', 0) == 1)
    elif op == 'HARVEST':
        product = bt.get('crop') or ANIMALS[bt['animal']][5]
        success = bt.get('yield_units', 0) > 0 and inv.get(product, 0) - oldinv.get(product, 0) == bt['yield_units']
    elif op == 'COLLECT_FERTILIZER':
        success = same and isinstance(nt, dict) and bt.get('fertilizer_available') and (not nt.get('fertilizer_available')) and (inv.get('FERTILIZER', 0) - oldinv.get('FERTILIZER', 0) == 1)
    elif op == 'DIG':
        success = bt is not None and nt is None
    elif op.startswith('BUILD_'):
        success = bt is None and isinstance(nt, dict) and (nt.get('kind') == op[6:])
    elif op == 'PLANT':
        success = bt is None and isinstance(nt, dict) and (nt.get('crop') == action[1]) and (nt.get('planted_day') == before['day'])
    elif op == 'PLACE' and action[1] in ANIMALS:
        success = isinstance(nt, dict) and nt.get('animal') == action[1] and (oldinv.get(action[1], 0) - inv.get(action[1], 0) == 1)
    else:
        return 'unknown'
    return 'confirmed' if success else 'failed'

def confirm_execution(st, obs):
    contracts = st.setdefault('contracts', {})
    events = st.setdefault('contract_events', [])
    for unit, contract in list(contracts.items()):
        receipt = contract.get('receipt')
        now = _receipt_observation(obs, unit, contract['target'])
        if receipt:
            outcome = _receipt_result(receipt, now)
            op = receipt['action'][0]
            st['metrics']['receipt_' + outcome] += 1
            events.append({'step': obs['step'], 'unit': unit, 'target': contract['target'], 'action': receipt['action'], 'outcome': outcome})
            if outcome != 'confirmed':
                del contracts[unit]
                continue
            if op not in ('NORTH', 'SOUTH', 'EAST', 'WEST', 'PICKUP'):
                if receipt['action'] == contract['stages'][0]['op']:
                    contract['stages'].pop(0)
                    st['metrics']['confirmed_' + op] += 1
                if op == 'HARVEST' and isinstance(receipt['before']['tile'], dict) and (receipt['before']['tile'].get('kind') == 'PLANT') and (not CROPS[receipt['before']['tile']['crop']][3]):
                    st['metrics']['terminal_harvest_stages_pruned'] += len(contract['stages'])
                    contract['stages'] = []
                contract['fingerprint'] = _identity(now['tile'])
            contract['receipt'] = None
            contract['phase'] = 'ready'
        if not contract['stages']:
            st['metrics']['contract_completed'] += 1
            del contracts[unit]
        elif now['day'] != contract['day'] or now['position'] is None or obs['step'] > contract['expires']:
            st['metrics']['contract_expired'] += 1
            del contracts[unit]
        elif _identity(now['tile']) != contract['fingerprint']:
            st['metrics']['contract_target_changed'] += 1
            del contracts[unit]
    if len(events) > 4096:
        del events[:-4096]

def shared_task_urgency(obs, units, groups, available):
    """目标共用最快可行工人的必要阶段余量；路远不会获得额外紧迫奖励。"""
    result = {}
    for group in groups:
        slacks = []
        for unit in units:
            offer = propose_contract(obs, unit, group, available)
            if offer and offer['slack'] is not None:
                slacks.append(offer['slack'])
        result[group['target']] = bool(slacks) and max(slacks) <= 0
    return result

def allocate(obs, st, plan, tasks):
    farm, private = (obs['farms'][obs['player']], obs['private'])
    positions = [tuple(farm['farmer'])] + [tuple(p) for p in farm['hands']]
    actions = [['PASS'] for _ in positions]
    available = dict(private['shed'])
    capacity = 100 - sum(available.values())
    seeds = dict(private['seeds'])
    groups = compile_contracts(obs, st, tasks)
    contracts = st.setdefault('contracts', {})
    occupied, assigned = (set(), set())
    day, hour = (obs['day'], obs['hour'])
    animal_count = sum((plan['counts'][a] for a in ANIMALS))

    def cancel(unit, why):
        if unit in contracts:
            del contracts[unit]
            st['metrics']['contract_' + why] += 1

    def accept(unit, offer, existing=False):
        nonlocal capacity
        route = _route(obs, unit, offer['target'], offer['stages'][0], available)
        if route is None:
            return False
        action = route['action']
        seed_demand = Counter((s['op'][1] for s in offer['stages'] if s['op'][0] == 'PLANT'))
        for crop, n in seed_demand.items():
            if seeds.get(crop, 0) < n:
                return False
        for crop, n in seed_demand.items():
            seeds[crop] -= n
        for p, n in route['reservation'].items():
            available[p] -= n
        if not existing:
            contract = {'owner': unit, 'target': offer['target'], 'kind': offer['kind'], 'fingerprint': offer['fingerprint'], 'stages': [dict(s) for s in offer['stages']], 'day': day, 'accepted_step': obs['step'], 'expires': obs['step'] + offer['cost']}
            contracts[unit] = contract
            st['metrics']['contract_accepted'] += 1
        else:
            contract = contracts[unit]
        contract['phase'] = 'awaiting_receipt'
        contract['route_phase'] = route['phase']
        contract['receipt'] = {'action': list(action), 'before': _receipt_observation(obs, unit, offer['target'])}
        actions[unit] = action
        assigned.add(unit)
        occupied.add(offer['target'])
        st['metrics']['dispatched_' + action[0]] += 1
        return True
    for unit, pos in enumerate(positions):
        inv = private['inventories'][unit]
        final_return = day == 29 and (hour + dist(pos, home(pos)) >= 19 or hour >= 20)
        if final_return and any((inv.get(p, 0) for p in PRODUCTS)):
            cancel(unit, 'terminal_return')
            if pos not in ACCESS:
                actions[unit] = move(pos, home(pos))
            elif capacity > 0:
                item = max((p for p in PRODUCTS if inv.get(p, 0)), key=lambda p: inv[p] * st['forecasts'][p])
                n = min(inv[item], capacity)
                actions[unit] = ['PLACE', item, n]
                capacity -= n
            assigned.add(unit)
    potential_units = [u for u in range(len(positions)) if u not in assigned]
    urgency = shared_task_urgency(obs, potential_units, groups, available)
    covered = set()
    for unit, contract in contracts.items():
        if unit in assigned:
            continue
        fit = _fit(obs, unit, contract['target'], contract['stages'], available)
        if fit and len(fit['stages']) == len(contract['stages']) and (not (urgency.get(contract['target'], False) and fit['slack'] is None)):
            covered.add(contract['target'])
    for unit, contract in sorted(list(contracts.items())):
        if unit in assigned:
            continue
        fitted = _fit(obs, unit, contract['target'], contract['stages'], available)
        if fitted is None or len(fitted['stages']) != len(contract['stages']):
            cancel(unit, 'infeasible')
            continue
        if urgency.get(contract['target'], False) and fitted['slack'] is None:
            cancel(unit, 'urgent_goal_not_covered')
            continue
        other_urgent = any((g['target'] != contract['target'] and g['target'] not in covered and urgency.get(g['target'], False) and (o := propose_contract(obs, unit, g, available)) and (o['slack'] is not None) for g in groups))
        if other_urgent and (not urgency.get(contract['target'], False)):
            cancel(unit, 'urgent_preempted')
            continue
        if contract['target'] in occupied or not accept(unit, {**fitted, **contract}, existing=True):
            cancel(unit, 'resource_unavailable')
    actors = [u for u in range(len(positions)) if u not in assigned]
    free_groups = [g for g in groups if g['target'] not in occupied]
    offers, weights = ({}, [])
    urgency = shared_task_urgency(obs, actors, free_groups, available)
    urgent_bonus = 1 + 1.15 * sum((max(0, s['value']) for g in free_groups for s in g['stages']))
    for u in actors:
        row = []
        for j, group in enumerate(free_groups):
            offer = propose_contract(obs, u, group, available)
            if offer:
                weight = sum((s['value'] for s in offer['stages'])) / max(1, offer['cost'])
                if positions[u] == group['target']:
                    weight *= 1.15
                row.append(weight + (urgent_bonus if urgency.get(group['target'], False) and offer['slack'] is not None else 0))
                offers[u, j] = offer
            else:
                row.append(-1000000.0)
        weights.append(row)
    for i, j in matching(weights).items() if free_groups else []:
        u = actors[i]
        offer = propose_contract(obs, u, free_groups[j], available)
        if offer and offer['target'] not in occupied:
            accept(u, offer)
    for u, pos in enumerate(positions):
        if u in assigned:
            continue
        inv = private['inventories'][u]
        cargo = {p: n for p, n in inv.items() if p in PRODUCTS and n > 0 and (p not in ('WHEAT', 'FERTILIZER') or n > (4 if p == 'WHEAT' and animal_count else 2))}
        carry_value = sum((n * st['forecasts'].get(p, 0) for p, n in cargo.items()))
        if pos in ACCESS and cargo and (capacity > 0):
            item = max(cargo, key=lambda p: cargo[p] * st['forecasts'].get(p, 0))
            keep = 4 if item == 'WHEAT' and animal_count and (day < 29) else 2 if item == 'FERTILIZER' and day < 28 else 0
            n = min(inv[item] - keep, capacity)
            if n > 0:
                actions[u] = ['PLACE', item, n]
                capacity -= n
        elif carry_value > 1800 and dist(pos, home(pos)) <= 3 and (hour < 19):
            actions[u] = move(pos, home(pos))
    if day < 29:
        for u, action in enumerate(actions):
            if action[0] != 'PICKUP' or action[1] != 'WHEAT':
                continue
            extra = min(max(0, 4 - action[2]), max(0, available.get('WHEAT', 0)))
            if extra:
                action[2] += extra
                available['WHEAT'] -= extra
                if u in contracts and contracts[u].get('receipt'):
                    contracts[u]['receipt']['action'] = list(action)
                st['metrics']['batch_feed_extra_requested'] += extra
    st['metrics']['unit_commands'] += len(actions)
    st['metrics']['pass'] += sum((a[0] == 'PASS' for a in actions))
    return actions

def market_orders(obs, st, plan, tasks, actions):
    farm, private = (obs['farms'][obs['player']], obs['private'])
    shed = dict(private['shed'])
    for u, action in enumerate(actions):
        inv = private['inventories'][u]
        if action[0] == 'PICKUP':
            shed[action[1]] = max(0, shed.get(action[1], 0) - action[2])
        elif action[0] == 'PLACE' and action[1] in PRODUCTS:
            shed[action[1]] = shed.get(action[1], 0) + min(action[2], inv.get(action[1], 0))
    cash = float(farm['money'])
    day, hour = (obs['day'], obs['hour'])
    own = plan['counts']
    n_animals = sum((own[a] for a in ANIMALS))
    orders = []
    feed_remaining = sum((isinstance(t, dict) and 'animal' in t and (not t['fed_today']) for row in farm['tiles'] for t in row))
    wheat_reserve = max(0, feed_remaining + n_animals // 2 - sum((i.get('WHEAT', 0) for i in private['inventories']))) if day < 29 else 0
    wheat_reserve = max(wheat_reserve, max(0, plan['owned_wheat_reserved'] - sum((i.get('WHEAT', 0) for i in private['inventories']))))
    fertil_reserve = min(12, sum((t['requirement'].get('FERTILIZER', 0) for t in tasks)) + 2) if day < 28 else 0
    for p in sorted(PRODUCTS, key=lambda p: shed.get(p, 0) * obs['market']['prices'].get(p, 0), reverse=True):
        keep = wheat_reserve if p == 'WHEAT' else fertil_reserve if p == 'FERTILIZER' else 0
        n = max(0, shed.get(p, 0) - keep)
        if n:
            orders.append(['SELL', p, n])
            shed[p] -= n
    if day == 29 and hour >= 18:
        record_investment_intents(st, orders, actions)
        return orders[:10]

    def fixed_order(order, cost):
        nonlocal cash
        if cost <= cash and len(orders) < 10:
            orders.append(order)
            cash -= cost
            return True
        return False
    sales, orders = (orders, [])
    desired_hands = int(plan['hire_target_today'])
    if hour < 8:
        for hire in range(len(farm['hands']), desired_hands):
            ordinal = int(farm.get('hires_today', len(farm['hands']))) + hire - len(farm['hands'])
            if not fixed_order(['HIRE'], FIB[min(ordinal, len(FIB) - 1)]):
                break
    sale_slots = max(0, 10 - len(orders) - plan['material_order_slots'])
    orders.extend(sales[:sale_slots])
    for sale in sales[sale_slots:]:
        shed[sale[1]] = shed.get(sale[1], 0) + sale[2]
    wheat_have = inventory_total(private, 'WHEAT')
    feed_target = n_animals + max(3, n_animals // 2)
    if day < 29 and n_animals and (wheat_have < feed_target):
        n = min(16, feed_target - wheat_have)
        supply = obs['market']['inventory']['WHEAT']
        estimate = sum((price('WHEAT', supply - k - 1, obs['market'].get('params')) for k in range(n)))
        if estimate * 1.1 <= cash and sum(shed.values()) + n <= 100:
            fixed_order(['BUY_PRODUCT', 'WHEAT', n], estimate * 1.1)
            shed['WHEAT'] = shed.get('WHEAT', 0) + n
    for animal, quantity in plan['animal_purchases'].items():
        n = min(100, max(0, int(quantity)))
        if n and day < 29 and (sum(shed.values()) + n <= 100):
            if fixed_order(['BUY_ANIMAL', animal, n], ANIMALS[animal][0] * n):
                shed[animal] = shed.get(animal, 0) + n
    for crop, quantity in plan['seed_purchases'].items():
        n = min(100, max(0, int(quantity)))
        if n:
            fixed_order(['BUY_SEED', crop, n], CROPS[crop][0] * n)
    if plan['buy_land']:
        fixed_order(['BUY_LAND'], plan['land_cash'])
    record_investment_intents(st, orders, actions)
    return orders[:10]

def diagnostics():
    return {str(seat): {'metrics': dict(st['metrics']), 'daily': st['daily'], 'purchase_misses': st['procurement'], 'active_contracts': st.get('contracts', {}), 'contract_events': st.get('contract_events', []), 'investment_receipts': st.get('investment_receipts', [])} for seat, st in _STATES.items()}

def agent(observation, configuration=None):
    seat, step = (int(observation['player']), int(observation['step']))
    st = _STATES.get(seat)
    if st is None or step <= st['last_step']:
        st = new_state(observation)
        _STATES[seat] = st
    confirm_execution(st, observation)
    confirm_orders(st, observation)
    plan = economic_plan(observation, st)
    tasks = make_tasks(observation, st, plan)
    actions = allocate(observation, st, plan, tasks)
    orders = market_orders(observation, st, plan, tasks, actions)
    if observation['day'] != st['last_day']:
        st['daily'].append({**summary(observation), 'expert': st['expert'], 'crop_choice': st['crop_choice'], 'tasks': len(tasks), 'metrics': dict(st['metrics'])})
    st.update(last_step=step, last_day=observation['day'], previous=summary(observation), issued=orders, unit_actions=actions)
    return {'farmer': actions[0], 'hands': actions[1:], 'market': orders}
