"""Read-only inference benchmark; does not alter a candidate or its training run."""
from pathlib import Path
import json,sys,time
import numpy as np
B=Path(__file__).resolve().parent;sys.path.insert(0,str(B/'ddbo'));import tree_runtime

def sparse_predict(a,x):
 x=np.asarray(x,np.float32).reshape(-1,int(a['dimensions']));n=len(x);nodes=np.repeat(a['roots'],n);active=np.arange(len(nodes),dtype=np.int32)
 for _ in range(int(a['depth'])):
  current=nodes[active];mask=a['left'][current]!=current;active=active[mask];current=current[mask]
  if not len(active):break
  f=a['feature'][current];values=x[active%n,f];nodes[active]=np.where(values<=a['threshold'][current],a['left'][current],a['right'][current])
 values=a['value'][nodes.reshape(len(a['roots']),n)]
 if int(a['kind'])==0:return values.sum(0)+a['baseline']
 return values.mean(0)

if __name__=='__main__':
 model=tree_runtime.Model(B/'ddbo/goal_rank.npz');p=next((B/'task_policy_data/ddbo').glob('validation_*.npz'))
 with np.load(p) as z:x=z['validation_x'][:8192]
 rows=[]
 for n in [1,128,512,2048,8192]:
  small=x[:n];start=time.perf_counter();old=model.predict(small);t_old=time.perf_counter()-start;start=time.perf_counter();new=sparse_predict(model.a,small);t_new=time.perf_counter()-start;assert np.array_equal(old,new)
  rows.append({'rows':n,'dense_seconds':t_old,'sparse_seconds':t_new,'speedup':t_old/t_new,'bitwise_equal':True})
 result={'candidate_modified':False,'model':'ddbo/goal_rank.npz','depth':int(model.a['depth']),'results':rows};(B/'diagnostics/sparse_tree_runtime_benchmark.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
