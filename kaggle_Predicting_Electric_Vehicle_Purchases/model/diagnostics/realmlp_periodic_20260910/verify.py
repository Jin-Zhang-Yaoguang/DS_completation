"""独立复算完整五折、身份、文件和固定门槛；不训练、不调权。"""
from pathlib import Path
import json,hashlib,sys
import numpy as np,pandas as pd
from scipy.stats import rankdata,spearmanr
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
P=Path(__file__).resolve().parent;R=P.parents[2]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
yframe=pd.read_csv(R/'data/train.csv',usecols=['id','Will_Buy_EV']);y=yframe.Will_Buy_EV.eq('Yes').to_numpy();ids=yframe.id.to_numpy();z=np.load(P/'diagnostic_oof.npz');np.testing.assert_array_equal(z['ids'],ids);pred=z['pred'];assert pred.shape==(len(y),2) and np.isfinite(pred).all() and ((pred>=0)&(pred<=1)).all()
fold_rows=[]
for fold,(fit,valid) in enumerate(StratifiedKFold(5,shuffle=True,random_state=42).split(ids,y),1):
 d=P/f'fold_{fold}';np.testing.assert_array_equal(np.load(d/'fit_rows.npy'),fit);np.testing.assert_array_equal(np.load(d/'valid_rows.npy'),valid);np.testing.assert_array_equal(z['fold'][valid],fold)
 meta=json.loads((d/'input.json').read_text())
 for name,h in meta['hashes'].items():assert sha(d/name)==h
 scores=[]
 for arm in [0,1]:
  q=d/f'arm_{arm}';a=json.loads((q/'result.json').read_text());assert sha(q/'model.pt')==a['model_sha'];assert sha(q/'prediction.npy')==a['prediction_sha'];np.testing.assert_array_equal(np.load(q/'prediction.npy'),pred[valid,arm]);score=float(roc_auc_score(y[valid],pred[valid,arm]));assert abs(score-a['auc'])<1e-12;scores.append(score)
 fold_rows.append({'fold':fold,'auc':scores,'delta':scores[1]-scores[0]})
a=[float(roc_auc_score(y,pred[:,j])) for j in range(2)];m=y.sum();n=(~y).sum();comps=[]
for j in range(2):
 v=np.r_[pred[y,j],pred[~y,j]];t=rankdata(v);tx=rankdata(v[:m]);ty=rankdata(v[m:]);comps.append(((t[:m]-tx)/n,1-(t[m:]-ty)/m));assert abs((t[:m].sum()/m-(m+1)/2)/n-a[j])<1e-12
se=float(np.sqrt(np.var(comps[1][0]-comps[0][0],ddof=1)/m+np.var(comps[1][1]-comps[0][1],ddof=1)/n));r=json.loads((P/'result.json').read_text());assert abs(r['delta']-(a[1]-a[0]))<1e-12;assert abs(r['conditional_standard_error']-se)<1e-12
wins=sum(x['delta']>0 for x in fold_rows);gate=a[1]-a[0]>=.0001 and wins==5 and a[1]>=.9452;assert gate==r['gate_passed']
sys.path.insert(0,str(R/'model/research_runtime'));from paired_auc import paired_auc
v85=np.load(R/'model/diagnostics/income_context_lowrank_20260906_retry1/diagnostic_oof.npz');np.testing.assert_array_equal(v85['ids'],ids);v100=np.load(R/'model/v100_v90_ctboost_nested_cv_blend/oof_proba.npy')
out={'status':'PASS','gate_passed':gate,'auc':a,'delta':a[1]-a[0],'positive_folds':wins,'independent_midrank_se':se,'matched_v85_comparison':paired_auc(y,v85['pred'][:,0],pred[:,1],z['fold']),'v100_context_only':{'auc':float(roc_auc_score(y,v100)),'candidate_delta':a[1]-roc_auc_score(y,v100),'spearman':float(spearmanr(v100,pred[:,1]).statistic),'scope':'训练/元验证方案不同，只报告差距，不作为同口径晋级证据'},'test_generated':False,'submission_allowed':False,'manifest':{str(f.relative_to(P)):sha(f) for f in P.rglob('*') if f.is_file() and f.name not in ['verification.json','train_log.txt','run.lock']}}
(P/'verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='manifest'},ensure_ascii=False))
