"""Trace one already-evaluated pilot case; no checkpoint selection from this diagnosis."""
from pathlib import Path
import json,collections
import main
B=Path(__file__).resolve().parent

def run():
 from kaggle_environments import make
 from kaggle_environments.envs.kaggriculture import kaggriculture as kg
 previous=json.loads((B/'closed_loop_games.json').read_text());case=next(r for r in previous if r['opponent']=='starter' and r['seat']==0)
 env=make('kaggriculture',configuration={'seed':case['seed']},debug=False);env.reset(2);policy=main.NumpyPolicy();escapes=[];days=[]
 for step in range(719):
  obs=[s.observation for s in env.state]
  for o in obs:o['step']=step
  farm=obs[0]['farms'][0];before={(x,y):dict(t) for y,row in enumerate(farm['tiles']) for x,t in enumerate(row) if isinstance(t,dict) and t.get('animal')};action=policy.act(obs[0]);other=kg.starter_agent(obs[1]);env.step([action,other]);farm=env.state[0].observation.farms[0]
  for (x,y),old in before.items():
   new=farm['tiles'][y][x]
   if not isinstance(new,dict) or not new.get('animal'):escapes.append({'decision_step':step,'position':[x,y],'animal':old['animal'],'consecutive_unfed_before':old['consecutive_unfed'],'fed_today_before':old['fed_today'],'action':action})
  if step%24==23:
   tiles=[t for row in farm['tiles'] for t in row if isinstance(t,dict) and t.get('animal')];days.append({'completed_day':step//24+1,'remaining_animals':len(tiles),'previous_day_missed_feed':sum(t.get('consecutive_unfed',0)>0 for t in tiles),'cash':farm['money'],'shed':dict(env.state[0].observation.private['shed'])})
 reward=float(env.state[0].reward);assert reward==case['own_cash'],(reward,case['own_cash']);out={'seed':case['seed'],'opponent':'starter','seat':0,'cash':reward,'reproduces_pilot':True,'escapes':escapes,'days':days};(B/'failure_diagnosis.json').write_text(json.dumps(out,indent=2));print('cash',reward,'escapes',len(escapes),'first',[{k:v for k,v in e.items() if k!='action'} for e in escapes[:8]])
if __name__=='__main__':run()
