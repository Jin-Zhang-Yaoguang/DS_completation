"""Exact weighted held-out metrics, including a training-only time/slot majority control."""
from pathlib import Path
import json
import numpy as np
import jax,jax.numpy as jnp
from flax.traverse_util import unflatten_dict
import train,network,action_space as space
B=Path(__file__).resolve().parent
UQ=np.asarray([n.startswith(('PICKUP:','PLACE:')) for n in space.UNIT_TOKENS]);MQ=np.asarray([n not in ['STOP','HIRE','BUY_LAND'] for n in space.MARKET_TOKENS])

def metrics(pred,b):
 masks={'unit_tokens':np.asarray(b['unit_mask']),'unit_quantities':np.asarray(b['unit_mask'])*UQ[np.asarray(b['unit_tokens'])],'market_tokens':np.asarray(b['market_mask']),'market_quantities':np.asarray(b['market_mask'])*MQ[np.asarray(b['market_tokens'])]};out={};exact=np.ones(len(b['step']),bool)
 for k,m in masks.items():
  equal=np.asarray(pred[k])==np.asarray(b[k]);out[k+'_correct']=int((equal*m).sum());out[k+'_count']=int(m.sum());exact&=np.all(equal|(m==0),axis=-1)
 out['joint_correct']=int(exact.sum());out['joint_count']=len(exact);return out

def main():
 model=network.Policy()
 with np.load(B/'weights.npz') as z:p=unflatten_dict({tuple(k.split('/')):jnp.asarray(z[k]) for k in z.files})
 @jax.jit
 def predict(b,teacher=False):
  out=model.apply({'params':p},b);pred={k:v.argmax(-1) for k,v in out.items()}
  if teacher:return pred
  x=dict(b);x['unit_tokens']=pred['unit_tokens'];x['market_tokens']=jnp.zeros_like(b['market_tokens']);x['market_quantities']=jnp.zeros_like(b['market_quantities']);active=jnp.ones(len(b['step']),bool)
  for i in range(10):
   o=model.apply({'params':p},x);t=jnp.where(active,o['market_tokens'][:,i].argmax(-1),0);q=jnp.where(active,o['market_quantities'][:,i].argmax(-1),0);active&=t!=0;x['market_tokens']=x['market_tokens'].at[:,i].set(t);x['market_quantities']=x['market_quantities'].at[:,i].set(q)
  pred['market_tokens']=x['market_tokens'];pred['market_quantities']=x['market_quantities'];return pred
 # Static bool for JIT.
 teacher_predict=jax.jit(lambda b:{k:v.argmax(-1) for k,v in model.apply({'params':p},b).items()})
 d=train.load('train');control={}
 for k in ['unit_tokens','unit_quantities','market_tokens','market_quantities']:
  a=np.asarray(d[k]).reshape((-1,719,d[k].shape[-1]));v=np.zeros(a.shape[1:],np.int32)
  for t in range(719):
   for u in range(v.shape[-1]):
    valid=np.asarray(d['unit_mask']).reshape((-1,719,16))[:,t,u]>0 if k.startswith('unit_') else np.asarray(d['market_mask']).reshape((-1,719,10))[:,t,u]>0
    values=a[:,t,u][valid];v[t,u]=np.bincount(values).argmax() if len(values) else 0
  control[k]=v
 np.savez_compressed(B/'time_slot_control.npz',**control)
 report={}
 for split in ['validation','test','version_shift']:
  d=train.load(split);acc={name:{} for name in ['teacher_forced','free_prefix','time_slot_control']}
  for start in range(0,len(d['step']),256):
   b=train.batch(d,np.arange(start,min(start+256,len(d['step']))));ps={'teacher_forced':teacher_predict(b),'free_prefix':predict(b),'time_slot_control':{k:v[np.asarray(b['step'])] for k,v in control.items()}}
   for name,pred in ps.items():
    m=metrics(pred,b)
    for k,v in m.items():acc[name][k]=acc[name].get(k,0)+v
  for name,m in acc.items():
   for k in ['unit_tokens','unit_quantities','market_tokens','market_quantities','joint']:m[k+'_accuracy']=m[k+'_correct']/max(m[k+'_count'],1)
  report[split]=acc;(B/'offline_metrics.json').write_text(json.dumps(report,indent=2));print(split,{name:{k:round(v,4) for k,v in m.items() if k.endswith('accuracy')} for name,m in acc.items()},flush=True)
if __name__=='__main__':main()
