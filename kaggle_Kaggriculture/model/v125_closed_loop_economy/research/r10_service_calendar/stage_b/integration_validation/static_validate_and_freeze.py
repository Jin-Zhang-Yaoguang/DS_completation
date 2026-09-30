"""仅校验JSON、AST和人工profile小函数；不导入候选或官方引擎。"""
import ast
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL = next(p for p in HERE.parents if p.name == 'v125_closed_loop_economy')
ROOT = next(p for p in HERE.parents if (p / '.venv').exists())


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    source_freeze = HERE.parent / 'engineering_source_freeze.json'
    assert sha(source_freeze) == '2ed3aaf4b7fc4627effdfa7ef115594077dbcceefa31e439ea6687d39e69dbdc'
    sources = json.loads(source_freeze.read_bytes())['files']
    for p, expected in sources.items(): assert sha(p) == expected, p
    fx = HERE / 'fixtures_v1.json'; ex = HERE / 'executor_fixtures_v1.json'
    assert sha(fx) == '002242ff38a0d9e4feb489782ab8cbf17e159bdb20b00b5882b4186f5f1b0537'
    assert sha(ex) == 'fdfdfbabcd2ccfc95e6a65275fa89c7a6290acddf4fc957527cb0a1d08c0989b'
    fixtures, executors = json.loads(fx.read_bytes()), json.loads(ex.read_bytes())
    assert len(fixtures['cases']) == 10 and len(executors['cases']) == 2
    ids = [r['id'] for r in fixtures['cases'] + executors['cases']]
    assert len(ids) == len(set(ids))
    legacies = [c for c in fixtures['cases'] if c['role'] == 'legacy_equivalence']
    assert len(legacies) == 6 and sum(c['decision_count'] for c in legacies) == 60
    assert {(c['seat'], c['observation']['farms'][c['seat']]['money']) for c in fixtures['cases'] if c['role'] == 'future_route_integration'} == {(s, cash) for s in (0, 1) for cash in (0, 100000)}
    for c in fixtures['cases'] + executors['cases']:
        obs = c['observation']
        assert c['observation_sha256'] == hashlib.sha256(json.dumps(obs, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
        assert obs['player'] == c['seat'] and obs['step'] == obs['day'] * 24 + obs['hour']
    harness = HERE / 'run_controls.py'
    ast.parse(harness.read_text())
    # 导入harness只定义工具；人工toy函数测试拒绝返回空时仍保留真实局部报价。
    spec = importlib.util.spec_from_file_location('r10_static_harness', harness)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    ns = {}
    exec('''def prefix_admission(baseline, trial, original_new_cash):
    return None
def funding_cash_book():
    return {}
def economic_plan_prefix(obs, st):
    f = {'money': 0}
    def budget_quote(item, pos):
        q = {'net_cash_model': 12, 'score': 4, 'selection_score': 12, '_r10_approval': {'labor_feasible_after_routes': True}}
        labor = {'feasible': False}
        next_work = {10: 300}
        admission = prefix_admission({}, {}, 12)
        q['funding_admission'] = admission
        return None, 'cash_prefix'
    return budget_quote('STRAWBERRY', (2, 3))
''', ns)
    with mod.BudgetProfile(ns) as profile: ns['economic_plan_prefix']({}, {})
    row = profile.budgets[0]
    assert row['returned_quote_present'] is False and row['local_quote_present'] is True
    assert row['quote_scores']['net_cash_model'] == 12 and row['route_proof']['labor_feasible_after_routes'] is True
    assert row['reason'] == 'cash_prefix' and row['prefix_calls'] == 1 and row['phase'] == 'initial_offer'
    r9manifest = MODEL / 'evaluation/r9_pass_diagnostic_s0/run_manifest.json'
    old = json.loads(r9manifest.read_bytes())
    r9 = MODEL / 'candidates/V125-R9/main.py'
    assert sha(r9) == old['candidate']['entry_sha256'] == 'e7f1fd549fc67ccec74015299af5366812abe43ec78c4142bb019429b6bb22e0'
    files = dict(sources)
    paths = [source_freeze, r9, r9manifest, fx, ex, harness, Path(__file__).resolve(), HERE / 'PLAN.md', HERE.parent / 'test_official_controls.py']
    paths += [Path(p) for p in fixtures['source_files']] + [Path(p) for p in executors['source_files']]
    paths += [Path(p) for p in old['engine']['files'] if 'kaggle_environments' in p]
    for p in paths: files[str(p)] = sha(p)
    result = {'schema': 'r10-integration-static-validation-v1', 'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'source_freeze_verified': True, 'fixture_count': 12, 'all_fixture_hashes_and_clock_valid': True,
        'profile_empty_return_local_quote_regression': True, 'candidate_calls': 0, 'official_initializations': 0,
        'official_steps': 0, 'toy_function_calls': 1, 'files': files}
    out = HERE / 'static_validation_v1.json'
    assert not out.exists()
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    files[str(out)] = sha(out)
    freeze = {'schema': 'r10-integration-execution-freeze-v1', 'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'root_execution_release': True, 'authorization': '根在engineering_source_freeze完成后明确放行，静态校验与本freeze完成后只执行一轮预登记工程控制。',
        'prototype_path': str(HERE.parent / 'integration_prototype.py'), 'r9_path': str(r9),
        'fixtures_path': str(fx), 'executor_fixtures_path': str(ex), 'files': files,
        'agent_visible_configuration': old['configuration'], 'maximum_calls': sources and json.loads(source_freeze.read_bytes())['allowed_maximum_calls'],
        'additional_call_counts': {'new_state': 8, 'module_definition_loads': 24, 'official_make': 16, 'official_explicit_reset': 16},
        'order': ['six_legacy_pairs', 'two_R9_default_executor_days', 'two_R10_default_funded_single_steps', 'four_internal_legacy_default_pairs'],
        'failure_policy': '每case首差/异常/>1s保留并停止该case；独立后续case继续；来源漂移则整轮停止；不重试择优。',
        'formal_status': 'NOT_GOLD_NOT_FULL_MATCH'}
    output = HERE / 'execution_freeze_v1.json'
    assert not output.exists()
    for p, expected in files.items(): assert sha(p) == expected
    output.write_text(json.dumps(freeze, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'freeze': str(output), 'freeze_sha256': sha(output), 'harness_sha256': sha(harness),
        'static_validation_sha256': sha(out), 'candidate_calls': 0, 'official_steps': 0}, ensure_ascii=False))


if __name__ == '__main__': main()
