"""独立逐动作检查当日完整WATER路线；不导入求解器或候选。"""
from copy import deepcopy


def r12_check(problem, certificate):
    try:
        assert isinstance(certificate, dict) and certificate.get('problem') == problem, 'PROBLEM_IDENTITY'
        board, start, end = problem['board'], problem['step'], problem['end']
        assert type(board) is int and board == 10, 'BOARD'
        assert type(start) is int and type(end) is int and 0 <= start <= end + 1 <= 719, 'CLOCK'
        targets = {}
        for t in problem['targets']:
            pos = tuple(t['pos'])
            assert len(pos) == 2 and all(type(v) is int and 0 <= v < board for v in pos), 'TARGET_POSITION'
            assert pos not in targets, 'DUPLICATE_TARGET'
            assert type(t['deadline']) is int, 'DEADLINE_TYPE'
            targets[pos] = t
        positions = deepcopy(problem['positions'])
        routes = certificate['routes']
        assert len(routes) == len(positions) and positions, 'ACTOR_COVERAGE'
        visited = set()
        for uid, route in enumerate(routes):
            x, y = positions[uid]
            assert type(x) is int and type(y) is int and 0 <= x < board and 0 <= y < board, 'ACTOR_POSITION'
            for offset, action in enumerate(route):
                step = start + offset
                assert step <= end, 'OVERTIME'
                assert isinstance(action, list) and len(action) == 1, 'ACTION_SHAPE'
                op = action[0]
                if op == 'NORTH': y -= 1
                elif op == 'SOUTH': y += 1
                elif op == 'WEST': x -= 1
                elif op == 'EAST': x += 1
                elif op == 'WATER':
                    pos = (x, y)
                    assert pos in targets and pos not in visited, 'UNKNOWN_OR_DUPLICATE_WATER'
                    assert step <= targets[pos]['deadline'], 'LIFESPAN_DEADLINE'
                    visited.add(pos)
                else: raise AssertionError('UNSUPPORTED_ACTION')
                assert 0 <= x < board and 0 <= y < board, 'MOVE_OUT_OF_BOARD'
        assert visited == set(targets), 'MISSING_SERVICE'
        return {'valid': True, 'services': len(visited), 'error': None}
    except (AssertionError, KeyError, TypeError, ValueError, IndexError) as exc:
        return {'valid': False, 'services': 0, 'error': str(exc)}
