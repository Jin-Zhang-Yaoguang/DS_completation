"""我方 live 对局:提取对手开局签名(与 sigscan 同口径)→ 匹配风格池 → 我方对各风格胜率表。"""
import json, glob, hashlib, collections, statistics as st
from pathlib import Path
HERE = Path(__file__).resolve().parent
OLD = "/private/tmp/claude-501/-Users-a1-6-Desktop-PycharmProjects-DS-completation--claude-worktrees-codex-knowledge-base-comparison-45cbaf/c4b08c78-e61d-4f46-80ad-0c38ef5aa260/scratchpad"
styles = {s['sig']: s for s in json.load(open(HERE/'style_pool_v1.json'))}
# 队名→主签名(官方数据众数)
team_sig = collections.defaultdict(collections.Counter)
for f in glob.glob(str(HERE/'sig_*.jsonl')):
    for l in open(f):
        r = json.loads(l)
        if 'err' not in r: team_sig[r['team']][r['op_sig']] += 1
rows = []
for d in ("b13live", "s2live", "wklive", "x3live"):
    for fn in glob.glob(f"{OLD}/{d}/episode-*.json"):
        try: rep = json.load(open(fn))
        except Exception: continue
        nm = rep['info']['TeamNames']
        if not isinstance(rep, dict) or nm.count('datatuu') != 1: continue
        p = nm.index('datatuu'); o = 1 - p; s = rep['steps']
        opening = []
        for t in range(1, 4):
            a = s[t][o].get('action') or {}
            opening.append([list(x) for x in (a.get('market') or [])])
        sig = hashlib.md5(json.dumps(opening).encode()).hexdigest()[:8]
        rows.append(dict(ver=d[:-4], ep=rep['info']['EpisodeId'], opp=nm[o], sig=sig,
                         margin=rep['rewards'][p] - rep['rewards'][o]))
# 去重(同一 episode 可能存两处)
seen = set(); uniq = []
for r in rows:
    if r['ep'] in seen: continue
    seen.add(r['ep']); uniq.append(r)
json.dump(uniq, open(HERE/'live_rows.json', 'w'), ensure_ascii=False)
def style_of(r):
    if r['sig'] in styles: return r['sig'], "直接"
    ts = team_sig.get(r['opp'])
    if ts:
        for sg, _ in ts.most_common():
            if sg in styles: return sg, "按队名"
    return None, None
agg = collections.defaultdict(list); un = []
for r in uniq:
    sg, how = style_of(r)
    if sg: agg[sg].append(r)
    else: un.append(r)
print(f"我方线上 {len(uniq)} 局;匹配到风格 {sum(len(v) for v in agg.values())} 局,未匹配 {len(un)} 局")
out = []
print(f"\n{'风格':9s}{'家族':13s}{'局':>4s}{'我胜':>5s}{'我方胜率':>7s}{'中位分差':>9s}  代表")
for sg, v in sorted(agg.items(), key=lambda kv: sum(1 for r in kv[1] if r['margin'] > 0)/len(kv[1])):
    s0 = styles[sg]; w = sum(1 for r in v if r['margin'] > 0)
    out.append(dict(sig=sg, fam=s0['fam'], n=len(v), win=w, med=round(st.median(r['margin'] for r in v))))
    print(f"{sg:9s}{s0['fam']:13s}{len(v):4d}{w:5d}{w/len(v):7.0%}{st.median(r['margin'] for r in v):9.0f}  {', '.join(s0['top'][:2])}")
json.dump(out, open(HERE/'live_vs_style.json', 'w'), ensure_ascii=False)
# 未匹配的看开局形态分布
c = collections.Counter(r['sig'] for r in un)
print("\n未匹配签名 Top8:", c.most_common(8))
wl = sum(1 for r in un if r['margin'] > 0)
print(f"未匹配合计 我方 {wl}/{len(un)} = {wl/max(1,len(un)):.0%}")
