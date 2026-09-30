"""按已保存动作重建一次R0前384帧；仅捕获第15日真实分派，不改候选。"""
import copy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
MODEL = HERE.parents[1]
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    protocol = json.loads((HERE / 'capture_protocol.json').read_text())
    assert all(sha(p) == h for p, h in protocol['files'].items())
    out = HERE / 'capture_once'
    out.mkdir(exist_ok=False)
    run = MODEL / 'evaluation/v125-r0_r10dev_pass_3x2'
    manifest = json.loads((run / 'run_manifest.json').read_text())
    row = json.loads((run / 'games.jsonl').read_text().splitlines()[0])
    with gzip.open(row['trace']['path'], 'rt') as f:
        actions = json.load(f)['actions']
    spec = importlib.util.spec_from_file_location('capture_r11_h', MODEL / 'evaluation/run_match_v3.py')
    h = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(h)
    make, rules, fast, engine = h.import_engines()
    assert engine['composite_sha256'] == manifest['engine']['composite_sha256']
    agent = h.Agent(manifest['candidate'], row['seed'], 0)
    env = h.Engine('official', row['seed'], make, fast)
    cfg = h.agent_configuration(manifest, env)
    captured = []
    code = agent.module.allocate.__code__

    def profile(frame, event, result):
        if frame.f_code is code and event == 'return':
            loc = frame.f_locals
            captured.append(copy.deepcopy({
                'observation': loc['obs'], 'plan': loc['plan'], 'tasks': loc['tasks'],
                'actions': result, 'actors': loc['actors'], 'weights': loc['weights'],
                'assignment': loc['assignment'], 'available': loc['available'],
            }))

    for step in range(384):
        obs = env.observe(0)
        assert obs['step'] == step
        if step >= 360:
            sys.setprofile(profile)
        try:
            result = agent.call(obs, cfg, 10)
        finally:
            sys.setprofile(None)
        assert result == actions[step][0], ('ACTION_DRIFT', step)
        env.step(copy.deepcopy(actions[step]))
    assert len(captured) == 24
    with gzip.open(out / 'captured.json.gz', 'wt') as f:
        json.dump(captured, f, ensure_ascii=False)
    assert all(sha(p) == v for p, v in protocol['files'].items())
    (out / 'summary.json').write_text(json.dumps({
        'status': 'EXACT_SAVED_PREFIX_CAPTURED', 'agent_calls': 384,
        'saved_action_official_steps': 384, 'new_complete_matches': 0,
        'all_actions_equal': True, 'capture_frames': 24,
        'performance_evidence': False, 'captured_sha256': sha(out / 'captured.json.gz'),
    }, ensure_ascii=False, indent=2))
    print('EXACT_SAVED_PREFIX_CAPTURED: 384 calls, 24 frames, zero new games')


if __name__ == '__main__':
    main()
