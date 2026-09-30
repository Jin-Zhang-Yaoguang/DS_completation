"""R11末时槽机制：原观测短反事实及两席人工控制，非完整对局。"""
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


def load(path, label):
    spec = importlib.util.spec_from_file_location(label, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def restore(obs, seat, mirror=False):
    env, _ = engine.setup(seat, 'fully_funded_control')
    farms = deepcopy(obs['farms'])
    if mirror:
        farms = farms[::-1]
    public = env.state[0].observation
    public.farms = farms
    public.market = engine.structify(deepcopy(obs['market']))
    public.town = engine.structify(deepcopy(obs['town']))
    for s in env.state:
        s.observation.farms = public.farms
        s.observation.market = public.market
        s.observation.town = public.town
        for key in ('day', 'hour', 'step'):
            setattr(s.observation, key, obs[key])
    env.state[seat].observation.private = engine.structify(deepcopy(obs['private']))
    return env


def execute(obs, seat, candidate, steps, mirror=False):
    env = restore(obs, seat, mirror)
    mod = load(candidate, 'r11_micro_' + str(seat))
    rows = []
    for _ in range(steps):
        current = engine.observed(env, seat)
        assert current['step'] == obs['step'] + len(rows)
        result = mod.agent(current)
        pair = [deepcopy(engine.PASS), deepcopy(engine.PASS)]
        pair[seat] = result
        engine.official_step(env, pair)
        assert engine.observed(env, seat)['step'] == current['step'] + 1
        rows.append({'step': current['step'], 'action': result,
                     'after': engine.observed(env, seat)})
    return {'seat': seat, 'initial': obs, 'rows': rows,
            'final': engine.observed(env, seat)}


def main():
    protocol = json.loads((HERE / 'micro_protocol_v2.json').read_text())
    assert all(sha(p) == h for p, h in protocol['files'].items())
    out = HERE / 'micro_once_v2'
    out.mkdir(exist_ok=False)
    raw = json.load(gzip.open(HERE / 'capture_once/captured.json.gz', 'rt'))
    observed = raw[22]['observation']
    parent = MODEL / 'candidates/V125-R0/main.py'
    child = HERE / 'prototype.py'
    checks, runs = {}, []
    for seat in (0, 1):
        for name, path in [('R0', parent), ('R11', child)]:
            result = execute(observed, seat, path, 2, mirror=seat == 1)
            result['label'] = name + '_saved_counterfactual'
            runs.append(result)
            tile = result['final']['farms'][seat]['tiles'][7][2]
            checks[f'{seat}_{name}_saved_expected'] = (
                tile.get('kind') == ('WEED' if name == 'R0' else 'PLANT'))

        # 冻结人工几何：无货物、无动物或种子，唯一临死小麦；R0和R11同初态。
        base = deepcopy(observed)
        for f in base['farms']:
            f.update(tiles=[[None for _ in range(10)] for _ in range(10)],
                     farmer=[2, 7], hands=[], hires_today=0, money=0,
                     unlocked_quadrants=['NW', 'NE', 'SW', 'SE'])
        base['private'] = {'shed': {}, 'seeds': {}, 'inventories': [{}]}
        base.update(hour=23, step=15 * 24 + 23)
        crop = engine.RULES._new_plant('WHEAT', 13, 24)
        crop.update(consecutive_unwatered=1, yield_units=1)
        base['farms'][0]['tiles'][7][2] = crop
        for name, path in [('R0', parent), ('R11', child)]:
            result = execute(base, seat, path, 1, mirror=seat == 1)
            result['label'] = name + '_last_slot_control'
            runs.append(result)
            checks[f'{seat}_{name}_last_slot'] = result['rows'][0]['action']['farmer'] == (
                ['PASS'] if name == 'R0' else ['WATER'])
            checks[f'{seat}_{name}_last_slot_state'] = result['final']['farms'][seat]['tiles'][7][2]['kind'] == (
                'WEED' if name == 'R0' else 'PLANT')

    # 同24个保存状态内部只读控制，经营与市场输入相同时保持一致。
    controls = []
    for rec in raw:
        obs = rec['observation']
        modules = [load(parent, 'r0_control'), load(child, 'r11_control')]
        derived = []
        for mod in modules:
            st = mod.new_state(obs)
            plan = mod.economic_plan(obs, st)
            tasks = mod.make_tasks(obs, st, plan)
            derived.append((plan, tasks))
        assert derived[0][0] == derived[1][0]
        assert len(derived[0][1]) == len(derived[1][1])
        changed = []
        for a, b in zip(derived[0][1], derived[1][1]):
            if a != b:
                assert a['ops'] == [['WATER']] and a['deadline'] == 21 and b['deadline'] == 23
                assert {k: v for k, v in a.items() if k != 'deadline'} == {k: v for k, v in b.items() if k != 'deadline'}
                changed.append(a['pos'])
        controls.append({'step': obs['step'], 'changed_water_deadlines': changed})
    checks['24_same_state_economic_and_other_tasks_unchanged'] = True
    with gzip.open(out / 'runs.json.gz', 'wt') as f:
        json.dump(runs, f, ensure_ascii=False)
    (out / 'controls.json').write_text(json.dumps(controls, ensure_ascii=False, indent=2))
    (out / 'summary.json').write_text(json.dumps({
        'status': 'PASS' if all(checks.values()) else 'FAIL', 'checks': checks,
        'full_agent_calls': 12, 'official_interpreter_steps': 12,
        'internal_same_state_plans': 48, 'new_matches': 0,
        'scope': '保存自然观测的两步分支与双席末帧人工场景；不是独立自然比赛或性能测量。',
        'files_unchanged': all(sha(p) == h for p, h in protocol['files'].items()),
    }, ensure_ascii=False, indent=2))
    assert all(checks.values()), checks
    print('PASS: 13 checks, 12 short steps, 48 same-state internal plans')


if __name__ == '__main__':
    main()
