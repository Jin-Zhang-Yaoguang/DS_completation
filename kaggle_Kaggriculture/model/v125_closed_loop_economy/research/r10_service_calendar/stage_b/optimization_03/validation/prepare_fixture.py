"""仅读已打开人工控制，登记 P3 五个输入；不调用策略或引擎。"""
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD = HERE.parents[1] / 'integration_validation'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    cases, files = [], {}
    for cash in ('funded', 'zero_cash'):
        for seat in (0, 1):
            path = OLD / ('controls_v1/pressure_48_strawberries_day8_' + cash + '_s' + str(seat) + '.json.gz')
            raw = json.loads(gzip.decompress(path.read_bytes()))
            legacy = next(row for row in raw['modes'] if row['mode'] == 'legacy')
            assert len(legacy['plan']['admitted_investments']) == 0
            cases.append({'id': 'day8_' + cash + '_s' + str(seat),
                          'observation': raw['fixture']['observation'], 'reference_path': str(path),
                          'reference_kind': 'full_legacy_plan_state', 'expected_cheap_admissions': 0,
                          'manual_conditions': raw['fixture']['manual_conditions'], 'max_daily_solvers': 21})
            files[str(path)] = sha(path)
    path = OLD / 'controls_v1/legacy_in_transit_s0.json.gz'
    assert sha(path) == '50a4f0053854bb808b2004cea6a5671c4594255fbe34d4d5a502eaf75c85c184'
    raw = json.loads(gzip.decompress(path.read_bytes()))
    receipt = raw['R9_diagnostics']['0']['investment_receipts'][0]
    assert receipt['step'] == 75 and len(receipt['admitted']) == 24
    cases.append({'id': 'day3_in_transit_batch24_s0', 'observation': raw['fixture']['observation'],
                  'reference_path': str(path), 'reference_kind': 'full_receipt_only',
                  'expected_cheap_admissions': 24,
                  'manual_conditions': {k: v for k, v in raw['fixture'].items() if k != 'observation'},
                  'max_daily_solvers': 26,
                  'limitation': '只存原完整回执和输入，不存在可比较的原内部完整plan/state。'})
    files[str(path)] = sha(path)
    files[str(Path(__file__).resolve())] = sha(__file__)
    pure_obs = {'step': 215, 'day': 8, 'hour': 23, 'player': 0,
                'farms': [{'tiles': [[None for _ in range(10)] for _ in range(10)], 'farmer': [4, 4]} for _ in range(2)],
                'market': {'prices': {'MELON': 100}}}
    output = {'schema': 'r10-p3-validation-fixture-v1', 'at': datetime.now(timezone.utc).isoformat(),
              'cases': cases, 'source_files': files, 'economic_timeout_seconds': 120,
              'pure_observation': pure_obs,
              'pure_offers': [{'name': 'A', 'item': 'MELON', 'position': [0, 0], 'selection_score': 100},
                              {'name': 'B', 'item': 'MELON', 'position': [1, 0], 'selection_score': 90},
                              {'name': 'C', 'item': 'MELON', 'position': [2, 0], 'selection_score': 10}],
              'pure_sequence': [{'step': 215, 'seat': 0, 'offers': ['A', 'B'], 'expect': 'A', 'fail': True},
                                {'step': 215, 'seat': 0, 'offers': ['A', 'B'], 'expect_status': 'ALREADY_ATTEMPTED_THIS_FRAME'},
                                {'step': 216, 'seat': 0, 'offers': ['A', 'B'], 'expect': 'B', 'fail': True},
                                {'step': 217, 'seat': 0, 'offers': ['A', 'B', 'C'], 'expect': 'C', 'fail': True},
                                {'step': 217, 'seat': 0, 'offers': ['A', 'B', 'C'], 'expect_status': 'ALREADY_ATTEMPTED_THIS_FRAME'},
                                {'step': 218, 'seat': 0, 'offers': ['A', 'B', 'C'], 'expect': 'A', 'expected_cycle': 1},
                                {'step': 218, 'seat': 1, 'offers': ['A', 'B'], 'expect': 'A', 'expected_cycle': 0},
                                {'step': 219, 'seat': 0, 'offers': ['A', 'B', 'C'], 'expect': 'A', 'expected_cycle': 1}],
              'new_plan_fields': ['rescue_expert', 'r10_route_feasibility_by_day', 'r10_effective_labor_feasible'],
              'new_receipt_fields': ['r10_rescue', 'r10_future_route'],
              'new_state_fields': ['_r10_rescue_cycles'],
              'receipt_downstream_only_fields': ['market_intents', 'unit_investment_intents'],
              'pure_scope': '人工报价只验证真实生产helper的轮转/原引用/键规则，不作报价、solver或通过许可证据。',
              'status': 'STATIC_NOT_EXECUTED', 'candidate_calls': 0, 'engine_calls': 0}
    assert len(cases) == 5 and sum(c['max_daily_solvers'] for c in cases) == 110
    path = HERE / 'fixture_v1.json'
    assert not path.exists()
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'fixture': str(path), 'sha256': sha(path), 'cases': 5, 'candidate_calls': 0, 'engine_calls': 0}))


if __name__ == '__main__':
    main()
