"""Matched V127b attribution and gates; full policies, official interpreter."""
from pathlib import Path
import os,sys,json,time,hashlib,copy,gzip,argparse,traceback,gc
import concurrent.futures
G=Path(__file__).resolve().parent
B=G.parent
sys.path.insert(0,str(B))
import main,executor,executor_a
PLAN=json.loads((G/'plan.json').read_text())
class ControlPolicy:
 def __init__(self,kind):
  self.kind=kind;self.planner=main.Planner('time_tasks' if kind=='time_tasks' else 'neural_tasks');self.reset()
 def reset(self):
  self.executor=executor_a.Executor() if self.kind=='v127a' else executor.Executor('reserve_only' if self.kind=='reserve_only' else 'full');self.plan_log=[]
 def act(self,obs):
  if obs['step']==0:self.reset()
  day=obs['step']//24
  if self.executor.day!=day:
   p=self.planner.plan(obs);self.executor.set_plan(p,day);self.plan_log.append({'day':day,'hands':int(p['hands']),'land':int(p['land']),'tiles':p['tiles'].tolist()})
  return self.executor.act(obs)
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:24]
def one(task):
 gc.collect()
 panel,kind,name,seed,seat=task
 from kaggle_environments import make
 from kaggle_environments.agent import get_last_callable
 start=time.perf_counter();p=main.Agent() if kind=='v127b' else ControlPolicy(kind);path=Path(next(o['frozen'] for o in PLAN['opponents'] if o['model']==name));other=get_last_callable(path.read_text(),path=str(path));entry=other.__name__
 env=make('kaggriculture',configuration={'seed':seed},debug=False);env.reset(2)
 trace=[];daily=[];escapes=[];drought=[];timings=[];opp_times=[]
 for step in range(719):
  obs=[copy.deepcopy(s.observation) for s in env.state]
  for o in obs:o['step']=step
  f=obs[seat]['farms'][seat];tiles=f['tiles'];positions=[f['farmer']]+f['hands']
  t=time.perf_counter();a=p.act(obs[seat]);timings.append(time.perf_counter()-t)
  t=time.perf_counter();b=other(obs[1-seat]);opp_times.append(time.perf_counter()-t)
  units=[a.get('farmer') or ['PASS']]+list(a.get('hands') or [])
  mkt=a.get('market') or []
  trace.append({'step':step,'units':units,'market':mkt,'positions':positions,'unit_hash':digest(units),'market_hash':digest(mkt),'full_hash':digest([units,mkt]),'position_hash':digest(positions),'active':any(u and u[0]!='PASS' for u in units)})
  acts=[None,None];acts[seat]=a;acts[1-seat]=b;env.step(acts)
  new=env.state[seat].observation.farms[seat]
  watered={tuple(positions[i]) for i,u in enumerate(units[:len(positions)]) if u and u[0]=='WATER'}
  for y,row in enumerate(tiles):
   for x,old in enumerate(row):
    if not isinstance(old,dict):continue
    after=new['tiles'][y][x]
    if old.get('animal') and (not isinstance(after,dict) or not after.get('animal')):escapes.append([step,x,y,old['animal']])
    if step%24==23 and old.get('crop') and old.get('consecutive_unwatered',0)>=1 and not old['watered_today'] and (x,y) not in watered and isinstance(after,dict) and after.get('kind')=='WEED':drought.append([step,x,y,old['crop']])
  if step%24==22 or step==718:
   ct=[t for row in new['tiles'] for t in row if isinstance(t,dict)]
   daily.append({'day':step//24,'cash':new['money'],'hands':len(new['hands']),'land':len(new['unlocked_quadrants']),'crops':sum(bool(t.get('crop')) for t in ct),'animals':sum(bool(t.get('animal')) for t in ct)})
  if step<718 and any(s.status!='ACTIVE' for s in env.state):raise RuntimeError(f'early end {step}: {[s.status for s in env.state]}')
 statuses=[str(s.status) for s in env.state];assert statuses==['DONE','DONE'],statuses
 cash=[float(s.reward) for s in env.state];margin=cash[seat]-cash[1-seat]
 out={'candidate':kind,'panel':panel,'opponent':name,'seed':seed,'seat':seat,'entrypoint':entry,'statuses':statuses,'steps':len(trace),'own_cash':cash[seat],'opponent_cash':cash[1-seat],'margin':margin,'win':margin>0,'draw':margin==0,'escapes':escapes,'drought':drought,'daily':daily,'plan_log':p.plan_log,'first_step_seconds':timings[0],'max_step_seconds':max(timings),'opponent_max_seconds':max(opp_times),'elapsed_seconds':time.perf_counter()-start,'trace':trace,'feedback_log':getattr(p.executor,'feedback_log',[]),'executor_stats':dict(p.executor.stats)}
 assert len(p.plan_log)==30
 target=G/panel/'games'/f'{kind}_{name}_{seed}_{seat}.json.gz';target.parent.mkdir(parents=True,exist_ok=True)
 with gzip.open(str(target)+'.tmp','wt') as f:json.dump(out,f,separators=(',',':'))
 os.replace(str(target)+'.tmp',target)
 return {k:v for k,v in out.items() if k not in ['trace','daily','plan_log','feedback_log']}

def run():
 ap=argparse.ArgumentParser();ap.add_argument('--panel',choices=['development','gate','fresh'],required=True);ap.add_argument('--workers',type=int,default=8);a=ap.parse_args();panel=a.panel
 if panel=='development':seeds=PLAN['development_seeds'];kinds=PLAN['development_variants'];ops=PLAN['development_opponents']
 elif panel=='gate':seeds=PLAN['gate_seeds'];kinds=PLAN['gate_variants'];ops=[o['model'] for o in PLAN['opponents']]
 else:seeds=PLAN['fresh_confirmation_seeds'];kinds=PLAN['fresh_variants'];ops=PLAN['fresh_opponents']
 if panel!='development':
  freeze=json.loads((G/'candidate_freeze.json').read_text())
  for f,h in freeze.items():assert hashlib.sha256((B/f).read_bytes()).hexdigest()==h,f
 for o in PLAN['opponents']:assert hashlib.sha256(Path(o['frozen']).read_bytes()).hexdigest()==o['sha256'],o['model']
 tasks=[(panel,k,op,s,seat) for k in kinds for op in ops for s in seeds for seat in [0,1]]
 out=G/panel;out.mkdir(exist_ok=True);tasks=[t for t in tasks if not (out/'games'/f'{t[1]}_{t[2]}_{t[3]}_{t[4]}.json.gz').exists()];print('pending',len(tasks),flush=True)
 with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers) as pool:
  fs={pool.submit(one,t):t for t in tasks}
  for i,fu in enumerate(concurrent.futures.as_completed(fs),1):
   try:r=fu.result()
   except Exception:
    err={'task':fs[fu],'traceback':traceback.format_exc()}
    with (out/'errors.jsonl').open('a') as f:f.write(json.dumps(err)+'\n')
    print(err,flush=True);continue
   with (out/'progress.jsonl').open('a') as f:f.write(json.dumps(r)+'\n')
   print(i,r['candidate'],r['opponent'],r['seed'],r['seat'],round(r['own_cash']),round(r['margin']),len(r['escapes']),len(r['drought']),flush=True)
 if panel!='development':
  for f,h in freeze.items():assert hashlib.sha256((B/f).read_bytes()).hexdigest()==h,f
if __name__=='__main__':run()
