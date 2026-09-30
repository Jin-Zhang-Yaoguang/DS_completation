"""从冻结的 Kaggle 官方元数据和败局回放生成本轮分析。"""
import collections
import hashlib
import json
import math
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent


def stats(rows):
    n = len(rows)
    wins = sum(r['margin'] > 0 for r in rows)
    z = 1.96
    q = wins / n
    center = (q + z*z/(2*n)) / (1+z*z/n)
    width = z * math.sqrt(q*(1-q)/n+z*z/(4*n*n)) / (1+z*z/n)
    return dict(games=n, wins=wins, losses=sum(r['margin'] < 0 for r in rows),
                draws=sum(r['margin'] == 0 for r in rows), win_rate=q,
                descriptive_wilson95=[center-width, center+width],
                mean_reward=statistics.mean(r['reward'] for r in rows),
                mean_opponent_reward=statistics.mean(r['opp_reward'] for r in rows),
                mean_margin=statistics.mean(r['margin'] for r in rows))


result = {'snapshot': json.loads((HERE/'snapshot.json').read_text()), 'submissions': {}, 'loss_replays': []}
submissions = json.loads((HERE/'submissions.json').read_text())
match_sets = {}
for sid in (56145471, 56145933):
    raw = json.loads((HERE/f'metadata_{sid}.json').read_text())
    assert len({r['id'] for r in raw}) == len(raw)
    cli = json.loads((HERE/f'episodes_{sid}.json').read_text())
    assert {r['id'] for r in raw} == {r['id'] for r in cli}
    rows = json.loads((HERE/f'matches_{sid}.json').read_text())
    assert len(rows) == sum(r['type'] == 'EPISODE_TYPE_PUBLIC' for r in raw)
    assert all(r['state'] == 'COMPLETED' for r in raw)
    assert rows == sorted(rows, key=lambda r: (r['end'], r['id']))
    match_sets[sid] = rows
    result['submissions'][sid] = dict(
        submission=next(s for s in submissions if s['ref'] == sid),
        public=stats(rows), validation_excluded=sum(r['type'] == 'EPISODE_TYPE_VALIDATION' for r in raw),
        first29=stats(rows[:29]), last10=stats(rows[-10:]),
        seats={seat: stats([r for r in rows if r['seat'] == seat]) for seat in (0, 1)},
        first_public_end=rows[0]['end'], last_public_end=rows[-1]['end'],
        losses=[r for r in rows if r['margin'] < 0])

result['common_opponent_submissions'] = sorted(
    {r['opp_submission'] for r in match_sets[56145471]} &
    {r['opp_submission'] for r in match_sets[56145933]})
result['common_opponent_teams'] = sorted(
    {r['opponent'] for r in match_sets[56145471]} &
    {r['opponent'] for r in match_sets[56145933]})
for sid, rows in match_sets.items():
    for row in rows:
        if row['margin'] >= 0:
            continue
        path = HERE/'replays'/f"episode-{row['id']}-replay.json"
        replay = json.loads(path.read_text())
        seat = row['seat']
        assert len(replay['steps']) == 720
        assert replay['info']['EpisodeId'] == row['id']
        assert replay['info']['TeamNames'][seat] == 'datatuu'
        assert [a['status'] for a in replay['steps'][-1]] == ['DONE', 'DONE']
        assert replay['steps'][-1][seat]['reward'] == row['reward']
        assert replay['steps'][-1][1-seat]['reward'] == row['opp_reward']
        checkpoints = []
        for step in (144, 288, 432, 576, 648, 696, 719):
            obs = replay['steps'][step][0]['observation']
            banks = [f['money'] for f in obs['farms']]
            checkpoints.append(dict(step=step, own_bank=banks[seat], opponent_bank=banks[1-seat],
                                    margin=banks[seat]-banks[1-seat],
                                    shops=obs['town']['unlocked_shops'],
                                    egg_inventory=obs['market']['inventory']['EGG']))
        result['loss_replays'].append(dict(
            submission_id=sid, episode_id=row['id'], seat=seat,
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            module_version=replay['module_version'], configuration=replay['configuration'],
            seed=replay['info']['seed'], steps=720, statuses=['DONE','DONE'],
            inferred_route_at144=1 if 'YARN_STORE' in checkpoints[0]['shops'] else 0,
            inferred_route_at648=2 if checkpoints[4]['egg_inventory'] <= 9888 else 3,
            checkpoints=checkpoints))

result['limitations'] = [
    '本轮是公开线上成绩诊断，未运行本地对战、训练、修改策略或提交。',
    '没有逐局赛前 rating，无法精确分解 625.8 分差。',
    '双方无共同对手团队，非同种子、同对手的配对比较。',
    'Wilson 区间仅作小样本描述；自适应匹配并非独立同分布抽样。',
    '按此前内部 1-40 / 41-80 观察口径，双方尚未覆盖稳定观察段；40/80 不是本次官方评测页规定的硬阈值。',
    '路线编号根据原包路由条件与实际公开观测推断，未伪称服务端记录了路由编号。']
(HERE/'analysis.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({sid: v['public'] for sid,v in result['submissions'].items()},ensure_ascii=False,indent=2))
print('共同对手团队:', result['common_opponent_teams'])
