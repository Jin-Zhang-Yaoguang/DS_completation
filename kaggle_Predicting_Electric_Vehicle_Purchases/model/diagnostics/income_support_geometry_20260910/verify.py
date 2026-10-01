"""Read-only independent identity, fold, AUC and paired midrank verification."""
from pathlib import Path
import hashlib,json
import numpy as np
import pandas as pd
from scipy.stats import rankdata
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold

P=Path(__file__).resolve().parent
R=P.parents[2]
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

raw=pd.read_csv(R/'data/train.csv',usecols=['id','Will_Buy_EV'])
y=raw.Will_Buy_EV.eq('Yes').to_numpy()
z=np.load(P/'diagnostic_oof.npz')
np.testing.assert_array_equal(z['ids'],raw.id)
old=np.load(R/'model/diagnostics/income_context_lowrank_20260906_retry1/diagnostic_oof.npz')
np.testing.assert_array_equal(z['baseline'],old['pred'][:,0])
pred=np.column_stack([z['baseline'],z['pred']])
assert pred.shape==(len(y),2) and np.isfinite(pred).all()
assert ((pred>=0)&(pred<=1)).all()
fold_results=[]
for f,(_,valid) in enumerate(StratifiedKFold(5,shuffle=True,random_state=42).split(raw.id,y),1):
    np.testing.assert_array_equal(z['fold'][valid],f)
    np.testing.assert_array_equal(z['pred'][valid],np.load(P/f'fold_{f}.npy'))
    record=json.loads((P/f'fold_{f}.json').read_text())
    assert sha(P/f'fold_{f}.npy')==record['prediction_sha']
    assert sha(P/f'fold_{f}.txt')==record['model_sha']
    a=[float(roc_auc_score(y[valid],pred[valid,j])) for j in range(2)]
    assert abs(a[0]-record['baseline_auc'])<1e-12
    assert abs(a[1]-record['candidate_auc'])<1e-12
    assert record['baseline_replay_max_abs']<=1e-12
    assert record['candidate_replay_max_abs']<=1e-12
    fold_results.append({'fold':f,'auc':a,'delta':a[1]-a[0]})
a=[float(roc_auc_score(y,pred[:,j])) for j in range(2)]
m=int(y.sum());n=int((~y).sum());components=[]
for j in range(2):
    v=np.r_[pred[y,j],pred[~y,j]]
    ranks=rankdata(v)
    assert abs((ranks[:m].sum()/m-(m+1)/2)/n-a[j])<1e-12
    components.append(((ranks[:m]-rankdata(v[:m]))/n,1-(ranks[m:]-rankdata(v[m:]))/m))
se=float(np.sqrt(np.var(components[1][0]-components[0][0],ddof=1)/m+np.var(components[1][1]-components[0][1],ddof=1)/n))
result=json.loads((P/'result.json').read_text())
assert abs(result['delta']-(a[1]-a[0]))<1e-12
assert abs(result['conditional_standard_error']-se)<1e-12
wins=sum(f['delta']>0 for f in fold_results)
gate=a[1]-a[0]>=.0001 and wins==5
assert gate==result['gate_passed']
out={'status':'PASS','gate_passed':gate,'auc':a,'delta':a[1]-a[0],
     'positive_folds':wins,'independent_midrank_se':se,'folds':fold_results,
     'scope':'Development diagnostic; outer-validation early stopping; no test predictions or submission.',
     'oof_sha':sha(P/'diagnostic_oof.npz'),'verifier_sha':sha(Path(__file__))}
(P/'verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False))
