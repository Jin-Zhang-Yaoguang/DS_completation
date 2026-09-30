# Static module: calendar_compiler
"""R10 B future service compiler. Frozen R9 economic calendar lineage; no candidate imports.

Only adds service/state diagnostics at original calendar accumulation points.
The legacy goods/work/feed values are preserved. Future state is conditional on
legacy timely care and delivery, never an observation or execution receipt.
"""
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

# Static module: scheduler
"""未来日完整服务的确定性构造器。结果须经独立checker，非最优性证明。"""
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

# Static module: checker
"""未来整日服务证书的独立重演检查；不导入调度器、编译器、候选或引擎。

动作规则依据冻结官方 kaggriculture.py（bc8a54879ef0…）。现金与未来
日初状态是外部条件；本检查只证明给定条件下的动作、物量与交付。
"""
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

# Static module: route_admission
"""R10 B 独立未来日劳动准入；不导入或调用候选，不改变原资金与评分。"""
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
