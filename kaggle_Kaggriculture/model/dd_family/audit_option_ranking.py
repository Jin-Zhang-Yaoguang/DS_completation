"""Held-out teacher-forced full-option confusion; never an arena result."""
from pathlib import Path
import collections,concurrent.futures,json,sys
import numpy as np
B=Path(__file__).resolve().parent

def run(p):
 sys.path.insert(0,str(B/'ddbk'));import tree_runtime,task_features as F
 model=tree_runtime.Model(B/'ddbk/goal_rank.npz');pairs=collections.Counter()
 with np.load(p) as z:
  x=z['validation_x'];scores=model.predict(x);off=z['validation_offsets'];labels=z['validation_choice']
  for k,chosen in enumerate(labels):
   start,end=off[k:k+2];truth=int(x[start+chosen,-(F.UT+11):-11].argmax());pred=start+scores[start:end].argmax();token=int(x[pred,-(F.UT+11):-11].argmax());pairs[F.GOAL_TOKENS[truth],F.GOAL_TOKENS[token],pred==start+chosen]+=1
 return pairs
if __name__=='__main__':
 paths=sorted((B/'task_policy_data/ddbk').glob('validation_*.npz'));tot=collections.Counter()
 with concurrent.futures.ProcessPoolExecutor(max_workers=2) as pool:
  for pairs in pool.map(run,paths):tot.update(pairs)
 rows=[{'truth':a,'predicted':b,'exact_position':bool(c),'count':n} for (a,b,c),n in tot.items()]
 truth=collections.Counter();pred=collections.Counter();correct=collections.Counter()
 for (a,b,c),n in tot.items():
  truth[a]+=n;pred[b]+=n
  if c:correct[a]+=n
 result={'queries':sum(tot.values()),'teacher_forced_validation_only':True,'true_counts':dict(truth),'predicted_counts':dict(pred),'exact_correct_counts':dict(correct),'confusion':rows}
 (B/'diagnostics/ddbk_option_ranking.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='confusion'},indent=2))
