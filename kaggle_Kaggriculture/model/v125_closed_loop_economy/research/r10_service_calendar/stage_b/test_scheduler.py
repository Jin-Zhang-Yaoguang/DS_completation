"""小型组合调度控制：只调用纯函数，无候选或比赛引擎。"""
import copy
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from calendar_compiler import project_calendar_with_services, compile_day_problem
from scheduler import schedule_day, canonical_sha
from checker import check_day

HERE = Path(__file__).resolve().parent


def make_tile(item, born=0):
    if item in ('COW', 'SHEEP', 'GOOSE'):
        return {'kind': 'COOP' if item == 'GOOSE' else 'PASTURE', 'animal': item,
                'placed_day': born, 'yield_units': 0, 'fed_today': False,
                'cared_today': False, 'consecutive_unfed': 0,
                'fertilizer_available': False, 'pending_care_bonus': 0}
    last = {'WHEAT': 4, 'CARROT': 3, 'TOMATO': 8, 'STRAWBERRY': 10, 'MELON': 12}[item]
    recurring = item in ('TOMATO', 'STRAWBERRY')
    return {'kind': 'PLANT', 'crop': item, 'planted_day': born,
            'yield_units': 0 if recurring else 1, 'watered_today': False,
            'consecutive_unwatered': 1, 'fertilized_until_day': -1,
            'max_lifespan_step': -1 if recurring else (born + last + 1) * 24}


def problem(items, positions, day, wheat=0, buy=0, other=None):
    calendars = [project_calendar_with_services(make_tile(item), 0, position=pos)
                 for item, pos in zip(items, positions)]
    return compile_day_problem(calendars, day, 0, {'WHEAT': wheat, **(other or {})},
                               {'FERTILIZER': 12},
                               {'qty': buy, 'estimated_cash': 27 * buy,
                                'order_hour': 0, 'available_from_hour': 1},
                               sum(c['work'].get(day, 0) for c in calendars), 376)


def main():
    fixtures = json.loads((HERE / 'compiler_examples.json').read_text())
    adjacent = [(3, 4), (3, 3), (4, 3), (5, 3), (6, 3), (6, 4),
                (6, 5), (6, 6), (5, 6), (4, 6), (3, 6), (3, 5)]
    fixtures.update({
        'twelve_cows_full_service_buy': problem(['COW'] * 12, adjacent, 8, buy=12),
        'six_cows_stock_and_buy': problem(['COW'] * 6, adjacent[:6], 8, wheat=2, buy=4),
        'twelve_melons_harvest_water_delivery': problem(['MELON'] * 12, adjacent, 10),
        'mixed_assets_shared_workers': problem(['COW', 'SHEEP', 'GOOSE', 'STRAWBERRY', 'TOMATO', 'MELON'], adjacent[:6], 10, buy=3),
        'near_full_shed_with_later_sales': problem(['COW'] * 4, adjacent[:4], 8, wheat=4, other={'CARROT': 95}),
        'last_day_animals_delivery': problem(['COW', 'SHEEP', 'GOOSE'], adjacent[:3], 29),
        'four_far_corners_water': problem(['MELON'] * 4, [(0, 0), (9, 0), (0, 9), (9, 9)], 2),
        'four_near_wheat_harvest': problem(['WHEAT'] * 4, adjacent[:4], 4),
    })
    results = []
    for name, p in fixtures.items():
        for hands in (0, 1, 3, 9, 10, 12):
            before = canonical_sha(p)
            started = time.perf_counter()
            cert = schedule_day(p, hands)
            elapsed = time.perf_counter() - started
            checked = check_day(p, cert) if cert['status'] == 'FEASIBLE' else None
            results.append({'fixture': name, 'n_hands': hands, 'status': cert['status'],
                            'reason': cert['reason'], 'elapsed_seconds': elapsed,
                            'problem_unchanged': before == canonical_sha(p),
                            'valid': checked['valid'] if checked else None,
                            'errors': checked['errors'] if checked else [],
                            'service_count': len(p['services']),
                            'completed_services': len(cert['scheduled_service_ids'])})
    # 明确无效/超范围输入必须维持拒绝；不把构造失败声称为无解证明。
    checks = {'all_feasible_certificates_independently_valid': all(r['valid'] is not False for r in results),
              'inputs_unchanged': all(r['problem_unchanged'] for r in results),
              'all_supported_twelve_hand_examples_constructed': all(r['status'] == 'FEASIBLE' for r in results if r['n_hands'] == 12)}
    invalid = copy.deepcopy(fixtures['cow_day8']); invalid['status'] = 'UNSUPPORTED'
    checks['unsupported_never_admitted'] = schedule_day(invalid, 12)['status'] == 'NO_CERTIFICATE'
    checks['bool_hand_count_rejected'] = schedule_day(fixtures['cow_day8'], True)['status'] == 'NO_CERTIFICATE'
    urgent = copy.deepcopy(fixtures['four_far_corners_water'])
    for service in urgent['services']:
        service['deadline'] = 1
    checks['unreachable_deadlines_rejected'] = schedule_day(urgent, 12)['status'] == 'NO_CERTIFICATE'
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    out = {'created_at_utc': datetime.now(timezone.utc).isoformat(),
           'scope': 'pure scheduler/compiler/checker integration only',
           'fixture_count': len(fixtures), 'portfolio_schedules': len(results),
           'extra_negative_schedules': 3, 'whole_candidate_calls': 0,
           'official_engine_calls': 0, 'new_complete_matches': 0,
           'checks': checks, 'results': results,
           'source_hashes': {name: sha(HERE / name) for name in ('scheduler.py', 'calendar_compiler.py', 'checker.py', 'test_scheduler.py')}}
    path = HERE / ('scheduler_tests_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'result': str(path), 'checks': checks, 'counts': {s: sum(r['status'] == s for r in results) for s in ('FEASIBLE', 'NO_CERTIFICATE')}, 'false_certificates': [r for r in results if r['valid'] is False]}, ensure_ascii=False))
    return 0 if all(checks.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
