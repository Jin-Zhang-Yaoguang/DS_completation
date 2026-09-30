"""Development-only search over feasible replay opening transport cohorts."""
from pathlib import Path
import argparse,concurrent.futures,contextlib,copy,gzip,hashlib,io,json,sys,time
import numpy as np
import evaluate
B=Path(__file__).resolve().parent;D=B/'ddao';OUT=B/'opening_search_ddao'
PORTFOLIOS=[('COW','COW'),('GOOSE','COW'),('COW','GOOSE'),('GOOSE','SHEEP'),('SHEEP','GOOSE'),('GOOSE','GOOSE')]
def game(task):
 a,b,seed=task
 with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
  from kaggle_environments import make
  from kaggle_environments.agent import get_last_callable
 sys.path.insert(0,str(D));import main
 policy=main.Agent();policy.config['initial_cow_cohorts']={'2':a,'3':b}
 proto=json.loads((B/'protocol.json').read_text());op=next(o for o in proto['opponents'] if o['name']=='y68v');path=B/op['file'];assert evaluate.sha(path)==op['sha256'];other=get_last_callable(path.read_text(),path=str(path))
 env=make('kaggriculture',configuration={'seed':seed});env.reset(2);daily=[];times=[]
 for t in range(719):
  obs=[copy.deepcopy(s.observation) for s in env.state]
  for o in obs:o['step']=t
  start=time.perf_counter();act=policy.act(obs[0]);times.append(time.perf_counter()-start);assert len(act['market'])<=10
  env.step([act,other(obs[1])])
  if t%24==22:
   f=env.state[0].observation.farms[0];tiles=[v for row in f['tiles'] for v in row if isinstance(v,dict)]
   daily.append({'day':t//24,'cash':f['money'],'animals':sum(bool(v.get('animal')) for v in tiles),'crops':sum(bool(v.get('crop')) for v in tiles),'land':len(f['unlocked_quadrants'])})
 assert all(s.status=='DONE' for s in env.state)
 own,opp=[float(s.reward) for s in env.state]
 if (a,b)==('COW','COW'):
  p=next((B/'ddam/runs').glob(f'*/games/y68v_{seed}_0.json.gz'));ref=json.load(gzip.open(p,'rt'));assert own==ref['own_cash'] and opp==ref['opponent_cash'],('baseline parity',seed,own,ref['own_cash'],opp,ref['opponent_cash'])
 return {'cohort2':a,'cohort3':b,'seed':seed,'own_cash':own,'opponent_cash':opp,'margin':own-opp,'win':own>opp,'max_seconds':max(times),'daily':daily,'stats':policy.stats}
def run():
 ap=argparse.ArgumentParser();ap.add_argument('--stage',choices=['screen','refine'],required=True);ap.add_argument('--workers',type=int,default=4);args=ap.parse_args();OUT.mkdir(exist_ok=True)
 if args.stage=='screen':pairs=PORTFOLIOS;seeds=[919260010,919260011,919260012,919260013]
 else:
  screen=json.loads((OUT/'screen_summary.json').read_text());pairs=[(r['cohort2'],r['cohort3']) for r in screen['ranking'] if (r['cohort2'],r['cohort3'])!=('COW','COW')][:2];seeds=[*range(919261001,919261009),*range(919262001,919262009)]
 tasks=[(a,b,s) for a,b in pairs for s in seeds];hashes=evaluate.snapshot(D);plan={'tasks':tasks,'hashes':hashes,'driver_sha256':evaluate.sha(Path(__file__)),'opponent':'y68v','seat':0,'panel':'development'};pf=OUT/f'{args.stage}_plan.json'
 if pf.exists():assert json.loads(pf.read_text())==json.loads(json.dumps(plan))
 else:pf.write_text(json.dumps(plan,indent=2)+'\n')
 rf=OUT/f'{args.stage}.jsonl';rows=[json.loads(l) for l in rf.read_text().splitlines()] if rf.exists() else [];done={(r['cohort2'],r['cohort3'],r['seed']) for r in rows};pending=[t for t in tasks if t not in done];print('pending',len(pending),flush=True)
 for start in range(0,len(pending),args.workers*6):
  with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
   for r in pool.map(game,pending[start:start+args.workers*6]):
    rows.append(r)
    with rf.open('a') as f:f.write(json.dumps(r)+'\n')
    print(len(rows),r['cohort2'],r['cohort3'],r['seed'],r['margin'],flush=True)
 assert evaluate.snapshot(D)==hashes
 ranking=[]
 for a,b in pairs:
  rs=[r for r in rows if r['cohort2']==a and r['cohort3']==b];ranking.append({'cohort2':a,'cohort3':b,'games':len(rs),'wins':sum(r['win'] for r in rs),'mean_margin':float(np.mean([r['margin'] for r in rs])),'worst_margin':min(r['margin'] for r in rs)})
 ranking.sort(key=lambda r:(r['wins'],r['mean_margin']),reverse=True)
 out={'stage':args.stage,'completed':len(rows),'expected':len(tasks),'ranking':ranking};assert len(rows)==len(tasks);(OUT/f'{args.stage}_summary.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out),flush=True)
if __name__=='__main__':run()
