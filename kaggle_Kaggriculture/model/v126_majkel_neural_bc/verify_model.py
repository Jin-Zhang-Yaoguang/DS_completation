from pathlib import Path
import json,tempfile,subprocess,sys,time,hashlib,zipfile
import numpy as np
import jax,jax.numpy as jnp
from flax.traverse_util import unflatten_dict
import network,main,train
B=Path(__file__).resolve().parent
FILES=['main.py','contract.py','features.py','action_space.py','rules.py','weights.npz']
def verify():
 d=train.load('train');idx=np.random.default_rng(126).choice(len(d['step']),64,replace=False);b=train.batch(d,idx)
 with np.load(B/'weights.npz') as z:p=unflatten_dict({tuple(k.split('/')):jnp.asarray(z[k]) for k in z.files})
 o=network.Policy().apply({'params':p},b);policy=main.NumpyPolicy();errors=[]
 for i in range(len(idx)):
  x={k:np.asarray(b[k][i]) for k in ['global','board','units','unit_mask','step']};core,u,q=policy.encode(x);m,mq=policy.market(core,np.asarray(b['unit_tokens'][i]),x['unit_mask'],np.asarray(b['market_tokens'][i]),np.asarray(b['market_quantities'][i]))
  for key,pred in zip(['unit_tokens','unit_quantities','market_tokens','market_quantities'],[u,q,m,mq]):errors.append(float(np.max(np.abs(np.asarray(o[key][i])-pred))))
 assert max(errors)<2e-4,max(errors)
 rs=json.loads((B/'split_manifest.json').read_text())['episodes'];seeds=json.loads((B/'evaluation_plan.json').read_text())['seeds'];assert not set(seeds)&{r['seed'] for r in rs}
 r=next(r for r in rs if r['split']=='train');replay=json.loads(Path(r['path']).read_text());obs=replay['steps'][0][r['seat']]['observation'];obs['step']=0
 with tempfile.TemporaryDirectory() as td:
  td=Path(td)
  for f in FILES:(td/f).write_bytes((B/f).read_bytes())
  (td/'obs.json').write_text(json.dumps(obs));code="import time,json; t=time.perf_counter(); import main; a=main.agent(json.load(open('obs.json'))); print(json.dumps({'cold_import_load_first_action_seconds':time.perf_counter()-t,'action':a}))"
  child=subprocess.run([sys.executable,'-c',code],cwd=td,capture_output=True,text=True,check=True);cold=json.loads(child.stdout)
 manifest={'files':{f:{'sha256':hashlib.sha256((B/f).read_bytes()).hexdigest(),'bytes':(B/f).stat().st_size} for f in FILES},'numpy_only_runtime':True,'trained_numpy_jax_max_abs_error':max(errors),'parity_train_rows':64,'fresh_eval_seeds_disjoint':True,'cold_process':cold,'checkpoint':json.loads((B/'selected_checkpoint.json').read_text()),'not_submitted':True}
 (B/'deployment_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
 with zipfile.ZipFile(B/'neural_policy_bundle.zip','w',zipfile.ZIP_DEFLATED) as z:
  for f in FILES+['deployment_manifest.json']:z.write(B/f,f)
 print(json.dumps(manifest,ensure_ascii=False,indent=2))
if __name__=='__main__':verify()
