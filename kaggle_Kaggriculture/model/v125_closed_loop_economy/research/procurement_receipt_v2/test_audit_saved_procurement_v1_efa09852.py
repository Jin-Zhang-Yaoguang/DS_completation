#!/usr/bin/env python3
"""纯数据故障注入；不导入策略/引擎、不产生对局。"""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

import audit_saved_procurement as audit

HERE = Path(__file__).resolve().parent
OLD_CASES = HERE.parent / 'procurement_receipt_audit/confirmation_microcases_r0/result.json'


class MemoryInputs:
    """只供人工fixture；实际输入路径的SHA校验另测。"""
    def __init__(self, data): self.data = data
    def load(self, path, expected=None, lines=False): return deepcopy(self.data[Path(path).name])


def constructed_capture(case):
    check = deepcopy(case['original_confirmation']['original_check'])
    step, order = check['issued_step'], check['order']
    op, item, n = audit.identity(order)
    trace = {'seed': 1, 'candidate_seat': 0,
             'actions': [[{'market': []}, {'market': []}] for _ in range(719)]}
    trace['actions'][step][0]['market'] = [order]
    game = {'status': 'DONE', 'calls': 719, 'seed': 1, 'candidate_seat': 0, 'key': 'CONSTRUCTED_NOT_A_GAME'}
    frames = [{'step': i, 'before': deepcopy(check['previous']), 'after': deepcopy(check['previous'])} for i in range(719)]
    frames[step]['after'] = deepcopy(check['now'])
    qty = case['official_committed_units']
    price = 400 if op == 'BUY_ANIMAL' else 10
    commits = [{'step': step, 'seat': 0, 'order_index': 0, 'op': op, 'item': item,
                'success': bool(qty), 'quantity': qty, 'price': price, 'money_delta': -price * qty}]
    data = {'trace.json': trace, 'games.jsonl': [game], 'external_state_frames.jsonl.gz': frames,
            'official_unit_commits.jsonl.gz': commits,
            'official_plant_consumption.jsonl.gz': [{'step': step, 'seat': 0, 'consumed': {item: case.get('actual_seed_consumption', 0)}}],
            'official_animal_escapes.jsonl.gz': [{'step': step, 'seat': 0, 'animal': item} for _ in range(case.get('escaped_units', 0))],
            'official_animal_overflow.jsonl.gz': [], 'candidate_fixed_order_calls.jsonl.gz': [],
            'candidate_original_checks.jsonl.gz': [check]}
    data['audit_manifest.json'] = {'source_trace': {'path': 'trace.json', 'sha256': 'FIXTURE'},
                                  'source_run': 'fixture_run', 'source_games_sha256': 'FIXTURE', 'source_game_index': 0}
    data['validation.json'] = {'files': {k: 'FIXTURE' for k in data}}
    return data


def capture(data):
    return audit.audit_capture(Path('fixture'), MemoryInputs(data))['orders'][0]


class AuditTests(unittest.TestCase):
    def test_saved_counterexamples_and_control(self):
        cases = json.loads(OLD_CASES.read_text())['rows']
        expected = [(0, 'PASS'), (0, 'FAIL_ORIGINAL_CONFIRMATION'), (1, 'FAIL_ORIGINAL_CONFIRMATION')]
        for case, (qty, status) in zip(cases, expected):
            with self.subTest(case=case['case']):
                row = capture(constructed_capture(case))
                self.assertEqual(row['actual_quantity'], qty)
                self.assertEqual(row['confirmation_status'], status)
                self.assertEqual(row['inventory_status'], 'PASS')
                self.assertEqual(row['corrected_frame_group_quantity'], qty)
                self.assertEqual(row['target_status'], 'PENDING_TARGET_EVIDENCE')

    def test_observation_loss_missing_fails(self):
        case = json.loads(OLD_CASES.read_text())['rows'][2]
        data = constructed_capture(case); data['official_animal_escapes.jsonl.gz'] = []
        self.assertEqual(capture(data)['inventory_status'], 'FAIL_OBSERVATION_IDENTITY')

    def test_missing_or_duplicate_confirm_is_pending(self):
        data = constructed_capture(json.loads(OLD_CASES.read_text())['rows'][0])
        old = data['candidate_original_checks.jsonl.gz'][0]
        for values in ([], [old, old]):
            data['candidate_original_checks.jsonl.gz'] = values
            self.assertEqual(capture(data)['confirmation_status'], 'PENDING_ORIGINAL_CONFIRM_CAPTURE')

    def test_missing_commit_is_not_zero(self):
        data = constructed_capture(json.loads(OLD_CASES.read_text())['rows'][0])
        data['official_unit_commits.jsonl.gz'] = []
        self.assertIsNone(capture(data)['actual_quantity'])
        self.assertNotEqual(capture(data)['actual_status'], 'PASS')

    def test_over_target_and_real_cash_chain(self):
        data = constructed_capture(json.loads(OLD_CASES.read_text())['rows'][2])
        target = {'step': 47, 'orders_before': 0, 'order': ['BUY_ANIMAL', 'COW', 1],
                  'accepted_by_original_budget_check': True, 'target': 2, 'net_target_gap': 1,
                  'cash_before': 400, 'cost_budgeted': 400}
        data['candidate_fixed_order_calls.jsonl.gz'] = [target]
        self.assertEqual(capture(data)['target_status'], 'PASS')
        self.assertEqual(capture(data)['cash_intent_status'], 'PASS')
        target['net_target_gap'] = 0
        self.assertEqual(capture(data)['target_status'], 'FAIL_OVER_TARGET')
        target['cash_before'] = 500
        self.assertNotEqual(capture(data)['cash_intent_status'], 'PASS')

    def test_input_sha_drift_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=HERE) as folder:
            path = Path(folder) / 'input.json'; path.write_text('{}')
            digest = audit.sha(path); path.write_text('{"changed":true}')
            with self.assertRaisesRegex(ValueError, 'INPUT_SHA_MISMATCH'):
                audit.Inputs().load(path, digest)

    def test_same_item_duplicates_are_not_assigned_fifo(self):
        rows = [self.req(index=i) for i in (0, 1)]
        output = audit.match_events(rows, [self.event(31)], 0, True)
        self.assertTrue(all(r['actual_status'] == 'PENDING_DUPLICATE_SAME_ITEM_ORDER' for r in output))
        self.assertTrue(all(r['actual_quantity'] is None for r in output))

    def test_actual_price_partial_fill_and_zero(self):
        row = audit.match_events([self.req(n=4)], [self.event(31), self.event(32)], 0, True)[0]
        self.assertEqual((row['actual_quantity'], row['actual_cash'], row['actual_status']), (2, 63, 'PASS'))
        self.assertEqual(row['actual_unit_prices'], [31, 32])
        zero = audit.match_events([self.req()], [], 0, True)[0]
        self.assertEqual(zero['actual_quantity'], 0)
        missing = audit.match_events([self.req()], [], 0, False)[0]
        self.assertIsNone(missing['actual_quantity'])

    def test_atomic_and_terminal_pending_boundaries(self):
        atomic = self.req(); atomic.update(op='BUY_LAND', item='land', order=['BUY_LAND'])
        self.assertEqual(audit.match_events([atomic], [], 0, True)[0]['actual_status'], 'PENDING_ATOMIC_EVENT_NOT_RECORDED')
        terminal = self.req(); terminal['step'] = 718
        self.assertEqual(audit.match_events([terminal], [], 0, True)[0]['confirmation_status'], 'EXTERNAL_TERMINAL_ONLY')

    def test_over_request_events_fail(self):
        row = audit.match_events([self.req(n=1)], [self.event(31), self.event(32)], 0, True)[0]
        self.assertEqual(row['actual_status'], 'FAIL_EVENT_QUANTITY_OVER_REQUEST')

    @staticmethod
    def req(index=0, n=1):
        return {'step': 0, 'seat': 0, 'order_index': index, 'order': ['BUY_PRODUCT', 'WHEAT', n],
                'op': 'BUY_PRODUCT', 'item': 'WHEAT', 'requested': n, 'outside_ten_order_limit': False}

    @staticmethod
    def event(price):
        return {'kind': 'market', 'seat': 0, 'decision_step': 0, 'op': 'BUY_PRODUCT',
                'item': 'WHEAT', 'quantity': 1, 'price': price}


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AuditTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    summary = {'test_methods': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
               'passed': result.wasSuccessful(), 'tool_sha256': audit.sha(HERE / 'audit_saved_procurement.py'),
               'test_sha256': audit.sha(__file__), 'old_microcases_sha256': audit.sha(OLD_CASES),
               'candidate_calls': 0, 'engine_calls': 0, 'new_complete_matches': 0}
    path = HERE / 'test_results.json'
    if path.exists(): raise RuntimeError('REFUSE_OVERWRITE:' + str(path))
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
