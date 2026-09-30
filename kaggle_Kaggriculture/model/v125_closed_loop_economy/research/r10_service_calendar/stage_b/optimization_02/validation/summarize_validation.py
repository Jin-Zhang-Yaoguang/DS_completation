"""只读已结束 P2 控制，独立保留源指纹与紧凑结果；不定义加载候选。"""
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    release_path = HERE / 'execution_release_v1.json'
    release = json.loads(release_path.read_bytes())
    source = HERE / 'controls_v1/summary.json'
    data = json.loads(source.read_bytes())
    assert data['schema'] == 'r10-p2-validation-result-v1'
    assert data['freeze_sha256'] == sha(release_path)
    files = {str(release_path): sha(release_path), str(source): sha(source),
             str(Path(__file__).resolve()): sha(__file__)}
    for path, expected in release['files'].items():
        assert sha(path) == expected, path
        files[path] = expected
    decoder_path = Path(release['decoder_path'])
    assert str(decoder_path) in files
    spec = importlib.util.spec_from_file_location('_p2_evidence_decoder_only', decoder_path)
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    decode = reader.decode
    compact_rows, full = {}, None
    for record in data['records']:
        path = Path(record['path'])
        assert sha(path) == record['sha256'], path
        files[str(path)] = record['sha256']
        row = json.loads(gzip.decompress(path.read_bytes()))
        if row['id'].startswith('P2_compact_'):
            compact_rows[row['id']] = {'checks': row['checks'], 'count_delta': row.get('count_delta'),
                                       'observed_returns': row.get('observed_returns'), 'error': row.get('error')}
            if 'result' in row:
                result = decode(row['result'])
                compact_rows[row['id']]['result'] = {k: result.get(k) for k in
                    ('status', 'reason', 'failed_day', 'labor_feasible_after_routes', 'route_feasibility_by_day',
                     'scheduler_calls', 'checker_calls', 'cache_hits')}
                compact_rows[row['id']]['cache_entry_count'] = len(decode(row['cache']))
        if row['id'] == 'P2_full_economic_once':
            full = {k: row.get(k) for k in ('module', 'returned', 'seconds', 'over_1s', 'observation_unchanged',
                                           'plan_sha256', 'state_sha256', 'error')}
            if row.get('returned'):
                plan, state = decode(row['plan']), decode(row['state'])
                full['plan_companions'] = {'expert': state['expert'], 'crop_choice': state['crop_choice'],
                    'admitted_investment_count': len(plan['admitted_investments']),
                    'remaining_investment_cash_model': plan['remaining_investment_cash_model'],
                    'buy_land': plan['buy_land'], 'rejected_types': plan['rejected_types'],
                    'route_audit': state['investment_receipts'][-1]['r10_future_route']}
    assert full is not None
    old = data['saved_P1_performance_reference']
    result = {'schema': 'r10-p2-validation-compact-v1', 'created_at_utc': datetime.now(timezone.utc).isoformat(),
              'status': data['status'], 'counts': data['counts'], 'count_overruns': data['count_overruns'],
              'full_interface_comparison': data['full_interface_saved_P1_comparison'],
              'compact_interface_comparison': data['compact_interface_checks'], 'compact_details': compact_rows,
              'full_economic_comparison': data['full_economic_equivalence'], 'P2_unprofiled_internal_call': full,
              'saved_P1_reference_time': old,
              'single_observed_relative_time_reduction': (1 - full['seconds'] / old['seconds']) if full['returned'] else None,
              'P2_internal_within_1s': data['P2_internal_within_1s'],
              'equivalence_and_source_integrity_pass': data['equivalence_and_source_integrity_pass'],
              'source_drift': data['source_drift'], 'errors': data['errors'], 'top_error': data['top_error'],
              'P0_calls': 0, 'P1_calls': 0, 'whole_agent_calls': 0, 'engine_calls': 0, 'new_complete_matches': 0,
              'scope': '只读单次完整内部规划和纯接口控制；模型许可并非实际成交/服务；单次跨时段计时差不能外推性能分布。'}
    out = HERE / 'compact_summary.json'
    assert not out.exists()
    for path, expected in files.items():
        assert sha(path) == expected, path
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    files[str(out)] = sha(out)
    manifest = HERE / 'summary_manifest.json'
    assert not manifest.exists()
    manifest.write_text(json.dumps({'schema': 'r10-p2-readonly-summary-v1', 'files': files,
                                   'candidate_calls': 0, 'pure_strategy_calls': 0, 'engine_calls': 0},
                                  ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'summary': str(out), 'sha256': sha(out), 'status': result['status'],
                      'seconds': full['seconds'], 'equivalence': result['equivalence_and_source_integrity_pass'],
                      'source_files': len(files)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
