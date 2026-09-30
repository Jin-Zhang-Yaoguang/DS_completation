"""WATER-only 当前日证书独立检查器；不导入调度器、候选或引擎。"""
from __future__ import annotations

from collections import Counter
import hashlib
import json

PROBLEM_SCHEMA = 'r10-water-problem-v1'
CERTIFICATE_SCHEMA = 'r10-water-certificate-v1'
CROPS = {'WHEAT', 'CARROT', 'TOMATO', 'STRAWBERRY', 'MELON'}
MOVES = {'NORTH': (0, -1), 'SOUTH': (0, 1), 'WEST': (-1, 0), 'EAST': (1, 0)}


class InvalidCertificate(ValueError):
    def __init__(self, code, detail, **context):
        self.error = {'code': code, 'detail': detail, **context}
        super().__init__(detail)


def need(condition, code, detail, **context):
    if not condition:
        raise InvalidCertificate(code, detail, **context)


def integer(value, label):
    need(type(value) is int, 'INTEGER_DOMAIN', label + '必须为严格整数')
    return value


def position(value, board, label):
    need(isinstance(value, list) and len(value) == 2, 'POSITION_DOMAIN', label + '必须为[x,y]')
    x, y = integer(value[0], label + '.x'), integer(value[1], label + '.y')
    need(0 <= x < board and 0 <= y < board, 'POSITION_OUTSIDE_BOARD', label + '超出棋盘')
    return x, y


def check_certificate(problem, certificate):
    """以原观测切片核动作证书；切片真实性仍由原obs/SHA链证明，不证明R9兑现。"""
    stats = {'guarantee': 'CONDITIONAL_CERTIFICATE_ONLY_NOT_R9_REALIZATION',
             'processed_actions': 0, 'completed_services': 0}
    try:
        need(isinstance(problem, dict) and isinstance(certificate, dict), 'OBJECT_REQUIRED', '问题和证书必须为对象')
        need(problem.get('schema') == PROBLEM_SCHEMA, 'PROBLEM_SCHEMA', '问题schema不匹配')
        need(certificate.get('schema') == CERTIFICATE_SCHEMA, 'CERTIFICATE_SCHEMA', '证书schema不匹配')
        encoded = json.dumps(problem, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')
        digest = hashlib.sha256(encoded).hexdigest()
        need(certificate.get('problem_sha256') == digest, 'PROBLEM_HASH_MISMATCH', '证书未绑定本份问题')
        stats['problem_sha256'] = digest
        need(certificate.get('status') == 'FEASIBLE', 'NO_FEASIBLE_CERTIFICATE', 'NO_CERTIFICATE不构成通过，也不证明无解')
        board = integer(problem['board_size'], 'board_size')
        need(board == 10, 'UNSUPPORTED_BOARD_SIZE', '阶段A只接受10×10棋盘')
        day = integer(problem['day'], 'day')
        start, end = integer(problem['start_step'], 'start_step'), integer(problem['end_step'], 'end_step')
        need(0 <= day <= 29 and 0 <= start <= end <= 718, 'GAME_TIME_RANGE', '时段不在实际决策范围')
        need(start // 24 == day and end // 24 == day, 'CROSS_DAY_UNSUPPORTED', '阶段A时段不能跨日')
        need(end <= day * 24 + (22 if day == 29 else 23), 'TERMINAL_HOUR_INVALID', 'day29没有h23动作')
        evidence = problem['observation_evidence']
        need(isinstance(evidence, dict), 'OBSERVATION_EVIDENCE_REQUIRED', '必须提供原观测切片')
        need(integer(evidence['step'], 'evidence.step') == start and integer(evidence['day'], 'evidence.day') == day
             and integer(evidence['hour'], 'evidence.hour') == start % 24, 'OBSERVATION_CLOCK_MISMATCH', '原观测时钟与问题不一致')
        need(isinstance(evidence['units'], list) and isinstance(evidence['tiles'], list), 'OBSERVATION_EVIDENCE_DOMAIN', '工人和地块证据必须为列表')
        observed_units, observed_tiles = {}, {}
        for record in evidence['units']:
            uid = integer(record['unit'], 'observed.unit')
            need(uid >= 0 and uid not in observed_units, 'OBSERVATION_DUPLICATE_UNIT', '原观测工人id必须唯一')
            observed_units[uid] = position(record['position'], board, 'observed.unit.position')
        for record in evidence['tiles']:
            pos = position(record['position'], board, 'observed.tile.position')
            need(pos not in observed_tiles, 'OBSERVATION_DUPLICATE_TILE', '原观测地块不能重复')
            observed_tiles[pos] = record['tile']
        units_list, services_list = problem['units'], problem['services']
        need(isinstance(units_list, list) and bool(units_list), 'UNITS_REQUIRED', '必须显式列出现有工人')
        need(isinstance(services_list, list), 'SERVICES_DOMAIN', '服务必须为列表')
        units, positions, expected_slots = {}, {}, set()
        for unit in units_list:
            need(isinstance(unit, dict), 'UNIT_DOMAIN', '工人记录必须为对象')
            uid = integer(unit['unit'], 'unit')
            need(uid >= 0 and uid not in units, 'DUPLICATE_OR_INVALID_UNIT', '工人id须唯一且非负')
            first = integer(unit['available_from'], 'available_from')
            last = integer(unit['available_until'], 'available_until')
            need(start <= first <= last <= end, 'UNIT_WINDOW_INVALID', '工人可用窗口须位于问题时段内', unit=uid)
            positions[uid] = position(unit['start'], board, 'unit.start')
            need(uid in observed_units and positions[uid] == observed_units[uid], 'OBSERVED_UNIT_START_MISMATCH', '工人必须已到场，起点必须等于原观测', unit=uid)
            return_to = unit.get('return_to')
            if return_to is not None:
                position(return_to, board, 'unit.return_to')
            units[uid] = unit
            expected_slots.update((step, uid) for step in range(first, last + 1))
        eligible_raw = problem['eligible_water_positions']
        need(isinstance(eligible_raw, list), 'ELIGIBLE_DOMAIN', '资格地块必须为列表')
        eligible = [position(p, board, 'eligible_water_positions') for p in eligible_raw]
        need(len(eligible) == len(set(eligible)), 'DUPLICATE_ELIGIBLE_POSITION', '资格地块不能重复')
        eligible = set(eligible)
        for pos in eligible:
            tile = observed_tiles.get(pos)
            need(isinstance(tile, dict) and tile.get('kind') == 'PLANT' and tile.get('watered_today') is False,
                 'ELIGIBLE_TILE_NOT_LIVE_UNWATERED', '资格集合不能包含已水、非植物、死亡或LOCKED地块', position=list(pos))
            lifespan = integer(tile['max_lifespan_step'], 'observed.max_lifespan_step')
            need(lifespan >= -1 and (lifespan == -1 or lifespan >= start), 'ELIGIBLE_TILE_ALREADY_EXPIRED', '已越过已知寿命时点的植物不支持', position=list(pos))
        services, occupied = {}, set()
        for service in services_list:
            need(isinstance(service, dict), 'SERVICE_DOMAIN', '服务记录必须为对象')
            sid = service['service_id']
            need(isinstance(sid, str) and bool(sid) and sid not in services, 'DUPLICATE_OR_INVALID_SERVICE', '服务id须为唯一非空字符串')
            pos = position(service['position'], board, 'service.position')
            need(pos not in occupied, 'DUPLICATE_PHYSICAL_WATER_SERVICE', '同一地块本日WATER不能以不同id重复列账')
            need(pos in eligible, 'SERVICE_NOT_ELIGIBLE', '服务地块不在真实未水植物资格集合', service_id=sid)
            asset = service['asset_id']
            need(isinstance(asset, dict), 'ASSET_DOMAIN', 'asset_id须显式给出出生信息')
            need(position(asset['position'], board, 'asset.position') == pos, 'ASSET_POSITION_MISMATCH', '资产位置与服务位置不一致')
            need(asset['crop'] in CROPS, 'ASSET_NOT_CROP', '资产必须为允许的作物')
            born = integer(asset['planted_day'], 'planted_day')
            need(0 <= born <= day, 'ASSET_NOT_YET_PLANTED', '不得对未来播种资产签当前日证书')
            tile = observed_tiles[pos]
            need(tile.get('crop') == asset['crop'] and integer(tile['planted_day'], 'observed.planted_day') == born,
                 'OBSERVED_ASSET_ID_MISMATCH', '资产品种/出生日期必须等于原观测，不能换资产身份')
            earliest = integer(service['earliest_step'], 'earliest_step')
            deadline = integer(service['deadline_step'], 'deadline_step')
            need(day * 24 <= earliest <= deadline <= day * 24 + (22 if day == 29 else 23),
                 'SERVICE_WINDOW_INVALID', '服务窗口须为当前真实日的合法时段')
            lifespan = tile['max_lifespan_step']
            need(lifespan == -1 or deadline <= lifespan, 'SERVICE_DEADLINE_AFTER_LIFESPAN', '服务截止不能晚于已知寿命时点', service_id=sid)
            services[sid] = service; occupied.add(pos)
        actions = certificate['actions']
        need(isinstance(actions, list), 'ACTIONS_DOMAIN', 'actions必须为列表')
        by_slot = {}
        for record in actions:
            need(isinstance(record, dict), 'ACTION_RECORD_DOMAIN', '动作记录必须为对象')
            step = integer(record['step'], 'action.step')
            uid = integer(record['unit'], 'action.unit')
            key = (step, uid)
            need(uid in units, 'UNKNOWN_UNIT', '不得引入未到场工人', unit=uid)
            need(key in expected_slots, 'ACTION_OUTSIDE_UNIT_WINDOW', '动作不在该工人的可用时槽', step=step, unit=uid)
            need(key not in by_slot, 'DUPLICATE_UNIT_SLOT', '同工人同一时槽只能有一个动作', step=step, unit=uid)
            op = record['action']
            need(isinstance(op, list) and len(op) == 1 and isinstance(op[0], str) and op[0] in {*MOVES, 'WATER', 'PASS'},
                 'UNSUPPORTED_ACTION', '阶段A只允许单个移动/WATER/PASS命令')
            sid = record['service_id']
            need(sid is None or isinstance(sid, str), 'ACTION_SERVICE_DOMAIN', 'service_id必须为字符串或null')
            if op[0] != 'WATER':
                need(sid is None, 'NON_WATER_HAS_SERVICE', '移动/PASS不能假记已服务阶段')
            by_slot[key] = record
        need(set(by_slot) == expected_slots, 'MISSING_UNIT_SLOT', '每个工人的每个可用时槽都须显式给出动作', missing_count=len(expected_slots - set(by_slot)))
        stats['expected_actions'] = len(expected_slots)
        done, counts = set(), Counter()
        for (step, uid), record in sorted(by_slot.items()):
            op, sid = record['action'][0], record['service_id']
            pos = positions[uid]
            if op in MOVES:
                dx, dy = MOVES[op]
                nxt = pos[0] + dx, pos[1] + dy
                need(0 <= nxt[0] < board and 0 <= nxt[1] < board, 'MOVE_OUTSIDE_BOARD', '移动越出棋盘', step=step, unit=uid)
                positions[uid] = nxt  # 允许路过LOCKED；不虚构地块阻挡或工人碰撞。
            elif op == 'WATER':
                need(sid in services, 'WATER_UNKNOWN_SERVICE', 'WATER必须绑定已声明服务', step=step, unit=uid)
                need(sid not in done, 'SERVICE_EXECUTED_TWICE', '同一服务只能实际完成一次', service_id=sid)
                service = services[sid]
                need(pos == tuple(service['position']), 'WATER_WRONG_POSITION', '必须站在服务地块才能浇水', step=step, unit=uid, service_id=sid)
                need(pos in eligible, 'WATER_NOT_ELIGIBLE', '已水/非活植物/LOCKED作业不可通过', step=step, unit=uid)
                need(service['earliest_step'] <= step <= service['deadline_step'], 'SERVICE_DEADLINE', '浇水未落在服务时窗', step=step, service_id=sid)
                done.add(sid)
            counts[op] += 1
            stats['processed_actions'] += 1
        stats.update(completed_services=len(done), action_counts=dict(counts), terminal_positions_derived={str(u): list(p) for u, p in positions.items()})
        need(done == set(services), 'UNSERVED_REQUIRED_SERVICE', '不能以完成字段代替实际WATER动作', missing=sorted(set(services) - done))
        claimed = certificate['scheduled_service_ids']
        need(isinstance(claimed, list) and all(isinstance(s, str) for s in claimed), 'SCHEDULED_IDS_DOMAIN', '完成服务id须为字符串列表')
        need(len(claimed) == len(set(claimed)) and set(claimed) == done, 'SCHEDULED_IDS_MISMATCH', '完成字段须与逐动作重演结果完全相同')
        terminal = certificate['terminal_positions']
        need(isinstance(terminal, dict) and set(terminal) == {str(uid) for uid in units}, 'TERMINAL_UNITS_MISMATCH', '终点必须精确覆盖原工人')
        for uid, pos in positions.items():
            need(position(terminal[str(uid)], board, 'terminal_position') == pos, 'TERMINAL_POSITION_MISMATCH', '证书声明终点与动作结果不符', unit=uid)
            target = units[uid].get('return_to')
            if target is not None:
                need(pos == tuple(target), 'RETURN_NOT_COMPLETED', '要求的返仓/终点尚未到达', unit=uid)
        return {'valid': True, 'errors': [], 'stats': stats}
    except InvalidCertificate as exc:
        return {'valid': False, 'errors': [exc.error], 'stats': stats}
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        return {'valid': False, 'errors': [{'code': 'MALFORMED_INPUT', 'detail': str(exc)}], 'stats': stats}
