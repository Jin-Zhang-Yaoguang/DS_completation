from pathlib import Path
import json,time,importlib.util,sys,collections,concurrent.futures,argparse,hashlib
import numpy as np
import main
B=Path(__file__).resolve().parent

def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def game(task):
 from kaggle_environments import make
 from kaggle_environments.envs.kaggriculture import kaggriculture as kg
 seed,seat,op,kind=task
 if kind=='v126':
  parent=B.parent/'v126_majkel_neural_bc';sys.path.insert(0,str(parent));p=load(parent/'main.py','v126_runtime').NumpyPolicy();act=p.act
 else:p=main.Agent(kind);act=p.act
 other=kg.starter_agent if op=='starter' else load(B/'evaluation_baseline.py','frozen_eval').agent
 env=make('kaggriculture',configuration={'seed':seed},debug=False);env.reset(2);escapes=[];drought=[];daily=[];times=[];start=time.time()
 for step in range(719):
  obs=[s.observation for s in env.state]
  for o in obs:o['step']=step
  f=obs[seat]['farms'][seat];before={(x,y):dict(t) for y,row in enumerate(f['tiles']) for x,t in enumerate(row) if isinstance(t,dict)};positions=[f['farmer']]+f['hands'];positions=[tuple(p) for p in positions]
  tick=time.perf_counter();action=act(obs[seat]);times.append(time.perf_counter()-tick);actions=[None,None];actions[seat]=action;actions[1-seat]=other(obs[1-seat]);env.step(actions);f=env.state[seat].observation.farms[seat]
  watered={positions[i] for i,a in enumerate([action['farmer']]+action['hands']) if a and a[0]=='WATER'}
  for (x,y),old in before.items():
   new=f['tiles'][y][x]
   if old.get('animal') and (not isinstance(new,dict) or not new.get('animal')):escapes.append({'step':step,'animal':old['animal'],'position':[x,y]})
   if step%24==23 and old.get('crop') and old.get('consecutive_unwatered',0)>=1 and not old['watered_today'] and (x,y) not in watered and isinstance(new,dict) and new.get('kind')=='WEED':drought.append({'step':step,'crop':old['crop'],'position':[x,y]})
  if step%24==22 or step==718:
   tiles=[t for row in f['tiles'] for t in row if isinstance(t,dict)];daily.append({'step':step+1,'cash':f['money'],'hands':len(f['hands']),'land':len(f['unlocked_quadrants']),'animals':sum(bool(t.get('animal')) for t in tiles),'crops':sum(bool(t.get('crop')) for t in tiles)})
 status=[str(s.status) for s in env.state];assert status==['DONE','DONE'];cash=[float(s.reward) for s in env.state]
 return {'seed':seed,'seat':seat,'opponent':op,'candidate':kind,'own_cash':cash[seat],'opponent_cash':cash[1-seat],'margin':cash[seat]-cash[1-seat],'win':cash[seat]>cash[1-seat],'draw':cash[seat]==cash[1-seat],'statuses':status,'escapes':escapes,'drought':drought,'daily':daily,'plan_log':p.plan_log if kind!='v126' else [],'p99_seconds':float(np.quantile(times,.99)),'max_seconds':max(times),'elapsed_seconds':time.time()-start}

def run():
 a=argparse.ArgumentParser();a.add_argument('--panel',choices=['development','confirmation'],default='development');args=a.parse_args();plan=json.loads((B/'evaluation_plan.json').read_text());seeds=plan[args.panel+'_seeds'];kinds=['neural_tasks','time_tasks'] if args.panel=='development' else plan['candidates'];ops=['starter'] if args.panel=='development' else plan['opponents'];tasks=[(seed,seat,op,kind) for kind in kinds for op in ops for seed in seeds for seat in [0,1]]
 if args.panel=='confirmation':
  files=['main.py','executor.py','plan_features.py','weights.npz','time_plan.npz','evaluation_baseline.py'];freeze={f:hashlib.sha256((B/f).read_bytes()).hexdigest() for f in files};(B/'confirmation_freeze.json').write_text(json.dumps(freeze,indent=2))
 rows=[]
 with concurrent.futures.ProcessPoolExecutor(max_workers=4) as p:
  for r in p.map(game,tasks):
   rows.append(r);print(r['candidate'],r['opponent'],r['seed'],r['seat'],r['own_cash'],len(r['escapes']),len(r['drought']),flush=True);(B/(args.panel+'_games.json')).write_text(json.dumps(rows,indent=2))
 summary={}
 for kind in kinds:
  for op in ops:
   rs=[r for r in rows if r['candidate']==kind and r['opponent']==op];summary[kind+':'+op]={'n':len(rs),'wins':sum(r['win'] for r in rs),'draws':sum(r['draw'] for r in rs),'mean_cash':float(np.mean([r['own_cash'] for r in rs])),'mean_margin':float(np.mean([r['margin'] for r in rs])),'mean_escapes':float(np.mean([len(r['escapes']) for r in rs])),'mean_drought':float(np.mean([len(r['drought']) for r in rs])),'max_p99_seconds':max(r['p99_seconds'] for r in rs)}
 (B/(args.panel+'_summary.json')).write_text(json.dumps(summary,indent=2));print(summary,flush=True)
if __name__=='__main__':run()
