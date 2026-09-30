"""事前冻结R12保活主指标；只读取原动作审计，缺证据拒绝通过。"""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL = HERE.parents[1]
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def aggregate(rows):
    assert rows
    keys = ('deaths', 'plants', 'plant_days', 'first_water', 'first_observed',
            'escapes', 'animals', 'animal_days', 'overflow_quote', 'mature_quote', 'fert_quote')
    return {k: sum(r[k] for r in rows) for k in keys}


def judge(parent, child):
    required = ('plants', 'plant_days', 'first_observed', 'animals', 'animal_days')
    if any(parent[k] <= 0 or child[k] <= 0 for k in required) or parent['deaths'] <= 0:
        return {'status': 'PENDING_DENOMINATOR', 'primary_pass': False, 'guard_pass': False}
    primary = 5 * child['deaths'] <= 4 * parent['deaths']
    guards = {
        'death_per_plant_not_worse': child['deaths'] * parent['plants'] <= parent['deaths'] * child['plants'],
        'death_per_plant_day_not_worse': child['deaths'] * parent['plant_days'] <= parent['deaths'] * child['plant_days'],
        'first_water_at_least_99pct': 100 * child['first_water'] >= 99 * child['first_observed'],
        'first_water_not_worse': child['first_water'] * parent['first_observed'] >= parent['first_water'] * child['first_observed'],
        'zero_escape': child['escapes'] == 0,
        'overflow_increase_at_most_10pct': 10 * child['overflow_quote'] <= 11 * parent['overflow_quote'],
        'mature_residual_increase_at_most_10pct': 10 * child['mature_quote'] <= 11 * parent['mature_quote'],
        'fert_residual_increase_at_most_10pct': 10 * child['fert_quote'] <= 11 * parent['fert_quote'],
    }
    return {'status': 'NUMERIC_COMPLETE', 'primary_pass': primary,
            'relative_death_reduction': 1 - child['deaths'] / parent['deaths'],
            'guards': guards, 'guard_pass': all(guards.values())}


def main():
    plan = json.loads((HERE / 'frozen_bundle.json').read_text())
    assert all(sha(p) == h for p, h in plan['source_files'].items())
    out = HERE / 'fresh_mechanism_assessment'
    out.mkdir(exist_ok=False)
    spec = importlib.util.spec_from_file_location('r11_g1_source', MODEL / 'evaluation/summarize_g1.py')
    g1 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g1)
    files, rows, seen = {}, [], set()

    def read(p):
        raw = Path(p).read_bytes()
        files[str(Path(p).resolve())] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw)

    for job in plan['jobs']:
        run = Path(job['output'])
        manifest = read(run / 'run_manifest.json')
        raw = (run / 'games.jsonl').read_bytes()
        files[str(run / 'games.jsonl')] = hashlib.sha256(raw).hexdigest()
        games = [json.loads(x) for x in raw.splitlines() if x.strip()]
        assert len(games) == 6
        for game in games:
            key = (job['candidate_id'], job['opponent_label'], game['seed'], game['candidate_seat'])
            assert key not in seen
            seen.add(key)
            directory = HERE / 'fresh_saved_audit' / run.name / f"seed{game['seed']}_seat{game['candidate_seat']}"
            audit = read(directory / 'audit_manifest.json')
            assert audit['candidate_entry_sha256'] == job['entry_sha256']
            analysis = read(directory / 'analysis.json')
            validation = read(directory / 'validation.json')
            assert validation['saved_actions_replayed'] == 719 and validation['agent_calls'] == 0
            for name, value in validation['files'].items():
                assert sha(directory / name) == value
                files[str(directory / name)] = value
            metrics = g1.game_metrics(game, manifest, run, directory)
            own = analysis['seats'][game['candidate_seat']]
            assert own['all_inventory_residual_zero']
            n = own['denominators']
            rows.append(dict(candidate_id=key[0], opponent=key[1], seed=key[2], seat=key[3],
                deaths=n['plant_eod_drought_deaths'], plants=n['plantings_all'], plant_days=n['plant_eod_exposures'],
                first_water=n['planting_day_watered'], first_observed=n['planting_day_eod_observed'],
                escapes=n['animal_eod_escapes'], animals=n['animal_placed'], animal_days=n['animal_eod_exposures'],
                overflow_quote=own['overflow']['eod_quote_value'], mature_quote=own['terminal_assets']['mature_quote_value'],
                fert_quote=own['terminal_assets']['uncollected_fertilizer_quote_value'],
                numeric_G1_companions=metrics))
    expected = {(c, o, s, t) for c in [plan['candidate']] + plan['references']
                for o in plan['opponents'] for s in plan['seeds'] for t in plan['seats']}
    assert seen == expected and len(rows) == 24
    groups = []
    for opponent in plan['opponents']:
        subset = [r for r in rows if r['opponent'] == opponent]
        parent = aggregate([r for r in subset if r['candidate_id'] == 'V125-R0'])
        child = aggregate([r for r in subset if r['candidate_id'] == 'V125-R12'])
        decision = judge(parent, child)
        seats = []
        for seat in plan['seats']:
            a = aggregate([r for r in subset if r['candidate_id'] == 'V125-R0' and r['seat'] == seat])
            b = aggregate([r for r in subset if r['candidate_id'] == 'V125-R12' and r['seat'] == seat])
            seats.append({'seat': seat, 'parent': a, 'child': b, 'deaths_nonincrease': b['deaths'] <= a['deaths']})
        decision['primary_pass'] = decision['primary_pass'] and all(x['deaths_nonincrease'] for x in seats)
        action_ok = all(r['numeric_G1_companions']['action_validity']['status'] == 'PASS'
                        for r in subset if r['candidate_id'] == 'V125-R12')
        decision['action_validity_pass'] = action_ok
        decision['guard_pass'] = decision['guard_pass'] and action_ok
        groups.append({'opponent': opponent, 'parent': parent, 'child': child, 'seats': seats, **decision})
    assert all(sha(p) == h for p, h in files.items())
    assert all(sha(p) == h for p, h in plan['source_files'].items())
    result = {'data_integrity_pass': True, 'groups': groups, 'per_game': rows,
              'primary_mechanism_pass': all(g['primary_pass'] for g in groups),
              'companion_guard_pass': all(g['guard_pass'] for g in groups),
              'candidate_calls': 0, 'engine_steps': 0, 'new_matches': 0,
              'formal_G0_G5': 'NOT_ASSESSED', 'qualification': '开发主机制及守护线；强度另判，正式门仍未通过。'}
    (out / 'assessment.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    (out / 'manifest.json').write_text(json.dumps({'sources': files, 'assessor_sha256': sha(__file__)}, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k not in ('per_game', 'groups')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
