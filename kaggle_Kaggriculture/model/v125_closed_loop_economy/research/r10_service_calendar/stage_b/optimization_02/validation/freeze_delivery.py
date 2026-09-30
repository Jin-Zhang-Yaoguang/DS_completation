"""冻结完成的 P2 控制与独立更正；不运行任何策略或引擎。"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    manifest = HERE / 'offline_correction_manifest.json'
    files = json.loads(manifest.read_bytes())['files']
    for path, expected in files.items():
        assert sha(path) == expected, path
    extra = ['offline_correction_manifest.json', 'REPORT.md', 'independent_result_review.json',
             'independent_result_review.md', 'freeze_delivery.py']
    for name in ('independent_result_review_addendum.json', 'independent_result_review_addendum.md'):
        if (HERE / name).exists():
            extra.append(name)
    for name in extra:
        path = HERE / name
        files[str(path)] = sha(path)
    corrected = json.loads((HERE / 'corrected_compact_summary.json').read_bytes())
    review = json.loads((HERE / 'independent_result_review.json').read_bytes())
    root_decision = HERE.parent / 'root_decision.json'
    files[str(root_decision)] = sha(root_decision)
    assert review['passed'] == review['total'] == 40
    assert corrected['status'] == 'P2_TIME_THRESHOLD_FAILED'
    assert corrected['equivalence_and_source_integrity_pass'] is True
    assert corrected['P2_internal_within_1s'] is False
    assert json.loads((HERE / 'controls_v1/summary.json').read_bytes())['status'] == 'EQUIVALENCE_OR_SOURCE_FAILURE'
    result = {'schema': 'r10-p2-validation-delivery-v1', 'created_at_utc': datetime.now(timezone.utc).isoformat(),
              'files': files, 'status': corrected['status'], 'source_integrity_and_full_equivalence': True,
              'original_raw_status_preserved': 'EQUIVALENCE_OR_SOURCE_FAILURE',
              'postprocessing_correction_only': 'audit counts nested path; saved outputs and timings unchanged',
              'independent_review_passed': review['passed'], 'independent_review_total': review['total'],
              'root_decision_path': str(root_decision), 'counts': corrected['counts'],
              'full_agent_calls': 0, 'engine_calls': 0, 'new_matches': 0,
              'P0_P1_reruns': 0, 'single_P2_internal_seconds': corrected['P2_unprofiled_internal_call']['seconds'],
              'saved_P1_internal_seconds': corrected['saved_P1_reference_time']['seconds'],
              'scope': '已打开人工输入的有限工程结果；完整plan/state/9counts相同，性能失败；原后处理错误和更正分开保留。'}
    for path, expected in files.items():
        assert sha(path) == expected, path
    out = HERE / 'delivery_manifest.json'
    assert not out.exists()
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'delivery': str(out), 'sha256': sha(out), 'files': len(files),
                      'status': result['status']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
