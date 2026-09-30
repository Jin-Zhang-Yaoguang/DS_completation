#!/usr/bin/env python3
"""一次人工初态入口诊断，不推进引擎、不修改候选函数。"""
import contextlib, copy, gzip, hashlib, io, json, os, signal, sys, tarfile, traceback
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
SOURCE = ROOT / '.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v26_f_base'

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def dump(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def main():
    sys.dont_write_bytecode = True
    if (HERE / 'freeze.json').exists():
        raise RuntimeError('REFUSE_RETRY_OR_OVERWRITE')
    dist = SOURCE / 'dist/main.py'
    archive = SOURCE / 'submission.tar.gz'
    expected = 'f22026c876254285cfb2bd2f301f2b44856584ad40093c3580330e4647948c8e'
    paths = [Path(__file__).resolve(), dist, SOURCE / 'variant_a30.py', archive,
             ROOT / '.venv/lib/python3.12/site-packages/kaggle_environments/agent.py',
             ROOT / '.venv/lib/python3.12/site-packages/kaggle_environments/envs/kaggriculture/kaggriculture.py',
             ROOT / '.venv/lib/python3.12/site-packages/kaggle_environments/envs/kaggriculture/kaggriculture.json']
    guards = {str(p): sha(p) for p in paths}
    assert sha(dist) == sha(SOURCE / 'variant_a30.py') == expected
    with tarfile.open(archive) as tf:
        assert hashlib.sha256(tf.extractfile('main.py').read()).hexdigest() == expected
    dump(HERE / 'freeze.json', {'created_at_utc': datetime.now(timezone.utc).isoformat(), 'files': guards,
        'source_sha256': expected, 'requested_candidate_calls': 1, 'requested_engine_steps': 0,
        'new_complete_matches': 0, 'profile_target': 'exact _V19_CORE code object, call event',
        'loader': 'official get_last_callable; no function replacement',
        'parameter_environment_sha256': {k: hashlib.sha256(v.encode()).hexdigest() for k, v in os.environ.items() if k == 'MM_PARAMS'}})
    calls = resets = initialized = 0
    events = []
    captured = io.StringIO()
    try:
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            from kaggle_environments import make
            from kaggle_environments.agent import get_last_callable
            env = make('kaggriculture', configuration={'seed': 1950905001, 'episodeSteps': 720}, debug=False)
            initialized = 1
            env.reset(2)
            resets = 1
            obs = copy.deepcopy(dict(env._Environment__get_shared_state(0).observation))
            cfg = dict(env.configuration)
            cfg['seed'] = None
            cfg['__raw_path__'] = str(dist)
            original_obs_hash = digest(obs)
            assert obs['step'] == obs['day'] == obs['hour'] == 0 and 'seed' not in obs
            entry = get_last_callable(dist.read_text(), path=str(dist))
            ns = entry.__globals__
            target = ns['_V19_CORE'].__code__
            before = {'actions_is_F': ns['_ACTIONS'] is ns['_F_ACTIONS'],
                      'actions_is_V120': ns['_ACTIONS'] is ns['_V120_DISTILLED_ROUTE'],
                      'actions_sha256': digest(ns['_ACTIONS']), 'F_sha256': digest(ns['_F_ACTIONS']),
                      'V120_sha256': digest(ns['_V120_DISTILLED_ROUTE'])}
            def profiler(frame, event, arg):
                if event == 'call' and frame.f_code is target:
                    g = frame.f_globals
                    events.append({'function': frame.f_code.co_name, 'first_line': frame.f_code.co_firstlineno,
                        'actions_is_F': g['_ACTIONS'] is g['_F_ACTIONS'],
                        'actions_is_V120': g['_ACTIONS'] is g['_V120_DISTILLED_ROUTE'],
                        'actions_sha256': digest(g['_ACTIONS']), 'observation_step': frame.f_locals['obs']['step']})
            oldprofile = sys.getprofile()
            def alarm(*_):
                raise TimeoutError('single diagnostic call exceeded 10 seconds')
            oldalarm = signal.signal(signal.SIGALRM, alarm)
            signal.setitimer(signal.ITIMER_REAL, 10)
            sys.setprofile(profiler)
            calls = 1
            try:
                action = entry(obs, cfg)
            finally:
                sys.setprofile(oldprofile)
                signal.setitimer(signal.ITIMER_REAL, 0)
                signal.signal(signal.SIGALRM, oldalarm)
            after = {'actions_is_F': ns['_ACTIONS'] is ns['_F_ACTIONS'],
                     'actions_is_V120': ns['_ACTIONS'] is ns['_V120_DISTILLED_ROUTE'],
                     'actions_sha256': digest(ns['_ACTIONS'])}
            assert len(events) == 1 and events[0]['actions_is_V120'] and not events[0]['actions_is_F']
            assert before['actions_is_F'] and after['actions_is_V120']
            assert digest(obs) == original_obs_hash, 'CANDIDATE_MUTATED_INPUT_OBSERVATION'
            assert all(sha(p) == value for p, value in guards.items())
            result = {'status': 'DIAGNOSTIC_COMPLETE', 'source_sha256': expected,
                'entrypoint': {'name': entry.__name__, 'line': entry.__code__.co_firstlineno},
                'before_candidate_call': before, 'profile_events': events, 'after_candidate_call': after,
                'action': action, 'calls': {'whole_candidate': calls, 'official_environment_objects': initialized,
                    'explicit_reset_calls': resets, 'official_interpreter_steps': 0, 'new_complete_matches': 0},
                'initial_observation_sha256': digest(obs), 'configuration_sha256': digest(cfg),
                'original_files_unchanged': True, 'performance_evidence': False,
                'limitations': '仅人工day0路径可达性；不是完整对局、强度、线上提交身份或性能验证'}
            dump(HERE / 'result.json', result)
            dump(HERE / 'initial_observation.json', obs)
    except Exception as exc:
        dump(HERE / 'failure.json', {'error': str(exc), 'traceback': traceback.format_exc(), 'candidate_calls': calls,
            'official_environment_objects': initialized, 'explicit_reset_calls': resets, 'engine_steps': 0,
            'new_complete_matches': 0, 'profile_events': events})
        raise
    finally:
        (HERE / 'captured_output.log').write_text(captured.getvalue())
    dump(HERE / 'delivery_manifest.json', {'files': {str(p): sha(p) for p in HERE.iterdir() if p.is_file()},
        'candidate_calls': calls, 'engine_steps': 0, 'new_complete_matches': 0})
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
