"""唯一预登记的人工连续轨迹；使用原观察器，候选计时中不加监控。"""
from pathlib import Path
from datetime import datetime, timezone
from copy import deepcopy
import argparse
import hashlib
import importlib.util
import json
import traceback


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--freeze', type=Path, required=True)
    args = ap.parse_args()
    raw = args.freeze.read_bytes()
    f = json.loads(raw)
    assert f['root_execution_release'] is True
    assert f['schema'] == 'p3-continuous-official-controls-v1'
    assert all(sha(path) == wanted for path, wanted in f['files'].items())
    assert f['files'][str(Path(__file__).resolve())] == sha(__file__)
    spec = importlib.util.spec_from_file_location('p3_frozen_entry_controls', f['helper_path'])
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    out = Path(f['output_path'])
    out.mkdir(parents=True, exist_ok=False)
    controls = helper.Controls(out, f)
    errors, outcomes = [], []
    for case in f['cases']:
        controls.active = {'id': case['id'], 'fixture': case, 'checks': {}, 'rows': [],
                           'scope': '人工完整入口及连续官方短轨迹，不是自然比赛'}
        observer, ns, env = None, None, None
        try:
            assert all(sha(path) == wanted for path, wanted in f['files'].items())
            ns, entry = controls.namespace('R10')
            controls.check('default_bounded_rescue_mode', ns['PARAMS']['r10_route_mode'] == 'bounded_future_failure_rescue')
            env = controls.environment(case['observation'])
            seat = case['seat']
            observer = controls.base.Observer(controls.rules, env, seat)
            with observer:
                for offset in range(case['decision_count']):
                    before = controls.observed(env, seat)
                    controls.check('consecutive_clock_' + str(offset), before['step'] == case['observation']['step'] + offset)
                    # Observer只包装官方规则函数，不包候选；其开销在agent计时之外。
                    action = controls.agent('P3', entry, before)
                    state = ns['_STATES'][seat]
                    receipt = deepcopy(state['investment_receipts'][-1])
                    rescue, counts = receipt['r10_rescue'], receipt['r10_future_route']['counts']
                    controls.check('explicit_attempt_count_' + str(offset),
                                   counts.get('route_attempts') == 1 if rescue['route_attempted'] else
                                   not rescue['approved'] and all(v == 0 for v in counts.values()))
                    controls.check('single_rescue_attempt_' + str(offset), counts.get('route_attempts', 0) <= 1)
                    controls.check('full_future_day_bound_' + str(offset),
                                   counts.get('scheduler_calls', 0) <= 29 - before['day'] and
                                   counts.get('checker_calls', 0) <= 29 - before['day'])
                    row = {'step': before['step'], 'before': before, 'action': action, 'receipt': receipt,
                           'unit_event_start': len(observer.unit_events), 'market_event_start': len(observer.market_events)}
                    controls.active['rows'].append(row)
                    controls.step(env, seat, action)
                    row['after'] = controls.observed(env, seat)
                    row['unit_event_end'] = len(observer.unit_events)
                    row['market_event_end'] = len(observer.market_events)
                    controls.check('official_step_advanced_' + str(offset), row['after']['step'] == before['step'] + 1)
                    controls.check('official_remains_active_' + str(offset), all(s.status == 'ACTIVE' for s in env.state))
            rows = controls.active['rows']
            attempted = [r for r in rows if r['receipt']['r10_rescue']['route_attempted']]
            approved = [r for r in rows if r['receipt']['r10_rescue']['approved']]
            outcome = {'id': case['id'], 'completed_steps': len(rows),
                       'rescue_attempts': len(attempted), 'approved_rescues': len(approved),
                       'scheduler_calls': sum(r['receipt']['r10_future_route']['counts'].get('scheduler_calls', 0) for r in rows),
                       'checker_calls': sum(r['receipt']['r10_future_route']['counts'].get('checker_calls', 0) for r in rows),
                       'first_approved_step': approved[0]['step'] if approved else None,
                       'max_entry_seconds': max(t['seconds'] for t in controls.active['call_times']),
                       'final_cash': rows[-1]['after']['farms'][seat]['money'],
                       'successful_rescue_path_status': 'OBSERVED_REQUIRES_EXECUTION_ATTRIBUTION' if approved else 'NOT_OBSERVED'}
            outcomes.append(outcome)
        except BaseException as exc:
            error = {'case': case['id'], 'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
            errors.append(error)
            controls.active['error'] = error
        finally:
            if observer is not None:
                controls.active.update(unit_events=observer.unit_events, market_events=observer.market_events,
                                       hires=observer.hire_events, eod=observer.eod_events)
            if ns is not None:
                controls.active['diagnostics'] = ns['diagnostics']()
            if env is not None:
                controls.active['final'] = controls.observed(env, case['seat'])
            controls.save()
        print(json.dumps({'case': case['id'], 'counts': dict(controls.counts), 'errors': len(errors),
                          'outcome': outcomes[-1] if outcomes and outcomes[-1]['id'] == case['id'] else None}, ensure_ascii=False), flush=True)
    drift = [p for p, h in f['files'].items() if sha(p) != h]
    if args.freeze.read_bytes() != raw:
        drift.append(str(args.freeze))
    overruns = {k: {'actual': controls.counts[k], 'max': n} for k, n in f['maximum_calls'].items() if controls.counts[k] > n}
    complete = len(outcomes) == 2 and all(r['completed_steps'] == 72 for r in outcomes)
    summary = {'schema': 'p3-continuous-official-result-v1', 'created_at_utc': datetime.now(timezone.utc).isoformat(),
               'status': 'CONTINUOUS_ENGINEERING_PASS_MECHANISM_REVIEW_REQUIRED' if complete and not(errors or drift or overruns) else 'FAILED',
               'freeze_sha256': hashlib.sha256(raw).hexdigest(), 'source_sha256': f['source_sha256'],
               'counts': dict(controls.counts), 'outcomes': outcomes, 'records': controls.results,
               'errors': errors, 'source_drift': drift, 'count_overruns': overruns,
               'new_complete_matches': 0, 'new_seeds_opened': False, 'gold_status': 'NOT_GOLD'}
    (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'summary': str(out / 'summary.json'), 'status': summary['status']}, ensure_ascii=False))
    return int(summary['status'] == 'FAILED')


if __name__ == '__main__':
    raise SystemExit(main())
