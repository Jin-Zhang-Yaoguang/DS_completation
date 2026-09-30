"""Development-only terminal-day counterfactual; reuse recorded parent prefix, not a full candidate evaluation."""
from pathlib import Path
import collections,concurrent.futures,contextlib,copy,gzip,hashlib,io,json,sys,time
B=Path(__file__).resolve().parent

def run(task):
 seed,seat=task
 with gzip.open(B/'ddbm/runs/development01/games'/f'y68v_{seed}_{seat}.json.gz','rt') as f:saved=json.load(f)
 with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
  from kaggle_environments import make
  from kaggle_environments.agent import get_last_callable
 sys.path.insert(0,str(B/'ddbn'));from main import Agent
 protocol=json.loads((B/'protocol.json').read_text());op=next(x for x in protocol['opponents'] if x['name']=='y68v');p=B/op['file'];assert hashlib.sha256(p.read_bytes()).hexdigest()==op['sha256'];other=get_last_callable(p.read_text(),path=str(p))
 env=make('kaggriculture',configuration={'seed':seed},debug=False);env.reset(2);agent=None;trace=[];times=[]
 for t in range(719):
  obs=[copy.deepcopy(s.observation) for s in env.state]
  for o in obs:o['step']=t
  if t<696:own=copy.deepcopy(saved['trace'][t]['action'])
  else:
   start=time.perf_counter()
   if agent is None:agent=Agent()
   own=agent.act(obs[seat]);times.append(time.perf_counter()-start)
  opposing=other(obs[1-seat]);actions=[None,None];actions[seat]=own;actions[1-seat]=opposing;env.step(actions)
  cash=float(env.state[seat].observation.farms[seat]['money'])
  if t<696:assert cash==saved['trace'][t]['cash'],(seed,seat,t,'parent prefix divergence')
  else:trace.append({'step':t,'action':own,'cash':cash,'diagnostic':copy.deepcopy(agent.last)})
 rewards=[float(s.reward) for s in env.state];assert all(s.status=='DONE' for s in env.state)
 result={'version':'ddbn','kind':'terminal_day_diagnostic_not_full_candidate_evaluation','seed':seed,'seat':seat,'opponent':'y68v','prefix_steps':696,'new_policy_steps':23,'parent_prefix_cash_exact':True,'fresh_policy_at_daily_reset':True,'own_cash':rewards[seat],'opponent_cash':rewards[1-seat],'margin':rewards[seat]-rewards[1-seat],'parent_cash':saved['own_cash'],'parent_margin':saved['margin'],'cash_change':rewards[seat]-saved['own_cash'],'max_terminal_seconds':max(times),'trace':trace}
 p=B/'diagnostics'/f'ddbn_terminal_{seed}_{seat}.json';p.write_text(json.dumps(result,indent=2)+'\n');return {k:v for k,v in result.items() if k!='trace'}
if __name__=='__main__':
 parent=B/'ddbm';child=B/'ddbn';plan=json.loads((parent/'runs/development01/plan.json').read_text())
 assert all(hashlib.sha256((parent/p).read_bytes()).hexdigest()==h for p,h in plan['hashes'].items())
 for p in parent.glob('*.py'):
  if p.name=='maintenance.py':
   expected=p.read_text().replace('def obligations(obs):\n    out=[]','def obligations(obs):\n    # The final recorded turn is 718; day 29 never receives an end-of-day refresh.\n    if int(obs["step"])//24>=29:return []\n    out=[]');assert (child/p.name).read_text()==expected
  else:assert p.read_bytes()==(child/p.name).read_bytes()
 for p in parent.glob('*.npz'):assert p.read_bytes()==(child/p.name).read_bytes()
 hashes={str(p.relative_to(B)):hashlib.sha256(p.read_bytes()).hexdigest() for p in child.iterdir() if p.suffix in ['.py','.json','.npz']}
 with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
  rows=[]
  for row in pool.map(run,[(s,i) for s in range(919260010,919260014) for i in [0,1]]):rows.append(row);print(json.dumps(row),flush=True)
 assert all(hashlib.sha256((B/p).read_bytes()).hexdigest()==h for p,h in hashes.items())
 result={'kind':'terminal_day_diagnostic_not_full_candidate_evaluation','hashes':hashes,'rows':rows,'games':len(rows),'wins':sum(r['margin']>0 for r in rows),'mean_cash':sum(r['own_cash'] for r in rows)/len(rows),'mean_margin':sum(r['margin'] for r in rows)/len(rows),'mean_cash_change':sum(r['cash_change'] for r in rows)/len(rows)}
 (B/'diagnostics/ddbn_terminal_summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['hashes','rows']}))
