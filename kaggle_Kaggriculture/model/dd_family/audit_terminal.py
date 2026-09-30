"""Capture live final-day stocks under an unchanged candidate and dynamic opponent."""
from pathlib import Path
import collections,contextlib,copy,gzip,importlib.util,io,json,sys,concurrent.futures
B=Path(__file__).resolve().parent

def run(task):
 version,seed=task
 with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
  from kaggle_environments import make
  from kaggle_environments.agent import get_last_callable
 sys.path.insert(0,str(B/version));import main,action_space as space,rules
 policy=main.Agent();proto=json.loads((B/'protocol.json').read_text());op=next(p for p in proto['opponents'] if p['name']=='y68v');other=get_last_callable((B/op['file']).read_text(),path=str(B/op['file']))
 env=make('kaggriculture',configuration={'seed':seed});env.reset(2);states={}
 for t in range(719):
  obs=[copy.deepcopy(s.observation) for s in env.state]
  for o in obs:o['step']=t
  if t==696:states['start']=copy.deepcopy(obs[0])
  env.step([policy.act(obs[0]),other(obs[1])])
 states['end']=copy.deepcopy(env.state[0].observation);out={}
 for label,obs in states.items():
  products=collections.Counter();farms=obs['farms'];tiles=[]
  for y,row in enumerate(farms[0]['tiles']):
   for x,tile in enumerate(row):
    if not isinstance(tile,dict) or tile.get('yield_units',0)<=0:continue
    if tile.get('crop'):
     if 29-tile['planted_day']<space.CROP_FIRST_YIELD_DAY[tile['crop']]:continue
     item=tile['crop']
    elif tile.get('animal'):item=rules.ANIMALS[tile['animal']]['product']
    else:continue
    products[item]+=tile['yield_units'];tiles.append({'xy':[x,y],'item':item,'quantity':tile['yield_units'],'quote_value':tile['yield_units']*obs['market']['prices'][item]})
  out[label]={'cash':farms[0]['money'],'mature_products':dict(products),'quote_value':sum(r['quote_value'] for r in tiles),'tiles':tiles,'bags':obs['private']['inventories'],'shed':obs['private']['shed']}
 out.update(seed=seed,version=version,final_reward=env.state[0].reward,opponent_reward=env.state[1].reward)
 d=B/'terminal_audit'/version;d.mkdir(parents=True,exist_ok=True)
 with gzip.open(d/f'{seed}_states.json.gz','wt') as f:json.dump(states,f)
 (d/f'{seed}_summary.json').write_text(json.dumps(out,indent=2)+'\n')
 return {k:v for k,v in out.items() if k not in ['start','end']}|{label:{k:v for k,v in out[label].items() if k not in ['tiles','bags','shed']} for label in ['start','end']}
if __name__=='__main__':
 version=sys.argv[1];seeds=list(map(int,sys.argv[2:]))
 with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
  for r in pool.map(run,[(version,s) for s in seeds]):print(json.dumps(r),flush=True)
