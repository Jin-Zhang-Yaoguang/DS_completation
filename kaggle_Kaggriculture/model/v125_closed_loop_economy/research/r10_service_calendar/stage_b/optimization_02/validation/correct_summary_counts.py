"""只读纠正后处理路径，不替换原 harness、原错误结果或任何调用证据。"""
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    source_manifest = HERE / 'summary_manifest.json'
    files = json.loads(source_manifest.read_bytes())['files']
    files[str(source_manifest)] = sha(source_manifest)
    files[str(Path(__file__).resolve())] = sha(__file__)
    for path, expected in files.items():
        assert sha(path) == expected, path
    raw_path = HERE / 'controls_v1/summary.json'
    original = json.loads(raw_path.read_bytes())
    release = json.loads((HERE / 'execution_release_v1.json').read_bytes())
    compact = json.loads((HERE / 'compact_summary.json').read_bytes())
    helper = load(release['helper_path'], '_p2_frozen_readonly_comparator')
    decode = load(release['decoder_path'], '_p2_frozen_readonly_decoder').decode
    records = {row['id']: row for row in original['records']}
    assert len(records) == len(original['records']) == 17
    paths = {'P1': Path(release['references']['full_economic']),
             'P2': Path(records['P2_full_economic_once']['path'])}
    outputs, values, counts = {}, {}, {}
    for label, path in paths.items():
        assert str(path) in files
        data = json.loads(gzip.decompress(path.read_bytes()))
        assert data['returned'] is True
        plan, state = decode(data['plan']), decode(data['state'])
        assert helper.fingerprint(plan) == data['plan_sha256']
        assert helper.fingerprint(state) == data['state_sha256']
        outputs[label] = data
        values[label] = (plan, state)
        counts[label] = state['investment_receipts'][-1]['r10_future_route']['counts']
    ds = helper.differences(values['P1'], values['P2'], 'entire_plan_and_state')
    count_ds = helper.differences(counts['P1'], counts['P2'], 'entire_route_counts')
    expected = release['expected_economic_counts']
    selected = {key: counts['P2'][key] for key in expected}
    raw_comparison = original['full_economic_equivalence']
    assert raw_comparison['actual_counts'] == {key: None for key in expected}
    assert raw_comparison['complete_economic_counts_equal'] is False
    assert original['status'] == 'EQUIVALENCE_OR_SOURCE_FAILURE'
    # 只纠正本次已复现的字段层级；其他错误或缺项不因修正而消失。
    all_record_checks = True
    for record in original['records']:
        data = json.loads(gzip.decompress(Path(record['path']).read_bytes()))
        if data.get('error') or data.get('skipped') or not all(data.get('checks', {}).values()):
            all_record_checks = False
    matrix = (len(original['full_interface_saved_P1_comparison']) == 4 and
              all(original['full_interface_saved_P1_comparison'].values()) and
              len(original['compact_interface_checks']) == 7 and all(original['compact_interface_checks'].values()))
    eq = bool(not ds and not count_ds and selected == expected and all_record_checks and matrix and
              not original['errors'] and not original['top_error'] and not original['source_drift'] and
              not original['count_overruns'])
    performance_pass = outputs['P2']['seconds'] <= 1 and outputs['P2']['returned']
    status = 'EQUIVALENCE_OR_SOURCE_FAILURE' if not eq else 'P2_TIME_THRESHOLD_FAILED' if not performance_pass else 'P2_BOUNDED_CONTROL_PASSED_NOT_QUALIFICATION'
    correction = {'schema': 'r10-p2-offline-count-path-correction-v1', 'created_at_utc': datetime.now(timezone.utc).isoformat(),
                  'original_summary_path': str(raw_path), 'original_summary_sha256': sha(raw_path),
                  'original_status': original['status'],
                  'original_actual_counts': raw_comparison['actual_counts'],
                  'bug': "原harness从r10_future_route直接取计数；真实计数在r10_future_route['counts']。",
                  'correct_path': "state['investment_receipts'][-1]['r10_future_route']['counts']",
                  'full_counts': counts, 'all_nine_counts_equal': not count_ds, 'count_differences': count_ds,
                  'registered_four_counts': {'expected': expected, 'actual': selected, 'equal': selected == expected},
                  'entire_typed_plan_state_equal': not ds, 'plan_state_differences': ds,
                  'typed_plan_sha256': {label: output['plan_sha256'] for label, output in outputs.items()},
                  'typed_state_sha256': {label: output['state_sha256'] for label, output in outputs.items()},
                  'all_individual_record_checks_pass': all_record_checks, 'complete_pure_matrix_pass': matrix,
                  'source_integrity_checked': True, 'corrected_equivalence_and_source_integrity_pass': eq,
                  'corrected_status': status, 'P2_seconds': outputs['P2']['seconds'], 'P2_within_1s': performance_pass,
                  'source_output_paths': {k: str(v) for k, v in paths.items()},
                  'new_candidate_calls': 0, 'new_pure_strategy_calls': 0, 'new_engine_calls': 0, 'new_matches': 0,
                  'scope': '离线后处理更正；原脚本和原false结果保留。未改变任何策略输出、阈值或原耗时。'}
    corrected = deepcopy(compact)
    corrected.update(schema='r10-p2-validation-corrected-compact-v1', original_status=compact['status'], status=status,
                     original_equivalence_and_source_integrity_pass=compact['equivalence_and_source_integrity_pass'],
                     equivalence_and_source_integrity_pass=eq,
                     count_path_correction=str(HERE / 'offline_count_path_correction.json'))
    corrected['full_economic_comparison']['original_actual_counts'] = raw_comparison['actual_counts']
    corrected['full_economic_comparison']['actual_counts'] = selected
    corrected['full_economic_comparison']['complete_economic_counts_equal'] = selected == expected
    corrected['full_economic_comparison']['all_nine_route_counts_equal'] = not count_ds
    for path, expected_sha in files.items():
        assert sha(path) == expected_sha, path
    for name, data in [('offline_count_path_correction.json', correction), ('corrected_compact_summary.json', corrected)]:
        path = HERE / name
        assert not path.exists()
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
        files[str(path)] = sha(path)
    manifest = HERE / 'offline_correction_manifest.json'
    assert not manifest.exists()
    manifest.write_text(json.dumps({'schema': 'r10-p2-offline-correction-manifest-v1', 'files': files,
                                   'candidate_calls': 0, 'pure_strategy_calls': 0, 'engine_calls': 0},
                                  ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'correction': str(HERE / 'offline_count_path_correction.json'), 'corrected_status': status,
                      'equivalence': eq, 'P2_seconds': outputs['P2']['seconds'],
                      'P1_P2_all_route_counts_equal': not count_ds, 'plan_state_differences': len(ds),
                      'manifest_sha256': sha(manifest)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
