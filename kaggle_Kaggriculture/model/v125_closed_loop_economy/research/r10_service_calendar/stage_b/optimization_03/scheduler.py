"""未来日完整服务的确定性构造器。结果须经独立checker，非最优性证明。"""
import hashlib
import json
from collections import Counter, defaultdict

ACCESS = ((4, 4), (5, 4), (4, 5), (5, 5))
PRODUCTS = ('WHEAT', 'CARROT', 'TOMATO', 'STRAWBERRY', 'MELON', 'EGG', 'MILK', 'WOOL', 'FERTILIZER')
PRIORITY = {'WATER': 0, 'FEED': 0, 'HARVEST': 1, 'CARE': 2, 'COLLECT_FERTILIZER': 3}


def distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def nearest_home(pos):
    return min(ACCESS, key=lambda q: (distance(pos, q), q))


def direction(pos, target):
    if pos[0] != target[0]:
        return ['EAST' if target[0] > pos[0] else 'WEST']
    if pos[1] != target[1]:
        return ['SOUTH' if target[1] > pos[1] else 'NORTH']
    return ['PASS']


def canonical_sha(problem):
    raw = json.dumps(problem, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def hire_cost(count):
    a, b, result = 1, 1, 0
    for _ in range(count):
        result += a
        a, b = b, a + b
    return result


def schedule_day(problem, n_hands):
    """逐小时构造所有工人、作业、物料和入仓动作；失败保留已构造前缀。"""
    result = {'schema': 'r10-future-day-certificate-v1', 'status': 'NO_CERTIFICATE',
              'problem_sha256': canonical_sha(problem), 'n_hands': n_hands,
              'actions': [], 'markets': [], 'scheduled_service_ids': [],
              'hire_cost': 0, 'terminal_positions': {}, 'reason': None}

    def reject(reason):
        result['reason'] = reason
        return result

    if problem.get('status') != 'SUPPORTED':
        return reject('UNSUPPORTED_PROBLEM')
    if isinstance(n_hands, bool) or not isinstance(n_hands, int) or not 0 <= n_hands <= 12:
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
    if any(s['op'] not in (*PRIORITY, 'PLACE') for s in services):
        return reject('UNSUPPORTED_SERVICE_OPERATION')
    if any(dep not in by_id for s in services for dep in s['dependencies']):
        return reject('UNKNOWN_DEPENDENCY')
    if problem['feed_units'] > 16 or problem['planned_wheat_buy']['qty'] > 16:
        return reject('FEED_SCOPE_EXCEEDED')

    field = [s for s in services if s['op'] != 'PLACE']
    deliveries = [s for s in services if s['op'] == 'PLACE']
    groups = defaultdict(list)
    for s in field:
        groups[s['asset_id']].append(s)
    for group in groups.values():
        if len({tuple(s['pos']) for s in group}) != 1:
            return reject('ASSET_POSITION_CONFLICT')
        group.sort(key=lambda s: (s['deadline'], PRIORITY[s['op']], s['service_id']))

    # 每份待交付物量绑定到明确田间来源；不能用仓内旧货核销新产物。
    outputs = defaultdict(list)
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

    workers = [{'pos': (4, 4), 'inv': Counter(), 'lots': Counter(), 'target': None}]
    shed = Counter(problem['start_shed'])
    reserved = Counter(problem['reserved_shed'])
    progress = Counter()
    done = set()
    assigned = {}
    total_hired = 0

    def remaining(group_id):
        return [s for s in groups[group_id] if s['service_id'] not in done]

    def ready(s, hour):
        return s['release'] <= hour <= s['deadline'] and all(dep in done for dep in s['dependencies'])

    def wheat_free(w):
        committed = sum(q for sid, q in w['lots'].items() if by_id[sid]['item'] == 'WHEAT')
        return w['inv'].get('WHEAT', 0) - committed

    def pending_items(w):
        return {by_id[sid]['item'] for sid, q in w['lots'].items() if q > 0}

    def projected_group_cost(w, group):
        pos = tuple(group[0]['pos'])
        steps = distance(w['pos'], pos)
        needed = sum(s['requires'].get('WHEAT', 0) for s in group)
        if needed > wheat_free(w):
            depot = min(ACCESS, key=lambda q: (distance(w['pos'], q) + distance(q, pos), q))
            steps = distance(w['pos'], depot) + 1 + distance(depot, pos)
        output_items = pending_items(w) | {item for s in group for item, qty in s['gives'].items() if qty}
        tail = distance(pos, nearest_home(pos)) + len(output_items) if output_items else 0
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
            deadline = min(s['deadline'] for s in rem)
            if hour + cost - 1 > end:
                continue
            if not any(ready(s, hour) or s['release'] > hour for s in rem):
                continue
            # 总交付尾程只作构造时筛选，最后仍逐时槽真实模拟，不能据估值直接通过。
            pool.append(((deadline, cost, distance(w['pos'], rem[0]['pos']), gid), gid))
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
            return ['PASS'], []
        if w['pos'] not in ACCESS:
            action = direction(w['pos'], nearest_home(w['pos']))
            move_worker(w, action)
            return action, []
        room = problem['capacity'] - sum(shed.values())
        if room <= 0:
            return ['PASS'], []
        item = min({by_id[sid]['item'] for sid in eligible},
                   key=lambda p: (min(by_id[sid]['deadline'] for sid in eligible if by_id[sid]['item'] == p), p))
        allocations, total = [], 0
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
            return ['PASS'], []
        w['inv'][item] -= total
        shed[item] += total
        for alloc in allocations:
            sid, qty = alloc['service_id'], alloc['qty']
            w['lots'][sid] -= qty
            progress[sid] += qty
            if progress[sid] == by_id[sid]['qty']:
                done.add(sid)
        return ['PLACE', item, total], allocations

    for hour in range(end + 1):
        # 新工只在市场阶段append；本循环开始时列出的工人才有本小时动作。
        for unit, w in enumerate(workers):
            action, allocations = ['PASS'], []
            if not (hour == 0 and unit == 0):
                gid = w['target']
                if gid and not remaining(gid):
                    w['target'] = None
                    assigned.pop(gid, None)
                if w['target'] is None:
                    free_assignment(w, unit, hour)
                gid = w['target']
                if gid:
                    rem = remaining(gid)
                    available = [s for s in rem if ready(s, hour)]
                    if available:
                        s = min(available, key=lambda q: (q['deadline'], PRIORITY[q['op']], q['service_id']))
                        target = tuple(s['pos'])
                        need = s['requires'].get('WHEAT', 0)
                        if need > wheat_free(w):
                            depot = min(ACCESS, key=lambda q: (distance(w['pos'], q) + distance(q, target), q))
                            if w['pos'] != depot:
                                action = direction(w['pos'], depot)
                                move_worker(w, action)
                            elif shed.get('WHEAT', 0) >= need - wheat_free(w):
                                # 精确领取当前阶段缺口，不让预取囤积饿住另一工人的必要阶段。
                                qty = need - wheat_free(w)
                                action = ['PICKUP', 'WHEAT', qty]
                                shed['WHEAT'] -= qty
                                w['inv']['WHEAT'] += qty
                        elif w['pos'] != target:
                            action = direction(w['pos'], target)
                            move_worker(w, action)
                        elif all(w['inv'].get(item, 0) >= qty for item, qty in s['requires'].items()):
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
            occupancy = Counter(w['pos'] for w in workers)
            spawn = min(ACCESS, key=lambda p: (occupancy[p], ACCESS.index(p)))
            workers.append({'pos': spawn, 'inv': Counter(), 'lots': Counter(), 'target': None})
            total_hired += 1
            orders.append(['HIRE'])
        if hour == 0 and problem['planned_wheat_buy']['qty']:
            qty = problem['planned_wheat_buy']['qty']
            if sum(shed.values()) + qty > problem['capacity']:
                return reject('PLANNED_BUY_EXCEEDS_SHED')
            orders.append(['BUY_PRODUCT', 'WHEAT', qty])
            shed['WHEAT'] += qty
        for item in PRODUCTS:
            qty = max(0, shed.get(item, 0) - reserved.get(item, 0))
            # 尚需FEED的小麦不可在材料服务前卖掉，保留量不等于额外库存。
            if item == 'WHEAT':
                needed = sum(s['requires'].get('WHEAT', 0) for s in field if s['service_id'] not in done)
                available_carried = sum(max(0, wheat_free(w)) for w in workers)
                qty = min(qty, max(0, shed.get(item, 0) - max(0, needed - available_carried)))
            if qty and len(orders) < 10:
                orders.append(['SELL', item, qty])
                shed[item] -= qty
        result['markets'].append({'hour': hour, 'orders': orders})

    result['scheduled_service_ids'] = sorted(done)
    result['hire_cost'] = hire_cost(total_hired)
    result['terminal_positions'] = {str(i): list(w['pos']) for i, w in enumerate(workers)}
    result['terminal_shed'] = dict(shed)
    result['terminal_inventories'] = [dict(w['inv']) for w in workers]
    result['remaining_service_quantities'] = {s['service_id']: s['qty'] - progress[s['service_id']] for s in services if s['service_id'] not in done}
    if result['remaining_service_quantities']:
        return reject('UNSCHEDULED_SERVICES')
    result['status'] = 'FEASIBLE'
    return result
