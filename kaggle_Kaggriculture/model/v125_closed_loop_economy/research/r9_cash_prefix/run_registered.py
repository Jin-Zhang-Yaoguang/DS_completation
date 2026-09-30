"""串行执行已冻结的R9诊断与36格；错误保留并停止，不覆盖或删结果。"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
plan_path = HERE / 'frozen_bundle.json'
assert hashlib.sha256(plan_path.read_bytes()).hexdigest() == '83c5fc9cf70761ad14382ef6b6e83ed732809dba7536c49f1f1fb9a3d59eba66'
plan = json.loads(plan_path.read_text())
runner = ROOT / 'evaluation/run_match_v3.py'
assert hashlib.sha256(runner.read_bytes()).hexdigest() == plan['runner_sha256']
env = dict(os.environ)
assert not any(key in env for key in ['V125_PARAMS', 'V15_PARAMS'])
env['PYTHONDONTWRITEBYTECODE'] = '1'
jobs = [{'entry': str(ROOT / 'candidates/V125-R9/main.py'), 'opponent':'PASS', 'output':str(ROOT / 'evaluation/r9_pass_diagnostic_s0'), 'seeds':'1950905001', 'seats':'0'}]
jobs += [{**job, 'seeds':','.join(map(str, plan['seeds'])), 'seats':'both'} for job in plan['jobs']]
for job in jobs:
    output = Path(job['output'])
    assert not output.exists(), str(output)
    command = [sys.executable, '-B', str(runner), '--candidate', job['entry'], '--opponent',job['opponent'], '--seeds',job['seeds'], '--seats',job['seats'],
               '--backend','official','--daily','--audit-actions','--parity','--trace','--diagnostics','--protocol',str(ROOT / 'GATE_PROTOCOL.md'),'--output',str(output)]
    print('START ' + output.name, flush=True)
    with (HERE / (output.name + '.stdout.log')).open('x') as stream:
        proc = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, env=env)
    if proc.returncode:
        raise RuntimeError('RUN_ERROR ' + output.name + ' exit=' + str(proc.returncode))
    summary = json.loads((output / 'summary.json').read_text())
    print(json.dumps({'output':output.name, 'summary':summary}, ensure_ascii=False), flush=True)
    assert summary['status'] == 'COMPLETE' and summary['all_parity_pass'] is True
print('ALL_REGISTERED_RUNS_COMPLETE', flush=True)
