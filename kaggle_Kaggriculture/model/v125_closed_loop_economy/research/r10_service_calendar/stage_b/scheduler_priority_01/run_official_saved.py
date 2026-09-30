"""将已保存新证书在双席人工条件中执行；不再调用求解器或候选。"""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import traceback

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    frozen = json.loads((HERE / 'official_protocol.json').read_text())
    assert all(sha(p) == h for p, h in frozen['files'].items())
    out = HERE / 'official_once'
    out.mkdir(exist_ok=False)
    spec = importlib.util.spec_from_file_location('saved_control', BASE / 'test_official_controls.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    suite = mod.Suite(out, frozen)
    capture = json.loads(Path(frozen['capture']).read_text())
    p = capture['problem']
    cert = json.loads((HERE / 'run_once/certificate.json').read_text())
    checked = json.loads((HERE / 'run_once/checker.json').read_text())
    assert cert['status'] == 'FEASIBLE' and checked['valid']
    errors = []
    for seat in (0, 1):
        suite.start('natural_problem_saved_certificate', seat, 'artificial_future_day_saved_certificate')
        suite.active.update(problem=p, certificate=cert, checker=checked, input_calendars=[],
                            limits='注入预测第21日资产和100000现金；不证明自然可达。无完整翌日逐资产预测对照。')
        env = suite.env({'day': p['day'], 'tiles': p['start_farm_tiles'], 'shed': p['start_shed']}, seat)
        farm = env.state[0].observation.farms[seat]
        farm['unlocked_quadrants'] = ['NW', 'NE', 'SW', 'SE']
        farm['tiles'] = [[None for _ in range(10)] for _ in range(10)]
        for entry in p['start_farm_tiles']:
            x, y = entry['pos']
            farm['tiles'][y][x] = copy.deepcopy(entry['tile'])
        suite.active['initial'] = mod.state_snapshot(env, seat)
        actions = {h: {} for h in range(24)}
        for a in cert['actions']:
            actions[a['hour']][a['unit']] = a['action']
        markets = {a['hour']: a['orders'] for a in cert['markets']}
        observer = mod.Observer(suite.rules, env, seat)
        try:
            with observer:
                for hour in range(24):
                    units = actions[hour]
                    suite.check('worker_count_' + str(hour), len(units) == len(farm['hands']) + 1)
                    suite.step(env, seat, {'farmer': units[0], 'hands': [units[u] for u in range(1, len(units))], 'market': markets[hour]})
                suite.verify_certificate(p, cert, checked, observer, env, seat)
        except Exception as exc:
            errors.append({'seat': seat, 'error': str(exc), 'traceback': traceback.format_exc()})
        finally:
            suite.attach(observer, env, seat)
            suite.save()
        if errors:
            break
    drift = [p for p, h in frozen['files'].items() if sha(p) != h]
    summary = {'status': 'OFFICIAL_SAVED_CERTIFICATE_PASS' if not errors and not drift and len(suite.results) == 2 else 'FAIL',
               'counts': dict(suite.counts), 'results': suite.results, 'errors': errors, 'drift': drift,
               'scheduler_calls': 0, 'candidate_calls': 0, 'new_complete_matches': 0}
    (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': summary['status'], 'counts': summary['counts'], 'errors': errors}, ensure_ascii=False))
    return 0 if summary['status'] == 'OFFICIAL_SAVED_CERTIFICATE_PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
