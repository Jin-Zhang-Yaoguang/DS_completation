import gc, glob, json, os, textwrap, warnings
from datetime import timezone
warnings.filterwarnings('ignore', message='Glyph')
import numpy as np
import pandas as pd
import pyarrow.dataset as pads
from IPython.display import Markdown, display
hits = glob.glob('/kaggle/input/**/episodes.csv', recursive=True) + glob.glob('../episodes_dataset/episodes.csv') + glob.glob('../../episodes_dataset/episodes.csv')
if not hits:
    raise FileNotFoundError('episodes.csv not found — attach the kaggriculture-episodes dataset')
BASE = os.path.dirname(hits[0])
eps = pd.read_csv(f'{BASE}/episodes.csv')
agents = pd.read_csv(f'{BASE}/agents.csv')
try:
    teams = pd.read_csv(f'{BASE}/teams.csv')
except FileNotFoundError:
    teams = pd.DataFrame(columns=['team_id', 'team_name', 'ladder_score', 'last_submission'])
NAME = dict(zip(teams.team_id, teams.team_name))
def name_of(tid):
    n = NAME.get(tid, f'team {tid}')
    return n if all((ord(ch) <= 1279 for ch in str(n))) else f'team {tid}'
try:
    feats = pd.read_csv(f'{BASE}/episode_features.csv', usecols=['episode_id'])
    replay_ids = set(feats.episode_id)
except (FileNotFoundError, ValueError):
    replay_ids = set()
    for _shard in sorted(glob.glob(f'{BASE}/replays*.parquet')):
        replay_ids |= set(pd.read_parquet(_shard, columns=['episode_id']).episode_id)
def load_replay(episode_id):
    scanner = pads.dataset(sorted(glob.glob(f'{BASE}/replays*.parquet')), format='parquet').scanner(filter=pads.field('episode_id') == int(episode_id), columns=['replay_json'], batch_size=1)
    blob = scanner.head(1).column('replay_json')[0].as_py()
    del scanner
    gc.collect()
    out = json.loads(blob)
    del blob
    gc.collect()
    return out
eps['has_replay'] = eps.episode_id.isin(replay_ids)
eps['winner_bank'] = eps[['bank_0', 'bank_1']].max(axis=1)
eps['end'] = pd.to_datetime(eps.end_time, format='mixed', utc=True)
ladder = eps[eps.type.eq('EPISODE_TYPE_PUBLIC') & eps.state.eq('COMPLETED') & eps.winner_bank.gt(0)].copy()
ladder_r = ladder[ladder.has_replay]
ladder_r = ladder_r.assign(winner_sub=np.where(ladder_r.bank_0 >= ladder_r.bank_1, ladder_r.sub_0, ladder_r.sub_1))
top_subs = ladder_r.groupby('winner_sub').winner_bank.max().nlargest(3)
FEAT = pd.read_csv(f'{BASE}/episode_features.csv')
FEAT_IX = FEAT.set_index(['episode_id', 'seat'])
CROPCOLS = [c for c in FEAT.columns if c.startswith('plants_')]
def fingerprint_row(episode_id, seat):
    try:
        r = FEAT_IX.loc[int(episode_id), int(seat)]
    except KeyError:
        fallback = globals().get('fingerprint')
        return fallback(episode_id, seat) if fallback else None
    plants = {c.replace('plants_', '').upper(): int(r[c]) for c in CROPCOLS if r[c] > 0}
    return {'hires / day': r.total_hires / 30, 'peak crew': r.peak_crew, 'first land (day)': r.first_land_day, 'plants': plants}
LEAD_ROW = ladder_r[ladder_r.winner_sub.eq(top_subs.index[0]) & ladder_r.winner_bank.eq(top_subs.iloc[0])].iloc[0]
LEAD_SEAT = 0 if LEAD_ROW.bank_0 >= LEAD_ROW.bank_1 else 1
LEAD_FP = fingerprint_row(LEAD_ROW.episode_id, LEAD_SEAT)
AS_OF = eps.end.max()
C_TOP, C_MID, C_LOW, C_ACC = ('#00795F', '#B84A00', '#9E2B72', '#0072B2')
fmt = lambda v: f'{v:,.0f}'
tb_feat = pd.read_csv(f'{BASE}/episode_features.csv')
tb_lad = ladder.copy()
tb_pool = pd.concat([tb_lad.rating_0, tb_lad.rating_1]).dropna()
tb_q = 96
def tb_seats(frame, lo, hi=None):
    out = []
    for s in (0, 1):
        r = frame[f'rating_{s}']
        keep = frame[(r >= lo) & (r <= hi)] if hi else frame[r >= lo]
        out.append(keep[['episode_id', f'team_{s}']].rename(columns={f'team_{s}': 'tb_team'}).assign(seat=s))
    return tb_feat.merge(pd.concat(out), on=['episode_id', 'seat'])
tb_ceiling = int(np.floor(np.nanpercentile(teams.ladder_score.dropna() if teams.ladder_score.notna().sum() >= 200 else tb_pool, tb_q) / 50) * 50)
tb_thr, tb_lowered = (tb_ceiling, False)
for tb_win in (2, 4, 7, 14):
    tb_w = tb_lad[tb_lad.end >= AS_OF - pd.Timedelta(days=tb_win)]
    tb_top = tb_seats(tb_w, tb_thr)
    if len(tb_top) >= 40:
        break
tb_poolw = pd.concat([tb_w.rating_0, tb_w.rating_1]).dropna()
tb_mid_lo, tb_mid_hi = [np.nanpercentile(tb_poolw, q) for q in (45, 55)]
if len(tb_top) < 40:
    tb_lowered = True
    for tb_thr in range(tb_ceiling - 50, int(tb_mid_hi) + 200, -50):
        tb_top = tb_seats(tb_w, tb_thr)
        if len(tb_top) >= 40:
            break
tb_mid = tb_seats(tb_w, tb_mid_lo, tb_mid_hi)
tb_seat_pct = 100 * (tb_poolw >= tb_thr).mean()
tb_teams = tb_top.tb_team.nunique()
tb_mid_teams = tb_mid.tb_team.nunique()
tb_conc = 100 * tb_top.tb_team.value_counts().iloc[0] / len(tb_top) if len(tb_top) else 0
tb_board = int((teams.ladder_score >= tb_thr).sum()) if len(teams) else 0
tb_of = int(teams.ladder_score.notna().sum())
tb_board_pct = 100 * tb_board / tb_of if tb_of else float('nan')
display(Markdown('## Today on the ladder'))
SUBMISSION_ID = int(top_subs.index[0])
mine = ladder_r[ladder_r.sub_0.eq(SUBMISSION_ID) | ladder_r.sub_1.eq(SUBMISSION_ID)].copy()
mine['my_seat'] = mine.sub_1.eq(SUBMISSION_ID).astype(int)
mine['my_bank'] = np.where(mine.my_seat.eq(1), mine.bank_1, mine.bank_0)
vp_val = eps[eps.type.eq('EPISODE_TYPE_VALIDATION') & (eps.sub_0.eq(SUBMISSION_ID) | eps.sub_1.eq(SUBMISSION_ID))]
vp_hits = glob.glob(f'{BASE}/stream_hashes.csv')
if len(vp_val) and vp_hits:
    vp_h = pd.read_csv(vp_hits[0])
    vp_h = vp_h[vp_h.episode_id.isin(set(vp_val.episode_id))]
    vp_w = vp_h.pivot_table(index='episode_id', columns='seat', values='stream_h719', aggfunc='first').dropna()
    if len(vp_w):
        vp_same = int((vp_w[0] == vp_w[1]).sum())
        vp_line = f'identical on **{vp_same} of {len(vp_w)}** (a fixed script does not read the board)' if vp_same else f'different in **all {len(vp_w)}** (the agent reacts to what it sees)'
        display(Markdown(f"One more free reading, from [destbreso's validation-game experiment](https://www.kaggle.com/code/destbreso/kaggriculture-the-free-experiment-you-already-ran): in this submission's self-play validation games the two seats' full action streams are {vp_line}."))
    else:
        display(Markdown('Validation games for this submission are not hashed yet; the purity check appears once the nightly backfill reaches them.'))
lb = teams.dropna(subset=['ladder_score']).sort_values('ladder_score', ascending=False)
if lb.empty:
    last = agents.sort_values('episode_id').groupby('team_id').rating_after.last()
    lb = last.reset_index().rename(columns={'rating_after': 'ladder_score'}).assign(team_name=lambda d: d.team_id.map(lambda t: f'team {t}')).sort_values('ladder_score', ascending=False)
top5 = lb.head(5).iloc[::-1]
ladder0 = eps[eps.type.eq('EPISODE_TYPE_PUBLIC') & eps.state.eq('COMPLETED')]
banks = ladder0[['bank_0', 'bank_1']].max(axis=1).dropna()
fig.patch.set_facecolor('#FBF7EE')
fig.text(0.015, 0.97, 'The Kaggriculture ladder', fontsize=19, weight='bold', color='#2B241D', va='top')
fig.text(0.015, 0.845, f'{len(eps):,} episodes · {len(replay_ids):,} full replays · {len(lb):,} teams', fontsize=11, color='#6B6152', va='top')
_lag_h = (pd.Timestamp.now(tz='UTC') - AS_OF).total_seconds() / 3600
_badge = '#00795F' if _lag_h <= 24 else '#B84A00'
fig.text(0.985, 0.975, f'data through {AS_OF:%b %d · %H:%M UTC}', fontsize=12, weight='bold', color='white', ha='right', va='top', bbox=dict(boxstyle='round,pad=0.45', facecolor=_badge, edgecolor='none'))
gs = fig.add_gridspec(1, 2, width_ratios=[1.15, 1], top=0.72, bottom=0.16, left=0.055, right=0.985, wspace=0.28)
ax1 = fig.add_subplot(gs[0])
ax1.set_facecolor('#FBF7EE')
ax1.hist(banks, bins=28, color='#00795F')
ax1.set_title('Where winning banks land', fontsize=11)
ax1.set_xlabel("winner's final bank")
ax1.set_ylabel('games')
ax1.xaxis.set_major_formatter(lambda v, _: f'{v / 1000:.0f}k' if v else '0')
ax2 = fig.add_subplot(gs[1])
ax2.set_facecolor('#FBF7EE')
ax2.barh(range(len(top5)), top5.ladder_score, color='#B84A00', height=0.62)
ax2.set_yticks(range(len(top5)), [n if len(n) < 19 else n[:17] + '…' for n in top5.team_name], fontsize=9)
ax2.set_title('Top of the leaderboard', fontsize=11)
if top5.ladder_score.nunique() > 1:
    ax2.set_xlim(min(top5.ladder_score) * 0.93, max(top5.ladder_score) * 1.02)
ax2.set_xlabel('skill rating')
display(Markdown(f"<sub>pandas {pd.__version__} · numpy {np.__version__} · executed {pd.Timestamp.now(tz='UTC'):%Y-%m-%d %H:%M} UTC · full run ~1 min</sub>"))
lag_h = (pd.Timestamp.now(tz='UTC') - AS_OF).total_seconds() / 3600
if lag_h > 24:
    display(Markdown(f'> **Heads up: this snapshot is {lag_h / 24:.1f} days behind.** The newest game on record ended {AS_OF:%b %d, %H:%M UTC}, so every number below describes the ladder as it was then, not today. The collector refreshes daily; if this notice is still here tomorrow, the crawl is stuck and I am on it.'))
else:
    display(Markdown(f'*Fresh: newest recorded game ended {AS_OF:%b %d, %H:%M UTC}, {lag_h:.0f}h before this run.*'))
n_subs = pd.unique(agents.submission_id).size
n_teams = pd.unique(agents.team_id).size
val_share = eps.type.eq('EPISODE_TYPE_VALIDATION').mean()
cover = eps.has_replay.mean()
span_h = (eps.end.max() - eps.end.min()).total_seconds() / 3600
summary = pd.DataFrame({'metric': ['episodes', 'with full replay', 'ladder games', 'validation (self-play)', 'submissions seen', 'teams seen', 'ladder time covered'], 'value': [f'{len(eps):,}', f'{len(replay_ids):,} ({cover:.0%})', f'{len(ladder):,}', f"{eps.type.eq('EPISODE_TYPE_VALIDATION').sum():,} ({val_share:.0%})", f'{n_subs:,}', f'{n_teams:,}', f'{span_h:.0f} hours' if span_h <= 72 else f'{span_h / 24:.1f} days']})
display(summary.style.hide(axis='index').set_properties(**{'font-size': '13px'}).set_table_styles([{'selector': 'th', 'props': [('font-size', '13px')]}]))
freq1, width1, unit1 = ('1h', 0.032, 'hour') if span_h <= 72 else ('1D', 0.8, 'day')
by_t = eps.set_index('end').resample(freq1).size()
axes[0].bar(by_t.index, by_t.values, width=width1, color=C_ACC)
axes[0].set_title(f'Episodes recorded per {unit1}')
axes[0].set_ylabel('episodes')
axes[0].tick_params(axis='x', labelsize=8)
games = agents.groupby('submission_id').size().sort_values(ascending=False)
axes[1].hist(games.values, bins=min(20, games.nunique()), color=C_TOP)
axes[1].set_title('Games on record per submission')
axes[1].set_xlabel('games')
axes[1].set_ylabel('submissions')
display(Markdown(f'Coverage is **{cover:.0%}** of episodes; the busiest submission has **{games.max()}** games on record and the median has **{games.median():.0f}**. Validation runs ({val_share:.0%} of rows) are a submission playing itself. Filter them out before comparing strength; the rest of this notebook does.'))
demo_id = int(ladder_r.episode_id.iloc[-1])
demo_row = pads.dataset(sorted(glob.glob(f'{BASE}/replays*.parquet'))).scanner(filter=pads.field('episode_id') == demo_id, columns=['replay_json'], batch_size=1).head(1)
demo = json.loads(demo_row.column('replay_json')[0].as_py())
print(f"episode {demo_id}: {len(demo['steps'])} steps, {len(demo_row.column('replay_json')[0].as_py()) / 1000000.0:.0f} MB of JSON, loaded alone in a fraction of a second")
del demo, demo_row
gc.collect()
ax.scatter(ladder.end, ladder.winner_bank, s=22, alpha=0.55, color=C_ACC, edgecolors='white', lw=0.4)
rec = ladder.loc[ladder.winner_bank.idxmax()]
ax.annotate(f'record: {fmt(rec.winner_bank)}', xy=(rec.end, rec.winner_bank), xytext=(10, 6), textcoords='offset points', fontsize=10, weight='bold', color=C_TOP)
ax.set_yscale('log')
ax.yaxis.set_major_formatter(lambda v, _: f'{v / 1000:g}k' if v >= 1000 else f'{v:g}')
ax.set_ylabel("winner's final bank (log)")
ax.set_xlabel('episode end time (UTC)')
ax.tick_params(axis='x', labelsize=8.5)
ax.set_title(f'Same rules, {ladder.winner_bank.max() / ladder.winner_bank.median():.0f}x spread between median and record')
q = ladder.winner_bank.quantile([0.25, 0.5, 0.9])
display(Markdown(f"The winner's bank across recorded games: **{fmt(q[0.25])}** at p25, **{fmt(q[0.5])}** median, **{fmt(q[0.9])}** at p90. The record of **{fmt(rec.winner_bank)}** is **{rec.winner_bank / q[0.5]:.1f}×** the median win; section 6 tracks how fast that gap moves."))
def money_curve(row, seat):
    return [s[0]['observation']['farms'][seat]['money'] for s in load_replay(row.episode_id)['steps']]
elbows, seen_teams = ({}, set())
for rank, (sub, bank) in enumerate(top_subs.items()):
    row = ladder_r[ladder_r.winner_sub.eq(sub) & ladder_r.winner_bank.eq(bank)].iloc[0]
    seat = 0 if row.bank_0 >= row.bank_1 else 1
    money = money_curve(row, seat)
    team = name_of(row.team_1 if seat else row.team_0)
    if team in seen_teams:
        team = f'{team} (2nd sub)'
    seen_teams.add(team)
    ax.plot(money, lw=2.4, color=[C_TOP, C_ACC, C_LOW][rank], label=f'{team}: {fmt(bank)}')
    cross = next((t for t, m in enumerate(money) if m > bank * 0.1), None)
    if cross is not None:
        elbows[rank + 1] = cross // 24
med_row = ladder_r.loc[(ladder_r.winner_bank - ladder_r.winner_bank.median()).abs().idxmin()]
seat = 0 if med_row.bank_0 >= med_row.bank_1 else 1
ax.plot(money_curve(med_row, seat), lw=2.4, color=C_MID, ls='--', label=f'a median game: {fmt(med_row.winner_bank)}')
ax.legend(fontsize=9.5, frameon=False, loc='upper left')
ax.set_xlabel('turn (24 turns = one in-game day)')
ax.set_ylabel('coins in the bank')
ax.yaxis.set_major_formatter(lambda v, _: f'{v / 1000:.0f}k' if v else '0')
ax.set_title('Top farms stay near zero, then compound')
if elbows:
    display(Markdown('Each top farm crosses a tenth of its final bank on in-game day ' + ', '.join((f'**{d}** (top-{r})' for r, d in elbows.items())) + '. That crossing, not the last-day sprint, is where the game is decided.'))
def fingerprint(episode_id, seat):
    crops, first_land, peak_crew, hires_by_day = ({}, None, 0, {})
    for t, step in enumerate(load_replay(episode_id)['steps']):
        farm = step[0]['observation']['farms'][seat]
        day = t // 24
        hires_by_day[day] = max(hires_by_day.get(day, 0), farm['hires_today'])
        peak_crew = max(peak_crew, len(farm['hands']))
        a = step[seat].get('action') or {}
        for order in a.get('market') or []:
            if isinstance(order, list) and order and (order[0] == 'BUY_LAND') and (first_land is None):
                first_land = day
        for unit in [a.get('farmer') or []] + list(a.get('hands') or []):
            if isinstance(unit, list) and unit and (unit[0] == 'PLANT') and (len(unit) > 1):
                crops[unit[1]] = crops.get(unit[1], 0) + 1
    return {'hires / day': sum(hires_by_day.values()) / max(1, len(hires_by_day)), 'peak crew': peak_crew, 'first land (day)': first_land, 'plants': crops}
rows = []
for rank, (sub, bank) in enumerate(top_subs.items()):
    row = ladder_r[ladder_r.winner_sub.eq(sub) & ladder_r.winner_bank.eq(bank)].iloc[0]
    seat = 0 if row.bank_0 >= row.bank_1 else 1
    rows.append({'who': name_of(row.team_1 if seat else row.team_0), 'bank': bank, **(fingerprint_row(row.episode_id, seat) or {})})
mid_pool = ladder_r[ladder_r.winner_bank.between(*ladder_r.winner_bank.quantile([0.45, 0.55]))]
mid = mid_pool.iloc[0] if len(mid_pool) else ladder_r.loc[(ladder_r.winner_bank - ladder_r.winner_bank.median()).abs().idxmin()]
seat = 0 if mid.bank_0 >= mid.bank_1 else 1
rows.append({'who': f'{name_of(mid.team_1 if seat else mid.team_0)} (mid-ladder)', 'bank': mid.winner_bank, **(fingerprint_row(mid.episode_id, seat) or {})})
fp = pd.DataFrame(rows)
fp['top crop'] = fp.plants.map(lambda d: max(d, key=d.get).title() if d else '—')
fp['plantings'] = fp.plants.map(lambda d: sum(d.values()))
display(fp[['who', 'bank', 'hires / day', 'peak crew', 'first land (day)', 'plantings', 'top crop']].style.hide(axis='index').format({'bank': '{:,.0f}', 'hires / day': '{:.1f}', 'first land (day)': '{:.0f}'}, na_rep='—').set_properties(**{'font-size': '13px'}).set_table_styles([{'selector': 'th', 'props': [('font-size', '13px')]}]))
lead, base = (fp.iloc[0], fp.iloc[-1])
crops_top = [c for c in fp['top crop'][:3].tolist() if c != '—']
uniq_crops = list(dict.fromkeys(crops_top))
lead_land = 'never buys land in this game' if pd.isna(lead['first land (day)']) else f"takes land on day **{lead['first land (day)']:.0f}**"
base_land = 'the mid-ladder farm never buys any' if pd.isna(base['first land (day)']) else f"the mid-ladder farm waits until day {base['first land (day)']:.0f}"
crop_line = f'All of the biggest wins lead with {uniq_crops[0]}.' if len(uniq_crops) == 1 else f"The three biggest wins lead with {', '.join(crops_top)}. The winning crop varies; what repeats is the economics around it, not the plant."
display(Markdown(f"One best game per submission, so read it as a sketch rather than a verdict. Still, the record holder ({lead['who']}) runs a crew of **{lead['peak crew']:.0f}** against the mid-ladder's **{base['peak crew']:.0f}** and {lead_land}; {base_land}. {crop_line}"))
feat = pd.read_csv(f'{BASE}/episode_features.csv')
feat = feat[feat.final_money > 0]
CROP_COLS = [c for c in feat.columns if c.startswith('plants_') and c[7:].upper() in {'CARROT', 'MELON', 'STRAWBERRY', 'TOMATO', 'WHEAT'}]
CAND = ['total_hires', 'peak_crew', 'tiles_planted', 'first_land_day'] + CROP_COLS
rho = feat[CAND + ['final_money']].corr(method='spearman')['final_money'].drop('final_money').sort_values()
labels = [c.replace('plants_', 'plants: ').replace('_', ' ') for c in rho.index]
axes[0].barh(range(len(rho)), rho.values, height=0.7, color=[C_TOP if v > 0 else C_LOW for v in rho.values])
axes[0].set_yticks(range(len(rho)), labels, fontsize=9)
axes[0].axvline(0, color='#2B241D', lw=0.8)
axes[0].set_xlabel('rank correlation with final bank')
axes[0].set_title(f'Labor leads, land timing does not (n={len(feat):,})')
top_feat = rho.abs().idxmax()
axes[1].scatter(feat[top_feat], feat.final_money, s=9, alpha=0.25, color=C_ACC, edgecolors='none')
axes[1].set_xlabel(top_feat.replace('_', ' '))
axes[1].set_ylabel('final bank')
axes[1].yaxis.set_major_formatter(lambda v, _: f'{v / 1000:.0f}k' if v else '0')
axes[1].set_title(f"{top_feat.replace('_', ' ').title()} against the outcome")
best_crop = max(CROP_COLS, key=lambda c: rho.get(c, 0))
display(Markdown(f"Across **{len(feat):,}** seats the strongest signal is **{top_feat.replace('_', ' ')}** (rank correlation **{rho[top_feat]:+.2f}**), with crew size close behind. The day a farm first buys land lands at **{rho['first_land_day']:+.2f}**, near zero, even though land is the thing everyone talks about. Among crops, **{best_crop.replace('plants_', '')}** tracks the bank best (**{rho[best_crop]:+.2f}**). Correlation is not a recipe: heavy hiring may be what winning farms can afford rather than the reason they win. Read it as a list of things worth testing in your own bot, not a ranking of tactics."))
feat_p = pd.read_csv(f'{BASE}/episode_features.csv').drop_duplicates('episode_id')
feat_p = feat_p[feat_p.episode_id.isin(ladder_r.episode_id)]
mkt_goods = sorted({c[len('price_'):-len('_min')] for c in feat_p.columns if c.startswith('price_') and c.endswith('_min')})
base_replay = load_replay(ladder_r.episode_id.iloc[-1])
mkt_base = {g.lower(): p for g, p in base_replay['steps'][0][0]['observation']['market']['prices'].items()}
del base_replay
gc.collect()
mkt_rows = []
for g in mkt_goods:
    mkt_lo = feat_p[f'price_{g}_min'] / mkt_base[g]
    mkt_hi = feat_p[f'price_{g}_max'] / mkt_base[g]
    mkt_rows.append({'good': g, 'lo_p10': mkt_lo.quantile(0.1), 'lo_med': mkt_lo.median(), 'hi_med': mkt_hi.median(), 'hi_p90': mkt_hi.quantile(0.9)})
mkt_rng = pd.DataFrame(mkt_rows)
mkt_rng['band'] = mkt_rng.hi_med - mkt_rng.lo_med
mkt_rng = mkt_rng.sort_values('band')
mkt_y = np.arange(len(mkt_rng))
ax.hlines(mkt_y, mkt_rng.lo_p10, mkt_rng.hi_p90, color=C_ACC, lw=2, alpha=0.35)
ax.hlines(mkt_y, mkt_rng.lo_med, mkt_rng.hi_med, color=C_ACC, lw=7)
ax.axvline(1, color='0.3', lw=1, ls=':')
ax.set_yticks(mkt_y, [g.title() for g in mkt_rng.good])
ax.set_xlabel('episode price range, as a multiple of the opening price')
ax.set_title(f'Which markets move, and which way ({len(feat_p):,} replayed episodes)')
mkt_wild, mkt_calm = (mkt_rng.iloc[-1], mkt_rng.iloc[0])
mkt_down = mkt_rng.loc[mkt_rng.lo_med.idxmin()]
mkt_down_coins = feat_p[f'price_{mkt_down.good}_min'].median()
mkt_note = '' if mkt_down.good == mkt_wild.good else f" Direction is part of the story too: half of all games dump **{mkt_down.good.title()}** down to **{mkt_down_coins:.0f} coin{('s' if mkt_down_coins != 1 else '')}** against an opening price of **{mkt_base[mkt_down.good]}**."
display(Markdown(f"Thick bars span the median episode's low and high; thin lines run from the 10th percentile of the lows to the 90th of the highs. **{mkt_wild.good.title()}** moves the most: the median episode already rides it from **{mkt_wild.lo_med:.2f}x** to **{mkt_wild.hi_med:.1f}x** of its opening price. **{mkt_calm.good.title()}** barely leaves its base.{mkt_note} A market that never moves is one nobody trades hard, and that gap is a strategy signal in itself."))
rec_r = ladder_r.loc[ladder_r.winner_bank.idxmax()]
replay = load_replay(rec_r.episode_id)
prices = {p: [s[0]['observation']['market']['prices'][p] for s in replay['steps']] for p in ('MELON', 'WHEAT')}
base_price = {p: prices[p][0] for p in prices}
for p, c in (('MELON', C_TOP), ('WHEAT', C_MID)):
    ax.plot(prices[p], lw=2.2, color=c, label=f'{p.title()} price')
    ax.axhline(base_price[p], color=c, lw=0.9, ls=':')
ax.set_xlabel('turn')
ax.set_ylabel('market price')
ax.set_title(f'Prices inside the biggest replayed game (episode {rec_r.episode_id})')
ax.legend(fontsize=9.5, frameon=False)
mel, whe = (prices['MELON'], prices['WHEAT'])
wheat_note = ' Wheat climbing that far above base usually means animal farms buying feed faster than the town supplies it.' if max(whe) > base_price['WHEAT'] * 1.4 else ''
display(Markdown(f"In this game melon starts at **{base_price['MELON']}**, bottoms at **{min(mel)}** and peaks at **{max(mel)}**, a swing of {(max(mel) - min(mel)) / base_price['MELON']:.0%} of its base price. Wheat runs **{min(whe)}–{max(whe)}** against a base of **{base_price['WHEAT']}**.{wheat_note} Both lines are a strategy log: you can see when a farm dumps and when it trickles."))
eng_f = pd.read_csv(f'{BASE}/episode_features.csv')
eng_ok = 'engine_version' in eng_f.columns and eng_f.engine_version.notna().mean() >= 0.95 and eng_f.episode_id.isin(ladder_r.episode_id).any()
DAILY = None
try:
    DAILY = pd.read_csv(f'{BASE}/daily_stats.csv', parse_dates=['date'])
except FileNotFoundError:
    pass
span_d6 = (ladder.end.max() - ladder.end.min()).total_seconds() / 86400
freq6 = '2h' if span_d6 <= 3 else '6h' if span_d6 <= 10 else '1D' if span_d6 <= 30 else '3D'
by_h = ladder.set_index('end').winner_bank.resample(freq6).agg(['median', 'max', 'count']).dropna()
solid = by_h[by_h['count'] >= 2]
if len(solid) >= 4:
    by_h = solid
if DAILY is not None and len(DAILY) >= 3:
    ci_rows = []
    for ci_day, ci_g in ladder.set_index('end').winner_bank.resample('1D'):
        ci_v = ci_g.sort_values().to_numpy()
        ci_n = len(ci_v)
        if ci_n >= 8:
            ci_lo = int(max(0, np.floor(ci_n / 2 - 1.96 * np.sqrt(ci_n) / 2)))
            ci_hi = int(min(ci_n - 1, np.ceil(ci_n / 2 + 1.96 * np.sqrt(ci_n) / 2)))
            ci_rows.append((ci_day, ci_v[ci_lo], ci_v[ci_hi]))
    if ci_rows:
        ci_d, ci_l, ci_h = zip(*ci_rows)
        ax.fill_between(ci_d, ci_l, ci_h, color=C_ACC, alpha=0.18, lw=0, label='95% CI of the median')
    ax.plot(DAILY.date, DAILY.median_winner_bank, lw=2.8, color=C_ACC, marker='o', ms=6, label='median winning bank')
    ax.plot(DAILY.date, DAILY.record_bank, lw=2, color=C_TOP, ls='--', label='best single game that day')
else:
    ax.plot(by_h.index, by_h['median'], lw=2.6, color=C_ACC, marker='o' if len(by_h) <= 48 else None, ms=5, label='median winning bank')
    ax.plot(by_h.index, by_h['max'], lw=2, color=C_TOP, ls='--', label='best game so far')
ax.set_ylabel('coins')
ax.set_xlabel('episode end time (UTC)')
ax.yaxis.set_major_formatter(lambda v, _: f'{v / 1000:.0f}k' if v else '0')
ax.set_title('A week of the meta: the middle rises, the ceiling holds')
ax.tick_params(axis='x', labelsize=8.5)
ax.legend(fontsize=9.5, frameon=False)
if DAILY is not None and len(DAILY) >= 3:
    first, last = (DAILY.median_winner_bank.iloc[0], DAILY.median_winner_bank.iloc[-1])
    hours = (DAILY.date.iloc[-1] - DAILY.date.iloc[0]).total_seconds() / 3600
else:
    first, last = (by_h['median'].iloc[0], by_h['median'].iloc[-1])
    hours = (by_h.index[-1] - by_h.index[0]).total_seconds() / 3600
daily = ladder.set_index('end').winner_bank.resample('1D').median().dropna()
move_txt = f': **{(last / first - 1) * 100:+.0f}%**' if first else ''
day_txt = f', and the most recent day moved **{(daily.iloc[-1] / daily.iloc[-2] - 1) * 100:+.0f}%** against the day before' if len(daily) >= 2 and daily.iloc[-2] > 0 else ''
tail_line = 'A bot that stands still slides down the table on its own.' if last >= first else 'The median can dip when new bots flood in; the record line is the bar that matters.'
display(Markdown(f'The median winning bank went from **{fmt(first)}** to **{fmt(last)}** over **{hours:.0f} hours** of ladder{move_txt}{day_txt}. {tail_line}'))
wk_ag = agents.dropna(subset=['rating_after', 'team_id']).merge(ladder[['episode_id', 'end']], on='episode_id').sort_values('end')
wk_now = wk_ag.end.max()
wk_cur = wk_ag[wk_ag.end > wk_now - pd.Timedelta(days=7)]
wk_old = wk_ag[(wk_ag.end <= wk_now - pd.Timedelta(days=7)) & (wk_ag.end > wk_now - pd.Timedelta(days=14))]
wk_a = wk_cur.groupby('team_id').agg(games=('rating_after', 'size'), r_new=('rating_after', 'last'))
wk_b = wk_old.groupby('team_id').agg(prior=('rating_after', 'size'), r_old=('rating_after', 'last'))
wk_m = wk_a.join(wk_b, how='inner')
wk_m = wk_m[(wk_m.games >= 5) & (wk_m.prior >= 3)]
wk_m['delta'] = wk_m.r_new - wk_m.r_old
lad = ladder.dropna(subset=['team_0', 'team_1']).copy()
lad['winner_team'] = np.where(lad.bank_0 >= lad.bank_1, lad.team_0, lad.team_1)
busiest = pd.concat([lad.team_0, lad.team_1]).value_counts().head(6).index.tolist()
mat = pd.DataFrame(np.nan, index=busiest, columns=busiest, dtype=float)
counts = pd.DataFrame(0, index=busiest, columns=busiest, dtype=int)
for a in busiest:
    for b in busiest:
        if a == b:
            continue
        games = lad[lad.team_0.eq(a) & lad.team_1.eq(b) | lad.team_0.eq(b) & lad.team_1.eq(a)]
        if len(games):
            mat.loc[a, b] = games.winner_team.eq(a).mean()
            counts.loc[a, b] = len(games)
labels = [n if len(n) <= 20 else n[:19] + '…' for n in (name_of(t) for t in busiest)]
im = ax.imshow(mat.values, cmap='PuOr', vmin=0, vmax=1)
ax.set_xticks(range(len(busiest)), labels, rotation=45, ha='right', fontsize=9)
ax.set_yticks(range(len(busiest)), labels, fontsize=9)
for i in range(len(busiest)):
    for j in range(len(busiest)):
        v, n = (mat.values[i, j], counts.values[i, j])
        if not np.isnan(v):
            ax.text(j, i, f'{v:.0%}\n({n})', ha='center', va='center', fontsize=8.5, color='white' if abs(v - 0.5) > 0.3 else '#2B241D')
        elif i != j:
            ax.text(j, i, '—', ha='center', va='center', fontsize=9, color='#8A8073')
ax.set_title('Win rate, row team vs column team (games)')
ax.grid(False)
fig.colorbar(im, ax=ax, shrink=0.75, label="row team's win rate")
upsets = [(r, c, mat.loc[r, c]) for r in busiest for c in busiest if not np.isnan(mat.loc[r, c]) and mat.loc[r, c] >= 0.999 and (counts.loc[r, c] >= 2)]
n_blank = int(np.isnan(mat.values).sum()) - len(busiest)
intro_hh = 'Every pair here has met at least once. ' if n_blank == 0 else 'Cells are blank where the pair has not met yet; early ladders are sparse. '
display(Markdown(intro_hh + (f'Clean sweeps so far: ' + '; '.join((f'**{name_of(r)}** over **{name_of(c)}** ({counts.loc[r, c]} games)' for r, c, _ in upsets[:3])) + '.' if upsets else 'No clean sweeps yet among the busiest teams.')))
per_sub = agents[agents.episode_id.isin(ladder.episode_id)].groupby('submission_id').final_bank.agg(['count', 'median', 'std']).query('count >= 4 and median > 0').dropna()
per_sub['cv'] = per_sub['std'] / per_sub['median']
axes[0].scatter(per_sub['median'], per_sub['cv'], s=30, alpha=0.65, color=C_LOW, edgecolors='white', lw=0.5)
axes[0].set_xlabel('median bank')
axes[0].set_ylabel('spread / median')
axes[0].xaxis.set_major_formatter(lambda v, _: f'{v / 1000:.0f}k' if v else '0')
axes[0].set_title('Do stronger bots score more consistently?')
top_ids = per_sub['median'].nlargest(6).index
lad_agents = agents[agents.episode_id.isin(ladder.episode_id)]
box = [lad_agents[lad_agents.submission_id.eq(s)].final_bank.values for s in top_ids]
axes[1].boxplot(box, widths=0.6)
axes[1].set_xticks(range(1, len(top_ids) + 1), [name_of(lad_agents[lad_agents.submission_id.eq(s)].team_id.iloc[0])[:9] + f'\n…{str(s)[-3:]}' for s in top_ids])
axes[1].set_title('Spread of the top six')
axes[1].set_ylabel('final bank')
axes[1].yaxis.set_major_formatter(lambda v, _: f'{v / 1000:.0f}k' if v else '0')
axes[1].tick_params(axis='x', rotation=45, labelsize=8)
display(Markdown(f'Across submissions with at least four games, the typical spread is **{per_sub.cv.median():.0%}** of the median bank (worst: **{per_sub.cv.max():.0%}**). One episode proves little, which is why the ladder keeps playing more of them.'))
op_hits = glob.glob(f'{BASE}/stream_hashes.csv')
op_h = pd.read_csv(op_hits[0]) if op_hits else pd.DataFrame(columns=['episode_id', 'seat'])
OP_GATE = 0.95
op_cov = op_h.episode_id.nunique() / max(1, len(eps))
lead_row = fp.iloc[0]
elbow_txt = '' if not elbows else f'day **{min(elbows.values())}**' if min(elbows.values()) == max(elbows.values()) else f'day **{min(elbows.values())}–{max(elbows.values())}**'
land_txt = 'no land purchase at all' if pd.isna(lead_row['first land (day)']) else f"land on day **{lead_row['first land (day)']:.0f}**"
crop_txt = f'and the biggest wins all lead with {uniq_crops[0]}' if len(uniq_crops) == 1 else 'while the biggest wins disagree on which crop to lead with'
display(Markdown(textwrap.dedent(f"""\n<a id="s13"></a>\n## Takeaways ({AS_OF:%b %d, %Y} snapshot)\n\n1. The ladder's spread is wide: the record win of **{fmt(rec.winner_bank)}** is\n   **{rec.winner_bank / q[0.5]:.1f}×** the median win of **{fmt(q[0.5])}**.\n2. Big games share one silhouette: reinvest almost everything, then compound. The leaders cross\n   a tenth of their final bank around in-game {elbow_txt}.\n3. The record holder's measurable edge is labor and land: a crew of\n   **{lead_row['peak crew']:.0f}** and {land_txt}, {crop_txt}.\n4. Market prices inside a game are their own strategy log: in the biggest replayed game melon swung\n   **{(max(prices['MELON']) - min(prices['MELON'])) / base_price['MELON']:.0%}** of its base price\n   and wheat ran **{min(prices['WHEAT'])}–{max(prices['WHEAT'])}**.\n\nThe [dataset]({'https://www.kaggle.com/datasets/georgymamarin/kaggriculture-episodes'}) and this\nnotebook both refresh daily, so these numbers re-compute themselves as the meta moves. Build\nsomething on top (a deeper dive, an imitation model, a better fingerprint) and post it; I\nfeature community work on the dataset page. If there is a metric you want tracked here, say so\nin the comments. Replays come from Kaggle's public episode service; credit to the hosts for\nkeeping it open. For the rules behind these curves, see\n[Kaggriculture, Visualized](https://www.kaggle.com/code/georgymamarin/kaggriculture-visualized-what-every-crop-pays).\n\n*— [Georgy Mamarin](https://www.kaggle.com/georgymamarin)*\n""")))