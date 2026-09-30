#!/usr/bin/env python3
"""独立手写动作与反例；不调用调度器产生测试oracle。"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import unittest

from checker import check_certificate

HERE = Path(__file__).resolve().parent
POSITIONS = [[3, 4], [3, 3], [3, 2], [3, 1], [2, 1], [1, 1]]
LITERAL_ROUTE = ['WEST', 'WATER', 'NORTH', 'WATER', 'NORTH', 'WATER', 'NORTH', 'WATER',
                 'WEST', 'WATER', 'WEST', 'WATER', 'EAST', 'EAST', 'EAST', 'SOUTH', 'SOUTH', 'SOUTH']
EVIDENCE = []


def bind(problem, certificate):
    certificate['problem_sha256'] = hashlib.sha256(json.dumps(problem, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    return certificate


def six_grid():
    problem = {'schema': 'r10-water-problem-v1', 'day': 0, 'start_step': 0, 'end_step': 17, 'board_size': 10,
               'units': [{'unit': 0, 'start': [4, 4], 'available_from': 0, 'available_until': 17, 'return_to': [4, 4]}],
               'services': [{'service_id': 'water_' + str(i), 'asset_id': {'position': p, 'crop': 'MELON', 'planted_day': 0},
                             'position': p, 'earliest_step': 0, 'deadline_step': 17} for i, p in enumerate(POSITIONS)],
               'eligible_water_positions': deepcopy(POSITIONS),
               'observation_evidence': {'step': 0, 'day': 0, 'hour': 0,
                                        'units': [{'unit': 0, 'position': [4, 4]}],
                                        'tiles': [{'position': list(p), 'tile': {'kind': 'PLANT', 'crop': 'MELON', 'planted_day': 0,
                                                                              'watered_today': False, 'max_lifespan_step': 312}} for p in POSITIONS]}}
    actions = []
    water_index = 0
    for step, op in enumerate(LITERAL_ROUTE):
        sid = 'water_' + str(water_index) if op == 'WATER' else None
        if op == 'WATER': water_index += 1
        actions.append({'step': step, 'unit': 0, 'action': [op], 'service_id': sid})
    cert = {'schema': 'r10-water-certificate-v1', 'status': 'FEASIBLE', 'actions': actions,
            'scheduled_service_ids': ['water_' + str(i) for i in range(6)], 'terminal_positions': {'0': [4, 4]}, 'reason': None}
    return problem, bind(problem, cert)


def passive(day=0, start=0, end=0, point=None):
    point = point or [4, 4]
    p = {'schema': 'r10-water-problem-v1', 'day': day, 'start_step': start, 'end_step': end, 'board_size': 10,
         'units': [{'unit': 0, 'start': point, 'available_from': start, 'available_until': end, 'return_to': None}],
         'services': [], 'eligible_water_positions': [],
         'observation_evidence': {'step': start, 'day': day, 'hour': start % 24,
                                  'units': [{'unit': 0, 'position': list(point)}], 'tiles': []}}
    c = {'schema': 'r10-water-certificate-v1', 'status': 'FEASIBLE',
         'actions': [{'step': t, 'unit': 0, 'action': ['PASS'], 'service_id': None} for t in range(start, end + 1)],
         'scheduled_service_ids': [], 'terminal_positions': {'0': point}, 'reason': None}
    return p, bind(p, c)


class CheckerTests(unittest.TestCase):
    def verify(self, p, c, expected, code=None):
        before = deepcopy((p, c))
        result = check_certificate(p, c)
        self.assertEqual(result['valid'], expected, result)
        self.assertEqual((p, c), before, '检查器不能修改输入问题或证书')
        if code: self.assertEqual(result['errors'][0]['code'], code, result)
        EVIDENCE.append(deepcopy({'test': self.id(), 'expected_valid': expected, 'problem': p, 'certificate': c, 'result': result}))
        return result

    def test_literal_six_grid_18_actions(self):
        p, c = six_grid(); result = self.verify(p, c, True)
        self.assertEqual(result['stats']['processed_actions'], 18)
        self.assertEqual(result['stats']['action_counts']['WATER'], 6)
        self.assertEqual(sum(result['stats']['action_counts'].get(k, 0) for k in ('NORTH', 'SOUTH', 'EAST', 'WEST')), 12)

    def test_only17_slots_rejects_unfinished_return(self):
        p, c = six_grid(); p['end_step'] = p['units'][0]['available_until'] = 16
        for s in p['services']: s['deadline_step'] = 16
        c['actions'].pop(); c['terminal_positions']['0'] = [4, 3]
        self.verify(p, bind(p, c), False, 'RETURN_NOT_COMPLETED')

    def test_far_observed_start_not_replaced_by_nearest_shed(self):
        p, c = six_grid(); p['units'][0]['start'] = [9, 9]
        p['observation_evidence']['units'][0]['position'] = [9, 9]
        self.verify(p, bind(p, c), False, 'WATER_WRONG_POSITION')

    def test_problem_hash_binds_exact_start(self):
        p, c = six_grid(); p['units'][0]['start'] = [9, 9]
        self.verify(p, c, False, 'PROBLEM_HASH_MISMATCH')

    def test_missing_action_slot(self):
        p, c = six_grid(); c['actions'].pop(0)
        self.verify(p, c, False, 'MISSING_UNIT_SLOT')

    def test_duplicate_unit_slot(self):
        p, c = six_grid(); c['actions'].append(deepcopy(c['actions'][0]))
        self.verify(p, c, False, 'DUPLICATE_UNIT_SLOT')

    def test_unknown_not_yet_arrived_worker(self):
        p, c = six_grid(); c['actions'][0]['unit'] = 7
        self.verify(p, c, False, 'UNKNOWN_UNIT')

    def test_action_before_unit_available(self):
        p, c = six_grid(); p['units'][0]['available_from'] = 1
        self.verify(p, bind(p, c), False, 'ACTION_OUTSIDE_UNIT_WINDOW')

    def test_water_requires_actual_position(self):
        p, c = six_grid(); c['actions'][0]['action'] = ['PASS']
        self.verify(p, c, False, 'WATER_WRONG_POSITION')

    def test_late_and_early_service_rejected(self):
        p, c = six_grid(); p['services'][0]['deadline_step'] = 0
        self.verify(p, bind(p, c), False, 'SERVICE_DEADLINE')
        p, c = six_grid(); p['services'][0]['earliest_step'] = 2
        self.verify(p, bind(p, c), False, 'SERVICE_DEADLINE')

    def test_nonwater_cannot_claim_service(self):
        for op in ('WEST', 'PASS'):
            p, c = six_grid(); c['actions'][0].update(action=[op], service_id='water_0')
            self.verify(p, c, False, 'NON_WATER_HAS_SERVICE')

    def test_completed_field_cannot_replace_water(self):
        p, c = six_grid(); c['actions'][1].update(action=['PASS'], service_id=None)
        self.verify(p, c, False, 'UNSERVED_REQUIRED_SERVICE')

    def test_scheduled_ids_must_match_real_actions(self):
        for ids in ([], ['water_' + str(i) for i in range(6)] + ['water_0'], [True]):
            p, c = six_grid(); c['scheduled_service_ids'] = ids
            self.verify(p, c, False)

    def test_duplicate_physical_service_with_new_id(self):
        p, c = six_grid(); duplicate = deepcopy(p['services'][0]); duplicate['service_id'] = 'fake_second_water'
        p['services'].append(duplicate)
        self.verify(p, bind(p, c), False, 'DUPLICATE_PHYSICAL_WATER_SERVICE')

    def test_service_twice_across_workers(self):
        p, c = passive(end=0)
        p['units'] = [{'unit': i, 'start': [4, 4], 'available_from': 0, 'available_until': 0, 'return_to': None} for i in (0, 1)]
        p['observation_evidence']['units'] = [{'unit': i, 'position': [4, 4]} for i in (0, 1)]
        p['observation_evidence']['tiles'] = [{'position': [4, 4], 'tile': {'kind': 'PLANT', 'crop': 'MELON', 'planted_day': 0, 'watered_today': False, 'max_lifespan_step': -1}}]
        p['eligible_water_positions'] = [[4, 4]]
        p['services'] = [{'service_id': 'w', 'asset_id': {'position': [4, 4], 'crop': 'MELON', 'planted_day': 0},
                          'position': [4, 4], 'earliest_step': 0, 'deadline_step': 0}]
        c['actions'] = [{'step': 0, 'unit': i, 'action': ['WATER'], 'service_id': 'w'} for i in (0, 1)]
        c['terminal_positions'] = {'0': [4, 4], '1': [4, 4]}; c['scheduled_service_ids'] = ['w']
        self.verify(p, bind(p, c), False, 'SERVICE_EXECUTED_TWICE')

    def test_adapter_ineligible_positions_cannot_be_serviced(self):
        # 资格集合明确排除时，服务不可重新把该格加回来。
        for reason in ('already_watered', 'dead_or_nonplant', 'locked_tile'):
            p, c = six_grid(); p['eligible_water_positions'].remove([3, 4])
            with self.subTest(adapter_exclusion=reason):
                self.verify(p, bind(p, c), False, 'SERVICE_NOT_ELIGIBLE')

    def test_eligible_cannot_lie_about_watered_dead_or_locked_tile(self):
        for tile in ({'kind': 'PLANT', 'crop': 'MELON', 'planted_day': 0, 'watered_today': True, 'max_lifespan_step': 312},
                     {'kind': 'WEED'}, 'LOCKED', None):
            p, c = six_grid(); p['observation_evidence']['tiles'][0]['tile'] = tile
            self.verify(p, bind(p, c), False, 'ELIGIBLE_TILE_NOT_LIVE_UNWATERED')

    def test_observed_unit_start_and_clock_cannot_be_forged(self):
        p, c = six_grid(); p['units'][0]['start'] = [9, 9]
        self.verify(p, bind(p, c), False, 'OBSERVED_UNIT_START_MISMATCH')
        p, c = six_grid(); p['observation_evidence']['hour'] = 1
        self.verify(p, bind(p, c), False, 'OBSERVATION_CLOCK_MISMATCH')

    def test_observed_asset_birth_must_match(self):
        p, c = six_grid(); p['observation_evidence']['tiles'][0]['tile']['crop'] = 'CARROT'
        self.verify(p, bind(p, c), False, 'OBSERVED_ASSET_ID_MISMATCH')

    def test_lifespan_before_arrival_and_fake_deadline(self):
        p, c = passive(day=2, start=48, end=50)
        p['units'][0]['return_to'] = [4, 4]
        p['eligible_water_positions'] = [[3, 4]]
        p['observation_evidence']['tiles'] = [{'position': [3, 4], 'tile': {'kind': 'PLANT', 'crop': 'MELON', 'planted_day': 0,
                                                                         'watered_today': False, 'max_lifespan_step': 48}}]
        p['services'] = [{'service_id': 'w', 'asset_id': {'position': [3, 4], 'crop': 'MELON', 'planted_day': 0},
                          'position': [3, 4], 'earliest_step': 48, 'deadline_step': 48}]
        c['actions'] = [{'step': 48+i, 'unit': 0, 'action': [op], 'service_id': 'w' if op == 'WATER' else None}
                        for i, op in enumerate(['WEST', 'WATER', 'EAST'])]
        c['scheduled_service_ids'] = ['w']; c['terminal_positions'] = {'0': [4, 4]}
        self.verify(p, bind(p, c), False, 'SERVICE_DEADLINE')
        p['services'][0]['deadline_step'] = 49
        self.verify(p, bind(p, c), False, 'SERVICE_DEADLINE_AFTER_LIFESPAN')
        p['services'][0]['deadline_step'] = 48
        p['observation_evidence']['tiles'][0]['tile']['max_lifespan_step'] = 47
        self.verify(p, bind(p, c), False, 'ELIGIBLE_TILE_ALREADY_EXPIRED')

    def test_water_at_exact_lifespan_is_allowed(self):
        p, c = passive(day=2, start=48, end=48, point=[3, 4])
        p['eligible_water_positions'] = [[3, 4]]
        p['observation_evidence']['tiles'] = [{'position': [3, 4], 'tile': {'kind': 'PLANT', 'crop': 'MELON', 'planted_day': 0,
                                                                         'watered_today': False, 'max_lifespan_step': 48}}]
        p['services'] = [{'service_id': 'w', 'asset_id': {'position': [3, 4], 'crop': 'MELON', 'planted_day': 0},
                          'position': [3, 4], 'earliest_step': 48, 'deadline_step': 48}]
        c['actions'][0].update(action=['WATER'], service_id='w'); c['scheduled_service_ids'] = ['w']
        self.verify(p, bind(p, c), True)

    def test_asset_mismatch_and_future_birth(self):
        p, c = six_grid(); p['services'][0]['asset_id'] = {'position': [3, 4], 'crop': 'COW', 'planted_day': 0}
        self.verify(p, bind(p, c), False, 'ASSET_NOT_CROP')
        p, c = six_grid(); p['services'][0]['asset_id']['planted_day'] = 1
        self.verify(p, bind(p, c), False, 'ASSET_NOT_YET_PLANTED')

    def test_move_boundary_and_locked_transit(self):
        p, c = passive(point=[0, 0]); c['actions'][0]['action'] = ['WEST']
        self.verify(p, c, False, 'MOVE_OUTSIDE_BOARD')
        p, c = passive(point=[4, 4]); c['actions'][0]['action'] = ['EAST']; c['terminal_positions']['0'] = [5, 4]
        # 资格为空也允许移动；不得把非作业资格格当移动障碍。
        self.verify(p, c, True)

    def test_terminal_position_cannot_be_faked(self):
        p, c = six_grid(); c['terminal_positions']['0'] = [9, 9]
        self.verify(p, c, False, 'TERMINAL_POSITION_MISMATCH')

    def test_day29_hour22_allowed_and_hour23_rejected(self):
        p, c = passive(day=29, start=718, end=718); self.verify(p, c, True)
        p, c = passive(day=29, start=719, end=719); self.verify(p, c, False, 'GAME_TIME_RANGE')
        p, c = passive(day=0, start=23, end=24); self.verify(p, c, False, 'CROSS_DAY_UNSUPPORTED')

    def test_two_workers_may_share_position(self):
        p, c = passive()
        p['units'].append({'unit': 1, 'start': [4, 4], 'available_from': 0, 'available_until': 0, 'return_to': [4, 4]})
        p['observation_evidence']['units'].append({'unit': 1, 'position': [4, 4]})
        c['actions'].append({'step': 0, 'unit': 1, 'action': ['PASS'], 'service_id': None})
        c['terminal_positions']['1'] = [4, 4]
        self.verify(p, bind(p, c), True)

    def test_numeric_and_action_domains(self):
        p, c = six_grid(); c['actions'][0]['step'] = True
        self.verify(p, c, False, 'INTEGER_DOMAIN')
        p, c = six_grid(); c['actions'][0]['action'] = ['FEED']
        self.verify(p, c, False, 'UNSUPPORTED_ACTION')
        p, c = six_grid(); p['units'][0]['start'] = [4.0, 4]
        self.verify(p, bind(p, c), False, 'INTEGER_DOMAIN')

    def test_no_certificate_is_not_pass(self):
        p, c = six_grid(); c['status'] = 'NO_CERTIFICATE'; c['reason'] = '搜索未找到'
        self.verify(p, c, False, 'NO_FEASIBLE_CERTIFICATE')


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CheckerTests))
    output = {'created_at': datetime.now(timezone.utc).isoformat(), 'test_methods': result.testsRun,
              'failures': len(result.failures), 'errors': len(result.errors), 'passed': result.wasSuccessful(),
              'checker_sha256': hashlib.sha256((HERE / 'checker.py').read_bytes()).hexdigest(),
              'test_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'cases': EVIDENCE,
              'scheduler_calls': 0, 'candidate_calls': 0, 'engine_calls': 0,
              'qualification': '依原obs证据切片核证书；切片真实性由adapter+obs SHA负责，不证明R9实际兑现。'}
    path = HERE / ('checker_tests_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    with path.open('x') as stream: json.dump(output, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({'output': str(path), 'test_methods': result.testsRun, 'recorded_cases': len(EVIDENCE), 'passed': result.wasSuccessful()}, ensure_ascii=False))
    raise SystemExit(0 if result.wasSuccessful() else 1)
