"""完整36格结束后，只读强度与保存动作机制；不执行候选。"""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
MODEL = HERE.parents[1]
PLAN_SHA = 'd15c89d76f09e075a1692acb1db6a7f704b8b20ebe0fe1fa47af4c24d899f8a8'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(label, command):
    print('START ' + label, flush=True)
    with (HERE / (label + '.log')).open('x') as log:
        code = subprocess.run([sys.executable, '-B', *map(str, command)], stdout=log, stderr=subprocess.STDOUT).returncode
    if code:
        raise RuntimeError(label + ': ' + str(code))
    print('DONE ' + label, flush=True)


def main():
    plan_path = HERE / 'frozen_bundle.json'
    assert sha(plan_path) == PLAN_SHA
    plan = json.loads(plan_path.read_text())
    assert all(sha(p) == h for p, h in plan['source_files'].items())
    for job in plan['jobs']:
        summary = json.loads((Path(job['output']) / 'summary.json').read_text())
        assert summary['done_games'] == 6 and summary['status'] == 'COMPLETE'
    strength = HERE / 'fresh_strength_assessment'
    run('strength_assessment', [MODEL / 'evaluation/assess_paired_development.py', '--plan', plan_path, '--output', strength])
    assessment = json.loads((strength / 'assessment.json').read_text())
    assert assessment['data_integrity_pass'] and assessment['observed_unique_cells'] == 36
    directory = HERE / 'fresh_mechanism_audit'
    saved = directory / 'saved_traces'
    freeze = json.loads((directory / 'driver_freeze.json').read_text())
    driver = directory / 'replay_saved_batch.py'
    assert sha(driver) == freeze['driver_sha256']
    command = [driver, '--output', saved]
    for path in freeze['run_dirs']:
        command.extend(['--run-dir', path])
    run('saved_mechanism_replay', command)
    validation = json.loads((saved / 'validation.json').read_text())
    assert validation['verified_games'] == 24 and validation['candidate_calls'] == 0
    results = json.loads((saved / 'results.json').read_text())
    first = directory / 'first_sale'
    command = [MODEL / 'research/r8_terminal_net_selection/summarize_first_produced_sale_v3.py', '--output', first]
    for result in results:
        assert result['status'] == 'VERIFIED'
        command.extend(['--audit-dir', result['output']])
    run('first_produced_sale', command)
    run('late_sales_assessment', [HERE / 'measurement/assess_late_produced_sales.py', '--plan', plan_path,
                                '--strength-dir', strength, '--first-sale-dir', first,
                                '--output', directory / 'assessment'])
    print('REGISTERED_ANALYSIS_COMPLETE_QUALIFICATION_REQUIRES_REVIEW', flush=True)


if __name__ == '__main__':
    main()
