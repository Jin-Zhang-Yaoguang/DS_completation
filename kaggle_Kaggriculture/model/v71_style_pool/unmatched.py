import json, collections, statistics as st
from pathlib import Path
HERE = Path(__file__).resolve().parent
rows = json.load(open(HERE/'live_rows.json'))
styles = {s['sig']: s for s in json.load(open(HERE/'style_pool_v1.json'))}
team_known = set()
import glob
for f in glob.glob(str(HERE/'sig_*.jsonl')):
    for l in open(f):
        r = json.loads(l)
        if 'err' not in r: team_known.add(r['team'])
un = [r for r in rows if r['sig'] not in styles and not (team_known & {r['opp']} and any(sg in styles for sg in []))]
# 重新精确分未匹配(与 match_live 相同逻辑)
team_sig = collections.defaultdict(collections.Counter)
for f in glob.glob(str(HERE/'sig_*.jsonl')):
    for l in open(f):
        r = json.loads(l)
        if 'err' not in r: team_sig[r['team']][r['op_sig']] += 1
def matched(r):
    if r['sig'] in styles: return True
    ts = team_sig.get(r['opp'])
    return bool(ts and any(sg in styles for sg in ts))
un = [r for r in rows if not matched(r)]
by = collections.defaultdict(list)
for r in un: by[r['sig']].append(r)
print("未匹配签名(≥3 局):")
for sg, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
    if len(v) < 3: continue
    w = sum(1 for r in v if r['margin'] > 0)
    teams = collections.Counter(r['opp'] for r in v)
    print(f"  {sg} 局{len(v):3d} 我胜 {w}/{len(v)} ({w/len(v):.0%}) 中位 {st.median(r['margin'] for r in v):+8.0f}  队伍 {len(teams)} 个: {[t[:14] for t,_ in teams.most_common(4)]}")
# 输局单点(所有未匹配+已匹配中 margin<0 的强对手)
print("\n我方全部输局按对手(≥2 败或大败):")
loss = collections.defaultdict(list)
for r in rows:
    if r['margin'] <= 0: loss[r['opp']].append(r['margin'])
for t, v in sorted(loss.items(), key=lambda kv: min(kv[1]))[:15]:
    print(f"  {t[:20]:20s} 败 {len(v)} 次 最差 {min(v):+8.0f}  签名 {[r['sig'] for r in rows if r['opp']==t][:2]}")
