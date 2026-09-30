"""先检投影和独立证书，再对同一保存日初观测做双席连续官方控制。"""
from copy import deepcopy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
MODEL = HERE.parents[1]
sys.path.insert(0, str(MODEL / 'research/procurement_audit'))
import run_microcases as engine

sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    protocol = json.loads((HERE / 'engineering_protocol.json').read_text())
    assert all(sha(p) == h for p, h in protocol['files'].items())
    out = HERE / 'engineering_once'
    out.mkdir(exist_ok=False)
    core = load(HERE / 'core.py', 'r12_core_test')
    checker = load(HERE / 'checker.py', 'r12_checker_test')
    controls = load(MODEL / 'research/r11_survival_routes/check_deadline_v2.py', 'r12_restore_helpers')
    saved = json.load(gzip.open(MODEL / 'research/r11_survival_routes/capture_once/captured.json.gz', 'rt'))
    cases = [(f"saved_{r['observation']['step']}", r['observation'], r['actions']) for r in saved]
    base = deepcopy(saved[0]['observation'])
    farm = base['farms'][0]
    farm.update(tiles=[[None for _ in range(10)] for _ in range(10)], farmer=[2, 7],
                hands=[[2, 7], [3, 7]], hires_today=2)
    base['private'] = {'seeds': {'WHEAT': 1}, 'shed': {}, 'inventories': [{}, {}, {}]}
    cases.append(('atomic_overrequest', deepcopy(base), [['PLANT', 'WHEAT'], ['PASS'], ['PLANT', 'WHEAT']]))
    crop = engine.RULES._new_plant('WHEAT', 13, 24)
    crop.update(consecutive_unwatered=1, yield_units=0)
    base['farms'][0]['tiles'][7][2] = crop
    cases.append(('water_then_harvest_removes_crop', deepcopy(base), [['WATER'], ['HARVEST'], ['PASS']]))
    cases.append(('dig_then_replant_new_obligation', deepcopy(base), [['DIG'], ['PLANT', 'WHEAT'], ['PASS']]))
    base['farms'][0]['tiles'][7][2] = None
    cases.append(('build_blocks_plant', deepcopy(base), [['BUILD_PASTURE'], ['PLANT', 'WHEAT'], ['PASS']]))
    base['farms'][0]['tiles'][7][2] = 'LOCKED'
    cases.append(('locked_water', deepcopy(base), [['WATER'], ['PLANT', 'WHEAT'], ['PASS']]))
    base['farms'][0]['farmer'] = [0, 0]
    cases.append(('outside_move', deepcopy(base), [['NORTH'], ['PASS'], ['PASS']]))
    checks, projection_rows = {}, []
    unit_calls = 0
    for name, obs, actions in cases:
        before = deepcopy(obs)
        actual = deepcopy(obs)
        own = actual['farms'][actual['player']]
        private = actual['private']
        demand = {}
        for action in actions:
            if action[0] == 'PLANT': demand[action[1]] = demand.get(action[1], 0) + 1
        blocked = {c for c, count in demand.items() if count > private['seeds'].get(c, 0)}
        for uid, action in enumerate(actions):
            applied = ['PASS'] if action[0] == 'PLANT' and action[1] in blocked else action
            engine.RULES._apply_unit_action(own, private, uid, applied, 10, obs['day'], 24, 100)
            unit_calls += 1
        actual['step'] += 1
        actual['hour'] += 1
        predicted = core.r12_project(obs, actions)
        expected = core.r12_problem(actual)
        checks[name] = predicted == expected and obs == before
        projection_rows.append({'name': name, 'predicted': predicted, 'expected': expected, 'passed': checks[name]})
    problem = core.r12_problem(saved[1]['observation'])
    certificate = core.r12_schedule(problem)
    checks['original_complete_certificate'] = checker.r12_check(problem, certificate)['valid']
    bad = deepcopy(certificate)
    nonempty = next(i for i, r in enumerate(bad['routes']) if r)
    bad['routes'][nonempty] = []
    checks['missing_route_rejected'] = not checker.r12_check(problem, bad)['valid']
    bad = deepcopy(certificate)
    bad['problem']['step'] += 1
    checks['different_problem_rejected'] = not checker.r12_check(problem, bad)['valid']
    bad = deepcopy(certificate)
    bad['routes'][nonempty] += [['EAST']] * 30
    checks['overtime_or_outside_rejected'] = not checker.r12_check(problem, bad)['valid']
    bad = deepcopy(certificate)
    water_index = next(i for i, a in enumerate(bad['routes'][nonempty]) if a == ['WATER'])
    bad['routes'][nonempty].insert(water_index, ['WATER'])
    checks['duplicate_service_rejected'] = not checker.r12_check(problem, bad)['valid']
    no_time = deepcopy(problem)
    no_time['step'] = no_time['end']
    checks['unreachable_last_slot_not_certified'] = core.r12_schedule(no_time) is None
    (out / 'projection.json').write_text(json.dumps(projection_rows, ensure_ascii=False, indent=2))
    (out / 'pure_checks.json').write_text(json.dumps({'checks': checks, 'official_unit_function_calls': unit_calls,
        'candidate_calls': 0, 'full_interpreter_steps': 0}, ensure_ascii=False, indent=2))
    assert all(checks.values()), checks

    runs, actual_calls = [], 0
    for seat in (0, 1):
        for label, path in [('R0', MODEL / 'candidates/V125-R0/main.py'), ('R12', HERE / 'prototype.py')]:
            initial = deepcopy(saved[0]['observation'])
            env = controls.restore(initial, seat, mirror=seat == 1)
            mod = load(path, 'r12_continuous_' + label + str(seat))
            steps = []
            for offset in range(24):
                obs = engine.observed(env, seat)
                assert obs['step'] == 360 + offset
                output = mod.agent(obs)
                actual_calls += 1
                pair = [deepcopy(engine.PASS), deepcopy(engine.PASS)]
                pair[seat] = output
                engine.official_step(env, pair)
                after = engine.observed(env, seat)
                assert after['step'] == obs['step'] + 1
                steps.append({'step': obs['step'], 'action': output, 'after': after})
            runs.append({'label': label, 'seat': seat, 'initial': initial, 'steps': steps,
                         'diagnostics': mod.diagnostics()})
    with gzip.open(out / 'continuous_runs.json.gz', 'wt') as f:
        json.dump(runs, f, ensure_ascii=False)
    counts = []
    for run in runs:
        initial = run['initial']['farms'][0]['tiles']
        final = run['steps'][-1]['after']['farms'][run['seat']]['tiles']
        surviving = []
        for y, row in enumerate(initial):
            for x, tile in enumerate(row):
                if isinstance(tile, dict) and tile.get('kind') == 'PLANT' and tile['consecutive_unwatered'] >= 1:
                    after = final[y][x]
                    surviving.append({'pos': [x, y], 'before': tile, 'after': after})
        counts.append({'label': run['label'], 'seat': run['seat'], 'tracked_initial_danger': surviving})
    (out / 'tracked_assets.json').write_text(json.dumps(counts, ensure_ascii=False, indent=2))
    (out / 'summary.json').write_text(json.dumps({'status': 'CONTINUOUS_EXECUTED_REVIEW_REQUIRED',
        'pure_checks_pass': all(checks.values()), 'pure_checks': len(checks),
        'official_unit_function_calls': unit_calls, 'candidate_calls': actual_calls,
        'official_short_steps': actual_calls, 'new_complete_matches': 0,
        'sources_unchanged': all(sha(p) == h for p, h in protocol['files'].items()),
        'scope': '真实保存观测作为人工初态；未恢复历史随机数内部态，不把末态现金或商店当自然收益证据。'}, ensure_ascii=False, indent=2))
    print('PURE_CHECKS_PASS_AND_96_SHORT_STEPS_COMPLETE_REVIEW_REQUIRED')


if __name__ == '__main__':
    main()
