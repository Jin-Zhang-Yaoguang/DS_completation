"""R12当前日WATER余量规划；只表示真实现有工人与危险植物，不计未来雇工。"""
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
