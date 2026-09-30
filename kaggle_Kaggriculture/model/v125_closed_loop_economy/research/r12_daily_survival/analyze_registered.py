"""同一串行链完成新24场强度、保存动作和保活审计；无候选调用。"""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
MODEL = HERE.parents[1]
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    release = json.loads((HERE / 'analysis_release.json').read_text())
    assert all(sha(p) == h for p, h in release['files'].items())
    plan = json.loads((HERE / 'frozen_bundle.json').read_text())
    assert all(sha(p) == h for p, h in plan['source_files'].items())
    for job in plan['jobs']:
        summary = json.loads((Path(job['output']) / 'summary.json').read_text())
        assert summary['status'] == 'COMPLETE' and summary['done_games'] == 6
    tasks = [
        ('strength', [str(MODEL / 'evaluation/assess_paired_development.py'),
                      '--plan', str(HERE / 'frozen_bundle.json'),
                      '--output', str(HERE / 'fresh_strength_assessment')]),
        ('saved_actions', [str(HERE / 'replay_fresh_saved.py')]
            + [arg for j in plan['jobs'] for arg in ['--run-dir', j['output']]]
            + ['--output', str(HERE / 'fresh_saved_audit')]),
        ('mechanism', [str(HERE / 'assess_mechanism.py')]),
    ]
    for name, args in tasks:
        assert all(sha(p) == h for p, h in release['files'].items())
        print('START ' + name, flush=True)
        with (HERE / (name + '_assessment.log')).open('x') as log:
            result = subprocess.run([sys.executable, '-B'] + args, stdout=log, stderr=subprocess.STDOUT)
        if result.returncode:
            raise RuntimeError(name + ' failed; preserve log, exit=' + str(result.returncode))
        print('DONE ' + name, flush=True)
    print('R12_ANALYSIS_COMPLETE_NOT_GOLD', flush=True)


if __name__ == '__main__':
    main()
