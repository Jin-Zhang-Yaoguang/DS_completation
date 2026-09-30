"""Fresh-seed closed-loop games; no fixed opponent replay used as a live policy."""
from pathlib import Path
import json,time,importlib.util,concurrent.futures,statistics,os
import numpy as np
import main
B=Path(__file__).resolve().parent
SEEDS=[926150126,926150127,926150128,926150129]

def game(task):
 from kaggle_environments import make
 from kaggle_environments.envs.kaggriculture import kaggriculture as kg
 seed,seat,name=task
 if name=='starter':opponent=kg.starter_agent
 else:
  p=B/'evaluation_baseline.py'
  spec=importlib.util.spec_from_file_location('eval_frozen_opponent',p);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);opponent=module.agent
 policy=main.NumpyPolicy();env=make('kaggriculture',configuration={'seed':seed},debug=False);env.reset(2);daily=[];start=time.time()
 for step in range(719):
  obs=[s.observation for s in env.state]
  for o in obs:o['step']=step
  actions=[None,None];actions[seat]=policy.act(obs[seat]);actions[1-seat]=opponent(obs[1-seat]);env.step(actions)
  if step%24==22 or step==718:
   f=env.state[seat].observation.farms[seat];tiles=[t for row in f['tiles'] for t in row if isinstance(t,dict)];daily.append({'step':step+1,'money':f['money'],'hands':len(f['hands']),'land':len(f['unlocked_quadrants']),'animals':sum(bool(t.get('animal')) for t in tiles),'crops':sum(t.get('kind')=='PLANT' for t in tiles)})
 status=[str(s.status) for s in env.state];assert status==['DONE','DONE'],status
 cash=[float(s.reward) for s in env.state];times=policy.stats.pop('seconds');return {'seed':seed,'seat':seat,'opponent':name,'own_cash':cash[seat],'opponent_cash':cash[1-seat],'margin':cash[seat]-cash[1-seat],'score':float(cash[seat]>cash[1-seat])+.5*float(cash[seat]==cash[1-seat]),'statuses':status,'daily':daily,'inference':{**policy.stats,'median_seconds':float(np.median(times)),'p99_seconds':float(np.quantile(times,.99)),'max_seconds':max(times)},'elapsed_seconds':time.time()-start}
def main_eval():
 tasks=[(seed,seat,op) for op in ['starter','frozen_local'] for seed in SEEDS for seat in [0,1]];rows=[]
 with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
  for r in pool.map(game,tasks):
   rows.append(r);print(json.dumps({k:v for k,v in r.items() if k not in ['daily','inference']}),flush=True);(B/'closed_loop_games.json').write_text(json.dumps(rows,indent=2))
 summary={}
 for op in ['starter','frozen_local']:
  rr=[r for r in rows if r['opponent']==op];summary[op]={'games':len(rr),'wins':sum(r['score']==1 for r in rr),'draws':sum(r['score']==.5 for r in rr),'mean_cash':statistics.mean(r['own_cash'] for r in rr),'median_cash':statistics.median(r['own_cash'] for r in rr),'mean_margin':statistics.mean(r['margin'] for r in rr),'all_done':all(r['statuses']==['DONE','DONE'] for r in rr)}
 (B/'closed_loop_summary.json').write_text(json.dumps(summary,indent=2));print(summary)
if __name__=='__main__':main_eval()
