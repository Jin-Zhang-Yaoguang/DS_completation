"""P2 仅读字节、AST 与 JSON，登记唯一候选、fixture、旧参照及审计工具。"""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
OPT = HERE.parent
P1 = OPT.parent / 'optimization_01/validation'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def literal(path, name):
    tree = ast.parse(Path(path).read_bytes())
    nodes = [node for node in tree.body if isinstance(node, ast.Assign) and
             any(isinstance(target, ast.Name) and target.id == name for target in node.targets)]
    assert len(nodes) == 1, name
    return ast.literal_eval(nodes[0].value)


def main():
    handoff = OPT / 'handoff_manifest.json'
    scope = OPT / 'ROOT_SCOPE.json'
    delivery = P1 / 'delivery_manifest.json'
    source = OPT / 'integration_prototype.py'
    assert sha(handoff) == 'fbe92e9c49d8ce88a20480297fd0edb49cbe6a4dfef6d68bcd555f430a1d5dfd'
    assert sha(scope) == '0eebb38dbe526aa326e9cf539606ca25afe8f44093ca16895c067e7c054d5f69'
    assert sha(delivery) == 'adde9155fc8979c7c77bd64f8366f932cc79a87e66dc3957a07b555c183510a3'
    assert sha(source) == '370063a750dfb8775a155fc9f36bcaff3f8e676795f70c91d8927dec5852e895'
    files = {}
    def merge(values):
        for path, value in values.items():
            if path in files:
                assert files[path] == value, 'INCONSISTENT_DUPLICATE_SOURCE:' + path
            files[path] = value
    merge(json.loads(delivery.read_bytes())['files'])
    merge({str(OPT / p): h for p, h in json.loads(handoff.read_bytes())['files'].items()})
    fixture_path = HERE / 'fixture_v1.json'
    assert sha(fixture_path) == '62ce2fe54894eccd635019adc4b04b3faa3585ee96cc7de6c8e253f29afc35ad'
    fixture = json.loads(fixture_path.read_bytes())
    original = json.loads((P1 / 'fixture_v1.json').read_bytes())
    assert fixture['economic_case'] == original['economic_case']
    assert fixture['interface_case'] == original['interface_case']
    assert fixture['economic_timeout_seconds'] == 120
    assert len(fixture['interface_case']['positions']) == 24
    assert len({tuple(p) for p in fixture['rollback_case']['positions']}) == 64
    assert fixture['rollback_case']['startup_fallback_days'] == [10]
    assert len(fixture['compact_cases']) == len(set(fixture['compact_cases'])) == 7
    old_release = json.loads((P1 / 'execution_release_v2.json').read_bytes())
    assert literal(source, 'PARAMS') == old_release['expected_params']
    assert literal(source, '_r10_integration_IMPLEMENTATION_IDS') == old_release['implementation_ids']
    for name in ('run_validation.py', 'prepare_fixture.py', 'freeze_static.py'):
        ast.parse((HERE / name).read_bytes())
    refs = {'interfaces': {name: str(P1 / ('controls_v1/P1_interface_' + name + '.json.gz'))
                           for name in fixture['interface_case']['registered_cases']},
            'full_economic': str(P1 / 'controls_v1/P1_full_economic_once.json.gz')}
    helper = P1 / 'run_validation_v2.py'
    decoder = P1 / 'summarize_validation.py'
    assert sha(helper) == 'f6128954935ead67299097e447b5056cf01ca296c08561b7b41f1b938a33e455'
    merge(fixture['source_files'])
    merge(fixture['files'])
    for path in (handoff, scope, delivery, source, fixture_path, helper, decoder, HERE / 'PLAN.md',
                 HERE / 'run_validation.py', HERE / 'prepare_fixture.py', Path(__file__).resolve()):
        merge({str(path): sha(path)})
    for path in [*refs['interfaces'].values(), refs['full_economic']]:
        assert str(path) in files
    for path, expected in files.items():
        assert sha(path) == expected, path
    maximum = {'module_definition_loads': 2, 'pure_route_calls': 11, 'pure_calendar_calls': 88,
               'pure_aggregate_calls': 2, 'pure_cache_constructions': 5,
               'pure_compile_day_problem_calls': 9, 'pure_native_scheduler_calls': 5,
               'pure_native_checker_calls': 5, 'pure_custom_schedule_calls': 1,
               'pure_custom_check_calls': 1, 'compact_schedule_hook_calls': 0,
               'compact_check_hook_calls': 0, 'new_state_calls': 1, 'internal_economic_calls': 1}
    expected = json.loads(scope.read_bytes())['expected_saved_reference']
    result = {'schema': 'r10-p2-validation-freeze-v1', 'created_at_utc': datetime.now(timezone.utc).isoformat(),
              'root_execution_release': False, 'sources': {'P2': str(source)},
              'source_sha256': {'P2': sha(source)}, 'candidate_labels': {'P2': literal(source, 'CANDIDATE_ID')},
              'expected_params': literal(source, 'PARAMS'), 'implementation_ids': old_release['implementation_ids'],
              'files': files, 'helper_path': str(helper), 'decoder_path': str(decoder), 'references': refs,
              'fixture_path': str(fixture_path), 'output_path': str(HERE / 'controls_v1'),
              'harness_path': str(HERE / 'run_validation.py'), 'maximum_calls': maximum,
              'expected_economic_counts': {k: expected[k] for k in ('route_attempts', 'scheduler_calls', 'checker_calls', 'cache_hits')},
              'expected_saved_plan_sha256': expected['plan_sha256'], 'expected_saved_state_sha256': expected['state_sha256'],
              'runtime': {'executable': sys.executable, 'version': sys.version, 'unprofiled_economic_guard_seconds': 120,
                          'pass_threshold_seconds': 1},
              'execution_order': ['P2_full_api_four_cases', 'saved_P1_full_result_cache_alias_comparison',
                                  'P2_compact_seven_cases', 'P2_full_economic_once', 'saved_P1_entire_typed_comparison'],
              'counter_scope': 'calendar/aggregate/cache为人工fixture的直接调用数；native计数为11纯接口内实际观察；完整economic内部后代计数独立从原审计报告读取，不混入pure预算。',
              'strict_comparison': '保留全部plan/state字段、类型、dict顺序；CID单列metadata，没有计划字段过滤。full接口整个result/cache/反向别名效果原样比较；compact只显式改变mode/schema参与的key与四项stats投影。',
              'static_checks': {'AST_parse_pass': True, 'all_frozen_files_match': True, 'same_P1_economic_fixture': True,
                                'same_P1_full_interface_fixture': True, 'candidate_definition_loads': 0,
                                'pure_module_calls': 0, 'candidate_calls': 0, 'engine_calls': 0},
              'P0_calls': 0, 'P1_calls': 0, 'whole_agent_calls': 0, 'official_steps': 0, 'new_complete_matches': 0,
              'scope': '静态预登记，等待根签独立release；P2只调用一次完整内部规划，失败保留不重复；不是正式门或金牌裁决。'}
    output = HERE / 'execution_freeze_v1.json'
    assert not output.exists()
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'freeze': str(output), 'freeze_sha256': sha(output),
                      'harness_sha256': sha(HERE / 'run_validation.py'), 'fixture_sha256': sha(fixture_path),
                      'files': len(files), 'candidate_calls': 0, 'pure_module_calls': 0, 'engine_calls': 0}, ensure_ascii=False))


if __name__ == '__main__':
    main()
