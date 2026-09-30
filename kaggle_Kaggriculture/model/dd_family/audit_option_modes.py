"""Measure source initial-decision ambiguity, using train-only labels and no test trajectories."""
from pathlib import Path
import collections,hashlib,json,sys
import numpy as np
B=Path(__file__).resolve().parent;version=sys.argv[1];sys.path.insert(0,str(B/version));import task_features as F
source=B/'task_policy_data'/version;groups=collections.defaultdict(collections.Counter);rows=[]
for p in sorted(source.glob('train_*.npz')):
 audit=json.loads(p.with_suffix('.json').read_text())
 with np.load(p) as z:
  y=z['rank_y'];starts=np.flatnonzero(y);x=z['rank_x'][:starts[1]];tokens=x[:,-(F.UT+11):-11].argmax(1);wait=np.flatnonzero(tokens==0);assert len(wait)==1
  context=hashlib.sha256(x[wait[0]].tobytes()).hexdigest();positive=x[0];label=(F.GOAL_TOKENS[int(tokens[0])],int(positive[-11]),int(positive[-10]));groups[context][label]+=1;rows.append({'source_index':audit['index'],'seed':audit['source_seed'],'context_sha256':context,'initial_goal':label})
result={'version':version,'train_episodes':len(rows),'context_definition':'Exact full feature vector for initial PASS candidate, not proof that all raw observations are identical','groups':[{'context_sha256':c,'episodes':sum(v.values()),'goals':[{'goal':g,'count':n} for g,n in v.most_common()]} for c,v in groups.items()],'rows':rows}
(B/'diagnostics'/f'{version}_initial_option_modes.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
