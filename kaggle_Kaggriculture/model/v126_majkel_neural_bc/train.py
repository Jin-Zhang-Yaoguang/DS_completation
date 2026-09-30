from pathlib import Path
import argparse,json,time
import numpy as np
import jax,jax.numpy as jnp,optax
from flax.training.train_state import TrainState
from flax.traverse_util import flatten_dict
import network,action_space as space
B=Path(__file__).resolve().parent
KEYS=['global','board','units','unit_mask','step','unit_tokens','unit_quantities','market_tokens','market_quantities','market_mask']
def load(split):return {k:np.load(B/'data'/split/f'{k}.npy',mmap_mode='r') for k in KEYS}
def batch(d,idx):return {k:jnp.asarray(v[idx],dtype=jnp.float32 if v.dtype.kind=='f' else jnp.int32) for k,v in d.items()}
UQ=jnp.asarray([n.startswith(('PICKUP:','PLACE:')) for n in space.UNIT_TOKENS]);MQ=jnp.asarray([n not in ['STOP','HIRE','BUY_LAND'] for n in space.MARKET_TOKENS])
def loss(p,apply,b):
 out=apply({'params':p},b);ms={'unit_tokens':b['unit_mask'],'unit_quantities':b['unit_mask']*UQ[b['unit_tokens']],'market_tokens':b['market_mask'],'market_quantities':b['market_mask']*MQ[b['market_tokens']]};ls={};acc={}
 for k,logits in out.items():
  m=ms[k];den=jnp.maximum(m.sum(),1);ce=optax.softmax_cross_entropy_with_integer_labels(logits,b[k]);ls[k]=(ce*m).sum()/den;acc[k]=((logits.argmax(-1)==b[k])*m).sum()/den
 total=ls['unit_tokens']+ls['market_tokens']+.3*(ls['unit_quantities']+ls['market_quantities'])
 return total,{**{k+'_accuracy':v for k,v in acc.items()},'loss':total}
@jax.jit
def update(s,b):
 (_,metrics),grad=jax.value_and_grad(loss,has_aux=True)(s.params,s.apply_fn,b);return s.apply_gradients(grads=grad),metrics
@jax.jit
def assess(s,b):return loss(s.params,s.apply_fn,b)[1]
def evaluate(s,d,bsize=256):
 n=len(d['step']);total={}
 for start in range(0,n,bsize):
  idx=np.arange(start,min(n,start+bsize));m=assess(s,batch(d,idx));weight=len(idx)
  for k,v in m.items():total[k]=total.get(k,0)+float(v)*weight
 return {k:v/n for k,v in total.items()}
def save(p,path):np.savez_compressed(path,**{'/'.join(k):np.asarray(v) for k,v in flatten_dict(p).items()})
def main():
 a=argparse.ArgumentParser();a.add_argument('--epochs',type=int,default=12);a.add_argument('--batch-size',type=int,default=256);args=a.parse_args();d=load('train');val=load('validation');rng=np.random.default_rng(20260915);model=network.Policy();params=model.init(jax.random.PRNGKey(126),batch(d,np.arange(2)))['params'];s=TrainState.create(apply_fn=model.apply,params=params,tx=optax.adamw(learning_rate=1e-3,weight_decay=1e-5));best=float('inf');history=[];start=time.time();print('parameters',sum(v.size for v in jax.tree_util.tree_leaves(params)),'train_rows',len(d['step']),flush=True)
 for epoch in range(1,args.epochs+1):
  idx=rng.permutation(len(d['step']));sums=[]
  for j in range(0,len(idx),args.batch_size):
   s,m=update(s,batch(d,idx[j:j+args.batch_size]));sums.append(float(m['loss']))
  vm=evaluate(s,val);row={'epoch':epoch,'train_loss':float(np.mean(sums)),'validation':vm,'elapsed_seconds':time.time()-start};history.append(row)
  if vm['loss']<best:best=vm['loss'];save(s.params,B/'weights.npz');(B/'selected_checkpoint.json').write_text(json.dumps(row,indent=2))
  (B/'training_history.json').write_text(json.dumps(history,indent=2));print(json.dumps(row),flush=True)
 save(s.params,B/'last_weights.npz')
if __name__=='__main__':main()
