"""Strict gate completeness and reproducible cross-seed trajectory agreement."""
from pathlib import Path
import json,gzip,itertools,hashlib,statistics
import numpy as np
G=Path(__file__).resolve().parent

def stats(vals):
 a=np.asarray(vals,float)
 return {'mean':float(a.mean()),'median':float(np.median(a)),'min':float(a.min()),'max':float(a.max()),'p90':float(np.quantile(a,.9))}
def similarity(rows):
 pairs=[(i,j) for i,j in itertools.combinations(range(len(rows)),2) if rows[i]['seed']!=rows[j]['seed'] and rows[i]['seat']==rows[j]['seat']]
 out={'pair_count':len(pairs),'same_seat_cross_seed':True};n=len(rows)
 for key in ['unit_hash','market_hash','full_hash','position_hash']:
  x=np.asarray([[s[key] for s in r['trace']] for r in rows]);eq=np.asarray([x[i]==x[j] for i,j in pairs]);out[key]=stats(eq.mean(axis=1))
  if key=='unit_hash':
   active=np.asarray([[s['active'] for s in r['trace']] for r in rows]);mask=np.asarray([active[i]|active[j] for i,j in pairs]);valid=mask.sum(axis=1)>0
   out['units_excluding_both_idle']=stats((eq&mask).sum(axis=1)[valid]/mask.sum(axis=1)[valid]);out['unit_daily_mean']=[float(eq[:,d*24:min((d+1)*24,719)].mean()) for d in range(30)]
   out['unit_after_day3_mean']=float(eq[:,72:].mean());out['unit_before_day3_mean']=float(eq[:,:72].mean())
 # Per-actor partial agreement: extra/missing workers count as different.
 # This explains how strict whole-team comparison can be low despite a common routine.
 actor=[];farmer=[]
 for i,j in pairs:
  hits=total=0;f=0
  for a,b in zip(rows[i]['trace'],rows[j]['trace']):
   ua,ub=a['units'],b['units'];total+=max(len(ua),len(ub));hits+=sum(x==y for x,y in zip(ua,ub));f+=ua[0]==ub[0]
  actor.append(hits/total);farmer.append(f/719)
 out['per_actor_agreement']=stats(actor);out['farmer_agreement']=stats(farmer)
 pl=np.asarray([[p['tiles'] for p in r['plan_log']] for r in rows]);out['daily_plan_tile_agreement']=stats([float((pl[i]==pl[j]).mean()) for i,j in pairs])
 return out

def main():
 m=json.loads((G/'freeze.json').read_text());rows=[];expected={(o['model'],s,p) for o in m['opponents'] for s in m['seeds'] for p in m['seats']};found=set()
 for path in sorted((G/'games').glob('*.json.gz')):
  with gzip.open(path,'rt') as f:r=json.load(f)
  key=(r['opponent'],r['seed'],r['seat']);assert key in expected and key not in found,key;found.add(key)
  assert r['statuses']==['DONE','DONE'] and r['steps']==719 and len(r['trace'])==719 and len(r['plan_log'])==30
  assert r['win']==(r['own_cash']>r['opponent_cash'])
  rows.append(r)
 if found!=expected:raise RuntimeError(f'incomplete: {len(found)}/{len(expected)}')
 for fn,h in m['candidate_files'].items():assert hashlib.sha256((G.parent/fn).read_bytes()).hexdigest()==h,fn
 for o in m['opponents']:assert hashlib.sha256(Path(o['frozen']).read_bytes()).hexdigest()==o['sha256'],o['model']
 summaries=[]
 for o in m['opponents']:
  rs=[r for r in rows if r['opponent']==o['model']];win=sum(r['win'] for r in rs);draw=sum(r['draw'] for r in rs)
  summaries.append({'opponent':o['model'],'games':len(rs),'wins':win,'draws':draw,'losses':len(rs)-win-draw,'win_rate':win/len(rs),'mean_cash':statistics.mean(r['own_cash'] for r in rs),'mean_opponent_cash':statistics.mean(r['opponent_cash'] for r in rs),'mean_margin':statistics.mean(r['margin'] for r in rs),'min_margin':min(r['margin'] for r in rs),'max_margin':max(r['margin'] for r in rs),'seat_wins':{str(s):sum(r['win'] for r in rs if r['seat']==s) for s in (0,1)},'escapes':sum(len(r['escapes']) for r in rs),'drought':sum(len(r['drought']) for r in rs),'trajectory':similarity(rs),'gate_pass':win==32,'entrypoints':sorted(set(r['entrypoint'] for r in rs))})
 out={'candidate':'v127a','games':len(rows),'opponent_count':len(summaries),'wins':sum(r['win'] for r in rows),'draws':sum(r['draw'] for r in rows),'gate_pass':all(s['gate_pass'] for s in summaries),'summaries':summaries,'macro_trajectory_mean':statistics.mean(s['trajectory']['unit_hash']['mean'] for s in summaries),'macro_market_mean':statistics.mean(s['trajectory']['market_hash']['mean'] for s in summaries),'macro_full_mean':statistics.mean(s['trajectory']['full_hash']['mean'] for s in summaries),'macro_position_mean':statistics.mean(s['trajectory']['position_hash']['mean'] for s in summaries),'macro_actor_mean':statistics.mean(s['trajectory']['per_actor_agreement']['mean'] for s in summaries),'macro_plan_tile_mean':statistics.mean(s['trajectory']['daily_plan_tile_agreement']['mean'] for s in summaries),'escapes':sum(len(r['escapes']) for r in rows),'drought':sum(len(r['drought']) for r in rows),'day1_zero_hands_games':sum(r['daily'][1]['hands']==0 for r in rows),'day0_zero_cash_games':sum(r['daily'][0]['cash']==0 for r in rows),'escape_step_counts':dict(__import__('collections').Counter(e[0] for r in rows for e in r['escapes'])),'drought_step_counts':dict(__import__('collections').Counter(e[0] for r in rows for e in r['drought'])),'macro_unit_daily_mean':[statistics.mean(s['trajectory']['unit_daily_mean'][d] for s in summaries) for d in range(30)],'all_done':True,'all_hashes_unchanged':True,'no_submission':True}
 (G/'summary.json').write_text(json.dumps(out,indent=2,ensure_ascii=False));print(json.dumps({k:v for k,v in out.items() if k!='summaries'},ensure_ascii=False))
 compact=[{k:v for k,v in r.items() if k!='trace'} for r in rows];(G/'games_summary.json').write_text(json.dumps(compact,ensure_ascii=False))
if __name__=='__main__':main()
