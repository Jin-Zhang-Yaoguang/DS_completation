"""Read-only reproduction of one completed game; excluded from gate denominator."""
import sys,json,gzip,copy
from pathlib import Path
G=Path(__file__).resolve().parent
sys.path.insert(0,str(G))
import evaluate as E
from kaggle_environments import make
from kaggle_environments.agent import get_last_callable
with gzip.open(G/'games/y68a_1100_0.json.gz','rt') as f:reference=json.load(f)
p=E.main.Agent();op=G/'opponents/y68a_main.py';other=get_last_callable(op.read_text(),path=str(op))
env=make('kaggriculture',configuration={'seed':1100},debug=False);env.reset(2);events=[];mismatch=0
for step in range(719):
 obs=[copy.deepcopy(s.observation) for s in env.state]
 for o in obs:o['step']=step
 a=p.act(obs[0]);b=other(obs[1]);units=[a.get('farmer') or ['PASS']]+list(a.get('hands') or [])
 mismatch+=E.digest([units,a.get('market') or []])!=reference['trace'][step]['full_hash']
 env.step([a,b])
 if step in [0,1,5,7,22,23,24,47,48,71,72,95,96,119,120]:
  before=obs[0];after=env.state[0].observation
  def brief(o):
   f=o['farms'][0];return {'money':f['money'],'hands':len(f['hands']),'shed':dict(o['private']['shed']),'seeds':dict(o['private']['seeds']),'animals':[{'x':x,'y':y,'animal':t['animal'],'unfed':t.get('consecutive_unfed',0),'fed':t.get('fed_today')} for y,row in enumerate(f['tiles']) for x,t in enumerate(row) if isinstance(t,dict) and t.get('animal')]}
  events.append({'step':step,'before':brief(before),'after':brief(after),'plan_hands':int(p.executor.plan['hands']),'own_action':a,'opponent_market':b.get('market',[])})
out={'seed':1100,'seat':0,'opponent':'y68a','extra_diagnostic_reproduction_not_gate_game':True,'action_mismatches':mismatch,'final_rewards':[s.reward for s in env.state],'reference_rewards':[reference['own_cash'],reference['opponent_cash']],'events':events}
assert mismatch==0 and out['final_rewards']==out['reference_rewards']
(G/'opening_diagnosis.json').write_text(json.dumps(out,indent=2,ensure_ascii=False));print('Reproduction passed: 719 identical actions and exact final rewards')
