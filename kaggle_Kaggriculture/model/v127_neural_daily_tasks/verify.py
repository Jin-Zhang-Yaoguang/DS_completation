from pathlib import Path
import json,hashlib,tempfile,subprocess,sys,zipfile
import numpy as np
import jax,jax.numpy as jnp
from flax.traverse_util import unflatten_dict
from network import DailyPlan
import main
B=Path(__file__).resolve().parent
FILES=['main.py','executor.py','plan_features.py','features.py','action_space.py','rules.py','weights.npz']
def run():
 with np.load(B/'weights.npz') as z:p=unflatten_dict({tuple(k.split('/')):jnp.asarray(z[k]) for k in z.files})
 with np.load(B/'data/train.npz') as z:x=z['x'][:32];days=z['day'][:32]
 expected=DailyPlan().apply({'params':p},{'x':jnp.asarray(x),'day':jnp.asarray(days)});planner=main.Planner();errors=[]
 for i in range(len(days)):
  h=np.concatenate([x[i],planner.w['day_embed/embedding'][days[i]]])
  for name in ['hidden1','hidden2']:h=np.maximum(0,h@planner.w[name+'/kernel']+planner.w[name+'/bias'])
  for name in ['tiles','hands','land']:
   a=h@planner.w[name+'/kernel']+planner.w[name+'/bias'];b=np.asarray(expected[name][i]).ravel();errors.append(float(np.max(np.abs(a-b))))
 assert max(errors)<2e-4
 rs=json.loads((B/'split_manifest.json').read_text())['episodes'];plan=json.loads((B/'evaluation_plan.json').read_text());old=json.loads((B.parent/'v126_majkel_neural_bc/evaluation_plan.json').read_text());reserved=set(plan['development_seeds'])|set(plan['confirmation_seeds']);assert len(reserved)==6;assert not reserved&{r['seed'] for r in rs};assert not reserved&set(old['seeds'])
 r=next(r for r in rs if r['split']=='train');raw=json.loads(Path(r['path']).read_text());obs=raw['steps'][0][r['seat']]['observation'];obs['step']=0
 with tempfile.TemporaryDirectory() as td:
  td=Path(td)
  for f in FILES:(td/f).write_bytes((B/f).read_bytes())
  (td/'obs.json').write_text(json.dumps(obs));code="import time,json; t=time.perf_counter(); import main; o=json.load(open('obs.json')); a=main.agent(o); print(json.dumps({'seconds':time.perf_counter()-t,'action':a}))"
  result=json.loads(subprocess.run([sys.executable,'-c',code],cwd=td,capture_output=True,text=True,check=True).stdout)
 manifest={'files':{f:{'bytes':(B/f).stat().st_size,'sha256':hashlib.sha256((B/f).read_bytes()).hexdigest()} for f in FILES},'parameters':sum(v.size for v in jax.tree_util.tree_leaves(p)),'trained_numpy_jax_max_abs_error':max(errors),'cold_import_load_first_action':result,'new_seeds_disjoint':True,'checkpoint_epoch':json.loads((B/'selected_checkpoint.json').read_text())['epoch'],'runtime':'NumPy + standard library; neural network once per game day, stateful task executor every turn','no_submission':True}
 (B/'deployment_manifest.json').write_text(json.dumps(manifest,indent=2))
 with zipfile.ZipFile(B/'daily_task_policy_bundle.zip','w',zipfile.ZIP_DEFLATED) as z:
  for f in FILES+['deployment_manifest.json']:z.write(B/f,f)
 print({k:v for k,v in manifest.items() if k!='files'})
if __name__=='__main__':run()
