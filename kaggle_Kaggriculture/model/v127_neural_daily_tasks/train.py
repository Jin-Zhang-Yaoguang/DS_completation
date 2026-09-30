from pathlib import Path
import json,time
import numpy as np
import jax,jax.numpy as jnp,optax
from flax.training.train_state import TrainState
from flax.traverse_util import flatten_dict
from network import DailyPlan
B=Path(__file__).resolve().parent

def loss(p,apply,b):
 o=apply({'params':p},b);mask=.1+.9*b['active'];ce=optax.softmax_cross_entropy_with_integer_labels(o['tiles'],b['tiles']);tile=(ce*mask).sum()/mask.sum();aux=sum(optax.softmax_cross_entropy_with_integer_labels(o[k],b[k]).mean() for k in ['hands','land']);return tile+.3*aux
@jax.jit
def update(s,b):
 v,g=jax.value_and_grad(loss)(s.params,s.apply_fn,b);return s.apply_gradients(grads=g),v
@jax.jit
def evaluate(s,b):return loss(s.params,s.apply_fn,b)
def main():
 with np.load(B/'data/train.npz') as z:d={k:z[k] for k in z.files}
 with np.load(B/'data/validation.npz') as z:v={k:jnp.asarray(z[k]) for k in z.files}
 n=len(d['day']);rng=np.random.default_rng(127);batch=lambda ix:{k:jnp.asarray(x[ix]) for k,x in d.items()};m=DailyPlan();p=m.init(jax.random.PRNGKey(127),batch(np.arange(2)))['params'];s=TrainState.create(apply_fn=m.apply,params=p,tx=optax.adamw(8e-4,weight_decay=1e-4));history=[];best=1e9;started=time.time()
 for epoch in range(1,41):
  idx=rng.permutation(n);ls=[]
  for i in range(0,n,128):s,l=update(s,batch(idx[i:i+128]));ls.append(float(l))
  val=float(evaluate(s,v));r={'epoch':epoch,'train_loss':float(np.mean(ls)),'validation_loss':val,'elapsed':time.time()-started};history.append(r)
  if val<best:
   best=val;np.savez_compressed(B/'weights.npz',**{'/'.join(k):np.asarray(x) for k,x in flatten_dict(s.params).items()});(B/'selected_checkpoint.json').write_text(json.dumps(r,indent=2))
  (B/'training_history.json').write_text(json.dumps(history,indent=2))
  if epoch%5==0:print(r,flush=True)
 # Training-only time baseline, with the exact same task executor during evaluation.
 out={}
 for k in ['tiles','hands','land']:
  arr=d[k];rows=[]
  for day in range(30):
   a=arr[d['day']==day];rows.append(np.apply_along_axis(lambda x:np.bincount(x).argmax(),0,a))
  out[k]=np.asarray(rows)
 np.savez_compressed(B/'time_plan.npz',**out)
if __name__=='__main__':main()
