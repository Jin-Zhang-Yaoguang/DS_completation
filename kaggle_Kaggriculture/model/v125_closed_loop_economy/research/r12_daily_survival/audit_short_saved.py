"""只重放R12已保存短控制，逐步核对并使用原官方事件审计器。"""
from copy import deepcopy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
MODEL = HERE.parents[1]
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    protocol = json.loads((HERE / 'short_audit_protocol.json').read_text())
    assert all(sha(p) == h for p, h in protocol['files'].items())
    out = HERE / 'short_saved_audit'
    out.mkdir(exist_ok=False)
    control = load(HERE / 'check_core.py', 'short_restore_control')
    prior = load(MODEL / 'research/r11_survival_routes/check_deadline_v2.py', 'short_restore_prior')
    audit_module = load(MODEL / 'research/mechanism_analysis/analyze_trace.py', 'r12_frozen_audit')
    engine = control.engine
    runs = json.load(gzip.open(HERE / 'engineering_once/continuous_runs.json.gz', 'rt'))
    results = []
    for run in runs:
        seat = run['seat']
        env = prior.restore(run['initial'], seat, mirror=seat == 1)
        adapter = SimpleNamespace(g=SimpleNamespace(interpreter=engine.RULES.interpreter))
        audit = audit_module.Audit(engine.RULES, adapter)
        initial = [audit_module.stock(engine.observed(env, s)['private']) for s in (0, 1)]
        with audit:
            for row in run['steps']:
                step = row['step']
                pair = [deepcopy(engine.PASS), deepcopy(engine.PASS)]
                pair[seat] = deepcopy(row['action'])
                for state, action in zip(env.state, pair):
                    state.action = action
                env.state = adapter.g.interpreter(env.state, env)
                for state in env.state:
                    state.observation.step = step + 1
                assert engine.observed(env, seat) == row['after'], (run['label'], seat, step, 'SAVED_STATE_DRIFT')
        # 原完整总结器需要终局元数据；短场景只输出原事件、真实流量和物料守恒。
        final = [audit_module.stock(engine.observed(env, s)['private']) for s in (0, 1)]
        own_events = [e for e in audit.events if e['seat'] == seat]
        record = {'label': run['label'], 'seat': seat, 'counters': dict(audit.counters[seat]),
                  'flow': {k: dict(v) for k, v in audit.flow[seat].items()},
                  'initial_inventory': dict(initial[seat]), 'final_inventory': dict(final[seat]),
                  'events': own_events, 'all_24_saved_observations_equal': True}
        results.append(record)
    with gzip.open(out / 'events_and_flows.json.gz', 'wt') as f:
        json.dump(results, f, ensure_ascii=False)
    summary = []
    for r in results:
        count = r['counters']
        summary.append({'label': r['label'], 'seat': r['seat'],
            'drought_deaths': count.get('plant_eod_drought_deaths', 0),
            'escapes': count.get('animal_eod_escapes', 0),
            'eod_overflow_events': sum(e['kind'] == 'eod_inventory_drop' for e in r['events']),
            'eod_overflow_quote': sum(e.get('quote_value', 0) for e in r['events'] if e['kind'] == 'eod_inventory_drop'),
            'harvested': r['flow'].get('harvested', {}), 'feed': r['flow'].get('feed', {}),
            'water': r['flow'].get('water', {}), 'fertilize': r['flow'].get('fertilize', {})})
    assert all(sha(p) == h for p, h in protocol['files'].items())
    (out / 'summary.json').write_text(json.dumps({'status': 'SAVED_SHORT_EVENTS_VERIFIED', 'rows': summary,
        'saved_interpreter_steps': 96, 'candidate_calls': 0, 'new_matches': 0,
        'all_saved_observations_equal': True, 'source_files_unchanged': True}, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
