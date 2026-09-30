"""仅复核已保存前271步，在首个失败点捕获原求解输入和返回；不新增比赛。"""
import copy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
MODEL = next(p for p in HERE.parents if p.name == 'v125_closed_loop_economy')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def main():
    protocol = json.loads((HERE / 'protocol_v2.json').read_text())
    assert all(sha(p) == h for p, h in protocol['files'].items())
    out = HERE / 'run_once_v2'
    out.mkdir(exist_ok=False)
    spec = importlib.util.spec_from_file_location('capture_match', MODEL / 'evaluation/run_match_v3.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    run = MODEL / 'evaluation/r10_opt03_opened_natural_01'
    manifest = json.loads((run / 'run_manifest.json').read_text())
    row = json.loads((run / 'games.jsonl').read_text())
    with gzip.open(run / 'trace_1950905001_seat0.json.gz', 'rt') as f:
        saved = json.load(f)['actions']
    make, rules, fast, engine = m.import_engines()
    assert engine['composite_sha256'] == manifest['engine']['composite_sha256']
    agent = m.Agent(manifest['candidate'], 1950905001, 0)
    env = m.Engine('official', 1950905001, make, fast)
    cfg = m.agent_configuration(manifest, env)
    code = agent.module._r10_scheduler_schedule_day.__code__
    captures = []

    def profile(frame, event, arg):
        if frame.f_code is code and event == 'return':
            loc = frame.f_locals
            captures.append(copy.deepcopy({'problem': loc['problem'], 'n_hands': loc['n_hands'], 'result': arg,
                                            'workers': loc.get('workers'), 'assigned': loc.get('assigned')}))

    for step in range(protocol['target_step'] + 1):
        obs = env.observe(0)
        assert obs['step'] == step
        if step == protocol['target_step']:
            write(out / 'observation.json', obs)
            sys.setprofile(profile)
        try:
            action = agent.call(obs, cfg, 10)
        finally:
            sys.setprofile(None)
        assert action == saved[step][0], f'ACTION_DRIFT:{step}'
        env.step(saved[step])
    receipts = agent.diagnostics()['0']['investment_receipts']
    assert len(captures) == 1
    write(out / 'scheduler_capture.json', captures[0])
    write(out / 'receipts.json', receipts)
    # 保存参照是JSON表示：日期整数键已变成字符串，先按相同序列化规则转换。
    assert json.loads(json.dumps(receipts)) == row['strategy_diagnostics'][0]['0']['investment_receipts'][:protocol['target_step'] + 1]
    assert all(sha(p) == h for p, h in protocol['files'].items())
    write(out / 'summary.json', {'status': 'SAVED_PREFIX_EXACT_CAPTURED', 'agent_calls': 271,
                                'saved_action_official_steps': 271, 'new_complete_matches': 0,
                                'source_files_verified': len(protocol['files']), 'all_actions_equal': True,
                                'all_271_receipts_equal': True, 'captured_original_scheduler_calls': 1,
                                'performance_evidence': False, 'target_step': protocol['target_step'],
                                'captured_files': {str(p): sha(p) for p in out.iterdir() if p.is_file()}})
    print(json.dumps({'status': 'SAVED_PREFIX_EXACT_CAPTURED', 'agent_calls': 271, 'new_complete_matches': 0}))


if __name__ == '__main__':
    main()
