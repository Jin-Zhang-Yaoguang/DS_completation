"""P3 静态字节/AST登记，无候选定义加载或策略调用。"""
import ast
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
OPT = HERE.parent
B = OPT.parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def literal(path, name):
    tree = ast.parse(Path(path).read_bytes())
    nodes = [n for n in tree.body if isinstance(n, ast.Assign) and
             any(isinstance(t, ast.Name) and t.id == name for t in n.targets)]
    assert len(nodes) == 1
    return ast.literal_eval(nodes[0].value)


def main():
    source = OPT / 'integration_prototype.py'
    handoff = OPT / 'handoff_manifest.json'
    original = B / 'integration_validation/delivery_manifest.json'
    assert sha(source) == 'b5bcdd51829e9df20686de08935e96f65ec3ca7f1bd13bf7f9c756cfaa0465e6'
    assert sha(handoff) == '336b3135070c6f9170e4c4ae84d201c58037d556790e2466b125816095bf862a'
    assert sha(original) == '58f1b65fcbd94b3b31b9899fce72f7e62cab8a70f226307557d1b1c214b259f1'
    files = {}
    def add(path, value):
        path = str(path)
        if path in files:
            assert files[path] == value
        assert sha(path) == value, path
        files[path] = value
    for path in (handoff, original):
        for file, value in json.loads(path.read_bytes())['files'].items():
            add(file, value)
        add(path, sha(path))
    fixture_path = HERE / 'fixture_v1.json'
    assert sha(fixture_path) == 'b8476d1cc71b099cd217273acc40d3347284887c9bc6705620de15d5c0722dc4'
    fixture = json.loads(fixture_path.read_bytes())
    for path, value in fixture['source_files'].items():
        add(path, value)
    assert len(fixture['cases']) == 5 and len(fixture['pure_sequence']) == 8
    assert sum(bool(row.get('fail')) for row in fixture['pure_sequence']) == 3
    assert sum(case['max_daily_solvers'] for case in fixture['cases']) == 110
    for case in fixture['cases']:
        raw = json.loads(gzip.decompress(Path(case['reference_path']).read_bytes()))
        assert raw['fixture']['observation'] == case['observation']
    helper = B / 'optimization_01/validation/run_validation_v2.py'
    normalizer = B / 'integration_validation/run_controls.py'
    assert sha(helper) == 'f6128954935ead67299097e447b5056cf01ca296c08561b7b41f1b938a33e455'
    for path in (fixture_path, helper, normalizer, HERE / 'PLAN.md', HERE / 'STATIC_FIXTURE_NOTE.md',
                 HERE / 'run_validation.py', HERE / 'prepare_fixture.py', Path(__file__).resolve()):
        add(path, sha(path))
        if path.suffix == '.py':
            ast.parse(path.read_bytes())
    labels = ['selector'] + [case['id'] for case in fixture['cases']]
    params = literal(source, 'PARAMS')
    assert params['cash_funding'] == 'cash_prefix'
    assert params['r10_route_mode'] == 'bounded_future_failure_rescue'
    result = {'schema': 'r10-p3-validation-freeze-v1', 'at': datetime.now(timezone.utc).isoformat(),
              'root_execution_release': False, 'sources': {label: str(source) for label in labels},
              'source_sha256': sha(source), 'candidate_id': literal(source, 'CANDIDATE_ID'),
              'expected_params': params, 'files': files, 'helper_path': str(helper), 'normalizer_path': str(normalizer),
              'fixture_path': str(fixture_path), 'output_path': str(HERE / 'controls_v1'),
              'harness_path': str(HERE / 'run_validation.py'),
              'maximum_direct_calls': {'module_definition_loads': 6, 'new_state_calls': 5,
                                       'internal_economic_calls': 5, 'pure_select_calls': 8,
                                       'pure_fail_calls': 3, 'pure_key_calls': 7},
              'nested_economic_bounds': {'route_attempts': 5, 'scheduler_calls': 110, 'checker_calls': 110},
              'timing': {'profile': False, 'guard_seconds': 120, 'threshold_seconds': 1},
              'runtime': {'executable': sys.executable, 'version': sys.version},
              'counter_path': "receipt['r10_future_route']['counts']",
              'zero_count_rule': '只有明确route_attempted=false且无rescue批准、审计计数皆0时，空计数才可推出0；尝试时显式route_attempts=1和native计数必备。',
              'comparison': '按PLAN已列原经营字段和新增状态；无监控恢复中间trial，无法核对即PENDING；正例不宣称不存在的原完整state等价。',
              'static_validation': {'AST_parse': True, 'all_files_match': True, 'five_original_observations_exact': True,
                                    'candidate_definition_loads': 0, 'candidate_calls': 0, 'pure_helper_calls': 0, 'engine_calls': 0},
              'full_agent_calls': 0, 'engine_calls': 0, 'new_complete_matches': 0, 'old_candidate_calls': 0,
              'scope': '待根release的唯一有限工程实例；不是正式候选或金牌门。'}
    out = HERE / 'execution_freeze_v1.json'
    assert not out.exists()
    for path, value in files.items():
        assert sha(path) == value, path
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'freeze': str(out), 'sha256': sha(out), 'files': len(files),
                      'harness_sha256': sha(HERE / 'run_validation.py'), 'fixture_sha256': sha(fixture_path),
                      'candidate_calls': 0, 'engine_calls': 0}, ensure_ascii=False))


if __name__ == '__main__':
    main()
