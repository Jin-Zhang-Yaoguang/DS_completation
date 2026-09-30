"""Neural daily plans + feedback execution. NumPy-only production entrypoint."""
from pathlib import Path
import numpy as np
import plan_features
from executor import Executor
B=Path(__file__).resolve().parent
class Planner:
 def __init__(self,kind='neural_tasks'):
  self.kind=kind
  with np.load(B/('weights.npz' if kind=='neural_tasks' else 'time_plan.npz')) as z:self.w={k:z[k] for k in z.files}
 def logits(self,obs):
  a=plan_features.encode(obs);day=int(a['day']);x=np.concatenate([a['x'],self.w['day_embed/embedding'][day]])
  for name in ['hidden1','hidden2']:x=np.maximum(0,x@self.w[name+'/kernel']+self.w[name+'/bias'])
  return {k:(x@self.w[k+'/kernel']+self.w[k+'/bias']).reshape(100,9) if k=='tiles' else x@self.w[k+'/kernel']+self.w[k+'/bias'] for k in ['tiles','hands','land']}
 def plan(self,obs):
  if self.kind=='time_tasks':return {k:np.asarray(self.w[k][obs['step']//24]).copy() for k in ['tiles','hands','land']}
  return {k:np.argmax(v,axis=-1) for k,v in self.logits(obs).items()}
class Agent:
 def __init__(self,kind='neural_tasks'):self.planner=Planner(kind);self.executor=Executor();self.plan_log=[]
 def act(self,obs):
  day=obs['step']//24
  if obs['step']==0:self.executor=Executor();self.plan_log=[]
  if self.executor.day!=day:
   p=self.planner.plan(obs);self.executor.set_plan(p,day);self.plan_log.append({'day':day,'hands':int(p['hands']),'land':int(p['land']),'tiles':p['tiles'].tolist()})
  return self.executor.act(obs)
_INSTANCE=None
def agent(obs,configuration=None):
 global _INSTANCE
 if _INSTANCE is None:_INSTANCE=Agent()
 return _INSTANCE.act(obs)
