from pathlib import Path
import json
import numpy as np
import jax,jax.numpy as jnp
from flax.traverse_util import unflatten_dict
from network import DailyPlan
import main
B=Path(__file__).resolve().parent

def main_eval():
 with np.load(B/'weights.npz') as z:p=unflatten_dict({tuple(k.split('/')):jnp.asarray(z[k]) for k in z.files})
 with np.load(B/'time_plan.npz') as z:control={k:z[k] for k in z.files}
 m=DailyPlan();infer=jax.jit(lambda b:m.apply({'params':p},b));out={}
 for split in ['validation','test','version_shift']:
  with np.load(B/'data'/f'{split}.npz') as z:d={k:z[k] for k in z.files}
  logits=infer({k:jnp.asarray(d[k]) for k in ['x','day']});pred={k:np.asarray(v).argmax(-1) for k,v in logits.items()};baseline={k:v[d['day']] for k,v in control.items()};stats={}
  for label,guess in [('neural',pred),('time_only',baseline)]:
   active=d['active']>0;changed=active&(d['tiles']!=d['current_tiles']);correct=guess['tiles']==d['tiles'];counts=lambda a:np.stack([(a==i).sum(-1) for i in range(1,9)],-1)
   stats[label]={'rows':len(d['day']),'active_tile_accuracy':float(correct[active].mean()),'changed_tile_accuracy':float(correct[changed].mean()),'changed_tile_count':int(changed.sum()),'hands_accuracy':float((guess['hands']==d['hands']).mean()),'land_accuracy':float((guess['land']==d['land']).mean()),'mean_total_type_count_absolute_error':float(np.abs(counts(guess['tiles'])-counts(d['tiles'])).sum(-1).mean())}
  out[split]=stats
 (B/'plan_metrics.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main_eval()
