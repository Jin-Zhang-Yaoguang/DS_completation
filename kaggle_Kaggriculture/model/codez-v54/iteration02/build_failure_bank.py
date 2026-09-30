from pathlib import Path
import json,collections,hashlib
P=Path(__file__).resolve().parent
reg={r['episode_id']:r for r in json.loads((P/'replay_registry.json').read_text())}
ledgers={r['episode_id']:r for r in map(json.loads,(P/'replay_ledger.jsonl').read_text().splitlines())};assert len(ledgers)==len(reg) and all(r['status']=='ok' and r['ledger_reconciled'] for r in ledgers.values())
diag={r['episode_id']:r for r in json.loads((P/'replay_diagnosis.json').read_text())['episodes']}
routes=collections.defaultdict(list)
for r in map(json.loads,(P/'route_diagnostic.jsonl').read_text().splitlines()):
 assert r['status']=='ok';routes[r['job']['episode_id']].append(r)
out={'scope':'Development bank only: every listed episode has already been inspected; none is a holdout. Cash attribution reconciles actual fills, but product differences alone are not causal strategy effects. Route maxima are hindsight fixed-tape upper-bound diagnostics, not deployable policy results.','episodes':[]}
dest=P/'failure_checkpoints';dest.mkdir(exist_ok=True)
for eid,meta in reg.items():
 if meta['live_margin']>=0:continue
 ledger=ledgers[eid];seat=meta['seat'];by=collections.defaultdict(lambda:[0,0,0.,0.])
 for q in ledger['ledger']:
  k=(q['operation'],q['item']);side=0 if q['player']==seat else 1;by[k][side]+=q['executed_units'];by[k][side+2]+=q['cash_change']
 attribution=[dict(operation=k[0],item=k[1],own_units=v[0],opponent_units=v[1],own_cash=v[2],opponent_cash=v[3],cash_gap_contribution=v[2]-v[3]) for k,v in by.items()]
 assert sum(r['cash_gap_contribution'] for r in attribution)==meta['live_margin']
 raw=json.loads((P/'replays'/f'episode-{eid}-replay.json').read_text());checkpoints=[]
 for window in diag[eid]['largest_cash_gap_widenings']:
  start=max(0,window['end_step']-24);end=window['end_step'];data={'episode_id':eid,'pre_action_step':start,'raw_state':raw['steps'][start],'replay_sha256':meta['replay_sha256'],'resume_method':'Replay original seed and original two-player actions [0, pre_action_step); do not restore RNG by injecting this snapshot. Preserve inventory insertion order.','window_end':end,'window_requests':[raw['steps'][t+1] for t in range(start,end)]}
  fp=dest/f'{eid}-t{start}.json';assert not fp.exists();fp.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')))
  checkpoints.append({'start':start,'end':end,'file':str(fp.relative_to(P)),'sha256':hashlib.sha256(fp.read_bytes()).hexdigest()})
 best=max(routes[eid],key=lambda r:r['margin']) if eid in routes else None
 out['episodes'].append({'episode_id':eid,'opponent':meta['opponent_name'],'opponent_submission_id':meta['opponent_submission_id'],'actual_margin':meta['live_margin'],'cash_attribution':sorted(attribution,key=lambda r:r['cash_gap_contribution']),'checkpoint_windows':checkpoints,'hindsight_route_max':{'route':best['job']['route'],'margin':best['margin'],'tested':len(routes[eid])} if best else None,'source_binding':'50/50 source requests reproduced exactly','suggested_work':'Test a new production plan or timing, existing route set could not win the tape' if best and best['margin']<0 else 'Test route selection on new opponent/seed groups; no promotion from hindsight tape result'})
(P/'failure_bank.json').write_text(json.dumps(out,indent=2,ensure_ascii=False));print('failure episodes',len(out['episodes']),'checkpoints',sum(len(r['checkpoint_windows']) for r in out['episodes']))
