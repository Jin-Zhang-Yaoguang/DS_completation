"""超过旧劳动容量的人工组合，预先固定规模后验证完整路线。"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
from test_scheduler import problem
from scheduler import schedule_day
from checker import check_day

HERE = Path(__file__).resolve().parent
positions = sorted([(x, y) for y in range(10) for x in range(10)
                    if (x, y) not in ((4, 4), (5, 4), (4, 5), (5, 5))],
                   key=lambda p: (abs(p[0] - 4) + abs(p[1] - 4), p[1], p[0]))
fixtures = {f'{n}_strawberries': problem(['STRAWBERRY'] * n, positions[:n], 10)
            for n in (16, 32, 48, 64)}
fixtures['sixteen_cows_sixteen_strawberries'] = problem(
    ['COW'] * 16 + ['STRAWBERRY'] * 16, positions[:32], 10, buy=16)
rows = []
for name, p in fixtures.items():
    c = schedule_day(p, 12)
    checked = check_day(p, c)
    rows.append({'name': name, 'problem': p, 'certificate': c, 'checker': checked,
                 'legacy_capacity': 298, 'legacy_failed': p['legacy_work'] > 298})
out = {'created_at_utc': datetime.now(timezone.utc).isoformat(),
       'role': 'artificial pressure controls, not actual observed portfolio or strength evidence',
       'source_hashes': {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
                         for name in ('pressure_fixture_probe.py', 'test_scheduler.py', 'calendar_compiler.py', 'scheduler.py', 'checker.py')},
       'scheduler_calls': 5, 'checker_calls': 5, 'whole_candidate_calls': 0,
       'official_engine_calls': 0, 'new_complete_matches': 0, 'rows': rows}
target = HERE / ('pressure_fixtures_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
target.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'path': str(target), 'rows': [{'name': r['name'], 'legacy_work': r['problem']['legacy_work'],
                  'legacy_failed': r['legacy_failed'], 'status': r['certificate']['status'],
                  'valid': r['checker']['valid'], 'errors': r['checker']['errors']} for r in rows]}, ensure_ascii=False))
