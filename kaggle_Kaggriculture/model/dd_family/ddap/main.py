"""Replay-derived request policy; the environment performs joint validation."""
from pathlib import Path
import json
import numpy as np
import action_space as space
B=Path(__file__).resolve().parent
class Agent:
 def __init__(self):
  self.config=json.loads((B/'config.json').read_text())
  self.arr={name:np.load(B/'data'/f'{name}.npy',mmap_mode='r') for name in ['unit_tokens','raw_unit_quantities','market_tokens','raw_market_quantities']}
  self.stats={'calls':0,'unrepresented_workers':0};self.last={}
 def act(self,obs):
  t=int(obs['step']);k=self.config['fixed_prototype'];orders=[]
  for i in range(space.unit_count(obs)):
   if i>=16:orders.append(['PASS']);self.stats['unrepresented_workers']+=1;continue
   name=space.UNIT_TOKENS[int(self.arr['unit_tokens'][t,k,i])];q=int(self.arr['raw_unit_quantities'][t,k,i]);parts=name.split(':')
   if parts[0] in ['PICKUP','PLACE']:parts.append(q)
   orders.append(parts)
  market=[]
  for tok,q in zip(self.arr['market_tokens'][t,k],self.arr['raw_market_quantities'][t,k]):
   name=space.MARKET_TOKENS[int(tok)]
   if name=='STOP':break
   parts=name.split(':')
   if len(parts)==2:parts.append(int(q))
   market.append(parts)
  self.stats['calls']+=1;self.last={'support_index':k,'mode':'joint_request'}
  return {'farmer':orders[0],'hands':orders[1:],'market':market}
_AGENT=None
def agent(obs,configuration=None):
 global _AGENT
 if _AGENT is None:_AGENT=Agent()
 return _AGENT.act(obs)
