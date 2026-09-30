"""Disaggregate held-out teacher-forced errors; not an arena score."""
from pathlib import Path
import collections,json,sys
import numpy as np
B=Path(__file__).resolve().parent;version=sys.argv[1];D=B/version;sys.path.insert(0,str(D))
import action_space as A,task_features as F,tree_runtime
goal=tree_runtime.Model(D/'goal_rank.npz');market=tree_runtime.Model(D/'market_policy.npz');quantity=tree_runtime.Model(D/'market_quantity.npz')
counts=collections.Counter();right=collections.Counter();confusion=collections.Counter();goal_counts=collections.Counter();goal_right=collections.Counter();gerrors=collections.Counter();qerr=collections.defaultdict(list)
for p in sorted((B/'task_policy_data'/version).glob('validation_*.npz')):
    with np.load(p) as z:
        x=z['market_x'];labels=z['market_y'];pred=np.concatenate([market.a['classes'][market.predict(x[i:i+512]).argmax(1)] for i in range(0,len(x),512)])
        for a,b in zip(labels,pred):counts[int(a)]+=1;right[int(a)]+=int(a==b);confusion[int(a),int(b)]+=1
        mask=(labels>0)&(labels<F.WAIT_MARKET);qx=np.concatenate([x[mask],F.MHOT[labels[mask]]],axis=1);qp=quantity.predict(qx)
        for a,v,y in zip(labels[mask],qp,z['market_quantity'][mask]):qerr[int(a)].append(abs(v-y))
        v=z['validation_x'];scores=goal.predict(v);offsets=z['validation_offsets'];choices=z['validation_choice'];tokens=v[:,-(F.UT+11):-11].argmax(1)
        for j,chosen in enumerate(choices):
            start,stop=offsets[j:j+2];prediction=int(scores[start:stop].argmax());a=int(tokens[start+chosen]);b=int(tokens[start+prediction]);goal_counts[a]+=1;goal_right[a]+=int(prediction==chosen);gerrors[a,b]+=1
names=[*A.MARKET_TOKENS,'WAIT_SLOT']
result={'scope':'Source validation under teacher forcing only; not dynamic competitive performance.',
        'market_by_token':[{'token':names[k],'rows':n,'accuracy':right[k]/n,'quantity_mae':float(np.mean(qerr[k])) if qerr[k] else None,'confusions':[(names[b],v) for (a,b),v in confusion.most_common() if a==k and b!=a][:4]} for k,n in counts.most_common()],
        'goal_by_token':[{'token':A.UNIT_TOKENS[k],'queries':n,'exact_goal_accuracy':goal_right[k]/n,'wrong_token':[(A.UNIT_TOKENS[b],v) for (a,b),v in gerrors.most_common() if a==k and b!=a][:4]} for k,n in goal_counts.most_common()]}
out=B/'diagnostics'/f'{version}_teacher_forced.json';out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
