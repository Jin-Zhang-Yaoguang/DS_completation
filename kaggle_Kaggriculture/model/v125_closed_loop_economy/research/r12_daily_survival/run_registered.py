"""串行运行事前冻结的完整24格；异常或超时保留结果并停止。"""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys

HERE = Path(__file__).resolve().parent
MODEL = HERE.parents[1]
PLAN_SHA = '21cc54dfa4a5092e6aabdcfc9eb472254df2c04b4ed9180be6e7fd90d743f439'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    plan_path = HERE / 'frozen_bundle.json'
    assert sha(plan_path) == PLAN_SHA
    plan = json.loads(plan_path.read_text())
    assert all(not Path(j['output']).exists() for j in plan['jobs'])
    env = dict(os.environ)
    assert not any(k in env for k in ['V125_PARAMS', 'V15_PARAMS'])
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    for job in plan['jobs']:
        assert sha(plan_path) == PLAN_SHA
        assert all(sha(p) == h for p, h in plan['source_files'].items())
        output = Path(job['output'])
        command = [sys.executable, '-B', str(MODEL / 'evaluation/run_match_v3.py'),
                   '--candidate', job['entry'], '--opponent', job['opponent'],
                   '--seeds', ','.join(map(str, plan['seeds'])), '--seats', 'both',
                   '--backend', 'official', '--daily', '--audit-actions', '--parity', '--trace', '--diagnostics',
                   '--protocol', str(plan_path), '--output', str(output), '--hard-call-timeout', '10']
        print('START ' + output.name, flush=True)
        with (HERE / (output.name + '.stdout.log')).open('x') as log:
            proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
            for line in proc.stdout:
                log.write(line)
                log.flush()
                print(line.rstrip(), flush=True)
            code = proc.wait()
        if code:
            raise RuntimeError('RUN_ERROR ' + output.name + ' exit=' + str(code))
        rows = [json.loads(s) for s in (output / 'games.jsonl').read_text().splitlines()]
        assert len(rows) == 6
        assert all(r['status'] == 'DONE' and r['calls'] == 719 and r['parity_state_checks'] == 1440 and not r['errors'] for r in rows)
        assert all(a['calls_over_1s'] == 0 and a['latency_ms']['max'] <= 1000 for r in rows for a in r['agents'])
    print('ALL_24_REGISTERED_GAMES_COMPLETE_NOT_GOLD', flush=True)


if __name__ == '__main__':
    main()
