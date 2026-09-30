"""Reproduce saved games and inspect day-opening hire decisions on actual student states."""
from pathlib import Path
import concurrent.futures,contextlib,copy,gzip,hashlib,io,json,sys
import numpy as np
B=Path(__file__).resolve().parent

def run(task):
 version,seed=task;seat=0;sys.path.insert(0,str(B/version));import action_space as A,rules,task_features as F,tree_runtime
 with gzip.open(B/version/'runs/development01/games'/f'y68v_{seed}_{seat}.json.gz','rt') as f:saved=json.load(f)
 with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
  from kaggle_environments import make
  from kaggle_environments.agent import get_last_callable
 op=next(r for r in json.loads((B/'protocol.json').read_text())['opponents'] if r['name']=='y68v');p=B/op['file'];assert hashlib.sha256(p.read_bytes()).hexdigest()==op['sha256'];other=get_last_callable(p.read_text(),path=str(p));env=make('kaggriculture',configuration={'seed':seed},debug=False);env.reset(2);model=tree_runtime.Model(B/version/'market_policy.npz');rows=[]
 for t in range(719):
  obs=copy.deepcopy(env.state[seat].observation);obs['step']=t;own=saved['trace'][t]['action']
  if t%24==0:
   shadow=copy.deepcopy(obs);farm=A.own_farm(shadow);priv=shadow['private'];goals={int(k):tuple(v) for k,v in saved['trace'][t]['diagnostic']['goals'].items()}
   for i,a in enumerate([own['farmer'],*own['hands']]):rules._apply_unit_action(farm,priv,i,a,10,t//24,24,100)
   probes={}
   for label,intents in [('actual_commitments',goals),('empty_commitments',{})]:
    probs=model.predict(F.market_features(shadow,0,[],intents)[None,:])[0];scores={A.MARKET_TOKENS[int(c)]:float(p) for c,p in zip(model.a['classes'],probs)};probes[label]={'hire_probability':scores.get('HIRE',0),'stop_probability':scores.get('STOP',scores.get('PASS',scores.get(A.MARKET_TOKENS[0],0))),'top3':sorted(scores.items(),key=lambda kv:-kv[1])[:3]}
   daily=saved['trace'][t:min(t+24,719)];tiles=[v for row in farm['tiles'] for v in row if isinstance(v,dict)];rows.append({'day':t//24,'start_cash':float(A.own_farm(obs)['money']),'first_hire_cost':rules._hire_cost(0),'first_hire_affordable':A.own_farm(obs)['money']>=rules._hire_cost(0),'hire_requests':sum(a[0]=='HIRE' for r in daily for a in r['action']['market']),'hands_at_hour22':saved['daily'][t//24]['hands'],'animals_at_open':sum(bool(v.get('animal')) for v in tiles),'plants_at_open':sum(bool(v.get('crop')) for v in tiles),'goals':goals,'classifier':probes})
  other_obs=copy.deepcopy(env.state[1-seat].observation);other_obs['step']=t;env.step([own,other(other_obs)]);assert float(env.state[seat].observation.farms[seat]['money'])==saved['trace'][t]['cash']
 assert [float(s.reward) for s in env.state]==[saved['own_cash'],saved['opponent_cash']]
 result={'version':version,'seed':seed,'seat':seat,'exact_saved_719_cash_and_final_rewards':True,'days':rows};(B/'diagnostics'/f'{version}_{seed}_staffing.json').write_text(json.dumps(result,indent=2)+'\n');return {'version':version,'seed':seed,'zero_hire_asset_days':[r['day'] for r in rows if r['hire_requests']==0 and r['first_hire_affordable'] and r['animals_at_open']+r['plants_at_open']>0]}
if __name__=='__main__':
 versions=sys.argv[1:] or ['ddbo'];tasks=[(v,s) for v in versions for s in range(919260010,919260014)]
 with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:rows=list(pool.map(run,tasks))
 (B/'diagnostics'/('staffing_'+'_'.join(versions)+'_summary.json')).write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
