SUBMISSION_ID = 'KING'
MAX_EPISODES = 200
PANEL_EPISODES = 40
BASELINE_EPISODES = 12
import json, collections
import numpy as np
import pandas as pd
LIST_URL = 'https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes'
REPLAY_URL = 'https://www.kaggleusercontent.com/episodes/{id}.json'
SAME, MUT, PLAN = ('#DCEEE1', '#B45309', '#0F172A')
if str(SUBMISSION_ID).upper() == 'KING':
    SUBMISSION_ID = _resolve_king()
SUBMISSION_ID = int(SUBMISSION_ID)
PASSY = ('PASS', None)
def macro_indicators(steps, me):
    """The macroeconomic core of one episode, read from the replay: when land
    arrived, the herd, CARE, endgame hygiene, and money by day."""
    land_days, bought = ({}, {})
    care = pass_work = shed_cap = floor_sells = 0
    for t, s in enumerate(steps):
        obs = s[me]['observation']
        day = obs.get('day', t // 24)
        farm = obs['farms'][me]
        act = s[me]['action'] or {}
        priv = obs.get('private') or {}
        shed = priv.get('shed') or {}
        prices = obs['market']['prices']
        land_days.setdefault(len(farm.get('unlocked_quadrants') or []), day)
        tiles = [t2 for row in farm['tiles'] for t2 in row if isinstance(t2, dict)]
        unwatered = sum((1 for t2 in tiles if t2.get('crop') and (not t2.get('watered_today'))))
        ready = sum((1 for t2 in tiles if (t2.get('yield_units') or 0) > 0))
        empties = sum((1 for row in farm['tiles'] for t2 in row if t2 is None))
        seeds = sum((priv.get('seeds') or {}).values())
        work = unwatered + ready + (empties if seeds and day <= 26 else 0)
        farmer = act.get('farmer') or ['PASS']
        hands = act.get('hands') or []
        idle = (1 if farmer[0] in PASSY else 0) + max(0, len(farm.get('hands') or []) - len([h for h in hands if h]))
        if work > 0 and idle:
            pass_work += min(idle, work)
        if farmer[0] == 'CARE':
            care += 1
        care += sum((1 for h in hands if h and h[0] == 'CARE'))
        if sum((v for k, v in shed.items() if k not in ('COW', 'GOOSE', 'SHEEP'))) >= 100:
            shed_cap += 1
        for mo in act.get('market') or []:
            if mo and mo[0] == 'BUY_ANIMAL':
                bought[mo[1]] = bought.get(mo[1], 0) + 1
            if mo and mo[0] == 'SELL' and (prices.get(mo[1], 0) <= 2):
                floor_sells += 1
    last = steps[-1][me]['observation']
    lp = last['market']['prices']
    lpriv = last.get('private') or {}
    stranded = sum((v * lp.get(k, 0) for k, v in (lpriv.get('shed') or {}).items() if k not in ('COW', 'GOOSE', 'SHEEP')))
    for inv in lpriv.get('inventories') or []:
        stranded += sum((v * lp.get(k, 0) for k, v in (inv or {}).items() if k not in ('COW', 'GOOSE', 'SHEEP')))
    fallow = []
    for t in range(25 * 24, len(steps), 24):
        obs = steps[t][me]['observation']
        if sum((obs.get('private', {}).get('seeds') or {}).values()):
            fallow.append(sum((1 for row in obs['farms'][me]['tiles'] for t2 in row if t2 is None)))
    money = [steps[min(d * 24, len(steps) - 1)][me]['observation']['farms'][me].get('money') or 0 for d in range(30)]
    money.append(steps[-1][me]['reward'] or 0)
    return dict(land2=land_days.get(2), land3=land_days.get(3), land4=land_days.get(4), care=care, herd=bought, fallow_late=round(sum(fallow) / len(fallow), 1) if fallow else 0, stranded=round(stranded), pass_work=pass_work, shed_cap_turns=shed_cap, floor_sells=floor_sells, money_by_day=money)
import time as _t
eps = []
eps.sort(key=lambda e: e.get('endTime') or '', reverse=True)
mine = []
for e in eps[:MAX_EPISODES]:
    seats = {a.get('index') or 0: a for a in e['agents']}
    me = next((i for i, a in seats.items() if a.get('submissionId') == SUBMISSION_ID))
    mine.append(dict(episode=e['id'], seat=me, opp_sub=seats[1 - me].get('submissionId'), opp_score=seats[1 - me].get('updatedScore'), bank=seats[me].get('reward') or 0, margin=(seats[me].get('reward') or 0) - (seats[1 - me].get('reward') or 0)))
if not mine:
    raise SystemExit(f'no completed episodes yet for submission {SUBMISSION_ID}; a brand-new submission gets its first ones within hours')
traj = []
for e in sorted(eps, key=lambda e: e.get('endTime') or ''):
    seats = {a.get('index') or 0: a for a in e['agents']}
    me = next((i for i, a in seats.items() if a.get('submissionId') == SUBMISSION_ID), None)
    if me is not None and seats[me].get('updatedScore') is not None:
        traj.append(seats[me]['updatedScore'])
mg = sorted((m['margin'] for m in mine))
W = sum((1 for m in mine if m['margin'] > 0))
L = sum((1 for m in mine if m['margin'] < 0))
print(f'submission {SUBMISSION_ID}: {len(eps)} episodes on the ladder, reading the newest {len(mine)}')
print(f'W{W}-L{L}-T{len(mine) - W - L}, margin median {mg[len(mg) // 2]:+,.0f}, worst {mg[0]:+,.0f}, best {mg[-1]:+,.0f}')
chron = sorted(mine, key=lambda m: m['episode'])
cols = ['#4c9f70' if m['margin'] > 0 else '#c44536' if m['margin'] < 0 else '#8a8f98' for m in chron]
axL.bar(range(1, len(chron) + 1), [m['margin'] for m in chron], color=cols, width=0.8)
axL.axhline(0, color='#222', lw=0.8)
axL.set_xlabel('episode, in play order')
axL.set_ylabel('margin (you minus rival)')
axL.set_title(f'submission {SUBMISSION_ID}: margin per episode (green wins, red losses, grey exact ties)', fontsize=9, loc='left')
PASS = {'farmer': ['PASS'], 'hands': [], 'market': []}
Z = lambda: [[0] * 10 for _ in range(10)]
OCC, PRES, UNLOCKED = (Z(), Z(), Z())
OCC_DAY = {}
OCC_HALF, PRES_HALF = ([Z(), Z()], [Z(), Z()])
rows = []
if not rows:
    raise SystemExit('no replays could be fetched; the CDN may be briefly unavailable, rerun')
rows.sort(key=lambda r: (r['pair'], r['episode']))
print(f"{len(rows)} replays loaded, {len({r['pair'] for r in rows})} distinct shop pairs")
AUTHOR_TEAM = next((r.get('team') for r in rows if r.get('team')), '?')
_slug = _author_slug(AUTHOR_TEAM)
_who = f'**{AUTHOR_TEAM}** ([@{_slug}](https://www.kaggle.com/{_slug}))' if _slug else f'**{AUTHOR_TEAM}**'
from IPython.display import Markdown as _MD, display as _disp
_disp(_MD(f'> This x-ray reads the live play of {_who} (submission {SUBMISSION_ID}), resolved from the ladder at run time. If that is you: hello, it is meant as a compliment, and the comment box below is yours.'))
BAND_EDGES = [(0, 1200), (1200, 1600), (1600, 2000), (2000, 2400), (2400, 2800), (2800, 10 ** 9)]
BAND_LABELS = ['<1200', '1200-1599', '1600-1999', '2000-2399', '2400-2799', '2800+']
def _band(score):
    if score is None:
        return None
    for (lo, hi), lab in zip(BAND_EDGES, BAND_LABELS):
        if lo <= score < hi:
            return lab
    return None
_cells = {}
for r in rows:
    b = _band(r.get('opp_score'))
    if b is None or r['pair'] == '?':
        continue
    w, nn = _cells.get((r['pair'], b), (0, 0))
    _cells[r['pair'], b] = (w + (1 if r['margin'] > 0 else 0), nn + 1)
_worlds = sorted({k[0] for k in _cells}, key=lambda pr: -sum((_cells.get((pr, b), (0, 0))[1] for b in BAND_LABELS)))
_tbl, _weak = ([], [])
for pr in _worlds:
    row = {'world': pr.replace('__', ' | ')}
    tw = tn = 0
    for b in BAND_LABELS:
        w, nn = _cells.get((pr, b), (0, 0))
        row[b] = f'{w}/{nn}' if nn else '·'
        tw += w
        tn += nn
    row['TOTAL'] = f'{tw}/{tn} = {tw / tn:.0%}'
    if tn >= 4 and tw / tn < 0.5:
        _weak.append((pr.replace('__', ' | '), tw, tn))
    _tbl.append(row)
_tot_row = {'world': 'BAND TOTAL'}
_gw = _gn = 0
for b in BAND_LABELS:
    w = sum((v[0] for k, v in _cells.items() if k[1] == b))
    nn = sum((v[1] for k, v in _cells.items() if k[1] == b))
    _gw += w
    _gn += nn
    _tot_row[b] = f'{w}/{nn} = {w / nn:.0%}' if nn else '·'
_tot_row['TOTAL'] = f'{_gw}/{_gn} = {_gw / _gn:.0%}'
_tbl.append(_tot_row)
_df = pd.DataFrame(_tbl).set_index('world')
_disp(_df)
if _weak:
    print('weak rows (win rate < 50% on n >= 4): ' + ', '.join((f'{p} ({w}/{n})' for p, w, n in _weak)))
else:
    print('no weak rows at n >= 4: every world with enough games is at or above 50%')
def canon(a):
    if not a:
        return ('PASS', (), ())
    return (tuple(a.get('farmer') or ['PASS']), tuple((tuple(h) for h in a.get('hands') or [])), tuple((tuple(o) for o in a.get('market') or [])))
n = min((len(r['stream']) for r in rows))
modal = []
for t in range(n):
    cnt = collections.Counter((canon(r['stream'][t]) for r in rows))
    modal.append(cnt.most_common(1)[0][0])
mat = []
for r in rows:
    line = []
    for t in range(n):
        a, m = (canon(r['stream'][t]), modal[t])
        line.append(2 if (a[0], a[1]) != (m[0], m[1]) else 1 if a[2] != m[2] else 0)
    mat.append(line)
arr = np.array(mat)
share = collections.Counter((int(c) for c in arr.flatten()))
tot = arr.size
print(f'texture: green {share[0] / tot:.1%}, amber {share[1] / tot:.1%}, navy {share[2] / tot:.1%}')
_pn = min(PANEL_EPISODES, len(rows))
_pidx = sorted(range(len(rows)), key=lambda i: -rows[i]['episode'])[:_pn]
_pw = sorted(_pidx, key=lambda i: (rows[i]['pair'], rows[i]['episode']))
stripe_panel([rows[i] for i in _pw], [mat[i] for i in _pw], f'newest {_pn} of {len(rows)}, rows grouped by world', True)
chrono = sorted(_pidx, key=lambda i: rows[i]['episode'])
stripe_panel([rows[i] for i in chrono], [mat[i] for i in chrono], f'newest {_pn} of {len(rows)}, in play order, oldest at the top', False)
CHANNELS = ('farmer', 'hands', 'market')
def compare_streams(streams):
    n = min((len(s) for s in streams))
    chan = {c: 0 for c in CHANNELS}
    first = None
    varying = 0
    for t in range(n):
        acts = [canon(s[t]) for s in streams]
        if len(set(acts)) > 1:
            varying += 1
            if first is None:
                first = t
            for i, c in enumerate(CHANNELS):
                if len({a[i] for a in acts}) > 1:
                    chan[c] += 1
    return dict(turns=n, varying=varying, frac=varying / max(1, n), first=first, chan=chan)
def classify(c):
    plan_moves = c['chan']['farmer'] + c['chan']['hands']
    if c['varying'] == 0:
        return 'PURE_REPLAY'
    if plan_moves == 0 and c['frac'] < 0.25:
        return 'REPAIRING_SCRIPT'
    if c['frac'] < 0.1:
        return 'REPAIRING_SCRIPT'
    return 'ADAPTIVE'
g = compare_streams([r['stream'] for r in rows])
gcls = classify(g)
print(f"GLOBAL: {gcls}  (varying {g['frac']:.1%}, first divergence t={g['first']}, channels {g['chan']})")
if gcls == 'ADAPTIVE' and g['first'] is not None and (70 <= g['first'] <= 146):
    print('  a plan fork in t=[72,144] tracks the shop draw: that is ROUTING; read the table below')
by_pair = collections.defaultdict(list)
for r in rows:
    by_pair[r['pair']].append(r['stream'])
tbl = []
for pr in sorted(by_pair):
    ss = by_pair[pr]
    if len(ss) < 2:
        tbl.append(dict(world=pr, n=1, cls='(one episode)', vary='', first=''))
        continue
    cw = compare_streams(ss)
    tbl.append(dict(world=pr, n=len(ss), cls=classify(cw), varyf=cw['frac'], vary=f"{cw['frac']:.1%}", first=cw['first']))
wtab = pd.DataFrame(tbl)
verdict = collections.Counter((t['cls'] for t in tbl if t['n'] >= 2))
print(f'within-world verdict: {dict(verdict)}')
multi = [t for t in tbl if t['n'] >= 2]
wtab.drop(columns=['varyf'], errors='ignore')
import hashlib
STRUCT = {'HIRE', 'BUY_LAND', 'BUY_ANIMAL'}
PROV = {'BUY_SEED', 'BUY_PRODUCT'}
def band(stream, day):
    sig = []
    for h in range(1, 5):
        t = day * 24 + h
        a = stream[t] if t < len(stream) else PASS
        m = [[o[0], o[1] if len(o) > 1 else None] for o in a.get('market') or [] if o and o[0] in STRUCT | PROV]
        sig.append([a.get('farmer'), a.get('hands'), m])
    return hashlib.md5(json.dumps(sig, sort_keys=True).encode()).hexdigest()
def barcode(stream):
    return [band(stream, d) for d in range(30)]
kin = []
for r in rows:
    mine_c = [canon(a) for a in r['stream']]
    opp_c = [canon(a) for a in r['opp_stream']]
    n = len(mine_c)
    plan = sum((1 for a, b in zip(mine_c, opp_c) if a[:2] == b[:2])) / n
    whole = sum((1 for a, b in zip(mine_c, opp_c) if a == b)) / n
    mb, ob = (barcode(r['stream']), barcode(r['opp_stream']))
    shared = sum((1 for x, y in zip(mb, ob) if x == y))
    fork = next((d for d, (x, y) in enumerate(zip(mb, ob)) if x != y), None)
    res = 'W' if r['margin'] > 0 else 'L' if r['margin'] < 0 else 'T'
    kin.append(dict(opponent=r['opp'], submission=r['opp_sub'], episode=r['episode'], res=res, margin=r['margin'], plan=round(plan, 3), whole=round(whole, 3), bands=f'{shared}/30', fork_day=fork))
kin.sort(key=lambda k: -k['plan'])
mirrors = [k for k in kin if k['plan'] >= 0.95]
siblings = [k for k in kin if 0.5 <= k['plan'] < 0.95]
print(f'{len(mirrors)} mirror games (plan >= 0.95), {len(siblings)} sibling games (0.50-0.95), {len(kin) - len(mirrors) - len(siblings)} unrelated')
if mirrors:
    mm = [k['margin'] for k in mirrors]
    print(f'against mirrors: {sum((1 for x in mm if x > 0))}W-{sum((1 for x in mm if x < 0))}L-{sum((1 for x in mm if x == 0))}T, margins {sorted(mm)}')
ks = sorted(kin, key=lambda k: k['plan'])
axK.scatter(range(1, len(ks) + 1), [k['plan'] for k in ks], c=['#c44536' if k['plan'] >= 0.95 else '#2a78d6' for k in ks], s=22)
axK.axhline(0.95, color='#222', lw=0.9, ls='--')
axK.text(1.2, 0.9, 'mirror line: plan 0.95', fontsize=8)
axK.set_xlabel('opponents, sorted by kinship')
axK.set_ylabel('plan agreement')
axK.set_ylim(-0.02, 1.06)
axK.set_title('the kinship spectrum', fontsize=9, loc='left')
kdf = pd.DataFrame(kin)
def _kin_tint(row):
    a = 0.04 + 0.32 * min(max(row['plan'], 0.0), 1.0)
    return [f'background-color: rgba(180, 83, 9, {a:.2f})'] * len(row)
kdf.style.apply(_kin_tint, axis=1).format({'margin': '{:+,.0f}'})
PRE = 144
pre_c = [[canon(a)[:2] for a in r['opp_stream'][:PRE]] for r in rows]
def pre_agree(i, j):
    return sum((1 for a, b in zip(pre_c[i], pre_c[j]) if a == b)) / PRE
parent = list(range(len(rows)))
def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x
for i in range(len(rows)):
    for j in range(i + 1, len(rows)):
        if pre_agree(i, j) >= 0.98:
            parent[find(i)] = find(j)
groups = collections.defaultdict(list)
for i in range(len(rows)):
    groups[find(i)].append(i)
mirror_eps = {k['episode'] for k in kin if k['plan'] >= 0.95}
gtab = []
for gid, idxs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
    ms = sorted((rows[i]['margin'] for i in idxs))
    subs = {rows[i]['opp_sub'] for i in idxs}
    names = [rows[i]['opp'] for i in idxs]
    plans = sorted((k['plan'] for k in kin if k['episode'] in {rows[i]['episode'] for i in idxs}))
    Wg = sum((1 for m in ms if m > 0))
    Lg = sum((1 for m in ms if m < 0))
    gtab.append(dict(group=f'G{len(gtab) + 1}', yours='<- your lineage' if any((rows[i]['episode'] in mirror_eps for i in idxs)) else '', games=len(idxs), submissions=len(subs), lead=collections.Counter(names).most_common(1)[0][0], record=f'W{Wg}-L{Lg}-T{len(ms) - Wg - Lg}', margin_med=ms[len(ms) // 2], worst=ms[0], best=ms[-1], plan_to_you=plans[len(plans) // 2] if plans else None))
big = [g for g in gtab if g['games'] >= 2]
print(f'{len(gtab)} genetic groups among {len(rows)} opponents ({len(big)} with 2+ games, {len(gtab) - len(big)} singletons)')
labels = [f"{g['group']} ({g['games']} games, {g['record']})" for g in big]
axG.barh(labels, [g['margin_med'] for g in big], color=[MUT if g['yours'] else '#2a78d6' for g in big], edgecolor='0.7')
axG.axvline(0, color='#222', lw=0.9)
axG.invert_yaxis()
axG.set_xlabel('median margin against the group')
axG.set_title('genetic groups with 2+ games (amber = contains your lineage)', fontsize=9, loc='left')
pd.DataFrame(gtab)
def q(vals, p):
    v = sorted(vals)
    return v[min(len(v) - 1, int(p * len(v)))]
M = [r['macro'] for r in rows]
herd_med = {a: q([m['herd'].get(a, 0) for m in M], 0.5) for a in ('COW', 'SHEEP', 'GOOSE')}
def mrow(label, vals, ref):
    vv = [v for v in vals if v is not None]
    if vv:
        print(f'  {label:<30} {q(vv, 0.5):>9,.0f} [{q(vv, 0.1):,.0f}, {q(vv, 0.9):,.0f}]    ref {ref}')
print('macro profile, median [p10, p90]; ref = the measured #1 shape')
mrow('2nd quadrant, day', [m['land2'] for m in M], '5')
mrow('care actions', [m['care'] for m in M], '280')
print(f"  {'herd bought (median)':<30} COW {herd_med['COW']}  SHEEP {herd_med['SHEEP']}  GOOSE {herd_med['GOOSE']}    ref 7 COW")
mrow('endgame fallow tiles d25-29', [m['fallow_late'] for m in M], '13')
mrow('stranded $ at the bell', [m['stranded'] for m in M], '442')
mrow('pass-with-work unit-turns', [m['pass_work'] for m in M], 'low')
mrow('shed-at-cap turns', [m['shed_cap_turns'] for m in M], '0')
mrow('floor sells (price <= 2)', [m['floor_sells'] for m in M], '0')
days = list(range(31))
for r in rows:
    ax2.plot(days, r['macro']['money_by_day'], color=PLAN, alpha=0.15, lw=0.8)
med = [q([r['macro']['money_by_day'][d] for r in rows], 0.5) for d in days]
ax2.plot(days, med, color=MUT, lw=2.2, label='median')
ax2.set_xlabel('in-game day')
ax2.set_ylabel('money')
ax2.set_title(f'submission {SUBMISSION_ID}: money by day, one line per episode', fontsize=9, loc='left')
ax2.legend(frameon=False, fontsize=8)
import random
LEADER_REF = json.loads('{"land2": [5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5], "land3": [8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 9, 9, 8, 8, 8, 8, 10, 8, 8, 9, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 9, 8, 8, 8, 8, 8, 9, 9, 8, 8, 8, 9, 8, 8, 8, 8, 8, 9, 8, 9, 8, 8, 9, 8, 8, 8, 8, 9, 8, 8, 8, 8, 8, 8, 8, 9, 8, 8, 8, 8, 9, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 9, 8, 9, 8, 8, 9, 9, 8, 8, 8, 8, 9, 8, 8, 8, 9, 8, 8, 8, 8, 9, 8, 9, 8, 9, 8, 9, 8, 8, 9, 8, 10, 8, 9, 8, 8, 8, 9, 8, 8, 8, 9, 10, 10, 8, 8, 8, 8, 8, 8, 8, 8, 9, 8, 8, 10, 8, 8, 8, 8, 9, 9, 8, 8, 8, 8, 8, 8, 8, 8, 9, 9, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 10, 8, 8, 8, 8, 8, 8, 8, 8, 9, 9, 8, 9, 8, 8, 9, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 9, 9, 8, 8, 9, 9, 8, 8, 8, 8, 9, 8, 9, 9, 8, 8, 8], "pass_work": [335, 339, 334, 326, 335, 336, 326, 336, 332, 330, 339, 346, 331, 340, 319, 331, 332, 322, 323, 324, 325, 329, 333, 337, 339, 342, 321, 332, 331, 317, 322, 320, 329, 325, 329, 324, 316, 320, 326, 328, 324, 322, 323, 320, 331, 321, 322, 316, 321, 323, 319, 325, 315, 328, 319, 326, 318, 314, 336, 316, 321, 321, 318, 321, 317, 325, 329, 319, 314, 317, 324, 331, 318, 320, 322, 324, 325, 328, 320, 316, 330, 317, 319, 313, 327, 325, 325, 323, 334, 318, 314, 327, 326, 322, 325, 317, 332, 317, 316, 324, 328, 313, 324, 316, 317, 328, 341, 337, 331, 325, 348, 341, 338, 328, 339, 337, 333, 331, 331, 328, 335, 328, 326, 333, 326, 336, 340, 330, 324, 341, 336, 329, 332, 332, 347, 326, 356, 336, 348, 338, 327, 331, 329, 326, 325, 333, 327, 337, 339, 331, 326, 329, 326, 331, 330, 343, 339, 320, 337, 324, 334, 335, 343, 328, 331, 330, 332, 335, 335, 351, 326, 332, 327, 321, 336, 332, 330, 333, 341, 344, 324, 328, 328, 340, 331, 337, 333, 328, 345, 332, 338, 338, 338, 330, 333, 331, 324, 347, 355, 341, 335, 348, 335, 348, 330, 341, 326, 328, 330, 336, 332, 330, 337, 332, 356, 328, 335, 330, 336, 333, 340, 339, 333, 325, 361, 339, 332, 329, 338, 333, 339, 330, 330, 348, 329, 336, 353, 340, 348, 340, 346, 328, 329, 331, 327], "fallow_late": [9.0, 30.8, 15.0, 9.0, 11.2, 16.6, 9.6, 17.6, 10.2, 10.6, 22.8, 12.4, 16.0, 21.4, 0, 21.4, 10.6, 9.6, 15.2, 12.2, 11.4, 7.8, 16.2, 14.2, 11.2, 8.4, 13.0, 13.2, 10.6, 7.4, 9.8, 14.2, 16.2, 13.0, 16.6, 16.2, 12.0, 13.0, 12.8, 14.2, 10.2, 14.0, 11.2, 13.0, 12.6, 12.0, 7.8, 12.0, 8.5, 11.0, 13.6, 1.0, 12.4, 13.0, 9.0, 12.8, 15.8, 15.2, 8.6, 10.8, 15.2, 16.6, 11.4, 13.4, 10.4, 4.5, 15.0, 18.4, 10.8, 15.2, 12.0, 14.4, 13.0, 14.4, 15.4, 12.2, 14.0, 16.6, 11.6, 10.6, 14.4, 14.6, 13.0, 16.2, 12.0, 17.2, 10.6, 7.6, 15.0, 10.0, 15.6, 13.4, 15.6, 13.2, 17.6, 13.4, 14.4, 11.2, 14.0, 13.4, 11.8, 10.8, 12.4, 17.0, 10.4, 10.4, 10.4, 12.6, 9.8, 10.8, 13.4, 12.8, 14.8, 11.4, 14.6, 17.2, 16.0, 17.2, 10.0, 10.6, 10.2, 8.0, 12.8, 15.8, 11.2, 15.0, 14.0, 15.4, 9.0, 14.4, 10.6, 11.8, 11.0, 20.0, 12.8, 9.0, 19.0, 11.2, 17.4, 11.8, 14.4, 13.4, 12.8, 9.6, 8.8, 15.2, 14.4, 8.5, 13.8, 17.2, 12.0, 15.4, 11.6, 6.0, 10.2, 14.6, 26.6, 11.8, 11.8, 11.0, 14.8, 19.6, 29.8, 10.8, 11.0, 15.6, 11.4, 14.6, 15.2, 0, 12.2, 17.6, 12.4, 10.6, 14.8, 1.5, 13.8, 16.6, 15.0, 15.6, 6.0, 15.0, 9.8, 21.2, 16.2, 10.4, 9.6, 10.8, 7.0, 11.0, 10.8, 13.4, 10.4, 9.8, 13.2, 13.6, 8.4, 22.0, 9.6, 18.6, 12.0, 13.2, 13.4, 8.8, 11.6, 16.8, 7.0, 14.4, 16.0, 15.4, 16.6, 13.0, 13.4, 13.6, 14.2, 11.4, 14.4, 13.4, 13.2, 17.6, 14.0, 15.4, 14.0, 7.8, 6.0, 18.2, 14.8, 8.8, 17.2, 11.0, 22.4, 11.4, 6.0, 22.8, 11.8, 18.6, 15.2, 16.6, 13.0, 13.4, 20.8, 10.0, 16.2, 12.2, 11.6], "stranded": [1796, 0, 0, 1129, 132, 616, 1124, 0, 231, 385, 442, 663, 369, 357, 0, 172, 803, 260, 0, 451, 242, 1276, 0, 723, 405, 624, 612, 238, 929, 316, 1591, 1133, 192, 579, 650, 647, 900, 714, 1125, 902, 17, 324, 285, 0, 451, 467, 1002, 271, 681, 40, 408, 0, 329, 183, 282, 637, 2, 276, 204, 112, 168, 0, 1083, 0, 716, 336, 144, 0, 1375, 160, 330, 330, 1, 0, 256, 217, 1878, 0, 4, 320, 301, 346, 0, 638, 0, 220, 64, 1107, 0, 1477, 0, 197, 0, 148, 288, 1016, 0, 288, 35, 256, 905, 226, 270, 3, 598, 1692, 0, 1188, 896, 1448, 946, 1196, 973, 357, 1071, 405, 810, 961, 1184, 1136, 227, 1054, 1047, 470, 7, 358, 1495, 0, 1394, 682, 1008, 1476, 1271, 0, 841, 0, 440, 1155, 589, 750, 193, 156, 1174, 782, 1157, 439, 1069, 0, 459, 467, 1125, 32, 963, 408, 1026, 183, 0, 282, 1346, 852, 30, 272, 0, 571, 632, 351, 364, 371, 1272, 0, 0, 249, 804, 1517, 378, 635, 550, 710, 1080, 0, 411, 760, 526, 0, 843, 1083, 972, 867, 84, 1316, 936, 1420, 1302, 1429, 297, 1780, 168, 0, 0, 168, 582, 870, 668, 666, 656, 1130, 495, 1345, 1053, 789, 219, 0, 1080, 495, 744, 418, 1088, 0, 564, 0, 524, 0, 587, 862, 0, 720, 615, 936, 1, 1060, 0, 0, 210, 0, 507, 424, 870, 212, 0, 622, 410, 1190, 599, 500, 551]}')
dot_rows = [('2nd quadrant settles', 'land2'), ('3rd quadrant settles', 'land3'), ('4th quadrant settles', 'land4'), ('idle-with-work', 'pass_work'), ('fallow tiles, late days', 'fallow_late'), ('stranded at the bell', 'stranded')]
NO_REF_SCALE = {'land4': 'land3'}
SEEN_AT_DAY = {'land4': 18}
def med(v):
    s = sorted(v)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
rng = random.Random(11)
XMAX = 6.0
for i, (lab, key) in enumerate(dot_rows):
    ref_vals = LEADER_REF.get(key) or []
    lm = (med(ref_vals) if ref_vals else med(LEADER_REF[NO_REF_SCALE[key]])) or 1.0
    if key in SEEN_AT_DAY:
        seen = min(SEEN_AT_DAY[key] / lm, XMAX)
        ax4.plot([seen, seen], [i - 0.3, i + 0.3], color='#2a78d6', lw=1.4, ls=(0, (3, 2)))
        ax4.annotate(f'day {SEEN_AT_DAY[key]}', (seen, i - 0.34), fontsize=7.5, color='#2a78d6', ha='center', va='bottom')
    mine_vals = [m[key] for m in M if m.get(key) is not None]
    for vals, colour, dy in ((ref_vals, '#2a78d6', +0.16), (mine_vals, '#eb6834', -0.16)):
        if not vals:
            continue
        xs = [min(v / lm, XMAX) for v in vals]
        ys = [i + dy + rng.uniform(-0.11, 0.11) for _ in xs]
        ax4.scatter(xs, ys, s=9, color=colour, alpha=0.18, linewidths=0)
        mm = min(med(vals) / lm, XMAX)
        ax4.plot([mm, mm], [i + dy - 0.14, i + dy + 0.14], color=colour, lw=2.4)
ax4.axvline(1.0, color='#222', lw=1.1)
ax4.set_yticks(range(len(dot_rows)))
ax4.set_yticklabels([r[0] for r in dot_rows], fontsize=9)
ax4.invert_yaxis()
ax4.set_xlim(-0.15, XMAX + 0.25)
ax4.set_xlabel('multiple of the leader median for that indicator (1 = the leader median)')
ax4.set_title(f'submission {SUBMISSION_ID} vs the leader: distributions, not points', fontsize=9, loc='left')
ax4.legend(handles=[Line2D([], [], marker='o', ls='', color='#2a78d6', label='leader, per episode'), Line2D([], [], marker='o', ls='', color='#eb6834', label='this submission, per episode')], frameon=False, loc='lower right', fontsize=8.5)
def _mf_events(stream, prices_t):
    out = []
    for t, act in enumerate(stream):
        if not isinstance(act, dict):
            continue
        for m in act.get('market') or []:
            if not (isinstance(m, list) and len(m) >= 2):
                continue
            qty = int(m[2]) if len(m) >= 3 and str(m[2]).lstrip('-').isdigit() else 1
            px = (prices_t[t] or {}).get(m[1], 0)
            out.append(dict(t=t, verb=m[0], prod=m[1], qty=qty, px=px, value=qty * px))
    return out
def _mf_craters(sellers, victims, prices_t, window=24, top=60):
    out = []
    for e in sorted((x for x in sellers if x['verb'] == 'SELL'), key=lambda x: -x['value'])[:top]:
        p0 = (prices_t[e['t']] or {}).get(e['prod'], 0)
        later = [o for o in victims if o['verb'] == 'SELL' and o['prod'] == e['prod'] and (e['t'] < o['t'] <= e['t'] + window)]
        if not later:
            continue
        dmg = sum((o['qty'] * max(0, p0 - o['px']) for o in later))
        if dmg <= 0:
            continue
        out.append(dict(t0=e['t'], t1=max((o['t'] for o in later)), prod=e['prod'], dmg=dmg))
    out.sort(key=lambda c: -c['dmg'])
    return out
_mf_r = max(rows, key=lambda r: abs(r['margin']))
_mf_T = len(_mf_r['money_me'])
_mf_me = _mf_events(_mf_r['stream'], _mf_r['prices_t'])
_mf_op = _mf_events(_mf_r['opp_stream'], _mf_r['prices_t'])
_mf_ours = _mf_craters(_mf_me, _mf_op, _mf_r['prices_t'])[:6]
_mf_theirs = _mf_craters(_mf_op, _mf_me, _mf_r['prices_t'])[:6]
_mf_xs = list(range(_mf_T))
_mf_ax.plot(_mf_xs, _mf_r['money_me'], color='#0F172A', lw=1.8, label=f'submission {SUBMISSION_ID}')
_mf_ax.plot(_mf_xs, _mf_r['money_op'], color='#94A3B8', lw=1.4, ls='--', label=f"rival ({_mf_r['opp']})")
for _mf_e in _mf_me:
    if _mf_e['verb'] == 'SELL':
        _mf_c, _mf_mk = ('#2E7D32', 'o')
    elif _mf_e['verb'] in ('BUY_LAND', 'BUY_ANIMAL', 'HIRE'):
        _mf_c, _mf_mk = ('#7B1FA2', 's')
    else:
        _mf_c, _mf_mk = ('#C62828', 'v')
    _mf_t = min(_mf_e['t'], _mf_T - 1)
    _mf_ax.scatter(_mf_t, _mf_r['money_me'][_mf_t], s=16 + _mf_e['value'] / 60, marker=_mf_mk, facecolors='none', edgecolors=_mf_c, linewidths=1.0, alpha=0.75, zorder=4)
for _mf_i, _mf_cr in enumerate(_mf_ours):
    _mf_ax.axvspan(_mf_cr['t0'], _mf_cr['t1'], color='#C62828', alpha=0.1)
    _mf_ax.annotate(f"{_mf_cr['prod'][:5]} -${_mf_cr['dmg']:,.0f} (theirs)", (_mf_cr['t0'], _mf_r['money_me'][min(_mf_cr['t0'], _mf_T - 1)]), textcoords='offset points', xytext=(4, 14 + _mf_i % 3 * 12), fontsize=7, color='#7f1d1d')
for _mf_i, _mf_cr in enumerate(_mf_theirs):
    _mf_ax.axvspan(_mf_cr['t0'], _mf_cr['t1'], color='#1D4ED8', alpha=0.08)
    _mf_ax.annotate(f"{_mf_cr['prod'][:5]} -${_mf_cr['dmg']:,.0f} (ours)", (_mf_cr['t0'], _mf_r['money_op'][min(_mf_cr['t0'], _mf_T - 1)]), textcoords='offset points', xytext=(4, -18 - _mf_i % 3 * 12), fontsize=7, color='#1e3a8a')
_mf_ax.legend(fontsize=8, loc='upper left')
_mf_ax.grid(alpha=0.2)
_mf_ax.set_ylabel('money')
_mf_ax.set_title(f"the decisive episode ({_mf_r['episode']}, margin {_mf_r['margin']:+,.0f}, world {_mf_r['pair']})\ncircle=sell  square=structural  triangle=other buy, size=$ weight;  red span: rival sold into OUR crater,  blue: we into theirs", fontsize=9, loc='left')
_mf_prods = {c['prod'] for c in _mf_ours} | {c['prod'] for c in _mf_theirs}
for _mf_P in sorted(_mf_prods):
    _mf_axp.plot(_mf_xs, [(pr or {}).get(_mf_P) for pr in _mf_r['prices_t']], lw=1.2, label=_mf_P)
for _mf_cr in _mf_ours:
    _mf_axp.axvspan(_mf_cr['t0'], _mf_cr['t1'], color='#C62828', alpha=0.1)
for _mf_cr in _mf_theirs:
    _mf_axp.axvspan(_mf_cr['t0'], _mf_cr['t1'], color='#1D4ED8', alpha=0.08)
if _mf_prods:
    _mf_axp.legend(fontsize=7)
_mf_axp.grid(alpha=0.2)
_mf_axp.set_xlabel('turn')
_mf_axp.set_ylabel('price')
_mf_axp.set_title('price paths of the crater products', fontsize=9, loc='left')
print(f'craters dug by us that the rival sold into: ' + (', '.join((f"{c['prod']} -${c['dmg']:,.0f}" for c in _mf_ours)) or 'none'))
print(f'craters we sold into: ' + (', '.join((f"{c['prod']} -${c['dmg']:,.0f}" for c in _mf_theirs)) or 'none'))
def _bh_corr(a, b):
    xa = [v for row in a for v in row]
    xb = [v for row in b for v in row]
    ma = sum(xa) / len(xa)
    mb = sum(xb) / len(xb)
    num = sum(((p - ma) * (q - mb) for p, q in zip(xa, xb)))
    den = (sum(((p - ma) ** 2 for p in xa)) * sum(((q - mb) ** 2 for q in xb))) ** 0.5
    return None if den == 0 else num / den
def _bh_uniformity(_bh_grid, unlocked):
    vals = [_bh_grid[y][x] for y in range(10) for x in range(10) if unlocked[y][x] > 0]
    tot = sum(vals)
    if not vals or tot == 0:
        return None
    exp = tot / len(vals)
    chi = sum(((v - exp) ** 2 / exp for v in vals))
    top = sum(sorted(vals, reverse=True)[:10])
    return (len(vals), chi / max(1, len(vals) - 1), top / tot, min(10, len(vals)) / len(vals))
def _bh_panel(ax, _bh_grid, title, vmax=None):
    ax.imshow(_bh_grid, cmap='magma', interpolation='nearest', vmin=0, vmax=vmax or max((v for r in _bh_grid for v in r), default=1) or 1)
    ax.set_title(title, fontsize=9)
    ax.set_xticks(range(0, 10, 3))
    ax.set_yticks(range(0, 10, 3))
    ax.tick_params(labelsize=6)
_bh_days = sorted(OCC_DAY)
_bh_thirds = [Z(), Z(), Z()]
for d in _bh_days:
    i = min(2, d * 3 // max(1, len(_bh_days)))
    for y in range(10):
        for x in range(10):
            _bh_thirds[i][y][x] += OCC_DAY[d][y][x]
_PR_WORK = {'PLANT', 'HARVEST', 'FEED', 'CARE', 'COLLECT_FERTILIZER', 'FERTILIZE', 'BUILD_PASTURE', 'BUILD_COOP', 'WATER', 'DIG'}
_PR_CARRY = {'PICKUP', 'PLACE', 'DROP'}
_PR_MOVE = {'NORTH', 'SOUTH', 'EAST', 'WEST'}
_PR_IDLE = {'PASS', 'NONE'}
def _pr_verb(a):
    if not a:
        return 'NONE'
    if isinstance(a, str):
        return a
    return str(a[0]) if isinstance(a, list) and a else 'NONE'
def _pr_bucket(v):
    return 'work' if v in _PR_WORK else 'carry' if v in _PR_CARRY else 'move' if v in _PR_MOVE else 'idle' if v in _PR_IDLE else 'unclassified'
def _pr_day_series(stream):
    """One row per day: the share of that day's unit-turns in each bucket."""
    days = {}
    for t, act in enumerate(stream):
        if not isinstance(act, dict):
            continue
        d = days.setdefault(t // 24, collections.Counter())
        d[_pr_bucket(_pr_verb(act.get('farmer')))] += 1
        for h in act.get('hands') or []:
            d[_pr_bucket(_pr_verb(h))] += 1
    _pr_out = []
    for day in sorted(days):
        b = days[day]
        n = sum(b.values())
        _pr_out.append({'day': day, **{k: b[k] / n if n else 0.0 for k in ('work', 'carry', 'move', 'idle', 'unclassified')}})
    return _pr_out
def _pr_band_of(list_of_series):
    per = {}
    for s in list_of_series:
        for r in s:
            per.setdefault(r['day'], []).append(r)
    _pr_out = {}
    for day, rs in per.items():
        _pr_out[day] = {}
        for k in ('work', 'idle'):
            v = sorted((x[k] for x in rs))
            _pr_out[day][k] = (v[max(0, int(0.1 * len(v)) - 1)], v[len(v) // 2], v[min(len(v) - 1, int(0.9 * len(v)))])
    return _pr_out
_pr_ours = [_pr_day_series(r['stream']) for r in rows]
_pr_unc = sum((x['unclassified'] for s in _pr_ours for x in s))
if _pr_unc:
    print(f'NOTE: {_pr_unc:.2f} day-shares fell in no bucket; a verb this cell does not know')
_pr_king = _resolve_king() if SUBMISSION_ID != 'KING' else SUBMISSION_ID
_pr_band = _pr_band_of(_pr_base)
_pr_med = [{'day': d, **{k: sorted((x[k] for x in [s[d] for s in _pr_ours if d < len(s)]))[len([s for s in _pr_ours if d < len(s)]) // 2] for k in ('work', 'idle')}} for d in sorted({r['day'] for s in _pr_ours for r in s}) if any((d < len(s) for s in _pr_ours))]
for ax, _pr_key in zip(axes, ('idle', 'work')):
    _pr_xs = [r['day'] for r in _pr_med]
    _pr_lo = [_pr_band.get(d, {}).get(_pr_key, (0, 0, 0))[0] for d in _pr_xs]
    _pr_mid = [_pr_band.get(d, {}).get(_pr_key, (0, 0, 0))[1] for d in _pr_xs]
    _pr_hi = [_pr_band.get(d, {}).get(_pr_key, (0, 0, 0))[2] for d in _pr_xs]
    ax.fill_between(_pr_xs, _pr_lo, _pr_hi, alpha=0.25, color='#4c78a8', label=f'{_pr_lab}, 10th-90th pct')
    ax.plot(_pr_xs, _pr_mid, color='#4c78a8', lw=1.1, ls='--', label='their median')
    _pr_ys = [r[_pr_key] for r in _pr_med]
    ax.plot(_pr_xs, _pr_ys, color='#e45756', lw=2.0, label=f'submission {SUBMISSION_ID} (median)')
    _pr_out = [(d, y) for d, y, a, b_ in zip(_pr_xs, _pr_ys, _pr_lo, _pr_hi) if y > b_ or y < a]
    if _pr_out:
        ax.scatter([d for d, _ in _pr_out], [y for _, y in _pr_out], s=64, zorder=5, facecolors='none', edgecolors='#e45756', linewidths=1.8, label=f'outside the band ({len(_pr_out)} days)')
    ax.set_ylabel(f'{_pr_key} share of unit-turns')
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8, loc='upper right')
    ax.set_ylim(bottom=0)
axes[-1].set_xlabel('day of the season')
axes[0].set_title(f'productivity per day: submission {SUBMISSION_ID} against {_pr_lab}', fontsize=11, loc='left')
_pr_tot = collections.Counter()
for _pr_s in _pr_ours:
    for _pr_r in _pr_s:
        for _pr_k in ('work', 'carry', 'move', 'idle'):
            _pr_tot[_pr_k] += _pr_r[_pr_k]
_pr_n = sum(_pr_tot.values()) or 1
print('season-wide split of every unit-turn: ' + '  '.join((f'{_pr_k} {_pr_tot[_pr_k] / _pr_n:.1%}' for _pr_k in ('work', 'carry', 'move', 'idle'))))
_hr_days = list(range(30))
_hr_ours = [sorted((r['hands_me'][d] for r in rows))[len(rows) // 2] for d in _hr_days]
_hr_rows_op = [r['hands_op'] for r in rows]
def _hr_q(d, p):
    v = sorted((x[d] for x in _hr_rows_op))
    return v[min(len(v) - 1, int(p * len(v)))]
_hr_lo = [_hr_q(d, 0.1) for d in _hr_days]
_hr_md = [_hr_q(d, 0.5) for d in _hr_days]
_hr_hi = [_hr_q(d, 0.9) for d in _hr_days]
_hr_ax.fill_between(_hr_days, _hr_lo, _hr_hi, alpha=0.25, color='#4c78a8', label=f'your rivals, 10th-90th pct ({len(rows)} episodes)')
_hr_ax.plot(_hr_days, _hr_md, color='#4c78a8', lw=1.1, ls='--', label='rival median')
_hr_ax.plot(_hr_days, _hr_ours, color='#e45756', lw=2.0, label=f'submission {SUBMISSION_ID} (median)')
_hr_out = [(d, y) for d, y, a, b in zip(_hr_days, _hr_ours, _hr_lo, _hr_hi) if y < a or y > b]
if _hr_out:
    _hr_ax.scatter([d for d, _ in _hr_out], [y for _, y in _hr_out], s=64, zorder=5, facecolors='none', edgecolors='#e45756', linewidths=1.8, label=f'outside the band ({len(_hr_out)} days)')
_hr_ax.set_xlabel('day of the season')
_hr_ax.set_ylabel('hands on the board')
_hr_ax.grid(alpha=0.25)
_hr_ax.legend(fontsize=8, loc='lower right')
_hr_ax.set_title(f'staffing: submission {SUBMISSION_ID} against the rivals it met', fontsize=11, loc='left')
print('field-wide reference (490 seasons): 4 hands to day 4, 8 by day 6, 11 by day 10, 12 from day 13 to the bell; IQR 0-2 hands all season')
if _hr_out:
    print(f"days outside your rivals' band: {[d for d, _ in _hr_out]}")
THRESH = 1.0
WIN = min(20, len(traj) - 1)
import datetime as _dt
ts = sorted((_dt.datetime.strptime(e['endTime'][:19], '%Y-%m-%dT%H:%M:%S') for e in eps if e.get('endTime')))
lab = f'submission {SUBMISSION_ID}'
print(f"{lab}: {len(rows)} episodes, {len({r['pair'] for r in rows})} distinct worlds")
mg2 = sorted((r['margin'] for r in rows))
W2 = sum((1 for r in rows if r['margin'] > 0))
L2 = sum((1 for r in rows if r['margin'] < 0))
print(f'  ledger  W{W2}-L{L2}-T{len(rows) - W2 - L2}, margin median {mg2[len(mg2) // 2]:+,.0f}, worst {mg2[0]:+,.0f}, best {mg2[-1]:+,.0f}')
print(f'  texture green {share[0] / tot:.1%}  amber {share[1] / tot:.1%}  navy {share[2] / tot:.1%}')
print(f"\n  GLOBAL class: {gcls}  (varying {g['frac']:.1%}, first divergence t={g['first']}, channels {g['chan']})")
if gcls == 'ADAPTIVE' and g['first'] is not None and (70 <= g['first'] <= 146):
    print('    NOTE a plan fork at t in [72, 144] with the shop draw is ROUTING, not reactivity; read the within-world table.')
print(f"\n  {'world':<34} {'n':>3} {'class':<17} {'vary':>6} {'first_div':>9}")
for t in tbl:
    if t['n'] < 2:
        print(f"  {t['world']:<34} {t['n']:>3} {'(one episode)':<17}")
    else:
        print(f"  {t['world']:<34} {t['n']:>3} {t['cls']:<17} {t['vary']:>6} {str(t['first']):>9}")
print(f'\n  within-world verdict: {dict(verdict)}')
km = [k for k in kin if k['plan'] >= 0.95]
print(f"  kinship: {len(km)} mirrors, {len([k for k in kin if 0.5 <= k['plan'] < 0.95])} siblings, {len(kin)} opponents read")
print('\n  macro profile, median [p10, p90]; ref = the measured #1 shape')
mrow('2nd quadrant, day', [m['land2'] for m in M], '5')
mrow('care actions', [m['care'] for m in M], '280')
print(f"  {'herd bought (median)':<30} COW {herd_med['COW']}  SHEEP {herd_med['SHEEP']}  GOOSE {herd_med['GOOSE']}    ref 7 COW")
mrow('endgame fallow tiles d25-29', [m['fallow_late'] for m in M], '13')
mrow('stranded $ at the bell', [m['stranded'] for m in M], '442')
if len(traj) >= 4:
    print(f'\n  convergence: {conv_verdict}  (drift {drift:+.2f} pts/episode, {flips} flips, threshold {THRESH}, n={len(traj)}, rating {traj[-1]:,.1f})')
import math
import statistics as _lang_st
LANG_DROP = {'PASS', 'NORTH', 'SOUTH', 'EAST', 'WEST'}
LANG_ARG = {'PLANT', 'PICKUP', 'PLACE'}
LANG_BANDS = [(6, 11), (12, 19), (20, 29)]
def _lang_tok(a):
    toks = []
    for u in [a.get('farmer') or ['PASS']] + list(a.get('hands') or []):
        if not u or u[0] in LANG_DROP:
            continue
        toks.append(f'{u[0]}:{u[1]}' if u[0] in LANG_ARG and len(u) > 1 else u[0])
    for o in a.get('market') or []:
        if not o:
            continue
        if o[0] in ('HIRE', 'BUY_LAND'):
            toks.append(o[0])
        elif len(o) > 1:
            toks.append(f'{o[0]}:{o[1]}')
    return '+'.join(sorted(toks)) if toks else None
def _lang_grams(acts, n=5):
    seq = [(t // 24, tok) for t, a in enumerate(acts) if (tok := _lang_tok(a or {})) and t // 24 >= 6]
    out = {b: set() for b in LANG_BANDS}
    for i in range(len(seq) - n + 1):
        day = seq[i][0]
        for lo, hi in LANG_BANDS:
            if lo <= day <= hi:
                out[lo, hi].add(tuple((t for _, t in seq[i:i + n])))
                break
    return out
def speech_fingerprint(episodes, n=5):
    per = [_lang_grams(a, n) for a in episodes]
    rows_out = {}
    for b in LANG_BANDS:
        counts = collections.Counter()
        for g in per:
            for gram in g[b]:
                counts[gram] += 1
        half = max(2, len(episodes) // 2)
        common = {g for g, c in counts.items() if c >= half}
        rates = [len(g[b] & common) / len(g[b]) for g in per if g[b]]
        total = sum(counts.values())
        Hn = 0.0
        if total and len(counts) > 1:
            H = -sum((c / total * math.log(c / total) for c in counts.values()))
            Hn = H / math.log(len(counts))
        rows_out[b] = {'repeat_rate': round(_lang_st.median(rates), 3) if rates else None, 'norm_entropy': round(Hn, 3), 'distinct': len(counts)}
    return rows_out
def speech_class(fp):
    r = [fp[b]['repeat_rate'] for b in LANG_BANDS]
    if any((x is None for x in r)):
        return 'INSUFFICIENT-SIGNAL'
    if r[0] >= 0.95 and r[1] >= 0.7:
        return 'SCRIPT (a frozen plan; observation changes at most repairs)'
    if r[0] >= 0.5 and r[1] < 0.5:
        return 'BRANCHER (commits to a trunk, forks on what it observes)'
    if r[0] < 0.5:
        return 'SCHEDULER (composes its plan per game)'
    return 'MIXED (a script with adaptive patches, or a composer with rituals)'
if len(rows) < 8:
    print(f'{len(rows)} episodes: below the 8-episode floor for cross-game statistics; raise MAX_EPISODES and rerun rather than reading noise')
else:
    fp = speech_fingerprint([r['stream'] for r in rows])
    print(f'{lab}: cross-game language over {len(rows)} episodes')
    print(f"{'band':>8}{'repeat_rate':>13}{'norm_entropy':>14}{'distinct':>10}")
    for b in LANG_BANDS:
        r_ = fp[b]
        print(f"  d{b[0]:02d}-{b[1]:02d}{str(r_['repeat_rate']):>13}{str(r_['norm_entropy']):>14}{r_['distinct']:>10}")
    print(f'class: {speech_class(fp)}')
    print('anchors: tapes 1.0 everywhere | brancher 0.89/0.15/0 | composer 0.02/0/0 (language only, not strength)')
import itertools
import random as _rnd
_fp12 = speech_fingerprint([r['stream'] for r in rows]) if len(rows) >= 8 else None
_cls12 = speech_class(_fp12) if _fp12 else 'INSUFFICIENT-SIGNAL (fewer than 8 episodes)'