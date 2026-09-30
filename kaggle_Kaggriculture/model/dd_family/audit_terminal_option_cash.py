"""Attribute terminal-day rule ablation with official actual fills and cash conservation."""
from pathlib import Path
import collections,concurrent.futures,contextlib,copy,gzip,hashlib,importlib,io,json,sys
B=Path(__file__).resolve().parent

def run(task):
 version,seed,seat=task
 with gzip.open(B/'ddbm/runs/development01/games'/f'y68v_{seed}_{seat}.json.gz','rt') as f:parent=json.load(f)
 branch=json.loads((B/'diagnostics'/f'ddbn_terminal_{seed}_{seat}.json').read_text()) if version=='ddbn' else None
 with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
  from kaggle_environments import make
  from kaggle_environments.agent import get_last_callable
  eng=importlib.import_module('kaggle_environments.envs.kaggriculture.kaggriculture')
 op=next(x for x in json.loads((B/'protocol.json').read_text())['opponents'] if x['name']=='y68v');p=B/op['file'];assert hashlib.sha256(p.read_bytes()).hexdigest()==op['sha256'];other=get_last_callable(p.read_text(),path=str(p))
 env=make('kaggriculture',configuration={'seed':seed},debug=False);env.reset(2);t_now=[0];flows=collections.Counter();fills=collections.Counter();initial=None;ops=collections.Counter()
 original={n:getattr(eng,n) for n in ['_commit_unit','_do_hire','_do_buy_land']}
 def commit(op,item,price,farm,private,market,capacity=100):
  player=sys._getframe(1).f_locals['player_id'];r=original['_commit_unit'](op,item,price,farm,private,market,capacity)
  if r and player==seat and t_now[0]>=696:flows[op+':'+item]+=price if op=='SELL' else -price;fills[op+':'+item]+=1
  return r
 def hire(farm,private,*args,**kwargs):
  player=sys._getframe(1).f_locals['player_id'];before=farm['money'];r=original['_do_hire'](farm,private,*args,**kwargs)
  if player==seat and t_now[0]>=696:flows['HIRE']+=farm['money']-before
  return r
 def land(farm,*args,**kwargs):
  player=sys._getframe(1).f_locals['player_id'];before=farm['money'];r=original['_do_buy_land'](farm,*args,**kwargs)
  if player==seat and t_now[0]>=696:flows['BUY_LAND']+=farm['money']-before
  return r
 for n,f in {'_commit_unit':commit,'_do_hire':hire,'_do_buy_land':land}.items():setattr(eng,n,f)
 try:
  for t in range(719):
   t_now[0]=t
   if t==696:initial=float(env.state[seat].observation.farms[seat]['money'])
   row=branch['trace'][t-696] if branch and t>=696 else parent['trace'][t];own=copy.deepcopy(row['action']);o=copy.deepcopy(env.state[1-seat].observation);o['step']=t;opp=other(o);acts=[None,None];acts[seat]=own;acts[1-seat]=opp;env.step(acts)
   assert float(env.state[seat].observation.farms[seat]['money'])==row['cash']
   if t>=696:
    for a in [own['farmer'],*own['hands']]:ops[':'.join(map(str,a[:2])) if len(a)>1 and a[0] in ['PLANT','PLACE','PICKUP'] else a[0]]+=1
 finally:
  for n,f in original.items():setattr(eng,n,f)
 final=float(env.state[seat].reward);assert initial+sum(flows.values())==final
 return {'version':version,'seed':seed,'seat':seat,'initial_terminal_cash':initial,'final_cash':final,'terminal_cash_conserved':True,'flows':dict(flows),'fills':dict(fills),'requested_unit_actions':dict(ops)}
if __name__=='__main__':
 with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:rows=list(pool.map(run,[(v,s,i) for v in ['ddbm','ddbn'] for s in range(919260010,919260014) for i in [0,1]]))
 out={'rows':rows,'summary':{}}
 for v in ['ddbm','ddbn']:
  flows=collections.Counter();fills=collections.Counter();ops=collections.Counter()
  for r in rows:
   if r['version']==v:flows.update(r['flows']);fills.update(r['fills']);ops.update(r['requested_unit_actions'])
  out['summary'][v]={'flows':dict(flows),'fills':dict(fills),'requested_unit_actions':dict(ops)}
 (B/'diagnostics/terminal_option_cash.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out['summary'],indent=2))
